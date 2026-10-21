+++
schema = 1
id = "ARCHIVAL"
title = "Integrate archival and reconcile the rendering contract"
priority = 40
source = "TODO.archive.md#toolset-009--account-for-archival-in-the-shared-rendering-contract"
status = "met"
focus = false
depends_on = []
+++

- Evidence: executed: Reviewed 218865c; coordinator exact-commit Python 3.12 scripts/check.py: 253/448/139/8 offline tests passed, 2 skipped, 8 excluded; native same-card review approved; local integration only (pass)
- Evidence: executed: cd skills/docs-sync/scripts && python3 -m unittest test_todo_archive test_archive_policy test_render_safety (31 tests; offline only) (pass)
- Evidence: executed: python3 scripts/check.py (411/572/204/8 offline tests passed; includes TOOLSET-042 archive newline, git diff --check and legacy-retry regressions); offline only (pass)
