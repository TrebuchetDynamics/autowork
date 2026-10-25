"""Fail-closed, explicitly reviewed Hermes observer classification (not a sandbox).

A private policy binds the repository, Hermes installation, profile and unique job
ID to a SHA-256 of the complete job configuration. Unknown fields are policy too.
Only the scheduler observations below can change without a fresh review.
"""
from collections import Counter
import hashlib
import json
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


def _read(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=_object, parse_constant=_constant)


def contract_sha256(job):
    """Fingerprint for a human-reviewed snapshot; computing it grants no exemption."""
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
    data = _read(path)
    if (not isinstance(data, dict) or set(data) != {'version', 'repo', 'hermes_home', 'observers'}
            or type(data['version']) is not int or data['version'] != 1
            or data['repo'] != repo or data['hermes_home'] != home
            or not isinstance(data['observers'], list)):
        raise ValueError('policy schema or repository/installation binding mismatch')
    result = {}
    for entry in data['observers']:
        if (not isinstance(entry, dict) or set(entry) != {'profile', 'id', 'sha256'}
                or any(not isinstance(entry[key], str) or not entry[key] for key in entry)
                or not re.fullmatch(r'[0-9a-f]{64}', entry['sha256'])):
            raise ValueError('invalid observer binding')
        identity = (entry['profile'], entry['id'])
        if identity in result:
            raise ValueError('duplicate observer identity')
        result[identity] = entry['sha256']
    return result


def _active(job):
    return job.get('enabled') is not False and not job.get('paused_at') and job.get('state') != 'paused'


def _targets_repo(job, repo):
    workdir = job.get('workdir')
    try:
        return isinstance(workdir, str) and bool(workdir) and os.path.realpath(workdir) == repo
    except (OSError, ValueError):
        return False


def _development_skill(job):
    skill, skills = job.get('skill'), job.get('skills')
    if ((skill is not None and not isinstance(skill, str))
            or (skills is not None and (not isinstance(skills, list)
                                       or any(not isinstance(s, str) for s in skills)))):
        return True  # malformed selection cannot be a verified observer
    for selected in [skill or '', *(skills or [])]:
        selected = selected.strip()
        # Check the explicit spelling too: a symlink cannot hide either an
        # Autowork target or a selection explicitly named Autowork.
        names = [os.path.normpath(selected)]
        if '/' in selected:
            try:
                names.append(os.path.realpath(os.path.expanduser(selected)))
            except (OSError, ValueError):
                return True  # an unresolvable selection is not a reviewed observer
        for name in names:
            name = name.lower().rstrip('/')
            if name.endswith('/skill.md'):
                name = name[:-len('/skill.md')]
            if name.rsplit('/', 1)[-1].rsplit(':', 1)[-1] == 'autowork':
                return True
    return False


def competing_jobs(repo, home, policy=None):
    """Return startup/install refusal lines, excluding only exact reviewed observers."""
    repo, home = os.path.realpath(repo), os.path.realpath(home)
    problems, rows = [], []
    try:
        reviews = _reviews(policy, repo, home)
    except (OSError, ValueError, UnicodeError):
        reviews = {}
        problems.append('Invalid Hermes observer policy; no observer exemptions applied.')
    root = Path(home)
    paths = [root / 'cron/jobs.json', *sorted(root.glob('profiles/*/cron/jobs.json'))]
    for path in paths:
        relative = path.relative_to(root).parts
        profile = relative[1] if relative[0] == 'profiles' else 'default'
        try:
            data = _read(path)
            jobs = data.get('jobs', []) if isinstance(data, dict) else data
            if not isinstance(jobs, list) or any(not isinstance(job, dict) for job in jobs):
                raise ValueError('invalid jobs list')
        except FileNotFoundError:
            continue
        except (OSError, ValueError, UnicodeError):
            if policy:
                problems.append(f'{profile}: cannot verify Hermes cron store; no observer exemption.')
            continue
        rows.extend((profile, job) for job in jobs)
    identities = Counter((profile, job.get('id')) for profile, job in rows if isinstance(job.get('id'), str))
    permitted = set()
    for identity, digest in reviews.items():
        if identities[identity] != 1:
            problems.append(f'{identity[0]}: observer identity missing or ambiguous; review required.')
            continue
        job = next(job for profile, job in rows if (profile, job.get('id')) == identity)
        if not _active(job):
            continue  # paused/disabled jobs never compete, including changed contracts
        if _development_skill(job) or contract_sha256(job) != digest or not _targets_repo(job, repo):
            problems.append(f'{identity[0]}: observer contract changed or selects development; review required.')
            continue
        permitted.add(identity)
    for profile, job in rows:
        if not _targets_repo(job, repo) or not _active(job):
            continue
        identity = (profile, job.get('id')) if isinstance(job.get('id'), str) else None
        if identity in permitted:
            continue
        text = ' '.join(str(job.get(key) or '') for key in ('skill', 'skills', 'prompt'))
        if 'autowork' in text.lower():
            problems.append(f"{profile}: {job.get('name') or job.get('id')}")
    return '\n'.join(problems)
