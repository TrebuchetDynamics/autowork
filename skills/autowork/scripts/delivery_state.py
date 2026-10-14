"""Conservative delivery claims from explicit, candidate-bound evidence.

This validates receipts, not their issuers: fixture scope stays fixture scope.
Git integration is independently read from the supplied local repository.
"""
import re
import subprocess
import os
import tempfile
from pathlib import Path
import check_receipt
import candidate_identity


def qualification_check(check, candidate, repo):
    """Validate helper evidence against explicitly supplied verification inputs."""
    if repo is None or not isinstance(check, dict):
        return None
    receipt = check.get('receipt')
    scope = check.get('qualification_scope')
    if (not isinstance(check.get('name'), str) or not check['name'].strip()
            or not isinstance(receipt, dict) or receipt.get('version') != 2
            or receipt.get('qualification') != 'exact_candidate'
            or receipt.get('candidate') != candidate or receipt.get('outcome') != 'passed'
            or scope is None or receipt.get('qualification_scope') != scope
            or not isinstance(check.get('command'), list) or not check['command']
            or not all(isinstance(arg, str) for arg in check['command'])
            or any(not isinstance(check.get(k), list)
                   or not all(isinstance(p, str) and p for p in check[k])
                   for k in ('paths', 'external_paths'))):
        return None
    try:
        if not check_receipt.reusable(receipt, repo, check['command'], candidate=candidate,
                                      paths=check['paths'], external_paths=check['external_paths'],
                                      qualification_scope=scope):
            return None
        return dict(scope, name=check['name'])
    except (ValueError, KeyError, TypeError, OSError, subprocess.TimeoutExpired):
        return None


def local_review(candidate, integration, policy):
    """Caller-owned policy is separate from worker assertions, not authentication."""
    if not isinstance(policy, dict):
        return False
    reviewers = policy.get('reviewers')
    implementer = policy.get('implementer')
    authority = policy.get('authority')
    provenance = integration.get('provenance')
    if (type(policy.get('version')) is not int or policy['version'] != 1
            or policy.get('mode') != 'reviewed_local' or policy.get('candidate') != candidate
            or policy.get('target') != integration.get('target')
            or not isinstance(authority, str) or not authority.strip()
            or not isinstance(implementer, str) or not implementer.strip()
            or not isinstance(reviewers, list) or not reviewers
            or any(not isinstance(r, str) or not r.strip() or r == implementer for r in reviewers)
            or len(set(reviewers)) != len(reviewers)
            or not isinstance(provenance, dict)
            or set(provenance) != {'source', 'authority', 'observed', 'review'}
            or provenance.get('source') != 'reviewed_local'
            or provenance.get('authority') != authority or provenance.get('observed') is not True):
        return False
    review = provenance.get('review')
    approved = (isinstance(review, dict) and review.get('candidate') == candidate
            and review.get('implementer') == implementer and review.get('reviewer') in reviewers
            and review.get('observed') is True and review.get('outcome') == 'approved'
            and isinstance(review.get('id'), str) and bool(review['id'].strip()))
    if 'closeout' not in policy:
        return approved
    if not approved or not isinstance(review, dict):
        return False
    closeout = policy['closeout']
    return (approved and isinstance(closeout, dict)
            and type(policy.get('run_id')) is int
            and type(closeout.get('review_run_id')) is int
            and closeout['review_run_id'] > policy['run_id']
            and isinstance(policy.get('task_id'), str) and bool(policy['task_id'])
            and review.get('task_id') == policy['task_id']
            and type(review.get('run_id')) is int
            and review['run_id'] == closeout['review_run_id']
            and type(review.get('implementation_run_id')) is int
            and review['implementation_run_id'] == policy['run_id']
            and isinstance(closeout.get('delivery_evidence'), dict)
            and closeout['delivery_evidence'].get('candidate') == candidate
            and closeout['delivery_evidence'].get('integration') == integration)


def changed_base_checks(original, integration, policy, repo):
    """The newer-main result needs its own identity and exact executed checks."""
    result = integration.get('result_candidate')
    qualification = integration.get('qualification')
    if (not isinstance(result, dict) or not candidate_identity.check(result, repo)
            or result.get('base_commit') != integration.get('before')
            or result.get('candidate_commit') != integration.get('after')
            or result.get('prerequisites') != original.get('prerequisites')):
        return False
    evidence = policy['closeout']['delivery_evidence']
    original_qualification = evidence.get('qualification')
    if not isinstance(original_qualification, dict) or not isinstance(qualification, dict):
        return False
    required = original_qualification.get('required_checks')
    result_required = qualification.get('required_checks')
    if (not isinstance(required, list) or not required
            or not isinstance(result_required, list)
            or any(not isinstance(name, str) for name in required + result_required)
            or not set(required).issubset(result_required)):
        return False
    # Reuse the exact-candidate checker, not worker result strings. This nested
    # evaluation has no integration/policy and cannot confer delivery recursively.
    checked = evaluate({'candidate': result, 'implementation': evidence.get('implementation'),
                        'qualification': qualification, 'required_mode': evidence.get('required_mode')}, repo)
    return checked['qualified']


def integration_state(candidate, integration, repo, local_policy=None, *, historical=False):
    """Read Git/provenance; historical local truth is not current-target admission.

    Both modes validate the original integration topology and candidate pins.
    Only historical mode permits main to descend from the recorded integration.
    Neither result grants mutation or publication authority.
    """
    if repo is None or not isinstance(integration, dict) or not valid_candidate(candidate):
        return 'unknown'
    if integration.get('candidate') != candidate or integration.get('target') != 'refs/heads/main':
        return 'unknown'
    candidate = candidate_fields(candidate)
    def git(*args):
        return subprocess.run(['git', '-C', str(repo), *args], text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
                              env=candidate_identity.git_environment())
    def revision(value):
        if not isinstance(value, str) or re.fullmatch(r'[0-9a-f]{40}', value) is None:
            return False
        result = git('rev-parse', '--verify', value + '^{commit}')
        return result.returncode == 0 and result.stdout.strip() == value
    def ancestor(a, b):
        return git('merge-base', '--is-ancestor', a, b).returncode == 0
    try:
        if not all(revision(candidate[k]) for k in ('commit', 'base')):
            return 'unknown'
        tree = git('rev-parse', candidate['commit'] + '^{tree}')
        if tree.returncode or tree.stdout.strip() != candidate['tree']:
            return 'unknown'
        if not ancestor(candidate['base'], candidate['commit']):
            return 'unknown'
        if any(not revision(v) or not ancestor(v, candidate['commit'])
               for v in candidate['prerequisites'].values()):
            return 'unknown'
        before, after = integration.get('before'), integration.get('after')
        if not revision(before) or not revision(after):
            return 'unknown'
        main = git('rev-parse', '--verify', 'refs/heads/main^{commit}')
        if main.returncode or not ancestor(after, main.stdout.strip()):
            return 'unknown'
        if not ancestor(candidate['commit'], after) or not ancestor(before, after):
            return 'unknown'
        if local_policy is not None:
            # The original integration must introduce only the reviewed candidate
            # tree, by fast-forward or exact two-parent merge. Historical readback
            # checks that event, not the tree of later unrelated main commits.
            original = integration['candidate']
            if (not local_review(original, integration, local_policy)
                    or not candidate_identity.check(original, repo)
                    or integration.get('action') != 'merge'
                    or before == after
                    or ancestor(candidate['commit'], before)
                    or (not historical and main.stdout.strip() != after)):
                return 'unknown'
            after_tree = git('rev-parse', str(after) + '^{tree}')
            parents = git('show', '-s', '--format=%P', after)
            if (after_tree.returncode or parents.returncode or (after != candidate['commit']
                    and parents.stdout.split() != [before, candidate['commit']])):
                return 'unknown'
            if before == candidate['base']:
                if after_tree.stdout.strip() != candidate['tree']:
                    return 'unknown'
            else:
                # Recompute a conflict-free merge in a private object store.
                # Matching the entire tree preserves both reviewed and newer-main
                # changes. Never accept a caller's conflict resolution.
                if ('closeout' not in local_policy or after == candidate['commit']
                        or not ancestor(candidate['base'], before)
                        or not changed_base_checks(original, integration, local_policy, repo)):
                    return 'unknown'
                if not preserved_delta(repo, candidate['base'], candidate['commit'], before,
                                       after_tree.stdout.strip()):
                    return 'unknown'
            return 'historically locally integrated' if historical else 'locally integrated'
        if integration.get('action') == 'synchronize' and before == after:
            return 'already synchronized'
        provenance = integration.get('provenance', {})
        if (integration.get('action') != 'merge' or before == after
                or ancestor(candidate['commit'], before) or not isinstance(provenance, dict)
                or provenance.get('source') != 'protected_pr'
                or not isinstance(provenance.get('id'), str) or not provenance['id'].strip()
                or provenance.get('observed') is not True or provenance.get('protected') is not True
                or provenance.get('required_checks') != 'passed'
                or provenance.get('head') != candidate['commit']
                or provenance.get('merge_commit') != after):
            return 'unknown'
        return 'merged'
    except (OSError, UnicodeError, subprocess.TimeoutExpired):
        return 'unknown'


def preserved_delta(repo, base, commit, before, expected_tree):
    """Recompute the clean merge without writing repository objects/refs/index.

    Disable custom merge drivers: reading evidence must never execute repository
    commands. Conflicts refuse; caller-supplied resolutions cannot pass by checks.
    Git without the required merge-tree capability fails closed.
    """
    environment = candidate_identity.git_environment()
    def execute(*args, env=environment):
        return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(repo), *args],
                              capture_output=True, timeout=10, env=env)
    drivers = execute('config', '--name-only', '--get-regexp', r'^merge\..*\.driver$')
    objects = execute('rev-parse', '--git-path', 'objects')
    if drivers.returncode not in (0, 1) or objects.returncode:
        return False
    object_path = (Path(repo) / os.fsdecode(objects.stdout.strip())).resolve()
    with tempfile.TemporaryDirectory(prefix='closeout-delta-') as directory:
        private = Path(directory)
        (private / 'objects').mkdir()
        env = dict(environment, GIT_INDEX_FILE=str(private / 'index'),
                   GIT_OBJECT_DIRECTORY=str(private / 'objects'),
                   GIT_ALTERNATE_OBJECT_DIRECTORIES=str(object_path))
        options = ['-c', 'merge.default=text', '-c', 'merge.renormalize=false',
                   '-c', 'merge.renames=true']
        for driver in drivers.stdout.decode().splitlines():
            options.extend(['-c', driver + '=false'])
        tree = execute(*options, 'merge-tree', '--write-tree', '--no-messages',
                       '--merge-base=' + base, before, commit, env=env)
        return tree.returncode == 0 and tree.stdout.decode().strip() == expected_tree


def candidate_fields(value):
    """Read both explicit identities and candidate_identity.capture's v1 format."""
    if not isinstance(value, dict):
        return {}
    if 'version' not in value:
        return value
    rows = value.get('prerequisites')
    if (value.get('version') != 1 or not isinstance(value.get('workspace'), str)
            or not value['workspace'] or not isinstance(value.get('candidate_ref'), str)
            or not value['candidate_ref'] or not isinstance(rows, list)
            or any(not isinstance(r, dict) or not isinstance(r.get('ref'), str)
                   or not r['ref'] for r in rows)):
        return {}
    pins = {r['ref']: r.get('commit') for r in rows}
    if len(pins) != len(rows):
        return {}
    return {'commit': value.get('candidate_commit'), 'tree': value.get('candidate_tree'),
            'base': value.get('base_commit'), 'prerequisites': pins}


def valid_candidate(value):
    value = candidate_fields(value)
    def sha(s):
        return isinstance(s, str) and re.fullmatch(r'[0-9a-f]{40}', s) is not None
    return (all(sha(value.get(k)) for k in ('commit', 'tree', 'base'))
            and isinstance(value.get('prerequisites'), dict)
            and all(isinstance(k, str) and k and sha(v)
                    for k, v in value['prerequisites'].items()))


def evaluate(evidence, repo=None, local_policy=None, *, historical=False):
    evidence = evidence if isinstance(evidence, dict) else {}
    candidate = evidence.get('candidate')
    implementation = evidence.get('implementation', {})
    artifacts = implementation.get('artifacts') if isinstance(implementation, dict) else None
    implemented = (repo is not None and valid_candidate(candidate)
                   and candidate_identity.check(candidate, repo) and isinstance(artifacts, list)
                   and bool(artifacts) and all(isinstance(x, str) and x for x in artifacts))
    qualification = evidence.get('qualification', {})
    qualification = qualification if isinstance(qualification, dict) else {}
    checks = qualification.get('checks')
    validated = ([qualification_check(c, candidate, repo) for c in checks]
                 if isinstance(checks, list) and checks else [])
    required = qualification.get('required_checks')
    names = [c['name'] for c in validated if c is not None]
    complete = (isinstance(required, list) and bool(required)
                and all(isinstance(name, str) and name.strip() for name in required)
                and len(set(required)) == len(required)
                and len(set(names)) == len(names) and set(required).issubset(names))
    qualified = (implemented and qualification.get('candidate') == candidate
                 and complete and bool(validated) and all(c is not None and
                     (evidence.get('required_mode') is None or c['mode'] == evidence['required_mode'])
                     for c in validated))
    scope = sorted({f"{c['name']}: {c['platform']}/{c['backend']} ({c['mode']})"
                    for c in validated if c is not None}) if qualified else []
    progress = ('Qualified: ' + ', '.join(scope) + '; delivery unknown' if qualified else
                'Implemented; qualification unknown; delivery unknown' if implemented else
                'Implementation unknown; qualification unknown; delivery unknown')
    if (isinstance(local_policy, dict) and 'closeout' in local_policy
            and (not isinstance(local_policy['closeout'], dict)
                 or local_policy['closeout'].get('delivery_evidence') != evidence)):
        local_policy = {}  # Explicit contradictory closeout never falls back.
    integration = integration_state(candidate, evidence.get('integration'), repo, local_policy,
                                    historical=historical)
    delivered = qualified and integration in {'merged', 'locally integrated', 'historically locally integrated'}
    if delivered:
        lane = ('historical reviewed local main integration' if integration == 'historically locally integrated'
                else 'reviewed local main integration' if integration == 'locally integrated' else 'merged main')
        progress = 'Delivered: ' + lane + '; qualified ' + ', '.join(scope)
    elif integration == 'already synchronized':
        progress = progress.replace('delivery unknown', 'already synchronized; delivery unknown')
    return {'state': 'delivered' if delivered else 'qualified' if qualified else 'implemented' if implemented else 'unknown',
            'candidate': candidate if valid_candidate(candidate) else None,
            'implemented': implemented, 'qualified': qualified, 'delivered': delivered,
            'milestone_complete': False, 'publication': 'unknown', 'qualification_scope': scope,
            'integration': integration, 'integration_evaluation': 'historical' if historical else 'current_target',
            'progress': progress}
