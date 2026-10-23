"""Offline contracts for bare Plan For Me autonomous project discovery.

These read the real skill, shared contract, adapters and disposable fixtures. They
do not run a model; host/model behavior is evaluated with the planning specimens.
"""
import runpy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/plan-for-me/SKILL.md'
DISCOVERY = ROOT / 'skills/plan-for-me/references/discovery.md'
RESEARCH_PLAN = ROOT / 'skills/shared/RESEARCH-PLAN.md'
PLANNING_CRAFT = ROOT / 'skills/shared/PLANNING-CRAFT.md'
ADAPTER = ROOT / 'adapters/skills/plan-for-me/SKILL.md'
SCENARIOS = ROOT / 'tests/fixtures/planning/scenarios.py'


def words(path):
    return ' '.join(path.read_text().split())


class PlanForMeDiscoveryContractTests(unittest.TestCase):
    def test_bare_and_vague_requests_start_discovery_without_a_goal_interview(self):
        text = words(SKILL)
        for requirement in (
                '## Route the request',
                'references/discovery.md',
                'Do not ask for a goal before investigating',
                'A bare `/plan_for_me` is a discovery request, not an interview',
                'Focused planning for that outcome and its authorized prerequisites',
                'Read-only, chat-only, no-write or dry-run',
                'An Autowork-owned planning substep',
                'If the repository has no accepted objective or meaningful source',
                'New product directions stay proposals'):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, text)

    def test_shared_contract_distinguishes_discovery_from_missing_interactive_intent(self):
        contract = words(RESEARCH_PLAN)
        self.assertIn('project-discovery protocol', contract)
        self.assertIn('Do not ask for a goal before that investigation', contract)
        self.assertIn('Plan With Me asks for the missing goal', contract)
        self.assertIn('Autowork-owned substep stays inside its named task', contract)
        self.assertNotIn('otherwise ask for the missing goal', contract)
        craft = words(PLANNING_CRAFT)
        self.assertIn('Project discovery', craft)
        self.assertIn('never an interview for a goal or invented product scope', craft)

    def test_discovery_reference_defines_goal_authority_evidence_and_batches(self):
        text = words(DISCOVERY)
        for requirement in (
                '## Goal classes',
                'Accepted',
                'Derived engineering',
                'Proposed strategic',
                '## Investigate progressively',
                '`OBSERVED`',
                '`DOCUMENTED`',
                '`INFERRED`',
                '`UNKNOWN`',
                'Goal -> Specification -> Implementation -> Verification -> Task',
                'implemented but unverified',
                'partially implemented',
                '## Prioritize the real frontier',
                'do not fabricate ROI percentages',
                '## Bound the batch',
                'at most eight new tasks',
                '## Reconcile repeated invocations',
                '## Respect authority and persistence',
                'Do not edit legacy TODO.md/goals.json',
                '## Report',
                'Next executable task'):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, text)

    def test_read_only_and_coordinator_boundaries_survive_the_default_discovery_route(self):
        text = words(SKILL) + ' ' + words(DISCOVERY)
        for requirement in (
                'save nothing, including queue metadata',
                'same coordinator',
                'authorized prerequisites',
                'Preserve read-only modes, live leases and active workers',
                'preserve the blocker'):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, text)

    def test_portable_adapter_exposes_the_same_discovery_default(self):
        text = words(ADAPTER)
        for requirement in (
                '../../../skills/plan-for-me/references/discovery.md',
                'No concrete objective',
                'Do not ask for a goal first',
                'Focused planning',
                'Read-only',
                'An Autowork-owned substep'):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, text)

    def test_discovery_fixture_matrix_covers_required_situations_and_prepares(self):
        cases = runpy.run_path(str(SCENARIOS))['CASES']
        required = {'bare-established', 'bare-sparse', 'bare-undefined', 'mature-backlog',
                    'vague-goal', 'verification-gap', 'spec-conflict', 'proposal',
                    'read-only', 'active-dirty', 'repeat', 'large', 'coordinator'}
        self.assertLessEqual(required, set(cases))
        self.assertEqual(cases['bare-established'][1], '')
        self.assertEqual(cases['vague-goal'][1], 'make this better')
        with tempfile.TemporaryDirectory(prefix='planning-fixture-') as temporary:
            destination = Path(temporary) / 'eval'
            subprocess.run(
                [sys.executable, str(SCENARIOS), 'prepare', str(destination),
                 '--cases', 'bare-established,bare-sparse,bare-undefined,active-dirty'],
                check=True, capture_output=True, text=True)
            self.assertTrue((destination / 'bare-established/docs/prd.md').is_file())
            self.assertIn('FMT-02', (destination / 'bare-established/docs/prd.md').read_text())
            self.assertFalse((destination / 'bare-sparse/docs/plan.md').exists())
            self.assertIn('test_trim', (destination / 'bare-sparse/tests/test_formatting.py').read_text())
            self.assertIn('no product direction',
                          (destination / 'bare-undefined/README.md').read_text())
            self.assertIn('- Held by: owner',
                          (destination / 'active-dirty/tasks/items/FMT-900-ab.md').read_text())
            self.assertTrue((destination / 'active-dirty/notes/owner-edit.txt').is_file())
            self.assertEqual((destination / 'bare-established.request.txt').read_text().count(
                'No one can reply'), 1)


if __name__ == '__main__':
    unittest.main()
