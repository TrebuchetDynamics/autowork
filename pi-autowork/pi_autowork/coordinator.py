"""The pi-autowork coordinator loop.

The toolset's Parallel Autowork engine (skills/autowork/scripts/owner_cycle.py) is
the only authority for task state: it plans, dispatches, verifies and closes. This
loop holds the engine lease (its PID is the owner) and supplies what the engine
leaves to the host: a session branch merged into the main branch at the end, Pi jobs
for Touches proposals and conflict resolution, health, requests, self-update and a
graceful stop. Every decision about a task is the engine's answer, not a guess here.
"""
from datetime import datetime
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from . import fleet_view, health, janitor, main_check, maintainer, pi_runtime, questions, release, touches_inference, worker, workspaces
from .common import LOG, dirty, git, git_ok, lifecycle, open_for_writing, safe_name, summary_list

IN_FLIGHT = ('dispatched', 'running', 'reported', 'integrating', 'integrated')
# The engine's planning files (parallel_integrate.PLANNING_FILES): a session that moves only by
# commits to these, or under docs/, does not invalidate a running review (TOOLSET-233-ba).
PLANNING_FILES = ('TODO.md', 'TODO.archive.md', 'todo.archive.md', 'goals.json', 'BLOCKERS.md')
CONTRACT_CHANGED = 'task contract changed since integration; no close'
MERGE_PROMPT = (
    '/skill:git-commit-push This worktree is on branch {branch} with an unfinished merge of {base} that conflicts '
    "in: {files}. Resolve every conflict keeping both sides' work: keep both task entries in TODO.md and "
    'TODO.archive.md, keep every task record in goals.json and run python3 {goals} merge-finalize . and '
    'python3 {goals} validate . if goals.json exists, then '
    'run only the tests that cover the conflicted files, not the full check (the runner runs it on the merged '
    'result), and conclude the merge with a commit. Do not push, rebase, '
    'switch branches or touch {repo}. End with one line: PI_AUTOWORK_RESULT: completed|blocked, then one sentence.')


def publishable(repo, paths):
    """(paths auto work may commit, [(path, key, why not)]). A submodule pointer whose new commit
    is on no branch of the submodule's remote stays uncommitted (TOOLSET-168-ff): the main branch
    would point at a commit no other clone can fetch. An untracked nested repository stays out
    too: adding it would record an embedded repository, not its files."""
    links = set()
    for line in (git(repo, 'ls-files', '-s', '--', *paths) or '').splitlines():
        meta, _, path = line.partition('\t')
        if meta.split(' ', 1)[0] == '160000':
            links.add(path)
    keep, held = [], []
    for path in paths:
        folder = Path(repo) / path
        if path.rstrip('/') in links:
            head = git(folder, 'rev-parse', 'HEAD') or ''
            try:
                subprocess.run(['git', '-C', str(folder), 'fetch', '-q'], capture_output=True, timeout=30,
                               env=dict(os.environ, GIT_TERMINAL_PROMPT='0'))
            except subprocess.TimeoutExpired:
                pass
            if not head or not git(folder, 'branch', '-r', '--contains', head):
                held.append((path, head, f'Left {path} uncommitted: submodule commit {head[:12] or "?"} is not on '
                                         'its remote yet'))
                continue
        elif (folder / '.git').exists():
            held.append((path, 'nested', f'Left {path} uncommitted: it is a separate Git repository, not files of '
                                         'this one'))
            continue
        keep.append(path)
    return keep, held


TRIAGE_PROMPT = (
    'You triage a blocker for the runner of {repo}. The worker of task {task} stopped and reported blockers '
    'instead of finishing; read them in full in {report}, then the task\'s TODO.md entry, its Sources and, if '
    'needed, the worker log beside the report. Its worktree is {root}: read it, but do not edit, commit or run '
    'anything that writes there (scratch goes in $TMPDIR). Decide whether only a person can resolve the '
    'blockers. Only these need the owner: credentials, secrets or an account; a physical device, hardware or '
    'operator access; spending; a change to third-party software the repository does not contain; a product, '
    'security or scope decision that the task, its sources and the repository\'s docs leave open. Anything '
    'else gets an answer the worker can act on. State as fact what the runner guarantees: the worker\'s ports '
    '$AUTOWORK_PORT_BASE to +99 are leased to it alone on this host; its $TMPDIR is private and on disk; its '
    'baseline is the session\'s current HEAD; other tasks\' overlapping work merges at integration, in priority '
    'order; the runner verifies an idle in_progress claim before adopting it; the runner\'s review runs the full '
    'check on the merged tree and tells new failures from old and flaky ones. The runner also provides '
    '$AUTOWORK_MAIN_EVIDENCE/<revision>/ for main checks: main_check.json (revision, last green, failures '
    'and commits), main-check.log, main-check.exit, main-check-reruns.log (isolated commands, exit codes '
    'and output), and flaky_history.json, retaining the latest five revisions. Read these bundles in place '
    'and answer a request for main-check logs or reruns with the relevant bundle path, not a question for '
    'a person. Do not copy evidence into worktrees or commits. No coordinator receipt, handoff, '
    'source refresh, registry or verification exists beyond these: the worker proceeds without one. A defect '
    'already in the baseline that stops a required check (a broken or unparsable test, a missing fixture, a '
    'stale generated file) is the worker\'s to repair as a separate commit on its branch. A missing input whose '
    'making the task\'s sources describe, the worker makes. Host load, a slow or flaky check or a time budget: '
    'the worker commits the finished work and reports the check\'s result. Be specific: name the files, commands '
    'and facts the worker needs, from what you read. Never grant authority, credentials or spending, never '
    'change Acceptance, and never decide a product or security question yourself. End with exactly one of two '
    'blocks: the line PI_AUTOWORK_TRIAGE: owner and then one line saying what the person must provide, or the '
    'line PI_AUTOWORK_TRIAGE: answer and then the answer for the worker, at most 15 lines.')
TRIAGE = re.compile(r'^PI_AUTOWORK_TRIAGE:\s*(answer|owner)\s*$', re.M)


def triage_verdict(text):
    """('answer'|'owner', text) from a triage job's output, or None when it ended without a verdict."""
    found = list(TRIAGE.finditer(text or ''))
    if not found:
        return None
    body = text[found[-1].end():].strip()
    return (found[-1].group(1), body[:4000]) if body else None


PROVISION_PROMPT = (
    'In {repo}, the review of task {task} could not run its checks because this is missing: {missing}. '
    'Install what is missing so that the checks can run, following the repository\'s own setup docs '
    '(README, docs, an ENVIRONMENT or setup file, the task\'s TODO.md entry), pinned versions included. '
    'Install only under {cache} ($AUTOWORK_CACHE), as <name>-<version>, and reuse what is already there. '
    'Do not edit, create or delete files in this checkout, commit, push or change branches. Check that the '
    'installed tool runs. End with one line: PI_AUTOWORK_RESULT: completed or PI_AUTOWORK_RESULT: blocked, '
    'then how to use it (paths and environment variables, for example FLUTTER_ROOT and PATH).')


class Finish(Exception):
    def __init__(self, code, text):
        super().__init__(text)
        self.code, self.text = code, text


def env_settings(path):
    """KEY=value lines of the service's settings file (systemd's EnvironmentFile)."""
    try:
        lines = Path(path).read_text().splitlines()
    except OSError:
        return {}
    found = {}
    for line in lines:
        key, sep, value = line.strip().partition('=')
        if sep and key and not key.startswith('#'):
            found[key] = value[1:-1] if len(value) > 1 and value[0] == value[-1] and value[0] in '"\'' else value
    return found


def settings_file(repo):
    """The service's settings file: the unit names it; a unit installed before that is found by
    its repository line. None outside a service."""
    if os.environ.get('PI_AUTOWORK_ENV_FILE'):
        return os.environ['PI_AUTOWORK_ENV_FILE']
    if not os.environ.get('INVOCATION_ID'):
        return None
    config = os.environ.get('XDG_CONFIG_HOME') or str(Path.home() / '.config')
    folder = Path(os.environ.get('PI_AUTOWORK_ENV_DIR') or f'{config}/pi-autowork')
    return next((str(p) for p in sorted(folder.glob('*.env')) if env_settings(p).get('PI_AUTOWORK_REPO') == str(repo)), None)


def reread_settings(path, started_with):
    """Apply the service's settings file as it is now, as a fresh service start would; a key
    removed since this process started (``started_with``) is dropped too."""
    if not path:
        return
    now = env_settings(path)
    for key in started_with - set(now):
        os.environ.pop(key, None)
    os.environ.update(now)


def batchable(rows, handled=()):
    """(task, commit) of each candidate a batch may take: reported, or integrating with no review
    running (one runs only while the session is busy, and no batch starts then). Reported alone,
    a review a restart cut short waited behind every later batch: 16 hours for one of them."""
    return [(r['task'], r.get('commit')) for r in rows
            if r.get('state') in ('reported', 'integrating') and r['task'] not in handled]


class Coordinator:
    def __init__(self, cfg):
        self.cfg = cfg
        self.repo, self.base, self.toolset = cfg['repo'], cfg['base'], cfg['toolset']
        self.package = os.environ.get('PI_AUTOWORK_PACKAGE', self.toolset)
        self.package_rev = cfg['toolset_rev']
        self.state = Path(cfg['state'])
        self.mode, self.workers = cfg['mode'], cfg['workers']
        env = os.environ
        self.interval = cfg['interval']
        self.max_cycles = cfg['max_cycles']
        # `or`, not a default: a service config that sets the name to nothing must keep the
        # documented limit. `get(name, default)` returns '', and float('') raised in review_limit.
        self.verify_timeout = env.get('PI_AUTOWORK_VERIFY_TIMEOUT') or '1800'
        self.task_timeout = env.get('PI_AUTOWORK_TASK_TIMEOUT') or '5400'
        self.max_failures = int(env.get('PI_AUTOWORK_MAX_FAILURES', '3'))
        self.failure_pause = int(env.get('PI_AUTOWORK_FAILURE_PAUSE', '3600'))
        self.claim_idle = cfg['claim_idle']
        self.max_runtime = int(env.get('PI_AUTOWORK_MAX_RUNTIME', '0'))
        self.min_free_mb = env.get('PI_AUTOWORK_MIN_FREE_MB', '3000')
        self.update_interval = int(env.get('PI_AUTOWORK_UPDATE_INTERVAL', '120'))
        self.update_wait = float(env.get('PI_AUTOWORK_UPDATE_WAIT', '600'))
        self.plan_settle = float(env.get('PI_AUTOWORK_PLAN_SETTLE', '3'))
        # Planning commits (questions, maintainer repairs, Touches) land soon, not only with a
        # closed task (TOOLSET-188-75); at least this often while the session is ahead.
        self.land_every = float(env.get('PI_AUTOWORK_LAND_EVERY', '600'))
        self.landed_at, self.land_soon = time.monotonic(), False
        self.plan_seen = None
        self.stall_after = env.get('PI_AUTOWORK_STALL_AFTER', '1800')
        self.engine_path = Path(self.toolset) / 'skills/autowork/scripts/owner_cycle.py'
        self.goals = Path(self.toolset) / 'skills/docs-sync/scripts/goals.py'
        self.process_script = str(Path(self.toolset) / 'scripts/pi-autowork.sh')
        self.worker_command = json.dumps(['/bin/bash', self.process_script, '--worker', str(self.state), '{worktree}',
                                          '{prompt_file}', '{report_file}', '{timeout}'])
        self.started = time.monotonic()
        self.integ = self.integ_branch = None
        self.merge_pending, self.resolved_for, self.merge_blocker = '', '', ''
        self.waiting_merge = None  # what the last merge while waiting saw
        self.stop, self.paused, self.child = False, False, None
        self.timeout_limits = {}  # task -> review limit for its reverify after a timeout (TOOLSET-196-fb)
        self.reload = False  # SIGHUP: re-execute in place at the next safe point (TOOLSET-174-1d)
        self.settings_file = settings_file(self.repo)
        self.started_with = set(env_settings(self.settings_file)) if self.settings_file else set()
        self.started_workers = self.failures = 0
        self.draining, self.once_task, self.once_done = False, None, False
        self.last_waiting, self.runner_blocker = '', ''
        self.ledger_errors = []
        self.integration = None  # the review running beside the loop (TOOLSET-183-d6)
        self.pause_until = 0.0
        self.seen, self.touches_tried = {}, set()
        self.known_at_start = False  # the first status read records task states without logging them
        self.drift_tried = self.drift_last_reason = self.drift_reason = ''
        self.last_update, self.last_update_note = time.monotonic(), ''
        self.settled = False
        self.toolset_rev = cfg['toolset_rev']
        self.runtime = pi_runtime.Settings(self.state)
        self.merge_drivers_registered = False
        self.planning_attributes = None

    # --- Engine -----------------------------------------------------------------
    def start_integration(self, task):
        """Start the engine's integration of ``task`` as a child the loop polls, so a review
        that runs a long check does not stop dispatch, status and questions (TOOLSET-183-d6)."""
        out = tempfile.NamedTemporaryFile(dir=self.state / 'runs', prefix='integrate.', delete=False)
        out.close()
        limit = str(self.review_limit(task))
        args = [sys.executable, str(self.engine_path), str(self.integ), '--owner-pid', str(os.getpid()),
                '--integrate', task, '--timeout', limit, '--reviewer-version', self.reviewer_version(),
                '--base-ref', self.base, *(['--batch-order', ','.join(chain)] if (chain := self.batch_chain()) else []),
                '--run', '/bin/bash', self.process_script, '--verify', str(self.state), task]
        # The reviewer's own Pi limit follows the review's: one doubled after a timeout reaches it too.
        with open(out.name, 'w') as stream, open(self.state / 'engine.err', 'a') as err:
            child = subprocess.Popen(args, stdout=stream, stderr=err, stdin=subprocess.DEVNULL,
                                     env=dict(os.environ, PI_AUTOWORK_VERIFY_TIMEOUT=limit))
        self.integration = {'task': task, 'proc': child, 'out': out.name, 'started': time.time()}
        self.snapshot = None

    BATCH = 'batch'

    def batch_due(self, reported):
        """Two or more candidates wait, batching is on, and this exact set of revisions has not
        been batched yet. ``reported`` is (task, commit) pairs. The commit is part of the key: a
        conflict the resolver merged with the session is a new revision, so the candidates the
        last batch had to skip are offered to a new batch once they merge (one check, not one
        each) instead of being held back for the process's lifetime."""
        size = int(os.environ.get('PI_AUTOWORK_BATCH') or 6)
        failed = self.batch_failed()
        fresh = [(t, commit) for t, commit in reported if not worker.batch_record(self.state, t).exists()
                 and f'{t}@{commit}' not in failed]
        if size < 2 or len(fresh) < 2 or self.reexec_due() or self.batch_pending():
            return []  # land the last batch first: a new one would be built on another tree
        if self.seen.pop('batched', None) and any(f'{t}@{commit}' in failed for t, commit in reported):
            # One review alone between two batches: while resolutions kept the batch fresh, nine
            # commits whose batch had failed never got a review of their own, one for 15 hours.
            return []
        half = self.batch_half({f'{t}@{commit}' for t, commit in fresh})
        if half:
            fresh = [(t, commit) for t, commit in fresh if f'{t}@{commit}' in half]
        key = ','.join(f'{t}@{commit}' for t, commit in sorted(fresh))
        if self.seen.get('batch-tried') == key:
            return []
        self.seen['batch-tried'] = key
        self.seen['batched'] = True
        self.batch_revisions = [f'{t}@{commit}' for t, commit in fresh]
        return [t for t, _ in fresh]

    def batch_failed(self):
        """Revisions whose batch failed its full check: they integrate one at a time. Kept on disk,
        since a restart, or one more candidate, built a new batch around the same failing one."""
        try:
            return set(json.loads((self.state / 'batch-failed.json').read_text()))
        except (OSError, ValueError, TypeError):
            return set()

    def batch_half(self, fresh):
        """The next half of a failed batch still to be checked, or None. A failed batch was split in
        two rather than sent one at a time: six candidates each waited out a review of their own,
        about an hour each, because one of them broke a test. A half no longer fresh (landed, or a
        new revision) shrinks; one left with a single candidate integrates it alone."""
        path = self.state / 'batch-split.json'
        try:
            halves = [h for h in json.loads(path.read_text()) if isinstance(h, list)]
        except (OSError, ValueError, TypeError):
            return None
        found, alone = None, []
        while halves and found is None:
            half = [r for r in halves.pop(0) if r in fresh]
            if len(half) >= 2:
                found = half
            else:
                alone += half
        if alone:
            (self.state / 'batch-failed.json').write_text(json.dumps(sorted(self.batch_failed() | set(alone))) + '\n')
        if halves:
            path.write_text(json.dumps(halves) + '\n')
        else:
            path.unlink(missing_ok=True)
        return found

    def start_batch(self, tasks):
        """TOOLSET-258-07: one full check on the candidates' merged tree and their reviews side
        by side, as a child the loop polls like a review; the engine then lands each one."""
        out = tempfile.NamedTemporaryFile(dir=self.state / 'runs', prefix='batch.', delete=False)
        out.close()
        args = ['/bin/bash', self.process_script, '--verify-batch', str(self.state), str(self.integ),
                self.process_script, *tasks]
        with open(out.name, 'w') as stream, open(self.state / 'engine.err', 'a') as err:
            child = subprocess.Popen(args, stdout=stream, stderr=err, stdin=subprocess.DEVNULL, cwd=self.integ)
        self.integration = {'task': self.BATCH, 'proc': child, 'out': out.name, 'started': time.time(),
                            'members': list(tasks)}
        self.snapshot = None
        self.batch_members = list(tasks)
        LOG.say(f'Batch of {len(tasks)} candidates ({", ".join(tasks)}): one full check on their merged tree, '
                'their reviews side by side')

    def batch_done(self, result):
        if result.get('outcome') == 'BATCH_GATE_FAILED':
            failure = f'Batch: the full check failed on the merged tree ({str(result.get("reason") or "")[:300]}); '
            revisions = {r.split('@')[0]: r for r in getattr(self, 'batch_revisions', [])}
            checked = [revisions[t] for t in result.get('tasks') or [] if t in revisions]
            suspects = [revisions[t] for t in result.get('suspects') or [] if t in revisions]
            if suspects and len(suspects) < len(checked):
                # The failing tests import or name only these candidates' changes: they integrate
                # one at a time, and the rest batch again at once instead of in halves.
                failed = self.batch_failed() | set(suspects)
                (self.state / 'batch-failed.json').write_text(json.dumps(sorted(failed)) + '\n')
                LOG.say(failure + f'the failing tests point at {", ".join(r.split("@")[0] for r in suspects)}, '
                        f'which integrate one at a time; the other {len(checked) - len(suspects)} batch again')
                return
            if len(checked) >= 4:
                middle = len(checked) // 2
                path = self.state / 'batch-split.json'
                try:
                    halves = json.loads(path.read_text())
                except (OSError, ValueError):
                    halves = []
                path.write_text(json.dumps([checked[:middle], checked[middle:], *halves]) + '\n')
                LOG.say(failure + f'checking its halves ({len(checked[:middle])} and {len(checked[middle:])} '
                        'candidates) to find the one that fails')
                return
            LOG.say(failure + 'its candidates integrate one at a time')
            failed = self.batch_failed() | set(checked)
            (self.state / 'batch-failed.json').write_text(json.dumps(sorted(failed)) + '\n')
            return
        parts = [f'{len(result.get("passed") or [])} passed ({", ".join(result.get("passed") or []) or "none"})']
        if result.get('held'):
            parts.append(f'held: {", ".join(result["held"])}')
        if result.get('skipped'):
            parts.append(f'left out (conflict): {", ".join(result["skipped"])}')
        if result.get('reason'):
            parts.append(str(result['reason']))
        later = [t for t in getattr(self, 'batch_members', []) if t not in (result.get('tasks') or [])
                 and t not in (result.get('skipped') or [])]
        if later:  # past the batch size: they were neither checked nor reported before (11 of 17)
            parts.append(f'{len(later)} wait for the next batch')
        LOG.say('Batch: ' + '; '.join(parts) + ' — landing them now')
        # The order they were verified in: each verdict holds only for its step of that chain.
        order = [t for t in result.get('tasks') or [] if worker.batch_record(self.state, t).exists()]
        (self.state / 'batch-order.txt').write_text('\n'.join(order) + '\n')
        # Offered first, out of priority order: the engine holds a conflict at once, and the
        # hold is what starts the resolver. Asked after a long review, they waited hours.
        (self.state / 'batch-conflicts.txt').write_text('\n'.join(result.get('skipped') or []) + '\n')

    def batch_conflicts(self):
        """Candidates the last batch left out because they do not merge with the session."""
        try:
            return (self.state / 'batch-conflicts.txt').read_text().split()
        except OSError:
            return []

    def batch_chain(self):
        """Batch-verified candidates not landed yet, in the order the batch verified them."""
        try:
            order = (self.state / 'batch-order.txt').read_text().split()
        except OSError:
            return []
        return [t for t in order if worker.batch_record(self.state, t).exists()]

    def batch_landing(self):
        """Batch-passed candidates not landed yet (TOOLSET-281-0d). Their verdicts hold only for
        the trees they were reached on, so until they land the runner neither re-executes nor
        merges code from main into the session: a reload 4 s after `landing them now` sent one
        passed candidate back to the end of a queue of single reviews for 15 hours. The verdicts'
        own two-hour lifetime (batch_pending) bounds the wait."""
        chain = self.batch_chain()
        if not chain or not self.batch_pending():
            return []
        states = {r.get('task'): r.get('state') for r in self.tasks()}
        return [t for t in chain if states.get(t) in ('reported', 'integrating')]

    def base_has_code(self):
        """Whether main holds anything but planning files and docs the session lacks; a batch
        verdict survives those (worker.same_code)."""
        changed = git(self.repo, 'diff', '--name-only', f'{self.integ_branch}...{self.base}').split()
        return any(p not in PLANNING_FILES and not p.startswith('docs/') for p in changed)

    def batch_pending(self):
        """Batch verdicts not used yet: the session holds still for them, or their trees no longer match."""
        folder = self.state / 'batch'
        now = time.time()
        for path in folder.glob('*.json') if folder.is_dir() else []:
            try:
                if now - float(json.loads(path.read_text()).get('at') or 0) < 7200:
                    return True
            except (OSError, ValueError, TypeError):
                continue
        return False

    REVIEW_CAP = 4 * 3600

    def review_limit(self, task=None):
        """Seconds a review may take (TOOLSET-196-fb): PI_AUTOWORK_VERIFY_TIMEOUT, or twice the
        longest of this repository's last five reviews if longer, capped at four hours; a task
        reverified after running out of time gets the limit it was given."""
        if task and task in self.timeout_limits:
            return self.timeout_limits[task]
        try:
            recent = json.loads((self.state / 'review_times.json').read_text())[-5:]
        except (OSError, ValueError):
            recent = []
        longest = max([float(x) for x in recent if isinstance(x, (int, float))] or [0])
        try:
            given = float(self.verify_timeout)
        except (TypeError, ValueError):  # a misconfigured limit must not stop the run loop
            given = 1800.0
        return int(min(self.REVIEW_CAP, max(given, 2 * longest)))

    def note_review_time(self, seconds):
        path = self.state / 'review_times.json'
        try:
            times = json.loads(path.read_text())
        except (OSError, ValueError):
            times = []
        path.write_text(json.dumps(([t for t in times if isinstance(t, (int, float))] + [round(seconds)])[-5:]))

    def session_busy(self):
        """A review is running: the session branch must not move or get dirty meanwhile, or
        its fast-forward at the end fails."""
        return bool(self.integration) and self.integration['proc'].poll() is None

    def collect_integration(self, wait=0):
        """(task, result) of the review once it ended, waiting up to ``wait`` seconds; None while it runs."""
        job = self.integration
        if not job:
            return None
        try:
            job['proc'].wait(timeout=wait or None) if wait else None
        except subprocess.TimeoutExpired:
            pass
        if job['proc'].poll() is None:
            return None
        self.integration = self.snapshot = None
        try:
            value = json.loads(Path(job['out']).read_text())
        except (OSError, ValueError):
            value = {'outcome': 'ACTION_REQUIRED', 'reason': 'no answer from the engine'}
        finally:
            Path(job['out']).unlink(missing_ok=True)
        if isinstance(value, dict) and value.get('outcome') in ('INTEGRATED', 'HELD'):
            # Queue contention is not evidence that this repository's checks need a longer budget.
            self.note_review_time(max(0, time.time() - job['started'] - value.get('check_slot_wait_seconds', 0)))
        return job['task'], value if isinstance(value, dict) else {}

    def stop_integration(self):
        """On a stop: end the review; the engine's recovery verifies the commit again later."""
        job, self.integration = self.integration, None
        self.snapshot = None
        if job and job['proc'].poll() is None:
            job['proc'].terminate()
            try:
                job['proc'].wait(timeout=20)
            except subprocess.TimeoutExpired:
                job['proc'].kill()
        if job:
            Path(job['out']).unlink(missing_ok=True)

    def engine(self, *argv, owned=True, directory=None):
        """The engine's JSON answer; {} when it printed nothing usable."""
        args = [sys.executable, str(self.engine_path), str(directory or self.integ), *argv]
        if owned:
            args[3:3] = ['--owner-pid', str(os.getpid())]
        self.snapshot = None  # an engine command can change every slot
        with open(self.state / 'engine.err', 'a') as err:
            out = subprocess.run(args, stdout=subprocess.PIPE, stderr=err, text=True).stdout
        try:
            value = json.loads(out)
        except ValueError:
            return {'outcome': 'ACTION_REQUIRED', 'reason': out.strip()[:300] or 'no answer from the engine'}
        return value if isinstance(value, dict) else {}

    # One status snapshot serves the calls of one cycle step: each call was a new engine process
    # that scanned /proc and the event journal (1.5 to 3.6 s of CPU), about 10 times in 30 s
    # per runner. Only the runner's own engine commands start or change work; those drop it.
    STATUS_FRESH = 5.0
    snapshot = None  # (directory, monotonic time, engine status output)

    def status(self, directory=None):
        where = str(directory or self.integ or self.repo)
        cached = self.snapshot
        if cached and cached[0] == where and time.monotonic() - cached[1] < self.STATUS_FRESH:
            out = cached[2]
        else:
            out = subprocess.run([sys.executable, str(self.engine_path), where,
                                  '--parallel-status', '--json'], capture_output=True, text=True).stdout
            self.snapshot = (where, time.monotonic(), out)
        try:
            value = json.loads(out)
        except ValueError:
            value = None
        if not isinstance(value, dict) or value.get('outcome') != 'PARALLEL_STATUS':
            self.snapshot = None  # a failed read (the writer lock was held) is never reused
        return value if isinstance(value, dict) else {}

    def tasks(self, snapshot=None):
        snapshot = self.status() if snapshot is None else snapshot
        return snapshot.get('tasks') if isinstance(snapshot.get('tasks'), list) else []

    def in_flight(self):
        # A held conflict whose resolution runs is still moving: the loop must come back for it.
        return bool(self.resolvers) or any(t.get('state') in IN_FLIGHT for t in self.tasks())

    @property
    def resolvers(self):
        """Task -> its merge resolution running beside the loop."""
        return self.__dict__.setdefault('_resolvers', {})

    def job_environment(self, **overrides):
        """Attribute all auxiliary jobs to this repository, including foreground runs.

        Do not replace TMPDIR or sanitize the marker in descendants: checks and fake
        agents they launch are runner work too, wherever their working directory is.
        """
        return dict(os.environ, AUTOWORK_EXECUTION_COMMON=str(self.cfg['git_common']),
                    AUTOWORK_MAIN_EVIDENCE=str(Path(self.cfg['git_common']) / 'autowork-execution/main-evidence'),
                    **overrides)

    # --- Pi -------------------------------------------------------------------------
    def pi_job(self, role, task, directory, message, session, limit, extra=()):
        """Runs one Pi job in a child (so a second Ctrl+C can reach it); returns (ok, text)."""
        out = tempfile.NamedTemporaryFile(dir=self.state / 'runs', prefix='job.', delete=False)
        out.close()
        # The loop waits on this job: say what it is, or the fleet reads the stale status as
        # `not cycling` (TOOLSET-177-d0).
        health.job_started(self.state, role, task)
        env = self.job_environment(PI_AUTOWORK_SESSION=self.integ_branch or os.environ.get('PI_AUTOWORK_SESSION', ''))
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
            health.job_finished(self.state)
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
            for proc in [self.child] + [job['proc'] for job in self.resolvers.values()]:
                if proc:
                    proc.terminate()
            return
        self.stop = True
        LOG.say('Stopping: pausing workers so they resume on the next start, then merging finished work '
                '(Ctrl+C again to force)')
        # Workers are interrupted by the main loop after the engine marks them paused, so a
        # deliberate stop or restart neither spends a task's retry nor holds a second attempt.
        for proc in [self.child] + [job['proc'] for job in self.resolvers.values()]:
            try:
                proc and proc.send_signal(signal.SIGINT)
            except OSError:
                pass

    def on_reload(self, *_):
        """SIGHUP (`autowork restart`, `systemctl reload`): re-execute on the current release and
        settings at the next safe point, keeping the PID and every running worker."""
        self.reload = True

    PLAN_FILES = ('TODO.md', 'goals.json', 'BLOCKERS.md', 'TODO.archive.md')

    def plan_signature(self):
        """What the owner's plan looks like on disk: the planning files in the main checkout
        and the main branch's commit (a planning commit moves it). Stat calls, plus reading the
        ref files when they changed."""
        found = {}
        for path in [Path(self.repo) / name for name in self.PLAN_FILES]:
            try:
                info = path.stat()
                found[path.name] = (info.st_mtime_ns, info.st_size)
            except OSError:
                found[path.name] = None
        found[self.base] = self.base_commit()
        return found

    def base_commit(self):
        """The main branch's commit from its loose ref or `packed-refs`, re-read only when one of
        them changed. Its commit, not the files' stats (TOOLSET-185-74): ending an idle session
        deletes its branch, Git rewrites `packed-refs`, and an idle runner took that for a new
        main and started a session every second."""
        common = Path(self.cfg['git_common'])
        loose, packed = common / 'refs' / 'heads' / self.base, common / 'packed-refs'
        stats = []
        for path in (loose, packed):
            try:
                info = path.stat()
                stats.append((info.st_mtime_ns, info.st_size, info.st_ino))
            except OSError:
                stats.append(None)
        cached = getattr(self, '_base_commit', None)
        if cached and cached[0] == stats:
            return cached[1]
        commit = None
        try:
            commit = loose.read_text().strip() or None
        except OSError:
            try:
                line = next((line for line in packed.read_text().splitlines()
                             if line.endswith(f' refs/heads/{self.base}')), '')
                commit = line.split(' ', 1)[0] or None
            except OSError:
                pass
        self._base_commit = (stats, commit)
        return commit

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
        while not self.stop and not self.reload and time.monotonic() < end:
            time.sleep(min(0.2, max(0.0, end - time.monotonic())))
            if time.monotonic() - checked < 1:
                continue
            checked = time.monotonic()
            now = self.plan_signature()
            if now != seen:
                seen, changed_at = now, time.monotonic()
            elif changed_at is not None and time.monotonic() - changed_at >= self.plan_settle:
                names = [n for n in now if now[n] != start.get(n)]
                labels = ['main' if n == self.base else n for n in names]
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
        canonical = str(workspaces.task_path(self.toolset, self.repo, branch.replace('/', '-')))
        if Path(path).is_dir() and Path(path).resolve() != Path(canonical).resolve():
            if read_only:
                return False
            own = git(self.repo, 'rev-list', '--count', f'{self.base}..{branch}')
            # Git's worktree removal also deletes ignored files: they are still local work.
            contents = git(path, 'status', '--porcelain', '--untracked-files=all', '--ignored')
            if own == '0' and contents == '':
                if not git_ok(self.repo, 'worktree', 'remove', path):
                    raise Finish(1, f'Cannot retire the old integration worktree at {path}')
                git(self.repo, 'branch', '-q', '-d', branch)
                session.unlink(missing_ok=True)
                LOG.say(f'Retired session {branch} at {path}; recreating at the canonical location')
                return False
            Path(canonical).parent.mkdir(parents=True, exist_ok=True)
            if not git_ok(self.repo, 'worktree', 'move', path, canonical):
                raise Finish(1, f'Cannot move the integration worktree from {path} to {canonical}; its work is kept')
            LOG.say(f'Moved session {branch} from {path} to {canonical}; its work is kept')
            path = canonical
            value['path'] = path
            session.write_text(json.dumps(value) + '\n')
        if not Path(path).is_dir():
            if read_only:
                return False
            self.forget_missing_worktree(path)
            path = canonical
            if not git_ok(self.repo, 'worktree', 'add', '-q', path, branch):
                raise Finish(1, f'Cannot restore the integration worktree for {branch}')
            value['path'] = path
            session.write_text(json.dumps(value) + '\n')
        self.integ, self.integ_branch = path, branch
        os.environ['PI_AUTOWORK_SESSION'] = branch
        return True

    def register_planning_merges(self):
        """Repair local driver commands even when planning is not ready for a session."""
        if not self.merge_drivers_registered:
            # Git also runs these after the runner exits. Keep engine calls on
            # self.goals pinned, but register the package that outlives releases.
            driver_goals = Path(self.package) / 'skills/docs-sync/scripts/goals.py'
            for kind in ('goals', 'todo', 'archive'):
                prefix = f'merge.docs-sync-{kind}'
                command = (f'{shlex.quote(sys.executable)} {shlex.quote(str(driver_goals))} '
                           f'merge-driver {kind} %O %A %B')
                for key, value in (('driver', command), ('recursive', 'binary')):
                    if git(self.repo, 'config', '--local', '--get', f'{prefix}.{key}') != value:
                        if not git_ok(self.repo, 'config', '--local', f'{prefix}.{key}', value):
                            raise Finish(1, 'Cannot register planning merge drivers')
            self.merge_drivers_registered = True

    def setup_planning_merges(self):
        """Local executable paths stay in Git config; portable attributes travel in Git."""
        self.register_planning_merges()
        if self.session_busy():
            return  # restored reviews own their pinned session until they finish
        path = Path(self.integ) / '.gitattributes'
        if path.is_symlink():
            raise Finish(1, 'Refusing symlink .gitattributes in session')
        before = path.read_text() if path.exists() else ''
        if self.planning_attributes is None:
            result = subprocess.run([sys.executable, str(self.goals), 'merge-attributes', self.integ],
                                    capture_output=True, text=True)
            if result.returncode:
                raise Finish(1, 'Cannot locate planning archive: ' + result.stderr.strip())
            self.planning_attributes = result.stdout.splitlines()
        missing = [line for line in self.planning_attributes if line not in before.splitlines()]
        if missing:
            # Never include another writer's dirty attributes in this setup commit.
            if git(self.integ, 'status', '--porcelain', '--', '.gitattributes'):
                raise Finish(1, 'Session .gitattributes is dirty; preserve it and reconcile planning drivers')
            path.write_text(before + ('\n' if before and not before.endswith('\n') else '') + '\n'.join(missing) + '\n')
            self.commit(['.gitattributes'], 'chore: register planning-file merge attributes (pi-autowork)')

    def ensure_session(self):
        if self.integ or self.load_session():
            self.setup_planning_merges()
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
        self.setup_planning_merges()

    def merge_planning(self, ref):
        """Complete derived planning data before Git commits, regardless of driver order."""
        if git_ok(self.integ, 'merge-base', '--is-ancestor', ref, 'HEAD'):
            return True
        if not git_ok(self.integ, 'merge', '-q', '--no-commit', '--no-ff', ref):
            return False
        if (Path(self.integ) / 'goals.json').exists():
            result = subprocess.run([sys.executable, str(self.goals), 'merge-finalize', self.integ],
                                    capture_output=True, text=True)
            if result.returncode:
                LOG.say('Planning merge needs reconciliation: ' + (result.stderr or result.stdout).strip())
                return False  # leave the merge for the existing Pi resolver
            git(self.integ, 'add', '--', 'goals.json', 'TODO.md')
        return git_ok(self.integ, 'commit', '-q', '--no-edit')

    def end_session(self):
        """Only a clean, fully merged session is removed. Its regenerable build output goes first:
        a day-old session kept for `.dart_tool/` alone said so every cycle and never rotated."""
        for name in janitor.CACHE_DIRS:
            cache = Path(self.integ) / name
            if cache.is_dir() and not cache.is_symlink() and git_ok(self.integ, 'check-ignore', '-q', name):
                shutil.rmtree(cache, ignore_errors=True)
        if git(self.integ, 'status', '--porcelain', '--untracked-files=all', '--ignored') != '':
            if self.seen.get('session-kept') != self.integ:
                LOG.say(f'Session worktree {self.integ} has uncommitted or ignored files; keeping it and {self.integ_branch}')
                self.seen['session-kept'] = self.integ
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

    def session_expired(self):
        """Rotate idle sessions after a day, using the persisted age across restarts."""
        try:
            session = json.loads((self.state / 'session.json').read_text())
            started = datetime.fromisoformat(session['started']).astimezone()
        except (OSError, ValueError, KeyError, TypeError):
            return False
        return (datetime.now().astimezone() - started).total_seconds() > 24 * 3600

    def merge_main(self):
        """The session into the main branch: the base into the session first (Pi resolves
        conflicts once per base revision), a fast-forward of the base in the main checkout, then a push."""
        self.merge_pending = ''
        if self.session_busy() or self.resolvers:
            return False  # a review or a merge resolution is running; the session merges after it
        if not self.integ and not self.load_session():
            return True
        landing = self.batch_landing()
        if landing and self.base_has_code():
            note = f"{', '.join(landing)} land first, on the trees their batch passed"
            if self.seen.get('merge-batch') != note:
                self.seen['merge-batch'] = note
                LOG.say(f'Merge pending: {note}')
            return False
        self.commit_session_leftovers()
        ahead = self.ahead()
        if ahead == 0:
            return True
        planning_note = self.commit_owner_changes()
        if not self.merge_planning(self.base):
            files = ' '.join((git(self.integ, 'diff', '--name-only', '--diff-filter=U') or '').split()) or 'TODO.md goals.json'
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
        reason = self.fast_forward_main()
        if reason:
            self.merge_pending = f'{self.base} in {self.repo} could not take {self.integ_branch}: {reason}'
        if self.merge_pending:
            if planning_note:
                self.merge_pending += f' (uncommitted changes not committed yet: {planning_note})'
            LOG.say(f'Merge pending: {self.merge_pending}. Branch {self.integ_branch} is kept; the next run retries.')
            return False
        LOG.say(f'Merged {self.integ_branch} into {self.base} ({ahead} commit(s))')
        self.sync_upstream()
        return True

    def checkout_operation(self):
        """Never land through an unfinished operation in the owner's checkout."""
        for marker in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'rebase-merge', 'rebase-apply'):
            found = git(self.repo, 'rev-parse', '--path-format=absolute', '--git-path', marker)
            if found and Path(found).exists():
                return f'a {marker.split("_")[0].split("-")[0].lower()} is in progress in the main checkout'
        return ''

    def fast_forward_main(self):
        """Land the already merged session; return the reason main must wait, or ''."""
        current = git(self.repo, 'symbolic-ref', '--short', '-q', 'HEAD')
        if current != self.base:
            return f'{self.repo} is on {current or "a detached HEAD"}, not {self.base}'
        reason = self.checkout_operation()
        if reason:
            return reason
        old, new = git(self.repo, 'rev-parse', self.base), git(self.repo, 'rev-parse', self.integ_branch)
        if not old or not new or not git_ok(self.repo, 'merge-base', '--is-ancestor', old, new):
            return f'{self.integ_branch} is not a fast-forward of {self.base}'
        # Non-planning work belongs to its writer: even a cleanly mergeable edit waits
        # when the session touches that path. Only planning edits use the off-tree fallback.
        # Do not parse Git's localized "would be overwritten" message.
        changed = (git(self.repo, 'diff', '--no-renames', '--name-only', '-z', old, new) or '').split('\0')
        overlap = [p for p in changed if p and git(self.repo, 'status', '--porcelain', '--', p)]
        if overlap:
            planning = self.owner_planning_paths()
            owned = [p for p in overlap if p not in planning]
            if owned:
                return 'uncommitted changes overlap the landing: ' + ', '.join(owned)
            return self.land_around_edits(old, new)
        held = open_for_writing([Path(self.repo) / p for p in changed if p])
        if held:
            return f'{os.path.relpath(sorted(held)[0], self.repo)} is open for writing'
        result = subprocess.run(['git', '-C', str(self.repo), 'merge', '--ff-only', new],
                                capture_output=True, text=True)
        return '' if result.returncode == 0 else (result.stdout + result.stderr).strip()

    def land_around_edits(self, old, new):
        """Prepare an index without checking out, rebase dirty regular files, then CAS main.

        No stash/reset/checkout touches the owner's work. Unsupported file kinds, staged
        overlapping edits and any conflict wait rather than guessing at their meaning.
        The real index is locked throughout; all files are prepared and checked before
        moving the ref, then checked again before installing any output. Snapshot and
        /proc checks detect races, but are not a lock shared by arbitrary external editors.
        """
        index = Path(git(self.repo, 'rev-parse', '--path-format=absolute', '--git-path', 'index'))
        lock = Path(str(index) + '.lock')
        try:
            lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except OSError:
            return 'the main index is locked; another Git writer may be active'
        prepared, snapshots, outputs = {}, {}, []
        moved = finished = installed = False
        ref = f'refs/heads/{self.base}'
        path = 'main index'
        try:
            with tempfile.TemporaryDirectory(prefix='autowork-land-') as scratch:
                scratch = Path(scratch)
                env = dict(os.environ, GIT_INDEX_FILE=str(scratch / 'index'))
                shutil.copyfile(index, env['GIT_INDEX_FILE'])
                def run(*args, **kwargs):
                    return subprocess.run(['git', '-C', str(self.repo), *args],
                                          capture_output=True, env=env, **kwargs)

                def tree(rev):
                    entries = run('ls-tree', '-rz', rev, check=True).stdout.split(b'\0')
                    return {os.fsdecode(e.split(b'\t', 1)[1]): e.split(b'\t', 1)[0].split()
                            for e in entries if e}

                before, after = tree(old), tree(new)
                changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
                # Raw blobs are correct only without checkout conversions. Do not silently
                # drop CRLF, smudge filters, encodings or ident expansion in this fallback.
                if (git(self.repo, 'config', '--get', 'core.autocrlf') not in (None, 'false')
                        or git(self.repo, 'config', '--get', 'core.eol') == 'crlf'):
                    return f'{changed[0]}: checkout conversion requires a normal Git landing'
                if git(self.repo, 'config', '--get', 'core.sparseCheckout') == 'true':
                    return f'{changed[0]}: sparse checkout requires a normal Git landing'
                staged = run('diff', '--cached', '--name-only', '-z', old, check=True).stdout.split(b'\0')
                result = run('read-tree', '-i', '-m', old, new)
                if result.returncode:
                    return 'the main index cannot take the landing: ' + result.stderr.decode(errors='replace').strip()
                # Check both the current working attributes and the destination's index:
                # the session may itself introduce a conversion in .gitattributes.
                for source in ((), ('--cached',)):
                    attrs = run('check-attr', *source, '-z', 'filter', 'working-tree-encoding', 'eol', 'text',
                                'ident', '--', *changed, check=True).stdout.split(b'\0')
                    for name, attr, value in zip(attrs[0::3], attrs[1::3], attrs[2::3]):
                        if value not in (b'unspecified', b'unset'):
                            return f'{os.fsdecode(name)}: checkout conversion ({os.fsdecode(attr)}) is unsupported'
                for path in sorted(changed):
                    file = Path(self.repo) / path
                    # Refuse symlinks, gitlinks and paths through symlink directories.
                    if any(p.is_symlink() for p in (file, *file.parents)):
                        return f'{path}: symlink path cannot be landed around safely'
                    a, b = before.get(path), after.get(path)
                    if any(e and e[0] not in (b'100644', b'100755') for e in (a, b)):
                        return f'{path}: unsupported file kind'
                    if os.fsencode(path) in staged:
                        return f'{path}: staged edit overlaps the landing'
                    if file.exists() and not file.is_file():
                        return f'{path}: not a regular file'
                    info = file.stat() if file.exists() else None
                    content = file.read_bytes() if info else None
                    snapshots[path] = (info, content)
                    base = run('cat-file', 'blob', a[2].decode(), check=True).stdout if a else None
                    target = run('cat-file', 'blob', b[2].decode(), check=True).stdout if b else None
                    mode = (info.st_mode & 0o777) if info else None
                    dirty_file = content != base or (a and bool(mode & 0o111) != (a[0] == b'100755'))
                    output = target
                    if dirty_file:
                        if (content is None or base is None or target is None or a[0] != b[0]
                                or bool(mode & 0o111) != (a[0] == b'100755')):
                            return f'{path}: uncommitted add/delete or mode change overlaps the landing'
                        for name, data in (('ours', target), ('base', base), ('theirs', content)):
                            (scratch / name).write_bytes(data)
                        merged = run('merge-file', '-p', str(scratch / 'ours'), str(scratch / 'base'),
                                     str(scratch / 'theirs'))
                        if merged.returncode:
                            return f'{path}: uncommitted edit conflicts with the landing'
                        output = merged.stdout
                    # Prepare destination-filesystem outputs before moving main: permission,
                    # disk-space or cross-device errors must not leave a half-written file.
                    file.parent.mkdir(parents=True, exist_ok=True)
                    with tempfile.NamedTemporaryFile(dir=file.parent, prefix='.autowork-land-', delete=False) as out:
                        staged_file = Path(out.name)
                        outputs.append(staged_file)
                        if output is not None:
                            out.write(output)
                            if mode is not None:
                                permissions = (mode if a and a[0] == b[0]
                                               else (mode & ~0o111) | (int(b[0], 8) & 0o111))
                            else:
                                # Linux is the runner's platform. Read rather than change
                                # the process-wide umask while preparing new files.
                                mask = next((line.split()[1] for line in Path('/proc/self/status').read_text().splitlines()
                                             if line.startswith('Umask:')), '077')
                                permissions = (0o777 if b[0] == b'100755' else 0o666) & ~int(mask, 8)
                            os.fchmod(out.fileno(), permissions)
                        out.flush()
                        os.fsync(out.fileno())
                    prepared[path] = staged_file if output is not None else None
                # Fill the real lockfile too before CAS: ENOSPC/flush failures must not
                # advance HEAD or leave an old index describing staged reversions.
                path = 'main index'
                with os.fdopen(lock_fd, 'wb') as stream:
                    lock_fd = None
                    stream.write(Path(env['GIT_INDEX_FILE']).read_bytes())
                    stream.flush()
                    os.fsync(stream.fileno())
                # Validate after the expensive merge work, not just when we first read.
                def unchanged():
                    reason = self.checkout_operation()
                    if reason:
                        return reason
                    if git(self.repo, 'symbolic-ref', '--short', '-q', 'HEAD') != self.base:
                        return 'the main checkout changed branches during landing'
                    held = open_for_writing([Path(self.repo) / p for p in snapshots])
                    if held:
                        return f'{os.path.relpath(sorted(held)[0], self.repo)} is open for writing'
                    def identity(st):
                        return ((st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
                                if st else None)
                    for name, (info, content) in snapshots.items():
                        file = Path(self.repo) / name
                        if any(p.is_symlink() for p in (file, *file.parents)):
                            return f'{name}: path changed to a symlink during landing'
                        now = file.lstat() if file.exists() else None
                        if identity(now) != identity(info) or (now and file.read_bytes() != content):
                            return f'{name}: working file changed during landing'
                    return ''

                reason = unchanged()
                if reason:
                    return reason
                if not git_ok(self.repo, 'update-ref', ref, new, old):
                    return f'{self.base} changed during landing; compare-and-swap refused'
                moved = True
                reason = unchanged()
                if reason:
                    if not git_ok(self.repo, 'update-ref', ref, old, new):
                        raise Finish(1, f'Cannot restore {self.base} after refused landing: {reason}')
                    moved = False
                    return reason
                for path, output in prepared.items():
                    file = Path(self.repo) / path
                    if output is None:
                        file.unlink(missing_ok=True)
                    else:
                        os.replace(output, file)
                    installed = True
                # Only the committed session tree goes into the index. The rebased owner
                # edit stays a working-tree diff, never part of a commit.
                os.replace(lock, index)
                finished = True
                return ''
        except (OSError, subprocess.CalledProcessError) as exc:
            # A file may disappear between lstat/read in the post-CAS validation.
            # Nothing has been installed yet: restore the ref just as for a changed
            # snapshot, rather than retaining an advanced HEAD with the old index.
            if moved and not installed:
                if not git_ok(self.repo, 'update-ref', ref, old, new):
                    raise Finish(1, f'Cannot restore {self.base} after refused landing: {exc}') from exc
                moved = False
            if moved:
                raise Finish(1, f'Landing moved {self.base} but could not finish writing {path}: {exc}; '
                             f'prepared index kept at {lock}; remaining .autowork-land-* outputs kept') from exc
            if isinstance(exc, OSError) and exc.filename:
                path = os.path.relpath(exc.filename, self.repo)
            return f'{path}: cannot prepare landing: {exc}'
        finally:
            if lock_fd is not None:
                os.close(lock_fd)
            if not moved or finished:
                lock.unlink(missing_ok=True)
                for output in outputs:
                    output.unlink(missing_ok=True)

    def sync_upstream(self):
        """Pull, then push: merge commits the upstream gained into the session and the main
        branch, then publish the main branch if it is ahead. Called after every landing and once
        at start, so a backlog is published and the session never drifts behind the upstream."""
        if os.environ.get('PI_AUTOWORK_PUSH', '1') == '0':
            return
        upstream = git(self.repo, 'rev-parse', '--abbrev-ref', '--symbolic-full-name', f'{self.base}@{{u}}')
        if not upstream or '/' not in upstream:
            return self.push()  # says once that there is no upstream
        remote, branch = upstream.split('/', 1)
        on_base = git(self.repo, 'symbolic-ref', '--short', '-q', 'HEAD') == self.base
        if on_base and git_ok(self.repo, 'fetch', '--quiet', remote, branch):
            behind = int(git(self.repo, 'rev-list', '--count', f'{self.base}..{upstream}') or 0)
            if behind and self.integ and not self.session_busy() and not dirty(self.integ):
                if self.merge_planning(upstream) and not self.fast_forward_main():
                    LOG.say(f'Pulled {behind} commit(s) from {upstream} into {self.base}')
                else:
                    git(self.integ, 'merge', '--abort')
                    LOG.say(f'{upstream} has {behind} commit(s) that do not merge cleanly; the push resolves them')
        if int(git(self.repo, 'rev-list', '--count', f'{upstream}..{self.base}') or 0):
            self.push()

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
                    and self.merge_planning(upstream):
                if not self.fast_forward_main():
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

    def owner_planning_paths(self):
        """The only main-checkout paths the quiet owner-planning sweep may commit."""
        _, dispatch = touches_inference.modules(self.toolset)
        try:
            archive = dispatch.execution.archive_file(Path(self.repo)).relative_to(self.repo).as_posix()
        except (ValueError, OSError):
            archive = None
        return {'TODO.md', 'goals.json', 'BLOCKERS.md', 'TODO.archive.md'} | ({archive} if archive else set())

    def commit_owner_changes(self):
        """Commit only quiet owner-planning files that no process holds open for writing.

        Other main-checkout work belongs to its writer, regardless of age or quietness.
        An unfinished Git operation is left alone. Returns '' when committed or no planning
        files were uncommitted, else why planning waited.
        """
        if git(self.repo, 'symbolic-ref', '--short', '-q', 'HEAD') != self.base:
            return f'the main checkout is not on {self.base}'
        reason = self.checkout_operation()
        if reason:
            return reason
        entries = iter([e for e in (git(self.repo, 'status', '--porcelain', '-z', '--untracked-files=all') or '')
                        .split('\0') if e])
        paths = []
        for entry in entries:
            status, path = entry[:2], entry[3:]
            if 'U' in status or status in ('AA', 'DD'):
                return f'{path} has an unresolved conflict'
            paths.append(path)
            if status[0] in 'RC':
                paths.append(next(entries, ''))  # the rename's source, so the commit records it
        planning = self.owner_planning_paths()
        paths = self.publishable([p for p in paths if p in planning])
        quiet = float(os.environ.get('PI_AUTOWORK_PLANNING_QUIET', '600'))
        recent = self.recent_owner_paths(paths, quiet)
        if not paths:
            return ''
        files = [Path(self.repo) / p for p in paths]
        if recent:
            return f'{", ".join(recent[:4])} changed in the last {int(quiet // 60)} min'
        held = open_for_writing([f for f in files if f.exists()])
        if held:
            return f'{", ".join(sorted(os.path.relpath(h, self.repo) for h in held))} is open for writing'
        git(self.repo, 'add', '-A', '--', *paths)
        if not git_ok(self.repo, 'commit', '-q', '-m', 'docs(tasks): owner planning (pi-autowork)',
                      '-m', 'Uncommitted planning changes in the main checkout, quiet and open nowhere, '
                            'committed so finished work can merge (auto work).', '--', *paths):
            return 'the commit of uncommitted changes failed'
        self.recent_owner_paths([], quiet)
        shown = ', '.join(paths[:6]) + (f' (+{len(paths) - 6} more)' if len(paths) > 6 else '')
        LOG.say(f'Committed uncommitted changes in {self.repo} ({shown}) so the session can merge')
        return ''

    def recent_owner_paths(self, paths, quiet):
        """Quiet means unchanged bytes since our last observation, not an old mtime.

        Persist observations so a service restart does not restart the quiet interval.
        Clean paths disappear from the record; a later edit starts a fresh interval.
        """
        record = self.state / 'owner-content.json'
        try:
            previous = json.loads(record.read_text())
            if not isinstance(previous, dict):
                previous = {}
        except (OSError, ValueError):
            previous = {}
        now, observed, recent = time.time(), {}, []
        for path in paths:
            file = Path(self.repo) / path
            try:
                data = os.fsencode(os.readlink(file)) if file.is_symlink() else file.read_bytes()
                digest = hashlib.sha256(data).hexdigest()
            except FileNotFoundError:
                digest = 'deleted'
            except OSError:
                recent.append(path)
                continue
            old = previous.get(path)
            since = (old.get('since') if isinstance(old, dict) and old.get('hash') == digest else now)
            if not isinstance(since, (int, float)) or since > now:
                since = now
            observed[path] = {'hash': digest, 'since': since}
            if now - since < quiet:
                recent.append(path)
        if observed != previous:
            with tempfile.NamedTemporaryFile(mode='w', dir=self.state, prefix='owner-content.', delete=False) as out:
                json.dump(observed, out)
            os.replace(out.name, record)
        return recent

    def sweep_tmp(self):
        """Stale agent scratch in RAM-backed /tmp goes, at most every 30 minutes per host
        (janitor.py, TOOLSET-162-d2), so it cannot keep new workers from starting."""
        self.prune_build_caches()
        try:
            result = janitor.sweep_if_due(Path(self.state).parent)
        except OSError:
            return
        if result and result[0]:
            LOG.say(f'Removed {result[0]} stale /tmp entries ({result[1] / 2 ** 30:.1f} GB) that nothing had '
                    f'used for {janitor.stale_after() // 60} min')

    def prune_build_caches(self):
        """Build output of this runner's idle worktrees goes every 30 minutes, and at once when the
        disk is low (TOOLSET-210-53): one repository's worktrees held 87 GB of it and filled the disk."""
        try:
            free = shutil.disk_usage(self.repo).free / 2 ** 30
        except OSError:
            return
        urgent = free < 2 * float(os.environ.get('PI_AUTOWORK_MIN_FREE_DISK_GB') or 20)
        if not urgent and time.monotonic() - self.seen.get('caches-pruned', -1e9) < janitor.SWEEP_EVERY:
            return
        self.seen['caches-pruned'] = time.monotonic()
        busy = [self.integ] + [t.get('worktree') for t in self.tasks()
                               if t.get('state') in ('dispatched', 'running', 'reported', 'integrating')]
        try:
            count, freed = janitor.prune_build_caches(Path(self.repo) / '.worktrees', busy, urgent=urgent)
        except OSError:
            return
        if count:
            LOG.say(f'Removed build output from {count} idle worktree(s) ({freed / 2 ** 30:.1f} GB)'
                    + (f'; {free:.0f} GB were free' if urgent else ''))

    def publishable(self, paths):
        """publishable(), with each held-back path logged once per commit."""
        keep, held = publishable(self.repo, paths)
        for path, key, message in held:
            if self.seen.get('unpublishable-' + path) != key:
                self.seen['unpublishable-' + path] = key
                LOG.say(message)
        return keep

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
        """The session follows the main branch whenever no review is running, and takes
        planning-only commits even beside one, so the owner's plan and toolset fixes reach
        dispatch and validation within one review (TOOLSET-233-ba). With nothing in flight, a
        conflict (the owner's TODO.md edit against the session's own bookkeeping) is resolved at
        once through the session merge, not left for a final merge a stalled runner never
        reaches; a merge that still fails is a runner blocker the owner sees. A refused ledger is an
        exception: task slots cannot settle until the owner's repair reaches the session, so the
        owner's planning edits are committed even beside work in flight. A merge resolution keeps
        the session still: its merge is adopted only onto the revision it merged."""
        if self.resolvers:
            return
        if self.integ and (not self.in_flight() or self.ledger_errors):
            # The owner's quiet planning edits (answers to held tasks) are committed even when
            # there is nothing to merge, or a stalled runner never sees them (TOOLSET-157-cd).
            self.commit_owner_changes()
        behind = git(self.repo, 'rev-list', f'{self.integ_branch}..{self.base}') if self.integ else ''
        if not behind or dirty(self.integ) or (self.batch_pending() and not self.session_busy()):
            return  # batch verdicts wait to land on the trees they were reached on (TOOLSET-258-07)
        if self.session_busy():
            # A review is running. Planning-only commits are taken at once: integration lands the
            # review's merge on top without validating again (TOOLSET-233-ba). Anything else waits
            # for the review to end, which is at most one review, not until the session lands.
            changed = git(self.repo, 'diff', '--name-only', f'{self.integ_branch}...{self.base}').split()
            if not changed or not all(p in PLANNING_FILES or p.startswith('docs/') for p in changed):
                return
        # Workers have their own worktrees and integration merges their commits into the session
        # as it is then, so work in flight never keeps the session from following main: a stale
        # session hid the owner's plan and every toolset fix for hours (TOOLSET-233-ba).
        import fcntl
        path = Path(self.cfg['git_common']) / 'autowork-execution' / 'writer.lock'
        path.parent.mkdir(exist_ok=True)
        with open(path, 'a') as lock:
            try:  # the engine moves the session under this lock; never beside it
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return  # the next cycle tries again
            merged = self.merge_planning(self.base)
            if not merged:
                git(self.integ, 'merge', '--abort')
        if merged:
            self.merge_blocker = ''
            rev = git(self.repo, 'rev-parse', self.base)
            if self.seen.get('took-base') != rev:
                self.seen['took-base'] = rev
                LOG.say(f'Took {len(behind.split())} commit(s) from {self.base} into the session')
            return
        if self.session_busy() or self.in_flight():
            return  # a conflict waits for the resolver at the next landing
        if self.merge_main():
            self.merge_blocker = ''
        else:
            self.merge_blocker = f'the session cannot take {self.base}: {self.merge_pending}'

    def land(self):
        """After every task closes: bring the session to the main branch, pull what upstream
        gained and push (owner direction, 2026-10-17: commit, push to upstream and pull-merge
        after every task). Workers keep their own bases, so others in flight do not wait it;
        only a running review does (its fast-forward needs the session unchanged)."""
        if not self.integ or self.session_busy():
            return
        self.landed_at, self.land_soon = time.monotonic(), False
        if self.ahead():
            self.merge_main()
        else:
            self.sync_upstream()

    def land_planning(self):
        """TOOLSET-188-75: a session whose tasks all run, wait or are held never closed one, so
        its planning commits (questions, maintainer repairs) stayed off main for hours. Land
        after such a commit, and every PI_AUTOWORK_LAND_EVERY seconds while ahead; running
        workers do not wait it; a Pi job does, and so does a review unless no merge is needed."""
        if not self.integ or self.child or self.resolvers:
            return
        if not (self.land_soon or time.monotonic() - self.landed_at >= self.land_every):
            return
        if self.integration:  # a review runs, or its answer is not read yet
            if self.session_busy() and self.land_beside_review():
                self.landed_at, self.land_soon = time.monotonic(), False
            return  # otherwise still due: it lands after the review
        self.landed_at, self.land_soon = time.monotonic(), False
        if self.ahead():
            self.merge_main()

    def land_beside_review(self):
        """TOOLSET-190-bf: with the base already in the session, landing is a fast-forward of the
        main checkout and a push; the session branch the review fast-forwards at its end is not
        touched, so it need not wait for a review (one runner's 25-minute reviews ran back to
        back and kept 14 planning commits off main). False when a merge would be needed."""
        ahead = self.ahead()
        if (not ahead or git(self.repo, 'symbolic-ref', '--short', '-q', 'HEAD') != self.base
                or not git_ok(self.repo, 'merge-base', '--is-ancestor', self.base, self.integ_branch)
                or self.fast_forward_main()):
            return False
        LOG.say(f'Merged {self.integ_branch} into {self.base} ({ahead} commit(s)) beside the running review')
        self.sync_upstream()
        return True

    def commit(self, paths, *message):
        if self.session_busy():
            return False  # a review is running: its fast-forward needs the session unchanged
        for path in paths:
            git(self.integ, 'add', '-A', '--', path)
        if git_ok(self.integ, 'diff', '--cached', '--quiet'):
            return False
        args = []
        for line in message:
            args += ['-m', line]
        done = git_ok(self.integ, 'commit', '-q', *args)
        self.land_soon = self.land_soon or done
        return done

    def finish(self, code, text):
        self.stop_integration()
        if self.integ:
            self.merge_main()
            if not self.merge_pending and not self.in_flight():
                self.engine('--parallel', str(self.workers), '--max-workers', '16', '--release')
                if self.ahead() == 0:
                    self.end_session()
        if self.merge_pending and code == 0:
            code = 4
        raise Finish(code, text)

    # --- Coordinator -------------------------------------------------------------------
    def note_state(self, task, state, reason='', quiet=False, *, paused=False):
        """Log each task's lifecycle change once. A waiting task is not news (the runner's
        one `No task can start now` line covers them), and states already reached when the
        runner started are not replayed (quiet)."""
        word = lifecycle(state, paused=paused)
        if self.seen.get(task) == word:
            return
        self.seen[task] = word
        if quiet or word == 'pending':
            return
        LOG.say(f'{task}: {word}' + (f' — {reason}' if reason else ''))

    # Holds that say something is broken for every task (a worker that dies or produces nothing,
    # a launch or a review that fails), and so earn the failure-streak pause. Holds shaped by the
    # queue (overlap, scope, a conflict, a changed entry, a worker's own blocker) are about one
    # task: three of them paused a whole runner for an hour.
    SYSTEMIC = ('crash', 'empty', 'launch', 'validation', None, '')

    # Integration mechanics, not a broken task or host: a review a restart interrupted, or a commit
    # already on main. Three of them after one restart paused every new task for an hour.
    MECHANICS = ('already in canonical HEAD', 'abandoned integration tree', 'stale or mismatched integration validation')

    def count_failure(self, task, cause=None, reason=''):
        if (cause not in self.SYSTEMIC or self.seen.get('counted-' + task)
                or any(text in (reason or '') for text in self.MECHANICS)):
            return
        if cause == 'validation' and self.environment_hold(task):
            return  # it could not be checked here: the runner provisions it (TOOLSET-173-94)
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
        self.finish_resolvers()
        snapshot = self.status()
        rows = self.tasks(snapshot)
        for row in rows:
            task, state, reason = row.get('task'), row.get('state') or '', row.get('reason') or ''
            before = self.seen.get(task)
            if state == 'held' and row.get('cause') == 'conflict' and not self.session_busy():
                if self.resolve_task_conflict(row):
                    self.settled = True
                    continue
                if task in self.resolvers:
                    continue  # its resolution runs beside the loop
            if (state == 'held' and row.get('cause') == 'blocker' and not self.session_busy()
                    and self.triage_blocker(row)):
                self.settled = True
                continue
            self.note_state(task, state, reason, quiet=not self.known_at_start, paused=row.get('paused'))
            if task == self.once_task and state == 'held':
                self.draining = True
            # Only a failure this run watched happen counts toward the streak; holds found
            # at start (say after a self-restart) were counted by the run that saw them.
            if state == 'held' and before and before != 'failed':
                self.count_failure(task, row.get('cause'), reason)
        self.known_at_start = True
        if self.stop:
            return
        if self.session_busy():
            return  # one review at a time; it is collected when it ends
        handled, deferred = set(), []
        finished = self.collect_integration()
        if finished and finished[0] == self.BATCH:
            self.batch_done(finished[1])
        elif finished:
            handled.add(finished[0])
            self.integrated(*finished, resolve_conflicts=False)
            if finished[1].get('cause') == 'conflict':
                deferred.append(finished[0])
            if self.stop:
                return
        self.reverify_held(rows)
        for task in [r['task'] for r in rows if r.get('state') == 'integrated' and r['task'] not in handled]:
            if self.stop:
                return
            self.close_task(task)
        # A conflict resolved above changed that candidate's commit: batch on the current
        # revisions, not the snapshot taken before the resolution.
        rows = self.tasks(self.status())
        if self.resolvers:
            return  # their merged revisions batch together once they end, before the next review
        # The engine integrates one candidate at a time, in priority order, and names the one it
        # wants when asked for another: start that one, never every candidate in turn (13 engine
        # runs and 13 "verifying" lines after one reload, TOOLSET-238-11).
        queue = [r['task'] for r in rows if r.get('state') in ('reported', 'integrating') and r['task'] not in handled]
        chain = [t for t in self.batch_chain() if t in queue]
        conflicts = [t for t in self.batch_conflicts() if t in queue and t not in chain]
        # Verified together: they land first, in order; then the batch's conflicts are held for the resolver.
        queue = chain + conflicts + [t for t in queue if t not in chain and t not in conflicts]
        batch = self.batch_due(batchable(rows, handled))
        if batch:
            self.start_batch(batch)
            return  # it runs beside the loop; its candidates land when it ends
        while queue:
            task = queue.pop(0)
            if self.stop:
                return
            if task in handled:
                continue
            if self.reexec_due() and task not in chain:
                # Back-to-back reviews left no gap for a reload: one runner kept its morning
                # release for hours (TOOLSET-236-4d). Re-execute now, between two reviews; a
                # batch-passed candidate lands first, or the reload would wait on it forever.
                self.resolve_deferred(deferred)
                self.restart_if_updated()
                return
            if deferred and task not in conflicts:
                # Before a review, which would keep the resolver waiting until it ends: eight held
                # conflicts sat behind the next candidate's 45-minute review.
                self.resolve_deferred(deferred)
                return
            self.follow_base()  # each review validates against the main branch as it is now
            self.start_integration(task)
            # Quick refusals (another task first, a busy writer) answer at once; one still running
            # after a moment is the review, and only it reads "verifying".
            finished = self.collect_integration(wait=1.5)
            if finished is None:
                self.note_integrating(task, chain)
                finished = self.collect_integration(wait=3.5)
            if finished is None:
                self.resolve_deferred(deferred)
                return  # a real review: it runs beside the loop until it ends
            handled.add(task)
            first = re.search(r'highest-priority reported task first: (\S+)', finished[1].get('reason') or '')
            if first:
                # A batch conflict that merges now waits its turn; the rest are still offered first.
                if first[1] not in handled and task not in conflicts:
                    queue.insert(0, first[1])
                continue
            if finished[1].get('outcome') in ('INTEGRATED', 'HELD'):
                self.note_integrating(task, chain)  # a quick review still ran: say so before its answer
            self.integrated(*finished, resolve_conflicts=False)
            if finished[1].get('cause') == 'conflict':
                deferred.append(task)
        self.resolve_deferred(deferred)

    def note_integrating(self, task, chain):
        """A batch-passed candidate lands on its batch's verdict: 'landing', not 'verifying', which
        read as a fresh review for the 15 hours one such candidate waited (TOOLSET-281-0d)."""
        if task in chain:
            self.note_state(task, 'landing', 'passed in its batch; not reviewed again')
        else:
            self.note_state(task, 'integrating')

    def resolve_deferred(self, deferred):
        """Resolve the conflicts this pass held back, then batch their merged revisions so they
        share one check. Runs before the pass returns it to the loop, so a held conflict never
        reaches a cycle boundary where a fresh retry could start (or --once would read it as final)."""
        if not deferred or self.stop or self.session_busy():
            return False
        for task in deferred:
            row = next((r for r in self.tasks() if r.get('task') == task), None)
            if row and row.get('state') == 'held' and row.get('cause') == 'conflict':
                self.resolve_task_conflict(row)
        rows = self.tasks(self.status())
        batch = self.batch_due(batchable(rows))
        if batch:
            self.start_batch(batch)
            return True
        return False

    def integrated(self, task, result, resolve_conflicts=True):
        """Act on the engine's answer to integrating ``task``. ``resolve_conflicts`` False holds a
        conflict instead of resolving it now: the next cycle's first pass resolves every held
        conflict together, so their merged revisions batch into one check instead of one each."""
        outcome, reason = result.get('outcome') or 'ACTION_REQUIRED', result.get('reason') or ''
        if outcome != 'BUSY':
            self.seen.pop('busy-' + task, None)
        if outcome == 'INTEGRATED':
            self.settled = True
            if dropped := result.get('ledger_edit_dropped'):
                LOG.say(f'{task}: its edit to {", ".join(dropped["paths"])} was left out; '
                        'the docs maintainer will review it')
            self.note_state(task, 'integrated')
            self.close_task(task)
        elif outcome == 'HELD':
            self.settled = True
            if (result.get('cause') == 'validation' and self.environment_hold(task)
                    and self.provision_and_reverify(task, self.reviewer_version())):
                return  # reviewed again before a refill can start a fresh retry
            if result.get('cause') == 'conflict':  # before a refill can start a fresh retry
                if resolve_conflicts:
                    row = next((r for r in self.tasks() if r.get('task') == task), None)
                    if row and (self.resolve_task_conflict(row) or task in self.resolvers):
                        return
                else:
                    # Grouping: hold it. The engine never retries a conflict with a fresh worker,
                    # so it waits safely for the grouped resolution; a transient conflict is not a
                    # failure streak either.
                    self.note_state(task, 'held', reason)
                    return
            self.note_state(task, 'held', reason)
            self.count_failure(task, result.get('cause'), reason)
            if task == self.once_task:
                self.draining = True
        elif outcome == 'SET_ASIDE':  # closed on the base meanwhile (TOOLSET-218-d0)
            self.note_state(task, 'closed', reason)
        elif outcome == 'BUSY':  # a live session in the main checkout: wait, said once
            # Once per session, not per status: "running command" and "terminal used 2 min ago"
            # of the same session repeated the line every minute.
            said = re.sub(r'\s*\(session: [^)]*\)', '', reason)
            if self.seen.get('busy-' + task) != said:
                if reason.startswith(('the repository writer lock', 'Repository execution lock')):
                    # This runner's own engine steps held it (TOOLSET-194-46): not another session.
                    LOG.say(f'{task}: integrating again shortly; {reason}')
                else:
                    LOG.say(f'{task}: waiting to integrate until another session leaves the main checkout ({reason})')
            self.seen['busy-' + task] = said
        elif outcome == 'PRIORITY_DRIFT' and self.draining and self.reconcile_priority():
            # A ledger repair can add a task while --once is draining. No refill
            # will reconcile its order, so do that before retrying this integration.
            self.settled = True
        elif 'highest-priority' not in reason:  # another reported task goes first
            LOG.say(f'{task}: integration needs attention: {reason or outcome}')

    def reviewer_version(self):
        """Fingerprint only verdict code and prompts, not unrelated worker helpers."""
        source = Path(__file__).with_name('worker.py').read_text()
        parts = {}
        for node in ast.parse(source).body:
            if isinstance(node, ast.FunctionDef) and node.name in ('review', 'full_suite_gate', 'run_gate', 'quiet_reruns'):
                parts[node.name] = ast.get_source_segment(source, node)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in ('REVIEW', 'LIVE', 'NO_LIVE', 'GATE'):
                        parts[target.id] = ast.literal_eval(node.value)
        digest = hashlib.sha256(json.dumps(parts, sort_keys=True).encode())
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
            if row.get('state') == 'held' and row.get('cause') == 'timeout' and not self.stop:
                self.reverify_after_timeout(task, version)
                continue
            held_by_validation = row.get('state') == 'held' and (
                row.get('cause') in ('validation', 'reviewed_twice')
                or (not row.get('cause') and str(row.get('reason') or '').startswith('integration validation failed')))
            if not held_by_validation or self.stop:
                continue
            if self.seen.get('reverify-' + task) == version:
                self.provision_and_reverify(task, version)
                continue
            self.seen['reverify-' + task] = version
            if self.engine('--parallel-reverify', task, '--reviewer-version', version).get('outcome') == 'REVERIFY':
                self.seen[task] = ''
                self.settled = True
                LOG.say(f'{task}: the reviewer changed since this commit was held; verifying it again')

    def reverify_after_timeout(self, task, version):
        """A review that ran out of time is run again on the same commit, with twice the limit it
        had, up to the cap: no worker reruns and no attempt is spent (TOOLSET-196-fb)."""
        _, dispatch = touches_inference.modules(self.toolset)
        if dispatch.resource_gate(0, float(self.min_free_mb), self.integ):
            return  # a host/check-only worker hold waits for a quieter host too
        try:
            slot = json.loads((Path(self.cfg['git_common']) / 'autowork-execution/slots' / (task + '.json')).read_text())
            prior = re.search(r'\.t(\d+)$', str(slot.get('reverified') or ''))
            durable_limit = min(self.REVIEW_CAP, int(prior[1])) if prior else 0
        except (OSError, ValueError, TypeError):
            durable_limit = 0
        given = max(self.timeout_limits.get(task) or self.review_limit(), durable_limit)
        if given >= self.REVIEW_CAP and (durable_limit >= self.REVIEW_CAP or self.seen.get('timeout-capped-' + task)):
            return
        limit = int(min(self.REVIEW_CAP, 2 * given))
        result = self.engine('--parallel-reverify', task, '--reviewer-version', f'{version}.t{limit}')
        if result.get('outcome') != 'REVERIFY':
            return
        self.seen['timeout-capped-' + task] = limit >= self.REVIEW_CAP
        self.timeout_limits[task] = limit
        self.seen[task] = ''
        self.settled = True
        if result.get('resume_worker'):
            LOG.say(f'{task}: the host has room again; resuming the same attempt to commit its finished work')
        else:
            LOG.say(f'{task}: its review ran out of time; reviewing the same commit again with a {limit // 60}-minute limit')

    MAIN_CHECK_WAIT = 1800

    def check_main(self):
        """Main's declared full offline check (PI_AUTOWORK_MAIN_CHECK), in the background, once
        per main revision, when the host has room and nothing is being verified (TOOLSET-176-98).
        A red result gives the DOCS-MAINTAINER a trigger to add one repair task."""
        cmd = main_check.command(repo=self.repo)
        if not cmd or self.stop:
            return
        record = main_check.read(self.state)
        pid, started = record.get('pid'), record.get('start_time')
        if pid is not None:
            try:
                # After re-exec there is no Popen left to reap this child. Never wait on a
                # reused PID; old records without start ticks still need zombie recovery.
                gone = (int(pid) <= 0 or (started is not None and main_check.start_time(pid) != str(started))
                        or os.waitpid(int(pid), os.WNOHANG)[0] != 0)
            except ChildProcessError:  # ECHILD: already reaped or another parent
                gone = not main_check.alive(pid, started)
            except (TypeError, ValueError):
                gone = True
            if gone:
                record.pop('pid', None)
                record.pop('start_time', None)
                main_check.write(self.state, record)
        if record.get('state') == 'running':
            if main_check.exit_code(self.state) is not None or not main_check.alive(pid, started):
                self.finish_main_check(record)
            return
        if record.get('pid') is not None:  # receipt consumed just before bash exited: reap next cycle
            return
        rev = git(self.repo, 'rev-parse', self.base)
        if not rev or rev == record.get('rev'):
            return
        if record.get('state') == 'green' and record.get('rev'):
            # The runner's own questions and planning commits moved main: a full check for each
            # (8 of 39 in a day) took a host check slot that a waiting review needed.
            changed = (git(self.repo, 'diff', '--name-only', record['rev'], rev) or '').split()
            if changed and all(p in PLANNING_FILES for p in changed):
                main_check.write(self.state, dict(record, rev=rev, green=rev))
                return
        # It waits for room at most MAIN_CHECK_WAIT: with eight workers and batches a review or a
        # loaded host was nearly always there, and main went unchecked for hours while it was red.
        if time.time() - float(record.get('finished') or 0) < self.MAIN_CHECK_WAIT:
            try:
                if os.getloadavg()[0] >= (os.cpu_count() or 1):
                    return
            except OSError:
                pass
            if any(t.get('state') == 'integrating' for t in self.tasks()):
                return
        path = self.scratch_checkout('main-check', rev)
        if not path:
            return
        tmp = tempfile.mkdtemp(prefix='aw-main-')  # honor the runner's short, disk-backed TMPDIR
        done, reruns = self.state / 'main-check.exit', self.state / 'main-check-reruns.json'
        done.unlink(missing_ok=True)
        reruns.unlink(missing_ok=True)
        reruns.with_suffix('.log').unlink(missing_ok=True)
        retry = shlex.join([sys.executable, str(Path(main_check.__file__).resolve()),
                            str(self.state / 'main-check.log'), path, str(reruns), rev])
        # Finish retries before publishing the receipt: reloads can adopt the job,
        # and finish_main_check can then safely remove the shared scratch checkout.
        progress = self.state / 'main-check-slot.json'
        progress.unlink(missing_ok=True)
        run = shlex.join([sys.executable, str(Path(main_check.__file__).resolve()), '--run', cmd,
                          os.environ.get('PI_AUTOWORK_VALIDATE_TIMEOUT') or '3600', str(progress)])
        script = f'{run}\nresult=$?\nif [ "$result" -ne 0 ]; then {retry}; fi\necho "$result" > {shlex.quote(str(done))}'
        with open(self.state / 'main-check.log', 'w') as log:
            child = subprocess.Popen(['bash', '-c', script], cwd=path,
                                     env=self.job_environment(TMPDIR=tmp),
                                     stdout=log, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, start_new_session=True)
        main_check.write(self.state, dict(state='running', rev=rev, pid=child.pid,
                                          start_time=main_check.start_time(child.pid), started=time.time(), path=path,
                                          tmp=tmp, slot_status=str(progress), green=record.get('green'), failures=record.get('failures'),
                                          red_since=record.get('red_since'), gated=record.get('gated'),
                                          crashed=record.get('crashed'), flaky_history=record.get('flaky_history') or {}))
        LOG.say(f'Checking main at {rev[:7]} in the background: {cmd}')

    def finish_main_check(self, record):
        """Record a finished (or aborted) main check and clean its checkout up."""
        code = main_check.exit_code(self.state)
        path, tmp = record.get('path') or '', record.get('tmp') or ''
        if path and Path(path).name.startswith('pi-scratch-main-check'):
            git(self.repo, 'worktree', 'remove', '--force', path)
        if tmp and Path(tmp).name.startswith('aw-main-'):
            shutil.rmtree(tmp, ignore_errors=True)
        rev, green = record.get('rev', ''), record.get('green')

        def finished(value):
            common = git(self.repo, 'rev-parse', '--path-format=absolute', '--git-common-dir')
            if common and rev and code is not None:
                main_check.publish_evidence(self.state, common, rev, value)
            return main_check.write(self.state, value)

        history = record.get('flaky_history') or {}
        # The receipt can precede bash's exit. Retain its identity until a later cycle reaps it.
        child = {k: record[k] for k in ('pid', 'start_time') if k in record}
        if code is None:  # the runner stopped under it: check this revision again
            main_check.write(self.state, dict(state='aborted', rev='', green=green, failures=record.get('failures'),
                                              red_since=record.get('red_since'), flaky_history=history, **child))
            return
        try:
            log_text = (self.state / 'main-check.log').read_text(errors='replace')
        except OSError:
            log_text = ''
        failures = named = main_check.failures(log_text, limit=None) if code else []
        flaky, incomplete = [], False
        if code:
            incomplete = code != 1  # signals and shell errors are not ordinary unittest failures
            try:
                reruns = json.loads((self.state / 'main-check-reruns.json').read_text())
                if reruns.get('rev') == rev and isinstance(reruns.get('flaky'), list):
                    flaky = [test_id for test_id in failures if test_id in reruns['flaky']]
                    incomplete = incomplete or bool(reruns.get('incomplete'))
            except (OSError, ValueError, AttributeError, TypeError):
                pass
            failures = [test_id for test_id in failures if test_id not in flaky]
            for test_id in flaky:
                revisions = history.setdefault(test_id, [])
                if rev not in revisions and len(revisions) < 3:
                    revisions.append(rev)
        if code and not failures and (not named or incomplete):
            # It crashed before naming a test, or was cut short with only flaky ones named
            # (TOOLSET-237-35): no placeholder test IDs for the maintainer to repair. Once more;
            # a second crash is a broken check, not a red main.
            crash = main_check.crash_line(log_text)
            if record.get('crashed') != rev:
                finished(dict(state='recheck', rev='', crashed=rev, green=green,
                                                  failures=record.get('failures'), red_since=record.get('red_since'),
                                                  flaky_history=history, **child))
                LOG.say(f'The main check at {rev[:7]} crashed before any test result ({crash}); checking it once more')
                return
            finished(dict(state='broken', rev=rev, green=green, crash=crash, finished=time.time(),
                                              failures=record.get('failures'), red_since=record.get('red_since'),
                                              flaky_history=history, **child))
            LOG.say(f'The main check is broken at {rev[:7]}: it crashed twice before any test result ({crash})')
            self.maintain(main_only=True)
            return
        skipped = main_check.gate_skips(log_text)
        if not failures and skipped and record.get('gated') != rev:
            # A busy host skipped some tests (TOOLSET-193-54): check this revision once more when
            # the load allows (check_main waits for it) before calling it green.
            finished(dict(state='recheck', rev='', gated=rev, green=green,
                                              failures=record.get('failures'), red_since=record.get('red_since'),
                                              flaky=flaky, flaky_history=history, **child))
            LOG.say(f'Main at {rev[:7]} passed, but the busy host skipped {skipped} test(s); '
                    'checking it again when the load allows')
            return
        if not failures:
            finished(dict(state='green', rev=rev, green=rev, finished=time.time(),
                                              flaky=flaky, flaky_history=history, **child))
            if record.get('failures'):
                LOG.say(f'Main is green again at {rev[:7]}')
            if flaky:
                LOG.say(f'Main is green at {rev[:7]} ({len(flaky)} flaky): {", ".join(flaky)}')
            if any(len(revisions) >= 3 for revisions in history.values()):
                self.maintain(main_only=True)
            return
        commits = (git(self.repo, 'log', '--format=%h %s', '-20', f'{green}..{rev}' if green else rev) or '').splitlines()
        red_since = record.get('red_since') if record.get('failures') else rev
        finished(dict(state='red', rev=rev, green=green, failures=failures, commits=commits,
                                          red_since=red_since or rev, finished=time.time(),
                                          flaky=flaky, flaky_history=history, **child))
        LOG.say(f'Main is red at {rev[:7]}: {len(failures)} failing ({", ".join(failures[:3])}'
                + (f', +{len(failures) - 3} more' if len(failures) > 3 else '') + ')')
        self.maintain(main_only=True)  # one repair task, now: red main hides every later regression

    def validate_ledger(self, reason=''):
        """Read full validator errors, falling back to an engine refusal if needed."""
        if (Path(self.integ) / 'goals.json').exists():
            result = self.goals_cli('validate', self.integ)
            if result.returncode:
                errors = (result.stdout + result.stderr).strip().splitlines()
                if errors:
                    return sorted({' '.join(e.split()) for e in errors if e.strip()})
        if reason.startswith('invalid goals.json'):
            return sorted(set(reason.removeprefix('invalid goals.json').lstrip(': ').split('; ')))
        return []

    def overlap_idles(self):
        """Worker slots idle while a task waits for another one's file: the queue, not the pool,
        is what limits the runner, so the DOCS-MAINTAINER re-cuts those tasks."""
        rows = self.tasks()
        busy = sum(1 for r in rows if r.get('state') in ('dispatched', 'running'))
        return busy < int(self.workers) and any(maintainer.overlap(r) for r in rows)

    def maintain(self, main_only=False, ledger_errors=None, ledger_edits_only=False, overlap=False):
        """DOCS-MAINTAINER (TOOLSET-164-f1): when nothing runs and tasks are held for a planning
        cause or are not runnable as written, one Pi job restates them from the repository's own
        evidence in a disposable checkout. Its commit merges into the session only if it changed
        planning files alone and goals.py validate passes. Only unhandled trigger items enter
        the prompt; an unchanged unsuccessful repair needs an owner, not another run.
        True when its repair merged, or another ledger-proposal batch still waits."""
        if self.stop or not self.integ:
            return False
        self.ledger_errors = self.validate_ledger() if ledger_errors is None else ledger_errors
        # Like MAIN repair, LEDGER repair may coexist with task workers/reported slots:
        # those slots cannot settle until the ledger is valid. Never move the session
        # under an active review, a merge resolution (its merge is adopted only onto the
        # revision it merged) or another writer.
        # A re-cut of tasks waiting on a shared file writes planning files only: it runs beside
        # workers, which is when idle slots make it worth a model run.
        if (dirty(self.integ) or self.session_busy() or self.resolvers
                or (self.in_flight() and not main_only and not self.ledger_errors and not overlap)):
            return False
        rows = [] if main_only or self.ledger_errors else self.tasks()
        if ledger_edits_only:
            rows = [r for r in rows if r.get('state') in ('integrated', 'closing', 'closed')
                    and r.get('ledger_edit_dropped')]
        findings = {r['task']: worker.review_findings(self.state, r['task']) for r in rows
                    if r.get('state') == 'held' and r.get('cause') == 'validation' and r.get('task')}
        main = {} if ledger_edits_only else main_check.read(self.state)
        found = (maintainer.overlaps(rows) if overlap and not self.ledger_errors else
                 maintainer.triggers(rows, main, findings, ledger_errors=self.ledger_errors, limit=None,
                                     reported_flakes=maintainer.last(self.state).get('flaky_tests', [])))
        goals = dispatch = None
        closures = []
        if not main_only and not ledger_edits_only and not self.ledger_errors:
            goals, dispatch = touches_inference.modules(self.toolset)
            closures = maintainer.archive_closures(self.integ, dispatch.execution)
        found = closures + found
        before = {}
        if any(task not in ('MAIN', 'LEDGER') for task, _, _ in found):
            if goals is None:
                goals, dispatch = touches_inference.modules(self.toolset)
            before = maintainer.entries((Path(self.integ) / 'TODO.md').read_text(), goals)
        reasons = {r['task']: r.get('reason') or '' for r in rows if r.get('task')}
        found += maintainer.archive_rejections(self.state, closures, entries=before, reasons=reasons)
        history = maintainer.last(self.state)
        found = [item for item in found if not maintainer.own_main_refresh(
            self.repo, item, history.get('items', {}).get(maintainer.item_key(item), {}),
            main.get('rev'), history.get('main_edits', []))]
        found = maintainer.pending(self.state, found, entries=before, reasons=reasons)
        if not found:
            return False
        # Mechanical replay is its own model-free batch in the same transaction.
        # Failed replay receipts are filtered above, so other repairs still proceed.
        replay = [item for item in found if item[1] == 'archive close']
        found = replay or found
        trigger_key = maintainer.key(found)
        rolling = any(kind == 'plan' for _, kind, _ in found)
        plan_before = maintainer.plan_entries(self.integ, goals, dispatch.execution.archive_file(Path(self.integ))) \
            if rolling else before
        scratch = self.scratch_checkout('maintainer')
        if not scratch:
            return False
        names = [task for task, _, _ in found]
        LOG.say(f'{maintainer.ROLE}: repairing the task docs of {", ".join(names)}')
        outcome, changed = 'no change', []
        try:
            base = git(scratch, 'rev-parse', 'HEAD')
            if replay:
                ok, text = maintainer.replay_archive(scratch, names, dispatch.execution, self.goals_cli)
                if ok:
                    ok = git_ok(scratch, 'add', '-A') and git_ok(scratch, 'commit', '-qm',
                        'docs(tasks): replay archived completion of ' + ', '.join(names))
            else:
                message = maintainer.prompt(found, self.repo, self.goals)
                if rolling:
                    message += f'\nFinished batch reports: {Path(self.cfg["git_common"]) / "autowork-execution/slot-data"}.'
                ok, text = self.pi_job('maintainer', maintainer.ROLE, scratch,
                                       message,
                                       f'pi-autowork-maintainer-{datetime.now():%Y%m%d%H%M%S}', self.verify_timeout)
            head = git(scratch, 'rev-parse', 'HEAD')
            paths = (git(scratch, 'diff', '--name-only', base, head) or '').split() if head and head != base else []
            diff = git(scratch, 'diff', base, head) or '' if paths else ''
            changed = [task for task in names if task in diff]
            plan_error = None
            if rolling:
                try:
                    proposed = maintainer.plan_entries(scratch, goals, dispatch.execution.archive_file(Path(scratch)))
                    plan_error = maintainer.plan_error(found, plan_before, proposed, scratch,
                                                       dispatch.parallel_plan.dependency_ids)
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    plan_error = 'invalid planning documents: ' + str(exc)
                if not ok or git(scratch, 'rev-list', '--count', f'{base}..{head}') != '1':
                    plan_error = 'planning must finish successfully in one commit'
            if rolling and plan_error:
                outcome = 'planning failed: ' + plan_error
            elif replay and not ok:
                outcome = maintainer.REPLAY_REFUSED + text.strip()
            elif not paths:
                outcome = 'no change' if ok else 'failed'
            elif (not (maintainer.planning_only(paths) or (replay and all(
                    maintainer.planning_only([p]) or
                    p == dispatch.execution.archive_file(Path(scratch)).relative_to(scratch).as_posix()
                    for p in paths))) or dirty(scratch)):
                outcome = 'refused: it changed more than planning files'
            elif (self.ledger_errors or (Path(scratch) / 'goals.json').exists()) and (
                    validation := self.goals_cli('validate', scratch)).returncode:
                outcome = (maintainer.REPLAY_REFUSED + (validation.stdout + validation.stderr).strip()
                           if replay else 'refused: goals.py validate failed')
            elif git_ok(self.integ, 'merge', '-q', '--no-edit', head):
                outcome = 'merged'
                self.settled = self.land_soon = True
            else:
                git(self.integ, 'merge', '--abort')
                outcome = maintainer.RETRYABLE
        finally:
            self.drop_scratch(scratch)
        after = before
        if outcome == 'merged' and (before or replay):
            after = maintainer.entries((Path(self.integ) / 'TODO.md').read_text(), goals)
            changed = names if replay else [task for task in names if before.get(task) != after.get(task)
                       or (task in ('MAIN', 'LEDGER') and task in changed)]
            self.snapshot = None  # waiting reasons must be reread against the repaired entries
        maintainer.remember(self.state, trigger_key=trigger_key, found=found, outcome=outcome, changed=changed,
                            entries=after, before=before, reasons=reasons,
                            main_edit=(base, head) if outcome == 'merged' else ())
        LOG.say(f'{maintainer.ROLE}: {outcome}' + (f'; changed {", ".join(changed)}' if changed else ''))
        if self.ledger_errors:
            if outcome == 'merged':
                self.ledger_errors = []
                self.snapshot = None
            else:
                LOG.say('The engine needs attention: invalid goals.json: ' + '; '.join(self.ledger_errors)
                        + f'; {maintainer.ROLE} {outcome}; see BLOCKERS.md')
        proposals = [item for item in maintainer.triggers(rows, limit=None) if item[1] == 'ledger edit']
        return (outcome == 'merged' or (bool(replay) and outcome.startswith(maintainer.REPLAY_REFUSED))
                or bool(maintainer.pending(self.state, proposals, entries=after, reasons=reasons)))

    def environment_hold(self, task):
        """What a review of the held commit could not run without, or None (TOOLSET-173-94)."""
        try:
            return json.loads(worker.environment_marker(self.state, task).read_text()).get('missing') or None
        except (OSError, ValueError, AttributeError):
            return None

    def provision_and_reverify(self, task, version):
        """A review that could not run for a missing tool: one provisioning job installs it into
        the repository's toolchain cache from its own setup docs, then the same commit is
        reviewed once more. Once per task and reviewer version; True when it went back to review."""
        missing = self.environment_hold(task)
        # On disk, not in memory: every reload started the same job again, and a reload ended it.
        record = self.state / 'provisioned.json'
        try:
            done = json.loads(record.read_text())
        except (OSError, ValueError):
            done = {}
        if not missing or done.get(task) == version:
            return False
        done[task] = version
        record.write_text(json.dumps(done, indent=1))
        cache = worker.repository_cache(self.integ)
        scratch = self.scratch_checkout('provision') if cache else None
        if not scratch:
            return False
        LOG.say(f'{task}: its review could not run ({missing}); installing it into the toolchain cache')
        os.environ['AUTOWORK_CACHE'] = str(cache)
        try:
            ok, text = self.pi_job('provision', task, scratch, PROVISION_PROMPT.format(
                task=task, missing=missing, cache=cache, repo=self.repo),
                f'pi-autowork-provision-{safe_name(task)}-{datetime.now():%Y%m%d%H%M%S}', self.verify_timeout)
        finally:
            self.drop_scratch(scratch)
        done = ok and 'PI_AUTOWORK_RESULT: completed' in text
        if not done and missing.startswith('a full check that runs to its test results'):
            # Nothing to install for a crash, and the crash may have been the runner's own (its gate
            # once ran without $TMPDIR): review it again on this release instead of waiting for a person.
            if self.engine('--parallel-reverify', task, '--reviewer-version', version + '-env').get('outcome') == 'REVERIFY':
                self.seen[task] = ''
                self.settled = True
                LOG.say(f'{task}: its check crashed and nothing needed installing; verifying it again on this release')
                return True
        if not done:
            LOG.say(f'{task}: could not install what its review needs ({missing}); it waits for a person')
            return False
        note = ' '.join(text.split('PI_AUTOWORK_RESULT: completed', 1)[1].split())[:600]
        with open(cache / 'PROVISIONED.md', 'a') as record:
            record.write(f'- {datetime.now():%Y-%m-%d %H:%M} for {task} ({missing}): {note}\n')
        if self.engine('--parallel-reverify', task, '--reviewer-version', version + '-env').get('outcome') == 'REVERIFY':
            self.seen[task] = ''
            self.settled = True
            LOG.say(f'{task}: installed what its review needed; verifying it again')
            return True
        return False

    def triage_blocker(self, row):
        """A worker-reported blocker is answered by the runner and the attempt resumes, unless only a
        person can resolve it: most blockers asked for what the runner already provides, or for a repair
        the worker may make itself, and waited hours for the owner. Once per task and reason."""
        task, root, reason = row.get('task'), row.get('worktree'), ' '.join(str(row.get('reason') or '').split())
        if (self.stop or row.get('waits_for') or row.get('quick_hold') or row.get('worker_live')
                or int(row.get('answered') or 0) >= 2 or not root or not Path(root).is_dir()):
            return False
        record = self.state / 'triage.json'
        try:
            done = json.loads(record.read_text())
        except (OSError, ValueError):
            done = {}
        key = hashlib.sha256(reason.encode()).hexdigest()[:16]
        if done.get(task) == key:
            return False
        before = (git(root, 'rev-parse', 'HEAD'), git(root, 'status', '--porcelain', '--untracked-files=all'))
        report = Path(self.cfg['git_common']) / 'autowork-execution' / 'slot-data' / task
        report = max(report.glob('attempt-*/report.json'), default=report / 'attempt-1' / 'report.json',
                     key=lambda p: int(p.parent.name.split('-')[1]))
        LOG.say(f'{task}: triaging its blocker: can the runner answer it?')
        _, text = self.pi_job('triage', task, root, TRIAGE_PROMPT.format(repo=self.repo, task=task, report=report,
                                                                          root=root),
                              f'pi-autowork-triage-{task}-{datetime.now():%Y%m%d%H%M%S}', 900)
        done[task] = key
        record.write_text(json.dumps(done, indent=1))
        verdict = triage_verdict(text)
        if (git(root, 'rev-parse', 'HEAD'), git(root, 'status', '--porcelain', '--untracked-files=all')) != before:
            LOG.say(f'{task}: its blocker triage changed the worktree; the blocker stays a question')
            return False
        if verdict is None or verdict[0] == 'owner':
            LOG.say(f'{task}: its blocker needs the owner' + (f': {fleet_view.short(verdict[1], 200)}' if verdict else ''))
            return False
        answer = self.state / 'runs' / f'answer-{task}.txt'
        answer.write_text(verdict[1] + '\n')
        result = self.engine('--parallel-answer', task, '--answer-file', str(answer))
        answer.unlink(missing_ok=True)
        if result.get('outcome') != 'ANSWERED':
            LOG.say(f'{task}: could not answer its blocker: {result.get("reason") or result.get("outcome")}')
            return False
        LOG.say(f'{task}: the runner answered its blocker; resuming its attempt ({fleet_view.short(verdict[1], 160)})')
        return True

    def resolve_task_conflict(self, row):
        """A commit held for a merge conflict with the session is merged with it in its own
        worktree, Pi resolving the conflict beside the loop, and the engine judges the merge from
        there (TOOLSET-157-cd): once per session revision, instead of reimplementing the task.
        Up to PI_AUTOWORK_RESOLVERS (3) run at once; one at a time inside the loop, nine held
        conflicts took about twenty minutes each while nothing else moved."""
        task, root = row.get('task'), row.get('worktree')
        if self.stop or row.get('worker_live') or not root or not Path(root).is_dir() or task in self.resolvers:
            return False
        if self.reexec_due():
            # The reload waits for running resolvers and a due reload starts no batch: new ones
            # each kept it pending, so for hours nothing landed while conflicts were resolved.
            return False
        adoption = row.get('merge_adoption') or {}
        if not adoption.get('allowed'):
            reason = adoption.get('reason') or 'the engine did not authorize merge adoption'
            if self.seen.get('merge-refused-' + task) != reason:
                LOG.say(f'{task}: not running the merge resolver: {reason}; it waits for the owner')
                self.seen['merge-refused-' + task] = reason
            return False
        head = git(self.integ, 'rev-parse', 'HEAD')
        if not head or adoption.get('baseline') != head or self.seen.get('resolved-' + task) == head:
            return False
        commit = git(root, 'rev-parse', 'HEAD')
        if self.seen.get('unresolved-' + task) == commit:
            return False  # the session moved beside its failed resolution; the owner answers it first
        if len(self.resolvers) >= max(1, worker.setting('PI_AUTOWORK_RESOLVERS', 3)) or not self.ready_to_merge(task, root):
            return False
        self.seen['resolved-' + task] = head
        if git_ok(root, 'merge', '-q', '--no-edit', head):
            return self.adopt_merge(task)
        files = ' '.join((git(root, 'diff', '--name-only', '--diff-filter=U') or '').split())
        LOG.say(f'{task}: its commit conflicts with the session in: {files}; asking Pi to resolve the merge '
                'in its worktree')
        branch = git(root, 'symbolic-ref', '--short', '-q', 'HEAD') or task
        out = tempfile.NamedTemporaryFile(dir=self.state / 'runs', prefix='merge.', delete=False)
        out.close()
        env = self.job_environment(PI_AUTOWORK_SESSION=self.integ_branch or os.environ.get('PI_AUTOWORK_SESSION', ''))
        with open(out.name, 'w') as stream:
            proc = subprocess.Popen([sys.executable, str(Path(__file__).with_name('pi_runtime.py')), 'job',
                                     str(self.state), 'merge', task, str(root),
                                     f'pi-autowork-merge-{task}-{datetime.now():%Y%m%d%H%M%S}', str(self.verify_timeout),
                                     MERGE_PROMPT.format(branch=branch, base=head[:12], files=files, goals=self.goals,
                                                         repo=self.repo)], stdout=stream, env=env)
        self.resolvers[task] = {'proc': proc, 'out': out.name, 'root': root, 'head': head, 'commit': commit,
                                'merged_count': adoption.get('merged_count')}
        self.note_resolvers()
        return False

    def ready_to_merge(self, task, root):
        """A worktree the resolver can merge in. A resolution stopped by a restart left its merge
        unfinished, and a worker can leave files uncommitted beside its commit: either kept the
        resolver away without a word. The merge starts again; the files go to a named stash."""
        marker = git(root, 'rev-parse', '--path-format=absolute', '--git-path', 'MERGE_HEAD')
        if marker and Path(marker).exists():
            git(root, 'merge', '--abort')
            LOG.say(f'{task}: its worktree held an unfinished merge resolution; starting it again')
        if dirty(root):
            if not git_ok(root, 'stash', 'push', '--include-untracked', '-m',
                          f'autowork: {task} left uncommitted before its merge resolution'):
                if self.seen.get('unstashed-' + task) != root:
                    LOG.say(f'{task}: its worktree has uncommitted files that could not be stashed; it waits for the owner')
                    self.seen['unstashed-' + task] = root
                return False
            LOG.say(f'{task}: its uncommitted files were stashed (git stash list in {root}) so its merge can be resolved')
        return not dirty(root)

    def finish_resolvers(self):
        """Judge each merge resolution that ended: adopt its merge, or abort it."""
        for task, job in list(self.resolvers.items()):
            if job['proc'].poll() is None:
                continue
            del self.resolvers[task]
            try:
                result = json.loads(Path(job['out']).read_text()) if job['proc'].returncode == 0 else {}
            except (OSError, ValueError):
                result = {}
            Path(job['out']).unlink(missing_ok=True)
            for note in result.get('notes') or []:
                LOG.say(note)
            root, head = job['root'], job['head']
            marker = git(root, 'rev-parse', '--path-format=absolute', '--git-path', 'MERGE_HEAD')
            if (marker and Path(marker).exists()) or dirty(root) or not git_ok(root, 'merge-base', '--is-ancestor',
                                                                              head, 'HEAD'):
                git(root, 'merge', '--abort')
                next_step = 'it waits for the owner' if job['merged_count'] else 'it is retried fresh instead'
                LOG.say(f'{task}: the merge could not be resolved; {next_step}')
                if job['merged_count']:
                    self.seen['unresolved-' + task] = job['commit']
                continue
            # The session often moves while Pi resolves (its own questions commit): merge that
            # too, or the engine refuses the resolution and the next pass merges it anyway.
            now = git(self.integ, 'rev-parse', 'HEAD')
            if now and now != head and not git_ok(root, 'merge', '-q', '--no-edit', now):
                git(root, 'merge', '--abort')
                continue  # the next pass resolves the resolution against the new session
            self.settled = self.adopt_merge(task) or self.settled
        self.note_resolvers()

    def note_resolvers(self):
        """The fleet reads job.json to say what the runner is doing beside its loop."""
        if self.resolvers:
            health.job_started(self.state, 'merge', ', '.join(sorted(self.resolvers)))
        elif not self.child:
            health.job_finished(self.state)

    def adopt_merge(self, task):
        result = self.engine('--parallel-merged', task)
        if result.get('outcome') != 'MERGED':
            LOG.say(f'{task}: could not adopt its merged commit: {result.get("reason") or result.get("outcome")}')
            return False
        count = result.get('merged_count', 1)
        again = f' again ({count} of 3)' if count > 1 else ''
        LOG.say(f'{task}: merged the session into its commit{again}; verifying again')
        return True

    # --- Touches proposals ------------------------------------------------------------
    def scratch_checkout(self, purpose, rev='HEAD'):
        """A disposable detached checkout inside the canonical .worktrees directory."""
        target = workspaces.task_path(self.toolset, self.repo, 'pi-scratch-' + purpose)
        target.parent.mkdir(exist_ok=True)
        path = tempfile.mkdtemp(prefix=target.name + '-', dir=target.parent)
        os.rmdir(path)
        with open(self.state / 'engine.err', 'a') as err:
            ok = subprocess.run(['git', '-C', self.integ or self.repo, 'worktree', 'add', '-q', '--detach', path, rev],
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
            if result.get('outcome') == 'BUSY':
                continue  # a review holds the integration lock: keep the request for a later cycle
            request.unlink(missing_ok=True)
            if result.get('outcome') == 'SET_ASIDE':
                self.seen[task] = 'pending'
                self.settled = True
                kept = ', '.join(r['branch_now'] for r in result.get('renamed') or [] if r.get('branch_now'))
                LOG.say(f'{task}: set aside on request; its earlier work is kept as {kept}; the task will run fresh')
            else:
                LOG.say(f'{task}: could not set aside: {result.get("reason") or result.get("outcome")}')
        # `--clear-held TASK` requests: return a held commit to integration as technical
        # recovery. The commit and worktrees are kept; no person has to decide anything.
        for request in sorted((self.state / 'requests').glob('clear-held-*')):
            task = request.name.removeprefix('clear-held-')
            if task in self.resolvers:
                continue  # cleared now, its resolved merge could not be adopted: keep the request
            result = self.engine('--parallel-clear-held', task)
            if 'live parallel coordinator owner' in json.dumps(result):
                continue  # before this runner's first dispatch it holds no lease: keep it
            if result.get('outcome') == 'BUSY':
                continue  # a review holds the integration lock: keep the request for a later cycle
            request.unlink(missing_ok=True)
            if result.get('outcome') == 'CLEARED':
                for name in result.get('tasks') or []:
                    self.seen[name] = 'pending'
                self.settled = True
                LOG.say(f'{task}: cleared its hold for technical recovery; its commit goes back to integration')
            else:
                LOG.say(f'{task}: could not clear its hold: {result.get("reason") or result.get("outcome")}')

    def health_update(self, snapshot=None):
        snapshot = self.status() if snapshot is None else snapshot
        paused = int(time.time() + self.pause_until - time.monotonic()) if self.pause_until > time.monotonic() else 0
        # Commits that only wait for another session to leave the main checkout are no progress.
        reported = [t for t in self.tasks(snapshot) if t.get('state') in ('reported', 'integrating')]
        waiting = [t for t in reported if self.seen.get('busy-' + str(t.get('task')))]
        blocker = self.runner_blocker or self.merge_blocker
        if waiting and not blocker:
            candidate = waiting[0].get('task')
            meanwhile = len(reported) - len(waiting)
            blocker = (f'{candidate} waits for another session in the main checkout'
                       + (f'; {meanwhile} other reported commit(s) integrate meanwhile' if meanwhile else '')
                       + ': ' + self.seen['busy-' + str(candidate)])
        runner = {'repo': str(self.repo), 'pid': str(os.getpid()), 'toolset_rev': self.toolset_rev,
                  'mode': self.mode, 'paused_until': str(paused), 'blocker': blocker,
                  'stuck_integrations': str(len(waiting)), 'maintainer': maintainer.last(self.state),
                  'main_check': {k: v for k, v in main_check.read(self.state).items() if k not in ('pid', 'path', 'tmp')}}
        try:
            line = health.update(self.state, snapshot, runner=runner, stall_after=int(self.stall_after))
        except (OSError, ValueError):
            return
        if line:
            LOG.warn(line)
        if not self.runner_blocker.startswith('planning files are not committed on '):
            ledger_key = maintainer.key(maintainer.triggers([], ledger_errors=self.ledger_errors))
            attempted = ledger_key in maintainer.last(self.state).get('ledger_attempts', {})
            self.update_questions(dict(snapshot, ledger_errors=self.ledger_errors if attempted else []))

    def update_questions(self, snapshot):
        """Keep the owner's questions in BLOCKERS.md (TOOLSET-120-fc 2): built without a model,
        written only when they change, committed alone on the session branch."""
        if (not self.integ or (snapshot.get('outcome') != 'PARALLEL_STATUS' and not snapshot.get('ledger_errors'))
                or dirty(self.integ) or self.session_busy()):
            return
        goals, _ = touches_inference.modules(self.toolset)
        path = Path(self.integ) / 'BLOCKERS.md'
        try:
            old = path.read_text() if path.exists() else None
            todo = (Path(self.integ) / 'TODO.md').read_text()
            rows = self.tasks(snapshot)
            findings = {r['task']: worker.review_findings(self.state, r['task']) for r in rows
                        if r.get('state') == 'held' and r.get('cause') == 'validation' and r.get('task')}
            triggers = maintainer.triggers(rows, findings=findings, limit=None)
            reasons = {r['task']: r.get('reason') or '' for r in rows if r.get('task')}
            repairs = maintainer.stalled(self.state, triggers, entries=maintainer.entries(todo, goals), reasons=reasons)
            found = questions.build(snapshot, todo, goals, repairs=repairs, resolving=self.resolving(rows))
            if os.environ.get('PI_AUTOWORK_ASK_FULL_CHECK', '1') != '0' and not main_check.full_check(self.integ):
                # TOOLSET-180-72: nothing guards the suite
                found.append(questions.full_check_question())
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

    def resolving(self, rows):
        """Held conflicts the merge resolver is settling or will take next: not the owner's yet. One
        is asked once its resolution failed or its merges ran out (merge_adoption not allowed)."""
        return set(self.resolvers) | {
            r['task'] for r in rows if r.get('state') == 'held' and r.get('cause') == 'conflict'
            and (r.get('merge_adoption') or {}).get('allowed')
            and self.seen.get('unresolved-' + r['task']) != r.get('commit')}

    def update_toolset(self):
        """While nothing is in flight, update the toolset package Pi loads, at most once per
        interval and one runner at a time, and only to a release that reads this state."""
        if self.mode != 'continuous' or self.update_interval == 0:
            return
        if time.monotonic() - self.last_update < self.update_interval:
            return
        self.last_update = time.monotonic()
        if os.environ.get('PI_AUTOWORK_PACKAGE_INSTALLED') != '1':
            return  # a checkout is updated by its owner, not by the runner
        source = git(self.package, 'remote', 'get-url', 'origin')
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
            check = release.check(self.cfg['state_root'], self.state, self.package, wait=self.update_wait,
                                  current_toolset=self.toolset)
            if not check['ok']:
                # Another runner's work in flight, or a release that cannot read this state.
                note = check['reason'].split(';')[0]
                if not check.get('current') and note != self.last_update_note:
                    LOG.say(f'Toolset update deferred: {check["reason"]}')
                self.last_update_note = note
                if not check.get('current'):  # a release is waiting: look again within minutes
                    self.last_update -= max(0, self.update_interval - min(300, self.update_interval))
                return
            self.last_update_note = ''
            if check.get('note'):
                LOG.say(f'Toolset update: {check["note"]}')
            with open(self.state / 'engine.err', 'a') as err:
                rc = subprocess.run(['timeout', '300', self.cfg['pi'], 'update', source], stdout=err,
                                    stderr=err).returncode
            if rc:
                LOG.say(f'Toolset update failed (see {self.state / "engine.err"}); keeping {self.toolset_rev}')

    def reexec_due(self):
        """'reload' or 'update' when the runner should re-execute at its next safe point: an
        asked-for reload, or a package that moved past the release this process runs."""
        if self.reload:
            return 'reload'
        if self.mode == 'continuous' and self.toolset_rev != 'unknown' and self.package:
            rev = git(self.package, 'rev-parse', '--short', 'HEAD')
            if rev and rev != self.package_rev:
                return 'update'
        return ''

    def restart_if_updated(self):
        """Only a re-exec selects the package's next immutable release.

        Existing engine/review/worker processes keep their inherited release.
        """
        if self.reload:
            return self.reexec('Reloading: settings and release re-read; running workers keep running',
                               reload=True)
        if self.mode != 'continuous' or self.toolset_rev == 'unknown':
            return
        rev = git(self.package, 'rev-parse', '--short', 'HEAD')
        if not rev or rev == self.package_rev:
            return
        try:
            candidate = release.prepare(self.cfg['state_root'], self.package)
            rev = git(candidate, 'rev-parse', '--short', 'HEAD')
            shell = subprocess.run(['bash', '-n', str(candidate / 'scripts/pi-autowork.sh')], capture_output=True)
            for path in (candidate / 'pi-autowork/pi_autowork').glob('*.py'):
                compile(path.read_bytes(), str(path), 'exec')
            if shell.returncode == 0:
                return self.reexec(f'Toolset updated to {rev}; restarting on it', revision=candidate.name)
        except (OSError, RuntimeError, SyntaxError, subprocess.SubprocessError) as exc:
            LOG.say(f'Cannot prepare toolset {rev}: {exc}')
        LOG.say(f'Toolset changed to {rev}, but its runner does not parse; keeping the running {self.toolset_rev}')
        self.package_rev = rev

    def reexec(self, text, reload=False, revision='HEAD'):
        """Run this runner again in place: same PID, so running workers stay its children and
        are adopted. Not while a review or a Pi job runs, nor once a review has ended but its
        answer is not read yet (TOOLSET-187-1d: a reload deferred behind a review re-executed the
        moment it ended and lost it): the cycle reads it, and a later cycle re-executes."""
        landing = [] if self.integration or self.child or self.resolvers else self.batch_landing()
        if self.integration or self.child or self.resolvers or landing:
            what = (f"the review of {self.integration['task']}" if self.integration else
                    f"the merge resolution of {', '.join(sorted(self.resolvers))}" if self.resolvers else
                    'a Pi job' if self.child else '')
            what = f'{what} to end' if what else f"{', '.join(landing)} to land (passed in a batch)"
            if self.seen.get('reexec-pending') != what:
                self.seen['reexec-pending'] = what
                LOG.say(f'Reload pending: waiting for {what}')
            return
        package = self.package
        if reload:
            reread_settings(self.settings_file, self.started_with)
            configured = os.environ.get('PI_AUTOWORK_TOOLSET')
            if configured and configured != self.toolset:
                package = configured
            elif not configured and 'PI_AUTOWORK_TOOLSET' in self.started_with:
                package = ''  # removing a checkout override restores automatic discovery
            os.environ['PI_AUTOWORK_RELOADS'] = str(int(os.environ.get('PI_AUTOWORK_RELOADS') or 0) + 1)
        # Keep the old pin through Bash/bootstrap startup; only the bootstrap's
        # locked exec publishes the new pin. Other runners may prune meanwhile.
        os.environ.update(PI_AUTOWORK_TOOLSET=self.toolset, PI_AUTOWORK_PACKAGE=package,
                          PI_AUTOWORK_RESELECT='1' if package else 'auto', PI_AUTOWORK_NEXT_REVISION=revision)
        os.environ.pop('PI_AUTOWORK_COMPONENT', None)
        LOG.say(text)
        (self.state / 'runner.json').unlink(missing_ok=True)
        sys.stdout.flush()
        # Ignored, not handled: exec keeps an ignored signal, so a reload sent while the new
        # process starts cannot end it (systemd does not restart a unit SIGHUP ended).
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        os.execv('/bin/bash', ['/bin/bash', self.process_script, *self.cfg['argv']])

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
            self.engine('--parallel', str(self.workers), '--max-workers', '16', '--wait', '--timeout', '5')
        self.settle()
        self.finish(130, 'Stopped. Unfinished tasks keep their worktrees and resume on the next start.')

    def blocked_pause(self, blocker):
        self.runner_blocker = blocker
        self.health_update()
        self.pause(self.interval)

    def planning_ready(self):
        """A session sees the committed base, not the owner's untracked planning files."""
        # The direct CLI also supports TODO-only repositories (unlike service readiness).
        # Once an index exists on disk it too must reach the committed base before dispatch.
        required = ('TODO.md', 'goals.json') if (Path(self.repo) / 'goals.json').exists() else ('TODO.md',)
        missing = fleet_view.uncommitted_planning(self.repo, self.base, required)
        path = Path(self.repo) / 'BLOCKERS.md'
        old = path.read_text() if path.exists() else None
        new = questions.update_planning(old, self.base if missing else None)
        receipt = self.state / 'planning-question.json'
        try:
            previous = json.loads(receipt.read_text())
        except (OSError, ValueError):
            previous = None
        if missing and previous and old == previous.get('before'):
            # The receipt may have reached disk just before a crash prevented the question
            # write. Reuse its exact text (including Since), so later restoration matches.
            new = previous['written']
        if missing and new != old and previous is None:
            # On recovery restore exactly what preceded our question, even across a restart.
            # Empty markers left behind here would block the session's next BLOCKERS.md merge.
            receipt.write_text(json.dumps({'before': old, 'written': new}) + '\n')
        elif not missing:
            committed = git(self.repo, 'show', f'{self.base}:BLOCKERS.md') or ''
            if 'RUNNER-PLANNING' in questions.previous_since(committed):
                # The owner may have committed our question along with the plan. Let the
                # session remove it through the usual questions commit, not a dirty main edit.
                new = old
            elif previous and old == previous.get('written'):
                new = previous['before']
        if new != old:
            if new is None:
                path.unlink(missing_ok=True)
            else:
                path.write_text(new)  # never commit the owner's files to bootstrap a runner
        if not missing:
            # A crash before restoration must leave the receipt for the next start.
            receipt.unlink(missing_ok=True)
            if self.runner_blocker.startswith('planning files are not committed on '):
                self.runner_blocker = ''
                self.last_waiting = ''
            return True
        blocker = f'planning files are not committed on {self.base}'
        if self.mode != 'continuous':
            raise Finish(4, f'{blocker}; commit TODO.md and goals.json on {self.base} first')
        if self.last_waiting != 'planning:' + blocker:
            LOG.say(f'Runner blocked: {blocker}; commit TODO.md and goals.json on {self.base} first')
        self.last_waiting = 'planning:' + blocker
        self.runner_blocker = blocker
        snapshot = self.status(directory=self.repo)
        if snapshot.get('outcome') != 'PARALLEL_STATUS':
            snapshot = {'outcome': 'PARALLEL_STATUS', 'tasks': [], 'roots': []}
        self.health_update(snapshot)
        self.pause(self.interval)
        return False

    def cycle(self):
        self.plan_seen = self.plan_signature()
        if self.stop:
            self.stop_now()
        if not self.draining and not self.in_flight():
            self.update_toolset()
        self.restart_if_updated()
        if not self.planning_ready():
            return
        self.ensure_session()
        if not self.seen.get('synced-at-start'):
            self.seen['synced-at-start'] = True
            self.sync_upstream()  # publish a backlog left by a run that could not push
        self.follow_base()
        self.sweep_tmp()
        self.check_main()
        self.land_planning()
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
        # Draining excludes fresh work, not a paused attempt's existing unfinished work.
        resumes = [r['task'] for r in self.tasks() if self.draining and r.get('state') == 'interrupted'
                   and r.get('paused') and (not self.once_task or r['task'] == self.once_task)]
        if not self.draining or resumes:
            chosen, reason = self.choose_model()
            if not chosen:
                reason = reason or 'primary and fallback not ready'
                if self.mode in ('once', 'until-empty'):
                    self.finish(1, f'No usable model: {reason}')
                LOG.say(f'No usable model ({reason}); checking again in {self.interval}s')
                return self.blocked_pause(f'no usable model: {reason}')
        self.runner_blocker = ''
        result = {}
        if (not self.draining or resumes) and time.monotonic() < self.pause_until:
            outcome = 'PAUSED'  # after a failure streak: settle running work, start nothing new
        elif not self.draining or resumes:
            # Workers leave the full check to the gate the runner runs on the merged tree (TOOLSET-227-a8).
            os.environ['AUTOWORK_RUNNER_FULL_CHECK'] = main_check.full_check(self.integ) if self.integ else ''
            result = self.engine('--apply', '--parallel', str(self.workers), '--max-workers', '16',
                                 '--worker-command', self.worker_command, '--worker-timeout', self.task_timeout,
                                 '--min-free-mem-mb', self.min_free_mb, '--adopt-idle-claims', str(self.claim_idle),
                                 '--base-ref', self.base, *(['--tasks', ','.join(resumes)] if resumes else []))
            outcome = result.get('outcome') or 'ACTION_REQUIRED'
            for task in result.get('closed_on_base') or []:
                self.note_state(task, 'closed', f'closed on {self.base}; its worker is stopped and its work set aside')
            for task in result.get('closing') or []:
                self.note_state(task, 'closing', f'closed on {self.base}; set aside once the running review ends')
            if outcome != 'ACTION_REQUIRED':
                self.ledger_errors = []  # an owner repair must also retire its question
        else:
            # --once/budget draining starts no new task, but a broken ledger also
            # prevents the already dispatched tasks from integrating or closing.
            self.ledger_errors = self.validate_ledger()
            outcome = 'ACTION_REQUIRED' if self.ledger_errors else 'DRAINING'
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
            elif result.get('why') == 'review_rework':
                LOG.say(f'{task}: its last attempt failed review; reworking it once with the findings'
                        + (f' (earlier work kept as {kept})' if kept else ''))
            elif result.get('why') == 'runner_merged':
                LOG.say(f'{task}: its branch was merged past its commit by the runner; running it fresh from that tip'
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
            if self.overlap_idles() and self.maintain(overlap=True):
                self.last_waiting = ''
                return  # dispatch again on the re-cut tasks first
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
            if self.maintain():  # also check a ledger the engine did not flag
                self.last_waiting = ''
                return  # dispatch again on the repaired docs first
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
            # Shape/parse failures have no `invalid goals.json` prefix. Consult the
            # validator on every refusal rather than guessing the engine's wording.
            self.ledger_errors = self.validate_ledger(reason) if outcome == 'ACTION_REQUIRED' else []
            if self.ledger_errors:
                if self.maintain(ledger_errors=self.ledger_errors):
                    return  # select again on valid docs before asking the owner
                if self.integration:
                    self.settle()  # reap an existing review so it cannot hold repair forever
                reason = 'invalid goals.json: ' + '; '.join(self.ledger_errors)
                self.last_waiting = 'engine:' + reason
                if self.mode != 'continuous':
                    self.runner_blocker = f'the engine needs attention: {reason}'
                    self.health_update()
                    self.finish(4, 'Ledger repair pending; see BLOCKERS.md')
                return self.blocked_pause(f'the engine needs attention: {reason}')
            if self.mode != 'continuous':
                self.finish(4, f'The engine needs attention: {reason}')
            if self.integration:
                # Read an ended review's answer: a reload onto a release that fixes the engine waits
                # for it, and it was never read while the engine failed (a deadlock until a restart).
                self.settle()
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
            self.engine('--parallel', str(self.workers), '--max-workers', '16', '--wait', '--timeout', '5')
            return
        if self.draining and any(r.get('state') == 'interrupted' and r.get('paused')
                                 and (not self.once_task or r['task'] == self.once_task) for r in self.tasks()):
            if outcome in ('WAITING', 'PAUSED'):
                self.pause(self.interval)  # do not spin on a resource-gated same-attempt resume
            return  # dispatch only these same-attempt resumes on the next cycle, even in --once
        if outcome in ('WAITING', 'BLOCKED', 'PAUSED'):
            # Tasks remain, but none can start now (held work, dependencies or the resource gate).
            if self.mode != 'continuous':
                self.finish(1, f'No runnable task can start: {self.last_waiting or "see --status"}')
            self.merge_waiting()
            return self.pause(self.interval)
        # --once/budget draining never reach IDLE's maintainer pass. Finish their
        # proposal batches (including discarded ones) without dispatching new work.
        if self.draining and self.maintain(ledger_edits_only=True):
            return
        # Nothing running, nothing to integrate and nothing waiting: finite runs end here.
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
                self.engine('--parallel', str(self.workers), '--max-workers', '16', '--release')
                # Keep the worktree and branch: follow_base() takes main's next plan in
                # place. Release the lease nevertheless, so interactive engine users can
                # work between intervals. Only a day-old, fully landed session rotates.
                if self.integ and self.session_expired() and self.ahead() == 0:
                    self.end_session()
            LOG.say(f'Queue empty; checking again in {self.interval}s')
            self.pause(self.interval)

    def run(self):
        signal.signal(signal.SIGINT, self.on_signal)
        signal.signal(signal.SIGTERM, self.on_signal)
        signal.signal(signal.SIGHUP, self.on_reload)
        LOG.say(f'Started (PID {os.getpid()}). Stop with Ctrl+C.')
        try:
            self.register_planning_merges()
            while True:
                self.cycle()
        except Finish as done:
            LOG.say(done.text)
            return done.code
        finally:
            (self.state / 'runner.json').unlink(missing_ok=True)
