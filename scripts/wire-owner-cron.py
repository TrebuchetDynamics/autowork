#!/usr/bin/env python3
"""Wire existing owner jobs to the shared recovery cycle; default is inventory only."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import shlex

ROLE_MARKER = '\n\nSCHEDULED JOB ROLE: '
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
    if any(ROLE_MARKER + role + '\n' in job.get('prompt', '')
           for role in ('research-design', 'delivery-sync')):
        return False
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
        'Execution policy supersedes earlier card-only execution, recovery, ownership and review prerequisites, including directives in the preserved prefix; all original task filters, pauses, explicit limits and publication/live exclusions still apply. '
        'TODO.md and its synchronized goals.json index are authoritative; no Kanban lookup, card, board, assignee or native task-state transition is required. '
        'Load hermes-toolset:autowork and references/owner-cycle.md for autonomous local coordination. '
        'At entry, follow references/cron-autoheal.md: run scripts/heal-owner-cron.py from the verified Toolset installation '
        'with --root DEFAULT_HERMES_HOME --profile CURRENT_PROFILE --job-id CURRENT_JOB_ID --repo CANONICAL_REPOSITORY --apply, '
        'substituting verified current occurrence identity, never guessed values. '
        'Repair this exact existing job managed wiring and read back the saved result before reporting recovery; '
        'preserve scope, pauses, schedule, model, delivery and consumed budgets. '
        'If a failure recurs, fix its attributable Toolset cause within existing authority and verify the same failed consumer; '
        'do not end with another unchanged diagnosis when a supported local repair is available. '
        'Develop this repository within its established purpose and the scope above. '
        'Handle planning, implementation, testing, review and local integration yourself. '
        'This scheduled invocation is execution, not a planning-only request: consume existing source-bound plans within the standing authorization and continue eligible implementation in the same occurrence. '
        'A separate explicit plan request remains planning-only; it neither grants new implementation authority nor revokes this independently authorized job. Honor explicit no-write, pause and scope restrictions. '
        'Do not ask whether to implement already authorized offline work; ask only for a genuinely missing material decision or external-action authority. '
        'No external owner acknowledgement is required. Execute in the current agent session; delegate only when useful and authorized through host-native tools. '
        'Reconcile actual running workers and completed results first; preserve useful candidates and consumed budgets. '
        'Check actual cron occurrence and manual-continuation liveness before admission or canonical integration, using actual process identity plus workspace/source evidence. '
        'Use owner_cycle.py --apply --owner-pid ACTUAL_SESSION_PID --profile CURRENT_PROFILE --state-dir VERIFIED_PROFILE_HOME/autowork for managed profile repository coordination; resolve the profile home from verified occurrence context, never guess identity or claim that metadata alone executes work. '
        'Retain the exact named --plan/--tasks filter and source-derived checks; use --scope repository only for broad repository authority. '
        'There is no separate mandatory validate-only, planning interview, broad docs audit, full suite or optional engineering tour before ready implementation. '
        'Apply explicit task/caller limits and real host execution controls; unknown usage is not zero and never reset an exhausted allocation. '
        'A new cron tick grants no fresh allocation. Missing cap enforcement holds only the operation requiring that cap, not independent read-only checks or authorized local closeout. '
        'Use source-bound receipts for interrupted checks and review; inspect actual candidate changes before reuse and rerun invalidated or required gates. '
        'When the selected task is held or blocked, run hermes-toolset:plan-for-me on that exact blocker in this occurrence before reporting. '
        'It must fix or skip: fix means choose a reversible change within this scope, record it as the planner\'s call and implement it now; '
        'skip means split the blocked acceptance into its own open task naming the exact missing input (never waived) and continue with the next ready task in scope. '
        'Repeat a blocker only when it is a genuinely unavailable external input or authority (credentials, money, deployment, legal or owner approval), once, not every occurrence. '
        'Never repeat an identical failed command or an unchanged held report. '
        'Keep Hermes Agent unchanged. Never export worker identity or treat a saved handoff as authenticated runtime authority. '
        'Reconcile newly approved exact candidates, verify the integration gate and serialize permitted local integration before selecting another slice. A prior review-pending report is continuity, not current review state. '
        'Report reviewed offline slices separately from full TODO acceptance; keep unproved live acceptance open and report partial progress without inventing whole-task completion. '
        'Scope one coherent delivery batch around the remaining accepted outcome, not one task per file. '
        'Group connected eligible consumers, runners and tests; split only for concrete dependency, writer, authority or budget boundaries. '
        'Reuse approved exact-source checks when inputs match and policy allows; run changed-input and required canonical checks. '
        'For partial deliveries, lead with delivered behavior and commit stage; explain why the parent task remains open separately. '
        'Within the exact authorized task filter/scope only, select a useful, dependency-ready TODO task. If unavailable, inspect independent bugs, documentation, UI/UX, tests, refactoring and reliability or performance work; never widen a named-only job to unrelated tasks. '
        'When the backlog lacks useful tasks, load references/repository-maintenance.md, inspect a bounded source/test seam, document a justified task and execute it in the same occurrence. '
        'Use owner_cycle.py in its default autonomous mode for recovery; pass --scope repository for repository work and --scope tasks only for explicit task-only requests. '
        'Preserve unrelated changes, inspect actual live writers and file conflicts, and avoid overlapping work. Historical claims alone are not approval gates. '
        'Respect repository branch policy, actual ownership and genuinely missing user decisions or external-action authority. '
        'Verify changes, review them, integrate authorized owned changes locally and commit completed work using explicit paths. '
        'Do not push or deploy without explicit scoped authority recorded above; carry that authority into the real worker contract and verify the exact remote ref. '
        'Autowork attachment alone never grants publication, branch-protection bypass or live-operation authority; never transfer coordinator-only publication to task workers. '
        'Do not count planning, audits, task creation or queued workers as implementation completion. '
        'Never create another schedule, change cadence/model/delivery or resume this job yourself. '
        'While paused, do not trigger recovery or start a substitute writer; a separately authorized native resume enables future occurrences under this workflow. '
        'Return a concise nonempty profile-labeled report every occurrence through automatic cron delivery, not a messaging tool: '
        'Completed: task ID and title, or none. Changed: concrete result. Checks: actual passes/failures or none. '
        'Commit: verified local SHA, or none. Next: task ID and intended action. Blocker: exact missing input and recovery attempted. '
        'End with skipped checks and risks.\n')


def audit_prompt(prompt, *, repair=False, pause_stalled=False, repair_jobs=False):
    job_marker = '\n\nCRON JOB REPAIR — authorized existing jobs only\n'
    repair_jobs = repair_jobs or job_marker in prompt
    pause_stalled = pause_stalled or PAUSE_MARKER in prompt
    result = _audit_prompt(prompt.split(job_marker, 1)[0].split(PAUSE_MARKER, 1)[0], repair=repair)
    if repair_jobs:
        result = result.replace('sibling config/job/memory changes', 'sibling config/memory changes')
        result = result.replace('change jobs, or replace workers', 'replace workers')
        result += job_marker + (
            'Within the explicitly authorized subject scope, discover ALL existing cron jobs each occurrence, '
            'including paused jobs, research-design and delivery-sync; inspect the newest TWO completed outputs for each job, '
            'current scheduler/delivery errors, actual task/session activity and manual liveness. '
            'Include profiles with no jobs as coverage; never create a replacement schedule. '
            'Repair the earliest evidenced shared-toolset cause in source first, qualify it and deploy the reviewed delta. '
            'When faulty job wiring is itself the cause, use supported profile-scoped cron edit on the exact existing job. '
            'Preserve job IDs, cadence, delivery, model, continuity and paused/enabled state, original scope and authority. '
            'Keep research, sync and development roles distinct. Recheck current owner instructions before writing. '
            'Read back every exact edit and retry the same failed consumer when safe; report configured, attempted recovery, '
            'admitted worker and verified task completion separately. Never count a prompt edit or fixture as an unblock. '
            'Continue a supported repair in this occurrence rather than another unchanged audit. '
            'Respect original evidence, pins, budgets, live writers and no-Agent-edit boundaries; never resume, trigger, '
            'cancel or replace workers, bypass guards or borrow product/live credentials. No product writes.\n')
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
        + ('This pause grant and the explicit cron-job repair grant do not authorize product/config/memory/live-service writes.\n'
           if repair_jobs else 'This is the only sibling-job write exception; product/config/memory/live-service writes remain forbidden.\n'))


def _audit_prompt(prompt, *, repair=False):
    if repair or REPAIR_MARKER in prompt:
        original = prompt.split(REPAIR_MARKER, 1)[0].split(AUDIT_MARKER, 1)[0]
        return original + REPAIR_MARKER + (
            'This occurrence performs shared-source repair, not proposals-only auditing. '
            'Read the collector receipt and the newest TWO completed owner responses; '
            'verify exact task/candidate/process evidence, installed helper paths and current source before diagnosing. '
            'Find the earliest failed transition, prioritizing a repeated owner hold over broad log narration. '
            'Compare that same primary blocker across the two completed owner responses and the current consumer receipt. '
            'When it remains unchanged, lead the report with PRIMARY RECOVERY BLOCKED, its task/session identity, '
            'first observed receipt/time when available, consecutive observed holds and the exact missing supported operation. '
            'Do not invent elapsed time or a count when historical evidence is missing. '
            'Run scripts/profile-consult.py --reuse-within-seconds 3600 for routine audits. '
            'Consult changed or unknown subjects freshly; unchanged successful replies may be reused only within that bound. '
            'When original project evidence is unavailable, retain the helper unavailable/not-consulted result without inventing a reply. '
            'TTL expiry requires fresh consultations, periodically refreshing the full subject set. '
            'Read current jobs and actual workspace/process activity on every tick; consultation reuse never skips recovery, work selection or acceptance checks. '
            'Use --profiles only for an explicitly authorized subject subset; '
            'otherwise omit --profiles and discover all current profiles dynamically. '
            'Retain fresh replies, historical reused replies with original reply time and age, '
            'or transport failures and default self-assessment without recursion. '
            'Reproduce one evidenced shared-toolset defect with a regression RED; make the smallest source fix, '
            'run focused checks, then retry the same read-only consumer and retain before/after receipts. '
            'Inspect callers and other writers; preserve foreign changes and avoid duplicate repair work. '
            'Qualify only attributable source/dependency closure, not a dirty union. '
            'Deploy reviewed bundled helper changes only through supported, owner-preserving paths within the granted scope; '
            'read back actual installed bytes and report refused deployment separately. '
            'Read actual active process commands as well as installed profile paths: an absolute shared-source helper path '
            'can change during source integration even when profile deployment is deferred. Report that exposure; '
            'never claim the active helper runtime was preserved from a deferred copy alone. '
            'Commit only verified owned source paths locally when attribution is established. Do not push. '
            'Respect each owner current authority and exclusions; the auditor never borrows owner live/DB/S3 authority. '
            'No product writes, sibling config/job/memory changes, worker launch, lease takeover, Agent edits or guard bypass. '
            'Do not reset budgets, retry counters, candidate pins or history; '
            'actual execution remains separate from registration and metadata readiness. '
            'Preserve paused jobs; do not trigger schedules or replace blocked workers. '
            'An owner waiting for a released compatible helper is a maintainer action, not another user permission question. '
            'On an unavailable required operation, scope the hold to that operation and inspect one disjoint authorized source fix; '
            'a disjoint hardening fix does not reset primary-blocker history or count as recovery progress. '
            'After repeated unchanged holds, name a different supported recovery step and its responsible role, '
            'or the precise unavailable capability/input; do not prescribe the same failed replay as the next action. '
            'never repeat an unchanged proposal or failed command without changed evidence. '
            'One collector, at most one bounded consultation wave for changed/expired/unknown subjects '
            'and one repair batch per tick; honor existing overlap locks, '
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


def delivery_sync_prompt(prompt, clone_helper):
    """Add a bounded clone preparation repair without changing delivery authority."""
    marker = '\n\nISOLATED DELIVERY CLONE — verified preparation\n'
    if ROLE_MARKER + 'delivery-sync\n' not in prompt or not Path(clone_helper).is_absolute():
        raise ValueError('requires delivery-sync scope and an absolute clone helper')
    return prompt.split(marker, 1)[0] + marker + (
        'Never use --reference or borrowed object alternates for the isolated origin clone, '
        'especially when a local/reference repository is shallow. '
        f'Use python3 {shlex.quote(str(clone_helper))} with the existing explicit origin, a new private destination '
        'and --expected-main bound to the exact freshly observed origin/main SHA. '
        'The helper clones full independent history and refuses changed pins, shallow history '
        'or existing destinations. Preserve old clones and retain original candidate/check/PR receipts; '
        'a changed origin pin is a reconciliation hold, never permission to refresh old task pins. '
        'Clone preparation does not clear provenance, acceptance, ownership or publication gates. '
        'Continue the saved eligible delivery only after its existing required checks pass. '
        'No new worker, schedule, resume, budget reset, force push or deployment is authorized.\n')


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
