#!/usr/bin/env python3
"""Read back TOOLSET-202-9a timing artifacts; never run a test or change a checkout."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def runtime_projection(inputs):
    return {path: value for path, value in inputs.items()
            if not path.startswith('docs/') and not path.endswith('.md')}


def verify(manifest, artifacts):
    evidence = json.loads(manifest.read_text())
    samples = evidence['samples']
    assert len(samples) == 7, 'missing timing samples'
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    current = {path: sha((ROOT / path).read_bytes()) for path in names
               if path.endswith(('.py', '.sh', '.mjs', '.json', '.md')) and (ROOT / path).is_file()}
    current_runtime = runtime_projection(current)
    measured_trees = {item['source']['index_tree'] for item in samples if item['label'].startswith('after')}
    assert len(measured_trees) == 1, 'candidate source tree changed between measurements'
    # The collector's explicit hash map is extension-bounded. Also compare the
    # entire measured Git tree to final tracked bytes, including YAML, JS and
    # extensionless files, allowing only the four subsequent evidence-doc edits.
    changes = subprocess.check_output(['git', 'diff', '--name-only', '--no-renames',
                                      next(iter(measured_trees))], cwd=ROOT).decode().splitlines()
    evidence_edits = {'docs/plans/2026-10-20-owner-cycle-retirement.md',
                      'docs/plans/owner-cycle-full-check-timings.json',
                      'docs/plans/owner-cycle-timing-readback.py', 'docs/testing.md'}
    assert not set(changes) - evidence_edits, 'non-evidence bytes differ from measured Git tree'
    expected_units = {'before': 162, 'after': 136}
    expected_tests = {'before': 2208, 'after': 1860}
    for sample in samples:
        label = sample['label']
        side = label.split('-')[0]
        raw_bytes = (artifacts / (label + '.json')).read_bytes()
        assert sha(raw_bytes) == sample['raw_record_sha256'], label + ': raw receipt changed'
        raw = json.loads(raw_bytes)
        text_bytes = (artifacts / (label + '.log')).read_bytes()
        assert sha(text_bytes) == sample['log_sha256'] == raw['log_sha256'], label + ': log changed'
        inventory = (artifacts / (label + '.inventory')).read_bytes()
        assert sha(inventory) == sample['inventory_sha256'] == raw['inventory_sha256'], label + ': inventory changed'
        inputs = json.loads((artifacts / (label + '.inputs.json')).read_text())
        assert sha(json.dumps(inputs, sort_keys=True).encode()) == sample['source']['inputs_sha256'], label + ': inputs changed'
        projection = runtime_projection(inputs)
        assert sha(json.dumps(projection, sort_keys=True).encode()) == sample['runtime_inputs']['sha256']
        if side == 'after':
            assert projection == current_runtime, label + ': final runtime/test/config bytes differ'
            assert sample['exit_code'] == 0 and not sample['unittest_skips']
        text = text_bytes.decode(errors='replace')
        for key in ('source', 'elapsed_seconds', 'exit_code', 'inputs_unchanged', 'jobs', 'affinity',
                    'python_executable_sha256', 'test_count', 'process_units', 'result', 'failures',
                    'unittest_skips', 'resource_gate_skips'):
            assert sample[key] == raw[key], label + ': altered ' + key
        assert sample['inputs_unchanged'] and sample['resource_gate_skips'] == 0
        assert sample['test_count'] == sum(map(int, re.findall(r'^Ran (\d+) tests?', text, re.M))) == expected_tests[side]
        assert sample['process_units'] == len(re.findall(r'^Ran \d+ tests?', text, re.M)) == expected_units[side]
        assert sample['result'] == re.findall(r'^Offline result:.*', text, re.M)
        observations = raw['observations']
        loads = [item['load'][0] for item in observations]
        for field, value in (('one_minute_min', min(loads)), ('one_minute_mean', statistics.mean(loads)),
                             ('one_minute_max', max(loads))):
            assert sample['host_load'][field] == value, label + ': altered load'
        first, last = observations[0]['cpu_ticks'], observations[-1]['cpu_ticks']
        busy = 1 - (last['idle'] - first['idle']) / (last['total'] - first['total'])
        assert sample['host_load']['cpu_busy_fraction'] == busy
    assert len({item['python_executable_sha256'] for item in samples}) == 1
    assert len({tuple(item['affinity']) for item in samples}) == 1
    before = [item['elapsed_seconds'] for item in samples if item['label'].startswith('before') and item['exit_code'] == 0]
    after = [item['elapsed_seconds'] for item in samples if item['label'].startswith('after') and item['exit_code'] == 0]
    comparison = evidence['comparison']
    assert len(before) == comparison['passing_baseline_samples'] == 2
    assert len(after) == comparison['passing_candidate_samples'] == 3
    assert statistics.median(before) == comparison['baseline_median_seconds']
    assert statistics.median(after) == comparison['candidate_median_seconds']
    reduction = 100 * (statistics.median(before) - statistics.median(after)) / statistics.median(before)
    assert math.isclose(reduction, comparison['median_reduction_percent']) and reduction > 0
    pair = {item['label']: item for item in samples}
    b, a = (pair[name] for name in comparison['matched_load_samples'])
    assert b['exit_code'] == a['exit_code'] == 0
    assert abs(b['host_load']['one_minute_mean'] - a['host_load']['one_minute_mean']) < 0.03
    assert a['host_load']['cpu_busy_fraction'] >= b['host_load']['cpu_busy_fraction']
    matched = 100 * (b['elapsed_seconds'] - a['elapsed_seconds']) / b['elapsed_seconds']
    assert math.isclose(matched, comparison['matched_load_reduction_percent']) and matched > 0
    return {'samples_read_back': len(samples), 'candidate_runtime_matches': True,
            'median_reduction_percent': reduction, 'matched_load_reduction_percent': matched}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, default=Path(os.environ.get('TMPDIR', '.')) / 'timings')
    parser.add_argument('--manifest', type=Path, default=Path(__file__).with_name('owner-cycle-full-check-timings.json'))
    args = parser.parse_args()
    print(json.dumps(verify(args.manifest, args.artifacts), indent=2))


if __name__ == '__main__':
    main()
