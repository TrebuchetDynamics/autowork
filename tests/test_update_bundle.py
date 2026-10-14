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
        (self.remote/'plugin.yaml').write_text('name: hermes-toolset\n')
        self.git(self.remote,'add','.');self.git(self.remote,'commit','-m','initial')
        self.repo=self.root/'checkout';self.git(self.root,'clone',str(self.remote),str(self.repo))
        self.home=self.root/'home';self.home.mkdir()
        self.profiles=[('default',self.home),('work',self.home/'profiles/work')]
        for name,home in self.profiles:
            (home/'plugins').mkdir(parents=True)
            (home/'plugins/hermes-toolset').symlink_to(self.repo)
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

    def test_modified_old_copy_is_drift_not_an_invented_merge_base(self):
        self.advance()
        self.git(self.repo, 'pull', '--ff-only')
        path = self.home / 'skills/demo/SKILL.md'
        path.write_text('old\ncustomization\n')
        plan = self.plan()
        self.assertEqual([item['path'] for item in plan['drift']], [str(path)])
        with self.assertRaisesRegex(ValueError, 'drift'):
            self.mod.apply(plan, self.home / 'backups')
        self.assertFalse((self.home / 'backups').exists())
        self.assertEqual(path.read_text(), 'old\ncustomization\n')
        self.assertEqual((self.profiles[1][1] / 'skills/demo/SKILL.md').read_text(), 'old\n')

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
        plan = self.plan()
        self.assertEqual(len(plan['drift']), 2)
        self.assertFalse(any(path.name == 'SKILL.md' for path, *_ in plan['writes']))

    def test_historical_lookup_is_cached_per_checkout_and_path(self):
        self.advance()
        self.git(self.repo, 'pull', '--ff-only')
        with patch.object(self.mod, 'git', wraps=self.mod.git) as calls:
            self.plan()
        history = [call for call in calls.call_args_list if call.args[1] == 'log']
        self.assertEqual(len(history), 1)
        self.assertIn('-100', history[0].args)

    def test_older_copy_refreshes_when_checkout_and_upstream_also_differ(self):
        self.advance()
        self.git(self.repo, 'pull', '--ff-only')
        (self.remote / 'skills/demo/SKILL.md').write_text('latest\n')
        self.git(self.remote, 'commit', '-am', 'another update')
        self.mod.apply(self.plan(), self.home / 'backups')
        for _, home in self.profiles:
            self.assertEqual((home / 'skills/demo/SKILL.md').read_text(), 'latest\n')

    def test_check_and_update_report_unresolved_drift_without_profile_writes(self):
        self.advance()
        self.git(self.repo, 'pull', '--ff-only')
        path = self.home / 'skills/demo/SKILL.md'
        path.write_text('custom\n')
        prepare = self.mod.prepare
        for check in (True, False):
            with self.subTest(check=check):
                args = ['--hermes-home', str(self.home)] + (['--check'] if check else [])
                with patch.object(self.mod, 'prepare', side_effect=lambda *_: prepare(self.repo, self.profiles, upstream=str(self.remote))), \
                     patch.dict('sys.modules', {'setup_bundle': self.setup_stub}), \
                     patch.object(self.mod, 'finalize_profiles') as finalize, \
                     contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(self.mod.main(args), 1)
                receipt = json.loads((self.home / 'maintenance/toolset-update/latest.json').read_text())
                self.assertEqual(receipt['status'], 'incomplete')
                self.assertEqual(receipt['drift'][0]['path'], str(path))
                self.assertIn('reconcile', receipt['action'])
                self.assertNotIn('backup', receipt)
                finalize.assert_not_called()
                self.assertEqual(path.read_text(), 'custom\n')
                self.assertEqual((self.profiles[1][1] / 'skills/demo/SKILL.md').read_text(), 'old\n')

    def test_update_heals_profile_settings_and_requests_one_graceful_gateway_restart(self):
        self.advance()
        self.git(self.repo, 'pull', '--ff-only')
        prepare = self.mod.prepare
        stale = self.profiles[0][1] / 'config.yaml'
        stale.write_text('platforms: {telegram: {extra: {command_menu: {priority: [autoresearch]}}}}\n')
        def activate(source, root, profiles):
            stale.write_text('platforms: {telegram: {extra: {command_menu: {priority: [autowork]}}}}\n')
            return [{'profile': name, 'status': 'ready'} for name, _ in profiles]
        for running, expected in ((True, 'requested'), (False, 'not_running')):
            with self.subTest(running=running), \
                 patch.object(self.mod, 'prepare', side_effect=lambda *_: prepare(self.repo, self.profiles, upstream=str(self.remote))), \
                 patch.dict('sys.modules', {'setup_bundle': self.setup_stub}), \
                 patch.object(self.mod, 'finalize_profiles', side_effect=activate), \
                 patch.object(self.mod, 'gateway_running', return_value=running), \
                 patch.object(self.mod, 'request_gateway_restart') as restart, \
                 contextlib.redirect_stdout(io.StringIO()):
                stale.write_text('platforms: {telegram: {extra: {command_menu: {priority: [autoresearch]}}}}\n')
                self.assertEqual(self.mod.main(['--hermes-home', str(self.home)]), 0)
                receipt = json.loads((self.home / 'maintenance/toolset-update/latest.json').read_text())
                self.assertEqual(receipt['settings_healed'], [self.profiles[0][0]])
                self.assertEqual(receipt['gateway_restart'], expected)
                self.assertEqual(restart.call_count, int(running))

    def test_noop_update_does_not_restart_the_gateway(self):
        self.advance()
        self.git(self.repo, 'pull', '--ff-only')
        prepare = self.mod.prepare
        receipts = []
        with patch.object(self.mod, 'prepare', side_effect=lambda *_: prepare(self.repo, self.profiles, upstream=str(self.remote))), \
             patch.dict('sys.modules', {'setup_bundle': self.setup_stub}), \
             patch.object(self.mod, 'finalize_profiles', side_effect=lambda s, r, profiles: [{'profile': n, 'status': 'ready'} for n, _ in profiles]), \
             patch.object(self.mod, 'gateway_running', return_value=True), \
             patch.object(self.mod, 'request_gateway_restart') as restart, \
             contextlib.redirect_stdout(io.StringIO()):
            for _ in range(2):
                self.assertEqual(self.mod.main(['--hermes-home', str(self.home)]), 0)
                receipts.append(json.loads((self.home / 'maintenance/toolset-update/latest.json').read_text()))
        self.assertEqual([r['status'] for r in receipts], ['updated', 'up_to_date'])
        self.assertEqual([r['gateway_restart'] for r in receipts], ['requested', 'not_needed'])
        self.assertEqual(restart.call_count, 1)

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

    def test_conflict_in_last_profile_prevents_all_mutations(self):
        self.advance();p=self.profiles[-1][1]/'skills/demo/SKILL.md';p.write_text('custom\n')
        with self.assertRaisesRegex(ValueError,'conflict'):self.plan()
        self.assertEqual((self.repo/'skills/demo/SKILL.md').read_text(),'old\n')
        self.assertEqual((self.home/'skills/demo/SKILL.md').read_text(),'old\n')
    def test_upstream_deletion_preserves_modified_local_skill(self):
        p=self.remote/'skills/demo/SKILL.md';p.unlink()
        self.git(self.remote,'commit','-am','remove')
        (self.home/'skills/demo/SKILL.md').write_text('custom\n')
        with self.assertRaisesRegex(ValueError,'conflict'):self.plan()

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

    def test_nonconflicting_customization_is_merged(self):
        old=b'one\n' + b'context\n'*10 + b'two\n'
        local=old.replace(b'one',b'custom')
        new=old.replace(b'two',b'upstream')
        merged=self.mod.merge_file(old,local,new,Path('SKILL.md'))
        self.assertIn(b'custom',merged);self.assertIn(b'upstream',merged)

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
            self.git(home, 'clone', str(stage), str(home/'plugins/hermes-toolset'))
        return {'commands': ['autowork', 'toolset']} if action == 'verify' else {'admitted': True}

    def deploy(self, names=('default',), **kwargs):
        return self.mod.scoped_update(self.home, self.remote, self.revision, names, 'python3', **kwargs)

    def test_scoped_api_exists(self):
        self.assertTrue(callable(getattr(self.mod, 'scoped_update', None)), 'scoped deployment is missing')

    def test_selected_link_replaced_without_shared_source_or_unselected_writes(self):
        result = self.deploy()
        self.assertEqual(result['status'], 'updated')
        self.assertEqual((self.home/'skills/demo/SKILL.md').read_text(), 'new\n')
        self.assertFalse((self.home/'plugins/hermes-toolset').is_symlink())
        self.assertEqual((self.repo/'skills/demo/SKILL.md').read_text(), 'old\n')
        self.assertEqual((self.profiles[1][1]/'skills/demo/SKILL.md').read_text(), 'old\n')
        self.assertTrue((self.profiles[1][1]/'plugins/hermes-toolset').is_symlink())
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
        self.assertTrue((self.home/'plugins/hermes-toolset').is_symlink())
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
            self.assertFalse((home/'plugins/hermes-toolset').is_symlink())
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
        self.assertTrue((self.home/'plugins/hermes-toolset').is_symlink())

    def test_destination_race_during_scan_is_not_overwritten(self):
        path = self.home/'skills/demo/SKILL.md'
        def race(action, *args):
            if action == 'scan': path.write_text('concurrent change')
            return self.fake_native(action, *args)
        with patch.object(self.mod, 'native_call', race): result = self.deploy()
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(path.read_text(), 'concurrent change')
        self.assertTrue((self.home/'plugins/hermes-toolset').is_symlink())

    def test_killed_after_slot_move_resumes_original_backup(self):
        class Killed(BaseException): pass
        def kill(action, *args):
            if action == 'install': raise Killed()
            return self.fake_native(action, *args)
        with patch.object(self.mod, 'native_call', kill), self.assertRaises(Killed): self.deploy()
        saved = json.loads((self.home/'maintenance/toolset-update/scoped.json').read_text())
        self.assertFalse((self.home/'plugins/hermes-toolset').exists())
        result = self.deploy()
        self.assertEqual(result['status'], 'updated')
        self.assertEqual(result['backup'], saved['backup'])
        self.assertEqual((Path(saved['backup'])/'default/file-0').read_text(), 'old\n')

    def test_slot_move_intent_before_rename_resumes_directory_install(self):
        import shutil
        slot = self.home/'plugins/hermes-toolset'
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
        self.assertTrue((self.home/'plugins/hermes-toolset').is_symlink())

    def test_untracked_native_output_cannot_be_reported_ready(self):
        def extra(action, home, stage, *args):
            result = self.fake_native(action, home, stage, *args)
            if action == 'install': (home/'plugins/hermes-toolset/extra.py').write_text('extra')
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
        self.assertTrue((self.home/'plugins/hermes-toolset').is_symlink())

    def test_helper_launch_lock_defers_install_without_changing_profile(self):
        import fcntl
        journal = self.home/'autowork'; journal.mkdir()
        with (journal/'goal-handoff.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.deploy()
        self.assertEqual(result['status'], 'incomplete')
        self.assertIn('handoff is active', result['profiles']['default']['error'])
        self.assertEqual(self.calls, [])
        self.assertTrue((self.home/'plugins/hermes-toolset').is_symlink())
        self.assertEqual((self.home/'skills/demo/SKILL.md').read_text(), 'old\n')

    def test_helper_started_during_scan_is_preserved_and_blocks_publication(self):
        processes = []
        def race(action, *args):
            if action == 'scan':
                process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)',
                                           str(self.home/'plugins/hermes-toolset/update_bundle.py')])
                processes.append(process)
                self.addCleanup(lambda: (process.terminate(), process.wait()))
            return self.fake_native(action, *args)
        with patch.object(self.mod, 'native_call', race):
            result = self.deploy()
        self.assertEqual(result['status'], 'incomplete')
        self.assertIn('Active helper process', result['profiles']['default']['error'])
        self.assertIsNone(processes[0].poll())
        self.assertTrue((self.home/'plugins/hermes-toolset').is_symlink())
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
        self.assertTrue((self.home/'plugins/hermes-toolset').is_symlink())
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
        self.assertTrue((self.home/'plugins/hermes-toolset').is_symlink())
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
        self.assertTrue((self.home/'plugins/hermes-toolset').is_symlink())
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
        self.assertTrue((self.home/'plugins/hermes-toolset').is_symlink())
        self.assertFalse((self.remote/'.git/FETCH_HEAD').exists())

    def test_unknown_or_empty_selection_is_rejected(self):
        for names in ((), ('missing',), ('../escape',)):
            with self.subTest(names=names), self.assertRaises(ValueError): self.deploy(names)

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
            admission = updater.native_call('scan', self.home, self.stage, 'a'*40, sys.executable)
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


if __name__ == '__main__':
    unittest.main()
