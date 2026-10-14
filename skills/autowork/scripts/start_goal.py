#!/usr/bin/env python3
"""Hand one selected autowork contract to Hermes' native goal-mode worker."""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import sqlite3
import shlex
import shutil
import uuid
from urllib.parse import quote
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

_runtime_spec = importlib.util.spec_from_file_location('worker_runtime_bundle', Path(__file__).with_name('runtime_bundle.py'))
runtime_bundle = importlib.util.module_from_spec(_runtime_spec)
_runtime_spec.loader.exec_module(runtime_bundle)

BUDGET = 100
ACTIVE = {'ready', 'running', 'todo', 'review', 'changes_requested'}
# Parked cards (triage after a terminal run, scheduled backoff) block only their own slice:
# a same-title handoff is refused, disjoint work proceeds. See SKILL.md 'Operating priorities'.
PARKED = {'triage', 'scheduled', 'blocked'}
# Native max_retries=1 trips on the first failure. Each new worker launch gets
# the full per-run goal allocation; automatic retries cannot preserve a total cap.
MAX_RETRIES = 1


CONTRACT_FIELDS = ('Objective', 'Scope', 'Verification', 'Source', 'Project payoff',
                   'Current evidence', 'Expected change', 'Acceptance', 'Stop conditions',
                   'Repo-docs pass')


def validate_contract(text, goal_max_turns=None):
    """Validate structure, not truth, priority, permissions or executable proof."""
    fields = {}
    current = None
    for line in text.splitlines():
        header = re.match(r'^\s*([A-Za-z][A-Za-z -]*):[ \t]*(.*)$', line)
        if header and header.group(1) in (*CONTRACT_FIELDS, 'Goal budget rationale'):
            current = header.group(1)
            if current in fields:
                raise ValueError(f'Duplicate contract field: {current}')
            fields[current] = header.group(2).strip()
        elif current is not None:
            fields[current] += '\n' + line
    for field in CONTRACT_FIELDS:
        if not fields.get(field, '').strip():
            raise ValueError(f'Missing or empty contract field: {field}')
    if goal_max_turns is None:
        goal_max_turns = BUDGET
        fields.setdefault('Goal budget rationale', 'Default allocation for one coherent implementation and recovery outcome.')
    if goal_max_turns == 100 and not fields.get('Goal budget rationale', '').strip():
        raise ValueError('100 turns requires a nonempty Goal budget rationale: in the contract')
    return {key: value.strip() for key, value in fields.items()}


def require_milestone_admission(workspace, goal_task=None, snapshot_file=None, fallback_file=None):
    """Use the ledger's dependency rules; admission is not completion evidence."""
    workspace = Path(workspace).expanduser().resolve(strict=True)
    ledger = workspace / 'goals.json'
    if not ledger.exists():
        if goal_task or fallback_file:
            raise ValueError('Explicit goal identity requires goals.json')
        return {'goal_task': None, 'milestone': None, 'fallback': None, 'ledger_sha256': None}
    ledger_bytes = ledger.read_bytes()
    data = json.loads(ledger_bytes)
    ledger_digest = hashlib.sha256(ledger_bytes).hexdigest()
    focus = data.get('primary_milestone')
    if not focus and not goal_task and not fallback_file:
        return {'goal_task': None, 'milestone': None, 'fallback': None,
                'ledger_sha256': ledger_digest}
    if not goal_task:
        raise ValueError('Primary milestone requires explicit --goal-task')
    if focus:
        require_fresh_sources(snapshot_file, workspace)
        snapshot = json.loads(Path(snapshot_file).read_text())
        if not any(row['path'] == 'goals.json' and row['sha256'] == ledger_digest for row in snapshot['files']):
            raise ValueError('Focused admission source evidence must include the fresh goal ledger')
    spec = importlib.util.spec_from_file_location('admission_goals',
        Path(__file__).resolve().parents[2] / 'docs-sync/scripts/goals.py')
    assert spec is not None and spec.loader is not None
    goals = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(goals)
    errors = goals.errors(data)
    if errors:
        raise ValueError('Invalid goal ledger: ' + '; '.join(errors))
    # A named goal task is an explicit request, so priority drift does not block it.
    eligible, _ = goals.queue(goals.normalize(data), goals.todo_text(workspace), allow_drift=True)
    selected = next((t for t, g in eligible if t['id'] == goal_task), None)
    if selected is None:
        raise ValueError('Goal task is not dependency-ready eligible: ' + goal_task)
    fallback = None
    if focus and selected['goal'] != focus:
        if not fallback_file:
            raise ValueError('Unrelated goal task requires complete structured fallback')
        require_fresh_sources(snapshot_file, workspace)
        snapshot = json.loads(Path(snapshot_file).read_text())
        if not any(row['path'] == 'goals.json' and row['sha256'] == ledger_digest for row in snapshot['files']):
            raise ValueError('Fallback source evidence must include the fresh goal ledger')
        fallback = json.loads(Path(fallback_file).read_text())
        bindings = {'version': 1, 'workspace': str(workspace), 'primary_milestone': focus,
                    'goal_task': goal_task, 'ledger_sha256': ledger_digest,
                    'source_snapshot_sha256': hashlib.sha256(Path(snapshot_file).read_bytes()).hexdigest()}
        if not isinstance(fallback, dict) or any(fallback.get(k) != v for k, v in bindings.items()):
            raise ValueError('Fallback does not match fresh ledger/workspace/source evidence')
        decision = fallback.get('reprioritization')
        if decision is not None:
            if ('reasons' in fallback or not isinstance(decision, dict)
                    or any(not isinstance(decision.get(k), str) or not decision[k].strip()
                           for k in ('actor', 'reason', 'evidence_ref'))):
                raise ValueError('Explicit reprioritization requires actor, reason and evidence_ref, not slice reasons')
        else:
            reasons = fallback.get('reasons')
            focused = {t['id'] for t, g in eligible if g['id'] == focus}
            if not isinstance(reasons, list) or any(not isinstance(row, dict) for row in reasons):
                raise ValueError('Fallback needs structured reasons for every eligible focused slice')
            ids = [row.get('task_id') for row in reasons]
            if any(not isinstance(i, str) or not i for i in ids) or len(ids) != len(set(ids)) or set(ids) != focused:
                raise ValueError('Fallback reasons must cover exactly every eligible focused slice')
            for row in reasons:
                if (row.get('kind') not in {'ownership', 'authority', 'environment'}
                        or any(not isinstance(row.get(k), str) or not row[k].strip() for k in ('reason', 'evidence_ref'))):
                    raise ValueError('Fallback reason needs ownership|authority|environment, reason and evidence_ref')
    # Catch focus/dependency edits made while the ledger was being evaluated.
    require_fresh_sources(snapshot_file, workspace)
    if hashlib.sha256(ledger.read_bytes()).hexdigest() != ledger_digest:
        raise ValueError('Goal ledger changed during admission; re-evaluate selection')
    return {'goal_task': goal_task, 'goal': selected['goal'], 'milestone': focus,
            'fallback': fallback, 'ledger_sha256': ledger_digest,
            'fallback_validation': 'caller_attestation_not_truth_verified' if fallback else None}


def require_fresh_sources(snapshot_file, workspace):
    if snapshot_file is None:
        raise ValueError('Source snapshot required for a new handoff; capture evidence before selection')
    spec=importlib.util.spec_from_file_location('autowork_freshness',Path(__file__).with_name('source_freshness.py'))
    freshness=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(freshness)
    result=freshness.check(json.loads(Path(snapshot_file).read_text()),workspace)
    if not result['fresh']:
        raise ValueError('Source changed since selection; re-evaluate unresolved work before dispatch: '+', '.join(result['changed']))
    return result


REVIEW_DOD = ('Definition of done for this card (goal judge): the contract below is implemented, its '
              'checks have run with evidence recorded, owned changes are committed (or an explicit no-commit '
              'instruction/no-change result is recorded), and the card is handed to native review. Review '
              'approval happens after that handoff and is NOT part of this goal: a pending review never makes '
              'this goal unfinished or unachievable.')


def validate_publication_authority(authority, workspace, profile, goal_task, contract):
    """Validate exact caller-supplied owner evidence, not independently prove permission."""
    required = {'version', 'workspace', 'profile', 'goal_task', 'contract_sha256',
                'remote', 'ref', 'owner', 'evidence_ref'}
    expected = {'version': 1, 'workspace': str(Path(workspace).resolve(strict=True)),
                'profile': profile, 'goal_task': goal_task,
                'contract_sha256': hashlib.sha256(contract.encode()).hexdigest()}
    if (not isinstance(authority, dict) or set(authority) != required or not goal_task
            or any(authority.get(key) != value for key, value in expected.items())):
        raise ValueError('publication authority must bind exact workspace/profile/task/contract')
    safe = lambda value: isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', value) is not None
    ref = authority['ref']
    if (not safe(profile) or not safe(goal_task) or not safe(authority['remote'])
            or ref != f'refs/heads/agent/{profile}/{goal_task}'
            or any('..' in token or token.endswith(('.', '.lock')) for token in (profile, goal_task))
            or any(not isinstance(authority[key], str) or not authority[key].strip()
                   for key in ('owner', 'evidence_ref'))):
        raise ValueError('publication permits one exact owned task ref and safe existing remote only')
    return dict(authority, authority_validation='caller_attestation_not_independent_authorization')


def build_task_body(contract, goal_max_turns=BUDGET, *, ledger_mode='worker',
                    integration_owner=None, publication_authority=None, helper_runtime=None):
    if ledger_mode not in ('worker', 'proposal'):
        raise ValueError('ledger mode must be worker or proposal')
    if ledger_mode == 'proposal' and (not isinstance(integration_owner, str) or
            re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', integration_owner) is None):
        raise ValueError('proposal ledger role requires explicit integration owner')
    if ledger_mode == 'worker' and integration_owner is not None:
        raise ValueError('integration owner requires proposal ledger mode')
    if publication_authority is not None:
        required = {'version', 'workspace', 'profile', 'goal_task', 'contract_sha256',
                    'remote', 'ref', 'owner', 'evidence_ref', 'authority_validation'}
        if (set(publication_authority) != required or
                publication_authority.get('authority_validation') != 'caller_attestation_not_independent_authorization'):
            raise ValueError('validated scoped publication authority required')
        raw = {key: value for key, value in publication_authority.items() if key != 'authority_validation'}
        validate_publication_authority(raw, raw['workspace'], raw['profile'], raw['goal_task'], contract)
        if ledger_mode != 'proposal' or integration_owner != raw['owner']:
            raise ValueError('scoped publication requires coherent proposal/integration-owner role')
    helper_root = Path(helper_runtime['root']) if helper_runtime else Path(__file__).resolve().parents[2]
    goals_command = (runtime_bundle.command(helper_runtime, 'docs-sync/scripts/goals.py') if helper_runtime else
                     shlex.join([sys.executable, str(helper_root / 'docs-sync/scripts/goals.py')]))
    finish_command = (runtime_bundle.command(helper_runtime, 'autowork/scripts/finish_task.py') if helper_runtime else
                      shlex.join([sys.executable, str(helper_root / 'autowork/scripts/finish_task.py')]))
    engineering_path = helper_root / 'engineering/SKILL.md'
    body = (REVIEW_DOD + '\n\n' + contract + '\n\nExecution: Implement only this selected slice; no new tasks. '
            'Decide routine reversible choices yourself; execute accepted decisions without reconfirmation. '
            'Adapt failed approaches on this card without replanning; preserve acceptance, exclusions, repository instructions, '
            'SOUL boundaries, dirty-file ownership and upstream/vendor code. '
            'Own debugging, fixes, focused tests and review handoff on this card. '
            'Repair first check failure, user-space tooling and recoverable inputs without reconfirmation. '
            'Complete all named consumers, callers, tests, fixtures and config; update scoped documentation. '
            'Do not stop after the first file; no silent scope expansion. Return outside-scope dependencies to the coordinator '
            'without discarding the candidate. Add minimal test seams within scope; dirty-file edits must be additive, '
            'attributed and disclosed. Correct stale card facts in a comment and handoff, not a replacement card.\n\n'
            'Recovery: reconstruct recoverable in-scope patches/inputs under existing authority; reuse the saved next step. '
            'For scope/attribution, inspect integration receipts and specs as well as Git refs; separately required immutable pins remain. '
            'Restore pinned artifacts only with original hash equality. A tool pending_approval holds its original operation and '
            'dependent work only: retain resume step/supplied request ID, never bypass or resubmit elsewhere; continue independent work within this card.\n\n'
            'Checks: use focused regressions and relevant analysis, cheapest first; required canonical gates remain. '
            'One integration owner coordinates heavy checks on a frozen candidate. Changed inputs invalidate affected evidence; '
            'reuse receipts only when relevant source, tests, dependencies and environment match. '
            'For repeated host gates, inspect freshness/command recognition and run the missing check; never bypass gates '
            'or replay unrelated suites. Trace changed imports to their runtime delivery boundary: inspect transitive '
            'local modules and packaging manifests with an isolated dependency-closure check when warranted; '
            'checkout tests do not prove packaged execution. If explicit scope excludes packaging edits, report the gap; '
            'keep image build/run/deployment NOT_CHECKED unless authorized and executed. '
            'Run long checks in tracked background/session execution with a finite command timeout; retain candidate, command, '
            'session identity, log and final exit. Respect execution deadlines and cancellation. '
            'Reconcile transport interruptions before retrying; never duplicate a live check. '
            'Use ignored scratch, remove owned build outputs, and update the profile-local journal.\n\n'
            'Ponytail application: choose the smallest complete change; prefer existing repository code, standard library/platform, '
            'installed dependency, then minimal new code. For material choices use verified ponytail:ponytail, '
            f'with `{helper_root / "autowork/references/ponytail.md"}` as the disclosed fallback; '
            'a retired compatibility shim is not the method. Record decision, reused paths, omitted extras and check/result; '
            'reuse unchanged source-bound decisions. Apply ponytail:ponytail-review or integrated criteria in the existing review lane. '
            'For trivial edits apply directly; preserve relevant regression coverage; never waive safety, acceptance criteria or required checks.\n\n'
            'Optional methods: only for a concrete method gap or explicit protocol request, use '
            f'`{engineering_path}` to select one verified technique. No routing-reference injection on the ready path. '
            'Autowork owns scope, authorization, task state and completion; protocols add no planning/approval/review loop. '
            'Preserve user-required methods; record material use (verified path/revision, decision/artifact and check/result) '
            'in the existing receipt. Missing optional guidance does not block work.\n\n'
            f'Mandatory completion gate: run `{finish_command} '
            '--repo <workspace> --profile <profile> --card <card-id> --message "<task summary>" '
            '--check-json \'["<check executable>", "<arg>"]\' -- <owned-file>...` before review handoff or kanban_complete; '
            'repeat --check-json for every required acceptance command. Its agent_commit.sh helper commits explicit owned files '
            'to agent/<profile>/<card-id>, preserving HEAD and foreign staged work. Isolate foreign hunks first. '
            'Require committed and exact branch/SHA; validation_failed, source_changed or commit_failed require repair/retry. '
            'no_changes means no new owned delta: cite existing source/checks, not a new commit. '
            'Explicit no-commit instructions: skip the helper, run checks, report restriction/uncommitted files. Rerun after review fixes. '
            'The integration owner performs authorized local integration of attributed commits after checks/review, '
            'using a protected PR when repository policy requires it; '
            'no direct main push or protection bypass.\n\n')
    if publication_authority is None:
        body += 'Workers perform no other commit, and no push, merge, deploy, publish, '
    else:
        body += 'Workers perform no other commit, and no merge, deploy, non-task publication, '
    body += ('spend, trade, third-party contact, profile configuration change, or schedule change.\n\n'
             'Ledger closure precondition: executed acceptance checks and required review acceptance at the tested source. '
             'Pending review keeps canonical tasks in_progress and dependencies ineligible. ')
    if ledger_mode == 'proposal':
        body += ('Canonical ledger proposals only: do not mutate goals.json, TODO goal coverage or goal evidence in any copy. '
                 'Submit task/goal IDs, source hashes, attributed changes and check receipts to integration owner ' +
                 integration_owner + ' via native context/comments; only that owner reconciles docs/tasks, validates/renders '
                 'and closes after review, then selects eligible work.\n\n')
    else:
        body += ('After that precondition, for a task named in the contract and goals.json, use docs-sync, never hand-edit goals.json: '
                 f'`{goals_command} task <repo> <TASK> done`; '
                 f'`{goals_command} evidence <repo> <GOAL> --kind executed --ref "<exact command>" --result pass|fail` '
                 f'for actual checks (met requires executed pass); `{goals_command} render <repo>`. '
                 'Without goals.json, anchor-patch the TODO task and Goal coverage.\n\n')
    body += (f'Budget: {goal_max_turns}-turn budget per invocation, not cumulative. Automatic retries are disabled. '
             'Before continuation reconcile all runs/sessions, consumed history and retry counts; unknown usage is not zero. '
             'New sessions/resume/max-turns do not preserve budgets; exhaustion requires explicit additional allocation, not a replacement card. '
             'Fix within scope until acceptance or 5 consecutive attempts without new evidence, within budget/ownership limits. '
             'Stop at acceptance; do not burn unused turns. Ask only for missing intent, conflicting requirements or authority; '
             'record recommendations in BLOCKERS.md and continue independent authorized work. Silence grants neither authority nor review.\n\n'
             'Review handoff finishes this worker card, not the product milestone; pending review is not a missing implementation criterion. '
             'One native review lane provides required independent review; no extra reviewers unless required. Only the authorized review lane can approve closure. '
             'If rejected solely for pending review, make one corrected review request citing the card Definition of done, deliverables/checks. '
             'If refused, preserve exact receipts and original card; never invent approval, force a live claim, replace the card, waive review, '
             'loop or rerun unchanged tests.\n\n'
             'Before calling kanban_complete, include Acceptance evidence: each criterion maps to delivered artifacts, '
             'exact commands/results or inspected contracts, and revision/fingerprint. Missing coverage is NOT_CHECKED; unrelated passes, '
             'judge verdicts and queue receipts prove nothing. Report Implemented, Qualified and Delivered separately: '
             'exact revision, named platform/backend journey, verified target ancestry/required PR evidence. '
             'Distinguish local integration from publication. A fixture is not live-provider qualification; Chromium is not Android qualification. '
             'Report Remaining milestone gaps, next slice, actual durations/retries/review time/usage; unknown cost stays unknown.')
    if publication_authority is not None:
        body += (' Scoped task-ref publication authority: after acceptance and owned local commit only, '
                 'the caller supplied owner evidence ' + publication_authority['evidence_ref'] +
                 ' (' + publication_authority['authority_validation'] + '). The ONLY permitted Git publication is ' +
                 '`git push ' + shlex.quote(publication_authority['remote']) + ' <receipt-commit-sha>:' +
                 shlex.quote(publication_authority['ref']) + '` from this owned workspace; use the verified receipt SHA, '
                 'not unchanged HEAD, and read back the exact remote ref/commit. No force/delete, other refs/remotes, main push, '
                 'merge, deploy, release or profile/schedule changes. This is caller attestation, not runtime enforcement or '
                 'independent approval; preserve host/repository gates and refuse unconfirmed current owner authority/ref ownership.')
    body += ('\n\nREVIEW ENTRY (same original card): reviewer/rework phase only. Do not rerun pass_workspace.py after edits. '
             'Verify original pre-edit admission in original run tool history: exact guard command, pinned manifest hash, workspace, '
             'success and ordering before edits; later receipts/replays cannot prove it. '
             'Bind the finish_task.py receipt to exact full commit/task ref; verify current ref, ancestry and cumulative diff '
             'from the admitted candidate within owned scope. Compare owned contents/modes/deletions; exclude foreign changes. '
             'Run independent checks on an isolated finish-commit snapshot, not dirty workspace union. Refuse missing or forged admission, '
             'moved task ref, unexplained blob drift or out-of-scope commits. Preserve original card/evidence; no repinning, reset, '
             'fabricated passes or replacement. Rework verifies the latest reviewed candidate before edits, reruns scoped acceptance '
             'and finish_task.py, then requests review of the exact new commit. Honor no-commit/no-change exceptions with '
             'independently bound source/checks, never fabricated commits. These instructions do not automatically enforce or approve review.')
    return body


def run(prefix, *args):
    return subprocess.check_output(prefix + list(args), text=True, timeout=30).strip()


def profile_home(prefix):
    text = run(prefix, 'profile', 'show', prefix[-1])
    for line in text.splitlines():
        if line.startswith('Path:'):
            return Path(line.partition(':')[2].strip()).resolve(strict=True)
    raise RuntimeError('Profile CLI did not return its canonical home')


def goal_fields(prefix, task_id):
    # Current CLI JSON omits these two fields. Read only the exact card row
    # in the CLI-resolved default board, never a guessed profile database.
    boards = json.loads(run(prefix, 'kanban', 'boards', 'list', '--json'))
    db_path = next(b['db_path'] for b in boards if b['slug'] == 'default')
    uri = 'file:' + quote(str(Path(db_path).resolve())) + '?mode=ro'
    with sqlite3.connect(uri, uri=True) as db:
        row = db.execute('SELECT goal_mode, goal_max_turns FROM tasks WHERE id=?', (task_id,)).fetchone()
    if row is None:
        raise RuntimeError('Created card missing from canonical board')
    return {'goal_mode': bool(row[0]), 'goal_max_turns': row[1]}


def validate_disjoint_triage(task, runs, claim, profile, title, workspace):
    """Governor-attested disjointness is not inferred from card status/title."""
    if (task.get('status') != 'triage' or task.get('assignee') != profile
            or task.get('title') == title or task.get('workspace_kind') != 'dir'
            or Path(task.get('workspace_path', '')).resolve() != Path(workspace).resolve()):
        raise ValueError('Disjoint exception requires a distinct same-profile/workspace triage card')
    if claim.get('current_run_id') is not None or claim.get('worker_pid') is not None:
        raise ValueError('Disjoint triage card has an active claim')
    if not runs or runs[-1].get('status') not in {'blocked', 'crashed'} or not runs[-1].get('ended_at'):
        raise ValueError('Disjoint triage card needs an observed terminal blocked/crashed run')
    return task['id']


def existing_task(tasks, profile, title, workspace=None, disjoint_triage=()):
    for task in tasks:
        if task.get('id') in disjoint_triage and task.get('status') == 'triage' and task.get('title') != title:
            continue
        if task.get('status') not in ACTIVE:
            continue
        same_workspace = (workspace is not None and task.get('workspace_kind') == 'dir'
                          and task.get('workspace_path')
                          and Path(task['workspace_path']).resolve() == Path(workspace).resolve())
        if task.get('assignee') == profile or same_workspace:
            return task
    for task in tasks:
        if (task.get('assignee') == profile and task.get('status') in PARKED
                and task.get('title') == title):
            return task  # Wording changes must not bypass an unresolved blocker.
    return None


def ensure_notification(prefix, task_id, home, profile):
    """Subscribe this profile's configured home chat, never wake another agent."""
    channel = None
    env_file = home / '.env'
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            key, sep, value = line.partition('=')
            if sep and key.strip() == 'TELEGRAM_HOME_CHANNEL':
                channel = value.strip().strip('\"').strip("'")
    if not channel:
        return None  # No configured Telegram home: preserve local-only profiles.
    if not channel.lstrip('-').isdigit():
        raise ValueError('Invalid configured Telegram home channel')
    board = ['kanban', '--board', 'default']
    run(prefix, *board, 'notify-subscribe', task_id, '--platform', 'telegram',
        '--chat-id', channel, '--notifier-profile', profile, '--delivery-mode', 'notify')
    subscriptions = json.loads(run(prefix, *board, 'notify-list', task_id, '--json'))
    for sub in subscriptions:
        if (sub['task_id'] == task_id and sub['platform'] == 'telegram'
                and str(sub['chat_id']) == channel and sub['notifier_profile'] == profile
                and sub['delivery_mode'] == 'notify'):
            return {k: sub[k] for k in ('platform', 'chat_id', 'notifier_profile', 'delivery_mode')}
    raise RuntimeError('Goal card exists but notification subscription was not verified; reconcile this card, do not create another')


def save_receipt(journal_dir, receipt):
    journal_dir.mkdir(parents=True, exist_ok=True)
    target = journal_dir / 'goal-handoff.json'
    if target.exists():
        original = target.read_bytes()
        previous = json.loads(original)
        # Reconcile accepts this legacy continuation wrapper; archive its complete
        # original bytes while using the nested handoff for identity and filenames.
        if (isinstance(previous, dict) and previous.get('task_id') is None
                and isinstance(previous.get('current_handoff'), dict)):
            previous = previous['current_handoff']
        if (not isinstance(previous, dict) or not isinstance(previous.get('task_id'), str)
                or not previous['task_id'] or Path(previous['task_id']).name != previous['task_id']
                or previous['task_id'] in ('.', '..')):
            raise ValueError('Invalid prior task ID; preserve the existing handoff receipt')
        identity = lambda row: (row.get('board_id'), row.get('task_id'), row.get('created_at'))
        if identity(previous) != identity(receipt):
            history = journal_dir / 'handoffs'
            history.mkdir(exist_ok=True)
            task_id = previous['task_id']
            if Path(task_id).name != task_id:
                raise ValueError('Invalid prior task ID')
            # Dated immutable content-addressed archives conserve original bytes.
            # Old undated receipts remain undated; never invent a historical date.
            stamp = previous.get('created_at', 'undated')
            stamp = re.sub(r'[^A-Za-z0-9_.-]', '-', str(stamp))
            board_digest = hashlib.sha256(str(previous.get('board_id', 'unknown')).encode()).hexdigest()[:12]
            content_digest = hashlib.sha256(original).hexdigest()
            dated = history / f'{stamp}--{board_digest}--{task_id}--{content_digest}.json'
            if not dated.exists():
                with dated.open('xb') as archive:
                    archive.write(original)
            elif dated.read_bytes() != original:
                raise ValueError('Historical receipt content collision; preserve existing archive')
            # Keep the legacy lookup only on first observation, never overwrite it.
            legacy = history / (task_id + '.json')
            if not legacy.exists():
                with legacy.open('xb') as archive:
                    archive.write(original)
    temporary = target.with_suffix('.json.pending')
    temporary.write_text(json.dumps(receipt, indent=2) + '\n')
    temporary.replace(target)


def record_handoff(prefix, journal_dir, home, profile, receipt):
    # Persist the exact created card before any fallible transport operation.
    save_receipt(journal_dir, receipt)
    try:
        receipt['notification'] = ensure_notification(prefix, receipt['task_id'], home, profile)
    except (RuntimeError, ValueError, OSError, subprocess.SubprocessError) as error:
        receipt['outcome'] = 'notification_blocked'
        receipt['notification_error'] = str(error)
    save_receipt(journal_dir, receipt)
    return receipt


def create_registered(native_python, request_path):
    """Native API owns transactional creation; retain uncertain requests without retry."""
    request = json.loads(Path(request_path).read_text())
    env = dict(os.environ, HERMES_HOME=request['profile_home'], HERMES_KANBAN_BOARD='default',
               HERMES_KANBAN_DB=request['db_path'], HERMES_KANBAN_HOME=str(Path(request['db_path']).parent))
    # Preserve worker identity so coordinator-only admission still refuses workers.
    result = subprocess.run([native_python, str(Path(__file__).with_name('registration_admission.py')),
        '--request', str(request_path)], capture_output=True, text=True, timeout=120, env=env)
    if result.returncode:
        raise ValueError('Registered native admission failed; preserve request/registry and reconcile: ' + result.stderr[-2000:])
    created = json.loads(result.stdout)
    if not isinstance(created, dict) or not created.get('id'):
        raise ValueError('Registered native admission returned no identity; reconcile retained request')
    return created


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile', required=True)
    p.add_argument('--workspace', required=True)
    p.add_argument('--title', required=True)
    p.add_argument('--contract-file', required=True)
    p.add_argument('--ledger-mode', choices=('worker', 'proposal'), default='worker',
                   help='Default worker closure, or proposals for the sole integration owner')
    p.add_argument('--integration-owner', help='Required named owner for proposal ledger mode')
    p.add_argument('--publication-authority', help='Exact owner-evidence JSON binding one remote task ref; default no push')
    p.add_argument('--goal-max-turns', type=int, choices=(50, 100),
                   help='New worker budget (default: 100); never resizes an existing owned card')
    p.add_argument('--goal-task', help='Exact dependency-ready ledger task identity')
    p.add_argument('--fallback-file', help='Structured JSON fallback attestations bound to selection evidence')
    p.add_argument('--source-snapshot', help='Scoped evidence snapshot captured before candidate selection')
    p.add_argument('--disjoint-blocked-handoff', help='Pinned original blocked card and distinct task owned-scope evidence')
    p.add_argument('--registration-native-python', help='Installed native runtime launcher for atomic registered creation; requires declaration')
    p.add_argument('--registration-declaration', help='Explicit JSONL coordination registry, field mappings and owned scope; reserve blocked without dispatch')
    p.add_argument('--base', help='Immutable full base commit; required for new Git write passes')
    p.add_argument('--candidate', help='Explicit committed candidate to assemble; defaults to the pinned base')
    p.add_argument('--prerequisite', action='append', default=[], metavar='REF=FULL_COMMIT')
    p.add_argument('--required-path', action='append', default=[], help='Explicit dependency-closure file that must exist after assembly')
    p.add_argument('--pass-root', default=str(Path.home() / '.hermes/cache/scratch/autowork-passes'),
                   help='Private isolated Git worktrees, never the shared source checkout')
    p.add_argument('--disjoint-terminal-triage', action='append', default=[], metavar='CARD_ID',
                   help='Governor-only attestation of resource-disjoint work; verify terminal claim under lock, preserve original card')
    p.add_argument('--validate-only', action='store_true',
                   help='Check contract structure without CLI calls, journal writes or dispatch')
    p.add_argument('--admission-attempt', help=argparse.SUPPRESS)
    p.add_argument('--admission-request-sha256', help=argparse.SUPPRESS)
    args = p.parse_args()
    if args.admission_attempt is not None:
        if (not re.fullmatch(r'[0-9a-f]{32}', args.admission_attempt)
                or not re.fullmatch(r'[0-9a-f]{64}', args.admission_request_sha256 or '')):
            p.error('invalid owner admission attempt binding')
    boundary = {'native_create_attempted': False}
    launcher_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    try:
        return admit(args, boundary)
    except (SystemExit, ValueError, OSError, TypeError, KeyError) as error:
        # Only this trusted launcher knows whether creation was entered. Transport
        # failures, process death and failures after the boundary remain unknown.
        if args.admission_attempt and not boundary['native_create_attempted']:
            print(json.dumps({'outcome': 'refused_before_create',
                'attempt_id': args.admission_attempt,
                'request_sha256': args.admission_request_sha256,
                'launcher_sha256': launcher_sha256,
                'native_create_attempted': False, 'reason': str(error)}))
            raise SystemExit(1) from error
        raise


def admit(args, boundary):
    if os.environ.get('HERMES_KANBAN_TASK'):
        raise SystemExit('Already a goal worker: execute the assigned card, never launch a nested goal.')
    if args.registration_native_python and not args.registration_declaration:
        raise SystemExit('Transactional registration requires --registration-declaration')
    contract = Path(args.contract_file).read_text().strip()
    role_contract = contract
    try:
        fields = validate_contract(contract, args.goal_max_turns)
        if args.goal_max_turns is None:
            args.goal_max_turns = BUDGET
            if not re.search(r'^\s*Goal budget rationale:', contract, re.MULTILINE):
                role_contract += '\nGoal budget rationale: ' + fields['Goal budget rationale']
        publication = None
        if args.publication_authority:
            publication = validate_publication_authority(json.loads(Path(args.publication_authority).read_text()),
                                                         args.workspace, args.profile, args.goal_task, contract)
        build_task_body(role_contract, args.goal_max_turns, ledger_mode=args.ledger_mode,
                        integration_owner=args.integration_owner, publication_authority=publication)
    except (ValueError, OSError, TypeError, KeyError) as error:
        raise SystemExit(str(error)) from error
    if args.validate_only:
        try:
            admission = require_milestone_admission(args.workspace, args.goal_task, args.source_snapshot, args.fallback_file)
        except (ValueError, OSError, TypeError, KeyError) as error:
            raise SystemExit(str(error)) from error
        print(json.dumps({'outcome': 'contract_validated', 'fields': list(CONTRACT_FIELDS),
                          'goal_max_turns': args.goal_max_turns,
                          'factual_validation': False, 'admission': admission,
                          **({'worker_roles': {'ledger_mode': args.ledger_mode,
                              'integration_owner': args.integration_owner,
                              'publication_ref': publication['ref'] if publication else None,
                              'authority_validation': publication['authority_validation'] if publication else None}}
                             if args.ledger_mode != 'worker' or publication else {})}))
        return
    prefix = ['hermes', '-p', args.profile]
    workspace = Path(args.workspace).expanduser().resolve(strict=True)
    configured = Path(run(prefix, 'config', 'get', 'terminal.cwd')).expanduser().resolve(strict=True)
    if workspace != configured:
        raise SystemExit(f'Workspace differs from profile cwd: {workspace} != {configured}')
    # Resolve the target, not the launch profile or a guessed ~/.hermes path.
    home = profile_home(prefix)
    journal_dir = home / 'autowork'
    journal_dir.mkdir(parents=True, exist_ok=True)
    with (journal_dir / 'goal-handoff.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        board = ['kanban', '--board', 'default']
        tasks = json.loads(run(prefix, *board, 'list', '--json'))
        distinct = None
        if args.disjoint_blocked_handoff:
            import disjoint_fallback
            distinct = disjoint_fallback.verify(args.disjoint_blocked_handoff,
                journal_dir / 'goal-handoff.json', workspace, args.profile, args.goal_task,
                args.registration_declaration)
        disjoint_triage = set()
        for task_id in args.disjoint_terminal_triage:
            detail = json.loads(run(prefix, *board, 'show', task_id, '--json'))
            boards = json.loads(run(prefix, 'kanban', 'boards', 'list', '--json'))
            db_path = next(b['db_path'] for b in boards if b['slug'] == 'default')
            with sqlite3.connect('file:' + quote(str(Path(db_path).resolve())) + '?mode=ro', uri=True) as db:
                row = db.execute('SELECT status,current_run_id,worker_pid FROM tasks WHERE id=?', (task_id,)).fetchone()
            if row is None or row[0] != 'triage':
                raise SystemExit('Disjoint triage state changed before handoff')
            claim = {'current_run_id': row[1], 'worker_pid': row[2]}
            disjoint_triage.add(validate_disjoint_triage(detail['task'], detail.get('runs', []), claim,
                                                       args.profile, args.title, workspace))
        task = existing_task(tasks, args.profile, args.title, workspace, disjoint_triage)
        if task is not None and task.get('assignee') != args.profile:
            print(json.dumps({'outcome': 'workspace_owned', 'task_id': task['id'],
                              'assignee': task.get('assignee'), 'status': task['status']}))
            return  # Do not attach this profile's notifier to another owner's card.
        if task is not None:
            # Existing ownership must never authorize a fresh preparation, even
            # when its notification/readback fails before our own create call.
            boundary['native_create_attempted'] = True
            notification = ensure_notification(prefix, task['id'], home, args.profile)
            print(json.dumps({'outcome': 'already_owned', 'task_id': task['id'], 'status': task['status'], 'notification': notification, **goal_fields(prefix, task['id'])}))
            return
        try:
            require_fresh_sources(args.source_snapshot, workspace)
            snapshot_bytes = Path(args.source_snapshot).read_bytes()
        except (ValueError, OSError, TypeError, KeyError) as error:
            raise SystemExit(str(error)) from error
        # Resolve stable board identity before the final admission/freshness checks.
        boards = json.loads(run(prefix, 'kanban', 'boards', 'list', '--json'))
        canonical_board = next(b for b in boards if b['slug'] == 'default')
        board_id = canonical_board.get('id') or canonical_board.get('board_id') or str(Path(canonical_board['db_path']).resolve())
        digest = hashlib.sha256((args.profile + '\n' + str(workspace) + '\n' + args.title + '\n' + contract).encode()).hexdigest()
        # Final check after live ownership reconciliation, immediately before create.
        try:
            require_fresh_sources(args.source_snapshot, workspace)
            admission = require_milestone_admission(workspace, args.goal_task, args.source_snapshot, args.fallback_file)
            require_fresh_sources(args.source_snapshot, workspace)
            ledger = workspace / 'goals.json'
            current_ledger = hashlib.sha256(ledger.read_bytes()).hexdigest() if ledger.exists() else None
            if current_ledger != admission['ledger_sha256']:
                raise ValueError('Goal ledger changed before create; re-evaluate selection')
        except (ValueError, OSError, TypeError, KeyError) as error:
            raise SystemExit(str(error)) from error
        # Assembly uses only attributed committed inputs, never the dirty checkout union.
        helper_runtime = None
        dispatch_ready = False
        try:
            if not args.base:
                raise ValueError('New write passes require --base full immutable commit')
            pins = {}
            for declaration in args.prerequisite:
                ref, sep, pin = declaration.partition('=')
                if not sep or not ref or ref in pins or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', pin):
                    raise ValueError('Prerequisite requires unique REF=FULL_COMMIT')
                pins[ref] = pin
            spec = importlib.util.spec_from_file_location('autowork_pass_workspace', Path(__file__).with_name('pass_workspace.py'))
            assert spec is not None and spec.loader is not None
            passes = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(passes)
            if Path(args.source_snapshot).read_bytes() != snapshot_bytes:
                raise ValueError('Source snapshot changed since selection; re-evaluate work')
            expected = json.loads(snapshot_bytes)
            registration = None
            if args.registration_declaration:
                if not args.goal_task:
                    raise ValueError('Required registration needs an exact goal task')
                registration_spec = importlib.util.spec_from_file_location('handoff_registration',
                    Path(__file__).with_name('writer_registration.py'))
                registration_module = importlib.util.module_from_spec(registration_spec)
                registration_spec.loader.exec_module(registration_module)
                declaration_raw = Path(args.registration_declaration).read_bytes()
                registration = registration_module.capture_declaration(
                    json.loads(declaration_raw, object_pairs_hook=registration_module.unique_object),
                    workspace, expected['files'], args.required_path)
                registration['declaration'] = declaration_raw.decode()
                registration['declaration_sha256'] = hashlib.sha256(declaration_raw).hexdigest()
            planning_context = (passes.capture_planning_context(workspace, expected, admission, args.integration_owner)
                                if args.ledger_mode == 'proposal' and admission.get('goal_task') else None)
            context_paths = set(planning_context['files']) if planning_context else set()
            required_paths = [name for name in args.required_path if name not in context_paths]
            pass_path = Path(args.pass_root).expanduser().resolve() / (digest[:16] + '-' + uuid.uuid4().hex)
            identity = passes.prepare(workspace, pass_path, args.base, args.candidate or args.base,
                                      pins, required_paths)
            helper_runtime = runtime_bundle.freeze(Path(__file__).resolve().parents[2], journal_dir / 'runtimes')
            body = build_task_body(role_contract, args.goal_max_turns, ledger_mode=args.ledger_mode,
                                   integration_owner=args.integration_owner, publication_authority=publication,
                                   helper_runtime=helper_runtime)
            body += ('\n\nHELPER RUNTIME: The commands below bind this card to the frozen bundle at ' +
                     shlex.quote(helper_runtime['root']) + ' with manifest SHA256 ' + helper_runtime['sha256'] +
                     '. Use these verified entry commands for the entire card, including rework and closeout. '
                     'Do not substitute helpers from a shared checkout or refreshed profile installation. '
                     'A missing or changed bundle is an original-card recovery hold; never silently rebind it.')
            manifest = {'version': 1, 'source_workspace': str(workspace), 'candidate_identity': identity,
                        'files': expected['files'], 'ledger_sha256': admission['ledger_sha256'],
                        'source_snapshot_sha256': hashlib.sha256(snapshot_bytes).hexdigest(),
                        'goal_task': args.goal_task, 'helper_runtime': helper_runtime}
            if planning_context:
                manifest.update(ledger_mode='proposal', planning_context=planning_context)
            if registration:
                manifest['registration_preparation'] = registration
            manifest_path = journal_dir / ('pass-' + pass_path.name + '.json')
            with manifest_path.open('x') as stream:
                json.dump(manifest, stream, indent=2)
            manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            guard = runtime_bundle.command(helper_runtime, 'autowork/scripts/pass_workspace.py') + \
                    ' --manifest ' + shlex.quote(str(manifest_path)) + ' --manifest-sha256 ' + manifest_sha256 + \
                    ' --workspace ' + shlex.quote(str(pass_path))
            body += ('\n\nMANDATORY WORKER START — INITIAL IMPLEMENTATION ONLY: This command does not apply to review entry or review rework. Before initial design, tests or any production edit, run `' + guard +
                     '`. Refusal means stop on the ORIGINAL card, with exact diagnostic; do not refresh evidence, '
                     'correct stale wording into a new scope, edit production or create a replacement. '
                     'All writes stay in this card native workspace; the source checkout is read-only. '
                     'The same helper can gate an initial write command with `-- <command>`. '
                     'This is an executable preflight, not a filesystem sandbox or native runtime hook. '
                     'Before this guard, check applicable repository instructions for explicit writer registration. '
                     'If required, the coordinator must register this exact card/workspace/base/owned scope '
                     'and bind its read-only verifier before edits; a generic worker_start_admitted receipt '
                     'alone does not establish repository registration. Use handoff.md registration guidance; '
                     'wait on this original card for preparation, not a replacement worker or retrospective entry.')
            if planning_context:
                body += ('\n\nREAD-ONLY PLANNING CONTEXT: The hash-pinned manifest above contains '
                         '`planning_context.files`: immutable goals.json, TODO.md and selected plan inputs. '
                         'Read those task instructions there, not stale or missing copies in the worker checkout. '
                         'They are context only, not adopted product edits. Do not copy, commit or close that '
                         'ledger; return implementation and acceptance evidence to the named integration owner. '
                         'Executable source still must match the admitted committed candidate.')
            # No native calls between this final source/ledger/candidate check and create.
            if Path(args.source_snapshot).read_bytes() != snapshot_bytes:
                raise ValueError('Source snapshot changed during assembly; re-evaluate selection')
            final_admission = require_milestone_admission(workspace, args.goal_task, args.source_snapshot, args.fallback_file)
            if final_admission != admission:
                raise ValueError('Goal admission changed during assembly')
            require_fresh_sources(args.source_snapshot, workspace)
            if registration:
                passes.verify_registration_preparation(manifest, pass_path)
                if args.registration_native_python:
                    body += ('\n\nREQUIRED REGISTRATION: Native creation commits only after this exact '
                             'card/workspace/base/owned scope is registered and its pinned guard verified. '
                             'Run the mandatory initial guard above; retain its original manifest. '
                             'Owned scope: ' + json.dumps(registration['scope']) + '.')
                else:
                    body += ('\n\nREQUIRED REGISTRATION: This card is reserved blocked without dispatch. '
                             'Owned scope: ' + json.dumps(registration['scope']) + '. '
                             'Use the repository supported operation for this exact native identity, then '
                             'prepare retained prerequisites with writer_registration.py. Preparation does '
                             'not release the card or migrate its frozen runtime; those require supported native controls.')
            else:
                passes.verify(manifest, pass_path)
            runtime_bundle.verify(helper_runtime)
            dispatch_ready = True
        except (ValueError, OSError, TypeError, KeyError) as error:
            raise SystemExit(str(error)) from error
        finally:
            # No native creation has been attempted in this block. After it, a
            # transport failure may hide a created card, so retain its runtime.
            if helper_runtime is not None and not dispatch_ready:
                shutil.rmtree(helper_runtime['root'])
        reservation = journal_dir / ('reservation-' + pass_path.name + '.json')
        reservation_template = dict(profile=args.profile, board_id=board_id,
            goal_task=args.goal_task, workspace=str(pass_path), source_workspace=str(workspace),
            helper_runtime=helper_runtime, goal_mode=True, goal_max_turns=args.goal_max_turns,
            max_retries=MAX_RETRIES, pass_manifest_path=str(manifest_path),
            pass_manifest_sha256=manifest_sha256, pass_manifest=manifest,
            source_snapshot=snapshot_bytes.decode())
        if distinct:
            # Re-read original terminal identity after assembly, immediately before new admission.
            checked = disjoint_fallback.verify(args.disjoint_blocked_handoff,
                journal_dir / 'goal-handoff.json', workspace, args.profile, args.goal_task,
                args.registration_declaration)
            if checked != distinct or str(pass_path) == distinct['original_workspace']:
                raise ValueError('Original fallback state changed or worker workspace reused')
            reservation_template['disjoint_fallback'] = distinct
        if args.registration_native_python:
            request_path = journal_dir / ('registration-request-' + pass_path.name + '.json')
            request = dict(db_path=str(Path(canonical_board['db_path']).resolve()),
                profile=args.profile, profile_home=str(home), manifest_path=str(manifest_path), manifest_sha256=manifest_sha256,
                receipt_path=str(reservation), handoff_template=reservation_template,
                task=dict(title=args.title, body=body, assignee=args.profile, workspace_kind='dir',
                    workspace_path=str(pass_path), goal_mode=True, goal_max_turns=args.goal_max_turns,
                    max_retries=MAX_RETRIES, completion_contract='local-only', created_by='autowork',
                    idempotency_key='autowork:' + digest))
            with request_path.open('x') as stream:
                json.dump(request, stream, indent=2)
            boundary['native_create_attempted'] = True
            created = create_registered(args.registration_native_python, request_path)
        else:
            boundary['native_create_attempted'] = True
            created = json.loads(run(prefix, *board, 'create', args.title, '--body', body,
                                     '--assignee', args.profile, '--workspace', 'dir:' + str(pass_path),
                                     '--goal', '--goal-max-turns', str(args.goal_max_turns), '--max-retries', str(MAX_RETRIES),
                                     '--completion-contract', 'local-only', '--created-by', 'autowork',
                                     *(['--initial-status', 'blocked'] if registration else []),
                                     '--idempotency-key', 'autowork:' + digest, '--json'))
        task_id = created['id']
        if registration and not args.registration_native_python:
            # Retain the returned identity before any fallible native readback.
            with reservation.open('x') as stream:
                json.dump(dict(reservation_template, native_create=created, task_id=task_id), stream, indent=2)
        saved = json.loads(run(prefix, *board, 'show', task_id, '--json'))
        task = saved.get('task', saved)
        task.update(goal_fields(prefix, task_id))
        if (task.get('workspace_kind') != 'dir' or Path(task.get('workspace_path', '')).resolve() != pass_path):
            # Native idempotency may reconcile a concurrent/original card. Never migrate it.
            if task.get('assignee') != args.profile:
                print(json.dumps({'outcome': 'workspace_owned', 'task_id': task_id,
                                  'assignee': task.get('assignee'), 'status': task['status']}))
                return
            notification = ensure_notification(prefix, task_id, home, args.profile)
            print(json.dumps({'outcome': 'already_owned', 'task_id': task_id, 'status': task['status'],
                              'notification': notification, 'goal_mode': task['goal_mode'],
                              'goal_max_turns': task['goal_max_turns']}))
            return
        if type(task.get('max_retries')) is not int or task['max_retries'] != MAX_RETRIES:
            raise ValueError('Native retry limit differs from the requested single-attempt policy; preserve the original card and reconcile it before retrying')
        assert task['goal_mode'] and task['goal_max_turns'] == args.goal_max_turns, task
        assert task['assignee'] == args.profile, task
        assert task['workspace_kind'] == 'dir' and Path(task['workspace_path']).resolve() == pass_path, task
        assert task['completion_contract'] == 'local-only', task
        if registration and not args.registration_native_python and (task['status'] != 'blocked' or saved.get('runs') != []
                             or task.get('current_run_id') or task.get('worker_pid')):
            raise ValueError('Required registration reservation is not an unused blocked card; preserve original evidence')
        created_at = task.get('created_at')
        if isinstance(created_at, (int, float)):
            created_at = datetime.fromtimestamp(created_at, timezone.utc)
        elif created_at:
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            if created_at.tzinfo is None:
                raise ValueError('Native created_at lacks timezone; preserve original card for reconciliation')
        else:
            created_at = datetime.now(timezone.utc)
        receipt = {'outcome': 'registration_pending' if registration and not args.registration_native_python else 'handed_off', 'task_id': task_id, 'profile': args.profile,
                   'workspace': str(pass_path), 'source_workspace': str(workspace),
                   'pass_manifest': manifest, 'pass_manifest_path': str(manifest_path),
                   'pass_manifest_sha256': manifest_sha256,
                   'helper_runtime': helper_runtime,
                   'goal_mode': True, 'goal_max_turns': args.goal_max_turns,
                   'max_retries': MAX_RETRIES,
                   'budget_policy': {'allocation_scope': 'worker_invocation',
                                     'automatic_failure_retries': False,
                                     'cumulative_enforcement': 'not_available',
                                     'resume_requires': 'verified remaining allocation and supported enforcement'},
                   'status': task['status'], 'board_id': task.get('board_id') or board_id,
                   'created_at': created_at.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z'),
                   **admission}
        if distinct:
            receipt['disjoint_fallback'] = distinct
        receipt = record_handoff(prefix, journal_dir, home, args.profile, receipt)
        # Notification setup and dispatch may have advanced the card. Preserve
        # the durable receipt even if this final read fails.
        try:
            latest = json.loads(run(prefix, *board, 'show', task_id, '--json'))
            receipt['status'] = latest.get('task', latest)['status']
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            receipt['observation_error'] = str(error)
        save_receipt(journal_dir, receipt)
        print(json.dumps(receipt))


if __name__ == '__main__':
    main()
