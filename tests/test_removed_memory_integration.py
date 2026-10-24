"""Retired memory integration cannot be selected by bundle setup."""
import json
import runpy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RemovedMemoryIntegration(unittest.TestCase):
    def test_retired_provider_has_no_setup_assets_or_defaults(self):
        self.assertFalse((ROOT / 'install-hindsight.py').exists())
        self.assertFalse((ROOT / 'plugins/hindsight.example.json').exists())
        defaults = json.loads((ROOT / 'plugins/defaults.json').read_text())
        self.assertNotIn('hindsight', defaults)
        self.assertNotIn('hindsight', defaults['imported_plugins'])
        layout = runpy.run_path(str(ROOT / 'autowork_bootstrap.py'))['Layout'](ROOT)
        for name in ('plugin.yaml', 'plugins/PLUGINS.md', 'bundle.py', 'setup_bundle.py', 'install-plugins.sh'):
            source = layout.implementation(name) if name.endswith('.py') else ROOT / name
            self.assertNotIn('hindsight', source.read_text().lower(), name)

    def test_setup_rejects_removed_flag_before_mutation(self):
        with tempfile.TemporaryDirectory() as home:
            result = subprocess.run([sys.executable, str(ROOT / 'setup_bundle.py'),
                                     '--hermes-home', home, '--dry-run',
                                     '--hindsight-config', '/nonexistent/config.json'],
                                    text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 2)
        self.assertIn('unrecognized arguments', result.stderr)


if __name__ == '__main__':
    unittest.main()
