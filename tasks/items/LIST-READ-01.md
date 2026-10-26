+++
schema = 1
id = "LIST-READ-01"
title = "Make fleet questions, stale activity and task selection readback evidence-bound"
short = "Repair misleading queue reads"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Now"
rank = 1000
depends_on = []
touches = ["Src/pi_autowork/fleet_view.py", "Src/pi_autowork/health.py", "Src/pi_autowork/questions.py", "Src/pi_autowork/task_commands.py", "pi-autowork/tests/test_fleet_view.py", "pi-autowork/tests/test_health.py", "pi-autowork/tests/test_questions.py", "tests/test_task_commands.py", "pi-autowork/task-store.md"]
resources = ["autowork-readback"]
kind = "implementation"
ownership = "coordinator"
scope = "Repair the observed fleet/list readback defects from the all-nine-runner audit at 66faaa02. Parse wrapped planning Task/Question fields as complete logical fields, retaining relevant explicit resolution/owner context without interpreting natural language as authority. Expire stale working health when no separately verified current job proves work; retain observation provenance. Make list/why explicitly identify canonical selection-only results, retaining compatible fields and separating runtime admission. Replace external-input remediation that suggests weakening acceptance with exact causal input/handoff guidance. Use explicit resolution markers for answered historical planning questions; never infer completion or release from a linked done planning task alone."
acceptance = ["Realistic wrapped planning questions retain their complete choices and stop at the next field/heading; explicit resolved history remains suppressed, and done planning tasks can still own unanswered continuation questions. Focused fleet reader regressions prove these cases.", "A live coordinator with stale working status and no current job is marked not cycling, not current working. Fresh working and separately live current-job controls preserve correct behavior. Health tests prove timestamp/provenance behavior.", "Task list/why preserve existing outputs while adding unambiguous committed-selection-only semantics and revision provenance; held runtime tasks are not represented as dispatch-authorized. CLI regressions and task-store docs prove the contract.", "External signed-artifact and exclusive-access blocker questions request the actual missing input/handoff and preserve acceptance/authority, not cosmetic edits or weakened safety. Question regressions cover this.", "Independent review and focused checks pass. Publication waits for exact-revision full-main PASS; supported installation/update compatibility and runtime revision are separately verified. No owner deferral, pause, resource hold or qualification is fabricated."]
checks = ["python3 scripts/check.py pi-autowork/tests/test_fleet_view.py pi-autowork/tests/test_health.py pi-autowork/tests/test_questions.py tests/test_task_commands.py", "python3 scripts/affected_tests.py --run", "python3 pi-autowork/pi_autowork/command.py tasks validate --worktree .", "git diff --check"]
exclusions = ["No bypass of owner decisions, signed artifacts, live ownership, device or production gates; no change to scheduler admission, claims, receipts or closure authority; no interpreting arbitrary natural language as resolution; no credential/model changes or unrelated checkout edits."]
+++
- Sources: Owner request to analyze all Autowork lists, improve Autowork and reinstall; Src/pi_autowork/fleet_view.py::_planning_questions; health.py::fleet; questions.py::build; task_commands.py::cmd_list/cmd_why.
- Evidence: Audit at 66faaa02 covered all nine registered repository queues. A consumer retains an explicitly answered historical planning question without a machine-readable resolution marker; another wrapped owner choice is truncated after its first physical line. Stale-working exemption reproduced independently. Selection-only list/why differs legitimately from runtime holds; disclosure must not clear those holds. Detailed private scout evidence retained locally in /tmp/autowork-list-audit-{a,b,c}.md.
- Planner calls: Retain canonical/runtime separation and backward-compatible fields. Prefer explicit resolution markers over natural-language inference or dropping every closed planner's questions. Use existing freshness window and verified-job override; no new liveness threshold or scheduler. Display fixes cannot grant authority.
- Builder disposition: Session precedence is existing intentional behavior, not the answered-question cause; do not redesign it. Wrapped fields need boundary tests. Stale worker counts are last-known observations, not current work. Verify actual CLI test paths before running. Full-main checks and installed adoption remain distinct from focused offline tests.
- Delivery: Explicit current owner request authorizes implementation and supported reinstall; exact-revision publication gate and existing live exclusions remain binding.
- Held by: interactive list-read repair
