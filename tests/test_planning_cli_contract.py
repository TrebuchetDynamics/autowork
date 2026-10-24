"""Planning examples at the public task CLI seam; runtime detail stays in test_task_commands."""
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / 'pi-autowork/pi_autowork/command.py'
WORKCENTER = 'skills/shared/TODO-WORKCENTER.md'
PLANNER = 'skills/plan-for-me/SKILL.md'
HANDOFF = 'skills/shared/PLAN-HANDOFF.md'


def prose(path):
    return ' '.join((ROOT / path).read_text().split())


class PlanningCliContractTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / 'repo'
        shutil.copytree(ROOT / 'pi-autowork/engine/fixtures/task_store', self.repo)
        for args in (('init', '-q'), ('add', '-A'), ('commit', '-qm', 'fixture')):
            subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=Fixture',
                            '-c', 'user.email=fixture@example.invalid', *args],
                           check=True, capture_output=True, text=True)

    def tasks(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(COMMAND), 'tasks', *args],
                                cwd=self.repo, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0 if ok else 1, result.stderr)
        return result

    def show(self):
        return json.loads(self.tasks('show', 'T-1', '--worktree').stdout)

    def test_documented_planning_close_forms_are_manual(self):
        original = (self.repo / 'tasks/items/T-1.md').read_bytes()
        for flags, missing in ((('--by', 'WHO'), '--reason'), (('--reason', 'TEXT'), '--by')):
            refused = subprocess.run([sys.executable, str(COMMAND), 'tasks', 'done', 'T-1', *flags],
                                     cwd=self.repo, capture_output=True, text=True, timeout=60)
            self.assertEqual(refused.returncode, 2)
            self.assertIn(missing, refused.stderr)
            self.assertEqual((self.repo / 'tasks/items/T-1.md').read_bytes(), original)
        for path in (PLANNER, WORKCENTER, 'adapters/skills/plan-for-me/SKILL.md'):
            forms = re.findall(r'`(autowork tasks done [^`]+)`', prose(path))
            self.assertTrue(forms, path)
            for index, form in enumerate(forms):
                with self.subTest(path=path, form=form):
                    tid = self.tasks('add', '--goal', 'G-1', '--title', f'{path} {index}',
                                     '--short', 'Planning close', '--kind', 'plan', '--scope', 'Plan',
                                     '--acceptance', 'Saved', '--checks', 'true', '--touches', 'docs/').stdout.split()[-1]
                    args = shlex.split(form.replace('autowork tasks ', '').replace('[--evidence REF]', ''))
                    args = [tid if arg == 'ID' else arg for arg in args]
                    result = subprocess.run([sys.executable, str(COMMAND), 'tasks', *args],
                                            cwd=self.repo, capture_output=True, text=True, timeout=60)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    record = json.loads(self.tasks('show', tid, '--worktree').stdout)
                    self.assertEqual((record['status'], record['closure']['provenance']), ('done', 'manual'))
                    self.assertEqual((record['closure']['actor'], record['closure']['reason']), ('WHO', 'TEXT'))
                    self.assertFalse((self.repo / f'tasks/evidence/{tid}.toml').exists())
        center = prose(WORKCENTER)
        for required in ('verified_depends_on', 'owner_waiver', 'owner_qualification', 'Never invent'):
            self.assertIn(required, center)

    def test_documented_literal_update_reconciles_a_stale_read(self):
        center = prose(WORKCENTER)
        read = 'autowork tasks show ID --worktree'
        update = 'autowork tasks field ID --json field.json --expect REV'
        self.assertIn(read, center)
        self.assertIn(update, center)
        shown = json.loads(self.tasks(*['T-1' if arg == 'ID' else arg
                                        for arg in shlex.split(read)[2:]]).stdout)
        literal = '`literal` $(not-a-command) $VAR "quoted" café\nsecond line'
        (self.repo / 'field.json').write_text(json.dumps({'label': 'scope', 'value': literal}), encoding='utf-8')
        self.tasks('field', 'T-1', 'Evidence', 'Concurrent evidence to preserve')
        path = self.repo / 'tasks/items/T-1.md'
        current = path.read_bytes()
        args = [shown['record_revision'] if arg == 'REV' else 'T-1' if arg == 'ID' else arg
                for arg in shlex.split(update)[2:]]
        refused = self.tasks(*args, ok=False)
        self.assertIn('reread', refused.stderr)
        self.assertEqual(path.read_bytes(), current)
        latest = self.show()
        # Reconcile the intended scope delta, not a replay of the earlier whole record.
        self.assertEqual(latest['scope'], shown['scope'])
        self.assertIn('Concurrent evidence to preserve', latest['notes'])
        args[-1] = latest['record_revision']
        self.tasks(*args)
        final = self.show()
        self.assertEqual(final['scope'], literal)
        self.assertIn('Concurrent evidence to preserve', final['notes'])
        for required in ('operation-local', 'reread', 'reapply', 'blind retry', 'stale full snapshot'):
            self.assertIn(required, center)

    def test_identifier_guidance_matches_current_allocation_without_renaming_history(self):
        center = prose(WORKCENTER)
        self.assertIn('eight-hex-digit', center)
        self.assertIn('Keep existing IDs unchanged', center)
        self.assertNotIn('two-hex-digit', center)
        self.assertNotIn('never create two tasks with the same ID', center)
        before = (self.repo / 'tasks/items/T-1.md').read_bytes()
        self.assertRegex(self.tasks('new-id').stdout.strip(), r'^T-\d+-[0-9a-f]{8}$')
        self.assertEqual((self.repo / 'tasks/items/T-1.md').read_bytes(), before)

    def test_readiness_guidance_separates_selection_from_dispatch_and_delivery(self):
        handoff = prose(HANDOFF)
        self.assertIn('committed-store selection', handoff)
        self.assertIn('admission', handoff)
        self.assertIn('dispatch', handoff)
        self.assertIn('branch-local', handoff)
        self.assertIn('consumer', handoff)
        self.assertNotIn('checks the ordered frontier within the named tasks\' goals', handoff)
        center = prose(WORKCENTER)
        for required in ('hot production', 'test modules', 'cold', 'affected', 'full', 'mandatory checks'):
            self.assertIn(required, center)
        planner = prose(PLANNER)
        self.assertIn('prepare_api', planner)
        self.assertIn('same coordinator', planner)


if __name__ == '__main__':
    unittest.main()
