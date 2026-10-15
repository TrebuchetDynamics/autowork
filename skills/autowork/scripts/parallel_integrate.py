"""Serialized, validated local integration. Worker reports are evidence, not acceptance."""
import math
import json
import os
from pathlib import Path
import subprocess
import re
import sys


import parallel_dispatch as dispatch
import parallel_plan as plan
import parallel_state as state
import task_execution as execution


def git(repo, *argv):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    result = subprocess.run(['git', '-C', str(repo), *argv], env=env,
                            capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise ValueError('git ' + argv[0] + ' failed: ' + result.stderr.strip())
    return result.stdout if '-z' in argv else result.stdout.strip()


def changed(repo, baseline, commit):
    # Disable rename folding so both the deleted source and new destination are checked.
    value = git(repo, 'diff', '--name-only', '--no-renames', '-z', baseline + '..' + commit)
    return value.rstrip('\0').split('\0') if value else []


def context(repo, owner_pid):
    repo = Path(execution.git(Path(repo).resolve(), 'rev-parse', '--show-toplevel')).resolve()
    common = state.common_dir(repo)
    owner = state.require_owner(common, owner_pid)
    if owner['workspace'] != str(repo):
        raise ValueError('integration must target the coordinator canonical checkout')
    return repo, common


def slot_for(common, task):
    return next((s for s in state.slots(common) if s['task_id'] == task), None)


def hold(common, slot, reason, **updates):
    slot = state.change(common, slot, 'held', dict(updates, reason=reason))
    return {'outcome': 'HELD', 'task': slot['task_id'], 'reason': reason}


def verify(repo, common, slot, contracts):
    task = contracts.get(slot['task_id'])
    if task is None:
        raise ValueError('task contract is no longer eligible')
    if state.worker_live(slot):
        raise ValueError('worker still running')
    state.workspace(common, slot['worktree'], slot['branch'], slot['baseline'])
    expected = 'autowork/' + slot['task_id'] + ('-r2' if slot['attempt'] == 2 else '')
    if slot['branch'] != expected:
        raise ValueError('unexpected worker branch')
    commit = slot.get('commit', '')
    try:
        lineage = git(repo, 'merge-base', slot['baseline'], commit) == slot['baseline'] if commit else False
    except ValueError:
        lineage = False
    if (not commit or commit == slot['baseline'] or git(repo, 'rev-parse', '--verify', commit + '^{commit}') != commit
            or git(repo, 'rev-parse', 'refs/heads/' + slot['branch']) != commit or not lineage):
        raise ValueError('reported commit/branch/lineage mismatch')
    report = execution.read(dispatch.data_dir(common, slot) / 'report.json')
    files = changed(repo, slot['baseline'], commit)
    if (not isinstance(report, dict) or report.get('task') != slot['task_id']
            or report.get('commit') != commit or not isinstance(report.get('changed_files'), list)
            or not all(isinstance(p, str) for p in report['changed_files'])
            or sorted(report['changed_files']) != sorted(files)
            or report.get('blockers') != [] or not isinstance(report.get('checks'), list)
            or any(not isinstance(c, dict) or c.get('result') != 'pass' for c in report['checks'])):
        raise ValueError('report.json does not match worker commit/files or reports failure')
    verify_scope(repo, common, slot, contracts, files)
    return files, report


def verify_scope(repo, common, slot, contracts, files):
    task = contracts[slot['task_id']]
    others: list[list[str]] = [list(dispatch.COORDINATOR_FILES)]
    for other in state.slots(common):
        if other['task_id'] == slot['task_id'] or other['state'] in ('released', 'closed'):
            continue
        if other.get('commit'):
            others.append(changed(repo, other['baseline'], other['commit']))
        else:
            others.append(plan.paths(contracts.get(other['task_id'], {}).get('fields', {}).get('Touches', '')))
    overlap = plan.overlap(files, plan.paths(task['fields'].get('Touches', '')), others)
    if overlap['outside'] or overlap['conflicts']:
        raise ValueError('changed files violate Touches or coordinator/other-slot ownership: ' + str(overlap))


def require_no_writers(repo):
    workers = execution.external_workers(repo)
    blocking = execution.blocking_workers(workers, repo)
    common = state.common_dir(repo)
    pool = state.slots(common)
    for worker in workers:
        if worker in blocking or worker['active'] is False:
            continue
        # Only a birth-identity-matched live pool leader (or its still-owned
        # process group) in that slot's isolated checkout is exempt. An unknown
        # agent in a sibling worktree is not evidence of pool membership.
        attributed = False
        for slot in pool:
            leader = slot.get('worker')
            if (not leader or execution.identity(leader['pid']) != leader
                    or slot['state'] not in ('dispatched', 'running')
                    or not worker['workspaces'] or set(worker['workspaces']) != {slot['worktree']}):
                continue
            try:
                fields = Path(f'/proc/{worker["pid"]}/stat').read_text().rsplit(')', 1)[1].split()
                same_group = int(fields[2]) == leader['pid']
            except (OSError, ValueError, IndexError):
                same_group = False
            found = {k: worker[k] for k in ('pid', 'start_ticks', 'boot_id')}
            if execution.identity(worker['pid']) == found and (found == leader or same_group):
                attributed = True
                break
        if not attributed:
            blocking.append(worker)
    if blocking:
        raise ValueError('live or unknown external writer/session; preserve canonical checkout')


def integration_worktree(repo, common, baseline):
    path = execution.safe_path(repo.parent / (repo.name + '-autowork-integration'))
    if path.exists():
        if not dispatch.created_by_autowork(common, path, '(detached)'):
            raise ValueError('integration worktree was not created by this coordinator')
        if state.common_dir(path) != common or git(path, 'rev-parse', '--show-toplevel') != str(path):
            raise ValueError('integration worktree identity changed')
        if git(path, 'status', '--porcelain', '--untracked-files=all'):
            raise ValueError('integration worktree has changes; preserve for diagnosis')
        if git(path, 'rev-parse', '--abbrev-ref', 'HEAD') != 'HEAD':
            raise ValueError('integration worktree is no longer detached')
        git(path, 'checkout', '--detach', baseline)
    else:
        git(repo, 'worktree', 'add', '--detach', str(path), baseline)
        state.event(common, 'worktree_created', worktree=str(path), branch='(detached)', baseline=baseline)
    return path


def integrate(repo, owner_pid, task, argv, timeout):
    if not argv or timeout is None or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('--integrate requires --run argv and a positive finite --timeout')
    repo, common = context(repo, owner_pid)
    # Separate from writer.lock: validation never holds the shared state lock.
    with execution.lock(common / 'integration.lock'):
        with execution.lock(common / 'writer.lock'):
            state.require_owner(common, owner_pid)
            slot = slot_for(common, task)
            if not slot or slot['state'] not in ('reported', 'integrating'):
                raise ValueError('integration requires a reported or abandoned integrating slot')
            contracts = {t['id']: t for t in dispatch.contracts(repo)}
            reported = {s['task_id'] for s in state.slots(common) if s['state'] in ('reported', 'integrating')}
            first = next((t for t in contracts if t in reported), None)
            if first != task:
                raise ValueError('integrate the highest-priority reported task first')
            try:
                require_no_writers(repo)
                files, report = verify(repo, common, slot, contracts)
                if slot['state'] == 'integrating':
                    recovered = recover_integration(repo, common, slot, contracts)
                    if recovered:
                        return recovered
            except (ValueError, OSError) as exc:
                return hold(common, slot, str(exc))
            if slot['state'] == 'reported':
                slot = state.change(common, slot, 'integrating', {'report': report})
        check = None
        def save_receipt(path, value):
            nonlocal slot
            with execution.lock(common / 'writer.lock'):
                state.require_owner(common, owner_pid)
                execution.save(path, value)
                slot = state.write_slot(common, dict(slot, checks=value), slot)

        try:
            for attempt in range(2):
                with execution.lock(common / 'writer.lock'):
                    state.require_owner(common, owner_pid)
                    require_no_writers(repo)
                    baseline = git(repo, 'rev-parse', 'HEAD')
                    if git(repo, 'merge-base', baseline, slot['commit']) == slot['commit']:
                        raise ValueError('worker commit already in canonical HEAD; no fresh two-parent integration')
                    canonical_branch = git(repo, 'symbolic-ref', 'HEAD')
                    root = integration_worktree(repo, common, baseline)
                    try:
                        git(root, 'merge', '--no-ff', '--no-edit', slot['commit'])
                    except ValueError:
                        git(root, 'merge', '--abort')
                        raise ValueError('merge conflict; worker and canonical checkout preserved')
                    merge = git(root, 'rev-parse', 'HEAD')
                    if git(repo, 'rev-list', '--parents', '-n', '1', merge).split()[1:] != [baseline, slot['commit']]:
                        raise ValueError('integration candidate must have canonical and worker parents')
                    files = changed(repo, baseline, merge)
                    verify_scope(repo, common, slot, contracts, files)
                    run_id = execution.uuid.uuid4().hex
                    integration = {'commit': merge, 'baseline': baseline, 'changed_files': files,
                                   'check_receipt': str(common / (run_id + '.json')),
                                   'task_contract': contracts[task]['contract'], 'canonical_branch': canonical_branch}
                    # Durable intent precedes validation and FF. An abandoned helper
                    # can only recover this exact candidate, never infer a landing.
                    slot = state.write_slot(common, dict(slot, integration=integration, checks=None), slot)
                inputs = {p: execution.digest(root / p) for p in ('TODO.md', 'goals.json')}
                check = execution.bounded_command(argv, root, common, task, timeout, inputs,
                            receipt_context={'integration_commit': merge}, receipt_writer=save_receipt, run_id=run_id)
                if (check['outcome'] != 'EXECUTED' or git(root, 'rev-parse', 'HEAD') != merge
                        or git(root, 'status', '--porcelain', '--untracked-files=all')):
                    raise ValueError('integration validation failed or changed the integration tree')
                with execution.lock(common / 'writer.lock'):
                    state.require_owner(common, owner_pid)
                    # Re-read report, refs, scopes and source contracts after arbitrary validation.
                    fresh_contracts = {t['id']: t for t in dispatch.contracts(repo)}
                    verify(repo, common, slot, fresh_contracts)
                    verify_scope(repo, common, slot, fresh_contracts, changed(repo, baseline, merge))
                    if fresh_contracts[task]['contract'] != contracts[task]['contract']:
                        raise ValueError('task contract changed during validation')
                    require_no_writers(repo)
                    if git(repo, 'symbolic-ref', 'HEAD') != canonical_branch:
                        raise ValueError('canonical branch changed during validation')
                    if git(repo, 'rev-parse', 'HEAD') != baseline:
                        state.event(common, 'integration_head_moved', task_id=task, attempt=attempt + 1)
                        if attempt == 0:
                            continue
                        raise ValueError('canonical HEAD moved twice; fresh integration required')
                    # This is the only canonical history-changing command. Git protects dirty files.
                    git(repo, 'merge', '--ff-only', merge)
                    if git(repo, 'rev-parse', 'HEAD') != merge:
                        raise ValueError('canonical fast-forward readback mismatch')
                    state.change(common, slot, 'integrated', {'integration': integration, 'checks': check})
                    return {'outcome': 'INTEGRATED', 'task': task, 'integration': integration}
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            with execution.lock(common / 'writer.lock'):
                state.require_owner(common, owner_pid)
                return hold(common, slot, str(exc), **({'checks': check} if check is not None else {}))


def validated_receipt(repo, common, slot):
    info, checks = slot.get('integration') or {}, slot.get('checks') or {}
    receipt_path = Path(info.get('check_receipt', ''))
    if receipt_path.parent != common or receipt_path.suffix != '.json':
        raise ValueError('validation receipt must be in repository execution state')
    saved = execution.read(receipt_path)
    if (saved != checks or checks.get('outcome') != 'EXECUTED'
            or checks.get('context', {}).get('integration_commit') != info.get('commit')
            or checks.get('command_receipt', {}).get('exit_code') != 0
            or checks['command_receipt'].get('task_id') != slot['task_id']
            or checks['command_receipt'].get('receipt') != str(receipt_path)
            or checks['command_receipt'].get('inputs_match') is not True
            or git(repo, 'merge-base', info['commit'], 'HEAD') != info['commit']
            or git(repo, 'rev-list', '--parents', '-n', '1', info['commit']).split()[1:]
               != [info['baseline'], slot['commit']]):
        raise ValueError('missing, failed, stale or mismatched integration validation')
    return info, checks


def recover_integration(repo, common, slot, contracts):
    """Called only under integration.lock: no cooperating validation is alive.

    Before FF, require exact baseline and an unmodified isolated candidate and
    rerun validation. After FF, require durable passing evidence for that exact
    landed merge. Missing or contradictory evidence is held, never adopted.
    """
    info = slot.get('integration') or {}
    if (not info.get('commit') or not info.get('baseline')
            or info.get('task_contract') != contracts[slot['task_id']]['contract']
            or info.get('canonical_branch') != git(repo, 'symbolic-ref', 'HEAD')
            or git(repo, 'rev-list', '--parents', '-n', '1', info['commit']).split()[1:]
               != [info['baseline'], slot['commit']]):
        raise ValueError('abandoned integration lacks exact candidate/contract/branch evidence')
    files = changed(repo, info['baseline'], info['commit'])
    verify_scope(repo, common, slot, contracts, files)
    if files != info.get('changed_files'):
        raise ValueError('abandoned integration delta does not match intent')
    root = execution.safe_path(repo.parent / (repo.name + '-autowork-integration'))
    if (not dispatch.created_by_autowork(common, root, '(detached)')
            or state.common_dir(root) != common
            or git(root, 'rev-parse', 'HEAD') != info['commit']
            or git(root, 'status', '--porcelain', '--untracked-files=all')):
        raise ValueError('abandoned integration tree changed; preserve for diagnosis')
    if git(repo, 'rev-parse', 'HEAD') == info['baseline']:
        return None  # Pre-FF; remerge and revalidate, retaining worker attempt.
    validated_receipt(repo, common, slot)
    state.change(common, slot, 'integrated', {})
    return {'outcome': 'INTEGRATED', 'task': slot['task_id'], 'integration': info}


def goals_command(repo, *argv):
    script = Path(__file__).resolve().parents[2] / 'docs-sync/scripts/goals.py'
    result = subprocess.run([sys.executable, str(script), argv[0], str(repo), *argv[1:]],
                            capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise ValueError('goals.py failed: ' + result.stderr.strip())
    return result.stdout


def close(repo, owner_pid, task):
    repo, common = context(repo, owner_pid)
    with execution.lock(common / 'integration.lock'), execution.lock(common / 'writer.lock'):
        state.require_owner(common, owner_pid)
        require_no_writers(repo)
        slot = slot_for(common, task)
        if not slot or slot['state'] not in ('integrated', 'closed'):
            raise ValueError('close requires an integrated slot with passing validation')
        info, checks = validated_receipt(repo, common, slot)
        if slot['state'] == 'closed':
            archive = repo / 'TODO.archive.md'
            archived = execution.goals_module().task_bodies(archive.read_text()) if archive.exists() else {}
            if len(archived.get(task, [])) != 1 or archived[task][0][1].lower() != 'x':
                raise ValueError('closed cleanup requires completed archive provenance')
            return {'outcome': 'CLOSED', 'task': task, 'cleaned': cleanup_worker(repo, common, slot)}
        # The helper has no TODO-only `task` CLI. Use its same coordination and
        # atomic writer in this narrow adapter instead of creating a goals ledger.
        goals = execution.goals_module()
        current = goals.task_bodies((repo / 'TODO.md').read_text()).get(task, [])
        if (len(current) > 1 or (current and current[0][1].lower() != 'x'
                and current[0][0].strip() != info.get('task_contract'))):
            raise ValueError('task contract changed since integration; no close')
        indexed = (repo / 'goals.json').exists()
        if indexed:
            require_no_writers(repo)
            goals_command(repo, 'task', task, 'done')
        # `goals.py task` updates the index, not the authored checkbox/body.
        # Update that exact body under the helper's own stale-write guard too.
        with goals.coordination(repo):
            todo = repo / 'TODO.md'
            before = todo.read_bytes()
            text = before.decode()
            blocks = [b for b in goals.task_blocks(text) if b['id'] == task]
            if len(blocks) > 1:
                raise ValueError('TODO task duplicated; no close')
            if blocks:
                block = blocks[0]
                body = text[block['start']:block['end']]
                body = re.sub(r'(?m)^([ \t]*[-*] \[)[ xX](\] ' + re.escape(task) + r'\b)', r'\g<1>x\2', body)
                body = re.sub(r'(?m)^([ \t]*(?:[-*][ \t]+)?Status:)[^\n]*', r'\1 done', body)
                require_no_writers(repo)
                goals.atomic_write(todo, text[:block['start']] + body + text[block['end']:], expected_bytes=before)
        require_no_writers(repo)
        archived_result = json.loads(goals_command(repo, 'archive', *([] if indexed else ['--verified-tasks', task])))
        # Read back exact target before journaling closure; archive can fail safely
        # after task mutation, in which case slot stays integrated and is retryable.
        # The archive command can return null on an idempotent retry.
        archive = repo / (archived_result.get('archive') or 'TODO.archive.md')
        archived = goals.task_bodies(archive.read_text()) if archive.exists() else {}
        if task not in archived or archived[task][0][1].lower() != 'x':
            raise ValueError('archive readback does not contain the completed task')
        slot = state.change(common, slot, 'closed', {})
        return {'outcome': 'CLOSED', 'task': task, 'cleaned': cleanup_worker(repo, common, slot)}


def cleanup_worker(repo, common, slot):
    """Independent idempotent cleanup; never repeat the archive/closed transition."""
    root = execution.safe_path(slot['worktree'])
    if not dispatch.created_by_autowork(common, root, slot['branch']) or state.worker_live(slot):
        return False
    path = common / ('cleanup-' + slot['task_id'] + '-' + str(slot['attempt']) + '.json')
    intent = {k: slot[k] for k in ('task_id', 'attempt', 'worktree', 'branch', 'baseline', 'commit')}
    previous = execution.read(path)
    if path.exists() and previous != intent:
        raise ValueError('cleanup provenance does not match closed worker')
    if root.exists():
        state.workspace(common, root, slot['branch'], slot['baseline'])
        if (git(root, 'status', '--porcelain', '--untracked-files=all')
                or git(root, 'rev-parse', 'HEAD') != slot['commit']):
            return False
        require_no_writers(root)
        execution.save(path, intent)  # Durable before either destructive operation.
        git(repo, 'worktree', 'remove', str(root))
    elif previous != intent:
        return False  # An absent directory alone is not evidence of our removal.
    registrations = git(repo, 'worktree', 'list', '--porcelain').split('\n\n')
    if root.exists() or any('worktree ' + str(root) in block.splitlines() for block in registrations):
        raise ValueError('worker removal readback mismatch')
    if git(repo, 'branch', '--list', slot['branch']):
        if (git(repo, 'rev-parse', 'refs/heads/' + slot['branch']) != slot['commit']
                or any('branch refs/heads/' + slot['branch'] in block.splitlines() for block in registrations)):
            return False
        git(repo, 'branch', '-d', slot['branch'])
    if git(repo, 'branch', '--list', slot['branch']):
        raise ValueError('worker branch cleanup readback mismatch')
    return True


def retry_held(args):
    """Refill adapter for held slots; first attempts and their artifacts survive."""
    repo, common = context(args.consumer, args.owner_pid)
    with execution.lock(common / 'dispatch.lock'), execution.lock(common / 'integration.lock'):
        with execution.lock(common / 'writer.lock'):
            state.require_owner(common, args.owner_pid)
            current = state.slots(common)
            pending = any(s['state'] == 'held' and s['attempt'] == 1 for s in current)
            if any(state.worker_live(s) for s in current):
                if pending or any(s['attempt'] == 2 and state.worker_live(s) for s in current):
                    return {'outcome': 'WAITING', 'reason': 'held retries run alone after the worker pool drains'}
                return {'outcome': 'IDLE'}
            held = {s['task_id']: s for s in current if s['state'] == 'held' and s['attempt'] == 1}
            tasks = dispatch.contracts(repo, args.tasks, args.plan)
            task = next((t for t in tasks if t['id'] in held), None)
            if task is None:
                return {'outcome': 'IDLE'}
            template, host = dispatch.worker_command(args, args.owner_pid)
            if template is None:
                return {'outcome': 'SEQUENTIAL_FALLBACK', 'reason': host}
            gate = dispatch.resource_gate(0, args.min_free_mem_mb)
            if gate:
                return {'outcome': 'WAITING', 'reason': gate}
            old = held[task['id']]
            baseline = git(repo, 'rev-parse', 'HEAD')
            branch = 'autowork/' + task['id'] + '-r2'
            root = execution.safe_path(repo.parent / (repo.name + '-autowork-' + task['id'] + '-r2'))
            if root.exists() or git(repo, 'branch', '--list', branch):
                raise ValueError('fresh retry branch/worktree already exists; preserve and reconcile by hand')
            git(repo, 'worktree', 'add', '-b', branch, str(root), baseline)
            state.event(common, 'worktree_created', task_id=task['id'], worktree=str(root), branch=branch, baseline=baseline)
            slot = state.change(common, old, 'dispatched', {'worktree': str(root), 'branch': branch, 'baseline': baseline})
            data = dispatch.data_dir(common, slot)
            data.mkdir(parents=True, exist_ok=True, mode=0o700)
            prompt = data / 'prompt.md'
            report = data / 'report.json'
            prompt.write_text(dispatch.prompt(task, root, branch, baseline, report) +
                              '\nFresh retry after a held integration. Inspect prior failure: ' + old.get('reason', '') + '\n')
            argv = dispatch.render(template, {'worktree': root, 'prompt_file': prompt, 'timeout': int(args.worker_timeout),
                                            'report_file': report, 'git_common_dir': common.parent})
            execution.save(data / 'meta.json', {'slot_index': 1, 'command': argv, 'host': host,
                           'prompt_file': str(prompt), 'report_file': str(report), 'worker_timeout': args.worker_timeout})
            try:
                worker = dispatch.launch(argv, root, data, 1, prompt)
                slot = state.change(common, slot, 'running', {'worker': worker, 'log_path': str(data / 'worker.log')})
            except (ValueError, OSError) as exc:
                return hold(common, slot, 'fresh retry launch failed: ' + str(exc))
            return {'outcome': 'RETRIED', 'task': task['id'], 'slot': slot}


def dispatch_with_retries(args):
    # Original dispatch owns admission/claims and never imports this adapter.
    # Only try retries when this invocation already owns an existing lease.
    common = state.common_dir(Path(args.consumer).resolve())
    live = state.live_coordinator(common)
    if live and live['owner'] == execution.owner_identity(args.owner_pid):
        result = retry_held(args)
        if result['outcome'] != 'IDLE':
            return result
    return dispatch.dispatch(args)
