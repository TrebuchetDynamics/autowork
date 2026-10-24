"""The runner's selected-release layout; independent of cwd and import search paths."""
import importlib.util
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location('_autowork_layout_bootstrap', _root / 'autowork_bootstrap.py')
_bootstrap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bootstrap)
Layout = _bootstrap.Layout
load = _bootstrap.load
LAYOUT = Layout(_root)
