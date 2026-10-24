"""Native owners execute in the public host namespace, never a borrowed release."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from src_fixture import copy_sources

ROOT = Path(__file__).resolve().parents[1]
OWNERS = {
    '__init__.py': ('plugin.py', 'register'),
    'bundle.py': ('bundle.py', 'defaults'),
    'autoresearch_commands.py': ('autoresearch_commands.py', 'register'),
    'workflow_commands.py': ('workflow_commands.py', 'register'),
    'runtime_defaults.py': ('runtime_defaults.py', 'expected_settings'),
    'telegram_menu_policy.py': ('telegram_menu_policy.py', 'menu_patch'),
}


class SrcNativeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = copy_sources(self.base / 'release', entries=('plugins/defaults.json',))

    def probe(self, body):
        result = subprocess.run(
            [sys.executable, '-B', '-c', body], cwd=self.base,
            env=dict(os.environ, PYTHONPATH=str(self.base)),
            capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_public_exec_module_keeps_host_identity_but_code_belongs_to_src(self):
        self.probe(rf'''import ast, importlib.util, sys
from pathlib import Path
root = Path({str(self.root)!r})
for entry, (owner, function) in {OWNERS!r}.items():
    spec = importlib.util.spec_from_file_location('host_' + Path(owner).stem, root / entry)
    module = importlib.util.module_from_spec(spec)
    # Some native callers do not insert the module in sys.modules.
    spec.loader.exec_module(module)
    assert module.__spec__ is spec
    assert module.__file__ == str(root / entry)
    assert module.__name__ == spec.name and module.__package__ == spec.parent
    if entry == '__init__.py': assert module.__path__ == [str(root)]
    func = getattr(module, function)
    assert func.__globals__ is module.__dict__ and func.__module__ == spec.name
    source = root / 'Src/autowork_runtime' / owner
    assert func.__code__.co_filename == str(source), func.__code__.co_filename
    assert module._AUTOWORK_LAYOUT.implementation(entry) == source
    tree = ast.parse((root / entry).read_text())
    assert not any(isinstance(n, (ast.FunctionDef, ast.ClassDef)) for n in ast.walk(tree))
    assert spec.name not in sys.modules
''')

    def test_foreign_cwd_and_two_releases_keep_peers_resources_and_patches(self):
        other = copy_sources(self.base / 'other', source=self.root, entries=('plugins/defaults.json',))
        for root, mode in ((self.root, 'off'), (other, 'manual')):
            import json
            path = root / 'plugins/defaults.json'
            settings = json.loads(path.read_text())
            settings['hermes']['approvals_mode'] = mode
            path.write_text(json.dumps(settings))
            for name in ('autowork', 'blockers', 'plan-with-me'):
                path = root / 'skills' / name / 'SKILL.md'
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('---\nname: ' + name + '\n---\nFixture skill.\n')
        self.probe(rf'''import argparse, importlib, importlib.util, sys, types
from pathlib import Path
sys.path.insert(0, {str(ROOT / 'tests')!r})
from test_plugin import Context
roots = [Path({str(self.root)!r}), Path({str(other)!r})]
sys.modules['hermes_constants'] = types.SimpleNamespace(get_hermes_home=lambda: roots[0].parent / 'profile')
sys.modules['hermes_cli.commands'] = types.SimpleNamespace(resolve_command=lambda name: None)
sys.modules['hermes_cli.plugins'] = types.SimpleNamespace(get_plugin_commands=lambda: {{}},
    get_plugin_manager=lambda: types.SimpleNamespace(list_plugin_skill_metadata=lambda: []))
sys.modules['gateway.session_context'] = types.SimpleNamespace(get_session_env=lambda *args: '')
# Unqualified modules and files in cwd must never supply a native peer.
for name in ('bundle', 'runtime_defaults', 'telegram_menu_policy', 'autowork_bootstrap'):
    sys.modules[name] = types.SimpleNamespace()
    Path(name + '.py').write_text('raise AssertionError("foreign cwd")\n')
def read(root, entry, name, cache=False):
    spec = importlib.util.spec_from_file_location(name, root / entry)
    module = importlib.util.module_from_spec(spec)
    if cache: sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
plugins = [read(root, '__init__.py', 'native_' + str(i), True) for i, root in enumerate(roots)]
for plugin, root in zip(plugins, roots):
    ctx = Context()
    plugin.register(ctx)
    assert ctx.skills['autowork'] == root / 'skills/autowork/SKILL.md'
    handler = ctx.commands['autowork']
    bundle = importlib.import_module(handler.func.__module__ + '.bundle')
    assert bundle.__file__ == str(root / 'bundle.py')
    bundle.start_update = lambda **kwargs: 'patched update'
    assert handler('update') == 'patched update'
    plugin.blockers_args = lambda raw: 'patched target'
    ctx.commands['plan_with_me']('blockers')
    assert ctx.messages[-1][0].endswith('User arguments:\npatched target')
    setup = plugin._AUTOWORK_COMPAT.peer(bundle.__dict__, 'setup_runtime')
    setup.finalize = lambda selected, report, args: ({{'root': str(selected)}}, 7)
    bundle.inventory = lambda: {{}}
    assert bundle.handle_cli(argparse.Namespace(action='finalize')) == 7
    # ROOT and SKILLS_DIR remain effective host-global resource patches.
    bundle.ROOT = roots[1]
    assert bundle.defaults()['hermes']['approvals_mode'] == 'manual'
    plugin.SKILLS_DIR = roots[1] / 'skills'
    assert plugin._discover_skills()[0][2].is_relative_to(roots[1])
standalone = [read(root, 'runtime_defaults.py', 'policy_' + str(i)) for i, root in enumerate(roots)]
assert [m.expected_settings({{}})['approvals']['mode'] for m in standalone] == ['off', 'manual']
one = standalone[0]._AUTOWORK_COMPAT.peer(standalone[0].__dict__, 'bundle')
one.defaults = lambda: {{'hermes': {{'approvals_mode': 'patched', 'destructive_slash_confirm': False,
    'mcp_reload_confirm': False, 'max_turns': 10, 'allow_gateway_injection': True}}}}
assert standalone[0].expected_settings({{}})['approvals']['mode'] == 'patched'
assert standalone[1].expected_settings({{}})['approvals']['mode'] == 'manual'
''')

    def test_missing_migrated_payload_refuses_without_legacy_or_cached_fallback(self):
        for entry, (owner, _) in OWNERS.items():
            with self.subTest(entry=entry):
                source = self.root / 'Src/autowork_runtime' / owner
                self.assertTrue(source.is_file(), f'missing owner: {source}')
                source.unlink()
                self.probe(f'''import importlib.util, sys, types
from pathlib import Path
root = Path({str(self.root)!r})
sys.modules['autowork_runtime.{Path(owner).stem}'] = types.SimpleNamespace()
spec = importlib.util.spec_from_file_location('missing_payload', root / {entry!r})
module = importlib.util.module_from_spec(spec)
try: spec.loader.exec_module(module)
except ImportError as error: assert 'missing selected-release source' in str(error)
else: raise AssertionError('missing source did not refuse')
''')


if __name__ == '__main__':
    unittest.main()
