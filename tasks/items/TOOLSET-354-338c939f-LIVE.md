+++
schema = 1
id = "TOOLSET-354-338c939f-LIVE"
title = "Live checks for TOOLSET-354-338c939f"
short = "Live checks for TOOLSET-354-338c939f"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Needs decision"
rank = 37001
depends_on = ["TOOLSET-354-338c939f"]
touches = ["pi-autowork/pi_autowork/", "pi-autowork/tests/", "tests/test_autowork_command.py", "pi-autowork/README.md", "docs/cross-host.md"]
resources = []
kind = "implementation"
ownership = "owner"
scope = "Run the live checks the offline work for TOOLSET-354-338c939f left pending."
acceptance = ["With explicit operator and subscription authorization, qualify one selected Pi model through a manually operated Hermes Nous proxy. Actual credential refresh, inference, model-plan access and billing were not tested offline.", "If unattended service operation is required, separately qualify the intended service environment and proxy availability after logout; no real service or proxy lifecycle was exercised."]
checks = ["Live qualification by an authorized person"]
exclusions = ["Offline evidence does not count"]
+++

- Owner decision: 2026-10-22: deferred pending explicit live authorization and an operator-run qualification window. Preserve every live acceptance criterion and the offline-evidence exclusion; no live service, model, credential, proxy, billing or external repository access is authorized. Offline delivery remains separate.
