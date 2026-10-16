"""Parallel mode is opt-in: sequential output is unchanged and unsupported hosts fall back.

The golden outputs below were captured from the last commit before any parallel
code (b5092b3) on the same fixtures, without and with goals.json, with the repository path and owner PID
replaced by placeholders. Real Git and the real CLI; no model hosts.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

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
T1 = {
    'id': 'T1', 'title': 'repair fixture', 'section': 'Now',
    'contract': '— repair fixture\n  Status: open\n  Scope: fixture.py only\n  Acceptance: fixture records '
                'execution\n  Checks: run fixture\n  Dependencies: None.\n  Ownership: current coordinator',
    'fields': {'Status': 'open', 'Scope': 'fixture.py only', 'Acceptance': 'fixture records execution',
               'Checks': 'run fixture', 'Dependencies': 'None.', 'Ownership': 'current coordinator'},
}
EXECUTE = {'outcome': 'EXECUTE', 'task': T1, 'completed_tasks': [], 'workspace': 'REPO',
           'priority': {'state': 'todo_only'},
           'reason': 'Current coordinator owns this TODO task; implement, check, review and record '
                     'completion in repository files.'}
LEDGER = {'version': 1, 'goals': [{'id': 'G', 'title': 'fixture', 'source': 'TODO.md', 'status': 'partial',
                                   'tasks': ['T1', 'T2'], 'priority': 1, 'depends_on': []}],
          'tasks': [{'id': 'T1', 'title': 'repair fixture', 'goal': 'G', 'status': 'open', 'section': 'Now',
                     'depends_on': []},
                    {'id': 'T2', 'title': 'successor', 'goal': 'G', 'status': 'open', 'section': 'Next',
                     'depends_on': ['T1']}]}
UNMIGRATED = {'state': 'unmigrated',
              'action': 'UNMIGRATED: TODO.md order is not recorded; legacy goal-priority selection applies. '
                        'Run `goals.py bootstrap-order <repo> --dry-run`, then apply with its revision.'}


def golden(priority, dependency_reason):
    """(arguments, exit code, stdout object) in call order against one fixture."""
    execute = dict(EXECUTE, priority=priority)
    return [
        ([], 0, {'outcome': 'READY', 'task': T1, 'completed_tasks': [], 'workspace': 'REPO', 'priority': priority}),
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
        (self.repo / 'TODO.md').write_text(TODO)
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

    def test_sequential_output_is_byte_identical_to_pre_parallel_release(self):
        self.assert_golden(golden({'state': 'todo_only'}, 'T2: unresolved dependency T1'))

    def test_ledger_output_is_byte_identical_to_pre_parallel_release(self):
        (self.repo / 'goals.json').write_text(json.dumps(LEDGER))
        self.assert_golden(golden(UNMIGRATED, 'T2: ledger dependency or disposition holds execution'))

    def assert_fallback(self, p, reason):
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        result = json.loads(p.stdout)
        self.assertEqual(result['outcome'], 'SEQUENTIAL_FALLBACK')
        self.assertIn(reason, result['reason'])
        self.assertEqual(result['task'], T1)
        self.assertIn('owner_cycle.py --apply', result['next'])
        # Nothing parallel was claimed or started: no journal, slots, worktrees or branches.
        execution = self.common / 'autowork-execution'
        self.assertFalse((execution / 'journal.jsonl').exists())
        self.assertFalse((execution / 'slots').exists())
        self.assertFalse((execution / 'coordinator.json').exists())
        self.assertFalse(list(self.repo.parent.glob('repo-autowork-*')))
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
        self.assertEqual(p.stdout.replace(str(self.repo), 'REPO'), json.dumps(EXECUTE, indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
