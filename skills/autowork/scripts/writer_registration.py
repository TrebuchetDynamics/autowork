#!/usr/bin/env python3
"""Check an explicitly required JSONL writer registration without changing it."""
import argparse
import hashlib
import json
from pathlib import Path
import re

REQUIRED = {'card', 'task', 'workspace', 'base', 'scope'}


def unique_object(pairs):
    row = {}
    for key, value in pairs:
        if key in row:
            raise ValueError('Registration contains duplicate JSON field: ' + key)
        row[key] = value
    return row


def read_rows(data):
    rows = [json.loads(line, object_pairs_hook=unique_object)
            for line in data.decode().splitlines() if line.strip()]
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError('Registration registry must contain JSON objects')
    return rows


def matches_field(actual, expected, key):
    return (isinstance(actual, list) and sorted(actual) == sorted(expected)
            if key == 'scope' else actual == expected)


def drift_diagnosis(data, fields, expected):
    """Describe current bytes only; no claim about which historical bytes changed."""
    try:
        rows = read_rows(data)
        candidates = [row for row in rows if row.get(fields['card']) == expected['card']]
        if not candidates:
            return 'current_row_missing'
        if len(candidates) != 1:
            return 'current_row_ambiguous'
        if all(matches_field(candidates[0].get(fields[key]), value, key)
               for key, value in expected.items()):
            return 'current_row_matches'
        return 'current_row_mismatch'
    except (ValueError, TypeError, RecursionError):
        return 'registry_invalid'


def verify(registry, digest, fields, expected):
    """Match mapped top-level fields; caller supplies repository-specific policy."""
    if not REQUIRED <= expected.keys() or fields.keys() != expected.keys():
        raise ValueError('Registration requires card, task, workspace, base and scope mappings')
    if (any(not isinstance(v, str) or not v for v in fields.values())
            or len(set(fields.values())) != len(fields)):
        raise ValueError('Registration field mappings must be distinct nonempty names')
    if any(not isinstance(expected[k], str) or not expected[k].strip()
           for k in ('card', 'task', 'workspace', 'base')):
        raise ValueError('Registration identity must be explicit')
    if not Path(expected['workspace']).is_absolute():
        raise ValueError('Registration workspace must be absolute')
    if not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', expected['base']):
        raise ValueError('Registration base must be an immutable commit')
    scope = expected['scope']
    if (not isinstance(scope, list) or not scope or any(not isinstance(p, str) or not p
            or not Path(p).parts or Path(p).as_posix() != p
            or Path(p).is_absolute() or '..' in Path(p).parts or '.git' in Path(p).parts for p in scope)
            or len(set(scope)) != len(scope)):
        raise ValueError('Registration scope must contain distinct repository-relative paths')
    path = Path(registry)
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Registration registry must be an absolute non-symlink path')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        diagnosis = drift_diagnosis(data, fields, expected)
        if path.read_bytes() != data:
            diagnosis = 'registry_changed_during_diagnosis'
        raise ValueError('Registration evidence changed; inspect current registry: ' + diagnosis +
                         '; admission refused; reconcile the original prerequisite through the repository supported process, never silently refresh pins')
    rows = read_rows(data)
    # Refuse ambiguous histories instead of guessing which registration is current.
    candidates = [row for row in rows if row.get(fields['card']) == expected['card']]
    if len(candidates) != 1:
        raise ValueError('Missing or ambiguous writer registration for original card')
    row = candidates[0]
    for key, value in expected.items():
        actual = row.get(fields[key])
        if not matches_field(actual, value, key):
            raise ValueError('Writer registration mismatch: ' + key)
    if path.read_bytes() != data:
        raise ValueError('Registration changed during verification')
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--requirement', required=True, help='Private JSON with registry, sha256, fields, expected')
    parser.add_argument('--requirement-sha256', required=True, help='Pin from coordinator handoff')
    args = parser.parse_args()
    try:
        raw = Path(args.requirement).read_bytes()
        if hashlib.sha256(raw).hexdigest() != args.requirement_sha256:
            raise ValueError('Registration requirement changed')
        requirement = json.loads(raw, object_pairs_hook=unique_object)
        verify(requirement['registry'], requirement['sha256'], requirement['fields'], requirement['expected'])
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, str(error) + '\n')
    print(json.dumps({'outcome': 'writer_registration_verified',
                      'card': requirement['expected']['card'],
                      'task': requirement['expected']['task']}))


if __name__ == '__main__':
    main()
