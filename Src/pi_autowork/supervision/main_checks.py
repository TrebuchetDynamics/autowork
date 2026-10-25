"""Main-check supervision implementations; Coordinator owns policy, state and phase dispatch."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

from .. import main_check, optimistic, post_merge_barrier
from ..common import LOG
from ..layout import LAYOUT


def remember_reused_main_green(owner, revision, finished, *, git):
    """Keep green transitions not backed by a new main-check evidence bundle."""
    path = owner.state / 'main-green-history.json'
    history = main_check.slot_status(path)
    history[revision] = finished
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(history) + '\n')
    temporary.replace(path)


def check_main(owner, *, git):
    """Main's declared full offline check (PI_AUTOWORK_MAIN_CHECK), in the background, once
    per main revision, when the host has room and nothing is being verified (TOOLSET-176-98).
    A red result gives the DOCS-MAINTAINER a trigger to add one repair task."""
    cmd = main_check.command(repo=owner.repo)
    if not cmd or owner.stop:
        return
    record = main_check.read(owner.state)
    pid, started = owner.check_main_reap(record)
    record = retry_repairs(owner, record)
    if record.get('state') == 'running':
        if main_check.exit_code(owner.state) is not None or not main_check.alive(pid, started):
            owner.finish_main_check(record)
        return
    if record.get('pid') is not None:  # receipt consumed just before bash exited: reap next cycle
        return
    if owner.check_main_revert_pending(record):
        return
    rev = git(owner.repo, 'rev-parse', owner.base)
    same_policy = (record.get('policy') == post_merge_barrier.POLICY
                   and record.get('command') == cmd and record.get('timeout') == post_merge_barrier.timeout()) \
        if post_merge_barrier.enabled() else not record.get('policy')
    request = owner.state / 'requests/recheck-main'
    retry = False
    if post_merge_barrier.enabled() and request.exists():
        try:
            retry = request.read_text().strip() == rev
        except OSError:
            return
        if not retry:
            request.unlink(missing_ok=True)  # stale request; current main still needs its own check
    if not rev or (rev == record.get('rev') and same_policy and not retry):
        return
    if owner.check_main_reuse_result(record, rev, cmd):
        return
    if owner.check_main_wait(record):
        return
    owner.check_main_start(record, rev, cmd)
    if retry and main_check.read(owner.state).get('state') == 'running':
        request.unlink(missing_ok=True)


def retry_repairs(owner, record):
    """Keep deferred red incidents in the existing receipt across checks and reloads."""
    pending = list(record.get('repair_pending') or [])
    if record.get('policy') == post_merge_barrier.POLICY and record.get('state') == 'red':
        if not any(item['rev'] == record['rev'] for item in pending):
            pending.append({key: record[key] for key in ('rev', 'command', 'timeout', 'failures', 'evidence') if key in record})
    if not pending:
        return record
    remaining = [item for item in pending if not owner.post_merge_repair(item)]
    return main_check.write(owner.state, dict(record, repair_pending=remaining))


def check_main_reap(owner, record, *, git):
    """Reap an adopted child without waiting on a reused PID; retain its observed identity."""
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
            main_check.write(owner.state, record)
    return pid, started


def check_main_revert_pending(owner, record, *, git):
    """Retry an optimistic regression revert once the session is free."""
    if post_merge_barrier.enabled():
        return False
    if record.get('state') == 'red' and record.get('revert_pending') and optimistic.enabled():
        # A review was running when main went red: revert once the session is free.
        try:
            log_text = (owner.state / 'main-check.log').read_text(errors='replace')
        except OSError:
            log_text = ''
        if owner.revert_regression(record['rev'], record.get('green'), record.get('failures') or [], log_text):
            return True
        if not owner.session_busy():
            main_check.write(owner.state, dict(record, revert_pending=False))  # nothing to revert: repair task
    return False


def check_main_reuse_result(owner, record, rev, cmd, *, git, planning_path):
    """Carry green across planning-only changes or reuse a full check of this exact tree."""
    if post_merge_barrier.enabled() or record.get('policy') == post_merge_barrier.POLICY:
        return False  # bounded verdicts are never reusable full-suite receipts
    if record.get('state') == 'green' and record.get('rev'):
        # The runner's own questions and planning commits moved main: a full check for each
        # (8 of 39 in a day) took a host check slot that a waiting review needed.
        changed = (git(owner.repo, 'diff', '--name-only', record['rev'], rev) or '').split()
        if changed and all(planning_path(p) for p in changed):
            owner.remember_reused_main_green(rev, record.get('finished') or time.time())
            main_check.write(owner.state, dict(record, rev=rev, green=rev))
            return True
    # A batch or merge-train check that passed on exactly main's tree already ran this check:
    # record main green from it instead of running the suite a second time (TOOLSET-336-3c).
    if passed := owner.passed_on_tree(rev, cmd):
        finished = time.time()
        owner.remember_reused_main_green(rev, finished)
        main_check.write(owner.state, dict(state='green', rev=rev, green=rev, finished=finished,
                                          checked_rev=rev, from_receipt=passed, flaky=[],
                                          flaky_history=record.get('flaky_history') or {},
                                          repair_pending=record.get('repair_pending') or []))
        LOG.say(f'Main is green at {rev[:7]}: the full check already passed on its tree ({passed})')
        return True
    return False


def check_main_wait(owner, record, *, git):
    """Yield to batches, reviews and host load within the existing bounded wait."""
    # A batch (or the merge train) is checking main plus its candidates right now: it covers
    # main's code and lands as main, so main's own check waits for it rather than running a
    # second full suite beside it, up to twice MAIN_CHECK_WAIT since the last main check.
    # A running or aborted check's record keeps the last finish as last_finished: without it a
    # restart read 'never checked' and ran main's suite beside the batch anyway.
    last = record.get('finished') or record.get('last_finished') or 0
    if owner.batch_running() and time.time() - float(last) < 2 * owner.MAIN_CHECK_WAIT:
        return True
    # It waits for room at most MAIN_CHECK_WAIT: with eight workers and batches a review or a
    # loaded host was nearly always there, and main went unchecked for hours while it was red.
    if time.time() - float(record.get('finished') or 0) < owner.MAIN_CHECK_WAIT:
        try:
            if os.getloadavg()[0] >= (os.cpu_count() or 1):
                return True
        except OSError:
            pass
        if any(t.get('state') == 'integrating' for t in owner.tasks()):
            return True
    return False


def check_main_start(owner, record, rev, cmd, *, git):
    """Launch the isolated background check and persist the receipt used after reloads."""
    barrier = post_merge_barrier.enabled()
    path = owner.scratch_checkout('main-check', rev)
    if not path:
        return
    tmp = tempfile.mkdtemp(prefix='aw-main-')  # honor the runner's short, disk-backed TMPDIR
    done, reruns = owner.state / 'main-check.exit', owner.state / 'main-check-reruns.json'
    done.unlink(missing_ok=True)
    reruns.unlink(missing_ok=True)
    reruns.with_suffix('.log').unlink(missing_ok=True)
    retry = shlex.join([sys.executable, str(LAYOUT.entrypoint('main_check')),
                        str(owner.state / 'main-check.log'), path, str(reruns), rev])
    # Finish retries before publishing the receipt: reloads can adopt the job,
    # and finish_main_check can then safely remove the shared scratch checkout.
    progress = owner.state / 'main-check-slot.json'
    progress.unlink(missing_ok=True)
    limit = post_merge_barrier.timeout() if barrier else os.environ.get('PI_AUTOWORK_VALIDATE_TIMEOUT') or '3600'
    run = shlex.join([sys.executable, str(LAYOUT.entrypoint('main_check')), '--run', cmd, str(limit), str(progress)])
    retry_script = '' if barrier else f'if [ "$result" -ne 0 ]; then {retry}; fi\n'
    script = f'{run}\nresult=$?\n{retry_script}echo "$result" > {shlex.quote(str(done))}'
    metadata, check_env = dict(repair_pending=record.get('repair_pending') or []), {}
    if barrier:
        verdict = post_merge_barrier.verdict_path(owner.state).resolve()
        verdict.unlink(missing_ok=True)
        run_id = uuid.uuid4().hex
        metadata.update(policy=post_merge_barrier.POLICY, command=cmd, timeout=limit,
                        run_id=run_id, verdict_path=str(verdict))
        check_env = dict(AUTOWORK_POST_MERGE_REVISION=rev, AUTOWORK_POST_MERGE_RUN_ID=run_id,
                         AUTOWORK_POST_MERGE_VERDICT=str(verdict),
                         AUTOWORK_POST_MERGE_BASE=record.get('green') or rev)
    lease = owner.main_check_port_lease()
    ports = {'AUTOWORK_PORT_BASE': str(lease[0])} if lease else {}
    with open(owner.state / 'main-check.log', 'w') as log:
        child = subprocess.Popen(['bash', '-c', script], cwd=path,
                                 env=owner.job_environment(TMPDIR=tmp, **ports, **check_env),
                                 stdout=log, stderr=subprocess.STDOUT, pass_fds=[lease[1]] if lease else (),
                                 stdin=subprocess.DEVNULL, start_new_session=True)
    if lease:
        os.close(lease[1])  # the check keeps the block for as long as it runs
    main_check.write(owner.state, dict(state='running', rev=rev, pid=child.pid,
                                      start_time=main_check.start_time(child.pid), started=time.time(), path=path,
                                      tmp=tmp, slot_status=str(progress), green=record.get('green'), failures=record.get('failures'),
                                      red_since=record.get('red_since'), gated=record.get('gated'),
                                      crashed=record.get('crashed'), flaky_history=record.get('flaky_history') or {},
                                      last_finished=record.get('finished') or record.get('last_finished'), **metadata))
    LOG.say(f'Checking main at {rev[:7]} in the background: {cmd}')


def passed_on_tree(owner, rev, cmd, *, git):
    """The task or batch whose passing full check (the same command) ran on exactly ``rev``'s
    tree, from its tree receipt in full-check/, or None."""
    tree = git(owner.repo, 'rev-parse', f'{rev}^{{tree}}')
    if not tree:
        return None
    try:
        receipt = json.loads((owner.state / 'full-check' / f'tree-{tree}.json').read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(receipt, dict) or receipt.get('ok') is not True or receipt.get('tree') != tree \
            or not main_check.receipt_command_matches(receipt, cmd):
        return None
    selection = receipt.get('selection')
    if selection is not None and (not isinstance(selection, dict) or selection.get('full') is not True):
        return None  # Landing a tested subset never marks main or its base full-suite green.
    return str(receipt.get('task') or receipt.get('commit') or 'a full check')


def finish_main_check(owner, record, *, git):
    """Record a finished (or aborted) main check and clean its checkout up."""
    code = main_check.exit_code(owner.state)
    path, tmp = record.get('path') or '', record.get('tmp') or ''
    if path and Path(path).name.startswith('pi-scratch-main-check'):
        git(owner.repo, 'worktree', 'remove', '--force', path)
    if tmp and Path(tmp).name.startswith('aw-main-'):
        shutil.rmtree(tmp, ignore_errors=True)
    green = record.get('green')
    history = record.get('flaky_history') or {}
    # The receipt can precede bash's exit. Retain its identity until a later cycle reaps it.
    child = {k: record[k] for k in ('pid', 'start_time') if k in record}
    if code is None:  # the runner stopped under it: check this revision again
        main_check.write(owner.state, dict(state='aborted', rev='', green=green, failures=record.get('failures'),
                                          red_since=record.get('red_since'), flaky_history=history,
                                          last_finished=record.get('last_finished'),
                                          repair_pending=record.get('repair_pending') or [], **child))
        return
    try:
        log_text = (owner.state / 'main-check.log').read_text(errors='replace')
    except OSError:
        log_text = ''
    owner.finish_main_check_result(record, code, log_text, child)


def finish_main_check_failures(owner, record, code, log_text, *, git):
    """Separate persistent failures from completed isolated reruns and remember flaky revisions."""
    rev = record.get('rev', '')
    history = record.get('flaky_history') or {}
    failures = named = main_check.failures(log_text, limit=None) if code else []
    flaky, incomplete = [], False
    if code:
        incomplete = code != 1  # signals and shell errors are not ordinary unittest failures
        try:
            reruns = json.loads((owner.state / 'main-check-reruns.json').read_text())
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
    return failures, named, flaky, incomplete, history


def finish_main_check_result(owner, record, code, log_text, child, *, git):
    """Publish the verdict, then trigger the same repair, revert or green-only push."""
    rev, green = record.get('rev', ''), record.get('green')

    def finished(value):
        value.setdefault('result_class', main_check.result_class(log_text, code))
        value.setdefault('repair_pending', record.get('repair_pending') or [])
        common = git(owner.repo, 'rev-parse', '--path-format=absolute', '--git-common-dir')
        if common and rev and code is not None:
            main_check.publish_evidence(owner.state, common, rev, value)
        return main_check.write(owner.state, value)

    if record.get('policy') == post_merge_barrier.POLICY:
        value = finished(post_merge_barrier.result(owner.state, record, code, child))
        retry_repairs(owner, value)
        LOG.say(f'Post-merge check at {rev[:12]}: {value["state"]}')
        return
    if post_merge_barrier.enabled():
        # An asynchronous job adopted while enabling the barrier is not barrier evidence
        # and must not execute the old policy's automatic regression revert.
        main_check.write(owner.state, dict(state='aborted', rev='', green=green,
                                          repair_pending=record.get('repair_pending') or [], **child))
        return
    failures, named, flaky, incomplete, history = owner.finish_main_check_failures(record, code, log_text)
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
        owner.maintain(main_only=True)
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
            owner.maintain(main_only=True)
        if optimistic.enabled():
            owner.push()  # optimistic landing publishes only green revisions: this one now
        return
    if optimistic.enabled() and owner.revert_regression(rev, green, failures, log_text):
        return  # reverted: main is checked again on the reverted revision
    commits = (git(owner.repo, 'log', '--format=%h %s', '-20', f'{green}..{rev}' if green else rev) or '').splitlines()
    red_since = record.get('red_since') if record.get('failures') else rev
    finished(dict(state='red', rev=rev, green=green, failures=failures, commits=commits,
                                      red_since=red_since or rev, finished=time.time(),
                                      flaky=flaky, flaky_history=history,
                                      revert_pending=optimistic.enabled(), **child))
    LOG.say(f'Main is red at {rev[:7]}: {len(failures)} failing ({", ".join(failures[:3])}'
            + (f', +{len(failures) - 3} more' if len(failures) > 3 else '') + ')')
    owner.maintain(main_only=True)  # one repair task, now: red main hides every later regression
