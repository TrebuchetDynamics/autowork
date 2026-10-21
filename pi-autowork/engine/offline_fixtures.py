"""Controlled host inputs for fake-worker CLI fixtures, never production runners."""
import os
from pathlib import Path


# A fixture's runtime directory is `<root>/awt-XXXXXXXX/aw-<uid>-<key>-<slot>`. The worker temp
# path rule (parallel_dispatch._tmp_record) allows 47 bytes, and a two-digit slot is the longest
# name, so the root itself has 14 bytes to spare.
RUNTIME_ROOT_BYTES = 14


def fixture_runtime_root():
    """A short, writable parent for a fixture's own runtime directory.

    Never `$XDG_RUNTIME_DIR`: that belongs to the session running the suite. On the fleet a
    stale one failed `setUp` outright, and a long one pushed the fixture's worker temp path
    past the 47-byte rule, so `$TMPDIR` silently fell back to `/tmp` and assertions about the
    runtime directory failed for a reason that had nothing to do with the code under test.
    The same `/var/tmp` then `/tmp` order that `parallel_dispatch.worker_root` falls back on.
    """
    for candidate in ('/var/tmp', '/tmp'):
        if (os.path.isdir(candidate) and os.access(candidate, os.W_OK)
                and len(os.fsencode(candidate)) <= RUNTIME_ROOT_BYTES):
            return candidate
    raise AssertionError('no short writable runtime root among /var/tmp and /tmp')


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
