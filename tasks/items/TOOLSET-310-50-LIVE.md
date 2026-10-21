+++
schema = 1
id = "TOOLSET-310-50-LIVE"
title = "Live checks for TOOLSET-310-50"
short = "Live checks for TOOLSET-310-50"
status = "open"
goal = "EVALUATION"
section = "Needs decision"
rank = 7001
depends_on = ["TOOLSET-310-50"]
touches = ["pi-autowork/pi_autowork/scorecard.py", "pi-autowork/pi_autowork/command.py", "pi-autowork/tests/", "pi-autowork/README.md", "docs/evaluation.md"]
resources = []
kind = "implementation"
ownership = "owner"
scope = "Run the live checks the offline work for TOOLSET-310-50 left pending."
acceptance = ["TOOLSET-311-d7: owner-operated 30-day evaluation on at least two other real repositories with controlled permissions; fixture reports do not establish live delivery, billing coverage or sustained recovery reliability."]
checks = ["Live qualification by an authorized person"]
exclusions = ["Offline evidence does not count"]
+++

