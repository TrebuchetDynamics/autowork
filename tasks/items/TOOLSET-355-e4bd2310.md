+++
schema = 1
id = "TOOLSET-355-e4bd2310"
title = "One process-liveness helper with start identity decides whether a runner or job is running"
short = "Liveness with start identity (PID reuse)"
status = "open"
goal = "CODE-HEALTH-2026-10"
section = "Next"
rank = 45000
depends_on = ["TOOLSET-325-d4", "TOOLSET-345-1db6f7cc", "TOOLSET-348-c29f8322"]
touches = ["pi-autowork/pi_autowork/health.py", "pi-autowork/pi_autowork/main_check.py", "pi-autowork/pi_autowork/coordinator.py", "pi-autowork/pi_autowork/cli.py", "pi-autowork/tests/test_health.py", "pi-autowork/tests/test_main_check.py", "pi-autowork/tests/test_own_lock.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "health._alive uses os.kill(pid, 0) with no identity, main_check.alive(pid, started) checks procfs start ticks, and coordinator.own_process walks procfs parents: three implementations, and runner.json records no start identity, so a PID reused after an unclean exit (power loss, SIGKILL) reads as a running runner in autowork status, the fleet view and current_job. Put one helper (start ticks, alive-with-identity, own-process, name) in a small module both health and main_check use; have the runner record its start ticks in runner.json and every reader require them to match. A record without start ticks is treated as not running once its PID is gone, never as running on PID alone."
acceptance = ["An offline test writes runner.json naming a live unrelated PID with mismatched start ticks and health.fleet reports the runner as not running; with matching ticks it reports running", "main_check.alive, health._alive and coordinator.own_process are replaced by the shared helper; no second liveness implementation remains in pi_autowork (grep in the test)", "autowork status for a runner.json whose PID is reused says the runner is not running"]
checks = ["python3 scripts/check.py pi-autowork/tests/test_health.py pi-autowork/tests/test_main_check.py pi-autowork/tests/test_own_lock.py tests/test_pi_autowork.py"]
exclusions = []
+++

- Sources: docs/plans/structural-audit-2026-10.md#hotspots
- Coordination: Overlap repair: wait for TOOLSET-348-c29f8322, whose attempt-1 slot is running in the Git common execution directory (no report yet at inspection). Its active-first status rows, finished-row count and aged status.json fallback do not deliver start-identity liveness. Keep all three Acceptance items together: cli.py writes runner.json in main and reads it in status_view; the helper and its health/main_check/coordinator consumers need that identity wiring for the end-to-end contract in docs/plans/structural-audit-2026-10.md#hotspots. Splitting off cli.py would leave the identity producer and status acceptance pending, not an independent complete liveness fix. The running task is untouched; existing prerequisites, Touches, Acceptance, Checks and priority are preserved.
