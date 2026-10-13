"""Read-only registration prerequisite; no native dispatch or live registry writes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

class RegistrationTests(unittest.TestCase):
    def test_bound_registration_and_rejections(self):
        spec = importlib.util.spec_from_file_location('registration', Path(__file__).with_name('writer_registration.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'registry.jsonl'
            expected = dict(card='card-1', task='T1', workspace=tmp, base='a'*40, scope=['src/a.py'])
            fields = dict(card='native_card', task='task', workspace='workspace', base='base', scope='files')
            row = {fields[k]: v for k,v in expected.items()}
            path.write_text(json.dumps(row)+'\n')
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertTrue(module.verify(path, digest, fields, expected))
            for scope in (['.'], ['src/a.py', 'src/./a.py'], ['src/../a.py']):
                with self.assertRaises(ValueError):
                    module.verify(path, digest, fields, dict(expected, scope=scope))
            symlink = Path(tmp) / 'linked.jsonl'
            symlink.symlink_to(path)
            with self.assertRaises(ValueError): module.verify(symlink, digest, fields, expected)
            with self.assertRaises(ValueError):
                module.verify(path, digest, dict(fields, status='status'), dict(expected, status='active'))
            before = path.read_bytes()
            for field in expected:
                wrong = dict(expected)
                wrong[field] = ['foreign.py'] if field == 'scope' else 'wrong'
                with self.subTest(field=field), self.assertRaises(ValueError):
                    module.verify(path, digest, fields, wrong)
            with self.assertRaises(ValueError): module.verify(path, '0'*64, fields, expected)
            self.assertEqual(path.read_bytes(), before)
            guard_spec = importlib.util.spec_from_file_location('registration_guard', Path(__file__).with_name('pass_workspace.py'))
            guard = importlib.util.module_from_spec(guard_spec)
            guard_spec.loader.exec_module(guard)
            requirement = Path(tmp) / 'requirement.json'
            requirement.write_text(json.dumps(dict(registry=str(path), sha256=digest, fields=fields, expected=expected)))
            pin = hashlib.sha256(requirement.read_bytes()).hexdigest()
            manifest = dict(goal_task='T1', candidate_identity=dict(base_commit='a'*40))
            self.assertTrue(guard.check_registration(manifest, tmp, requirement, pin, 'card-1'))
            command = [sys.executable, str(Path(__file__).with_name('writer_registration.py')),
                       '--requirement', str(requirement), '--requirement-sha256', pin]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['outcome'], 'writer_registration_verified')
            for wrong_manifest in (dict(manifest, goal_task='T2'),
                                   dict(manifest, candidate_identity=dict(base_commit='b'*40))):
                with self.assertRaises(ValueError):
                    guard.check_registration(wrong_manifest, tmp, requirement, pin, 'card-1')
            for card in (None, 'foreign'):
                with self.assertRaises(ValueError): guard.check_registration(manifest, tmp, requirement, pin, card)
            with self.assertRaises(ValueError): guard.check_registration(manifest, tmp, requirement, '0'*64, 'card-1')
            for field in fields.values():
                with self.subTest(duplicate_field=field):
                    path.write_text('{'+json.dumps(field)+': "foreign",'+before.decode()[1:])
                    duplicate = path.read_bytes()
                    with self.assertRaisesRegex(ValueError, 'duplicate JSON field'):
                        module.verify(path, hashlib.sha256(duplicate).hexdigest(), fields, expected)
                    self.assertEqual(path.read_bytes(), duplicate)
            path.write_bytes(before + before)
            with self.assertRaises(ValueError):
                module.verify(path, hashlib.sha256(path.read_bytes()).hexdigest(), fields, expected)
            path.write_text('')
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
            with self.assertRaises(ValueError):
                module.verify(path, hashlib.sha256(b'').hexdigest(), fields, expected)

if __name__ == '__main__': unittest.main()
