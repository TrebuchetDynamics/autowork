"""Bounded Pi JSONL transport. No shell, provider fallback, or global configuration writes.

Raw protocol/diagnostics stay in private files. Callbacks are for a trusted local UI,
not public telemetry. The caller owns the subprocess for exactly one turn.
"""
import json
import os
from pathlib import Path
import queue
import select
import signal
import subprocess
import threading
import time
import uuid


class RPCError(Exception):
    """Transport/run failure; raw provider diagnostics deliberately omitted."""


class Cancelled(RPCError):
    pass


def private_dir(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise RPCError('refuse symlinked private state directory')
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def private_open(path, flags=os.O_WRONLY | os.O_CREAT | os.O_APPEND):
    fd = os.open(path, flags | os.O_NOFOLLOW, 0o600)
    os.fchmod(fd, 0o600)
    return os.fdopen(fd, 'ab' if flags & os.O_APPEND else 'wb')


class RPC:
    """One continuous binary stdout reader correlates replies even during steering."""
    MAX_RECORD = 4 * 1024 * 1024
    MAX_LOG = 32 * 1024 * 1024

    def __init__(self, argv, cwd, state, *, cancel=None, on_event=None,
                 command_timeout=20, run_timeout=900, shutdown_timeout=2):
        self.cancel = cancel
        self.on_event = on_event
        self.command_timeout = command_timeout
        self.run_timeout = run_timeout
        self.shutdown_timeout = shutdown_timeout
        self.pending = {}
        self.mutex = threading.Lock()
        self.write_lock = threading.Lock()
        self.events = queue.Queue(maxsize=4096)
        self.failure = None
        self.closed = False
        state = private_dir(state)
        self.raw = private_open(state / (uuid.uuid4().hex + '.jsonl'))
        self.errors = private_open(state / (uuid.uuid4().hex + '.stderr'))
        try:
            self.process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE, start_new_session=True, umask=0o077,
                                            env={k: v for k, v in os.environ.items() if not k.startswith('GIT_')})
        except OSError as exc:
            self.raw.close()
            self.errors.close()
            raise RPCError('could not start Pi RPC executable') from exc
        os.set_blocking(self.process.stdin.fileno(), False)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.stderr_reader = threading.Thread(target=self._stderr, daemon=True)
        self.reader.start()
        self.stderr_reader.start()

    def _fail(self, message):
        with self.mutex:
            self.failure = self.failure or message

    def _read(self):
        total = 0
        try:
            while True:
                # Binary readline splits only at LF, not U+2028 or U+2029.
                line = self.process.stdout.readline(self.MAX_RECORD + 1)
                if not line:
                    self._fail('unexpected EOF from Pi RPC')
                    return
                total += len(line)
                if len(line) > self.MAX_RECORD or not line.endswith(b'\n') or total > self.MAX_LOG:
                    self._fail('Pi RPC output exceeded framing/size budget')
                    return
                self.raw.write(line)
                self.raw.flush()
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError('not an object')
                if record.get('type') == 'response':
                    with self.mutex:
                        waiting = self.pending.get(record.get('id'))
                    if waiting is None:
                        self._fail('uncorrelated Pi RPC response')
                        return
                    try:
                        waiting.put_nowait(record)
                    except queue.Full:
                        self._fail('duplicate Pi RPC response')
                        return
                else:
                    try:
                        self.events.put_nowait(record)
                    except queue.Full:
                        self._fail('Pi RPC event buffer exceeded budget')
                        return
        except (OSError, ValueError, UnicodeError):
            self._fail('invalid Pi RPC output')

    def _stderr(self):
        total = 0
        try:
            while chunk := self.process.stderr.read(8192):
                if total < self.MAX_LOG:
                    self.errors.write(chunk[:self.MAX_LOG - total])
                total += len(chunk)
        except OSError:
            self._fail('cannot drain Pi diagnostics')

    def _check(self, deadline, *, cancellation=True):
        if cancellation and self.cancel is not None and self.cancel.is_set():
            raise Cancelled('planning turn cancelled')
        if self.failure:
            raise RPCError(self.failure)
        if time.monotonic() >= deadline:
            raise RPCError('Pi RPC deadline exceeded')

    def _write(self, payload, deadline):
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8') + b'\n'
        if len(data) > self.MAX_RECORD:
            raise RPCError('Pi RPC input exceeded size budget')
        with self.write_lock:
            while data:
                self._check(deadline, cancellation=payload['type'] not in ('abort', 'clear_queue'))
                _, writable, _ = select.select([], [self.process.stdin], [], .05)
                if writable:
                    try:
                        data = data[os.write(self.process.stdin.fileno(), data):]
                    except (OSError, ValueError) as exc:
                        raise RPCError('Pi RPC input closed') from exc

    def request(self, command, **values):
        ident = uuid.uuid4().hex
        waiting = queue.Queue(maxsize=1)
        deadline = time.monotonic() + self.command_timeout
        with self.mutex:
            if self.closed:
                raise RPCError('Pi RPC is closed')
            self.pending[ident] = waiting
        try:
            self._write(dict(values, id=ident, type=command), deadline)
            while True:
                self._check(deadline)
                try:
                    reply = waiting.get(timeout=.05)
                    break
                except queue.Empty:
                    pass
            if reply.get('command') != command or reply.get('success') is not True:
                raise RPCError('Pi RPC command refused: ' + command)
            return reply.get('data') or {}
        finally:
            with self.mutex:
                self.pending.pop(ident, None)

    def turn(self, message):
        deadline = time.monotonic() + self.run_timeout
        reply = self.request('prompt', message=message)
        self._check(deadline)
        disposition = reply.get('disposition')
        if disposition == 'handled':
            return {'text': '', 'status': 'handled'}
        if disposition not in ('started', 'queued'):
            raise RPCError('unknown Pi prompt disposition')
        text, last_stop, failed_retry = '', None, False
        while True:
            self._check(deadline)
            try:
                event = self.events.get(timeout=.05)
            except queue.Empty:
                continue
            kind = event.get('type')
            if self.on_event is not None:
                self.on_event(event)
            # Cancellation observed while waiting/delivering settlement wins over success.
            self._check(deadline)
            if kind == 'message_end':
                msg = event.get('message') or {}
                if msg.get('role') == 'assistant':
                    last_stop = msg.get('stopReason')
                    text = '\n'.join(c.get('text', '') for c in msg.get('content', [])
                                     if isinstance(c, dict) and c.get('type') == 'text')
            elif kind == 'auto_retry_end':
                failed_retry = event.get('success') is False
            elif kind in ('extension_error', 'extension_ui_request'):
                raise RPCError('unexpected extension activity in read-only planner')
            elif kind == 'agent_settled':
                if event.get('aborted'):
                    raise Cancelled('Pi aborted the planning turn')
                if failed_retry or last_stop not in ('stop', 'length'):
                    raise RPCError('Pi planning turn failed or produced no completed assistant message')
                return {'text': text, 'status': 'ready'}

    def close(self, abort=False):
        with self.mutex:
            if self.closed:
                return
            self.closed = True
        if abort and self.process.poll() is None:
            # Do not await abort: even a wedged provider must have a bounded shutdown.
            for command in ('clear_queue', 'abort'):
                ident = uuid.uuid4().hex
                with self.mutex:
                    self.pending[ident] = queue.Queue(maxsize=1)
                try:
                    self._write({'id': ident, 'type': command},
                                time.monotonic() + self.shutdown_timeout)
                except RPCError:
                    break
        try:
            self.process.stdin.close()
        except OSError:
            pass
        for sig in (None, signal.SIGTERM, signal.SIGKILL):
            if sig is not None:
                try:
                    os.killpg(self.process.pid, sig)
                except ProcessLookupError:
                    pass
            try:
                self.process.wait(timeout=self.shutdown_timeout)
                break
            except subprocess.TimeoutExpired:
                continue
        # Kill remaining tool descendants, even if Pi already exited.
        try:
            os.killpg(self.process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.reader.join(self.shutdown_timeout)
        self.stderr_reader.join(self.shutdown_timeout)
        self.process.stdout.close()
        self.process.stderr.close()
        self.raw.close()
        self.errors.close()
