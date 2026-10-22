"""The `autowork` command against fakes: systemctl, journalctl, pi and the runner script.

No real service or model is touched.
"""
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
AUTOWORK = ROOT / 'pi-autowork' / 'bin' / 'autowork'
sys.path.insert(0, str(ROOT / 'pi-autowork' / 'engine'))
import store_fixture  # noqa: E402
import task_store  # noqa: E402
sys.path.insert(0, str(ROOT / 'pi-autowork'))
from pi_autowork import fleet_view  # noqa: E402
from pi_autowork.processes import start_time  # noqa: E402

GOAL = ('+++\nschema = 1\nid = "G"\ntitle = "Fixture"\npriority = 1\nsource = "docs/plan.md"\n'
        'status = "unmet"\nfocus = false\n+++\n')

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
  printf 'PI_AUTOWORK_REPO=%s\nPI_AUTOWORK_STATE_DIR=%s\n' "$repo" "$PI_AUTOWORK_STATE_DIR" > "$PI_AUTOWORK_ENV_DIR/$name.env"
  [[ -n ${PI_CODING_AGENT_DIR:-} ]] && printf 'PI_CODING_AGENT_DIR=%s\n' "$PI_CODING_AGENT_DIR" >> "$PI_AUTOWORK_ENV_DIR/$name.env"
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
        self.env.update(HOME=str(base / 'home'), FAKE_LOG=str(self.log), FAKE_UNITS=str(self.units), PI_AUTOWORK_ENV_DIR=str(self.env_dir),
                        PI_AUTOWORK_UNIT_DIR=str(base / 'unit-dir'), PI_AUTOWORK_STATE_DIR=str(self.state),
                        PI_AUTOWORK_SYSTEMCTL=str(base / 'bin/systemctl'), PI_AUTOWORK_SCRIPT=str(base / 'bin/pi-autowork.sh'),
                        AUTOWORK_JOURNALCTL=str(base / 'bin/journalctl'), AUTOWORK_PI=str(base / 'bin/pi'),
                        AUTOWORK_COLOR='never', AUTOWORK_TUI='0', COLUMNS='160')

    def make_repo(self, name, files=('tasks/goals/G.md',)):
        repo = self.base / name
        repo.mkdir()
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
        for f in files:
            (repo / f).parent.mkdir(parents=True, exist_ok=True)
            (repo / f).write_text(GOAL if f.startswith('tasks/') else '# TODO\n')
        subprocess.run(['git', '-C', str(repo), 'add', '-A'], check=True)
        subprocess.run(['git', '-C', str(repo), '-c', 'user.name=T', '-c', 'user.email=t@example.invalid',
                        'commit', '-qm', 'planning'], check=True)
        return repo

    def aw(self, *args, cwd=None):
        return subprocess.run([str(AUTOWORK), *args], cwd=cwd or self.base, env=self.env, capture_output=True,
                              text=True, timeout=60)

    def calls(self):
        return self.log.read_text().splitlines()

    def portal_stub(self):
        requests = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append((self.path, self.headers.get('Authorization')))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"status":"ok","upstream":"Nous Portal","authenticated":true}')

            def log_message(self, *args):
                pass

        server = http.server.HTTPServer(('127.0.0.1', int(os.environ.get('AUTOWORK_PORT_BASE', '20700')) + 1), Handler)
        self.addCleanup(server.server_close)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        return f'http://127.0.0.1:{server.server_port}/v1', requests

    def test_portal_setup_requires_consent_and_preserves_other_providers(self):
        agent = self.base / 'agent'
        agent.mkdir()
        config = agent / 'models.json'
        original = b'{"other": true, "providers": {"private": {"apiKey": "DO-NOT-LOG", "baseUrl": "https://example.invalid"}}}\n'
        config.write_bytes(original)
        self.env['PI_CODING_AGENT_DIR'] = str(agent)
        endpoint, requests = self.portal_stub()
        args = ('setup-portal', '--provider', 'nous-test', '--model', 'openai/example', '--endpoint', endpoint, '--json')
        preview = self.aw(*args)
        self.assertEqual(preview.returncode, 0, preview.stderr)
        proposal = json.loads(preview.stdout)
        self.assertFalse(proposal['applied'])
        self.assertIn('consent', proposal['message'].lower())
        self.assertEqual(proposal['endpoint'], endpoint)
        self.assertEqual(proposal['proxy']['state'], 'available')
        self.assertEqual(config.read_bytes(), original)
        self.assertEqual(sorted(p.name for p in agent.iterdir()), ['models.json'])
        result = self.aw(*args, '--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        prepared = json.loads(result.stdout)
        self.assertTrue(prepared['applied'])
        data = json.loads(config.read_text())
        self.assertEqual(data['providers']['private'], json.loads(original)['providers']['private'])
        self.assertTrue(data['other'])
        self.assertEqual(data['providers']['nous-test'], {
            'baseUrl': endpoint, 'api': 'openai-completions',
            'apiKey': 'local-proxy-placeholder', 'models': [{'id': 'openai/example'}]})
        self.assertEqual(config.stat().st_mode & 0o777, 0o600)
        self.assertNotIn('DO-NOT-LOG', preview.stdout + preview.stderr + result.stdout + result.stderr)
        before = config.read_bytes()
        self.assertEqual(self.aw(*args, '--apply').returncode, 0)
        self.assertEqual(config.read_bytes(), before)
        data['providers']['nous-test']['models'][0].update(name='Retained name', contextWindow=32000)
        config.write_text(json.dumps(data))
        result = self.aw('setup-portal', '--provider', 'nous-test', '--model', 'another-model',
                         '--endpoint', endpoint, '--apply', '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        updated = json.loads(config.read_text())
        self.assertEqual(updated['providers']['nous-test']['models'], [
            {'id': 'openai/example', 'name': 'Retained name', 'contextWindow': 32000}, {'id': 'another-model'}])
        self.assertEqual(updated['providers']['private'], data['providers']['private'])
        self.assertTrue(requests)
        self.assertEqual(set(requests), {('/health', None)})
        self.assertEqual(self.calls(), [])  # no Pi auth, Hermes CLI or lifecycle operation

    def test_service_model_uses_saved_or_default_directory_not_the_callers(self):
        endpoint, requests = self.portal_stub()
        default = self.base / 'home' / '.pi' / 'agent'
        caller = self.base / 'caller-agent'
        saved = self.base / 'saved-agent'
        self.env['PI_CODING_AGENT_DIR'] = str(caller)
        entry = {'apiKey': 'local-proxy-placeholder', 'api': 'openai-completions',
                 'baseUrl': endpoint, 'models': [{'id': 'example'}]}
        for folder in (default, caller, saved):
            folder.mkdir(parents=True)
            folder.joinpath('models.json').write_text(json.dumps({'providers': {'nous-test': entry}}))
        caller.joinpath('models.json').write_text(json.dumps({'providers': {'nous-test': {
            **entry, 'baseUrl': f'http://127.0.0.1:{int(os.environ.get("AUTOWORK_PORT_BASE", "20700")) + 3}/v1'}}}))
        self.base.joinpath('bin/pi').write_text('#!/usr/bin/env bash\necho "catalog $PI_CODING_AGENT_DIR" >> "$FAKE_LOG"\necho "provider model context"\necho "nous-test example 128K"\n')
        env_file = self.env_dir / 'india.env'
        for selected in (default, saved):
            with self.subTest(selected=selected):
                original = f'PI_AUTOWORK_REPO={self.repo}\n'
                if selected == saved:
                    original += f'PI_CODING_AGENT_DIR={saved}\n'
                env_file.write_text(original)
                self.log.write_text('')
                result = self.aw('model', 'india', 'nous-test/example')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f'catalog {selected}', self.calls())
                self.assertIn('PI_AUTOWORK_PRIMARY=nous-test/example', env_file.read_text())
                self.assertNotIn(str(caller), env_file.read_text())
        self.assertEqual(set(requests), {('/health', None)})

    def test_portal_setup_refuses_conflicts_without_partial_write(self):
        agent = self.base / 'agent'
        agent.mkdir()
        self.env['PI_CODING_AGENT_DIR'] = str(agent)
        config = agent / 'models.json'
        for original in (b'{bad', b'{"providers": []}',
                         b'{"providers": {}, "providers": {}}', b'{"bad":NaN}', b'{"bad":1e999}',
                         b'{"providers":{"nous-test":{"apiKey":"local-proxy-placeholder","api":"openai-completions","baseUrl":123}}}',
                         b'{"providers":{"nous-test":{"apiKey":"DO-NOT-LOG"}}}',
                         *[json.dumps({'providers': {'nous-test': {
                             'apiKey': 'local-proxy-placeholder', 'api': 'openai-completions',
                             'baseUrl': 'http://127.0.0.1:8645/v1', 'models': [{'id': 'example', **override}]}
                         }}).encode() for override in (
                             {'baseUrl': 'https://example.invalid/v1'}, {'api': 'anthropic-messages'},
                             {'headers': {'Authorization': '!DO-NOT-LOG'}})]):
            with self.subTest(original=original):
                config.write_bytes(original)
                result = self.aw('setup-portal', '--provider', 'nous-test', '--model', 'example', '--apply')
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(config.read_bytes(), original)
                self.assertNotIn('DO-NOT-LOG', result.stdout + result.stderr)
                self.assertNotIn('Traceback', result.stderr)
        self.assertEqual(self.calls(), [])

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

    def test_start_refuses_conflicting_service_settings_without_starting(self):
        self.assertEqual(self.aw('start', str(self.repo)).returncode, 0)
        settings = self.env_dir / 'india.env'
        saved = settings.read_text() + ('PI_AUTOWORK_PUSH=1\nPI_AUTOWORK_TASK_TIMEOUT=600\n'
                                       'PI_AUTOWORK_WORKERS=2\nPI_AUTOWORK_NO_FALLBACK=1\n'
                                       'PI_AUTOWORK_ALLOW_HERMES=1\n')
        settings.write_text(saved)
        for active in (False, True):
            marker = self.units / 'pi-autowork@india.service.active'
            marker.touch() if active else marker.unlink(missing_ok=True)
            for key, value in (('PI_AUTOWORK_PUSH', '0'), ('PI_AUTOWORK_TASK_TIMEOUT', '900'),
                               ('PI_AUTOWORK_WORKERS', '8'), ('PI_AUTOWORK_NO_FALLBACK', '0'),
                               ('PI_AUTOWORK_ALLOW_HERMES', '0'), ('PI_AUTOWORK_REVIEW', '0')):
                with self.subTest(active=active, setting=key):
                    paused = self.env_dir / 'india.paused'
                    paused.write_text('paused\n')
                    self.log.write_text('')
                    self.env[key] = value
                    result = self.aw('start', str(self.repo))
                    del self.env[key]
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn(key, result.stderr)
                    self.assertIn(str(settings), result.stderr)
                    self.assertIn('--install-service', result.stderr)
                    self.assertEqual(settings.read_text(), saved)
                    self.assertTrue(paused.exists())
                    self.assertEqual(marker.exists(), active)
                    self.assertFalse(any(c.startswith('script') or 'enable' in c or 'restart' in c
                                         for c in self.calls()))
        self.env['PI_AUTOWORK_PUSH'] = '1'  # a matching request remains idempotent
        self.assertEqual(self.aw('start', str(self.repo)).returncode, 0)

    def test_push_grant_is_persisted_per_repository_and_status_is_read_only(self):
        # Exercise the real settings installer/loader, with only systemctl and Pi faked.
        launcher = self.base / 'bin/pi-autowork.sh'
        launcher.write_text(f'#!/bin/sh\nexec {sys.executable} {ROOT}/pi-autowork/pi_autowork/cli.py "$@"\n')
        self.env.update(PI_AUTOWORK_TOOLSET=str(ROOT), PI_BIN=str(self.base / 'bin/pi'),
                        PI_AUTOWORK_HERMES_HOME=str(self.base / 'no-hermes'))
        self.env.pop('PI_AUTOWORK_PUSH', None)
        initial = self.aw('status', str(self.repo))
        self.assertEqual(initial.returncode, 0, initial.stderr)
        self.assertIn('Push:       disabled', initial.stdout)
        self.assertFalse((self.env_dir / 'india.env').exists())
        self.env['PI_AUTOWORK_PUSH'] = '1'
        installed = self.aw('start', str(self.repo))
        self.assertEqual(installed.returncode, 0, installed.stderr)
        del self.env['PI_AUTOWORK_PUSH']
        settings = self.env_dir / 'india.env'
        self.assertIn('PI_AUTOWORK_PUSH=1\n', settings.read_text())
        # A same-named repository elsewhere must not inherit india's saved grant.
        (self.base / 'elsewhere').mkdir()
        other = self.make_repo('elsewhere/india')
        for setting, label in (('1', 'enabled'), ('0', 'disabled')):
            saved = settings.read_bytes().replace(b'PI_AUTOWORK_PUSH=1\n', f'PI_AUTOWORK_PUSH={setting}\n'.encode())
            settings.write_bytes(saved + b'# preserve this formatting\n\n')
            before = settings.read_bytes()
            self.log.write_text('')
            for _ in range(2):
                status = self.aw('status', str(self.repo))
                self.assertEqual(status.returncode, 0, status.stderr)
                self.assertIn(f'Push:       {label}', status.stdout)
            self.assertIn('Push:       disabled', self.aw('status', str(other)).stdout)
            self.assertEqual(settings.read_bytes(), before)
            self.assertEqual(self.calls(), [])

    def test_ls_json_shows_saved_push_grant_not_the_callers_environment(self):
        settings = self.env_dir / 'india.env'
        for value, expected in ((None, False), ('1', True), ('0', False), ('', False), ('true', False)):
            with self.subTest(value=value):
                saved = f'PI_AUTOWORK_REPO={self.repo}\n# keep this comment\n'
                if value is not None:
                    saved += f'PI_AUTOWORK_PUSH={value}\n'
                settings.write_text(saved)
                self.env['PI_AUTOWORK_PUSH'] = '0' if expected else '1'
                self.log.write_text('')
                result = self.aw('ls', '--json')
                self.assertEqual(result.returncode, 0, result.stderr)
                runner, = json.loads(result.stdout)['runners']
                self.assertIs(runner.get('push'), expected)
                self.assertEqual(settings.read_text(), saved)
                self.assertTrue(all(c.startswith(('systemctl --user list-units ',
                                                 'systemctl --user is-enabled ')) for c in self.calls()))

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
        """Services ran from the Pi package under an older name."""
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
                                              'echo "  git:github.com/TrebuchetDynamics/old-toolset"\necho "    /old"\n'
                                              f'echo "  git:github.com/TrebuchetDynamics/autowork (filtered)"\necho "    {package}"\n')
        import sys
        sys.path.insert(0, str(ROOT / 'pi-autowork'))
        from pi_autowork import command
        from unittest import mock
        with mock.patch.dict(os.environ, AUTOWORK_PI=str(self.base / 'bin' / 'pi')):
            self.assertEqual(command.package_script(), str(package / 'scripts' / 'pi-autowork.sh'))
            (package / 'scripts' / 'pi-autowork.sh').unlink()
            self.assertIsNone(command.package_script())

    def test_clear_held_requests_technical_recovery(self):
        """One command turns every held task into a request the runner clears, no decision asked."""
        self.aw('start', str(self.repo))
        state = self.state / 'deadbeef'
        state.mkdir()
        (state / 'runner.json').write_text(json.dumps(
            {'repo': str(self.repo), 'pid': os.getpid(), 'start_time': start_time(os.getpid()),
             'started': '2026-01-01T00:00:00', 'reloads': 0,
             'toolset_rev': 'test'}))
        (state / 'status.json').write_text(json.dumps(
            {'schema': 1, 'repo': str(self.repo), 'state': 'working',
             'held': [{'task': 'ALPHA-1', 'cause': 'conflict'}, {'task': 'BETA-2', 'cause': None}]}))
        dry = self.aw('clear-held', 'india', '--dry-run')
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertIn('would clear 2 held task(s): ALPHA-1, BETA-2', dry.stdout)
        self.assertFalse((state / 'requests').exists())
        done = self.aw('clear-held', 'india')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue((state / 'requests' / 'clear-held-ALPHA-1').exists())
        self.assertTrue((state / 'requests' / 'clear-held-BETA-2').exists())
        one = self.aw('clear-held', 'india', 'ALPHA-1')
        self.assertIn('ALPHA-1', one.stdout)
        self.assertNotIn('BETA-2', one.stdout)

    def test_tasks_move_re_sorts_an_open_task_by_its_rank(self):
        """The Tasks window's Up and Down: a task's rank is the priority."""
        store_fixture.write_todo(self.repo, '# TODO\n\n## Now\n\n- [ ] A-1 — First\n\n- [ ] A-2 — Second\n')
        result = self.aw('tasks', 'move', 'A-2', 'up', str(self.repo))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('ok A-2 rank', result.stdout)
        ranks = {t.id: t.rank for t in task_store.TaskStore.at(self.repo, 'HEAD').tasks.values()}
        moved = task_store.TaskStore.at(self.repo, self.commit_tasks()).tasks
        self.assertLess(moved['A-2'].rank, moved['A-1'].rank, ranks)
        result = self.aw('tasks', 'move', 'A-2', 'up', str(self.repo))
        self.assertEqual(result.returncode, 1)
        self.assertIn('A-2 is already at the top of Now', result.stderr)

    def commit_tasks(self):
        subprocess.run(['git', '-C', str(self.repo), 'add', '-A', '--', 'tasks'], check=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=T', '-c', 'user.email=t@example.invalid',
                        'commit', '-qm', 'tasks'], check=True)
        return 'HEAD'

    def test_owner_answers_and_new_tasks_go_through_autowork_tasks(self):
        """The TUI's answers, section moves and new tasks are writes to the task store."""
        store_fixture.write_todo(self.repo, '# TODO\n\n## Now\n\n- [ ] A-1 — First\n  Status: open\n')
        result = self.aw('tasks', 'field', 'A-1', 'Owner decision', '2026-10-20: ship it', str(self.repo))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = self.aw('tasks', 'place', 'A-1', 'Needs decision', str(self.repo), '--decision',
                         '2026-10-20: deferred: later')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        text = (self.repo / 'tasks/items/A-1.md').read_text()
        self.assertIn('section = "Needs decision"', text)
        self.assertIn('- Owner decision: 2026-10-20: deferred: later\n', text)
        result = self.aw('tasks', 'add', '--title', 'Second', '--short', 'Second', '--goal',
                         store_fixture.FIXTURE_GOAL, '--section', 'Next', str(self.repo))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        added = result.stdout.split()[-1]
        self.assertIn('section = "Next"', (self.repo / 'tasks/items' / f'{added}.md').read_text())
        self.assertEqual(len(task_store.TaskStore.at(self.repo, self.commit_tasks()).tasks), 2)

    def test_blockers_starts_the_agent_in_the_repository(self):
        """From the TUI or the home directory, Claude Code asked to trust the whole home
        directory: the agent ran where autowork was started, not in the repository."""
        agent = self.base / 'agent'
        agent.write_text('#!/usr/bin/env bash\npwd > "$0.cwd"; printf %s "$*" > "$0.args"\n')
        agent.chmod(0o755)
        result = subprocess.run([str(AUTOWORK), 'blockers', str(self.repo)], cwd=self.base,
                                env={**self.env, 'AUTOWORK_AGENT': str(agent)}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(Path(str(agent) + '.cwd').read_text().strip(), str(self.repo.resolve()))
        self.assertEqual(Path(str(agent) + '.args').read_text(), f'/blockers {self.repo.resolve()}')

    def test_update_runs_the_configured_installer(self):
        installer = self.base / 'bin' / 'install.sh'
        installer.write_text('#!/usr/bin/env bash\necho "install.sh $*" >> "$FAKE_LOG"\n')
        installer.chmod(0o755)
        env = {**self.env, 'AUTOWORK_INSTALLER': str(installer)}
        result = subprocess.run([str(AUTOWORK), 'update', '-q', '--dry-run'], env=env,
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('install.sh update -q --dry-run', self.log.read_text())

    def test_start_refuses_a_repository_that_is_not_ready(self):
        bare = self.make_repo('bare', files=('TODO.md',))
        result = self.aw('start', str(bare))
        self.assertEqual(result.returncode, 1)
        self.assertIn('needs tasks', result.stderr)
        self.assertIn('autowork tasks prepare', result.stderr)
        subprocess.run(['git', '-C', str(self.repo), 'rm', '-r', '--cached', 'tasks'], check=True,
                       capture_output=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=T', '-c', 'user.email=t@example.invalid',
                        'commit', '-qm', 'planning only on disk'], check=True)
        result = self.aw('start', str(self.repo))
        self.assertEqual(result.returncode, 1)
        self.assertIn('commit tasks/ on main first', result.stderr)
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
        refused = self.aw('restart', '--stop-workers', 'india')  # this fixture predates safe restarts
        self.assertEqual(refused.returncode, 1, refused.stdout)
        self.assertIn('no safe-restart handshake', refused.stdout)
        self.assertNotIn('systemctl --user restart pi-autowork@india.service', self.calls())
        stopped = self.aw('restart', '--stop-workers', '--now', 'india')
        self.assertEqual(stopped.returncode, 0, stopped.stderr)
        self.assertIn('systemctl --user restart pi-autowork@india.service', self.calls())
        self.assertIn('workers paused and resume on the same attempt', stopped.stdout)

    def test_a_runner_that_does_not_reload_in_time_is_named_not_killed(self):
        self.aw('start', str(self.repo))
        self.running()  # nothing answers the signal
        self.env['PI_AUTOWORK_RELOAD_WAIT'] = '1'
        result = self.aw('restart', 'india')
        self.assertEqual(result.returncode, 1)
        self.assertIn('autowork restart --stop-workers --now india', result.stdout)
        self.assertNotIn('systemctl --user restart pi-autowork@india.service', self.calls())

    def test_restart_rejects_invalid_waits_and_now_without_stop_workers(self):
        self.aw('start', str(self.repo))
        self.running()
        invalid = self.aw('restart', '--now', 'india')
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn('--now requires --stop-workers', invalid.stderr)
        for value in ('-1', 'nan', 'inf', 'not-seconds'):
            with self.subTest(wait=value):
                self.env['PI_AUTOWORK_RESTART_WAIT'] = value
                result = self.aw('restart', '--stop-workers', 'india')
                self.assertEqual(result.returncode, 1)
                self.assertIn('PI_AUTOWORK_RESTART_WAIT', result.stdout)
        self.assertNotIn('systemctl --user restart pi-autowork@india.service', self.calls())

    def test_overlapping_safe_restarts_cannot_reuse_permission_for_the_old_runner(self):
        from unittest.mock import patch
        from pi_autowork import command
        self.aw('start', str(self.repo))
        record = self.running()
        status = record.parent / 'restart-status.json'
        status.write_text(json.dumps({'pid': 4242, 'operation': '', 'ready_for': []}))
        entered, release, done = threading.Event(), threading.Event(), threading.Event()
        restarted = []
        results = []

        def ctl(paths, *args, **kwargs):
            if args[0] == 'is-active' and entered.is_set():
                return subprocess.CompletedProcess(args, 1)  # service is deactivating during first restart
            if args[0] == 'restart':
                restarted.append(json.loads(record.read_text())['pid'])
                entered.set()
                release.wait(timeout=5)
                record.write_text(json.dumps({'pid': 4243, 'repo': str(self.repo)}))
            return subprocess.CompletedProcess(args, 0)

        def acknowledge():
            while not done.wait(0.01):
                requests = []
                for path in record.parent.glob('restart-*/request.json'):
                    try:
                        if json.loads(path.read_text())['runner_pid'] == 4242:
                            requests.append(path.parent.name)
                    except FileNotFoundError:  # a completed request was just removed
                        continue
                tmp = status.with_suffix('.tmp')
                tmp.write_text(json.dumps({'pid': 4242, 'operation': '', 'ready_for': requests}))
                tmp.replace(status)

        with patch.dict(os.environ, PI_AUTOWORK_RESTART_WAIT='5'), patch.object(command, 'systemctl', ctl):
            paths = command.env_paths(self.env)
            ack = threading.Thread(target=acknowledge)
            first = threading.Thread(target=lambda: results.append(command.restart(paths, 'india', str(self.repo), True)))
            ack.start()
            first.start()
            try:
                self.assertTrue(entered.wait(timeout=5))  # first caller holds its acknowledged request
                with patch.dict(os.environ, PI_AUTOWORK_RESTART_WAIT='0.2'):
                    second = command.restart(paths, 'india', str(self.repo), True)
                self.assertEqual(second[0], 1, second)
                self.assertEqual(restarted, [4242])  # second caller must not reach systemctl
            finally:
                release.set()
                first.join(timeout=5)
                done.set()
                ack.join(timeout=5)
        self.assertEqual(results[0][0], 0, results)
        self.assertEqual(json.loads(record.read_text())['pid'], 4243)

    def test_a_runner_from_before_reloads_is_restarted(self):
        self.aw('start', str(self.repo))
        record = self.running()
        record.write_text(json.dumps({'pid': 4242, 'started': 'now', 'repo': str(self.repo)}))
        self.assertIn('workers paused', self.aw('restart', 'india').stdout)
        self.assertIn('systemctl --user restart pi-autowork@india.service', self.calls())

    def test_a_runner_rewriting_its_record_is_reloaded_not_restarted(self):
        """TOOLSET-191-0a: restarting a runner that was re-executing found no record and
        restarted the unit, pausing its worker."""
        self.aw('start', str(self.repo))
        record = self.running()
        record.unlink()  # removed by the re-executing runner; written again two seconds later
        writer = subprocess.Popen(['sh', '-c', 'sleep 2; printf %s "$1" > "$2"', 'sh',
                                   json.dumps({'pid': 4242, 'started': 'now', 'repo': str(self.repo), 'reloads': 1}),
                                   str(record)])
        result = self.aw('restart', 'india')
        writer.wait()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Reloaded pi-autowork@india.service; 2 worker(s) kept running.', result.stdout)
        self.assertNotIn('systemctl --user restart pi-autowork@india.service', self.calls())

    def test_a_runner_that_never_writes_its_record_is_restarted(self):
        self.aw('start', str(self.repo))
        self.running().unlink()
        self.env['PI_AUTOWORK_RECORD_WAIT'] = '1'
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

    def test_ls_reports_failed_discovery_instead_of_successful_empty_fleet(self):
        probe = self.base / 'bin/systemctl'
        for body in ['#!/bin/sh\nexit 1\n', '#!/missing/interpreter\n']:
            with self.subTest(body=body.splitlines()[0]):
                probe.write_text(body)
                probe.chmod(0o755)
                result = self.aw('ls')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('runner discovery unavailable', result.stderr.lower())
                self.assertNotIn('autowork runners: none', result.stdout)
        probe.write_text('#!/bin/sh\nexit 0\n')
        probe.chmod(0o755)
        result = self.aw('ls')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('autowork runners: none', result.stdout)

    def test_ls_shows_each_runner_with_its_model_and_pause(self):
        self.assertIn('autowork runners: none', self.aw('ls').stdout)
        self.aw('start', str(self.repo))
        folder = self.state / 'k'
        folder.mkdir()
        (folder / 'runner.json').write_text(json.dumps(
            {'pid': os.getpid(), 'start_time': start_time(os.getpid()), 'repo': str(self.repo)}))
        (folder / 'status.json').write_text(json.dumps({'repo': str(self.repo), 'state': 'working', 'since': time.time() - 300,
                                                        'updated_at': time.time(), 'active_workers': 1, 'waiting': 4}))
        brief = self.aw('ls').stdout
        self.assertIn('autowork runners: 1 (1 working)', brief)
        self.assertRegex(brief, r'india\s+service\s+working [45]m\s+1 running, 4 waiting')
        self.assertIn('model openai-codex/gpt-6.1-sol', self.aw('ls', '--long').stdout)
        listed = json.loads(self.aw('ls', '--json').stdout)['runners']
        self.assertEqual([(r['name'], r['state'], r['running'], r['waiting']) for r in listed],
                         [('india', 'working', 1, 4)])
        self.aw('pause', 'india')
        self.assertRegex(self.aw('ls').stdout, r'india\s+service\s+paused\s')

    def test_run_and_status_keep_the_requested_target_despite_git_routing(self):
        other = self.make_repo('other')
        self.env.update(GIT_DIR=str(other / '.git'), GIT_WORK_TREE=str(other),
                        PI_AUTOWORK_SCRIPT=str(ROOT / 'scripts/pi-autowork.sh'),
                        PI_AUTOWORK_TOOLSET=str(ROOT), PI_BIN=str(self.base / 'bin/pi'))
        result = self.aw('run', str(self.repo))
        self.assertEqual(result.returncode, 4, result.stderr)
        self.assertIn('Repository identity mismatch', result.stderr)
        status = self.aw('status', str(self.repo))
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertIn(f'Repository: {self.repo}', status.stdout)
        self.assertIn('Repository identity mismatch', status.stdout)

    def test_status_and_fleet_keep_the_reason_a_runner_stopped_during_setup(self):
        self.env.update(PI_AUTOWORK_SCRIPT=str(ROOT / 'scripts/pi-autowork.sh'),
                        PI_AUTOWORK_TOOLSET=str(ROOT), PI_BIN=str(self.base / 'bin/pi'))
        for repo in (self.repo, self.make_repo('project with spaces')):
            with self.subTest(repo=repo):
                failed = subprocess.run([sys.executable, str(ROOT / 'pi-autowork/pi_autowork/cli.py'),
                                         '--repo', str(repo), '--workers', '17'],
                                        env=self.env, capture_output=True, text=True, timeout=30)
                self.assertEqual(failed.returncode, 4, failed.stderr)
                # Observation works with invalid settings and even without .git.
                self.env['PI_AUTOWORK_WORKERS'] = '17'
                name = subprocess.check_output(['systemd-escape', repo.name], text=True).strip()
                (self.env_dir / f'{name}.env').write_text(f'PI_AUTOWORK_REPO={repo}\n')
                (repo / '.git').rename(repo / 'saved-git')
                status = self.aw('status', name)
                self.assertEqual(status.returncode, 0, status.stderr)
                self.assertIn('--workers must be 1 to 16', status.stdout)
                fleet = json.loads(self.aw('ls', '--json').stdout)['runners']
                runner = next(row for row in fleet if row['repo'] == str(repo))
                self.assertIn('--workers must be 1 to 16', runner['blocker'])
                # The TUI consumes these helpers, not the raw blocker field.
                # A generic setup label or stopped-service action must not hide
                # the persisted reason in its headline, Needs or Blocker detail.
                view = fleet_view.Runner(**runner)
                for displayed in (fleet_view.verdict(view)[0], fleet_view.needs(view),
                                  fleet_view.blocker_parts(view)):
                    self.assertIn('--workers must be 1 to 16', displayed)

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
