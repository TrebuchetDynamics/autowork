#!/usr/bin/env python3
"""Copy into the default Hermes home's scripts directory for native cron."""
from pathlib import Path
import json
import runpy
import sys

home = Path(__file__).resolve().parents[1]
helper = home / 'plugins/hermes-toolset/skills/autogoal/scripts/audit_profiles.py'
if not helper.is_file():
    print(json.dumps({'state': 'collector_failed', 'reason': 'shared audit helper missing'}))
    sys.exit(1)
sys.path.insert(0, str(helper.parent.resolve()))
sys.argv = [str(helper), '--root', str(home), '--state-dir',
            str(home / 'maintenance/profile-audit/collector'),
            '--launch-cwd', 'default=' + str(Path.cwd())]
runpy.run_path(str(helper), run_name='__main__')
