+++
schema = 1
id = "UI-TASTE"
title = "Ship Uizze's UI Taste as a vendored bundled skill"
priority = 85
source = "docs/project.md#vendored-ui-taste-skill"
status = "met"
focus = false
depends_on = []
+++

- Evidence: executed: python3 scripts/check.py (440/575/209/8 offline tests, includes test_ui_taste_bundle and portable package tests) and node --test tests/portable_pi.test.mjs (3 passed); offline only (pass)
