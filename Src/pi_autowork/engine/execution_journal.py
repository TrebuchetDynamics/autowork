"""The existing private execution journal: append once, tolerate torn/duplicate lines.

Lifecycle envelopes contain identifiers and enum outcomes only, never task prose,
commands, paths or transcripts. Legacy diagnostic payloads are left compatible.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

from pi_autowork.engine import task_execution as execution


def read(common, *, ordered=False):
    path = execution.safe_path(common / 'journal.jsonl')
    events, seen = [], set()
    skipped = dict(duplicate=0, torn=0)
    if not path.exists():
        return dict(events=events, skipped=skipped)
    with path.open('rb') as stream:
        for line in stream:
            try:
                if not line.endswith(b'\n'):
                    raise ValueError('torn final line')
                value = json.loads(line, object_pairs_hook=execution.unique)
            except (ValueError, UnicodeError):
                skipped['torn'] += 1
                continue
            if (not isinstance(value, dict) or type(value.get('timestamp')) not in (float, int)
                    or not math.isfinite(value['timestamp']) or not isinstance(value.get('event'), str)):
                raise ValueError('malformed parallel journal event')
            identity = value.get('event_id') or json.dumps(value, sort_keys=True)
            if identity in seen:
                skipped['duplicate'] += 1
                continue
            seen.add(identity)
            if ordered and events and value['timestamp'] < events[-1]['timestamp']:
                raise ValueError('parallel journal timestamps moved backwards')
            events.append(value)
    return dict(events=events, skipped=skipped)


def lifecycle_events(common):
    result = read(common)
    events, seen = [], set()
    for line in result['events']:
        for event in line.get('lifecycle', []):
            if event['event_id'] in seen:
                result['skipped']['duplicate'] += 1
                continue
            seen.add(event['event_id'])
            events.append(event)
    return dict(events=events, skipped=result['skipped'])


# An in-process index only; the journal remains the source of truth across restart.
_known = {}


def signature(common):
    try:
        stat = (common / 'journal.jsonl').stat()
        return stat.st_ino, stat.st_size, stat.st_mtime_ns
    except FileNotFoundError:
        return None


def pending(common, facts):
    key = str(common)
    stamp = signature(common)
    cached = _known.get(key)
    if cached is None or cached[0] != stamp:
        # Refresh only the appended tail in a long-lived coordinator. Truncation,
        # replacement or an in-place same-size rewrite invalidates the index.
        reuse = bool(cached and stamp and cached[0] and stamp[0] == cached[0][0]
                     and stamp[1] > cached[0][1])
        seen = set(cached[1]) if reuse else set()
        task_events = set(cached[3]) if reuse else set()
        offset = cached[2] if reuse else 0
        path = execution.safe_path(common / 'journal.jsonl')
        if path.exists():
            with path.open('rb') as stream:
                stream.seek(offset)
                for line in stream:
                    if not line.endswith(b'\n'):
                        break
                    offset = stream.tell()
                    try:
                        value = json.loads(line)
                    except (ValueError, UnicodeError):
                        continue
                    if isinstance(value, dict):
                        for event in value.get('lifecycle', []):
                            seen.add(event['event_id'])
                            task_events.add((event['task_id'], event['event']))
        cached = stamp, seen, offset, task_events
        if len(_known) > 32:
            _known.clear()
        _known[key] = cached
    seen = set(cached[1])
    result = []
    for fact in facts:
        if fact['event_id'] not in seen:
            result.append(fact)
            seen.add(fact['event_id'])
    return result


def known_tasks(common):
    pending(common, [])  # refresh the in-process tail index
    return set(_known[str(common)][3])


def append(common, kind, fields):
    """No additional lock or retry: one O_APPEND write under the caller's writer lock.

    Telemetry I/O is best effort and must never turn a successful operation into a
    hold. A short write/crash leaves a torn line; the next append separates it.
    """
    try:
        before = signature(common)
        facts = pending(common, fields.pop('lifecycle', []))
        value = dict(timestamp=time.time(), event=kind, event_id=uuid.uuid4().hex, **fields)
        if facts:
            value['lifecycle'] = facts
        data = (json.dumps(value, allow_nan=False) + '\n').encode()
        path = execution.safe_path(common / 'journal.jsonl')
        fd = os.open(path, os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
            size = os.fstat(fd).st_size
            if size and os.pread(fd, 1, size - 1) != b'\n':
                data = b'\n' + data
            written = os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        cached = _known.get(str(common))
        if cached and cached[0] == before and written == len(data):
            cached[1].update(e['event_id'] for e in facts)
            cached[3].update((e['task_id'], e['event']) for e in facts)
            final = signature(common)
            _known[str(common)] = final, cached[1], final[1], cached[3]
        else:
            _known.pop(str(common), None)
        return written == len(data)
    except (OSError, ValueError):
        return False


def label(value):
    """Do not redact arbitrary prose into identifiers: reject it outright."""
    value = str(value or '')
    if (re.match(r'^[A-Za-z]:[/\\\\]', value)
            or not re.fullmatch(r'[A-Za-z0-9_.:-]+(?:/[A-Za-z0-9_.:-]+)*', value)
            or len(value) > 128 or re.search(r'(?i)(sk-|gh[pousr]_|password|secret|token|api.key)', value)):
        return 'unknown'
    return value


def context(common, slot=None):
    slot = slot or {}
    return dict(repository=hashlib.sha256(str(common.resolve()).encode()).hexdigest()[:24],
                task_id=label(slot.get('task_id')), attempt_id=label(slot.get('attempt_id', 'unassigned')),
                host=label(slot.get('host') or os.environ.get('AUTOWORK_TELEMETRY_HOST')),
                model=label(slot.get('model') or os.environ.get('AUTOWORK_TELEMETRY_MODEL')))


def fact(ctx, kind, *, scope='attempt', key='', timestamp=None, revision=None):
    identity = [ctx['repository'], ctx['task_id'], kind,
                ctx['attempt_id'] if scope == 'attempt' else 'task', key]
    event = dict(ctx, event=kind, scope=scope, timestamp=time.time() if timestamp is None else timestamp,
                 event_id=hashlib.sha256(json.dumps(identity).encode()).hexdigest())
    if revision:
        event['revision'] = revision
    return event


def current_revision(repo):
    try:
        return execution.git(repo, 'rev-parse', 'HEAD')
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def acceptance(repo, ctx):
    """First reachable committed task record, not its working-tree creation time."""
    path = execution.task_path(ctx['task_id'])
    history = execution.git(repo, 'log', '--reverse', '--diff-filter=A', '--format=%H %ct', 'HEAD', '--', path)
    if not history:
        return []
    revision, stamp = history.splitlines()[0].split()
    return [fact(ctx, 'accepted', scope='task', timestamp=float(stamp), revision=revision)]


def slot_facts(common, slot, previous, observations=()):
    """Durable facts accompany the slot replace, so a missed append can be replayed."""
    slot = dict(slot)
    fresh = not previous or previous.get('attempt', 1) != slot.get('attempt', 1)
    if fresh or not slot.get('attempt_id'):
        slot['attempt_id'] = uuid.uuid4().hex
    slot.setdefault('host', label(os.environ.get('AUTOWORK_TELEMETRY_HOST')))
    slot.setdefault('model', label(os.environ.get('AUTOWORK_TELEMETRY_MODEL')))
    ctx = context(common, slot)
    facts = list((previous or slot).get('lifecycle', []))
    def add(kind, scope='attempt'):
        facts.append(fact(ctx, kind, scope=scope, key='' if scope == 'task' else str(len(facts))))
    before = (previous or {}).get('state')
    after = slot['state']
    if not previous:
        try:
            facts.extend(acceptance(Path(slot['worktree']), ctx))
        except (OSError, ValueError, subprocess.SubprocessError):
            pass  # Older/removed task records are not invented.
    if after == 'dispatched' and (fresh or before != after):
        if previous and fresh:
            add('retry')
        if fresh:
            add('admitted')
            add('dispatched')
        else:
            add('resumed')
    elif after != before:
        if after == 'held':
            if slot.get('cause') in ('validation', 'stale_validation', 'reviewed_twice'):
                add('verification_failed')
            add('held')
        elif after in ('interrupted', 'released'):
            add('interrupted')
        elif after == 'integrated':
            add('reviewed')
            add('integrated')
        elif after == 'closed':
            add('closed', 'task')
        elif before in ('held', 'interrupted', 'released'):
            add('resumed')
    if slot.get('answered', 0) > (previous or {}).get('answered', 0):
        add('blocker_answered')
    for kind in observations:
        add(kind)
    slot['lifecycle'] = facts
    return slot
