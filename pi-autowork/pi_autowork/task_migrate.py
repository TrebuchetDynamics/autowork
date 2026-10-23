"""`autowork migrate <repo> [--dry-run] [--no-commit] [--accept-consumers]`: convert once.

Tracked code/build/test references to TODO.md or goals.json are listed and block conversion
unless explicitly accepted; documentation references are separate nonblocking drift. Extra
TODO content triggers a CHECKLIST.md snapshot, keeping source bytes and line numbers except
for generated goal coverage (blanked). An existing destination is never overwritten.

It reads TODO.md, goals.json and the archive once, builds tasks/items/ and tasks/goals/,
proves the result first (same task set, same contract fields read back, and the same
selection order as the current TODO.md queue), and only then changes anything. It refuses,
writing nothing, while anything is in flight: a live worker slot or an unfinished
integration or closure, a live lease, a claimed task, uncommitted planning files, or a
repository already converted. There is no reverse migration.

The change is one transaction. The converted commit (tasks/ added, TODO.md and goals.json
removed, no stub; TODO.archive.md stays as history) is built with plumbing and recorded as
refs/autowork/migration before any file changes. Its paths are then staged in the working
tree and index, and HEAD moves to it by compare-and-swap; the ref is deleted last. A run
interrupted at any step leaves that ref, and the next run finishes from wherever it
stopped, or refuses, changing nothing, when a path holds content that is neither the old
nor the converted version. `--no-commit` stops after staging: HEAD stays where it is, and
the owner's commit (or a later run) lands it.

One kind of slot does not stop it: a held slot that only waits for the owner's answer to a
worker-reported blocker (no live worker, no finished commit, not a repeated quick hold).
The runner that would take that answer cannot run before conversion, so the conversion sets
that attempt aside, as `--parallel-set-aside` does (worktrees and branches kept under
-set-aside-N names, the slot moved to slot-history), once the store is proven and before any
file changes; the task then dispatches fresh from its converted record, with whatever answer
its entry now holds.

Work in flight defers a conversion instead of ending it. `autowork tasks prepare` (Docs
Sync) records the owner's request as an intent (convert-intent.json in the execution
state); a runner on this release that finds a legacy repository with that intent drains it
itself: it starts nothing, waits for live workers to stop, sets every remaining attempt
aside as above (worktrees, branches and uncommitted files kept), and converts under its own
coordinator lease, releasing the claims of the attempts it set aside (their tasks convert
open and dispatch fresh). Nothing live is stopped, no lease is broken and no task is closed.

Mapping (lossless; every other label becomes a `- Label: value` note in the body):
rank = 1000 x the queue's human order; Dependencies -> depends_on (task IDs, or the
whole prose clause when it names none, which keeps it waiting as before); Touches ->
touches (none -> ["**"], the whole repository, as an unknown set was treated);
Resources -> the resource tokens the engine enforces today (`port:8080 — ...` is `port`); Kind plan -> kind plan; an owner-only Ownership without a
recorded Live authorization -> ownership owner, otherwise worker; a Live authorization
-> live authorized. The original Ownership, Resources and Live authorization wording is
kept as notes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time

ENGINE = Path(__file__).resolve().parents[1] / 'engine'
sys.path.insert(0, str(ENGINE))
import parallel_plan  # noqa: E402
import task_execution  # noqa: E402  (git only)
from pi_autowork import task_commands  # noqa: E402
from pi_autowork.legacy import conversion_audit, reader  # noqa: E402
import task_select  # noqa: E402
import task_store  # noqa: E402
from task_store import StoreError, TaskStore, WriteError  # noqa: E402

STEP = 1000
PLANNING = ('TODO.md', 'goals.json', 'TODO.archive.md')
CANDIDATE = 'refs/autowork/migration'
SUBJECT = 'chore(tasks): convert to the tasks/ store (autowork migrate)'
TYPED_LABELS = ('Short', 'Status', 'Goal', 'Scope', 'Acceptance', 'Checks', 'Verification',
                'Dependencies', 'Touches', 'Exclusions', 'Kind')
KEPT_AS_NOTES = ('Ownership', 'Resources', 'Live authorization')
# Free text becomes a typed grant only here: a value that says no, or not yet, is refused
# (naming the task) rather than read as authorized, as any non-empty text was before.
NOT_A_GRANT = re.compile(
    # A bare "no" word, alone or followed by punctuation and an explanation ("none (ask)").
    r'(?:none|no|nope|n/?a|na|nil|null|-+|—|–|\?+|tbd|tba|todo|denied|refused|revoked|withdrawn|'
    r'missing|unknown|unauthori[sz]ed)\s*(?:[.;:,!)(—–]\s*.*)?'
    # A phrase that says the grant is still to come, whatever follows it.
    r'|(?:pending|awaiting|not\s+(?:yet|granted|given|recorded|authori[sz]ed)|to\s+be\s+'
    r'(?:decided|confirmed|granted)|ask)\b.*', re.I)


class Refused(Exception):
    """Conversion is unsafe or lossy; nothing was written."""


def _git(repo, *args, env=None, stdin=None):
    # No optional locks: a status read never refreshes the index, so --check writes nothing.
    clean = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')} | {'GIT_OPTIONAL_LOCKS': '0'}
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True,
                            env={**clean, **(env or {})}, input=stdin, timeout=120,
                            errors='replace' if args[0] == 'grep' else None)
    if args[0] == 'grep' and result.returncode == 1:
        return ''  # no matches, not an unreadable snapshot
    if result.returncode:
        raise Refused(f'git {args[0]} failed: {result.stderr.strip()}')
    return result.stdout if '-z' in args else result.stdout.strip()


# --- refusals --------------------------------------------------------------------------

def _ok(repo, *args):
    """git's output, or None when it fails: a missing ref or path is an answer, not an error."""
    try:
        return _git(repo, *args)
    except Refused:
        return None


def committed(repo, rev, path):
    return _ok(repo, 'rev-parse', '--verify', '-q', f'{rev}:{path}') is not None


def awaiting_answer(repo):
    """Held slots that only wait for the owner's answer to a worker-reported blocker: no live
    worker, and not a repeated quick hold (that one needs its Blocker resolution first)."""
    import parallel_state
    common = parallel_state.common_dir(Path(repo))
    try:
        slots = parallel_state.slots(common) if (common / 'slots').is_dir() else []
    except ValueError:
        return []  # busy() reports the unreadable slots
    return [s for s in slots if s['state'] == 'held' and s.get('cause') == 'blocker'
            and not parallel_state.worker_live(s) and not parallel_state.quick_hold(common, s)]


def _own_lease(common, owner_pid):
    """Whether ``owner_pid`` (the draining runner) holds the parallel coordinator lease."""
    import parallel_state
    if owner_pid is None:
        return False
    try:
        current = parallel_state.lease(common)
    except ValueError:
        return False
    return bool(current) and current.get('owner') == task_execution.owner_identity(owner_pid)


def busy(repo, owner_pid=None):
    """What is in flight, as plain sentences: nothing may convert under it. A slot waiting on
    an owner's answer is not in flight: conversion sets it aside. The lease of ``owner_pid``,
    the runner converting after its drain, is its own and not in flight."""
    import parallel_state
    held, problems = task_commands.in_flight(repo)
    if _own_lease(parallel_state.common_dir(Path(repo)), owner_pid):
        problems = [p for p in problems if p != 'a live parallel coordinator lease']
    held -= {s['task_id'] for s in awaiting_answer(repo)}
    if held:
        problems.append('worker slots in flight or unfinished integration/closure: ' + ', '.join(sorted(held)))
    return problems


def set_aside_waiting(repo, owner_pid=None):
    """Set aside every slot waiting on an owner's answer, under the engine's own locks; the
    task dispatches fresh after conversion. Returns their task IDs."""
    import parallel_integrate
    import parallel_state
    common = parallel_state.common_dir(Path(repo))
    done = []
    try:
        with task_execution.lock(common / 'dispatch.lock', 5), task_execution.lock(common / 'integration.lock', 5), \
                task_execution.lock(common / 'writer.lock', 5):
            if parallel_state.live_coordinator(common) and not _own_lease(common, owner_pid):
                raise Refused('a live parallel coordinator lease')
            for slot in awaiting_answer(repo):  # reread under the locks
                parallel_integrate._retire(repo, common, slot, True)
                done.append(slot['task_id'])
    except BlockingIOError:
        raise Refused('the engine is busy (its dispatch, integration or writer lock is held)') from None
    except ValueError as exc:
        raise Refused(f'setting aside a slot waiting on an answer failed: {exc}') from None
    return done


def uncommitted_planning(repo):
    """TODO.md, goals.json and TODO.archive.md paths that differ from HEAD or are untracked
    (by name: porcelain status lines lose their leading space to _git's strip)."""
    changed = _git(repo, 'diff', '--name-only', 'HEAD', '--', *PLANNING).splitlines()
    new = _git(repo, 'ls-files', '--others', '--exclude-standard', '--', *PLANNING).splitlines()
    return sorted({p for p in changed + new if p})


def claimed(repo):
    """Task IDs goals.json marks in_progress (a legacy runner's claims)."""
    try:
        ledger = json.loads((Path(repo) / 'goals.json').read_text())
        return sorted(t['id'] for t in ledger.get('tasks', []) if t.get('status') == 'in_progress')
    except (OSError, ValueError, AttributeError, TypeError):
        return []


def reference_inventory(repo):
    """Tracked working-tree and retained Git-snapshot references (read-only).

    Conversion retains HEAD's other files, not uncommitted repairs. A pending transaction
    retains its candidate instead. Neither repair nor deletion may hide that snapshot.
    """
    try:
        found = conversion_audit.references(repo, [p for p in _git(repo, 'ls-files', '-z').split('\0') if p])
        candidate = pending(repo)
        revision = candidate if candidate and not _stale(repo, candidate, drop=False) else 'HEAD'
        if _ok(repo, 'rev-parse', '--verify', '-q', revision):
            output = _git(repo, 'grep', '--no-color', '--no-textconv', '--full-name', '--no-column',
                          '--no-heading', '--no-break', '--no-recurse-submodules', '-n', '-z', '-I', '-F',
                          '-e', 'TODO.md', '-e', 'goals.json', revision, '--')
            retained = conversion_audit.retained_references(output, revision)
            for group in found:
                for hit in retained[group]:
                    if hit not in found[group]:
                        found[group].append(dict(hit, revision=revision))
                found[group].sort(key=lambda hit: (hit['path'], hit['line'], hit['names']))
        return found
    except OSError as exc:
        raise Refused(f'cannot inspect tracked legacy consumers: {exc}') from None


def consumer_refusal(inventory):
    if not inventory['consumers']:
        return None
    return ('tracked legacy consumers: ' + ', '.join(f"{h['path']}:{h['line']} ({', '.join(h['names'])})"
            for h in inventory['consumers']) + '; repair them first, or explicitly convert with '
            '`autowork migrate --accept-consumers` (consumer code is never rewritten)')


def preservation(repo, converted):
    try:
        snapshot, ranges = conversion_audit.preservation((Path(repo) / 'TODO.md').read_bytes(), converted)
    except (OSError, ValueError) as exc:
        raise Refused(f'cannot account for TODO.md content: {exc}') from None
    if snapshot is not None:
        path = conversion_audit.PRESERVED
        target = Path(repo) / path
        if target.exists() or target.is_symlink() or committed(repo, 'HEAD', path):
            named = ', '.join(f'{start}-{end}' for start, end in ranges)
            raise Refused(f'TODO.md lines {named} need preservation in {path}, but it already exists; '
                          'move that document aside without losing its content, then convert')
    return snapshot, ranges


def preserve_content(repo, files):
    """Add the line-accounted snapshot to a conversion, not to the shared record mapper."""
    active = {t['id']: t for t in reader.ledger(repo)['tasks'] if t['status'] in ('open', 'in_progress')}
    snapshot, ranges = preservation(repo, active)
    if snapshot is not None:
        files[conversion_audit.PRESERVED] = snapshot
        return dict(path=conversion_audit.PRESERVED, line_ranges=ranges)
    return None


def refusals(repo, owner_pid=None, released=()):
    """Every reason conversion may not run now, as plain sentences. ``released``: claimed
    tasks whose attempts a drain set aside; they convert open."""
    repo = Path(repo)
    found = []
    if committed(repo, 'HEAD', 'tasks'):
        found.append('already converted: tasks/ is committed')
    if not (repo / 'TODO.md').is_file() or not (repo / 'goals.json').is_file():
        found.append('TODO.md and goals.json are both needed to convert')
    if dirty := uncommitted_planning(repo):
        found.append('uncommitted planning files: ' + ', '.join(dirty))
    found += busy(repo, owner_pid)
    if held := [tid for tid in claimed(repo) if tid not in set(released)]:
        found.append('claimed tasks (release them first): ' + ', '.join(held))
    return found


def deferrable(found):
    """Whether every refusal is work in flight a drain ends (not a decision or a defect)."""
    kinds = ('worker slots in flight', 'a live parallel coordinator lease', 'a live sequential execution lease',
             'claimed tasks', 'the engine is busy')
    return bool(found) and all(problem.startswith(kinds) for problem in found)


# --- deferred conversion ---------------------------------------------------------------

def _intent_path(repo):
    import parallel_state
    return parallel_state.common_dir(Path(repo)) / 'convert-intent.json'


def intent(repo):
    """The recorded request to convert once work in flight ends, or None."""
    try:
        return json.loads(_intent_path(repo).read_text())
    except (OSError, ValueError):
        return None


def record_intent(repo, requested_by, reasons):
    """Record (idempotently) that the owner asked for this conversion; the runner drains to it."""
    path = _intent_path(repo)
    current = intent(repo)
    if current and current.get('requested_by') == requested_by:
        return current
    value = dict(schema=1, requested_by=requested_by, reasons=list(reasons),
                 head=_ok(repo, 'rev-parse', 'HEAD'))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    os.replace(temporary, path)
    return value


def clear_intent(repo):
    try:
        _intent_path(repo).unlink()
    except FileNotFoundError:
        pass


def _end_process(owner, wait=90.0):
    """Stop the process a lease names (SIGTERM, then SIGKILL), only while that identity holds:
    a reused PID is never signalled. A runner pauses its workers on SIGTERM."""
    pid = owner.get('pid') if isinstance(owner, dict) else None
    for sig, pause in ((signal.SIGTERM, wait), (signal.SIGKILL, 5.0)):
        if not pid or task_execution.identity(pid) != owner:
            return
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            return
        deadline = time.time() + pause
        while time.time() < deadline and task_execution.identity(pid) == owner:
            time.sleep(0.2)


def force_leases(repo, owner_pid):
    """The owner's force: end every other live holder of this repository's coordinator or
    sequential execution lease. Returns what it ended, as sentences."""
    import parallel_state
    common = parallel_state.common_dir(Path(repo))
    ended = []
    current = parallel_state.live_coordinator(common)
    if current and not _own_lease(common, owner_pid):
        _end_process(current['owner'])
        ended.append(f"stopped the runner holding the coordinator lease (PID {current['owner'].get('pid')})")
    sequential = task_execution.read(common / 'active.json') if (common / 'active.json').exists() else None
    if sequential and task_execution.active_owner(sequential):
        _end_process(sequential['owner'])
        ended.append(f"stopped the sequential run holding the execution lease (PID {sequential['owner'].get('pid')})")
    return ended


def commit_planning(repo):
    """The owner's force: commit their uncommitted TODO.md, goals.json and TODO.archive.md
    edits as they are, so the conversion includes them. Returns the paths committed."""
    if dirty := uncommitted_planning(repo):
        _git(repo, 'add', '-A', '--', *dirty)
        _git(repo, 'commit', '-q', '-m', 'docs(tasks): owner planning before a forced conversion', '--', *dirty)
    return dirty


def drain(repo, owner_pid, force=False):
    """The runner's step towards a deferred conversion, under its coordinator lease and the
    engine's locks: every attempt with no live worker is set aside (work kept). Returns
    dict(live=[...], set_aside=[...], landed=[...], blocked=[...]); conversion may run once
    live and blocked are empty. ``landed``: set-aside attempts whose merge is already in
    main but whose task was never closed (it converts open; close it with its evidence). A
    repeated quick hold without its Blocker resolution stays: it needs the owner's answer.

    ``force`` (the owner's /docs_sync force): live workers are stopped and their attempts
    set aside too, and a repeated quick hold is set aside without its answer; ``stopped``
    names them. Work is still never discarded: worktrees, branches and files are kept."""
    import parallel_dispatch
    import parallel_integrate
    import parallel_state
    common = parallel_state.common_dir(Path(repo))
    result = dict(live=[], set_aside=[], landed=[], blocked=[], stopped=[], claimed=False)
    if not _own_lease(common, owner_pid) or not parallel_state.live_coordinator(common):
        # A dead runner's lease is taken over; a live one is never broken (unless forced first).
        taken = parallel_state.claim(Path(repo), owner_pid, max_workers=16)
        if taken['outcome'] != 'CLAIMED':
            raise Refused(f"{taken.get('reason', 'the coordinator lease is held')}: {taken.get('owner')}")
        result['claimed'] = True
    try:
        with task_execution.lock(common / 'dispatch.lock', 5), task_execution.lock(common / 'integration.lock', 5), \
                task_execution.lock(common / 'writer.lock', 5):
            parallel_state.require_owner(common, owner_pid)
            slots = parallel_state.slots(common) if (common / 'slots').is_dir() else []
            for slot in slots:
                if slot['state'] not in task_commands.OCCUPYING:
                    continue
                if parallel_state.worker_live(slot):
                    if not force:
                        result['live'].append(slot['task_id'])
                        continue
                    parallel_dispatch.stop(slot.get('worker'), slot.get('worktree'))
                    if parallel_state.worker_live(slot):
                        result['blocked'].append(f"{slot['task_id']}: its worker survived SIGKILL")
                        continue
                    result['stopped'].append(slot['task_id'])
                merged = slot['state'] in ('integrating', 'integrated') and parallel_integrate.landed(
                    repo, (slot.get('integration') or {}).get('commit'))
                try:
                    try:
                        parallel_integrate._retire(repo, common, slot, True)
                    except ValueError:
                        if not force:
                            raise
                        parallel_integrate._retire(repo, common, slot, False)  # its hold check is waived
                    result['set_aside'].append(slot['task_id'])
                    if merged:
                        result['landed'].append(slot['task_id'])
                except ValueError as exc:
                    result['blocked'].append(f"{slot['task_id']}: {exc}")
    except BlockingIOError:
        if result['claimed']:
            release_drain(repo, owner_pid)
        raise Refused('the engine is busy (its dispatch, integration or writer lock is held)') from None
    except ValueError as exc:
        if result['claimed']:
            release_drain(repo, owner_pid)
        raise Refused(f'the drain could not read or retire a slot: {exc}') from None
    return result


def release_drain(repo, owner_pid):
    """Release the lease a drain claimed, so the runner's engine claims its own workspace."""
    import parallel_state
    parallel_state.release(Path(repo), owner_pid)


def convert_after_drain(repo, owner_pid, force=False):
    """A runner's whole deferred-conversion step: dict(outcome=CONVERTED|WAITING|BLOCKED,
    detail, set_aside). Writes only through drain() and convert(); idempotent. ``force``
    (the owner's): end other lease holders and live workers, commit the owner's planning
    edits, accept reported legacy consumers, and convert now; it never discards work
    and never overwrites unknown content."""
    repo = Path(task_execution.git(Path(repo), 'rev-parse', '--show-toplevel')).resolve()
    ended = force_leases(repo, owner_pid) if force else []
    drained = drain(repo, owner_pid, force)
    drained['ended'] = ended
    try:
        if force:
            drained['committed'] = commit_planning(repo)
        if drained['live']:
            return dict(outcome='WAITING', set_aside=drained['set_aside'],
                        detail='conversion waits for running workers: ' + ', '.join(sorted(drained['live'])))
        if drained['blocked']:
            return dict(outcome='BLOCKED', set_aside=drained['set_aside'],
                        detail='conversion needs an answer first: ' + '; '.join(drained['blocked']))
        try:
            with task_commands.locked(repo):
                result = convert(repo, commit=True, owner_pid=owner_pid, released=claimed(repo),
                                 accept_consumers=force)
        except Refused as exc:
            found = refusals(repo, owner_pid, claimed(repo))
            return dict(outcome='WAITING' if deferrable(found) else 'BLOCKED', set_aside=drained['set_aside'],
                        detail=f'conversion refused: {exc}')
        clear_intent(repo)
        return dict(result, outcome='CONVERTED', set_aside=drained['set_aside'] + result.get('set_aside', []),
                    landed=drained['landed'], stopped=drained['stopped'], ended=ended,
                    committed=drained.get('committed', []),
                    detail=f"converted {result.get('tasks')} tasks and {result.get('goals')} goals")
    finally:
        if drained['claimed']:
            release_drain(repo, owner_pid)


# --- mapping ---------------------------------------------------------------------------

def _owner_only(fields):
    task = {'id': '', 'fields': {k: v for k, v in fields.items() if k != 'Live authorization'}}
    return bool(parallel_plan.authorization_wait(task))


def _task_record(tid, title, entry, fields, rank, known, listed=()):
    """(header fields, body) for one open task, or Refused naming what cannot be held."""
    checks = reader.task_checks(fields)
    deps_text = fields.get('Dependencies', 'None.').strip()
    deps = parallel_plan.dependency_ids(deps_text, known)
    try:
        touches = parallel_plan.paths(fields['Touches']) if fields.get('Touches', '').strip() else ['**']
    except ValueError as exc:
        raise Refused(f'{tid}: Touches cannot be converted ({exc})') from None
    resources = sorted(parallel_plan._resources({'fields': fields}))
    owner_only = _owner_only(fields)
    grant = ' '.join(fields.get('Live authorization', '').split())
    if grant and NOT_A_GRANT.fullmatch(grant):
        raise Refused(f'{tid}: "Live authorization: {grant}" is not a grant; write the authorization '
                      'or remove the line, then convert')
    live = bool(grant)
    header = dict(schema=1, id=tid, title=title, short=fields.get('Short', '').strip() or title,
                  # in_progress reaches here only as a claim a drain released: open again.
                  status='open' if entry['status'] == 'in_progress' else entry['status'],
                  goal=entry['goal'], section=entry['section'], rank=rank,
                  depends_on=list(deps), touches=list(touches), resources=resources,
                  kind='plan' if fields.get('Kind', '').strip().lower() == 'plan' else 'implementation',
                  ownership='owner' if owner_only and not live else 'worker', exclusions=[])
    if live:
        header['live'] = 'authorized'
    if fields.get('Scope', '').strip():
        header['scope'] = fields['Scope'].strip()
    if fields.get('Acceptance', '').strip():
        header['acceptance'] = _items(fields['Acceptance'])
    if checks and checks.strip():
        header['checks'] = _items(checks)
    if fields.get('Exclusions', '').strip():
        header['exclusions'] = [fields['Exclusions'].strip()]
    labels = [label for label, _ in listed]
    repeated = sorted({label for label in labels if labels.count(label) > 1
                       and (label in TYPED_LABELS or label in KEPT_AS_NOTES)})
    if repeated:
        raise Refused(f'{tid}: {", ".join(repeated)} written more than once; keep one, then convert')
    # Every note, repeated ones too: the field parser keeps only labels written once.
    notes = [(label, value) for label, value in (listed or fields.items())
             if label not in TYPED_LABELS or label in KEPT_AS_NOTES]
    if deps and deps_text and deps_text.rstrip('.') != ', '.join(deps):
        notes.append(('Dependencies', deps_text))
    if not fields.get('Touches', '').strip():
        notes.append(('Touches', 'none before conversion; ** stands for the whole repository'))
    return header, _notes(tid, notes)


ITEM = re.compile(r'(?:\d+[.)]|[-*])\s+')


def _items(text):
    """An array field's value: one item per numbered or bulleted point of a value written over
    several lines (`1. ...` / `- ...`, its continuation lines joined), in order; otherwise the
    whole value as one item, its line breaks folded."""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if len(lines) > 1 and ITEM.match(lines[0]):
        items = []
        for line in lines:
            if ITEM.match(line):
                items.append(ITEM.sub('', line, count=1))
            else:
                items[-1] += ' ' + line
        return items
    return [' '.join(lines)]


def _notes(tid, notes):
    lines = []
    for label, value in notes:
        value = ' '.join(str(value).split())
        if not value:
            continue
        if not re.fullmatch(r"[A-Za-z][A-Za-z '-]*", label):
            raise Refused(f'{tid}: field label {label!r} cannot be kept as a note')
        lines.append(f'- {label}: {value}\n')
    return '\n' + ''.join(lines)


def build(repo, released=()):
    """{relative path: text} for the whole store, plus the legacy order it must reproduce.
    ``released`` claims count as open in that order too: their attempts were set aside."""
    repo = Path(repo)
    try:
        inputs = reader.inputs(repo)
        for task in inputs['ledger'].get('tasks', []):
            if task.get('status') == 'in_progress' and task.get('id') in set(released):
                task['status'] = 'open'
        legacy = reader.order(repo, inputs)
    except reader.Drift as exc:
        raise Refused(f'TODO.md order differs from the recorded priority ({exc}); reconcile it first') from None
    except (ValueError, SystemExit) as exc:
        raise Refused(f'the current queue does not validate: {exc}') from None
    ledger, bodies = inputs['ledger'], inputs['bodies']
    tasks = {t['id']: t for t in ledger['tasks']}
    known = set(tasks) | set(bodies)
    record = ledger.get('priority_order') or {}
    sections = ('Now', 'Next', 'Needs decision')
    todo_order = [tid for tid in bodies if tasks.get(tid, {}).get('status') in ('open', 'in_progress')]
    human = [tid for tid in record.get('tasks', []) if tid in todo_order] or todo_order
    human += [tid for tid in todo_order if tid not in human]
    human = sorted(human, key=lambda tid: (sections.index(tasks[tid]['section']), human.index(tid)))
    files = {}
    duplicated = sorted(tid for tid in human if len(bodies[tid]) != 1)
    if duplicated:
        raise Refused('more than one TODO.md entry for ' + ', '.join(duplicated) + '; keep one, then convert')
    for index, tid in enumerate(human):
        body, _mark, _section = bodies[tid][0]
        fields = reader.task_fields(body)
        title = body.splitlines()[0].split('—', 1)[-1].strip(' —:-') or tid
        header, notes = _task_record(tid, title, tasks[tid], fields, STEP * (index + 1), known,
                                     reader.task_field_list(body))
        files[f'tasks/items/{tid}.md'] = _render(tid, header, notes)
    archived = reader.archived_done(repo)
    for tid, entry in tasks.items():
        if entry['status'] in ('done', 'superseded'):
            header = dict(schema=1, id=tid, title=entry.get('title') or tid, status=entry['status'], goal=entry['goal'])
            notes = [('Archived', 'TODO.archive.md')] if tid in archived else []
            if entry['status'] == 'superseded':
                notes.append(('Superseded by', ', '.join(entry.get('superseded_by') or []) + '; '
                              + (entry.get('supersession_reason') or '')))
            files[f'tasks/items/{tid}.md'] = _render(tid, header, _notes(tid, notes))
    # Dependencies on tasks that exist only in the archive stay satisfied.
    needed = {d for tid in human for d in parallel_plan.dependency_ids(
        reader.task_fields(bodies[tid][0][0]).get('Dependencies', 'None.'), known)}
    for tid in sorted(needed & archived - set(tasks)):
        files[f'tasks/items/{tid}.md'] = _render(tid, dict(schema=1, id=tid, title=tid, status='done'),
                                                 _notes(tid, [('Archived', 'TODO.archive.md')]))
    focus = ledger.get('primary_milestone')
    for goal in ledger['goals']:
        header = dict(schema=1, id=goal['id'], title=goal['title'], priority=goal['priority'],
                      source=goal['source'], status=goal['status'], focus=goal['id'] == focus,
                      depends_on=list(goal.get('depends_on') or []))
        notes = [('Evidence', f"{e.get('kind', '')}: {e.get('ref', '')} ({e.get('result', '')})")
                 for e in goal.get('evidence') or []]
        try:
            files[f'tasks/goals/{goal["id"]}.md'] = task_store.render(header, _notes(goal['id'], notes), goal=True)
        except WriteError as exc:
            raise Refused(f'{goal["id"]}: {exc}') from None
    return files, legacy, set(tasks)


def _render(tid, header, body):
    try:
        return task_store.render(header, body)
    except WriteError as exc:
        raise Refused(f'{tid}: {exc}') from None


# --- proof and write -------------------------------------------------------------------

def converted_tree(repo, files, *, env=None):
    """Build a conversion in the selected object store, without editing files/index."""
    with tempfile.TemporaryDirectory() as tmp:
        env = {**(env or {}), 'GIT_INDEX_FILE': str(Path(tmp) / 'index')}
        _git(repo, 'read-tree', 'HEAD', env=env)
        for path, text in files.items():
            oid = _git(repo, 'hash-object', '-w', '--stdin', stdin=text, env=env)
            _git(repo, 'update-index', '--add', '--cacheinfo', f'100644,{oid},{path}', env=env)
        _git(repo, 'update-index', '--force-remove', '--', 'TODO.md', 'goals.json', env=env)
        return _git(repo, 'write-tree', env=env)


def proof_store(repo, tree, *, env):
    """The converted tree read back through a throwaway commit."""
    ident = {'GIT_AUTHOR_NAME': 'autowork', 'GIT_AUTHOR_EMAIL': 'autowork@localhost',
             'GIT_COMMITTER_NAME': 'autowork', 'GIT_COMMITTER_EMAIL': 'autowork@localhost'}
    commit = _git(repo, 'commit-tree', tree, '-p', 'HEAD', '-m', 'migration proof', env={**env, **ident})
    try:
        return TaskStore.at(repo, commit, env=env)
    except StoreError as exc:
        raise Refused(f'the converted store does not validate: {exc}') from None


def prove(repo, tree, legacy, ids, *, env):
    store = proof_store(repo, tree, env=env)
    missing = sorted(ids - set(store.tasks))
    if missing:
        raise Refused('tasks missing from the converted store: ' + ', '.join(missing))
    new = [t.id for t in task_select.order(store)]
    if new != legacy:
        raise Refused(f'selection order differs: TODO.md queue {legacy}, converted {new}')
    return store


# --- the transaction -------------------------------------------------------------------

def _changes(repo, old, new):
    """[(path, mode, old oid, new oid)] from ``old`` to ``new``; a zero oid is an absent file."""
    out = _git(repo, 'diff-tree', '-r', '--no-renames', '-z', old, new).split('\0')
    changes = []
    for meta, path in zip(out[0::2], out[1::2]):
        if meta:
            _old_mode, mode, old_oid, new_oid, _status = meta.lstrip(':').split()
            changes.append((path, mode, old_oid, new_oid))
    return changes


def _blob_id(repo, data):
    """The object ID ``data`` would have, computed without writing an object."""
    algorithm = _ok(repo, 'rev-parse', '--show-object-format') or 'sha1'
    return hashlib.new(algorithm, b'blob %d\0' % len(data) + data).hexdigest()


def _staged(repo, path):
    entry = _git(repo, 'ls-files', '-s', '--', path)
    return entry.split()[1] if entry else None


def stage(repo, old, new):
    """Bring the working tree and index of every path ``old``..``new`` changes to ``new``.
    A path may already be in either version (an interrupted run stopped part-way); any other
    content refuses before anything is written. A path whose new version is staged keeps its
    working-tree file, which may hold later edits."""
    zero = '0' * len(old)
    plan = []
    for path, mode, old_oid, new_oid in _changes(repo, old, new):
        index = _staged(repo, path) or zero
        if index == new_oid:
            continue
        if index != old_oid:
            raise Refused(f'{path} is staged with content that is neither the old nor the converted version')
        target = Path(repo) / path
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise Refused(f'{path} is not a regular file; move it aside, then run again')
        present = _blob_id(repo, target.read_bytes()) if target.is_file() else zero
        if present not in (old_oid, new_oid):
            raise Refused(f'{path} holds working-tree content that is neither the old nor the converted '
                          'version; move it aside, then run again')
        plan.append((path, mode, new_oid))
    for path, _mode, new_oid in plan:
        target = Path(repo) / path
        if new_oid == zero:
            target.unlink(missing_ok=True)
            continue
        data = subprocess.run(['git', '-C', str(repo), 'cat-file', 'blob', new_oid], capture_output=True,
                              check=True, timeout=60).stdout
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(f'.{target.name}.{os.getpid()}.tmp')
        tmp.write_bytes(data)
        os.replace(tmp, target)
    if plan:
        _git(repo, 'update-index', '--index-info',
             stdin=''.join(f'{"0" if oid == zero else mode} {oid}\t{path}\n' for path, mode, oid in plan))


def finish(repo, candidate, commit=True):
    """Land a recorded conversion from wherever it stopped; returns the outcome."""
    old = _git(repo, 'rev-parse', f'{candidate}^')
    head = _git(repo, 'rev-parse', 'HEAD')
    if head not in (old, candidate):
        if committed(repo, 'HEAD', 'tasks') and not committed(repo, 'HEAD', 'TODO.md'):
            _git(repo, 'update-ref', '-d', CANDIDATE, candidate)  # landed by its own commit
            return 'ALREADY_CONVERTED'
        raise Refused(f'the conversion recorded at {CANDIDATE} ({candidate[:12]}) was built on {old[:12]}, '
                      f'but HEAD is now {head[:12]} and the conversion is staged; commit or unstage it, then run again')
    stage(repo, old, candidate)
    if head == old and not commit:
        return 'STAGED'
    if head == old:
        _git(repo, 'update-ref', '-m', 'autowork migrate', 'HEAD', candidate, old)
    _git(repo, 'update-ref', '-d', CANDIDATE, candidate)
    return 'CONVERTED'


def _stale(repo, candidate, drop=True):
    """A conversion on an older HEAD with nothing staged/written must be rebuilt.
    ``drop=False`` detects this read-only for previews and retained-snapshot inventories."""
    old = _git(repo, 'rev-parse', f'{candidate}^')
    if _git(repo, 'rev-parse', 'HEAD') in (old, candidate) or committed(repo, 'HEAD', 'tasks'):
        return False
    zero = '0' * len(old)
    for path, _mode, _old_oid, new_oid in _changes(repo, old, candidate):
        if new_oid != zero and ((Path(repo) / path).exists() or _staged(repo, path)):
            return False
    if drop:
        _git(repo, 'update-ref', '-d', CANDIDATE, candidate)
    return True


def pending(repo):
    """The recorded, unfinished conversion's commit, or None."""
    return _ok(repo, 'rev-parse', '--verify', '-q', CANDIDATE)


def migrate(repo, dry_run=False, commit=True, accept_consumers=False):
    """Convert under the repository's task lock."""
    repo = Path(task_execution.git(Path(repo), 'rev-parse', '--show-toplevel')).resolve()
    with task_commands.locked(repo):
        return convert(repo, dry_run, commit, accept_consumers=accept_consumers)


def convert(repo, dry_run=False, commit=True, owner_pid=None, released=(), accept_consumers=False):
    """Convert, or finish a recorded conversion; the caller holds the task lock. A draining
    runner passes its own pid (its lease is not in flight) and the claims it released."""
    candidate = pending(repo)
    if candidate and _stale(repo, candidate, drop=not dry_run):
        candidate = None
    inventory = reference_inventory(repo)
    if candidate:
        reason = consumer_refusal(inventory)
        if dry_run:
            return dict(outcome='PENDING', candidate=candidate, refusals=[reason] if reason and not accept_consumers
                        else [], **inventory)
        if reason and not accept_consumers:
            raise Refused(reason)
        if found := busy(repo, owner_pid):
            raise Refused('; '.join(found))
        outcome = finish(repo, candidate, commit)
        summary = dict(outcome=outcome, candidate=candidate, resumed=True, **inventory)
        if committed(repo, candidate, conversion_audit.PRESERVED):
            summary['preserved'] = dict(path=conversion_audit.PRESERVED)
        if outcome == 'CONVERTED':
            summary['commit'] = _git(repo, 'rev-parse', '--short', 'HEAD')
        return summary
    if found := refusals(repo, owner_pid, released):
        raise Refused('; '.join(found))
    if not dry_run and not accept_consumers and (reason := consumer_refusal(inventory)):
        raise Refused(reason)
    files, legacy, ids = build(repo, released)
    kept = preserve_content(repo, files)
    with task_store.temporary_objects(repo) as env:
        tree = converted_tree(repo, files, env=env)
        store = prove(repo, tree, legacy, ids, env=env)
    summary = dict(outcome='DRY_RUN' if dry_run else 'CONVERTED', tasks=len(store.tasks), goals=len(store.goals),
                   order=legacy, **inventory)
    if kept:
        summary['preserved'] = kept
    if reason := consumer_refusal(inventory):
        summary['refusals'] = [] if accept_consumers else [reason]
    waiting = sorted(s['task_id'] for s in awaiting_answer(repo))
    if dry_run:
        if waiting:
            summary['would_set_aside'] = waiting
        return summary
    if waiting:
        summary['set_aside'] = set_aside_waiting(repo, owner_pid)
    # Only an actual conversion persists the proven tree; its proof commit never does.
    tree = converted_tree(repo, files)
    head = _git(repo, 'rev-parse', 'HEAD')
    candidate = _git(repo, 'commit-tree', tree, '-p', head, '-m', SUBJECT, '-m',
                     f'{len(store.tasks)} tasks and {len(store.goals)} goals; selection order unchanged. '
                     'TODO.archive.md stays as history.')
    _git(repo, 'update-ref', '-m', 'autowork migrate: candidate', CANDIDATE, candidate, '')
    summary.update(outcome=finish(repo, candidate, commit), candidate=candidate)
    if summary['outcome'] == 'CONVERTED':
        summary['commit'] = _git(repo, 'rev-parse', '--short', 'HEAD')
        clear_intent(repo)  # however it converted, nothing is left to defer
    return summary


def add_parser(sub):
    p = sub.add_parser('migrate', help='convert a repository to the tasks/ store once (local commit)')
    p.add_argument('repo', nargs='?', default='.')
    p.add_argument('--dry-run', action='store_true', help='check and show the result; write nothing')
    p.add_argument('--no-commit', action='store_true', help='stage the conversion; never move HEAD')
    p.add_argument('--accept-consumers', action='store_true',
                   help='explicitly accept reported code/build/test references to the removed legacy files')
    # The runner's deferred-conversion step, run as its helper (engine leases name an ancestor).
    p.add_argument('--after-drain', action='store_true', help=argparse.SUPPRESS)
    p.add_argument('--owner-pid', type=int, help=argparse.SUPPRESS)
    p.add_argument('--force', action='store_true', help=argparse.SUPPRESS)
    return p


def run(args, repo):
    if args.after_drain:
        try:
            step = convert_after_drain(repo, args.owner_pid, args.force)
        except Refused as exc:
            step = dict(outcome='BLOCKED', detail=str(exc), set_aside=[])
        print(json.dumps(step, indent=2))
        return 0
    try:
        result = migrate(repo, args.dry_run, not args.no_commit, args.accept_consumers)
    except Refused as exc:
        print(f'autowork migrate: refused, nothing written: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0
