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
    others: list[list[str]] = [list(dispatch.COORDINATOR_FILES)]
    for other in state.slots(common):
        if other['task_id'] == slot['task_id'] or other['state'] == 'released':
            continue
        if other.get('commit'):
            others.append(changed(repo, other['baseline'], other['commit']))
        else:
            others.append(plan.paths(contracts.get(other['task_id'], {}).get('fields', {}).get('Touches', '')))
    overlap = plan.overlap(files, plan.paths(task['fields'].get('Touches', '')), others)
    if overlap['outside'] or overlap['conflicts']:
        raise ValueError('changed files violate Touches or coordinator/other-slot ownership: ' + str(overlap))
    return files, report


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
            if not slot or slot['state'] != 'reported':
                raise ValueError('integration requires a reported slot')
            contracts = {t['id']: t for t in dispatch.contracts(repo)}
            reported = {s['task_id'] for s in state.slots(common) if s['state'] == 'reported'}
            first = next((t for t in contracts if t in reported), None)
            if first != task:
                raise ValueError('integrate the highest-priority reported task first')
            try:
                files, report = verify(repo, common, slot, contracts)
            except (ValueError, OSError) as exc:
                return hold(common, slot, str(exc))
            slot = state.change(common, slot, 'integrating', {'report': report})
        check = None
        def save_receipt(path, value):
            with execution.lock(common / 'writer.lock'):
                state.require_owner(common, owner_pid)
                execution.save(path, value)

        try:
            for attempt in range(2):
                with execution.lock(common / 'writer.lock'):
                    state.require_owner(common, owner_pid)
                    baseline = git(repo, 'rev-parse', 'HEAD')
                    canonical_branch = git(repo, 'symbolic-ref', 'HEAD')
                    root = integration_worktree(repo, common, baseline)
                    try:
                        git(root, 'merge', '--no-ff', '--no-edit', slot['commit'])
                    except ValueError:
                        git(root, 'merge', '--abort')
                        raise ValueError('merge conflict; worker and canonical checkout preserved')
                    merge = git(root, 'rev-parse', 'HEAD')
                inputs = {p: execution.digest(root / p) for p in ('TODO.md', 'goals.json')}
                check = execution.bounded_command(argv, root, common, task, timeout, inputs,
                            receipt_context={'integration_commit': merge}, receipt_writer=save_receipt)
                if (check['outcome'] != 'EXECUTED' or git(root, 'rev-parse', 'HEAD') != merge
                        or git(root, 'status', '--porcelain', '--untracked-files=all')):
                    raise ValueError('integration validation failed or changed the integration tree')
                with execution.lock(common / 'writer.lock'):
                    state.require_owner(common, owner_pid)
                    # Re-read report, refs, scopes and source contracts after arbitrary validation.
                    fresh_contracts = {t['id']: t for t in dispatch.contracts(repo)}
                    verify(repo, common, slot, fresh_contracts)
                    if fresh_contracts[task]['contract'] != contracts[task]['contract']:
                        raise ValueError('task contract changed during validation')
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
                    integration = {'commit': merge, 'baseline': baseline, 'changed_files': files,
                                   'check_receipt': check['command_receipt']['receipt'],
                                   'task_contract': contracts[task]['contract']}
                    state.change(common, slot, 'integrated', {'integration': integration, 'checks': check})
                    return {'outcome': 'INTEGRATED', 'task': task, 'integration': integration}
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            with execution.lock(common / 'writer.lock'):
                state.require_owner(common, owner_pid)
                return hold(common, slot, str(exc), **({'checks': check} if check is not None else {}))


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
        slot = slot_for(common, task)
        if not slot or slot['state'] != 'integrated':
            raise ValueError('close requires an integrated slot with passing validation')
        info, checks = slot.get('integration', {}), slot.get('checks', {})
        receipt_path = Path(info.get('check_receipt', ''))
        if receipt_path.parent != common or receipt_path.suffix != '.json':
            raise ValueError('validation receipt must be in repository execution state')
        saved = execution.read(receipt_path)
        if (saved != checks or checks.get('outcome') != 'EXECUTED'
                or checks.get('context', {}).get('integration_commit') != info.get('commit')
                or checks.get('command_receipt', {}).get('exit_code') != 0
                or checks['command_receipt'].get('task_id') != task
                or checks['command_receipt'].get('inputs_match') is not True
                or git(repo, 'merge-base', info['commit'], 'HEAD') != info['commit']
                or git(repo, 'rev-list', '--parents', '-n', '1', info['commit']).split()[1:]
                   != [info['baseline'], slot['commit']]):
            raise ValueError('missing, failed, stale or mismatched integration validation')
        # The helper has no TODO-only `task` CLI. Use its same coordination and
        # atomic writer in this narrow adapter instead of creating a goals ledger.
        goals = execution.goals_module()
        current = goals.task_bodies((repo / 'TODO.md').read_text()).get(task, [])
        if (len(current) > 1 or (current and current[0][1].lower() != 'x'
                and current[0][0].strip() != info.get('task_contract'))):
            raise ValueError('task contract changed since integration; no close')
        indexed = (repo / 'goals.json').exists()
        if indexed:
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
                goals.atomic_write(todo, text[:block['start']] + body + text[block['end']:], expected_bytes=before)
        archived_result = json.loads(goals_command(repo, 'archive', *([] if indexed else ['--verified-tasks', task])))
        # Read back exact target before journaling closure; archive can fail safely
        # after task mutation, in which case slot stays integrated and is retryable.
        # The archive command can return null on an idempotent retry.
        archive = repo / (archived_result.get('archive') or 'TODO.archive.md')
        archived = goals.task_bodies(archive.read_text()) if archive.exists() else {}
        if task not in archived or archived[task][0][1].lower() != 'x':
            raise ValueError('archive readback does not contain the completed task')
        slot = state.change(common, slot, 'closed', {})
        cleaned = False
        root = Path(slot['worktree'])
        if (dispatch.created_by_autowork(common, root, slot['branch']) and root.exists()
                and not state.worker_live(slot)):
            state.workspace(common, root, slot['branch'], slot['baseline'])
            if (not git(root, 'status', '--porcelain', '--untracked-files=all')
                    and git(root, 'rev-parse', 'HEAD') == slot['commit']):
                git(repo, 'worktree', 'remove', str(root))
                git(repo, 'branch', '-d', slot['branch'])
                cleaned = True
                state.event(common, 'worker_cleaned', task_id=task, worktree=str(root), branch=slot['branch'])
        return {'outcome': 'CLOSED', 'task': task, 'cleaned': cleaned}


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
