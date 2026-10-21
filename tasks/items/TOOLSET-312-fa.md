+++
schema = 1
id = "TOOLSET-312-fa"
title = "The fleet view puts runners that need the owner above idle ones"
short = "Needs-attention first"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 8000
depends_on = []
touches = ["pi-autowork/pi_autowork/fleet_view.py", "pi-autowork/pi_autowork/tui.py", "pi-autowork/tests/"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "fleet_view's runner headline returns 'Idle — nothing left to run in Now/Next' before it looks at open questions, so an idle runner with unanswered owner questions reads Idle; an unconverted repository (no tasks/) also reads like any idle runner. Check those conditions first and label them distinctly (needs your decision, setup required: run autowork migrate), and order the fleet list so runners needing the owner come before idle and working ones."
acceptance = ["tests cover: an idle runner with an open question reads 'Waiting on you', not Idle; an unconverted repository reads setup required with the migrate instruction; the fleet list orders needs-owner runners above idle ones."]
checks = ["python3 -m unittest discover -s pi-autowork/tests; python3 scripts/check.py"]
exclusions = []
+++

