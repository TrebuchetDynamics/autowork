"""Small shared pieces of the pi-autowork runner: logging, Git and task wording."""
from datetime import datetime
import os
from pathlib import Path
import re
import subprocess
import sys


class Log:
    """`[HH:MM] text` on stdout; the same line with an ISO time in STATE/runner.log."""

    def __init__(self):
        self.state = None

    def _file(self, text):
        if self.state and Path(self.state).is_dir():
            with open(Path(self.state) / 'runner.log', 'a') as stream:
                stream.write(f'{datetime.now().astimezone().isoformat(timespec="seconds")} {text}\n')

    def say(self, text):
        print(f'[{datetime.now():%H:%M}] {text}', flush=True)
        self._file(text)

    def warn(self, text):
        """A warning-priority journal line under systemd (journald reads the <4> prefix)."""
        if os.environ.get('INVOCATION_ID'):
            print(f'<4>[{datetime.now():%H:%M}] {text}', flush=True)
            self._file(text)
        else:
            self.say(text)


LOG = Log()


def die(code, text):
    print(f'pi-autowork: {text}', file=sys.stderr, flush=True)
    sys.exit(code)


def git(repo, *argv, check=False):
    """stdout of `git -C repo argv`, stripped; None on failure unless check."""
    result = subprocess.run(['git', '-C', str(repo), *argv], capture_output=True, text=True)
    if result.returncode:
        if check:
            raise RuntimeError(result.stderr.strip() or f'git {argv[0]} failed')
        return None
    # NUL-separated (-z) output keeps its leading spaces: they are part of status codes.
    return result.stdout if '-z' in argv else result.stdout.strip()


def git_ok(repo, *argv):
    return subprocess.run(['git', '-C', str(repo), *argv], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0


def dirty(path):
    return git(path, 'status', '--porcelain=v1', '--untracked-files=all') or ''


def safe_name(text):
    return re.sub(r'[^A-Za-z0-9._-]', '-', text)


def provider_of(model):
    return model.split('/', 1)[0]


def model_of(model):
    return model.split('/', 1)[1] if '/' in model else model


def lifecycle(state):
    """Task lifecycle words for the engine's slot states."""
    return {'waiting': 'pending', 'pending': 'pending', '': 'pending', 'dispatched': 'running',
            'running': 'running', 'reported': 'implemented', 'integrating': 'verifying',
            'integrated': 'integrated', 'closed': 'done', 'held': 'failed', 'interrupted': 'failed',
            'released': 'failed'}.get(state or '', state)


def push_guard(env=os.environ):
    """Pushes from any git the runner, its workers or Pi's tools start fail; fetches work."""
    env.update(GIT_CONFIG_COUNT='2', GIT_CONFIG_KEY_0='url.pi-autowork-push-disabled:///.pushInsteadOf',
               GIT_CONFIG_VALUE_0='', GIT_CONFIG_KEY_1='protocol.pi-autowork-push-disabled.allow',
               GIT_CONFIG_VALUE_1='never')


def summary_list(rows, label=lambda r: f"{r.get('id') or r.get('task')}: {r.get('reason')}"):
    """First four `id: reason` entries, then a count of the rest."""
    items = [label(r) for r in rows]
    if not items:
        return ''
    return '; '.join(items[:4]) + (f' (+{len(items) - 4} more; see --status)' if len(items) > 4 else '')


def open_for_writing(paths):
    """Those of ``paths`` some process holds open for writing (Linux /proc)."""
    wanted = {str(Path(p).resolve()) for p in paths}
    found = set()
    for entry in Path('/proc').glob('[0-9]*'):
        try:
            fds = list((entry / 'fd').iterdir())
        except OSError:
            continue
        for link in fds:
            try:
                target = os.readlink(link)
                if target not in wanted:
                    continue
                flags = int(re.search(r'^flags:\s+([0-7]+)', (entry / 'fdinfo' / link.name).read_text(), re.M)[1], 8)
            except (OSError, TypeError):
                continue
            if flags & os.O_ACCMODE:
                found.add(target)
    return found
