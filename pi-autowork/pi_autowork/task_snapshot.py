"""One immutable committed task inventory, with independently observed runtime/pending data.

This is a display model, never admission or Start authority. Only the pinned store
supplies membership; execution observations must prove repository/contract identity.
"""
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
import math
import sys
import time

_ENGINE = str(Path(__file__).resolve().parents[1] / 'engine')
if _ENGINE not in sys.path:
    sys.path.insert(0, _ENGINE)
import task_queue
from task_store import TaskStore, StoreError, _git


@dataclass(frozen=True)
class TaskRow:
    task: str
    short: str
    section: str
    state: str
    kind: str
    why: str = ''
    question: bool = False
    pending: bool = False
    bucket: str = ''


@dataclass(frozen=True)
class Source:
    workspace: str | None = None
    repository_identity: str | None = None
    revision: str | None = None
    observed_at: float | None = None


@dataclass(frozen=True)
class TaskSnapshot:
    workspace: str
    repository_identity: str | None
    revision: str | None
    generation: int
    captured_at: float
    store: TaskStore | None = None
    rows: tuple = ()
    closed_rows: tuple = ()
    counts: tuple | None = None
    goals: tuple = ()
    questions: tuple = ()
    question_rows: tuple = ()
    questions_at: float | None = None
    questions_workspace: str | None = None
    pending_paths: tuple | None = None
    pending_at: float | None = None
    engine_source: Source = Source()
    engine_freshness: str = 'unknown'
    freshness: str = 'unavailable'
    errors: tuple = ()
    annotations: tuple = ()
    joined_lanes: tuple = ()


def _closed_rows(store):
    rows = []
    for record in sorted(store.tasks.values(), key=lambda t: t.id):
        if record.status == 'done':
            info = record.closure_info
            if record.closure == 'coordinator_verified':
                why = info['evidence'] or 'Verification evidence not recorded'
            elif record.closure == 'manual':
                why = (f'Manually closed by {info["actor"] or "unknown"} at {info["timestamp"] or "unknown"}; '
                       f'not coordinator-verified. {info["reason"] or "Reason not recorded"}')
            else:
                why = 'Closure provenance not recorded (legacy); no coordinator verification recorded.'
            rows.append(TaskRow(record.id, record.short or record.title, 'Closed', info['label'], 'closed', why))
    return tuple(rows)


def _canonical_reason(record, store):
    def unfinished(task, dep):
        target = store.tasks.get(dep)
        return (target is None or target.status != 'done'
                or (dep in task.verified_depends_on and not target.qualified))

    def stopping(dep, trail):
        target = store.tasks.get(dep)
        if dep in trail:
            return [dep + ' (dependency cycle)']
        if target is None:
            return [dep + ' (outside inventory)']
        if target.section == 'Needs decision' or target.status == 'superseded':
            return [dep + f' ({target.section if target.status == "open" else target.status})']
        return [root for child in target.depends_on if unfinished(target, child)
                for root in stopping(child, trail | {dep})]

    missing = [dep for dep in record.depends_on if unfinished(record, dep)]
    if missing:
        roots = list(dict.fromkeys(root for dep in missing for root in stopping(dep, {record.id})))
        reason = 'dependency: ' + ', '.join(missing)
        if roots:
            return 'Blocker', reason + '; stopped by ' + ', '.join(roots)
        return 'Waiting', reason
    return 'Waiting', 'ready; awaiting dispatch'


def capture(repo, *, engine_observation, generation, last_good=None):
    """Capture HEAD once; no working files or session branches can add inventory.

    A caller may explicitly supply its last good result after acquisition failure.
    Its inventory revision/time stay original; pending/runtime observations have
    separate provenance and are never silently replaced by empty values.
    """
    from pi_autowork import task_status as view, health
    now = time.time()
    workspace = str(Path(repo).resolve()) if repo else ''
    errors, annotations = [], []
    identity = revision = store = None
    pending = None
    try:
        if not repo:
            raise StoreError('selected repository unavailable')
        identity = str(Path(_git(repo, 'rev-parse', '--path-format=absolute', '--git-common-dir').decode().strip()).resolve())
        revision = task_queue.commit(repo)
        store = task_queue.store(repo, revision) if revision else None
        if store is None:
            raise StoreError('no committed task store')
    except (StoreError, OSError, ValueError) as exc:
        errors.append('inventory: ' + str(exc))
    try:
        if not repo:
            raise StoreError('selected repository unavailable')
        pending = TaskStore.pending(repo)
    except (StoreError, OSError, ValueError) as exc:
        errors.append('pending: ' + str(exc))
    obs = engine_observation or {}
    if not isinstance(obs, dict):
        errors.append('engine observation: expected an object')
        obs = {}
    metadata = obs.get('task_source') or {}
    if not isinstance(metadata, dict):
        errors.append('engine task_source: expected an object')
        metadata = {}
    values = {key: metadata.get(key) for key in Source.__dataclass_fields__}
    for key, value in values.items():
        valid = (isinstance(value, (int, float)) and math.isfinite(value)) if key == 'observed_at' else isinstance(value, str)
        if value is not None and not valid:
            errors.append(f'engine task_source: invalid {key}')
            values[key] = None
    source = Source(**values)
    stamp = source.observed_at
    fresh = (isinstance(stamp, (int, float)) and 0 <= now - stamp <= health.STALE_AFTER
             and not obs.get('status_unavailable_since'))
    same_repo = bool(identity and source.repository_identity == identity)
    engine_freshness = ('fresh' if fresh else 'stale') if stamp is not None else 'unknown'
    if not same_repo:
        engine_freshness = 'unknown'
    if source.revision and source.revision != revision:
        annotations.append(f'session revision {source.revision}; canonical revision {revision}')
    errors.extend(obs.get('errors') or ())
    if obs.get('status_unavailable_since'):
        errors.append('engine observation unavailable; retained observation is stale')
    if store is None:
        if (last_good and last_good.counts is not None and last_good.workspace == workspace
                and (identity is None or last_good.repository_identity == identity)):
            return replace(last_good, generation=generation, freshness='stale', errors=tuple(errors),
                           pending_paths=pending, pending_at=now,
                           engine_source=source if source.observed_at is not None else last_good.engine_source,
                           engine_freshness=engine_freshness if source.observed_at is not None else 'unknown')
        return TaskSnapshot(workspace, identity, revision, generation, now, errors=tuple(errors),
                            pending_paths=pending, pending_at=now, engine_source=source,
                            engine_freshness=engine_freshness)
    raw = obs.get('task_observations', obs.get('tasks')) or []
    # Old health arrays intentionally have no contract identity. They remain annotations.
    observations = [row for row in raw if isinstance(row, dict) and row.get('task')]
    multiplicity = Counter(row['task'] for row in observations)
    records = sorted((t for t in store.tasks.values() if t.status == 'open'),
                     key=lambda t: ({'Now': 0, 'Next': 1, 'Needs decision': 2}.get(t.section, 3), t.rank or 0, t.id))
    current = {t.id: t for t in records}
    compatible = {}
    for row in observations:
        record = current.get(row['task'])
        # Attempts must match the current contract too; today's hash alone cannot
        # bless an older slot or a pre-edit admission.
        admitted = row.get('admitted_contract_hash')
        attempt_state = row.get('state') in (*view.IN_FLIGHT, 'held', 'interrupted', 'released', 'closing')
        valid = (record and same_repo and fresh and source.revision and source.workspace
                 and multiplicity[row['task']] == 1 and row.get('contract_hash') == record.contract_hash
                 and (not attempt_state or admitted == record.contract_hash))
        if valid:
            compatible[row['task']] = row
        else:
            annotations.append(f"{row['task']}: unmatched execution observation ({row.get('state', 'unknown')})")
    if raw and not observations:
        annotations.append('legacy execution observations: contract identity unknown')
    # Aggregated health groups have neither complete membership nor root contract
    # identity. Recompute from compatible observations and validated roots instead.
    roots = []
    for root in obs.get('roots') or []:
        observed = compatible.get(root.get('id'))
        if root.get('kind') == 'runner' and same_repo and fresh:
            roots.append(root)
        elif observed:
            if root.get('kind') == 'held':
                valid_root = observed.get('state') == 'held' and root.get('cause') == observed.get('cause')
            else:
                valid_root = observed.get('state') == 'waiting'
            if valid_root:
                roots.append(root)
    stopped = {}
    for root in roots:
        if health.needs_person(root):
            targets = compatible if root.get('kind') == 'runner' else root.get('tasks') or ()
            for task in targets:
                if compatible.get(task, {}).get('state') == 'waiting':
                    stopped.setdefault(task, health.describe(root))
    lane_groups = {}
    for lane in obs.get('lanes') or []:
        lane_groups.setdefault(lane.task, []).append(lane)
        observed = compatible.get(lane.task, {})
        if (observed.get('state') not in view.IN_FLIGHT or lane.attempt != observed.get('attempt')
                or getattr(lane, 'slot_state', None) != observed.get('state')
                or getattr(lane, 'contract_hash', None) != observed.get('admitted_contract_hash')):
            annotations.append(f'{lane.task}: unmatched slot activity ({lane.phase}); not inventory evidence')
    questions = tuple(obs.get('questions') or ())
    asked = {q.id: q for q in questions}
    rows, joined_lanes = [], []
    for record in records:
        row = compatible.get(record.id, {})
        state, cause = row.get('state'), row.get('cause')
        bucket, why = _canonical_reason(record, store)
        kind, words = 'waiting', view.WAITING
        if record.section == 'Needs decision':
            bucket, why, words = 'Decision', 'needs your decision', 'Waiting · Needs decision'
        elif state in view.IN_FLIGHT:
            phase = view.PHASES[state]
            candidates = lane_groups.get(record.id, [])
            if len(candidates) == 1:
                lane = candidates[0]
                # Do not let an old slot/log upgrade a new observed attempt, or
                # change a reported commit into verified/integrated evidence.
                if (lane.attempt == row.get('attempt') and getattr(lane, 'slot_state', None) == state
                        and getattr(lane, 'contract_hash', None) == row.get('admitted_contract_hash')
                        and isinstance(row.get('started_at'), (int, float))
                        and getattr(lane, 'started_at', None) == row['started_at']
                        and row['started_at'] <= getattr(lane, 'phase_at', 0) <= (stamp or 0)
                        and lane.phase != 'integrated'
                        and (state != 'reported' or view.status(lane)[0] == view.WAITING)):
                    phase = lane.phase
                    joined_lanes.append((lane.task, lane.attempt, lane.phase))
            bucket, detail = view.phase_status(phase)
            words, kind = f'{bucket} · {detail}', 'working'
            why = view.WAIT_LABELS.get(detail, detail.lower()) if bucket == view.WAITING else row.get('reason') or detail
        elif state == 'held':
            bucket = view.WAITING if cause in view.WAIT_CAUSES else view.BLOCKER
            words, kind = f'{bucket} · ' + view.blocker_detail(cause, record.id in asked), 'held'
            why = "waiting for another task's files" if bucket == view.WAITING else view.blocker_detail(cause, record.id in asked)
        elif state in ('waiting', 'pending', 'interrupted', 'released'):
            bucket = view.BLOCKER if record.id in stopped or bucket == view.BLOCKER else view.WAITING
            why = ('behind ' + stopped[record.id]) if record.id in stopped else (
                row.get('reason') or ('paused by a restart' if state in ('interrupted', 'released') else why))
            words = bucket
        if bucket == view.BLOCKER:
            words, kind = (words if words.startswith(view.BLOCKER) else view.BLOCKER), 'held'
        question = asked.get(record.id)
        if question:
            # The question is separate context, not a replacement for bucket provenance.
            why += '; you: ' + question.needs
        edited = pending is not None and record.path in pending
        if edited:
            words += ' · Edit not committed'
        short = ' '.join((record.short or record.title).split())
        rows.append(TaskRow(record.id, short if len(short) <= 40 else short[:39].rstrip() + '…',
                            record.section, words, kind, why, bool(question), edited, bucket))
    counts = Counter(row.bucket for row in rows)
    vector = tuple(counts[b] for b in ('Active', 'Mergeable', 'Waiting', 'Blocker', 'Decision')) + (len(rows),)
    question_rows = tuple(TaskRow(q.id, 'Planning stopped' if q.kind == 'decision' else 'Execution question',
                                 'Annotation', 'Question · not committed open inventory', 'annotation',
                                 'you: ' + q.needs, True) for q in questions if q.id not in current)
    return TaskSnapshot(workspace, identity, revision, generation, now, store=store, rows=tuple(rows),
                        closed_rows=_closed_rows(store), counts=vector,
                        goals=tuple((g.id, g.title) for g in store.goals.values() if g.status != 'met'),
                        questions=questions, question_rows=question_rows, questions_at=obs.get('questions_at'),
                        questions_workspace=obs.get('questions_workspace'), pending_paths=pending, pending_at=now,
                        engine_source=source, engine_freshness=engine_freshness, freshness='fresh',
                        errors=tuple(errors), annotations=tuple(annotations), joined_lanes=tuple(joined_lanes))
