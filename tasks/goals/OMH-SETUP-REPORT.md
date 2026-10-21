+++
schema = 1
id = "OMH-SETUP-REPORT"
title = "Report OMH memory left off when another provider holds the slot"
priority = 95
source = "docs/memory.md"
status = "met"
focus = false
depends_on = []
+++

- Evidence: executed: python3 scripts/check.py --timeout 300 (410/572/197/8 offline tests passed; includes test_install_omh memory-off regressions; offline only) (pass)
