"""Offline policy contracts; actual Graphify smoke is separate, not model proof."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GraphifyContractTests(unittest.TestCase):
    def test_graphify_is_targeted_to_relationship_analysis(self):
        core = (ROOT / 'skills/docs-sync/SKILL.md').read_text()
        self.assertIn('## 2a. Targeted relationship analysis', core)
        self.assertIn('Routine link, wording and task-metadata repairs use direct source evidence', core)
        self.assertNotIn('Mandatory Graphify analysis', core)
        self.assertIn('references/graphify-analysis.md', core)
        self.assertIn('Graph evidence:', core)
        self.assertIn('Graphify coverage/limitations', core)

    def test_reference_preserves_authority_and_quality(self):
        text = (ROOT / 'skills/docs-sync/references/graphify-analysis.md').read_text()
        for phrase in ('graphify query', 'graphify path', 'graphify explain',
                       'graphify extract', '--code-only', 'EXTRACTED', 'INFERRED',
                       'AMBIGUOUS', 'source_location', 'dirty/untracked',
                       'Audit creates no graph', 'accepted intent',
                       'Dependencies:', 'Ownership:', 'negative/failure',
                       'graphify_unavailable', 'graphify_partial',
                       'No API key is required', 'byte-identical',
                       'not proof of missing behavior', 'do not invent task IDs'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == '__main__':
    unittest.main()
