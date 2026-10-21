+++
schema = 1
id = "TOOLSET-326-fb"
title = "Decide whether pushing becomes opt-in per repository"
short = "Owner: push default on or opt-in"
status = "open"
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
+++

- Sources: https://github.com/TrebuchetDynamics/autowork/issues/4
