# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in the [`tasks/`](tasks/) store. This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-337-e0 — USER_DECISION — effort investigate — unblocks 0

- Task: TOOLSET-337-e0 — The runner end-to-end tests (tests/test_pi_autowork.py) run in a fraction of their time
- Needs: integration validation failed or changed the integration tree: PI_AUTOWORK_VERIFY: fail — Affected checks failed: test_a_batched_candidate_that_fails_its_review_is_held_and_the_other_lands never formed the expected batch. Commit evidence also explicitly leaves the required 50% idle-host speedup and three consecutive full-check passes unqualified.; this was its one rework after review, and the earlier review found: TOOLSET-337-e0’s performance and verification acceptance criteria remain unmet.
- Since: 2026-10-22T01:36:00Z
- Answer: Read the evidence (the worker's report and validation log under .git/autowork-execution/slot-data/TOOLSET-337-e0/), then rescope or split TOOLSET-337-e0 in tasks/items/TOOLSET-337-e0.md. The runner reruns it when the record changes.
- Kind: held

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
