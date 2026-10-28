"""Terminal copy policy uses the pinned Textual public run API."""
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from offline_textual import textual_unavailable

ROOT = Path(__file__).resolve().parents[2]


class MouseSelectionTests(unittest.TestCase):
    def test_terminal_defaults_to_native_drag_selection(self):
        if not shutil.which('uv'):
            self.skipTest('uv is needed for pinned Textual')
        code = '''
import sys
from unittest.mock import patch
sys.path.insert(0, 'pi-autowork')
from pi_autowork import tui
with patch.object(tui.FleetApp, 'run', return_value=None) as run:
    assert tui.main(['--command', 'aw', '--script', 'pa.sh']) == 0
    run.assert_called_once_with(mouse=False)
'''
        result = subprocess.run(['uv', 'run', '--offline', '--no-project', '--with', 'textual==8.2.8',
                                 'python', '-c', code], cwd=ROOT, capture_output=True, text=True, timeout=40)
        if textual_unavailable(result):
            self.skipTest('textual==8.2.8 is not in the uv cache (offline)')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


    def test_click_mode_is_opt_in_and_preserved_for_the_browser(self):
        if not shutil.which('uv'):
            self.skipTest('uv is needed for pinned Textual')
        code = '''
import shlex, sys
from unittest.mock import patch
sys.path.insert(0, 'pi-autowork')
from pi_autowork import tui, command, tui_web
with patch.object(tui.FleetApp, 'run', return_value=None) as run:
    tui.main(['--command', 'aw', '--script', 'pa.sh', '--mouse'])
    run.assert_called_once_with(mouse=True)
args = command.parser().parse_args(['tui', '--mouse', '--view-only'])
with patch.object(command, 'uv_python', return_value=['uv', 'python']), \\
     patch.object(command, 'self_path', return_value='aw'), \\
     patch.object(command, 'script', return_value='pa.sh'), \\
     patch.object(command.os, 'execvp') as execute:
    command.cmd_tui(args, {})
    assert '--mouse' in execute.call_args.args[1]
    assert '--view-only' in execute.call_args.args[1]
assert '--mouse' in shlex.split(tui_web.command('aw', 'pa.sh'))
'''
        result = subprocess.run(['uv', 'run', '--offline', '--no-project', '--with', 'textual==8.2.8',
                                 'python', '-c', code], cwd=ROOT, capture_output=True, text=True, timeout=40)
        if textual_unavailable(result):
            self.skipTest('textual==8.2.8 is not in the uv cache (offline)')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
