"""The skill standard: description shape, boundaries and a checkable done line.

See docs/skill-standard.md. These are the mechanical rules; judgement rules (one
home, disclosure, positive wording) stay with review.
"""
import re
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
BANNED_OPENERS = ('use when', 'use to', 'use for', 'use if', 'use after', 'use before')
# Hermes installs Graphify's own skill into profiles, so Autowork ships the adapter only.
ADAPTER_ONLY = {'graphify'}


class SkillStandardTests(unittest.TestCase):
    def skills(self, folder):
        return sorted((ROOT / folder).glob('*/SKILL.md'))

    def test_descriptions_are_summaries_within_the_index(self):
        for path in self.skills('skills') + self.skills('adapters/skills'):
            with self.subTest(skill=path.relative_to(ROOT)):
                text = path.read_text()
                self.assertTrue(text.startswith('---\n'))
                description = yaml.safe_load(text.split('---', 2)[1])['description']
                self.assertIsInstance(description, str)
                self.assertLessEqual(len(description), 60, description)
                self.assertFalse(description.lower().startswith(BANNED_OPENERS), description)
                self.assertRegex(description, r'\.$')
                self.assertEqual(description.count('.'), 1, description)

    def test_every_native_skill_states_boundaries_and_a_done_line(self):
        for path in self.skills('skills'):
            if path.parent.name == 'shared':
                continue
            with self.subTest(skill=path.parent.name):
                text = path.read_text()
                self.assertIn('## Boundaries', text)
                boundaries = text.split('## Boundaries', 1)[1]
                self.assertRegex(boundaries, r'(?m)^- \S', 'a boundary with no cut')
                self.assertIn('**Done when:**', text)
                self.assertEqual(text.count('**Done when:**'), 1, 'one completion line')

    def test_sibling_pairs_name_each_other(self):
        # The pairs from docs/skill-standard.md, in both directions.
        pairs = [('plan-with-me', 'plan-for-me'), ('grilling', 'grill-me'),
                 ('grilling', 'grill-with-docs'), ('grill-me', 'grill-with-docs'),
                 ('autowork', 'autonomous-codebase-improver'),
                 ('autowork', 'improve-codebase-architecture'),
                 ('bug-harvest', 'unused-code'), ('bug-harvest', 'test-optimizer'),
                 ('unused-code', 'skill-folder-refactor'),
                 ('git-commit-push', 'ponytail-review'),
                 ('ponytail-review', 'ponytail-audit')]
        for a, b in pairs:
            with self.subTest(pair=f'{a} -> {b}'):
                text = (ROOT / 'skills' / a / 'SKILL.md').read_text()
                self.assertIn(f'`/{b}`', text.split('## Boundaries', 1)[1])

    def test_the_router_names_every_skill(self):
        # Upstream's rule: a router that never mentions a skill, or still names a
        # removed one, is a router that lies.
        router = (ROOT / 'skills/ask-autowork/SKILL.md').read_text()
        for path in self.skills('skills'):
            name = path.parent.name
            if name in ('shared', 'ask-autowork'):
                continue
            with self.subTest(skill=name):
                self.assertIn(f'`/{name}`', router)
        listed = set(re.findall(r'`/([a-z0-9-]+)`', router))
        known = {p.parent.name for p in self.skills('skills')} | {'graphify'}
        self.assertEqual(sorted(listed - known), [], 'router names a missing skill')

    def test_portable_adapters_point_at_the_native_skill(self):
        for path in self.skills('adapters/skills'):
            name = path.parent.name
            with self.subTest(adapter=name):
                text = path.read_text()
                if name in ADAPTER_ONLY:
                    self.assertNotIn(f'../../../skills/{name}/', text)
                else:
                    native = ROOT / 'skills' / name / 'SKILL.md'
                    self.assertTrue(native.is_file(), f'{name} has no native skill')
                    self.assertIn(f'../../../skills/{name}/SKILL.md', text)
                self.assertTrue((path.parent / 'agents/openai.yaml').is_file())


if __name__ == '__main__':
    unittest.main()
