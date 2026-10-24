"""The engine-launched modes of pi-autowork.

    --worker STATE WORKTREE PROMPT REPORT TIMEOUT   one Pi worker for one engine slot
    --verify STATE TASK                             the engine's validation command for a merge
    --verify-batch STATE SESSION SCRIPT TASK...     one full check and side-by-side reviews for a batch

The engine starts each in its own process group; a stop sent to the group reaches
Pi too. Exit 0 means a finished worker with a report, or a passing review.
"""
from datetime import datetime
import ast
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

from . import main_check, optimistic, pi_runtime, review_policy, workspaces
from .common import dirty, git, push_guard, safe_name
from .processes import alive, start_time

REVIEW = ('You are an independent reviewer verifying task {task} in {checkout}, which holds a worker\'s commit '
          'merged onto the session branch (see git log -1 and git diff HEAD^1 HEAD). Read the task\'s record, '
          'tasks/items/{task}.md (its acceptance and checks), run the offline checks it lists, and judge the merged change '
          'against the acceptance criteria. Block only concrete acceptance failures, regressions, security issues '
          'or credible data-loss risks, with the affected behavior and evidence named. Do not ask for more '
          'tests than the acceptance and Checks need. Style, preferred abstractions, duplicate tests and '
          'table-driven test preferences are advisory follow-ups, not failures, unless they cause a concrete '
          'defect or violate an explicit task requirement. Keep the review focused; reuse check evidence '
          'instead of exploring unrelated improvements. Do not edit, create or delete files, commit, push or change branches; '
          'build output in gitignored paths is fine. Put every temporary file and copy under $TMPDIR, '
          'never directly under /tmp, which is RAM on this host; $TMPDIR is removed after the review. '
          'For a scratch copy of the checkout use git worktree add --detach "$TMPDIR/copy" HEAD, not a '
          'file copy. If a check the task requires cannot run because a tool, SDK or service is missing '
          'here, not because the change is wrong, end instead with: PI_AUTOWORK_VERIFY: fail environment — '
          '<what is missing, and the setup doc that names it>. Otherwise end with exactly one line: '
          'PI_AUTOWORK_VERIFY: pass or '
          'PI_AUTOWORK_VERIFY: fail, then the reason.')
# The runner's full check on the merged tree is the one trusted full run (TOOLSET-227-a8).
GATE = (' The runner\'s recorded full-check gate (`{command}`) for tree `{tree}`: {outcome}. '
        '{evidence}. Reuse identifies tree and command, not an environment-bound qualification. '
        'Do not run the full check again; read the available producing evidence, and rerun only '
        'individual tests you need to examine. Every Checks entry that runs tests the full check '
        'also runs (a test file, a test directory or the full check itself) is satisfied by the '
        'runner\'s accepted gate policy: do not run it again. Run only a check '
        'the full check does not cover, such as a lint, a build or a script, and single tests to settle a doubt. '
        'Rerunning whole test files took most of every review\'s 20 to 40 minutes.')
# Offline completion is separate from live qualification (AGENTS.md): checks recorded as
# pending live become their own TASK-LIVE follow-up, so they must not fail the review.
LIVE = (' Checks that need a physical device, hardware, production or live services, or a person cannot run '
        'here. The worker recorded these as pending live checks, which become a separate live follow-up task: '
        '{items}. Do not fail for those; judge everything that can be checked offline. A live check the task '
        'requires that is not in that list is a failure: it would be lost.')
NO_LIVE = (' The worker recorded no pending live checks: a device, hardware, production or human check the '
           'task requires and that cannot run here is a failure, because nothing would record it.')
# CHANGELOG.md is coordinator-owned: the worker's line is in its report and the close writes it
# (parallel_integrate.changelog_entry). Reviews failed task after task for a changelog entry the
# merged tree could not contain (TOOLSET-368, 370, 372, 374 on 2026-10-23).
CHANGELOG_NOTE = (' CHANGELOG.md is coordinator-owned: the worker may not edit it and proposed this one-line entry '
                  'in its report, which the closure commit writes under Unreleased after this review: "{line}". '
                  'Judge that proposal against the merged change (accurate, one line, claiming nothing the code '
                  'does not do); do not fail the review because the merged tree\'s CHANGELOG.md has no entry.')
NO_CHANGELOG = (' CHANGELOG.md is coordinator-owned and the worker proposed no entry for it in its report. The '
                'closure commit writes only such a proposal: if the task\'s acceptance or scope requires a '
                'changelog entry, fail with that finding; otherwise do not ask for one.')
PROVISIONED = (' Toolchains, SDKs and caches the worker provisioned for this task (its $TMPDIR) are in {path}, '
               'also exported as AUTOWORK_WORKER_TMPDIR. Use them read-only, for example an SDK the task\'s docs place '
               'under $TMPDIR, instead of downloading again; do not write there.')
CACHE = (' SDKs, toolchains and package caches this repository\'s tasks installed are in {path} '
         '(AUTOWORK_CACHE; PROVISIONED.md there says how to use what the runner installed): use them instead '
         'of downloading again, and add one there only if a check needs it.')
ENVIRONMENT = re.compile(r'^PI_AUTOWORK_VERIFY: fail environment(?:\s*[—:-]+\s*(.*))?\s*$')
# The reviewer's verdict, with any reason after it (`pass all checks`); an echo of the prompt's
# `pass or ... fail` line is never a pass.
VERDICT = re.compile(r'^PI_AUTOWORK_VERIFY: (?:(pass)(?:ed)?\b(?!\s+or\b)|(fail)\b)')
PLANNING_FILES = ('TODO.archive.md', 'todo.archive.md', 'BLOCKERS.md')
PLANNING_DIRS = ('docs', 'tasks')  # no check reads them


def setting(name, default, kind=int):
    """A numeric setting from the environment; a malformed one falls back to the default."""
    try:
        return kind(os.environ.get(name) or default)
    except ValueError:
        print(f'pi-autowork: ignoring {name}={os.environ.get(name)!r}: not a number', file=sys.stderr)
        return default


def first_ten(items):
    """``items`` for a reason, cut at ten."""
    return ', '.join(items[:10]) + (f' (+{len(items) - 10} more)' if len(items) > 10 else '')


def timed_out_failures(failures):
    """The directories check.py gave up on, which it reports as failures."""
    return [f for f in failures if f.endswith('(timed out)')]


def check_stop():
    """Give up between suites once the engine said stop: the next one would not be stopped."""
    if pi_runtime.STOP:
        raise main_check.Stopped('stopped')


def link_ignored(checkout):
    """Gitignored dependencies are linked from the canonical checkout first: the paths the service
    names, and the installed dependencies of tracked lockfiles both trees share (TOOLSET-283-15)."""
    paths, repo = os.environ.get('PI_AUTOWORK_LINK_PATHS') or '', os.environ.get('PI_AUTOWORK_REPO')
    if not repo:
        return
    named = [p.strip() for p in paths.split(',') if p.strip()]
    found, skipped = workspaces.lockfile_dependencies(repo, checkout)
    for path, reason in skipped:
        print(f'pi-autowork: linked path {path}: {reason}', file=sys.stderr)
    wanted = named + [p for p in found if p not in named]
    if wanted:
        for path, outcome in workspaces.link_ignored(repo, checkout, ','.join(wanted)):
            print(f'pi-autowork: linked path {path}: {outcome}', file=sys.stderr)


def worker(state, worktree, prompt_file, report, limit):
    link_ignored(worktree)
    prompt = Path(prompt_file).read_text()
    task = (re.search(r'^Task: (.*)$', prompt, re.M) or [None, ''])[1]
    if not task.strip():
        print(f'pi-autowork: {prompt_file} names no task (no "Task:" line)', file=sys.stderr)
        return 1
    attempt = Path(report).parent.name
    session = f'pi-autowork-{safe_name(task)}-{attempt}'
    # The engine captures unfinished tool calls before stopping a timed-out worker.
    Path(report).with_name('session.json').write_text(json.dumps({
        'directory': str(Path(state).resolve() / 'sessions'), 'id': session}))
    settings = pi_runtime.Settings(state)
    result = pi_runtime.job(settings, 'worker', task, worktree,
                            f'Follow the instructions in this file exactly: @{prompt_file}',
                            session, limit, [f'@{prompt_file}'])
    question = unanswered(result, worktree, prompt, report)
    if question:
        # TOOLSET-282-43: a worker loaded an interactive skill, asked "Do you approve?" after 28 s
        # and stopped; the runner called it dead and asked the owner to rescope the task.
        print(f'pi-autowork: {task} asked instead of implementing ({question[:200]}); '
              'resuming its session once with the contract as its approval', file=sys.stderr)
        result = pi_runtime.job(settings, 'worker', task, worktree, APPROVAL.format(prompt=prompt_file),
                                session, limit, [f'@{prompt_file}'])
        question = unanswered(result, worktree, prompt, report)
        if question:
            Path(report).write_text(json.dumps({
                'task': task, 'commit': None, 'changed_files': [], 'checks': [], 'changelog': '',
                'blockers': [f'the worker asked twice instead of implementing: {question}']}))
            return 1
    return 0 if result['ok'] and Path(report).is_file() else 1


APPROVAL = ('No person is attached to this session, so nobody will answer your question. The task '
            'contract in @{prompt} is your approval: implement it now, commit, and write the report. '
            'Stop only for a real blocker, and write it in the report.')


def unanswered(result, worktree, prompt, report):
    """The question a worker ended its session with, having written no report and no commit; else ''."""
    if not result.get('ok') or Path(report).is_file():
        return ''
    baseline = (re.search(r'^Baseline: (\S+)$', prompt, re.M) or [None, ''])[1]
    if baseline and git(worktree, 'rev-parse', 'HEAD') != git(worktree, 'rev-parse', baseline):
        return ''
    lines = [line.strip().strip('*_ ').strip() for line in (result.get('text') or '').splitlines()]
    last = next((line for line in reversed(lines) if line), '')
    return last if last.endswith('?') else ''


def execution_dir(checkout):
    """The engine's shared `autowork-execution` directory, or None outside a repository."""
    common = git(checkout, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    return Path(common) / 'autowork-execution' if common else None


def attempt_data(execution, task):
    """The slot data directory of the task's current data attempt."""
    slot = json.loads((execution / 'slots' / f'{task}.json').read_text())
    return execution / 'slot-data' / task / f'attempt-{slot.get("data_attempt", slot["attempt"])}'


def worker_report(checkout, task):
    """The worker's report for the task's current attempt, from the engine's slot data, or {}."""
    execution = execution_dir(checkout)
    if not execution:
        return {}
    try:
        report = json.loads((attempt_data(execution, task) / 'report.json').read_text())
    except (OSError, ValueError, KeyError, TypeError):
        return {}
    return report if isinstance(report, dict) else {}


def changelog_note(checkout, task):
    """What the reviewer is told about CHANGELOG.md: the worker's proposal, or that there is none."""
    line = ' '.join(str(worker_report(checkout, task).get('changelog') or '').split())
    return CHANGELOG_NOTE.format(line=line.replace('"', "'")[:600]) if line else NO_CHANGELOG


def pending_live(checkout, task):
    """The pending live checks the worker's report recorded, from the engine's slot data."""
    report = worker_report(checkout, task)
    items = report.get('pending_live') if isinstance(report, dict) else None
    items = items if isinstance(items, list) else [items] if items else []
    texts = [' — '.join(str(i[k]) for k in ('check', 'command', 'summary', 'description', 'reason') if i.get(k))
             if isinstance(i, dict) else str(i) if i is not None else '' for i in items]
    return [' '.join(t.split()) for t in texts if t.strip()]  # the engine's live_items, which the close uses


def findings_path(state, task):
    """A failed review's verdict, for the DOCS-MAINTAINER to split or restate the task by."""
    return Path(state) / 'review-findings' / f'{safe_name(task)}.json'


def record_findings(state, task, verdict, commit):
    findings = findings_path(state, task)
    findings.parent.mkdir(parents=True, exist_ok=True)
    findings.write_text(json.dumps({'verdict': verdict[:800], 'commit': commit}))


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
    execution = execution_dir(checkout)
    if not execution:
        return None
    cache = execution / 'cache'
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
    execution = execution_dir(checkout)
    if not execution:
        return None
    try:
        attempt = attempt_data(execution, task)
        allocation = attempt.parent / 'tmp.json'
        if allocation.is_symlink():
            return None
        if allocation.exists():
            path = Path(json.loads(allocation.read_text())['path'])
            if not path.is_absolute() or path.resolve() != path or path.stat().st_uid != os.getuid():
                return None
        else:
            path = attempt / 'tmp'
        return path if path.is_dir() and any(path.iterdir()) else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def run_suite(command, checkout, limit, log, progress=None):
    """{code, failures, timed_out} of ``command`` in ``checkout``, its output in ``log``."""
    check_stop()
    log.parent.mkdir(parents=True, exist_ok=True)
    progress = progress or log.with_suffix('.status.json')
    with open(log, 'w') as out:
        code, timed_out = main_check.run_command(command, checkout, limit, progress, output=out,
                                                 stop=lambda: pi_runtime.STOP)
    text = log.read_text(errors='replace')
    summaries = re.findall(r'^Ran \d+ tests? in [\d.]+s\n\n((?:OK|FAILED)\b[^\n]*)', text, re.M)
    # Arbitrary declared commands may use an unsupported inventory format. A zero exit
    # still admits them, but no parsed skips must not be advertised as no skipped tests.
    unknown_skips = any(re.search(r'\bskip(?:ped|ping)?\b', line, re.I)
                        for line in text.splitlines() if line not in summaries)
    skips = (sum(int(n) for s in summaries for n in re.findall(r'\bskipped=(\d+)', s))
             if summaries and not unknown_skips else None)
    return {'code': code, 'failures': main_check.failures(text, limit=None), 'timed_out': timed_out,
            'skips': skips,
            'resource_skips': main_check.gate_skips(text)}


def base_tree(checkout, rev):
    """A Git tree ID excluding root planning files and the docs/ and tasks/ subtrees, not the worktree."""
    listing = subprocess.run(['git', '-C', str(checkout), 'ls-tree', '-z', rev],
                             check=True, capture_output=True).stdout
    excluded = {path.encode() for path in PLANNING_FILES}
    entries = []
    for entry in listing.split(b'\0'):
        if not entry:
            continue
        metadata, path = entry.split(b'\t', 1)
        directory = metadata.startswith(b'040000 ')
        if (path in excluded and not directory) or (directory and path.decode() in PLANNING_DIRS):
            continue
        entries.append(entry + b'\0')
    return subprocess.run(['git', '-C', str(checkout), 'mktree', '-z'], input=b''.join(entries),
                          check=True, capture_output=True).stdout.decode().strip()


def conclusive(value):
    """Whether a suite result says something about its tree, so it is worth caching.

    A crash and a directory check.py gave up on are the host's, not the tree's: caching such a
    base let the same timeout on a candidate read as nothing new, and the gate passed a tree
    whose full check never ran that directory.
    """
    return (bool(value['code'] == 0 or value['failures'])
            and not value.get('timed_out')
            and not timed_out_failures(value['failures']))


def main_green_base(state, checkout, command, rev, tree):
    """The base result main's own check already proved, or None: main's latest record is green
    for the same command, on a revision whose planning-stripped tree is the base's. A candidate
    whose merged tree failed 21 tests then ran the whole suite again on a base main had just
    checked, about ten minutes to confirm a hold. Tests main's check excused as flaky are the
    base's failures, so they are not blamed on the candidate."""
    record = main_check.read(state)
    green = record.get('green') if record.get('state') == 'green' else None
    if not green or main_check.command(repo=checkout) != command:
        return None
    try:
        if green != rev and base_tree(checkout, green) != tree:
            return None
    except (OSError, subprocess.CalledProcessError):
        return None  # main's revision is not in this checkout: no proof
    flaky = [f for f in record.get('flaky') or [] if isinstance(f, str)]
    return {'code': 1 if flaky else 0, 'failures': flaky, 'timed_out': False, 'skips': None, 'resource_skips': 0,
            'command': command, 'rev': rev, 'tree': tree, 'from_main': green}


def base_result(state, checkout, command, rev, limit, progress=None):
    """Cache a base check by revision and planning-stripped tree, for the same command only."""
    if not rev:
        raise ValueError('the base revision is unknown, so the merged tree has nothing to compare with')
    cache = Path(state) / 'full-check' / f'base-{rev}.json'
    tree = base_tree(checkout, rev)
    tree_cache = cache.with_name(f'base-tree-{tree}.json')
    value = None
    for source in (cache, tree_cache):
        try:
            cached = json.loads(source.read_text())
            if cached.get('command') == command and conclusive(cached):
                value = dict(cached, rev=cached.get('rev', rev), tree=tree)
                break
        except (OSError, ValueError, AttributeError, KeyError):
            pass
    if value is None:
        value = main_green_base(state, checkout, command, rev, tree)
    if value is None:
        # A short directory on disk, like a review's scratch: under the state directory this path
        # reached 87 characters before the suite added its own, past the 108-byte AF_UNIX limit.
        # The `aw-r-<pid>-*` name keeps a killed review's copy where drop_dead_scratch sweeps it.
        holder = Path(tempfile.mkdtemp(prefix=f'aw-r-{os.getpid()}-', dir=review_root()))
        scratch = holder / 'base'
        try:
            if git(checkout, 'worktree', 'add', '--detach', str(scratch), rev) is None:
                raise ValueError(f'the base worktree for {rev[:12]} could not be created in {holder}')
            value = dict(run_suite(command, scratch, limit, cache.with_suffix('.log'), progress),
                         command=command, rev=rev, tree=tree)
        finally:
            git(checkout, 'worktree', 'remove', '--force', '--force', str(scratch))
            shutil.rmtree(holder, ignore_errors=True)
    if conclusive(value):
        # A crash or a timeout may be the host's: run it again next time. A cached timeout named
        # only the tests before its cut-off, so later ones read as new failures on every tree.
        cache.parent.mkdir(parents=True, exist_ok=True)  # main's record ran no suite to create it
        cache.write_text(json.dumps(value))
        tree_cache.write_text(json.dumps(value))
    return value


def gate_log(state, task):
    return Path(state) / 'full-check' / f'{safe_name(task)}-merged.log'


def producing_gate_log(state, cached):
    """Only a readable, runner-owned log bound to this record is explanatory evidence."""
    try:
        source = Path(cached['log'])
        if (source.is_symlink() or source.parent.resolve() != (Path(state) / 'full-check').resolve()
                or not source.is_file() or source.stat().st_uid != os.getuid()):
            return None
        content = source.read_bytes()
        if content and hashlib.sha256(content).hexdigest() == cached.get('log_sha256'):
            return source
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def replay_gate_log(state, task, cached):
    """Keep the task-local log for existing consumers; reviewer text uses the producer record."""
    target, source = gate_log(state, task), producing_gate_log(state, cached)
    try:
        # Replaced even when present: it may be this task's log of an earlier tree.
        if source and not (target.exists() and target.samefile(source)):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    except OSError:
        pass


def full_suite_gate(state, task, checkout, base=None):
    """(ok, reason) of the merged-tree landing check (affected where supported), once per tree and
    command (TOOLSET-227-a8): a re-review of the same tree, by a changed reviewer or after a
    requeue, reuses the verdict instead of running the suite again. A crash is never cached,
    so provisioning can fix it."""
    full_command = main_check.full_check(checkout)
    if not full_command:
        return True, ''
    command, selection = main_check.landing_check(
        checkout, base or git(checkout, 'rev-parse', 'HEAD^1'), full_command)
    tree = git(checkout, 'rev-parse', 'HEAD^{tree}')
    cache = Path(state) / 'full-check' / f'tree-{tree}.json'
    try:
        cached = json.loads(cache.read_text())
        if tree and cached.get('command') == command:
            replay_gate_log(state, task, cached)
            gate_event(state, task, "full check: this tree's earlier result reused ("
                       + ('passed' if cached['ok'] else 'failed') + ')', fresh=True)
            return cached['ok'], cached['reason']
    except (OSError, ValueError, KeyError, AttributeError, TypeError):
        pass
    details = {}
    ok, reason = run_gate(state, task, checkout, command, base, evidence=details,
                          baseline_command=full_command)
    if tree and (ok or reason.startswith(('the full check has new failures', 'the full check exits'))):
        cache.parent.mkdir(parents=True, exist_ok=True)
        # The evidence is tree-keyed too: this cache outlives the task that ran it, and that
        # task's own log is overwritten when it next gates a different tree.
        evidence = cache.with_suffix('.log')
        try:
            shutil.copyfile(gate_log(state, task), evidence)
        except OSError:
            evidence = gate_log(state, task)
        try:
            digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
        except OSError:
            digest = None
        cache.write_text(json.dumps({'command': command, 'full_command': full_command,
                                     'selection': selection, 'tree': tree,
                                     'commit': git(checkout, 'rev-parse', 'HEAD'),
                                     'ok': ok, 'reason': reason, 'task': task,
                                     'log': str(evidence), 'log_sha256': digest, **details}))
    return ok, reason


class QuietWindowMissed(Exception):
    """No quiet window came within PI_AUTOWORK_QUIET_WAIT."""


def quiet_reruns(state, task, log, checkout, rev, tests, limit):
    """The ``tests`` that pass when rerun one at a time with a host check slot held, once this
    repository's main check is done. Rerun four at a time beside main's full suite, the runner's
    own engine tests ran out of their 120 s and held three candidates whose trees pass them.
    The wait for that quiet window is bounded by PI_AUTOWORK_QUIET_WAIT (default 900 s): the
    host's few check slots are shared by every runner's full suite, and a two-minute rerun queued
    behind them held a review for three hours. Past the bound the tests rerun one at a time
    without a slot."""
    receipt = log.with_suffix('.quiet.json')
    receipt.unlink(missing_ok=True)
    wait = setting('PI_AUTOWORK_QUIET_WAIT', 900, float)
    deadline = time.monotonic() + min(limit, wait)
    while time.monotonic() < deadline:
        record = main_check.read(state)
        if record.get('state') != 'running' or not main_check.alive(record.get('pid'), record.get('start_time')):
            break
        check_stop()
        time.sleep(5)

    def waiting(_ahead):
        check_stop()
        if time.monotonic() >= deadline:
            raise QuietWindowMissed

    def rerun(only):
        main_check.rerun_failures(str(log), checkout, str(receipt), rev, only=set(only), workers=1)
        quiet = json.loads(receipt.read_text())
        if not isinstance(quiet, dict) or quiet.get('rev') != rev or not isinstance(quiet.get('flaky'), list):
            raise ValueError('the rerun left no receipt for this revision')
        return quiet['flaky']

    def reruns():
        # A sample first: 108 failures rerun one at a time, each to its 120 s limit, took three
        # hours and every review's time limit with them. When no failure of the sample passes
        # alone they are not flaky; the base comparison that follows says whose they are.
        sample = max(1, setting('PI_AUTOWORK_QUIET_SAMPLE', 5))
        flaky = rerun(tests[:sample])
        if flaky and tests[sample:]:
            flaky += rerun(tests[sample:])
        elif tests[sample:]:
            print(f'pi-autowork: none of {sample} failures of {task} passed alone; the other '
                  f'{len(tests) - sample} are not rerun', file=sys.stderr)
        return flaky

    try:
        try:
            with main_check.check_slot(waiting):
                return reruns()
        except QuietWindowMissed:
            print(f'pi-autowork: no quiet check slot for {task} within {wait:g} s; '
                  'rerunning its failures one at a time without one', file=sys.stderr)
            return reruns()
    except main_check.Stopped:
        raise
    except Exception as error:  # like the first reruns: without a receipt, none is excused
        print(f'pi-autowork: rerunning the failures of {task} alone failed: {error}', file=sys.stderr)
        return []


def gate_events(state, task):
    """Where a review's gate records its stages, one JSON line each ({at, text}), for the TUI's
    task view: after the worker's last action it showed nothing for the 15 minutes the merged
    and base suites ran."""
    return Path(state) / 'full-check' / f'{safe_name(task)}.gate.jsonl'


def gate_event(state, task, text, *, fresh=False):
    path = gate_events(state, task)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w' if fresh else 'a') as stream:
            stream.write(json.dumps({'at': time.time(), 'text': text}) + '\n')
    except OSError:
        pass  # a view's record; the gate's verdict never depends on it


def run_gate(state, task, checkout, command, base_rev=None, *, evidence=None, baseline_command=None):
    """(ok, reason) of ``command`` on the merged tree (TOOLSET-180-72): a reviewer-approved commit
    landed while breaking 44 tests its own checks never ran. Only what the base does not already
    fail rejects a candidate; a test that passes when rerun alone is flaky, not new."""
    gate_event(state, task, 'full check on the merged tree started', fresh=True)
    ok, reason = _run_gate(state, task, checkout, command, base_rev, evidence=evidence,
                           baseline_command=baseline_command)
    gate_event(state, task, 'full check passed' if ok else f'full check failed: {reason}')
    return ok, reason


def merged_gate_verdict(result, isolated_rerun, incomplete, limit):
    """A verdict needing no base, or None when a base comparison is still required."""
    if result['code'] == 0:
        return True, ''
    if result['timed_out']:
        return False, f'the full check ran out of time after {limit:g} s'
    failures = [f for f in result['failures'] if f not in isolated_rerun]
    if result['failures'] and not failures:
        # Named tests passing alone cannot excuse a signal or an unfinished inventory.
        if result['code'] != 1 or incomplete:
            return False, f'the full check stopped before its results were complete (exit {result["code"]}); the rest never ran'
        return True, ''
    unfinished = timed_out_failures(result['failures'])
    if unfinished:
        # A directory timeout is not a failure the base can excuse.
        return False, 'the full check did not complete ' + first_ten(unfinished)
    return None


def incomplete_base(base):
    """A cut-off base names only failures before its cut-off, so cannot excuse a candidate."""
    return not conclusive(base) and bool(base.get('timed_out') or base['failures'])


def gate_verdict(result, isolated_rerun=(), baseline=None, *, incomplete=False, limit=3600,
                 crash='', base_error=None):
    """Pure (ok, reason) from recorded results and reruns, with no suites or receipt writes.

    Supply a baseline (or base_error) unless the merged result is decisive on its own.
    The caller retries a nameless crash before presenting its final result here.
    """
    verdict = merged_gate_verdict(result, isolated_rerun, incomplete, limit)
    if verdict is not None:
        return verdict
    if base_error is not None:
        return False, f'the full check has no base to compare with: {base_error}'
    if incomplete_base(baseline):
        return False, 'the full check has no base to compare with: the base run did not complete'
    if not result['failures']:
        if baseline['code'] == 0 or baseline['failures']:
            return False, (f'the full check exits {result["code"]} where the base '
                           + ('passes' if baseline['code'] == 0 else 'runs to its test results') + f': {crash}')
        return False, f'the full check crashed before any test result, on the base too: {crash}'
    failures = [f for f in result['failures'] if f not in isolated_rerun]
    new = failures if baseline['code'] == 0 else [f for f in failures if f not in baseline['failures']]
    return (False, 'the full check has new failures the base does not: ' + first_ten(new)) if new else (True, '')


def gate_reruns(state, task, checkout, log, failures, limit):
    """Collect isolated passes and completeness evidence; an invalid rerun receipt excuses nothing."""
    receipt = log.with_suffix('.reruns.json')
    receipt.unlink(missing_ok=True)
    rev = git(checkout, 'rev-parse', 'HEAD') or ''
    check_stop()
    gate_event(state, task, f'rerunning the {len(failures)} failure(s) alone')
    try:
        main_check.rerun_failures(str(log), checkout, str(receipt), rev)
        reruns = json.loads(receipt.read_text())
    except Exception as error:
        print(f'pi-autowork: rerunning the failures of {task} failed: {error}', file=sys.stderr)
        reruns = {}
    if not isinstance(reruns, dict) or reruns.get('rev') != rev or not isinstance(reruns.get('flaky'), list):
        reruns = {}
    remaining = [f for f in failures if f not in (reruns.get('flaky') or [])]
    if remaining and reruns:
        remaining = [f for f in remaining if f not in quiet_reruns(state, task, log, checkout, rev, remaining, limit)]
    isolated = [f for f in failures if f not in remaining]
    gate_event(state, task, f'{len(isolated)} passed alone; {len(remaining)} still fail')
    return isolated, reruns.get('incomplete')


def compare_gate_base(state, task, checkout, command, base_rev, limit, log, progress, evidence):
    """Collect the full baseline and crash evidence, then record only the original receipt fields."""
    gate_event(state, task, 'comparing with the base (its full check, unless one is on record)')
    try:
        # Never compare with an affected-only green.
        base = base_result(state, checkout, command,
                           base_rev or git(checkout, 'rev-parse', 'HEAD^1'), limit, progress)
        gate_event(state, task, 'base: ' + ('all tests pass' if base['code'] == 0 else f'{len(base["failures"])} failing')
                   + (f" (main's check of {base['from_main'][:7]}, not run again)" if base.get('from_main') else ''))
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        return gate_verdict(evidence['result'], evidence['isolated_rerun'], base_error=str(error))
    merged, isolated, crash = evidence['result'], evidence['isolated_rerun'], ''
    if not incomplete_base(base):
        if merged['failures']:
            failures = [f for f in merged['failures'] if f not in isolated]
            evidence['baseline'] = base
            evidence['baseline_equivalent'] = [f for f in failures if base['code'] != 0 and f in base['failures']]
        else:
            crash = main_check.crash_line(log.read_text(errors='replace'))
            if base['code'] != 0 and not base['failures']:
                marker = environment_marker(state, task)
                marker.parent.mkdir(parents=True, exist_ok=True)
                marker.write_text(json.dumps({
                    'missing': f'a full check that runs to its test results (it crashed: {crash})',
                    'commit': git(checkout, 'rev-parse', 'HEAD')}))
    return gate_verdict(merged, isolated, base, crash=crash)


def _run_gate(state, task, checkout, command, base_rev=None, *, evidence=None, baseline_command=None):
    limit = setting('PI_AUTOWORK_VALIDATE_TIMEOUT', 3600, float)
    log = gate_log(state, task)
    progress = log.with_name(f'{safe_name(task)}.status.json')
    evidence = evidence if evidence is not None else {}
    evidence.update(isolated_rerun=[], baseline_equivalent=[])
    merged = run_suite(command, checkout, limit, log, progress)
    evidence['result'] = merged
    gate_event(state, task, 'merged tree: ' + ('all tests passed' if merged['code'] == 0 else
                                               f'{len(merged["failures"])} test(s) failed' if merged['failures']
                                               else f'exit {merged["code"]} before any test result'))
    if merged['code'] != 0 and not merged['timed_out'] and not merged['failures']:
        # A nameless crash gets one retry before requiring evidence from the base.
        merged = run_suite(command, checkout, limit, log, progress)
        evidence['result'] = merged
    incomplete = False
    if merged['code'] != 0 and not merged['timed_out'] and merged['failures']:
        # If all pass alone, avoid the full base suite altogether.
        evidence['isolated_rerun'], incomplete = gate_reruns(state, task, checkout, log, merged['failures'], limit)
    verdict = merged_gate_verdict(merged, evidence['isolated_rerun'], incomplete, limit)
    if verdict is not None:
        return verdict
    return compare_gate_base(state, task, checkout, baseline_command or command,
                             base_rev, limit, log, progress, evidence)


def batch_record(state, task):
    """A batch's verdict on one candidate's merged tree (TOOLSET-258-07)."""
    return Path(state) / 'batch' / f'{safe_name(task)}.json'


def same_code(checkout, left, right):
    """Whether two trees differ at most in planning files, docs/ or tasks/, which no check reads."""
    if not left:
        return False
    out = subprocess.run(['git', '-C', str(checkout), 'diff', '-z', '--name-only', left, right],
                         capture_output=True, text=True)
    return out.returncode == 0 and all(p in PLANNING_FILES or p.startswith(tuple(d + '/' for d in PLANNING_DIRS))
                                       for p in out.stdout.split('\0') if p)


def batched_verdict(state, task, checkout):
    """(ok, reason) a batch reached for exactly this merged tree and commit, used once; else None."""
    record = batch_record(state, task)
    try:
        value = json.loads(record.read_text())
    except (OSError, ValueError):
        return None
    if value.get('commit') != git(checkout, 'rev-parse', 'HEAD^2') or not same_code(checkout, value.get('tree'), 'HEAD^{tree}'):
        # The session moved since by more than planning files: today's full verification. The record
        # can never match again; left, it held new batches back for two hours.
        record.unlink(missing_ok=True)
        return None
    policy = value.get('review_policy')
    # A skipped model review cannot inherit same_code's broad docs/tasks drift allowance.
    # Nor may an old skip survive a policy/configuration change or be advertised as a review.
    if ((os.environ.get('PI_AUTOWORK_REVIEW') == 'auto'
         and (not isinstance(policy, dict) or type(policy.get('required')) is not bool))
            or (isinstance(policy, dict) and policy.get('required') is False and (
                dirty(checkout) or policy.get('tree') != git(checkout, 'rev-parse', 'HEAD^{tree}')
                or policy.get('version') != review_policy.version()
                or policy.get('mode') != os.environ.get('PI_AUTOWORK_REVIEW', '1')
                or policy.get('command') != main_check.full_check(checkout)))):
        record.unlink(missing_ok=True)
        return None
    if value.get('ok'):
        landing_receipt(state, task, checkout, value.get('selection'))
    record.unlink(missing_ok=True)
    return bool(value.get('ok')), value.get('reason') or ''


def landing_receipt(state, task, checkout, selection):
    """Keep the accepted landing scope after a one-use batch verdict is consumed."""
    target = Path(state) / 'landing-check' / f'{safe_name(task)}.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dict(task=task, commit=git(checkout, 'rev-parse', 'HEAD'),
                                     tree=git(checkout, 'rev-parse', 'HEAD^{tree}'), selection=selection)))


def gate_selection(state, checkout):
    tree = git(checkout, 'rev-parse', 'HEAD^{tree}')
    try:
        record = json.loads((Path(state) / 'full-check' / f'tree-{tree}.json').read_text())
        if main_check.receipt_command_matches(record, main_check.full_check(checkout)):
            return record.get('selection')
    except (OSError, ValueError, AttributeError):
        pass
    return None


def review_gate_evidence(state, checkout):
    """A source/log-bound receipt, not merely success from a possibly absent gate."""
    if dirty(checkout):
        return None
    tree = git(checkout, 'rev-parse', 'HEAD^{tree}')
    try:
        record = json.loads((Path(state) / 'full-check' / f'tree-{tree}.json').read_text())
        if (record.get('tree') == tree and record.get('ok') is True
                and main_check.receipt_command_matches(record, main_check.full_check(checkout))
                and producing_gate_log(state, record)):
            return record
    except (OSError, ValueError, AttributeError, TypeError):
        pass
    return None


def review_decision(state, task, checkout, evidence=None):
    decision = review_policy.decide(checkout, task, evidence=evidence)
    decision.update(tree=git(checkout, 'rev-parse', 'HEAD^{tree}'),
                    commit=git(checkout, 'rev-parse', 'HEAD'), command=main_check.full_check(checkout))
    path = Path(state) / 'review-policy' / f'{safe_name(task)}.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(decision))
    action = 'required' if decision['required'] else 'skipped'
    print(f'pi-autowork: model review {action} for {task}: {decision["reason"]}', file=sys.stderr)
    return decision


def verify(state, task):
    checkout = os.getcwd()
    link_ignored(checkout)
    batch_gate = os.environ.get('PI_AUTOWORK_BATCH_GATE')
    # A batch child reviews afresh: an unused record from an earlier batch is not its verdict.
    batched = None if batch_gate else batched_verdict(state, task, checkout)
    if batched is not None:
        ok, reason = batched
        if ok:
            print(f'pi-autowork: {task} passed batch verification', file=sys.stderr)
            return 0
        print(f'AUTOWORK_HOLD_REASON: {reason}', flush=True)
        return 1
    environment_marker(state, task).unlink(missing_ok=True)  # this run says afresh what was missing
    # So do its findings: a pass, an unreviewed pass or no verdict left an earlier commit's in place.
    findings_path(state, task).unlink(missing_ok=True)
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
    lease = review_port_lease()
    try:
        if batch_gate:  # a batch already passed the full check on a tree containing this one
            return batch_review(state, task, checkout, json.loads(batch_gate))
        if optimistic.enabled() and not main_check.affected_checker(checkout, main_check.full_check(checkout)):
            # Optimistic landing (TOOLSET-344-7dadea23): its own checks and the review decide;
            # main's full check runs after it lands, and a regression there reverts it.
            if not review_decision(state, task, checkout)['required']:
                return 0
            head_before = git(checkout, 'rev-parse', 'HEAD')
            return review(state, task, checkout, head_before, OPTIMISTIC_NOTE)
        ok, reason = full_suite_gate(state, task, checkout)
        if not ok:
            # The engine puts this line into the hold reason, which the retry's prompt quotes.
            print(f'AUTOWORK_HOLD_REASON: {reason}', flush=True)
            if not environment_marker(state, task).exists():  # a crash is the host's, not a finding
                record_findings(state, task, reason, git(checkout, 'rev-parse', 'HEAD'))
            print(f'pi-autowork: the full check rejects {task}: {reason}', file=sys.stderr)
            return 1
        if not review_decision(state, task, checkout, review_gate_evidence(state, checkout))['required']:
            landing_receipt(state, task, checkout, gate_selection(state, checkout))
            return 0
        head_before = git(checkout, 'rev-parse', 'HEAD')
        code = review(state, task, checkout, head_before, gate_note(state, task, checkout))
        if code == 0:
            landing_receipt(state, task, checkout, gate_selection(state, checkout))
        return code
    except main_check.Stopped:
        print(f'pi-autowork: verification of {task} stopped', file=sys.stderr)
        return 1
    finally:
        if lease is not None:
            os.close(lease)
        drop_scratch_worktrees(checkout, scratch)
        shutil.rmtree(scratch, ignore_errors=True)


def review_port_lease():
    """A 100-port block of its own for this review's checks and reviewer, as each worker gets: a
    task whose checks bind $AUTOWORK_PORT_BASE failed its review for want of one. The block is the
    process's while the returned descriptor stays open; None when none is free."""
    try:
        dispatch, _, _ = engine_modules()
        base, lease = dispatch.port_lease(1)
    except (ImportError, OSError, ValueError):
        return None
    os.environ['AUTOWORK_PORT_BASE'] = str(base)
    return lease


def review_root():
    """Where reviews keep their scratch: a short directory on disk (`/var/tmp`)."""
    return Path(os.environ.get('PI_AUTOWORK_REVIEW_ROOT') or '/var/tmp')


def drop_dead_scratch(checkout, folder):
    """Remove the scratch of reviews whose process is gone: a review killed at its timeout
    never reaches its own cleanup (2.7 GB left on one host). Each is `aw-r-<pid>-<random>`, or
    `aw-b-<pid>-<random>` for a batch."""
    for old in [*folder.glob('aw-r-*-*'), *folder.glob('aw-b-*-*')] if folder.is_dir() else ():
        pid = old.name.split('-')[2]
        try:
            if old.is_symlink() or not old.is_dir() or not pid.isdigit() or old.stat().st_uid != os.getuid():
                continue
        except OSError:
            continue  # a parallel review removed it first
        if alive(int(pid)) and not started_after(int(pid), old):
            continue  # still running
        drop_scratch_worktrees(checkout, old)
        shutil.rmtree(old, ignore_errors=True)


def started_after(pid, path):
    """Whether ``pid`` started after ``path`` was last changed: a reused PID, not the scratch's owner,
    which started before it made the folder. Unknown is False, so the scratch is kept."""
    try:
        ticks = int(start_time(pid))
        boot = next(int(l.split()[1]) for l in Path('/proc/stat').read_text().splitlines() if l.startswith('btime '))
        return boot + ticks / os.sysconf('SC_CLK_TCK') > path.stat().st_mtime + 1
    except (OSError, ValueError, TypeError, IndexError, StopIteration):
        return False


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
    # An environment fail or no verdict writes no findings: an earlier review's would be recorded.
    findings_path(state, task).unlink(missing_ok=True)
    policy = review_decision(state, task, checkout, gate.get('evidence'))
    code = review(state, task, checkout, head, gate['note']) if policy['required'] else 0
    reason = review_findings(state, task)
    record = batch_record(state, task)
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps({'tree': git(checkout, 'rev-parse', 'HEAD^{tree}'), 'commit': git(checkout, 'rev-parse', 'HEAD^2'),
                                  'ok': code == 0, 'at': time.time(), 'selection': gate.get('selection'),
                                  'review_policy': policy,
                                  # verify prints it as the hold reason, which must never be empty
                                  'reason': (reason or f'the batch review of {task} failed without a finding '
                                             '(no verdict, an environment miss or a changed checkout)') if code else ''}))
    return code


def engine_modules():
    """The repository's engine modules: parallel_dispatch, parallel_integrate, parallel_state."""
    from pi_autowork.engine import parallel_dispatch
    from pi_autowork.engine import parallel_integrate
    from pi_autowork.engine import parallel_state
    return parallel_dispatch, parallel_integrate, parallel_state


def batch_order(session, reported):
    """The reported tasks in the order the engine integrates them: its contract order, without a
    task waiting out a writer (TOOLSET-223-8e). A different order gives different trees."""
    parallel_dispatch, parallel_integrate, parallel_state = engine_modules()
    common = parallel_state.common_dir(Path(session))
    slots = {s['task_id']: s for s in parallel_state.slots(common)}
    eligible = {t for t, s in slots.items() if s['state'] == 'reported'
                and not parallel_integrate.writers_busy(s) and not parallel_state.worker_live(s)
                and not parallel_state.missing_commit_report(common, s)}
    order = [t['id'] for t in parallel_dispatch.contracts(Path(session))]
    return [t for t in order if t in reported and t in eligible], {t: slots[t] for t in reported if t in eligible}


def new_failures(state, checkout):
    """The tests the recorded full check of ``checkout``'s tree failed that the base passes and
    that did not pass when rerun alone; [] without a record that names them."""
    tree = git(checkout, 'rev-parse', 'HEAD^{tree}')
    try:
        record = json.loads((Path(state) / 'full-check' / f'tree-{tree}.json').read_text())
        failures = record['result']['failures']
        excused = (record.get('baseline_equivalent') or []) + (record.get('isolated_rerun') or [])
    except (OSError, ValueError, KeyError, TypeError):
        return []
    return [f for f in failures if isinstance(f, str) and f not in excused]


def imported_files(checkout, start, index, limit=500):
    """``start`` and every tracked Python file it imports, transitively, by module name. A name
    matches every file of that basename (and a package's __init__.py): too many, never too few."""
    found, todo = set(), [start]
    while todo and len(found) < limit:
        path = todo.pop()
        if path in found:
            continue
        found.add(path)
        try:
            tree = ast.parse((Path(checkout) / path).read_text(errors='replace'))
        except (OSError, SyntaxError, ValueError):
            continue
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(part for alias in node.names for part in alias.name.split('.'))
            elif isinstance(node, ast.ImportFrom):
                names.update((node.module or '').split('.'))
                names.update(alias.name for alias in node.names)
        todo += [p for name in names if name for p in index.get(name, ()) if p not in found]
    return found


FRAME = re.compile(r'^\s*File "([^"]+)", line (\d+), in ')


def tracebacks(log):
    """{test id: [(path, line)]}: the frames of each failure or error in unittest output."""
    found, current = {}, None
    for line in log.splitlines():
        head = re.match(r'^(?:FAIL|ERROR): \S+ \(([^)]+)\)', line)
        if head:
            current = found.setdefault(head[1], [])
        elif line.startswith(('-----', '=====')) and current is not None and current:
            current = None
        elif current is not None and (frame := FRAME.match(line)):
            current.append((frame[1], int(frame[2])))
    return found


def traceback_blame(checkout, frames, tracked, owner):
    """The candidates that wrote a line the failure ran through: `git blame` of each frame in a
    tracked file, by its path inside the checkout (the log may name another chain's copy)."""
    blamed = set()
    for path, line in frames:
        parts = Path(path).parts
        relative = next(('/'.join(parts[i:]) for i in range(len(parts)) if '/'.join(parts[i:]) in tracked), None)
        if relative is None:
            continue  # the standard library or a temporary file
        out = git(checkout, 'blame', '--porcelain', '-L', f'{line},{line}', 'HEAD', '--', relative) or ''
        if task := owner(out.split(' ', 1)[0]):
            blamed.add(task)
    return blamed


def batch_suspects(state, checkout, base, steps):
    """The batch candidates a new failing test points at: those that wrote a line its traceback
    ran through (`git blame`), else those whose changes it imports or reads by name. Halving a
    failed batch cost a full check per round. Every failure must point at a candidate, and not
    all of them may be suspects; otherwise [] and the batch is halved as before."""
    failing = new_failures(state, checkout)
    try:
        tree = git(checkout, 'rev-parse', 'HEAD^{tree}')
        record = json.loads((Path(state) / 'full-check' / f'tree-{tree}.json').read_text())
        frames = tracebacks(Path(record['log']).read_text(errors='replace'))
    except (OSError, ValueError, KeyError, TypeError):
        frames = {}

    def contains(commit, rev):
        return subprocess.run(['git', '-C', str(checkout), 'merge-base', '--is-ancestor', commit, rev],
                              capture_output=True).returncode == 0

    def owner(commit):
        """The first candidate whose step brought ``commit``; None for the base's own."""
        if not re.fullmatch(r'[0-9a-f]{40}', commit) or contains(commit, base):
            return None
        return next((task for task, head in steps if contains(commit, head)), None)

    files = (git(checkout, 'ls-files') or '').splitlines()
    index = {}
    for path in files:
        if path.endswith('.py'):
            name = Path(path).stem if Path(path).name != '__init__.py' else Path(path).parent.name
            index.setdefault(name, []).append(path)
    changed, before = {}, base
    for task, head in steps:
        changed[task] = set((git(checkout, 'diff', '--name-only', before, head) or '').splitlines())
        before = head
    suspects = set()
    for test in failing:
        blamed = traceback_blame(checkout, frames.get(test, ()), set(files), owner)
        if blamed:
            suspects |= blamed
            continue
        module = next((part for part in test.split('.') if part.startswith('test')), '')
        reach = set()
        for path in index.get(module, ()):
            reach |= imported_files(checkout, path, index)
        if not reach:
            return []  # a failure no test file explains
        text = ''
        for path in reach:
            try:
                text += (Path(checkout) / path).read_text(errors='replace')
            except OSError:
                pass
        # Imported modules, or a file the test reads by name: 'autowork/SKILL.md' anywhere, or just
        # 'SKILL.md' beside the test (ROOT.joinpath('SKILL.md') in pi-autowork/engine/).
        homes = {'/'.join(Path(path).parent.parts[:2]) + '/' for path in index.get(module, ())}

        def read(path):
            return not path.endswith('.py') and ('/'.join(Path(path).parts[-2:]) in text or (
                Path(path).name in text and any(path.startswith(home) for home in homes)))
        blamed = {task for task, paths in changed.items() if paths & reach or any(read(p) for p in paths)}
        if not blamed:
            return []
        suspects |= blamed
    if not failing or len(suspects) >= len(steps):
        return []
    return [task for task, _ in steps if task in suspects]


def merge_batch_candidates(chain, order, slots, size, skipped):
    """Build the engine's stripped merge chain, counting only candidates that merge."""
    _, parallel_integrate, _ = engine_modules()
    steps = []
    for task in order:
        if len(steps) >= size:
            break
        slot = slots.get(task)
        if not slot or not slot.get('commit'):
            skipped.append(task)
            continue
        try:
            # Only integration persists the dropped proposal and slot evidence.
            parallel_integrate.merge_candidate(chain, slot, git(chain, 'rev-parse', 'HEAD'))
        except parallel_integrate.Hold:
            skipped.append(task)
            continue
        steps.append((task, git(chain, 'rev-parse', 'HEAD')))
    return steps


def batch_gate(state, chain, base, steps, result):
    """The shared review instructions, or None after printing a failed batch gate."""
    if optimistic.enabled() and not main_check.affected_checker(str(chain), main_check.full_check(str(chain))):
        # Optimistic batches only review; main checks the full suite after landing.
        return json.dumps({'note': OPTIMISTIC_NOTE})
    ok, reason = full_suite_gate(state, 'batch', str(chain), base)
    if not ok:
        # Attribute failing tests when possible; otherwise the coordinator halves the batch.
        print(json.dumps(dict(result, outcome='BATCH_GATE_FAILED', reason=reason,
                              suspects=batch_suspects(state, str(chain), base, steps))))
        return None
    return json.dumps({'note': gate_note(state, 'batch', str(chain)),
                       'selection': gate_selection(state, str(chain)),
                       'evidence': review_gate_evidence(state, str(chain))})


def run_batch_reviews(state, session, script, root, steps, gate, result, running, order):
    """Review each step side by side; leave running children visible to the caller's cleanup."""
    limit = max(1, setting('PI_AUTOWORK_REVIEWS', 3))
    pending = list(steps)
    # A stop reaches only reviews already running: start no more, and let those record theirs.
    while (pending and not pi_runtime.STOP) or running:
        while pending and len(running) < limit and not pi_runtime.STOP:
            task, head = pending.pop(0)
            where = root / safe_name(task)
            if git(session, 'worktree', 'add', '--detach', str(where), head) is None:
                result['tasks'].remove(task)  # unreviewed: it integrates on its own
                continue
            child = subprocess.Popen(['bash', script, '--verify', state, task], cwd=where,
                                     env=dict(os.environ, PI_AUTOWORK_BATCH_GATE=gate),
                                     stdout=subprocess.DEVNULL, stderr=sys.stderr)
            running.append((task, where, child))
        if running:  # WNOWAIT leaves reaping to Popen
            os.waitid(os.P_ALL, 0, os.WEXITED | os.WNOWAIT)
        for item in [r for r in running if r[2].poll() is not None]:
            running.remove(item)
            task, where, child = item
            result['passed' if child.returncode == 0 else 'held'].append(task)
            git(session, 'worktree', 'remove', '--force', '--force', str(where))
    for task, _ in pending:  # left by a stop: each integrates on its own
        result['tasks'].remove(task)
    for verdict in ('passed', 'held'):
        result[verdict].sort(key=order.index)


def cleanup_batch(session, root, running):
    """Stop leftover reviews before removing the scratch worktrees they may still be using."""
    for _, _, child in running:
        if child.poll() is None:
            child.kill()
            child.wait()
    for path in [p for p in root.iterdir() if p.is_dir()] if root.exists() else []:
        subprocess.run(['git', '-C', session, 'worktree', 'remove', '--force', '--force', str(path)],
                       capture_output=True)
    shutil.rmtree(root, ignore_errors=True)


def verify_batch(state, session, script, tasks):
    """Gate one merged chain, then review its steps for the engine's later integration."""
    order, slots = batch_order(session, set(tasks))
    size = max(2, setting('PI_AUTOWORK_BATCH', 6))
    drop_dead_scratch(session, review_root())
    # The next merge-train car starts on the previous batch's tip and needs just one candidate.
    on = os.environ.get('PI_AUTOWORK_BATCH_ON') or ''
    base = git(session, 'rev-parse', '--verify', '-q', on + '^{commit}') if on else git(session, 'rev-parse', 'HEAD')
    fewest = 1 if on else 2
    root = Path(tempfile.mkdtemp(prefix=f'aw-b-{os.getpid()}-', dir=review_root()))
    chain = root / 'chain'
    skipped, running = [], []
    result = {'outcome': 'BATCH', 'tasks': [], 'skipped': skipped, 'passed': [], 'held': []}
    try:
        if not base or git(session, 'worktree', 'add', '--detach', str(chain), base) is None:
            print(json.dumps(dict(result, reason=f'the batch chain could not be created in {root}')))
            return 0
        steps = merge_batch_candidates(chain, order, slots, size, skipped)
        result['tasks'] = [t for t, _ in steps]
        if len(steps) < fewest:
            print(json.dumps(dict(result, reason='fewer than two candidates merge together' if fewest == 2
                                  else 'no candidate merges onto the batch ahead')))
            return 0
        if os.environ.get('PI_AUTOWORK_BATCH_TIP'):
            # Publish before the long check, so the next car can start beside it.
            Path(os.environ['PI_AUTOWORK_BATCH_TIP']).write_text(
                json.dumps({'tip': steps[-1][1], 'tasks': result['tasks']}) + '\n')
        os.environ['TMPDIR'] = str(root)
        lease = review_port_lease()  # held until this process exits
        gate = batch_gate(state, chain, base, steps, result)
        if gate is None:
            return 0
        run_batch_reviews(state, session, script, root, steps, gate, result, running, order)
        print(json.dumps(result))
        return 0
    except main_check.Stopped:
        print('pi-autowork: the batch stopped', file=sys.stderr)
        return 1
    finally:
        cleanup_batch(session, root, running)


OPTIMISTIC_NOTE = ('The runner did not run the full test suite before this review (optimistic landing): it lands '
                   'when you pass it, and main\'s full check runs afterwards and reverts it if it broke anything. '
                   'Run the task\'s own checks and the tests nearest its changes yourself before you pass it, but '
                   'not the full suite or whole test directories, even when a Checks entry names them: main\'s full '
                   'check after landing covers those (a review here ran the full suite for six minutes). If the '
                   'repository\'s AGENTS.md names a tool that selects the tests a change affects, use it.')


def gate_inventory_complete(record, tree):
    """Legacy aggregate caches are admissible, but cannot establish an all-green inventory."""
    result = record.get('result')
    return (record.get('tree') == tree and bool(record.get('commit')) and isinstance(result, dict)
            and isinstance(result.get('failures'), list)
            and all(isinstance(f, str) for f in result['failures'])
            and type(result.get('code')) is int
            and type(result.get('timed_out')) is bool
            and type(result.get('resource_skips')) is int
            and (result.get('skips') is None or type(result['skips']) is int))


def gate_result_outcome(record, log, fallback):
    """Prompt outcome from validated inventory and whether its producing log is available."""
    result = record['result']
    named = result['failures']
    baseline, isolated = record.get('baseline_equivalent'), record.get('isolated_rerun')
    classified = (isinstance(baseline, list) and isinstance(isolated, list)
                  and all(isinstance(f, str) for f in baseline + isolated)
                  and set(named) == set(baseline + isolated))
    if record.get('ok') is not True or result['timed_out']:
        return fallback
    if result['code'] == 0 and not named and log and type(result.get('skips')) is int:
        return ('accepted with skipped tests' if result['skips'] or result['resource_skips']
                else 'it passed (all-green recorded result)')
    if result['code'] != 0 and named and classified:
        outcome = 'accepted under exception policy'
        if baseline:
            outcome += '; baseline-equivalent failures: ' + first_ten(baseline)
        if isolated:
            outcome += '; isolated-rerun passes: ' + first_ten(isolated)
        if not log:
            outcome += '; log detail unavailable'
        return outcome
    return fallback


def gate_inventory_reference(result):
    """The producing suite's inventory, not a claim that exception acceptance was all-green."""
    named = result['failures']
    return (f'; original inventory: exit {result["code"]}; failures: '
            + (first_ten(named) if named else 'none recorded')
            + f'; unittest skips: {result.get("skips") if result.get("skips") is not None else "unavailable (unsupported inventory)"}'
            + f'; resource-gate skips: {result["resource_skips"]}')


def build_gate_note(command, tree, outcome, reference, selection):
    """Render review instructions without reading or validating receipts."""
    if isinstance(selection, dict) and selection.get('full') is False:
        return (f' The runner checked affected modules only (`{command}`) for tree `{tree}`: {outcome}. '
                f'{reference}. This is not full-suite qualification: main runs the full suite after '
                'landing and attributes regressions to the landed task. Read the producing evidence '
                'instead of repeating the selection. Run task-specific checks outside that selection, '
                'but do not expand to the full suite or whole test directories.')
    return GATE.format(command=command, tree=tree, outcome=outcome, evidence=reference)


def gate_note(state, task, checkout):
    """Explain the runner's recorded gate instead of asking the reviewer to repeat it."""
    command = main_check.full_check(checkout)
    if not command:
        return ''
    tree = git(checkout, 'rev-parse', 'HEAD^{tree}')
    cache = Path(state) / 'full-check' / f'tree-{tree}.json'
    outcome, reference = 'result detail unavailable: no matching gate record', 'Producing evidence unavailable'
    selection = None
    try:
        record = json.loads(cache.read_text())
        if not main_check.receipt_command_matches(record, command) or record.get('tree', tree) != tree:
            raise ValueError('mismatched gate identity')
        outcome = ('accepted result with unavailable detail' if record.get('ok') is True else
                   'gate rejected the tree: ' + str(record.get('reason') or 'reason unavailable'))
        command = record.get('command') or command
        reference = f'Gate record: {cache}; producer task: {record.get("task") or "unavailable"}'
        selection = record.get('selection')
        if isinstance(selection, dict):
            scope = 'full suite' if selection.get('full') else 'affected modules only'
            reference += f'; checked selection: {scope}: ' + ', '.join(selection.get('tests') or [])
        if not gate_inventory_complete(record, tree):
            reference += '; original inventory and log detail unavailable (legacy or incomplete metadata)'
        else:
            reference += f'; producer commit: {record["commit"]}'
            log = producing_gate_log(state, record)
            reference += f'; producing log: {log}' if log else '; producing log unavailable (missing, unreadable or mismatched)'
            outcome = gate_result_outcome(record, log, outcome)
            reference += gate_inventory_reference(record['result'])
    except (OSError, ValueError, AttributeError, TypeError):
        pass
    return build_gate_note(command, tree, outcome, reference, selection)


def review(state, task, checkout, head_before, gate=''):
    provisioned = worker_tmp(checkout, task)
    cache = repository_cache(checkout)
    # Set or cleared: a value inherited from the caller names another task's files.
    for name, value in (('AUTOWORK_WORKER_TMPDIR', provisioned), ('AUTOWORK_CACHE', cache)):
        if value:
            os.environ[name] = str(value)
        else:
            os.environ.pop(name, None)
    result = pi_runtime.job(pi_runtime.Settings(state), 'verify', task, checkout,
                            REVIEW.format(task=task, checkout=checkout)
                            + gate
                            + (PROVISIONED.format(path=provisioned) if provisioned else '')
                            + (CACHE.format(path=cache) if cache else '') + (
                                LIVE.format(items='; '.join(live)) if (live := pending_live(checkout, task)) else NO_LIVE)
                            + changelog_note(checkout, task),
                            f'pi-autowork-verify-{safe_name(task)}-{datetime.now():%Y%m%d%H%M%S}',
                            f"{(limit := setting('PI_AUTOWORK_VERIFY_TIMEOUT', 1800, float)):g}",
                            ['--tools', 'read,bash,grep,find,ls'])
    if dirty(checkout) or git(checkout, 'rev-parse', 'HEAD') != head_before:
        # Checked first: its verdict is void, so it neither clears nor records findings or a marker.
        # The engine owns this disposable integration worktree: it keeps the changes as a
        # patch for diagnosis and resets it before the next integration.
        print('AUTOWORK_HOLD_REASON: the reviewer changed the checkout, which a review must not do', flush=True)
        print('pi-autowork: the reviewer changed the checkout; verification fails', file=sys.stderr)
        return 1
    # Markdown around the line (bold, code) is the reviewer's formatting, not part of the verdict.
    line = next((l for l in (raw.strip().strip('*`_').strip() for raw in reversed(result['text'].splitlines()))
                 if l.startswith('PI_AUTOWORK_VERIFY:')), '')
    match = VERDICT.match(line)
    verdict = (match[1] or match[2]) if match else ''
    marker = environment_marker(state, task)
    missing = ENVIRONMENT.match(line)
    if missing and verdict == 'fail':
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({'missing': ' '.join((missing.group(1) or 'unnamed').split())[:300],
                                      'commit': head_before}))
    else:
        marker.unlink(missing_ok=True)
    if verdict == 'fail':
        # Preserve the failure line in the engine's hold reason, not just a generic validation
        # failure: a changed reviewer only gets another look while its verdict changes.
        print(f'AUTOWORK_HOLD_REASON: {line}', flush=True)
    if verdict == 'fail' and not missing:  # checked and found wanting: what the maintainer acts on
        record_findings(state, task, ' '.join(line.split()), head_before)
    elif verdict == 'pass':
        findings_path(state, task).unlink(missing_ok=True)
    if result['ok'] and verdict == 'pass':
        return 0
    if not verdict:
        # Why there is no verdict, for the hold: a review that ran out of time is reviewed again with
        # a longer limit (the engine's timeout cause), not reimplemented by a fresh worker.
        why = result.get('why') or ('' if result['ok'] else 'failed')
        print('AUTOWORK_HOLD_REASON: ' + (f'the review ran out of time after {limit:g} s' if why == 'timeout'
                                          else f'the reviewer did not finish ({why})' if why
                                          else 'the reviewer gave no verdict'), flush=True)
    print(f'pi-autowork: review of {task}: {verdict or "no verdict"} {line[:200]}', file=sys.stderr)
    return 1


def main(argv):
    push_guard()  # the engine removes GIT_* from workers' environments
    # A stop reaches the whole process group, Pi included: record it and let Pi exit.
    signal.signal(signal.SIGINT, pi_runtime._stop)
    signal.signal(signal.SIGTERM, pi_runtime._stop)
    if argv[:1] == ['--verify-batch'] and len(argv) >= 5:
        state, session, script, *tasks = argv[1:]
        return verify_batch(state, session, script, tasks)
    if argv[:1] == ['--worker'] and len(argv) >= 5:
        state, worktree, prompt_file, report = argv[1:5]
        limit = argv[5] if len(argv) > 5 else f"{setting('PI_AUTOWORK_TASK_TIMEOUT', 5400, float):g}"
        return worker(state, worktree, prompt_file, report, limit)
    if argv[:1] == ['--verify'] and len(argv) == 3:
        return verify(argv[1], argv[2])
    print(__doc__, file=sys.stderr)
    return 2
