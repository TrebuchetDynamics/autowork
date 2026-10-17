#!/usr/bin/env python3
"""Copy into the default Hermes home's scripts directory for native cron."""
from pathlib import Path
import json
import runpy
import sys

home = Path(__file__).resolve().parents[1]
helper = home / 'plugins/autowork/skills/autowork/scripts/audit_profiles.py'
if not helper.is_file():
    print(json.dumps({'state': 'collector_failed', 'reason': 'shared audit helper missing'}))
    sys.exit(1)
sys.path.insert(0, str(helper.parent.resolve()))
sys.argv = [str(helper), '--root', str(home), '--state-dir',
            str(home / 'maintenance/profile-audit/collector'),
            '--launch-cwd', 'default=' + str(Path.cwd()),
            '--log-bytes', '1048576', '--profile-log-bytes', '8388608']
config = home / 'maintenance/profile-audit/config.json'
if config.exists():
    try:
        profiles = json.loads(config.read_text())['profiles']
        if not isinstance(profiles, list) or not profiles or not all(isinstance(n, str) for n in profiles):
            raise ValueError('profiles must be a nonempty list')
    except (OSError, ValueError, KeyError, TypeError):
        print(json.dumps({'state': 'collector_failed', 'reason': 'invalid audit profile configuration'}))
        sys.exit(1)
    sys.argv += ['--profiles', *profiles]
runpy.run_path(str(helper), run_name='__main__')
