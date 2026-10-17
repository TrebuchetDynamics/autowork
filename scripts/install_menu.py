#!/usr/bin/env python3
"""Install autowork's components from one menu: every item checked by default.

    install.sh                 a checkbox menu on a terminal (arrows, Space, Enter)
    install.sh --all           everything available, no menu
    install.sh --only tx,pi    just these; --skip hermes leaves those out
    install.sh --list          the items and whether each host is available
    install.sh --dry-run ...   print each command instead of running it

Each item runs the host's own supported install command; a host whose CLI is not
installed is skipped and says so. Hermes options (--hermes-home, --bundle-only,
--no-reload, --yes-deps) apply to the Hermes item. Standard library only.
"""
import argparse
from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'TrebuchetDynamics/autowork'
PI_SOURCE = 'git:github.com/TrebuchetDynamics/autowork'
OLD_PI_SOURCE = 'git:github.com/TrebuchetDynamics/hermes-toolset'  # the package's name before the rename
HOME = Path(os.environ.get('HOME', str(Path.home())))
BIN = Path(os.environ.get('AUTOWORK_BIN_DIR') or HOME / '.local' / 'bin')


@dataclass
class Step:
    describe: str                   # what this step does, for --dry-run and the summary
    argv: list = None               # a command to run, or
    run: object = None              # a Python callable returning a message


@dataclass
class Item:
    key: str
    label: str
    needs: str = ''                 # the host CLI this item needs, '' for none
    note: str = ''                  # why it is unavailable or what is special
    steps: list = field(default_factory=list)

    @property
    def available(self):
        return not self.needs or shutil.which(self.needs) is not None


def pi_package(source=PI_SOURCE):
    """The directory Pi installed this package source in, or None."""
    if not shutil.which('pi'):
        return None
    try:
        lines = subprocess.run(['pi', 'list'], capture_output=True, text=True, timeout=60).stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        return None
    for i, line in enumerate(lines):
        if line.strip() == source and i + 1 < len(lines):
            return Path(lines[i + 1].strip())
    return None


def move_services():
    """Point the pi-autowork service unit at the autowork package and restart running services.

    The package used to be installed as hermes-toolset, and the one template unit runs its
    script from there; it must move before that package is removed. Running services
    restart (workers pause and resume on the same attempt).
    """
    package = pi_package()
    if package is None:
        raise OSError('the autowork Pi package is not installed')
    config = Path(os.environ.get('XDG_CONFIG_HOME') or HOME / '.config')
    unit = config / 'systemd' / 'user' / 'pi-autowork@.service'
    if not unit.is_file():
        return 'no pi-autowork service unit to move'
    text = unit.read_text()
    script = package / 'scripts' / 'pi-autowork.sh'
    new = re.sub(r'(?m)^(ExecStart=\S*bash )\S*pi-autowork\.sh ', rf'\g<1>{script} ', text)
    if new == text:
        return f'the service unit already runs {script}'
    unit.write_text(new)
    systemctl = os.environ.get('PI_AUTOWORK_SYSTEMCTL', 'systemctl')
    subprocess.run([systemctl, '--user', 'daemon-reload'], check=True)
    active = [line.split()[0] for line in subprocess.run(
        [systemctl, '--user', 'list-units', 'pi-autowork@*', '--state=active', '--plain', '--no-legend'],
        capture_output=True, text=True).stdout.splitlines() if line.strip()]
    for name in active:
        subprocess.run([systemctl, '--user', 'restart', name], check=True)
    return f'the service unit runs {script}' + (f'; restarted {", ".join(active)}' if active else '')


def link(target, name):
    """~/.local/bin/<name> -> target; an existing different file is kept as <name>.bak."""
    BIN.mkdir(parents=True, exist_ok=True)
    path = BIN / name
    if path.is_symlink() and Path(os.readlink(path)) == target:
        return f'{path} already links to {target}'
    if path.exists() or path.is_symlink():
        backup = path.with_name(name + '.bak')
        os.replace(path, backup)
        note = f' (the old one is {backup})'
    else:
        note = ''
    path.symlink_to(target)
    return f'{path} -> {target}{note}'


def install_tx():
    """tx and its completions; tmux config and helpers only where none exist yet."""
    BIN.mkdir(parents=True, exist_ok=True)
    done = []
    target = BIN / 'tx'
    source = ROOT / 'tmux' / 'tx'
    if target.is_file() and target.read_bytes() == source.read_bytes():
        done.append(f'{target} is current')
    else:
        if target.exists():
            shutil.copy2(target, target.with_name('tx.bak'))
        shutil.copy2(source, target)
        target.chmod(0o755)
        done.append(f'installed {target}')
    for shell, folder, name in (('bash', HOME / '.local/share/bash-completion/completions', 'tx'),
                                ('zsh', HOME / '.zsh/completions', '_tx'),
                                ('fish', HOME / '.config/fish/completions', 'tx.fish')):
        text = subprocess.run(['bash', str(source), 'completion', shell], capture_output=True, text=True).stdout
        if text:
            folder.mkdir(parents=True, exist_ok=True)
            (folder / name).write_text(text)
    done.append('completions for bash, zsh and fish')
    kept = []
    for src, dest in ((ROOT / 'tmux/tmux.conf', HOME / '.tmux.conf'),
                      (ROOT / 'tmux/style.tmux', HOME / '.tmux/style.tmux'),
                      (ROOT / 'tmux/git-status.sh', HOME / '.tmux/git-status.sh'),
                      (ROOT / 'tmux/short-path.sh', HOME / '.tmux/short-path.sh')):
        if dest.exists():
            kept.append(dest.name)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text()
        if dest.name == '.tmux.conf':  # point the status bar at the installed helpers
            text = text.replace('~/.tmux/', f'{HOME}/.tmux/')
        dest.write_text(text)
        if dest.suffix == '.sh':
            dest.chmod(0o755)
        done.append(f'installed {dest}')
    if kept:
        done.append('kept your existing ' + ', '.join(kept))
    return '; '.join(done)


def items(hermes_args):
    package, old = pi_package(), pi_package(OLD_PI_SOURCE)
    pi = Item('pi', 'Pi package', needs='pi', note='needs Node 22+')
    if not package:
        pi.steps.append(Step(f'pi install {PI_SOURCE}', ['pi', 'install', PI_SOURCE]))
    if old:
        pi.note = f'replaces the hermes-toolset package at {old}'
        pi.steps += [Step('point the pi-autowork service unit at the autowork package', run=move_services),
                     Step(f'pi remove {OLD_PI_SOURCE}', ['pi', 'remove', OLD_PI_SOURCE])]
    elif package:
        pi.note = f'installed at {package}; its runners update it themselves at a safe point'
    # The command follows the package the runners update, once it is installed.
    def command():
        installed = pi_package()
        return installed / 'pi-autowork/bin/autowork' if installed else ROOT / 'pi-autowork/bin/autowork'
    return [
        pi,
        Item('autowork', 'autowork command and TUI', note='TUI and web view need uv',
             steps=[Step(f'link {BIN}/autowork to the autowork release', run=lambda: link(command(), 'autowork'))]),
        Item('tx', 'tx tmux session launcher', note='keeps your existing ~/.tmux.conf',
             steps=[Step(f'install {BIN}/tx and completions', run=install_tx)]),
        Item('hermes', 'Hermes plugin (sets up every live profile)', needs='hermes',
             steps=[Step('setup_bundle.py ' + ' '.join(hermes_args), [sys.executable, str(ROOT / 'setup_bundle.py'),
                                                                    *hermes_args])]),
        Item('claude', 'Claude Code plugin', needs='claude',
             steps=[Step(f'claude plugin marketplace add {SOURCE}', ['claude', 'plugin', 'marketplace', 'add', SOURCE]),
                    Step('claude plugin install autowork@autowork', ['claude', 'plugin', 'install', 'autowork@autowork'])]),
        Item('codex', 'Codex plugin', needs='codex',
             steps=[Step(f'codex plugin marketplace add {SOURCE} --ref main',
                         ['codex', 'plugin', 'marketplace', 'add', SOURCE, '--ref', 'main']),
                    Step('codex plugin add autowork@autowork-marketplace',
                         ['codex', 'plugin', 'add', 'autowork@autowork-marketplace'])]),
    ]


def describe(item):
    if not item.available:
        return f'{item.needs} not found'
    return item.note


# -- choosing ---------------------------------------------------------------------
def choose_curses(all_items, chosen):
    import curses

    def ui(screen):
        curses.curs_set(0)
        row = 0
        while True:
            screen.erase()
            screen.addstr(0, 0, 'autowork installer: Space toggles, a all, n none, Enter installs, q quits')
            for i, item in enumerate(all_items):
                box = '[x]' if item.key in chosen else '[ ]'
                text = f' {box} {item.label:<44} {describe(item)}'
                screen.addstr(2 + i, 0, text[:curses.COLS - 1], curses.A_REVERSE if i == row else 0)
            key = screen.getch()
            if key in (curses.KEY_UP, ord('k')):
                row = (row - 1) % len(all_items)
            elif key in (curses.KEY_DOWN, ord('j')):
                row = (row + 1) % len(all_items)
            elif key == ord(' '):
                item = all_items[row]
                if item.available:
                    chosen.symmetric_difference_update({item.key})
            elif key == ord('a'):
                chosen.update(i.key for i in all_items if i.available)
            elif key == ord('n'):
                chosen.clear()
            elif key in (10, 13, curses.KEY_ENTER):
                return True
            elif key in (ord('q'), 27):
                return False
    return curses.wrapper(ui)


def choose_text(all_items, chosen, read=input, write=print):
    while True:
        write('\nautowork installer (all available items are checked):')
        for i, item in enumerate(all_items, 1):
            write(f"  [{'x' if item.key in chosen else ' '}] {i} {item.label:<44} {describe(item)}")
        answer = read('Toggle numbers (e.g. 4 5), a = all, n = none, Enter = install, q = quit: ').strip().lower()
        if answer == '':
            return True
        if answer == 'q':
            return False
        if answer == 'a':
            chosen.update(i.key for i in all_items if i.available)
            continue
        if answer == 'n':
            chosen.clear()
            continue
        for part in answer.replace(',', ' ').split():
            if part.isdigit() and 1 <= int(part) <= len(all_items) and all_items[int(part) - 1].available:
                chosen.symmetric_difference_update({all_items[int(part) - 1].key})


# -- installing -------------------------------------------------------------------
def install(all_items, chosen, dry_run=False, write=print):
    results = []
    for item in all_items:
        if item.key not in chosen:
            results.append((item.key, 'skipped', describe(item) if not item.available else 'not chosen'))
            continue
        if not item.steps:
            results.append((item.key, 'skipped', item.note))
            continue
        write(f'\n== {item.label}')
        outcome, detail = 'installed', []
        for step in item.steps:
            write(f'  {step.describe}')
            if dry_run:
                detail.append('dry run')
                continue
            try:
                if step.run:
                    detail.append(step.run())
                else:
                    result = subprocess.run(step.argv, capture_output=True, text=True)
                    text = (result.stdout + result.stderr).strip()
                    if result.returncode and 'already' not in text.lower():
                        outcome = 'failed'
                        detail.append(text.splitlines()[-1] if text else f'exit {result.returncode}')
                        break
                    detail.append('already there' if result.returncode else 'ok')
            except (OSError, subprocess.SubprocessError) as exc:
                outcome = 'failed'
                detail.append(str(exc))
                break
        results.append((item.key, 'planned' if dry_run else outcome, '; '.join(d for d in detail if d)))
    write('\nSummary:')
    for key, outcome, detail in results:
        write(f'  {key:<9} {outcome:<9} {detail}')
    return 1 if any(outcome == 'failed' for _, outcome, _ in results) else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--all', action='store_true', help='install every available item without a menu')
    parser.add_argument('--only', help='comma-separated items to install (pi,autowork,tx,hermes,claude,codex)')
    parser.add_argument('--skip', help='comma-separated items to leave out')
    parser.add_argument('--list', action='store_true', help='show the items and whether each is available')
    parser.add_argument('--dry-run', action='store_true', help='print each command instead of running it')
    parser.add_argument('--menu', action='store_true', help='always show the menu')
    for flag in ('--bundle-only', '--no-reload', '--yes-deps'):
        parser.add_argument(flag, action='store_true', help='passed to the Hermes item')
    parser.add_argument('--hermes-home', help='passed to the Hermes item')
    args = parser.parse_args(argv)
    hermes = [f for f, on in (('--bundle-only', args.bundle_only), ('--no-reload', args.no_reload),
                              ('--yes-deps', args.yes_deps), ('--dry-run', args.dry_run)) if on]
    if args.hermes_home:
        hermes += ['--hermes-home', args.hermes_home]
    all_items = items(hermes)
    keys = [i.key for i in all_items]
    for given in (args.only, args.skip):
        unknown = [k for k in (given or '').split(',') if k and k not in keys]
        if unknown:
            parser.error(f'unknown item(s): {", ".join(unknown)}; choose from {", ".join(keys)}')
    if args.list:
        for item in all_items:
            print(f"  {item.key:<9} {'available' if item.available else 'unavailable':<12} {item.label}"
                  + (f' ({describe(item)})' if describe(item) else ''))
        return 0
    chosen = {i.key for i in all_items if i.available}
    if args.only:
        chosen &= set(args.only.split(','))
    if args.skip:
        chosen -= set(args.skip.split(','))
    menu = args.menu or not (args.all or args.only or args.skip)
    if menu and not (sys.stdin.isatty() and sys.stdout.isatty()) and os.environ.get('AUTOWORK_INSTALL_UI') != 'text':
        parser.error('no terminal for the menu; choose with --all, --only or --skip (see --list)')
    if menu:
        try:
            go = choose_curses(all_items, chosen) if os.environ.get('AUTOWORK_INSTALL_UI') != 'text' \
                else choose_text(all_items, chosen)
        except Exception:  # no usable terminal for curses: the numbered menu
            go = choose_text(all_items, chosen)
        if not go:
            print('Nothing installed.')
            return 0
    return install(all_items, chosen, dry_run=args.dry_run)


if __name__ == '__main__':
    raise SystemExit(main())
