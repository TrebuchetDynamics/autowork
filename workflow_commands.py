"""Compatibility entry; execute this release's native source in the host namespace."""
import importlib.util as _importlib_util
from pathlib import Path as _Path

_spec = _importlib_util.spec_from_file_location(
    __name__ + '._bootstrap', _Path(__file__).resolve().parent / 'autowork_bootstrap.py')
_bootstrap = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_bootstrap)
_bootstrap.execute(globals(), 'Src/autowork_runtime/workflow_commands.py')
