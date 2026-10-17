#!/usr/bin/env python3
"""Repair managed wiring of one existing development cron; preview by default."""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

_spec = importlib.util.spec_from_file_location('owner_cron_wiring', Path(__file__).with_name('wire-owner-cron.py'))
wiring = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wiring)

# Scheduler observations may advance during an edit. Everything else is policy,
# including unknown future fields: do not silently waive a configuration change.
OBSERVATIONS = {'last_run_at', 'next_run_at', 'last_status', 'last_error',
                'last_delivery_error', 'last_execution_error', 'last_failure',
                'failure_streak', 'fire_claim', 'run_claim', 'pending_slot',
                'last_dispatch', 'last_fire_error', 'preflight_alerted',
                'last_delivery_unverified', 'last_delivery_queued', 'monitor_state',
                'manual_run_at', 'manual_run_prompt', 'quota_hold_until',
                'quota_hold_cron_expr', 'unreachable_retry'}



class Refused(ValueError):
    """A refusal whose fixed message is safe to report (no job, prompt or native output)."""

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def configuration(job):
    result = {key: value for key, value in job.items() if key not in OBSERVATIONS}
    if isinstance(result.get('repeat'), dict):
        result['repeat'] = {key: value for key, value in result['repeat'].items() if key != 'completed'}
    return result


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Refused('duplicate JSON field')
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_text(), object_pairs_hook=unique_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(Refused('nonfinite JSON')))


def exact_job(home, job_id):
    path = home / 'cron/jobs.json'
    if path.is_symlink() or path.parent.is_symlink():
        raise Refused('refuse symlinked cron store')
    data = read_json(path)
    rows = data.get('jobs') if isinstance(data, dict) else data
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise Refused('invalid cron store')
    rows = [row for row in rows if row.get('id') == job_id]
    if len(rows) != 1:
        raise Refused('expected exactly one existing job in the selected profile')
    return rows[0]


def target(root, profile, job_id, repo):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', profile) or not re.fullmatch(r'[A-Za-z0-9_-]+', job_id):
        raise Refused('invalid profile or job ID')
    if root.parent.name == 'profiles' or root.is_symlink() or (root / 'profiles').is_symlink():
        raise Refused('use the default root with independent profile homes')
    home = root if profile == 'default' else root / 'profiles' / profile
    if home.is_symlink() or not (home / 'config.yaml').is_file():
        raise Refused('profile home missing or symlinked')
    job = exact_job(home, job_id)
    workdir = job.get('workdir')
    if not repo.is_absolute() or not repo.is_dir() or not isinstance(workdir, str) or not Path(workdir).is_absolute() or Path(workdir).resolve() != repo.resolve():
        raise Refused('saved workdir must match the explicit existing repository')
    if (not wiring.is_owner_job(job) or wiring.MARKER not in job.get('prompt', '')
            or job.get('no_agent') is True or type(job.get('enabled')) is not bool):
        raise Refused('requires a managed development Autowork job with explicit enabled state')
    if profile == 'default' and job.get('name') == wiring.AUDIT_JOB:
        raise Refused('audit jobs require their separate maintenance policy')
    return home, job


def save(path, value):
    fd, tmp = tempfile.mkstemp(prefix='.heal-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


class NotLaunched(Exception):
    """The OS refused process creation; no cron edit was executed."""


def run_edit(command, *, env):
    try:
        process = subprocess.Popen(command, env=env, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as error:
        raise NotLaunched from error
    with process:
        try:
            process.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, command)


def heal(root, profile, job_id, repo, *, apply=False, hermes='hermes'):
    root, repo = Path(root).absolute(), Path(repo)
    home, before = target(root, profile, job_id, repo)
    result = {'profile': profile, 'job_id': job_id, 'changed': False}
    if before['enabled'] is False or before.get('state') == 'paused':
        return {**result, 'state': 'paused'}
    prompt = wiring.owner_prompt(before['prompt'], True)
    skills = wiring.autowork_skills(before)
    expected = {**before, 'prompt': prompt, 'skills': skills, 'skill': skills[0]}
    if not apply:
        return {**result, 'state': 'unchanged' if configuration(before) == configuration(expected) else 'would_update'}
    directory = home / 'autowork/cron-heal'
    for path in (directory.parent, directory):
        if path.is_symlink():
            raise Refused('refuse symlinked healing state')
        path.mkdir(mode=0o700, exist_ok=True)
    receipt_path = directory / (job_id + '.json')
    lock_path = directory / (job_id + '.lock')
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {**result, 'state': 'busy'}
        if receipt_path.is_symlink():
            raise Refused('refuse symlinked healing receipt')
        previous = read_json(receipt_path) if receipt_path.exists() else None
        current = exact_job(home, job_id)
        current_hash = digest(configuration(current))
        if previous is not None:
            if (not isinstance(previous, dict) or previous.get('schema') != 1
                    or previous.get('profile') != profile or previous.get('job_id') != job_id
                    or previous.get('state') not in ('pending', 'updated_verified', 'not_launched')
                    or not re.fullmatch('[0-9a-f]{64}', str(previous.get('expected_sha256', '')))):
                raise Refused('invalid saved healing receipt; inspect without resetting it')
            if previous['state'] == 'pending':
                if current_hash == previous['expected_sha256']:
                    save(receipt_path, {**previous, 'state': 'updated_verified'})
                    return {**result, 'state': 'updated_verified', 'changed': True, 'reconciled': True}
                return {**result, 'state': 'edit_uncertain',
                        'next_action': 'Inspect the original edit outcome and current job configuration; do not replay or replace the job.'}
        if current_hash != digest(configuration(before)):
            return {**result, 'state': 'configuration_changed', 'next_action': 'Reread current job policy before repair.'}
        if configuration(before) == configuration(expected):
            return {**result, 'state': 'unchanged'}
        receipt = {'schema': 1, 'profile': profile, 'job_id': job_id, 'state': 'pending',
                   'before_sha256': current_hash, 'expected_sha256': digest(configuration(expected))}
        save(receipt_path, receipt)  # Persist before any possible native write.
        command = [hermes, '-p', profile, 'cron', 'edit', job_id, '--prompt', prompt]
        for skill in skills:
            command += ['--skill', skill]
        env = dict(os.environ, HERMES_HOME=str(root))
        env.pop('HERMES_PROFILE', None)
        try:
            run_edit(command, env=env)
        except NotLaunched:
            # Popen failed before any child existed: it is safe to try again once
            # the executable/permissions are repaired, without an uncertain write.
            save(receipt_path, {**receipt, 'state': 'not_launched'})
            return {**result, 'state': 'launcher_unavailable',
                    'next_action': 'Restore the verified Hermes executable or its execute permission, then retry.'}
        except (subprocess.SubprocessError, OSError):
            # An error is not proof the write failed; read back before any retry.
            pass
        try:
            after = exact_job(home, job_id)
            if digest(configuration(after)) != receipt['expected_sha256']:
                raise Refused('configuration readback mismatch')
        except (ValueError, OSError, KeyError, TypeError):
            return {**result, 'state': 'edit_uncertain',
                    'next_action': 'Inspect the original edit outcome and current job configuration; do not replay or replace the job.'}
        save(receipt_path, {**receipt, 'state': 'updated_verified'})
        return {**result, 'state': 'updated_verified', 'changed': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--job-id', required=True)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        result = heal(args.root, args.profile, args.job_id, args.repo, apply=args.apply)
    except (ValueError, OSError, TypeError, KeyError) as error:
        # Avoid emitting native command output or saved prompt/config secrets.
        result = {'state': 'refused', 'reason': str(error) if isinstance(error, Refused) else type(error).__name__}
    print(json.dumps(result, sort_keys=True))
    return 0 if result['state'] in ('unchanged', 'updated_verified', 'would_update', 'paused') else 1


if __name__ == '__main__':
    raise SystemExit(main())
