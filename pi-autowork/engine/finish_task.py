"""Compatibility entry; implementation belongs to Src/pi_autowork/engine/finish_task.py."""
import importlib.util as _util
from pathlib import Path as _Path
import sys as _sys

_root = _Path(__file__).resolve().parents[2]
_spec = _util.spec_from_file_location('_autowork_entry_bootstrap', _root / 'autowork_bootstrap.py')
_bootstrap = _util.module_from_spec(_spec)
_spec.loader.exec_module(_bootstrap)
if __name__ == '__main__':
    _sys.exit(_bootstrap.run(_root, 'pi_autowork.engine.finish_task', _sys.argv[1:]))
else:
    _sys.modules.pop(__name__, None)
    _sys.modules[__name__] = _bootstrap.load(_root, 'pi_autowork.engine.finish_task')
