"""Profile creation policy and actual bundled command discovery; no live profiles."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/profile-create/SKILL.md'


class ProfileCreateTests(unittest.TestCase):
    def test_creation_contract_requires_repo_bundle_and_isolated_memory(self):
        self.assertTrue(SKILL.is_file())
        text = SKILL.read_text()
        for requirement in ('name: profile-create', 'terminal.cwd', 'git -C',
                            'rev-parse --show-toplevel', 'hermes profile create',
                            'plugins install', 'plugins show hermes-toolset',
                            'install-omh.py', 'independent', 'SOUL.md',
                            'Never clone credentials', 'Never restart',
                            'incomplete', 'profile_create', '--dry-run'):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, text)
        description = next(line for line in text.splitlines() if line.startswith('description:'))
        self.assertLessEqual(len(description.split(':', 1)[1].strip().strip('"')), 60)
        self.assertNotRegex(text, r'/home/[^/\s]+')

    def test_real_discovery_and_gateway_dispatch_preserve_arguments(self):
        self.assertTrue(SKILL.is_file())
        spec = importlib.util.spec_from_file_location('profile_create_plugin', ROOT / '__init__.py')
        assert spec is not None and spec.loader is not None
        plugin = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin)
        matches = [row for row in plugin._discover_skills() if row[0] == 'profile-create']
        self.assertEqual(matches, [('profile-create', 'profile-create', SKILL)])
        messages = []
        ctx = types.SimpleNamespace(inject_message=lambda prompt, **kw: messages.append((prompt, kw)) or True)
        session = {'HERMES_SESSION_PLATFORM': 'telegram', 'HERMES_SESSION_CHAT_ID': 'fixture-chat'}
        stub = types.SimpleNamespace(get_session_env=lambda key: session.get(key, ''))
        args = 'fixture /repository with spaces --dry-run'
        with patch.dict(sys.modules, {'gateway.session_context': stub}):
            self.assertIsNone(plugin._invoke(ctx, 'profile-create', SKILL, args))
        self.assertIn('hermes-toolset:profile-create', messages[0][0])
        self.assertIn(args, messages[0][0])
        self.assertEqual(messages[0][1]['origin']['chat_id'], 'fixture-chat')


if __name__ == '__main__':
    unittest.main()
