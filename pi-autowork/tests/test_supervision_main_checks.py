"""Compatibility seam for the stateless main-check supervision owner."""
import ast
import importlib
from importlib.util import resolve_name
import inspect
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import coordinator, main_check  # noqa: E402
from pi_autowork.coordinator import Coordinator  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SIGNATURES = {
    'remember_reused_main_green': '(self, revision, finished)',
    'check_main': '(self)',
    'check_main_reap': '(self, record)',
    'check_main_revert_pending': '(self, record)',
    'check_main_reuse_result': '(self, record, rev, cmd)',
    'check_main_wait': '(self, record)',
    'check_main_start': '(self, record, rev, cmd)',
    'passed_on_tree': '(self, rev, cmd)',
    'finish_main_check': '(self, record)',
    'finish_main_check_failures': '(self, record, code, log_text)',
    'finish_main_check_result': '(self, record, code, log_text, child)',
}


def reverse_imports(source):
    """Resolve even deferred/local relative imports against the leaf package."""
    found = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = resolve_name('.' * node.level + (node.module or ''), 'pi_autowork.supervision') \
                if node.level else node.module
            found.update([base, *(f'{base}.{alias.name}' for alias in node.names)])
    return found & {'pi_autowork.coordinator'}


class SupervisionMainCheckTests(unittest.TestCase):
    def test_coordinator_signatures_stay_compatible(self):
        for name, signature in SIGNATURES.items():
            with self.subTest(method=name):
                self.assertEqual(str(inspect.signature(getattr(Coordinator, name))), signature)
        leaf = importlib.import_module('pi_autowork.supervision.main_checks')
        for name, signature in SIGNATURES.items():
            with self.subTest(helper=name):
                ports = ', *, git, planning_path)' if name == 'check_main_reuse_result' else ', *, git)'
                expected = signature.replace('self', 'owner')[:-1] + ports
                self.assertEqual(str(inspect.signature(getattr(leaf, name))), expected)

    def test_reuse_uses_current_git_and_planning_policy(self):
        with tempfile.TemporaryDirectory() as folder:
            owner = Coordinator.__new__(Coordinator)
            owner.state, owner.repo = Path(folder), folder
            owner.passed_on_tree = lambda *args: None
            record = dict(state='green', rev='old', green='old', finished=123)
            for revision, accepted in (('first', True), ('second', False)):
                with self.subTest(revision=revision), \
                        patch.object(coordinator, 'git', return_value=f'{revision}.custom'), \
                        patch.object(coordinator, 'planning_path', lambda path: path == 'first.custom'):
                    main_check.write(owner.state, record)
                    self.assertEqual(owner.check_main_reuse_result(record, revision, 'true'), accepted)
                    self.assertEqual(main_check.read(owner.state)['rev'], revision if accepted else 'old')
            self.assertEqual(main_check.slot_status(owner.state / 'main-green-history.json'), {'first': 123})

    def test_phase_dispatch_respects_owner_overrides_in_order(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, PI_AUTOWORK_MAIN_CHECK='true'):
            owner = Coordinator.__new__(Coordinator)
            owner.state, owner.repo, owner.base, owner.stop = Path(folder), folder, 'main', False
            calls = []
            owner.check_main_reap = lambda record: (calls.append('reap') or (None, None))
            owner.check_main_revert_pending = lambda record: calls.append('revert')
            owner.check_main_reuse_result = lambda record, rev, cmd: calls.append(('reuse', rev, cmd))
            owner.check_main_wait = lambda record: calls.append('wait')
            owner.check_main_start = lambda record, rev, cmd: calls.append(('start', rev, cmd))
            with patch.object(coordinator, 'git', return_value='new'):
                owner.check_main()
            self.assertEqual(calls, ['reap', 'revert', ('reuse', 'new', 'true'), 'wait', ('start', 'new', 'true')])
            owner.finish_main_check_result = lambda *args: calls.append(args)
            (owner.state / 'main-check.exit').write_text('0\n')
            (owner.state / 'main-check.log').write_text('checked\n')
            record = dict(rev='new', pid=123, start_time='456')
            owner.finish_main_check(record)
            self.assertEqual(calls[-1], (record, 0, 'checked\n', dict(pid=123, start_time='456')))

    def test_leaf_has_no_reverse_imports_even_when_local_or_relative(self):
        for source in ('import pi_autowork.coordinator', 'from pi_autowork import coordinator',
                       'def deferred():\n    from ..coordinator import Coordinator',
                       'def deferred():\n    from .. import coordinator'):
            with self.subTest(source=source):
                self.assertEqual(reverse_imports(source), {'pi_autowork.coordinator'})
        package = ROOT / 'Src/pi_autowork/supervision'
        self.assertEqual((package / '__init__.py').read_bytes(), b'')
        self.assertEqual(reverse_imports((package / 'main_checks.py').read_text()), set())

    def test_fresh_leaf_import_is_inert_and_does_not_load_the_facade(self):
        script = '''import importlib, os, sys
sys.path.insert(0, sys.argv[1])
def audit(event, args):
    if event == 'open' and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        raise AssertionError(('write on import', args))
    if event in {'subprocess.Popen', 'os.system', 'os.fork', 'os.mkdir', 'os.remove', 'os.rename', 'socket.bind'}:
        raise AssertionError(('side effect on import', event))
sys.addaudithook(audit)
leaf = importlib.import_module('pi_autowork.supervision.main_checks')
assert 'pi_autowork.coordinator' not in sys.modules
assert not any(name.startswith('pi_autowork.engine') for name in sys.modules)
assert leaf.__file__ == sys.argv[2]
'''
        result = subprocess.run([sys.executable, '-B', '-c', script, str(ROOT / 'pi-autowork'),
                                 str(ROOT / 'Src/pi_autowork/supervision/main_checks.py')],
                                cwd=os.environ['TMPDIR'], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
