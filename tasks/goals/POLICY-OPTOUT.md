+++
schema = 1
id = "POLICY-OPTOUT"
title = "Honor the documented runtime-policy opt-out everywhere it is checked"
priority = 90
source = "docs/installation.md#install"
status = "met"
focus = false
depends_on = []
+++

- Evidence: executed: python3 scripts/check.py --timeout 300 (406/571/197/8 offline tests passed; includes RuntimePolicyOptOutTests; offline only) (pass)
