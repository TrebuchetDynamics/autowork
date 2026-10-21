"""Offline real-ledger lifecycle; review receipts are simulated, no model/native runs."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CycleGuidanceTests(unittest.TestCase):
    def test_caller_controlled_continuation_matrix_across_hosts(self):
        # Instruction contracts only: these fixtures do not execute a model or cron.
        paths = ('skills/shared/ENGINEERING-CYCLE.md', 'skills/autowork/SKILL.md',
                 'adapters/skills/autowork/SKILL.md')
        cases = {
            'default interactive': 'Default interactive execution',
            'explicit one-task': 'An explicit one-task limit stops new selection',
            'explicit continuation': 'Explicit continuation or whole-spec scope',
            'recurring occurrence': 'Recurrence authorizes the saved occurrence',
            'saved batch limit': 'saved stop/batch limits',
            'exhausted allocation': 'exhaustion requires explicit additional allocation',
        }
        for path in paths:
            text = (ROOT / path).read_text()
            if path == 'skills/autowork/SKILL.md':
                self.assertIn('references/iteration-and-decisions.md#mode-precedence', text)
                text += (ROOT / 'skills/autowork/references/iteration-and-decisions.md').read_text()
            for case, requirement in cases.items():
                with self.subTest(path=path, case=case):
                    self.assertIn(requirement, text)
            self.assertNotIn('Only an explicit whole-spec implementation request authorizes', text)

    def test_same_task_recovery_and_independent_fallback_keep_real_holds(self):
        iteration = (ROOT / 'skills/autowork/references/iteration-and-decisions.md').read_text()
        for requirement in ('Never block\n   on a first failure', 'non-privileged tooling',
                            'same task', 'consequential choices', 'no automatic failure retry',
                            'never reset an exhausted allocation'):
            self.assertIn(requirement, iteration)
        recovery = (ROOT / 'skills/autowork/references/blocker-recovery.md').read_text()
        for requirement in ('original pin', 'consumed budget', 'pending_approval',
                            'resume step', 'another channel', 'live resource ownership',
                            'inside its contract'):
            self.assertIn(requirement, recovery)
        scheduled = (ROOT / 'skills/autowork/references/scheduled-policy.md').read_text()
        for requirement in ('saved stop/batch limits', 'at-most-one-new-batch',
                            'provenance', 'current ownership', 'checks and required review',
                            'non-overlapping', 'unknown usage is not zero'):
            self.assertIn(requirement, scheduled)

    def test_ready_native_and_portable_guidance_use_composition_not_duplicate_validation(self):
        native = (ROOT / 'skills/autowork/SKILL.md').read_text()
        portable = (ROOT / 'adapters/skills/autowork/SKILL.md').read_text()
        self.assertIn('default is one composed command', native)
        self.assertIn('--owner-pid', native)
        self.assertNotIn('run `scripts/start_goal.py … --validate-only`', native)
        self.assertIn('one host-native', portable)
        self.assertIn('No Kanban lookup', portable)
        self.assertIn('consumed budget', native)
        self.assertIn('consumed budget', portable)

    def test_autowork_starts_the_runner_service_and_works_by_hand_only_when_it_cannot(self):
        """`/autowork start` did the work in the session while the repository's runner sat unused."""
        portable = (ROOT / 'adapters/skills/autowork/SKILL.md').read_text()
        start, by_hand = portable.index('Run `autowork start .`'), portable.index('Do the work by hand in this session')
        self.assertLess(start, by_hand)
        for phrase in ('If `AUTOWORK_SLOT` is set', 'only when the service\n   can\'t run', 'the runner owns them'):
            self.assertIn(phrase, portable)

    def test_default_guidance_does_not_route_through_native_card_tools(self):
        paths = ('skills/autowork/SKILL.md',
                 'skills/autowork/references/scheduled-policy.md',
                 'skills/autowork/references/iteration-and-decisions.md',
                 'skills/autowork/references/delivery-batches.md',
                 'skills/shared/ENGINEERING-CYCLE.md')
        for path in paths:
            with self.subTest(path=path):
                text = (ROOT / path).read_text()
                for obsolete in ('hermes kanban', 'start_goal.py', 'reconcile.py',
                                 '--goal-max-turns', '--max-retries', '100-turn default'):
                    self.assertNotIn(obsolete, text)
        direct = (ROOT / 'skills/autowork/references/owner-cycle.md').read_text()
        for requirement in ('`tasks/` owns product requirements', 'Selection reads `tasks/` at the base commit',
                            'actual process plus workspace/Git', 'explicit finite timeout',
                            'not provider spend, tokens', 'it never closes the task'):
            self.assertIn(requirement, direct)

    def test_cross_profile_audit_verifies_publication_without_takeover(self):
        text = (ROOT / 'skills/autowork/references/state-and-recovery.md').read_text()
        self.assertIn('## Cross-profile audit and publication evidence', text)
        for requirement in ('git status --porcelain=v1 -z', 'git worktree list --porcelain',
                            'git ls-remote --heads', 'audit_unverified',
                            'last_run_commit', 'published_branch', 'integrated_main',
                            'read-only', 'No automatic commit', 'nonempty',
                            'bounded backlog', 'UTC', 'mode=ro'):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, text)

    def test_shared_scheduled_policy_owns_fallback_and_authorized_delivery(self):
        core = (ROOT / 'skills/autowork/SKILL.md').read_text()
        self.assertIn('references/scheduled-policy.md', core)
        text = (ROOT / 'skills/autowork/references/scheduled-policy.md').read_text()
        self.assertIn('# Scheduled policy and profile exceptions', text)
        self.assertIn('load `autowork:docs-sync`', text)
        self.assertIn('rerun selection in the same occurrence', text)
        self.assertIn('load `autowork:git-commit-push`', text)
        self.assertIn('exact remote ref and SHA', text)
        self.assertIn('publication authority', text)
        self.assertIn('source before changing profile prompts', text)
        self.assertIn('never implies push permission', text)
        self.assertNotIn('at most once per day', text)
        self.assertNotIn('Repo-docs runs separately;', text)

    def test_cycle_routes_available_skills_and_preserves_authority(self):
        policy = ROOT / 'skills/shared/ENGINEERING-CYCLE.md'
        self.assertTrue(policy.is_file(), 'missing shared engineering cycle')
        text = policy.read_text()
        for requirement in ('interview-me', 'spec-driven-development', 'documentation-and-adrs',
                            'planning-and-task-breakdown', 'incremental-implementation',
                            'test-driven-development', 'code-review-and-quality',
                            'skills/.hub/lock.json', 'systematic-debugging',
                            'No native card admission',
                            'tasks/todo.md', 'review acceptance', 'NOT_CHECKED'):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, text)
        for path in ('docs-sync/SKILL.md', 'autowork/SKILL.md',
                     'autowork/references/whole-spec-execution.md'):
            self.assertIn('ENGINEERING-CYCLE.md', (ROOT / 'skills' / path).read_text())

    def test_supporting_guidance_does_not_reintroduce_phase_checklists(self):
        forbidden = {
            'shared/ENGINEERING-CYCLE.md': ['At intake and whenever the work changes phase',
                                           'For each relevant skill, read'],
            'autoresearch/SKILL.md': ['Use verified Addy skills through the engineering-cycle matrix:'],
            'autowork/references/discovery.md': ["skill and its STE-inspired reference with"],
            'autowork/references/handoff.md': ['Before solution design or implementation, load `ponytail`'],
            'autowork/references/backlog-planning.md': ['or immediately\nwhen the observed queue'],
        }
        for path, phrases in forbidden.items():
            text = (ROOT / 'skills' / path).read_text()
            for phrase in phrases:
                with self.subTest(path=path, phrase=phrase):
                    self.assertNotIn(phrase, text)

    def test_autonomy_does_not_turn_missing_intent_into_approval(self):
        core = (ROOT / 'skills/autowork/SKILL.md').read_text() + (ROOT / 'skills/autowork/references/iteration-and-decisions.md').read_text()
        self.assertNotIn('proceed on the recommended reading', core)
        self.assertIn('continue only independent authorized work', core)
        self.assertIn('Silence never grants', core)
        cycle = (ROOT / 'skills/shared/ENGINEERING-CYCLE.md').read_text()
        for skill in ('api-and-interface-design', 'deprecation-and-migration',
                      'ci-cd-and-automation', 'observability-and-instrumentation',
                      'frontend-ui-engineering', 'context-engineering', 'code-simplification'):
            self.assertIn(skill, cycle)


if __name__ == '__main__':
    unittest.main()
