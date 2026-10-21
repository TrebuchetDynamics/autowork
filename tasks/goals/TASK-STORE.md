+++
schema = 1
id = "TASK-STORE"
title = "Keep project tasks in a Git-native tasks/ store the engine reads directly"
priority = 100
source = "docs/project.md#task-store-v2-2026-10-20"
status = "met"
focus = false
depends_on = []
+++

- Evidence: This repository runs on tasks/ alone: converted by autowork migrate (40b24ead), cutover merged in one merge (38999d67); the new runner dispatched, verified, merged and closed TOOLSET-303-24 end to end with a receipt (tasks/evidence/TOOLSET-303-24.toml, 2026-10-21 09:06), then TOOLSET-304-2c (tasks/evidence/TOOLSET-304-2c.toml, 09:58); CI green on main (run 39614136081). Follow-ups continue under TASK-STORE-HARDENING.
