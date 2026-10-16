"""Instruction contract: task-writing skills require Touches:, not model or cron behavior."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRITERS = ('skills/autowork/SKILL.md', 'adapters/skills/autowork/SKILL.md',
           'skills/docs-sync/SKILL.md', 'adapters/skills/docs-sync/SKILL.md',
           'skills/plan-for-me/SKILL.md', 'adapters/skills/plan-for-me/SKILL.md',
           'skills/plan-with-me/SKILL.md', 'adapters/skills/plan-with-me/SKILL.md',
           'skills/autoresearch/SKILL.md', 'skills/shared/PLANNING-CRAFT.md',
           'skills/docs-sync/references/document-scaffold.md')


class TaskTouchesContractTests(unittest.TestCase):
    def test_every_task_writer_asks_for_touches(self):
        for path in WRITERS:
            with self.subTest(path=path):
                self.assertIn('Touches:', (ROOT / path).read_text())

    def test_shared_rule_requires_touches_or_an_explicit_exclusive(self):
        text = (ROOT / 'skills/shared/TODO-WORKCENTER.md').read_text()
        for requirement in ('Every executable task you create or rewrite gets `Touches:`',
                            'widen to the owning directories rather than omit',
                            '`Resources: exclusive` with the reason',
                            'the coordinator owns them'):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, ' '.join(text.split()))
        self.assertNotIn('When the paths are known', text)


if __name__ == '__main__':
    unittest.main()
