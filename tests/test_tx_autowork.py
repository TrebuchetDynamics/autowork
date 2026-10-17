"""tx stays the traditional tmux launcher; `tx autowork` moved to the autowork command."""
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

    def test_tx_autowork_points_to_the_autowork_command(self):
        for args in (('autowork',), ('autowork', 'ls'), ('autowork', 'start', '.')):
            with self.subTest(args=args):
                result = self.tx(*args)
                self.assertEqual(result.returncode, 1)
                self.assertIn('tx autowork is now the autowork command; run: autowork', result.stderr)

    def test_help_is_the_traditional_launcher(self):
        out = self.tx('help').stdout
        self.assertIn('tx <alias>', out)
        self.assertNotIn('autowork', out)
        self.assertIn('reserved', self.tx('add', 'autowork', str(ROOT)).stderr)

    def test_the_package_installs_tx_and_autowork(self):
        package = json.loads((ROOT / 'package.json').read_text())
        self.assertEqual(package['bin'], {'autowork': 'pi-autowork/bin/autowork', 'tx': 'tmux/tx'})
        for folder in ('tmux/', 'pi-autowork/bin/'):
            self.assertIn(folder, package['files'])
        for path in (TX, ROOT / 'pi-autowork/bin/autowork'):
            self.assertTrue(os.access(path, os.X_OK), path)


if __name__ == '__main__':
    unittest.main()
