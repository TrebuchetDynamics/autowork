"""The `autowork` command against fakes: systemctl, journalctl, pi and the runner script.

No real service or model is touched.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
AUTOWORK = ROOT / 'pi-autowork' / 'bin' / 'autowork'

# The fake systemctl keeps each unit's active/enabled state in files and logs every call.
SYSTEMCTL = r'''#!/usr/bin/env bash
echo "systemctl $*" >> "$FAKE_LOG"
shift  # --user
cmd=$1; shift
quiet=0; now=0; args=()
for a in "$@"; do case $a in --quiet) quiet=1 ;; --now) now=1 ;; *) args+=("$a") ;; esac; done
unit=${args[0]:-}
state=$FAKE_UNITS/$unit
case $cmd in
  is-active) [[ -f $state.active ]] ;;
  is-enabled) [[ -f $state.enabled ]] ;;
  start|restart) touch "$state.active" ;;
  stop) rm -f "$state.active" ;;
  kill) [[ -n ${FAKE_RELOADS:-} ]] && python3 -c 'import json, sys; p = sys.argv[1]; r = json.load(open(p))
r["reloads"] += 1; json.dump(r, open(p, "w"))' "$FAKE_RELOADS"; true ;;
  enable) touch "$state.enabled"; ((now)) && touch "$state.active"; true ;;
  disable) rm -f "$state.enabled"; ((now)) && rm -f "$state.active"; true ;;
  list-units)
    for f in "$FAKE_UNITS"/*.service.*; do
      [[ -e $f ]] || continue
      u=$(basename "$f"); u=${u%.active}; u=${u%.enabled}
      sub=dead; [[ -f $FAKE_UNITS/$u.active ]] && sub=running
      echo "$u loaded active $sub pi-autowork"
    done | sort -u ;;
esac
'''
SCRIPT = r'''#!/usr/bin/env bash
echo "script $*" >> "$FAKE_LOG"
if [[ $1 == --install-service ]]; then
  repo=$3; name=$(basename "$repo")
  mkdir -p "$PI_AUTOWORK_ENV_DIR"
  echo "PI_AUTOWORK_REPO=$repo" > "$PI_AUTOWORK_ENV_DIR/$name.env"
  touch "$FAKE_UNITS/pi-autowork@$name.service.enabled" "$FAKE_UNITS/pi-autowork@$name.service.active"
  echo "Installed and started pi-autowork@$name.service"
fi
[[ $3 == --status || $2 == --status ]] && echo "STATUS $*"
exit 0
'''
PI = r'''#!/usr/bin/env bash
echo "provider      model                         context"
echo "openai-codex  gpt-6-luna                    272K"
echo "openai-codex  gpt-6.1-sol                   500K"
echo "openrouter    deepseek/deepseek-v4.1-flash  128K"
'''
JOURNAL = '#!/usr/bin/env bash\necho "journal $*"\n'


class AutoworkCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = self.base = Path(self.tmp.name).resolve()
        self.units, self.env_dir, self.state = base / 'units', base / 'env', base / 'state'
        for folder in (self.units, self.env_dir, self.state, base / 'bin'):
            folder.mkdir()
        self.log = base / 'calls.log'
        self.log.touch()
        for name, body in (('systemctl', SYSTEMCTL), ('pi-autowork.sh', SCRIPT), ('pi', PI), ('journalctl', JOURNAL)):
            path = base / 'bin' / name
            path.write_text(body)
            path.chmod(0o755)
        self.repo = self.make_repo('india')
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(('GIT_', 'TMUX'))}
        self.env.update(FAKE_LOG=str(self.log), FAKE_UNITS=str(self.units), PI_AUTOWORK_ENV_DIR=str(self.env_dir),
                        PI_AUTOWORK_UNIT_DIR=str(base / 'unit-dir'), PI_AUTOWORK_STATE_DIR=str(self.state),
                        PI_AUTOWORK_SYSTEMCTL=str(base / 'bin/systemctl'), PI_AUTOWORK_SCRIPT=str(base / 'bin/pi-autowork.sh'),
                        AUTOWORK_JOURNALCTL=str(base / 'bin/journalctl'), AUTOWORK_PI=str(base / 'bin/pi'),
                        AUTOWORK_COLOR='never', AUTOWORK_TUI='0', COLUMNS='160')

    def make_repo(self, name, files=('TODO.md', 'goals.json')):
        repo = self.base / name
        repo.mkdir()
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
        for f in files:
            (repo / f).write_text('{}\n' if f.endswith('.json') else '# TODO\n')
        return repo

    def aw(self, *args, cwd=None):
        return subprocess.run([str(AUTOWORK), *args], cwd=cwd or self.base, env=self.env, capture_output=True,
                              text=True, timeout=60)

    def calls(self):
        return self.log.read_text().splitlines()

    def test_start_installs_once_then_only_starts(self):
        first = self.aw('start', cwd=self.repo)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual([c for c in self.calls() if c.startswith('script')],
                         [f'script --install-service --repo {self.repo}'])
        again = self.aw('start', str(self.repo))
        self.assertIn('is already running', again.stdout)
        self.assertEqual(len([c for c in self.calls() if c.startswith('script')]), 1)  # idempotent
        self.aw('pause', 'india')
        self.assertTrue((self.env_dir / 'india.paused').exists())
        restarted = self.aw('start', 'india' if False else str(self.repo))
        self.assertFalse((self.env_dir / 'india.paused').exists())  # starting ends the pause
        self.assertIn('Started pi-autowork@india.service', restarted.stdout)
        self.assertIn('systemctl --user enable --now pi-autowork@india.service', self.calls())  # survives a reboot

    def test_start_reinstalls_a_service_whose_unit_script_is_gone(self):
        self.aw('start', str(self.repo))
        unit = self.base / 'unit-dir' / 'pi-autowork@.service'
        unit.parent.mkdir(parents=True)
        unit.write_text('[Service]\nExecStart=/bin/bash /gone/old-package/scripts/pi-autowork.sh --repo ${PI_AUTOWORK_REPO}\n')
        self.aw('stop', 'india')
        env = dict(self.env)
        env.pop('PI_AUTOWORK_SCRIPT')
        env['PI_AUTOWORK_SCRIPT'] = str(self.base / 'bin/pi-autowork.sh')  # this release's script
        result = subprocess.run([str(AUTOWORK), 'start', str(self.repo)], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len([c for c in self.calls() if c.startswith('script --install-service')]), 2)

    def test_start_moves_a_service_off_another_copy_of_the_package(self):
        """Services ran from the Pi package under its old hermes-toolset name."""
        self.aw('start', str(self.repo))
        other = self.make_repo('bravo')
        self.aw('start', str(other))
        unit = self.base / 'unit-dir' / 'pi-autowork@.service'
        unit.parent.mkdir(exist_ok=True)
        old = self.base / 'old' / 'scripts' / 'pi-autowork.sh'
        old.parent.mkdir(parents=True)
        old.write_text('exit 0\n')
        unit.write_text(f'[Service]\nExecStart=/bin/bash {old} --repo ${{PI_AUTOWORK_REPO}}\n')
        moved = self.aw('start', str(self.repo))
        self.assertEqual(moved.returncode, 0, moved.stderr)
        self.assertIn(f'Moving pi-autowork services from {old} to {self.base / "bin/pi-autowork.sh"}', moved.stdout)
        self.assertIn('Still on the old copy until restarted: bravo', moved.stdout)
        self.assertEqual([c for c in self.calls() if c.startswith('script')][-1],
                         f'script --install-service --repo {self.repo}')
        unit.write_text(f'[Service]\nExecStart=/bin/bash {self.base / "bin/pi-autowork.sh"} --repo x\n')
        self.assertIn('is already running', self.aw('start', str(self.repo)).stdout)  # moved: nothing to do

    def test_the_package_is_found_where_pi_installed_it(self):
        package = self.base / 'pkg'
        (package / 'scripts').mkdir(parents=True)
        (package / 'scripts' / 'pi-autowork.sh').write_text('exit 0\n')
        (self.base / 'bin' / 'pi').write_text('#!/usr/bin/env bash\necho "User packages:"\n'
                                              'echo "  git:github.com/TrebuchetDynamics/hermes-toolset"\necho "    /old"\n'
                                              f'echo "  git:github.com/TrebuchetDynamics/autowork (filtered)"\necho "    {package}"\n')
        import sys
        sys.path.insert(0, str(ROOT / 'pi-autowork'))
        from pi_autowork import command
        from unittest import mock
        with mock.patch.dict(os.environ, AUTOWORK_PI=str(self.base / 'bin' / 'pi')):
            self.assertEqual(command.package_script(), str(package / 'scripts' / 'pi-autowork.sh'))
            (package / 'scripts' / 'pi-autowork.sh').unlink()
            self.assertIsNone(command.package_script())

    def test_start_refuses_a_repository_that_is_not_ready(self):
        bare = self.make_repo('bare', files=('TODO.md',))
        result = self.aw('start', str(bare))
        self.assertEqual(result.returncode, 1)
        self.assertIn('needs goals.json', result.stderr)
        self.assertIn('Create goals.json from TODO.md', result.stderr)
        subprocess.run(['git', '-C', str(self.repo), 'checkout', '-q', '-b', 'feature'], check=True)
        self.assertIn('main checked out', self.aw('start', str(self.repo)).stderr)
        self.assertIn('not ready', self.aw('start', str(self.base)).stderr)
        self.assertEqual(self.calls(), [c for c in self.calls() if not c.startswith('script')])

    def test_pause_resume_stop_restart_remove_go_through_systemctl(self):
        self.aw('start', str(self.repo))
        for args, expected in ((('pause', 'india'), 'disable --now'), (('resume', 'india'), 'enable --now'),
                               (('restart', 'india'), 'restart'), (('stop', 'india'), 'stop')):
            with self.subTest(args=args):
                result = self.aw(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f'systemctl --user {expected} pi-autowork@india.service', self.calls())
                self.assertEqual((self.env_dir / 'india.paused').exists(), args[0] == 'pause')
        self.aw('remove', 'india')
        self.assertIn(f'script --remove-service --repo {self.repo}', self.calls())
        self.assertIn('no runner named nothing', self.aw('stop', 'nothing').stderr)

    def running(self, reloads=0):
        """A live runner's record as the runner writes it; a reload grows its count."""
        folder = self.state / 'abc123'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'runner.json').write_text(json.dumps({'pid': 4242, 'started': 'now', 'repo': str(self.repo),
                                                        'reloads': reloads}))
        (folder / 'status.json').write_text(json.dumps({'active_workers': 2}))
        return folder / 'runner.json'

    def test_restart_reloads_a_running_runner_in_place_so_workers_keep_running(self):
        """TOOLSET-174-1d: every restart paused all workers; one cost a 10-minute run."""
        self.aw('start', str(self.repo))
        self.env['FAKE_RELOADS'] = str(self.running())
        result = self.aw('restart', 'india')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Reloaded pi-autowork@india.service; 2 worker(s) kept running.', result.stdout)
        self.assertIn('systemctl --user kill --kill-whom=main --signal=SIGHUP pi-autowork@india.service', self.calls())
        self.assertNotIn('systemctl --user restart pi-autowork@india.service', self.calls())
        stopped = self.aw('restart', '--stop-workers', 'india')  # the explicit form still restarts the unit
        self.assertIn('systemctl --user restart pi-autowork@india.service', self.calls())
        self.assertIn('workers paused and resume on the same attempt', stopped.stdout)

    def test_a_runner_that_does_not_reload_in_time_is_named_not_killed(self):
        self.aw('start', str(self.repo))
        self.running()  # nothing answers the signal
        self.env['PI_AUTOWORK_RELOAD_WAIT'] = '1'
        result = self.aw('restart', 'india')
        self.assertEqual(result.returncode, 1)
        self.assertIn('autowork restart --stop-workers india', result.stdout)
        self.assertNotIn('systemctl --user restart pi-autowork@india.service', self.calls())

    def test_a_runner_from_before_reloads_is_restarted(self):
        self.aw('start', str(self.repo))
        record = self.running()
        record.write_text(json.dumps({'pid': 4242, 'started': 'now', 'repo': str(self.repo)}))
        self.assertIn('workers paused', self.aw('restart', 'india').stdout)
        self.assertIn('systemctl --user restart pi-autowork@india.service', self.calls())

    def test_model_is_chosen_per_service_from_pis_list(self):
        self.assertEqual(self.aw('models').stdout.split(),
                         ['openai-codex/gpt-6-luna', 'openai-codex/gpt-6.1-sol', 'openrouter/deepseek/deepseek-v4.1-flash'])
        self.assertIn('no service yet', self.aw('model', str(self.repo), 'openai-codex/gpt-6-luna').stderr)
        self.aw('start', str(self.repo))
        self.assertIn('model openai-codex/gpt-6.1-sol, fallback openrouter/deepseek/deepseek-v4.1-flash',
                      self.aw('model', 'india').stdout)
        set_it = self.aw('model', 'india', 'openai-codex/gpt-6-luna', '--fallback', 'openrouter/deepseek/deepseek-v4.1-flash')
        self.assertEqual(set_it.returncode, 0, set_it.stderr)
        self.assertIn('Restarted pi-autowork@india.service', set_it.stdout)
        settings = (self.env_dir / 'india.env').read_text()
        self.assertIn('PI_AUTOWORK_PRIMARY=openai-codex/gpt-6-luna', settings)
        self.assertIn('PI_AUTOWORK_REPO=', settings)  # other settings kept
        self.assertEqual(oct((self.env_dir / 'india.env').stat().st_mode & 0o777), '0o600')
        bad = self.aw('model', 'india', 'nobody/nothing')
        self.assertIn("not in Pi's model list: nobody/nothing", bad.stderr)

    def test_ls_shows_each_runner_with_its_model_and_pause(self):
        self.assertIn('autowork runners: none', self.aw('ls').stdout)
        self.aw('start', str(self.repo))
        folder = self.state / 'k'
        folder.mkdir()
        (folder / 'runner.json').write_text(json.dumps({'pid': os.getpid(), 'repo': str(self.repo)}))
        (folder / 'status.json').write_text(json.dumps({'repo': str(self.repo), 'state': 'working', 'since': time.time() - 300,
                                                        'updated_at': time.time(), 'active_workers': 1, 'waiting': 4}))
        brief = self.aw('ls').stdout
        self.assertIn('autowork runners: 1 (1 working)', brief)
        self.assertRegex(brief, r'india\s+service\s+working [45]m\s+1 running, 4 waiting')
        self.assertIn('model openai-codex/gpt-6.1-sol', self.aw('ls', '--long').stdout)
        self.aw('pause', 'india')
        self.assertRegex(self.aw('ls').stdout, r'india\s+service\s+paused\s')

    def test_logs_status_and_help(self):
        self.aw('start', str(self.repo))
        self.assertEqual(self.aw('logs', 'india').stdout.strip(),
                         'journal --user -u pi-autowork@india.service -n 200 -o cat --no-pager')
        self.assertIn('-f', self.aw('logs', '-f', 'india').stdout)
        self.assertIn(f'STATUS --repo {self.repo} --status', self.aw('status', 'india').stdout)
        for args in ((), ('help',)):
            out = self.aw(*args).stdout
            self.assertIn('autowork start [dir]', out)
            self.assertIn('autowork model [target] [provider/model]', out)


if __name__ == '__main__':
    unittest.main()
