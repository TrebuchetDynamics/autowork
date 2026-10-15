"""Repository-type role profiles through the actual docs.py CLI."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('docs.py')
SCAFFOLD = Path(__file__).resolve().parents[1] / 'references' / 'document-scaffold.md'


class DocsProfileTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        (self.repo / 'docs').mkdir()
        (self.repo / 'README.md').write_text('# Tool\n')

    def manifest(self, profile, roles):
        data = {'version': 1, 'roles': {name: {'status': 'maintained', 'path': 'README.md'}
                                        for name in roles}}
        if profile is not None:
            data['profile'] = profile
        (self.repo / 'docs' / 'roles.json').write_text(json.dumps(data))

    def cli(self, command='check', expected=0):
        result = subprocess.run([sys.executable, str(SCRIPT), command, str(self.repo)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        return result.stdout + result.stderr

    def baseline(self, profile):
        result = subprocess.run([sys.executable, str(SCRIPT), 'profiles'],
                                capture_output=True, text=True, timeout=10, check=True)
        return json.loads(result.stdout)[profile]

    def test_every_profile_lists_readme_and_changelog(self):
        result = subprocess.run([sys.executable, str(SCRIPT), 'profiles'],
                                capture_output=True, text=True, timeout=10, check=True)
        profiles = json.loads(result.stdout)
        self.assertEqual(set(profiles), {'service', 'library', 'cli-plugin', 'application', 'infrastructure'})
        for name, roles in profiles.items():
            with self.subTest(profile=name):
                self.assertIn('readme', roles)
                self.assertIn('changelog', roles)

    def test_cli_plugin_requires_reference_but_service_does_not(self):
        cli_roles = [role for role in self.baseline('cli-plugin') if role != 'reference']
        self.manifest('cli-plugin', cli_roles)
        self.assertIn('reference: baseline role is neither mapped', self.cli(expected=1))
        self.manifest('service', self.baseline('service'))
        self.assertNotIn('reference', self.baseline('service'))
        self.assertEqual(self.cli().strip(), 'ok')

    def test_missing_profile_keeps_current_baseline(self):
        self.manifest(None, ['readme', 'prd', 'architecture', 'spec', 'test-plan', 'runbook', 'changelog'])
        self.assertEqual(self.cli().strip(), 'ok')

    def test_unknown_or_malformed_profile_fails_validation(self):
        for profile in ('desktop', 3):
            with self.subTest(profile=profile):
                self.manifest(profile, ['readme'])
                self.assertIn('manifest: unknown profile', self.cli('validate', expected=1))

    def test_scaffold_documents_every_profile_and_new_role(self):
        text = SCAFFOLD.read_text()
        result = subprocess.run([sys.executable, str(SCRIPT), 'profiles'],
                                capture_output=True, text=True, timeout=10, check=True)
        for name, roles in json.loads(result.stdout).items():
            with self.subTest(profile=name):
                self.assertIn(f'| `{name}` |', text)
                for role in roles:
                    self.assertIn(f'`{role}`', text)
        for role in ('reference', 'glossary', 'troubleshooting', 'install-upgrade'):
            self.assertIn(f'`{role}`', text)


if __name__ == '__main__':
    unittest.main()
