"""Model-based checks of the parallel worker slot state machine (stdlib only).

A seeded random walk drives the public parallel_state API (create, transition,
retry, pause, reconcile, rescope, reoffer, readopt, coordinator restart) against a
real disposable Git repository, alongside a small reference model of what every
slot should hold. Crash injection fails the atomic replace or the journal append,
and corrupt slot files must fail closed. After each step the disk is compared with
the model and with structural invariants (see ``Walk.check``).

Replay: a failure prints the seed, the step trace and a shrunk trace. Set
``AUTOWORK_STATE_MODEL_SEEDS=7,8`` and ``AUTOWORK_STATE_MODEL_STEPS=200`` to walk
other seeds, or ``AUTOWORK_STATE_MODEL_TRACE='<json list>'`` to replay one trace
exactly. The defaults are fixed so the suite stays deterministic and fast.
"""
import copy
import json
import os
from pathlib import Path
import random
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import task_execution as execution
import parallel_dispatch as dispatch
import parallel_state as state

TASKS = ('A', 'B', 'C')
STATES = tuple(state.TRANSITIONS)
FAKE = 'f' * 40
DEFAULT_SEEDS = (1, 2, 3)
DEFAULT_STEPS = 40
# Writes that do not go through change(): rescope, reoffer and readopt return a held commit
# to reported; reconcile resumes (held -> interrupted) or re-holds (held -> held) an old
# host-only blocker; pause marks a live worker in place. parallel_integrate makes the same
# held -> interrupted write for a reverify or an answered blocker.
EXTRA_EDGES = {('held', 'reported'), ('held', 'interrupted'), ('held', 'held'),
               ('dispatched', 'dispatched'), ('running', 'running')}
HOST_ONLY = 'flaky tests unrelated to this change; needs a quieter host'
REPORTS = {'none': None, 'empty': [], 'input': ['needs an API key for the payment sandbox'],
           'host': [HOST_ONLY]}
TOUCHES = {'file': 'src/x.py', 'dir': 'src/', 'other': 'docs/', 'none': ''}
DIVERGED = 'worker HEAD does not descend from baseline'
MODEL_FIELDS = ('worker', 'reason', 'commit', 'paused', 'cause', 'outside', 'check')
TODO = '# Work queue\n## Next\n' + ''.join(
    f'- [ ] {t} — Fixture {t}\n- Scope: Change {t.lower()}.txt.\n- Acceptance: Changed.\n'
    f'- Checks: Check it.\n- Dependencies: None.\n- Touches: {t.lower()}.txt\n\n' for t in TASKS)


def updates_for(key, task, paths):
    """Concrete update menus; ``'live'`` becomes a freshly spawned worker identity."""
    scope = {'cause': 'scope', 'reason': state.SCOPE_HOLD + ': src/x.py', 'outside': ['src/x.py']}
    r2 = str(paths[task + '-r2'])
    return {
        'none': {}, 'reason': {'reason': 'fixture reason'}, 'live': {'worker': 'live'},
        'dead': {'worker': None}, 'paused': {'paused': True, 'reason': 'fixture stop'},
        'empty': {'reason': state.EMPTY}, 'scope': dict(scope, commit=FAKE), 'scope_nocommit': scope,
        'overlap': {'cause': 'overlap', 'reason': 'overlap with another slot', 'commit': FAKE},
        'report': {'cause': 'report', 'reason': 'report mismatch', 'commit': FAKE},
        'blocker': {'cause': 'blocker', 'reason': 'worker reported a blocker: input'},
        'validation': {'cause': 'validation', 'reason': 'validation failed', 'commit': FAKE},
        'commit': {'commit': FAKE}, 'bogus': {'task_id': 'Z'}, 'unknown_cause': {'cause': 'typo'},
        'r2': {'worktree': r2, 'branch': f'autowork/{task}-r2', 'baseline': paths['base']},
        'r2_same': {'worktree': str(paths[task]), 'branch': f'autowork/{task}-r2', 'baseline': paths['base']},
        'r2_badbranch': {'worktree': r2, 'branch': f'autowork/{task}', 'baseline': paths['base']},
    }[key]


class Repo:
    """A disposable repository with a root commit, a baseline and a sibling of the baseline."""

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        (self.repo / 'file').write_text('root')
        self.git('add', '.')
        self.git('commit', '-qm', 'root')
        self.root_commit = self.git('rev-parse', 'HEAD')
        (self.repo / 'TODO.md').write_text(TODO)
        self.git('add', '.')
        self.git('commit', '-qm', 'base')
        self.base = self.git('rev-parse', 'HEAD')
        self.sibling = self.git('commit-tree', self.base + '^{tree}', '-p', self.root_commit, '-m', 'sibling')
        self.owner = os.getppid()
        self.common = state.common_dir(self.repo)
        state.claim(self.repo, self.owner, profile='fixture')
        self.paths = {'base': self.base}

    def git(self, *args, repo=None):
        return execution.git(repo or self.repo, *args)

    def worktree(self, name):
        path = self.root / name
        self.git('worktree', 'add', '-qb', 'autowork/' + name, str(path))
        self.paths[name] = path
        return path


def blank(attempt=1):
    return dict(state='dispatched', attempt=attempt, worktree=None, branch=None, worker=None, paused=False,
                cause=None, reason=None, commit=None, outside=None, check=False, rescoped=False, touches=None,
                contract=None, reoffered=frozenset(), readopted=False, data_attempt=None, prev=[])


class Walk:
    """One random walk: the system under test, its reference model and the step trace."""

    def __init__(self, case, root):
        self.case = case
        self.fx = Repo(root)
        for task in TASKS:
            self.fx.worktree(task)
            self.fx.worktree(task + '-r2')
        self.model = {t: None for t in TASKS}
        self.claim_gen, self.paused_claim = 0, {}  # coordinator claims; claim that paused each task
        self.alive = {}  # pid -> Popen of a fixture worker process
        self.trees = {str(self.fx.paths[n]): dict(moved=False, dirty=False, head=self.fx.base, diverged=False)
                      for n in self.fx.paths if n != 'base'}
        self.reports = {}
        self.journal_seen = 0
        self.last_event = {}  # task -> state the journal last recorded
        self.lagging = set()  # tasks whose latest write lost its journal line (injected)
        self.attempts = {}
        self.counter = 0

    # -- helpers -----------------------------------------------------------------------
    @property
    def common(self):
        return self.fx.common

    def close(self):
        for proc in self.alive.values():
            self.reap(proc)

    @staticmethod
    def reap(proc):
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        proc.wait()

    def spawn(self):
        proc = subprocess.Popen(['sleep', '300'], start_new_session=True)
        self.alive[proc.pid] = proc
        return proc.pid

    def live(self, rec):
        return rec is not None and rec['worker'] is not None and rec['worker'] in self.alive

    def snapshot(self):
        files = {p.name: p.read_bytes() for p in sorted((self.common / 'slots').glob('*'))} \
            if (self.common / 'slots').exists() else {}
        journal = self.common / 'journal.jsonl'
        return files, journal.read_bytes() if journal.exists() else b''

    def disk(self, task):
        return execution.read(self.common / 'slots' / (task + '.json'))

    @staticmethod
    def strip(rec):
        return {k: v for k, v in rec.items() if k != 'prev'}

    # -- model -------------------------------------------------------------------------
    def m_change(self, task, rec, target, upd):
        """Predicted change(): ('reject', None), ('ok', new) or ('either', new) when the
        held retry pool check (parallel_dispatch.retry_plan) decides."""
        if target not in state.TRANSITIONS[rec['state']]:
            return 'reject', None
        retry = target == 'dispatched'
        extra = set(upd) - state.FIELDS - ({'worktree', 'branch', 'baseline'} if retry else set())
        if extra:
            return 'reject', None
        new = copy.deepcopy(rec)
        resume = bool(rec['paused']) and rec['state'] in ('interrupted', 'released')
        either = False
        if retry:
            if rec['attempt'] >= 2 and not resume or self.live(rec):
                return 'reject', None
            if rec['state'] == 'held':
                either = any(self.live(r) for r in self.model.values())
                if upd.get('branch') != f'autowork/{task}-r2':
                    return 'reject', None
                if not upd.get('worktree') or Path(upd['worktree']).resolve() == Path(rec['worktree']):
                    return 'reject', None
                if (Path(upd['worktree']).resolve() != self.fx.paths[task + '-r2']
                        or upd.get('baseline') != self.fx.base):
                    return 'reject', None
                new['worktree'], new['branch'] = str(Path(upd['worktree']).resolve()), upd['branch']
            elif (upd.get('worktree', rec['worktree']) != rec['worktree']
                  or upd.get('branch', rec['branch']) != rec['branch']
                  or upd.get('baseline', self.fx.base) != self.fx.base):
                return 'reject', None
            new['prev'] = rec['prev'] + [self.strip(rec)]
            for key in MODEL_FIELDS:
                new[key] = blank()[key]
            new['attempt'] = rec['attempt'] if resume else 2
        upd = dict(upd)
        if target in ('interrupted', 'released') and rec['attempt'] == 2 and not upd.get('paused', rec['paused']):
            target = 'held'
            upd.setdefault('cause', 'empty' if str(upd.get('reason', '')).startswith(state.EMPTY) else 'crash')
        if target == 'held':
            upd.setdefault('cause', 'crash')
            if upd['cause'] not in state.HOLD_CAUSES:
                return 'reject', None
        for key, value in upd.items():
            if key in ('worktree', 'branch', 'baseline'):
                continue
            new['check' if key == 'check_failure_resumed' else key] = value
        new['state'] = target
        return ('either' if either else 'ok'), new

    def m_rescopable(self, rec, touches, only):
        declared = TOUCHES[touches]
        return bool(rec and rec['state'] == 'held' and rec['cause'] == 'scope' and rec['commit']
                    and (not rec['rescoped'] or only) and not self.live(rec) and rec['outside']
                    and declared in ('src/x.py', 'src/'))

    def m_first_held(self, rec):
        held = [r for r in rec['prev'] if r['state'] == 'held']
        return held[0] if len(held) == 1 else {}

    def m_readoptable(self, rec):
        first = self.m_first_held(rec)
        return bool(rec and rec['state'] == 'held' and rec['attempt'] == 2 and not rec['commit']
                    and not rec['readopted'] and not self.live(rec) and first.get('state') == 'held'
                    and first.get('commit') and str(first.get('reason') or '').startswith(state.SCOPE_HOLD))

    def m_exhausted(self, rec):
        return (rec['state'] == 'held' and (rec['attempt'] >= 2 or rec['cause'] in state.NEEDS_PERSON)
                and not self.m_readoptable(rec))

    def m_check_resumed(self, rec):
        return rec['check'] or any(r['check'] for r in rec['prev'])

    def report(self, rec, task):
        return self.reports.get((task, rec['data_attempt'] or rec['attempt']))

    def m_reconcile(self):
        """Predicted reconcile(): {task: new record} for every slot it writes."""
        writes = {}
        for task in sorted(t for t in TASKS if self.model[t]):
            rec = self.model[task]
            live = self.live(rec)
            old_blocker = rec['state'] == 'held' and rec['cause'] == 'blocker' and not rec['commit'] and not live
            if rec['state'] not in ('dispatched', 'running') and not old_blocker:
                continue
            blockers = self.report(rec, task)
            host_only = dispatch.check_only_blockers(blockers)
            if old_blocker and not host_only:
                continue
            upd = {}
            if live:
                target = 'running'
                if rec['state'] == 'running' and rec['paused'] and self.paused_claim.get(task) != self.claim_gen:
                    new = copy.deepcopy(rec)
                    new['paused'] = False
                    writes[task] = self.model[task] = new
            else:
                tree = self.trees[rec['worktree']]
                if old_blocker and (tree['moved'] or not tree['dirty']):
                    continue
                if tree['moved']:
                    if tree['diverged']:
                        target, upd = 'held', {'reason': DIVERGED, 'cause': 'diverged'}
                    else:
                        target, upd = 'reported', {'commit': tree['head']}
                        if tree['dirty']:
                            upd['reason'] = 'commit retained; uncommitted work also preserved'
                elif blockers:
                    if tree['dirty'] and host_only:
                        repeated = self.m_check_resumed(rec)
                        target = 'held' if repeated else 'interrupted'
                        upd = {'reason': state.blocker_reason(blockers), 'check_failure_resumed': True,
                               'paused': not repeated, 'cause': 'timeout' if repeated else None}
                        if old_blocker:
                            new = copy.deepcopy(rec)
                            new.update(state=target, reason=upd['reason'], check=True, paused=upd['paused'],
                                       cause=upd['cause'])
                            writes[task] = self.model[task] = new
                            continue
                    else:
                        target, upd = 'held', {'reason': state.blocker_reason(blockers), 'cause': 'blocker'}
                elif blockers == [] and not tree['dirty'] and not rec['paused']:
                    target, upd = 'held', {'reason': 'its worker found nothing to change: see report.json',
                                           'cause': 'no_change'}
                else:
                    target = 'interrupted' if tree['dirty'] else 'released'
                    reason = 'dead worker with uncommitted changes' if tree['dirty'] else state.EMPTY
                    if rec['paused']:
                        reason = f'stopped by a runner restart; resumes on attempt {rec["attempt"]}'
                        if tree['dirty']:
                            reason += ' with uncommitted changes'
                    upd = {'reason': reason}
            if target != rec['state']:
                outcome, new = self.m_change(task, rec, target, upd)
                assert outcome == 'ok', (task, rec['state'], target, outcome)
                writes[task] = self.model[task] = new
        return writes

    # -- views and invariants ----------------------------------------------------------
    @staticmethod
    def view_disk(slot):
        worker = slot.get('worker')
        return dict(state=slot['state'], attempt=slot['attempt'], worktree=slot['worktree'], branch=slot['branch'],
                    worker=worker['pid'] if worker else None, paused=bool(slot.get('paused')),
                    cause=slot.get('cause'), reason=slot.get('reason'), commit=slot.get('commit'),
                    outside=slot.get('outside'), check=bool(slot.get('check_failure_resumed')),
                    rescoped=bool(slot.get('rescoped')), touches=slot.get('touches'),
                    contract=slot.get('rescoped_contract'), reoffered=frozenset(state.reoffered(slot)),
                    readopted=bool(slot.get('readopted')), data_attempt=slot.get('data_attempt'),
                    prev=len(slot.get('previous_attempts', [])))

    @staticmethod
    def view_model(rec):
        return dict(Walk.strip(rec), paused=bool(rec['paused']), check=bool(rec['check']), prev=len(rec['prev']))

    def check(self, writes):
        tc = self.case
        # 1. Every slot file is valid JSON in a known state with attempt 1 or 2 (slots() fails closed
        #    otherwise), and no half-written temporary file survives a step.
        slots = {s['task_id']: s for s in state.slots(self.common)}
        tc.assertEqual([p.name for p in (self.common / 'slots').glob('.execution-*')], [])
        # 2. The disk equals the model, slot by slot; no slot appears without a create.
        tc.assertEqual(set(slots), {t for t in TASKS if self.model[t]})
        for task, slot in slots.items():
            rec = self.model[task]
            tc.assertEqual(self.view_disk(slot), self.view_model(rec), f'slot {task} diverged from the model')
            # A held slot always has a known, recoverable cause.
            if slot['state'] == 'held':
                tc.assertIn(slot['cause'], state.HOLD_CAUSES)
            # 3. Attempts never decrease and never exceed 2.
            tc.assertGreaterEqual(slot['attempt'], self.attempts.get(task, 1))
            self.attempts[task] = slot['attempt']
            # 4. The derived queries agree with the model.
            tc.assertEqual(state.readoptable(slot), self.m_readoptable(rec), task)
            tc.assertEqual(state.exhausted(slot), self.m_exhausted(rec), task)
            tc.assertEqual(state.worker_live(slot), self.live(rec), task)
        # 5. No two slots share a worktree or a branch.
        for key in ('worktree', 'branch'):
            values = [s[key] for s in slots.values()]
            tc.assertEqual(len(values), len(set(values)), f'two slots share a {key}')
        # 6. The journal is complete JSON lines; each step appends exactly one slot_changed per
        #    write, along TRANSITIONS or a documented extra edge, chained to the last state.
        data = (self.common / 'journal.jsonl').read_bytes()
        tc.assertTrue(data.endswith(b'\n'))
        fresh = [json.loads(line) for line in data[self.journal_seen:].splitlines()]
        self.journal_seen = len(data)
        changes = [e for e in fresh if e['event'] == 'slot_changed']
        tc.assertEqual(sorted(e['task_id'] for e in changes), sorted(writes),
                       'journal lines do not match the writes the model expected')
        for item in changes:
            task, before, after = item['task_id'], item['previous_state'], item['state']
            if before is None:
                tc.assertEqual(after, 'dispatched')
            else:
                tc.assertTrue(after in state.TRANSITIONS[before] or (before, after) in EXTRA_EDGES,
                              f'journal edge {before} -> {after} is not a known transition')
            if task not in self.lagging and task in self.last_event:
                tc.assertEqual(before, self.last_event[task], f'journal chain broken for {task}')
            self.lagging.discard(task)
            self.last_event[task] = after
            if task not in self.lagging:
                tc.assertEqual(item['slot'], slots[task], 'journal slot differs from disk')

    # -- operations --------------------------------------------------------------------
    def resolve(self, upd):
        if upd.get('worker') == 'live':
            return dict(upd, worker=execution.identity(self.spawn()))
        return upd

    def apply(self, op):
        kind, *args = op
        return getattr(self, 'op_' + kind)(*args)

    def unchanged(self, before):
        self.case.assertEqual(self.snapshot(), before, 'a refused operation changed state')
        return {}

    def op_create(self, task, worker):
        before = self.snapshot()
        upd = self.resolve({'worker': worker} if worker else {})
        call = lambda: state.create_slot(self.fx.repo, self.fx.owner, task, worktree=str(self.fx.paths[task]),
                                         branch='autowork/' + task, baseline=self.fx.base, **upd)
        if self.model[task] is not None:
            with self.case.assertRaises(ValueError):
                call()
            return self.unchanged(before)
        call()
        rec = blank()
        rec.update(worktree=str(self.fx.paths[task]), branch='autowork/' + task,
                   worker=upd['worker']['pid'] if upd.get('worker') else None)
        self.model[task] = rec
        return {task: rec}

    def op_transition(self, task, target, key, crash):
        rec = self.model[task]
        before = self.snapshot()
        raw = updates_for(key, task, self.fx.paths)
        upd = self.resolve(raw)
        model_upd = dict(upd, worker=upd['worker']['pid']) if upd.get('worker') else upd
        call = lambda: state.transition(self.fx.repo, self.fx.owner, task, target, **upd)
        if rec is None:
            with self.case.assertRaisesRegex(ValueError, 'unknown worker slot'):
                call()
            return self.unchanged(before)
        outcome, new = self.m_change(task, rec, target, model_upd)
        if outcome == 'reject':
            with self.case.assertRaises(ValueError):
                call()
            return self.unchanged(before)
        if crash == 'save':
            # Crash before the atomic replace: the old record stays, no temporary file remains.
            with patch.object(execution.os, 'replace', side_effect=OSError('injected crash')):
                try:
                    call()
                except ValueError:
                    self.case.assertEqual(outcome, 'either')
                except OSError:
                    pass
                else:
                    self.case.fail('injected replace failure did not surface')
            return self.unchanged(before)
        try:
            if crash == 'journal':
                # Crash after the slot is durable but before its journal line.
                with patch.object(state, 'event', side_effect=OSError('injected crash')):
                    with self.case.assertRaises(OSError):
                        call()
            else:
                call()
        except ValueError as exc:
            if outcome != 'either' or 'conflicts with worker pool' not in str(exc):
                raise
            return self.unchanged(before)
        self.model[task] = new
        if crash == 'journal':
            self.lagging.add(task)
            return {}
        return {task: new}

    def op_kill(self, task):
        rec = self.model[task]
        if self.live(rec):
            self.reap(self.alive.pop(rec['worker']))
        return {}

    def tree(self, task):
        rec = self.model[task]
        return (Path(rec['worktree']), self.trees[rec['worktree']]) if rec else (None, None)

    def op_dirty(self, task):
        path, tree = self.tree(task)
        if path:
            self.counter += 1
            (path / f'wip-{self.counter}.txt').write_text('uncommitted')
            tree['dirty'] = True
        return {}

    def op_commit(self, task):
        path, tree = self.tree(task)
        if path and not tree['diverged']:
            self.counter += 1
            (path / f'work-{self.counter}.txt').write_text('work')
            self.fx.git('add', '-A', repo=path)
            self.fx.git('commit', '-qm', 'worker', repo=path)
            tree.update(moved=True, dirty=False, head=self.fx.git('rev-parse', 'HEAD', repo=path))
        return {}

    def op_diverge(self, task):
        path, tree = self.tree(task)
        if path:
            self.fx.git('reset', '-q', '--hard', self.fx.sibling, repo=path)
            tree.update(moved=True, head=self.fx.sibling, diverged=True)
        return {}

    def op_report(self, task, kind):
        rec = self.model[task]
        if rec is None:
            return {}
        number = rec['data_attempt'] or rec['attempt']
        path = self.common / 'slot-data' / task / f'attempt-{number}' / 'report.json'
        if REPORTS[kind] is None:
            path.unlink(missing_ok=True)
        else:
            execution.save(path, {'task': task, 'blockers': REPORTS[kind]})
        self.reports[(task, number)] = REPORTS[kind]
        return {}

    def op_pause(self):
        expected, writes = [], {}
        for task in TASKS:
            rec = self.model[task]
            if rec and rec['state'] in ('dispatched', 'running') and self.live(rec) and not rec['paused']:
                rec['paused'] = True
                self.paused_claim[task] = self.claim_gen
                expected.append(task)
                writes[task] = rec
        self.case.assertEqual(state.pause(self.fx.repo, self.fx.owner)['paused'], expected)
        return writes

    def op_reconcile(self):
        writes = self.m_reconcile()
        result = state.reconcile(self.fx.repo, self.fx.owner)
        # Reconcile is idempotent: an immediate second pass writes nothing.
        journal = (self.common / 'journal.jsonl').read_bytes()
        self.case.assertEqual(state.reconcile(self.fx.repo, self.fx.owner), result)
        self.case.assertEqual((self.common / 'journal.jsonl').read_bytes(), journal)
        return writes

    def op_restart(self, task):
        before = self.snapshot()
        state.release(self.fx.repo, self.fx.owner)
        # Without a live coordinator nothing may change a slot.
        with self.case.assertRaises(ValueError):
            state.transition(self.fx.repo, self.fx.owner, task, 'held')
        with self.case.assertRaises(ValueError):
            state.reconcile(self.fx.repo, self.fx.owner)
        self.case.assertEqual(state.claim(self.fx.repo, self.fx.owner, profile='fixture')['outcome'], 'CLAIMED')
        self.claim_gen += 1
        self.case.assertEqual(self.snapshot()[0], before[0], 'a coordinator restart changed slot records')
        return {}

    def op_rescope(self, task, touches, only, contract):
        rec = self.model[task]
        if rec is None:
            return {}
        slot = self.disk(task)
        predicted = self.m_rescopable(rec, touches, only)
        self.case.assertEqual(state.rescopable(slot, TOUCHES[touches], touches_only=only), predicted)
        if not predicted:
            return {}
        text = f'\n  - [ ] {task} — answered contract {contract}\n  '
        with execution.lock(self.common / 'writer.lock'):
            state.rescope(self.common, slot, TOUCHES[touches], contract=text)
        rec.update(state='reported', rescoped=True, touches=TOUCHES[touches], contract=text.strip(),
                   reason=None, cause=None, outside=None)
        return {task: rec}

    def op_reoffer(self, task):
        rec = self.model[task]
        if not (rec and rec['state'] == 'held' and rec['cause'] in ('overlap', 'report', 'validation', 'scope')
                and rec['cause'] not in rec['reoffered'] and not self.live(rec)):
            return {}  # integration's own precondition; reoffer() itself trusts its caller
        with execution.lock(self.common / 'writer.lock'):
            state.reoffer(self.common, self.disk(task))
        rec.update(state='reported', reoffered=rec['reoffered'] | {rec['cause']}, reason=None, cause=None)
        return {task: rec}

    def op_readopt(self, task):
        rec = self.model[task]
        if rec is None:
            return {}
        before = self.snapshot()
        with execution.lock(self.common / 'writer.lock'):
            if not self.m_readoptable(rec):
                with self.case.assertRaises(ValueError):
                    state.readopt(self.common, self.disk(task))
                return self.unchanged(before)
            state.readopt(self.common, self.disk(task))
        first = copy.deepcopy(self.m_first_held(rec))
        new = dict(first, reason=None, attempt=2, readopted=True, data_attempt=first['attempt'],
                   state='reported', prev=[first, self.strip(rec)])
        self.model[task] = new
        return {task: new}

    def op_corrupt(self, task, mode):
        if self.model[task] is None:
            return {}
        path = self.common / 'slots' / (task + '.json')
        original = path.read_bytes()
        bad = {'truncated': original[:len(original) // 2], 'empty': b'{}', 'null': b'null',
               'state': json.dumps(dict(json.loads(original), state='lost')).encode()}[mode]
        path.write_bytes(bad)
        before = self.snapshot()
        other = next((t for t in TASKS if t != task and self.model[t]), task)
        for call in (lambda: state.transition(self.fx.repo, self.fx.owner, other, 'held'),
                     lambda: state.pause(self.fx.repo, self.fx.owner),
                     lambda: state.reconcile(self.fx.repo, self.fx.owner)):
            with self.case.assertRaises(ValueError):  # fail closed, touching nothing
                call()
            self.unchanged(before)
        path.write_bytes(original)
        return {}

    # -- generation --------------------------------------------------------------------
    def generate(self, rng):
        task = rng.choice(TASKS)
        rec = self.model[task]
        if rec is None and rng.random() < 0.7:
            return ['create', task, 'live' if rng.random() < 0.3 else None]
        roll = rng.random()
        if rec is None or roll < 0.5:
            legal = sorted(state.TRANSITIONS[rec['state']]) if rec else []
            pick = rng.random()
            target = (rng.choice(legal) if legal and pick < 0.75
                      else rng.choice(STATES) if pick < 0.96 else 'bogus')
            menus = {'running': ['live', 'live', 'none', 'reason'],
                     'held': ['scope', 'scope', 'scope_nocommit', 'overlap', 'report', 'blocker', 'validation',
                              'none', 'reason', 'unknown_cause'],
                     'interrupted': ['none', 'reason', 'empty', 'paused'],
                     'released': ['none', 'reason', 'empty', 'paused'],
                     'reported': ['commit', 'none', 'reason'],
                     'dispatched': (['r2', 'r2', 'r2', 'r2_same', 'r2_badbranch', 'none']
                                    if rec and rec['state'] == 'held' else ['none', 'none', 'live', 'r2'])}
            key = rng.choice(menus.get(target, ['none', 'reason']))
            if rng.random() < 0.04:
                key = 'bogus'
            crash = rng.choices([None, 'save', 'journal'], [0.88, 0.07, 0.05])[0]
            return ['transition', task, target, key, crash]
        return rng.choices([
            ['kill', task], ['dirty', task], ['commit', task], ['diverge', task],
            ['report', task, rng.choice(sorted(REPORTS))], ['pause'], ['reconcile'], ['restart', task],
            ['rescope', task, rng.choice(sorted(TOUCHES)), rng.random() < 0.3, rng.randrange(3)],
            ['reoffer', task], ['readopt', task],
            ['corrupt', task, rng.choice(['truncated', 'empty', 'null', 'state'])]],
            [6, 4, 4, 0.5, 4, 2, 6, 1.5, 4, 3, 3, 1])[0]


def seeds():
    raw = os.environ.get('AUTOWORK_STATE_MODEL_SEEDS', '')
    return tuple(int(s) for s in raw.split(',') if s.strip()) or DEFAULT_SEEDS


def steps():
    return int(os.environ.get('AUTOWORK_STATE_MODEL_STEPS') or DEFAULT_STEPS)


class StateModelTests(unittest.TestCase):
    def replay(self, trace):
        """Run a concrete trace on a fresh repository; return (index, exception) or None."""
        with tempfile.TemporaryDirectory() as tmp:
            walk = Walk(self, tmp)
            try:
                walk.check({})
                for index, op in enumerate(trace):
                    try:
                        walk.check(walk.apply(op))
                    except Exception as exc:  # noqa: BLE001 - reported with its trace
                        return index, exc
            finally:
                walk.close()
        return None

    def shrink(self, trace, failure, budget=40, deadline=20.0):
        """Shrinking-lite: greedily drop single steps while the same kind of failure remains."""
        kind = type(failure)
        end = time.monotonic() + deadline
        index = 0
        while index < len(trace) and budget > 0 and time.monotonic() < end:
            candidate = trace[:index] + trace[index + 1:]
            budget -= 1
            found = self.replay(candidate)
            if found is not None and type(found[1]) is kind:
                trace = candidate[:found[0] + 1]
            else:
                index += 1
        return trace

    def walk(self, seed, count):
        rng = random.Random(seed)
        trace = []
        with tempfile.TemporaryDirectory() as tmp:
            walk = Walk(self, tmp)
            self.addCleanup(walk.close)
            try:
                walk.check({})
                for _ in range(count):
                    op = walk.generate(rng)
                    trace.append(op)
                    walk.check(walk.apply(op))
            except Exception as exc:  # noqa: BLE001 - re-raised with the replay recipe
                walk.close()
                shrunk = self.shrink(list(trace), exc)
                raise AssertionError(
                    f'state model failed: seed={seed} step={len(trace)}: {type(exc).__name__}: {exc}\n'
                    f'replay: AUTOWORK_STATE_MODEL_SEEDS={seed} AUTOWORK_STATE_MODEL_STEPS={len(trace)}\n'
                    f'trace: {json.dumps(trace)}\n'
                    f"shrunk ({len(shrunk)} steps): AUTOWORK_STATE_MODEL_TRACE='{json.dumps(shrunk)}'") from exc
        return trace

    def test_random_walks_match_the_model(self):
        explicit = os.environ.get('AUTOWORK_STATE_MODEL_TRACE')
        if explicit:
            found = self.replay(json.loads(explicit))
            if found is not None:
                raise AssertionError(f'trace failed at step {found[0]}: {found[1]!r}') from found[1]
            return
        covered = set()
        for seed in seeds():
            with self.subTest(seed=seed):
                trace = self.walk(seed, steps())
                covered |= {op[0] for op in trace}
                covered |= {('to', op[2]) for op in trace if op[0] == 'transition'}
        if not os.environ.get('AUTOWORK_STATE_MODEL_SEEDS'):
            # The fixed seeds must keep exercising every operation and every target state.
            expected = {'create', 'transition', 'kill', 'dirty', 'commit', 'report', 'pause', 'reconcile',
                        'restart', 'rescope', 'reoffer', 'readopt', 'corrupt'} | {('to', s) for s in STATES}
            self.assertEqual(expected - covered, set())

    def test_a_scripted_walk_reaches_rescope_reoffer_and_readopt(self):
        """Random walks rarely chain the re-offer paths; this trace drives each one once."""
        trace = [
            ['create', 'A', None], ['transition', 'A', 'reported', 'commit', None],
            ['transition', 'A', 'held', 'scope', None], ['rescope', 'A', 'other', False, 0],
            ['rescope', 'A', 'dir', False, 1], ['transition', 'A', 'held', 'scope', None],
            ['rescope', 'A', 'file', False, 2], ['rescope', 'A', 'file', True, 2],
            ['transition', 'A', 'integrating', 'none', None], ['transition', 'A', 'integrated', 'none', None],
            ['transition', 'A', 'closed', 'none', None], ['transition', 'A', 'held', 'none', None],
            ['create', 'B', None], ['transition', 'B', 'reported', 'none', None],
            ['transition', 'B', 'held', 'overlap', None], ['reoffer', 'B'], ['transition', 'B', 'held', 'report', None],
            ['reoffer', 'B'], ['transition', 'B', 'held', 'overlap', None], ['reoffer', 'B'],  # once per cause
            ['create', 'C', None], ['transition', 'C', 'reported', 'none', None],
            ['transition', 'C', 'held', 'scope', None], ['transition', 'C', 'dispatched', 'r2', None],
            ['readopt', 'C'], ['transition', 'C', 'held', 'reason', None], ['readopt', 'C'],
            ['transition', 'C', 'reported', 'none', None], ['transition', 'C', 'held', 'validation', None],
            ['transition', 'C', 'dispatched', 'r2', None],
        ]
        self.assertIsNone(self.replay(trace))
        with tempfile.TemporaryDirectory() as tmp:
            walk = Walk(self, tmp)
            self.addCleanup(walk.close)
            for op in trace:
                walk.check(walk.apply(op))
            # The rescoped contract is what later reads return, stripped, and survives integration.
            self.assertEqual(walk.disk('A')['rescoped_contract'], '- [ ] A — answered contract 2')
            self.assertEqual(walk.disk('A')['state'], 'closed')
            self.assertEqual(state.reoffered(walk.disk('B')), {'overlap', 'report'})
            self.assertEqual(walk.disk('B')['state'], 'held')
            self.assertEqual((walk.disk('C')['state'], walk.disk('C')['readopted']), ('held', True))

    def test_a_scripted_walk_covers_reconcile_reports_and_pause(self):
        trace = [
            ['create', 'A', 'live'], ['create', 'B', None], ['create', 'C', None],
            ['dirty', 'B'], ['report', 'B', 'host'], ['report', 'C', 'empty'], ['pause'], ['reconcile'],
            ['kill', 'A'], ['reconcile'], ['transition', 'A', 'dispatched', 'none', None],
            ['transition', 'B', 'dispatched', 'none', None], ['reconcile'],
            ['transition', 'B', 'dispatched', 'r2', None], ['transition', 'C', 'dispatched', 'r2', None],
            ['report', 'C', 'input'], ['reconcile'], ['commit', 'A'], ['reconcile'],
            ['create', 'A', None], ['restart', 'A'], ['corrupt', 'A', 'truncated'], ['reconcile'],
        ]
        self.assertIsNone(self.replay(trace))

    def test_every_state_event_pair_from_the_table(self):
        """Exhaustive small scope: transition() accepts exactly TRANSITIONS, plus the attempt rules."""
        with tempfile.TemporaryDirectory() as tmp:
            fx = Repo(tmp)
            worktree, fresh = fx.worktree('X'), fx.worktree('X-r2')
            path = fx.common / 'slots' / 'X.json'
            journal = fx.common / 'journal.jsonl'
            accepted = {}
            for source in STATES:
                for target in STATES + ('bogus', ''):
                    for attempt, paused in ((1, False), (2, False), (2, True)):
                        for bogus in (False, True):
                            slot = dict(task_id='X', worktree=str(worktree), branch='autowork/X', baseline=fx.base,
                                        worker=None, state=source, attempt=attempt, started_at=time.time())
                            if paused:
                                slot['paused'] = True
                            execution.save(path, slot)
                            before = (path.read_bytes(), journal.read_bytes())
                            upd = ({'worktree': str(fresh), 'branch': 'autowork/X-r2', 'baseline': fx.base}
                                   if source == 'held' and target == 'dispatched' else {})
                            if bogus:
                                upd['task_id'] = 'Y'
                            resume = paused and source in ('interrupted', 'released')
                            legal = (target in state.TRANSITIONS[source] and not bogus
                                     and not (target == 'dispatched' and attempt == 2 and not resume))
                            label = f'{source} -> {target!r} attempt={attempt} paused={paused} bogus={bogus}'
                            if not legal:
                                with self.assertRaises(ValueError, msg=label):
                                    state.transition(fx.repo, fx.owner, 'X', target, **upd)
                                self.assertEqual((path.read_bytes(), journal.read_bytes()), before, label)
                                continue
                            result = state.transition(fx.repo, fx.owner, 'X', target, **upd)
                            demoted = target in ('interrupted', 'released') and attempt == 2 and not paused
                            self.assertEqual(result['state'], 'held' if demoted else target, label)
                            if demoted:
                                self.assertEqual(result['cause'], 'crash', label)
                            if target == 'dispatched':
                                self.assertEqual(result['attempt'], attempt if resume else 2, label)
                                self.assertEqual(result['worktree'], str(fresh if source == 'held' else worktree))
                            event = json.loads(journal.read_bytes()[len(before[1]):])
                            self.assertEqual((event['previous_state'], event['state']), (source, result['state']))
                            if attempt == 1 and not bogus:
                                accepted.setdefault(source, set()).add(target)
            self.assertEqual(accepted, {s: t for s, t in state.TRANSITIONS.items() if t})
            self.assertEqual(state.TRANSITIONS['closed'], set())  # closed is terminal

    # -- found defects -----------------------------------------------------------------
    def reconciled_pair(self, tmp):
        fx = Repo(tmp)
        for task in ('A', 'B'):
            fx.worktree(task)
            state.create_slot(fx.repo, fx.owner, task, worktree=str(fx.paths[task]),
                              branch='autowork/' + task, baseline=fx.base)
        return fx

    def test_reconcile_holds_a_worker_whose_head_has_unrelated_history(self):
        # Was a bug: parallel_state.reconcile runs `git merge-base BASELINE HEAD`, which exits 1
        # when the worker's HEAD shares no history with the baseline; execution.git turns that into
        # ValueError('consumer must be an existing Git workspace') and the whole reconcile aborts.
        # Expected: that slot is held 'worker HEAD does not descend from baseline' (the diverged
        # case) and every later slot is still reconciled. Actual: reconcile raises and slot B,
        # sorted after A, stays 'dispatched' with a dead worker on every restart.
        with tempfile.TemporaryDirectory() as tmp:
            fx = self.reconciled_pair(tmp)
            orphan = fx.git('commit-tree', fx.base + '^{tree}', '-m', 'unrelated', repo=fx.paths['A'])
            fx.git('reset', '-q', '--hard', orphan, repo=fx.paths['A'])
            result = {s['task_id']: s for s in state.reconcile(fx.repo, fx.owner)}
            self.assertEqual((result['A']['state'], result['A']['reason']), ('held', DIVERGED))
            self.assertEqual(result['B']['state'], 'released')

    def test_a_diverged_worker_hold_records_a_cause(self):
        # Was a contract gap: references/parallel-workers.md says "every held slot records a
        # machine-readable cause", but reconcile's diverged-HEAD hold (parallel_state.py ~613)
        # sets only `reason`. Sequence: create A; reset its worktree to a sibling of the baseline;
        # reconcile. Expected: held with a cause. Actual: held with cause None (unless an earlier
        # update left a stale one on the record).
        with tempfile.TemporaryDirectory() as tmp:
            fx = self.reconciled_pair(tmp)
            fx.git('reset', '-q', '--hard', fx.sibling, repo=fx.paths['A'])
            held = next(s for s in state.reconcile(fx.repo, fx.owner) if s['task_id'] == 'A')
            self.assertEqual((held['state'], held['reason']), ('held', DIVERGED))
            self.assertIsNotNone(held.get('cause'))

    def test_an_adopted_worker_does_not_keep_a_stale_pause(self):
        # Was a bug: pause() marks live workers so the death a deliberate stop causes resumes the same
        # attempt. When the worker survives the stop, the next coordinator adopts it (reconcile:
        # target 'running', no write because it already is running) and `paused` stays set. Its
        # later, genuine crash is then reported as 'stopped by a runner restart; resumes on
        # attempt 2' and released, instead of a second interruption being held (cause 'crash'):
        # change() (line ~388) skips the attempt-2 hold because old['paused'] is still true.
        with tempfile.TemporaryDirectory() as tmp:
            fx = self.reconciled_pair(tmp)
            worker = subprocess.Popen(['sleep', '300'], start_new_session=True)
            self.addCleanup(lambda: (worker.kill(), worker.wait()))
            state.transition(fx.repo, fx.owner, 'B', 'released')
            state.transition(fx.repo, fx.owner, 'B', 'dispatched')  # attempt 2
            state.transition(fx.repo, fx.owner, 'B', 'running', worker=execution.identity(worker.pid))
            state.pause(fx.repo, fx.owner)
            state.release(fx.repo, fx.owner)
            state.claim(fx.repo, fx.owner, profile='fixture')
            adopted = next(s for s in state.reconcile(fx.repo, fx.owner) if s['task_id'] == 'B')
            self.assertEqual(adopted['state'], 'running')
            worker.kill()
            worker.wait()
            crashed = next(s for s in state.reconcile(fx.repo, fx.owner) if s['task_id'] == 'B')
            # Held, not resumed: a second interruption on attempt 2. A worker that left nothing
            # behind is labelled 'empty' rather than 'crash' by change().
            self.assertEqual(crashed['state'], 'held')
            self.assertIn(crashed.get('cause'), ('crash', 'empty'))


if __name__ == '__main__':
    unittest.main()
