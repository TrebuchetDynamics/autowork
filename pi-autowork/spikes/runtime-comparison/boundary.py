"""TOOLSET-117-cb experiment, NOT a production runtime selection mechanism.

launch -> JSON-serializable handle; observe -> normalized execution event;
stop -> bounded process-tree stop; resume -> adopt live work or recover storage.
Toolset owns CWD, attempt fencing, process identity and retention. A settled
execution is never verification, acceptance, integration or cleanup permission.
"""
import fcntl
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import time
import uuid

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO / 'skills/autowork/scripts'), str(REPO / 'pi-autowork')]
import parallel_state as state
import task_execution as execution
from pi_autowork import pi_runtime

HERE = Path(__file__).resolve().parent


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix('.new')
    temporary.write_text(json.dumps(value))
    os.replace(temporary, path)


class Runtime:
    """Single coordinator/writer per root; no concurrent mutation API promised."""
    def __init__(self, backend, root, config):
        if backend not in ('cli', 'agwab', 'durable'):
            raise ValueError(backend)
        self.backend, self.root, self.config = backend, Path(root), config
        self.root.mkdir(parents=True, exist_ok=True)
        self.children = []
        self.capabilities = dict(
            live_process_reuse=False, persistent_transcripts=True,
            reload_survival='coordinator-reload-only', extension_reload_survival='not-qualified',
            crash_restart_adoption='storage-resume' if backend == 'durable' else 'live-only',
            per_tool_replay={'fixture_safe': 'safe', 'fixture_unsafe': 'unsafe'},
            replay_default='unsafe', per_tool_replay_enforced=backend == 'durable')

    @staticmethod
    def owned_leader(worker):
        return worker if worker and execution.identity(worker['pid']) == worker else None

    def live(self, worker, cwd):
        return bool(self.owned_leader(worker) or state.strays(str(Path(cwd).resolve())))

    def launch(self, cwd, fixture, previous=None):
        cwd = Path(cwd).resolve()
        if self.live((previous or {}).get('worker'), cwd):
            raise RuntimeError('CWD still has a live writer')
        token = uuid.uuid4().hex
        directory = self.root / token
        directory.mkdir()
        request = dict(backend=self.backend, config=self.config, cwd=str(Path(cwd).resolve()),
                       fixture=fixture, token=token, directory=str(directory),
                       storage=str(self.root / 'storage'),
                       requestId=(execution.read(Path(previous['directory']) / 'request.json')['requestId']
                                  if previous else token), resume=previous is not None)
        save(directory / 'request.json', request)  # register before spawning
        save(self.root / 'active.json', {'token': token})
        env = {**os.environ, state.WORKER_MARKER: request['cwd'], 'PI_OFFLINE': '1',
               'PI_CODING_AGENT_DIR': str(self.root / 'agent-home'),
               'PI_CODING_AGENT_SESSION_DIR': str(self.root / 'sessions'),
               'HOME': str(self.root / 'agent-home'),
               'PATH': str(Path(self.config['pi']).parent) + os.pathsep + os.environ['PATH']}
        # Preserve only explicitly isolated resources; never load a user's extensions/auth.
        with (directory / 'supervisor.log').open('wb') as log:
            process = subprocess.Popen([sys.executable, str(HERE / 'boundary.py'),
                                        'execute', str(directory / 'request.json')],
                                       cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        self.children.append(process)
        worker = execution.identity(process.pid)
        if worker is None:
            process.wait(timeout=10)
            raise RuntimeError('supervisor exited before birth identity was recorded')
        return dict(token=token, backend=self.backend, cwd=request['cwd'],
                    directory=str(directory), worker=worker)

    def observe(self, handle):
        for child in self.children:
            child.poll()  # reap completed children, not adopted processes
        if execution.read(self.root / 'active.json') != {'token': handle['token']}:
            return dict(status='stale', token=handle['token'])
        receipt = execution.read(Path(handle['directory']) / 'result.json')
        # Wait for descendants too, even when a terminal receipt already exists.
        if self.live(handle['worker'], handle['cwd']):
            return dict(status='running', token=handle['token'])
        if receipt and receipt.get('token') == handle['token']:
            return receipt
        return dict(status='interrupted', token=handle['token'],
                    message='Worker interrupted; unfinished tools/checks were not replayed.')

    def stop(self, handle):
        if execution.read(self.root / 'active.json') != {'token': handle['token']}:
            return dict(status='stale', token=handle['token'])
        # Recheck birth at EACH escalation. A recycled numeric PGID is not proof
        # of ownership; after the leader exits, only marked descendants qualify.
        for sig in (signal.SIGTERM, signal.SIGKILL):
            if not self.live(handle['worker'], handle['cwd']):
                break
            leader = self.owned_leader(handle['worker'])
            if leader:
                try:
                    os.killpg(leader['pid'], sig)
                except ProcessLookupError:
                    pass
            for pid in state.strays(handle['cwd']):
                identity = execution.identity(pid)
                if identity and execution.identity(pid) == identity:
                    try:
                        os.kill(pid, sig)
                    except ProcessLookupError:
                        pass
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline and self.live(handle['worker'], handle['cwd']):
                time.sleep(0.05)
        return self.observe(handle)

    def resume(self, handle):
        event = self.observe(handle)
        if event['status'] != 'interrupted' or self.backend != 'durable':
            return event
        request = execution.read(Path(handle['directory']) / 'request.json')
        return self.launch(handle['cwd'], request['fixture'], previous=handle)


def execute(request):
    directory = Path(request['directory'])
    config = request['config']
    if request['backend'] == 'cli':
        settings = pi_runtime.Settings(directory, {'PI_BIN': config['pi']})
        run = pi_runtime.run_pi(settings, request['cwd'], 'FIXTURE_JSON:' + json.dumps(request['fixture']),
                                request['token'], 'offline/fixture', 45,
                                ['--offline', '--no-extensions', '--no-skills', '--no-context-files',
                                 '--no-prompt-templates', '--extension', str(HERE / 'provider.mjs'),
                                 '--tools', 'fixture_safe,fixture_unsafe'])
        result = dict(status='completed' if run['settled'] and not run['aborted']
                      and run['rc'] == 0 and run['stop'] == 'stop' else 'failed', run=run)
    else:
        # pi-durable explicitly has no cross-process storage lock. Enforce one owner
        # here before opening it, including across crash/restart attempts.
        with (Path(request['storage']).with_suffix('.lock')).open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            child = subprocess.run([config['node'], str(HERE / 'bridge.mjs'),
                                    str(directory / 'request.json')], check=False)
            result = execution.read(directory / 'bridge-result.json') or dict(
                status='failed', message=f'bridge exited {child.returncode}; see supervisor.log')
    save(directory / 'result.json', dict(result, token=request['token']))


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'execute':
        execute(json.loads(Path(sys.argv[2]).read_text()))
    else:
        raise SystemExit('internal spike supervisor: execute REQUEST')
