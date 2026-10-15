import argparse
import json
import os
import importlib.util
from pathlib import Path
import tempfile
import time
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'bundle.py').exists(), 'Missing bundle integration')
        spec = importlib.util.spec_from_file_location('bundle_test', ROOT / 'bundle.py')
        self.bundle = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.bundle)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'SKILL.md'
        self.path.write_text('skill')
        self.commands = {'ponytail-review': {'plugin': 'ponytail', 'handler': object()}}
        self.skills = ['ponytail:ponytail', 'ponytail:ponytail-review', 'hermes-speech:configure-allmodels-speech']
        self.manager = types.SimpleNamespace(
            list_plugin_skill_metadata=lambda: [{'name': n} for n in self.skills],
            find_plugin_skill=lambda n: self.path,
        )
        self.ctx = types.SimpleNamespace(
            register_command=self.register_command,
            get_config=lambda key, default=None: default,
        )
        self.messages = []
        stubs = {
            'hermes_cli.plugins': types.SimpleNamespace(get_plugin_manager=lambda: self.manager,
                                                        get_plugin_commands=lambda: self.commands),
            'hermes_cli.commands': types.SimpleNamespace(resolve_command=lambda n: object() if n == 'help' else None),
        }
        p = patch.dict('sys.modules', stubs)
        p.start()
        self.addCleanup(p.stop)

    def register_command(self, name, handler, description='', args_hint=''):
        self.commands[name] = {'handler': handler, 'plugin': 'hermes-toolset'}

    def invoke(self, ctx, name, path, args, namespace='hermes-toolset'):
        self.messages.append((namespace, name, args))

    def test_chat_update_is_not_treated_as_inventory_filter(self):
        with patch.object(self.bundle, 'start_update', return_value='started') as start:
            self.assertEqual(self.bundle.handle_chat('update'), 'started')
            start.assert_called_once_with(check=False)
        with patch.object(self.bundle, 'start_update', return_value='checking') as start:
            self.assertEqual(self.bundle.handle_chat('update --check'), 'checking')
            start.assert_called_once_with(check=True)
        with patch.object(self.bundle, 'update_status', return_value='updated'):
            self.assertEqual(self.bundle.handle_chat('update status'), 'updated')
        self.assertIn('Usage:', self.bundle.handle_chat('update --force'))

    def test_update_cli_uses_dedicated_updater(self):
        args=argparse.Namespace(action='update', check=True, hermes_home='/tmp/home')
        with patch.object(self.bundle.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0)) as run:
            self.assertEqual(self.bundle.handle_cli(args), 0)
            self.assertIn(str(ROOT/'update_bundle.py'),run.call_args.args[0])
            self.assertIn('--check',run.call_args.args[0])

    def test_chat_update_receipt_keeps_paths_as_literal_json_not_attachments(self):
        home = Path(self.tmp.name)
        folder = home / 'maintenance/toolset-update'
        folder.mkdir(parents=True)
        receipt = {
            'status': 'incomplete',
            'error': f'Local skill conflict: {self.path}; reconcile this file',
            'detail': 'A customization contains ``` and `quoted` text',
        }
        saved = json.dumps(receipt)
        (folder / 'latest.json').write_text(saved)
        with patch.object(self.bundle, 'update_home', return_value=home):
            rendered = self.bundle.handle_chat('update status full')
            summary = self.bundle.handle_chat('update status')
        self.assertTrue(summary.startswith('```text\n') and summary.endswith('\n```'), summary)
        self.assertNotIn('`', summary[len('```text\n'):-len('\n```')])
        self.assertIn(str(self.path), summary)  # inside the fence, never a bare attachment path
        self.assertTrue(rendered.startswith('```json\n'), rendered)
        self.assertTrue(rendered.endswith('\n```'), rendered)
        payload = rendered[len('```json\n'):-len('\n```')]
        self.assertNotIn('`', payload)  # Embedded delimiters cannot expose paths.
        self.assertEqual(json.loads(payload), receipt)
        self.assertEqual((folder / 'latest.json').read_text(), saved)

    def test_new_cli_receipt_is_not_hidden_by_older_chat_request(self):
        home=Path(self.tmp.name);folder=home/'maintenance/toolset-update';folder.mkdir(parents=True)
        (folder/'request.json').write_text(json.dumps({'pid':111,'started_ns':1}))
        (folder/'latest.json').write_text(json.dumps({'pid':222,'started_ns':2,'status':'updated'}))
        with patch.object(self.bundle,'update_home',return_value=home):
            self.assertIn('updated',self.bundle.update_status())

    def test_dead_duplicate_request_does_not_hide_current_result(self):
        home=Path(self.tmp.name);folder=home/'maintenance/toolset-update';folder.mkdir(parents=True)
        (folder/'request.json').write_text(json.dumps({'pid':111,'started_ns':2}))
        (folder/'latest.json').write_text(json.dumps({'pid':222,'started_ns':1,'status':'updated'}))
        with patch.object(self.bundle,'update_home',return_value=home), patch.object(self.bundle.os,'kill',side_effect=ProcessLookupError):
            result=self.bundle.update_status()
            self.assertIn('updated',result)
            self.assertIn('did not produce',result)

    def test_status_shows_what_a_pending_gateway_restart_waits_on(self):
        home = Path(self.tmp.name); folder = home / 'maintenance/toolset-update'; folder.mkdir(parents=True)
        (folder / 'latest.json').write_text(json.dumps({'pid': 2, 'started_ns': 1, 'status': 'updated', 'gateway_restart': 'requested'}))
        drain = {'restart_pid': 9, 'seconds_left': 1525, 'waiting_on': ['chat turn agent:demo running 8m32s']}
        with patch.object(self.bundle, 'update_home', return_value=home):
            with patch.object(self.bundle, 'gateway_drain', return_value=drain):
                self.assertEqual(json.loads(self.bundle.update_status(full=True).strip('`json\n'))['gateway_restart_progress'], drain)
                summary = self.bundle.update_status()
                self.assertIn('draining (1525s left, 1 turn(s))', summary)
                self.assertIn('waiting on chat turn agent:demo running 8m32s', summary)
            self.assertIn('completed or not tracked', self.bundle.update_status(full=True))
            self.assertIn('Gateway restart: requested, done', self.bundle.update_status())

    def test_status_shows_a_deferred_restart_and_a_stopped_waiter(self):
        home = Path(self.tmp.name); folder = home / 'maintenance/toolset-update'; folder.mkdir(parents=True)
        (folder / 'latest.json').write_text(json.dumps({'pid': 2, 'started_ns': 1, 'status': 'updated', 'gateway_restart': 'deferred'}))
        waiting = {'state': 'deferred', 'waiter_pid': 9, 'chat_turns': 2}
        with patch.object(self.bundle, 'update_home', return_value=home):
            with patch.object(self.bundle, 'gateway_drain', return_value=waiting):
                self.assertEqual(json.loads(self.bundle.update_status(full=True).strip('`json\n'))['gateway_restart_progress'], waiting)
                summary = self.bundle.update_status()
                self.assertIn('Gateway restart: deferred, waiting for no chat turn in flight (2 at last check)', summary)
                self.assertNotIn('draining', summary)
            with patch.object(self.bundle, 'gateway_drain', return_value=None):
                summary = self.bundle.update_status()
                self.assertIn('waiter is not running', summary)
                self.assertNotIn(', done', summary)
        (folder / 'latest.json').write_text(json.dumps({'pid': 2, 'started_ns': 1, 'status': 'updated',
            'gateway_restart': 'deferred_expired', 'gateway_restart_action': 'Run hermes gateway restart when convenient.'}))
        with patch.object(self.bundle, 'update_home', return_value=home):
            summary = self.bundle.update_status()
        self.assertIn('Gateway restart: deferred_expired', summary)
        self.assertIn('Gateway restart action: Run hermes gateway restart when convenient.', summary)

    def test_status_finishes_a_completed_restart_and_summarizes_it(self):
        home = Path(self.tmp.name); folder = home / 'maintenance/toolset-update'; folder.mkdir(parents=True)
        (folder / 'latest.json').write_text(json.dumps({'pid': 2, 'started_ns': 1, 'status': 'updated', 'gateway_restart': 'requested'}))
        done = {'gateway_restart': 'completed', 'gateway_restart_result': {
            'gateway_pid': 4321, 'gateway_started': '2026-10-15T12:15:16', 'menus_resent': ['alpha', 'default'],
            'menus_not_seen': ['beta'], 'interrupted': ['Gateway drain timed out after 30.0s with 1 in-flight cron job(s)']}}
        with patch.object(self.bundle, 'update_home', return_value=home), \
             patch.object(self.bundle, 'gateway_drain', return_value=None), \
             patch.object(self.bundle, 'finish_restart', return_value=done) as finish:
            summary = self.bundle.update_status()
            full = json.loads(self.bundle.update_status(full=True).strip('`json\n'))
        finish.assert_called_with(home, folder)
        self.assertIn('Gateway restart: completed, new gateway PID 4321', summary)
        self.assertIn('Menus resent: alpha, default; not seen: beta', summary)
        self.assertIn('Interrupted: Gateway drain timed out after 30.0s with 1 in-flight cron job(s)', summary)
        self.assertNotIn('done', summary)
        self.assertEqual(full['gateway_restart_result']['gateway_pid'], 4321)

    def test_status_says_how_many_updates_one_restart_covers(self):
        home = Path(self.tmp.name); folder = home / 'maintenance/toolset-update'; folder.mkdir(parents=True)
        (folder / 'latest.json').write_text(json.dumps({'pid': 2, 'started_ns': 1, 'status': 'updated',
            'gateway_restart': 'pending'}))
        waiting = {'state': 'deferred', 'waiter_pid': 9, 'chat_turns': 1, 'covers': 3}
        with patch.object(self.bundle, 'update_home', return_value=home), \
             patch.object(self.bundle, 'gateway_drain', return_value=waiting):
            self.assertIn('covers 3 updates', self.bundle.update_status())
        (folder / 'latest.json').write_text(json.dumps({'pid': 2, 'started_ns': 1, 'status': 'updated',
            'gateway_restart': 'requested', 'gateway_restart_covers': 2}))
        with patch.object(self.bundle, 'update_home', return_value=home), \
             patch.object(self.bundle, 'gateway_drain', return_value=None):
            self.assertIn('covers 2 updates', self.bundle.update_status())

    def _chat_updater(self, body):
        """Point start_update at a disposable updater script; never the real one."""
        checkout = Path(self.tmp.name) / 'checkout'
        checkout.mkdir(exist_ok=True)
        (checkout / 'update_bundle.py').write_text(body)
        self.bundle.ROOT = checkout

    def _wait_exited(self, pid):
        # The gateway never waits on the child, so an exited child stays a zombie.
        stat = Path(f'/proc/{pid}/stat')
        if not stat.parent.exists():
            self.skipTest('needs /proc to observe an unreaped child')
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if stat.read_text().rsplit(')', 1)[1].split()[0] == 'Z':
                return
            time.sleep(0.05)
        self.fail('chat-started updater did not exit')

    def test_refused_chat_update_child_reports_latest_receipt_not_starting(self):
        home = Path(self.tmp.name) / 'home'
        folder = home / 'maintenance/toolset-update'
        folder.mkdir(parents=True)
        (folder / 'latest.json').write_text(json.dumps({'pid': 1, 'started_ns': 1, 'status': 'updated'}))
        # Like a lock-refused updater: exits without writing a receipt.
        self._chat_updater('raise SystemExit(1)\n')
        with patch.object(self.bundle, 'update_home', return_value=home):
            self.assertIn('requested', self.bundle.start_update())
            self._wait_exited(json.loads((folder / 'request.json').read_text())['pid'])
            result = self.bundle.update_status()
        self.assertNotIn('starting', result)
        self.assertIn('Toolset update: updated', result)
        self.assertIn('did not produce', result)

    def test_killed_chat_update_child_reports_stopped_not_running(self):
        home = Path(self.tmp.name) / 'home'
        folder = home / 'maintenance/toolset-update'
        self._chat_updater(
            'import json, os, signal, sys, time\n'
            'from pathlib import Path\n'
            'folder = Path(sys.argv[sys.argv.index("--hermes-home") + 1]) / "maintenance/toolset-update"\n'
            'receipt = {"pid": os.getpid(), "started_ns": time.time_ns(), "status": "running"}\n'
            '(folder / "latest.json").write_text(json.dumps(receipt))\n'
            'os.kill(os.getpid(), signal.SIGKILL)\n')
        with patch.object(self.bundle, 'update_home', return_value=home):
            self.assertIn('requested', self.bundle.start_update())
            pid = json.loads((folder / 'request.json').read_text())['pid']
            self._wait_exited(pid)
            self.assertEqual(json.loads((folder / 'latest.json').read_text())['pid'], pid)
            result = self.bundle.update_status()
        self.assertIn('Update process stopped without a final receipt', result)

    def test_status_summary_fits_one_chat_message(self):
        home = Path(self.tmp.name); folder = home / 'maintenance/toolset-update'; folder.mkdir(parents=True)
        names = [f'profile{i}' for i in range(10)]
        receipt = {'status': 'updated', 'pid': 1, 'started_ns': 1, 'profiles': names,
                   'sources': {f'/h/{n}/plugins/hermes-toolset': {'before': '10ef9be' + 'a' * 33, 'after': '2187e98' + 'b' * 33} for n in names},
                   'skill_files': 500, 'drift': [], 'local_edits': [{'action': 'kept_retired'}] * 3,
                   'backup': '/h/maintenance/toolset-update/x', 'settings_healed': [],
                   'activation': [{'profile': n, 'status': 'ready', 'enable_exit': 0, 'finalize_exit': 0} for n in names],
                   'chat_menus_healed': [{'profile': 'profile1', 'status': 'unreachable', 'failed': ['...5095'], 'error': 'HTTPError'},
                                         {'profile': 'profile4', 'status': 'cleared', 'chats': ['...9244']}],
                   'gateway_restart': 'requested', 'note': 'n' * 300}
        (folder / 'latest.json').write_text(json.dumps(receipt))
        with patch.object(self.bundle, 'update_home', return_value=home), \
                patch.object(self.bundle, 'gateway_drain', return_value=None):
            summary = self.bundle.handle_chat('update status')
        self.assertLess(len(summary), 600)
        for part in ('Toolset update: updated, 10 profile(s); at 2187e98 (from 10ef9be)', 'Skill files written: 500; local edits: 3 kept_retired',
                     'Chat menus: cleared profile4; unreachable profile1', 'Gateway restart: requested, done',
                     'Full receipt: /toolset update status full'):
            self.assertIn(part, summary)

    def test_running_receipt_owned_by_other_user_is_still_running(self):
        home = Path(self.tmp.name)
        folder = home / 'maintenance/toolset-update'
        folder.mkdir(parents=True)
        (folder / 'latest.json').write_text(json.dumps({'pid': 4242, 'started_ns': 1, 'status': 'running'}))
        with patch.object(self.bundle, 'update_home', return_value=home), \
                patch.object(self.bundle.os, 'kill', side_effect=PermissionError):
            result = self.bundle.update_status()
        self.assertNotIn('Cannot read update receipt', result)
        self.assertIn('Toolset update: running', result)

    def test_chat_update_accepts_symlinked_hermes_home(self):
        real = Path(self.tmp.name) / 'real-home'
        real.mkdir()
        link = Path(self.tmp.name) / 'dot-hermes'
        link.symlink_to(real, target_is_directory=True)
        self._chat_updater('raise SystemExit(0)\n')
        with patch.object(self.bundle, 'update_home', return_value=link):
            result = self.bundle.start_update()
        self.assertNotIn('refused', result)
        self.assertIn('requested', result)
        request = json.loads((real / 'maintenance/toolset-update/request.json').read_text())
        self._wait_exited(request['pid'])
        os.waitpid(request['pid'], 0)

    def test_chat_update_still_refuses_symlinked_state_directory(self):
        home = Path(self.tmp.name) / 'home'
        (home / 'maintenance').mkdir(parents=True)
        elsewhere = Path(self.tmp.name) / 'elsewhere'
        elsewhere.mkdir()
        (home / 'maintenance/toolset-update').symlink_to(elsewhere, target_is_directory=True)
        self._chat_updater('raise SystemExit(0)\n')
        with patch.object(self.bundle, 'update_home', return_value=home):
            self.assertIn('symlinked update state directory', self.bundle.start_update())
        self.assertFalse((elsewhere / 'request.json').exists())

    def test_imported_skills_get_commands_without_overwriting_native_handlers(self):
        native = self.commands['ponytail-review']['handler']
        self.bundle.register_imported_skills(self.ctx, self.invoke)
        self.assertIs(self.commands['ponytail-review']['handler'], native)
        self.commands['ponytail']['handler']('full')
        self.assertEqual(self.messages, [('ponytail', 'ponytail', 'full')])
        self.assertIn('configure-allmodels-speech', self.commands)

    def test_builtin_collision_uses_plugin_prefix(self):
        self.skills = ['ponytail:help']
        self.bundle.register_imported_skills(self.ctx, self.invoke)
        self.assertNotIn('help', self.commands)
        self.commands['ponytail-help']['handler']('details')
        self.assertEqual(self.messages, [('ponytail', 'help', 'details')])

    def test_long_imported_skill_names_have_stable_telegram_safe_alias(self):
        self.skills = ['ponytail:' + 'long-name-' * 6]
        first = self.bundle.register_imported_skills(self.ctx, self.invoke)
        name = next(iter(first))
        self.assertLessEqual(len(name), 32)
        self.assertRegex(name, r'^[a-z0-9-]+$')
        self.commands.clear()
        self.assertEqual(first, self.bundle.register_imported_skills(self.ctx, self.invoke))

    def test_unlisted_plugin_skills_are_not_exported(self):
        self.skills = ['other:secret']
        self.assertEqual(self.bundle.register_imported_skills(self.ctx, self.invoke), {})

    def test_setup_uses_complete_orchestrator_and_preserves_arguments(self):
        args = argparse.Namespace(action='setup', dry_run=True, hermes_home='/tmp/home with spaces',
                                  yes_deps=True, bundle_only=True, no_reload=True)
        with patch.object(self.bundle.subprocess, 'run', return_value=types.SimpleNamespace(returncode=7)) as run:
            self.assertEqual(self.bundle.handle_cli(args), 7)
        self.assertEqual(run.call_args.args[0], ['python3', str(ROOT / 'setup_bundle.py'),
            '--dry-run', '--yes-deps', '--bundle-only', '--no-reload', '--hermes-home', '/tmp/home with spaces'])
        self.assertNotIn('shell', run.call_args.kwargs)

    def test_setup_parser_requires_action_and_supports_doctor(self):
        parser = argparse.ArgumentParser()
        self.bundle.setup_parser(parser)
        args = parser.parse_args(['doctor', '--json'])
        self.assertEqual(args.action, 'doctor')
        self.assertTrue(args.json)

    def external_source_fixture(self):
        source=Path(self.tmp.name)/'source';(source/'plugins').mkdir(parents=True)
        (source/'plugins/defaults.json').write_bytes((ROOT/'plugins/defaults.json').read_bytes())
        (source/'plugins/PLUGINS.md').write_text('skills https://github.com/example/optional-skills all profiles\n')
        return source

    def test_missing_imports_track_partial_install_and_removed_commands(self):
        home = Path(self.tmp.name)
        source=self.external_source_fixture()
        self.bundle.record_skill_repository(home, 'https://github.com/example/optional-skills', ['alpha', 'beta'])
        with patch.object(self.bundle,'ROOT',source):
            missing, unchecked = self.bundle.missing_skill_imports(home, {'alpha', 'graphify', 'omh-plan'})
        self.assertEqual(missing, ['beta'])
        self.assertEqual(unchecked, [])

    def test_unattempted_skill_repository_is_not_reported_healthy(self):
        source=self.external_source_fixture()
        with patch.object(self.bundle,'ROOT',source):
            missing, unchecked = self.bundle.missing_skill_imports(Path(self.tmp.name), {'graphify', 'omh-plan'})
        self.assertEqual(missing, [])
        self.assertEqual(unchecked, ['https://github.com/example/optional-skills'])

    def test_retired_external_addy_inventory_does_not_require_duplicate_imports(self):
        home=Path(self.tmp.name)
        self.bundle.record_skill_repository(home,'https://github.com/addyosmani/agent-skills',['old-import'])
        missing,unchecked=self.bundle.missing_skill_imports(home,{'graphify','omh-plan'})
        self.assertNotIn('old-import',missing)
        self.assertNotIn('https://github.com/addyosmani/agent-skills',unchecked)

    def test_named_profiles_do_not_require_or_export_unlisted_plugins(self):
        self.manager.home_path = Path(self.tmp.name) / 'profiles/coder'
        self.manager.discover_and_load = lambda: None
        self.manager.list_plugins = lambda: []
        modules = {
            'hermes_cli.commands_platforms': types.SimpleNamespace(
                telegram_menu_commands=lambda **kw: ([], 0), telegram_menu_max_commands=lambda: 100),
            'agent.skill_commands': types.SimpleNamespace(get_skill_commands=lambda: {}),
        }
        with patch.dict('sys.modules', modules):
            report = self.bundle.inventory()
        self.assertNotIn('example-plugin', report['missing_plugins'])
        self.skills = ['example-plugin:example-plugin']
        self.assertEqual(self.bundle.register_imported_skills(self.ctx, self.invoke), {})
        self.assertNotIn('example-plugin', (ROOT / 'plugins/PLUGINS.md').read_text())
        self.assertNotIn('example-plugin', (ROOT / 'plugin.yaml').read_text())

    def test_optional_hindsight_is_not_part_of_bundle_inventory(self):
        self.manager.home_path = Path(self.tmp.name)
        self.manager.discover_and_load = lambda: None
        self.manager.list_plugins = lambda: [{'name': 'hindsight', 'kind': 'exclusive',
            'enabled': False, 'error': 'exclusive plugin — activate via <category>.provider config'}]
        modules = {
            'hermes_cli.commands_platforms': types.SimpleNamespace(
                telegram_menu_commands=lambda **kw: ([], 0), telegram_menu_max_commands=lambda: 100),
            'agent.skill_commands': types.SimpleNamespace(get_skill_commands=lambda: {}),
            'hermes_cli.config': types.SimpleNamespace(load_config_readonly=lambda: {'memory': {'provider': 'hindsight'}}),
            'plugins.memory': types.SimpleNamespace(load_memory_provider=lambda *a, **kw:
                types.SimpleNamespace(is_available=lambda: True)),
        }
        with patch.dict('sys.modules', modules):
            report = self.bundle.inventory()
        self.assertNotIn('hindsight', report['missing_plugins'])
        self.assertEqual(report['plugins'], [])

    def report(self):
        return {'plugins': [{'name': 'ponytail', 'version': '5.1.0', 'enabled': True,
                             'tools': 0, 'commands': 6, 'hooks': 2, 'error': None}],
                'plugin_skills': ['ponytail:ponytail', 'ponytail:ponytail-help'],
                'commands': [{'command': 'ponytail', 'telegram': 'ponytail', 'source': 'ponytail'},
                             {'command': 'docs-sync', 'telegram': 'docs_sync', 'source': 'hermes-toolset'}],
                'missing_plugins': [], 'missing_skills': ['blocked-skill'],
                'unchecked_skill_sources': [], 'telegram_menu_hidden': 12}

    def test_default_summary_reports_capabilities_and_gaps_without_command_dump(self):
        report = self.report()
        report['plugins'].insert(0, {'name': 'hermes-toolset', 'version': '0.2.0', 'enabled': True,
                                     'tools': 0, 'commands': 44, 'hooks': 0, 'error': None})
        report['plugin_skills'] += ['hermes-toolset:autowork', 'hermes-toolset:docs-sync']
        report['commands'].append({'command': 'autowork', 'telegram': 'autowork', 'source': 'hermes-toolset'})
        report['missing_plugins'] = ['hermes-speech']
        with patch.object(self.bundle, 'inventory', return_value=report), \
                patch.object(self.bundle, '_identity', return_value=('abc1234', 'work')), \
                patch.object(self.bundle, '_last_update', return_value='Last update: updated, 5 min ago, at abc1234 · /toolset update status'):
            output = self.bundle.list_commands('')
        lines = output.splitlines()
        self.assertEqual(lines[0], 'Hermes Toolset 0.2.0 (abc1234) · profile work')
        self.assertEqual(lines[1], 'Ready: /docs_sync /autowork · 2 skills, 3 commands in all')
        self.assertIn('ponytail 5.1.0: loaded — 6 commands, 2 skills, 2 hooks', output)
        self.assertIn('Needs setup: plugins hermes-speech; skills blocked-skill → hermes toolset setup', output)
        self.assertIn('Telegram menu hides 12 commands', output)
        self.assertNotIn('/docs-sync', output)
        self.assertNotIn('Counts show', output)
        self.assertLessEqual(len(lines), 8)

    def test_list_filter_shows_only_matches_and_distinct_telegram_aliases(self):
        with patch.object(self.bundle, 'inventory', return_value=self.report()):
            output = self.bundle.list_commands('list docs-sync')
            ponytail = self.bundle.list_commands('list ponytail')
        self.assertIn('/docs-sync (Telegram: /docs_sync)', output)
        self.assertNotIn('/ponytail —', output)
        self.assertNotIn('/ponytail /ponytail', ponytail)

    def test_summary_distinguishes_failed_disabled_and_missing_plugins(self):
        report = self.report()
        report['plugins'][0]['error'] = 'load failed'
        report['plugins'].append({'name': 'other', 'enabled': False})
        report['missing_plugins'] = ['absent']
        with patch.object(self.bundle, 'inventory', return_value=report):
            output = self.bundle.list_commands('')
        self.assertIn('ponytail 5.1.0: error', output)
        self.assertIn('load failed', output)
        self.assertIn('other: disabled', output)
        self.assertIn('absent', output)


if __name__ == '__main__':
    unittest.main()
