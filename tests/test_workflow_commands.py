"""Public workflow names preserve skill identity, arguments and gateway routing."""
import unittest
import test_plugin as fixture


class WorkflowCommands(unittest.TestCase):
    setUp = fixture.PluginTests.setUp
    skill = fixture.PluginTests.skill

    def test_new_names_route_to_existing_skills_and_preserve_arguments(self):
        for name in ('plan-with-me', 'docs-sync', 'autoresearch'):
            self.skill(name)
        self.plugin.register(self.ctx)
        self.session.update(HERMES_SESSION_PLATFORM='telegram', HERMES_SESSION_CHAT_ID='fixture')
        for command, skill, subcommand in (
                ('plan_with_me', 'plan-with-me', None),
                ('docs_sync', 'docs-sync', None),
                ('plan_for_me', 'plan-for-me', 'plan')):
            for spelling in (command, command.replace('_', '-')):
                with self.subTest(spelling=spelling):
                    self.assertIn(spelling, self.ctx.commands)
                    raw = 'read-only: compare approaches\n--no-push $(literal)'
                    self.ctx.commands[spelling](raw)
                    prompt, routing = self.ctx.messages[-1]
                    self.assertIn('hermes-toolset:' + skill, prompt)
                    self.assertTrue(prompt.endswith(raw))
                    self.assertEqual(routing['origin']['chat_id'], 'fixture')
                    if subcommand:
                        self.assertIn('Selected subcommand: plan\n', prompt)
        self.assertTrue({'repo-interview', 'repo-docs', 'autoresearch-plan'} <= self.ctx.commands.keys())

    def test_alias_pair_preserves_existing_command_owner(self):
        self.skill('docs-sync')
        self.existing['docs-sync'] = {'plugin': 'other'}
        self.plugin.register(self.ctx)
        self.assertNotIn('docs-sync', self.ctx.commands)
        self.assertNotIn('docs_sync', self.ctx.commands)
        self.assertIn('repo-docs', self.ctx.commands)

    def test_retired_local_snapshots_are_not_discovered_or_installed(self):
        for name in ('repo-docs', 'repo-interview', 'docs-sync', 'plan-with-me'):
            self.skill(name)
        discovered = self.plugin._discover_skills()
        self.assertEqual({name for name, _, _ in discovered}, {'docs-sync', 'plan-with-me'})
        self.plugin.register(self.ctx)
        self.assertEqual(set(self.ctx.skills), {'docs-sync', 'plan-with-me'})
        for old, canonical in [('repo-docs','docs-sync'),('repo-interview','plan-with-me')]:
            self.ctx.commands[old]('resume')
            self.assertIn('hermes-toolset:'+canonical,self.ctx.messages[-1][0])

    def test_legacy_alias_pair_preserves_foreign_owner(self):
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
        for name in ('plan-with-me', 'docs-sync', 'autoresearch', 'grill-me'):
            self.skill(name)
        self.plugin.register(self.ctx)
        self.assertEqual(set(self.ctx.skills), {'plan-with-me', 'docs-sync', 'plan-for-me'})
        self.ctx.commands['grill-me']('challenge my cache plan')
        prompt, _ = self.ctx.messages[-1]
        self.assertIn('skill_view(name="hermes-toolset:plan-with-me")', prompt)
        self.assertIn('../grill-me/SKILL.md', prompt)
        self.assertTrue(prompt.endswith('challenge my cache plan'))

    def test_foreign_namespace_keeps_its_own_skill_identity(self):
        path = self.skill('autoresearch')
        self.plugin._invoke(self.ctx, 'autoresearch', path, 'debug', namespace='other')
        self.assertIn('skill_view(name="other:autoresearch")', self.ctx.messages[-1][0])
        self.assertNotIn('TODO.md is the central work queue', self.ctx.messages[-1][0])
