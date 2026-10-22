"""Stable failure classification shared by the engine, health, questions and the TUI.

A failure type says what went wrong. The resolution owner says who can clear it. The two
must not be conflated: a rejected review or a dead worker is an engineering problem even
when the worker's retry budget is exhausted; only a genuine product, scope, authorization
or external-input decision belongs to the owner.

The inputs are typed hold causes from ``parallel_state``, never substrings of a
human-readable reason. Unknown evidence stays an engineering investigation instead of
being promoted to an owner decision.
"""
from hashlib import sha1
import re

ENGINE = 'ENGINE'
AGENT_REPAIR = 'AGENT_REPAIR'
OWNER = 'OWNER'
EXTERNAL = 'EXTERNAL'
RESOLUTION_OWNERS = (ENGINE, AGENT_REPAIR, OWNER, EXTERNAL)

# cause -> (failure_class, resolution_owner, state, next_action)
POLICY = {
    # Technical defects: a coding or documentation agent must repair the candidate.
    'validation': ('VALIDATION_FAILURE', AGENT_REPAIR, 'repair_required', 'repair_validation_findings'),
    'reviewed_twice': ('VALIDATION_FAILURE', AGENT_REPAIR, 'engineering_stuck', 'resume_repair_with_new_evidence'),
    'no_change': ('CONTRACT_MISMATCH', AGENT_REPAIR, 'repair_required', 'restate_or_close_task'),
    'scope': ('SCOPE_VIOLATION', OWNER, 'owner_decision_required', 'decide_scope_or_touches'),
    'scope_request': ('SCOPE_VIOLATION', OWNER, 'owner_decision_required', 'decide_scope_or_touches'),
    # Process and recovery failures: the engine can retry or recover without a person.
    'timeout': ('PROCESS_TIMEOUT', ENGINE, 'recovery_required', 'reverify_candidate'),
    'overlap': ('RESOURCE_CONFLICT', ENGINE, 'recovery_required', 'reoffer_when_files_are_free'),
    'report': ('EVIDENCE_MISSING', ENGINE, 'recovery_required', 'resume_report'),
    # The report-only resume was used and the attempt still has no acceptable report: the retained
    # commit is kept (no fresh attempt replaces it), so a person inspects it, then releases or
    # sets it aside. Left as an engine recovery, nothing ever acted on it (2026-10-21, 14 hours).
    'report_exhausted': ('EVIDENCE_MISSING', OWNER, 'owner_decision_required',
                         'inspect_retained_commit_then_release_or_set_aside'),
    'conflict': ('MERGE_CONFLICT', ENGINE, 'recovery_required', 'resolve_conflict'),
    'task_wait': ('DEPENDENCY_WAIT', ENGINE, 'waiting', 'wait_for_dependency'),
    'runner_merged': ('STALE_CANDIDATE', ENGINE, 'recovery_required', 'requeue_from_kept_tip'),
    'contract_changed': ('CONTRACT_CHANGED', ENGINE, 'recovery_required', 'requeue_from_current_contract'),
    'moved': ('CANONICAL_MOVED', ENGINE, 'recovery_required', 'reverify_candidate'),
    'stale_validation': ('VALIDATION_FAILURE', ENGINE, 'recovery_required', 'reoffer_candidate'),
    'crash': ('PROCESS_INTERRUPTED', ENGINE, 'recovery_required', 'requeue_safely'),
    'empty': ('PROCESS_INTERRUPTED', ENGINE, 'recovery_required', 'requeue_safely'),
    'diverged': ('PROCESS_INTERRUPTED', ENGINE, 'recovery_required', 'requeue_safely'),
    'launch': ('PROCESS_INTERRUPTED', ENGINE, 'recovery_required', 'requeue_safely'),
    # The worker asked for a human-supplied input or authorization.
    'blocker': ('EXTERNAL_INPUT', OWNER, 'owner_decision_required', 'answer_owner_question'),
}

UNKNOWN = ('UNKNOWN_FAILURE', ENGINE, 'investigation_required', 'inspect_and_classify')


def effective_cause(cause, resume_used=False):
    """The typed cause the policy judges: a report hold whose report-only resume was already
    used (``resume_used``, from the slot's own fields, never from reason text) is exhausted."""
    return 'report_exhausted' if cause == 'report' and resume_used else cause


def classify(cause, reason=''):
    """Typed disposition for a hold ``cause``.

    ``reason`` is retained for diagnostics only; it never promotes a technical cause to an
    owner decision, and no branch matches text inside it. An unknown or missing cause is
    investigated by the engine, not asked of the owner.
    """
    values = POLICY.get(cause)
    failure_class, owner, state, next_action = values or UNKNOWN
    return dict(failure_class=failure_class, resolution_owner=owner, state=state,
                next_action=next_action, owner_decision_required=owner == OWNER,
                reason_code=str(cause or 'unknown'))


def owner_decision_required(cause, reason=''):
    return classify(cause, reason)['owner_decision_required']


def technical(cause, reason=''):
    """A failure the engine or an agent can act on without a human decision."""
    return not owner_decision_required(cause, reason)


def fingerprint(text):
    """Normalize a failure finding so repeated polling does not look like new evidence."""
    normalized = ' '.join(str(text or '').split()).lower()
    # Volatile timing/attempt decorations do not make a failure materially different.
    normalized = re.sub(r'\b\d+(?:\.\d+)?\s*(?:s|sec|secs|seconds|min|mins|minutes)\b', '<time>', normalized)
    normalized = re.sub(r'\battempt\s+\d+(?:/\d+)?\b', 'attempt <n>', normalized)
    return sha1(normalized.encode('utf-8'), usedforsecurity=False).hexdigest()[:16]


def incident_id(repository, task, cause, candidate='', finding=''):
    """Stable identity for one failure of one task at one candidate/contract revision."""
    values = classify(cause, finding)
    material = '\0'.join((str(repository), str(task), values['failure_class'],
                          str(candidate or ''), fingerprint(finding)))
    return 'INC-' + sha1(material.encode('utf-8'), usedforsecurity=False).hexdigest()[:16]
