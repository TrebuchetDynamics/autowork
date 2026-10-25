"""Read-only blocker report: real committed store, no services or agents."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import fleet_view, blockers_report


class BlockersReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo, self.state = self.root / 'repo', self.root / 'state'
        shutil.copytree(Path(__file__).resolve().parents[1] / 'engine/fixtures/task_store', self.repo)
        self.state.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')
        self.runner = fleet_view.Runner('example', repo=str(self.repo), state='paused',
                                      service='dead', state_dir=str(self.state), prepare_state='converted')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True).strip()

    def test_full_copyable_report_without_writes_or_truncation(self):
        reason = 'Waiting for an external dependency: ' + 'full detail ' * 40 + 'END-OF-REASON'
        self.runner.blocker = 'dispatch stopped by the main check'
        self.runner.gate = 'memory budget exhausted'
        self.runner.stop_reason = 'startup preflight refused'
        revision = 'abcdef1234567890' * 2 + '12345678'
        failure = 'tests.test_unique_failure.Example.test_diagnostic'
        self.runner.main_check = {'state': 'red', 'rev': revision, 'failures': [failure]}
        self.runner.questions = [fleet_view.Question('Q-' + str(i), 'input', 0, reason) for i in range(6)]
        self.runner.lanes = [fleet_view.Lane('T-2', 'waiting to integrate', 'checkout occupied',
                                            activity_age=1800)]
        self.runner.waiting_groups = [{'label': reason, 'count': 25, 'tasks': ['T-' + str(i) for i in range(25)]}]
        (self.state / 'status.json').write_text(json.dumps({'updated_at': 123, 'tasks': [
            ['T-1', 'held', 'validation', reason]]}))
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        text = blockers_report.build(self.runner)
        self.assertIn('Runner: example', text)
        self.assertIn('Repository: ' + str(self.repo), text)
        for word in ['paused', 'dead', 'memory budget exhausted', 'startup preflight refused',
                     'checkout occupied', 'Q-5', 'T-24', reason, '123', 'Committed task', 'T-1',
                     revision, failure]:
            self.assertIn(word, text)
        self.assertIn('may be stale', text)
        self.assertNotIn('\x1b', text)
        self.assertEqual(before, {p.relative_to(self.root): p.read_bytes()
                                  for p in self.root.rglob('*') if p.is_file()})

    def test_inventory_join_annotations_remain_in_details_not_the_owner_summary(self):
        from dataclasses import replace
        snap = fleet_view.snapshot_for(self.runner)
        warning = 'RETIRED-99: unmatched execution observation (closed)'
        self.runner.snapshot = replace(snap, annotations=(warning,))
        report = blockers_report.build(self.runner)
        self.assertIn(warning, report)
        self.assertNotIn(warning, blockers_report.summary(report))

    def test_committed_decisions_holds_and_dependencies_not_uncommitted_text(self):
        path = self.repo / 'tasks/items/T-1.md'
        path.write_text(path.read_text().replace('section = "Now"', 'section = "Needs decision"')
                        + '\n- Question: Which supported backend?\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'decision')
        path.write_text('uncommitted invalid content must not become a report')
        text = blockers_report.build(self.runner)
        self.assertIn('NEEDS_DECISION', text)
        self.assertIn('Which supported backend?', text)
        self.assertNotIn('uncommitted invalid', text)

    def test_unavailable_sources_are_not_reported_as_no_blockers(self):
        self.runner.repo = str(self.root / 'missing')
        (self.state / 'status.json').write_text('{bad json')
        text = blockers_report.build(self.runner)
        self.assertIn('Committed task information unavailable', text)
        self.assertIn('Runtime status unavailable', text)
        self.assertNotIn('No blockers', text)

    def test_question_acquisition_errors_survive_the_fleet_snapshot_attachment(self):
        (self.repo / 'BLOCKERS.md').write_bytes(b'\xff')
        errors = []
        self.runner.questions = fleet_view.read_questions(str(self.repo), errors=errors)
        self.runner.acquisition_errors = errors
        self.assertTrue(errors, 'the real question reader must observe the bad source')
        fleet_view.snapshot_for(self.runner)
        text = blockers_report.build(self.runner)
        self.assertIn('Fleet acquisition error', text)
        self.assertIn(errors[0], text)
        self.assertIn('Eligible for selection', text, 'observation errors must not replace current eligibility')

    def test_committed_hold_and_dependency_use_the_shared_selector(self):
        first = self.repo / 'tasks/items/T-1.md'
        original = first.read_text()
        first.write_text(original + '\n- Held by: fixture owner; reason pending approval\n')
        (first.parent / 'T-2.md').write_text(original.replace('id = "T-1"', 'id = "T-2"')
                                          .replace('depends_on = []', 'depends_on = ["T-1"]'))
        self.git('add', '.')
        self.git('commit', '-qm', 'held prerequisite')
        text = blockers_report.build(self.runner)
        self.assertIn('HELD: fixture owner; reason pending approval', text)
        self.assertIn('DEPENDENCY_UNFINISHED: T-1', text)

    def test_invalid_committed_store_is_explicit(self):
        (self.repo / 'tasks/items/T-1.md').write_text('invalid store')
        self.git('add', '.')
        self.git('commit', '-qm', 'invalid fixture')
        text = blockers_report.build(self.runner)
        self.assertIn('Committed task information unavailable', text)
        self.assertNotIn('No open records', text)

    def test_real_producer_full_held_and_root_reasons_survive_compact_task_summaries(self):
        from pi_autowork import health
        reason = 'Long validation diagnostic ' * 20 + 'ACTIONABLE-HELD-SUFFIX'
        root_reason = 'Full dependency root ' * 20 + 'ACTIONABLE-ROOT-SUFFIX'
        wait_reason = 'Full waiting diagnostic ' * 20 + 'ACTIONABLE-WAIT-SUFFIX'
        ids = ['DEPENDENT-' + str(i) for i in range(25)]
        health.update(self.state, {'outcome': 'PARALLEL_STATUS', 'tasks': [
            {'task': 'T-1', 'state': 'held', 'cause': 'validation', 'reason': reason},
            {'task': 'T-2', 'state': 'waiting', 'reason': wait_reason}],
            'roots': [{'id': 'T-1', 'kind': 'held', 'cause': 'validation',
                       'reason': root_reason, 'blocks': 25, 'tasks': ids}],
            'merge_backlog': {'paused': True, 'count': 3, 'oldest_seconds': 9876,
                              'reason': 'integration waiting for live writer pid 123 pi'}}, now=123)
        data = json.loads((self.state / 'status.json').read_text())
        self.assertEqual(data['held'][0]['reason'], reason)
        self.assertEqual(data['roots'][0]['reason'], root_reason)
        text = blockers_report.build(self.runner)
        self.assertIn(reason, text)
        self.assertIn(root_reason, text)
        self.assertIn(wait_reason, text)
        self.assertIn('DEPENDENT-24', text)
        self.assertIn('integration waiting for live writer pid 123 pi', text)
        self.assertIn('paused=True; count=3; oldest_seconds=9876', text)

    def test_decision_summary_reconciles_ids_and_flags_restricted_selectable_tasks(self):
        path = self.repo / 'tasks/items/T-1.md'
        original = path.read_text()
        path.write_text(original + '\n- Owner decision: 2026-10-22: No ejecutar hasta autorización y corpus revisado.\n')
        (path.parent / 'T-2.md').write_text(original.replace('id = "T-1"', 'id = "T-2"')
            .replace('section = "Now"', 'section = "Needs decision"')
            + '\n- Question: Which bounded phase and verified inputs?\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'record owner gates')
        self.runner.state, self.runner.service, self.runner.minutes = 'blocked', 'running', 936
        reason = 'Authorization and reviewed corpus required. ' + 'specific evidence ' * 20 + 'FINAL-INPUT'
        self.runner.questions = [fleet_view.Question('T-1', 'input', 0, reason[:60] + '…',
            'widen touches or narrow the acceptance'), fleet_view.Question('PLAN-1', 'decision', 1,
            'Task: [T-2](tasks/items/T-2.md), Needs decision / owner. Question: Which bounded phase?')]
        self.runner.held = [('T-1', 'blocker')]
        (self.state / 'status.json').write_text(json.dumps({'updated_at': 1792791493,
            'merge_backlog': {'paused': False, 'count': 0},
            'held': [{'task': 'T-1', 'cause': 'blocker', 'reason': reason}],
            'task_observations': [{'task': 'T-1', 'state': 'held', 'cause': 'blocker', 'reason': reason},
                                  {'task': 'DONE-1', 'state': 'closed', 'reason': ''}],
            'tasks': [['T-1', 'held', 'blocker', reason[:60]], ['DONE-1', 'closed', '', '']]}))
        report = blockers_report.build(self.runner)
        summary = report.split('\n\n## Diagnostics\n')[0]
        self.assertIn('Awaiting owner decisions', summary)
        self.assertIn('execution restriction', summary)
        self.assertIn('Raised by: PLAN-1', summary)
        self.assertIn('tasks/items/T-2.md', summary)
        self.assertNotIn('ago ago', report)
        self.assertEqual(summary.count('Which bounded phase and verified inputs?'), 1)
        self.assertEqual(summary.count('FINAL-INPUT'), 1)
        self.assertNotIn('narrow the acceptance', report)
        self.assertNotIn('DONE-1', summary)
        self.assertIn('No worker observations supplied', summary)
        self.assertIn('Recorded blocked-state duration:', summary)
        self.assertNotIn('1792791493', summary)
        self.assertIn('2026-10-23', report)
        self.assertLess(len(summary), 2400)
        self.assertEqual(report.count(reason), 1, 'full runtime reason must not be dumped three times')

    def test_engineering_blockers_do_not_become_an_owner_only_headline(self):
        self.runner.state = 'blocked'
        self.runner.questions = [fleet_view.Question('CHOICE', 'decision', 0, 'Which product?')]
        self.runner.held = [('T-1', 'reviewed_twice')]
        report = blockers_report.build(self.runner)
        self.assertNotIn('Awaiting owner decisions', report.splitlines()[0])
        self.assertIn('reviewed_twice', report)

    def test_technical_roots_and_partial_runtime_data_preclude_owner_only_headline(self):
        self.runner.state = 'blocked'
        self.runner.questions = [fleet_view.Question('T-1', 'decision', 0, 'Permission required')]
        for status in ({}, {'tasks': [], 'roots': [{'id': 'OTHER-1', 'cause': 'reviewed_twice'}]},
                       {'tasks': [], 'roots': 'invalid'}):
            with self.subTest(status=status):
                (self.state / 'status.json').write_text(json.dumps(status))
                report = blockers_report.build(self.runner)
                self.assertNotIn('Awaiting owner decisions', report.splitlines()[0])

    def test_integrated_but_unclosed_work_is_not_hidden_as_closed_history(self):
        (self.state / 'status.json').write_text(json.dumps({'task_observations': [
            {'task': 'T-1', 'state': 'integrated', 'reason': 'Awaiting closure after main check'}]}))
        report = blockers_report.build(self.runner)
        self.assertIn('Awaiting closure after main check', report)

    def test_linked_question_keeps_distinct_planning_requirements_in_details(self):
        path = self.repo / 'tasks/items/T-1.md'
        path.write_text(path.read_text() + '\n- Question: Which phase?\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'record question')
        self.runner.questions = [fleet_view.Question('PLAN-1', 'decision', 1,
            'Task: [T-1](tasks/items/T-1.md) Question: Which phase? Also requires LEGAL-APPROVAL-42.')]
        report = blockers_report.build(self.runner)
        self.assertIn('Raised by: PLAN-1', blockers_report.summary(report))
        self.assertIn('LEGAL-APPROVAL-42', report)
        self.assertIn('PLAN-1 → T-1', report)

    def test_same_id_question_preserves_fleet_only_technical_hold(self):
        self.runner.state = 'blocked'
        self.runner.questions = [fleet_view.Question('T-1', 'decision', 1, 'Old permission question')]
        self.runner.held = [('T-1', 'reviewed_twice')]
        (self.state / 'status.json').write_text('{"tasks": []}')
        summary = blockers_report.summary(blockers_report.build(self.runner))
        self.assertIn('reviewed_twice', summary)
        self.assertIn('fleet', summary.lower())
        self.assertNotIn('Awaiting owner decisions', summary.splitlines()[0])

    def test_shared_reason_keeps_each_task_association_via_reference(self):
        self.runner.questions = [fleet_view.Question(task, 'decision', 0, 'Owner must provide dataset')
                                 for task in ('Q-1', 'Q-2')]
        summary = blockers_report.summary(blockers_report.build(self.runner))
        self.assertEqual(summary.count('Owner must provide dataset'), 1)
        second = summary.split('2. Q-2', 1)[1]
        self.assertIn('Recorded question: Same text as [E1]', second)

    def test_multiline_full_reason_deduplicates_whitespace_compacted_legacy_row(self):
        full = 'First validation detail\nSecond validation detail ' + 'long evidence ' * 30
        status = {'task_observations': [{'task': 'T-1', 'state': 'held', 'cause': 'validation', 'reason': full}],
                  'tasks': [['T-1', 'held', 'validation', ' '.join(full.split())[:100]]]}
        errors = []
        rows = blockers_report._runtime(status, errors)
        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['reason'], full)
        status['tasks'][0][-1] = 'Different observation which must not be lost'
        self.assertEqual(len(blockers_report._runtime(status, [])), 2)

    def test_source_diagnostics_heading_cannot_truncate_the_summary(self):
        self.runner.questions = [fleet_view.Question('T-1', 'decision', 0,
            'Required input\n\n## Diagnostics\nDO-NOT-LOSE-THIS-REQUIREMENT')]
        report = blockers_report.build(self.runner)
        self.assertIn('DO-NOT-LOSE-THIS-REQUIREMENT', blockers_report.summary(report))
        self.assertNotIn('Committed task information', blockers_report.summary(report))

    def test_recorded_deferral_is_short_and_does_not_invent_a_new_permission_question(self):
        path = self.repo / 'tasks/items/T-1.md'
        original = path.read_text()
        decision = ('2026-10-22: Preserve the recorded owner deferral until the upstream root, '
                    'authorization and confinement contract is available. No new permission question. '
                    + 'Retain existing acceptance and evidence. ' * 12)
        path.write_text(original.replace('section = "Now"', 'section = "Needs decision"')
                        + '\n- Owner decision: ' + decision + '\n')
        dependent = original.replace('id = "T-1"', 'id = "T-2"').replace('section = "Now"', 'section = "Next"')
        dependent = dependent.replace('depends_on = []', 'depends_on = ["T-1"]').replace('checks = ["python3 -m unittest"]', 'checks = []')
        (path.parent / 'T-2.md').write_text(dependent)
        self.git('add', '.')
        self.git('commit', '-qm', 'existing deferral and dependent')
        self.runner.state, self.runner.service = 'stalled', 'running'
        resolved = ('# BLOCKERS\n## Active\n<!-- pi-autowork:questions:start -->\n'
                    '<!-- pi-autowork:questions:end -->\n## Resolved\n'
                    '### Q-OLD-PLAN — Planning stopped\n- Status: RESOLVED\n'
                    '- Task: T-1 — owner-only deferred continuation.\n')
        (self.repo / 'BLOCKERS.md').write_text(resolved)
        self.runner.questions = fleet_view.read_questions(self.repo)
        self.assertEqual(fleet_view.question_summary(self.runner), '')
        from pi_autowork import task_snapshot
        snapshot = task_snapshot.capture(self.repo, engine_observation={}, generation=1)
        self.assertEqual(next(row.why for row in snapshot.rows if row.task == 'T-1'),
                         'recorded owner deferral')
        self.runner.main_check = {'state': 'green', 'rev': 'a' * 40}
        (self.state / 'status.json').write_text(json.dumps({'updated_at': 1792791493,
            'merge_backlog': {'count': 0, 'paused': False}, 'tasks': [
                ['T-2', 'waiting', '', 'wait for deferred T-1'], *[
                    ['CLOSED-' + str(n), 'closed', '', ''] for n in range(100)]]}))
        report = blockers_report.build(self.runner)
        brief = blockers_report.summary(report)
        self.assertLess(len(brief.splitlines()), 10)
        self.assertLess(len(brief), 1000)
        self.assertIn('until the upstream root, authorization and confinement contract is available', brief)
        self.assertIn('full note: Details', brief)
        self.assertNotIn('2026-10-22:', brief)
        self.assertIn('recorded deferral', brief.lower())
        self.assertIn('no new question', brief.lower())
        self.assertIn('T-2', brief)
        self.assertIn('checks', brief)
        self.assertNotIn('Awaiting owner decisions', report)
        self.assertNotIn('record the answer/input', report)
        self.assertNotIn('CLOSED-', brief)
        self.assertIn(decision.strip(), report, 'full evidence remains in Details')
        data = json.loads((self.state / 'status.json').read_text())
        data['tasks'].append(['UNRELATED', 'held', 'blocker', 'Do not hide this different prerequisite'])
        (self.state / 'status.json').write_text(json.dumps(data))
        self.assertIn('Do not hide this different prerequisite',
                      blockers_report.summary(blockers_report.build(self.runner)))
        data['tasks'].pop()
        for fleet_count, runtime_count in ((1, 0), (0, 1)):
            with self.subTest(fleet=fleet_count, runtime=runtime_count):
                self.runner.running = fleet_count
                data['active_workers'] = runtime_count
                (self.state / 'status.json').write_text(json.dumps(data))
                current = blockers_report.summary(blockers_report.build(self.runner))
                self.assertIn('Captured:', current, 'positive activity counts require the general report')
                source = 'fleet' if fleet_count else 'runtime'
                self.assertIn(f'Recorded worker count ({source}): 1', current)
                self.assertNotIn('No worker observations supplied', current)
        self.runner.running = 0
        data['active_workers'] = 0
        data['tasks'][0] = ['T-2', 'waiting', 'session_claim', 'LIVE-WRITER-777 must release the checkout']
        (self.state / 'status.json').write_text(json.dumps(data))
        self.assertIn('LIVE-WRITER-777', blockers_report.summary(blockers_report.build(self.runner)))

    def test_compact_wait_requires_deferral_evidence_not_just_an_open_task_id(self):
        for row in ({'blocked_by': ['OTHER']}, {'blocked_by': []}, {'blocked_by': 'T-1'},
                    {'blocked_by': ['T-1'], 'cause': 'session_claim'},
                    {'blocked_by': ['T-1'], 'root_kind': 'contract'}, {'reason': 'independent wait'}):
            with self.subTest(row=row):
                self.assertFalse(blockers_report._deferred_wait(row, {'T-1'}))
        self.assertTrue(blockers_report._deferred_wait({'blocked_by': ['T-1']}, {'T-1'}))
        self.assertTrue(blockers_report._deferred_wait({'reason': 'wait for deferred T-1'}, {'T-1'}))

    def test_control_characters_are_not_exported_to_a_terminal(self):
        self.runner.blocker = 'literal [red]markup[/red] \x1b]52;bad\x07'
        text = blockers_report.build(self.runner)
        self.assertIn('[red]markup[/red]', text)
        self.assertNotIn('\x1b', text)
        self.assertNotIn('\x07', text)


class BlockersPilotTests(unittest.TestCase):
    def test_pinned_textual_report_interactions(self):
        if not shutil.which('uv'):
            self.skipTest('uv is needed for pinned Textual')
        result = subprocess.run(['uv', 'run', '--offline', '--no-project', '--with', 'textual==8.2.8',
                                 'python', str(Path(__file__).with_name('blockers_pilot.py'))],
                                capture_output=True, text=True, timeout=90)
        if result.returncode == 2 and 'offline' in result.stderr.lower() and 'textual' in result.stderr.lower():
            self.skipTest('textual==8.2.8 is not in the offline cache')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
