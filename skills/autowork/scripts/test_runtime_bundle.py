"""Pinned worker helpers must survive updates to the dispatcher's installation."""
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest


class RuntimeBundleTests(unittest.TestCase):
    def load(self):
        path = Path(__file__).with_name('runtime_bundle.py')
        self.assertTrue(path.exists(), 'Missing frozen helper runtime')
        spec = importlib.util.spec_from_file_location('runtime_bundle', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_source_update_does_not_change_worker_or_transitive_helper(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            for name in ('autowork', 'docs-sync', 'shared', 'engineering'):
                (source / name).mkdir(parents=True)
            scripts = source / 'autowork/scripts'
            scripts.mkdir()
            (scripts / 'runtime_bundle.py').write_bytes(Path(module.__file__).read_bytes())
            entry = scripts / 'entry.py'
            entry.write_text('from dependency import value\nprint(value)\n')
            dependency = scripts / 'dependency.py'
            dependency.write_text('value = "original"\n')
            runtime = module.freeze(source, root / 'runtimes')
            command = shlex.split(module.command(runtime, 'autowork/scripts/entry.py'))
            dependency.write_text('value = "updated"\n')
            entry.write_text('raise RuntimeError("updated entry")\n')
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), 'original')
            frozen_dependency = Path(runtime['root']) / 'autowork/scripts/dependency.py'
            frozen_dependency.chmod(0o600)
            frozen_dependency.write_text('value = "tampered"\n')
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('tampered', result.stdout)
            self.assertIn('Runtime file changed', result.stderr)

    def test_real_helper_closure_runs_from_bundle_and_rejects_wrong_pin(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as directory:
            runtime = module.freeze(Path(__file__).resolve().parents[2], Path(directory))
            for script in ('autowork/scripts/pass_workspace.py', 'autowork/scripts/finish_task.py',
                           'docs-sync/scripts/goals.py'):
                command = shlex.split(module.command(runtime, script)) + ['--help']
                result = subprocess.run(command, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('usage:', result.stdout)
            bad = dict(runtime, sha256='0' * 64)
            result = subprocess.run(shlex.split(module.command(bad, 'docs-sync/scripts/goals.py')) + ['--help'],
                                    text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Runtime manifest changed', result.stderr)

    def test_symlink_source_is_rejected(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('autowork', 'docs-sync', 'shared', 'engineering'):
                (root / 'source' / name).mkdir(parents=True)
            (root / 'outside.py').write_text('print("foreign")')
            (root / 'source/autowork/linked.py').symlink_to(root / 'outside.py')
            with self.assertRaisesRegex(ValueError, 'symlink'):
                module.freeze(root / 'source', root / 'runtimes')

    def test_completion_shell_dependency_keeps_runtime_reusable(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / 'repo'
            repo.mkdir()
            def git(*args):
                return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()
            git('init', '-q')
            git('config', 'user.name', 'Fixture')
            git('config', 'user.email', 'fixture@local')
            (repo / 'code.py').write_text('print("base")\n')
            git('add', 'code.py')
            git('commit', '-qm', 'base')
            original_head = git('rev-parse', 'HEAD')
            (repo / 'code.py').write_text('print("fixed")\n')
            runtime = module.freeze(Path(__file__).resolve().parents[2], root / 'runtimes')
            command = shlex.split(module.command(runtime, 'autowork/scripts/finish_task.py')) + [
                '--repo', str(repo), '--profile', 'fixture', '--card', 't_fixture', '--message', 'fix fixture',
                '--check-json', json.dumps([sys.executable, '-c', 'pass']), '--', 'code.py']
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], 'committed')
            self.assertEqual(git('rev-parse', 'HEAD'), original_head)
            try:
                module.verify(runtime)
            except ValueError as error:
                self.fail('Completion mutated the frozen helper runtime: ' + str(error))


if __name__ == '__main__':
    unittest.main()
