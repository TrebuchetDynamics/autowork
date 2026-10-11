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
    def test_owner_prompt_routes_to_one_shared_executable_cycle(self):
        module = load()
        prompt = 'Accepted scope: fixture-only. No production writes. No push.'
        updated = module.owner_prompt(prompt, enabled=True)
        self.assertIn(prompt, updated)
        self.assertIn('references/owner-cycle.md', updated)
        self.assertIn('execute', updated)
        self.assertEqual(module.owner_prompt(updated, enabled=True), updated)

    def test_paused_prompt_cannot_resume_or_replace_writer(self):
        updated = load().owner_prompt('Main-only; chat-only implementation.', enabled=False)
        self.assertIn('Main-only; chat-only implementation.', updated)
        self.assertIn('Do not resume', updated)
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

    def test_apply_binds_edits_to_inventory_root_and_explicit_profile(self):
        import os
        from unittest.mock import patch
        module = load()
        root = Path('/fixture/hermes')
        before = {'id': 'abc', 'name': 'autogoal', 'enabled': False, 'prompt': 'scope'}
        after = {**before, 'prompt': module.owner_prompt('scope', False)}
        with patch.object(module, 'inventory', return_value=[{'profile': 'default', 'home': str(root), 'jobs': [before]}]), \
             patch.object(module, 'jobs', side_effect=[[before], [after]]), \
             patch.object(module.subprocess, 'run') as run, \
             patch.dict(os.environ, {'HERMES_HOME': '/wrong', 'HERMES_PROFILE': 'wrong'}):
            module.wire(root, apply=True)
        self.assertEqual(run.call_args.args[0][:3], ['hermes', '-p', 'default'])
        self.assertEqual(run.call_args.kwargs['env']['HERMES_HOME'], str(root))
        self.assertNotIn('HERMES_PROFILE', run.call_args.kwargs['env'])

    def test_external_window_does_not_hold_independent_offline_work(self):
        policy = (ROOT / 'skills/autogoal/references/owner-cycle.md').read_text()
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
