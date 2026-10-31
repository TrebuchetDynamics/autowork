+++
schema = 1
goal = "EVALUATION"
status = "open"
resources = []
id = "TOOLSET-389-6dedfd8c"
title = "Qualify one owned installed RPC runner and matched engineering measurements"
short = "Qualify installed RPC cutover"
section = "Needs decision"
rank = 4200
depends_on = ["TOOLSET-388-b422fa9e"]
touches = ["docs/research"]
kind = "inspection"
ownership = "owner"
live = "denied"
scope = "Select an explicitly owned target and safe cutover window after canonical integration. Qualify installed execution, actual engine closure and interrupted-attempt recovery with automatic steering off; compare matched engineering tasks against explicit JSON baseline without changing publication authority. The existing disposable model smokes do not qualify a fleet."
acceptance = ["Target identity, ownership release, update/rollback window and any live authorization are explicit before an installed runner is changed; paused jobs remain paused.","Actual model work reaches checks, independent review and engine closure, and an interrupted accepted attempt recovers without duplicate dispatch or lost partial work.","Report comparable wall time, startup/tool/recovery latency, token coverage, retry/intervention counts and quality/check coverage. Missing cost remains unknown; no savings or fleet claim is inferred from synthetic fixtures."]
checks = ["python3 pi-autowork/pi_autowork/command.py tasks validate --worktree ."]
exclusions = ["No blanket fleet restart, credential changes, deployment, push grant, money movement or automatic steering activation."]
+++
- Source: docs/research/pi-rpc-qualification-2026-10-24.md
- This follow-up is pending; no acceptance, ownership release or installed activation is asserted.
- Pilot preparation: Owner direction 2026-10-24: delivery gates before new RPC features. Proposed bounded installed-runner plan: docs/research/pi-rpc-installed-pilot-plan-2026-10-24.md. Prefer one disposable standalone target, no remotes, one worker, isolated state, automatic steering and publication disabled. Exact target, model/time budget and interruption window still require explicit authorization; live remains denied. Preserve active fleet workers and existing recovery evidence. Source/default/readiness observations are not installed execution or fleet qualification.
- Pipeline experiment: 2026-10-24 planning-only: reuse this same pending installed-pilot authority decision for docs/evaluation.md#controlled-experiment-plan; no second live task or job is created. Existing docs/research/pi-rpc-installed-pilot-plan-2026-10-24.md remains the bounded pilot owner. Explicit runner-window/landing/qualification endpoints and private attention records are needed before productivity claims; n=1 is diagnostic, not a throughput comparison. A larger matched sample needs separately authorized limits and does not widen this task's current live=denied or spending/publication authority.
- Owner decision: 2026-10-24: deferred until Paseo qualification finishes. Preserve the installed RPC pilot acceptance and exclusions; live operations remain denied. Keep TOOLSET-390-e1c2afa6 dependent on this unfinished pilot. This decision supplies no runner start/restart, model-call, interruption or publication authority.
- Blocker resolution: 2026-10-31: owner deleted dependent TOOLSET-390-e1c2afa6; preserve this deferred pilot, live=denied and acceptance.
