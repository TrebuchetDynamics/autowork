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
