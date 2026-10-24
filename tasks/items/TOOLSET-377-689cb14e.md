+++
schema = 1
id = "TOOLSET-377-689cb14e"
title = "Native setup implementations move into Src with complete copied-source validation"
short = "Move setup and installers into Src"
status = "open"
goal = "CODE-HEALTH-2026-10"
section = "Next"
rank = 9000
depends_on = ["TOOLSET-368-24bdb225"]
touches = ["install_skills.py", "setup_bundle.py", "setup_preflight.py", "setup_runtime.py", "install-omh.py", "install-graphify.py", "Src/autowork_runtime/install_skills.py", "Src/autowork_runtime/setup_bundle.py", "Src/autowork_runtime/setup_preflight.py", "Src/autowork_runtime/setup_runtime.py", "Src/autowork_runtime/install_omh.py", "Src/autowork_runtime/install_graphify.py", "tests/test_complete_setup.py", "tests/test_install_skills.py", "tests/test_native_provisioning.py", "tests/test_setup_runtime.py", "tests/test_install_omh.py", "tests/test_install_graphify.py", "pi-autowork/engine/test_parallel_integrate.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Move exactly the six setup/install body pairs in the plan into Src/autowork_runtime, retaining old root filenames/main behavior. Use namespace-preserving execute and same-release peer loading. Update required-file/source closure validation and explicitly named copied fixtures, including the engine installer-only copy. Preserve installation targets/stages and do not run actual installers or profiles."
acceptance = ["Existing setup/provisioning/install tests execute real source bodies through old root entrypoints in private fixtures; collaborator patches, ROOT paths, hyphenated public filenames and exception/exit behavior remain compatible.", "Missing declared Src/bootstrap payload is rejected before writes; copied setup/installer fixtures include their same-release closure and never use installed/other-checkout fallbacks.", "No setup-stage, target-profile, dependency, permission or rollback policy expands; named offline suites and affected tests pass without live installation."]
checks = ["python3 scripts/check.py tests/test_complete_setup.py tests/test_install_skills.py tests/test_native_provisioning.py tests/test_setup_runtime.py tests/test_install_omh.py tests/test_install_graphify.py pi-autowork/engine/test_parallel_integrate.py", "python3 scripts/affected_tests.py --run"]
exclusions = ["No behavior/schema/state/receipt/lock/authority changes, production source duplication, mixed-release fallback, extra approval system, unrelated refactor/test relocation, installs/profile edits, live services/models/jobs, publication or worker interruption. Preserve standalone hook copies."]
+++
- Sources: docs/plans/structural-audit-2026-10.md#native-setup-and-installer-relocation
- Planner call: User explicitly added root Src/ (capital S), superseding only the old no-source-root-migration planner choice; preserve completed 355-359 and reuse existing IDs. SDD protocol 1be8e34187e34647bb83adc3a1323b26ae6f6abe, hash c4b97ce3d7f24be0e67fd612c7595f65504872e3a9f8d338d098b2363fdb66ef. Interfaces/behavior oracles specified before movement; no upstream human checkpoints. All implementation tests are proposed/unrun and in scope to create.
- Next action: Characterize the named compatibility seam before the move, implement this bounded source cut using the foundation, then run Checks on the actual base.
- Consumes: TOOLSET-368-24bdb225: loading/Layout/fixture contracts from accepted source section. No source/package mapping is requested from an external coordinator.
- Evidence: Refreshed against canonical 34aca3f6487eda7d0c45589cdd4c1b33cbe2d3fa and independent read-only current-source reviews; no implementation, product tests, installed-copy or live qualification in this occurrence.
- Planning scope: Owner selected both instruction fixes and Src refresh, instruction fixes first; this occurrence saves metadata only, not execution.
- Delivery: Saved planning; consumer inclusion/selection must be checked separately from implementation and dispatch.
