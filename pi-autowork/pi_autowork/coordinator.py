"""The pi-autowork coordinator loop.

The toolset's Parallel Autowork engine (skills/autowork/scripts/owner_cycle.py) is
the only authority for task state: it plans, dispatches, verifies and closes. This
loop holds the engine lease (its PID is the owner) and supplies what the engine
leaves to the host: a session branch merged into the main branch at the end, Pi jobs
for Touches proposals and conflict resolution, health, requests, self-update and a
graceful stop. Every decision about a task is the engine's answer, not a guess here.
"""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from . import health, pi_runtime, questions, release, touches_inference, workspaces
from .common import LOG, dirty, git, git_ok, lifecycle, open_for_writing, safe_name, summary_list

IN_FLIGHT = ('dispatched', 'running', 'reported', 'integrating', 'integrated')
CONTRACT_CHANGED = 'task contract changed since integration; no close'
TOUCHES_PROMPT = (
    'Plan the file scope of task {task} in {checkout} so it can run beside other tasks. Read its entry in TODO.md, '
    'then the files and directories its Sources, Scope and acceptance name, and the repository layout around them. '
    'List the repository-relative files, directories (ending in /) or globs the task\'s change will edit, including '
    'its tests and docs; prefer a component\'s directory over guessing single files, and when unsure widen to the '
    'owning directories rather than give up: a worker that edits outside the list is only held and retried alone. '
    'Scope is about which files change, not how the result is checked: a task verified on a device, emulator, '
    'screenshot harness or live service still lists the code and test files it edits. Never list TODO.md, '
    'TODO.archive.md, goals.json or CHANGELOG.md. Answer NONE only when the task edits no repository file (purely '
    'live, manual or device operation) or would edit files across most of the repository, and give the reason. '
    'Do not change any file. End with exactly one line: PI_AUTOWORK_TOUCHES: path, path, ... or '
    'PI_AUTOWORK_TOUCHES: NONE - reason')
MERGE_PROMPT = (
    '/skill:git-commit-push This worktree is on branch {branch} with an unfinished merge of {base} that conflicts '
    "in: {files}. Resolve every conflict keeping both sides' work: keep both task entries in TODO.md and "
    'TODO.archive.md, keep every task record in goals.json and run python3 {goals} validate . if it exists, then '
    'run the checks that cover the conflicted files and conclude the merge with a commit. Do not push, rebase, '
    'switch branches or touch {repo}. End with one line: PI_AUTOWORK_RESULT: completed|blocked, then one sentence.')


class Finish(Exception):
    def __init__(self, code, text):
        super().__init__(text)
        self.code, self.text = code, text


class Coordinator:
    def __init__(self, cfg):
        self.cfg = cfg
        self.repo, self.base, self.toolset = cfg['repo'], cfg['base'], cfg['toolset']
        self.state = Path(cfg['state'])
        self.mode, self.workers = cfg['mode'], cfg['workers']
        env = os.environ
        self.interval = cfg['interval']
        self.max_cycles = cfg['max_cycles']
        self.verify_timeout = env.get('PI_AUTOWORK_VERIFY_TIMEOUT', '1800')
        self.task_timeout = env.get('PI_AUTOWORK_TASK_TIMEOUT', '5400')
        self.max_failures = int(env.get('PI_AUTOWORK_MAX_FAILURES', '3'))
        self.failure_pause = int(env.get('PI_AUTOWORK_FAILURE_PAUSE', '3600'))
        self.claim_idle = cfg['claim_idle']
        self.max_runtime = int(env.get('PI_AUTOWORK_MAX_RUNTIME', '0'))
        self.min_free_mb = env.get('PI_AUTOWORK_MIN_FREE_MB', '3000')
        self.update_interval = int(env.get('PI_AUTOWORK_UPDATE_INTERVAL', '3600'))
        self.plan_settle = float(env.get('PI_AUTOWORK_PLAN_SETTLE', '3'))
        self.plan_seen = None
        self.stall_after = env.get('PI_AUTOWORK_STALL_AFTER', '1800')
        self.engine_path = Path(self.toolset) / 'skills/autowork/scripts/owner_cycle.py'
        self.goals = Path(self.toolset) / 'skills/docs-sync/scripts/goals.py'
        self.touches_helper = Path(__file__).with_name('touches_inference.py')
        self.inferred_file = self.state / 'touches-inferred.json'
        self.touches_cache = self.state / ('touches-' + hashlib.sha256(
            TOUCHES_PROMPT.format(task='TASK', checkout='DIR').encode()).hexdigest()[:12] + '.json')
        self.worker_command = json.dumps(['/bin/bash', cfg['script'], '--worker', str(self.state), '{worktree}',
                                          '{prompt_file}', '{report_file}', '{timeout}'])
        self.started = time.monotonic()
        self.integ = self.integ_branch = None
        self.merge_pending, self.resolved_for, self.merge_blocker = '', '', ''
        self.waiting_merge = None  # what the last merge while waiting saw
        self.stop, self.paused, self.child = False, False, None
        self.started_workers = self.failures = 0
        self.draining, self.once_task, self.once_done = False, None, False
        self.last_waiting, self.runner_blocker = '', ''
        self.pause_until = 0.0
        self.seen, self.touches_tried = {}, set()
        self.known_at_start = False  # the first status read records task states without logging them
        self.drift_tried = self.drift_last_reason = self.drift_reason = ''
        self.last_update, self.last_update_note = time.monotonic(), ''
        self.settled = False
        self.toolset_rev = cfg['toolset_rev']
        self.runtime = pi_runtime.Settings(self.state)

    # --- Engine -----------------------------------------------------------------
    def engine(self, *argv, owned=True, directory=None):
        """The engine's JSON answer; {} when it printed nothing usable."""
        args = [sys.executable, str(self.engine_path), str(directory or self.integ), *argv]
        if owned:
            args[3:3] = ['--owner-pid', str(os.getpid())]
        with open(self.state / 'engine.err', 'a') as err:
            out = subprocess.run(args, stdout=subprocess.PIPE, stderr=err, text=True).stdout
        try:
            value = json.loads(out)
        except ValueError:
            return {'outcome': 'ACTION_REQUIRED', 'reason': out.strip()[:300] or 'no answer from the engine'}
        return value if isinstance(value, dict) else {}

    def status(self, directory=None):
        out = subprocess.run([sys.executable, str(self.engine_path), str(directory or self.integ),
                              '--parallel-status', '--json'], capture_output=True, text=True).stdout
        try:
            value = json.loads(out)
        except ValueError:
            return {}
        return value if isinstance(value, dict) else {}

    def tasks(self, snapshot=None):
        snapshot = self.status() if snapshot is None else snapshot
        return snapshot.get('tasks') if isinstance(snapshot.get('tasks'), list) else []

    def in_flight(self):
        return any(t.get('state') in IN_FLIGHT for t in self.tasks())

    # --- Pi -------------------------------------------------------------------------
    def pi_job(self, role, task, directory, message, session, limit, extra=()):
        """Runs one Pi job in a child (so a second Ctrl+C can reach it); returns (ok, text)."""
        out = tempfile.NamedTemporaryFile(dir=self.state / 'runs', prefix='job.', delete=False)
        out.close()
        env = dict(os.environ, PI_AUTOWORK_SESSION=self.integ_branch or os.environ.get('PI_AUTOWORK_SESSION', ''))
        try:
            with open(out.name, 'w') as stream:
                self.child = subprocess.Popen([sys.executable, str(Path(__file__).with_name('pi_runtime.py')), 'job',
                                               str(self.state), role, task, str(directory), session, str(limit),
                                               message, *extra], stdout=stream, env=env)
                rc = self.child.wait()
            self.child = None
            result = json.loads(Path(out.name).read_text()) if rc == 0 else {}
        except (OSError, ValueError):
            result = {}
        finally:
            self.child = None
            Path(out.name).unlink(missing_ok=True)
        for note in result.get('notes') or []:
            LOG.say(note)
        return bool(result.get('ok')), result.get('text') or ''

    def choose_model(self):
        chosen, reason = pi_runtime.choose(self.runtime)
        return chosen, reason

    # --- Signals and pauses -----------------------------------------------------------
    def worker_groups(self):
        slots = Path(self.cfg['git_common']) / 'autowork-execution/slots'
        groups = []
        for path in slots.glob('*.json') if slots.is_dir() else []:
            try:
                slot = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            if slot.get('state') in ('running', 'dispatched') and (slot.get('worker') or {}).get('pid'):
                groups.append(int(slot['worker']['pid']))
        return groups

    def on_signal(self, *_):
        if self.stop:  # a second Ctrl+C forces: stop workers and the current Pi job
            for group in self.worker_groups():
                try:
                    os.killpg(group, signal.SIGTERM)
                except OSError:
                    pass
            if self.child:
                self.child.terminate()
            return
        self.stop = True
        LOG.say('Stopping: pausing workers so they resume on the next start, then merging finished work '
                '(Ctrl+C again to force)')
        # Workers are interrupted by the main loop after the engine marks them paused, so a
        # deliberate stop or restart neither spends a task's retry nor holds a second attempt.
        if self.child:
            try:
                self.child.send_signal(signal.SIGINT)
            except OSError:
                pass

    PLAN_FILES = ('TODO.md', 'goals.json', 'BLOCKERS.md', 'TODO.archive.md')

    def plan_signature(self):
        """What the owner's plan looks like on disk: the planning files in the main checkout
        and the main branch's ref (a planning commit moves it). Only stat calls."""
        paths = [Path(self.repo) / name for name in self.PLAN_FILES]
        common = Path(self.cfg['git_common'])
        paths += [common / 'refs' / 'heads' / self.base, common / 'packed-refs']
        found = {}
        for path in paths:
            try:
                info = path.stat()
                found[path.name] = (info.st_mtime_ns, info.st_size)
            except OSError:
                found[path.name] = None
        return found

    def pause(self, seconds):
        """Interruptible sleep: a stop ends it at once, and so does a change to the plan.

        Once a second the planning files and the main branch are compared with how they
        looked when this cycle began reading the plan (a change made while the cycle ran
        counts too, or it would wait out the whole interval); after a change has been quiet for PI_AUTOWORK_PLAN_SETTLE
        seconds (default 3, so a save in progress is not read half-written) the wait ends
        and the next cycle reads the new plan. No model call is involved.
        """
        end = time.monotonic() + float(seconds)
        seen, self.plan_seen = self.plan_seen or self.plan_signature(), None
        start = dict(seen)
        checked = time.monotonic()
        changed_at = None
        while not self.stop and time.monotonic() < end:
            time.sleep(min(0.2, max(0.0, end - time.monotonic())))
            if time.monotonic() - checked < 1:
                continue
            checked = time.monotonic()
            now = self.plan_signature()
            if now != seen:
                seen, changed_at = now, time.monotonic()
            elif changed_at is not None and time.monotonic() - changed_at >= self.plan_settle:
                names = [n for n in now if now[n] != start.get(n)]
                labels = ['main' if n in (self.base, 'packed-refs') else n for n in names]
                LOG.say(f'{", ".join(dict.fromkeys(labels)) or "the plan"} changed; checking now')
                return

    # --- Session --------------------------------------------------------------------
    def forget_missing_worktree(self, path):
        """Drop only this path's stale registration; other worktrees are not ours to prune."""
        if Path(path).exists():
            return
        listing = git(self.repo, 'worktree', 'list', '--porcelain') or ''
        if f'worktree {path}' in listing.splitlines():
            git(self.repo, 'worktree', 'remove', str(path))

    def load_session(self, read_only=False):
        session = self.state / 'session.json'
        try:
            value = json.loads(session.read_text())
        except (OSError, ValueError):
            return False
        branch, path = value.get('branch'), value.get('path')
        if not git_ok(self.repo, 'show-ref', '--verify', '-q', f'refs/heads/{branch}'):
            session.unlink(missing_ok=True)
            return False
        if not Path(path).is_dir():
            if read_only:
                return False
            self.forget_missing_worktree(path)
            path = str(workspaces.task_path(self.toolset, self.repo, branch.replace('/', '-')))
            if not git_ok(self.repo, 'worktree', 'add', '-q', path, branch):
                raise Finish(1, f'Cannot restore the integration worktree for {branch}')
            value['path'] = path
            session.write_text(json.dumps(value) + '\n')
        self.integ, self.integ_branch = path, branch
        os.environ['PI_AUTOWORK_SESSION'] = branch
        return True

    def ensure_session(self):
        if self.integ or self.load_session():
            return
        branch = f'pi-autowork/{datetime.now():%Y%m%d-%H%M%S}'
        path = str(workspaces.task_path(self.toolset, self.repo, branch.replace('/', '-')))
        self.forget_missing_worktree(path)
        if Path(path).exists():
            raise Finish(1, f'{path} exists but belongs to no session; remove it after checking its contents.')
        if not git_ok(self.repo, 'worktree', 'add', '-q', '-b', branch, path, self.base):
            raise Finish(1, 'Cannot create the integration worktree')
        (self.state / 'session.json').write_text(json.dumps({
            'branch': branch, 'path': path, 'base': self.base,
            'started': datetime.now().astimezone().isoformat(timespec='seconds')}) + '\n')
        self.integ, self.integ_branch = path, branch
        os.environ['PI_AUTOWORK_SESSION'] = branch
        LOG.say(f'Session {branch} started from {self.base}')

    def end_session(self):
        """Only a clean, fully merged session is removed."""
        if dirty(self.integ):
            LOG.say(f'Session worktree {self.integ} has uncommitted changes; keeping it and {self.integ_branch}')
            return False
        if not git_ok(self.repo, 'worktree', 'remove', self.integ):
            return False
        git(self.repo, 'branch', '-q', '-D', self.integ_branch)
        (self.state / 'session.json').unlink(missing_ok=True)
        self.integ = self.integ_branch = None
        self.resolved_for = ''
        return True

    def ahead(self):
        return int(git(self.repo, 'rev-list', '--count', f'{self.base}..{self.integ_branch}') or 0)

    def merge_main(self):
        """The session into the main branch: the base into the session first (Pi resolves
        conflicts once per base revision), a fast-forward of the base in the main checkout, then a push."""
        self.merge_pending = ''
        if not self.integ and not self.load_session():
            return True
        self.commit_session_leftovers()
        ahead = self.ahead()
        if ahead == 0:
            return True
        planning_note = self.commit_owner_changes()
        if not git_ok(self.integ, 'merge', '-q', '--no-edit', self.base):
            files = ' '.join((git(self.integ, 'diff', '--name-only', '--diff-filter=U') or '').split())
            base_rev = git(self.repo, 'rev-parse', self.base)
            if not self.stop and self.resolved_for != base_rev:  # once per main revision, not per session
                self.resolved_for = base_rev
                LOG.say(f'{self.base} moved and conflicts with this session in: {files}; asking Pi to resolve the merge')
                self.pi_job('merge', self.integ_branch.removeprefix('pi-autowork/'), self.integ,
                            MERGE_PROMPT.format(branch=self.integ_branch, base=self.base, files=files,
                                                goals=self.goals, repo=self.repo),
                            f'pi-autowork-merge-{datetime.now():%Y%m%d%H%M%S}', self.verify_timeout)
            marker = git(self.integ, 'rev-parse', '--path-format=absolute', '--git-path', 'MERGE_HEAD')
            if ((marker and Path(marker).exists())
                    or not git_ok(self.repo, 'merge-base', '--is-ancestor', self.base, self.integ_branch)
                    or dirty(self.integ)):
                git(self.integ, 'merge', '--abort')
                self.merge_pending = f'{self.integ_branch} conflicts with {self.base} in: {files}'
                LOG.say(f'Merge pending: {self.merge_pending}. The branch and its worktree ({self.integ}) are kept.')
                return False
        current = git(self.repo, 'symbolic-ref', '--short', '-q', 'HEAD')
        if current != self.base:
            self.merge_pending = f'{self.repo} is on {current or "a detached HEAD"}, not {self.base}'
        else:
            result = subprocess.run(['git', '-C', str(self.repo), 'merge', '--ff-only', self.integ_branch],
                                    capture_output=True, text=True)
            if result.returncode:
                out = (result.stdout + result.stderr).splitlines()
                line = next((l for l in out if re.search(r'error|fatal|abort', l, re.I)), out[0] if out else '')
                # Git lists the blocking files on the indented lines after the error.
                files = [l.strip() for l in out if l.startswith(('\t', '    ')) and l.strip()]
                if files:
                    shown = ', '.join(files[:6]) + (f' (+{len(files) - 6} more)' if len(files) > 6 else '')
                    line = line.rstrip(':') + ': ' + shown
                self.merge_pending = f'{self.base} in {self.repo} could not take {self.integ_branch}: {line}'
        if self.merge_pending:
            if planning_note:
                self.merge_pending += f' (uncommitted changes not committed yet: {planning_note})'
            LOG.say(f'Merge pending: {self.merge_pending}. Branch {self.integ_branch} is kept; the next run retries.')
            return False
        LOG.say(f'Merged {self.integ_branch} into {self.base} ({ahead} commit(s))')
        self.push()
        return True

    def push(self, retry=True):
        """Publish the main branch to its upstream after a merge (owner decision, 2026-10-16).

        Fast-forward only, never forced; workers and Pi's tools stay unable to push (the push
        guard), only this step runs without it. A rejected push fetches the upstream, merges
        it into the session, lands that and pushes once more. PI_AUTOWORK_PUSH=0 turns it off.
        """
        if os.environ.get('PI_AUTOWORK_PUSH', '1') == '0':
            return
        upstream = git(self.repo, 'rev-parse', '--abbrev-ref', '--symbolic-full-name', f'{self.base}@{{u}}')
        if not upstream or '/' not in upstream:
            if self.seen.get('push-note') != 'no upstream':
                self.seen['push-note'] = 'no upstream'
                LOG.say(f'Not pushed: {self.base} has no upstream branch')
            return
        remote, branch = upstream.split('/', 1)
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_CONFIG_')}
        result = subprocess.run(['git', '-C', str(self.repo), 'push', '--quiet', remote, f'{self.base}:{branch}'],
                                capture_output=True, text=True, env=env, timeout=300)
        if result.returncode == 0:
            self.seen.pop('push-note', None)
            LOG.say(f'Pushed {self.base} to {upstream}')
            return
        text = (result.stdout + result.stderr).strip()
        if retry and re.search(r'rejected|non-fast-forward|fetch first', text):
            if git_ok(self.repo, 'fetch', '--quiet', remote, branch) and self.integ \
                    and git_ok(self.integ, 'merge', '-q', '--no-edit', upstream):
                if git_ok(self.repo, 'merge', '--ff-only', '--quiet', self.integ_branch):
                    LOG.say(f'{upstream} had moved; merged it and pushing again')
                    return self.push(retry=False)
            if self.integ:
                git(self.integ, 'merge', '--abort')
        note = text.splitlines()[-1] if text else f'exit {result.returncode}'
        if self.seen.get('push-note') != note:
            self.seen['push-note'] = note
            LOG.say(f'Push of {self.base} to {upstream} failed: {note}; the merge stays local and the next merge retries')

    def merge_waiting(self):
        """While every remaining task waits (on the owner, a dependency or the resource gate)
        and nothing is in flight, the session reaches the main branch now: the owner's
        questions and finished tasks would otherwise stay on the session branch until the
        queue empties, which a runner waiting on the owner never sees. A merge that could
        not happen is tried again once the session, the main branch or its checkout moves."""
        if not self.integ or self.in_flight() or not self.ahead():
            return
        seen = (git(self.integ, 'rev-parse', 'HEAD'), git(self.repo, 'rev-parse', self.base),
                git(self.repo, 'status', '--porcelain', '--untracked-files=all'))
        if seen == self.waiting_merge:
            return
        self.waiting_merge = seen
        self.merge_main()

    SECRET = re.compile(r'(^|/)(\.env(\..*)?|.*\.(pem|key|p12|pfx)|id_(rsa|ed25519|ecdsa)(\.pub)?|'
                        r'.*credentials.*|.*secret.*|.*\.token)$', re.I)

    def commit_owner_changes(self):
        """Auto work: uncommitted changes never keep finished work from merging. When the
        main checkout's changes have been quiet for PI_AUTOWORK_PLANNING_QUIET seconds and
        no process holds them open for writing, commit them all before merging (planning
        files alone keep their planning message). Untracked files that look like secrets
        stay untracked; a merge, rebase or cherry-pick in progress is left alone.
        Returns '' when committed or nothing was uncommitted, else why it waited."""
        if git(self.repo, 'symbolic-ref', '--short', '-q', 'HEAD') != self.base:
            return f'the main checkout is not on {self.base}'
        for marker in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'rebase-merge', 'rebase-apply'):
            found = git(self.repo, 'rev-parse', '--path-format=absolute', '--git-path', marker)
            if found and Path(found).exists():
                return f'a {marker.split("_")[0].split("-")[0].lower()} is in progress in the main checkout'
        entries = iter([e for e in (git(self.repo, 'status', '--porcelain', '-z', '--untracked-files=all') or '')
                        .split('\0') if e])
        paths, kept = [], []
        for entry in entries:
            status, path = entry[:2], entry[3:]
            if 'U' in status or status in ('AA', 'DD'):
                return f'{path} has an unresolved conflict'
            if status == '??' and self.SECRET.search(path):
                kept.append(path)
                continue
            paths.append(path)
            if status[0] in 'RC':
                paths.append(next(entries, ''))  # the rename's source, so the commit records it
        paths = [p for p in paths if p]
        if not paths:
            return ''
        quiet = float(os.environ.get('PI_AUTOWORK_PLANNING_QUIET', '600'))
        files = [Path(self.repo) / p for p in paths]
        recent = [p for p, f in zip(paths, files) if f.exists() and time.time() - f.stat().st_mtime < quiet]
        if recent:
            return f'{", ".join(recent[:4])} changed in the last {int(quiet // 60)} min'
        held = open_for_writing([f for f in files if f.exists()])
        if held:
            return f'{", ".join(sorted(os.path.relpath(h, self.repo) for h in held))} is open for writing'
        _, dispatch = touches_inference.modules(self.toolset)
        try:
            archive = dispatch.execution.archive_file(Path(self.repo)).relative_to(self.repo).as_posix()
        except (ValueError, OSError):
            archive = None
        planning = {'TODO.md', 'goals.json', 'BLOCKERS.md', 'TODO.archive.md'} | ({archive} if archive else set())
        subject = ('docs(tasks): owner planning (pi-autowork)' if set(paths) <= planning
                   else 'chore: uncommitted work in the main checkout (pi-autowork)')
        git(self.repo, 'add', '-A', '--', *paths)
        if not git_ok(self.repo, 'commit', '-q', '-m', subject,
                      '-m', 'Uncommitted changes in the main checkout, quiet and open nowhere, committed so '
                            'finished work can merge (auto work).', '--', *paths):
            return 'the commit of uncommitted changes failed'
        shown = ', '.join(paths[:6]) + (f' (+{len(paths) - 6} more)' if len(paths) > 6 else '')
        LOG.say(f'Committed uncommitted changes in {self.repo} ({shown}) so the session can merge'
                + (f'; left untracked as possible secrets: {", ".join(kept)}' if kept else ''))
        return ''

    def commit_session_leftovers(self):
        """The session worktree is the runner's own: anything left there uncommitted (a close
        that failed after writing, an interrupted merge) is committed, or every later merge
        refuses it (bravo, TASK-010)."""
        marker = git(self.integ, 'rev-parse', '--path-format=absolute', '--git-path', 'MERGE_HEAD')
        if marker and Path(marker).exists():
            git(self.integ, 'merge', '--abort')
        if not dirty(self.integ):
            return
        git(self.integ, 'add', '-A')
        if git_ok(self.integ, 'commit', '-q', '-m', 'chore: commit uncommitted session changes (pi-autowork)',
                  '-m', 'Left uncommitted in the session worktree; committed so the session can merge.'):
            LOG.say(f'Committed uncommitted changes left in the session worktree ({self.integ})')

    def follow_base(self):
        """While nothing is in flight the session follows the main branch, so the owner's
        plan is seen; a running worker's base never moves under it. A conflict (the owner's
        TODO.md edit against the session's own bookkeeping) is resolved at once through the
        session merge, not left for a final merge a stalled runner never reaches; a merge
        that still fails is a runner blocker the owner sees."""
        if not git(self.repo, 'rev-list', f'{self.integ_branch}..{self.base}') or dirty(self.integ) \
                or self.in_flight():
            return
        if git_ok(self.integ, 'merge', '-q', '--no-edit', self.base):
            self.merge_blocker = ''
            return
        git(self.integ, 'merge', '--abort')
        if self.merge_main():
            self.merge_blocker = ''
        else:
            self.merge_blocker = f'the session cannot take {self.base}: {self.merge_pending}'

    def land(self):
        """After a task closes, bring the session to the main branch (and push) while nothing
        is in flight, so the session never drifts far from the owner's plan."""
        if self.integ and not self.in_flight() and self.ahead():
            self.merge_main()

    def commit(self, paths, *message):
        for path in paths:
            git(self.integ, 'add', '-A', '--', path)
        if git_ok(self.integ, 'diff', '--cached', '--quiet'):
            return False
        args = []
        for line in message:
            args += ['-m', line]
        return git_ok(self.integ, 'commit', '-q', *args)

    def finish(self, code, text):
        if self.integ:
            self.merge_main()
            if not self.merge_pending and not self.in_flight():
                self.engine('--parallel', str(self.workers), '--max-workers', '8', '--release')
                if self.ahead() == 0:
                    self.end_session()
        if self.merge_pending and code == 0:
            code = 4
        raise Finish(code, text)

    # --- Coordinator -------------------------------------------------------------------
    def note_state(self, task, state, reason='', quiet=False):
        """Log each task's lifecycle change once. A waiting task is not news (the runner's
        one `No task can start now` line covers them), and states already reached when the
        runner started are not replayed (quiet)."""
        word = lifecycle(state)
        if self.seen.get(task) == word:
            return
        self.seen[task] = word
        if quiet or word == 'pending':
            return
        LOG.say(f'{task}: {word}' + (f' — {reason}' if reason else ''))

    def count_failure(self, task):
        if self.seen.get('counted-' + task):
            return
        self.seen['counted-' + task] = True
        self.failures += 1

    def close_task(self, task):
        """Archive an integrated task and commit exactly the files the close wrote."""
        result = self.engine('--parallel-close', task)
        if result.get('outcome') == 'CLOSED':
            self.commit(result.get('files') or [], f'docs(tasks): close {task} (pi-autowork)',
                        'Integrated, verified and closed by the Parallel Autowork engine.')
            self.note_state(task, 'closed')
            self.land()
            if result.get('live_followup'):
                LOG.say(f'{task}: done offline; its live checks are recorded as {result["live_followup"]} (Needs decision)')
            self.failures = 0
            if task == self.once_task:
                self.once_done = True
            self.settled = True
            return
        reason = result.get('reason') or result.get('outcome') or ''
        # Its TODO entry was rewritten (or archived by someone else) after the merge: the
        # merge stays in main, so retire the slot instead of blocking on it forever.
        if reason == CONTRACT_CHANGED:
            aside = self.engine('--parallel-set-aside', task)
            if aside.get('outcome') == 'SET_ASIDE':
                if aside.get('requeued') is False:
                    LOG.say(f'{task}: its TODO entry was archived or removed by someone else after integration; '
                            'the merged work stays in main')
                else:
                    LOG.say(f'{task}: its TODO entry changed after integration; the merged work stays in main and '
                            'the task is queued again under its new entry')
                self.seen[task] = 'pending'
                self.settled = True
                return
        if self.seen.get('close-' + task) != reason:
            LOG.say(f'{task}: could not close: {reason}')
        self.seen['close-' + task] = reason

    def settle(self):
        """Integrate, verify and close every reported task, in the engine's priority order."""
        self.settled = False
        snapshot = self.status()
        rows = self.tasks(snapshot)
        for row in rows:
            task, state, reason = row.get('task'), row.get('state') or '', row.get('reason') or ''
            before = self.seen.get(task)
            # A worker that asked for files outside Touches this runner inferred: widen the
            # guess and the engine resumes it in its worktree (not counted as a failure).
            if state == 'interrupted' and row.get('paused'):
                state = 'resuming'  # a deliberate stop or a granted request, not a failure
            if state == 'held' and row.get('cause') == 'scope_request':
                if self.seen.get('awaiting-' + task):
                    continue  # widened already: the next refill resumes it
                if not self.stop and self.widen_inferred(task, ', '.join(row.get('requested') or []), requested=True):
                    self.settled = True
                    continue
            self.note_state(task, state, reason, quiet=not self.known_at_start)
            if task == self.once_task and state == 'held':
                self.draining = True
            # Only a failure this run watched happen counts toward the streak; holds found
            # at start (say after a self-restart) were counted by the run that saw them.
            if state == 'held' and before and before != 'failed':
                self.count_failure(task)
        self.known_at_start = True
        if self.stop:
            return
        self.reverify_held(rows)
        for task in [r['task'] for r in rows if r.get('state') == 'integrated']:
            if self.stop:
                return
            self.close_task(task)
        for task in [r['task'] for r in rows if r.get('state') in ('reported', 'integrating')]:
            if self.stop:
                return
            if not self.seen.get('busy-' + task):  # a waiting commit is not announced every cycle
                self.note_state(task, 'integrating')
            result = self.engine('--integrate', task, '--timeout', self.verify_timeout,
                                 '--reviewer-version', self.reviewer_version(), '--run', '/bin/bash',
                                 self.cfg['script'], '--verify', str(self.state), task)
            outcome, reason = result.get('outcome') or 'ACTION_REQUIRED', result.get('reason') or ''
            if outcome != 'BUSY':
                self.seen.pop('busy-' + task, None)
            if outcome == 'INTEGRATED':
                self.settled = True
                self.note_state(task, 'integrated')
                self.close_task(task)
            elif outcome == 'HELD':
                self.settled = True
                if result.get('cause') == 'scope' and self.widen_inferred(task, ', '.join(result.get('outside') or [])):
                    continue  # the next refill verifies the same commit again (RESCOPED)
                self.note_state(task, 'held', reason)
                self.count_failure(task)
                if task == self.once_task:
                    self.draining = True
            elif outcome == 'BUSY':  # a live session in the main checkout: wait, said once
                if self.seen.get('busy-' + task) != reason:
                    LOG.say(f'{task}: waiting to integrate until another session leaves the main checkout ({reason})')
                self.seen['busy-' + task] = reason
            elif 'highest-priority' not in reason:  # another reported task goes first
                LOG.say(f'{task}: integration needs attention: {reason or outcome}')

    def reviewer_version(self):
        """Fingerprint of this runner's validation: the reviewer's code and prompts plus the
        settings that change what validation runs."""
        digest = hashlib.sha256(Path(__file__).with_name('worker.py').read_bytes())
        for name in ('PI_AUTOWORK_VALIDATE', 'PI_AUTOWORK_REVIEW'):
            digest.update(f'{name}={os.environ.get(name, "")}'.encode())
        return 'review-' + digest.hexdigest()[:12]

    def reverify_held(self, rows):
        """A commit an earlier reviewer held is reviewed again, once, by a changed reviewer
        (flutter TASK-006: held for want of a device before the reviewer knew
        about pending live checks). The engine refuses a second try under the same version."""
        version = self.reviewer_version()
        for row in rows:
            task = row.get('task')
            held_by_validation = row.get('state') == 'held' and (
                row.get('cause') == 'validation'
                or (not row.get('cause') and str(row.get('reason') or '').startswith('integration validation failed')))
            if not held_by_validation or self.seen.get('reverify-' + task) == version or self.stop:
                continue
            self.seen['reverify-' + task] = version
            if self.engine('--parallel-reverify', task, '--reviewer-version', version).get('outcome') == 'REVERIFY':
                self.seen[task] = ''
                self.settled = True
                LOG.say(f'{task}: the reviewer changed since this commit was held; verifying it again')

    # --- Scope: widening Touches this runner inferred ------------------------------
    def inferred(self):
        try:
            value = json.loads(self.inferred_file.read_text())
        except (OSError, ValueError):
            return {}
        return value if isinstance(value, dict) else {}

    def remember_inferred(self, task, touches):
        value = self.inferred()
        value[task] = touches
        tmp = self.inferred_file.with_suffix('.tmp')
        tmp.write_text(json.dumps(value) + '\n')
        os.replace(tmp, self.inferred_file)

    def helper(self, *argv):
        with open(self.state / 'engine.err', 'a') as err:
            result = subprocess.run([sys.executable, str(self.touches_helper), *argv], stdout=subprocess.PIPE,
                                    stderr=err, text=True)
        return result.stdout.strip() if result.returncode == 0 else None

    def recorded_touches(self, task):
        """Touches this runner recorded for the task: from its record, or for older runs from
        its own `declare Touches` commit (the helper still refuses if they changed since)."""
        recorded = self.inferred().get(task)
        if recorded:
            return recorded
        commit = git(self.integ, 'log', '-1', '--format=%H', '--fixed-strings',
                     f'--grep=docs(tasks): declare Touches for {task} (pi-autowork)')
        text = git(self.integ, 'show', f'{commit}:TODO.md') if commit else None
        if not text:
            return None
        goals, _ = touches_inference.modules(self.toolset)
        bodies = goals.task_bodies(text).get(task) or []
        value = goals.task_fields(bodies[0][0]).get('Touches', '').strip() if len(bodies) == 1 else ''
        return value or None

    def widen_inferred(self, task, outside, requested=False):
        """Touches this runner inferred are a guess: widen them once to the files a held
        commit changed (the engine verifies it again) or a worker asked for (the engine
        resumes it in place). Touches a person wrote, or edited since, are never changed:
        the helper refuses."""
        recorded = self.recorded_touches(task)
        if not recorded or not outside or dirty(self.integ) or self.seen.get('widened-' + task):
            return False
        widened = self.helper('widen', self.integ, self.toolset, task, recorded, outside)
        if widened is None:
            return False
        if requested:
            self.commit(['TODO.md'], f'docs(tasks): widen inferred Touches for {task} (pi-autowork)',
                        f'Its worker needs {outside}, outside the inferred Touches; it resumes in its worktree.')
        else:
            self.commit(['TODO.md'], f'docs(tasks): widen inferred Touches for {task} (pi-autowork)',
                        f"The worker's commit changed {outside}, outside the inferred Touches; the engine verifies it again.")
        self.remember_inferred(task, widened)
        self.seen['widened-' + task] = True
        if requested:
            self.seen['awaiting-' + task] = True
            LOG.say(f'{task}: its worker needs files outside the inferred Touches ({outside}); widened them and '
                    'resuming it in its worktree')
        else:
            LOG.say(f'{task}: its commit changed files outside the inferred Touches ({outside}); widened them and verifying again')
        return True

    # --- Touches proposals ------------------------------------------------------------
    def touches_held_until(self):
        try:
            return json.loads(self.touches_cache.read_text())
        except (OSError, ValueError):
            return {}

    def touches_hold(self, task, seconds):
        value = self.touches_held_until()
        value[task] = int(time.time()) + seconds
        tmp = self.touches_cache.with_name(self.touches_cache.name + f'.{os.getpid()}')
        tmp.write_text(json.dumps(value))
        os.replace(tmp, self.touches_cache)

    def scratch_checkout(self, purpose):
        """A disposable detached checkout inside the canonical .worktrees directory."""
        target = workspaces.task_path(self.toolset, self.repo, 'pi-scratch-' + purpose)
        target.parent.mkdir(exist_ok=True)
        path = tempfile.mkdtemp(prefix=target.name + '-', dir=target.parent)
        os.rmdir(path)
        with open(self.state / 'engine.err', 'a') as err:
            ok = subprocess.run(['git', '-C', self.integ, 'worktree', 'add', '-q', '--detach', path, 'HEAD'],
                                stdout=subprocess.DEVNULL, stderr=err).returncode == 0
        if ok:
            self.__dict__.setdefault('_scratch_paths', set()).add(path)
        return path if ok else None

    def drop_scratch(self, path):
        # Only checkouts this instance created are disposable. Other worktrees
        # under the same directory can contain a person's unfinished work.
        owned = getattr(self, '_scratch_paths', set())
        if path not in owned or Path(path).is_symlink():
            return
        if git_ok(self.integ, 'worktree', 'remove', '--force', path):
            owned.remove(path)

    def infer_touches(self):
        """For the top runnable tasks without Touches, a read-only Pi pass proposes the
        paths; recorded in the session branch, the engine then enforces them."""
        if os.environ.get('PI_AUTOWORK_INFER_TOUCHES', '1') == '0':
            return
        listing = self.helper('missing', self.integ, self.toolset, str(self.workers))
        try:
            rows = json.loads(listing or '[]')
        except ValueError:
            return
        # A task with a slot keeps the scope it was dispatched with: a Touches commit for it
        # would read as an answered question and re-queue it.
        slotted = {r.get('task') for r in self.tasks() if r.get('state') not in ('waiting', None)}
        for task in [r.get('id') for r in rows if isinstance(r, dict) and r.get('id') not in slotted]:
            if self.stop:
                return
            if task in self.touches_tried:
                continue
            self.touches_tried.add(task)
            # A task judged unboundable is asked again after a day, not every cycle.
            if float(self.touches_held_until().get(task) or 0) > time.time():
                continue
            # A planning pass reads a disposable copy of the session; nothing it does can
            # touch the session checkout. The copy is removed afterwards.
            scratch = self.scratch_checkout('touches')
            if not scratch:
                LOG.say(f'{task}: could not create a scratch checkout; skipping the Touches pass')
                continue
            ok, text = self.pi_job('touches', task, scratch, TOUCHES_PROMPT.format(task=task, checkout=scratch),
                                   f'pi-autowork-touches-{safe_name(task)}-{datetime.now():%Y%m%d%H%M%S}', 900,
                                   ['--tools', 'read,grep,find,ls'])
            self.drop_scratch(scratch)
            line = next((l for l in text.splitlines() if l.startswith('PI_AUTOWORK_TOUCHES:')), '')
            answer = line.removeprefix('PI_AUTOWORK_TOUCHES:').strip()
            recorded = None
            if ok and answer and not re.match(r'^NONE([^A-Za-z0-9_./]|$)', answer):
                recorded = self.helper('apply', self.integ, self.toolset, task, answer)
            if recorded is not None:
                self.commit(['TODO.md'], f'docs(tasks): declare Touches for {task} (pi-autowork)',
                            'Proposed by a read-only planning pass; the engine holds any change outside it.')
                self.remember_inferred(task, recorded)
                LOG.say(f'{task}: can run beside others; Touches: {recorded}')
            elif not ok or not answer:
                # No answer (provider failure, timeout, missing result line) is not a judgment.
                self.touches_hold(task, 3600)
                self.touches_tried.discard(task)
                LOG.say(f'{task}: runs alone for now (the Touches pass gave no answer; asking again within the hour)')
            else:
                self.touches_hold(task, 86400)
                LOG.say(f'{task}: runs alone (no Touches proposed: {answer})')

    # --- Priority, requests, health, self-update --------------------------------------
    def goals_cli(self, *argv):
        return subprocess.run([sys.executable, str(self.goals), *argv], capture_output=True, text=True)

    def reconcile_priority(self):
        """TODO.md order is the human priority; record it once per change with the
        documented guarded command, committing only goals.json, then select again."""
        self.drift_reason = ''
        revision = self.goals_cli('revision', self.integ)
        if revision.returncode:
            self.drift_reason = 'no ledger revision'
            return False
        revision = revision.stdout.strip()
        if revision == self.drift_tried:
            self.drift_reason = self.drift_last_reason or 'drift remains after recording the order'
            return False
        self.drift_tried = revision
        if dirty(self.integ):
            self.drift_reason = 'the session checkout has uncommitted changes'
        else:
            result = self.goals_cli('reorder', self.integ, '--expected-revision', revision)
            if result.returncode:
                tail = (result.stdout + result.stderr).splitlines()[-3:]
                self.drift_reason = ' '.join(tail)[:300]
            else:
                self.commit(['goals.json'], 'docs(tasks): record TODO.md priority order (pi-autowork)',
                            'TODO.md order is the human priority; recorded with goals.py reorder.')
                # Drift that survives the recording is not something another reorder fixes.
                self.drift_tried = self.goals_cli('revision', self.integ).stdout.strip()
                self.drift_last_reason = 'drift remains after recording the order (duplicate task IDs?)'
                LOG.say('TODO.md priority changed; recorded the new order and selecting again')
                return True
        self.drift_last_reason = self.drift_reason
        return False

    def handle_requests(self):
        """`--set-aside TASK` requests; only this runner holds the engine lease."""
        for request in sorted((self.state / 'requests').glob('set-aside-*')):
            task = request.name.removeprefix('set-aside-')
            result = self.engine('--parallel-set-aside', task)
            if 'live parallel coordinator owner' in json.dumps(result):
                continue  # before this runner's first dispatch it holds no lease: keep it
            request.unlink(missing_ok=True)
            if result.get('outcome') == 'SET_ASIDE':
                self.seen[task] = 'pending'
                self.settled = True
                kept = ', '.join(r['branch_now'] for r in result.get('renamed') or [] if r.get('branch_now'))
                LOG.say(f'{task}: set aside on request; its earlier work is kept as {kept}; the task will run fresh')
            else:
                LOG.say(f'{task}: could not set aside: {result.get("reason") or result.get("outcome")}')

    def health_update(self):
        snapshot = self.status()
        paused = int(time.time() + self.pause_until - time.monotonic()) if self.pause_until > time.monotonic() else 0
        # Commits that only wait for another session to leave the main checkout are no progress.
        waiting = [t for t in self.tasks(snapshot) if t.get('state') in ('reported', 'integrating')
                   and self.seen.get('busy-' + str(t.get('task')))]
        blocker = self.runner_blocker or self.merge_blocker
        if waiting and not blocker:
            blocker = (f'{len(waiting)} verified commit(s) wait for another session in the main checkout: '
                       + self.seen['busy-' + waiting[0]['task']])
        runner = {'repo': str(self.repo), 'pid': str(os.getpid()), 'toolset_rev': self.toolset_rev,
                  'mode': self.mode, 'paused_until': str(paused), 'blocker': blocker,
                  'stuck_integrations': str(len(waiting))}
        try:
            line = health.update(self.state, snapshot, runner=runner, stall_after=int(self.stall_after))
        except (OSError, ValueError):
            return
        if line:
            LOG.warn(line)
        self.update_questions(snapshot)

    def update_questions(self, snapshot):
        """Keep the owner's questions in BLOCKERS.md (TOOLSET-120-fc 2): built without a model,
        written only when they change, committed alone on the session branch."""
        if not self.integ or snapshot.get('outcome') != 'PARALLEL_STATUS' or dirty(self.integ):
            return
        goals, _ = touches_inference.modules(self.toolset)
        path = Path(self.integ) / 'BLOCKERS.md'
        try:
            old = path.read_text() if path.exists() else None
            found = questions.build(snapshot, (Path(self.integ) / 'TODO.md').read_text(), goals)
            new = questions.update(old, found)
        except (OSError, ValueError):
            return
        if new is None or new == old:
            return
        path.write_text(new)
        self.commit(['BLOCKERS.md'], 'docs(blockers): questions for the owner (pi-autowork)',
                    'Built from the engine status without a model; /blockers answers them.')
        LOG.say(f'Questions for the owner in BLOCKERS.md: {len(found)} open'
                + (f" (easiest: {found[0]['id']}, {found[0]['effort']})" if found else ''))

    def update_toolset(self):
        """While nothing is in flight, update the toolset package Pi loads, at most once per
        interval and one runner at a time, and only to a release that reads this state."""
        if self.mode != 'continuous' or self.update_interval == 0:
            return
        if time.monotonic() - self.last_update < self.update_interval:
            return
        self.last_update = time.monotonic()
        if self.cfg['skill_args']:
            return  # not the package Pi loads: a checkout is updated by its owner
        source = git(self.toolset, 'remote', 'get-url', 'origin')
        if not source:
            return
        import fcntl
        with open(Path(self.cfg['state_root']) / 'toolset-update.lock', 'a') as lock:
            deadline = time.monotonic() + 600
            while True:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() > deadline:
                        return
                    time.sleep(1)
            check = release.check(self.cfg['state_root'], self.state, self.toolset)
            if not check['ok']:
                # Another runner's work in flight, or a release that cannot read this state.
                if not check.get('current') and check['reason'] != self.last_update_note:
                    LOG.say(f'Toolset update deferred: {check["reason"]}')
                self.last_update_note = check['reason']
                return
            self.last_update_note = ''
            with open(self.state / 'engine.err', 'a') as err:
                rc = subprocess.run(['timeout', '300', self.cfg['pi'], 'update', source], stdout=err,
                                    stderr=err).returncode
            if rc:
                LOG.say(f'Toolset update failed (see {self.state / "engine.err"}); keeping {self.toolset_rev}')

    def restart_if_updated(self):
        """`pi update` replaces the runner and the engine under a running runner: continue on
        the new release instead of mixing the two. A restart keeps the PID and adopts workers."""
        if self.mode != 'continuous' or self.toolset_rev == 'unknown':
            return
        rev = git(self.toolset, 'rev-parse', '--short', 'HEAD')
        if not rev or rev == self.toolset_rev:
            return
        script = self.cfg['script']
        checks = [subprocess.run(['bash', '-n', script], capture_output=True),
                  subprocess.run([sys.executable, '-m', 'py_compile',
                                  *map(str, Path(self.toolset, 'pi-autowork/pi_autowork').glob('*.py'))],
                                 capture_output=True)]
        if all(c.returncode == 0 for c in checks):
            LOG.say(f'Toolset updated to {rev}; restarting on it')
            (self.state / 'runner.json').unlink(missing_ok=True)
            sys.stdout.flush()
            os.execv('/bin/bash', ['/bin/bash', script, *self.cfg['argv']])
        LOG.say(f'Toolset changed to {rev}, but its runner does not parse; keeping the running {self.toolset_rev}')
        self.toolset_rev = rev

    # --- Main loop -------------------------------------------------------------------------
    def stop_now(self):
        if not self.paused:
            self.paused = True
            self.engine('--parallel-pause')
            for group in self.worker_groups():
                try:
                    os.killpg(group, signal.SIGINT)
                except OSError:
                    pass
        # Interrupted workers stay in their worktrees; the next start resumes them.
        for _ in range(4):
            self.engine('--parallel', str(self.workers), '--max-workers', '8', '--wait', '--timeout', '5')
        self.settle()
        self.finish(130, 'Stopped. Unfinished tasks keep their worktrees and resume on the next start.')

    def blocked_pause(self, blocker):
        self.runner_blocker = blocker
        self.health_update()
        self.pause(self.interval)

    def cycle(self):
        self.plan_seen = self.plan_signature()
        if self.stop:
            self.stop_now()
        if not self.draining and not self.in_flight():
            self.update_toolset()
        self.restart_if_updated()
        self.ensure_session()
        self.follow_base()
        if not self.draining:
            if self.max_cycles and self.started_workers >= self.max_cycles:
                self.draining = True
                LOG.say(f'Reached --max-cycles {self.max_cycles}; finishing running tasks')
            if self.max_runtime and time.monotonic() - self.started >= self.max_runtime:
                self.draining = True
                LOG.say('Reached PI_AUTOWORK_MAX_RUNTIME; finishing running tasks')
            if pi_runtime.over_budget(self.runtime):
                self.draining = True
                LOG.say(f'Budget reached (${pi_runtime.spent(self.runtime)} of ${self.runtime.max_cost} in '
                        f'{self.runtime.window_text} h); finishing running tasks')
            if self.failures >= self.max_failures:
                if self.mode == 'continuous':
                    # A service that exits on its own is a silent stop; pause new work instead.
                    LOG.say(f'{self.failures} tasks failed in a row; pausing new tasks for {self.failure_pause}s '
                            '(running ones continue)')
                    self.failures = 0
                    self.pause_until = time.monotonic() + self.failure_pause
                else:
                    self.draining = True
                    LOG.say(f'Stopping after {self.failures} failed tasks in a row; finishing running tasks')
        if not self.draining:
            chosen, reason = self.choose_model()
            if not chosen:
                reason = reason or 'primary and fallback not ready'
                if self.mode in ('once', 'until-empty'):
                    self.finish(1, f'No usable model: {reason}')
                LOG.say(f'No usable model ({reason}); checking again in {self.interval}s')
                return self.blocked_pause(f'no usable model: {reason}')
        self.runner_blocker = ''
        result = {}
        if not self.draining and time.monotonic() < self.pause_until:
            outcome = 'PAUSED'  # after a failure streak: settle running work, start nothing new
        elif not self.draining:
            self.infer_touches()
            result = self.engine('--apply', '--parallel', str(self.workers), '--max-workers', '8',
                                 '--worker-command', self.worker_command, '--worker-timeout', self.task_timeout,
                                 '--min-free-mem-mb', self.min_free_mb, '--adopt-idle-claims', str(self.claim_idle))
            outcome = result.get('outcome') or 'ACTION_REQUIRED'
        else:
            outcome = 'DRAINING'
        if outcome in ('DISPATCHED', 'RETRIED'):
            started = [d.get('task') for d in result.get('dispatched') or []]
            if isinstance(result.get('retried'), dict) and result['retried'].get('task'):
                started.append(result['retried']['task'])
            elif outcome == 'RETRIED' and result.get('task'):
                started.append(result['task'])
            for task in started:
                self.started_workers += 1
                if self.mode == 'once' and not self.once_task:
                    self.once_task, self.draining = task, True  # no second task
                if task in (result.get('adopted') or []):
                    self.note_state(task, 'running', f'worker started; adopted an idle claim (no activity for '
                                                     f'{self.claim_idle // 3600} h or more)')
                else:
                    self.note_state(task, 'running', 'worker started')
        elif outcome == 'READOPTED':
            self.seen[result.get('task')] = ''
            LOG.say(f'{result.get("task")}: the retry made no change; re-verifying the first attempt\'s commit')
        elif outcome == 'REQUEUED':
            task = result.get('task')
            self.seen[task] = ''
            kept = ', '.join(r['branch_now'] for r in result.get('renamed') or [] if r.get('branch_now'))
            if result.get('requeued') is False:
                LOG.say(f'{task}: its TODO entry was removed or closed while it was held; set aside'
                        + (f' (earlier work kept as {kept})' if kept else ''))
            else:
                LOG.say(f'{task}: its TODO entry changed while it was held; running it fresh'
                        + (f' (earlier work kept as {kept})' if kept else ''))
        elif outcome in ('RESCOPED', 'RESUMED', 'REOFFERED'):
            self.seen[result.get('task')] = ''
            self.seen.pop('awaiting-' + str(result.get('task')), None)
        elif outcome == 'WAITING':
            waiting = summary_list(result.get('waiting') or [])
            if waiting and waiting != self.last_waiting:
                LOG.say(f'Waiting: {waiting}')
            self.last_waiting = waiting
        elif outcome == 'IDLE':
            # IDLE only means no worker is running: tasks may still be waiting on something.
            blocked = summary_list(result.get('waiting') or [])
            if not blocked:
                rows = [t for t in self.tasks() if t.get('state') == 'waiting']
                blocked = summary_list(rows, lambda r: f"{r.get('task')}: {r.get('reason') or 'waiting'}")
            if blocked:
                outcome = 'BLOCKED'
                if blocked != self.last_waiting:
                    LOG.say(f'No task can start now: {blocked}')
                self.last_waiting = blocked
        elif outcome in ('DRAINING', 'PAUSED'):
            pass
        elif outcome == 'BUSY':
            reason = result.get('reason') or 'busy'
            if self.mode in ('once', 'until-empty'):
                self.finish(4, f'Repository busy: {reason}')
            LOG.say(f'Repository busy ({reason}); checking again in {self.interval}s')
            return self.blocked_pause(f'repository busy: {reason}')
        elif outcome == 'PRIORITY_DRIFT':
            # Scheduled runs record the human order themselves (Autowork SKILL.md), once per change.
            if self.reconcile_priority():
                return
            if self.mode in ('once', 'until-empty'):
                self.finish(4, f'TODO.md priority changed and could not be recorded: {self.drift_reason}')
            if self.last_waiting != 'drift:' + self.drift_reason:
                LOG.say(f'TODO.md priority changed and could not be recorded ({self.drift_reason}); '
                        f'checking again in {self.interval}s')
            self.last_waiting = 'drift:' + self.drift_reason
            return self.blocked_pause(f'TODO.md priority changed and goals.py reorder refused: {self.drift_reason}')
        else:
            reason = result.get('reason') or outcome
            if self.mode != 'continuous':
                self.finish(4, f'The engine needs attention: {reason}')
            # A service that exits here stops silently (deliberate exits are not restarted):
            # report it once, keep it visible in health, and look again next interval.
            if self.last_waiting != 'engine:' + reason:
                LOG.say(f'The engine needs attention: {reason}; checking again in {self.interval}s')
            self.last_waiting = 'engine:' + reason
            return self.blocked_pause(f'the engine needs attention: {reason}')
        self.settle()
        self.handle_requests()
        self.health_update()
        if self.settled:
            return  # closing work can make dependents runnable: dispatch again first
        if self.in_flight():
            self.engine('--parallel', str(self.workers), '--max-workers', '8', '--wait', '--timeout', '5')
            return
        if outcome in ('WAITING', 'BLOCKED', 'PAUSED'):
            # Tasks remain, but none can start now (held work, dependencies or the resource gate).
            if self.mode != 'continuous':
                self.finish(1, f'No runnable task can start: {self.last_waiting or "see --status"}')
            self.merge_waiting()
            return self.pause(self.interval)
        # Nothing running, nothing to integrate and nothing waiting: the session ends here.
        if self.draining or self.mode != 'continuous':
            if self.mode == 'once' and not self.once_task and outcome == 'IDLE':
                self.finish(0, 'Queue empty')
            if outcome == 'IDLE' and self.mode == 'until-empty':
                self.finish(0, 'Queue empty')
            if self.mode == 'once':
                if self.once_done:
                    self.finish(0, f'Done (--once): {self.once_task}')
                self.finish(1, f'Done (--once): {self.once_task} did not finish; see --status')
            if self.draining:
                self.finish(1 if self.failures >= self.max_failures else 0, 'Finished.')
        if outcome == 'IDLE':
            if self.merge_main():
                self.engine('--parallel', str(self.workers), '--max-workers', '8', '--release')
                if self.integ:
                    self.end_session()
            LOG.say(f'Queue empty; checking again in {self.interval}s')
            self.pause(self.interval)

    def run(self):
        signal.signal(signal.SIGINT, self.on_signal)
        signal.signal(signal.SIGTERM, self.on_signal)
        LOG.say(f'Started (PID {os.getpid()}). Stop with Ctrl+C.')
        try:
            while True:
                self.cycle()
        except Finish as done:
            LOG.say(done.text)
            return done.code
        finally:
            (self.state / 'runner.json').unlink(missing_ok=True)
