"""Explicit, private Hermes observer reviews; classification, not a sandbox.

Bind a unique job to its complete saved execution contract. Only known scheduler
observations may drift without review. Never infer read-only authority from prose.
"""
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import re


OBSERVATIONS = frozenset({'last_run_at', 'next_run_at', 'last_status', 'last_error',
                          'last_delivery_error', 'last_execution_error', 'last_failure',
                          'failure_streak'})


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON field')
        result[key] = value
    return result


def _constant(value):
    raise ValueError('nonfinite JSON value')


def _float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('nonfinite JSON value')
    return number


def _read(path):
    return json.loads(path.read_text(), object_pairs_hook=_object,
                      parse_constant=_constant, parse_float=_float)


def contract_sha256(job):
    """Hash a reviewed job snapshot. Computing a hash does not grant a review."""
    config = {key: value for key, value in job.items() if key not in OBSERVATIONS}
    if isinstance(config.get('repeat'), dict):
        config['repeat'] = {key: value for key, value in config['repeat'].items() if key != 'completed'}
    return hashlib.sha256(json.dumps(config, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def _reviews(path, repo, home):
    if not path:
        return {}
    if not Path(path).is_absolute():
        raise ValueError('policy path must be absolute')
    data = _read(Path(path))
    if (not isinstance(data, dict) or set(data) != {'version', 'repo', 'hermes_home', 'observers'}
            or type(data['version']) is not int or data['version'] != 1
            or data['repo'] != repo or data['hermes_home'] != home
            or not isinstance(data['observers'], list)):
        raise ValueError('invalid policy schema or repository/installation binding')
    reviews = {}
    for entry in data['observers']:
        if (not isinstance(entry, dict) or set(entry) != {'profile', 'id', 'sha256'}
                or any(not isinstance(value, str) or not value for value in entry.values())
                or not re.fullmatch(r'[0-9a-f]{64}', entry['sha256'])):
            raise ValueError('invalid observer binding')
        identity = (entry['profile'], entry['id'])
        if identity in reviews:
            raise ValueError('duplicate observer binding')
        reviews[identity] = entry['sha256']
    return reviews


def _jobs(data):
    jobs = data.get('jobs') if isinstance(data, dict) else data
    if not isinstance(jobs, list):
        raise ValueError('invalid jobs list')
    for job in jobs:
        if not isinstance(job, dict) or not isinstance(job.get('id'), str) or not job['id']:
            raise ValueError('invalid job identity')
        for key in ('workdir', 'prompt', 'skill', 'paused_at', 'state'):
            if job.get(key) is not None and not isinstance(job[key], str):
                raise ValueError('invalid job field')
        workdir = job.get('workdir')
        if workdir and ('\x00' in workdir or not os.path.isabs(workdir)):
            raise ValueError('ambiguous workdir')
        if 'enabled' in job and type(job['enabled']) is not bool:
            raise ValueError('invalid enabled flag')
        for key in ('skills', 'enabled_toolsets'):
            value = job.get(key)
            if value is not None and (not isinstance(value, list)
                                      or any(not isinstance(item, str) for item in value)):
                raise ValueError('invalid selection')
    return jobs


def _stores(home):
    yield 'default', home / 'cron/jobs.json'
    # Unlike glob, scandir reports permission and IO errors rather than making a
    # failed profile scan indistinguishable from an installation with no jobs.
    try:
        with os.scandir(home / 'profiles') as entries:
            profiles = []
            for entry in entries:
                if entry.is_dir():
                    profiles.append(entry.name)
                elif entry.is_symlink():
                    raise ValueError('unresolvable profile link')
            profiles.sort()
    except FileNotFoundError:
        if (home / 'profiles').is_symlink():
            raise ValueError('broken profiles link')
        return
    for profile in profiles:
        yield profile, home / 'profiles' / profile / 'cron/jobs.json'


def _active(job):
    return job.get('enabled') is not False and not job.get('paused_at') and job.get('state') != 'paused'


def _targets(job, repo):
    return bool(job.get('workdir')) and os.path.realpath(job['workdir']) == repo


def _development_skill(job):
    for selected in [job.get('skill') or '', *(job.get('skills') or [])]:
        selected = selected.strip()
        names = [os.path.normpath(selected)]
        if '/' in selected:
            names.append(os.path.realpath(os.path.expanduser(selected)))
        for name in names:
            name = name.lower().rstrip('/')
            if name.endswith('/skill.md'):
                name = name[:-len('/skill.md')]
            if name.rsplit('/', 1)[-1].rsplit(':', 1)[-1] == 'autowork':
                return True
    return False


def competing_jobs(repo, home, policy=None):
    """Return refusal lines for startup and installation; empty means no overlap."""
    repo, home = os.path.realpath(repo), os.path.realpath(home)
    problems, rows = [], []
    try:
        reviews = _reviews(policy, repo, home)
    except (OSError, ValueError, UnicodeError, RecursionError):
        reviews = {}
        problems.append('Invalid Hermes observer policy; no observer exemptions applied.')
    try:
        for profile, path in _stores(Path(home)):
            try:
                jobs = _jobs(_read(path))
            except FileNotFoundError:
                if not any(part.is_symlink() and not part.exists() for part in (path, path.parent)):
                    continue  # a profile need not have a cron store
                problems.append(f'{profile}: cannot verify Hermes cron store; review required.')
                continue
            except (OSError, ValueError, UnicodeError, RecursionError):
                problems.append(f'{profile}: cannot verify Hermes cron store; review required.')
                continue
            rows.extend((profile, job) for job in jobs)
    except (OSError, ValueError):
        problems.append('Cannot verify Hermes profile stores; review required.')
    identities = Counter((profile, job['id']) for profile, job in rows)
    permitted = set()
    for identity, digest in reviews.items():
        if identities[identity] != 1:
            problems.append(f'{identity[0]}: observer identity missing or ambiguous; review required.')
            continue
        job = next(job for profile, job in rows if (profile, job['id']) == identity)
        if not _active(job):
            continue  # paused/disabled jobs do not compete, even after contract drift
        try:
            valid = (_targets(job, repo) and not _development_skill(job)
                     and contract_sha256(job) == digest)
        except (OSError, ValueError, RecursionError):
            valid = False
        if not valid:
            problems.append(f'{identity[0]}: observer contract changed or selects development; review required.')
            continue
        permitted.add(identity)
    for profile, job in rows:
        if not _active(job) or not _targets(job, repo) or (profile, job['id']) in permitted:
            continue
        text = ' '.join(str(job.get(key) or '') for key in ('skill', 'skills', 'prompt'))
        try:
            development = _development_skill(job)
        except (OSError, ValueError):
            development = True  # an unresolvable skill cannot establish safe coexistence
        if development or 'autowork' in text.lower():
            problems.append(f"{profile}: {job.get('name') or job['id']}")
    return '\n'.join(problems)
