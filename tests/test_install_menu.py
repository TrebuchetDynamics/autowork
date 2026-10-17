"""install.sh's component menu against fake host CLIs in a throwaway HOME.

The Hermes item runs only as a dry run here: the real setup changes live profiles.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / 'install.sh'
NEW, OLD = 'git:github.com/TrebuchetDynamics/autowork', 'git:github.com/TrebuchetDynamics/hermes-toolset'

# A fake pi: `pi list` reads installed sources from a file; install and remove edit it.
PI = r'''#!/usr/bin/env bash
echo "pi $*" >> "$FAKE_LOG"
db=$FAKE_HOME/pi-installed
touch "$db"
case $1 in
  list) echo "User packages:"; while read -r src; do [[ -n $src ]] && { echo "  $src"; echo "    $FAKE_HOME/pkg/${src##*/}"; }; done < "$db" ;;
  install) echo "$2" >> "$db"; mkdir -p "$FAKE_HOME/pkg/${2##*/}/scripts" "$FAKE_HOME/pkg/${2##*/}/pi-autowork/bin";
           : > "$FAKE_HOME/pkg/${2##*/}/pi-autowork/bin/autowork" ;;
  remove) grep -vxF "$2" "$db" > "$db.new"; mv "$db.new" "$db" ;;
esac
'''
LOGGING = '#!/usr/bin/env bash\necho "$(basename "$0") $*" >> "$FAKE_LOG"\n'


class InstallMenuTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()
        self.bin = self.home / 'fakebin'
        self.bin.mkdir()
        self.log = self.home / 'calls.log'
        self.log.touch()
        self.fake('pi', PI)
        for name in ('claude', 'codex', 'systemctl'):
            self.fake(name, LOGGING)
        self.env = {'PATH': f'{self.bin}:/usr/bin:/bin', 'HOME': str(self.home), 'FAKE_LOG': str(self.log),
                    'FAKE_HOME': str(self.home), 'XDG_CONFIG_HOME': str(self.home / '.config'),
                    'PI_AUTOWORK_SYSTEMCTL': str(self.bin / 'systemctl'), 'LANG': 'C.UTF-8'}

    def fake(self, name, body):
        path = self.bin / name
        path.write_text(body)
        path.chmod(0o755)

    def install(self, *args, stdin=None, env=None):
        return subprocess.run(['bash', str(INSTALL), *args], env={**self.env, **(env or {})}, input=stdin,
                              capture_output=True, text=True, timeout=120)

    def calls(self, prefix=''):
        return [c for c in self.log.read_text().splitlines() if c.startswith(prefix)]

    def test_list_marks_missing_hosts(self):
        out = self.install('--list').stdout
        for key in ('pi', 'autowork', 'tx', 'claude', 'codex'):
            self.assertRegex(out, rf'{key}\s+available')
        self.assertRegex(out, r'hermes\s+unavailable.*hermes not found')

    def test_all_installs_every_available_item_in_order(self):
        result = self.install('--all')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls('pi install'), [f'pi install {NEW}'])
        self.assertEqual(self.calls('claude'), ['claude plugin marketplace add TrebuchetDynamics/autowork',
                                                'claude plugin install autowork@autowork'])
        self.assertEqual(self.calls('codex'), ['codex plugin marketplace add TrebuchetDynamics/autowork --ref main',
                                               'codex plugin add autowork@autowork-marketplace'])
        link = self.home / '.local/bin/autowork'
        self.assertEqual(Path(os.readlink(link)), self.home / 'pkg/autowork/pi-autowork/bin/autowork')  # the package's
        self.assertEqual((self.home / '.local/bin/tx').read_bytes(), (ROOT / 'tmux/tx').read_bytes())
        self.assertTrue((self.home / '.local/share/bash-completion/completions/tx').is_file())
        self.assertTrue((self.home / '.tmux.conf').is_file())  # none existed
        self.assertRegex(result.stdout, r'hermes\s+skipped\s+hermes not found')
        self.assertRegex(result.stdout, r'tx\s+installed')

    def test_tx_keeps_an_existing_tmux_config(self):
        mine = b'set -g mouse on\n# mine\n'
        (self.home / '.tmux.conf').write_bytes(mine)
        result = self.install('--only', 'tx')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.home / '.tmux.conf').read_bytes(), mine)
        self.assertIn('kept your existing .tmux.conf', result.stdout)
        self.assertEqual(self.calls('pi install'), [])

    def test_the_old_package_is_replaced_after_its_services_move(self):
        (self.home / 'pi-installed').write_text(OLD + '\n')
        unit = self.home / '.config/systemd/user/pi-autowork@.service'
        unit.parent.mkdir(parents=True)
        unit.write_text(f'[Service]\nExecStart=/bin/bash {self.home}/pkg/hermes-toolset/scripts/pi-autowork.sh '
                        '--repo ${PI_AUTOWORK_REPO}\n')
        self.fake('systemctl', LOGGING + '[[ $2 == list-units ]] && echo "pi-autowork@india.service loaded active running x"\n'
                  'exit 0\n')
        result = self.install('--only', 'pi')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f'{self.home}/pkg/autowork/scripts/pi-autowork.sh --repo', unit.read_text())
        order = [c for c in self.log.read_text().splitlines() if c.startswith(('pi install', 'pi remove', 'systemctl'))]
        self.assertEqual([c for c in order if 'list-units' not in c],
                         [f'pi install {NEW}', 'systemctl --user daemon-reload',
                          'systemctl --user restart pi-autowork@india.service', f'pi remove {OLD}'])
        self.assertEqual((self.home / 'pi-installed').read_text().split(), [NEW])

    def test_menu_toggles_items_and_needs_a_terminal(self):
        result = self.install('--dry-run', '--menu', stdin='3 5 6\n\n', env={'AUTOWORK_INSTALL_UI': 'text'})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('[x] 1 Pi package', result.stdout)
        self.assertRegex(result.stdout, r'tx\s+skipped\s+not chosen')
        self.assertRegex(result.stdout, r'pi\s+planned')
        self.assertEqual(self.calls('pi install'), [])  # a dry run runs nothing
        self.assertIn('no terminal for the menu', self.install().stderr)

    def test_a_failed_step_is_reported_and_already_installed_is_fine(self):
        self.fake('claude', LOGGING + 'echo "boom: no network" >&2; exit 1\n')
        self.fake('codex', LOGGING + 'echo "marketplace already added" >&2; exit 1\n')
        result = self.install('--only', 'claude,codex')
        self.assertEqual(result.returncode, 1)
        self.assertRegex(result.stdout, r'claude\s+failed\s+boom: no network')
        self.assertRegex(result.stdout, r'codex\s+installed\s+already there')
        self.assertIn('unknown item(s): nope', self.install('--only', 'nope').stderr)

    def test_hermes_options_reach_the_hermes_item(self):
        self.fake('hermes', LOGGING)
        result = self.install('--only', 'hermes', '--dry-run', '--hermes-home', '/h', '--yes-deps')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('setup_bundle.py --yes-deps --dry-run --hermes-home /h', result.stdout)


if __name__ == '__main__':
    unittest.main()
