"""Revision-bound admission policy; uses main-check receipts, not a second scheduler.

The repository command writes a schema-1 verdict to the supplied absolute path.
Only its completed, successful supervised attempt can authorize the next landing.
"""
import json
import math
import os
from pathlib import Path
import shlex
import time

POLICY = 'revision-barrier'


def enabled(env=os.environ):
    return env.get('PI_AUTOWORK_POST_MERGE_POLICY', 'async') == POLICY


def timeout(env=os.environ):
    value = float(env.get('PI_AUTOWORK_POST_MERGE_TIMEOUT') or '900')
    if not math.isfinite(value) or not 0 < value <= 900:
        raise ValueError('PI_AUTOWORK_POST_MERGE_TIMEOUT must be positive and at most 900 seconds')
    return value


def validate_settings(env=os.environ):
    if env.get('PI_AUTOWORK_POST_MERGE_POLICY', 'async') not in ('async', POLICY):
        raise ValueError('PI_AUTOWORK_POST_MERGE_POLICY must be async or revision-barrier')
    if enabled(env):
        timeout(env)
        if not env.get('PI_AUTOWORK_MAIN_CHECK', '').strip():
            raise ValueError('revision-barrier requires an explicit PI_AUTOWORK_MAIN_CHECK command')


def verdict_path(state):
    return Path(state) / 'post-merge-verdict.json'


def verdict(state, record):
    """Read an exact attempt's complete verdict. Untrusted/missing data fails closed."""
    try:
        value = json.loads(verdict_path(state).read_text())
    except (OSError, ValueError, UnicodeError):
        return None
    if (not isinstance(value, dict) or type(value.get('schema')) is not int or value['schema'] != 1
            or value.get('revision') != record.get('rev')
            or not isinstance(record.get('run_id'), str) or not record['run_id']
            or value.get('run_id') != record['run_id'] or value.get('complete') is not True
            or value.get('status') not in ('green', 'red')
            or not isinstance(value.get('failures'), list)
            or any(not isinstance(item, str) or not item.strip() for item in value['failures'])
            or (value['status'] == 'green') != (not value['failures'])):
        return None
    return value


def admission(state, revision, record, command):
    """A reason to hold, or ''. No cached/ancestor/tree-only green releases this gate."""
    value = verdict(state, record)
    if (Path(state) / 'requests/recheck-main').exists():
        return 'post-merge barrier: a fresh check was requested'
    finished = record.get('finished')
    if (record.get('policy') == POLICY and record.get('state') == 'green'
            and record.get('rev') == revision and record.get('command') == command
            and record.get('timeout') == timeout() and type(record.get('exit_code')) is int
            and record['exit_code'] == 0 and type(finished) in (int, float)
            and math.isfinite(finished) and finished > 0 and value and value['status'] == 'green'):
        return ''
    return f'post-merge barrier: {revision[:12]} requires its completed green verdict'


def repair_check(record):
    """Run the same check against a candidate, never against canonical verdict storage."""
    script = ('scratch=$(mktemp -d "${TMPDIR:?}/aw-post-merge.XXXXXX") || exit 2\n'
              'trap \'rm -rf "$scratch"\' EXIT\n'
              'export AUTOWORK_POST_MERGE_VERDICT="$scratch/verdict.json"\n'
              'export AUTOWORK_POST_MERGE_REVISION="$(git rev-parse HEAD)"\n'
              'export AUTOWORK_POST_MERGE_RUN_ID="candidate-$$"\n'
              f'export AUTOWORK_POST_MERGE_BASE={shlex.quote(record["rev"])}\n'
              f'timeout --signal=KILL {shlex.quote(str(record.get("timeout") or 900))} '
              f'bash -c {shlex.quote(record["command"])}')
    return shlex.join(['bash', '-c', script])


def result(state, record, code, child):
    """Classify only a terminal command + valid verdict pair; never infer success from logs."""
    value = verdict(state, record)
    status = value['status'] if value and ((code == 0 and value['status'] == 'green')
                                         or (code == 1 and value['status'] == 'red')) else 'broken'
    classification = {'green': 'PASS', 'red': 'TEST_FAILURE', 'broken': 'INCOMPLETE'}[status]
    return dict(record, **child, state=status, exit_code=code, finished=time.time(), verdict=value,
                result_class=classification,
                green=record['rev'] if status == 'green' else record.get('green'),
                failures=value['failures'] if value else [],
                crash='' if status != 'broken' else 'missing, invalid, incomplete or exit-mismatched post-merge verdict')
