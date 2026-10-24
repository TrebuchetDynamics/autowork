+++
schema = 1
id = "TOOLSET-378-07c50be2"
title = "Native update implementations move into Src while keeping source integrity and restart recovery"
short = "Move updater implementations into Src"
status = "open"
goal = "CODE-HEALTH-2026-10"
section = "Next"
rank = 10000
depends_on = ["TOOLSET-368-24bdb225"]
touches = ["update_bundle.py", "update_bundle_native.py", "Src/autowork_runtime/update_bundle.py", "Src/autowork_runtime/update_bundle_native.py", "tests/test_update_bundle.py", "tests/test_update_quiet_restart.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Move only update_bundle.py and update_bundle_native.py bodies into Src/autowork_runtime with stable namespace-preserving root loaders. Keep selected-root peers, tracked-blob closure/modes, native subprocess/interpreter/path selection, restart waiter and rollback/lock/transaction behavior. Offline private fixtures only; installed integration remains NOT_CHECKED."
acceptance = ["Existing update and quiet-restart tests exercise moved bodies through original entrypoints with late-bound prepare/peer patches, source paths and unchanged arguments/interpreter/exit behavior.", "Two native releases do not share cached peers/resources; source_tree tracked blobs/modes cover the source payload, missing payload fails and no Git-archive/installed-code fallback bypasses source integrity.", "Restart/recovery/rollback/lock assertions remain meaningful and focused/affected tests pass; no live gateway restart, profile install or deployed acceptance is inferred."]
checks = ["python3 scripts/check.py tests/test_update_bundle.py tests/test_update_quiet_restart.py", "python3 scripts/affected_tests.py --run"]
exclusions = ["No behavior/schema/state/receipt/lock/authority changes, production source duplication, mixed-release fallback, extra approval system, unrelated refactor/test relocation, installs/profile edits, live services/models/jobs, publication or worker interruption. Preserve standalone hook copies."]
+++
- Sources: docs/plans/structural-audit-2026-10.md#native-updater-relocation
- Planner call: User explicitly added root Src/ (capital S), superseding only the old no-source-root-migration planner choice; preserve completed 355-359 and reuse existing IDs. SDD protocol 1be8e34187e34647bb83adc3a1323b26ae6f6abe, hash c4b97ce3d7f24be0e67fd612c7595f65504872e3a9f8d338d098b2363fdb66ef. Interfaces/behavior oracles specified before movement; no upstream human checkpoints. All implementation tests are proposed/unrun and in scope to create.
- Next action: Characterize the named compatibility seam before the move, implement this bounded source cut using the foundation, then run Checks on the actual base.
- Consumes: TOOLSET-368-24bdb225: loading/Layout/fixture contracts from accepted source section. No source/package mapping is requested from an external coordinator.
- Evidence: Refreshed against canonical 34aca3f6487eda7d0c45589cdd4c1b33cbe2d3fa and independent read-only current-source reviews; no implementation, product tests, installed-copy or live qualification in this occurrence.
- Planning scope: Owner selected both instruction fixes and Src refresh, instruction fixes first; this occurrence saves metadata only, not execution.
- Delivery: Saved planning; consumer inclusion/selection must be checked separately from implementation and dispatch.
