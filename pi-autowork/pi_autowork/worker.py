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

from . import pi_runtime, workspaces
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
          'file copy. End with exactly one line: PI_AUTOWORK_VERIFY: pass or '
          'PI_AUTOWORK_VERIFY: fail, then the reason.')
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
    result = pi_runtime.job(pi_runtime.Settings(state), 'worker', task, worktree,
                            f'Follow the instructions in this file exactly: @{prompt_file}',
                            f'pi-autowork-{safe_name(task)}-{attempt}', limit, [f'@{prompt_file}'])
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


def worker_tmp(checkout, task):
    """The finished worker's $TMPDIR (slot data), where it may have provisioned a toolchain the
    task's checks need; the reviewer gets its own $TMPDIR and would not find it otherwise."""
    try:
        common = Path(git(checkout, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
        slot = json.loads((common / 'autowork-execution' / 'slots' / f'{task}.json').read_text())
        attempt = slot.get('data_attempt', slot['attempt'])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    path = common / 'autowork-execution' / 'slot-data' / task / f'attempt-{attempt}' / 'tmp'
    return path if path.is_dir() and any(path.iterdir()) else None


def verify(state, task):
    checkout = os.getcwd()
    link_ignored(checkout)
    validate = os.environ.get('PI_AUTOWORK_VALIDATE')
    if validate and subprocess.run(['bash', '-c', validate]).returncode:
        print(f'pi-autowork: PI_AUTOWORK_VALIDATE failed for {task}', file=sys.stderr)
        return 1
    if os.environ.get('PI_AUTOWORK_REVIEW', '1') == '0':
        return 0
    head_before = git(checkout, 'rev-parse', 'HEAD')
    # Its own scratch on disk, removed afterwards: reviewers copied whole repositories into
    # RAM-backed /tmp and left them (39 GB on one host).
    scratch = Path(state) / 'review-tmp' / f'{safe_name(task)}-{os.getpid()}'
    scratch.mkdir(parents=True, exist_ok=True)
    os.environ['TMPDIR'] = str(scratch)
    try:
        return review(state, task, checkout, head_before)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        subprocess.run(['git', '-C', checkout, 'worktree', 'prune'], capture_output=True)


def review(state, task, checkout, head_before):
    provisioned = worker_tmp(checkout, task)
    if provisioned:
        os.environ['AUTOWORK_WORKER_TMPDIR'] = str(provisioned)
    result = pi_runtime.job(pi_runtime.Settings(state), 'verify', task, checkout,
                            REVIEW.format(task=task, checkout=checkout)
                            + (PROVISIONED.format(path=provisioned) if provisioned else '') + (
                                LIVE.format(items='; '.join(live)) if (live := pending_live(checkout, task)) else NO_LIVE),
                            f'pi-autowork-verify-{safe_name(task)}-{datetime.now():%Y%m%d%H%M%S}',
                            os.environ.get('PI_AUTOWORK_VERIFY_TIMEOUT', '1800'),
                            ['--tools', 'read,bash,grep,find,ls'])
    line = next((l for l in result['text'].splitlines() if l.startswith('PI_AUTOWORK_VERIFY:')), '')
    verdict = (re.match(r'^PI_AUTOWORK_VERIFY: (pass|fail)', line) or [None, ''])[1]
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
    if argv[0] == '--worker':
        state, worktree, prompt_file, report = argv[1:5]
        limit = argv[5] if len(argv) > 5 else os.environ.get('PI_AUTOWORK_TASK_TIMEOUT', '5400')
        return worker(state, worktree, prompt_file, report, limit)
    return verify(argv[1], argv[2])
