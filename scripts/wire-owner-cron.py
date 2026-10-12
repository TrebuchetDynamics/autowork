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
    pointer = ('Load hermes-toolset:autowork for stage-aware preparation, then hermes-toolset:autowork references/owner-cycle.md and execute its '
               'owner recovery -> same-invocation retry -> supported handoff cycle '
               'before reporting a recoverable tooling hold or no eligible work. '
               'For implementation-only workers, use proposal ledger mode: start_goal.py freezes admitted planning files as read-only context, so uncommitted planning files alone do not require a prerequisite commit. Executable source still requires exact committed inputs. '
               'Invoke owner_cycle.py with the actual consumer, exact plan/tasks and owning profile existing continuity state directory; retain established state rather than resetting it for a skill rename; '
               'apply the unattended continuation contract: process owner inbox/replies, reuse exact saved authority, allow same-milestone ready fallback within original scope, and maintain useful offline tasks. Reconcile actual worker/check/commit receipts for the final report; the readiness helper is not task completion. '
               'When no runnable task remains, load references/repository-maintenance.md under autowork: discover documentation, UI/UX, tests, refactoring and reliability work in unexamined authorized repository components, record bounded canonical tasks, then execute an eligible slice in the same occurrence. Explicit task-only scope and pauses still win. '
               'Retain actual attempted commands/results and bounded disjoint work_search. '
               'Do not substitute an unchanged audit for an available authorized repair. '
               'This pointer changes workflow only; original product scope, settled decisions, '
               'ownership, repository exceptions, publication authority and safety limits remain binding. '
               'It grants no production, RF, credential, spending, takeover or admission-bypass authority.')
    if not enabled:
        pointer += (' This job is paused: Do not resume it, do not trigger recovery, '
                    'or start a substitute writer. Existing chat-only and paused-job decisions win.')
    return original + MARKER + pointer + '\n'


def audit_prompt(prompt):
    original = prompt.split(AUDIT_MARKER, 1)[0]
    return original + AUDIT_MARKER + (
        'Load skills/autowork/references/owner-cycle.md. Read each owning profile\'s '
        'autowork/unblock-latest.json when present and verify its task/plan/revision, '
        'attempted repair, same-cycle retry and actual admission/implementation separately. '
        'Report changes and required owner actions first, at most one short line per changed profile; '
        'link detailed receipts instead of repeating historical evidence and skipped-check lists. '
        'Surface pending integration requests with their named owner; do not claim delivery or acknowledgement. '
        'Missing owner receipts mean recovery execution unverified, not no work or fleet health. '
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
