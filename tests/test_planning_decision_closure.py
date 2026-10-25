"""Focused instruction contracts, not model compliance or reduced-stall evidence."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def section(path, heading):
    text = (ROOT / path).read_text()
    marker = f'## {heading}\n'
    if marker not in text:
        return ''
    return ' '.join(text.split(marker, 1)[1].split('\n## ', 1)[0].split())


class PlanningDecisionClosureTests(unittest.TestCase):
    def test_every_material_finding_gets_an_actionable_disposition(self):
        # Losing the planner-resolvable branch sends technical choices back to owners.
        closure = section('skills/shared/PLANNING-CRAFT.md', 'Decision closure')
        for disposition, action in (
                ('Already answered', 'copy the answer and source into the affected task'),
                ('Planner-resolvable', 'resolve consequential engineering choices within delegated scope'),
                ('Worker-reversible', 'leave reversible coding details to the worker'),
                ('Owner/external-blocked', 'exact missing intent, authority or input and resume condition')):
            with self.subTest(disposition=disposition):
                self.assertIn(disposition, closure)
                self.assertIn(action, closure)
        self.assertIn('No material finding remains unclassified in a ready task', closure)
        self.assertIn('Recheck changed findings, not the whole unchanged planning pass', closure)

    def test_closure_walks_inputs_to_checks_without_inventing_external_blockers(self):
        closure = section('skills/shared/PLANNING-CRAFT.md', 'Decision closure')
        for rule in ('starting inputs through implementation and verification to handoff',
                     'interfaces, data, error, compatibility and migration behavior',
                     'reachable inputs and setup', 'bounded prerequisite repairs',
                     'exact checks and success evidence',
                     'New tests and fixtures the task can create are deliverables, not external blockers',
                     'Keep real live qualification separate and unmet',
                     'no offline substitute or waiver'):
            with self.subTest(rule=rule):
                self.assertIn(rule, closure)

    def test_decision_map_is_prose_not_a_new_schema_or_clear_task_ceremony(self):
        closure = section('skills/shared/PLANNING-CRAFT.md', 'Decision closure')
        for rule in ('selected approach and evidence/reason', 'rejected alternative when meaningful',
                     'affected task IDs and acceptance/check', 'not a new required field',
                     'For a clear task, fill only actual gaps'):
            self.assertIn(rule, closure)
        builder = section('skills/shared/PLANNING-CRAFT.md', 'Builder check before handoff')
        self.assertIn('#decision-closure', builder)
        self.assertNotIn('**Minor**', builder)
        self.assertNotIn('**Theirs**', builder)

    def test_mode_specific_decisions_preserve_interview_and_authority(self):
        craft = section('skills/shared/PLANNING-CRAFT.md', 'Facts and decision authority')
        self.assertIn('Plan For Me resolves evidence-supported engineering trade-offs', craft)
        self.assertIn('Plan With Me retains consequential intent interviews', craft)
        self.assertIn('Never infer authorization from an engineering preference, silence or an Accepted heading', craft)
        interactive = section('skills/shared/RESEARCH-PLAN.md', 'Interactive planning: Plan With Me')
        for rule in ('user participating in consequential decisions', 'Ask the highest-impact ready question',
                     'A skipped choice stays open', 'no fixed question count'):
            self.assertIn(rule, interactive)

    def test_handoff_requires_reachable_contract_not_just_valid_metadata(self):
        handoff = section('skills/shared/PLAN-HANDOFF.md', 'One planning pass, one handoff')
        self.assertIn('PLANNING-CRAFT.md#decision-closure', handoff)
        self.assertIn('Metadata validity and selection eligibility do not prove reachable inputs or checks', handoff)
        self.assertIn('persist a resolution or keep only the affected task pending', handoff)
        research = section('skills/shared/RESEARCH-PLAN.md', 'Research and persistence method')
        self.assertIn('PLANNING-CRAFT.md#decision-closure', research)

    def test_closure_does_not_widen_planning_writes_or_execution_authority(self):
        contract = section('skills/shared/RESEARCH-PLAN.md', 'Planning artifact and authority contract')
        for rule in ('Save the requested plan/batch, then stop', 'same coordinator',
                     'save nothing, including queue metadata or research scratch',
                     'do not write them during planning',
                     'Acceptance of a plan is not execution authority'):
            self.assertIn(rule, contract)


if __name__ == '__main__':
    unittest.main()
