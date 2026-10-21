"""Parallel mode is opt-in: sequential output is unchanged by it and unsupported hosts fall back.

The expected outputs are the sequential selector's own, built from the task store's contract
for the fixture's first task; the parallel flags must not change a byte of them. Real Git and
the real CLI; no model hosts.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import store_fixture
import task_queue

CLI = Path(__file__).with_name('owner_cycle.py')
TODO = '''# Work
## Now
- [ ] T1 — repair fixture
  Status: open
  Scope: fixture.py only
  Acceptance: fixture records execution
  Checks: run fixture
  Dependencies: None.
  Ownership: current coordinator
## Next
- [ ] T2 — successor
  Status: open
  Scope: fixture.py
  Acceptance: successor works
  Checks: run fixture
  Dependencies: T1.
'''


def golden(task, dependency_reason):
    """(arguments, exit code, stdout object) in call order against one fixture."""
    priority = task['priority']
    execute = {'outcome': 'EXECUTE', 'task': {k: v for k, v in task.items() if k != 'priority'},
               'completed_tasks': [], 'workspace': 'REPO', 'priority': priority,
               'reason': 'Current coordinator owns this task; implement, check, review and record '
                         'completion in repository files.'}
    return [
        ([], 0, {'outcome': 'READY', 'task': execute['task'], 'completed_tasks': [], 'workspace': 'REPO',
                 'priority': priority}),
        (['--tasks', 'T2'], 1, {'outcome': 'ACTION_REQUIRED', 'reason': dependency_reason}),
        (['--apply', '--owner-pid', 'PID'], 0, execute),
        (['--apply', '--owner-pid', 'PID'], 0, execute),
        (['--apply', '--owner-pid', 'PID', '--release'], 0, {'outcome': 'RELEASED'}),
    ]


class ParallelCompatibilityTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / 'repo'
        self.repo.mkdir()
        self.state = Path(tmp.name) / 'state'
        self.state.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        store_fixture.write_todo(self.repo, TODO)
        snapshot = task_queue.store(self.repo)
        self.t1 = task_queue.contract(snapshot.tasks['T1'], snapshot)
        self.common = self.repo / '.git'
        # A caller's GIT_DIR (for example inside a hook) must not redirect the CLI.
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}

    def call(self, *args, env=None):
        args = [str(os.getpid()) if a == 'PID' else a for a in args]
        return subprocess.run([sys.executable, str(CLI), str(self.repo), '--state-dir', str(self.state), *args],
                              capture_output=True, text=True, timeout=30, env=env or self.env)

    def assert_golden(self, expected_calls):
        for args, code, expected in expected_calls:
            with self.subTest(args=args):
                p = self.call(*args)
                self.assertEqual(p.returncode, code, p.stdout + p.stderr)
                self.assertEqual(p.stdout.replace(str(self.repo), 'REPO'), json.dumps(expected, indent=2) + '\n')
        execution = self.common / 'autowork-execution'
        self.assertFalse((execution / 'journal.jsonl').exists())
        self.assertFalse((execution / 'coordinator.json').exists())

    def test_sequential_output_is_the_selectors_own(self):
        self.assert_golden(golden(self.t1, 'T2: unresolved dependency T1'))

    def assert_fallback(self, p, reason):
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        result = json.loads(p.stdout)
        self.assertEqual(result['outcome'], 'SEQUENTIAL_FALLBACK')
        self.assertIn(reason, result['reason'])
        self.assertEqual(result['task'], {k: v for k, v in self.t1.items() if k != 'priority'})
        self.assertIn('owner_cycle.py --apply', result['next'])
        # Nothing parallel was claimed or started: no journal, slots, worktrees or branches.
        execution = self.common / 'autowork-execution'
        self.assertFalse((execution / 'journal.jsonl').exists())
        self.assertFalse((execution / 'slots').exists())
        self.assertFalse((execution / 'coordinator.json').exists())
        self.assertFalse(list((self.repo / '.worktrees').glob('autowork-*')))
        branches = subprocess.run(['git', '-C', str(self.repo), 'branch', '--list', 'autowork/*'],
                                  capture_output=True, text=True, check=True).stdout
        self.assertEqual(branches, '')

    def test_claude_coordinator_without_worker_command_falls_back(self):
        p = self.call('--apply', '--parallel', '2', '--worker-host', 'claude', '--owner-pid', 'PID')
        self.assert_fallback(p, 'explicit --worker-command')

    def test_missing_worker_cli_falls_back(self):
        bin_dir = self.state / 'bin'  # only git: no hermes, codex or pi
        bin_dir.mkdir()
        (bin_dir / 'git').symlink_to(shutil.which('git'))
        env = dict(self.env, PATH=str(bin_dir))
        for host in ('hermes', 'codex', 'pi'):
            with self.subTest(host=host):
                p = self.call('--apply', '--parallel', '2', '--worker-host', host, '--owner-pid', 'PID', env=env)
                self.assert_fallback(p, 'is not installed')

    def test_fallback_leaves_sequential_claim_available(self):
        self.assert_fallback(self.call('--apply', '--parallel', '--worker-host', 'claude', '--owner-pid', 'PID'),
                             'explicit --worker-command')
        p = self.call('--apply', '--owner-pid', 'PID')
        expected = golden(self.t1, '')[2][2]
        self.assertEqual(p.stdout.replace(str(self.repo), 'REPO'), json.dumps(expected, indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
