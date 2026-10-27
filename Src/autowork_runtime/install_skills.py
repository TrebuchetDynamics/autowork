"""Idempotent offline provisioning shared by plugin loading and fleet setup."""
import argparse
import ctypes
import errno
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile


def _publish(staged, target):
    # POSIX rename can replace an empty owner directory; require no-replace.
    if os.name == 'nt':
        staged.rename(target)
        return
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == 'darwin':
        rename = libc.renamex_np
        rename.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint)
        arguments = (os.fsencode(staged), os.fsencode(target), 4)  # RENAME_EXCL
    else:
        rename = getattr(libc, 'renameat2', None)
        if rename is None:
            raise OSError(errno.ENOTSUP, 'Atomic no-replace publication is unavailable', str(target))
        rename.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
        arguments = (-100, os.fsencode(staged), -100, os.fsencode(target), 1)  # AT_FDCWD, RENAME_NOREPLACE
    rename.restype = ctypes.c_int
    if rename(*arguments):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(target))


def supplement_shared(source, target, *, dry_run=False):
    """Add missing shared Markdown only; never replace a profile's existing content."""
    if target.is_symlink():
        raise ValueError(f'Symlinked shared support destination: {target}')
    missing = [p for p in sorted(source.glob('*.md'))
               if not (target / p.name).exists() and not (target / p.name).is_symlink()]
    if dry_run or not missing:
        return len(missing)
    # Anchor POSIX publication to the actual directory, not a swappable symlink.
    anchored = os.link in os.supports_dir_fd and hasattr(os, 'O_NOFOLLOW')
    fd = os.open(target, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW) if anchored else None
    added = 0
    try:
        with tempfile.TemporaryDirectory(prefix='.install-shared-', dir=target.parent) as temporary:
            for source_file in missing:
                staged = Path(temporary) / source_file.name
                shutil.copy2(source_file, staged)
                try:
                    if fd is not None:
                        os.link(staged, source_file.name, dst_dir_fd=fd)
                    else:
                        # Windows rename is no-replace, like directory installation.
                        if target.is_symlink():
                            raise ValueError(f'Symlinked shared support destination: {target}')
                        _publish(staged, target / source_file.name)
                    added += 1
                except FileExistsError:
                    pass  # A concurrent writer's file wins, including a symlink.
    finally:
        if fd is not None:
            os.close(fd)
    return added


def install(source, profiles, *, dry_run=False, report=print, skills=None):
    if not source.is_dir() or source.is_symlink():
        raise ValueError(f'Missing or symlinked skills folder: {source}')
    if skills is None:
        skills = sorted(p for p in source.iterdir() if not p.name.startswith('.') and p.name not in {'__pycache__', 'repo-docs', 'repo-interview'} and p.is_dir())
    if not skills:
        raise ValueError(f'No skill folders found in {source}')
    ignore = shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo', '.pytest_cache', '.git', '.DS_Store')
    for skill in skills:
        shared_support = skill.name == 'shared' and all(
            (skill / name).is_file() for name in
            ('COMMON-CONTRACT.md', 'PLAN-HANDOFF.md', 'WORKTREE-ISOLATION.md'))
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', skill.name) or not (shared_support or (skill / 'SKILL.md').is_file()):
            raise ValueError(f'Invalid skill folder or missing SKILL.md: {skill}')
        if skill.is_symlink() or any(p.is_symlink() for p in skill.rglob('*')):
            raise ValueError(f'Symlinks are not supported inside source skills: {skill}')


    installed = skipped = planned = failed = 0
    for name, home in profiles:
        destination = home / 'skills'
        if home.is_symlink() or destination.is_symlink() or (destination.exists() and not destination.is_dir()):
            report(f'Failed: {name}: unsafe or non-directory destination {destination}')
            failed += 1
            continue
        for skill in skills:
            target = destination / skill.name
            required = ('COMMON-CONTRACT.md', 'PLAN-HANDOFF.md', 'WORKTREE-ISOLATION.md') if skill.name == 'shared' else ('SKILL.md',)
            if target.exists() or target.is_symlink():
                if not all((target / filename).is_file() for filename in required):
                    report(f'Failed: {skill.name} ({name}): incomplete existing skill at {target}; preserved')
                    failed += 1
                    continue
                if skill.name == 'shared':
                    try:
                        added = supplement_shared(skill, target, dry_run=dry_run)
                    except (OSError, ValueError) as error:
                        report(f'Failed: shared ({name}): {error}')
                        failed += 1
                        continue
                    if added:
                        report(f'{"Plan" if dry_run else "Installed"}: shared ({name}): '
                               f'{added} missing support files; existing files preserved')
                        if dry_run:
                            planned += 1
                        else:
                            installed += 1
                        continue
                report(f'Skip: {skill.name} ({name}) already exists: {target}')
                skipped += 1
                continue
            # shortcut: native one-level categories; extend if deeper categories are supported.
            categorized = next((p.parent for p in destination.glob(f'*/{skill.name}/SKILL.md')
                                if p.is_file() and not p.relative_to(destination).parts[0].startswith('.')), None)
            if categorized is not None:
                report(f'Skip: {skill.name} ({name}) already exists: {categorized}')
                skipped += 1
                continue
            if dry_run:
                report(f'Plan: {skill} -> {target} ({name})')
                planned += 1
                continue
            try:
                destination.mkdir(parents=True, exist_ok=True)
                # Publish only complete copies. Failed copies leave no partial skill.
                with tempfile.TemporaryDirectory(prefix='.install-skills-', dir=destination) as temporary:
                    staged = Path(temporary) / skill.name
                    shutil.copytree(skill, staged, ignore=ignore)
                    # Ignore rules can leave obsolete parents containing no support files.
                    for directory, _, _ in os.walk(staged, topdown=False):
                        directory = Path(directory)
                        if directory != staged and not any(directory.iterdir()):
                            directory.rmdir()
                    try:
                        _publish(staged, target)
                    except OSError:
                        if not all((target / filename).is_file() for filename in required):
                            raise
                        report(f'Skip: {skill.name} ({name}) installed concurrently: {target}')
                        skipped += 1
                        continue
                report(f'Installed: {skill.name} ({name})')
                installed += 1
            except OSError as error:
                report(f'Failed: {skill.name} ({name}): {error}')
                failed += 1
    report(f'Skills: {installed} installed, {planned} planned, {skipped} skipped, {failed} failed')
    return 1 if failed else 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='install-skills.sh',
        description='Copy local skills/ to default and all existing Hermes profiles. '
                    'Existing skills are preserved; missing shared Markdown is added. '
                    'No configuration or gateways are changed.')
    parser.add_argument('--dry-run', action='store_true', help='show destinations without writing')
    parser.add_argument('--hermes-home', type=Path, metavar='ROOT',
                        help='default Hermes root (otherwise HERMES_HOME or ~/.hermes)')
    parser.add_argument('--profile-home', type=Path, metavar='HOME',
                        help='install only into this profile (no fleet discovery)')
    args = parser.parse_args(argv)
    if args.hermes_home and args.profile_home:
        parser.error('--hermes-home and --profile-home are mutually exclusive')
    if args.profile_home:
        root = args.profile_home.expanduser()
        if not root.is_dir():
            parser.error(f'Hermes home does not exist: {root}')
        return install(Path(__file__).resolve().parent / 'skills', [('current', root)], dry_run=args.dry_run)
    root = args.hermes_home
    if root is None:
        root = Path(os.environ.get('HERMES_HOME') or Path.home() / '.hermes').expanduser()
        if root.parent.name == 'profiles':
            root = root.parent.parent
    root = root.expanduser().resolve()

    if not root.is_dir():
        parser.error(f'Hermes home does not exist: {root}')
    profiles = [('default', root)]
    profiles_root = root / 'profiles'
    markers = ('config.yaml', '.env', 'SOUL.md', 'profile.yaml', 'auth.json', 'state.db')
    if profiles_root.is_dir():
        for home in sorted(profiles_root.iterdir()):
            if (home.is_dir() and home.name != 'default'
                    and re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', home.name)
                    and not (profiles_root / '.deleted' / home.name).exists()
                    and any((home / marker).is_file() or (home / marker).is_symlink() for marker in markers)):
                profiles.append((home.name, home))

    return install(Path(__file__).resolve().parent / 'skills', profiles, dry_run=args.dry_run)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError) as error:
        print(f'Error: {error}', file=sys.stderr)
        sys.exit(1)
