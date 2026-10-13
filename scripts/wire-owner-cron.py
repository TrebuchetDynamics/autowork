#!/usr/bin/env python3
"""Wire existing owner jobs to the shared recovery cycle; default is inventory only."""
import argparse
import json
import os
from pathlib import Path
import subprocess

MARKER = '\n\nSHARED OWNER RECOVERY CYCLE — required execution\n'
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


def audit_prompt(prompt):
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
