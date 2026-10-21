+++
schema = 1
id = "RELIABILITY-2026-10"
title = "Fix the reproduced high-ROI reliability bugs from the 2026-10-15 harvest"
priority = 15
source = "docs/project.md#reliability-bug-harvest-2026-10-15"
status = "partial"
focus = false
depends_on = []
+++

- Evidence: executed: python3 scripts/check.py on integrated main (437/575/209/8 offline tests passed, includes the TOOLSET-043..051 regressions) and node --test tests/portable_pi.test.mjs (3 passed); offline only (pass)
