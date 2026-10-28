"""Load the SSH profile in an isolated tmux server, never the user's server."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'tmux/tmux.conf'


@unittest.skipUnless(shutil.which('tmux'), 'tmux is not installed')
class TmuxConfigTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix='aw-tmux-')
        self.addCleanup(self.folder.cleanup)
        self.socket = str(Path(self.folder.name) / 'socket')
        self.env = {**os.environ, 'HOME': self.folder.name, 'TMUX_SLOW': '0'}
        self.env.pop('TMUX', None)
        self.addCleanup(lambda: subprocess.run(
            ['tmux', '-S', self.socket, 'kill-server'], env=self.env,
            capture_output=True, timeout=10))
        self.tmux('-f', '/dev/null', 'new-session', '-d', '-s', 'test')
        result = self.tmux('source-file', str(CONFIG))
        self.assertEqual(result.stderr, '')

    def tmux(self, *args):
        result = subprocess.run(['tmux', '-S', self.socket, *args],
                                env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def test_mouse_release_keeps_selection_without_copying(self):
        self.assertEqual(self.tmux('show-options', '-gv', 'mouse').stdout.strip(), 'on')
        for table in ('copy-mode', 'copy-mode-vi'):
            with self.subTest(table=table):
                binding = self.tmux('list-keys', '-T', table, 'MouseDragEnd1Pane').stdout
                self.assertIn('send-keys -X stop-selection', binding)
                self.assertNotIn('copy', binding.split('MouseDragEnd1Pane', 1)[1])

    def test_copy_is_explicit_and_clipboard_remains_available_over_ssh(self):
        for key in ('y', 'Enter'):
            binding = self.tmux('list-keys', '-T', 'copy-mode-vi', key).stdout
            self.assertIn('copy-selection-and-cancel', binding)
        self.assertEqual(self.tmux('show-options', '-sv', 'set-clipboard').stdout.strip(), 'external')

    def test_window_tabs_are_visible_without_idle_refresh(self):
        for option in ('window-status-format', 'window-status-current-format'):
            value = self.tmux('show-options', '-gv', option).stdout
            self.assertIn('#I', value)
            self.assertIn('#W', value)
        self.assertEqual(self.tmux('show-options', '-gv', 'status-interval').stdout.strip(), '0')
        self.assertEqual(self.tmux('show-options', '-gv', 'window-size').stdout.strip(), 'latest')


if __name__ == '__main__':
    unittest.main()
