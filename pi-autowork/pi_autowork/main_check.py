"""Main's full offline check after a landing, so a red main opens its own repair (TOOLSET-176-98).

A task's review runs only that task's Checks; a landing that breaks an unrelated test went
unnoticed until a person ran the full check. A repository that declares its full offline
check (PI_AUTOWORK_MAIN_CHECK) has it run in the background, once per main revision, in a
disposable checkout of main; a failure names the failing tests and the commits since the
last green revision, and the DOCS-MAINTAINER adds one repair task for it. Standard library only.
"""
import json
import os
from pathlib import Path
import re
import time

FAILURE = re.compile(r'^(FAIL|ERROR): (\S+) \(([^)]+)\)', re.M)
TIMEOUT = re.compile(r'^TIMEOUT: (\S+) after', re.M)


def command(env=os.environ):
    return env.get('PI_AUTOWORK_MAIN_CHECK', '').strip()


def record_path(state):
    return Path(state) / 'main_check.json'


def read(state):
    try:
        value = json.loads(record_path(state).read_text())
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def write(state, value):
    path = record_path(state)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value) + '\n')
    tmp.replace(path)
    return value


def failures(log_text, limit=20):
    """Failing tests as 'module.Class.test' (or a timed-out directory), first ones first."""
    found = [where for _, _, where in FAILURE.findall(log_text)]
    found += [f'{directory} (timed out)' for directory in TIMEOUT.findall(log_text)]
    return list(dict.fromkeys(found))[:limit]


def gate_skips(log_text):
    """Tests the host's resource gate skipped (TOOLSET-193-54): not failures, but not checked."""
    return log_text.count('RESOURCE_GATE_SKIP:')


def alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def line(record, now=None):
    """'main red since 1a2b3c4: 5 failing', 'main green at 1a2b3c4', 'main check running …', or ''."""
    now = time.time() if now is None else now
    state = record.get('state')
    if state == 'red':
        return f"main red since {record.get('rev', '')[:7]}: {len(record.get('failures') or [])} failing"
    if state == 'recheck':
        return f"main check again at {record.get('gated', '')[:7]} when the host is quieter"
    if state == 'green':
        return f"main green at {record.get('rev', '')[:7]}"
    if state == 'running':
        return f"main check running on {record.get('rev', '')[:7]} ({int((now - record.get('started', now)) // 60)}m)"
    return ''
