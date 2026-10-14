#!/usr/bin/env python3
"""Wire existing owner jobs to the shared recovery cycle; default is inventory only."""
import argparse
import json
import os
from pathlib import Path
import subprocess

MARKER = '\n\nSHARED OWNER RECOVERY CYCLE — required execution\n'
REPAIR_MARKER = '\n\nSHARED TOOLSET REMEDIATION — authorized execution\n'
PAUSE_MARKER = '\n\nAUDIT AUTO-PAUSE — authorized owner schedules only\n'
AUDIT_MARKER = '\n\nOWNER RECOVERY COVERAGE — read-only\n'
PRESERVE = ('id', 'name', 'schedule', 'schedule_display', 'repeat', 'enabled', 'state',
            'paused_at', 'paused_reason', 'model', 'provider', 'base_url', 'deliver',
            'failure_deliver', 'origin', 'context_from', 'workdir', 'script', 'interpreter',
            'no_agent', 'skills', 'skill', 'enabled_toolsets', 'monitor_script',
            'monitor_url', 'monitor_state')


def jobs(home):
    path = home / 'cron/jobs.json'
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    rows = data['jobs'] if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise ValueError('invalid jobs list')
    return rows


def inventory(root):
    if root.parent.name == 'profiles' or (root / 'profiles').is_symlink():
        raise ValueError('use the default root with independent profile homes')
    homes = [('default', root)]
    for home in sorted((root / 'profiles').glob('*')):
        if home.name.startswith('.') or (root / 'profiles/.deleted' / home.name).exists():
            continue
        if home.is_symlink():
            raise ValueError('refuse symlinked profile home')
        if home.is_dir() and (home / 'config.yaml').is_file():
            homes.append((home.name, home))
    return [{'profile': name, 'home': str(home), 'jobs': jobs(home)} for name, home in homes]


def is_owner_job(job):
    skills = job.get('skills') or []
    return any(name in job.get('name', '').lower()
               or f'hermes-toolset:{name}' in skills or name in skills
               for name in ('autowork', 'autogoal'))


def autowork_skills(job):
    skills = job.get('skills') or ([job['skill']] if job.get('skill') else [])
    return ['hermes-toolset:autowork'] + [name for name in skills if name not in
            ('autogoal', 'hermes-toolset:autogoal', 'autowork', 'hermes-toolset:autowork')]


def owner_prompt(prompt, enabled):
    original = prompt.split(MARKER, 1)[0]
    return original + MARKER + (
        'Load hermes-toolset:autowork and references/owner-cycle.md for autonomous local coordination. '
        'Develop this repository within its established purpose and the scope above. '
        'Handle planning, implementation, testing, review and local integration yourself. '
        'This scheduled invocation is execution, not a planning-only request: consume existing source-bound plans within the standing authorization and continue eligible implementation in the same occurrence. '
        'A separate explicit plan request remains planning-only; it neither grants new implementation authority nor revokes this independently authorized job. Honor explicit no-write, pause and scope restrictions. '
        'Do not ask whether to implement already authorized offline work; ask only for a genuinely missing material decision or external-action authority. '
        'No external owner acknowledgement is required. Use default worker mode and supported native helpers where needed. '
        'Reconcile actual running workers and completed results first; preserve original cards, budgets and useful candidates. '
        'New workers receive 100 turns by default: omit --goal-max-turns so start_goal.py supplies the default Goal budget rationale; retain an explicit --goal-max-turns 50 override when bounded work calls for it. '
        'Preserve existing-card limits, cumulative usage and worker sessions; use --max-retries 1 for new cards and never automatically retry or reset an exhausted or interrupted worker. '
        'Use reconcile.py --compact and its saved continuation; read full evidence only for the next required decision. '
        'After two unchanged blocked observations, change the supported recovery approach or select independent authorized work; never repeat an identical failed command. '
        'Keep Hermes Agent unchanged. Never export worker identity or treat a saved handoff as authenticated runtime authority. '
        'Reconcile newly approved exact candidates, verify the integration gate and serialize permitted local integration before selecting another slice. A prior review-pending report is continuity, not current review state. '
        'Report reviewed offline slices separately from full TODO acceptance; keep unproved live acceptance open and report partial progress without inventing whole-task completion. '
        'Scope one coherent delivery batch around the remaining accepted outcome, not one card per file. '
        'Group connected eligible consumers, runners and tests; split only for concrete dependency, writer, authority or budget boundaries. '
        'Reuse approved exact-source checks when inputs match and policy allows; run changed-input and required canonical checks. '
        'For partial deliveries, lead with delivered behavior and commit stage; explain why the parent task remains open separately. '
        'Select a useful, dependency-ready TODO task. If unavailable, inspect independent bugs, documentation, UI/UX, tests, refactoring and reliability or performance work. '
        'When the backlog lacks useful tasks, load references/repository-maintenance.md, inspect a bounded source/test seam, document a justified task and execute it in the same occurrence. '
        'Use owner_cycle.py in its default autonomous mode for recovery; pass --scope repository for repository work and --scope tasks only for explicit task-only requests. '
        'Preserve unrelated changes, inspect actual live writers and file conflicts, and avoid overlapping work. Historical claims alone are not approval gates. '
        'Respect repository branch policy, native admission and genuinely missing user decisions or external-action authority. '
        'Verify changes, review them, integrate authorized owned changes locally and commit completed work using explicit paths. Do not push or deploy. '
        'Do not count planning, audits, task creation or queued workers as implementation completion. '
        'Never create another schedule, change cadence/model/delivery or resume this job yourself. '
        'While paused, do not trigger recovery or start a substitute writer; a separately authorized native resume enables future occurrences under this workflow. '
        'Return a concise nonempty profile-labeled report every occurrence through automatic cron delivery, not a messaging tool: '
        'Completed: task ID and title, or none. Changed: concrete result. Checks: actual passes/failures or none. '
        'Commit: verified local SHA, or none. Next: task ID and intended action. Blocker: exact missing input and recovery attempted. '
        'End with skipped checks and risks.\n')


def audit_prompt(prompt, *, repair=False, pause_stalled=False):
    pause_stalled = pause_stalled or PAUSE_MARKER in prompt
    result = _audit_prompt(prompt.split(PAUSE_MARKER, 1)[0], repair=repair)
    if not pause_stalled:
        return result
    result = result.replace('owner jobs/config/memories', 'owner config/memories')
    result = result.replace('sibling config/job/memory changes', 'sibling config/memory changes')
    result = result.replace('change jobs, or replace workers', 'replace workers')
    return result + PAUSE_MARKER + (
        'The user authorizes pausing existing development Autowork cron jobs for configured subjects ONLY. '
        'Never pause the default maintainer, excluded profiles, unrelated jobs or a missing/ambiguous target. '
        'Match profile, repository and exact existing job ID before action. Preserve already paused jobs. '
        'Pause after THREE distinct consecutive completed occurrences are blocked/failed with the same '
        'primary task/blocker and no verified implementation, useful candidate change, acceptance, review '
        'or integration progress since the latest real progress or relevant repair. '
        'Use exact run/output IDs and fingerprints; repeated polls are one occurrence. '
        'A new helper repair or a changed recovery input requires fresh owner observations; '
        'do not count pre-repair failures against the corrected path. '
        'Also pause on verified no tasks left: read canonical TODO/goals and saved continuations; '
        'require the owning agent repository-maintenance/docs-sync work search and its checked scope exhausted receipt. '
        'An empty board, an empty selector, all work dependency-held or no eligible task is not no tasks left. '
        'Do not manufacture busywork to keep a schedule enabled. Missing evidence is unknown, not exhaustion. '
        'Recheck actual worker and manual-continuation liveness immediately before pausing; '
        'do not classify an actually progressing worker as stalled. Preserve cards, budgets, candidates and history; '
        'never cancel a worker, trigger a run, reset retries or launch a replacement. '
        'Use the supported command hermes -p PROFILE cron pause JOB_ID; read back enabled=false '
        'on that exact job and unchanged cadence/model/delivery, and save before/after plus reason '
        'and supporting run IDs in default-owned maintenance evidence. Report every pause via existing Telegram delivery. '
        'Keep auditing paused subjects; never resume automatically. A resume requires explicit user instruction. '
        'This is the only sibling-job write exception; product/config/memory/live-service writes remain forbidden.\n')


def _audit_prompt(prompt, *, repair=False):
    if repair or REPAIR_MARKER in prompt:
        original = prompt.split(REPAIR_MARKER, 1)[0].split(AUDIT_MARKER, 1)[0]
        return original + REPAIR_MARKER + (
            'This occurrence performs shared-source repair, not proposals-only auditing. '
            'Read the collector receipt and the newest TWO completed owner responses; '
            'verify exact original cards/runs, installed helper paths and current source before diagnosing. '
            'Find the earliest failed transition, prioritizing a repeated owner hold over broad log narration. '
            'Compare that same primary blocker across the two completed owner responses and the current consumer receipt. '
            'When it remains unchanged, lead the report with PRIMARY RECOVERY BLOCKED, its original card/run, '
            'first observed receipt/time when available, consecutive observed holds and the exact missing supported operation. '
            'Do not invent elapsed time or a count when historical evidence is missing. '
            'Ask each configured subject once through scripts/profile-consult.py with its explicit --profiles set; '
            'retain actual replies or transport failures and default self-assessment without recursion. '
            'Reproduce one evidenced shared-toolset defect with a regression RED; make the smallest source fix, '
            'run focused checks, then retry the same read-only consumer and retain before/after receipts. '
            'Inspect callers and other writers; preserve foreign changes and avoid duplicate repair work. '
            'Qualify only attributable source/dependency closure, not a dirty union. '
            'Deploy reviewed bundled helper changes only through supported, owner-preserving paths within the granted scope; '
            'read back actual installed bytes and report refused deployment separately. '
            'Read active card commands as well as installed profile paths: an absolute shared-source helper path '
            'can change during source integration even when profile deployment is deferred. Report that exposure; '
            'never claim the active helper runtime was preserved from a deferred copy alone. '
            'Commit only verified owned source paths locally when attribution is established. Do not push. '
            'Respect each owner current authority and exclusions; the auditor never borrows owner live/DB/S3 authority. '
            'No product writes, sibling config/job/memory changes, worker launch, lease takeover, Agent edits or guard bypass. '
            'Do not reset budgets, retry counters, original cards, candidate pins or history; '
            'native admission remains separate from registration and metadata readiness. '
            'Preserve paused jobs; do not trigger schedules or replace blocked workers. '
            'An owner waiting for a released compatible helper is a maintainer action, not another user permission question. '
            'On an unavailable native operation, scope the hold to that operation and inspect one disjoint authorized source fix; '
            'a disjoint hardening fix does not reset primary-blocker history or count as recovery progress. '
            'After repeated unchanged holds, name a different supported recovery step and its responsible role, '
            'or the precise unavailable capability/input; do not prescribe the same failed replay as the next action. '
            'never repeat an unchanged proposal or failed command without changed evidence. '
            'One collector, one bounded consultation wave and one repair batch per tick; honor existing overlap locks, '
            'no catch-up runs or automatic budget extensions. '
            'Report every subject via existing automatic delivery: current task/stage, concrete fix/checks, '
            'deployed or prepared status, same-consumer result, exact remaining gate and next owner action. '
            'Successful cron delivery or fixtures alone never proves product recovery. End with skipped checks and risk.\n')
    original = prompt.split(AUDIT_MARKER, 1)[0]
    return original + AUDIT_MARKER + (
        'Load skills/autowork/references/owner-cycle.md. Read each owning profile\'s '
        'autowork/unblock-latest.json when present and verify its task/plan/revision, '
        'attempted repair, same-cycle retry and actual admission/implementation separately. '
        'Report every requested profile, including paused jobs and missing evidence; '
        'link compact default-owned receipts instead of repeating raw logs. '
        'Treat historical owner names/claims as attribution, not acknowledgement gates. '
        'Missing execution receipts mean recovery unverified, not no work or fleet health. '
        'Do not perform product --apply, write sibling state, change jobs, or replace workers. '
        'Identify shared helper defects from the actual failed transition; owner consultations '
        'and successful cron delivery are not recovered tasks. Keep all paused jobs paused.\n')


def verify_edit(before, after, prompt):
    if after.get('prompt') != prompt:
        raise ValueError('prompt readback mismatch')
    def policy(value):
        return {key: item for key, item in value.items() if key != 'completed'} if isinstance(value, dict) else value
    # A scheduler completion may race the edit; its counter is not repeat configuration.
    changed = [key for key in PRESERVE if
               (policy(before.get(key)) != policy(after.get(key)) if key == 'repeat'
                else before.get(key) != after.get(key))]
    if changed:
        raise ValueError('unrelated job fields changed: ' + ','.join(changed))


def wire(root, apply=False, hermes='hermes'):
    results = []
    for row in inventory(root):
        name, home = row['profile'], Path(row['home'])
        targets = [job for job in row['jobs'] if is_owner_job(job) or
                   (name == 'default' and job.get('name') == 'Profile audit and hermes-toolset maintenance')]
        if not targets:
            results.append({'profile': name, 'state': 'no_matching_job', 'changed': False})
        for before in targets:
            audit = name == 'default' and before.get('name') == 'Profile audit and hermes-toolset maintenance'
            prompt = (audit_prompt(before['prompt']) if audit
                      else owner_prompt(before['prompt'], before['enabled']))
            skills = autowork_skills(before)
            expected = {**before, 'skills': skills, 'skill': skills[0]}
            state = 'unchanged' if prompt == before['prompt'] and all(
                before.get(key) == expected[key] for key in ('skills', 'skill')) else 'would_update'
            if apply and state == 'would_update':
                current = next(job for job in jobs(home) if job['id'] == before['id'])
                verify_edit(before, current, before['prompt'])
                argv = [hermes, '-p', name]
                env = dict(os.environ, HERMES_HOME=str(root))
                env.pop('HERMES_PROFILE', None)
                command = argv + ['cron', 'edit', before['id'], '--prompt', prompt]
                for skill in skills:
                    command += ['--skill', skill]
                subprocess.run(command, check=True, text=True, capture_output=True, timeout=60, env=env)
                after = next(job for job in jobs(home) if job['id'] == before['id'])
                verify_edit(expected, after, prompt)
                state = 'updated_verified'
            results.append({'profile': name, 'job_id': before['id'], 'state': state,
                            'enabled': before['enabled'], 'changed': state == 'updated_verified'})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    print(json.dumps(wire(args.root.resolve(), args.apply), indent=2))


if __name__ == '__main__':
    main()
