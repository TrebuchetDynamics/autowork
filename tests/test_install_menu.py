"""install.sh's component menu against fake host CLIs in a throwaway HOME.

The Hermes item runs only as a dry run here: the real setup changes live profiles.
"""
import os
import pty
import selectors
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / 'install.sh'
NEW = 'git:github.com/TrebuchetDynamics/autowork'

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
        # The cached plugin is dropped first: Claude Code caches by version, and a reinstall of the
        # same version kept the old workflows.
        self.assertEqual(self.calls('claude'), ['claude plugin marketplace add TrebuchetDynamics/autowork',
                                                'claude plugin marketplace update autowork',
                                                'claude plugin uninstall --keep-data autowork@autowork',
                                                'claude plugin install autowork@autowork'])
        self.assertEqual(self.calls('codex'), ['codex plugin marketplace add TrebuchetDynamics/autowork --ref main',
                                               'codex plugin marketplace upgrade autowork-marketplace',
                                               'codex plugin remove autowork@autowork-marketplace',
                                               'codex plugin add autowork@autowork-marketplace'])
        link = self.home / '.local/bin/autowork'
        self.assertEqual(Path(os.readlink(link)), self.home / 'pkg/autowork/pi-autowork/bin/autowork')  # the package's
        self.assertEqual((self.home / '.local/bin/tx').read_bytes(), (ROOT / 'tmux/tx').read_bytes())
        self.assertTrue((self.home / '.local/share/bash-completion/completions/tx').is_file())
        self.assertTrue((self.home / '.tmux.conf').is_file())  # none existed
        self.assertRegex(result.stdout, r'hermes\s+skipped\s+hermes not found')
        self.assertRegex(result.stdout, r'tx\s+installed')

    def test_update_runs_the_same_items_as_a_full_install(self):
        result = self.install('update')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Autowork suite update', result.stdout)
        self.assertIn(f'pi install {NEW}', self.calls('pi'))
        self.assertIn('claude plugin install autowork@autowork', self.calls('claude'))
        self.assertIn('codex plugin add autowork@autowork-marketplace', self.calls('codex'))

    def test_a_transient_preflight_race_is_retried_once(self):
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        self.addCleanup(sys.path.remove, str(ROOT / 'scripts'))
        import install_menu
        original = install_menu.run_command
        self.addCleanup(setattr, install_menu, 'run_command', original)
        answers = [(1, 'ValueError: Destination changed since preflight: /x/skills/SKILL.md'), (0, '')]
        install_menu.run_command = lambda argv, output: answers.pop(0)
        item = install_menu.Item('hermes', 'Hermes plugin', steps=[
            install_menu.Step('update_bundle.py', ['true'], retry_on='changed since preflight')])
        code = install_menu.install([item], {'hermes'}, output=install_menu.Output('never', 0))
        self.assertEqual(code, 0)
        self.assertEqual(answers, [])  # the second (successful) run consumed the queue

    def test_a_failure_without_the_retry_marker_is_not_retried(self):
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        import install_menu
        original = install_menu.run_command
        self.addCleanup(setattr, install_menu, 'run_command', original)
        seen = []

        def fake(argv, output):
            seen.append(argv)
            return 1, 'some other failure'

        install_menu.run_command = fake
        item = install_menu.Item('hermes', 'Hermes plugin', steps=[
            install_menu.Step('update_bundle.py', ['true'], retry_on='changed since preflight')])
        code = install_menu.install([item], {'hermes'}, output=install_menu.Output('never', 0))
        self.assertEqual(code, 1)
        self.assertEqual(len(seen), 1)

    def test_no_arguments_installs_full_suite_with_verbose_output(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls('pi install'), [f'pi install {NEW}'])
        self.assertIn('claude plugin install autowork@autowork', self.calls('claude'))
        self.assertIn('codex plugin add autowork@autowork-marketplace', self.calls('codex'))
        self.assertTrue((self.home / '.local/bin/autowork').is_symlink())
        self.assertTrue((self.home / '.local/bin/tx').is_file())
        self.assertIn('$ codex plugin add autowork@autowork-marketplace', result.stdout)
        self.assertRegex(result.stdout, r'hermes\s+skipped.*hermes not found')

    def test_dry_run_defaults_to_the_full_suite_without_installing(self):
        self.fake('hermes', LOGGING)
        (self.home / '.hermes').mkdir()
        result = self.install('--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        for key in ('pi', 'autowork', 'tx', 'hermes', 'claude', 'codex'):
            self.assertRegex(result.stdout, rf'{key}\s+planned')
        self.assertEqual(self.calls('pi install'), [])
        self.assertEqual(self.calls('codex'), [])
        self.assertEqual(self.calls('hermes'), [])
        self.assertFalse((self.home / '.local/bin').exists())

    def test_tx_keeps_an_existing_tmux_config(self):
        mine = b'set -g mouse on\n# mine\n'
        paths = ('.tmux.conf', '.tmux/style.tmux', '.tmux/git-status.sh', '.tmux/short-path.sh',
                 '.local/share/bash-completion/completions/tx', '.zsh/completions/_tx',
                 '.config/fish/completions/tx.fish')
        for relative in paths:
            path = self.home / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(mine)
        preview = self.install('--full', '--skip', 'hermes,pi', '--dry-run')
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertFalse((self.home / '.local/bin/tx').exists())
        result = self.install('--only', 'tx')
        self.assertEqual(result.returncode, 0, result.stderr)
        for relative in paths:
            self.assertEqual((self.home / relative).read_bytes(), mine, relative)
        self.assertIn('kept your existing .tmux.conf', result.stdout)
        self.assertEqual(self.calls('pi install'), [])
        config = self.home / '.tmux.conf'
        config.unlink()
        config.symlink_to(self.home / 'absent-user-config')
        result = self.install('--only', 'tx')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(config.is_symlink())
        self.assertFalse(config.exists())

    def test_an_installed_package_is_updated_and_its_runners_move_onto_it(self):
        (self.home / 'pi-installed').write_text(NEW + '\n')
        result = self.install('--only', 'pi')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls('pi install'), [])
        self.assertEqual(self.calls('pi update'), [f'pi update {NEW}'])
        self.assertRegex(result.stdout, r'pi\s+installed')

    def test_menu_toggles_items_and_needs_a_terminal(self):
        result = self.install('--dry-run', '--menu', stdin='3 5 6\n\n', env={'AUTOWORK_INSTALL_UI': 'text'})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('[x] 1 Pi package', result.stdout)
        self.assertRegex(result.stdout, r'tx\s+skipped\s+not chosen')
        self.assertRegex(result.stdout, r'pi\s+planned')
        self.assertEqual(self.calls('pi install'), [])  # a dry run runs nothing
        self.assertIn('no terminal for the menu', self.install('--menu').stderr)

    def test_failed_steps_remain_failures_even_when_output_says_already(self):
        self.fake('claude', LOGGING + 'echo "boom: no network" >&2; exit 1\n')
        self.fake('codex', LOGGING + 'echo "marketplace already added" >&2; exit 4\n')
        report = self.home / 'install.jsonl'
        result = self.install('--full', '--skip', 'hermes,pi', '-q',
                              env={'AUTOWORK_INSTALL_REPORT': str(report)})
        self.assertEqual(result.returncode, 1)
        import json
        rows = {r['item']: r for r in map(json.loads, report.read_text().splitlines())}
        self.assertEqual(rows['claude'], {'item': 'claude', 'status': 'failed', 'exit': 1})
        self.assertEqual(rows['codex'], {'item': 'codex', 'status': 'failed', 'exit': 4})
        self.assertEqual(rows['tx'], {'item': 'tx', 'status': 'installed', 'exit': 0})
        self.assertEqual(rows['hermes'], {'item': 'hermes', 'status': 'skipped', 'exit': None})
        self.assertRegex(result.stdout, r'claude\s+failed\s+boom: no network')
        self.assertRegex(result.stdout, r'codex\s+failed.*marketplace already added')
        self.assertIn('unknown item(s): nope', self.install('--only', 'nope').stderr)
        (self.bin / 'codex').unlink()
        self.install('--full', '--skip', 'hermes,pi', '-q',
                     env={'AUTOWORK_INSTALL_REPORT': str(report)})
        rows = {r['item']: r for r in map(json.loads, report.read_text().splitlines())}
        self.assertEqual(rows['codex'], {'item': 'codex', 'status': 'skipped', 'exit': None})

    def test_full_selects_all_hosts_and_bundled_skills(self):
        self.fake('hermes', LOGGING)
        (self.home / '.hermes').mkdir()
        result = self.install('--full', '--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        for key in ('pi', 'autowork', 'tx', 'hermes', 'claude', 'codex'):
            self.assertRegex(result.stdout, rf'{key}\s+planned')
        self.assertIn('codex plugin add autowork@autowork-marketplace', result.stdout)
        self.assertIn('setup_bundle.py', result.stdout)
        self.assertEqual(self.calls('codex'), [])
        self.assertEqual(self.calls('hermes'), [])

    def test_explicit_missing_host_fails_but_other_items_continue(self):
        result = self.install('--only', 'hermes,tx')
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertRegex(result.stdout, r'hermes\s+failed.*hermes not found')
        self.assertTrue((self.home / '.local/bin/tx').is_file())

    def test_default_output_shows_both_child_streams(self):
        self.fake('codex', LOGGING + 'echo "skill stdout"; echo "skill stderr" >&2\n')
        result = self.install('--only', 'codex')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('skill stdout', result.stdout)
        self.assertIn('skill stderr', result.stdout)
        self.assertIn('[1/1]', result.stdout)
        self.assertNotIn('\x1b[', result.stdout)

    def test_verbose_prints_commands_and_quiet_keeps_failure_details(self):
        self.fake('codex', LOGGING + 'echo "registered skills"\n')
        result = self.install('--only', 'codex', '--verbose')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('$ codex plugin add', result.stdout)
        self.assertIn('registered skills', result.stdout)
        result = self.install('--only', 'codex', '--quiet')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('registered skills', result.stdout)
        self.assertNotIn('$ codex', result.stdout)
        self.assertRegex(result.stdout, r'codex\s+installed')
        self.fake('codex', LOGGING + 'echo "failure context"; echo "failure cause" >&2; exit 4\n')
        result = self.install('--only', 'codex', '--quiet')
        self.assertEqual(result.returncode, 1)
        self.assertIn('failure context', result.stdout)
        self.assertIn('failure cause', result.stdout)
        self.assertIn('exit 4', result.stdout)

    def test_color_controls_and_no_color_environment(self):
        for args, env, colored in (
            (('--color', 'always'), {}, True),
            (('--color', 'never'), {}, False),
            ((), {'NO_COLOR': '1', 'TERM': 'xterm-256color'}, False),
            (('--color', 'always'), {'NO_COLOR': '1'}, True),
        ):
            with self.subTest(args=args, env=env):
                result = self.install('--full', '--dry-run', *args, env=env)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual('\x1b[' in result.stdout, colored)

    def test_auto_color_uses_terminal_and_respects_opt_out(self):
        for env, colored in (({'TERM': 'xterm'}, True),
                             ({'TERM': 'dumb'}, False),
                             ({'TERM': 'xterm', 'NO_COLOR': '1'}, False)):
            with self.subTest(env=env):
                master, slave = pty.openpty()
                try:
                    result = subprocess.run(['bash', str(INSTALL), '--only', 'codex', '--dry-run'],
                                            env={**self.env, **env}, stdout=slave,
                                            stderr=subprocess.PIPE, timeout=10)
                    os.close(slave)
                    slave = None
                    chunks = []
                    while True:
                        try:
                            chunk = os.read(master, 4096)
                        except OSError:
                            break  # Linux PTY reports EIO when its writer closes.
                        if not chunk:
                            break
                        chunks.append(chunk)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(b'\x1b[' in b''.join(chunks), colored)
                finally:
                    os.close(master)
                    if slave is not None:
                        os.close(slave)

    def test_child_output_arrives_before_command_exits(self):
        # The child cannot finish until the parent receives its prompt.
        # A capture-until-exit implementation deadlocks this handshake.
        self.fake('codex', LOGGING + 'printf "waiting for input: "; read -r answer; '
                  'test "$answer" = continue || exit 9\n')
        with subprocess.Popen(['bash', str(INSTALL), '--only', 'codex'], env=self.env,
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as proc:
            seen = b''
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(proc.stdout, selectors.EVENT_READ)
                    for _ in range(3):  # marketplace add, marketplace upgrade, plugin add
                        pending = b''
                        while b'waiting for input: ' not in pending:
                            self.assertTrue(selector.select(timeout=5), seen.decode(errors='replace'))
                            chunk = os.read(proc.stdout.fileno(), 4096)
                            self.assertTrue(chunk, seen.decode(errors='replace'))
                            pending += chunk
                            seen += chunk
                        proc.stdin.write(b'continue\n')
                        proc.stdin.flush()
                tail, _ = proc.communicate(timeout=5)
                seen += tail
                self.assertEqual(proc.returncode, 0, seen.decode(errors='replace'))
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()

    def test_hermes_options_reach_the_hermes_item(self):
        self.fake('hermes', LOGGING)
        result = self.install('--only', 'hermes', '--dry-run', '--hermes-home', '/h', '--yes-deps')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('setup_bundle.py --yes-deps --dry-run --hermes-home /h', result.stdout)
        # Profiles with their own plugin clone (`hermes plugins install`) are updated: setup
        # would refuse them as "another checkout".
        clone = self.home / '.hermes/profiles/work/plugins/autowork'
        (clone / '.git').mkdir(parents=True)
        result = self.install('--only', 'hermes', '--dry-run')
        self.assertIn(f"update_bundle.py --hermes-home {self.home / '.hermes'}", result.stdout)
        self.assertNotIn('setup_bundle.py', result.stdout)


    def test_tx_moves_a_symlink_aside_instead_of_writing_through_it(self):
        elsewhere = self.home / 'other-checkout/tx'
        elsewhere.parent.mkdir()
        elsewhere.write_text('someone else\'s tx\n')
        (self.home / '.local/bin').mkdir(parents=True)
        (self.home / '.local/bin/tx').symlink_to(elsewhere)
        result = self.install('--only', 'tx')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(elsewhere.read_text(), 'someone else\'s tx\n')
        self.assertFalse((self.home / '.local/bin/tx').is_symlink())
        self.assertEqual((self.home / '.local/bin/tx').read_bytes(), (ROOT / 'tmux/tx').read_bytes())
        self.assertEqual(Path(os.readlink(self.home / '.local/bin/tx.bak')), elsewhere)

    def test_a_second_replacement_keeps_the_first_backup(self):
        command = self.home / '.local/bin/autowork'
        command.parent.mkdir(parents=True)
        for content in ('first script\n', 'second script\n'):
            if command.is_symlink():
                command.unlink()
            command.write_text(content)
            (self.home / '.local/bin/tx').write_text('old ' + content)
            result = self.install('--only', 'autowork,tx')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        bin = self.home / '.local/bin'
        self.assertEqual((bin / 'autowork.bak').read_text(), 'first script\n')
        self.assertEqual((bin / 'autowork.bak.1').read_text(), 'second script\n')
        self.assertEqual((bin / 'tx.bak').read_text(), 'old first script\n')
        self.assertEqual((bin / 'tx.bak.1').read_text(), 'old second script\n')

    def test_a_filtered_pi_package_counts_as_installed(self):
        package = self.home / 'pkg/autowork'
        (package / 'pi-autowork/bin').mkdir(parents=True)
        (package / 'pi-autowork/bin/autowork').touch()
        self.fake('pi', LOGGING + f'[ "$1" = list ] && printf "User packages:\\n  {NEW} (filtered)\\n    {package}\\n"\ntrue\n')
        result = self.install('--only', 'pi,autowork')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls('pi install'), [])
        self.assertEqual(self.calls('pi update'), [f'pi update {NEW}'])
        self.assertEqual(Path(os.readlink(self.home / '.local/bin/autowork')), package / 'pi-autowork/bin/autowork')

    def test_setup_only_hermes_options_are_refused_for_profile_clones(self):
        self.fake('hermes', LOGGING)
        (self.home / '.hermes/profiles/work/plugins/autowork/.git').mkdir(parents=True)
        for flag in ('--no-reload', '--bundle-only', '--yes-deps'):
            with self.subTest(flag=flag):
                result = self.install('--only', 'hermes,tx', flag)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertRegex(result.stdout, rf'hermes\s+failed\s+{flag} cannot apply')
                self.assertNotIn('update_bundle.py --hermes-home', self.calls())
                self.assertRegex(result.stdout, r'tx\s+installed')

    def test_hermes_without_a_home_is_unavailable_not_a_failed_setup(self):
        self.fake('hermes', LOGGING)
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r'hermes\s+skipped\s+no Hermes home at .*\.hermes')
        self.assertRegex(self.install('--list').stdout, r'hermes\s+unavailable.*no Hermes home')
        result = self.install('--only', 'hermes')
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertRegex(result.stdout, r'hermes\s+failed\s+no Hermes home')
        self.assertEqual(self.calls('hermes'), [])

if __name__ == '__main__':
    unittest.main()
