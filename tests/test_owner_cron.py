"""Owner schedules must invoke executable recovery, not only inventory blockers."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location('wire_owner_cron', ROOT / 'scripts/wire-owner-cron.py')
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OwnerCronTests(unittest.TestCase):
    def test_autonomous_prompt_has_no_external_owner_or_proposal_gate(self):
        module = load()
        scope = 'Repository: /fixture/repo. Scope: offline collector tests only.'
        updated = module.owner_prompt(scope, enabled=False)
        self.assertIn(scope, updated)
        self.assertIn('No external owner acknowledgement is required', updated)
        self.assertIn('Do not push or deploy', updated)
        self.assertNotIn('process owner inbox/replies', updated)
        self.assertNotIn('supported handoff cycle', updated)
        self.assertNotIn('proposal ledger mode', updated)
        for label in ('Completed:', 'Changed:', 'Checks:', 'Commit:', 'Next:', 'Blocker:'):
            self.assertIn(label, updated)
        self.assertEqual(module.owner_prompt(scope, enabled=True), updated)
        legacy = scope + module.MARKER + 'process owner inbox/replies; proposal ledger mode'
        self.assertNotIn('process owner inbox/replies', module.owner_prompt(legacy, False))

    def test_delivery_batches_and_reports_are_in_generated_cron_prompt(self):
        prompt = load().owner_prompt('Offline removal only; no deployment.', True)
        for rule in ('one coherent delivery batch', 'not one card per file',
                     'approved exact-source checks', 'lead with delivered behavior',
                     'parent task remains open', 'reconcile.py --compact',
                     'two unchanged blocked observations', 'Keep Hermes Agent unchanged'):
            self.assertIn(rule, prompt)
        self.assertIn('Offline removal only; no deployment.', prompt)
        self.assertIn('Do not push or deploy', prompt)

    def test_generated_prompt_defaults_new_workers_to_100_without_reset_or_retry(self):
        module = load()
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                prompt = module.owner_prompt('Offline work only.', enabled)
                for rule in ('100 turns by default', 'omit --goal-max-turns',
                             'explicit --goal-max-turns 50', 'cumulative usage',
                             '--max-retries 1', 'never automatically retry or reset'):
                    self.assertIn(rule, prompt)
                self.assertEqual(module.owner_prompt(prompt, enabled), prompt)

    def test_scheduled_execution_consumes_plans_and_approved_results(self):
        module = load()
        prompt = module.owner_prompt('Offline work authorized. Preserve live-operation exclusions.', True)
        for rule in ('This scheduled invocation is execution, not a planning-only request',
                     'A separate explicit plan request remains planning-only',
                     'Reconcile newly approved exact candidates',
                     'continue eligible implementation in the same occurrence',
                     'Do not ask whether to implement already authorized offline work',
                     'Report reviewed offline slices separately from full TODO acceptance'):
            self.assertIn(rule, prompt)
        self.assertIn('Preserve live-operation exclusions', prompt)
        self.assertIn('Do not push or deploy', prompt)
        self.assertIn('do not trigger recovery', prompt)
        self.assertEqual(module.owner_prompt(prompt, True), prompt)

    def test_scoped_offline_isolation_permission_keeps_main_and_external_limits(self):
        module = load()
        scope = ('User authorizes isolated task branches/worktrees for offline work. '
                 'Keep main protected; no push, deployment or live/RF operations.')
        prompt = module.owner_prompt(scope, True)
        self.assertIn(scope, prompt)
        self.assertEqual(module.owner_prompt(prompt, True), prompt)
        policy = (ROOT / 'skills/autowork/references/scheduled-policy.md').read_text()
        self.assertIn('not the unsupported canonical main-only', policy)
        self.assertIn('it remains unproved rather than being falsely closed', policy)
        self.assertIn('Respect separately recorded pause/resume decisions', policy)

    def test_owner_prompt_routes_to_one_shared_executable_cycle(self):
        module = load()
        prompt = 'Accepted scope: fixture-only. No production writes. No push.'
        updated = module.owner_prompt(prompt, enabled=True)
        self.assertIn(prompt, updated)
        self.assertIn('references/owner-cycle.md', updated)
        self.assertIn('execute', updated)
        self.assertEqual(module.owner_prompt(updated, enabled=True), updated)

    def test_idle_jobs_load_repository_maintenance_without_widening_task_only_scope(self):
        updated = load().owner_prompt('Develop this repository.', enabled=True)
        self.assertIn('references/repository-maintenance.md', updated)
        self.assertIn('documentation, UI/UX, tests, refactoring and reliability', updated)
        self.assertIn('task-only', updated)
        self.assertIn('same occurrence', updated)
        self.assertIn('--scope repository', updated)
        self.assertIn('--scope tasks', updated)
        self.assertEqual(load().owner_prompt(updated, enabled=True), updated)

    def test_paused_prompt_cannot_resume_or_replace_writer(self):
        updated = load().owner_prompt('Main-only; chat-only implementation.', enabled=False)
        self.assertIn('Main-only; chat-only implementation.', updated)
        self.assertIn('resume this job yourself', updated)
        self.assertIn('do not trigger recovery', updated)

    def test_all_profiles_including_missing_jobs_remain_in_coverage(self):
        import tempfile, json
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'config.yaml').write_text('{}')
            for name in ('alpha', 'beta'):
                home = root / 'profiles' / name
                home.mkdir(parents=True)
                (home / 'config.yaml').write_text('{}')
            (root / 'cron').mkdir()
            (root / 'cron/jobs.json').write_text(json.dumps({'jobs': []}))
            rows = load().inventory(root)
            self.assertEqual([row['profile'] for row in rows], ['default', 'alpha', 'beta'])
            self.assertTrue(all(row['jobs'] == [] for row in rows))

    def test_only_development_jobs_are_owner_targets(self):
        module = load()
        self.assertTrue(module.is_owner_job({'name': 'scheduled autogoal', 'skills': []}))
        self.assertTrue(module.is_owner_job({'name': 'progress', 'skills': ['hermes-toolset:autogoal']}))
        self.assertTrue(module.is_owner_job({'name': 'scheduled autowork', 'skills': []}))
        self.assertTrue(module.is_owner_job({'name': 'progress', 'skills': ['hermes-toolset:autowork']}))
        self.assertFalse(module.is_owner_job({'name': 'mail brief', 'skills': []}))

    def test_autowork_is_primary_and_legacy_skill_is_replaced(self):
        module = load()
        self.assertEqual(module.autowork_skills({'skills': ['hermes-toolset:autogoal', 'ponytail:ponytail']}),
                         ['hermes-toolset:autowork', 'ponytail:ponytail'])
        self.assertEqual(module.autowork_skills({'skill': 'autogoal'}), ['hermes-toolset:autowork'])
        ready = {'skills': ['hermes-toolset:autowork', 'hermes-toolset:git-commit-push']}
        self.assertEqual(module.autowork_skills(ready), ready['skills'])

    def test_authorized_maintenance_repairs_shared_source_not_products(self):
        module = load()
        scope = 'Subjects: alpha, beta, gamma, delta. Preserve paused jobs.'
        prompt = module.audit_prompt(scope, repair=True)
        for rule in ('shared-source repair', 'earliest failed transition',
                     'regression RED', 'same read-only consumer',
                     'native admission remains separate', 'Do not reset budgets',
                     'No product writes', 'Preserve paused jobs'):
            self.assertIn(rule, prompt)
        self.assertNotIn(module.AUDIT_MARKER, prompt)
        self.assertEqual(module.audit_prompt(prompt), prompt)
        self.assertIn('Do not push', prompt)

    def test_repair_mode_is_opt_in_and_sticky_in_existing_audit_wiring(self):
        module = load()
        self.assertNotIn('shared-source repair', module.audit_prompt('Audit only.'))
        scope = 'Maintenance scope; no product mutations.'
        prompt = module.audit_prompt(scope, repair=True)
        self.assertTrue(prompt.startswith(scope))
        self.assertEqual(module.audit_prompt(prompt), prompt)
        self.assertIn('other writers', prompt)

    def test_audit_keeps_read_only_role_after_autowork_attachment(self):
        from unittest.mock import patch
        module = load()
        root = Path('/fixture/hermes')
        before = {'id': 'audit', 'name': 'Profile audit and hermes-toolset maintenance',
                  'enabled': True, 'prompt': module.audit_prompt('Audit scope'),
                  'skills': ['hermes-toolset:autowork'], 'skill': 'hermes-toolset:autowork'}
        with patch.object(module, 'inventory', return_value=[{'profile': 'default', 'home': str(root), 'jobs': [before]}]):
            rows = module.wire(root)
        self.assertEqual(rows[0]['state'], 'unchanged')

    def test_apply_binds_edits_to_inventory_root_and_explicit_profile(self):
        import os
        from unittest.mock import patch
        module = load()
        root = Path('/fixture/hermes')
        before = {'id': 'abc', 'name': 'autogoal', 'enabled': False,
                  'prompt': module.owner_prompt('scope', False),
                  'skills': ['hermes-toolset:autogoal', 'ponytail:ponytail'],
                  'skill': 'hermes-toolset:autogoal'}
        after = {**before, 'skills': ['hermes-toolset:autowork', 'ponytail:ponytail'],
                 'skill': 'hermes-toolset:autowork'}
        with patch.object(module, 'inventory', return_value=[{'profile': 'default', 'home': str(root), 'jobs': [before]}]), \
             patch.object(module, 'jobs', side_effect=[[before], [after]]), \
             patch.object(module.subprocess, 'run') as run, \
             patch.dict(os.environ, {'HERMES_HOME': '/wrong', 'HERMES_PROFILE': 'wrong'}):
            module.wire(root, apply=True)
        self.assertEqual(run.call_args.args[0][:3], ['hermes', '-p', 'default'])
        self.assertEqual(run.call_args.kwargs['env']['HERMES_HOME'], str(root))
        self.assertNotIn('HERMES_PROFILE', run.call_args.kwargs['env'])
        self.assertEqual(run.call_args.args[0][-4:],
                         ['--skill', 'hermes-toolset:autowork', '--skill', 'ponytail:ponytail'])

    def test_external_window_does_not_hold_independent_offline_work(self):
        policy = (ROOT / 'skills/autowork/references/owner-cycle.md').read_text()
        self.assertIn('independent implementation or fixture qualification', policy)
        self.assertIn('leave the original live task in Needs decision', policy)
        self.assertIn('record the actual source/test seam inspected', policy)

    def test_completion_counter_can_advance_without_changing_repeat_policy(self):
        module = load()
        before = {'prompt': 'old', 'repeat': {'times': None, 'completed': 64}}
        module.verify_edit(before, {'prompt': 'new', 'repeat': {'times': None, 'completed': 65}}, 'new')
        with self.assertRaises(ValueError):
            module.verify_edit(before, {'prompt': 'new', 'repeat': {'times': 2, 'completed': 65}}, 'new')

    def test_schedule_and_safety_configuration_must_read_back_exactly(self):
        module = load()
        before = {'id': 'abc', 'enabled': False, 'schedule': {'minutes': 15}, 'model': None,
                  'deliver': 'local', 'prompt': 'old', 'workdir': '/repository'}
        after = {**before, 'prompt': 'new'}
        module.verify_edit(before, after, 'new')
        with self.assertRaises(ValueError):
            module.verify_edit(before, {**after, 'enabled': True}, 'new')


if __name__ == '__main__':
    unittest.main()
