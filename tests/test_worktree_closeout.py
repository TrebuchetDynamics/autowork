"""Instruction contracts and real disposable Git examples, not model/cron qualification."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / 'skills/autowork/references/worktree-closeout.md'


class WorktreeCloseoutTests(unittest.TestCase):
    def reference(self):
        self.assertTrue(REFERENCE.is_file(), 'Missing worktree closeout contract')
        return REFERENCE.read_text()

    def test_native_portable_and_shared_entrypoints_require_closeout(self):
        for path in ('skills/autowork/SKILL.md', 'adapters/skills/autowork/SKILL.md',
                     'skills/shared/WORKTREE-ISOLATION.md'):
            with self.subTest(path=path):
                self.assertIn('worktree-closeout.md', (ROOT / path).read_text())

    def test_contract_preserves_live_and_unfinished_work(self):
        text = self.reference()
        for requirement in ('main', 'master', 'active', 'locked', 'ignored',
                            'unmerged', 'receipts', 'cleanup pending',
                            'no hard limit', 'No push', 'not a runtime guarantee'):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, text)
        command = re.findall(r'```sh\n(.*?)```', text, re.S)[0]
        self.assertNotIn('--force', command)
        self.assertNotIn('rm -rf', command)
        self.assertNotIn('prune', command)

    def git(self, root, *args, check=True):
        return subprocess.run(['git', '-C', str(root), *args], check=check,
                              text=True, capture_output=True)

    def fixture(self, root, branch):
        canonical = root / 'canonical'
        canonical.mkdir()
        self.git(canonical, 'init', '-q', '-b', branch)
        self.git(canonical, 'config', 'user.name', 'Fixture')
        self.git(canonical, 'config', 'user.email', 'fixture@example.invalid')
        (canonical / '.gitignore').write_text('ignored-cache/\n')
        (canonical / 'base.txt').write_text('base\n')
        self.git(canonical, 'add', '.gitignore', 'base.txt')
        self.git(canonical, 'commit', '-qm', 'base')
        worktree = root / 'task worktree'
        self.git(canonical, 'worktree', 'add', '-q', '-b', 'task/example', str(worktree))
        (worktree / 'result.txt').write_text('verified fixture result\n')
        self.git(worktree, 'add', 'result.txt')
        self.git(worktree, 'commit', '-qm', 'task')
        commit = self.git(worktree, 'rev-parse', 'HEAD').stdout.strip()
        return canonical, worktree, commit

    def test_documented_git_sequence_on_main_and_master(self):
        command = re.findall(r'```sh\n(.*?)```', self.reference(), re.S)[0]
        for branch in ('main', 'master'):
            for state in ('merged', 'unmerged', 'dirty', 'ignored', 'locked', 'wrong-target', 'moved-head'):
                with self.subTest(branch=branch, state=state), tempfile.TemporaryDirectory() as folder:
                    canonical, worktree, commit = self.fixture(Path(folder), branch)
                    if state != 'unmerged':
                        self.git(canonical, 'merge', '--ff-only', 'task/example')
                    if state == 'locked':
                        self.git(canonical, 'worktree', 'lock', str(worktree))
                    if state == 'dirty':
                        (worktree / 'untracked.txt').write_text('preserve\n')
                    if state == 'ignored':
                        (worktree / 'ignored-cache').mkdir()
                        (worktree / 'ignored-cache/receipt.json').write_text('{}\n')
                    if state == 'moved-head':
                        (worktree / 'later.txt').write_text('not integrated\n')
                        self.git(worktree, 'add', 'later.txt')
                        self.git(worktree, 'commit', '-qm', 'later work')
                    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
                    env.update(CANONICAL=str(canonical), TASK_WORKTREE=str(worktree),
                               TASK_COMMIT=commit, DEFAULT_BRANCH='wrong' if state == 'wrong-target' else branch)
                    result = subprocess.run(['bash', '-c', command], cwd=canonical,
                                            env=env, capture_output=True, text=True)
                    self.assertEqual(result.returncode == 0, state == 'merged', result.stderr)
                    self.assertEqual(worktree.exists(), state != 'merged')
                    self.assertTrue(canonical.is_dir())
                    self.assertEqual(self.git(canonical, 'branch', '--show-current').stdout.strip(), branch)
                    listed = self.git(canonical, 'worktree', 'list', '--porcelain').stdout
                    self.assertEqual(str(worktree) in listed, state != 'merged')


if __name__ == '__main__':
    unittest.main()
