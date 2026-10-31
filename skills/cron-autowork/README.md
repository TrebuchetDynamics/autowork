# Cron pre-run script

This folder is not a skill. Its `SKILL.md` was removed, and no command, adapter or
docs entry registers it. The folder stays because Hermes runs a cron job's pre-run
script from `HERMES_HOME/scripts`, and the plugin copies
[`scripts/autowork-start-notice.py`](scripts/autowork-start-notice.py) there for jobs
that already reference it. Removing the path would break those saved jobs.

Schedule work with the host's own cron command. The plugin does not add a scheduling
workflow.
