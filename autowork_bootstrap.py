"""Load only this release's shared bootstrap, including path-based native callers."""
import hashlib as _hashlib
from pathlib import Path as _Path
import sys as _sys
import types as _types

_root = _Path(__file__).resolve().parent
_source = _root / 'Src/autowork_bootstrap.py'
if not _source.resolve().is_relative_to(_root):
    raise ImportError('bootstrap source escapes selected release')
_key = '_autowork_bootstrap_' + _hashlib.sha256(str(_source).encode()).hexdigest()
_bootstrap = _sys.modules.get(_key)
if _bootstrap is None:
    _bootstrap = _types.ModuleType(_key)
    _bootstrap.__file__ = str(_source)
    _sys.modules[_key] = _bootstrap
    try:
        exec(compile(_source.read_bytes(), str(_source), 'exec'), _bootstrap.__dict__)
    except BaseException:
        _sys.modules.pop(_key, None)
        raise
elif _Path(_bootstrap.__file__).resolve() != _source:
    raise ImportError('foreign Autowork bootstrap')

Layout = _bootstrap.Layout
activate = _bootstrap.activate
load = _bootstrap.load
run = _bootstrap.run
execute = _bootstrap.execute
peer = _bootstrap.peer
