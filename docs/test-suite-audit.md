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
