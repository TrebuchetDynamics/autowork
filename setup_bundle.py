"""Complete explicit bundle setup, then verify and rewire every live profile.

Runs only from install/setup entry points, never during plugin discovery.
"""
import argparse
import os
from pathlib import Path
import re
import subprocess
from setup_preflight import preflight, print_plan

ROOT = Path(__file__).resolve().parent


def live_profiles(root):
    if (root / 'profiles').is_symlink():
        raise ValueError('Refusing symlinked profiles directory')
    result = [('default', root)]
    markers = ('config.yaml', '.env', 'SOUL.md', 'profile.yaml', 'auth.json', 'state.db')
    for home in sorted((root / 'profiles').glob('*')):
        if home.is_symlink():
            raise ValueError(f'Refusing shared/symlinked profile: {home.name}')
        if (home.is_dir() and home.name != 'default'
                and re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', home.name)
                and not (root / 'profiles/.deleted' / home.name).exists()
                and any((home / m).is_file() or (home / m).is_symlink() for m in markers)):
            result.append((home.name, home))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hermes-home', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--bundle-only', action='store_true', help='Set up bundled skills and commands only')
    parser.add_argument('--no-reload', action='store_true', help='Explicitly defer live gateway wiring')
    parser.add_argument('--yes-deps', action='store_true')
    # Compatibility: full setup and enablement are now defaults.
    parser.add_argument('--setup', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--enable', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = (args.hermes_home or Path(os.environ.get('HERMES_HOME') or Path.home() / '.hermes')).expanduser()
    if root.parent.name == 'profiles': root = root.parent.parent
    root = root.resolve()
    if not root.is_dir(): parser.error(f'Hermes root does not exist: {root}')
    try:
        profiles = live_profiles(root)
    except ValueError as exc:
        parser.error(str(exc))
    for name in ('install-skills.sh', 'install-plugins.sh'):
        if not (ROOT / name).is_file(): parser.error(f'Missing installer: {name}')
    try:
        report = preflight(ROOT, root, profiles, bundle_only=args.bundle_only)
    except (ValueError, OSError, KeyError) as exc:
        print(f'Preflight failed ({type(exc).__name__}); no installation stages started.')
        return 1
    print_plan(report)
    if report['errors']:
        return 1
    if args.dry_run:
        print(f'Bundle setup preview: {len(profiles)} profiles; no installation stages started.')
        return 0
    common = ['--hermes-home', str(root)]
    if args.dry_run: common.append('--dry-run')
    plugins = ['bash', str(ROOT / 'install-plugins.sh'), '--sources-only', '--setup', '--enable', *common]
    if args.bundle_only: plugins.append('--bundle-only')
    if args.yes_deps: plugins.append('--yes-deps')
    env = dict(os.environ, HERMES_HOME=str(root))
    failures = []
    def run(label, command):
        print(f'Setup: {label}', flush=True)
        try:
            result = subprocess.run(command, cwd=ROOT, env=env, check=False)
            if result.returncode: failures.append(label)
        except OSError as exc:
            print(f'Failed: {label}: {exc}', flush=True)
            failures.append(label)
    run('bundled skills', ['bash', str(ROOT / 'install-skills.sh'), *common])
    run('plugins and configuration', plugins)
    for profile, home in profiles:
        if args.dry_run:
            print(f'Plan: verify bundled skills/plugins and refresh gateway ({profile})')
            continue
        command = ['hermes', '-p', profile, 'toolset', 'finalize', '--hermes-home', str(root)]
        if args.bundle_only: command.append('--bundle-only')
        if args.no_reload: command.append('--no-reload')
        # Even partially failed installs must refresh successful registrations and
        # expose missing capabilities. A later pass never masks an earlier failure.
        run(f'verify/wire {profile}', command)
    state = 'incomplete' if failures else ('preview' if args.dry_run else 'complete')
    print(f'Bundle setup {state}: {len(profiles)} profiles; {len(failures)} failed stages.')
    return int(bool(failures))


if __name__ == '__main__': raise SystemExit(main())
