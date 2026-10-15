#!/usr/bin/env python3
"""Read-only fleet collector. Only --state-dir (under ROOT/maintenance) is writable.

stdout is a compact projection, NOT full log coverage or live ownership proof.
No profile CLI, board SQL, network publication check, recovery or dispatch.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import sqlite3
from contextlib import closing, redirect_stdout
from io import StringIO
from types import SimpleNamespace
import subprocess
import sys
from datetime import datetime, timezone
from uuid import uuid4

import yaml
from candidate_identity import git_environment
from retry_selection import goals


def dirty_count(status):
    records = iter(status.split(b'\0'))
    count = 0
    for record in records:
        if not record:
            continue
        count += 1
        if b'R' in record[:2] or b'C' in record[:2]:
            next(records, None)  # Porcelain -z rename/copy includes a second path.
    return count


def backlog_readiness(root, gaps):
    try:
        identity = goals.git_identity(root)
        canonical = {'state': 'observed', 'repo': safe(root)} if identity else {
            'state': 'unknown', 'gate': 'non-Git workspace'}
        ledger_path = root / 'goals.json'
        if not ledger_path.exists() and not ledger_path.is_symlink():
            # The direct selector reads TODO contracts without creating locks/state.
            from task_execution import select
            goals.checked_bytes(root / 'TODO.md')
            task = select(root, None, None)
            return {'state': 'consumer_ready', 'source': 'TODO.md',
                    'primary_milestone': None, 'eligible_task_ids': [safe(task['id'])],
                    'tasks': [{'task_id': safe(task['id']), 'state': 'ready_for_autowork',
                               'reasons': [], 'plan': None}],
                    'canonical_readiness': canonical, 'live_ownership': 'unknown',
                    'boundary': 'local task contract only; ownership, candidate and execution not verified'}
        data = read_json(ledger_path, gaps)
        if data is None:
            return {'state': 'invalid'}
        problems = goals.errors(data)
        if problems:
            gaps.append('backlog validation failed')
            return {'state': 'invalid', 'errors': [safe(p) for p in problems]}
        picks, priority = goals.queue(goals.normalize(data), goals.todo_text(root), allow_drift=True)
        tasks = []
        todo = goals.checked_bytes(root / 'TODO.md')
        bodies = goals.task_bodies(todo.decode('utf-8')) if todo else {}
        if len(picks) > 12: gaps.append('backlog consumer checks: eligible tasks beyond 12 omitted')
        for task, goal in picks[:12]:
            entries = bodies.get(task['id'], [])
            fields = goals.task_fields(entries[0][0]) if len(entries) == 1 else {}
            refs = re.findall(r'\[[^\]]*\]\(([^\s)]+)\)', fields.get('Sources', ''))
            plan = None
            for ref in refs:
                reasons = []
                section = goals.local_reference(root, ref, {}, reasons)
                if '#' in ref and not reasons and re.search(r'^\s*(?:\*\*)?Status:(?:\*\*)?\s*Accepted\s*$', section, re.M | re.I):
                    plan = ref; break
            # Use the consumer's pure check directly; its CLI coordination creates a lock.
            output = StringIO()
            with redirect_stdout(output):
                goals.backlog_check(SimpleNamespace(repo=root, plan=plan or goal['source'], tasks=task['id'], receipt=None))
            checked = json.loads(output.getvalue())
            tasks.append({'task_id': safe(task['id']), 'state': checked['state'],
                          'reasons': [safe(reason) for reason in checked['reasons']],
                          'plan': safe(plan) if plan else None})
        return {'state': 'consumer_ready' if tasks and canonical['state'] == 'observed' and
                any(t['state'] == 'ready_for_autowork' for t in tasks) else
                'ledger_eligible_only' if picks else 'no_ledger_eligible_task',
                'primary_milestone': data.get('primary_milestone'),
                'priority_state': priority['state'],
                'eligible_task_ids': [safe(t['id']) for t, _ in picks], 'tasks': tasks,
                'canonical_readiness': canonical, 'live_ownership': 'unknown',
                'boundary': 'local consumer qualification only; ownership, admission, candidate and dispatch not verified'}
    except SystemExit as error:
        gaps.append('backlog consumer qualification refused')
        return {'state': 'unknown', 'gate': safe(error), 'live_ownership': 'unknown'}
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError, subprocess.SubprocessError):
        gaps.append('backlog consumer qualification unavailable')
        return {'state': 'unknown', 'live_ownership': 'unknown'}


def cron_responses(home, jobs, gaps):
    rows = []
    for job in jobs:
        identifier = job.get('id')
        if not isinstance(identifier, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', identifier):
            gaps.append('cron response: invalid job identity'); continue
        directory = home / 'cron/output' / identifier
        try:
            resolved = directory.resolve()
            contained = resolved.is_relative_to(home.resolve())
            aliased = resolved != home.resolve() / 'cron/output' / identifier
        except (OSError, RuntimeError):
            gaps.append('cron response directory unresolvable: ' + identifier); continue
        if not contained:
            gaps.append('cron response directory outside profile: ' + identifier); continue
        if aliased:
            gaps.append('cron response directory aliased: ' + identifier); continue
        try:
            paths = sorted(p for p in directory.glob('*.md') if p.is_file() and not p.is_symlink())
            if not paths:
                gaps.append('cron response missing: ' + identifier); continue
            for path in paths[-2:]:
                try:
                    with path.open('rb') as handle:
                        size = os.fstat(handle.fileno()).st_size
                        start = max(0, size - 32768)
                        handle.seek(start)
                        data = handle.read(32768)
                except OSError:
                    gaps.append('cron response unreadable: ' + identifier + ': ' + safe(path.name))
                    continue
                truncated = start > 0
                text = data.decode('utf-8', errors='replace')
                if truncated:
                    text = '[EARLIER OUTPUT OMITTED; PARTIAL FIRST LINE REDACTED]\n' + text.partition('\n')[2]
                    gaps.append('cron response truncated: ' + identifier)
                sections = re.split(r'^## Response\n\n', text, flags=re.M)
                projection = 'Response delimiter absent from observed tail; compatibility tail only'
                if len(sections) > 1:
                    text = sections[-1]
                    projection = 'text after last exact Response delimiter in observed tail'
                rows.append({'job_id': identifier, 'path': str(path), 'start': start, 'bytes_observed': len(data),
                             'remaining_bytes': start + max(0, size - start - len(data)), 'sha256': digest(data),
                             'payload': safe(text), 'analysis': 'not_analyzed',
                             'output_rank': 1 if path == paths[-1] else 2, 'latest': path == paths[-1],
                             'boundary': 'newest two output files by filename order; rank 1 is latest; exact execution association not proved; ' + projection + '; full output coverage not proved'})
        except OSError:
            gaps.append('cron response unreadable: ' + identifier)
    return rows



def digest(value):
    return hashlib.sha256(value).hexdigest()


def safe(value):
    text = str(value)

    def scrub(item):
        if isinstance(item, dict):
            return {safe(key): '[REDACTED]' if re.fullmatch(
                        r'(?i)api[_-]?key|token|password|secret|authorization|cookie', key)
                    else scrub(part) for key, part in item.items()}
        if isinstance(item, list):
            return [scrub(part) for part in item]
        return safe(item) if isinstance(item, str) else item

    try:
        parsed = json.loads(text)
    except (ValueError, RecursionError):
        parsed = None
    if isinstance(parsed, (dict, list, str)):
        try:
            # Decoding supplements, never bypasses, the contextual masking below.
            text = json.dumps(scrub(parsed), ensure_ascii=False)
        except RecursionError:
            # A decodable envelope can still exceed the recursive scrubber's stack.
            return '[NESTED JSON REDACTED]'
    # Mask whole quoted values before delimiters can expose a credential suffix.
    text = re.sub(r'''(?is)((?:api[_-]?key|token|password|secret|authorization|cookie)\s*["']?\s*[:=]\s*)(?:"(?:\\.|[^"\\])*(?:"|\\?\Z)|'(?:\\.|[^'\\])*(?:'|\\?\Z))''', r'\1[REDACTED]', text)
    text = re.sub(r'(?i)(bearer\s+)[^\s,;]+', r'\1[REDACTED]', text)
    text = re.sub(r'(?i)((?:api[_-]?key|token|password|secret|authorization|cookie)\s*[\"\']?\s*[:=]\s*)[^\n,;]+', r'\1[REDACTED]', text)
    text = re.sub(r'https?://[^\s\"\'<>]+', '[URL REDACTED]', text)
    text = re.sub(r'\b(?:sk-|ghp_|github_pat_|xox[baprs]-)[\w-]+', '[REDACTED]', text)
    text = re.sub(r'[A-Za-z0-9+/=_-]{48,}', '[OPAQUE REDACTED]', text)
    return text


def project(obj, keys):
    return {k: safe(obj[k]) if isinstance(obj[k], str) else obj[k]
            for k in keys if k in obj and isinstance(obj[k], (str, int, float, bool, type(None)))}


def read_json(path, gaps, optional=False):
    try:
        if path.stat().st_size > 2 * 1024 * 1024:
            gaps.append(str(path.name) + ': size limit'); return None
        return json.loads(path.read_text())
    except FileNotFoundError:
        if not optional: gaps.append(str(path.name) + ': missing')
    except (OSError, ValueError):
        gaps.append(str(path.name) + ': unreadable or invalid JSON')
    return None


def homes(root):
    result = [('default', root)]
    directory = root / 'profiles'
    if directory.is_dir():
        for p in sorted(directory.iterdir()):
            if (p.is_dir() and re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', p.name)
                    and p.name != 'default' and not (directory / '.deleted' / p.name).exists()
                    and any((p / marker).is_file() or (p / marker).is_symlink() for marker in
                            ('config.yaml', '.env', 'SOUL.md', 'profile.yaml', 'auth.json', 'state.db'))):
                result.append((p.name, p))
    return result


def database(path, table, keys, order, gaps, limit=12):
    if not path.is_file():
        gaps.append(path.name + ': missing'); return []
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=1)) as db:
            db.execute('PRAGMA query_only=ON')
            columns = {r[1] for r in db.execute('PRAGMA table_info(' + table + ')')}
            chosen = [k for k in keys if k in columns]
            if not chosen or order not in columns:
                gaps.append(table + ': unknown schema'); return []
            total = db.execute('SELECT count(*) FROM ' + table).fetchone()[0]
            rows = db.execute('SELECT ' + ','.join(chosen) + ' FROM ' + table +
                              ' ORDER BY ' + order + ' DESC LIMIT ?', (limit,)).fetchall()
            if total > limit: gaps.append(table + ': older metadata omitted (' + str(total - limit) + ')')
            return [project(dict(zip(chosen, r)), chosen) for r in rows]
    except sqlite3.Error:
        gaps.append(path.name + ': SQLite read failed'); return []


def git(repo, *args):
    env = git_environment()
    env['GIT_OPTIONAL_LOCKS'] = '0'
    result = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
                             '-C', str(repo), *args],
                            capture_output=True, timeout=10, env=env)
    if result.returncode:
        # Never retain raw stderr: even a Git URL or path can contain credentials.
        raise ValueError('git ' + args[0] + ' failed; stderr withheld (' + str(len(result.stderr)) + ' bytes)')
    return result.stdout


def repository(home, launch, gaps):
    try:
        config = yaml.safe_load((home / 'config.yaml').read_text()) or {}
        cwd = config.get('terminal', {}).get('cwd')
        if not isinstance(cwd, str) or not cwd:
            gaps.append('terminal.cwd: missing'); return {'state': 'unknown_cwd'}
        path = Path(cwd).expanduser()
        if not path.is_absolute():
            if launch is None:
                gaps.append('terminal.cwd: relative, launch context unknown')
                return {'state': 'unknown_relative_cwd', 'configured_cwd': safe(cwd)}
            path = launch / path
        root = Path(git(path, 'rev-parse', '--show-toplevel').decode().strip())
        status = git(root, 'status', '--porcelain=v1', '-z')
        diff = git(root, 'diff', '--no-ext-diff', '--no-textconv', 'HEAD', '--')
        worktrees = git(root, 'worktree', 'list', '--porcelain').decode(errors='replace')
        backlog = {}
        for name in ('goals.json', 'TODO.md'):
            p = root / name
            if p.is_file() and p.stat().st_size <= 2 * 1024 * 1024:
                backlog[name] = digest(p.read_bytes())
            else:
                backlog[name] = None
                gaps.append(name + ': absent or beyond limit')
        # shortcut: untracked bodies are not inspected; an unchanged dirty count is not progress proof.
        if b'?? ' in status: gaps.append('untracked content not inspected')
        return {'state': 'observed', 'root': safe(root),
                'head': git(root, 'rev-parse', 'HEAD').decode().strip(),
                'branch': safe(git(root, 'branch', '--show-current').decode().strip()),
                'dirty_records': dirty_count(status),
                'backlog_readiness': backlog_readiness(root, gaps),
                'status_sha256': digest(status), 'tracked_diff_sha256': digest(diff),
                'backlog': backlog, 'worktrees': safe(worktrees),
                'worktree_boundary': 'registry only; sibling contents and worker liveness unknown'}
    except (OSError, ValueError, AttributeError, yaml.YAMLError, subprocess.SubprocessError) as error:
        gaps.append(str(error) if isinstance(error, ValueError) else 'repo/config read failed: ' + type(error).__name__)
        return {'state': 'unverified'}


def inspect_profile(name, home, launch):
    gaps = []
    jobs = read_json(home / 'cron/jobs.json', gaps)
    if isinstance(jobs, dict) and isinstance(jobs.get('jobs'), list): jobs = jobs['jobs']
    if not isinstance(jobs, list):
        if jobs is not None: gaps.append('jobs.json: unknown schema')
        jobs = []
    jobs = [project(j, ('id', 'name', 'enabled', 'last_status', 'last_run_at', 'next_run_at', 'last_error',
                        'last_delivery_error', 'last_delivery_unverified', 'last_fire_error'))
            for j in jobs if isinstance(j, dict)]
    if not jobs: gaps.append('no scheduled jobs observed')
    sessions = database(home / 'state.db', 'sessions',
                        ('id', 'source', 'parent_session_id', 'cwd', 'git_repo_root', 'started_at',
                         'ended_at', 'end_reason', 'message_count', 'tool_call_count'), 'started_at', gaps)
    executions = database(home / 'cron/executions.db', 'executions',
                          ('id', 'job_id', 'pid', 'process_started_at', 'status', 'started_at',
                           'finished_at', 'error', 'delivery_outcome'), 'started_at', gaps)
    continuity = {}
    # reconcile.py consumes only goal-handoff.json, with top-level task precedence.
    # state.json is legacy evidence, never a replacement for a missing current handoff.
    for filename in ('state.json', 'goal-handoff.json'):
        raw = read_json(home / 'autowork' / filename, gaps, optional=filename == 'state.json')
        if isinstance(raw, dict):
            if raw.get('task_id') is None and isinstance(raw.get('current_handoff'), dict):
                raw = raw['current_handoff']
            if not isinstance(raw.get('task_id'), str) or not raw['task_id']:
                gaps.append(filename + ': current task identity unknown'); continue
            row = project(raw, ('task_id', 'run_id', 'blocker', 'blocked_reason', 'commit', 'candidate_commit',
                                'worker_session_id', 'outcome', 'status'))
            owner = raw.get('profile')
            if isinstance(owner, str) and owner:
                row['owner_profile'] = safe(owner)
                if owner != name: gaps.append(filename + ': profile metadata differs; ownership unknown')
            metadata = raw.get('metadata') if isinstance(raw.get('metadata'), dict) else {}
            for key in ('checks', 'delivery_evidence'):
                value = raw.get(key, metadata.get(key))
                if isinstance(value, (dict, list)):
                    row[key + '_sha256'] = digest(json.dumps(value, sort_keys=True).encode())
            continuity[filename] = row
        elif raw is not None: gaps.append(filename + ': unknown schema')
    cycle_raw = read_json(home / 'autowork/unblock-latest.json', gaps, optional=True)
    owner_cycle = {}
    if isinstance(cycle_raw, dict) and cycle_raw.get('version') == 1 and isinstance(cycle_raw.get('task_ids'), list):
        owner_cycle = project(cycle_raw, ('timestamp', 'run_id', 'task_ids', 'plan', 'consumer',
                              'outcome', 'action', 'unchanged_runs', 'request_status', 'integration_request',
                              'next_action', 'selected_task', 'dispatch_attempted', 'completed_tasks', 'delivery'))
        owner_cycle['task_ids'] = [safe(t) for t in cycle_raw['task_ids'] if isinstance(t, str)][:100]
        if isinstance(cycle_raw.get('selected_task'), dict):
            owner_cycle['selected_task'] = project(cycle_raw['selected_task'], ('id', 'title', 'status'))
        for field in ('held_task_ids', 'repairs', 'blocker', 'resolved_requests'):
            if isinstance(cycle_raw.get(field), list):
                owner_cycle[field] = [safe(v) for v in cycle_raw[field] if isinstance(v, str)][:100]
        queue = cycle_raw.get('ready_queue')
        owner_cycle['ready_queue'] = [project(t, ('id', 'title', 'goal'))
                                    for t in (queue if isinstance(queue, list) else []) if isinstance(t, dict)][:3]
        owner_cycle.update(project(cycle_raw, ('queue_shortfall', 'routing_gap')))
        owner_cycle['boundary'] = 'Reported owner-cycle evidence; not fresh worker, remote or product acceptance verification'
    elif cycle_raw is not None:
        gaps.append('owner cycle receipt missing supported schema; recovery execution unverified')
    # start_goal.save_receipt archives continuity here; archives are not current runs.
    directory = home / 'autowork/handoffs'
    history = {'files_observed': 0, 'boundary': 'archive inventory only; not current handoff or ownership'}
    if directory.is_dir():
        for path in directory.iterdir():
            if path.suffix == '.json' and path.is_file() and not path.is_symlink():
                history['files_observed'] += 1
                if history['files_observed'] >= 100:
                    gaps.append('handoff archive inventory capped at 100'); break
    repo = repository(home, launch, gaps)
    return {'profile': name, 'home': str(home), 'jobs': jobs, 'executions': executions,
            'cron_responses': cron_responses(home, jobs, gaps),
            'sessions': sessions, 'owner_cycle': owner_cycle, 'continuity': continuity, 'handoff_history': history, 'repo': repo, 'gaps': gaps,
            'live_ownership': 'unknown',
            'workers': {'session_anchors': [r['id'] for r in sessions if r.get('parent_session_id')],
                        'boundary': 'session metadata, not process liveness or board ownership'},
            'publication': {'state': 'unverified', 'boundary': 'no exact authorized network claim checked'},
            'recovery': 'recommendation only: owner reconcile original task/worker; no automatic mutation'}


def private_write(path, obj):
    if path.is_symlink(): raise ValueError('refuse symlink state target')
    temporary = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w') as handle:
        json.dump(obj, handle, separators=(',', ':'), sort_keys=True)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def log_chunks(home, prior, file_budget, profile_budget, gaps):
    directory = home / 'logs'
    files = sorted(p for p in directory.iterdir() if p.is_file() and not p.is_symlink()) if directory.is_dir() else []
    if not files: gaps.append('logs: missing or empty')
    rows, cursors = [], {}
    share = min(file_budget, max(1, profile_budget // max(1, len(files))))
    budget = profile_budget
    for p in files:
        old = prior.get(p.name, {})
        try:
            with p.open('rb') as handle:
                stat = os.fstat(handle.fileno())
                identity = [stat.st_dev, stat.st_ino]
                history = list(old.get('history_gaps', []))
                start = old.get('cursor', 0)
                if old and old.get('identity') != identity:
                    history.append('rotated/replaced; previous unread bytes=' + str(old.get('remaining_bytes', 'unknown')))
                    start = 0
                elif old and stat.st_size < start:
                    history.append('truncated; historical byte continuity lost'); start = 0
                elif old and start:
                    handle.seek(max(0, start - 64))
                    if digest(handle.read(min(64, start))) != old.get('anchor'):
                        history.append('truncated/rewritten; historical byte continuity lost'); start = 0
                if not old: history.append('pre-collector rotated/deleted history unknown; legacy cursors not trusted')
                handle.seek(start)
                payload = handle.read(min(share, budget))
                cursor = start + len(payload)
                budget -= len(payload)
                handle.seek(max(0, cursor - 64))
                anchor = digest(handle.read(min(64, cursor)))
                text = payload.decode('utf-8', errors='replace')
                # Chunk edges may split a secret; withhold partial lines rather than leak suffixes.
                parts = text.splitlines(keepends=True)
                if parts and start: parts[0] = '[PARTIAL FIRST LINE REDACTED]\n'
                if parts and not payload.endswith(b'\n'): parts[-1] = '[PARTIAL LAST LINE REDACTED]\n'
                row = {'file': p.name, 'identity': identity, 'start': start, 'cursor': cursor,
                       'size': stat.st_size, 'bytes_observed': len(payload),
                       'remaining_bytes': max(0, stat.st_size - cursor), 'sha256': digest(payload),
                       'anchor': anchor, 'history_gaps': sorted(set(history)),
                       'payload': safe(''.join(parts)), 'analysis': 'not_analyzed',
                       'redaction': 'heuristic secrets/URLs/opaque values and partial lines withheld; private only'}
                rows.append(row)
                cursors[p.name] = {k: row[k] for k in ('identity', 'cursor', 'anchor', 'remaining_bytes', 'history_gaps')}
                if row['remaining_bytes']: gaps.append(p.name + ': unread suffix=' + str(row['remaining_bytes']))
                if history: gaps.append(p.name + ': history continuity unknown')
        except OSError:
            gaps.append(p.name + ': log read failed')
            if old: cursors[p.name] = old
    for name, old in prior.items():
        if name not in cursors:
            missing = dict(old)
            missing['history_gaps'] = sorted(set(old.get('history_gaps', []) + ['removed log; remaining historical bytes unknown']))
            cursors[name] = missing
            gaps.append(name + ': removed log history gap')
    return rows, cursors


def progress(row, previous):
    # Historical handoffs do not link cron occurrences to fresh task evidence.
    finished = [r for r in row['executions'] if r.get('status') in ('completed', 'failed') and r.get('finished_at') and r.get('id')]
    latest = finished[0]['id'] if finished else None
    seen = set(previous.get('completed_runs', []))
    if previous.get('completed_run'): seen.add(previous['completed_run'])
    seen.update(r['id'] for r in finished)
    # Retain legacy counters/fingerprints as history, never as a validated streak.
    saved = {**previous, 'completed_run': latest or previous.get('completed_run'),
             'completed_runs': sorted(seen)}
    row['gaps'].append('no-progress: exact job/occurrence/task attribution and fresh evidence unavailable')
    result = {'consecutive': None, 'state': 'unknown',
              'boundary': 'task-to-cron-run attribution unknown; historical counters are not validated streaks; '
                          'observation is not auto-pause authorization'}
    return result, saved


def compact_profile(row, previous):
    result = {'profile': row['profile'], 'gaps': row['gaps'], 'no_progress': row['no_progress']}
    failures = []
    for job in row['jobs']:
        failure = project(job, ('id', 'last_error', 'last_delivery_error', 'last_delivery_unverified', 'last_fire_error'))
        if any(v for k, v in failure.items() if k != 'id'): failures.append(failure)
    for execution in row['executions']:
        if execution.get('error') or execution.get('status') in ('failed', 'interrupted'):
            failures.append(project(execution, ('id', 'job_id', 'status', 'error')))
    if failures: result['failures'] = failures
    if row['continuity']: result['tasks'] = row['continuity']
    if row.get('owner_cycle'): result['owner_cycle'] = row['owner_cycle']
    readiness = row['repo'].get('backlog_readiness', {})
    held = [task for task in readiness.get('tasks', []) if task.get('reasons')]
    if held:
        reasons = sorted({reason for task in held for reason in task['reasons']})
        excerpts = [reason[:160] for reason in reasons[:3]]
        result['task_gates'] = {'tasks': [project(task, ('task_id', 'state')) for task in held],
                                'reasons': excerpts, 'reason_count': len(reasons),
                                'details_omitted': excerpts != reasons,
                                'details': 'full sanitized reasons in receipt'}
    if readiness.get('gate'): result['backlog_gate'] = readiness['gate']
    canonical = readiness.get('canonical_readiness', {})
    if canonical.get('gate'): result['canonical_gate'] = canonical
    fields = {'repo_state': row['repo']['state'], 'head': row['repo'].get('head'),
              'dirty_records': row['repo'].get('dirty_records'), 'jobs': len(row['jobs']),
              'executions': len(row['executions']), 'backlog_state': readiness.get('state'),
              'unread_log_bytes': sum(r['remaining_bytes'] for r in row['logs'])}
    for key, value in fields.items():
        if previous is None or previous.get(key) != value: result[key] = value
    return result


def collect(args):
    root = args.root.resolve(strict=True)
    if root.parent.name == 'profiles': raise ValueError('--root must be default home, not named profile')
    state_dir = args.state_dir.resolve()
    maintenance = root / 'maintenance'
    if maintenance.is_symlink() or not state_dir.is_relative_to(maintenance) or state_dir == maintenance:
        raise ValueError('--state-dir must be a private subdirectory of default ROOT/maintenance')
    for _, home in homes(root)[1:]:
        resolved = home.resolve()
        if state_dir.is_relative_to(resolved) or resolved.is_relative_to(state_dir):
            raise ValueError('--state-dir overlaps named profile')
    for ancestor in (state_dir, *state_dir.parents):
        if (ancestor / '.git').exists(): raise ValueError('--state-dir overlaps repository')
    available = homes(root)
    requested = getattr(args, 'profiles', None)
    if requested is not None and (not requested or len(requested) != len(set(requested))
            or not set(requested).issubset({name for name, _ in available})):
        raise ValueError('profiles must be unique existing profiles')
    selected = available if requested is None else [(name, home) for name, home in available if name in requested]
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = state_dir / 'collector.lock'
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'a') as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'schema': 'fleet-audit/v1', 'state': 'overlap_refused', 'profiles': []}
        prior = read_json(state_dir / 'collector-state.json', [], optional=True) or {}
        if not isinstance(prior, dict) or prior.get('schema') != 'fleet-collector-state/v1':
            prior = {}
        profiles, summaries = [], []
        prior_profiles = prior.get('profiles', {})
        if not isinstance(prior_profiles, dict):
            raise ValueError('collector profile state must be an object')
        next_state = {'schema': 'fleet-collector-state/v1', 'profiles': dict(prior_profiles)}
        for name, home in selected:
            row = inspect_profile(name, home, args.launch_cwd.get(name))
            previous = prior.get('profiles', {}).get(name, {})
            row['logs'], log_state = log_chunks(home, previous.get('logs', {}), args.log_bytes,
                                                args.profile_log_bytes, row['gaps'])
            row['no_progress'], progress_state = progress(row, previous.get('progress', {}))
            row['gaps'].extend(('live board ownership not queried; no CLI initialization',
                                'publication not verified; cached receipts are not current proof',
                                'collected log payload is not analyzed coverage'))
            profiles.append(row)
            summaries.append(compact_profile(row, previous.get('summary')))
            next_state['profiles'][name] = {'logs': log_state, 'progress': progress_state,
                                            'summary': compact_profile(row, None)}
        receipt = {'schema': 'fleet-audit/v1', 'at': datetime.now(timezone.utc).isoformat(),
                   'profiles': profiles, 'boundary': 'read-only observation; no health, ownership, delivery or acceptance inference'}
        path = state_dir / ('receipt-' + uuid4().hex + '.json')
        private_write(path, receipt)  # Persist payload before advancing any cursor.
        next_state['receipt'] = str(path)
        private_write(state_dir / 'collector-state.json', next_state)
        return {'schema': receipt['schema'], 'state': 'observed_with_gaps', 'receipt': str(path),
                'boundary': 'unchanged repo fields omitted; live ownership/publication unknown; logs not analyzed',
                'profiles': summaries}


class JsonParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({'state': 'collector_failed', 'error': 'arguments', 'reason': safe(message)}))
        raise SystemExit(2)


def main():
    parser = JsonParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='default Hermes home, not HERMES_HOME of a named profile')
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--profiles', nargs='+', help='Collect only these existing profiles; keep excluded cursors')
    parser.add_argument('--launch-cwd', action='append', default=[], metavar='PROFILE=/absolute/path')
    parser.add_argument('--log-bytes', type=int, default=16384, help='maximum observed bytes per log file per tick')
    parser.add_argument('--profile-log-bytes', type=int, default=131072)
    args = parser.parse_args()
    contexts = {}
    for value in args.launch_cwd:
        name, sep, path = value.partition('=')
        if not sep or not Path(path).is_absolute(): parser.error('--launch-cwd needs PROFILE=/absolute/path')
        contexts[name] = Path(path)
    args.launch_cwd = contexts
    if args.log_bytes <= 0 or args.profile_log_bytes <= 0: parser.error('byte budgets must be positive')
    def deadline(signum, frame):
        raise RuntimeError('collector deadline')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(115)
    try:
        result = collect(args)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RuntimeError) as error:
        print(json.dumps({'state': 'collector_failed', 'error': type(error).__name__,
                          'reason': safe(str(error)) if isinstance(error, ValueError) else 'filesystem operation failed'}))
        return 1
    print(json.dumps(result, separators=(',', ':')))
    return 2 if result['state'] == 'overlap_refused' else 0


if __name__ == '__main__':
    sys.exit(main())
