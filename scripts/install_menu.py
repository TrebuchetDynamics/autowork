#!/usr/bin/env python3
"""Install the full Autowork suite with verbose output by default.

    install.sh                every available component, live output and exact commands
    install.sh --menu         a checkbox menu on a terminal (arrows, Space, Enter)
    install.sh --full          the full suite for available hosts, no menu (--all also works)
    install.sh --only tx,pi    just these; --skip hermes leaves those out
    install.sh --list          the items and whether each host is available
    install.sh --dry-run ...   print each command instead of running it

Each item runs the host's own supported install command; a host whose CLI is not
installed is skipped and says so, and fails when named with --only. Hermes options
(--hermes-home, --bundle-only, --no-reload, --yes-deps) apply to the Hermes item.
Standard library only.
"""
import argparse
import codecs
import json
from dataclasses import dataclass, field
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'TrebuchetDynamics/autowork'
PI_SOURCE = 'git:github.com/TrebuchetDynamics/autowork'
HOME = Path(os.environ.get('HOME', str(Path.home())))
BIN = Path(os.environ.get('AUTOWORK_BIN_DIR') or HOME / '.local' / 'bin')


class Output:
    """Flush progress immediately; color only where requested or supported."""
    COLORS = {'heading': '1;36', 'installed': '32', 'failed': '31',
              'skipped': '33', 'planned': '36', 'command': '2'}

    def __init__(self, color='auto', verbosity=2):
        self.verbosity = verbosity
        self.color = color == 'always' or (color == 'auto' and sys.stdout.isatty()
                      and os.environ.get('TERM') != 'dumb' and not os.environ.get('NO_COLOR'))

    def line(self, message='', style=''):
        if self.color and style in self.COLORS:
            message = f'\033[{self.COLORS[style]}m{message}\033[0m'
        print(message, flush=True)

    def raw(self, message):
        print(message, end='', flush=True)


def run_command(argv, output):
    """Stream both child channels, including prompts without a trailing newline.

    Keep a bounded diagnostic tail for quiet failures; stdin remains inherited.
    Quiet mode still shows native prompts/output when input is a terminal.
    """
    env = dict(os.environ, PYTHONUNBUFFERED='1')
    if not output.color:
        env['NO_COLOR'] = '1'
    stream = output.verbosity > 0 or sys.stdin.isatty()
    decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
    tail = ''
    with subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env) as child:
        try:
            while chunk := child.stdout.read1(4096):
                text = decoder.decode(chunk)
                tail = (tail + text)[-16384:]
                if stream:
                    output.raw(text)
            text = decoder.decode(b'', final=True)
            tail = (tail + text)[-16384:]
            if stream:
                output.raw(text)
            code = child.wait()
        except BaseException:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
            raise
    if stream and tail and not tail.endswith('\n'):
        output.line()
    if code and not stream and tail:
        output.line(tail.rstrip(), 'failed')
    return code, tail.strip()


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
    missing: str = ''               # what else it needs that is absent, '' for nothing
    refuse: str = ''                # why the selected options cannot be honored

    @property
    def available(self):
        return not self.missing and (not self.needs or shutil.which(self.needs) is not None)


def pi_package(source=PI_SOURCE):
    """The directory Pi installed this package source in, or None."""
    if not shutil.which('pi'):
        return None
    try:
        lines = subprocess.run(['pi', 'list'], capture_output=True, text=True, timeout=60).stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        return None
    for i, line in enumerate(lines):
        # Pi marks a package with a filter as `<source> (filtered)`.
        if line.split()[:1] == [source] and i + 1 < len(lines):
            return Path(lines[i + 1].strip())
    return None


def set_aside(path):
    """Move a file or symlink out of the way as <name>.bak, or .bak.N if that is taken,
    so an earlier backup is never overwritten. Return where it went."""
    backup, n = path.with_name(path.name + '.bak'), 1
    while backup.exists() or backup.is_symlink():
        backup, n = path.with_name(f'{path.name}.bak.{n}'), n + 1
    os.replace(path, backup)
    return backup


def link(target, name):
    """~/.local/bin/<name> -> target; an existing different file is kept as a backup."""
    BIN.mkdir(parents=True, exist_ok=True)
    path = BIN / name
    if path.is_symlink() and Path(os.readlink(path)) == target:
        return f'{path} already links to {target}'
    note = f' (the old one is {set_aside(path)})' if path.exists() or path.is_symlink() else ''
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
        # Move the old one, a symlink included, rather than write through it: a link
        # may point into another checkout.
        note = f' (the old one is {set_aside(target)})' if target.exists() or target.is_symlink() else ''
        shutil.copy2(source, target)
        target.chmod(0o755)
        done.append(f'installed {target}{note}')
    for shell, folder, name in (('bash', HOME / '.local/share/bash-completion/completions', 'tx'),
                                ('zsh', HOME / '.zsh/completions', '_tx'),
                                ('fish', HOME / '.config/fish/completions', 'tx.fish')):
        dest = folder / name
        if dest.exists() or dest.is_symlink():
            continue
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
        if dest.exists() or dest.is_symlink():
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


def hermes_home(hermes_args):
    """(home, given): the Hermes home the item works on, and whether it was named."""
    given = hermes_args[hermes_args.index('--hermes-home') + 1] if '--hermes-home' in hermes_args else ''
    named = given or os.environ.get('HERMES_HOME')
    return Path(named or HOME / '.hermes'), bool(named)


def hermes_installed(hermes_args):
    """The Hermes home when a profile already has its own Autowork plugin checkout (a
    `hermes plugins install` clone): those are updated, not linked to this checkout."""
    home, _ = hermes_home(hermes_args)
    for plugin in [home / 'plugins/autowork', *home.glob('profiles/*/plugins/autowork')]:
        if (plugin / '.git').exists() and plugin.resolve() != ROOT.resolve():
            return home
    return None


SETUP_ONLY = ('--bundle-only', '--no-reload', '--yes-deps')


def hermes_item(hermes_args):
    label = 'Hermes plugin (sets up every live profile)'
    home = hermes_installed(hermes_args)
    if home:
        argv = [sys.executable, str(ROOT / 'update_bundle.py'), '--hermes-home', str(home)]
        item = Item('hermes', label, needs='hermes',
                    steps=[Step(f'update_bundle.py --hermes-home {home} (the profiles\' installed plugin)', argv)])
        # update_bundle.py has none of these and restarts gateways, so it cannot honor them.
        unsupported = [flag for flag in SETUP_ONLY if flag in hermes_args]
        if unsupported:
            item.refuse = (f'{", ".join(unsupported)} cannot apply: profiles here have their own plugin clone, '
                           f'which update_bundle.py updates; rerun without them')
        return item
    item = Item('hermes', label, needs='hermes',
                steps=[Step('setup_bundle.py ' + ' '.join(hermes_args),
                            [sys.executable, str(ROOT / 'setup_bundle.py'), *hermes_args])])
    home, named = hermes_home(hermes_args)
    if not named and not home.is_dir():  # a named home is checked by setup_bundle.py itself
        item.missing = f'no Hermes home at {home}; start hermes once first'
    return item


def drop_claude_plugin():
    """Claude Code caches a plugin by its version, which changes rarely: a reinstall of the same
    version kept the old workflows (sessions lacked two skills a release had added). Uninstalling
    first makes the install copy the current release; not being installed yet is fine."""
    done = subprocess.run(['claude', 'plugin', 'uninstall', '--keep-data', 'autowork@autowork'], stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, timeout=120)
    return 'dropped the cached plugin' if done.returncode == 0 else 'no cached plugin to drop'


def drop_codex_plugin():
    """Codex caches a plugin by its version too (see drop_claude_plugin)."""
    done = subprocess.run(['codex', 'plugin', 'remove', 'autowork@autowork-marketplace'], stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, timeout=120)
    return 'dropped the cached plugin' if done.returncode == 0 else 'no cached plugin to drop'


def items(hermes_args):
    package = pi_package()
    pi = Item('pi', 'Pi package', needs='pi', note='needs Node 22+')
    if package:
        pi.note = f'installed at {package}; its runners update it themselves at a safe point'
    else:
        pi.steps.append(Step(f'pi install {PI_SOURCE}', ['pi', 'install', PI_SOURCE]))
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
        hermes_item(hermes_args),
        Item('claude', 'Claude Code plugin and full portable skill suite', needs='claude',
             steps=[Step(f'claude plugin marketplace add {SOURCE}', ['claude', 'plugin', 'marketplace', 'add', SOURCE]),
                    Step('claude plugin marketplace update autowork',
                         ['claude', 'plugin', 'marketplace', 'update', 'autowork']),
                    Step('drop the cached plugin, keeping its data', run=drop_claude_plugin),
                    Step('claude plugin install autowork@autowork', ['claude', 'plugin', 'install', 'autowork@autowork'])]),
        Item('codex', 'Codex plugin and full portable skill suite', needs='codex',
             steps=[Step(f'codex plugin marketplace add {SOURCE} --ref main',
                         ['codex', 'plugin', 'marketplace', 'add', SOURCE, '--ref', 'main']),
                    Step('codex plugin marketplace upgrade autowork-marketplace',
                         ['codex', 'plugin', 'marketplace', 'upgrade', 'autowork-marketplace']),
                    Step('drop the cached plugin', run=drop_codex_plugin),
                    Step('codex plugin add autowork@autowork-marketplace',
                         ['codex', 'plugin', 'add', 'autowork@autowork-marketplace'])]),
    ]


def describe(item):
    if item.needs and shutil.which(item.needs) is None:
        return f'{item.needs} not found'
    return item.missing or item.note


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
def install(all_items, chosen, dry_run=False, output=None):
    output = output or Output()
    results = []
    # Private machine-readable progress for update_bundle.py, separate from native output.
    report = os.environ.get('AUTOWORK_INSTALL_REPORT')
    if report:
        Path(report).write_text('')

    def record(key, status, detail, code=None):
        results.append((key, status, detail))
        if report:
            with Path(report).open('a') as stream:
                stream.write(json.dumps({'item': key, 'status': status, 'exit': code}) + '\n')

    total = len(chosen)
    current = 0
    started = time.monotonic()
    if output.verbosity or dry_run:
        output.line('Autowork full suite installer' + (' — preview' if dry_run else ''), 'heading')
        output.line('Selected: ' + (', '.join(i.key for i in all_items if i.key in chosen) or 'none'))
    for item in all_items:
        if item.key not in chosen:
            record(item.key, 'skipped', describe(item) if not item.available else 'not chosen')
            continue
        current += 1
        if output.verbosity or dry_run:
            output.line(f'\n[{current}/{total}] {item.label}', 'heading')
        if not item.available or item.refuse:
            record(item.key, 'failed', item.refuse or describe(item), 1)
            if item.refuse:
                output.line(f'  FAILED: {item.refuse}', 'failed')
            continue
        if not item.steps:
            record(item.key, 'skipped', item.note)
            continue
        outcome, detail, exit_code = 'installed', [], 0
        for index, step in enumerate(item.steps, 1):
            if output.verbosity or dry_run:
                output.line(f'  ({index}/{len(item.steps)}) {step.describe}')
            if step.argv and (output.verbosity > 1 or dry_run):
                output.line('  $ ' + shlex.join(step.argv), 'command')
            if dry_run:
                detail.append('dry run')
                continue
            step_started = time.monotonic()
            try:
                if step.run:
                    message = step.run()
                    detail.append(message)
                    if output.verbosity:
                        output.line('  ' + message)
                else:
                    code, text = run_command(step.argv, output)
                    if code:
                        outcome, exit_code = 'failed', code
                        cause = text.splitlines()[-1] if text else 'command failed'
                        detail.append(f'{cause} (exit {code})')
                        output.line(f'  FAILED: {step.describe} (exit {code})', 'failed')
                        break
                    detail.append('ok')
                if output.verbosity:
                    output.line(f'  Done in {time.monotonic() - step_started:.1f}s', 'installed')
            except (OSError, subprocess.SubprocessError) as exc:
                outcome, exit_code = 'failed', 1
                detail.append(str(exc))
                output.line(f'  FAILED: {exc}', 'failed')
                break
        record(item.key, 'planned' if dry_run else outcome, '; '.join(d for d in detail if d),
               None if dry_run else exit_code)
    output.line('\nSummary:', 'heading')
    for key, outcome, detail in results:
        output.line(f'  {key:<9} {outcome:<9} {detail}', outcome)
    counts = {state: sum(outcome == state for _, outcome, _ in results)
              for state in ('installed', 'planned', 'skipped', 'failed')}
    output.line('\n' + ', '.join(f'{count} {state}' for state, count in counts.items())
                + f' — {time.monotonic() - started:.1f}s', 'failed' if counts['failed'] else 'heading')
    if any(key in ('claude', 'codex', 'pi') and outcome == 'installed' for key, outcome, _ in results):
        output.line('Open a new host session to discover the installed skills.')
    return int(bool(counts['failed']))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--all', '--full', action='store_true', help='install the full suite for every available host (default)')
    selection.add_argument('--only', help='comma-separated items to install (pi,autowork,tx,hermes,claude,codex)')
    parser.add_argument('--skip', help='comma-separated items to leave out')
    parser.add_argument('--list', action='store_true', help='show the items and whether each is available')
    parser.add_argument('--dry-run', action='store_true', help='print each command instead of running it')
    parser.add_argument('--menu', action='store_true', help='choose components using the checkbox menu')
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument('-v', '--verbose', action='store_true', help='show exact commands as well as live output (default)')
    verbosity.add_argument('-q', '--quiet', action='store_true', help='show summary and failures only (native terminal prompts remain visible)')
    parser.add_argument('--color', choices=('auto', 'always', 'never'), default='auto',
                        help='color output (default: auto; respects NO_COLOR)')
    for flag in ('--bundle-only', '--no-reload', '--yes-deps'):
        parser.add_argument(flag, action='store_true', help='passed to the Hermes item')
    parser.add_argument('--hermes-home', help='passed to the Hermes item')
    args = parser.parse_args(argv)
    output = Output(args.color, 0 if args.quiet else 2)
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
            output.line(f"  {item.key:<9} {'available' if item.available else 'unavailable':<12} {item.label}"
                  + (f' ({describe(item)})' if describe(item) else ''),
                        'installed' if item.available else 'skipped')
        return 0
    chosen = {i.key for i in all_items if i.available}
    if args.only:
        chosen = {k for k in args.only.split(',') if k}
    if args.skip:
        chosen -= set(args.skip.split(','))
    menu = args.menu
    if menu and not (sys.stdin.isatty() and sys.stdout.isatty()) and os.environ.get('AUTOWORK_INSTALL_UI') != 'text':
        parser.error('no terminal for the menu; choose with --all, --only or --skip (see --list)')
    if menu:
        try:
            go = choose_curses(all_items, chosen) if os.environ.get('AUTOWORK_INSTALL_UI') != 'text' \
                else choose_text(all_items, chosen, write=output.line)
        except Exception:  # no usable terminal for curses: the numbered menu
            go = choose_text(all_items, chosen, write=output.line)
        if not go:
            print('Nothing installed.')
            return 0
    return install(all_items, chosen, dry_run=args.dry_run, output=output)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\nInstallation interrupted; completed steps remain installed.', file=sys.stderr)
        raise SystemExit(130)
