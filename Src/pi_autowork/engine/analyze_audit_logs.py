#!/usr/bin/env python3
"""Incremental deterministic triage of retained sanitized audit chunks, never raw-log deletion."""
import argparse
from collections import Counter
import fcntl
import json
import os
from pathlib import Path
import re
import sys
from uuid import uuid4
from pi_autowork.engine.audit_profiles import digest, private_write, safe


PATTERNS = {
    'error': re.compile(r'\b(error|exception|traceback|failed|failure)\b', re.I),
    'admission': re.compile(r'\b(admission|draft_saved|not.eligible|refus|blocked)\b', re.I),
    'delivery': re.compile(r'\b(delivery|telegram|preflight)\b', re.I),
    'timeout': re.compile(r'\b(timeout|timed out|retry.exhausted)\b', re.I),
}


def confined(root, path):
    path = Path(path).absolute()
    maintenance = root / 'maintenance'
    if root.parent.name == 'profiles' or maintenance.is_symlink():
        raise ValueError('default-owned maintenance required')
    if not path.resolve().is_relative_to(maintenance) or path.resolve() == maintenance:
        raise ValueError('path must be below default maintenance')
    for parent in (path, *path.parents):
        if parent.is_symlink() or (parent / '.git').exists():
            raise ValueError('symlink or repository path refused')
        if parent == root:
            break
    return path


def analyze(root, directories, state_dir, limit=100):
    root = Path(root).resolve(strict=True)
    state_dir = confined(root, state_dir)
    directories = [confined(root, path) for path in directories]
    if not 0 <= limit <= 1000:
        raise ValueError('chunk budget must be between 0 and 1000')
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(state_dir / 'analysis.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'state': 'overlap_refused', 'semantic_review': 'not_performed'}
        state_path = state_dir / 'analysis-state.json'
        if state_path.is_symlink():
            raise ValueError('symlink state refused')
        state = json.loads(state_path.read_text()) if state_path.exists() else {'schema': 'audit-log-triage/v1', 'seen': [], 'profiles': {}}
        if state.get('schema') != 'audit-log-triage/v1':
            raise ValueError('unknown analysis state schema')
        seen = set(state['seen'])
        profiles = state['profiles']
        paths = sorted({p for directory in directories for p in directory.rglob('receipt*.json')
                        if p.is_file() and not p.is_symlink()}, key=lambda p: (p.stat().st_mtime_ns, str(p)))
        gaps, chunks = [], {}
        if len(paths) > 2000:
            gaps.append('receipt inventory beyond 2000 omitted')
            paths = paths[:2000]
        for path in paths:
            try:
                confined(root, path)
                if path.stat().st_size > 16 * 1024 * 1024:
                    gaps.append('oversized receipt skipped'); continue
                receipt = json.loads(path.read_text())
                if receipt.get('schema') != 'fleet-audit/v1':
                    gaps.append('unsupported receipt schema skipped'); continue
                for row in receipt['profiles']:
                    name = row['profile']
                    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', name):
                        raise ValueError('invalid profile identity')
                    summary = profiles.setdefault(name, {'signals': {}, 'samples': [], 'redacted_lines': 0, 'triaged_chunks': 0})
                    summary['latest_unread_bytes'] = sum(log['remaining_bytes'] for log in row['logs'])
                    summary['latest_receipt'] = str(path)
                    for log in row['logs']:
                        if (not all(isinstance(log[k], int) and not isinstance(log[k], bool)
                                    for k in ('start', 'cursor', 'bytes_observed'))
                                or log['cursor'] < log['start'] or log['start'] < 0
                                or log['cursor'] - log['start'] != log['bytes_observed']
                                or not isinstance(log.get('payload'), str)):
                            raise ValueError('invalid chunk range or payload')
                        key = digest(json.dumps([name, log['file'], log['identity'], log['start'], log['cursor'], log['sha256']], sort_keys=True).encode())
                        chunks.setdefault(key, (name, log, str(path)))
            except (OSError, UnicodeError, ValueError, KeyError, TypeError):
                gaps.append('receipt malformed, unsafe or unreadable; skipped')
        pending = [(key, row) for key, row in chunks.items() if key not in seen]
        new_bytes = 0
        for key, (name, log, receipt) in pending[:limit]:
            summary = profiles[name]
            counts = Counter(summary['signals'])
            for line_number, line in enumerate(log['payload'].splitlines(), 1):
                if 'REDACTED' in line or 'PARTIAL' in line:
                    summary['redacted_lines'] += 1
                matches = [label for label, pattern in PATTERNS.items() if pattern.search(line)]
                counts.update(matches)
                if matches and len(summary['samples']) < 5:
                    summary['samples'].append({'kinds': matches, 'excerpt': safe(line)[:240],
                        'receipt': receipt, 'file': log['file'], 'raw_range': [log['start'], log['cursor']],
                        'payload_line': line_number})
            summary['signals'] = dict(counts)
            summary['triaged_chunks'] += 1
            seen.add(key)
            new_bytes += log['bytes_observed']
        report = {'schema': 'audit-log-triage/v1', 'state': 'triaged_with_gaps',
            'method': 'deterministic keyword classification of sanitized payloads',
            'semantic_review': 'not_performed', 'new_chunks': min(limit, len(pending)),
            'new_chunk_bytes': new_bytes, 'pending_chunks': max(0, len(pending) - limit),
            'byte_boundary': 'unique exact chunk records; overlapping ranges may be counted; redacted bytes are not semantic coverage',
            'gaps': sorted(set(gaps)), 'profiles': profiles}
        output = state_dir / ('triage-' + uuid4().hex + '.json')
        private_write(output, report)
        private_write(state_path, {'schema': 'audit-log-triage/v1', 'seen': sorted(seen), 'profiles': profiles})
        report['report'] = str(output)
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--receipts-dir', type=Path, action='append', required=True)
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--chunks', type=int, default=100)
    args = parser.parse_args()
    try:
        result = analyze(args.root, args.receipts_dir, args.state_dir, args.chunks)
        print(json.dumps({k: v for k, v in result.items() if k != 'profiles'}, separators=(',', ':')))
        return 2 if result['state'] == 'overlap_refused' else 0
    except (OSError, ValueError, KeyError, TypeError):
        print(json.dumps({'state': 'analysis_failed', 'reason': 'invalid state, receipt or path; no deletion performed'}))
        return 1


def _compat_main(argv):
    import sys
    previous = sys.argv
    sys.argv = [previous[0], *argv]
    try:
        sys.exit(main())
    finally:
        sys.argv = previous
