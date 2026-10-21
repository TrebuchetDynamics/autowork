+++
schema = 1
id = "TOOLSET-326-fb"
title = "Decide whether pushing becomes opt-in per repository"
short = "Owner: push default on or opt-in"
status = "done"
goal = "RELIABILITY-2026-10"
section = "Needs decision"
rank = 3000
depends_on = []
touches = []
resources = []
kind = "plan"
ownership = "owner"
scope = "An outside review (2026-10-21) recommends making publication opt-in: a runner pushes only after the owner authorizes it for that repository, persisted per runner. Today push is on unless PI_AUTOWORK_PUSH=0. The owner's current workflow relies on unattended pushes. Decide: keep the default, or make it opt-in with a one-time per-repository grant; TOOLSET-324-73 makes the effective setting reliable and visible either way."
acceptance = ["The owner records the decision as an Owner decision note on this task"]
exclusions = []
closure = "manual"
closure_actor = "blockers"
closure_timestamp = "2026-10-21T22:11:52.763368+00:00"
closure_reason = "Owner decision recorded; implementation stays open as TOOLSET-353-9db87df7"
closure_evidence = "2026-10-21 blockers interview: owner explicitly selected push opt-in for new repositories, with no live changes now. Owner decision and follow-up are recorded in this task; implementation and live migration are not claimed."
+++

- Sources: https://github.com/TrebuchetDynamics/autowork/issues/4
- Owner decision: 2026-10-21: Owner chose push opt-in per repository for new repositories. Implement the policy as future product work; do not change any live runner, saved service setting, job, pause, publication authority or credential in this blockers session.
- Follow-up: TOOLSET-353-9db87df7 implements the accepted policy for new repositories; existing live runners remain untouched.
