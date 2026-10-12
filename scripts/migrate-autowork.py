#!/usr/bin/env python3
"""Explicit, quiescent upgrade of old profile state; no job activation or dispatch."""
import argparse
import fcntl
import json
from pathlib import Path

LEGACY = 'autogoal'
CURRENT = 'autowork'


def migrate_state(home, apply=False):
    """Move state without rewriting signed/pinned evidence or resetting locks.

    A legacy path link is retained solely for historical receipts. New callers use
    the real current directory; this is not a skill or slash-command alias.
    Call only while the profile's scheduled/native workers are quiescent.
    """
    home = Path(home).absolute()
    if any(p.is_symlink() for p in (home, *home.parents)):
        raise ValueError('profile home must not traverse symlinks')
    old, new = home / LEGACY, home / CURRENT
    if old.is_symlink():
        if old.resolve() != new or not new.is_dir() or new.is_symlink():
            raise ValueError('unexpected legacy state link')
        return 'already_migrated'
    if not old.exists():
        return 'no_legacy_state'
    if not old.is_dir() or new.exists() or new.is_symlink():
        raise ValueError('conflicting state directories; reconcile before migration')
    # Match the locks used by owner_cycle and start_goal. Do not interrupt a writer.
    locks = []
    try:
        for name in ('.owner-cycle.lock', 'goal-handoff.lock'):
            path = old / name
            if path.is_symlink():
                raise ValueError('state lock must not be a symlink')
            if path.exists():
                stream = path.open('r+')
                locks.append(stream)
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not apply:
            return 'would_migrate'
        old.rename(new)
        old.symlink_to(CURRENT, target_is_directory=True)
        return 'migrated'
    finally:
        for stream in locks:
            stream.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    print(json.dumps({'state': migrate_state(args.home, args.apply)}))


if __name__ == '__main__':
    main()
