"""Best-effort host observations into the engine's existing private journal."""
from pathlib import Path
import sys
import subprocess


def engine():
    from pi_autowork.engine import parallel_state
    return parallel_state


def observe(repo, delivered_rev=None):
    try:
        engine().observe_history(repo, delivered_rev=delivered_rev)
    except (OSError, ValueError, subprocess.SubprocessError):
        pass


def model_run(repo, role, task, model, outcome, run=None):
    """Correlate the actual model (including fallback) without exporting run text."""
    if role not in ('worker', 'verify'):
        return
    try:
        state = engine()
        common = state.common_dir(repo)
        with state.execution.lock(common / 'writer.lock'):
            slot = state.execution.read(state.slot_path(common, task))
            if not slot or slot['state'] == 'closed':
                return
            if role == 'worker' and outcome == 'selected':
                # Context only: no scheduling/state transition and no transcript persisted.
                slot = dict(slot, host='pi', model=state.journal.label(model))
                state.execution.save(state.slot_path(common, task), slot)
            ctx = state.journal.context(common, dict(slot, host='pi', model=state.journal.label(model)))
            kind = ('model_retry' if outcome in ('provider_failure', 'crash_failure')
                    else 'model_' + outcome)
            # Separate provider runs from a fresh task attempt; never spend an attempt here.
            fact = state.journal.fact(ctx, kind, key=state.execution.uuid.uuid4().hex)
            fact['role'] = role
            if run and type(run.get('retries')) is int:
                fact['retries'] = run['retries']
            state.event(common, 'task_lifecycle', lifecycle=[fact])
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
