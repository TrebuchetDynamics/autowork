#!/usr/bin/env python3
"""Create a registered card atomically through the installed native Python API.

Run with the selected Hermes installation's Python runtime. The dispatcher sees
no card until its exact registration and startup guard pass. No existing card is
released, migrated, retried or replaced. Files and SQLite are separate resources:
an interrupted/failed transaction retains attributable evidence for reconciliation.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pass_workspace
import runtime_bundle
import writer_registration


def publish(path, value):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Registration receipt must not traverse symlinks')
    if path.exists():
        raise ValueError('Retained registration attempt exists; reconcile it before another admission')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    try:
        with temporary.open('x') as stream:
            os.chmod(temporary, 0o600)
            json.dump(value, stream, sort_keys=True, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        temporary.unlink(missing_ok=True)


def create_registered(kb, conn, request):
    if os.environ.get('HERMES_KANBAN_TASK'):
        raise ValueError('Registered admission is coordinator-only')
    path = Path(request['manifest_path'])
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != request['manifest_sha256']:
        raise ValueError('Original registration manifest changed')
    manifest = json.loads(raw, object_pairs_hook=writer_registration.unique_object)
    pending = manifest['registration_preparation']
    task = request['task']
    template = request['handoff_template']
    bindings = dict(profile=request['profile'], workspace=manifest['candidate_identity']['workspace'],
                    source_workspace=manifest['source_workspace'], goal_task=manifest['goal_task'],
                    pass_manifest_path=str(path), pass_manifest_sha256=request['manifest_sha256'],
                    pass_manifest=manifest, helper_runtime=manifest['helper_runtime'])
    if (any(template.get(k) != v for k, v in bindings.items())
            or {'task_id', 'native_create'} & template.keys()
            or task.get('assignee') != request['profile']
            or task.get('workspace_kind') != 'dir' or task.get('workspace_path') != bindings['workspace']
            or task.get('goal_mode') is not True or template.get('goal_mode') is not True
            or task.get('goal_max_turns') not in (50, 100)
            or task['goal_max_turns'] != template.get('goal_max_turns')
            or task.get('max_retries') != 1 or template.get('max_retries') != 1
            or task.get('completion_contract') != 'local-only'
            or task.get('created_by') != 'autowork'
            or not task.get('idempotency_key') or 'initial_status' in task):
        raise ValueError('Registered admission differs from original task/workspace/allocation')
    receipt_path = Path(request['receipt_path']).absolute()
    if receipt_path.parent != path.absolute().parent or not receipt_path.name.startswith('reservation-'):
        raise ValueError('Registration receipt must be in the original manifest journal')
    if receipt_path.exists():
        raise ValueError('Retained registration attempt exists; reconcile it before another admission')
    attempt_key = hashlib.sha256(json.dumps([request['profile'], manifest['source_workspace'],
        manifest['goal_task']], separators=(',', ':')).encode()).hexdigest()
    attempt_path = receipt_path.parent / ('registration-attempt-' + attempt_key + '.json')
    if attempt_path.exists():
        raise ValueError('Retained registration attempt exists for this task; reconcile before retry')
    frozen = runtime_bundle.verify(manifest['helper_runtime'])
    for name in ('pass_workspace.py', 'writer_registration.py'):
        if frozen['files']['autowork/scripts/' + name]['sha256'] != hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest():
            raise ValueError('Frozen registration guard differs from admission implementation')
    pass_workspace.verify_registration_preparation(manifest, task['workspace_path'])
    registry = writer_registration.registry_path(pending['registry'])
    baseline = pending['baseline'].encode()
    # Coordinate participating registry writers; exact readback also catches
    # appenders which do not use this lock. Never rewrite their evidence.
    fd = os.open(registry, os.O_RDWR | os.O_APPEND | os.O_NOFOLLOW)
    with os.fdopen(fd, 'r+b') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if stream.read() != baseline or registry.read_bytes() != baseline:
            raise ValueError('Registry changed before native admission')
        publish(attempt_path, dict(profile=request['profile'], goal_task=manifest['goal_task'],
            idempotency_key=task['idempotency_key'], receipt_path=str(receipt_path),
            manifest_path=str(path), manifest_sha256=request['manifest_sha256'], native_commit='unverified'))
        with kb.write_txn(conn):
            fallback = template.get('disjoint_fallback')
            if fallback:
                original = kb.get_task(conn, fallback['original_card'])
                runs = kb.list_runs(conn, fallback['original_card'])
                if (original is None or original.status != 'blocked'
                        or original.assignee != request['profile']
                        or original.workspace_path != fallback['original_workspace']
                        or any(getattr(original, key, None) for key in ('current_run_id', 'worker_pid', 'claim_lock'))
                        or hashlib.sha256((original.body or '').encode()).hexdigest() != fallback['original_body_sha256']
                        or not runs or any(not run.ended_at for run in runs)
                        or runs[-1].id != fallback['original_run_id']
                        or runs[-1].status not in ('blocked', 'crashed')):
                    raise ValueError('Original blocked ownership changed before registered admission')
            # Native create_task explicitly supports nested transactions. Native
            # unblock_task does not, and is intentionally never invoked here.
            if conn.execute("SELECT id FROM tasks WHERE idempotency_key=? LIMIT 1",
                            (task['idempotency_key'],)).fetchone():
                raise ValueError('Original idempotency key already has a card; reconcile without replacement')
            card = kb.create_task(conn, initial_status='running', project_id='', board='default', **task)
            native = kb.get_task(conn, card)
            if (native is None or native.status != 'ready' or kb.list_runs(conn, card)
                    or getattr(native, 'project_id', None) is not None
                    or any(getattr(native, key, None) != value for key, value in task.items())
                    or any(getattr(native, key, None) for key in ('current_run_id', 'worker_pid', 'claim_lock', 'consecutive_failures'))):
                raise ValueError('Native creation returned a changed or previously used card')
            expected = dict(pending['expected'], card=card, task=manifest['goal_task'],
                workspace=task['workspace_path'], base=manifest['candidate_identity']['base_commit'], scope=pending['scope'])
            row = {pending['fields'][key]: value for key, value in expected.items()}
            append = (json.dumps(row, sort_keys=True) + '\n').encode()
            # Before touching the registry, retain identity even if SQLite later
            # rolls back. This receipt is never a claim that COMMIT succeeded.
            receipt = dict(template, task_id=card, native_create={'id':card},
                           native_commit='unverified', registration_expected=expected,
                           registry_before_sha256=pending['baseline_sha256'],
                           registry_after_sha256=hashlib.sha256(baseline + append).hexdigest())
            publish(receipt_path, receipt)
            stream.write(append)
            stream.flush()
            os.fsync(stream.fileno())
            if registry.stat().st_ino != os.fstat(stream.fileno()).st_ino:
                raise ValueError('Registry replaced during admission; preserve attributed append')
            pass_workspace.verify(manifest, task['workspace_path'], registration_card_id=card)
            if path.read_bytes() != raw:
                raise ValueError('Registration manifest changed during admission')
            kb.add_comment(conn, card, 'autowork', 'Registration verified before initial dispatch; '
                'original manifest sha256=' + request['manifest_sha256'] + '; receipt sha256=' +
                hashlib.sha256(receipt_path.read_bytes()).hexdigest())
    return {'id':card, 'outcome':'registered_card_created', 'status':'ready',
            'registration_receipt':str(receipt_path), 'worker_execution':'not_observed'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True)
    args = parser.parse_args()
    try:
        request = json.loads(Path(args.request).read_text(), object_pairs_hook=writer_registration.unique_object)
        db = Path(request['db_path'])
        if not db.is_absolute() or not db.is_file() or any(p.is_symlink() for p in (db, *db.parents)):
            raise ValueError('Existing canonical native board is required')
        from hermes_cli import kanban_db as kb
        from hermes_cli.kanban_db_connect import connect_closing
        with connect_closing(db_path=db) as conn:
            print(json.dumps(create_registered(kb, conn, request)))
    except (ValueError, OSError, KeyError, TypeError, ImportError, RuntimeError) as exc:
        parser.exit(2, str(exc) + '; preserve any retained registration attempt\n')


if __name__ == '__main__':
    main()
