#!/usr/bin/env python3
"""Deterministic stand-in for a host worker CLI in parallel dispatch tests.

argv: PROMPT_FILE WORKTREE. Behavior per task comes from the JSON file named by
FAKE_WORKER_SPEC: {"TASK": {"files": {"path": "text"}, "sleep": 0.5,
"commit": true, "exit": 0}}. Start and end times are appended to
FAKE_WORKER_LOG so tests can prove overlapping lifetimes.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

prompt = Path(sys.argv[1]).read_text()
worktree = Path(sys.argv[2])
task = re.search(r'^Task: (\S+)', prompt, re.M)[1]
report = Path(re.search(r'^Report file: (\S+)', prompt, re.M)[1])
spec = json.loads(Path(os.environ['FAKE_WORKER_SPEC']).read_text()).get(task, {})
log = Path(os.environ['FAKE_WORKER_LOG'])


def note(kind):
    with log.open('a') as stream:
        stream.write(json.dumps({'task': task, 'event': kind, 'time': time.time(),
                                 'cwd': os.getcwd(), 'tmpdir': os.environ.get('TMPDIR'),
                                 'slot': os.environ.get('AUTOWORK_SLOT'),
                                 'port_base': os.environ.get('AUTOWORK_PORT_BASE'),
                                 'marker': 'HERMES_TOOLSET_EXECUTION_COMMON' in os.environ}) + '\n')


note('start')
if spec.get('orphan'):
    # A child that ignores SIGTERM and outlives this leader, in the same process group.
    subprocess.Popen([sys.executable, '-c', 'import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); '
                      'time.sleep(60)'])
for name, text in spec.get('files', {}).items():
    path = worktree / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
time.sleep(spec.get('sleep', 0.5))
commit = None
if spec.get('commit', True) and spec.get('files'):
    subprocess.run(['git', '-C', str(worktree), 'add', '-A'], check=True)
    subprocess.run(['git', '-C', str(worktree), 'commit', '-qm', 'fake work for ' + task], check=True)
    commit = subprocess.run(['git', '-C', str(worktree), 'rev-parse', 'HEAD'], check=True,
                            capture_output=True, text=True).stdout.strip()
    report.write_text(json.dumps({'task': task, 'commit': commit, 'changed_files': sorted(spec['files']),
                                  'checks': [], 'blockers': [], 'changelog': ''}))
note('end')
sys.exit(spec.get('exit', 0))
