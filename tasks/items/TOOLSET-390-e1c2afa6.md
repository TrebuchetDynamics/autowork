+++
schema = 1
goal = "EVALUATION"
status = "open"
resources = []
id = "TOOLSET-390-e1c2afa6"
title = "Connect bounded SDK controls to existing coordinator supervision without new authority"
short = "Qualify coordinator RPC controls"
section = "Next"
rank = 4300
depends_on = ["TOOLSET-388-b422fa9e"]
touches = ["Src","pi-autowork","tests","docs/pi-rpc.md"]
kind = "implementation"
ownership = "worker"
scope = "Integrate the existing fixed-template SDK-host control API with the existing coordinator, using a bounded private per-invocation channel rather than a second scheduler/database. Keep automatic intervention off by default and make any observation-only policy explicit. This slice currently exposes no production cross-process control endpoint."
acceptance = ["Control submission remains bound to live generation, engine attempt, unchanged accepted canonical contract and worker role; reviewers cannot be steered.","No raw model/tool text becomes instructions or authorization. Pre-send budgets/fingerprints survive crash; late, duplicate, stale and uncertain submissions never replay automatically.","Native SDK tests exercise a control accepted during the owned stream, settlement/abort races and private channel bounds. Existing engine verification and closure remain authoritative."]
checks = ["python3 scripts/affected_tests.py --json","python3 pi-autowork/pi_autowork/command.py tasks validate --worktree ."]
exclusions = ["No custom Pi protocol, new task authority or remote service, automatic steering opt-in, scope expansion or reviewer influence."]
+++
- Source: docs/research/pi-rpc-qualification-2026-10-24.md
- This follow-up is pending; no acceptance, ownership release or installed activation is asserted.
