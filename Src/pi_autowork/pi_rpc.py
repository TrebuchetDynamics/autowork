"""SDK-backed Pi execution. Task admission, retry and closure stay in pi_runtime/engine.

This module imports the SDK only when executing. The synchronous engine runs this
host beneath pi_process's OS ownership boundary, never a shared fleet daemon.
"""
import asyncio
from dataclasses import asdict, dataclass
import fcntl
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import sys
import time
import uuid

from pi_autowork.layout import LAYOUT
from pi_autowork import pi_run_support

SDK_VERSION = '0.2.6'
PI_VERSION = '1.4.0'
MAX_PROMPT_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class RunSpec:
    pi: str
    directory: str
    state: str
    session: str
    target: str
    role: str
    prompt: str
    prompt_digest: str
    timeout: float
    extra_args: tuple
    environment: tuple
    task: str = ''
    attempt_id: str = ''
    contract_hash: str = ''
    command_timeout: float = 30.0
    allow_steering: bool = False


def make_spec(settings, directory, message, session, target, limit, extra, role=None, task=''):
    """Expand only caller-supplied startup attachments, never @text inside RPC input."""
    timeout = float(limit)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('Pi timeout must be positive and finite')
    parts, args = [], []
    for arg in [*settings.skill_args, *extra]:
        if arg.startswith('@'):
            path = Path(arg[1:])
            if not path.is_absolute():
                path = Path(directory) / path
            with path.open('rb') as stream:
                content = stream.read(MAX_PROMPT_BYTES + 1)
            if len(content) > MAX_PROMPT_BYTES:
                raise ValueError('Pi prompt attachment exceeds the bounded input size')
            parts.append(content.decode('utf-8'))
        else:
            args.append(arg)
    prompt = '\n\n'.join([*parts, message])
    if len(prompt.encode('utf-8')) > MAX_PROMPT_BYTES:
        raise ValueError('Pi prompt exceeds the bounded input size')
    # Trust flags are not OS sandboxing. Explicitly disable retained ambient MCP
    # for reviewers/diagnostics, where --tools alone does not remove it in Pi 1.4.
    if role in ('verify', 'reviewer', 'triage', 'investigator'):
        args += ['--no-mcp']
    attempt_id = contract_hash = ''
    if task:
        try:
            from pi_autowork import telemetry
            engine = telemetry.engine()
            slot = engine.execution.read(engine.slot_path(engine.common_dir(directory), task)) or {}
            attempt_id = str(slot.get('attempt_id') or '')
            contract = engine.execution.read(engine.common_dir(directory) / 'slot-data' / task /
                                             f"attempt-{slot.get('attempt')}" / 'contract.json') or {}
            contract_hash = str(contract.get('contract_hash') or '')
        except (OSError, ValueError, RuntimeError):
            pass  # Auxiliary jobs have no engine attempt; they cannot be steered.
    return RunSpec(str(settings.pi), str(Path(directory).resolve()), str(settings.state.resolve()),
                   session, target, role or 'job', prompt,
                   hashlib.sha256(prompt.encode()).hexdigest(), timeout,
                   tuple(['--no-approve', *args]), tuple(os.environ.items()), task,
                   attempt_id, contract_hash,
                   allow_steering=os.environ.get('PI_AUTOWORK_STEERING') == '1')


def private_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex)
    try:
        with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
            json.dump(value, stream, separators=(',', ':'))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def runtime_path(state, session, suffix='json'):
    return Path(state) / 'rpc' / (hashlib.sha256(session.encode()).hexdigest() + '.' + suffix)


CONTROL_TEXT = {
    'reconcile': 'Reconcile the existing worktree and report with the accepted task contract before continuing. '
                 'Preserve partial work. Do not expand scope, permissions, checks or publication authority.',
    'avoid_repeat': 'Do not repeat an unchanged failing approach. Inspect its existing evidence and choose '
                    'another approach within the accepted task contract. Required checks and review still apply.',
}


def authorize_control(spec, request):
    """Only fixed corrective templates, not arbitrary model/tool-derived instructions."""
    allowed = {'kind', 'action', 'task', 'attempt_id', 'contract_hash', 'fingerprint', 'generation'}
    if set(request) - allowed or request.get('kind') not in ('steer', 'follow_up'):
        raise ValueError('unsupported control; arbitrary instructions are not authorized')
    if not spec.allow_steering or spec.role != 'worker':
        raise ValueError('automatic steering is disabled or role is not a worker')
    for field in ('task', 'attempt_id', 'contract_hash'):
        if not getattr(spec, field) or request.get(field) != getattr(spec, field):
            raise ValueError('control does not match the pinned attempt contract')
    if not re.fullmatch(r'[a-f0-9]{64}', str(request.get('fingerprint', ''))):
        raise ValueError('control requires a bounded evidence fingerprint')
    if request.get('action') not in CONTROL_TEXT:
        raise ValueError('unsupported corrective action')
    return CONTROL_TEXT[request['action']]


class PiRpcRuntime:
    """One client, one owned attempt invocation. No internal retry or scheduler."""
    def __init__(self, spec):
        from pi_autowork.pi_events import EventProjection
        self.spec = spec
        self.events = EventProjection()
        self.generation = uuid.uuid4().hex
        self.client = None
        self.active = False
        self.failure = None
        self.pi_version = None
        self._done = asyncio.Event()
        self._control_lock = asyncio.Lock()
        from pi_autowork.processes import start_time
        self.host_start = start_time(os.getpid())
        self.pi_identity = None
        self.stopping = {}

    def progress(self):
        return dict(self.events.progress(), transport='rpc', sdk_version=SDK_VERSION,
                    pi_version=self.pi_version, session_id=self.spec.session,
                    task=self.spec.task, attempt_id=self.spec.attempt_id,
                    contract_hash=self.spec.contract_hash, generation=self.generation,
                    prompt_digest=self.spec.prompt_digest, role=self.spec.role,
                    active=self.active, failure_kind=self.failure, updated_at=time.time(),
                    pid=os.getpid(), start_time=self.host_start, command_interruptions=len(self.stopping))

    async def get_state(self):
        if not self.client or not self.active:
            raise ValueError('no active owned Pi client')
        return await self.client.get_state(timeout=self.spec.command_timeout)

    async def abort(self):
        if self.client and self.active:
            await self.client.clear_queue(timeout=self.spec.command_timeout)
            await self.client.abort(timeout=self.spec.command_timeout)

    async def control(self, request):
        async with self._control_lock:
            return await self._control(request)

    async def _control(self, request):
        text = authorize_control(self.spec, request)
        if request.get('generation') != self.generation or not self.active or self.events.outcome()['settled']:
            raise ValueError('stale or settled runtime generation')
        # Reads can involve Git and filesystem I/O: never block SDK event routing.
        await asyncio.to_thread(self._assert_binding)
        path = runtime_path(self.spec.state, self.spec.session, 'controls.json')
        try:
            history = json.loads(path.read_text())
        except FileNotFoundError:
            history = []
        if not isinstance(history, list) or len(history) >= 3:
            raise ValueError('intervention budget exhausted or invalid')
        if any(row['fingerprint'] == request['fingerprint'] for row in history):
            raise ValueError('duplicate intervention')
        if history and time.time() - history[-1]['at'] < 60:
            raise ValueError('intervention cooldown')
        row = dict(at=time.time(), fingerprint=request['fingerprint'], action=request['action'],
                   kind=request['kind'], generation=self.generation, disposition='uncertain')
        history.append(row)
        # Spend the budget before sending. A crash can never replay this intervention.
        await asyncio.to_thread(private_json, path, history)
        await asyncio.to_thread(self._assert_binding)
        if not self.active or self.events.progress()['settled']:
            raise ValueError('run settled before control; spent budget retained')
        response = await self.client.request(request['kind'], message=text, timeout=self.spec.command_timeout)
        row['disposition'] = (response.get('data') or {}).get('disposition', 'accepted')
        await asyncio.to_thread(private_json, path, history)
        return dict(row)  # ACK is never reported as consumed.

    def _assert_binding(self):
        from pi_autowork import telemetry
        engine = telemetry.engine()
        from pi_autowork.engine.task_store import TaskStore
        common = engine.common_dir(self.spec.directory)
        slot = engine.execution.read(engine.slot_path(common, self.spec.task)) or {}
        contract = engine.execution.read(common / 'slot-data' / self.spec.task /
                                         f"attempt-{slot.get('attempt')}" / 'contract.json') or {}
        if (slot.get('attempt_id') != self.spec.attempt_id
                or contract.get('contract_hash') != self.spec.contract_hash or slot.get('state') != 'running'):
            raise ValueError('engine attempt changed; control refused')
        canonical = common.parent.parent  # existing engine common is <git-common>/autowork-execution
        store = TaskStore.at(canonical, 'HEAD')
        task = store.tasks.get(self.spec.task)
        if (task is None or task.status != 'open' or task.contract_hash != self.spec.contract_hash
                or f'tasks/items/{self.spec.task}.md' in TaskStore.pending(canonical)):
            raise ValueError('canonical contract changed; control refused')

    async def _watch_commands(self):
        from pi_autowork.processes import alive
        limit = pi_run_support.command_limit(self.spec.role, self.spec.timeout, env=dict(self.spec.environment))
        if limit and self.pi_identity and alive(*self.pi_identity):
            await asyncio.to_thread(pi_run_support.stop_stuck_commands, os.getpid(), limit,
                                    self.stopping, pi_pid=self.pi_identity[0], pi_started=self.pi_identity[1])

    def _save_progress(self):
        value = self.progress()
        private_json(runtime_path(self.spec.state, self.spec.session), value)
        if self.spec.task:
            private_json(runtime_path(self.spec.state, self.spec.role + ':' + self.spec.task, 'active.json'), value)

    async def _publish(self):
        while not self._done.is_set():
            await self._watch_commands()
            await asyncio.to_thread(self._save_progress)
            try:
                await asyncio.wait_for(self._done.wait(), .25)
            except TimeoutError:
                pass
        await asyncio.to_thread(self._save_progress)

    async def execute(self):
        from pi_autowork.pi_events import ProjectionOverflow
        begin = time.monotonic()
        failure, retry_safe, rc = None, False, 1
        lock = publisher = None
        try:
            if version('pi-agent-python-sdk') != SDK_VERSION:
                failure = 'toolchain'
                return self._outcome(begin, failure, False, 1)
            from pi_agent import (AsyncPiClient, Limits, PiCommandError, PiTimeoutError, PiVersionError,
                                  PiProcessError, PiProtocolError, PiRunError,
                                  PiSubscriptionOverflow, PiResultOverflow)
            lock_path = runtime_path(self.spec.state, self.spec.session, 'lock')
            lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            lock = os.fdopen(os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600), 'w')
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                failure = 'session_busy'
                return self._outcome(begin, failure, False, 1)
            publisher = asyncio.create_task(self._publish())
            provider, _, model = self.spec.target.partition('/')
            limits = Limits(command_timeout=self.spec.command_timeout,
                            run_start_timeout=self.spec.command_timeout,
                            startup_timeout=min(30, self.spec.timeout), cleanup_timeout=2)
            self.client = AsyncPiClient(executable=self.spec.pi, cwd=self.spec.directory,
                                       provider=provider, model=model or provider,
                                       session_dir=str(Path(self.spec.state) / 'sessions'),
                                       session_id=self.spec.session, extra_args=self.spec.extra_args,
                                       env=dict(self.spec.environment), inherit_env=False,
                                       strict_version=True, limits=limits)
            from pi_autowork.processes import start_time
            before = set(pi_run_support._children(os.getpid()))
            try:
                async with self.client:
                    children = set(pi_run_support._children(os.getpid())) - before
                    if len(children) == 1:
                        pid = children.pop()
                        born = start_time(pid)
                        if not born:
                            raise RuntimeError('Pi process identity unavailable')
                        self.pi_identity = (pid, born)
                    else:
                        raise RuntimeError('cannot identify the exclusively owned Pi process')
                    self.pi_version = self.client.pi_version
                    if self.pi_version != PI_VERSION:
                        raise RuntimeError('toolchain')
                    self.active = True
                    async with self.client.stream(self.spec.prompt, timeout=self.spec.timeout) as stream:
                        async for event in stream:
                            self.events.consume(event.raw)
                            if publisher.done():
                                publisher.result()  # Failed observation is not silent success.
                        await stream.result()  # Includes successful ACK, even if events arrived first.
                    state = await self.get_state()
                    if state.get('sessionId') != self.spec.session:
                        failure = 'session_identity'
                    elif self.events.outcome()['aborted']:
                        failure = 'interrupted'
                    elif not self.events.outcome()['settled']:
                        failure = 'unsettled'
                    else:
                        rc = 0
            except PiVersionError:
                failure = 'toolchain'
            except PiCommandError:
                failure = 'rejected'
            except PiTimeoutError:
                failure = 'uncertain_acceptance'
            except (PiSubscriptionOverflow, PiResultOverflow, ProjectionOverflow):
                failure = 'overflow'
            except PiProtocolError:
                failure = 'protocol'
            except PiProcessError:
                failure = 'transport'
            except PiRunError:
                outcome = self.events.outcome()
                failure = ('provider' if outcome['stop'] == 'error' and not outcome['aborted'] else 'interrupted')
                retry_safe = failure == 'provider' and outcome['settled'] and not outcome['aborted']
        except (PackageNotFoundError, ImportError):
            failure = 'toolchain'
        except asyncio.CancelledError:
            failure = 'interrupted'
        except (OSError, ValueError, RuntimeError):
            failure = failure or 'runtime'
        finally:
            self.active = False
            self.failure = failure
            self._done.set()
            if publisher:
                try:
                    await publisher
                except (OSError, ValueError, RuntimeError):
                    failure, retry_safe, rc = 'observation', False, 1
            if lock:
                lock.close()
        return self._outcome(begin, failure, retry_safe, rc)

    def _outcome(self, begin, failure, retry_safe, rc):
        from pi_autowork.pi_events import ProjectionOverflow
        try:
            values = self.events.outcome()
        except ProjectionOverflow:
            values = pi_run_support.analyse('')
            failure, retry_safe, rc = 'overflow', False, 1
        return dict(values, rc=rc, seconds=time.monotonic()-begin,
                    failure_kind=failure, retry_safe=retry_safe,
                    transport='rpc', sdk_version=SDK_VERSION, pi_version=self.pi_version,
                    session_id=self.spec.session, generation=self.generation,
                    command_interruptions=len(self.stopping), prompt_digest=self.spec.prompt_digest)


def sdk_python(settings):
    if settings.rpc_python:
        return settings.rpc_python
    try:
        if version('pi-agent-python-sdk') == SDK_VERSION:
            return sys.executable
    except PackageNotFoundError:
        pass
    root = Path(os.environ.get('PI_AUTOWORK_STATE_DIR') or
                Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local/state') / 'pi-autowork')
    return str(root / 'runtimes' / ('pi-rpc-' + SDK_VERSION) / 'bin/python')


def readiness(settings):
    """No imports of SDK in the CLI, no installs/auth refresh or model calls."""
    try:
        result = subprocess.run([sdk_python(settings), '-c',
                                 "from importlib.metadata import version; print(version('pi-agent-python-sdk'))"],
                                capture_output=True, text=True, timeout=15)
        if result.returncode or result.stdout.strip() != SDK_VERSION:
            return 'Pi RPC SDK 0.2.6 required; run python3 scripts/install-pi-rpc.py'
        result = subprocess.run([settings.pi, '--version'], capture_output=True, text=True, timeout=15)
        if result.returncode or result.stdout.strip() != PI_VERSION:
            return 'Pi RPC requires qualified Pi 1.4.0; installed executable is incompatible'
    except (OSError, subprocess.SubprocessError):
        return 'Pi RPC toolchain unavailable; run python3 scripts/install-pi-rpc.py (or explicitly select JSON rollback)'
    return ''


def run(settings, directory, message, session, target, limit, extra, role=None, task='', *,
        stop_requested=lambda: False):
    """Synchronous engine seam; cancellation stays owned by the calling job runtime."""
    from pi_autowork.processes import start_time
    base = dict(pi_run_support.analyse(''), rc=1, seconds=0, transport='rpc', sdk_version=SDK_VERSION,
                failure_kind='toolchain', retry_safe=False, cleanup_complete=False)
    reason = readiness(settings)
    if reason:
        return dict(base, error=reason)
    try:
        spec = make_spec(settings, directory, message, session, target, limit, extra, role, task)
    except (OSError, ValueError, UnicodeError):
        return dict(base, failure_kind='prompt', error='Invalid or oversized accepted prompt input')
    runs = settings.state / 'runs'
    runs.mkdir(parents=True, exist_ok=True, mode=0o700)
    begin = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='rpc-', dir=runs) as temporary:
        identity = Path(temporary) / 'process.json'
        argv = [sys.executable, str(LAYOUT.entrypoint('pi_autowork.pi_process')),
                '--identity', str(identity), '--deadline', str(float(limit) + 10),
                '--parent-pid', str(os.getpid()), '--parent-start', str(start_time(os.getpid())), '--',
                sdk_python(settings), str(LAYOUT.entrypoint('pi_autowork.pi_rpc'))]
        try:
            child = subprocess.Popen(argv, cwd=directory, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            started = start_time(child.pid)
            payload = json.dumps(asdict(spec)).encode()
            while True:
                if time.monotonic() - begin > float(limit) + 25:
                    child.kill()  # Missing cleanup proof is terminal; never replay.
                    try:
                        child.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        pass
                    return dict(base, failure_kind='cleanup_unproven', error='Process guard exceeded cleanup deadline')
                try:
                    output, _ = child.communicate(payload, timeout=.5)
                    break
                except subprocess.TimeoutExpired:
                    payload = None
                    if stop_requested() or time.monotonic() - begin > float(limit) + 20:
                        child.terminate()  # Guard remains alive to reap its complete subtree.
            proof = json.loads(identity.read_text())
            try:
                result = json.loads(output)
                if not isinstance(result, dict):
                    raise ValueError('result is not an object')
            except (ValueError, UnicodeError):
                result = dict(base, failure_kind='transport', error='SDK host returned no valid terminal outcome')
            clean = bool(started and proof.get('pid') == child.pid and proof.get('start_time') == started
                         and proof.get('cleanup_complete') is True and proof.get('exit_code') is not None)
            result['cleanup_complete'] = clean
            result['retry_safe'] = bool(clean and result.get('retry_safe'))
            if not clean:
                result.update(rc=1, failure_kind='cleanup_unproven', retry_safe=False)
            elif child.returncode != 0:
                result.update(rc=child.returncode, retry_safe=False,
                              failure_kind='timeout' if child.returncode == 124 else 'interrupted')
            result['seconds'] = time.monotonic() - begin
            result['error'] = pi_run_support.redact(str(result.get('error') or ''))[:300]
            return result
        except (OSError, ValueError):
            return dict(base, failure_kind='cleanup_unproven', error='RPC host or ownership proof unavailable',
                        seconds=time.monotonic()-begin)


def main():
    # Input is private stdin, not a prompt-bearing process argument or public log.
    raw = sys.stdin.buffer.read(MAX_PROMPT_BYTES * 2 + 1)
    if len(raw) > MAX_PROMPT_BYTES * 2:
        raise ValueError('runtime input exceeds bounded size')
    values = json.loads(raw)
    values['extra_args'] = tuple(values['extra_args'])
    values['environment'] = tuple(tuple(pair) for pair in values['environment'])
    spec = RunSpec(**values)

    async def run():
        task = asyncio.create_task(PiRpcRuntime(spec).execute())
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, task.cancel)
        return await task
    print(json.dumps(asyncio.run(run())), flush=True)


def _compat_main(argv):
    if argv:
        raise ValueError('RPC host accepts its input over stdin, not command arguments')
    return main()
