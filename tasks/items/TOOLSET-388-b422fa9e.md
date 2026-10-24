+++
schema = 1
goal = "EVALUATION"
status = "open"
resources = []
id = "TOOLSET-388-b422fa9e"
title = "Reconcile and integrate the RPC default after canonical Src ownership settles"
short = "Land RPC on canonical runtime"
section = "Next"
rank = 5000
depends_on = ["TOOLSET-387-132efe18","TOOLSET-375-8e02693d","TOOLSET-369-b5db2d3a"]
touches = ["Src","pi-autowork","scripts","tests","docs"]
kind = "implementation"
ownership = "worker"
scope = "Re-resolve the canonical runtime after relocation/extraction, adapt the reviewed RPC implementation without duplicate implementation owners, rerun proportional checks and use the supported serialized integration path. Preserve live candidates and unrelated dirty files; a local branch is not an installed release."
acceptance = ["There is one canonical owner for the RPC/guard/projection/runtime code and entrypoints resolve to it after Src relocation.","Existing engine, SDK/native contract, cancellation/recovery and install checks pass on the reconciled source; task evidence names its exact revision.","Integration is serialized against current coordinator/workers and preserves the independent review/check/publication gates. No service restart or remote publication is inferred."]
checks = ["python3 scripts/affected_tests.py --json","python3 pi-autowork/pi_autowork/command.py tasks validate --worktree ."]
exclusions = ["Do not edit a live worker's checkout, bypass integration guards, repin failed evidence, publish or restart services."]
+++
- Source: docs/research/pi-rpc-qualification-2026-10-24.md
- This follow-up is pending; no acceptance, ownership release or installed activation is asserted.
- Pending live: TOOLSET-389-6dedfd8c: qualify one explicitly owned installed runner with interrupted-attempt recovery and real-model engine closure. Native offline fixtures are not installed-fleet acceptance; no activation or restart performed.
- Pending live: TOOLSET-390-e1c2afa6: production coordinator control-channel and automatic-intervention qualification remain separate; automatic steering was not enabled.
- Reopened: its landing broke the full check on main at 7e29570: test_task_prepare.PackageImportTests.test_every_module_imports_in_isolation_and_all_import_edges_are_acyclic; reverted by optimistic landing. Fix those tests in the next attempt
