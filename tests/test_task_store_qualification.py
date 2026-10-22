"""Task Store v2 qualification on a disposable fixture repository (TOOLSET-301-32).

A runner converts nothing on its own and refuses an unconverted repository; after
`autowork migrate` it selects, runs and closes one task with one receipt commit. Each
step's command and outcome is printed as a `QUALIFICATION` line. The workers, reviewer
and model are the fake Pi of test_pi_autowork: offline evidence, not a live fleet claim.
"""
import json
from pathlib import Path
import subprocess
import sys
import unittest

import test_pi_autowork
from test_pi_autowork import Fixture, todo

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / 'pi-autowork/pi_autowork/command.py'
sys.path.insert(0, str(ROOT / 'pi-autowork/engine'))
import store_fixture  # noqa: E402
import task_queue  # noqa: E402


def setUpModule():
    test_pi_autowork.setUpModule()  # the runner under test is this change's committed code


def tearDownModule():
    test_pi_autowork.tearDownModule()


class QualificationTests(Fixture):
    def note(self, command, result):
        print(f'QUALIFICATION {command} -> exit {result.returncode}', flush=True)

    def test_a_runner_converts_nothing_then_runs_one_task_after_migration(self):
        # The repository as it was before the store: one task in TODO.md and goals.json.
        self.git(self.repo, 'rm', '-r', '-q', 'tasks')
        legacy = todo([('A', None)])
        (self.repo / 'TODO.md').write_text(legacy)
        (self.repo / 'goals.json').write_text(json.dumps(store_fixture._ledger_for(legacy), indent=2))
        self.git(self.repo, 'add', 'TODO.md', 'goals.json')
        self.git(self.repo, 'commit', '-qm', 'a repository from before the task store')
        before = self.git(self.repo, 'rev-parse', 'HEAD')

        refused = self.run_runner('--once')
        self.note('pi-autowork.sh --once (unconverted)', refused)
        self.assertEqual(refused.returncode, 4, refused.stdout + refused.stderr)
        self.assertIn('autowork migrate', refused.stderr)
        self.assertFalse((self.repo / 'tasks').exists())  # it converted nothing
        self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), before)
        self.assertEqual(self.git(self.repo, 'status', '--porcelain'), '')
        self.assertEqual(self.runs(), [])  # no worker, no model

        migrated = subprocess.run([sys.executable, str(COMMAND), 'migrate', str(self.repo)],
                                  capture_output=True, text=True, timeout=120, env=self.env)
        self.note('autowork migrate', migrated)
        self.assertEqual(migrated.returncode, 0, migrated.stdout + migrated.stderr)
        self.assertEqual(self.git(self.repo, 'rev-list', '--count', f'{before}..HEAD'), '1')
        self.assertFalse((self.repo / 'TODO.md').exists())
        self.assertFalse((self.repo / 'goals.json').exists())
        self.assertEqual(task_queue.record(self.repo, 'A').status, 'open')
        converted = self.git(self.repo, 'rev-parse', 'HEAD')

        ran = self.run_runner('--once')
        self.note('pi-autowork.sh --once (converted)', ran)
        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        self.assertEqual([r['task'] for r in self.runs('worker')], ['A'])
        self.assertTrue(self.done('A'))
        self.assertEqual(task_queue.record(self.repo, 'A').status, 'done')
        closes = self.git(self.repo, 'log', '--format=%H', f'{converted}..HEAD', '--grep=^docs(tasks): close A').split()
        self.assertEqual(len(closes), 1)
        self.assertEqual(sorted(self.git(self.repo, 'show', '--format=', '--name-only', closes[0]).split()),
                         ['tasks/evidence/A.toml', 'tasks/items/A.md'])
        receipt = (self.repo / 'tasks/evidence/A.toml').read_text()
        self.assertIn(f'contract_hash = "{task_queue.record(self.repo, "A").contract_hash}"', receipt)
        self.assertNotIn(str(self.repo), receipt)
        self.assertEqual(task_queue.stale_closures(self.repo), [])
        print('QUALIFICATION result: refused before migration, one conversion commit, '
              'one task selected, run and closed with one receipt commit (offline fixture)', flush=True)


if __name__ == '__main__':
    unittest.main()
