"""Repeated plugin loads preserve owners and handle concurrent publication."""
import errno
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_provisioning', ROOT / 'install_skills.py')
assert spec is not None and spec.loader is not None
provisioning = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provisioning)


class ProvisioningTests(unittest.TestCase):
    def test_new_native_autowork_defaults_to_100_and_existing_owner_copy_is_preserved(self):
        import json
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profiles = [('default', root / 'home'), ('other', root / 'home/profiles/other')]
            skills = [ROOT / 'skills' / name for name in ('autowork', 'docs-sync', 'shared')]
            self.assertEqual(provisioning.install(ROOT / 'skills', profiles, skills=skills,
                                                 report=lambda _: None), 0)
            workspace = root / 'workspace'
            workspace.mkdir()
            contract = root / 'contract.txt'
            contract.write_text(''.join(f'{key}: fixture {key}\n' for key in
                ('Objective', 'Scope', 'Verification', 'Source', 'Project payoff', 'Current evidence',
                 'Expected change', 'Acceptance', 'Stop conditions', 'Repo-docs pass')))
            for profile, home in profiles:
                script = home / 'skills/autowork/scripts/start_goal.py'
                result = subprocess.run([sys.executable, str(script), '--profile', profile,
                    '--workspace', str(workspace), '--title', 'Fixture', '--contract-file', str(contract),
                    '--validate-only'], capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['goal_max_turns'], 100)
                self.assertIn('current agent session', (home / 'skills/autowork/SKILL.md').read_text())
            owner = profiles[0][1] / 'skills/autowork/scripts/start_goal.py'
            owner.write_text(owner.read_text().replace('BUDGET = 100', 'BUDGET = 50') + '\n# Owner customization\n')
            original = owner.read_bytes()
            self.assertEqual(provisioning.install(ROOT / 'skills', profiles, skills=skills,
                                                 report=lambda _: None), 0)
            self.assertEqual(owner.read_bytes(), original)

    def test_concurrent_complete_winner_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            skill = source / 'example'
            skill.mkdir(parents=True)
            (skill / 'SKILL.md').write_text('bundled skill')
            home = root / 'home'
            target = home / 'skills/example'

            def publish_winner(staged, destination):
                destination.mkdir()
                (destination / 'SKILL.md').write_text('concurrent winner')
                raise OSError(errno.ENOTEMPTY, 'destination published concurrently')

            with patch.object(provisioning, '_publish', publish_winner):
                result = provisioning.install(source, [('owner', home)], report=lambda message: None)
            self.assertEqual(result, 0)
            self.assertEqual((target / 'SKILL.md').read_text(), 'concurrent winner')
            self.assertEqual(sorted(p.name for p in target.parent.iterdir()), ['example'])

    def test_empty_slot_created_during_publication_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            skill = source / 'example'
            skill.mkdir(parents=True)
            (skill / 'SKILL.md').write_text('bundled skill')
            home = root / 'home'
            target = home / 'skills/example'
            publish = provisioning._publish
            original_inode = []

            def create_slot_then_publish(staged, destination):
                destination.mkdir()
                original_inode.append(destination.stat().st_ino)
                return publish(staged, destination)

            with patch.object(provisioning, '_publish', create_slot_then_publish):
                result = provisioning.install(source, [('owner', home)], report=lambda message: None)
            self.assertEqual(result, 1)
            self.assertEqual(target.stat().st_ino, original_inode[0])
            self.assertEqual(list(target.iterdir()), [])

    def test_invalid_existing_slot_fails_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            skill = source / 'example'
            skill.mkdir(parents=True)
            (skill / 'SKILL.md').write_text('bundled skill')
            home = root / 'home'
            target = home / 'skills/example'
            target.mkdir(parents=True)
            (target / 'owner-note').write_text('keep me')
            result = provisioning.install(source, [('owner', home)], report=lambda message: None)
            self.assertEqual(result, 1)
            self.assertEqual((target / 'owner-note').read_text(), 'keep me')
            self.assertFalse((target / 'SKILL.md').exists())


if __name__ == '__main__':
    unittest.main()
