"""Tests that dispatch through the host's real resource gate skip when it refuses (TOOLSET-193-54).

A busy host (the fleet's own workers) made such tests fail, so main read red and reviews
rejected sound candidates. A refused test is skipped with the gate's reason, and a marker line
lets `scripts/check.py` and the runner's main check count and recheck those skips.
"""
import json
import re
import sys
import unittest

MARKER = 'RESOURCE_GATE_SKIP'


def skip_if_gated(*results):
    """Raise SkipTest when any engine answer in ``results`` carries a resource-gate refusal."""
    found = re.search(r'resource gate: [^"\\]*', json.dumps(results, default=str))
    if found:
        print(f'{MARKER}: {found[0]}', file=sys.stderr, flush=True)
        raise unittest.SkipTest(f'host busy: {found[0]}')
