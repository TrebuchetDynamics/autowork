"""Render real ledgers without treating documentation examples as write targets."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import goals


class RenderSafetyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        self.todo = self.repo / 'TODO.md'
        self.data = {'version': 1, 'goals': [
            {'id': 'G1', 'title': 'Startup', 'source': 'SPEC.md#slice',
             'status': 'unmet', 'tasks': ['T1']}], 'tasks': [
            {'id': 'T1', 'goal': 'G1', 'title': 'Start', 'status': 'open', 'section': 'Now'}]}
        (self.repo / 'goals.json').write_text(json.dumps(self.data))
        self.live = '\n## Now\n\n- [ ] T1: Start\n  Scope: preserve this body\n'

    def render(self):
        return subprocess.run([sys.executable, str(Path(goals.__file__)), 'render', str(self.repo)],
                              capture_output=True, text=True, timeout=10)

    def test_fenced_markers_are_preserved_and_real_block_is_updated(self):
        example = '```markdown\n' + goals.BEGIN + '\nexample\n' + goals.END + '\n```\n'
        self.todo.write_text(example + '\n## Goal coverage\n' + goals.BEGIN + '\nold\n'
                             + goals.END + self.live)
        result = self.render()
        self.assertEqual(result.returncode, 0, result.stderr)
        text = self.todo.read_text()
        self.assertTrue(text.startswith(example))
        self.assertNotIn('\nold\n', text)
        self.assertTrue(text.endswith(self.live))
        self.assertEqual(self.render().returncode, 0)
        self.assertEqual(self.todo.read_text(), text)

    def test_fenced_coverage_heading_is_not_a_replacement_target(self):
        example = '```markdown\n## Goal coverage\nexample\n```\n'
        self.todo.write_text(example + '\n## Goal coverage\nold\n' + self.live)
        result = self.render()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.todo.read_text().startswith(example))
        self.assertNotIn('\nold\n', self.todo.read_text())
        self.assertTrue(self.todo.read_text().endswith(self.live))

    def test_ambiguous_markers_fail_before_any_write(self):
        for markers in ((goals.END, goals.BEGIN), (goals.BEGIN,), (goals.END,),
                        (goals.BEGIN, goals.END, goals.BEGIN, goals.END)):
            with self.subTest(markers=markers):
                self.todo.write_text('\n'.join(markers) + self.live)
                before = self.todo.read_bytes()
                result = self.render()
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn('coverage markers', result.stderr)
                self.assertEqual(self.todo.read_bytes(), before)

    def test_legacy_section_does_not_consume_next_top_level_section(self):
        following = '\n# Operations\nKeep these instructions.\n' + self.live
        self.todo.write_text('# TODO\n\n## Goal coverage\nold table\n' + following)
        result = self.render()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.todo.read_text().endswith(following))

    def test_ledger_text_cannot_escape_generated_coverage(self):
        self.data['goals'][0]['title'] = 'A | B\n' + goals.END + '\n## Now\n- [ ] FAKE: example'
        self.data['goals'][0]['evidence'] = [
            {'kind': 'inspection', 'ref': '`pipe|check`\n' + goals.BEGIN, 'result': 'pass'}]
        ledger = self.repo / 'goals.json'
        ledger.write_text(json.dumps(self.data))
        before = ledger.read_bytes()
        self.todo.write_text('# TODO\n' + self.live)
        result = self.render()
        self.assertEqual(result.returncode, 0, result.stderr)
        once = self.todo.read_text()
        self.assertEqual(once.count(goals.BEGIN), 1)
        self.assertEqual(once.count(goals.END), 1)
        self.assertEqual(set(goals.task_bodies(once)), {'T1'})
        self.assertEqual(self.render().returncode, 0)
        self.assertEqual(self.todo.read_text(), once)
        self.assertEqual(ledger.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
