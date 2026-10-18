# TOOLSET-184-b3: MAIN and scratch recovery evidence

Evidence supplement, not an accepted replacement plan or a passing check. The
[existing task](../../TODO.md#toolset-184-b3--restore-the-full-offline-check-after-the-red-main-at-36e2b7c)
retains every Acceptance item, dependency, status and priority. Its accepted source
remains [the continuous runner](../project.md#continuous-pi-runner-2026-10-15).
No duplicate repair task is needed.

## MAIN receipt at e5de1b4

The runner's `main_check.json` reports red revision
`e5de1b4294e5d4658ed2e73b71b47cd6c40fd95e`, `green: null`, and
`red_since: 36e2b7c0ea0c6096a7b20197edcacf68dc11dfa4`. The completed
`main-check.log` has 21 distinct FAIL/ERROR identities, one beyond the JSON
summary's first 20. `main-check.exit` is 1; the log ends
`Offline result: 2 test directories passed; 3 failed; 8 modules excluded.`
These are retained receipts, not checks rerun by this documentation pass.

Full inventory:

- `test_pi_autowork.EngineTests.test_a_changed_reviewer_reviews_held_commits_again_by_itself`
- `test_pi_autowork.EngineTests.test_merged_work_is_pushed_to_main_upstream`
- `test_pi_autowork.EngineTests.test_a_backlog_left_unpushed_is_published_at_start`
- `test_pi_autowork.EngineTests.test_upstream_commits_are_pulled_into_main_after_a_task_before_its_push`
- `test_pi_autowork.EngineTests.test_a_rejected_push_merges_the_upstream_and_pushes_again`
- `test_pi_autowork.SetupTests.test_an_idle_runner_updates_its_toolset_and_restarts_on_the_new_code`
- `test_pi_autowork.SetupTests.test_a_release_that_cannot_read_current_state_is_never_installed`
- `test_pi_autowork.SetupTests.test_a_broken_toolset_update_keeps_the_running_code`
- `test_parallel_adversarial.AdversarialWorkerTests.test_a_report_written_after_a_coordinator_restart_is_adopted`
- `test_parallel_e2e.EndToEndTests.test_abc_real_cli`
- `test_parallel_e2e.EndToEndTests.test_abc_with_delayed_initial_observation`
- `test_parallel_e2e.EndToEndTests.test_serial_control`
- `test_publication_readiness.PublicationReadinessTests.test_ancestry_conflict_never_becomes_force_push_readiness`
- `test_publication_readiness.PublicationReadinessTests.test_multiple_remotes_are_resolved_by_bound_authority_not_origin_guess`
- `test_publishable.PublishableTests.test_a_pointer_to_a_local_only_commit_stays_out_until_it_is_pushed`
- `test_publishable.PublishableTests.test_an_untracked_nested_repository_is_not_added`
- `test_publishable.PublishableTests.test_ordinary_files_are_unchanged`
- `test_release.ReleaseCheckTests.test_a_compatible_release_may_be_installed`
- `test_release.ReleaseCheckTests.test_a_release_that_cannot_read_this_state_is_refused`
- `test_release.ReleaseCheckTests.test_another_runner_with_work_in_flight_defers_the_update`
- `test_release.ReleaseCheckTests.test_fetched_declarations_are_parsed_never_executed`

Reported commit window: `e5de1b4`, `7745319`, `7e804d0`, `0de0ae6`,
`c3f3230`, `3ca53ce`, `3bd1d95`, `c15b392`, `b5b4944`, `ef85685`,
`36e2b7c`, `7b77f3d`, `99813f9`, `ce43743`, `d9e39b4`, `db2e4ba`,
`69937f0`, `0749177`, `b40d85f`, `2f27806`. With no green revision, this is
neither fault attribution nor a proven since-green range. The existing repair's
Touches cover the failing modules and the checker/coordinator/engine changes
in that window. `e5de1b4` changes `update_bundle.py` and
`tests/test_update_bundle.py`; its presence in the window alone does not justify
adding unrelated updater scope. Earlier commit/path evidence remains in the
[prior receipt](../../TODO.archive.md#main-receipt-at-7745319).

SHA-256 receipt bindings, inspected in the existing runner state:

| Receipt | SHA-256 |
| --- | --- |
| `main_check.json` | `99d3772c056b84421a30758f20e25792a0af9ec26a9c67c1a787dfafcdeec362` |
| `main-check.log` | `76470c5b1944c55c434f16f853afc4d1f007f77a84cb2398be6d80108227e013` |
| `main-check.exit` | `4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865` |

## Current continuation, not the older candidate

The current `slot-data/TOOLSET-184-b3/attempt-1/report.json` has `commit: null`
and 19 changed files, matching the task worktree's inspected status: 17 modified
tracked files and two untracked files (`pi-autowork/tests/test_coordinator.py`
and `skills/autowork/scripts/offline_fixtures.py`). Its baseline is `0c420d5`.
The slot is held with cause `blocker`; recorded worker PID 3084725 no longer
exists. Preserve those bytes and the consumed attempt. The old committed
candidate `2c23b62` and rejected merged candidate `a7d3f9f` are not this result.
No runtime state was changed by this pass.

The report records focused passes for checker, Pi, parallel, publication,
budget, containment, task execution, closeout, tx and janitor suites. Its final
full run nevertheless exits 1: 3 directories passed, 2 failed, 8 exclusions;
1,816 tests executed (677/835/219/9/76). Actual child command is
`python3 scripts/check.py`, on the uncommitted continuation, not current main.
The physical TMPDIR is a descendant of
`.git/autowork-execution/slot-data/TOOLSET-184-b3/attempt-1/tmp/`.
The report says the original failure inventory and prior review seams pass
there; this does not establish complete acceptance or independent qualification.
Remaining full-run failures:

- `test_audit_profiles.CollectorTests.test_completed_new_run_no_progress_and_unrelated_dirt`
- `test_audit_profiles.CollectorTests.test_default_all_real_profiles_and_missing_sources`
- `test_audit_profiles.CollectorTests.test_git_observation_does_not_execute_repository_fsmonitor`
- `test_audit_profiles.CollectorTests.test_job_delivery_and_response_coverage_are_not_silently_omitted`
- `test_audit_profiles.CollectorTests.test_logs_cursor_suffix_rotation_and_no_sibling_writes`
- `test_audit_profiles.CollectorTests.test_owner_cycle_receipt_is_collected_without_claiming_live_progress`
- `test_audit_profiles.CollectorTests.test_rename_status_counts_one_record_and_backlog_readiness_is_read_only`
- `test_audit_profiles.CollectorTests.test_ro_sqlite_allowlist_and_state_lock_boundary`
- `test_audit_profiles.CollectorTests.test_scoped_collection_preserves_excluded_profile_cursors`
- `test_docs_stale.DocsStaleTests.test_non_git_repository_and_missing_manifest`

Source corroboration: `skills/autowork/scripts/audit_profiles.py` rejects a
state path with any `.git` ancestor (`--state-dir overlaps repository`).
`skills/docs-sync/scripts/test_docs_stale.py` creates a temporary non-Git fixture;
its CLI deliberately strips inherited `GIT_*` overrides. A Git ceiling is not a
safe substitute for a physically non-repository directory. These protections
must not be weakened to make this scratch layout pass. The task's Touches now
explicitly includes the latter failing test file; the collector and its tests
were already covered by `skills/autowork/scripts/`.

The worker reports independent confirmation of that setup conflict. That is
worker-reported evidence, not a new runner review: the retained runner finding
still rejects `a7d3f9f` for socket paths, worktree cleanup and tx. All its findings
and the budget-evidence checks remain explicit in the task's Review continuation.

| Current attempt receipt | SHA-256 |
| --- | --- |
| `report.json` | `50559aa4074f01b494dc4bce119aa135acd84246d747f3fc70286b2f9c404394` |
| `tmp/continuation-full.json` | `a8082145579989da5e11891030022ba71b8f0c9209383288d9d33cde946a96ed` |
| `tmp/continuation-full.log` | `d98768a023869684398a025cbecfcda297245dea61747c80339c745aee912a0e` |
| `tmp/continuation-audit.json` | `815407716c89393acea90a2cb0756b7408dde25f47c1010d3002955a5295c3bf` |

## Bounded recovery

The missing input is coordinator-supplied, permitted physical task scratch with
no `.git` ancestor, for both the resumed worker and reviewer. The task's old
`mktemp -d /tmp/aw-XXXXXX` sample contradicted the reviewer's supplied-TMPDIR-only
rule in `pi-autowork/pi_autowork/worker.py`; the corrected Checks creates a child
of supplied TMPDIR instead. Neither that wording nor this evidence grants access
to a new location or makes a descendant of the current scratch suitable.

Existing TOOLSET-140-f4 owns private short slot scratch and already includes
reviewer setup in Touches from worker evidence. Reconcile that existing recovery
through the coordinator; do not create a competing scratch feature, rewrite its
acceptance or infer that it has landed. Keep TOOLSET-184-b3 first in Now and
preserve owner ordering. No new task dependency is asserted: the report requires
a valid supplied scratch input, not completion of every TOOLSET-140-f4 criterion.

Once the coordinator supplies it, resume the retained continuation, run all
required focused checks and the same complete offline inventory, then review the
resulting merged tree. No skip, timeout increase, assertion weakening, alias,
collector bypass, outside-scratch write, slot reset or evidence repin is allowed.
No implementation, full-suite rerun, live qualification or closure occurred in
this documentation pass.
