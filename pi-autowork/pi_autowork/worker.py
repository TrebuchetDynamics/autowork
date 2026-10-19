"""The engine-launched modes of pi-autowork.

    --worker STATE WORKTREE PROMPT REPORT TIMEOUT   one Pi worker for one engine slot
    --verify STATE TASK                             the engine's validation command for a merge

The engine starts each in its own process group; a stop sent to the group reaches
Pi too. Exit 0 means a finished worker with a report, or a passing review.
"""
from datetime import datetime
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

from . import main_check, pi_runtime, workspaces
from .common import dirty, git, push_guard, safe_name

REVIEW = ('You are an independent reviewer verifying task {task} in {checkout}, which holds a worker\'s commit '
          'merged onto the session branch (see git log -1 and git diff HEAD^1 HEAD). Read the task\'s entry in '
          'TODO.md (its Acceptance and Checks), run the offline checks it lists, and judge the merged change '
          'against the acceptance criteria. Do not ask for more tests than the acceptance and Checks need; fail a '
          'change whose new tests mostly repeat existing cases or add many near-identical tests where one table '
          'would do. Do not edit, create or delete files, commit, push or change branches; '
          'build output in gitignored paths is fine. Put every temporary file and copy under $TMPDIR, '
          'never directly under /tmp, which is RAM on this host; $TMPDIR is removed after the review. '
          'For a scratch copy of the checkout use git worktree add --detach "$TMPDIR/copy" HEAD, not a '
          'file copy. If a check the task requires cannot run because a tool, SDK or service is missing '
          'here, not because the change is wrong, end instead with: PI_AUTOWORK_VERIFY: fail environment — '
          '<what is missing, and the setup doc that names it>. Otherwise end with exactly one line: '
          'PI_AUTOWORK_VERIFY: pass or '
          'PI_AUTOWORK_VERIFY: fail, then the reason.')
# The runner's full check on the merged tree is the one trusted full run (TOOLSET-227-a8).
GATE = (' The runner already ran the repository\'s full check (`{command}`) on this merged tree: {outcome}. '
        'Its log is {log}. Do not run the full check again; read that log, and rerun only individual tests you '
        'need to examine. A Checks entry naming the full check is satisfied by that run.')
# Offline completion is separate from live qualification (AGENTS.md): checks recorded as
# pending live become their own TASK-LIVE follow-up, so they must not fail the review.
LIVE = (' Checks that need a physical device, hardware, production or live services, or a person cannot run '
        'here. The worker recorded these as pending live checks, which become a separate live follow-up task: '
        '{items}. Do not fail for those; judge everything that can be checked offline. A live check the task '
        'requires that is not in that list is a failure: it would be lost.')
NO_LIVE = (' The worker recorded no pending live checks: a device, hardware, production or human check the '
           'task requires and that cannot run here is a failure, because nothing would record it.')


def link_ignored(checkout):
    """Gitignored dependencies the service names are linked from the canonical checkout first."""
    paths, repo = os.environ.get('PI_AUTOWORK_LINK_PATHS'), os.environ.get('PI_AUTOWORK_REPO')
    if paths and repo:
        for path, outcome in workspaces.link_ignored(repo, checkout, paths):
            print(f'pi-autowork: linked path {path}: {outcome}', file=sys.stderr)


def worker(state, worktree, prompt_file, report, limit):
    link_ignored(worktree)
    prompt = Path(prompt_file).read_text()
    task = (re.search(r'^Task: (.*)$', prompt, re.M) or [None, ''])[1]
    attempt = Path(report).parent.name
    session = f'pi-autowork-{safe_name(task)}-{attempt}'
    # The engine captures unfinished tool calls before stopping a timed-out worker.
    Path(report).with_name('session.json').write_text(json.dumps({
        'directory': str(Path(state).resolve() / 'sessions'), 'id': session}))
    result = pi_runtime.job(pi_runtime.Settings(state), 'worker', task, worktree,
                            f'Follow the instructions in this file exactly: @{prompt_file}',
                            session, limit, [f'@{prompt_file}'])
    return 0 if result['ok'] and Path(report).is_file() else 1


def pending_live(checkout, task):
    """The pending live checks the worker's report recorded, from the engine's slot data."""
    common = git(checkout, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    if not common:
        return []
    execution = Path(common) / 'autowork-execution'
    try:
        slot = json.loads((execution / 'slots' / f'{task}.json').read_text())
        attempt = slot.get('data_attempt', slot['attempt'])
        report = json.loads((execution / 'slot-data' / task / f'attempt-{attempt}' / 'report.json').read_text())
    except (OSError, ValueError, KeyError, TypeError):
        return []
    items = report.get('pending_live') if isinstance(report, dict) else None
    items = items if isinstance(items, list) else [items] if items else []
    texts = [' — '.join(str(i[k]) for k in ('check', 'command', 'summary', 'description', 'reason') if i.get(k))
             if isinstance(i, dict) else str(i) if i is not None else '' for i in items]
    return [' '.join(t.split()) for t in texts if t.strip()]  # the engine's live_items, which the close uses


PROVISIONED = (' Toolchains, SDKs and caches the worker provisioned for this task (its $TMPDIR) are in {path}, '
               'also exported as AUTOWORK_WORKER_TMPDIR. Use them read-only, for example an SDK the task\'s docs place '
               'under $TMPDIR, instead of downloading again; do not write there.')


CACHE = (' SDKs, toolchains and package caches this repository\'s tasks installed are in {path} '
         '(AUTOWORK_CACHE; PROVISIONED.md there says how to use what the runner installed): use them instead '
         'of downloading again, and add one there only if a check needs it.')
ENVIRONMENT = re.compile(r'^PI_AUTOWORK_VERIFY: fail environment\s*[—:-]+\s*(.*)$')


def findings_path(state, task):
    """A failed review's verdict, for the DOCS-MAINTAINER to split or restate the task by."""
    return Path(state) / 'review-findings' / f'{safe_name(task)}.json'


def review_findings(state, task):
    try:
        return json.loads(findings_path(state, task).read_text()).get('verdict') or ''
    except (OSError, ValueError, AttributeError):
        return ''


def environment_marker(state, task):
    """Where a review that could not run for a missing tool records what was missing
    (TOOLSET-173-94); the coordinator provisions it and reviews once more."""
    return Path(state) / 'review-env' / f'{safe_name(task)}.json'


def repository_cache(checkout):
    """The repository's shared toolchain cache (TOOLSET-169-1d), created if missing."""
    try:
        common = Path(git(checkout, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
    except (OSError, ValueError, TypeError):
        return None
    cache = common / 'autowork-execution' / 'cache'
    try:
        cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError:
        return None
    return cache


def worker_tmp(checkout, task):
    """The finished worker's saved $TMPDIR; old slots used an attempt-local directory.

    A durable allocation is authoritative even if empty or missing: never point
    a reviewer at stale files from an older attempt instead.
    """
    try:
        common = Path(git(checkout, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
        slot = json.loads((common / 'autowork-execution' / 'slots' / f'{task}.json').read_text())
        data = common / 'autowork-execution' / 'slot-data' / task
        allocation = data / 'tmp.json'
        if allocation.is_symlink():
            return None
        if allocation.exists():
            path = Path(json.loads(allocation.read_text())['path'])
            if not path.is_absolute() or path.resolve() != path or path.stat().st_uid != os.getuid():
                return None
        else:
            attempt = slot.get('data_attempt', slot['attempt'])
            path = data / f'attempt-{attempt}' / 'tmp'
        return path if path.is_dir() and any(path.iterdir()) else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def run_suite(command, checkout, limit, log, progress=None):
    """{code, failures, timed_out} of ``command`` in ``checkout``, its output in ``log``."""
    log.parent.mkdir(parents=True, exist_ok=True)
    progress = progress or log.with_suffix('.status.json')
    with open(log, 'w') as out:
        code, timed_out = main_check.run_command(command, checkout, limit, progress, output=out)
    text = log.read_text(errors='replace')
    return {'code': code, 'failures': main_check.failures(text, limit=None), 'timed_out': timed_out}


def base_tree(checkout, rev):
    """A Git tree ID excluding root planning files and the docs/ subtree, not the worktree."""
    listing = subprocess.run(['git', '-C', str(checkout), 'ls-tree', '-z', rev],
                             check=True, capture_output=True).stdout
    excluded = {path.encode() for path in PLANNING_FILES}
    entries = []
    for entry in listing.split(b'\0'):
        if not entry:
            continue
        metadata, path = entry.split(b'\t', 1)
        directory = metadata.startswith(b'040000 ')
        if (path in excluded and not directory) or (path == b'docs' and directory):
            continue
        entries.append(entry + b'\0')
    return subprocess.run(['git', '-C', str(checkout), 'mktree', '-z'], input=b''.join(entries),
                          check=True, capture_output=True).stdout.decode().strip()


def base_result(state, checkout, command, rev, limit, progress=None):
    """Cache a base check by revision and planning-stripped tree, for the same command only."""
    cache = Path(state) / 'full-check' / f'base-{rev}.json'
    tree = base_tree(checkout, rev)
    tree_cache = cache.with_name(f'base-tree-{tree}.json')
    value = None
    for source in (cache, tree_cache):
        try:
            cached = json.loads(source.read_text())
            if cached.get('command') == command:
                value = dict(cached, rev=cached.get('rev', rev), tree=tree)
                break
        except (OSError, ValueError, AttributeError):
            pass
    if value is None:
        scratch = Path(state) / 'review-tmp' / f'base-{rev[:12]}-{os.getpid()}'
        git(checkout, 'worktree', 'add', '--detach', str(scratch), rev)
        try:
            value = dict(run_suite(command, scratch, limit, cache.with_suffix('.log'), progress),
                         command=command, rev=rev, tree=tree)
        finally:
            git(checkout, 'worktree', 'remove', '--force', str(scratch))
    if value['code'] == 0 or value['failures']:  # a crash may be the host's: run it again next time
        cache.write_text(json.dumps(value))
        tree_cache.write_text(json.dumps(value))
    return value


def gate_log(state, task):
    return Path(state) / 'full-check' / f'{safe_name(task)}-merged.log'


def full_suite_gate(state, task, checkout, base=None):
    """(ok, reason) of the repository's full check on the merged tree, run once per tree and
    command (TOOLSET-227-a8): a re-review of the same tree, by a changed reviewer or after a
    requeue, reuses the verdict instead of running the suite again. A crash is never cached,
    so provisioning can fix it."""
    command = main_check.full_check(checkout)
    if not command:
        return True, ''
    tree = git(checkout, 'rev-parse', 'HEAD^{tree}')
    cache = Path(state) / 'full-check' / f'tree-{tree}.json'
    try:
        cached = json.loads(cache.read_text())
        if tree and cached.get('command') == command:
            return cached['ok'], cached['reason']
    except (OSError, ValueError, KeyError, AttributeError):
        pass
    ok, reason = run_gate(state, task, checkout, command, base)
    if tree and (ok or reason.startswith(('the full check has new failures', 'the full check exits'))):
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({'command': command, 'ok': ok, 'reason': reason, 'task': task}))
    return ok, reason


def run_gate(state, task, checkout, command, base_rev=None):
    """(ok, reason) of ``command`` on the merged tree (TOOLSET-180-72): a reviewer-approved commit
    landed while breaking 44 tests its own checks never ran. Only what the base does not already
    fail rejects a candidate; a test that passes when rerun alone is flaky, not new."""
    limit = float(os.environ.get('PI_AUTOWORK_VALIDATE_TIMEOUT') or 3600)
    log = gate_log(state, task)
    progress = log.with_name(f'{safe_name(task)}.status.json')
    merged = run_suite(command, checkout, limit, log, progress)
    if merged['code'] == 0:
        return True, ''
    if merged['timed_out']:
        return False, f'the full check ran out of time after {limit:g} s'
    if not merged['failures']:
        # It crashed before naming a test (TOOLSET-237-35): once more, then never a pass for want
        # of evidence. A crash only this tree has is its own; one the base shares is the host's.
        merged = run_suite(command, checkout, limit, log, progress)
        if merged['code'] == 0:
            return True, ''
        if merged['timed_out']:
            return False, f'the full check ran out of time after {limit:g} s'
    failures = merged['failures']
    if failures:
        # Rerun them alone first: when each passes, there is nothing for the base to explain, and the
        # base suite (as long as the merged one, on nearly every review) is not run at all.
        receipt = log.with_suffix('.reruns.json')
        main_check.rerun_failures(str(log), checkout, str(receipt), 'merged')
        try:
            flaky = json.loads(receipt.read_text()).get('flaky') or []
        except (OSError, ValueError):
            flaky = []
        failures = [f for f in failures if f not in flaky]
        if not failures:
            return True, ''
    base = base_result(state, checkout, command, base_rev or git(checkout, 'rev-parse', 'HEAD^1'), limit, progress)
    if not merged['failures']:
        crash = main_check.crash_line(log.read_text(errors='replace'))
        if base['code'] == 0:
            return False, f'the full check exits {merged["code"]} where the base passes: {crash}'
        marker = environment_marker(state, task)
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({'missing': f'a full check that runs to its test results (it crashed: {crash})',
                                      'commit': git(checkout, 'rev-parse', 'HEAD')}))
        return False, f'the full check crashed before any test result, on the base too: {crash}'
    new = failures if base['code'] == 0 else [f for f in failures if f not in base['failures']]
    if not new:
        return True, ''
    return False, 'the full check has new failures the base does not: ' + ', '.join(new[:10]) + (
        f' (+{len(new) - 10} more)' if len(new) > 10 else '')


def batch_record(state, task):
    """A batch's verdict on one candidate's merged tree (TOOLSET-258-07)."""
    return Path(state) / 'batch' / f'{safe_name(task)}.json'


PLANNING_FILES = ('TODO.md', 'TODO.archive.md', 'todo.archive.md', 'goals.json', 'BLOCKERS.md')


def same_code(checkout, left, right):
    """Whether two trees differ at most in planning files or docs/, which no check reads."""
    if not left:
        return False
    out = subprocess.run(['git', '-C', str(checkout), 'diff', '--name-only', left, right], capture_output=True, text=True)
    return out.returncode == 0 and all(p in PLANNING_FILES or p.startswith('docs/') for p in out.stdout.split())


def batched_verdict(state, task, checkout):
    """(ok, reason) a batch reached for exactly this merged tree and commit, used once; else None."""
    record = batch_record(state, task)
    try:
        value = json.loads(record.read_text())
    except (OSError, ValueError):
        return None
    if value.get('commit') != git(checkout, 'rev-parse', 'HEAD^2') or not same_code(checkout, value.get('tree'), 'HEAD^{tree}'):
        return None  # the session moved since by more than planning files: today's full verification
    record.unlink(missing_ok=True)
    return bool(value.get('ok')), value.get('reason') or ''


def verify(state, task):
    checkout = os.getcwd()
    link_ignored(checkout)
    batched = batched_verdict(state, task, checkout)
    if batched is not None:
        ok, reason = batched
        if ok:
            print(f'pi-autowork: {task} passed the full check and its review in a batch', file=sys.stderr)
            return 0
        print(f'AUTOWORK_HOLD_REASON: {reason}', flush=True)
        return 1
    environment_marker(state, task).unlink(missing_ok=True)  # this run says afresh what was missing
    # Its own private scratch, removed afterwards, on disk (reviewers copied whole repositories
    # into RAM-backed /tmp and left them, 39 GB on one host) and short: under the state directory
    # the path was 85 characters before a test added its own, past the 108-byte AF_UNIX limit.
    # A short link to it was not enough: code that resolves links got the long path back.
    # The gate's suites run in it too: the runner has no $TMPDIR, and a check that requires one
    # crashed on every candidate and its base.
    root = review_root()
    drop_dead_scratch(checkout, root)
    scratch = Path(tempfile.mkdtemp(prefix=f'aw-r-{os.getpid()}-', dir=root))
    os.environ['TMPDIR'] = str(scratch)
    batch_gate = os.environ.get('PI_AUTOWORK_BATCH_GATE')
    try:
        if batch_gate:  # a batch already passed the full check on a tree containing this one
            return batch_review(state, task, checkout, json.loads(batch_gate))
        ok, reason = full_suite_gate(state, task, checkout)
        if not ok:
            # The engine puts this line into the hold reason, which the retry's prompt quotes.
            print(f'AUTOWORK_HOLD_REASON: {reason}', flush=True)
            if not environment_marker(state, task).exists():  # a crash is the host's, not a finding
                findings = findings_path(state, task)
                findings.parent.mkdir(parents=True, exist_ok=True)
                findings.write_text(json.dumps({'verdict': reason[:800], 'commit': git(checkout, 'rev-parse', 'HEAD')}))
            print(f'pi-autowork: the full check rejects {task}: {reason}', file=sys.stderr)
            return 1
        if os.environ.get('PI_AUTOWORK_REVIEW', '1') == '0':
            return 0
        head_before = git(checkout, 'rev-parse', 'HEAD')
        return review(state, task, checkout, head_before, gate_note(state, task, checkout))
    finally:
        drop_scratch_worktrees(checkout, scratch)
        shutil.rmtree(scratch, ignore_errors=True)


def review_root():
    """Where reviews keep their scratch: a short directory on disk (`/var/tmp`)."""
    return Path(os.environ.get('PI_AUTOWORK_REVIEW_ROOT') or '/var/tmp')


def drop_dead_scratch(checkout, folder):
    """Remove the scratch of reviews whose process is gone: a review killed at its timeout
    never reaches its own cleanup (2.7 GB left on one host). Each is `aw-r-<pid>-<random>`."""
    for old in folder.glob('aw-r-*-*') if folder.is_dir() else ():
        pid = old.name.split('-')[2]
        if old.is_symlink() or not old.is_dir() or not pid.isdigit() or old.stat().st_uid != os.getuid():
            continue
        try:
            os.kill(int(pid), 0)
            continue  # still running, or a reused PID: a later review removes it
        except ProcessLookupError:
            pass
        except PermissionError:
            continue
        drop_scratch_worktrees(checkout, old)
        shutil.rmtree(old, ignore_errors=True)


def drop_scratch_worktrees(checkout, scratch):
    """Unregister the worktrees a review made under its scratch (`git worktree add --detach
    "$TMPDIR/copy"`), and nothing else: a repository-wide prune also drops other stale
    registrations, such as a session worktree the runner restores."""
    scratch = Path(scratch).resolve()
    for line in (git(checkout, 'worktree', 'list', '--porcelain') or '').splitlines():
        path = Path(line[len('worktree '):]).resolve() if line.startswith('worktree ') else None
        if path and (path == scratch or scratch in path.parents):
            subprocess.run(['git', '-C', checkout, 'worktree', 'remove', '--force', '--force', str(path)],
                           capture_output=True)


def batch_review(state, task, checkout, gate):
    """The review of one batched candidate, on its own step of the batch's merge chain; the
    verdict is recorded for the engine's later integration of that same tree."""
    head = git(checkout, 'rev-parse', 'HEAD')
    note = GATE.format(command=gate['command'], outcome='it passed', log=gate['log'])
    code = review(state, task, checkout, head, note)
    try:
        reason = json.loads(findings_path(state, task).read_text()).get('verdict') or ''
    except (OSError, ValueError, AttributeError):
        reason = ''
    record = batch_record(state, task)
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps({'tree': git(checkout, 'rev-parse', 'HEAD^{tree}'), 'commit': git(checkout, 'rev-parse', 'HEAD^2'),
                                  'ok': code == 0, 'reason': reason if code else '', 'at': time.time()}))
    return code


def batch_order(session, reported):
    """The reported tasks in the order the engine integrates them: its contract order, without a
    task waiting out a writer (TOOLSET-223-8e). A different order gives different trees."""
    scripts = Path(__file__).resolve().parents[2] / 'skills' / 'autowork' / 'scripts'
    sys.path.insert(0, str(scripts))
    import parallel_dispatch
    import parallel_integrate
    import parallel_state
    common = parallel_state.common_dir(Path(session))
    slots = {s['task_id']: s for s in parallel_state.slots(common)}
    busy = {t for t, s in slots.items() if parallel_integrate.writers_busy(s)}
    order = [t['id'] for t in parallel_dispatch.contracts(Path(session))]
    return [t for t in order if t in reported and t not in busy], {t: slots[t].get('commit') for t in reported if t in slots}


def verify_batch(state, session, script, tasks):
    """TOOLSET-258-07: the reported candidates merged onto the session one after another in the
    engine's order, the full check run once on the result, and each candidate reviewed side by
    side on its own step of that chain. Verdicts are recorded per tree; the engine then lands
    each candidate through its usual integration, which finds its verdict when the tree matches."""
    order, commits = batch_order(session, set(tasks))
    order = order[:max(2, int(os.environ.get('PI_AUTOWORK_BATCH') or 6))]
    base = git(session, 'rev-parse', 'HEAD')
    root = Path(tempfile.mkdtemp(prefix='aw-b-', dir=review_root()))
    chain = root / 'chain'
    git(session, 'worktree', 'add', '--detach', str(chain), base)
    steps, skipped = [], []
    try:
        for task in order:
            commit = commits.get(task)
            merged = commit and subprocess.run(['git', '-C', str(chain), 'merge', '--no-ff', '--no-edit', commit],
                                               capture_output=True).returncode == 0
            if not merged:
                subprocess.run(['git', '-C', str(chain), 'merge', '--abort'], capture_output=True)
                skipped.append(task)
                continue
            steps.append((task, git(chain, 'rev-parse', 'HEAD')))
        result = {'outcome': 'BATCH', 'tasks': [t for t, _ in steps], 'skipped': skipped, 'passed': [], 'held': []}
        if len(steps) < 2:
            print(json.dumps(dict(result, reason='fewer than two candidates merge together')))
            return 0
        os.environ['TMPDIR'] = str(root)
        command = main_check.full_check(str(chain))
        ok, reason = full_suite_gate(state, 'batch', str(chain), base)
        if not ok:
            # Which candidate broke it is not known yet: each goes through today's integration.
            print(json.dumps(dict(result, outcome='BATCH_GATE_FAILED', reason=reason)))
            return 0
        gate = json.dumps({'command': command or '', 'log': str(gate_log(state, 'batch'))})
        limit = max(1, int(os.environ.get('PI_AUTOWORK_REVIEWS') or 3))
        pending, running = list(steps), []
        while pending or running:
            while pending and len(running) < limit:
                task, head = pending.pop(0)
                where = root / safe_name(task)
                git(session, 'worktree', 'add', '--detach', str(where), head)
                child = subprocess.Popen(['bash', script, '--verify', state, task], cwd=where,
                                         env=dict(os.environ, PI_AUTOWORK_BATCH_GATE=gate),
                                         stdout=subprocess.DEVNULL, stderr=sys.stderr)
                running.append((task, where, child))
            time.sleep(1)
            for item in [r for r in running if r[2].poll() is not None]:
                running.remove(item)
                task, where, child = item
                result['passed' if child.returncode == 0 else 'held'].append(task)
                git(session, 'worktree', 'remove', '--force', str(where))
        print(json.dumps(result))
        return 0
    finally:
        for path in [p for p in root.iterdir() if p.is_dir()] if root.exists() else []:
            subprocess.run(['git', '-C', session, 'worktree', 'remove', '--force', str(path)], capture_output=True)
        shutil.rmtree(root, ignore_errors=True)


def gate_note(state, task, checkout):
    """What the review prompt says about the runner's full check, so the reviewer judges from
    that run instead of repeating it (TOOLSET-227-a8); '' without a full check."""
    command = main_check.full_check(checkout)
    if not command:
        return ''
    log = gate_log(state, task)
    named = main_check.failures(log.read_text(errors='replace'), limit=None) if log.exists() else []
    outcome = ('it passed' if not named else 'it passed apart from failures the base already has or that '
               'passed when rerun alone: ' + ', '.join(named[:10]))
    return GATE.format(command=command, outcome=outcome, log=log)


def review(state, task, checkout, head_before, gate=''):
    provisioned = worker_tmp(checkout, task)
    if provisioned:
        os.environ['AUTOWORK_WORKER_TMPDIR'] = str(provisioned)
    cache = repository_cache(checkout)
    if cache:
        os.environ['AUTOWORK_CACHE'] = str(cache)
    result = pi_runtime.job(pi_runtime.Settings(state), 'verify', task, checkout,
                            REVIEW.format(task=task, checkout=checkout)
                            + gate
                            + (PROVISIONED.format(path=provisioned) if provisioned else '')
                            + (CACHE.format(path=cache) if cache else '') + (
                                LIVE.format(items='; '.join(live)) if (live := pending_live(checkout, task)) else NO_LIVE),
                            f'pi-autowork-verify-{safe_name(task)}-{datetime.now():%Y%m%d%H%M%S}',
                            os.environ.get('PI_AUTOWORK_VERIFY_TIMEOUT', '1800'),
                            ['--tools', 'read,bash,grep,find,ls'])
    line = next((l for l in result['text'].splitlines() if l.startswith('PI_AUTOWORK_VERIFY:')), '')
    verdict = (re.match(r'^PI_AUTOWORK_VERIFY: (pass|fail)', line) or [None, ''])[1]
    marker = environment_marker(state, task)
    missing = ENVIRONMENT.match(line)
    if missing and verdict == 'fail':
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({'missing': ' '.join(missing.group(1).split())[:300], 'commit': head_before}))
    else:
        marker.unlink(missing_ok=True)
    findings = findings_path(state, task)
    if verdict == 'fail':
        # Preserve the failure line in the engine's hold reason, not just a generic validation
        # failure: a changed reviewer only gets another look while its verdict changes.
        print(f'AUTOWORK_HOLD_REASON: {line}', flush=True)
    if verdict == 'fail' and not missing:  # checked and found wanting: what the maintainer acts on
        findings.parent.mkdir(parents=True, exist_ok=True)
        findings.write_text(json.dumps({'verdict': ' '.join(line.split())[:800], 'commit': head_before}))
    elif verdict == 'pass':
        findings.unlink(missing_ok=True)
    if dirty(checkout) or git(checkout, 'rev-parse', 'HEAD') != head_before:
        # The engine owns this disposable integration worktree: it keeps the changes as a
        # patch for diagnosis and resets it before the next integration.
        print('pi-autowork: the reviewer changed the checkout; verification fails', file=sys.stderr)
        return 1
    if result['ok'] and verdict == 'pass':
        return 0
    print(f'pi-autowork: review of {task}: {verdict or "no verdict"} {line[:200]}', file=sys.stderr)
    return 1


def main(argv):
    push_guard()  # the engine removes GIT_* from workers' environments
    # A stop reaches the whole process group, Pi included: record it and let Pi exit.
    signal.signal(signal.SIGINT, pi_runtime._stop)
    signal.signal(signal.SIGTERM, pi_runtime._stop)
    if argv[0] == '--verify-batch':
        state, session, script, *tasks = argv[1:]
        return verify_batch(state, session, script, tasks)
    if argv[0] == '--worker':
        state, worktree, prompt_file, report = argv[1:5]
        limit = argv[5] if len(argv) > 5 else os.environ.get('PI_AUTOWORK_TASK_TIMEOUT', '5400')
        return worker(state, worktree, prompt_file, report, limit)
    return verify(argv[1], argv[2])
