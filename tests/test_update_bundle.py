"""Offline update tests using local Git remotes, never a live Hermes home."""
import importlib.util
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.remote=self.root/'upstream'
        self.remote.mkdir();self.git(self.remote,'init','-b','main')
        self.git(self.remote,'config','user.email','fixture@example.invalid')
        self.git(self.remote,'config','user.name','Fixture')
        (self.remote/'skills/demo').mkdir(parents=True)
        (self.remote/'skills/demo/SKILL.md').write_text('old\n')
        (self.remote/'plugin.yaml').write_text('name: autowork\n')
        self.git(self.remote,'add','.');self.git(self.remote,'commit','-m','initial')
        self.repo=self.root/'checkout';self.git(self.root,'clone',str(self.remote),str(self.repo))
        self.home=self.root/'home';self.home.mkdir()
        self.profiles=[('default',self.home),('work',self.home/'profiles/work')]
        for name,home in self.profiles:
            (home/'plugins').mkdir(parents=True)
            (home/'plugins/autowork').symlink_to(self.repo)
            (home/'skills/demo').mkdir(parents=True)
            (home/'skills/demo/SKILL.md').write_text('old\n')
        spec=importlib.util.spec_from_file_location('update_under_test',ROOT/'update_bundle.py')
        self.mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.mod)
        self.setup_stub = ModuleType('setup_bundle')
        self.setup_stub.live_profiles = lambda root: self.profiles
    def git(self,path,*args):
        return subprocess.check_output(['git','-C',str(path),*args],stderr=subprocess.DEVNULL,text=True).strip()
    def advance(self):
        (self.remote/'skills/demo/SKILL.md').write_text('new\n')
        self.git(self.remote,'commit','-am','update')
    def plan(self):
        return self.mod.prepare(self.repo,self.profiles,upstream=str(self.remote))
    def test_existing_categorized_skill_is_updated_without_duplicate(self):
        for _, home in self.profiles:
            folder = home / 'skills/creative/demo'
            folder.parent.mkdir()
            (home / 'skills/demo').rename(folder)
        self.advance()
        self.mod.apply(self.plan(), self.home / 'backups')
        for _, home in self.profiles:
            self.assertEqual((home/'skills/creative/demo/SKILL.md').read_text(), 'new\n')
            self.assertFalse((home/'skills/demo').exists())

    def test_ambiguous_categorized_skills_are_preserved(self):
        original = self.home/'skills/demo/SKILL.md'
        original.unlink()
        original.parent.rmdir()
        for category in ('creative', 'custom'):
            path = self.home/'skills'/category/'demo/SKILL.md'
            path.parent.mkdir(parents=True)
            path.write_text('old\n')
        self.advance()
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            self.plan()

    def test_updates_shared_checkout_and_both_profiles(self):
        self.advance();plan=self.plan()
        self.assertEqual(len(plan['sources']),1)
        self.mod.apply(plan,self.home/'backups')
        for _,home in self.profiles:self.assertEqual((home/'skills/demo/SKILL.md').read_text(),'new\n')
        self.assertEqual(self.git(self.repo,'rev-parse','HEAD'),self.git(self.remote,'rev-parse','HEAD'))
        self.assertEqual(self.plan()['writes'],[])
    def test_already_advanced_checkout_refreshes_historical_native_copies(self):
        self.advance()
        self.git(self.repo, 'pull', '--ff-only')
        plan = self.plan()
        self.assertEqual(len(plan['writes']), 2)
        self.mod.apply(plan, self.home / 'backups')
        for _, home in self.profiles:
            self.assertEqual((home / 'skills/demo/SKILL.md').read_text(), 'new\n')

    def install_lines(self, text):
        (self.remote / 'skills/demo/SKILL.md').write_text(text)
        self.git(self.remote, 'commit', '-am', 'lines')
        self.git(self.repo, 'pull', '--ff-only')
        for _, home in self.profiles:
            (home / 'skills/demo/SKILL.md').write_text(text)

    def release(self, text):
        (self.remote / 'skills/demo/SKILL.md').write_text(text)
        self.git(self.remote, 'commit', '-am', 'release')
        # The shared checkout advances before profiles update, so old == new.
        self.git(self.repo, 'pull', '--ff-only')

    def test_retired_skill_is_removed_even_when_the_shared_checkout_already_advanced(self):
        gone = self.remote / 'skills/gone'
        (gone / 'scripts').mkdir(parents=True)
        (gone / 'SKILL.md').write_text('retired\n')
        (gone / 'scripts/helper.sh').write_text('echo helper\n')
        self.git(self.remote, 'add', '.'); self.git(self.remote, 'commit', '-m', 'add gone')
        self.git(self.repo, 'pull', '--ff-only')
        for _, home in self.profiles:
            (home / 'skills/gone/scripts').mkdir(parents=True)
            (home / 'skills/gone/SKILL.md').write_text('retired\n')
            (home / 'skills/gone/scripts/helper.sh').write_text('echo helper\n')
            (home / 'skills/gone/scripts/__pycache__').mkdir()
        edited = self.profiles[1][1] / 'skills/gone/SKILL.md'
        edited.write_text('retired\nlocal lesson\n')
        self.git(self.remote, 'rm', '-rq', 'skills/gone'); self.git(self.remote, 'commit', '-m', 'retire gone')
        self.git(self.repo, 'pull', '--ff-only')  # old == new: the deletion is only in history
        plan = self.plan()
        self.mod.apply(plan, self.root / 'backup')
        self.assertFalse((self.home / 'skills/gone').exists())
        work = self.profiles[1][1] / 'skills/gone'
        self.assertFalse(edited.exists())  # removed too; its bytes are in the backup
        self.assertFalse((work / 'scripts/helper.sh').exists())
        self.assertEqual([(e['path'], e['action']) for e in plan['local_edits']], [(str(edited), 'removed')])
        manifest = json.loads((self.root / 'backup/manifest.json').read_text())
        (saved,) = [r['backup'] for r in manifest if r['path'] == str(edited)]
        self.assertEqual((self.root / 'backup' / saved).read_text(), 'retired\nlocal lesson\n')
        again = self.plan()
        self.assertEqual((again['writes'], again['local_edits']), ([], []))

    def test_retired_name_of_a_required_external_skill_is_never_removed(self):
        graph = self.remote / 'skills/graphify'
        graph.mkdir(parents=True); (graph / 'SKILL.md').write_text('bundled once\n')
        self.git(self.remote, 'add', '.'); self.git(self.remote, 'commit', '-m', 'bundle graphify')
        self.git(self.remote, 'rm', '-rq', 'skills/graphify'); self.git(self.remote, 'commit', '-m', 'external now')
        self.git(self.repo, 'pull', '--ff-only')
        for _, home in self.profiles:
            (home / 'skills/graphify').mkdir(parents=True)
            (home / 'skills/graphify/SKILL.md').write_text('bundled once\n')
        plan = self.plan()
        self.assertEqual([w for w in plan['writes'] if 'graphify' in str(w[0])], [])
        self.assertEqual(plan['local_edits'], [])

    def assert_reset(self, local):
        """A profile's edited copy becomes the release; its bytes stay in the backup."""
        path = self.home / 'skills/demo/SKILL.md'
        path.write_text(local)
        plan = self.plan()
        self.assertIn({'profile': self.profiles[0][0], 'path': str(path), 'action': 'reset', 'base': None},
                      plan['local_edits'])
        backup = self.home / 'backups'
        self.mod.apply(plan, backup)
        release = (self.remote / 'skills/demo/SKILL.md').read_text()
        self.assertEqual(path.read_text(), release)
        self.assertEqual((self.profiles[1][1] / 'skills/demo/SKILL.md').read_text(), release)
        manifest = json.loads((backup / 'manifest.json').read_text())
        (saved,) = [r['backup'] for r in manifest if r['path'] == str(path)]
        self.assertEqual((backup / saved).read_text(), local)

    def test_an_edit_added_to_an_older_copy_is_reset_to_the_release(self):
        self.install_lines('a\nb\nc\nd\ne\n')
        self.release('A\nb\nc\nd\ne\n')
        self.assert_reset('a\nb\nc\nd\ne\nlocal lesson\n')

    def test_an_addition_over_the_current_release_is_reset(self):
        """Kept additions blocked every later release of the file (Hermes' skill review writes them)."""
        self.install_lines('a\nb\nc\n')
        self.release('a\nB\nc\n')
        self.assert_reset('a\nB\nc\nmine\n')

    def test_an_edit_of_a_release_changed_line_is_reset(self):
        self.install_lines('a\nfoo\nc\nd\ne\n')
        self.release('a\nbar\nc\nd\ne\n')
        self.assert_reset('a\nbaz\nc\nd\ne\n')

    def test_an_unedited_older_copy_is_updated_without_a_report(self):
        self.install_lines('a\nb\nc\n')
        self.release('a\nB\nc\n')
        plan = self.plan()
        self.assertEqual(plan['local_edits'], [])
        self.mod.apply(plan, self.home / 'backups')
        self.assertEqual((self.home / 'skills/demo/SKILL.md').read_text(), 'a\nB\nc\n')

    def test_history_does_not_match_other_paths_or_unreachable_branches(self):
        (self.remote / 'skills/demo/other.md').write_text('unrelated\n')
        self.git(self.remote, 'add', '.')
        self.git(self.remote, 'commit', '-m', 'other path')
        self.git(self.remote, 'checkout', '-b', 'untrusted')
        (self.remote / 'skills/demo/SKILL.md').write_text('branch-only\n')
        self.git(self.remote, 'commit', '-am', 'branch only')
        self.git(self.remote, 'checkout', 'main')
        self.git(self.repo, 'fetch', 'origin', 'untrusted:refs/heads/untrusted')
        self.advance()
        self.git(self.repo, 'pull', '--ff-only')
        for (_, home), content in zip(self.profiles, ('unrelated\n', 'branch-only\n')):
            (home / 'skills/demo/SKILL.md').write_text(content)
        # Bytes from another path or an untrusted branch are not a release of this file:
        # each copy is an edit, reset to the release and reported.
        plan = self.plan()
        self.assertEqual([e['action'] for e in plan['local_edits']], ['reset'] * len(self.profiles))
        self.mod.apply(plan, self.home / 'backups')
        release = (self.remote / 'skills/demo/SKILL.md').read_text()
        self.assertEqual([(home / 'skills/demo/SKILL.md').read_text() for _, home in self.profiles],
                         [release] * len(self.profiles))

    def test_historical_lookup_is_cached_per_checkout_and_path(self):
        self.advance()
        self.git(self.repo, 'pull', '--ff-only')
        with patch.object(self.mod, 'git', wraps=self.mod.git) as calls:
            self.plan()
        logs = [call for call in calls.call_args_list if call.args[1] == 'log']
        history = [call for call in logs if '--diff-filter=D' not in call.args]
        self.assertEqual(len(history), 1)
        self.assertIn('-100', history[0].args)
        # One retired-path lookup per checkout, shared by both profiles.
        self.assertEqual(len(logs) - len(history), 1)

    def test_older_copy_refreshes_when_checkout_and_upstream_also_differ(self):
        self.advance()
        self.git(self.repo, 'pull', '--ff-only')
        (self.remote / 'skills/demo/SKILL.md').write_text('latest\n')
        self.git(self.remote, 'commit', '-am', 'another update')
        self.mod.apply(self.plan(), self.home / 'backups')
        for _, home in self.profiles:
            self.assertEqual((home / 'skills/demo/SKILL.md').read_text(), 'latest\n')

    def test_check_and_update_report_local_edits_and_still_update(self):
        self.install_lines('a\nb\nc\nd\ne\n')
        path = self.home / 'skills/demo/SKILL.md'
        path.write_text('a\nb\nc\nd\ne\ncustom\n')
        self.release('A\nb\nc\nd\ne\n')
        prepare = self.mod.prepare
        for check, status in ((True, 'update_available'), (False, 'updated')):
            with self.subTest(check=check):
                args = ['--hermes-home', str(self.home)] + (['--check'] if check else [])
                with patch.object(self.mod, 'prepare', side_effect=lambda *_: prepare(self.repo, self.profiles, upstream=str(self.remote))), \
                     patch.dict('sys.modules', {'setup_bundle': self.setup_stub}), \
                     patch.object(self.mod, 'finalize_profiles', side_effect=lambda s, r, profiles, **_: [{'profile': n, 'status': 'ready'} for n, _ in profiles]), \
                     patch.object(self.mod, 'gateway_running', return_value=False), \
                     contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(self.mod.main(args), 0)
                receipt = json.loads((self.home / 'maintenance/toolset-update/latest.json').read_text())
                self.assertEqual(receipt['status'], status)
                self.assertEqual([(e['path'], e['action']) for e in receipt['local_edits']], [(str(path), 'reset')])
        self.assertEqual(path.read_text(), 'A\nb\nc\nd\ne\n')

    def test_a_second_update_changes_nothing(self):
        """Idempotent: once a release is in place, rerunning writes, reports and restarts nothing."""
        self.install_lines('a\nb\nc\n')
        (self.home / 'skills/demo/SKILL.md').write_text('a\nb\nc\nedited\n')
        self.release('a\nB\nc\n')
        prepare = self.mod.prepare
        receipts = []
        for _ in range(2):
            with patch.object(self.mod, 'prepare', side_effect=lambda *_: prepare(self.repo, self.profiles, upstream=str(self.remote))), \
                 patch.dict('sys.modules', {'setup_bundle': self.setup_stub}), \
                 patch.object(self.mod, 'finalize_profiles', side_effect=lambda s, r, profiles, **_: [{'profile': n, 'status': 'ready'} for n, _ in profiles]), \
                 patch.object(self.mod, 'heal_chat_menus', return_value=[]), \
                 patch.object(self.mod, 'gateway_running', return_value=False), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(self.mod.main(['--hermes-home', str(self.home)]), 0)
            receipts.append(json.loads((self.home / 'maintenance/toolset-update/latest.json').read_text()))
        first, second = receipts
        self.assertEqual(first['status'], 'updated')
        self.assertEqual([e['action'] for e in first['local_edits']], ['reset'])
        self.assertEqual((second['status'], second['skill_files'], second['local_edits'], second['gateway_restart']),
                         ('up_to_date', 0, [], 'not_needed'))
        self.assertNotIn('backup', second)
        backups = [p for p in (self.home / 'maintenance/toolset-update').iterdir() if p.is_dir() and p.name[:1].isdigit()]
        self.assertEqual(len(backups), 1)  # only the first run wrote, so only it left a backup

    def test_release_refreshes_hosts_once_without_failing_the_hermes_update(self):
        log = self.root / 'host-calls'
        (self.remote / 'install.sh').write_text(
            '#!/bin/bash\n'
            f'printf "%s\\n" "$*" >> "{log}"\n'
            'test "$*" = "--full --skip hermes,pi -q" || exit 9\n'
            'read -r answer && exit 8\n'  # background updates cannot prompt
            'printf \'%s\\n\' \'{"item":"autowork","status":"installed","exit":0}\' '
            '\'{"item":"tx","status":"installed","exit":0}\' '
            '\'{"item":"claude","status":"failed","exit":7}\' '
            '\'{"item":"codex","status":"skipped","exit":null}\' > "$AUTOWORK_INSTALL_REPORT"\n'
            'exit 1\n')
        self.git(self.remote, 'add', '.'); self.git(self.remote, 'commit', '-m', 'installer')
        prepare = self.mod.prepare
        receipts = []
        with patch.object(self.mod, 'prepare', side_effect=lambda *_: prepare(self.repo, self.profiles, upstream=str(self.remote))), \
             patch.dict('sys.modules', {'setup_bundle': self.setup_stub}), \
             patch.object(self.mod, 'finalize_profiles', return_value=[{'status': 'ready'}]), \
             patch.object(self.mod, 'heal_chat_menus', return_value=[]), \
             patch.object(self.mod, 'gateway_running', return_value=False), \
             contextlib.redirect_stdout(io.StringIO()):
            for extra in (['--check'], [], []):
                self.assertEqual(self.mod.main(['--hermes-home', str(self.home), *extra]), 0)
                receipts.append(json.loads((self.home / 'maintenance/toolset-update/latest.json').read_text()))
                self.assertEqual(log.exists(), len(receipts) > 1)
        self.assertEqual(log.read_text().splitlines(), ['--full --skip hermes,pi -q'])
        self.assertEqual([r['status'] for r in receipts], ['update_available', 'updated', 'up_to_date'])
        self.assertEqual(receipts[1]['hosts'], [
            {'item': 'autowork', 'status': 'installed', 'exit': 0},
            {'item': 'tx', 'status': 'installed', 'exit': 0},
            {'item': 'claude', 'status': 'failed', 'exit': 7},
            {'item': 'codex', 'status': 'skipped', 'exit': None}])
        self.assertNotIn('hosts', receipts[0])
        self.assertNotIn('hosts', receipts[2])

    def test_unavailable_or_unreported_host_installs_stay_best_effort(self):
        installer = self.repo / 'install.sh'
        for body, status, code in (
            (None, 'unavailable', None),
            ('printf "\\377" > "$AUTOWORK_INSTALL_REPORT"\n', 'unreported', 0),
            ('exit 6\n', 'failed', 6),
        ):
            with self.subTest(status=status):
                if body is not None:
                    installer.write_text('#!/bin/bash\n' + body)
                self.assertEqual(self.mod.refresh_hosts(self.repo), [
                    {'item': item, 'status': status, 'exit': code}
                    for item in ('autowork', 'tx', 'claude', 'codex')])

    def test_host_refresh_timeout_keeps_completed_items_and_stops_descendants(self):
        import time
        child = self.root / 'late-write'
        (self.repo / 'install.sh').write_text(
            '#!/bin/bash\n'
            'echo \'{"item":"autowork","status":"installed","exit":0}\' > "$AUTOWORK_INSTALL_REPORT"\n'
            f'(sleep 0.5; touch "{child}") &\nwait\n')
        with patch.object(self.mod, 'HOST_REFRESH_TIMEOUT_S', 0.1):
            rows = self.mod.refresh_hosts(self.repo)
        self.assertEqual(rows, [
            {'item': 'autowork', 'status': 'installed', 'exit': 0},
            {'item': 'tx', 'status': 'timeout', 'exit': None},
            {'item': 'claude', 'status': 'timeout', 'exit': None},
            {'item': 'codex', 'status': 'timeout', 'exit': None}])
        time.sleep(0.6)
        self.assertFalse(child.exists())

    def test_update_heals_profile_settings_and_requests_one_graceful_gateway_restart(self):
        self.advance()
        self.git(self.repo, 'pull', '--ff-only')
        prepare = self.mod.prepare
        stale = self.profiles[0][1] / 'config.yaml'
        stale.write_text('platforms: {telegram: {extra: {command_menu: {priority: [autoresearch]}}}}\n')
        def activate(source, root, profiles, **_):
            stale.write_text('platforms: {telegram: {extra: {command_menu: {priority: [autowork]}}}}\n')
            return [{'profile': name, 'status': 'ready'} for name, _ in profiles]
        for running, expected in ((True, 'requested'), (False, 'not_running')):
            with self.subTest(running=running), \
                 patch.object(self.mod, 'prepare', side_effect=lambda *_: prepare(self.repo, self.profiles, upstream=str(self.remote))), \
                 patch.dict('sys.modules', {'setup_bundle': self.setup_stub}), \
                 patch.object(self.mod, 'finalize_profiles', side_effect=activate), \
                 patch.object(self.mod, 'gateway_running', return_value=running), \
                 patch.object(self.mod, 'chat_turns', return_value=0), \
                 patch.object(self.mod, 'request_gateway_restart', return_value=4242) as restart, \
                 contextlib.redirect_stdout(io.StringIO()):
                stale.write_text('platforms: {telegram: {extra: {command_menu: {priority: [autoresearch]}}}}\n')
                self.assertEqual(self.mod.main(['--hermes-home', str(self.home)]), 0)
                receipt = json.loads((self.home / 'maintenance/toolset-update/latest.json').read_text())
                self.assertEqual(receipt['settings_healed'], [self.profiles[0][0]])
                self.assertEqual(receipt['gateway_restart'], expected)
                self.assertEqual(receipt['chat_menus_healed'], [])
                self.assertEqual(restart.call_count, int(running))

    def test_chat_menu_heal_is_per_bot_masked_and_never_fatal(self):
        sys.path.insert(0, str(ROOT)); self.addCleanup(sys.path.remove, str(ROOT))
        work = self.profiles[1][1]
        (self.home / '.env').write_text('TELEGRAM_BOT_TOKEN="t1"\nTELEGRAM_ALLOWED_USERS=123456789\n')
        (work / '.env').write_text('export TELEGRAM_BOT_TOKEN=t1\nTELEGRAM_ALLOWED_USERS=123456789\n')
        menus = {('t1', 123456789): ['autogoal']}
        def call(token, method, scope):
            if method == 'deleteMyCommands':
                return menus.pop((token, scope['chat_id'])) is not None
            return [{'command': c} for c in menus.get((token, scope['chat_id']), [])]
        self.assertEqual(self.mod.heal_chat_menus(self.profiles, call),
                         [{'profile': 'default', 'status': 'cleared', 'chats': ['...6789']}])
        self.assertEqual(self.mod.heal_chat_menus(self.profiles, call), [])
        def offline(*_, **__): raise OSError('offline')
        self.assertEqual(self.mod.heal_chat_menus(self.profiles, offline),
                         [{'profile': 'default', 'status': 'unreachable', 'error': 'OSError'}])

    def test_noop_update_does_not_restart_the_gateway(self):
        self.advance()
        self.git(self.repo, 'pull', '--ff-only')
        prepare = self.mod.prepare
        receipts = []
        with patch.object(self.mod, 'prepare', side_effect=lambda *_: prepare(self.repo, self.profiles, upstream=str(self.remote))), \
             patch.dict('sys.modules', {'setup_bundle': self.setup_stub}), \
             patch.object(self.mod, 'finalize_profiles', side_effect=lambda s, r, profiles, **_: [{'profile': n, 'status': 'ready'} for n, _ in profiles]), \
             patch.object(self.mod, 'gateway_running', return_value=True), \
             patch.object(self.mod, 'chat_turns', return_value=0), \
             patch.object(self.mod, 'request_gateway_restart', return_value=4242) as restart, \
             contextlib.redirect_stdout(io.StringIO()):
            for _ in range(2):
                self.assertEqual(self.mod.main(['--hermes-home', str(self.home)]), 0)
                receipts.append(json.loads((self.home / 'maintenance/toolset-update/latest.json').read_text()))
        self.assertEqual([r['status'] for r in receipts], ['updated', 'up_to_date'])
        self.assertEqual([r['gateway_restart'] for r in receipts], ['requested', 'not_needed'])
        self.assertEqual(restart.call_count, 1)

    def test_draining_restart_is_reported_and_not_requested_again(self):
        self.advance()
        self.git(self.repo, 'pull', '--ff-only')
        prepare = self.mod.prepare
        state = self.home / 'maintenance/toolset-update'
        self.assertIsNone(self.mod.gateway_drain(state))
        drain = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)', 'gateway', 'restart'])
        self.addCleanup(drain.wait)
        self.addCleanup(drain.kill)
        def spawn(root, log):
            log.write_text('⏳ User service restarting gracefully (PID 7) — waiting up to 1885s...\n'
                           '  ⏳ still draining — 1525s left before the forced restart\n'
                           '     waiting on 1 active work unit(s):\n'
                           '       • chat turn agent:demo running 8m32s [model m]\n'
                           '     finish or kill the work above to release the drain now\n')
            return drain.pid
        with patch.object(self.mod, 'prepare', side_effect=lambda *_: prepare(self.repo, self.profiles, upstream=str(self.remote))), \
             patch.dict('sys.modules', {'setup_bundle': self.setup_stub}), \
             patch.object(self.mod, 'finalize_profiles', side_effect=lambda s, r, profiles, **_: [{'profile': n, 'status': 'ready'} for n, _ in profiles]), \
             patch.object(self.mod, 'gateway_running', return_value=True), \
             patch.object(self.mod, 'chat_turns', return_value=0), \
             patch.object(self.mod, 'request_gateway_restart', side_effect=spawn) as restart, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.mod.main(['--hermes-home', str(self.home)]), 0)
            self.assertEqual(json.loads((state / 'latest.json').read_text())['gateway_restart'], 'requested')
            self.assertEqual(self.mod.gateway_drain(state)['waiting_on'], ['chat turn agent:demo running 8m32s [model m]'])
            self.assertEqual(self.mod.gateway_drain(state)['seconds_left'], 1525)
            (self.remote / 'skills/demo/SKILL.md').write_text('newer\n')
            self.git(self.remote, 'commit', '-am', 'second update')
            self.git(self.repo, 'pull', '--ff-only')
            self.assertEqual(self.mod.main(['--hermes-home', str(self.home)]), 0)
            self.assertEqual(json.loads((state / 'latest.json').read_text())['gateway_restart'], 'pending')
            self.assertEqual(restart.call_count, 1)
            drain.kill()
            drain.wait()
            self.assertIsNone(self.mod.gateway_drain(state))

    def test_check_reports_stale_copies_without_applying_them(self):
        self.advance()
        self.git(self.repo, 'pull', '--ff-only')
        prepare = self.mod.prepare
        with patch.object(self.mod, 'prepare', side_effect=lambda *_: prepare(self.repo, self.profiles, upstream=str(self.remote))), \
             patch.dict('sys.modules', {'setup_bundle': self.setup_stub}), \
             patch.object(self.mod, 'finalize_profiles') as finalize, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.mod.main(['--hermes-home', str(self.home), '--check']), 0)
        receipt = json.loads((self.home / 'maintenance/toolset-update/latest.json').read_text())
        self.assertEqual(receipt['status'], 'update_available')
        self.assertEqual(receipt['skill_files'], 2)
        finalize.assert_not_called()
        for _, home in self.profiles:
            self.assertEqual((home / 'skills/demo/SKILL.md').read_text(), 'old\n')

    def test_new_pinned_engineering_tree_reaches_every_profile(self):
        payloads = {
            'SKILL.md': 'Hermes adapter\n',
            'UPSTREAM.json': '{"revision":"reviewed-pin"}\n',
            'upstream/skills/planning/PROTOCOL.md': 'Plan a bounded task\n',
            'upstream/references/checklist.md': 'Verify the task\n',
            'upstream/LICENSE': 'MIT\n',
        }
        for relative, content in payloads.items():
            path = self.remote / 'skills/engineering' / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        self.git(self.remote, 'add', '.')
        self.git(self.remote, 'commit', '-m', 'reviewed engineering snapshot')
        self.mod.apply(self.plan(), self.home / 'backups')
        for _, home in self.profiles:
            for relative, content in payloads.items():
                self.assertEqual((home / 'skills/engineering' / relative).read_text(), content)
        self.assertEqual(self.plan()['writes'], [])

    def test_a_shallow_plugin_clone_is_deepened_and_updated(self):
        """A pinned Hermes install is a shallow clone, and its fast-forward check failed."""
        self.git(self.remote, 'commit', '--allow-empty', '-m', 'second')
        shallow = self.root / 'shallow'
        subprocess.check_output(['git', 'clone', '-q', '--depth', '1', self.remote.as_uri(), str(shallow)],
                                stderr=subprocess.DEVNULL)
        link = self.profiles[1][1] / 'plugins/autowork'
        link.unlink(); link.symlink_to(shallow)
        self.advance()
        plan = self.plan()
        self.assertEqual(self.git(shallow, 'rev-parse', '--is-shallow-repository'), 'false')
        self.mod.apply(plan, self.home / 'backups')
        self.assertEqual((shallow / 'skills/demo/SKILL.md').read_text(), 'new\n')

    def test_an_edited_copy_in_the_last_profile_is_reset_too(self):
        self.advance();p=self.profiles[-1][1]/'skills/demo/SKILL.md';p.write_text('custom\n')
        plan=self.plan();self.mod.apply(plan,self.home/'backups')
        self.assertEqual(p.read_text(),'new\n')
        self.assertEqual((self.home/'skills/demo/SKILL.md').read_text(),'new\n')
    def test_upstream_deletion_removes_an_edited_copy_too(self):
        p=self.remote/'skills/demo/SKILL.md';p.unlink()
        self.git(self.remote,'commit','-am','remove')
        (self.home/'skills/demo/SKILL.md').write_text('custom\n')
        plan=self.plan();self.mod.apply(plan,self.home/'backups')
        self.assertFalse((self.home/'skills/demo/SKILL.md').exists())
        self.assertIn('removed',[e['action'] for e in plan['local_edits']])

    def test_local_commit_ahead_is_not_discarded(self):
        self.git(self.repo,'config','user.email','fixture@example.invalid')
        self.git(self.repo,'config','user.name','Fixture')
        (self.repo/'local.txt').write_text('local')
        self.git(self.repo,'add','.');self.git(self.repo,'commit','-m','local')
        before=self.git(self.repo,'rev-parse','HEAD')
        with self.assertRaises(ValueError):self.plan()
        self.assertEqual(before,self.git(self.repo,'rev-parse','HEAD'))

    def test_missing_profile_plugin_uses_source_and_installs_skill_files(self):
        home=self.root/'fresh';home.mkdir()
        self.profiles.append(('fresh',home));self.advance()
        plan=self.plan();self.mod.apply(plan,self.home/'backups')
        self.assertEqual((home/'skills/demo/SKILL.md').read_text(),'new\n')

    def test_update_preserves_executable_permission(self):
        (self.home/'skills/demo/SKILL.md').chmod(0o755)
        self.advance();self.mod.apply(self.plan(),self.home/'backups')
        self.assertEqual((self.home/'skills/demo/SKILL.md').stat().st_mode & 0o777,0o755)

    def test_interrupted_file_publication_retains_merge_base_for_retry(self):
        self.advance();before=self.git(self.repo,'rev-parse','HEAD');plan=self.plan()
        original=Path.replace;count=0
        def fail_second(path,target):
            nonlocal count
            count+=1
            if count==2:raise OSError('interrupted write')
            return original(path,target)
        with patch.object(Path,'replace',fail_second):
            with self.assertRaises(OSError):self.mod.apply(plan,self.home/'backups')
        self.assertEqual(self.git(self.repo,'rev-parse','HEAD'),before)
        retry=self.plan();self.assertTrue(retry['writes'])
        self.mod.apply(retry,self.home/'retry-backups')
        for _,home in self.profiles:self.assertEqual((home/'skills/demo/SKILL.md').read_text(),'new\n')

    def test_separate_checkouts_are_finalized_per_profile(self):
        with patch.object(self.mod.subprocess,'run',return_value=type('Result',(),{'returncode':0})()) as run:
            results=self.mod.finalize_profiles(self.repo,self.home,self.profiles)
        self.assertTrue(all(r['status']=='ready' for r in results))
        commands=[c.args[0] for c in run.call_args_list]
        self.assertEqual(sum('finalize' in c for c in commands),2)
        self.assertFalse(any(any('setup_bundle.py' in a for a in c) for c in commands))

    def test_a_profile_left_incomplete_is_finalized_again_after_each_delay(self):
        """A just-restarted gateway wires its commands a little after it serves."""
        exits = iter([0, 0, 0, 1, 1, 0])  # enable/finalize per profile, then two retries of the second
        result = lambda *a, **k: type('Result', (), {'returncode': next(exits)})()
        with patch.object(self.mod.subprocess, 'run', side_effect=result) as run, \
             patch.object(self.mod.time, 'sleep') as sleep:
            rows = self.mod.finalize_profiles(self.repo, self.home, self.profiles, retries=(15, 30, 60))
        self.assertEqual([r['status'] for r in rows], ['ready', 'ready'])
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [15, 30])
        self.assertEqual(sum('finalize' in c.args[0] for c in run.call_args_list), 4)

    def test_an_update_between_gateways_waits_for_the_new_one(self):
        folder = self.home / 'maintenance/toolset-update'; folder.mkdir(parents=True, exist_ok=True)
        states = iter(['starting', 'starting', 'running'])
        with patch.object(self.mod, 'pending_restart', return_value={'mode': 'requested'}), \
             patch.object(self.mod, 'gateway_state', side_effect=lambda r: next(states)), \
             patch.object(self.mod, 'gateway_running', return_value=True), \
             patch.object(self.mod.time, 'sleep') as sleep:
            self.assertTrue(self.mod.wait_for_gateway(self.home, folder))
        self.assertEqual(sleep.call_count, 2)

    def test_a_draining_or_deferred_restart_is_not_waited_for(self):
        folder = self.home / 'maintenance/toolset-update'; folder.mkdir(parents=True, exist_ok=True)
        for record, state in (({'mode': 'requested'}, 'draining'), ({'mode': 'deferred'}, 'starting'), (None, 'starting')):
            with self.subTest(record=record, state=state), \
                 patch.object(self.mod, 'pending_restart', return_value=record), \
                 patch.object(self.mod, 'gateway_state', return_value=state), \
                 patch.object(self.mod, 'gateway_running', return_value=True), \
                 patch.object(self.mod.time, 'sleep') as sleep:
                self.assertFalse(self.mod.wait_for_gateway(self.home, folder))
                sleep.assert_not_called()

    def test_upstream_executable_only_change_updates_native_mode(self):
        (self.remote/'skills/demo/SKILL.md').chmod(0o755)
        self.git(self.remote,'commit','-am','executable')
        plan=self.plan();self.assertTrue(plan['writes'])
        self.mod.apply(plan,self.home/'backups')
        self.assertTrue((self.home/'skills/demo/SKILL.md').stat().st_mode & 0o111)

    def test_dirty_checkout_is_preserved(self):
        self.advance();(self.repo/'plugin.yaml').write_text('local work\n')
        with self.assertRaisesRegex(ValueError,'local changes'):self.plan()
    def test_skill_symlink_is_refused(self):
        self.advance();p=self.home/'skills/demo/SKILL.md';p.unlink();p.symlink_to(self.remote/'plugin.yaml')
        with self.assertRaisesRegex(ValueError,'symlink'):self.plan()
    def test_changed_destination_after_preflight_is_preserved(self):
        self.advance();plan=self.plan();p=self.home/'skills/demo/SKILL.md';p.write_text('new user change\n')
        with self.assertRaisesRegex(ValueError,'changed since'):self.mod.apply(plan,self.home/'backups')
        self.assertEqual(p.read_text(),'new user change\n')


class ScopedUpdateTests(unittest.TestCase):
    """Real Git and file publication; the native installer is the external boundary."""
    git = UpdateTests.git
    advance = UpdateTests.advance

    def setUp(self):
        UpdateTests.setUp(self)
        self.enterContext(patch.object(sys, 'path', [str(ROOT), *sys.path]))
        self.advance()
        self.revision = self.git(self.remote, 'rev-parse', 'HEAD')
        self.calls = []
        self.native = patch.object(self.mod, 'native_call', self.fake_native, create=True)
        self.native.start(); self.addCleanup(self.native.stop)

    def fake_native(self, action, home, stage, revision, python):
        if action == 'inventory':
            raise ValueError('Kanban lookup is forbidden during deployment')
        self.calls.append((action, str(home)))
        if action == 'install':
            self.git(home, 'clone', str(stage), str(home/'plugins/autowork'))
        return {'commands': ['autowork']} if action == 'verify' else {'admitted': True}

    def deploy(self, names=('default',), **kwargs):
        return self.mod.scoped_update(self.home, self.remote, self.revision, names, 'python3', **kwargs)

    def test_scoped_api_exists(self):
        self.assertTrue(callable(getattr(self.mod, 'scoped_update', None)), 'scoped deployment is missing')

    def test_selected_link_replaced_without_shared_source_or_unselected_writes(self):
        result = self.deploy()
        self.assertEqual(result['status'], 'updated')
        self.assertEqual((self.home/'skills/demo/SKILL.md').read_text(), 'new\n')
        self.assertFalse((self.home/'plugins/autowork').is_symlink())
        self.assertEqual((self.repo/'skills/demo/SKILL.md').read_text(), 'old\n')
        self.assertEqual((self.profiles[1][1]/'skills/demo/SKILL.md').read_text(), 'old\n')
        self.assertTrue((self.profiles[1][1]/'plugins/autowork').is_symlink())
        self.assertEqual(self.git(self.remote, 'rev-parse', 'HEAD'), self.revision)
        self.assertTrue(result['profiles']['default']['installed_hashes'])
        self.assertEqual((Path(result['backup'])/'default/original-source/skills/demo/SKILL.md').read_text(), 'old\n')

    def test_unchanged_retry_is_noop_with_original_backup(self):
        first = self.deploy(); self.calls.clear()
        second = self.deploy()
        self.assertEqual(second['status'], 'up_to_date')
        self.assertEqual(first['backup'], second['backup'])
        self.assertEqual(self.calls, [])

    def test_scan_refusal_leaves_plugin_skills_settings_and_schedules_intact(self):
        config = self.home/'config.yaml'; config.write_text('model: unchanged\n')
        def refuse(action, *args):
            if action == 'scan': raise ValueError('native scanner caution requires approval')
            return self.fake_native(action, *args)
        with patch.object(self.mod, 'native_call', refuse):
            result = self.deploy()
        self.assertEqual(result['status'], 'incomplete')
        self.assertIn('scanner', result['profiles']['default']['error'])
        self.assertTrue((self.home/'plugins/autowork').is_symlink())
        self.assertEqual((self.home/'skills/demo/SKILL.md').read_text(), 'old\n')
        self.assertEqual(config.read_text(), 'model: unchanged\n')

    def test_dirty_source_and_wrong_reviewed_revision_refuse(self):
        (self.remote/'plugin.yaml').write_text('local change')
        with self.assertRaisesRegex(ValueError, 'source'):
            self.deploy()
        self.assertFalse((self.home/'maintenance/toolset-update/scoped.json').exists())

    def test_profile_drift_preserved_while_independent_profile_updates(self):
        (self.home/'skills/demo/SKILL.md').write_text('customization\n')
        (self.profiles[1][1]/'config.yaml').write_text('{}\n')
        result = self.deploy(('default', 'work'))
        self.assertEqual(result['profiles']['default']['status'], 'deferred')
        self.assertEqual(result['profiles']['work']['status'], 'ready')
        self.assertEqual((self.home/'skills/demo/SKILL.md').read_text(), 'customization\n')

    def board(self, *, named=False, assignee='work', status='running', run_profile=None):
        import sqlite3
        path = self.root / ('canonical-boards/kanban/boards/named/kanban.db' if named else 'canonical-boards/kanban.db')
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as db:
            db.execute('create table tasks (id text, status text, assignee text, current_run_id integer, worker_pid integer)')
            db.execute('create table task_runs (id integer, task_id text, profile text, status text, ended_at integer, worker_pid integer)')
            db.execute('insert into tasks values (?, ?, ?, ?, ?)', ('card', status, assignee, 7 if run_profile else None, None))
            if run_profile:
                db.execute('insert into task_runs values (?, ?, ?, ?, ?, ?)', (7, 'card', run_profile, 'running', None, 424242))
        (self.profiles[1][1]/'config.yaml').write_text('{}\n')
        return path

    def assert_historical_state_ignored(self, path=None):
        before = path.read_bytes() if path else None
        with patch('sqlite3.connect', side_effect=AssertionError('native database access is forbidden')):
            result = self.deploy(('default', 'work'))
        self.assertEqual(result['status'], 'updated', result['profiles'])
        for _, home in self.profiles:
            self.assertFalse((home/'plugins/autowork').is_symlink())
            self.assertEqual((home/'skills/demo/SKILL.md').read_text(), 'new\n')
        if path:
            self.assertEqual(path.read_bytes(), before)

    def test_absent_board_and_historical_handoff_do_not_veto_deployment(self):
        (self.profiles[1][1]/'config.yaml').write_text('{}\n')
        journal = self.home/'autowork'; journal.mkdir()
        handoff = journal/'goal-handoff.json'; handoff.write_text('malformed old receipt')
        self.assert_historical_state_ignored(handoff)
        self.assertFalse((self.root/'canonical-boards').exists())

    def test_blocked_historical_card_does_not_veto_deployment(self):
        self.assert_historical_state_ignored(self.board(status='blocked'))

    def test_done_historical_card_does_not_veto_deployment(self):
        self.assert_historical_state_ignored(self.board(status='done'))

    def test_paused_historical_card_does_not_veto_deployment(self):
        self.assert_historical_state_ignored(self.board(status='paused'))

    def test_unknown_historical_owner_does_not_veto_deployment(self):
        self.assert_historical_state_ignored(self.board(assignee=None))

    def test_mismatched_historical_run_does_not_veto_deployment(self):
        import sqlite3
        path = self.board(named=True, assignee='reviewer', run_profile='work')
        with sqlite3.connect(path) as db:
            db.execute("update task_runs set task_id = 'different-card'")
        self.assert_historical_state_ignored(path)

    def test_orphan_historical_run_does_not_veto_deployment(self):
        import sqlite3
        path = self.board(assignee='reviewer', status='done', run_profile='work')
        with sqlite3.connect(path) as db:
            db.execute('update tasks set current_run_id = null')
        self.assert_historical_state_ignored(path)

    def test_malformed_historical_database_does_not_veto_deployment(self):
        (self.profiles[1][1]/'config.yaml').write_text('{}\n')
        path = self.root/'canonical-boards/kanban.db'; path.parent.mkdir()
        path.write_text('not sqlite')
        self.assert_historical_state_ignored(path)

    def test_interruption_after_native_install_resumes_same_backup(self):
        def interrupt(action, *args):
            if action == 'verify': raise OSError('interrupted verification')
            return self.fake_native(action, *args)
        with patch.object(self.mod, 'native_call', interrupt): first = self.deploy()
        self.assertEqual(first['status'], 'incomplete')
        self.calls.clear()
        second = self.deploy()
        self.assertEqual(second['status'], 'updated')
        self.assertEqual(first['backup'], second['backup'])
        self.assertNotIn('install', [a for a, _ in self.calls])

    def test_source_race_during_scan_prevents_publication(self):
        def race(action, *args):
            if action == 'scan': (self.remote/'plugin.yaml').write_text('raced source')
            return self.fake_native(action, *args)
        with patch.object(self.mod, 'native_call', race): result = self.deploy()
        self.assertEqual(result['status'], 'incomplete')
        self.assertTrue((self.home/'plugins/autowork').is_symlink())

    def test_destination_race_during_scan_is_not_overwritten(self):
        path = self.home/'skills/demo/SKILL.md'
        def race(action, *args):
            if action == 'scan': path.write_text('concurrent change')
            return self.fake_native(action, *args)
        with patch.object(self.mod, 'native_call', race): result = self.deploy()
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(path.read_text(), 'concurrent change')
        self.assertTrue((self.home/'plugins/autowork').is_symlink())

    def test_killed_after_slot_move_resumes_original_backup(self):
        class Killed(BaseException): pass
        def kill(action, *args):
            if action == 'install': raise Killed()
            return self.fake_native(action, *args)
        with patch.object(self.mod, 'native_call', kill), self.assertRaises(Killed): self.deploy()
        saved = json.loads((self.home/'maintenance/toolset-update/scoped.json').read_text())
        self.assertFalse((self.home/'plugins/autowork').exists())
        result = self.deploy()
        self.assertEqual(result['status'], 'updated')
        self.assertEqual(result['backup'], saved['backup'])
        self.assertEqual((Path(saved['backup'])/'default/file-0').read_text(), 'old\n')

    def test_slot_move_intent_before_rename_resumes_directory_install(self):
        import shutil
        slot = self.home/'plugins/autowork'
        slot.unlink(); shutil.copytree(self.repo, slot)
        original = Path.rename
        class Killed(BaseException): pass
        def kill(path, target):
            if path == slot: raise Killed()
            return original(path, target)
        with patch.object(Path, 'rename', kill), self.assertRaises(Killed): self.deploy()
        result = self.deploy()
        self.assertEqual(result['status'], 'updated')
        self.assertEqual((slot/'skills/demo/SKILL.md').read_text(), 'new\n')

    def test_staging_extra_code_added_during_scan_is_refused(self):
        def race(action, home, stage, *args):
            if action == 'scan': (stage/'extra.py').write_text('print("extra")')
            return self.fake_native(action, home, stage, *args)
        with patch.object(self.mod, 'native_call', race): result = self.deploy()
        self.assertEqual(result['status'], 'incomplete')
        self.assertTrue((self.home/'plugins/autowork').is_symlink())

    def test_untracked_native_output_cannot_be_reported_ready(self):
        def extra(action, home, stage, *args):
            result = self.fake_native(action, home, stage, *args)
            if action == 'install': (home/'plugins/autowork/extra.py').write_text('extra')
            return result
        with patch.object(self.mod, 'native_call', extra): result = self.deploy()
        self.assertEqual(result['status'], 'incomplete')

    def test_live_helper_process_defers_selected_skill_replacement(self):
        import sys
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)',
                                    str(self.home/'skills/demo/SKILL.md')])
        self.addCleanup(lambda: (process.terminate(), process.wait()))
        result = self.deploy()
        self.assertEqual(result['profiles']['default']['status'], 'deferred')
        self.assertTrue((self.home/'plugins/autowork').is_symlink())

    def test_helper_launch_lock_defers_install_without_changing_profile(self):
        import fcntl
        journal = self.home/'autowork'; journal.mkdir()
        with (journal/'goal-handoff.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.deploy()
        self.assertEqual(result['status'], 'incomplete')
        self.assertIn('handoff is active', result['profiles']['default']['error'])
        self.assertEqual(self.calls, [])
        self.assertTrue((self.home/'plugins/autowork').is_symlink())
        self.assertEqual((self.home/'skills/demo/SKILL.md').read_text(), 'old\n')

    def test_helper_started_during_scan_is_preserved_and_blocks_publication(self):
        processes = []
        def race(action, *args):
            if action == 'scan':
                process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)',
                                           str(self.home/'plugins/autowork/update_bundle.py')])
                processes.append(process)
                self.addCleanup(lambda: (process.terminate(), process.wait()))
            return self.fake_native(action, *args)
        with patch.object(self.mod, 'native_call', race):
            result = self.deploy()
        self.assertEqual(result['status'], 'incomplete')
        self.assertIn('Active helper process', result['profiles']['default']['error'])
        self.assertIsNone(processes[0].poll())
        self.assertTrue((self.home/'plugins/autowork').is_symlink())
        self.assertEqual((self.home/'skills/demo/SKILL.md').read_text(), 'old\n')
        self.assertNotIn('install', [action for action, _ in self.calls])

    def direct_claim(self, **changes):
        import os
        state = self.repo/'.git/autowork-execution'; state.mkdir()
        claim_path = state/'active.json'
        claim = {'task_id': 'TASK-1', 'workspace': str(self.repo), 'profile': 'default',
                 'owner': {'pid': os.getpid(),
                           'start_ticks': Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19],
                           'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}}
        claim.update(changes)
        claim_path.write_text(json.dumps(claim))
        journal = self.home/'autowork'; journal.mkdir(exist_ok=True)
        (journal/'task-execution-latest.json').write_text(json.dumps(
            {'claim_path': str(claim_path), 'task_id': 'TASK-1'}))
        return claim_path, claim

    def test_live_direct_coordinator_blocks_install_without_helper_argv(self):
        claim_path, _ = self.direct_claim()
        before = claim_path.read_bytes()
        result = self.deploy()
        self.assertEqual(result['profiles']['default']['status'], 'deferred')
        self.assertIn('Active direct coordinator', result['profiles']['default']['error'])
        self.assertEqual(claim_path.read_bytes(), before)
        self.assertTrue((self.home/'plugins/autowork').is_symlink())
        self.assertEqual(self.calls, [])

    def test_released_direct_claim_does_not_veto_install(self):
        claim_path, _ = self.direct_claim(); claim_path.unlink()
        self.assertEqual(self.deploy()['status'], 'updated')

    def test_reused_pid_does_not_veto_install(self):
        claim_path, claim = self.direct_claim()
        claim['owner']['start_ticks'] = str(int(claim['owner']['start_ticks']) + 1)
        claim_path.write_text(json.dumps(claim))
        self.assertEqual(self.deploy()['status'], 'updated')

    def test_exited_direct_coordinator_does_not_veto_install(self):
        process = subprocess.Popen([sys.executable, '-c', 'pass'])
        process.wait()
        claim_path, claim = self.direct_claim()
        claim['owner']['pid'] = process.pid
        claim_path.write_text(json.dumps(claim))
        self.assertEqual(self.deploy()['status'], 'updated')

    def test_direct_coordinator_claim_started_during_scan_blocks_publication(self):
        def race(action, *args):
            if action == 'scan': self.direct_claim()
            return self.fake_native(action, *args)
        with patch.object(self.mod, 'native_call', race):
            result = self.deploy()
        self.assertEqual(result['status'], 'incomplete')
        self.assertIn('Active direct coordinator', result['profiles']['default']['error'])
        self.assertTrue((self.home/'plugins/autowork').is_symlink())
        self.assertEqual((self.home/'skills/demo/SKILL.md').read_text(), 'old\n')
        self.assertNotIn('install', [action for action, _ in self.calls])

    def test_claim_from_prior_boot_does_not_veto_install(self):
        claim_path, claim = self.direct_claim()
        claim['owner']['boot_id'] = 'prior-boot'
        claim_path.write_text(json.dumps(claim))
        self.assertEqual(self.deploy()['status'], 'updated')

    def test_other_profiles_live_direct_claim_does_not_veto_install(self):
        self.direct_claim(profile='work')
        self.assertEqual(self.deploy()['status'], 'updated')

    def test_malformed_direct_claim_requires_explicit_repair(self):
        claim_path, _ = self.direct_claim(owner={})
        before = claim_path.read_bytes()
        result = self.deploy()
        self.assertEqual(result['profiles']['default']['status'], 'deferred')
        self.assertIn('Repair direct execution', result['profiles']['default']['error'])
        self.assertEqual(claim_path.read_bytes(), before)

    def test_malformed_direct_pointer_requires_explicit_repair(self):
        self.direct_claim()
        receipt = self.home/'autowork/task-execution-latest.json'; receipt.write_text('[]')
        result = self.deploy()
        self.assertEqual(result['profiles']['default']['status'], 'deferred')
        self.assertIn('Repair direct execution', result['profiles']['default']['error'])
        self.assertEqual(receipt.read_text(), '[]')

    def test_releasing_latest_repository_preserves_other_live_coordinator(self):
        import hashlib
        claim_a, original = self.direct_claim()
        journal = self.home/'autowork'
        pointers = journal/'task-execution-claims'; pointers.mkdir()
        latest = journal/'task-execution-latest.json'
        key_a = hashlib.sha256(str(self.repo/'.git').encode()).hexdigest()
        (pointers/f'{key_a}.json').write_bytes(latest.read_bytes())
        repo_b = self.root/'second-repository'; repo_b.mkdir()
        self.git(repo_b, 'init', '-b', 'main')
        state_b = repo_b/'.git/autowork-execution'; state_b.mkdir()
        claim_b = state_b/'active.json'
        claim_b.write_text(json.dumps({**original, 'task_id': 'TASK-2', 'workspace': str(repo_b)}))
        pointer_b = json.dumps({'claim_path': str(claim_b), 'task_id': 'TASK-2'})
        key_b = hashlib.sha256(str(repo_b/'.git').encode()).hexdigest()
        (pointers/f'{key_b}.json').write_text(pointer_b)
        latest.write_text(pointer_b)
        claim_b.unlink()  # B releases, while A's exact coordinator remains alive.
        before = claim_a.read_bytes()
        result = self.deploy()
        self.assertEqual(result['profiles']['default']['status'], 'deferred')
        self.assertIn('Active direct coordinator owns TASK-1', result['profiles']['default']['error'])
        self.assertTrue((self.home/'plugins/autowork').is_symlink())
        self.assertEqual(claim_a.read_bytes(), before)
        self.assertEqual(self.calls, [])
        claim_a.unlink()
        self.assertEqual(self.deploy()['status'], 'updated')

    def test_repository_pointer_protects_claim_without_latest_pointer(self):
        self.direct_claim()
        journal = self.home/'autowork'
        pointers = journal/'task-execution-claims'; pointers.mkdir()
        (journal/'task-execution-latest.json').rename(pointers/'repo.json')
        result = self.deploy()
        self.assertEqual(result['profiles']['default']['status'], 'deferred')
        self.assertIn('Active direct coordinator', result['profiles']['default']['error'])

    def test_duplicate_latest_and_repository_pointers_inspect_claim_once(self):
        claim_path, claim = self.direct_claim()
        claim['owner']['boot_id'] = 'prior-boot'
        claim_path.write_text(json.dumps(claim))
        journal = self.home/'autowork'
        pointers = journal/'task-execution-claims'; pointers.mkdir()
        (pointers/'repo.json').write_bytes((journal/'task-execution-latest.json').read_bytes())
        read_text = Path.read_text
        claim_reads = []
        def once(path, *args, **kwargs):
            if path == claim_path:
                claim_reads.append(path)
                if len(claim_reads) > 1:
                    raise OSError('duplicate claim inspection')
            return read_text(path, *args, **kwargs)
        with patch.object(Path, 'read_text', once):
            self.assertIsNone(self.mod.active_consumers(self.home, 'default'))
        self.assertEqual(len(claim_reads), 1)

    def test_malformed_repository_pointer_requires_repair(self):
        pointers = self.home/'autowork/task-execution-claims'; pointers.mkdir(parents=True)
        (pointers/'repo.json').write_text('not json')
        result = self.deploy()
        self.assertEqual(result['profiles']['default']['status'], 'deferred')
        self.assertIn('Repair direct execution', result['profiles']['default']['error'])
        self.assertEqual((pointers/'repo.json').read_text(), 'not json')

    def test_symlinked_repository_pointer_directory_is_refused(self):
        journal = self.home/'autowork'; journal.mkdir()
        outside = self.root/'foreign-pointers'; outside.mkdir()
        (journal/'task-execution-claims').symlink_to(outside, target_is_directory=True)
        result = self.deploy()
        self.assertEqual(result['profiles']['default']['status'], 'deferred')
        self.assertIn('Repair direct execution', result['profiles']['default']['error'])

    def test_git_export_attributes_do_not_change_deployed_blob_hashes(self):
        (self.remote/'.gitattributes').write_text('skills/demo/SKILL.md export-ignore\n')
        self.git(self.remote, 'add', '.'); self.git(self.remote, 'commit', '-m', 'archive attributes')
        self.revision = self.git(self.remote, 'rev-parse', 'HEAD')
        result = self.deploy()
        self.assertEqual(result['status'], 'updated')
        self.assertEqual((self.home/'skills/demo/SKILL.md').read_text(), 'new\n')

    def assert_interrupted_clone_resumes(self, target_name):
        class Killed(BaseException): pass
        original_git = self.mod.git
        def kill(repo, *args):
            if args[0] == 'clone' and target_name in str(args[-1]):
                Path(args[-1]).mkdir()
                (Path(args[-1])/'partial').write_text('interrupted clone')
                raise Killed()
            return original_git(repo, *args)
        with patch.object(self.mod, 'git', kill), self.assertRaises(Killed): self.deploy()
        saved = json.loads((self.home/'maintenance/toolset-update/scoped.json').read_text())
        result = self.deploy()
        self.assertEqual(result['status'], 'updated')
        self.assertEqual(result['backup'], saved['backup'])
        self.assertEqual((Path(saved['backup'])/'default/file-0').read_text(), 'old\n')

    def test_interrupted_stage_clone_can_resume(self):
        self.assert_interrupted_clone_resumes('stage')

    def test_interrupted_original_snapshot_clone_can_resume(self):
        self.assert_interrupted_clone_resumes('original-source')

    def test_local_check_never_installs_or_fetches(self):
        result = self.deploy(check=True)
        self.assertEqual(result['status'], 'update_available')
        self.assertEqual(self.calls, [])
        self.assertTrue((self.home/'plugins/autowork').is_symlink())
        self.assertFalse((self.remote/'.git/FETCH_HEAD').exists())

    def test_unknown_or_empty_selection_is_rejected(self):
        for names in ((), ('missing',), ('../escape',)):
            with self.subTest(names=names), self.assertRaises(ValueError): self.deploy(names)

class ManagedRecoveryTests(unittest.TestCase):
    """All-profile CLI recovery; native admission and process inventory are injected."""
    git = UpdateTests.git

    def fake_native(self, action, home, stage, revision, python):
        result = ScopedUpdateTests.fake_native(self, action, home, stage, revision, python)
        if action == 'install':
            path = home / 'plugins/.install-metadata.json'
            records = json.loads(path.read_text())
            records['autowork'] = {'source': stage.as_uri(), 'revision': revision, 'pinned': True}
            path.write_text(json.dumps(records))
        return result

    def setUp(self):
        UpdateTests.setUp(self)
        # These disposable homes launch no helpers. Keep real admission checks,
        # but never scan unrelated host processes that can vanish mid-inventory.
        iterdir = Path.iterdir
        def fixture_processes(path):
            return iter(()) if path == Path('/proc') else iterdir(path)
        self.enterContext(patch.object(Path, 'iterdir', fixture_processes))
        (self.remote / 'skills/demo/SKILL.md').write_text('old\none\ntwo\nthree\n')
        self.git(self.remote, 'commit', '-am', 'multiline base')
        self.git(self.repo, 'pull', '--ff-only')
        for _, home in self.profiles:
            (home / 'skills/demo/SKILL.md').write_text('old\none\ntwo\nthree\n')
        self.enterContext(patch.object(sys, 'path', [str(ROOT), *sys.path]))
        slot = self.home / 'plugins/autowork'
        slot.unlink()
        self.repo.rename(slot)
        self.repo = slot
        self.profiles[1][1].joinpath('plugins/autowork').unlink()
        self.profiles[1][1].joinpath('plugins/autowork').symlink_to(slot)
        self.before = self.git(slot, 'rev-parse', 'HEAD')
        self.metadata = self.home / 'plugins/.install-metadata.json'
        self.metadata.write_text(json.dumps({'autowork': {
            'source': str(self.remote), 'revision': self.before, 'custom': 'keep'},
            'other': {'custom': 'also keep'}}))
        (self.home / 'config.yaml').write_text('plugins:\n  enabled: [autowork]\n')
        self.calls = []
        self.enterContext(patch.object(self.mod, 'native_call', self.fake_native))
        prepare = self.mod.prepare
        self.enterContext(patch.object(self.mod, 'prepare',
            side_effect=lambda *args, **kwargs: prepare(*args, upstream=str(self.remote), **kwargs)))
        self.enterContext(patch.dict('sys.modules', {'setup_bundle': self.setup_stub}))
        self.enterContext(patch.object(self.mod, 'finalize_profiles',
                                      side_effect=AssertionError('recovery must not activate profiles')))
        self.git(self.remote, 'checkout', '--orphan', 'rewritten')
        (self.remote / 'skills/demo/SKILL.md').write_text('new\none\ntwo\nthree\n')
        self.git(self.remote, 'add', '.')
        self.git(self.remote, 'commit', '-m', 'rewritten history')
        self.git(self.remote, 'branch', '-M', 'main')
        self.after = self.git(self.remote, 'rev-parse', 'HEAD')

    def run_update(self, *extra):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = self.mod.main(['--hermes-home', str(self.home), *extra])
        return code, json.loads(output.getvalue())

    def test_verified_rewrite_preserves_checkout_customizations_and_shared_links(self):
        metadata = json.loads(self.metadata.read_text())
        metadata['autowork'].pop('revision')  # older native records use the pre-fetch trusted tip
        self.metadata.write_text(json.dumps(metadata))
        path = self.home / 'skills/demo/SKILL.md'
        path.write_text('old\none\ntwo\nthree\nlocal lesson\n')
        path.chmod(0o600)
        independent = self.home / 'profiles/independent'
        (independent / 'plugins').mkdir(parents=True)
        self.git(independent, 'clone', str(self.remote), str(independent / 'plugins/autowork'))
        (independent / 'skills/demo').mkdir(parents=True)
        (independent / 'skills/demo/SKILL.md').write_text('new\none\ntwo\nthree\n')
        self.profiles.append(('independent', independent))
        jobs = self.home / 'cron/jobs.json'
        jobs.parent.mkdir()
        jobs.write_text('{"jobs":[{"enabled":false}]}\n')
        config = (self.home / 'config.yaml').read_bytes()
        def tracking_refresh(action, *args):
            result = self.fake_native(action, *args)
            if action == 'scan' and self.git(self.repo, 'rev-parse', 'HEAD') == self.before:
                self.git(self.repo, 'update-ref', 'refs/remotes/origin/main', self.after)
            return result
        with patch.object(self.mod, 'native_call', tracking_refresh):
            code, result = self.run_update()
        self.assertEqual(code, 0, result)
        self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.after)
        self.assertEqual(path.read_text(), 'new\none\ntwo\nthree\nlocal lesson\n')
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(jobs.read_text(), '{"jobs":[{"enabled":false}]}\n')
        self.assertEqual((self.home / 'config.yaml').read_bytes(), config)
        self.assertEqual((self.profiles[1][1] / 'skills/demo/SKILL.md').read_text(), 'new\none\ntwo\nthree\n')
        self.assertTrue((self.profiles[1][1] / 'plugins/autowork').is_symlink())
        backup = Path(result['recovery']['backup'])
        self.assertEqual(self.git(backup / 'default/plugin', 'rev-parse', 'HEAD'), self.before)
        self.assertEqual((backup / 'default/file-0').read_text(), 'old\none\ntwo\nthree\nlocal lesson\n')
        metadata = json.loads(self.metadata.read_text())
        self.assertEqual(metadata['autowork']['custom'], 'keep')
        self.assertEqual(metadata['other'], {'custom': 'also keep'})
        self.assertEqual(metadata['autowork']['source'], str(self.remote))
        self.assertEqual(self.calls.count(('install', str(self.home))), 1)
        calls = list(self.calls)
        code, again = self.run_update()
        self.assertEqual((code, again['status']), (0, 'up_to_date'))
        self.assertEqual(again['recovery']['backup'], str(backup))
        self.assertEqual(self.calls, calls)
        self.assertEqual(path.read_text(), 'new\none\ntwo\nthree\nlocal lesson\n')
        # A later managed source still on the old release must not be masked by
        # the completed consumers' no-op, or replace their preservation bases.
        late = self.home / 'profiles/late'
        (late / 'plugins').mkdir(parents=True)
        self.git(late, 'clone', str(backup / 'default/plugin'), str(late / 'plugins/autowork'))
        (late / 'plugins/.install-metadata.json').write_text(json.dumps({'autowork': {
            'source': str(self.remote), 'revision': self.before}}))
        (late / 'skills/demo').mkdir(parents=True)
        (late / 'skills/demo/SKILL.md').write_text('old\none\ntwo\nthree\n')
        self.profiles.append(('late', late))
        code, extended = self.run_update()
        self.assertEqual(code, 0, extended)
        self.assertEqual(self.git(late / 'plugins/autowork', 'rev-parse', 'HEAD'), self.after)
        self.assertEqual(extended['recovery']['backup'], str(backup))
        self.assertEqual(self.run_update()[1]['status'], 'up_to_date')
        self.assertEqual(path.read_text(), 'new\none\ntwo\nthree\nlocal lesson\n')

    def test_unproven_or_unsafe_sources_defer_without_publication(self):
        for case in ('ahead', 'diverged', 'unregistered', 'untrusted', 'untracked', 'dirty',
                     'worktree', 'shared-objects', 'active', 'unselected', 'shallow', 'gateway-unknown'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                # Each fixture has its own old provenance; never reset or clean a checkout.
                fixture = ManagedRecoveryTests()
                fixture.setUp()
                try:
                    if case in ('ahead', 'diverged'):
                        fixture.git(fixture.repo, 'config', 'user.email', 'fixture@example.invalid')
                        fixture.git(fixture.repo, 'config', 'user.name', 'Fixture')
                        (fixture.repo / 'local').write_text('local commit\n')
                        fixture.git(fixture.repo, 'add', '.')
                        fixture.git(fixture.repo, 'commit', '-m', 'local work')
                        if case == 'ahead':
                            fixture.git(fixture.remote, 'update-ref', 'refs/heads/main', fixture.before)
                    elif case == 'unregistered': fixture.metadata.unlink()
                    elif case == 'untrusted': fixture.metadata.write_text('{"autowork":{"source":"unknown"}}')
                    elif case == 'untracked': (fixture.repo / 'local').write_text('untracked\n')
                    elif case == 'dirty': (fixture.repo / 'plugin.yaml').write_text('name: changed\n')
                    elif case == 'worktree':
                        fixture.git(fixture.repo, 'worktree', 'add', '--detach', directory, fixture.before)
                    elif case == 'shared-objects':
                        objects = fixture.root / 'shared-objects'
                        (fixture.repo / '.git/objects').rename(objects)
                        (fixture.repo / '.git/objects').symlink_to(objects)
                    elif case == 'active':
                        fixture.enterContext(patch.object(fixture.mod, 'active_consumers', return_value='Active shared consumer'))
                    elif case == 'unselected':
                        alias = fixture.home / 'profiles/not-live/plugins/autowork'
                        alias.parent.mkdir(parents=True)
                        alias.symlink_to(fixture.repo)
                    elif case == 'gateway-unknown':
                        (fixture.home / 'gateway.pid').write_text('{"pid":12345}')
                        fixture.enterContext(patch.object(fixture.mod.os, 'kill', side_effect=PermissionError('inaccessible process')))
                    elif case == 'shallow':
                        old = fixture.root / 'old-source'
                        fixture.repo.rename(old)
                        fixture.git(fixture.home, 'clone', '--depth=1', old.as_uri(), str(fixture.repo))
                        fixture.git(fixture.repo, 'remote', 'set-url', 'origin', str(fixture.remote))
                    code, result = fixture.run_update()
                    self.assertEqual(code, 1, result)
                    self.assertTrue(result.get('error') or result.get('recovery'), result)
                    self.assertEqual((fixture.repo / 'skills/demo/SKILL.md').read_text(), 'old\none\ntwo\nthree\n')
                    self.assertEqual(fixture.calls, [])
                finally: fixture.doCleanups()

    def test_scan_refusal_and_foreign_edits_cannot_publish_or_become_a_new_baseline(self):
        path = self.home / 'skills/demo/SKILL.md'
        def refuse(action, *args):
            if action == 'scan': raise ValueError('native scanner denied staged source')
            return self.fake_native(action, *args)
        with patch.object(self.mod, 'native_call', refuse):
            code, first = self.run_update()
        self.assertEqual(code, 1)
        self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.before)
        newcomer = self.home / 'profiles/paused/plugins/autowork'
        newcomer.parent.mkdir(parents=True)
        newcomer.symlink_to(self.repo)
        code, held = self.run_update()
        self.assertEqual(code, 1, held)
        self.assertIn('Unselected shared consumer', str(held))
        self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.before)
        newcomer.unlink()
        path.write_text('foreign edit\n')
        code, second = self.run_update()
        self.assertEqual(code, 1, second)
        self.assertEqual(path.read_text(), 'foreign edit\n')
        self.assertEqual(first['recovery']['backup'], second['recovery']['backup'])

    def test_interrupted_publication_resumes_original_backup(self):
        class Killed(BaseException): pass
        for point in ('source-stage', 'stage', 'backup', 'rename', 'install', 'skill', 'verify',
                      'ordinary', 'ordinary-skill', 'ordinary-source'):
            with self.subTest(point=point), contextlib.ExitStack() as cleanup:
                fixture = ManagedRecoveryTests()
                cleanup.callback(fixture.doCleanups)
                fixture.setUp()
                independent = fixture.home / 'profiles/independent'
                (independent / 'plugins').mkdir(parents=True)
                fixture.git(independent, 'clone', str(fixture.remote), str(independent / 'plugins/autowork'))
                (independent / 'skills/demo').mkdir(parents=True)
                (independent / 'skills/demo/SKILL.md').write_text('new\none\ntwo\nthree\n')
                fixture.profiles.append(('independent', independent))
                (fixture.remote / 'skills/demo/SKILL.md').write_text('new\none\nTWO\nthree\n')
                fixture.git(fixture.remote, 'commit', '-am', 'next release')
                target = fixture.git(fixture.remote, 'rev-parse', 'HEAD')
                original_git, write, rename, replace = fixture.mod.git, Path.write_bytes, Path.rename, Path.replace
                original_apply = fixture.mod.apply
                def apply(plan, backup, **kwargs):
                    if point == 'ordinary': raise Killed()
                    return original_apply(plan, backup, **kwargs)
                def native(action, *args):
                    result = fixture.fake_native(action, *args)
                    if action == point: raise Killed()
                    return result
                def git(repo, *args):
                    if args[0] == 'clone' and ((point == 'stage' and '.stage.preparing-' in str(args[-1]))
                            or (point == 'source-stage' and '.recovery-source-' in str(args[-1]))):
                        raise Killed()
                    result = original_git(repo, *args)
                    if point == 'ordinary-source' and args[0] == 'merge' and repo == independent / 'plugins/autowork':
                        raise Killed()
                    return result
                def write_backup(path, content):
                    result = write(path, content)
                    if point == 'backup' and path.name == 'file-0': raise Killed()
                    return result
                def rename_slot(path, target):
                    if point == 'rename' and path == fixture.repo: raise Killed()
                    return rename(path, target)
                def replace_skill(path, target):
                    if point == 'skill' and target == fixture.home / 'skills/demo/SKILL.md': raise Killed()
                    result = replace(path, target)
                    if point == 'ordinary-skill' and target == independent / 'skills/demo/SKILL.md': raise Killed()
                    return result
                with patch.object(fixture.mod, 'native_call', native), patch.object(fixture.mod, 'git', git), \
                     patch.object(fixture.mod, 'apply', apply), \
                     patch.object(Path, 'write_bytes', write_backup), patch.object(Path, 'rename', rename_slot), \
                     patch.object(Path, 'replace', replace_skill), self.assertRaises(Killed):
                    returned = fixture.run_update()
                    self.fail(f'{point} interruption not reached: {returned!r}; native calls: {fixture.calls!r}')
                saved = json.loads((fixture.home / 'maintenance/toolset-update/recovery.json').read_text())
                (fixture.remote / 'skills/demo/SKILL.md').write_text('later upstream release\n')
                fixture.git(fixture.remote, 'commit', '-am', 'upstream moved during interruption')
                if point == 'ordinary':
                    foreign = independent / 'skills/demo/SKILL.md'
                    foreign.write_text('foreign ordinary edit\n')
                    code, held = fixture.run_update()
                    self.assertEqual(code, 1, held)
                    self.assertEqual(foreign.read_text(), 'foreign ordinary edit\n')
                    foreign.write_text('new\none\ntwo\nthree\n')  # operator reconciles the disposable fixture
                code, result = fixture.run_update()
                self.assertEqual(code, 0, result)
                self.assertEqual(saved['backup'], result['recovery']['backup'])
                self.assertEqual(fixture.git(Path(saved['backup']) / 'default/plugin', 'rev-parse', 'HEAD'), fixture.before)
                self.assertEqual(fixture.git(fixture.repo, 'rev-parse', 'HEAD'), target)
                self.assertEqual((Path(saved['backup']) / 'default/file-0').read_text(), 'old\none\ntwo\nthree\n')
                self.assertEqual(fixture.git(independent / 'plugins/autowork', 'rev-parse', 'HEAD'), target)
                self.assertEqual((independent / 'skills/demo/SKILL.md').read_text(), 'new\none\nTWO\nthree\n')

    def test_interrupted_slot_intent_does_not_move_new_source_edits(self):
        class Killed(BaseException): pass
        rename = Path.rename
        def interrupt(path, target):
            if path == self.repo: raise Killed()
            return rename(path, target)
        with patch.object(Path, 'rename', interrupt), self.assertRaises(Killed):
            self.run_update()
        saved = json.loads((self.home / 'maintenance/toolset-update/recovery.json').read_text())
        (self.repo / 'plugin.yaml').write_text('name: autowork\n# foreign edit\n')
        code, result = self.run_update()
        self.assertEqual(code, 1, result)
        self.assertEqual(saved['backup'], result['recovery']['backup'])
        self.assertEqual((self.repo / 'plugin.yaml').read_text(), 'name: autowork\n# foreign edit\n')
        self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.before)
        self.assertFalse((Path(saved['backup']) / 'default/plugin').exists())

    def test_native_readback_cannot_claim_changed_permissions(self):
        _, unused = self.profiles.pop()  # isolate final read-back, without a later shared-consumer check
        (unused / 'plugins/autowork').unlink()
        path = self.home / 'skills/demo/SKILL.md'
        path.chmod(0o600)
        def foreign(action, *args):
            result = self.fake_native(action, *args)
            if action == 'verify': path.chmod(0o644)
            return result
        with patch.object(self.mod, 'native_call', foreign):
            code, result = self.run_update()
        self.assertEqual(code, 1, result)
        self.assertIn('permission', str(result).lower())
        self.assertEqual(path.stat().st_mode & 0o777, 0o644)  # never roll back a foreign writer

    def test_git_failures_are_not_misclassified_as_negative_ancestry(self):
        original = self.mod.git
        for verb in ('fetch', 'merge-base'):
            def fail(repo, *args):
                if args[0] == verb:
                    raise self.mod.GitFailure(repo, args, 128)
                return original(repo, *args)
            with self.subTest(verb=verb), patch.object(self.mod, 'git', fail):
                code, result = self.run_update()
            self.assertEqual(code, 1, result)
            self.assertIn(f'Git {verb} failed', result['error'])
            self.assertIn('exit 128', result['error'])
            self.assertNotIn('recovery', result)
            self.assertEqual(self.calls, [])

    def test_a_stalled_fetch_is_retried_once(self):
        original, fetches = self.mod.git, []
        def stall_once(repo, *args):
            if args[0] == 'fetch':
                fetches.append(args)
                if len(fetches) == 1:
                    raise subprocess.TimeoutExpired(['git', 'fetch'], 120)
            return original(repo, *args)
        with patch.object(self.mod, 'git', stall_once):
            code, result = self.run_update()
        self.assertEqual(len(fetches), 2)
        self.assertEqual(code, 0, result)

    def test_a_fetch_aborts_a_stalled_transfer(self):
        seen = {}
        def run(argv, **kwargs):
            seen['env'], seen['stdin'] = kwargs.get('env'), kwargs.get('stdin')
            return subprocess.CompletedProcess(argv, 0, b'', b'')
        with patch.object(self.mod.subprocess, 'run', run):
            self.mod.git(self.repo, 'fetch', 'origin')
        self.assertEqual(seen['env']['GIT_CONFIG_KEY_0'], 'http.lowSpeedLimit')
        self.assertEqual(seen['env']['GIT_CONFIG_VALUE_1'], '30')
        # Nor waits at a prompt: an SSH rewrite of the URL fails at once instead.
        self.assertEqual(seen['env']['GIT_TERMINAL_PROMPT'], '0')
        self.assertIn('-o BatchMode=yes', seen['env']['GIT_SSH_COMMAND'])
        self.assertIs(seen['stdin'], subprocess.DEVNULL)
        with patch.dict(self.mod.os.environ, {'GIT_SSH_COMMAND': 'ssh -i key'}), patch.object(self.mod.subprocess, 'run', run):
            self.mod.git(self.repo, 'fetch', 'origin')
        self.assertTrue(seen['env']['GIT_SSH_COMMAND'].startswith('ssh -i key -o BatchMode=yes'))
        with patch.object(self.mod.subprocess, 'run', run):
            self.mod.git(self.repo, 'status')
        self.assertIsNone(seen['env'])

    def test_dry_run_has_no_fetch_or_recovery_state(self):
        before = self.git(self.repo, 'rev-parse', 'refs/remotes/origin/main')
        fetched = (self.repo / '.git/FETCH_HEAD').read_bytes()
        code, result = self.run_update('--dry-run')
        self.assertEqual((code, result['status']), (0, 'preview'))
        self.assertEqual((self.repo / '.git/FETCH_HEAD').read_bytes(), fetched)
        self.assertFalse((self.home / 'maintenance').exists())
        self.assertEqual(self.git(self.repo, 'rev-parse', 'refs/remotes/origin/main'), before)


class NativeAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        package = self.root/'hermes_cli'; package.mkdir()
        (package/'__init__.py').write_text('')
        (package/'plugins_cmd.py').write_text('''
import os
from pathlib import Path

def _scan_on_install_enabled(): return os.environ.get('FAKE_SCAN') != 'disabled'
def _scan_plugin_tree(path, source, *, force, **kwargs):
    assert force is False and not kwargs, 'scan override leaked'
    if os.environ.get('FAKE_SCAN') == 'caution': raise ValueError('caution refused')
    return object()
def cmd_install(source, *, force, ref, enable):
    assert force is False and enable is False and len(ref) == 40
    assert source.startswith('file://')
    Path(os.environ['HERMES_HOME'], 'installed').write_text(source)
''')
        self.stage = self.root/'stage'; self.stage.mkdir()
        self.home = self.root/'home'; self.home.mkdir()

    def run_helper(self, action, scan='safe'):
        import os, sys
        return subprocess.run([sys.executable, str(ROOT/'update_bundle_native.py'), action,
                               str(self.home), str(self.stage), 'a'*40],
                              env=dict(os.environ, PYTHONPATH=str(self.root), FAKE_SCAN=scan),
                              capture_output=True, text=True)

    def test_removed_inventory_action_cannot_access_native_boards(self):
        (self.root/'hermes_cli/kanban_db.py').write_text(
            "raise AssertionError('native board import is forbidden')\n")
        result = self.run_helper('inventory')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Unknown native admission action', result.stderr)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_native_call_resolves_launcher_source_without_pythonpath(self):
        import os, shlex
        package = self.root/'hermes_cli'
        (package/'plugins.py').write_text('')
        (package/'kanban_db.py').write_text(
            "raise AssertionError('native board import is forbidden')\n")
        launcher = self.root/'hermes'
        bootstrap = f'import sys; sys.path.insert(0, {str(self.root)!r})'
        launcher.write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} -I -c {shlex.quote(bootstrap)} "$@"\n')
        launcher.chmod(0o755)
        spec = importlib.util.spec_from_file_location('update_launcher_test', ROOT/'update_bundle.py')
        updater = importlib.util.module_from_spec(spec); spec.loader.exec_module(updater)
        with patch.dict(os.environ, PATH=str(self.root), PYTHONPATH=''), \
             patch.object(sys, 'path', [str(ROOT), *sys.path]):
            admission = updater.native_call('scan', self.home, self.stage, 'a'*40, None)
        self.assertEqual(admission, {'admitted': True})
        self.assertEqual(list(self.home.iterdir()), [])

    def test_native_adapter_exists(self):
        self.assertTrue((ROOT/'update_bundle_native.py').is_file(), 'native admission adapter missing')

    def test_native_scan_refusal_and_disabled_scanning_fail_closed(self):
        for verdict in ('caution', 'disabled'):
            result = self.run_helper('scan', verdict)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('caution refused' if verdict == 'caution' else 'scanning is disabled', result.stderr)
            self.assertFalse((self.home/'installed').exists())

    def test_native_installer_gets_exact_local_source_without_force_or_enable(self):
        result = self.run_helper('install')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.home/'installed').read_text(), self.stage.as_uri())


class ChatMenuEnvTests(unittest.TestCase):
    """TOOLSET-050: `.env` comments, odd chat IDs and per-chat failures during menu healing."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        spec = importlib.util.spec_from_file_location('update_env_under_test', ROOT/'update_bundle.py')
        self.mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.mod)
        sys.path.insert(0, str(ROOT)); self.addCleanup(sys.path.remove, str(ROOT))

    def test_inline_comments_are_dropped_like_dotenv(self):
        (self.home/'.env').write_text(
            '# leading comment\n'
            'TELEGRAM_BOT_TOKEN=111:AAA # main bot\n'
            'TELEGRAM_ALLOWED_USERS="11,22" # owner and wife\n'
            "TELEGRAM_HOME_CHANNEL='-1001'   # group\n"
            'export PLAIN=value\n'
            'HASH=a#b\n'
            'QUOTED_HASH="x # y"\n'
            'EMPTY=\n')
        self.assertEqual(self.mod.read_env(self.home/'.env'), {
            'TELEGRAM_BOT_TOKEN': '111:AAA', 'TELEGRAM_ALLOWED_USERS': '11,22',
            'TELEGRAM_HOME_CHANNEL': '-1001', 'PLAIN': 'value', 'HASH': 'a#b',
            'QUOTED_HASH': 'x # y', 'EMPTY': ''})

    def test_commented_env_reaches_every_owner_chat(self):
        (self.home/'.env').write_text('TELEGRAM_BOT_TOKEN=tok # bot\n'
                                      'TELEGRAM_ALLOWED_USERS="11,22" # owner and wife\n'
                                      'TELEGRAM_HOME_CHANNEL=-1001 # group\n')
        seen = []
        def call(token, method, scope):
            seen.append((token, scope['chat_id'])); return []
        self.assertEqual(self.mod.heal_chat_menus([('default', self.home)], call), [])
        self.assertEqual(seen, [('tok', 11), ('tok', 22), ('tok', -1001)])

    def test_odd_chat_ids_are_skipped_not_fatal(self):
        (self.home/'.env').write_text('TELEGRAM_BOT_TOKEN=tok\nTELEGRAM_ALLOWED_USERS=--5,²,123456789\n')
        menus = {123456789: ['autogoal']}
        def call(token, method, scope):
            if method == 'deleteMyCommands': return menus.pop(scope['chat_id']) is not None
            return [{'command': c} for c in menus.get(scope['chat_id'], [])]
        self.assertEqual(self.mod.heal_chat_menus([('default', self.home)], call),
                         [{'profile': 'default', 'status': 'cleared', 'chats': ['...6789']}])

    def test_failing_chat_is_reported_and_remaining_chats_are_healed(self):
        (self.home/'.env').write_text('TELEGRAM_BOT_TOKEN=tok\nTELEGRAM_ALLOWED_USERS=11,70007,22\n'
                                      'TELEGRAM_HOME_CHANNEL=-1001\n')
        menus = {11: ['autogoal'], 22: ['autogoal'], -1001: ['autoresearch_plan']}
        def call(token, method, scope):
            if scope['chat_id'] == 70007: raise OSError('Bad Request: chat not found')
            if method == 'deleteMyCommands': return menus.pop(scope['chat_id']) is not None
            return [{'command': c} for c in menus.get(scope['chat_id'], [])]
        self.assertEqual(self.mod.heal_chat_menus([('default', self.home)], call), [
            {'profile': 'default', 'status': 'cleared', 'chats': ['...11', '...22', '...1001'],
             'failed': ['...0007'], 'error': 'OSError'}])
        self.assertEqual(menus, {})
        def all_fail(*_, **__): raise OSError('offline')
        self.assertEqual(self.mod.heal_chat_menus([('default', self.home)], all_fail),
                         [{'profile': 'default', 'status': 'unreachable', 'error': 'OSError'}])


class PinProfileTests(unittest.TestCase):
    """TOOLSET-079: report linked profiles; opt-in, reversible pinning to a clone."""
    setUp, git, advance, plan = UpdateTests.setUp, UpdateTests.git, UpdateTests.advance, UpdateTests.plan
    def pin(self, name='work', **options):
        with patch.dict('sys.modules', {'setup_bundle': self.setup_stub}):
            return self.mod.pin_profile(self.home, name, upstream=str(self.remote), **options)
    def unpin(self, name='work', **options):
        with patch.dict('sys.modules', {'setup_bundle': self.setup_stub}):
            return self.mod.unpin_profile(self.home, name, **options)
    def plugin(self, name='work'):
        return dict(self.profiles)[name]/'plugins/autowork'

    def test_reports_only_linked_profiles_with_their_checkout_state(self):
        rows = self.mod.linked_profiles(self.profiles, upstream=str(self.remote))
        head = self.git(self.repo, 'rev-parse', 'HEAD')
        self.assertEqual([(r['profile'], r['revision'], r['dirty'], r['released']) for r in rows],
                         [('default', head, False, True), ('work', head, False, True)])
        self.pin()
        self.assertEqual([r['profile'] for r in self.mod.linked_profiles(self.profiles, upstream=str(self.remote))],
                         ['default'])

    def test_dry_run_writes_nothing(self):
        result = self.pin(dry_run=True)
        self.assertEqual((result['status'], result['revision']), ('would_pin', self.git(self.repo, 'rev-parse', 'HEAD')))
        self.assertTrue(self.plugin().is_symlink())
        self.assertFalse((self.home/'maintenance/toolset-update/pinned').exists())

    def test_pin_keeps_revision_and_saves_the_link(self):
        head = self.git(self.repo, 'rev-parse', 'HEAD')
        result = self.pin()
        plugin = self.plugin()
        self.assertFalse(plugin.is_symlink())
        self.assertEqual(self.git(plugin, 'rev-parse', 'HEAD'), head)
        self.assertEqual(self.git(plugin, 'status', '--porcelain'), '')
        self.assertEqual(self.git(plugin, 'branch', '--show-current'), 'main')
        backup = Path(result['backup'])
        self.assertEqual(Path((backup/'link').readlink()), self.repo)
        self.assertEqual(json.loads((backup/'record.json').read_text())['revision'], head)
        # Unreleased work in the checkout no longer reaches the pinned profile.
        (self.repo/'skills/demo/SKILL.md').write_text('unreleased\n')
        self.git(self.repo, 'commit', '-qam', 'local')
        self.assertEqual(self.git(plugin, 'rev-parse', 'HEAD'), head)
        self.assertEqual((plugin/'skills/demo/SKILL.md').read_text(), 'old\n')

    def test_update_advances_the_pinned_clone(self):
        self.pin()
        self.advance()
        plan = self.plan()
        self.assertEqual(len(plan['sources']), 2)
        self.mod.apply(plan, self.home/'backups')
        self.assertEqual(self.git(self.plugin(), 'rev-parse', 'HEAD'), self.git(self.remote, 'rev-parse', 'HEAD'))

    def test_refuses_dirty_or_unreleased_checkout(self):
        (self.repo/'skills/demo/SKILL.md').write_text('edited\n')
        with self.assertRaisesRegex(ValueError, 'uncommitted'):
            self.pin()
        self.git(self.repo, 'commit', '-qam', 'local')
        with self.assertRaisesRegex(ValueError, 'not on upstream main'):
            self.pin(dry_run=True)
        self.assertTrue(self.plugin().is_symlink())

    def test_refuses_while_an_update_runs(self):
        state = self.home/'maintenance/toolset-update'
        state.mkdir(parents=True)
        held = self.mod._try_update_lock(state)
        self.addCleanup(held.close)
        with self.assertRaisesRegex(ValueError, 'update is running'):
            self.pin()
        self.assertTrue(self.plugin().is_symlink())

    def test_unpin_restores_the_link_and_keeps_the_clone(self):
        self.pin()
        self.assertEqual(self.unpin(dry_run=True)['status'], 'would_unpin')
        self.assertFalse(self.plugin().is_symlink())
        result = self.unpin()
        self.assertEqual(Path(self.plugin().readlink()), self.repo)
        self.assertTrue((Path(result['clone_kept_at'])/'.git').is_dir())
        with self.assertRaisesRegex(ValueError, 'No saved link'):
            self.unpin()

    def test_unlinked_profile_and_cli_refusal(self):
        self.pin()
        self.assertEqual(self.pin()['status'], 'not_linked')
        output = io.StringIO()
        with patch.dict('sys.modules', {'setup_bundle': self.setup_stub}), contextlib.redirect_stdout(output):
            code = self.mod.main(['--hermes-home', str(self.home), '--pin-profile', 'missing', '--dry-run'])
        self.assertEqual((code, json.loads(output.getvalue())['status']), (1, 'refused'))


if __name__ == '__main__':
    unittest.main()
