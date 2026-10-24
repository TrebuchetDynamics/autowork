"""Read-only closure preparation and its canonical compatibility boundary."""
import ast
from dataclasses import FrozenInstanceError, fields
import importlib
import importlib.util
import inspect
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import parallel_integrate as facade

ROOT = Path(__file__).resolve().parents[2]
LEAF = 'pi_autowork.engine.integration.closure_documents'
COMMITTED = '+++\nschema = 1\nid = "A"\ntitle = "Task A"\nstatus = "open"\n+++\nBody stays.\n'
DONE = ('+++\nschema = 1\nid = "A"\ntitle = "Task A"\nstatus = "done"\n'
        'closure = "coordinator_verified"\nclosure_evidence = "tasks/evidence/A.toml"\n+++\nBody stays.\n')
RECEIPT = ('schema = 1\ntask = "A"\ncandidate = "candidate"\nintegration = "merge"\n'
           'tree = "tree"\ncontract_hash = "contract"\n'
           'checks = ["check", "[REDACTED]", "<path>"]\nresult = "pass"\nreview = "passed"\n')


class ClosureDocumentsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ['TMPDIR'])
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.record = SimpleNamespace(goal='GOAL-1', rank=7, touches=('src/a.py', 'shared'),
                                      resources=('device',), contract_hash='contract')
        self.slot = {'commit': 'candidate', 'report': {'pending_live': ['Phone check']}}
        self.info = {'commit': 'merge'}
        self.checks = {'outcome': 'EXECUTED', 'command_receipt': {
            'exit_code': 0, 'argv': ['check', 'fixture-private-value', '/private/work/check.py']}}
        self.head = {'tasks/items/A.md': COMMITTED}

        def git(repo, *args, raw=False):
            self.assertEqual(repo, self.repo)
            if args == ('rev-parse', 'merge^{tree}'):
                self.assertFalse(raw)
                return 'tree'
            self.assertEqual(args[0], 'show')  # no mutating Git operations
            self.assertTrue(raw)
            self.assertTrue(args[1].startswith('HEAD:'))
            try:
                return self.head[args[1][5:]].encode()
            except KeyError:
                raise ValueError('not at HEAD') from None

        for guard in (patch.object(facade, 'git', git),
                      patch.dict(os.environ, PI_AUTOWORK_LIVE_FOLLOWUP='notes',
                                 CLOSURE_TEST_TOKEN='fixture-private-value')):
            guard.start()
            self.addCleanup(guard.stop)

    def prepare(self):
        return facade.close_writes(self.repo, 'A', self.slot, self.info, self.checks, self.record)

    def test_repeat_preparation_returns_exact_maps_without_writing(self):
        # Working task bytes must never replace the committed verified contract.
        path = self.repo / 'tasks/items/A.md'
        path.parent.mkdir(parents=True)
        path.write_text('uncommitted owner bytes')
        before = {p.relative_to(self.repo): p.read_bytes() for p in self.repo.rglob('*') if p.is_file()}
        expected = {'tasks/items/A.md': DONE + '- Pending live: Phone check\n',
                    'tasks/evidence/A.toml': RECEIPT}
        with patch.object(Path, 'write_text', side_effect=AssertionError('preparation wrote')), \
                patch.object(Path, 'write_bytes', side_effect=AssertionError('preparation wrote')):
            self.assertEqual(self.prepare(), expected)
            self.assertEqual(self.prepare(), expected)
        self.assertEqual({p.relative_to(self.repo): p.read_bytes() for p in self.repo.rglob('*') if p.is_file()}, before)
        # A partial/replayed close removes manual attribution and never duplicates notes.
        self.head['tasks/items/A.md'] = expected['tasks/items/A.md'].replace(
            '+++\nBody', 'closure_actor = "Someone"\nclosure_timestamp = "yesterday"\n'
            'closure_reason = "manual"\nowner_waiver = "old"\nowner_qualification = "old"\n+++\nBody')
        self.assertEqual(self.prepare(), expected)
        self.slot['review'] = {'decision': 'approved fixture-private-value /private/work/review'}
        self.checks['outcome'] = 'FAILED'
        self.checks['command_receipt'] = {'exit_code': 1, 'command': 'check'}
        receipt = facade.receipt_text(self.repo, 'A', self.slot, self.info, self.checks, self.record)
        self.assertEqual(receipt, RECEIPT.replace('["check", "[REDACTED]", "<path>"]', '["check"]')
                         .replace('result = "pass"', 'result = "fail"')
                         .replace('review = "passed"', 'review = "approved [REDACTED] <path>"'))

    def test_followup_modes_keep_notes_or_return_one_backlog(self):
        for mode in (None, 'notes', ' UNKNOWN ', 'none', ' BACKLOG '):
            with self.subTest(mode=mode), patch.dict(os.environ):
                if mode is None:
                    os.environ.pop('PI_AUTOWORK_LIVE_FOLLOWUP', None)
                else:
                    os.environ['PI_AUTOWORK_LIVE_FOLLOWUP'] = mode
                writes = self.prepare()
                self.assertEqual(writes['tasks/evidence/A.toml'], RECEIPT)
                self.assertEqual(writes['tasks/items/A.md'], DONE + (
                    '- Pending live: Phone check\n' if mode in (None, 'notes', ' UNKNOWN ') else ''))
                if mode == ' BACKLOG ':
                    self.assertEqual(list(writes), ['tasks/items/A.md', 'tasks/evidence/A.toml',
                                                    'tasks/items/LIVE-GOAL-1.md'])
                    self.assertEqual(writes['tasks/items/LIVE-GOAL-1.md'],
                        '+++\nschema = 1\nid = "LIVE-GOAL-1"\ntitle = "Live qualifications for GOAL-1"\n'
                        'short = "Live qualifications"\nstatus = "open"\ngoal = "GOAL-1"\n'
                        'section = "Needs decision"\nrank = 8\ndepends_on = ["A"]\n'
                        'touches = ["src/a.py", "shared"]\nresources = ["device"]\n'
                        'kind = "implementation"\nownership = "owner"\n'
                        'scope = "Owner-authorized live checks accumulated from offline task closures in this goal."\n'
                        'acceptance = ["A: Phone check"]\nchecks = ["Live qualification by an authorized person"]\n'
                        'exclusions = ["Offline evidence does not count"]\n+++\n')
                else:
                    self.assertEqual(len(writes), 2)
        self.slot['report']['pending_live'] = []
        self.assertEqual(self.prepare(), {'tasks/items/A.md': DONE, 'tasks/evidence/A.toml': RECEIPT})

    @patch.dict(os.environ, PI_AUTOWORK_LIVE_FOLLOWUP='backlog')
    def test_backlog_reads_worktree_before_head_and_reuses_suffix_with_ordered_dedup(self):
        closed = '+++\nschema = 1\nid = "LIVE-GOAL-1"\ntitle = "Live"\nstatus = "done"\n+++\n'
        self.head['tasks/items/LIVE-GOAL-1.md'] = closed
        open_text = ('+++\nschema = 1\nid = "LIVE-GOAL-1-2"\ntitle = "Live"\nstatus = "open"\n'
                     'depends_on = ["B"]\ntouches = ["shared", "b.py"]\nresources = ["lab", "device"]\n'
                     'acceptance = ["B: First", "A: Phone check"]\n+++\nKeep body.\n')
        self.head['tasks/items/LIVE-GOAL-1-2.md'] = open_text
        working = self.repo / 'tasks/items/LIVE-GOAL-1-2.md'
        working.parent.mkdir(parents=True)
        working.write_text(open_text.replace('B: First', 'B: Working'))
        self.slot['report']['pending_live'] = ['Phone check', 'Second check', 'Second check']
        writes = self.prepare()
        self.assertEqual(writes['tasks/items/LIVE-GOAL-1-2.md'],
                         open_text.replace('["B"]', '["A", "B"]')
                         .replace('["shared", "b.py"]', '["shared", "b.py", "src/a.py"]')
                         .replace('B: First', 'B: Working')
                         .replace('"A: Phone check"]', '"A: Phone check", "A: Second check"]'))
        working.unlink()
        self.assertIn('B: First', self.prepare()['tasks/items/LIVE-GOAL-1-2.md'])
        self.head['tasks/items/LIVE-GOAL-1-2.md'] = open_text.replace('"open"', '"done"')
        self.assertIn('tasks/items/LIVE-GOAL-1-3.md', self.prepare())
        for number in range(3, 100):
            self.head[f'tasks/items/LIVE-GOAL-1-{number}.md'] = closed
        with self.assertRaisesRegex(ValueError, 'too many closed live backlogs'):
            self.prepare()
        self.assertEqual(facade.live_backlog_id(SimpleNamespace(goal='a / b')), 'LIVE-a-b')
        self.assertEqual(facade.live_backlog_id(SimpleNamespace(goal=None)), 'LIVE-UNASSIGNED')
        self.assertEqual(facade.task_store_rank(SimpleNamespace(rank=None)), 1)

    def test_facades_keep_signatures_identity_and_fresh_four_callable_ports(self):
        leaf = importlib.import_module(LEAF)
        self.assertIs(facade, importlib.import_module('pi_autowork.engine.parallel_integrate'))
        self.assertIs(facade.close_files, importlib.import_module('pi_autowork.engine.parallel_state').close_files)
        signatures = {
            'receipt_path': '(task)', 'receipt_text': '(repo, task, slot, info, checks, record)',
            'live_backlog_id': '(record)',
            'followup_text': '(task, record, items, *, existing=None, followup=None)',
            'existing_backlog': '(repo, followup)', 'backlog_target': '(repo, record)',
            'task_store_rank': '(record)', 'close_writes': '(repo, task, slot, info, checks, record)'}
        for name, signature in signatures.items():
            self.assertEqual(str(inspect.signature(getattr(facade, name))), signature)
        self.assertEqual([f.name for f in fields(leaf.ClosurePorts)], ['git', 'passed', 'task_path', 'live_items'])
        ports = leaf.ClosurePorts(facade.git, facade.passed, facade.execution.task_path, facade.live_items)
        with self.assertRaises(FrozenInstanceError):
            ports.git = None
        seen = []
        original = leaf.close_writes

        def prepare(*args, ports):
            seen.append(ports)
            return original(*args, ports=ports)

        for n in (1, 2):
            def git(repo, *args, raw=False):
                return COMMITTED.encode() if raw else f'tree-{n}'
            with patch.object(leaf, 'close_writes', prepare), \
                    patch.object(facade, 'git', git), patch.object(facade, 'passed', lambda check: n == 1), \
                    patch.object(facade.execution, 'task_path', lambda task: f'records/{task}.md'), \
                    patch.object(facade, 'live_items', lambda value: [f'live-{n}']):
                writes = self.prepare()
                self.assertEqual(facade.receipt_text(self.repo, 'A', self.slot, self.info,
                                                     self.checks, self.record), writes['tasks/evidence/A.toml'])
                self.assertEqual(facade.existing_backlog(self.repo, 'A'), ('records/A.md', COMMITTED))
                self.assertEqual(facade.backlog_target(self.repo, self.record),
                                 ('LIVE-GOAL-1', ('records/LIVE-GOAL-1.md', COMMITTED)))
            self.assertEqual(writes['records/A.md'], DONE + f'- Pending live: live-{n}\n')
            self.assertEqual(writes['tasks/evidence/A.toml'], RECEIPT.replace('tree = "tree"', f'tree = "tree-{n}"')
                             .replace('result = "pass"', 'result = "pass"' if n == 1 else 'result = "fail"')
                             .replace('review = "passed"', 'review = "passed"' if n == 1 else 'review = "failed"'))
        self.assertIsNot(seen[0], seen[1])

    def test_actual_src_leaf_rejects_reverse_imports_and_import_time_side_effects(self):
        leaf = importlib.import_module(LEAF)
        path = ROOT / 'Src/pi_autowork/engine/integration/closure_documents.py'
        self.assertEqual(Path(leaf.__file__), path)
        self.assertEqual(path.with_name('__init__.py').read_bytes(), b'')
        package = LEAF.rpartition('.')[0]
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                module = importlib.util.resolve_name('.' * node.level + (node.module or ''), package) if node.level else node.module
                names = [module + '.' + alias.name for alias in node.names] if module == 'pi_autowork.engine' else [module]
            else:
                continue
            for name in names:
                self.assertTrue(name.split('.')[0] in sys.stdlib_module_names or name in (
                    'pi_autowork.engine.task_store', 'pi_autowork.engine.check_receipt'), name)
        code = f'''
import os, sys
sys.path.insert(0, {str(ROOT / 'Src')!r})
def audit(event, args):
    if event == 'open':
        mode, flags = args[1:3]
        assert not (mode and any(c in mode for c in 'wax+')), (event, args)
        assert not (flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)), (event, args)
    assert event not in ('subprocess.Popen', 'os.system', 'os.mkdir', 'os.rename', 'os.remove', 'socket.connect'), (event, args)
sys.addaudithook(audit)
import {LEAF}
assert 'pi_autowork.engine.check_receipt' not in sys.modules
assert not any(name in sys.modules for name in (
    'pi_autowork.coordinator', 'pi_autowork.engine.parallel_integrate',
    'pi_autowork.engine.parallel_dispatch', 'pi_autowork.engine.parallel_state',
    'pi_autowork.engine.task_execution'))
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', code], cwd=self.repo,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
