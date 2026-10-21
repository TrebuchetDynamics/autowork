+++
schema = 1
id = "README-DESIGN"
title = "Vendor the README design skill and use it on this README"
priority = 20
source = "docs/project.md#readme-design-skill-2026-10-15"
status = "met"
focus = false
depends_on = []
+++

- Evidence: executed: TOOLSET-060/061 (b15bbc7, 5a9c044, ff7196f): python3 scripts/check.py 4/4 directories passed, node --test tests/portable_pi.test.mjs passed, docs.py check ok, vendored audit_readme.py passed with 2 local images; independent review of the vendoring; offline only (pass)
- Evidence: executed: TOOLSET-116-fc: python3 scripts/check.py passed 575/715/217/8 tests (one skip/eight excluded modules); all 12 focused README-audit tests and exact-source independent review approved; mixed-text single-line examples and adjacent-image preservation verified offline (pass)
