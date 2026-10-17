"""tx is the tmux session launcher; runners are the autowork command's."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TX = ROOT / 'tmux' / 'tx'


class TxTests(unittest.TestCase):
    def tx(self, *args):
        with tempfile.TemporaryDirectory() as folder:
            env = {**os.environ, 'TX_CONFIG': str(Path(folder) / 'tx.config'), 'TX_COLOR': 'never'}
            return subprocess.run(['bash', str(TX), *args], env=env, capture_output=True, text=True, timeout=30)

    def test_tx_has_no_autowork_commands(self):
        self.assertNotIn('autowork', self.tx('help').stdout)
        self.assertNotIn('autowork', TX.read_text())
        self.assertEqual(self.tx('autowork').returncode, 1)  # just an unknown alias

    def test_the_package_installs_tx_and_autowork(self):
        package = json.loads((ROOT / 'package.json').read_text())
        self.assertEqual(package['bin'], {'autowork': 'pi-autowork/bin/autowork', 'tx': 'tmux/tx'})
        for folder in ('tmux/', 'pi-autowork/bin/'):
            self.assertIn(folder, package['files'])
        for path in (TX, ROOT / 'pi-autowork/bin/autowork'):
            self.assertTrue(os.access(path, os.X_OK), path)


if __name__ == '__main__':
    unittest.main()
