"""`/autowork blockers` contract: the owner answers, runners stay untouched.

Instruction contracts only; they do not prove a model follows them.
"""
from pathlib import Path
import re
import unittest

SKILL = Path(__file__).resolve().parents[1]
ROOT = SKILL.parents[1]


def text(path):
    return re.sub(r'\s+', ' ', path.read_text())


class OwnerBlockersContract(unittest.TestCase):
    def setUp(self):
        self.ref = text(SKILL / 'references/owner-blockers.md')

    def test_every_entry_point_offers_the_mode(self):
        for path in (SKILL / 'SKILL.md', ROOT / 'adapters/skills/autowork/SKILL.md'):
            with self.subTest(path=path.name):
                body = text(path)
                self.assertIn('/autowork blockers [repo|name]', body)
                self.assertIn('owner-blockers.md', body)
                self.assertRegex(body, r'never starts?, stops?')

    def test_plan_with_me_offers_the_same_list_with_replanning(self):
        for path in (ROOT / 'skills/plan-with-me/SKILL.md', ROOT / 'adapters/skills/plan-with-me/SKILL.md',
                     ROOT / 'skills/plan-with-me/references/special-cases.md'):
            with self.subTest(path=str(path.relative_to(ROOT))):
                body = text(path)
                self.assertIn('/plan_with_me blockers [repo|', body)
                self.assertIn('easiest first', body)
        for phrase in ('`/plan_with_me blockers [repo|runner name]` uses the same list and order',
                       "it plans that one question with Plan With Me's planning craft",
                       '`/autowork blockers [repo|runner name]` stays quick'):
            self.assertIn(phrase, self.ref)

    def test_easiest_first_from_deterministic_effort(self):
        for phrase in ('one question at a time', 'easiest first', 'Effort is deterministic from the kind, never guessed',
                       '| quick |', '| decision |', '| input |', '| investigate |',
                       'a larger `unblocks` count comes first, then the oldest'):
            self.assertIn(phrase, self.ref)

    def test_reads_the_runner_block_or_the_engine_without_a_model(self):
        for phrase in ('<!-- pi-autowork:questions:start -->', '<!-- pi-autowork:questions:end -->',
                       '--parallel-status --json', 'without a model call',
                       'no runner or schedule invokes them, so an idle queue still costs no tokens'):
            self.assertIn(phrase, self.ref)

    def test_answers_are_planning_not_runner_management(self):
        for phrase in ('never starts, stops, restarts or reconfigures a runner', 'never kills a session',
                       'never pushes', 'Edit that task\'s TODO.md entry', 'never edit inside the runner\'s marked block',
                       'Commit only the planning files', 'do not push unless the owner asks',
                       '--set-aside TASK'):
            self.assertIn(phrase, self.ref)


if __name__ == '__main__':
    unittest.main()
