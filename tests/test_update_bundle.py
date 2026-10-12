"""Offline update tests using local Git remotes, never a live Hermes home."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
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
    def git(self,path,*args):
        return subprocess.check_output(['git','-C',str(path),*args],stderr=subprocess.DEVNULL,text=True).strip()
    def advance(self):
        (self.remote/'skills/demo/SKILL.md').write_text('new\n')
        self.git(self.remote,'commit','-am','update')
    def plan(self):
        return self.mod.prepare(self.repo,self.profiles,upstream=str(self.remote))
    def test_updates_shared_checkout_and_both_profiles(self):
        self.advance();plan=self.plan()
        self.assertEqual(len(plan['sources']),1)
        self.mod.apply(plan,self.home/'backups')
        for _,home in self.profiles:self.assertEqual((home/'skills/demo/SKILL.md').read_text(),'new\n')
        self.assertEqual(self.git(self.repo,'rev-parse','HEAD'),self.git(self.remote,'rev-parse','HEAD'))
        self.assertEqual(self.plan()['writes'],[])
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

if __name__=='__main__':unittest.main()
