+++
schema = 1
id = "GENTLE-UPDATE"
title = "Roll out updates without forcing gateway restarts"
priority = 88
source = "docs/project.md#gentler-update-rollout-2026-10-15"
status = "met"
focus = false
depends_on = []
+++

- Evidence: executed: TOOLSET-075..079 offline: python3 scripts/check.py (506/576/209/8 passed, 1 skipped) and node --test tests/portable_pi.test.mjs (3 passed); read-only pin dry run against the live home refused an unreleased revision as designed; live rollout not qualified (TOOLSET-084) (pass)
- Evidence: executed: TOOLSET-084 live 2026-10-15: hermes toolset update at afe1482 requested the restart with no chat turn in flight; /toolset update status showed gateway_restart completed, new PID 553964, menus resent 9/9; concurrent --check returned busy (exit 3) without touching the first receipt; earlier deferred restart waited for a chat turn that ended on its own (no forced chat drain); 7 linked profiles pinned to clean clones that only updates advance (pass)
