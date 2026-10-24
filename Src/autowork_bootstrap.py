"""Stdlib-only, selected-release paths and narrowly distinct compatibility loaders.

Native sources execute in their public caller's dictionary. Runner sources import
once under canonical package names. Neither mechanism searches for another release.
"""
from dataclasses import dataclass
import hashlib
import importlib
import importlib.abc
import importlib.util
from pathlib import Path
import sys
from types import ModuleType

_ROOT = Path(__file__).resolve().parents[1]
HOOKS = frozenset(('worktree_paths', 'checkout_lock'))
NATIVE = {
    '__init__.py': 'plugin.py',
    **{name + '.py': name + '.py' for name in (
        'bundle', 'autoresearch_commands', 'workflow_commands', 'runtime_defaults',
        'telegram_menu_policy', 'install_skills', 'setup_bundle', 'setup_preflight',
        'setup_runtime', 'update_bundle', 'update_bundle_native')},
    'install-omh.py': 'install_omh.py', 'install-graphify.py': 'install_graphify.py',
}


def _inside(root, relative, *, required=False):
    relative = Path(relative)
    path = root / relative
    if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root):
        raise ValueError(f'path escapes selected release: {relative}')
    if required and not path.is_file():
        raise ImportError(f'missing selected-release source: {path}')
    return path


@dataclass(frozen=True)
class Layout:
    root: Path

    def __post_init__(self):
        object.__setattr__(self, 'root', Path(self.root).resolve())

    @property
    def src(self):
        return self.root / 'Src'

    @property
    def runtime(self):
        return self.src / 'autowork_runtime'

    @property
    def package(self):
        return self.src / 'pi_autowork'

    @property
    def engine(self):
        return self.package / 'engine'

    @property
    def component(self):
        return self.root / 'pi-autowork'

    def resource(self, relative):
        return _inside(self.root, relative)

    def entrypoint(self, name):
        """Stable launch paths; explicit relative public paths are also accepted."""
        if '/' in name or name.endswith('.py'):
            return _inside(self.root, name)
        if name == 'autowork':
            return _inside(self.root, 'pi-autowork/bin/autowork')
        if name == 'agent_commit':
            return _inside(self.root, 'pi-autowork/engine/agent_commit.sh')
        native = {'plugin': '__init__.py', **{Path(p).stem.replace('-', '_'): p for p in NATIVE}}
        if name in native:
            return _inside(self.root, native[name])
        if name.startswith('pi_autowork.engine.'):
            relative = name.removeprefix('pi_autowork.engine.').replace('.', '/') + '.py'
            return _inside(self.root, 'pi-autowork/engine/' + relative)
        if name.startswith('pi_autowork.'):
            relative = name.removeprefix('pi_autowork.').replace('.', '/') + '.py'
            return _inside(self.root, 'pi-autowork/pi_autowork/' + relative)
        candidate = _inside(self.root, 'pi-autowork/pi_autowork/' + name + '.py')
        if candidate.is_file():
            return candidate
        return _inside(self.root, 'pi-autowork/engine/' + name + '.py')

    def implementation(self, relative):
        """Actual source owner; unmigrated entries remain owners until their cut lands.

        A native shim's literal execute source is authoritative, even when missing.
        """
        entry = _inside(self.root, relative)
        if entry.is_file():
            import ast
            tree = ast.parse(entry.read_bytes(), str(entry))
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == 'execute' and len(node.args) == 2
                        and isinstance(node.args[1], ast.Constant)
                        and isinstance(node.args[1].value, str)):
                    return _inside(self.root, node.args[1].value, required=True)
                if (Path(relative).parts[:2] in (('pi-autowork', 'pi_autowork'), ('pi-autowork', 'engine'))
                        and isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr in ('load', 'run') and len(node.args) >= 2
                        and isinstance(node.args[1], ast.Constant)
                        and isinstance(node.args[1].value, str)
                        and node.args[1].value.startswith('pi_autowork')):
                    # A migrated public entry declares an owner, not a fallback.
                    return _runner_path(self, node.args[1].value)
        parts = Path(relative).parts
        if len(parts) > 2 and parts[:2] in (('pi-autowork', 'pi_autowork'), ('pi-autowork', 'engine')):
            tail = parts[2:] if parts[1] == 'pi_autowork' else ('engine', *parts[2:])
            if parts[1] == 'engine' and Path(relative).stem in HOOKS:
                return entry
            owner = _inside(self.root, str(Path('Src/pi_autowork', *tail)))
            if owner.is_file():
                return owner
        return entry

    @staticmethod
    def python_sources(root):
        """Sorted, bounded production Python; no tests, fixtures or escaping links."""
        layout = Layout(root)
        paths = set(layout.root.glob('*.py'))
        for folder in (layout.src, layout.component / 'pi_autowork', layout.component / 'engine'):
            paths.update(folder.rglob('*.py'))
        excluded = {'tests', 'test', 'fixtures', 'fixture', '__pycache__'}
        return tuple(sorted({layout.implementation(p.relative_to(layout.root).as_posix())
                             for p in paths if p.is_file()
                             and p.resolve().is_relative_to(layout.root)
                             and not excluded.intersection(p.relative_to(layout.root).parts)
                             and not p.name.startswith('test_')
                             and p.name not in ('store_fixture.py', 'offline_fixtures.py')}))


def _selected(root):
    layout = Layout(root)
    if layout.root != _ROOT:
        raise ImportError(f'bootstrap root mismatch: {_ROOT} != {layout.root}')
    return layout


def _origin(module, expected):
    origin = getattr(module, '__file__', None)
    if not origin or Path(origin).resolve() != expected.resolve():
        raise ImportError(f'foreign module {module.__name__}: {origin}; expected {expected}')


def _runner_path(layout, name):
    parts = name.split('.')
    if parts[0] != 'pi_autowork' or not all(p.isidentifier() for p in parts):
        raise ImportError(f'not a canonical runner module: {name}')
    if len(parts) == 3 and parts[1] == 'engine' and parts[2] in HOOKS:
        return _inside(layout.root, f'pi-autowork/engine/{parts[2]}.py', required=True)
    relative = Path('Src', *parts)
    if (layout.root / relative).is_dir():
        relative /= '__init__.py'
    else:
        relative = relative.with_suffix('.py')
    return _inside(layout.root, relative.as_posix(), required=True)


class _SourceLoader(importlib.abc.Loader):
    def __init__(self, path):
        self.path = path

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        exec(compile(self.path.read_bytes(), str(self.path), 'exec'), module.__dict__)

    def get_code(self, fullname):
        # runpy (-m) executes an adapter, not another copy of the owner as __main__.
        # Library-only modules historically imported and exited without an action.
        source = (f'import sys as _sys\n'
                  f'_target = _sys.modules[{__name__!r}].load({str(_ROOT)!r}, {fullname!r})\n'
                  f'_adapter = getattr(_target, "_compat_main", None)\n'
                  f'_sys.exit(_adapter(_sys.argv[1:]) if _adapter else None)\n')
        return compile(source, str(self.path), 'exec')


class _AliasLoader(importlib.abc.Loader):
    def __init__(self, canonical):
        self.canonical = canonical

    def create_module(self, spec):
        module = importlib.import_module(self.canonical)
        self.metadata = {key: getattr(module, key) for key in
                         ('__name__', '__spec__', '__loader__', '__package__')}
        return module

    def exec_module(self, module):
        # Import machinery assigns the alias spec even to an existing object.
        # Preserve the owning spec so reload and future imports stay canonical.
        module.__dict__.update(self.metadata)


class _RunnerFinder(importlib.abc.MetaPathFinder):
    def __init__(self, layout, aliases):
        self.layout, self.aliases = layout, aliases

    def find_spec(self, fullname, path=None, target=None):
        if fullname in self.aliases:
            return importlib.util.spec_from_loader(fullname, _AliasLoader(self.aliases[fullname]))
        if fullname == 'pi_autowork' or fullname.startswith('pi_autowork.'):
            source = _runner_path(self.layout, fullname)
            return importlib.util.spec_from_file_location(
                fullname, source, loader=_SourceLoader(source),
                submodule_search_locations=[str(source.parent)] if source.name == '__init__.py' else None)
        return None


_finder = None


def activate(root):
    """Bind the runner to one complete canonical source tree, never the legacy tree."""
    global _finder
    layout = _selected(root)
    _runner_path(layout, 'pi_autowork')
    aliases = {p.stem: 'pi_autowork.engine.' + p.stem
               for p in layout.engine.glob('*.py') if p.stem != '__init__' and not p.stem.startswith('test_')}
    aliases.update({name: 'pi_autowork.engine.' + name for name in HOOKS})
    # Validate *before* using cached imports, including a preloaded flat engine.
    for name, module in tuple(sys.modules.items()):
        if name == 'pi_autowork' or name.startswith('pi_autowork.'):
            _origin(module, _runner_path(layout, name))
        elif name in aliases:
            _origin(module, _runner_path(layout, aliases[name]))
            if sys.modules.get(aliases[name], module) is not module:
                raise ImportError(f'duplicate engine identity: {name}')
            sys.modules[aliases[name]] = module
    if _finder is None:
        _finder = _RunnerFinder(layout, aliases)
        sys.meta_path.insert(0, _finder)
    else:
        _finder.aliases = aliases
    importlib.import_module('pi_autowork')
    return layout


def load(root, module):
    layout = activate(root)
    expected = _runner_path(layout, module)
    result = importlib.import_module(module)
    _origin(result, expected)
    return result


def run(root, module, argv):
    """Dispatch only an explicit adapter; never re-execute a canonical body."""
    target = load(root, module)
    adapter = getattr(target, '_compat_main', None)
    if adapter is None:
        raise ImportError(f'{module} has no explicit _compat_main adapter')
    return adapter(list(argv))


def execute(namespace, source_relative):
    """Execute a native owner in its existing public module/patch namespace."""
    layout = Layout(Path(namespace['__file__']).resolve().parent)
    if layout.root != _ROOT:
        raise ImportError('native entry and bootstrap roots differ')
    source = _inside(layout.root, source_relative, required=True)
    if not source.is_relative_to(layout.runtime):
        raise ValueError('native source must be under Src/autowork_runtime')
    namespace['_AUTOWORK_LAYOUT'] = layout
    namespace['_AUTOWORK_COMPAT'] = sys.modules[__name__]
    exec(compile(source.read_bytes(), str(source), 'exec'), namespace)


def peer(namespace, name):
    """A native peer belongs to the caller's release and plugin package, not cwd."""
    if not name.isidentifier():
        raise ValueError(f'invalid native peer: {name}')
    layout = namespace.get('_AUTOWORK_LAYOUT') or Layout(Path(namespace['__file__']).resolve().parent)
    if layout.root != _ROOT:
        raise ImportError('native peer and bootstrap roots differ')
    source = _inside(layout.root, name + '.py', required=True)
    package = namespace.get('__package__')
    parent = sys.modules.get(package) if package else None
    if parent is None or not hasattr(parent, '__path__'):
        package = '_autowork_native_' + hashlib.sha256(str(layout.root).encode()).hexdigest()
        if package not in sys.modules:
            parent = ModuleType(package)
            parent.__path__ = [str(layout.root)]
            sys.modules[package] = parent
    elif [Path(p).resolve() for p in parent.__path__] != [layout.root]:
        raise ImportError('foreign native plugin package')
    qualified = package + '.' + name
    if qualified in sys.modules:
        module = sys.modules[qualified]
        _origin(module, source)
        return module
    spec = importlib.util.spec_from_file_location(qualified, source, loader=_SourceLoader(source))
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(qualified, None)
        raise
    setattr(sys.modules[package], name, module)
    return module
