"""Generated worker contract coverage; no worker, model or board dispatch."""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('start_goal', Path(__file__).with_name('start_goal.py'))
assert SPEC is not None and SPEC.loader is not None
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class PonytailHandoffTests(unittest.TestCase):
    def test_worker_and_proposal_handoffs_carry_the_simplification_method(self):
        contract = 'Objective: scoped implementation\nAcceptance: retain required checks'
        for options in ({}, {'ledger_mode': 'proposal', 'integration_owner': 'fixture-owner'}):
            with self.subTest(options=options):
                body = m.build_task_body(contract, **options)
                self.assertIn(contract, body)
                self.assertIn('Ponytail application:', body)
                self.assertIn('existing repository code, standard library/platform, installed dependency', body)
                self.assertIn('smallest complete change', body)
                self.assertIn('callers, tests, fixtures and config', body)
                self.assertIn('decision, reused paths, omitted extras and check/result', body)
                self.assertIn('preserve relevant regression coverage', body)
                self.assertIn('never waive safety, acceptance criteria or required checks', body)
                self.assertIn('no push, merge, deploy', body)

    def test_handoff_resolves_real_skills_and_reuses_the_existing_review_lane(self):
        body = m.build_task_body('Objective: scoped implementation')
        self.assertIn('ponytail:ponytail', body)
        self.assertIn('retired compatibility shim', body)
        self.assertIn('ponytail:ponytail-review', body)
        self.assertIn('existing review lane', body)
        self.assertIn('reuse unchanged source-bound decisions', body)
        guide = Path(__file__).parents[1] / 'references/ponytail.md'
        self.assertIn(str(guide.resolve()), body)
        self.assertTrue(guide.is_file(), 'worker must receive an available bundled fallback')


if __name__ == '__main__':
    unittest.main()
