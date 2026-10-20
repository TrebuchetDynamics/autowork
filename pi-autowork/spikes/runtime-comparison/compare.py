#!/usr/bin/env python3
"""Run identical offline comparison fixtures against real, explicitly cached runtimes.

Compatibility failures are comparison results, NOT passing qualifications. Exit 1
means an unexpected probe/contract failure; recorded incompatibilities exit 0. No fleet
settings, acceptance authority or default runtime are changed by this probe.
"""
import argparse
import hashlib
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from boundary import REPO, Runtime, execution, save

NAMES = ['cancellation', 'restart_adoption', 'stale_results', 'out_of_order', 'combined_tree',
         'cleanup_retention', 'term_to_kill', 'crash_replay', 'pi_events']


def source_hashes():
    paths = [*Path(__file__).parent.glob('*.py'), *Path(__file__).parent.glob('*.mjs'),
             REPO / 'pi-autowork/pi_autowork/pi_runtime.py',
             *(REPO / 'skills/autowork/scripts' / f'{name}.py'
               for name in ['parallel_state', 'task_execution'])]
    return {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def git(cwd, *args, env=None):
    return subprocess.check_output(['git', '-c', 'user.name=Fixture', '-c',
        'user.email=fixture@example.invalid', *args], cwd=cwd, text=True,
        stderr=subprocess.STDOUT, env=env).strip()


class CompatibilityError(Exception):
    """Observed limitation retained as a comparison result, never a qualification."""


class Fixtures:
    def __init__(self, root, backend, config):
        self.root, self.backend, self.config = root, backend, config
        self.handles = []
        self.runtimes = {}
        self.counter = 0

    def workspace(self):
        self.counter += 1
        repo = self.root / f'repo-{self.counter}'
        repo.mkdir()
        git(repo, 'init', '-q', '-b', 'main')
        (repo / '.gitignore').write_text('.worktrees/\n.fixture-*\n.runtime-agwab/\n')
        (repo / 'a.txt').write_text('0')
        (repo / 'b.txt').write_text('0')
        git(repo, 'add', '.gitignore', 'a.txt', 'b.txt')
        git(repo, 'commit', '-qm', 'fixture base')
        worker = repo / '.worktrees/worker'
        git(repo, 'worktree', 'add', '-qb', 'worker', str(worker))
        runtime = Runtime(self.backend, self.root / f'state-{self.counter}', self.config)
        self.runtimes[worker] = runtime
        return repo, worker, runtime

    def launch(self, runtime, cwd, fixture):
        handle = runtime.launch(cwd, fixture)
        self.handles.append((runtime, handle))
        return handle

    def until(self, predicate, runtime, handle, seconds=35):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            event = runtime.observe(handle)
            if predicate(event):
                return event
            if event['status'] not in ('running', 'completed'):
                raise AssertionError(json.dumps(event)[:1500])
            time.sleep(0.04)
        raise AssertionError('fixture deadline exceeded; see retained scratch logs')

    def started(self, runtime, handle, name='.fixture-started'):
        return self.until(lambda _: (Path(handle['cwd']) / name).exists(), runtime, handle)

    def finished(self, runtime, handle):
        event = self.until(lambda e: e['status'] != 'running', runtime, handle)
        assert event['status'] == 'completed', json.dumps(event)[:1500]
        return event

    def cancellation(self):
        _, cwd, runtime = self.workspace()
        handle = self.launch(runtime, cwd, {'op': 'wait'})
        self.started(runtime, handle)
        event = runtime.stop(handle)
        assert event['status'] in ('interrupted', 'failed', 'cancelled'), event
        assert not runtime.live(handle['worker'], handle['cwd'])
        assert cwd.exists()
        return 'active tool stopped; no success delivered; CWD retained'

    def restart_adoption(self):
        _, cwd, runtime = self.workspace()
        # A launching coordinator really exits. A new process/object gets only the
        # serialized handle, not a Popen, callbacks or in-memory runtime state.
        code = ('import json,sys; from boundary import Runtime; '
                'r=Runtime(sys.argv[1],sys.argv[2],json.loads(sys.argv[3])); '
                'print(json.dumps(r.launch(sys.argv[4], {"op":"wait"})))')
        env = {**os.environ, 'PYTHONPATH': str(Path(__file__).parent)}
        handle = json.loads(subprocess.check_output([sys.executable, '-c', code, self.backend,
            str(runtime.root), json.dumps(self.config), str(cwd)], env=env, text=True, timeout=10))
        self.handles.append((runtime, handle))
        self.started(runtime, handle)
        restored = Runtime(self.backend, runtime.root, self.config)
        assert restored.resume(json.loads(json.dumps(handle)))['status'] == 'running'
        (cwd / '.fixture-release').touch()
        self.finished(restored, handle)
        assert (cwd / '.fixture-calls').read_text().splitlines() == ['wait']
        return 'new coordinator adopted live birth identity; 1 tool execution, no relaunch'

    def stale_results(self):
        _, cwd, runtime = self.workspace()
        old = self.launch(runtime, cwd, {'op': 'write', 'file': 'a.txt', 'value': '1'})
        self.finished(runtime, old)
        (cwd / '.fixture-started').unlink()
        current = self.launch(runtime, cwd, {'op': 'wait'})
        assert runtime.observe(old)['status'] == 'stale'
        self.started(runtime, current)
        save(Path(current['directory']) / 'result.json',
             {'token': old['token'], 'status': 'completed'})
        assert runtime.observe(current)['status'] == 'running'
        (cwd / '.fixture-release').touch()
        result = self.finished(runtime, current)
        assert result['token'] == current['token']
        return 'superseded handle rejected; injected old-token success not delivered'

    def out_of_order(self):
        _, a, ra = self.workspace()
        _, b, rb = self.workspace()
        first = self.launch(ra, a, {'op': 'wait', 'file': 'a.txt', 'value': 'first'})
        self.started(ra, first)
        second = self.launch(rb, b, {'op': 'write', 'file': 'b.txt', 'value': 'second'})
        self.finished(rb, second)
        assert ra.observe(first)['status'] == 'running'
        (a / '.fixture-release').touch()
        self.finished(ra, first)
        assert (a / 'a.txt').read_text() == 'first'
        assert (b / 'b.txt').read_text() == 'second'
        return 'second completed before first; distinct receipts and CWD outputs'

    def combined_tree(self):
        repo, a, ra = self.workspace()
        base = git(repo, 'rev-parse', 'HEAD')
        b = repo / '.worktrees/other'
        git(repo, 'worktree', 'add', '-qb', 'other', str(b), base)
        rb = Runtime(self.backend, self.root / f'other-state-{self.counter}', self.config)
        commits = []
        for cwd, runtime, file in [(a, ra, 'a.txt'), (b, rb, 'b.txt')]:
            self.finished(runtime, self.launch(runtime, cwd, {'op': 'write', 'file': file, 'value': '1'}))
            # Each candidate independently satisfies a+b <= 1.
            assert sum(int((cwd / f).read_text()) for f in ('a.txt', 'b.txt')) == 1
            git(cwd, 'add', file)
            git(cwd, 'commit', '-qm', 'fixture candidate')
            commits.append(git(cwd, 'rev-parse', 'HEAD'))
        # Form the exact combined tree in an isolated index, not canonical HEAD.
        env = {**os.environ, 'GIT_INDEX_FILE': str(self.root / f'index-{self.counter}')}
        git(repo, 'read-tree', '-m', base, *commits, env=env)
        tree = git(repo, 'write-tree', env=env)
        combined_ok = sum(int(git(repo, 'show', f'{tree}:{f}')) for f in ('a.txt', 'b.txt')) <= 1
        assert not combined_ok, 'semantic collision was accepted'
        assert git(repo, 'rev-parse', 'HEAD') == base
        return '2 individual passes; exact combined tree rejected (a+b=2); main unchanged'

    def cleanup_retention(self):
        repo, cwd, runtime = self.workspace()
        handle = self.launch(runtime, cwd, {'op': 'write', 'file': 'candidate.txt', 'value': 'retain'})
        self.finished(runtime, handle)
        runtime.stop(handle)
        assert cwd.exists() and (cwd / 'candidate.txt').read_text() == 'retain'
        git(cwd, 'add', 'candidate.txt')
        git(cwd, 'commit', '-qm', 'unmerged candidate')
        assert git(repo, 'rev-parse', 'main') != git(cwd, 'rev-parse', 'HEAD')
        runtime.stop(handle)
        assert cwd.exists() and (cwd / 'candidate.txt').read_text() == 'retain'
        return 'dirty output and then committed-unmerged worktree both retained'

    def term_to_kill(self):
        _, cwd, runtime = self.workspace()
        handle = self.launch(runtime, cwd, {'op': 'stubborn'})
        self.started(runtime, handle, '.fixture-child')
        pid = int((cwd / '.fixture-child').read_text())
        event = runtime.stop(handle)
        assert event['status'] in ('interrupted', 'failed', 'cancelled'), event
        assert not runtime.live(handle['worker'], handle['cwd'])
        # Existing engine liveness ignores zombies: an unreaped killed process
        # cannot write. Verify the TERM-ignoring setsid descendant cannot execute.
        stat = Path(f'/proc/{pid}/stat')
        assert not stat.exists() or stat.read_text().rsplit(')', 1)[1].split()[0] == 'Z'
        return 'TERM-ignoring escaped descendant killed; group/marker liveness drained'

    def crash_replay(self):
        outcomes = []
        for safe in [False, True]:
            _, cwd, runtime = self.workspace()
            handle = self.launch(runtime, cwd, {'op': 'replay', 'safe': safe})
            self.started(runtime, handle)
            os.killpg(handle['worker']['pid'], signal.SIGKILL)  # crash, not graceful abort
            if self.backend == 'agwab':
                # Headless Pi has its own session/process group. Do not quietly kill
                # it as part of the fault: this is the same supervisor-group crash.
                self.until(lambda _: execution.identity(handle['worker']['pid']) is None,
                           runtime, handle, seconds=5)
                recovered = Runtime(self.backend, runtime.root, self.config)
                if recovered.resume(handle)['status'] == 'running':
                    raise CompatibilityError('supervisor-group crash left detached headless Pi live; '
                        'new coordinator sees marker liveness but cannot recover the lost Toolset receipt; '
                        'unsafe tool remains in flight (not replayed); stop is required before retry')
            self.until(lambda e: e['status'] == 'interrupted', runtime, handle)
            (cwd / '.fixture-release').touch()
            recovered = Runtime(self.backend, runtime.root, self.config)
            resumed = recovered.resume(handle)
            if self.backend == 'durable':
                self.handles.append((recovered, resumed))
                receipt = self.finished(recovered, resumed)
                assert receipt['duplicate'], 'requestId did not deduplicate'
                if not safe:
                    assert 'interrupted' in json.dumps(receipt['messages']).lower()
            else:
                assert resumed['status'] == 'interrupted'
                assert 'not replayed' in resumed['message']
            count = len((cwd / '.fixture-calls').read_text().splitlines())
            assert count == (2 if safe and self.backend == 'durable' else 1), count
            outcomes.append(f'{"safe" if safe else "unsafe"} executions={count}')
        return '; '.join(outcomes) + ('; durable requestId deduplicated; unsafe interruption shown to model'
            if self.backend == 'durable' else '; crash continuation refused (no per-tool replay engine)')

    def pi_events(self):
        if self.backend == 'durable':
            return 'not applicable: Harness has its own committed submission/task events, not Pi AgentSession events'
        _, cwd, runtime = self.workspace()
        handle = self.launch(runtime, cwd, {'op': 'settle'})
        self.started(runtime, handle, '.fixture-before-settle')
        assert runtime.observe(handle)['status'] == 'running', 'agent_end incorrectly settled execution'
        assert (cwd / '.fixture-events').read_text().splitlines() == ['agent_end']
        (cwd / '.fixture-settle-release').touch()
        self.finished(runtime, handle)
        events = (cwd / '.fixture-events').read_text().splitlines()
        assert events == ['agent_end', 'agent_end', 'agent_settled'], events
        return '2 agent_end, 1 agent_settled; no terminal delivery at first agent_end'

    def close(self):
        for runtime, handle in self.handles:
            runtime.stop(handle)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', choices=['cli', 'agwab', 'durable', 'all'], default='all')
    parser.add_argument('--pi', help='explicit pinned Pi CLI executable')
    parser.add_argument('--modules', help='cached node_modules with pi-durable 1.3.0')
    parser.add_argument('--agwab', help='AgwaB source checkout at ab91a74')
    parser.add_argument('--output', help='compact measurement JSON, outside runtime state')
    parser.add_argument('--readback', help='verify full retained inventory and exact measured source hashes')
    parser.add_argument('--fixture', choices=NAMES, help='run only one named fixture')
    args = parser.parse_args()
    if args.readback:
        record = json.loads(Path(args.readback).read_text())
        assert record['source_sha256'] == source_hashes(), 'measurement source drift'
        rows = record['fixtures']
        assert len(rows) == 27 and {(r['backend'], r['fixture']) for r in rows} == {
            (b, n) for b in ['cli', 'agwab', 'durable'] for n in NAMES}, 'incomplete/duplicate inventory'
        assert all(r['verdict'] in ['pass', 'compatibility_failure', 'not_applicable'] for r in rows)
        print('Readback: 27 unique measurements; exact source hashes match; incompatibilities remain explicit')
        return 0
    if not all([args.pi, args.modules, args.agwab, args.output]):
        parser.error('--pi, --modules, --agwab and --output are required for execution')
    config = dict(pi=str(Path(args.pi).resolve()), modules=str(Path(args.modules).resolve()),
                  agwab=str(Path(args.agwab).resolve()), node=shutil.which('node'))
    # resolve() on .bin/pi would lose its bin directory for AgwaB's PATH lookup.
    config['pi'] = str(Path(args.pi).absolute())
    backends = ['cli', 'agwab', 'durable'] if args.backend == 'all' else [args.backend]
    version = subprocess.check_output([config['pi'], '--version'], text=True).strip()
    revision = git(config['agwab'], 'rev-parse', 'HEAD')
    if version != '1.3.0' or revision != 'ab91a74fcbd079caa27f9e48932004d1fd9c1e9f':
        parser.error('probe requires Pi 1.3.0 and the pinned AgwaB source; do not relabel another version')
    git(config['agwab'], 'diff', '--exit-code', 'HEAD')
    for package in ['pi-coding-agent', 'pi-durable']:
        package_json = Path(config['modules']) / '@earendil-works' / package / 'package.json'
        if json.loads(package_json.read_text())['version'] != '1.3.0':
            parser.error(f'{package} must be 1.3.0')
    root = Path(tempfile.mkdtemp(prefix='runtime-comparison-', dir=os.environ['TMPDIR']))
    print(f'Scratch (retained for diagnosis): {root}', file=sys.stderr, flush=True)
    results = {'measured_at_utc': datetime.now(timezone.utc).isoformat(), 'pi': '1.3.0', 'agwab': 'ab91a74fcbd079caa27f9e48932004d1fd9c1e9f',
               'durable': '1.3.0', 'node': subprocess.check_output(['node', '--version'], text=True).strip(),
               'source_sha256': source_hashes(), 'fixtures': [], 'capabilities': {}}
    for backend in backends:
        base = root / backend
        base.mkdir()
        suite = Fixtures(base, backend, config)
        results['capabilities'][backend] = Runtime(backend, base / 'capabilities', config).capabilities
        try:
            for name in NAMES:
                if args.fixture and name != args.fixture:
                    continue
                start = time.monotonic()
                try:
                    detail = getattr(suite, name)()
                    verdict = 'not_applicable' if name == 'pi_events' and backend == 'durable' else 'pass'
                except CompatibilityError as error:
                    verdict, detail = 'compatibility_failure', str(error)
                except Exception as error:
                    verdict, detail = 'contract_failure', f'{type(error).__name__}: {error}'
                row = dict(backend=backend, fixture=name, verdict=verdict,
                           seconds=round(time.monotonic() - start, 3), detail=detail)
                results['fixtures'].append(row)
                print(json.dumps(row), flush=True)
        finally:
            suite.close()
    save(Path(args.output), results)
    return int(any(r['verdict'] == 'contract_failure' for r in results['fixtures']))


if __name__ == '__main__':
    raise SystemExit(main())
