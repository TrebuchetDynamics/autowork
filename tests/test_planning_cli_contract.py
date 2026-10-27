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
INTERACTIVE = ('skills/plan-with-me/SKILL.md', 'adapters/skills/plan-with-me/SKILL.md')
AUTONOMOUS = (PLANNER, 'adapters/skills/plan-for-me/SKILL.md')
SPECIAL_CASES = 'skills/plan-with-me/references/special-cases.md'


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
        portable = prose(AUTONOMOUS[1])
        for required in ('[Docs Sync](../docs-sync/SKILL.md)', 'capability/prepare flow',
                         'actual consumer', 'reuse its result while inputs are unchanged',
                         'do not install updates or interrupt workers'):
            with self.subTest(portable_prepare=required):
                self.assertIn(required, portable)

    def test_planning_handoffs_limit_selection_claims_and_disclose_delivery(self):
        # Entrypoints must not turn a branch's selection result into runtime readiness.
        for path in (*INTERACTIVE, *AUTONOMOUS):
            text = prose(path)
            marker = ('## Save answers and finish the plan' if path == INTERACTIVE[0]
                      else '## Save the plan and hand off' if path == PLANNER
                      else 'Use the [single-pass handoff]')
            handoff = text.split(marker, 1)[1]
            with self.subTest(path=path):
                self.assertIn('autowork tasks why ID', handoff)
                self.assertIn('committed-store selection eligibility and position only', handoff)
                self.assertIn('not resource/ownership admission, capacity or dispatch', handoff)
                self.assertIn('branch-local commit', handoff)
                self.assertIn('actual canonical consumer', handoff)
                self.assertIn('whether that consumer includes the commit', handoff)
                self.assertIn('whether selection was checked there', handoff)
                self.assertIn('runtime and ownership unassessed unless observed', handoff)
                self.assertNotIn('shows whether each task can run', handoff)
                self.assertNotIn('actual readiness result', handoff)

    def test_interactive_runtime_failure_reuses_task_and_coordinator(self):
        # A known failed attempt is recovery evidence, not a new product interview.
        for path in INTERACTIVE:
            with self.subTest(path=path):
                text = prose(path)
                self.assertIn('When existing execution fails without new product uncertainty', text)
                self.assertIn('exact task ID, attempt evidence and failed operation', text)
                self.assertIn('same coordinator for supported recovery', text)
                self.assertIn('do not reopen the product interview or create duplicate tasks', text)
                self.assertIn('single-pass handoff', text)
                self.assertIn('builder check', text)

    def test_autonomous_blocker_routing_preserves_existing_contract_and_recovery(self):
        # Runtime trouble must not trigger blanket fix/skip or forced acceptance splitting.
        for path in AUTONOMOUS:
            text = prose(path)
            with self.subTest(path=path, rule='no blanket fix or split'):
                self.assertNotIn('return a **fix or skip** decision', text)
                self.assertNotIn('skip by splitting the blocked acceptance', text)
            for required in (
                    'classify the observed source and phase',
                    'Resolve engineering planning choices within delegated scope',
                    'existing task or candidate has a runtime, transport, gate or continuation failure',
                    'exact failed operation, task ID, attempt evidence and source-bound candidate evidence',
                    'same coordinator for supported recovery',
                    'no new interview, replacement task or acceptance split just to get moving',
                    'genuinely unavailable external, owner or physical-access inputs pending',
                    'only on affected tasks, with the exact missing input and resume condition',
                    'Split only when authorized scope and evidence justify decomposition',
                    'preserve existing task IDs, contracts, acceptance and history',
                    'never silently waive acceptance',
                    'single-pass handoff', 'builder check'):
                with self.subTest(path=path, rule=required):
                    self.assertIn(required, text)

    def test_ready_continuation_returns_without_executing_inside_planning(self):
        continuation = prose(SPECIAL_CASES).split('## Continuations and live gates', 1)[1]
        for rule in ("recheck that worker's terminal state",
                     'return the ready continuation to the existing authorized coordinator',
                     'execution outside standalone planning under existing scope and limits',
                     'otherwise keep one pending request',
                     'Do not ask again for settled authorization',
                     'explicit current no-execution limit',
                     'preserves existing pauses'):
            with self.subTest(rule=rule):
                self.assertIn(rule, continuation)
        self.assertNotIn('execute the continuation now', continuation)


if __name__ == '__main__':
    unittest.main()
