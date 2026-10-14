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
    def test_native_observation_reads_omitted_claim_and_budget_fields_without_writes(self):
        import sqlite3
        from unittest.mock import patch
        import writer_registration as module
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / 'board.db'
            with sqlite3.connect(db) as conn:
                conn.execute('CREATE TABLE tasks (id TEXT, status TEXT, current_run_id TEXT, worker_pid INT, goal_mode INT, goal_max_turns INT)')
                conn.execute('INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?)', ('original', 'blocked', None, 42, 1, 100))
            before = db.read_bytes()
            def native(argv, **kwargs):
                if argv[3:] == ['kanban', 'boards', 'list', '--json']:
                    return json.dumps([dict(slug='default', id='board-1', db_path=str(db))])
                if argv[3:] == ['kanban', '--board', 'default', 'show', 'original', '--json']:
                    return json.dumps(dict(task=dict(id='original', status='blocked'), runs=[]))
                raise AssertionError(argv)
            observe = getattr(module, 'native_observation', None)
            self.assertTrue(callable(observe), 'Native JSON omits claims and budget; preparation must read authoritative fields')
            with patch.object(module.subprocess, 'check_output', side_effect=native):
                observed = observe('fixture', 'original')
            self.assertEqual(observed['task']['worker_pid'], 42)
            self.assertEqual(observed['task']['goal_max_turns'], 100)
            self.assertEqual(observed['task']['board_id'], 'board-1')
            self.assertEqual(db.read_bytes(), before)

    def test_preparation_accepts_only_one_exact_append_and_retains_baseline(self):
        import writer_registration as module
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'writers.jsonl'
            original = (json.dumps({'card': 'older'}) + '\n').encode()
            path.write_bytes(original)
            declaration = dict(registry=str(path), scope=['src/a.py'],
                fields={key:key for key in ('card','task','workspace','base','scope')})
            capture = getattr(module, 'capture_declaration', None)
            self.assertTrue(callable(capture), 'Preparation must capture the pre-card registry without a fabricated identity')
            pending = capture(declaration, Path(tmp), [], [])
            expected = dict(card='original', task='T1', workspace=tmp, base='a'*40, scope=['src/a.py'])
            row = (json.dumps(expected) + '\n').encode()
            path.write_bytes(original + row)
            requirement = module.prepare_requirement(pending, expected)
            self.assertTrue(module.verify(**requirement))
            self.assertEqual(pending['baseline'], original.decode())
            for data in (row, original + row + row, original + row + b'{}\n',
                         original + (json.dumps(dict(expected, scope=['foreign.py'])) + '\n').encode()):
                path.write_bytes(data)
                with self.subTest(data=data), self.assertRaises(ValueError):
                    module.prepare_requirement(pending, expected)
                self.assertEqual(path.read_bytes(), data)

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
            valid_requirement = requirement.read_bytes()
            variants = [
                ('top', b'{"registry":"foreign",' + valid_requirement[1:]),
                ('expected', valid_requirement.replace(b'"expected": {', b'"expected": {"card":"foreign",', 1)),
                ('fields', valid_requirement.replace(b'"fields": {', b'"fields": {"card":"foreign",', 1)),
            ]
            for name, ambiguous in variants:
                with self.subTest(requirement_duplicate=name):
                    requirement.write_bytes(ambiguous)
                    ambiguous_pin = hashlib.sha256(ambiguous).hexdigest()
                    rejected = subprocess.run(command[:-1] + [ambiguous_pin], capture_output=True, text=True)
                    self.assertEqual(rejected.returncode, 2, rejected.stdout)
                    self.assertIn('duplicate JSON field', rejected.stderr)
                    with self.assertRaisesRegex(ValueError, 'duplicate JSON field'):
                        guard.check_registration(manifest, tmp, requirement, ambiguous_pin, 'card-1')
                    self.assertEqual(requirement.read_bytes(), ambiguous)
                    self.assertEqual(path.read_bytes(), before)
            requirement.write_bytes(valid_requirement)
            for wrong_manifest in (dict(manifest, goal_task='T2'),
                                   dict(manifest, candidate_identity=dict(base_commit='b'*40))):
                with self.assertRaisesRegex(ValueError, 'mismatched fields: ' + ('task' if wrong_manifest.get('goal_task') == 'T2' else 'base')):
                    guard.check_registration(wrong_manifest, tmp, requirement, pin, 'card-1')
            for card in (None, 'foreign'):
                with self.assertRaisesRegex(ValueError, 'mismatched fields: card'):
                    guard.check_registration(manifest, tmp, requirement, pin, card)
            other_workspace = Path(tmp) / 'other'
            other_workspace.mkdir()
            with self.assertRaisesRegex(ValueError, 'mismatched fields: workspace'):
                guard.check_registration(manifest, other_workspace, requirement, pin, 'card-1')
            with self.assertRaisesRegex(ValueError, 'mismatched fields: card, base, task'):
                guard.check_registration(dict(manifest, goal_task='T2',
                    candidate_identity=dict(base_commit='b'*40)), tmp, requirement, pin, None)
            self.assertEqual(requirement.read_bytes(), valid_requirement)
            self.assertEqual(path.read_bytes(), before)
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

class DriftDiagnosticsTests(unittest.TestCase):
    def test_drift_diagnosis_never_admits_or_rewrites_evidence(self):
        import writer_registration as module
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / 'writers.jsonl'
            expected = dict(card='card-1', task='T1', workspace=directory, base='a'*40, scope=['src/a.py'])
            fields = {key: key for key in expected}
            original = (json.dumps(expected) + '\n').encode()
            digest = hashlib.sha256(original).hexdigest()
            cases = [
                (original + (json.dumps(dict(expected, card='other')) + '\n').encode(), 'current_row_matches'),
                ((json.dumps(dict(expected, task='T2')) + '\n').encode(), 'current_row_mismatch'),
                ((json.dumps(dict(expected, card='other')) + '\n').encode(), 'current_row_missing'),
                (original + original, 'current_row_ambiguous'),
                (b'{"card":"wrong",' + original[1:], 'registry_invalid'),
                (b'not json\n', 'registry_invalid'),
            ]
            for content, diagnosis in cases:
                with self.subTest(diagnosis=diagnosis):
                    registry.write_bytes(content)
                    with self.assertRaisesRegex(ValueError, diagnosis):
                        module.verify(registry, digest, fields, expected)
                    self.assertEqual(registry.read_bytes(), content)

if __name__ == '__main__': unittest.main()
