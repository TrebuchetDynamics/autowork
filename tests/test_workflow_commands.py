"""Public workflow names preserve skill identity, arguments and gateway routing."""
import unittest
import test_plugin as fixture


class WorkflowCommands(unittest.TestCase):
    setUp = fixture.PluginTests.setUp
    skill = fixture.PluginTests.skill

    def test_new_names_route_to_existing_skills_and_preserve_arguments(self):
        for name in ('plan-with-me', 'plan-for-me', 'docs-sync', 'autoresearch'):
            self.skill(name)
        self.plugin.register(self.ctx)
        self.session.update(HERMES_SESSION_PLATFORM='telegram', HERMES_SESSION_CHAT_ID='fixture')
        for command, skill in (
                ('plan_with_me', 'plan-with-me'),
                ('docs_sync', 'docs-sync'),
                ('plan_for_me', 'plan-for-me')):
            for spelling in (command, command.replace('_', '-')):
                with self.subTest(spelling=spelling):
                    self.assertIn(spelling, self.ctx.commands)
                    raw = 'read-only: compare approaches\n--no-push $(literal)'
                    self.ctx.commands[spelling](raw)
                    prompt, routing = self.ctx.messages[-1]
                    self.assertIn('autowork:' + skill, prompt)
                    self.assertTrue(prompt.endswith(raw))
                    self.assertEqual(routing['origin']['chat_id'], 'fixture')
                    if command == 'plan_for_me':
                        self.assertIn('TODO.md is the central work queue', prompt)
        self.assertIn('autoresearch-plan', self.ctx.commands)
        for retired in ('repo-docs', 'repo_docs', 'repo-interview', 'repo_interview'):
            self.assertNotIn(retired, self.ctx.commands)

    def test_cron_autowork_command_routes_without_creating_a_schedule(self):
        self.skill('cron-autowork')
        self.plugin.register(self.ctx)
        self.session.update(HERMES_SESSION_PLATFORM='telegram', HERMES_SESSION_CHAT_ID='fixture')
        # Telegram normalizes /cron_autowork to the registered hyphen spelling.
        raw = 'every 30m; repository scope; no push'
        self.ctx.commands['cron-autowork'](raw)
        prompt, routing = self.ctx.messages[-1]
        self.assertIn('autowork:cron-autowork', prompt)
        self.assertTrue(prompt.endswith(raw))
        self.assertEqual(routing['origin']['chat_id'], 'fixture')

    def test_plan_for_me_is_registered_and_installed_from_its_own_source(self):
        source = fixture.ROOT / 'skills/plan-for-me/SKILL.md'
        self.assertTrue(source.is_file())
        self.plugin.SKILLS_DIR = fixture.ROOT / 'skills'
        self.plugin.register(self.ctx)
        self.assertEqual(self.ctx.skills['plan-for-me'], source)
        self.assertEqual(self.ctx.skills['autoresearch'], fixture.ROOT / 'skills/autoresearch/SKILL.md')
        installed = self.root.parent / 'home/skills/plan-for-me/SKILL.md'
        self.assertEqual(installed.read_bytes(), source.read_bytes())

    def test_plan_for_me_reserves_both_spellings_for_existing_owners(self):
        self.skill('plan-for-me')
        self.existing['plan_for_me'] = {'plugin': 'other'}
        self.plugin.register(self.ctx)
        self.assertNotIn('plan-for-me', self.ctx.commands)
        self.assertNotIn('plan_for_me', self.ctx.commands)

    def test_alias_pair_preserves_existing_command_owner(self):
        self.skill('docs-sync')
        self.existing['docs-sync'] = {'plugin': 'other'}
        self.plugin.register(self.ctx)
        self.assertNotIn('docs-sync', self.ctx.commands)
        self.assertNotIn('docs_sync', self.ctx.commands)
        self.assertNotIn('repo-docs', self.ctx.commands)
        self.assertNotIn('repo_docs', self.ctx.commands)

    def test_retired_local_snapshots_are_not_discovered_or_installed(self):
        for name in ('repo-docs', 'repo-interview', 'docs-sync', 'plan-with-me'):
            self.skill(name)
        discovered = self.plugin._discover_skills()
        self.assertEqual({name for name, _, _ in discovered}, {'docs-sync', 'plan-with-me'})
        self.plugin.register(self.ctx)
        self.assertEqual(set(self.ctx.skills), {'docs-sync', 'plan-with-me'})
        for retired in ('repo-docs', 'repo_docs', 'repo-interview', 'repo_interview'):
            self.assertNotIn(retired, self.ctx.commands)
        self.ctx.commands['docs_sync']('resume')
        self.assertIn('autowork:docs-sync', self.ctx.messages[-1][0])

    def test_foreign_retired_command_does_not_block_docs_sync(self):
        self.skill('docs-sync')
        self.existing['repo-docs'] = {'plugin':'other'}
        self.plugin.register(self.ctx)
        self.assertNotIn('repo-docs',self.ctx.commands)
        self.assertNotIn('repo_docs',self.ctx.commands)
        self.assertIn('docs_sync',self.ctx.commands)

    def test_missing_skills_do_not_advertise_workflows(self):
        self.skill('other')
        self.plugin.register(self.ctx)
        for command in ('docs-sync', 'docs_sync', 'plan-with-me', 'plan-for-me'):
            self.assertNotIn(command, self.ctx.commands)

    def test_catalog_uses_current_names_and_grilling_is_a_mode(self):
        for name in ('plan-with-me', 'plan-for-me', 'docs-sync', 'autoresearch', 'grill-me'):
            self.skill(name)
        self.plugin.register(self.ctx)
        self.assertEqual(set(self.ctx.skills), {'plan-with-me', 'docs-sync', 'plan-for-me', 'autoresearch'})
        self.ctx.commands['grill-me']('challenge my cache plan')
        prompt, _ = self.ctx.messages[-1]
        self.assertIn('skill_view(name="autowork:plan-with-me")', prompt)
        self.assertIn('../grill-me/SKILL.md', prompt)
        self.assertTrue(prompt.endswith('challenge my cache plan'))

    def test_foreign_namespace_keeps_its_own_skill_identity(self):
        path = self.skill('autoresearch')
        self.plugin._invoke(self.ctx, 'autoresearch', path, 'debug', namespace='other')
        self.assertIn('skill_view(name="other:autoresearch")', self.ctx.messages[-1][0])
        self.assertNotIn('TODO.md is the central work queue', self.ctx.messages[-1][0])
