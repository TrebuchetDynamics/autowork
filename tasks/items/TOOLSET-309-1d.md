+++
schema = 1
id = "TOOLSET-309-1d"
title = "Runner health stops reading unavailable when the engine lock is briefly busy"
short = "Health flaps on a busy lock"
status = "done"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 4000
depends_on = []
touches = ["pi-autowork/engine/parallel_status.py", "pi-autowork/pi_autowork/health.py", "pi-autowork/pi_autowork/cli.py", "pi-autowork/pi_autowork/coordinator.py", "pi-autowork/engine/", "pi-autowork/tests/", "tests/"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "parallel_status.snapshot reads under writer.lock with no wait (task_execution.lock wait=0), so any status read that meets a dispatch, integration or another status read fails with [Errno 11] Resource temporarily unavailable; health.update then records state unavailable (seen on a healthy runner right after a restart: 3 of 10 sampled reads failed while it dispatched and merged). Give status reads a short bounded wait for the lock, and keep one failed read from turning a working runner unavailable. The autowork status Health line (cli.py) prints record['since'], which during an unavailable spell still holds the previous state's start (a day-old date): show status_unavailable_since instead."
acceptance = ["tests cover: a status read that meets writer.lock held for under the wait returns PARALLEL_STATUS; health stays working across one failed read and reads unavailable only when reads keep failing; the Health line of an unavailable runner shows when reads began failing, not the earlier state's start."]
checks = ["python3 -m unittest discover -s pi-autowork/tests; python3 scripts/check.py"]
exclusions = []
+++

