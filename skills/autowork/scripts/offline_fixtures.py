"""Controlled host inputs for fake-worker CLI fixtures, never production runners."""
import os
from pathlib import Path


def idle_host_env(root):
    """Give CLI children a small positive load, independent of the owner's fleet.

    Keep the real gate and its explicit AUTOWORK_GATE_CPUS override: 0.01 permits
    ordinary scenarios even on one CPU, while a tiny threshold still refuses them.
    """
    shim = Path(root) / 'idle-host'
    shim.mkdir()
    (shim / 'sitecustomize.py').write_text('import os\nos.getloadavg = lambda: (0.01, 0.01, 0.01)\n')
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join(filter(None, [str(shim), env.get('PYTHONPATH')]))
    return env
