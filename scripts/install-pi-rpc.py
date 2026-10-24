#!/usr/bin/env python3
"""Explicit, hash-pinned RPC SDK installation, separate from global Python and Pi."""
import argparse
import fcntl
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import venv

VERSION = '0.2.6'
REQUIREMENTS = Path(__file__).resolve().parents[1] / 'pi-autowork/requirements-rpc.txt'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root',type=Path,default=Path(os.environ.get('PI_AUTOWORK_STATE_DIR') or
                        Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'pi-autowork'))
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--wheelhouse',type=Path,help='Install offline from this wheel directory only')
    args=parser.parse_args()
    target=args.state_root.resolve()/'runtimes'/f'pi-rpc-{VERSION}'
    flags=['-m','pip','--isolated','install','--disable-pip-version-check','--require-hashes',
           '--only-binary=:all:','--no-deps','-r',str(REQUIREMENTS)]
    if args.wheelhouse:
        flags += ['--no-index','--find-links',str(args.wheelhouse.resolve())]
    if args.dry_run:
        print('Create isolated Python environment:',target)
        print(shlex.join([str(target/'bin/python'),*flags]))
        print('No Pi upgrade, credentials, global Python or services changed.')
        return 0
    if sys.version_info < (3,11):
        parser.error('Python 3.11 or later is required')
    target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (target.parent/'.install.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if not target.exists():
            # Venv activation files and executable shebangs contain absolute paths.
            # Build at the final path under the install lock, never rename a venv.
            target.mkdir(mode=0o700)
            try:
                # Managed Python builds require the resolved interpreter link.
                venv.EnvBuilder(with_pip=True, symlinks=True).create(target)
                subprocess.run([str(target/'bin/python'),*flags],check=True)
            except BaseException:
                shutil.rmtree(target)  # Only the new environment created by this call.
                raise
        result=subprocess.run([str(target/'bin/python'),'-c',
                               "from importlib.metadata import version; print(version('pi-agent-python-sdk'))"],
                              capture_output=True,text=True,check=True)
        if result.stdout.strip()!=VERSION:
            parser.error('Existing runtime environment has the wrong SDK; refusing to overwrite it')
    print('RPC SDK ready:',target/'bin/python')
    print('Qualified Pi version: 1.4.0. No Pi upgrade or service restart performed.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
