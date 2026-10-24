"""Select this release's canonical runner package."""
import importlib.util as _util
from pathlib import Path as _Path
import sys as _sys

_root = _Path(__file__).resolve().parents[2]
_spec = _util.spec_from_file_location('_autowork_entry_bootstrap', _root / 'autowork_bootstrap.py')
_bootstrap = _util.module_from_spec(_spec)
_spec.loader.exec_module(_bootstrap)
_sys.modules.pop(__name__, None)
_sys.modules[__name__] = _bootstrap.load(_root, 'pi_autowork')
