"""Autoresearch command dispatch and pinned distribution contracts."""
import hashlib
import json
from pathlib import Path
import subprocess
import unittest

import test_plugin as fixture

ROOT = fixture.ROOT

COMMANDS = ('plan', 'debug', 'fix', 'security', 'ship', 'probe', 'scenario',
            'predict', 'reason', 'learn', 'improve', 'evals', 'regression')


class AutoresearchCommands(unittest.TestCase):
    setUp = fixture.PluginTests.setUp
    skill = fixture.PluginTests.skill

    def test_all_upstream_commands_route_to_one_skill_preserving_arguments(self):
        self.skill('autoresearch')
        self.plugin.register(self.ctx)
        raw = 'Goal: cache latency\n--chain evals $(do-not-execute)'
        for command in COMMANDS:
            for alias in (f'autoresearch:{command}', f'autoresearch-{command}'):
                self.assertIn(alias, self.ctx.commands)
                self.ctx.commands[alias](raw)
                prompt, _ = self.ctx.messages[-1]
                self.assertIn('hermes-toolset:autoresearch', prompt)
                self.assertIn(f'Selected subcommand: {command}\n', prompt)
                self.assertTrue(prompt.endswith(raw))

    def test_todo_default_reaches_router_and_aliases_without_losing_restrictions(self):
        self.skill('autoresearch')
        self.plugin.register(self.ctx)
        for alias in ('autoresearch', 'autoresearch:plan', 'autoresearch-plan'):
            for raw in ('Improve onboarding', 'read-only: inspect onboarding', '--dry-run plan onboarding'):
                self.ctx.commands[alias](raw)
                prompt, _ = self.ctx.messages[-1]
                self.assertIn('TODO.md is the central work queue', prompt)
                self.assertIn('read-only', prompt)
                self.assertIn('--dry-run', prompt)
                self.assertTrue(prompt.endswith(raw))

    def test_alias_collision_preserves_existing_owner(self):
        self.skill('autoresearch')
        self.existing['autoresearch:plan'] = {'plugin': 'other'}
        self.plugin.register(self.ctx)
        self.assertNotIn('autoresearch:plan', self.ctx.commands)
        self.assertIn('autoresearch-plan', self.ctx.commands)

    def test_absent_skill_does_not_register_commands(self):
        self.skill('other')
        self.plugin.register(self.ctx)
        self.assertFalse(any(n.startswith('autoresearch') for n in self.ctx.commands))


class AutoresearchDistribution(unittest.TestCase):
    def test_vendor_integrity_and_complete_command_set(self):
        root = ROOT / 'skills/autoresearch'
        self.assertTrue((root / 'UPSTREAM.json').is_file(), 'Missing pinned upstream')
        manifest = json.loads((root / 'UPSTREAM.json').read_text())
        self.assertEqual(set(manifest['commands']), set(COMMANDS))
        for name, digest in manifest['sha256'].items():
            self.assertEqual(hashlib.sha256((root / 'upstream' / name).read_bytes()).hexdigest(), digest, name)
        for command in ('autoresearch', *COMMANDS):
            self.assertIn(command + '.md', manifest['sha256'])

    def test_vendored_runtime_executes_without_host_plugin(self):
        script = ROOT / 'skills/autoresearch/upstream/scripts/orchestrate.sh'
        self.assertTrue(script.is_file(), 'Missing runtime')
        result = subprocess.run(['bash', str(script), 'classify', 'fix the cache bug'], text=True, capture_output=True)
        self.assertEqual((result.returncode, result.stdout.strip()), (0, 'fix-broken'))


if __name__ == '__main__':
    unittest.main()
