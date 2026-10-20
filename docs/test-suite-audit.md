# Subprocess coverage and assertion audit (TOOLSET-073)

Audit only, 2026-10-16, source `de0f3ac8239d8aecbf38de0c113f60aa1757a50f`,
Linux, Python 3.12.14, coverage.py 7.13.5. The offline inventory grew since
TOOLSET-068: **1,491 tests** (562/709/212/8), not the old 1,253.
No source or test was changed by this audit.

## Method and limits

Used the [optimization protocol](../skills/engineering/local/test-suite-optimization/PROTOCOL.md):
a scratch startup hook calls `coverage.process_startup()` and switches context to
the calling unittest ID inherited through an environment variable. A scratch
`TextTestResult.startTest` switches the parent's context and exports that ID;
`stopTest` records duration and resets the context. Each offline directory gets
its own runner, with the same eight model/native/integration exclusions as
`scripts/check.py`. Branch measurement, parallel data and an absolute scratch
config/data path are enabled; source is the repository root, tests and vendored
upstream omitted. Children were verified to retain caller IDs on nested sources.
Combined all completed shards and exported JSON with contexts. Raw data stays in
scratch, not Git. No repository coverage dependency or plugin was added.

A root-only include glob in the first attempt omitted nested sources; that attempt
is retained but rejected. The corrected run recorded **1,278 of 1,491 contexts
(85.7%)**, exceeding the requested absolute minimum of 1,150. The **213 without
owned-source lines** are not redundant: text/package/shell-only checks, copied
fixture sources outside the measured root, scrubbed/isolated environments and
non-Python commands remain blind spots. Largest missing module counts: plugin
installation 29, OMH installation 28, behind-only shell realignment 26, skill
installation 10, check runner 9 and Pi runner 9. Coverage is not shell coverage.

Corrected aggregate: 64 owned Python files, **10,277/11,806 statements (87.05%)**,
**3,980/5,020 branches (79.28%)**, combined 84.73%. These are this revision's
instrumented results, not a comparison proving an improvement over TOOLSET-068.
Mutation score was not measured; no tool was installed.

The corrected instrumented run passed 562, 212 and 8-test directories. Autowork
ran 709 with one skip and one failure:
`test_check_receipt.ReceiptTests.test_runtime_reuses_inventory_without_sharing_mutable_receipt_values`
observed two scans, not one. Coverage shards were written into the startup-hook
folder on `sys.path`, changing a metadata-cache search root during measurement.
The exact test passed uninstrumented (0.333 s); after moving coverage output off
`sys.path`, it passed with instrumentation (0.854 s). The full instrumented run
was **not** rerun after that harness repair and is **not** reported as green.
The protocol now records both this trap and nested-source include validation.

The ordinary, uninstrumented `python3 scripts/check.py` subsequently passed all
four directories: 562/709/212/8 tests, one skip and eight excluded modules. This
separate normal gate does not retroactively make the instrumented attempt pass.

## Grouping and reading contract

Recomputed identical **nonempty covered-line sets** across tests; strict subsets
compare only siblings in the same class. Result: **89 identical groups / 252 test
IDs**, and **366 strict-subset tests**. Branches and assertions were not used as
identity keys. Read all **31 groups of at least three tests (136 IDs)** plus every
subset in the corrected run's 30 slowest tests and every listed superset.
Two read-only assertion reviews supplied exact-body/helper inspection; the
coordinator reconciled identifiers and reasons. Smaller groups and other subsets
remain unverified leads, not removal recommendations.

Classification: **26 distinct-contract groups**, **five case-preserving
parametrization candidates** (13, 18, 22, 27, 30), **zero removal candidates**.
All five slow subset cases are distinct contracts. Thin-wrapper consolidation has
no measured runtime benefit; do not queue it merely to shrink the test count.
Keep rules protect named regressions, safety/security, composed handoffs and
qualification. Inherited/called duplicate executions are identified explicitly
without waiving those protections.

## All identical groups of at least three

### G01 — distinct contract

- `test_owner_cron.OwnerCronTests.test_autonomous_prompt_has_no_external_owner_or_proposal_gate`
- `test_owner_cron.OwnerCronTests.test_delivery_batches_and_reports_are_in_generated_cron_prompt`
- `test_owner_cron.OwnerCronTests.test_direct_policy_migration_keeps_scope_and_exact_self_heal_binding`
- `test_owner_cron.OwnerCronTests.test_generated_prompt_preserves_caps_without_mandatory_native_allocation`
- `test_owner_cron.OwnerCronTests.test_idle_jobs_load_repository_maintenance_without_widening_task_only_scope`
- `test_owner_cron.OwnerCronTests.test_owner_prompt_retains_explicit_publication_authority_and_default_limits`
- `test_owner_cron.OwnerCronTests.test_owner_prompt_routes_to_one_shared_executable_cycle`
- `test_owner_cron.OwnerCronTests.test_owner_prompt_uses_direct_session_execution_without_card_prepasses`
- `test_owner_cron.OwnerCronTests.test_paused_prompt_cannot_resume_or_replace_writer`
- `test_owner_cron.OwnerCronTests.test_scheduled_execution_consumes_plans_and_approved_results`
- `test_owner_cron.OwnerCronTests.test_scoped_offline_isolation_permission_keeps_main_and_external_limits`

Independent generated-prompt assertions cover exact scope, publication, caps, pause, self-heal identity, direct execution, maintenance and review/qualification boundaries. Same generator does not make those strings interchangeable; retain all authorization regressions.

### G02 — distinct contract

- `test_finish_task.FinishTaskTests.test_worker_definition_requires_commit_before_review`
- `test_goal_handoff.HandoffTests.test_circular_entry_retries_once_without_waiving_review`
- `test_goal_handoff.HandoffTests.test_review_handoff_is_not_circular_completion_requirement`
- `test_goal_handoff.HandoffTests.test_worker_body_makes_completion_evidence_explicit`
- `test_goal_handoff.HandoffTests.test_worker_checks_changed_dependency_delivery_boundary`
- `test_goal_handoff.HandoffTests.test_worker_owns_debug_fix_test_review_without_intermediate_cards`
- `test_ponytail_handoff.PonytailHandoffTests.test_handoff_resolves_real_skills_and_reuses_the_existing_review_lane`
- `test_worker_role_contract.WorkerRoles.test_default_body_remains_worker_closure_and_no_publication`
- `test_worker_role_contract.WorkerRoles.test_worker_finishes_all_in_scope_consumers_before_review`
- `test_workflow_handoff.WorkflowHandoffTests.test_body_separates_card_and_product_delivery`

Worker-body assertions separately cover commit-before-review, circular-retry limits, exact contract retention, all consumers, packaging, method provenance and worker versus proposal/publication authority. Several also read reference documents; keep composed handoff contracts.

### G03 — distinct contract

- `test_collector_correctness.CorrectnessTests.test_failed_occurrence_without_task_evidence_stays_unknown`
- `test_collector_correctness.CorrectnessTests.test_finished_failed_occurrences_preserve_ids_without_stall_inference`
- `test_collector_correctness.CorrectnessTests.test_invalid_task_identity_stays_unknown`
- `test_collector_correctness.CorrectnessTests.test_new_worker_run_id_alone_does_not_establish_stagnation`
- `test_collector_correctness.CorrectnessTests.test_previously_observed_completed_run_is_not_counted_again`
- `test_collector_correctness.CorrectnessTests.test_stale_handoff_never_establishes_attributed_stagnation`
- `test_collector_correctness.CorrectnessTests.test_unknown_execution_gap_does_not_recount_same_run`

Histories differ: first failed occurrence, repeated finished IDs, numeric task ID, changing worker IDs, replay after gaps and stale handoffs. Preserve unknown attribution, historical counter/list immutability and no-auto-pause evidence; none proves all other transitions.

### G04 — distinct contract

- `test_task_execution.DirectExecutionTests.test_bounded_run_performs_useful_action_without_card_or_completion_claim`
- `test_task_execution.DirectExecutionTests.test_changed_source_does_not_create_reusable_passing_receipt`
- `test_task_execution.RecoveryTests.test_bounded_run_performs_useful_action_without_card_or_completion_claim`
- `test_task_execution.RecoveryTests.test_changed_source_does_not_create_reusable_passing_receipt`
- `test_task_execution.RecoveryTests.test_failed_command_is_not_task_completion`
- `test_task_execution.RecoveryTests.test_receipt_identifies_exact_command_and_is_not_acceptance`
- `test_task_execution.RecoveryTests.test_relative_path_executable_is_fingerprinted_at_child_cwd`

Two RecoveryTests methods inherit identical DirectExecutionTests bodies without a fixture override (bounded action and source mutation). This proves repeated execution, not permission to remove named execution/evidence safety cases. Failed-command, argv/nonacceptance and child-cwd executable assertions are distinct. Any hierarchy refactor must inventory every inherited case and preserve the safety contracts.

### G05 — distinct contract

- `test_check_receipt.ReceiptTests.test_runtime_inventory_invalidates_when_standard_finders_are_removed`
- `test_check_receipt.ReceiptTests.test_runtime_inventory_preserves_symlink_egg_alias_semantics`
- `test_check_receipt.ReceiptTests.test_runtime_inventory_tracks_case_insensitive_egg_metadata`
- `test_check_receipt.ReceiptTests.test_runtime_inventory_tracks_custom_distribution_providers`
- `test_check_receipt.ReceiptTests.test_runtime_reuses_interpreter_hash_until_file_replacement`
- `test_check_receipt.ReceiptTests.test_runtime_reuses_inventory_without_sharing_mutable_receipt_values`

Finder removal/restoration, symlink egg aliases, case-insensitive egg metadata, custom in-memory providers, executable replacement and caller mutation are different inventory/evidence invalidators. Keep every positive and negative cache assertion.

### G06 — distinct contract

- `test_owner_cycle.ComposedReadyTests.test_capability_does_not_block_observation_or_closeout`
- `test_owner_cycle.ComposedReadyTests.test_closeout_and_state_reconciliation_request_action_not_a_blocker`
- `test_owner_cycle.ComposedReadyTests.test_missing_native_cap_is_reported_without_dispatch_or_replenishment`
- `test_owner_cycle.ComposedReadyTests.test_observation_is_waiting_not_a_failed_cycle`
- `test_owner_cycle.ComposedReadyTests.test_prior_interrupted_or_review_card_precedes_selection`

Composed recovery tests distinguish missing capability from observation/closeout, WAITING versus ACTION_REQUIRED, pending original work and unchanged backlog/no new dispatch. Independent return-code and action assertions must remain.

### G07 — distinct contract

- `test_owner_cycle.OwnerCycleTests.test_ledger_input_change_resets_repetition`
- `test_owner_cycle.OwnerCycleTests.test_missing_ledger_requests_integration_instead_of_validate_loop`
- `test_owner_cycle.OwnerCycleTests.test_new_evidence_is_retained_without_duplicate_request`
- `test_owner_cycle.OwnerCycleTests.test_supplied_acknowledgement_is_distinct_from_request_creation`
- `test_owner_cycle.OwnerCycleTests.test_unchanged_blocker_reuses_request_and_changes_action`

Persisted integration request histories differ: initial missing ledger, input change resets repetition, appended evidence, explicit acknowledgement and repeated request reuse. Different transitions and journal counts; keep lifecycle/acknowledgement boundaries.

### G08 — distinct contract

- `test_pi_autowork.EngineTests.test_main_moving_meanwhile_is_merged_with_pi_resolving_conflicts`
- `test_pi_autowork.EngineTests.test_missing_credentials_at_run_time_fall_back`
- `test_pi_autowork.EngineTests.test_once_runs_one_task`
- `test_pi_autowork.EngineTests.test_pushes_are_blocked_in_workers`
- `test_pi_autowork.SetupTests.test_hermes_autowork_job_on_the_same_repository_needs_allow`

Real runner plus fake-Pi/local-Git scenarios prove concurrent-main merge, credential fallback, one-task limit, blocked worker push and same-repository cron admission. Equal Python lines omit shell/Git behavior; keep composed authority tests.

### G09 — distinct contract

- `test_update_bundle.UpdateTests.test_conflicting_local_edit_still_stops_the_update_without_writes`
- `test_update_bundle.UpdateTests.test_deliberate_deletion_from_the_release_is_not_silently_undone`
- `test_update_bundle.UpdateTests.test_edit_of_a_release_changed_line_stops_instead_of_guessing`
- `test_update_bundle.UpdateTests.test_equally_close_older_versions_are_ambiguous_not_a_coin_flip`
- `test_update_bundle.UpdateTests.test_history_does_not_match_other_paths_or_unreachable_branches`

Different release histories reproduce overlapping edits, deliberate deletion, changed-line edit, equally close old versions and untrusted path/branch merge bases. Every case proves refusal without overwriting local/profile bytes; Keep data-loss regressions.

### G10 — distinct contract

- `test_budget_controller.BudgetTests.test_final_effect_read_error_fails_qualification_without_erasing_evidence`
- `test_budget_controller.BudgetTests.test_final_snapshot_error_retains_normal_process_evidence`
- `test_budget_controller.BudgetTests.test_final_source_read_error_fails_qualification_without_erasing_evidence`
- `test_budget_controller.UnsynchronizedAdmissionTests.test_process_cleanup_receipt_survives_ledger_removal`

Final effect, source or ledger read failure must preserve normal process evidence while marking only the failed observation unknown; ledger-removal cleanup is separate. Existing helper already shares the full oracle. Retain qualification, durable cleanup and secret-omission assertions.

### G11 — distinct contract

- `test_finish_task.FinishTaskTests.test_acceptance_git_uses_requested_repository_and_its_real_index`
- `test_finish_task.FinishTaskTests.test_index_override_alone_does_not_hijack_acceptance_or_commit`
- `test_finish_task.FinishTaskTests.test_pass_commits_only_owned_files_and_reports_exact_sha`
- `test_finish_task.FinishTaskTests.test_wrapper_cannot_be_routed_to_foreign_repository`

Ordinary owned-only commit, full hostile Git selectors, index-only selector and acceptance-child isolation are distinct seams. Each preserves exact real index/HEAD/foreign bytes; retain authorization and data-preservation proof.

### G12 — distinct contract

- `test_goal_concurrency.ConcurrencyTests.test_linked_backlog_check_uses_local_inputs_without_native_config_lookup`
- `test_handoff_reconciliation.HandoffReconciliationTests.test_bold_task_ids_are_ready_without_changing_identifiers`
- `test_handoff_reconciliation.HandoffReconciliationTests.test_equivalent_plan_link_does_not_block_task`
- `test_handoff_reconciliation.HandoffReconciliationTests.test_generated_coverage_fields_are_not_part_of_task_contract`

Linked-worktree authority refuses native config redirection, whereas bold IDs, equivalent links and generated coverage test different Markdown exclusions. The real CLI helper snapshots files to prove read-only behavior; retain composed authority proof.

### G13 — parametrize candidate (preserve every case)

- `test_handoff_reconciliation.HandoffReconciliationTests.test_fenced_example_links_are_not_required_inputs`
- `test_handoff_reconciliation.HandoffReconciliationTests.test_fenced_fields_and_headings_do_not_end_the_real_task`
- `test_handoff_reconciliation.HandoffReconciliationTests.test_fenced_heading_does_not_steal_real_plan_anchor`
- `test_handoff_reconciliation.HandoffReconciliationTests.test_fenced_task_examples_are_not_executable_contracts`

Same CLI readiness/read-only oracle with fenced link, fields/headings, plan anchor and task examples. Six input scenarios including three delimiter variants could share a table/helper, but retain named wrappers, every row and full CLI assertions. Clarity only: no fewer executions or measured speed benefit.

### G14 — distinct contract

- `test_native_containment.SyntheticLaunchTests.test_cancellation_does_not_acknowledge_failed_exact_cleanup`
- `test_native_containment.SyntheticLaunchTests.test_empty_present_cgroup_never_acknowledges_cancellation`
- `test_native_containment.SyntheticLaunchTests.test_immediate_pre_release_cancellation_prevents_execution`
- `test_native_containment.SyntheticLaunchTests.test_lingering_host_pid_identity_prevents_acknowledgement`

Failed exact stop, empty-but-present cgroup, cancellation before release and lingering host PID identity are different cleanup conditions. Keep all containment/cancellation evidence and persisted receipt assertions.

### G15 — distinct contract

- `test_owner_cycle.OwnerCycleTests.test_failed_or_uncertain_handoff_persists_reconciliation_receipt`
- `test_owner_cycle.OwnerCycleTests.test_notification_error_without_recorded_card_is_not_success`
- `test_owner_cycle.OwnerCycleTests.test_notification_failure_preserves_successful_native_handoff`
- `test_owner_cycle.OwnerCycleTests.test_saved_native_handoff_is_used_for_ready_task`

Partial/timeout dispatch, notification failure without valid identity, failed notification after real handoff and saved request reuse prove opposite transport/identity outcomes. Keep composed recovery and no-fabricated-success boundaries.

### G16 — distinct contract

- `test_profile_consult.ConsultationTests.test_consultation_heavy_history_binds_original_without_transcripts`
- `test_profile_consult.ConsultationTests.test_contextual_quoted_keys_in_partial_evidence_are_redacted`
- `test_profile_consult.ConsultationTests.test_cookie_credentials_are_withheld_from_consultation_evidence`
- `test_profile_consult.ConsultationTests.test_read_is_anchored_to_latest_owner_reply_not_session_bookends`

Heavy history original-session binding, partial quoted credentials, cookie/header leakage and latest-owner message anchoring have distinct database/projection/secret oracles. Keep security, byte limits, idempotence and no-DB-mutation assertions.

### G17 — distinct contract

- `test_profile_consult.ConsultationTests.test_json_keys_and_contextual_credential_values_are_redacted`
- `test_profile_consult.ConsultationTests.test_quoted_assignment_credentials_are_redacted_in_full`
- `test_profile_consult.ConsultationTests.test_redaction_preserves_json_structure_for_plain_text_secrets`
- `test_profile_consult.ConsultationTests.test_unterminated_quoted_credentials_fail_closed`

JSON keys versus contextual values, escaped/multiline quoted assignments, plain text within valid JSON and unterminated quotes exercise different secret grammars. Existing matrices already preserve structure, safe fields and redaction idempotence; keep security regressions.

### G18 — parametrize candidate (preserve every case)

- `test_update_bundle.ScopedUpdateTests.test_malformed_historical_database_does_not_veto_deployment`
- `test_update_bundle.ScopedUpdateTests.test_mismatched_historical_run_does_not_veto_deployment`
- `test_update_bundle.ScopedUpdateTests.test_orphan_historical_run_does_not_veto_deployment`
- `test_update_bundle.ScopedUpdateTests.test_unknown_historical_owner_does_not_veto_deployment`

Four malformed/attribution board fixtures share assert_historical_state_ignored: no SQLite access, both-profile update, symlink replacement and database-byte preservation. A named fixture-builder table may improve readability, but retain corrupt DB, mismatched run, orphan run and unknown owner independently. No measured speed saving.

### G19 — distinct contract

- `test_budget_controller.BudgetTests.test_duplicate_race_records_deterministic_transaction_coordination`
- `test_budget_controller.BudgetTests.test_failed_race_evidence_survives_assertion_and_temp_cleanup`
- `test_budget_controller.BudgetTests.test_real_duplicate_process_race_has_one_fixture_effect`

One discovered race test literally calls another, but adds coordination, all-zero exit and source-identity assertions; the failure-artifact test uses an uncoordinated race and verifies durable cleanup. Keep process/evidence qualification, not deletion by line sets. A future helper refactor needs separate measured acceptance.

### G20 — distinct contract

- `test_check_receipt.ReceiptTests.test_receipts_without_execution_directory_resolution_policy_are_not_reused`
- `test_check_receipt.ReceiptTests.test_reuse_requires_same_source_dependencies_environment_and_command`
- `test_check_receipt.ReceiptTests.test_terminal_metadata_is_removed_from_execution_and_reuse_identity`

Receipt schema compatibility, bound artifact/environment/command/interpreter drift, and scrubbing incidental terminal metadata have different positive/negative reuse expectations. Keep execution/evidence qualification.

### G21 — distinct contract

- `test_disjoint_triage.DisjointTriageTests.test_scheduled_backoff_blocks_only_its_own_slice`
- `test_disjoint_triage.DisjointTriageTests.test_triage_blocks_only_its_own_slice`
- `test_goal_handoff.HandoffTests.test_blocked_same_title_survives_contract_wording_changes`

Scheduled backoff, terminal triage and blocked same-title wording differ in state and workspace-presence semantics. Named disjoint-triage regression and scope/ownership boundaries remain; do not merge away cases across modules.

### G22 — parametrize candidate (preserve every case)

- `test_doctor_modes.DoctorModes.test_complete_full_install_passes`
- `test_doctor_modes.DoctorModes.test_core_succeeds_with_visible_external_gaps`
- `test_doctor_modes.DoctorModes.test_default_full_check_fails_on_external_gaps`

Three fixture/CLI/expected-field rows could share a table: complete full readiness, core-only success with visible missing integrations, and full failure despite ready core. Preserve inventory-once and asymmetric JSON field assertions, not just exit codes. Clarity only, not live installation proof.

### G23 — distinct contract

- `test_finish_task.FinishTaskTests.test_broad_path_refused_without_commit`
- `test_finish_task.FinishTaskTests.test_literal_pathspec_cannot_capture_foreign_files`
- `test_finish_task.FinishTaskTests.test_missing_untracked_filename_is_not_a_noop`

Broad dot, Git pathspec magic and missing untracked filename fail for different unsafe inputs; each must avoid branch creation and preserve real index/HEAD/foreign bytes. Keep authorization/data-preservation tests.

### G24 — distinct contract

- `test_finish_task.FinishTaskTests.test_checked_out_task_ref_is_not_moved`
- `test_finish_task.FinishTaskTests.test_commit_failure_keeps_task_incomplete_and_preserves_index`
- `test_finish_task.FinishTaskTests.test_requested_repository_reference_hook_is_still_enforced`

Checked-out target ref, obstructed branch namespace and requested-repository reference hook fail at different reference seams. Keep hook enforcement, no fabricated commit, unchanged refs and exact index/foreign snapshots.

### G25 — distinct contract

- `test_isolated_origin_clone.IsolatedOriginCloneTests.test_foreign_shallow_selector_cannot_truncate_history`
- `test_isolated_origin_clone.IsolatedOriginCloneTests.test_inherited_repository_selectors_do_not_redirect_clone`
- `test_isolated_origin_clone.IsolatedOriginCloneTests.test_shallow_reference_failure_is_avoided_without_borrowed_objects`

Foreign shallow selector, combined repository/object/index selectors and reproduced shallow-reference clone failure exercise Git behavior not visible in Python line equality. Keep history, fsck, no-alternates and foreign-byte isolation regressions.

### G26 — distinct contract

- `test_parallel_e2e.StatusTests.test_empty_status_does_not_claim_or_create_runtime_state`
- `test_pi_autowork.EngineTests.test_status_and_dry_run_change_nothing`
- `test_pi_autowork.SetupTests.test_the_pi_installed_package_wins_over_the_scripts_checkout`

Engine empty status, shell status/dry-run and installed-package discovery have different entrypoints and side effects. Keep zero runtime-state creation, unchanged porcelain/no model calls and installed package precedence.

### G27 — parametrize candidate (preserve every case)

- `test_parallel_integrate.IntegrationTests.test_branch_cleanup_failure_is_retryable_after_worktree_removal`
- `test_parallel_integrate.IntegrationTests.test_legacy_archive_cleanup_retry`
- `test_parallel_integrate.IntegrationTests.test_worktree_cleanup_failure_is_retryable_without_reclosing`

Three thin wrappers inject worktree removal, branch deletion and legacy lowercase archive cleanup failures. A table could preserve fresh Git fixture per row, closed-once journal, retry without reclosure, archive bytes and worktree/branch removal. Keep all composed recovery cases; no speed benefit established.

### G28 — distinct contract

- `test_ponytail_handoff.PonytailHandoffTests.test_worker_and_proposal_handoffs_carry_the_simplification_method`
- `test_worker_role_contract.WorkerRoles.test_caller_limits_survive_worker_and_proposal_payloads`
- `test_worker_role_contract.WorkerRoles.test_shared_worker_instructions_fit_a_bounded_context_budget`

Method provenance, exact caller stop/budget contract and bounded instruction word overhead are independent predicates. Keep both worker/proposal payload checks and no authority transfer.

### G29 — distinct contract

- `test_reconcile.ReconcileTests.test_ended_review_failure_needs_recovery_not_endless_observation`
- `test_reconcile.ReconcileTests.test_terminal_run_behind_queued_card_requires_reconciliation`
- `test_reconcile.ReconcileTests.test_terminal_run_on_running_card_requires_state_reconciliation`

Ended review, queued terminal run and terminal run on running card use different sparse/bound status/outcome matrices; some require matching run status/not-delivered. Existing subtests already enumerate cases. Keep reconciliation regressions rather than a giant table.

### G30 — parametrize candidate (preserve every case)

- `test_update_bundle.ScopedUpdateTests.test_blocked_historical_card_does_not_veto_deployment`
- `test_update_bundle.ScopedUpdateTests.test_done_historical_card_does_not_veto_deployment`
- `test_update_bundle.ScopedUpdateTests.test_paused_historical_card_does_not_veto_deployment`

Blocked, done and paused historical board statuses share the same no-database-access/update/preservation oracle. A named three-row table is a clarity candidate with independent fixtures; retain every status. Ignoring historical cards does not permit modifying paused schedules.

### G31 — distinct contract

- `test_workflow_cycle.CycleGuidanceTests.test_same_task_recovery_and_independent_fallback_keep_real_holds`
- `test_workflow_cycle.CycleGuidanceTests.test_short_worker_body_omits_routing_and_gates_direct_closure_on_review`
- `test_workflow_cycle.CycleGuidanceTests.test_workers_receive_optional_methods_without_delegating_workflow_authority`

Recovery reference/source alignment, review-before-closure instruction ordering and optional-method authority are independent contracts across documents and role payloads. Keep exact content, order and bounded-body assertions.

## Strict subsets among the 30 slowest instrumented tests

Times below include coverage and concurrent-directory contention; they are not
normal-suite baselines or speedup evidence. Every listed superset body was read.

### S1 — distinct contract

`test_pi_autowork.EngineTests.test_empty_queue_calls_no_model` — 19.433 s instrumented.

Candidate line supersets:
- `test_pi_autowork.EngineTests.test_a_waiting_runner_sees_tasks_committed_to_main_later`
- `test_pi_autowork.EngineTests.test_interrupt_and_resume`

The empty-queue case drains existing work, clears the fake-model log, then requires Queue empty and zero subsequent calls. Waiting-for-new-main and interruption/resume tests do not assert no calls after exhaustion. Keep this negative no-model contract. A fixture-only speed-up may prepare equivalent completed session state without the initial full workflow; it must preserve the state shape and all empty-rerun oracles.

### S2 — distinct contract

`test_pi_autowork.EngineTests.test_independent_tasks_run_in_parallel_and_merge_verified_into_main` — 17.055 s instrumented.

Candidate line supersets:
- `test_pi_autowork.EngineTests.test_a_task_integrates_while_another_worker_is_still_running`
- `test_pi_autowork.EngineTests.test_a_waiting_runner_sees_tasks_committed_to_main_later`
- `test_pi_autowork.EngineTests.test_an_unboundable_task_runs_alone_and_is_not_asked_again`
- `test_pi_autowork.EngineTests.test_answers_from_an_older_prompt_do_not_hold_a_task`
- `test_pi_autowork.EngineTests.test_empty_queue_calls_no_model`
- `test_pi_autowork.EngineTests.test_interrupt_and_resume`
- `test_pi_autowork.EngineTests.test_tasks_without_touches_get_proposed_ones_and_run_in_parallel`
- `test_pi_autowork.EngineTests.test_user_changes_in_main_block_only_the_final_merge`

This positive composed case uses a barrier proving overlapping workers, then checks exact-once worker/reviewer sets, three isolated cwd values, provider/model/no-approve/reviewer tool limits, clean merged main, all task contents and archived done records. Scope inference also uses a barrier but lacks that identity matrix; the other supersets prove different scheduling, pause/resume or preservation seams. None replaces the full oracle.

### S3 — distinct contract

`test_pi_autowork.EngineTests.test_other_stale_worktree_registrations_survive_a_session` — 16.832 s instrumented.

Candidate line supersets:
- `test_pi_autowork.EngineTests.test_a_task_integrates_while_another_worker_is_still_running`
- `test_pi_autowork.EngineTests.test_a_waiting_runner_sees_tasks_committed_to_main_later`
- `test_pi_autowork.EngineTests.test_an_unboundable_task_runs_alone_and_is_not_asked_again`
- `test_pi_autowork.EngineTests.test_answers_from_an_older_prompt_do_not_hold_a_task`
- `test_pi_autowork.EngineTests.test_empty_queue_calls_no_model`
- `test_pi_autowork.EngineTests.test_interrupt_and_resume`
- `test_pi_autowork.EngineTests.test_tasks_without_touches_get_proposed_ones_and_run_in_parallel`
- `test_pi_autowork.EngineTests.test_user_changes_in_main_block_only_the_final_merge`

This creates an unrelated stale worktree registration and asserts it survives an otherwise successful session. None of the supersets creates or checks that unrelated registration. A clean-branches assertion in a different fixture cannot prove selective cleanup; Keep data-preservation case.

### S4 — distinct contract

`test_pi_autowork.EngineTests.test_a_missing_session_worktree_is_restored_without_pruning_others` — 13.790 s instrumented.

Candidate line supersets:
- `test_pi_autowork.EngineTests.test_user_changes_in_main_block_only_the_final_merge`

This first creates a merge-pending session, then deletes its own worktree directory while preserving an unrelated stale registration; retry must restore/merge its saved branch and remove only its own registration. Dirty-main recovery does not delete/restore a session directory or test selective pruning; keep both.

### S5 — distinct contract

`test_budget_controller.BudgetTests.test_zero_unit_fixture_ledger_has_bounded_identity_capacity` — 9.843 s instrumented.

Candidate line supersets:
- `test_budget_controller.BudgetTests.test_held_transaction_distinguishes_lock_refusal_from_permanent_duplicate`

This fills a zero-rate, cap-zero ledger to MAX_REQUESTS (bounded integer 1..256), rejects the next identity and preserves duplicate behavior/callback count. The superset holds a SQLite transaction with positive-cost reservation 19 of cap 30 and distinguishes lock/duplicate/changed-identity/unit capacity. It never exercises zero-cost identity exhaustion; Keep resource-bound safety case.

## Bounded follow-up

Prefer fixture cost over assertion consolidation. The exact empty-queue Pi test
passed three ordinary, uninstrumented runs in **5.158 / 5.003 / 5.187 s wall**
(median **5.158 s**; unittest body 5.116 / 4.965 / 5.148 s). Its 19.433 s
instrumented duration is not the baseline. Record one successor to replace its
full A/B/C warm-up with equivalent completed-session setup, retaining the named
regression, zero subsequent fake-model calls, output, isolation and stale-state
semantics. Require same-machine before/after timing, unchanged touched line/branch
coverage, focused and full normal checks. No speedup is claimed until executed.
No deletion or wrapper-only consolidation task is justified by this audit.

## Completed-session fixture result (TOOLSET-102-ea)

Measured on the same machine with Python 3.12.14 and coverage.py 7.13.5,
starting at `7024f6a`. The named empty-queue test now builds a fresh completed
A/B/C repository and archive, closed worker slots, the released coordinator's
journal and a detached engine integration worktree containing stale open tasks.
No old session file or live lease is seeded. Historical worker reports and Pi
usage logs are not consulted by this uncapped empty rerun and are not reproduced.
The unchanged sibling parallel-and-merge test retains the actual worker/reviewer,
dependency, merge and archival journey. No test or original assertion was removed.
The changed test also checks real `--status` before dispatch: successful exit and
`0 running; 3 done`. This caught a review gap where a malformed historical claim
could otherwise be masked by the next runner's valid claim.

- Ordinary focused wall times before: **5.497 / 5.390 / 5.287 s**, median
  **5.390 s**. After: **0.730 / 0.709 / 0.703 s**, median **0.709 s**:
  **86.8% lower**, or **7.60 times faster** for this test, not the whole suite.
- Same-config subprocess-attributed coverage runs select the exact changed test
  **and** `test_independent_tasks_run_in_parallel_and_merge_verified_into_main`.
  The pair covers **1,536 owned Python lines / 403 branch arcs before and after**,
  with no previously executed line or arc lost in any file. Caller test IDs are
  inherited by children through a scratch startup hook. This is the pair's union,
  not a claim that the empty test alone still executes worker/reviewer setup.
  Shell/Git commands, sanitized environments and hard-killed children remain
  coverage blind spots. Raw shards/configs/logs remain private scratch artifacts.
- Final normal module: `python3 -m unittest discover -s tests -p
  test_pi_autowork.py`: **40 tests passed**. Final `python3 scripts/check.py`:
  **562/712/212/8 tests passed**, one skip and eight native/model/integration
  modules excluded. Independent review approved after the journal correction.
- Retained failed attempts: an initial focused module-name invocation failed to
  import the non-package `tests` directory; corrected to unittest discovery.
  An instrumented whole-module attempt exceeded the tool's 420-second window and
  did not finish; it is not a passing full-coverage run. Initial synthetic slots
  omitted required metadata and failed before correction. The first paired
  candidate lost the historical coordinator-release branch; seeding the consumed
  journal restored it, then review required a complete historical claim payload.
- Mutation score **not measured**; no dependency or mutation tool was added.
  Offline fixture evidence does not qualify a live model, fleet run or delivery.


## Suite thinning plan (2026-10-16)

Status: Accepted

Intent: the owner's Plan For Me request, "minimize and thin all tests suite",
authorizes this planning pass and the supported design choices below, not test
edits, dispatch, commits or live execution in this pass. Reuse TOOLSET-124-97 as
the one open audit. Reduce unnecessary test executions, fixture weight and
wording-coupled maintenance while preserving defect detection. No arbitrary test
count, percentage reduction or latency SLA is imposed.

Scope: all owned offline Python tests in the five directories maintained by
[scripts/check.py](../scripts/check.py), the JavaScript adapter tests in
[CI](../.github/workflows/test.yml), and a static inventory of the eight excluded
native/model/integration suites. Vendored upstream tests and live qualification
are outside executable cleanup scope. This plan does not remove exclusions or
launch profiles, models, services or paid tools.

Acceptance: each removal maps to retained behavior or a documented non-executable
obligation; unique branches, named regressions, authorization, privacy, data-loss
and composed integration boundaries remain covered. Reduced test lines or counts
alone do not satisfy acceptance. The final normal Python and JavaScript checks
must pass; failures and timeouts stay visible. Preserve distinct case labels when
consolidating tables and use fresh mutable fixtures. No test-only production hook,
weakened assertion, hidden skip, or timeout increase to manufacture success.

### Current evidence and limits

Inspected HEAD `bbfffe2893a2832038628a3635393d50559765e1` plus the existing uncommitted
installer edits on 2026-10-16. Static AST inventory used `discover_tests()` from
`scripts/check.py` without importing the suite: **126 offline Python modules,
30,176 lines, 1,723 declared test methods**. These are neither collected execution
counts nor a passing runtime baseline; subtests and inherited methods differ.
The largest files are `tests/test_pi_autowork.py` (1,502 lines),
`skills/autowork/scripts/test_parallel_integrate.py` (1,424), and
`tests/test_update_bundle.py` (1,143). Splitting them without reducing repeated
work or improving responsibility ownership is not a success criterion.

The earlier installer check on `9fb32e8` plus that task's changes timed out in
`tests/` at 600 seconds; the other groups passed 815/217/9/46 tests (one skip,
eight excluded modules). The run also emitted unreaped-process/unclosed-stream
warnings. This was a shared-host, nonpassing run, not an idle baseline, not proof
of a test defect, and not evidence that this plan made anything faster. Raw logs
remain outside Git. Do not repeat three full runs just to plan this qualitative
cleanup. Establish focused before/after evidence for the changed batch; comparable
repeated passing runs are required if later reporting a performance percentage.

The earlier TOOLSET-073 audit remains historical evidence: its same-line coverage
groups mostly represented distinct assertions, and it approved no removals.
Re-read current bodies before acting; equal coverage alone still proves nothing.

### Selected approach and alternatives

Choose small behavior-owned batches, beginning with proven repeated execution,
then prose-only assertions and costly fixture orchestration. Preserve standard
unittest and Node test tooling. Each batch identifies its public seam and the
negative change its remaining assertion detects.

Rejected: delete by coverage similarity or a count target (loses distinct contracts);
rewrite the whole suite or switch framework (adds migration risk); split every
large file (does not reduce work); globally mock subprocesses/time (loses the
process and Git boundaries); weaken the default gate or simply raise its timeout
(hides the observed problem). Sharing immutable fixture inputs is allowed;
sharing mutable repositories, environment or process state across tests is not.

### Evidence-backed batches

| Batch | Evidence and change | Boundary to preserve |
| --- | --- | --- |
| Inherited execution | `RecoveryTests(DirectExecutionTests)` has no fixture override. Narrow unittest collection confirms 11 parent cases plus 36 child cases, including the same 11 methods. Use a fixture-only base/helper: 36 unique executions remain. | All 11 original named parent regressions and all 25 unique recovery cases, with equivalent setup/actions/assertions. |
| Prose assertions | `tests/test_blockers.py` has six contract methods that search prose plus two actual routing tests. Review each phrase's obligation; remove pure wording checks and retain machine-consumed metadata, paths and behavior. | BlockersRouting, helper execution from an installed archive, command dispatch, required index compatibility, and real authorization/security checks. No blanket deletion of the six methods. |
| Pi fixture cost | Service pause and stalled-notice tests wait three/four seconds after observing the event; idle adoption warms a full queue then sleeps two seconds. Component tests now exist alongside the 1,502-line legacy journey file. | Observable later-cycle proof, real process ownership/cancellation, push refusal, Git integration and safe update/restart journeys. A shorter sleep is not equivalent proof. |
| Remaining suite | Update/history, parallel integration, receipt and document suites dominate remaining size. Earlier audit groups identify leads, not approved deletion lists. | Inventory every module under the existing audit and keep distinct refusal, recovery, parsing and data-preservation cases. Queue another change only when its value is demonstrated. |

The inherited-repeat mapping is exact: each removed
`RecoveryTests.test_*` maps to `DirectExecutionTests` with the same method name:

- `test_todo_only_default_needs_no_profile_board_or_registration`
- `test_default_import_does_not_load_native_pipeline`
- `test_bounded_run_performs_useful_action_without_card_or_completion_claim`
- `test_named_task_dependencies_and_decision_hold_are_respected`
- `test_claiming_a_task_removes_finished_worktrees_and_keeps_unfinished_ones`
- `test_live_ancestor_claim_persists_across_calls_and_releases`
- `test_invalid_owner_never_claims`
- `test_running_direct_command_blocks_other_profile_and_worktree`
- `test_changed_source_does_not_create_reusable_passing_receipt`
- `test_timeout_budget_cannot_be_refilled_by_next_tick`
- `test_ordinary_apply_without_owner_does_not_fake_dispatch`

For freshness, the reviewed `test_task_execution.py` SHA-256 is
`3649f1091baf82f350e47c353079c6e14531de5f0c5ca169ae4c057a64e8b1ba`;
`tests/test_pi_autowork.py` is
`aeeda1e797e23ba0637d3a4f26b9c8ab3ba2bb4d401610d6acbc951cedc76d28`.
Changed fixtures or inherited helpers invalidate that equivalence conclusion.

### Execution and verification

Keep existing Now tasks and their owners. Extend the first TEST-SUITE task in Next,
TOOLSET-124-97, to create a per-module keep/thin/investigate map over the whole
inventory. Do not redo the historical audit or complete it from this static pass.
The inheritance batch already has sufficient structural evidence; the prose and
Pi batches depend on the audit's precise disposition and focused measurements.
Apply one bounded batch, inspect the diff, run its focused checks, and run the
normal gate once before that batch's commit. Reuse a passing gate only when all
bound inputs match. Do not rerun the whole suite after each prose edit.

Use focused line/branch coverage for changed runtime seams when needed to establish
equivalence, with subprocess contexts and the prior audit's blind spots recorded.
No repository coverage or mutation dependency is added. Mutation testing remains
optional and unmeasured unless a suitable tool is already available. Plain-text
instruction checks are not coverage evidence of agent compliance.

Final guards: `python3 scripts/check.py`, `node --test tests/portable_pi.test.mjs`,
and `git diff --check`. A before-run failure is retained as a blocker to a claimed
passing final gate, not addressed by deleting its test. The completed report must
account for collected executions, unique cases, fixture/code size and actual
commands/results, with remaining uncertainty explicit. No implementation, timing
improvement, full-suite pass or live qualification is claimed by saving this plan.

### Task order

| Task | Outcome | Dependencies |
| --- | --- | --- |
| TOOLSET-124-97 | Whole-suite disposition and bounded candidate evidence | None |
| TOOLSET-125-e6 | Run inherited execution regressions once | None; existing exact-duplicate evidence |
| TOOLSET-126-6b | Trim prose-only test assertions while retaining executable contracts | TOOLSET-124-97 |
| TOOLSET-127-b1 | Thin repeated Pi lifecycle fixtures and fixed waits | TOOLSET-124-97 |
| TOOLSET-128-69 | Qualify suite thinning and reconcile the test budget | TOOLSET-125-e6,TOOLSET-126-6b,TOOLSET-127-b1 |

## Whole-suite disposition (TOOLSET-124-97, 2026-10-17)

### Scope, method and decision

Audit source: `2ef55487d3dcb56e0bf3c8782fb83dbe279c6cd3`; Linux x86_64,
Python 3.12.14, Node 26.7.0, shared runner host, not certified idle. This is a
qualitative audit, not implementation or qualification of the thinning batches.
No tests, runtime, dependencies, exclusions or timeouts changed. TOOLSET-073 and
TOOLSET-102-ea above remain historical, source-bound results, byte-preserved.

Docs/source map: the shared test budget and optimization protocol own the method;
`scripts/check.py:13-54` owns discovery/exclusions; `.github/workflows/test.yml:12-21`
owns the Python/JavaScript CI gates. No codebase map or codebase-memory tool was
available; discovery used live files, ASTs and `rg`. Prior attempt `4146c5b`
provided a source/assertion review at `0baf36b`; this retry rechecked inventory,
candidates and the six changed test modules, including an independent read-only
review of their changed detectors. It does not treat the old inventory as current.

Method: import only the checker, call `discover_tests(Path.cwd())`, parse every
returned file with `ast.parse`, count `splitlines()` and declared
`FunctionDef`/`AsyncFunctionDef` names starting `test_`. Inspect bases, fixtures,
assertions/helpers, embedded child scripts and sleeps. A method-body AST comparison
ignoring locations/names finds **no identical declared-body pairs**; it cannot
establish semantic equivalence or detect inherited/called repetition. Collect only
the inherited-execution candidate with unittest separately. Excluded suites are
parsed/read only, never imported. Tracked `tests/fixtures/legacy_owner_cycle.py`
and `pi-autowork/tests/tui_pilot.py` are fixture/helper inputs, not omitted suites.
Vendored upstream tests are outside owned executable scope.

| Current offline directory | Modules | Lines | Declared test methods |
| --- | ---: | ---: | ---: |
| `tests` | 50 | 10,770 | 653 |
| `skills/autowork/scripts` | 53 | 15,052 | 815 |
| `skills/docs-sync/scripts` | 15 | 3,681 | 217 |
| `skills/git-commit-push/scripts` | 1 | 102 | 9 |
| `pi-autowork/tests` | 7 | 944 | 50 |
| **Total** | **126** | **30,549** | **1,744** |

JavaScript: **one file, 109 lines, three top-level `test()` cases** with many
command/selector inputs. Excluded: **eight files, 72 declared methods** plus
standalone assertion scripts. These are not whole-suite collected execution or
unique behavior counts, passing-gate evidence or timings. The accepted plan's
30,176 lines / 1,723 declarations and first attempt's 30,308 / 1,729 are historical.
The three files over 1,000 lines are Pi runner **1,617**, parallel integration
**1,507**, and bundle update **1,143**. Six changed modules add fifteen declarations
since the first attempt; no reduction or speedup follows from those counts.

**Decision (Judgment):** prioritize TOOLSET-125-e6's proven inherited repeats,
then TOOLSET-127-b1's bounded fixture/cycle work. TOOLSET-126-6b can independently
thin editorial predicates, but has little demonstrated latency payoff. Keep other
detectors pending stronger evidence. No new task is justified by size, mocks,
shared helpers, missing failure history or equal historical coverage. The existing
implementation tasks remain the owners; task/index reconciliation is coordinator-owned.

The earlier **600-second timeout remains nonpassing**, including process/stream
warnings, not an idle baseline. `scripts/check.py:88` now defaults to 1,800 seconds;
that separately shipped change does not retroactively pass the old run. No full
Python gate is run here. Repeated comparable passing full runs are required for a
quantitative suite-speedup claim, not this qualitative disposition.

Retry evidence: the prior integration verifier exited 0, but its receipt outcome
was **CHILDREN_TERMINATED**, `reusable_acceptance: false`, with one terminated
descendant and unchanged recorded TODO/index inputs. Its log was empty. Neither a
passing integration nor a particular failing test/tree mutation is established;
the descendant's origin is unknown. This audit does not waive that guard, repair
runner code or rerun integration in another worktree. The coordinator must obtain
fresh valid integration evidence after the worker commit.

### Findings and candidate-specific before evidence

#### F1 — exact inherited executions (Fact; Low; ready to thin)

`skills/autowork/scripts/test_task_execution.py:15-46,132-141` defines
`RecoveryTests(DirectExecutionTests)` without overriding `setUp` or `call`.
Fresh `TestLoader.getTestCaseNames` collection and object-identity checks prove
**11 parent + 37 child = 48 executions / 37 unique methods**: eleven parent and
**26**, not 25, unique recovery cases. Each duplicate is the identical parent
method object. The eleven-name mapping in the accepted plan remains exact:
remove only each second `RecoveryTests.<name>` execution and retain the matching
`DirectExecutionTests.<name>` with all setup/actions/assertions. This removes no
unique safety regression.

The added `test_a_git_timeout_under_load_answers_busy_not_action_required`
(`:177-199`) covers both entrypoints' BUSY classification, safe diagnostics and a
non-timeout negative control. Keep it. **TOOLSET-125-e6 needs coordinator count
reconciliation from 47 → 36 to 48 → 37, retaining 26 unique recovery methods**;
never delete it to force an obsolete target.

Fresh before command: `python3 -m unittest discover -s skills/autowork/scripts -p
test_task_execution.py`: **48 passed**, unittest **16.639 s**, external wall
**45.644 s**, one run. Wall includes startup/exit; its discrepancy with unittest's
interval was not profiled. It is not an idle median or a suite-speedup forecast.
Structural identity justifies the fixture-only base/helper proposal; application
still requires same-machine focused before/after timing and unchanged retained
line/branch seams. No new coverage or replacement implementation is claimed here.

Current candidate SHA-256 (accepted-plan hashes stay historical):

| File | SHA-256 |
| --- | --- |
| `skills/autowork/scripts/test_task_execution.py` | `2d0eeb916f6ce406fb788b56d3af68e6dbae2811145e224df2825f47af661dd2` |
| `tests/test_pi_autowork.py` | `f383060b47ea5a5db74180a70919f579dada6992e5162b56ae39ea37771b8177` |
| `tests/test_blockers.py` | `1790f7cbec5017dd923aa34ecb4c81ad83f1ed7287c444f51f7e6811de9e7bda` |
| `tests/portable_pi.test.mjs` | `e8b297e909775257624e0a35bf0386bb6c4c2626bb4a02277007c2c157bdcb29` |

#### F2 — prose locks versus real seams (Fact; Low; assertion-level thinning)

TOOLSET-126-6b must classify individual predicates, not delete mixed modules:

| Exact location / candidate | Disposition and surviving detector/obligation |
| --- | --- |
| `tests/test_blockers.py:24-69`, six `BlockersContract` methods | Five pure prose methods check filtering/clarification, replanning, ordering, model-free reading and planning-only authority. `test_every_entry_point_is_the_same_command` mixes spellings, links and a Pi implementation substring. Thin editorial wording, not machine-readable question markers or authorization obligations by default. |
| `tests/test_blockers.py:78-93`, two `BlockersRouting` methods | Keep the named wrong-skill incident: five spellings load Blockers with the literal target; incidental “blockers” text must not hijack another workflow. Link/path closure remains in workflow/package tests. |
| `tests/test_skill_descriptions.py:20-26` | Terminal punctuation at :26 is editorial. Retain parseable frontmatter, nonempty string and ≤60-character index compatibility; no whole-method deletion. |
| `tests/test_workflow_commands.py:29,109-113` | Central-queue sentence is editorial. Retain aliases, literal arguments, origin, collisions, installed source and namespace. The negative sentence at :113 proxies foreign-namespace isolation: retain an observable augmentation-boundary oracle before dropping that obligation. |
| `tests/test_portable_package.py:39,68-72,89` | “native tools”, heading host names and “questions-only” are wording leads. Keep resource selection, references, no-install-hooks, version alignment, explicit-only authorization metadata and nonrecursive planning topology. Forbidden helper names at :37-38 express host isolation, not mere style. |
| `tests/test_workflow_contract.py:16-79` | Keep all three: real reference resolution, unsupported install-path lint and copied-install helper execution with spaces. Actual generated-command ledger mutations are not redundant with file existence. |
| `tests/portable_pi.test.mjs:15,19,26,42` | Human titles/“host contract” matches are wording leads inside an executed adapter. Investigate stable resource-identity oracles while retaining selector/mode identity, literal bytes, idle/follow-up delivery and all three journeys. |

A document mentioning a rule is not proof of model compliance. Blockers' no-push,
no-runner-management, paused-job, scope and planning-only obligations cannot simply
vanish with their phrase checks. Router/metadata tests detect wrong selection or
implicit invocation, **not** a model choosing to push, edit a marked block or restart
a service. Preserve an assertion-to-obligation record when thinning.

Proposed bounded evaluation, **unrun**: in a disposable repository/isolated host,
present routine repair, one genuinely missing decision, unequal-effort blockers and
separately requested publication. Observe actual tool calls/artifacts: no runner,
process, schedule or push mutation; at most one ordered genuine question; literal
target and authorized planning-only edits. This is a non-executable obligation for
this audit, not an always-on paid dependency or replacement for executable safety tests.

Fresh ordinary before runs (once each, wall / unittest seconds):

| `python3 -m unittest discover -s tests -p …` | Passed | Seconds |
| --- | ---: | ---: |
| `test_blockers.py` | 8 | 0.348 / 0.183 |
| `test_skill_descriptions.py` | 1 | 0.066 / 0.007 |
| `test_workflow_contract.py` | 3 | 0.765 / 0.667 |
| `test_workflow_commands.py` | 10 | 0.363 / 0.204 |
| `test_portable_package.py` | 7 | 0.098 / 0.016 |

These are **29 Python executions**, not the JavaScript cases or a speedup. Text
checks often record no owned Python lines; equal coverage could not establish
instruction-compliance equivalence. Only the identified editorial predicates have
a thinning rationale; safety obligations and mixed cases remain protected.

#### F3 — Pi fixture and cycle cost (Fact; Medium; thin fixtures, not journeys)

All IDs are `test_pi_autowork.EngineTests`. Each ran once in a separate ordinary
interpreter with `python3 -c "import sys,unittest;sys.path.insert(0,'tests');
unittest.main(module=None,argv=['audit','test_pi_autowork.EngineTests.<ID>'])"`,
outer limit 180 seconds. They use fake Pi/local Git, no installed service, model,
network endpoint or port. All three passed on the audit source:

| ID / `tests/test_pi_autowork.py` lines | Exact before fixture/wait | Wall / unittest seconds; retained oracle |
| --- | --- | --- |
| `test_a_service_pauses_after_a_failure_streak_instead_of_exiting`, :678-694 | A/B block, failure threshold 1, pause 3,600 s, interval 1 s; bounded 0.2 s polling to pause log, then fixed **3 s** at :689. | **26.501 / 26.440**; later-cycle survival, no `Finished.`, SIGINT exit 130. |
| `test_a_stalled_service_says_so_once_and_the_fleet_view_shows_why`, :696-719 | A blocks, B completes, C waits; stall threshold 2 s, interval 1 s; poll to notice, then fixed **4 s** at :707. | **29.542 / 29.491**; one notice after later cycles, root attribution, real `--fleet`/`--status` readback. |
| `test_a_claim_idle_long_enough_is_adopted_and_finished`, :721-733 | Commit A in-progress; full first queue proves fresh-claim refusal and executes B; fixed **2 s** at :728; threshold 1 s, second queue. | **14.085 / 14.030**; fresh refusal, aged adoption and A/B/C complete. |

Nine literal sleep seconds are **not nine proven removable seconds**. Alive before
a wait is not later-cycle proof; a smaller sleep under contention is not equivalent.
Replace with observable cycle milestones or existing explicit-time component seams,
retaining real CLI composition. A smaller consumed-state fixture must match actual
journal/claim/state inputs as TOOLSET-102-ea did, not arbitrarily backdate timestamps.
No replacement fixture or candidate line/branch equivalence has been measured here.

Failure-safe cleanup lead: pause/stall coordinator launches (:681-682,700-701)
precede assertions without immediate coordinator cleanup. `Fixture.stop_workers`
(:247-258) kills recorded workers only; `start_runner` (:290-292) registers no
cleanup. The new quiet-planning journey (:1178-1190) has the same assertion-before-
shutdown pattern. Include failure-safe coordinator reaping in TOOLSET-127-b1's
existing fixture scope; no leak reproduction or attribution of the prior integration
descendant to these tests is established by this static observation.

Legacy/component matrix (legacy paths: `tests/test_pi_autowork.py`; short component
filenames: `pi-autowork/tests/`):

| Legacy seam | Lower-cost component | Why composition stays |
| --- | --- | --- |
| Fallback/session :386-411 | `test_pi_runtime.py:85-122` | Cooling/choice is not completion in the resumed session/worktree. |
| Stall/fleet/status :696-719 | `test_health.py:31-107`, `test_fleet_view.py:47-83,133-173` | Explicit time/state is not continuous invocation, emitted logs or actual state readback. |
| Questions :1032-1070, quiet planning :1172-1191 | `test_questions.py:56-94` | Rendering is not no-model restart, question commit/merge or owner-answer consumption. |
| Release/restart :1440-1488 | `test_release.py:50-111` | Decisions are not launcher selection, no installer on rejection, code preservation or same-PID restart. |
| Dependencies/restoration :817-834,1307-1317 | `test_workspaces.py:53-104` | Links are not worker consumption, resumed integration or selective stale-registration preservation. |
| Touches :836-911 | `test_touches_inference.py:26-45,48-95` | Byte/provenance and bounded grant logic do not prove same-worktree resumption, same-commit re-verification or second-request refusal. |
| Budget restart :1137-1150 | `test_pi_runtime.py:109-122` | Persisted runtime-window spending across jobs is not coordinator restart/expired-record composition. |
| Pause/adoption :678-694,721-733 | `test_health.py:79-87`; `skills/autowork/scripts/test_parallel_claims.py:41-130` | State/claim classification is not failure-streak survival or actual aged-claim dispatch. |

**No legacy/component deletion equivalence is proven.** Keep incident, no-model,
barrier/parallel, ownership/cancellation, worker-push refusal, reviewer containment,
dirty-main, conflict resolution, selective cleanup and update/restart journeys.
Current changes require **once-only bounded authored-scope widening plus refusal**,
not the prior unconditional authored-scope refusal. Likewise manifest work is serial
with other serial work, not exclusive of all independent work. Retain these changed
positive/negative policies (`test_parallel_dispatch.py:133-152`,
`test_parallel_plan.py:84-123,180-208` under `skills/autowork/scripts`).

#### F4 — JavaScript package-count drift (Fact; Low; repair finding)

`npm pack --dry-run --json --cache "$TMPDIR/npm-cache"` succeeds and lists **13**
portable `SKILL.md` adapters, including Blockers; Python package tests (:24-26)
expect the same set. `tests/portable_pi.test.mjs:91` still expects **12** after
archive extraction. This proves stale expected-count inconsistency, not a Node
test outcome: **the Node suite was not executed or reported green here**.
Reconcile within TOOLSET-126-6b's existing JavaScript scope (or an explicit repair
receipt) before TOOLSET-128-69 qualifies it. Keep archive isolation/resource checks;
deleting the detector is not a fix. No new task/framework is needed.

### Per-module disposition map

**K = keep** current detector, not “proved minimal”. **T = thin** only F1–F3's
identified executions/predicates/fixtures. **I = investigate**, retaining tests now:
missing equivalence/cost evidence means no new implementation task. Anchors name
representative current seams, not independent coverage/mutation qualification of
every assertion. Counts are declarations, not inherited executions/subtests.
Directory headings supply each filename's path prefix. Totals: **104 K / six T /
16 I** Python modules.

#### `tests/` — 50 modules

| File:line | Methods | Disposition; retained risk / bounded lead |
| --- | ---: | --- |
| `test_audit_launcher.py:13` | 1 | K — launcher forwards explicitly owned default paths. |
| `test_autoresearch.py:20` | 6 | K — selector/alias routing, literal limits, integrity and standalone vendor execution. |
| `test_autowork_command.py:99` | 9 | K — fake-systemctl lifecycle, readiness, package precedence and per-service settings. |
| `test_autowork_migration.py:13` | 3 | K — receipt/lock-inode preservation, conflict and symlink refusal. |
| `test_beautify_readme_vendor.py:34` | 12 | K — provenance and real image parser/SVG safety regressions. |
| `test_behind_only_realign.py:73` | 26 | K — literal Git paths, hidden index flags, collisions, safety refs and local bytes. |
| `test_blockers.py:24` | 8 | T — F2 editorial lists only; keep incident routing and authorization obligations. |
| `test_bundle.py:51` | 33 | K — maintenance parsing, dead/concurrent update receipts, collisions and partial inventory. |
| `test_changelog_merge.py:23` | 2 | K — real two-entry merge and narrowly owned union-driver scope. |
| `test_check.py:37` | 12 | K — import-free discovery, symlink/live isolation, concurrency, output and nonpassing timeouts. |
| `test_complete_setup.py:62` | 7 | K — all-profile orchestration, partial failure, preview and symlink refusal. |
| `test_cron_autoheal.py:63` | 16 | K — exact managed job, uncertain-write no replay, pause/scope, concurrent edits and redaction. |
| `test_cron_autowork.py:16` | 5 | I — instruction routing/reporting; Telegram/authority obligations are not disposable wording. |
| `test_doctor_modes.py:40` | 9 | K — core/full asymmetry and foreign-command refusal; G22 table is clarity-only. |
| `test_engineering_vendor.py:15` | 8 | K — route selection/tamper refusal, immutable hashes and install closure. |
| `test_impeccable_bundle.py:13` | 2 | K — byte-exact provenance/license and clean-profile support installation. |
| `test_install.py:21` | 2 | K — shell entrypoint dispatch/argument forwarding, not shell-framework tests. |
| `test_install_graphify.py:47` | 9 | K — isolated profile/tree install, path safety and no partial publication. |
| `test_install_menu.py:60` | 16 | K — host selection, preview, failure and streaming; terminal/color contracts remain. |
| `test_install_omh.py:67` | 28 | K — provider/store isolation, precedence, malformed config and zero-write refusal/preview. |
| `test_install_plugins.py:61` | 29 | K — profile scope, consent, publication, existing edits and policy opt-out. |
| `test_install_skills.py:44` | 10 | K — support closure, repeat preservation and unsafe-destination refusal. |
| `test_isolated_origin_clone.py:36` | 7 | K — shallow/Git-selector isolation, pins and destination bytes. |
| `test_native_provisioning.py:17` | 4 | K — offline publication races/existing skills; no native qualification. |
| `test_omh_trim.py:50` | 6 | K — merge preserves user disabled skills, rejects foreign provenance. |
| `test_owner_cron.py:18` | 27 | K — generated authority/pause/scope and real wiring; G01 stays protected. |
| `test_pi_autowork.py:309` | 78 | T — F3 fixture/cycle work only; keep composed Git/process, session conflict, quiet planning and bounded scope grant/refusal. |
| `test_pi_touches.py:13` | 1 | K — old public script inserts Touches without unrelated byte changes. |
| `test_plugin.py:80` | 12 | K — discovery, ownership, literal origin routing and symlink escape refusal. |
| `test_portable_package.py:11` | 7 | T — F2 editorial predicates only; keep authorization metadata/manifests/closure. |
| `test_preflight.py:25` | 12 | K — malformed/foreign facts and safe prerequisite refusal before profile writes. |
| `test_profile_consult.py:50` | 45 | K — cache/expiry, secret grammars, original session and timeout tree cleanup. |
| `test_profile_create.py:14` | 2 | I — prose plus actual discovery/argument dispatch; no blanket deletion. |
| `test_project_status.py:34` | 5 | I — historical prose versus local link/anchor checks; keep live/offline distinction. |
| `test_removed_memory_integration.py:13` | 2 | K — retired assets/defaults and removed-flag refusal before writes. |
| `test_repo_docs_graphify.py:9` | 2 | I — guidance/authority phrase guards; no executable-equivalence evidence. |
| `test_scheduled_progress.py:9` | 4 | I — outcome/recovery/paused policy, not scheduler execution evidence. |
| `test_setup_runtime.py:35` | 10 | K — activation/registration receipts, foreign gateway refusal and explicit no-reload. |
| `test_skill_descriptions.py:11` | 1 | T — F2 punctuation only; retain index length/metadata compatibility. |
| `test_start_notice.py:53` | 5 | K — fake API route/topic, nonfatal error and existing-file preservation. |
| `test_task_touches_contract.py:15` | 2 | I — task-authoring prose, not executable protected-path admission. |
| `test_telegram_menu_policy.py:15` | 13 | K — cap/aliases, scoped API errors, opt-out and no-owner/no-call behavior. |
| `test_tx.py:19` | 2 | K — launcher avoids Autowork injection; package exposes intended commands. |
| `test_ui_taste_bundle.py:22` | 5 | K — immutable snapshot, license, single registration and offline provisioning. |
| `test_update_bundle.py:46` | 95 | I — fresh Git/profile cost lead; keep history/data-loss/races, no G09/G18/G30 removals. |
| `test_update_quiet_restart.py:48` | 24 | K — busy/unknown refusal, coalescing, real locks/readback and outcome conservation. |
| `test_workflow_commands.py:10` | 10 | T — F2 wording only; retain aliases, collisions, namespace and installed source. |
| `test_workflow_contract.py:16` | 3 | K — links, install paths and copied-install helper execution. |
| `test_workflow_cycle.py:23` | 13 | I — mixed policy/executable ledger lifecycle; keep review/authority boundaries. |
| `test_worktree_closeout.py:19` | 3 | K — policy plus documented main/master closeout invocation, distinct from helper units. |

#### `skills/autowork/scripts/` — 53 modules

| File:line | Methods | Disposition; retained risk / bounded lead |
| --- | ---: | --- |
| `test_analyze_audit_logs.py:20` | 2 | K — deduplication, chunk bounds and receipt/cursor immutability. |
| `test_audit_profiles.py:38` | 12 | K — scope, read-only SQLite/backlog, cursor rotation and no fsmonitor execution. |
| `test_backlog_plan.py:14` | 16 | K — observed/unknown empty queue, bounded reuse and no ownership bypass. |
| `test_blocker_recovery.py:23` | 2 | K — attributed prerequisite recovery composed with admission. |
| `test_budget_controller.py:166` | 35 | I — called race test adds coordination/evidence; keep capacity/uncertainty, no removal. |
| `test_candidate_identity.py:33` | 3 | K — base/tree/prerequisite identity, no dirty-union qualification. |
| `test_check_receipt.py:18` | 50 | K — positive/negative environment/cache/source identity, cleanup and exact reuse. |
| `test_cli_bounds.py:9` | 1 | I — mock-only deadline/errors, but timeout is an owned boundary; no safe deletion proof. |
| `test_collector_correctness.py:34` | 16 | K — unknown attribution, replay IDs, sparse schema and preserved projections. |
| `test_continuation_capability.py:55` | 12 | K — legacy caps still enforce exhaustion/unknown usage/no replenishment. |
| `test_controller_bridge.py:16` | 11 | K — real local Unix identity/deadlines, protocol rejection and uncertain reservations. |
| `test_delivery_state.py:133` | 23 | K — exact review/source/merge policy, changed-base conservation and receipt seam. |
| `test_discovery.py:21` | 7 | K — owned plans/docs, exclusions, root escape and dependency pruning. |
| `test_disjoint_fallback.py:45` | 5 | K — native-compatible disjoint ownership/refusal/handoff, not default-path prerequisite. |
| `test_disjoint_triage.py:19` | 9 | K — triage/backoff only its slice, retaining live ownership/blocked duplicates. |
| `test_engineering_signals.py:14` | 4 | K — bounded signals, no generated/symlink scan or unsupported bug claim. |
| `test_finish_task.py:46` | 21 | K — actual index/HEAD, literal paths, hooks, timeout writers and owned commits. |
| `test_goal_handoff.py:19` | 27 | K — composed admission/source/identity/notification uncertainty and review; G02/G15. |
| `test_main_only.py:47` | 6 | K — serialized lifecycle, foreign bytes, timeout release and no native launch without hook. |
| `test_milestone_admission.py:108` | 16 | K — transaction, immutable preparation, focus/dependency races and fallback authority. |
| `test_native_containment.py:22` | 27 | K — synthetic manifest/isolation, registration-before-release and exact cancellation evidence. |
| `test_owner_cycle.py:32` | 47 | I — large legacy/default fixture matrix; retain recovery/bookkeeping/unknown delivery. |
| `test_owner_unblock.py:63` | 18 | K — attributable repairs, immutable body, source/ownership refusal and foreign bytes. |
| `test_parallel_adversarial.py:68` | 7 | K — escaped descendants, stale reports/lost receipts and exact-once landing. |
| `test_parallel_claims.py:41` | 10 | K — claim/branch age, live session/file ownership and adoption refusal. |
| `test_parallel_compat.py:97` | 5 | K — real CLI byte compatibility and fallback without state/worktrees. |
| `test_parallel_dispatch.py:97` | 32 | K — isolation, capacities, original timeout, serial/exclusive distinction and interrupted/overlap-held admission. |
| `test_parallel_e2e.py:164` | 12 | K — real CLI A/B/C composition/status/journal; delayed observation is distinct. |
| `test_parallel_integrate.py:79` | 100 | I — mutable Git cost lead; keep closeout/races plus once-only reoffer, interrupted readoption and empty retry. |
| `test_parallel_plan.py:15` | 16 | K — protected scope, serial/exclusive, transitive dependencies and priority-preserving backfill. |
| `test_parallel_state.py:52` | 13 | K — shared leases, owner birth identity, recovery and retry budget preservation. |
| `test_pass_workspace.py:46` | 23 | K — frozen candidate/ledger, start guards and no dirty-source workspace. |
| `test_picker_policy.py:13` | 6 | I — predicates include exhaustion/authority/privacy; no safe deletion proof. |
| `test_pipeline.py:114` | 17 | K — compatibility creation/readback and budget-history refusal, not model dispatch proof. |
| `test_ponytail_handoff.py:13` | 2 | K — method references and worker/proposal authority in existing review lane. |
| `test_prerequisite_recovery.py:40` | 5 | K — immutable provenance and failed-acceptance prerequisite cleanup. |
| `test_priority_selection.py:51` | 4 | K — entrypoint order agreement, drift refusal and active continuation. |
| `test_progress_runtime.py:19` | 10 | K — owner/session binding, idempotence, inbox conflicts and no retargeting. |
| `test_publication_readiness.py:44` | 4 | K — destination/authority, ancestry conflict and no-force readiness. |
| `test_reconcile.py:18` | 28 | K — original run/review/owner identity, unknown/delivered distinction; G29 transitions. |
| `test_registered_create_cli.py:8` | 2 | K — native launcher/profile transaction argv seam, not native acceptance. |
| `test_registration_admission.py:73` | 6 | K — transaction rollback, writer race, stale binding and attributed append. |
| `test_response_tail.py:18` | 22 | K — frames, secret masking before truncation and job/path isolation. |
| `test_retry_selection.py:33` | 36 | K — source/status/dependency parser, registered writers and no invented historical scope. |
| `test_runtime_bundle.py:21` | 4 | K — immutable closure, wrong pins/symlinks and shell dependency reuse. |
| `test_selection_cost.py:14` | 1 | K — dependency-search operation bound protects real complexity contract. |
| `test_source_freshness.py:8` | 3 | K — source appearance/deletion/symlink/workspace identity without secrets. |
| `test_task_execution.py:47` | 37 | T — F1's eleven repeated child executions only; retain all unique named methods. |
| `test_worker_role_contract.py:11` | 8 | K — caller limits, proposal/publication modes, CLI validation and payload bound. |
| `test_workflow_handoff.py:7` | 1 | I — text card/product boundary; keep obligation until thinning evidence exists. |
| `test_worktree_closeout.py:58` | 21 | K — selective removal/archive, exact bytes, evidence/dirty/live/locked preservation. |
| `test_worktree_paths.py:34` | 6 | K — canonical ignored placement, hook create/remove and escape refusals. |
| `test_writer_registration.py:12` | 4 | K — bound append/provenance, read-only native observation and drift refusal. |

#### `skills/docs-sync/scripts/` — 15 modules

| File:line | Methods | Disposition; retained risk / bounded lead |
| --- | ---: | --- |
| `test_archive_policy.py:13` | 3 | I — two prose contracts plus actual history/selection preservation; no blanket deletion. |
| `test_backlog_recovery.py:46` | 13 | K — same-task recovery, ambiguous/fenced acceptance refusal and original bytes. |
| `test_docs_manifest.py:51` | 24 | K — real links/anchors/roles/paths, malformed shapes and symlinks; named parser regressions. |
| `test_docs_profiles.py:40` | 5 | K — profile/CLI baselines and scaffold alignment, not arbitrary wording. |
| `test_docs_stale.py:61` | 7 | K — real Git ancestry/environment isolation, unknown provenance explicit. |
| `test_goal_concurrency.py:70` | 17 | K — common-dir locks, hostile Git selectors, stale revision and in-flight edits. |
| `test_goal_redaction.py:48` | 11 | K — private archive, scope/path refusal, locking and no partial writes. |
| `test_goals.py:70` | 43 | K — init rollback, schema/graph, stable render and named CRLF/data-loss regressions. |
| `test_handoff_reconciliation.py:44` | 21 | K — accepted-plan/readiness parsing, fences and read-only CLI; G13 clarity-only. |
| `test_live_harness_guard.py:11` | 1 | K — import refuses live harness before writes; not just inventory exclusion. |
| `test_milestone_focus.py:44` | 10 | K — focus roundtrip, dependency/status refusal and legacy order. |
| `test_priority_order.py:84` | 18 | K — human order, grouped/revision-guarded bootstrap and entrypoint drift refusal. |
| `test_render_safety.py:29` | 5 | K — fenced/ambiguous markers, neighbor sections and injected-text preservation. |
| `test_supersession.py:53` | 8 | K — not-completed semantics, unchecked history/dependencies and byte-stable archive. |
| `test_todo_archive.py:45` | 31 | K — crash/concurrency/symlinks, task boundaries and source/archive byte conservation. |

#### `skills/git-commit-push/scripts/` — one module

| File:line | Methods | Disposition; retained risk / bounded lead |
| --- | ---: | --- |
| `test_delivery_scope.py:33` | 9 | I — publication/allowlist/writer phrases plus executable inventory, not publication behavior proof. |

#### `pi-autowork/tests/` — seven modules

| File:line | Methods | Disposition; retained risk / bounded lead |
| --- | ---: | --- |
| `test_fleet_view.py:47` | 15 | K — state/readiness, action confirmation, question lanes and headless TUI. |
| `test_health.py:31` | 9 | K — explicit-time stall/dedup/reset, stuck/dead/silent and overlap-only versus mixed-blocker deadlock. |
| `test_pi_runtime.py:75` | 5 | K — fake executable stream/timeout/fallback, redaction and persisted spending across jobs. |
| `test_questions.py:56` | 5 | K — deterministic order, first-seen stability and owner bytes outside marked block. |
| `test_release.py:50` | 5 | K — local compatibility, fetched code never executed, busy deferral and package precedence. |
| `test_touches_inference.py:26` | 6 | K — byte/provenance/shim, bounded once-only authored grant and ownership/refusal cases. |
| `test_workspaces.py:35` | 5 | K — canonical restoration, traversal, dependency links and unsafe paths. |

#### JavaScript — `tests/portable_pi.test.mjs`

| Case / line | Disposition; retained risk |
| --- | --- |
| `Pi registers workflows and all 13 research commands; routes literal arguments`, :5 | I — F2 title-text leads; keep 26 commands, selector/resource matrix, literal bytes and follow-up delivery. |
| `npm package excludes local bytecode and keeps portable support files`, :46 | K — actual npm inventory excludes bytecode and retains support, not source-tree existence alone. |
| `installed archive resolves portable references and commands without checkout files`, :61 | K + repair F4 — extract real archive, resolve links and run installed commands independent of checkout. |

### Excluded-suite map — static review only

Counts are declarations; zero means standalone assertions, **not an empty suite**.
Keep all eight exclusions. The three `integration_*.py` files also fall outside the
`test_*.py` glob; deleting their exclusion entries would not execute them. Offline
mocks do not replace installed/live qualification.

| File / source anchor | Methods | Disposition, retained detector and prerequisite |
| --- | ---: | --- |
| `skills/docs-sync/scripts/test_goal_gap_regression.py:17-79` | 0 | K — two real Docs Sync/model passes, protected inputs and byte-exact repeat; needs isolated Hermes chat/profile receipts. Import now raises SkipTest before writes; check.py's import-write reason is stale, not a reason to execute it. |
| `skills/autowork/scripts/test_native_lifecycle_controls.py:210-265,469-553,790-883` | 43 | I, keep excluded — native contracts/history, deadlines/lifetime and real create/dedup/dry-dispatch preflight; installed Hermes interpreter/CLI/Linux needed. Fake transport does not qualify native execution. Separating portable cases needs dependency evidence. |
| `skills/autowork/scripts/test_native_handoff.py:38-69,72-130,152-319` | 15 | I, keep excluded — three offline validation cases mixed with twelve opt-in native identity/comment/readback cases, isolated SQLite and OS workers. Requires installed Hermes and HERMES_NATIVE_HANDOFF_TEST=1. Extracting three is an unverified lead. |
| `skills/autowork/scripts/test_native_containment_linux.py:12-285` | 8 | K — actual registration/namespaces/environment and detached-child cleanup/cancellation; opt-in backend, systemd user manager, bubblewrap, cgroup v2/fixed runtime. Live model remains NOT_RUN. |
| `skills/autowork/scripts/test_controller_bridge_linux.py:15-17,307-482` | 6 | K — installed controller/containment, egress negative/positive controls, replay/capacity/uncertainty; opt-in backend/local listeners required, no ports bound here. No provider qualification. |
| `tests/integration_plugin.py:17-35,105-191` | 0 | K — actual loader/provisioning/defaults/menu, captured origin/unload in temporary profile; Hermes source/interpreter required. No model or Telegram delivery proof. |
| `tests/integration_autoresearch.py:12-80` | 0 | K — actual loader/aliases/CLI queue/captured routing; temporary profile/Hermes, explicitly no network/model calls. |
| `tests/integration_bundle.py:1-4,15-77` | 0 | K — existing isolated installed bundle inventory/loader/skills/alias queues; requires actual isolated HERMES_HOME, unlike temporary-profile fixtures. No bot/model qualification. |

### Remaining leads, protected seams and blind spots

- **Fixture repetition is not behavior repetition.** `tests/test_update_bundle.py:17-38`
  rebuilds a Git remote/clone and profiles; `skills/autowork/scripts/test_parallel_integrate.py:19-43`
  rebuilds repository/coordinator/slot state. Distinct conflicts, interrupted writes,
  foreign bytes and closeout races require fresh mutable fixtures. Share immutable
  input/builders only after timing/source-consumption evidence; no new task from setup counts.
- **Called repetition is not removal proof.** `skills/autowork/scripts/test_budget_controller.py:660-673`
  calls another case but adds coordination, exit and source-evidence predicates.
  Existing process/observation helpers share durable cleanup oracles. Keep SQLite
  at-most-once, capacity, crash/uncertainty, secret omission and zero-unit exhaustion
  (G10/G19/S5), not just common covered lines.
- **Classify sleeps.** Thirteen offline modules contain AST `.sleep()` calls, not
  thirteen unconditional waits. `test_check_receipt.py:497-508` and
  `test_parallel_adversarial.py:137-154` under `skills/autowork/scripts` wait beyond
  escaped-child effects to detect failed cleanup: keep those negative oracles.
  Polls bound observation; embedded fake-child sleeps are outside this AST count.
  `pi-autowork/tests/test_pi_runtime.py:40,104` interrupts a 30-second fake hang
  with a one-second job limit; it does not pay an unconditional 30-second wait.
  No global clock mocking in race/process tests.
- **Retain changed incident seams.** Current cases for same-commit conflict recovery
  and quiet owner planning (`tests/test_pi_autowork.py:1161-1191`), interrupted and
  overlap-held admission (`skills/autowork/scripts/test_parallel_dispatch.py:538-567`),
  once-free reoffer/history/empty retry (`test_parallel_integrate.py:152-172,400-417`
  in that directory), overlap-only deadlock (`pi-autowork/tests/test_health.py:43-53`)
  and bounded widening/refusal (`pi-autowork/tests/test_touches_inference.py:69-95`)
  are new distinct protections, not dispensable duplicates of component logic.
- **Legacy does not mean dead.** Shipped orchestration still has native consumers
  and compatibility/refusal obligations; see `docs/project.md` current components.
  Removing those sources/obligations is outside this task.
- **Coverage/mutation:** no new measurement/tool/dependency. TOOLSET-073's 213
  no-record contexts and TOOLSET-102-ea's paired union are historical, not today's
  whole-suite equivalence. Text, shell/Git, copied sources, sanitized/isolated
  children, alternate interpreters and killed descendants remain blind spots.
  Replacement fixtures need focused before/after lines **and branches**, inherited
  child caller IDs, data off sys.path and retained assertions, not static counts.
- **Unknown history:** no CI failure-history dataset or repeated flake sample was
  available. One pass is not a zero-flake rate. No quarantine/hidden skip or unique
  branch/mutant detector removal is justified. Instruction compliance, native
  loading, model behavior and delivery remain outside offline evidence.

### Bounded handoff and verification

| Existing task | Bounded action / acceptance and checks |
| --- | --- |
| [TOOLSET-125-e6](../TODO.md#toolset-125-e6--run-inherited-execution-regressions-once) | Fixture-only base/helper; keep 37 unique methods, remove only eleven second executions (F1). Coordinator corrects stale counts. Focused task-execution discovery, before/after timing, unchanged retained line/branch seams, full normal Python gate and diff check. |
| [TOOLSET-127-b1](../TODO.md#toolset-127-b1--thin-repeated-pi-lifecycle-fixtures-and-fixed-waits) | Three F3 candidates first; keep fresh refusal, later cycles, fleet/status, signals and failure-safe reaping. Compare focused timing/subprocess coverage; run Pi module, component discovery, composed journeys and normal gate. No test-only production hook or blanket legacy deletion. |
| [TOOLSET-126-6b](../TODO.md#toolset-126-6b--trim-prose-only-test-assertions-while-retaining-executable-contracts) | F2 predicate/obligation record; keep routing/metadata/link/archive/security seams. Repair F4 without weakening archive isolation. Five focused Python modules, Node gate, normal Python gate and diff check. No policy-compliance equivalence from line coverage. |
| [TOOLSET-128-69](../TODO.md#toolset-128-69--qualify-suite-thinning-and-reconcile-the-test-budget) | After three batches: refresh map, unique/collected counts, fixture/test lines and retained obligations; inventory/full Python gate, Node gate, goals validation and diff check. Preserve failures/timeouts, no speedup percentages without comparable repeated passing measurements. |

Unknown candidates stay **I**, not queued work. Mixed excluded suites and the stale
goal-gap reason remain findings only; no runner policy changes. Apply the shared
one-behavior/one-focused-test budget, no new tests for this documentation, fresh
mutable fixtures and existing full Python/Node qualification gates. Review growth
at the behavior seam, not against a target count.

Executed on this audit source: checker `--list` (126 modules/five directories/eight
exclusions); static AST inventory/body scan and full map accounting; narrow
inheritance collection and 48-case run; three bounded Pi candidates; five focused
Python prose/package modules (29 executions); npm dry-run (13 adapters); goal
validation and diff check. Raw inventories/timings/logs stay in scratch. No full
Python gate, Node test gate, excluded suite, live service/model or Telegram check
ran here. This is a disposition and bounded handoff, **not a minimized or newly
qualified suite**; integration remains the coordinator's separate guarded step.

## Inherited execution result (TOOLSET-125-e6)

Applied only the inherited-execution batch from baseline
`c5d87eef3e5158f34e6ae48d2f41c614c483b2a8`, on Linux x86_64 with Python 3.12.14.
The current source has more cases than either historical inventory above:
**11 direct + 38 recovery + one selection-cache = 50 executions** before;
**11 direct + 27 recovery + one selection-cache = 39 unique executions** after.
The accepted plan's 47 → 36 and F1's 48 → 37 remain historical, not targets that
justify deleting later regressions. Coordinator-owned task counts need reconciliation.
The Git-timeout/BUSY and runner-job/session-attribution recovery cases and the
selection-cache case are retained, not thinned to force an obsolete count.

[ExecutionFixtureMixin](../skills/autowork/scripts/test_task_execution.py) now owns
only `setUp` and `call`, and does not inherit `unittest.TestCase`. Both concrete
classes inherit that mixin and `unittest.TestCase` independently. The eleven removed
`RecoveryTests.test_*` IDs map exactly to the same-name retained
`DirectExecutionTests.test_*` IDs in the accepted plan's eleven-name mapping above.
Before refactoring each pair was the identical method object; RecoveryTests had no
fixture override. Fresh collection confirms exactly those eleven IDs disappeared,
no IDs were added, and all 39 declared cases still execute once.

A task-local AST comparison against the baseline verifies every retained test and
helper body is unchanged, including actions, assertions and branch predicates.
The moved `setUp` and `call` bodies are unchanged and resolve to the same method
objects for both classes; each test still creates and cleans its own mutable fixture.
Their sizes remain 26 and five lines respectively. The module grows from 563 to
566 lines solely for the fixture-only class boundary/documentation; it retains all
39 declared test methods. No replacement meta-test, skip, framework, dependency,
production hook or runtime change was added. Dynamic line/branch coverage and
mutation were not measured; structural equivalence is not a new coverage receipt.

Same-machine, uninstrumented focused command, one passing run per version:
`python3 -m unittest discover -s skills/autowork/scripts -p test_task_execution.py`.
Before: **50 passed, 43.474 s unittest / 43.60 s wall**. After: **39 passed,
27.296 s unittest / 27.38 s wall**. Shared-host samples are not idle medians or a
whole-suite speedup claim. Raw logs, collection mappings and the AST verifier stay
in task scratch outside Git.

The focused sharded-runner command `python3 scripts/check.py
skills/autowork/scripts/test_task_execution.py` also passed **39 tests** (28.437 s
unittest), with the normal eight module exclusions unchanged. Full
`python3 scripts/check.py` acceptance belongs to the coordinator's merged-tree gate
and was not run by this worker. No live/model, service or delivery check was run;
this test-only batch adds no live qualification requirement.
