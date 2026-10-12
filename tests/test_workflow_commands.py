"""Public workflow names preserve skill identity, arguments and gateway routing."""
import unittest
import test_plugin as fixture


class WorkflowCommands(unittest.TestCase):
    setUp = fixture.PluginTests.setUp
    skill = fixture.PluginTests.skill

    def test_new_names_route_to_existing_skills_and_preserve_arguments(self):
        for name in ('repo-interview', 'repo-docs', 'autoresearch'):
            self.skill(name)
        self.plugin.register(self.ctx)
        self.session.update(HERMES_SESSION_PLATFORM='telegram', HERMES_SESSION_CHAT_ID='fixture')
        for command, skill, subcommand in (
                ('plan_with_me', 'repo-interview', None),
                ('docs_sync', 'repo-docs', None),
                ('plan_for_me', 'autoresearch', 'plan')):
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
        self.skill('repo-docs')
        self.existing['docs-sync'] = {'plugin': 'other'}
        self.plugin.register(self.ctx)
        self.assertNotIn('docs-sync', self.ctx.commands)
        self.assertNotIn('docs_sync', self.ctx.commands)
        self.assertIn('repo-docs', self.ctx.commands)

    def test_missing_skills_do_not_advertise_workflows(self):
        self.skill('other')
        self.plugin.register(self.ctx)
        for command in ('docs-sync', 'docs_sync', 'plan-with-me', 'plan-for-me'):
            self.assertNotIn(command, self.ctx.commands)
