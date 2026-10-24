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
depends_on = ["TOOLSET-388-b422fa9e", "TOOLSET-389-6dedfd8c"]
touches = ["Src","pi-autowork","tests","docs/pi-rpc.md"]
kind = "implementation"
ownership = "worker"
scope = "Integrate the existing fixed-template SDK-host control API with the existing coordinator, using a bounded private per-invocation channel rather than a second scheduler/database. Keep automatic intervention off by default and make any observation-only policy explicit. This slice currently exposes no production cross-process control endpoint."
acceptance = ["Control submission remains bound to live generation, engine attempt, unchanged accepted canonical contract and worker role; reviewers cannot be steered.","No raw model/tool text becomes instructions or authorization. Pre-send budgets/fingerprints survive crash; late, duplicate, stale and uncertain submissions never replay automatically.","Native SDK tests exercise a control accepted during the owned stream, settlement/abort races and private channel bounds. Existing engine verification and closure remain authoritative."]
checks = ["test -n \"$PI_AUTOWORK_RPC_PYTHON\" && \"$PI_AUTOWORK_RPC_PYTHON\" -c \"import pi_agent\"", "\"$PI_AUTOWORK_RPC_PYTHON\" scripts/check.py pi-autowork/tests/test_pi_rpc.py pi-autowork/tests/test_pi_process.py pi-autowork/tests/test_recovery_runtime_failures.py tests/test_pi_rpc_engine.py", "PI_EXECUTABLE=\"$(command -v pi)\" && AUTOWORK_TEST_PI=\"$PI_EXECUTABLE\" \"$PI_AUTOWORK_RPC_PYTHON\" pi-autowork/tests/test_installed_pi_rpc.py -v", "python3 scripts/affected_tests.py --run", "python3 pi-autowork/pi_autowork/command.py tasks validate --worktree ."]
exclusions = ["No custom Pi protocol, new task authority or remote service, automatic steering opt-in, scope expansion or reviewer influence."]
+++
- Source: docs/research/pi-rpc-qualification-2026-10-24.md
- This follow-up is pending; no acceptance, ownership release or installed activation is asserted.
- Delivery gate: Owner direction 2026-10-24: implement coordinator controls only after TOOLSET-389 records real installed-runner engine closure and interrupted-attempt recovery without duplicate dispatch. Source integration or synthetic smokes alone do not satisfy this gate. Automatic steering remains off.
- Check handoff: 2026-10-24 pipeline planning: docs/evaluation.md#delivery-pipeline-optimization and docs/pi-rpc.md#verification-and-rollback supply executing commands, replacing selection-only --json. Before this still-blocked task runs, use the already-qualified pinned SDK interpreter and installed Pi from TOOLSET-389; do not install/change a fleet runtime here. Extend these fixtures for the new controls acceptance, require SDK/native cases actually execute (skips do not satisfy acceptance), and record exact counts/receipts. Native fixture uses a deterministic offline provider, not real-model qualification. Existing 388/389 dependencies, delivery gate, automatic-steering-off policy, authority and closure remain unchanged; bound the production-channel write set from the qualified interface before admission.
