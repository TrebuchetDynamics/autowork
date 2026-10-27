"""Keep owned skill triggers readable in the truncated Hermes index."""
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class SkillDescriptionTests(unittest.TestCase):
    def test_owned_descriptions_fit_index(self):
        skills = sorted((ROOT / 'skills').glob('*/SKILL.md'))
        self.assertTrue(skills)
        for path in skills:
            with self.subTest(skill=path.parent.name):
                text = path.read_text()
                self.assertTrue(text.startswith('---\n'))
                metadata = yaml.safe_load(text.split('---', 2)[1])
                description = metadata['description']
                self.assertIsInstance(description, str)
                self.assertTrue(description.strip())
                self.assertLessEqual(len(description), 60, description)


if __name__ == '__main__':
    unittest.main()
