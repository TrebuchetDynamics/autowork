# Autowork reliability implementation plan

> Execution: isolated writers with regression-first changes and independent review.

## Accepted scope

Harden Hermes Toolset and Autowork itself. Do not repair profile projects, modify
upstream Hermes Agent, change live jobs, contact profiles, deploy private copies,
or start native/model workers. Preserve unrelated TODO.md and goals.json edits.
Existing authorization covers these bounded source repairs and local integration.

## Design and acceptance

1. **Distinguish local admission refusal from uncertain native dispatch.**
   `owner_cycle.py` currently marks attempted dispatch before `start_goal.py`, so a
   local prerequisite error can permanently poison future preparation despite no
   native create call. Bind a structured refusal to the exact launch attempt and
   stop asserting no-create before the first native creation operation. Only
   proven pre-create refusal permits archiving the old preparation and preparing
   corrected inputs. Preserve all history. Timeout, transport failure, malformed
   evidence, mismatched identity and any create attempt remain uncertain and may
   not clear the original marker or reset a consumed allocation.
   Tests must cover actual launcher refusal, corrected preparation, failure after
   creation, wrong/stale proof, immutable archive, and repeated uncertain attempts.

2. **Reuse unchanged consultation suggestions within a bounded interval.**
   Add opt-in private reuse to `scripts/profile-consult.py`, with unchanged default
   fresh behavior. Discover subjects each run; respect explicit subsets. Require
   matching bounded owner evidence, cron/continuity context and helper context,
   successful compliant response, and age at most one hour. Missing or uncertain
   input, changes, expiry or failures require fresh consultation. Label reused
   replies and their age explicitly; never count them as new replies, live state,
   recovery, authority or task completion. Default self-assessment stays fresh.
   Update generated maintenance guidance to use reuse and changed-only reporting
   without skipping fresh scheduler/ownership readback or required acceptance.
   Tests use fake providers only, asserting unchanged model-call count, individual
   invalidation, expiry, corruption, bounded reads and path isolation.

3. **Keep offline checks offline under inherited environment settings.**
   Strip `HERMES_NATIVE_REGISTRATION_TEST` alongside the other explicit opt-ins in
   `scripts/check.py`. Test through a real child checker without invoking native
   code. Failure diagnostics must not dump the inherited environment.

## Execution and review

- Each slice has one isolated worktree/writer; source changes integrate only after
  focused tests and independent review.
- Run the combined `uv run --python 3.12 --no-project --with-requirements
  requirements-test.txt python scripts/check.py` offline gate on the integrated
  candidate. Inspect all exclusions; no native/model qualification is claimed.
- Verify canonical unrelated dirty bytes before and after local integration.
- Report actual fixes, test results and local commit, plus remaining capability
  limits. Do not claim universal correctness or measured live speedup.

## Explicit remaining boundary

These changes do not invent same-card native continuation or replace its missing
cumulative-accounting provider. Existing stopped workers retain their original
allocation and evidence. Proven absence of a native create attempt is a different
state from an attempted or interrupted worker and is the only new retry path.
