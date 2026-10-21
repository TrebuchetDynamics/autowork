#!/usr/bin/env python3
"""Controlled fake-worker ABC serial/parallel benchmark, never an LLM speedup."""
import argparse
import json
import os
from pathlib import Path
import platform
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pi-autowork/engine'))
from test_parallel_e2e import ABCWorkload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--delay', type=float, default=1.0, help='controlled sleep per task in seconds (default: 1)')
    args = parser.parse_args()
    if not 0 < args.delay <= 10:
        parser.error('--delay must be positive and at most 10 seconds')
    runs = []
    for count in (1, 2):
        with ABCWorkload(workers=count, delay=args.delay) as workload:
            runs.append(workload.run())
    result = dict(machine=dict(system=platform.system(), release=platform.release(), architecture=platform.machine(),
                               cpu=platform.processor(), logical_cpus=os.cpu_count(), python=platform.python_version(),
                               load_average=os.getloadavg()),
                  workload='Disposable Git ABC: disjoint A/B, C depends on closed A; sleep then commit, validate, integrate, close.',
                  comparison='Same real CLI pipeline, --parallel 1 (serial control) versus --parallel 2; local fake workers only.',
                  overhead_definition='Elapsed minus controlled sleep critical path; includes CLI/process startup, Git, validation, close and scheduling/barrier waits. Not isolated coordinator CPU time.',
                  runs=runs,
                  elapsed_difference_seconds=runs[0]['elapsed_seconds'] - runs[1]['elapsed_seconds'],
                  qualification='Offline controlled workload only. No LLM-worker speedup or live host qualification claimed.')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
