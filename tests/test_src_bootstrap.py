"""Release-local compatibility boundaries, exercised only in private source copies."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from src_fixture import copy_sources


class SrcBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = copy_sources(self.base / 'release')

    def write(self, name, body):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
        return path

    def probe(self, body):
        result = subprocess.run([sys.executable, '-B', '-c', body], cwd=self.root,
                                env=dict(os.environ, PYTHONPATH=str(self.root)),
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(list(self.root.rglob('__pycache__')))

    def test_layout_is_frozen_bounded_and_reports_actual_owners(self):
        self.write('Src/pi_autowork/nested/owner.py', 'VALUE = 1\n')
        self.write('Src/pi_autowork/test_ignored.py', 'raise RuntimeError\n')
        self.write('Src/pi_autowork/fixtures/ignored.py', 'raise RuntimeError\n')
        outside = self.base / 'outside.py'
        outside.write_text('raise RuntimeError\n')
        (self.root / 'Src/pi_autowork/escape.py').symlink_to(outside)
        alias = self.base / 'linked'
        alias.symlink_to(self.root, target_is_directory=True)
        self.probe(f'''from pathlib import Path
from dataclasses import FrozenInstanceError
import autowork_bootstrap as b
layout = b.Layout(Path({str(alias)!r}))
assert layout.root == Path.cwd()
assert layout.entrypoint('main_check') == Path.cwd() / 'pi-autowork/pi_autowork/main_check.py'
assert layout.entrypoint('runtime_defaults') == Path.cwd() / 'runtime_defaults.py'
assert layout.entrypoint('pi_autowork.legacy.task_migrate') == layout.component / 'pi_autowork/legacy/task_migrate.py'
assert layout.resource('skills') == Path.cwd() / 'skills'
assert layout.implementation('pi-autowork/pi_autowork/nested/owner.py') == layout.package / 'nested/owner.py'
paths = b.Layout.python_sources(Path({str(alias)!r}))
assert paths == tuple(sorted(set(paths)))
assert layout.package / 'nested/owner.py' in paths
assert all(p.name not in ('test_ignored.py', 'ignored.py', 'escape.py') for p in paths)
try: layout.root = Path('/')
except FrozenInstanceError: pass
else: raise AssertionError('mutable layout')
''')

    def test_native_namespace_and_release_local_peers_preserve_patches(self):
        shim = '''from pathlib import Path
import importlib.util
p = Path(__file__).parent / 'autowork_bootstrap.py'
s = importlib.util.spec_from_file_location(__name__ + '._bootstrap', p)
b = importlib.util.module_from_spec(s)
s.loader.exec_module(b)
b.execute(globals(), 'Src/autowork_runtime/example.py')
'''
        self.write('example.py', shim)
        self.write('sibling.py', 'VALUE = "selected"\n')
        self.write('another.py', 'VALUE = 2\n')
        self.write('Src/autowork_runtime/example.py', '''ROOT = __file__
def value():
    return _AUTOWORK_COMPAT.peer(globals(), 'sibling').VALUE
''')
        other = copy_sources(self.base / 'other', source=self.root, entries=('sibling.py',))
        (other / 'sibling.py').write_text('VALUE = "other"\n')
        self.probe(f'''import importlib.util, sys, types
from pathlib import Path
sys.modules['sibling'] = types.SimpleNamespace(VALUE='poison')
def read(root, name):
    spec = importlib.util.spec_from_file_location(name, root / 'example.py',
        submodule_search_locations=[str(root)] if name == 'plugin' else None)
    module = importlib.util.module_from_spec(spec)
    if name == 'plugin': sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
one = read(Path.cwd(), 'plugin')
two = read(Path({str(other)!r}), 'other_plugin')
assert one.value() == 'selected' and two.value() == 'other'
assert one.value.__globals__ is one.__dict__
assert one.value.__module__ == one.__spec__.name == one.__package__ == 'plugin'
assert one.__path__ == [str(Path.cwd())]
assert one._AUTOWORK_COMPAT.peer(one.__dict__, 'sibling') is sys.modules['plugin.sibling']
assert one.ROOT == one.__file__ == str(Path.cwd() / 'example.py')
one._AUTOWORK_COMPAT.peer(one.__dict__, 'sibling').VALUE = 'patched'
assert one.value() == 'patched' and two.value() == 'other'
assert one._AUTOWORK_COMPAT.peer(one.__dict__, 'another').VALUE == 2
assert one._AUTOWORK_LAYOUT.root == Path.cwd()
''')

    def test_runner_canonical_and_flat_import_orders_share_identity(self):
        self.write('Src/pi_autowork/engine/__init__.py', '')
        self.write('Src/pi_autowork/engine/example.py', 'class Error(Exception): pass\nVALUE = []\n')
        self.write('Src/pi_autowork/command.py', 'def _compat_main(argv): return len(argv)\n')
        for first in ('example', 'pi_autowork.engine.example'):
            with self.subTest(first=first):
                self.probe(f'''from pathlib import Path
import importlib, sys
import autowork_bootstrap as b
layout = b.activate(Path.cwd())
one = importlib.import_module({first!r})
two = b.load(Path.cwd(), 'pi_autowork.engine.example')
assert one is two is importlib.import_module('example')
assert one.Error is two.Error
assert one.__name__ == one.__spec__.name == 'pi_autowork.engine.example'
assert importlib.reload(one) is one
assert one.__name__ == one.__spec__.name == 'pi_autowork.engine.example'
one.VALUE.append('patched')
assert two.VALUE == ['patched']
assert list(sys.modules['pi_autowork'].__path__) == [str(layout.package)]
assert str(layout.component / 'engine') not in sys.path
assert b.run(Path.cwd(), 'pi_autowork.command', ['a', 'b']) == 2
for name in ('worktree_paths', 'checkout_lock'):
    module = b.load(Path.cwd(), 'pi_autowork.engine.' + name)
    assert Path(module.__file__) == layout.component / 'engine' / (name + '.py')
''')

    def test_missing_poisoned_sources_and_cross_root_runner_refuse(self):
        outside = self.base / 'outside'
        outside.mkdir()
        (outside / 'main_check.py').write_text('raise RuntimeError("foreign")\n')
        (self.root / 'pi-autowork/pi_autowork/main_check.py').unlink()
        (self.root / 'pi-autowork/pi_autowork/main_check.py').symlink_to(outside / 'main_check.py')
        (self.root / 'pi-autowork/bin').symlink_to(outside, target_is_directory=True)
        self.write('Src/pi_autowork/engine/__init__.py', '')
        self.write('Src/pi_autowork/engine/example.py', 'VALUE = 1\n')
        self.probe('''from pathlib import Path
import sys, types
import autowork_bootstrap as b
root = Path.cwd()
def refuses(call):
    try: call()
    except (ImportError, ValueError, FileNotFoundError): pass
    else: raise AssertionError('borrowed missing or foreign source')
refuses(lambda: b.Layout(root).entrypoint('main_check'))
refuses(lambda: b.Layout(root).entrypoint('autowork'))
refuses(lambda: b.execute({'__file__': str(root / 'example.py'), '__name__': 'example'}, 'Src/autowork_runtime/missing.py'))
refuses(lambda: b.execute({'__file__': str(root / 'example.py')}, '../outside.py'))
poison = types.ModuleType('pi_autowork')
poison.__file__ = '/foreign/pi_autowork/__init__.py'
sys.modules['pi_autowork'] = poison
refuses(lambda: b.activate(root))
del sys.modules['pi_autowork']
b.activate(root)
refuses(lambda: b.load(root.parent / 'other', 'pi_autowork.command'))
(root / 'Src/pi_autowork/engine/example.py').unlink()
refuses(lambda: b.load(root, 'pi_autowork.engine.example'))
''')


if __name__ == '__main__':
    unittest.main()
