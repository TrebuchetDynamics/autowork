"""Compatibility entrypoint; implementation belongs to Src/autowork_runtime."""
import importlib.util as _importlib_util
from pathlib import Path as _Path

_bootstrap_path = _Path(__file__).resolve().parent / 'autowork_bootstrap.py'
_bootstrap_spec = _importlib_util.spec_from_file_location(__name__ + '._bootstrap', _bootstrap_path)
_bootstrap = _importlib_util.module_from_spec(_bootstrap_spec)
exec(compile(_bootstrap_path.read_bytes(), str(_bootstrap_path), 'exec'), _bootstrap.__dict__)
_bootstrap.execute(globals(), 'Src/autowork_runtime/setup_preflight.py')
