#!/usr/bin/env python3
"""Check an explicitly required JSONL writer registration without changing it."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import importlib.util
import subprocess
import sqlite3
from urllib.parse import quote

REQUIRED = {'card', 'task', 'workspace', 'base', 'scope'}


def validate_scope(scope):
    if (not isinstance(scope, list) or not scope or any(not isinstance(p, str) or not p
            or not Path(p).parts or Path(p).as_posix() != p
            or Path(p).is_absolute() or '..' in Path(p).parts or '.git' in Path(p).parts for p in scope)
            or len(set(scope)) != len(scope)):
        raise ValueError('Registration scope must contain distinct repository-relative paths')


def registry_path(registry):
    path = Path(registry)
    if (not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents))
            or path != path.resolve()):
        raise ValueError('Registration registry must be an absolute non-symlink path')
    return path


def capture_declaration(declaration, source, files, required_paths):
    """Capture explicit coordination input before native identity exists; never register."""
    if set(declaration) - {'registry', 'fields', 'scope', 'expected'}:
        raise ValueError('Unknown registration declaration field')
    path = registry_path(declaration['registry'])
    if path.suffix != '.jsonl':
        raise ValueError('Preparation requires an explicitly declared JSONL coordination registry')
    scope, fields = declaration['scope'], declaration['fields']
    validate_scope(scope)
    extra = declaration.get('expected', {})
    if (not isinstance(extra, dict) or REQUIRED & extra.keys()
            or set(fields) != REQUIRED | extra.keys()
            or any(not isinstance(v, str) or not v for v in fields.values())
            or len(set(fields.values())) != len(fields)):
        raise ValueError('Declaration requires distinct identity mappings and only extra expected fields')
    source = Path(source).resolve(strict=True)
    relative = path.relative_to(source).as_posix() if path.is_relative_to(source) else None
    if relative in set(scope) | set(required_paths) or relative in ('goals.json', 'TODO.md'):
        raise ValueError('Coordination registry cannot also be an executable or owned input')
    data = path.read_bytes()
    read_rows(data)
    digest = hashlib.sha256(data).hexdigest()
    rows = [row for row in files if row['path'] == relative]
    if rows and (len(rows) != 1 or rows[0]['sha256'] != digest):
        raise ValueError('Registry differs from original selection evidence')
    return dict(version=1, registry=str(path), fields=fields, scope=scope, expected=extra,
                source_path=relative, baseline=data.decode(), baseline_sha256=digest)


def prepare_requirement(pending, expected):
    """Allow exactly one attributed append, preserving all prior registry bytes."""
    if expected['scope'] != pending['scope']:
        raise ValueError('Registration scope differs from reserved contract')
    before = pending['baseline'].encode()
    if hashlib.sha256(before).hexdigest() != pending['baseline_sha256']:
        raise ValueError('Original registry baseline changed')
    path = registry_path(pending['registry'])
    data = path.read_bytes()
    if not data.startswith(before) or (before and not before.endswith(b'\n')):
        raise ValueError('Registration must preserve original bytes and append one row')
    appended = read_rows(data[len(before):])
    row = {pending['fields'][key]: value for key, value in expected.items()}
    if appended != [row]:
        raise ValueError('Registration change must be exactly the original card identity and scope')
    requirement = dict(registry=str(path), digest=hashlib.sha256(data).hexdigest(),
                       fields=pending['fields'], expected=expected)
    verify(**requirement)
    return requirement


def native_observation(profile, card):
    """Read CLI-resolved native state; omitted claim/budget fields use read-only SQL."""
    if (not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*', profile)
            or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*', card)):
        raise ValueError('Invalid original native identity')
    prefix = ['hermes', '-p', profile]
    boards = json.loads(subprocess.check_output(prefix + ['kanban', 'boards', 'list', '--json'],
                                                text=True, timeout=30), object_pairs_hook=unique_object)
    matches = [board for board in boards if board.get('slug') == 'default']
    if len(matches) != 1:
        raise ValueError('Canonical native board is unavailable or ambiguous')
    board = matches[0]
    state = json.loads(subprocess.check_output(prefix + ['kanban', '--board', 'default', 'show', card, '--json'],
                                               text=True, timeout=30), object_pairs_hook=unique_object)
    database = Path(board['db_path']).resolve(strict=True)
    with sqlite3.connect('file:' + quote(str(database)) + '?mode=ro', uri=True) as db:
        row = db.execute('SELECT status,current_run_id,worker_pid,goal_mode,goal_max_turns FROM tasks WHERE id=?', (card,)).fetchone()
    if row is None or state['task']['id'] != card or state['task']['status'] != row[0]:
        raise ValueError('Native card changed during observation')
    state['task'].update(current_run_id=row[1], worker_pid=row[2], goal_mode=bool(row[3]), goal_max_turns=row[4],
                         board_id=board.get('id') or board.get('board_id') or str(database))
    return state


def prepare_handoff(handoff_path, digest, native, output):
    """Produce reviewable prerequisites, never a native release or runtime migration."""
    raw = Path(handoff_path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('Original handoff changed')
    handoff = json.loads(raw, object_pairs_hook=unique_object)
    manifest_raw = Path(handoff['pass_manifest_path']).read_bytes()
    if hashlib.sha256(manifest_raw).hexdigest() != handoff['pass_manifest_sha256']:
        raise ValueError('Original pass manifest changed')
    manifest = json.loads(manifest_raw, object_pairs_hook=unique_object)
    if manifest != handoff['pass_manifest'] or manifest.get('helper_runtime') != handoff.get('helper_runtime'):
        raise ValueError('Original runtime/manifest binding changed')
    pending = manifest.get('registration_preparation')
    if not pending:
        raise ValueError('Original-card prerequisite/runtime migration unavailable; preserve original evidence')
    task = native['task']
    if (native.get('runs') != [] or task.get('status') != 'blocked'
            or not {'current_run_id', 'worker_pid'} <= task.keys()
            or task.get('current_run_id') or task.get('worker_pid')
            or any(task.get(key) != handoff[value] for key, value in
                   [('id', 'task_id'), ('board_id', 'board_id'), ('assignee', 'profile'),
                    ('workspace_path', 'workspace')]) or task.get('workspace_kind') != 'dir'):
        raise ValueError('Original blocked card identity or unused native claim changed')
    if (task.get('goal_mode') not in (True, 1) or task.get('goal_max_turns') != handoff['goal_max_turns']
            or task.get('max_retries') != handoff['max_retries']
            or task.get('completion_contract') != 'local-only'):
        raise ValueError('Original allocation or completion policy changed')
    if (manifest['candidate_identity']['workspace'] != handoff['workspace']
            or manifest['source_workspace'] != handoff['source_workspace']
            or manifest['goal_task'] != handoff['goal_task']):
        raise ValueError('Original task/workspace binding changed')
    expected = dict(pending['expected'], card=handoff['task_id'], task=handoff['goal_task'],
                    workspace=handoff['workspace'], base=manifest['candidate_identity']['base_commit'],
                    scope=pending['scope'])
    requirement = prepare_requirement(pending, expected)
    spec = importlib.util.spec_from_file_location('registration_pass', Path(__file__).with_name('pass_workspace.py'))
    passes = importlib.util.module_from_spec(spec); spec.loader.exec_module(passes)
    passes.verify_registration_preparation(manifest, handoff['workspace'], requirement)
    runtime_spec = importlib.util.spec_from_file_location('registration_runtime', Path(__file__).with_name('runtime_bundle.py'))
    runtime = importlib.util.module_from_spec(runtime_spec); runtime_spec.loader.exec_module(runtime)
    frozen = runtime.verify(handoff['helper_runtime'])
    for name in ('writer_registration.py', 'pass_workspace.py'):
        original_helper = frozen['files'].get('autowork/scripts/' + name, {})
        if original_helper.get('sha256') != hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest():
            raise ValueError('Original frozen helper differs; supported runtime migration unavailable')
    requirement['sha256'] = requirement.pop('digest')
    report = dict(outcome='registration_prepared_native_transition_unavailable', expected=expected,
                  original_handoff_sha256=digest, original_manifest_sha256=handoff['pass_manifest_sha256'],
                  registry_before_sha256=pending['baseline_sha256'], registry_after_sha256=requirement['sha256'],
                  helper_runtime=handoff['helper_runtime'], native_execution='held',
                  unavailable=['atomic same-card prerequisite record/release', 'existing frozen-runtime migration'])
    artifacts = {'original-handoff.json': raw, 'original-manifest.json': manifest_raw,
                 'registry-before.jsonl': pending['baseline'].encode(),
                 'registry-after.jsonl': Path(pending['registry']).read_bytes(),
                 'requirement.json': (json.dumps(requirement, sort_keys=True, indent=2) + '\n').encode(),
                 'native-observation.json': (json.dumps(native, sort_keys=True, indent=2) + '\n').encode(),
                 'preparation.json': (json.dumps(report, sort_keys=True, indent=2) + '\n').encode()}
    if hashlib.sha256(artifacts['registry-after.jsonl']).hexdigest() != requirement['sha256']:
        raise ValueError('Registry changed during preparation')
    output = Path(output).absolute()
    if any(path.is_symlink() for path in (output, *output.parents)):
        raise ValueError('Preparation output must not traverse a symlink')
    output = output.resolve()
    if any(output.is_relative_to(Path(handoff[key]).resolve()) for key in ('workspace', 'source_workspace')):
        raise ValueError('Preparation evidence must stay outside source and worker workspaces')
    output.mkdir(parents=True, exist_ok=True)
    for name, content in artifacts.items():
        path = output / name
        if path.is_symlink() or (path.exists() and path.read_bytes() != content):
            raise ValueError('Retained preparation evidence differs: ' + name)
    for name, content in artifacts.items():
        path = output / name
        if not path.exists():
            with path.open('xb') as stream:
                stream.write(content)
    return report


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
    validate_scope(expected['scope'])
    path = registry_path(registry)
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
    parser.add_argument('--requirement', help='Private JSON with registry, sha256, fields, expected')
    parser.add_argument('--requirement-sha256', help='Pin from coordinator handoff')
    parser.add_argument('--prepare-handoff', help='Original blocked handoff receipt; preparation does not dispatch')
    parser.add_argument('--handoff-sha256', help='Original receipt hash')
    parser.add_argument('--output', help='Private immutable preparation evidence directory; retry resumes identical bytes')
    args = parser.parse_args()
    try:
        if args.prepare_handoff:
            if not args.handoff_sha256 or not args.output or args.requirement or args.requirement_sha256:
                raise ValueError('Preparation requires handoff hash and output, without a requirement override')
            raw = Path(args.prepare_handoff).read_bytes()
            if hashlib.sha256(raw).hexdigest() != args.handoff_sha256:
                raise ValueError('Original handoff changed')
            receipt = json.loads(raw, object_pairs_hook=unique_object)
            native = native_observation(receipt['profile'], receipt['task_id'])
            report = prepare_handoff(args.prepare_handoff, args.handoff_sha256, native, args.output)
            latest = native_observation(receipt['profile'], receipt['task_id'])
            if latest != native:
                raise ValueError('Native state changed during preparation; retained evidence is stale, execution remains held')
            print(json.dumps(report))
            return
        if not args.requirement or not args.requirement_sha256 or args.handoff_sha256 or args.output:
            raise ValueError('Verification requires requirement and requirement hash only')
        raw = Path(args.requirement).read_bytes()
        if hashlib.sha256(raw).hexdigest() != args.requirement_sha256:
            raise ValueError('Registration requirement changed')
        requirement = json.loads(raw, object_pairs_hook=unique_object)
        verify(requirement['registry'], requirement['sha256'], requirement['fields'], requirement['expected'])
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error, subprocess.SubprocessError) as error:
        parser.exit(2, str(error) + '\n')
    print(json.dumps({'outcome': 'writer_registration_verified',
                      'card': requirement['expected']['card'],
                      'task': requirement['expected']['task']}))


if __name__ == '__main__':
    main()
