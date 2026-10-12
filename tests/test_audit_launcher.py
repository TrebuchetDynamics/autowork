"""Cron launcher real execution; no Hermes profiles initialized."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AuditLauncherTests(unittest.TestCase):
    def test_launcher_passes_explicit_default_owned_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / 'scripts').mkdir()
            script = home / 'scripts/profile-audit-cron.py'
            script.write_bytes((ROOT / 'scripts/profile-audit-cron.py').read_bytes())
            helper = home / 'plugins/hermes-toolset/skills/autowork/scripts/audit_profiles.py'
            helper.parent.mkdir(parents=True)
            helper.write_text('import json, sys\nprint(json.dumps(sys.argv))\n')
            result = subprocess.run([sys.executable, str(script)], cwd=home,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            args = json.loads(result.stdout)
            self.assertEqual(args, [str(helper), '--root', str(home), '--state-dir',
                str(home / 'maintenance/profile-audit/collector'), '--launch-cwd', 'default=' + str(home)])
            helper.unlink()
            result = subprocess.run([sys.executable, str(script)], cwd=home,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)['state'], 'collector_failed')


if __name__ == '__main__':
    unittest.main()
