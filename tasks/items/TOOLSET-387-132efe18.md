+++
schema = 1
id = "TOOLSET-387-132efe18"
title = "Implement SDK-backed Pi RPC as the default with fenced process ownership"
short = "Default Pi RPC runtime"
status = "done"
goal = "EVALUATION"
section = "Now"
rank = 4000
depends_on = []
touches = ["README.md","pi-autowork/README.md","pi-autowork/pi_autowork","pi-autowork/tests","tests/test_pi_autowork.py","tests/test_pi_rpc_engine.py","tests/test_install_menu.py","scripts/install-pi-rpc.py","scripts/install_menu.py","pi-autowork/requirements-rpc.txt","docs/plans/2026-10-24-pi-rpc-default.md","docs/pi-rpc.md","docs/research/pi-rpc-qualification-2026-10-24.md","tasks/items"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Implement the owner-requested SDK-backed default RPC runtime in an isolated branch; retain explicit JSON rollback, existing model/review/engine authority, process cleanup proof, structured technical holds, bounded progress and controls. Reconcile Src relocation before landing; no modification of another live checkout or fleet restart. Live pilot remains separately evidenced."
acceptance = ["RPC is default through AsyncPiClient0.2.6/Pi1.4.0; JSON rollback explicit, read-only CLI remains usable without SDK; prompt expansion, independent sessions and bounded existing provider fallback preserved.", "Real process-tree cancellation and parent-death tests leave no owned live descendants and preserve unrelated processes; settlement, uncertain acceptance and overflow fail closed with no automatic replay.", "Events project while running with bounded private metadata; no raw transcript retention, unknown costs remain unknown; steering does not expand task or reviewer authority.", "Report exact offline/native/live evidence and limitations; no fleet activation or verified delivery claim without qualification."]
checks = ["python3 scripts/check.py pi-autowork/tests/test_pi_process.py pi-autowork/tests/test_pi_events.py pi-autowork/tests/test_pi_runtime.py pi-autowork/tests/test_recovery_runtime_failures.py pi-autowork/tests/test_pi_rpc_install.py pi-autowork/tests/test_blocker_triage.py","RPC_PYTHON=\"${PI_AUTOWORK_RPC_PYTHON:-${PI_AUTOWORK_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/pi-autowork}/runtimes/pi-rpc-0.2.6/bin/python}\"; \"$RPC_PYTHON\" scripts/check.py pi-autowork/tests/test_pi_rpc.py tests/test_pi_rpc_engine.py","RPC_PYTHON=\"${PI_AUTOWORK_RPC_PYTHON:-${PI_AUTOWORK_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/pi-autowork}/runtimes/pi-rpc-0.2.6/bin/python}\"; PI_EXECUTABLE=\"$(command -v \"${PI_BIN:-pi}\")\" && AUTOWORK_TEST_PI=\"$PI_EXECUTABLE\" \"$RPC_PYTHON\" pi-autowork/tests/test_installed_pi_rpc.py -v","python3 pi-autowork/pi_autowork/command.py tasks validate --worktree ."]
exclusions = ["No other live checkout edits, global Pi changes, production credential changes, service restarts, publication permission changes, second scheduler/database or SDK private APIs."]
closure = "manual"
closure_actor = "interactive Pi implementation"
closure_timestamp = "2026-10-24T07:55:47.091258+00:00"
closure_reason = "Bounded local RPC-default implementation, isolated SDK install, proportional tests, native qualification and disposable model smokes completed with independent bounded-slice review. Canonical integration, installed activation and production control-channel qualification remain separate open follow-ups. Manual local closure is not an engine verification receipt or publication."
closure_evidence = "docs/research/pi-rpc-qualification-2026-10-24.md"
+++
- Sources: docs/plans/2026-10-24-pi-rpc-default.md; docs/pi-rpc.md; docs/research/pi-rpc-qualification-2026-10-24.md
- Delivery scope: bounded local implementation and isolated SDK installation, not canonical integration, an engine verification receipt, publication or fleet activation.
- Follow-ups: TOOLSET-388-b422fa9e (canonical reconciliation/integration), TOOLSET-389-6dedfd8c (installed/live qualification), TOOLSET-390-e1c2afa6 (production coordinator control channel).
- Validation: requirements/docs cause affected selection to choose the whole inventory. Named affected modules, direct native opt-in checks and explicit live smokes were run instead; no whole-suite pass is claimed.
