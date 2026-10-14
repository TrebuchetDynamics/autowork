#!/usr/bin/env python3
# hermes-toolset: autowork-start-notice (bundle-managed; local edits are replaced)
"""Cron pre-run script: tell the job's Telegram destination that a run started.

Hermes runs a job's script before the agent, from the job's workdir, and injects
stdout into the prompt. The finished report is Hermes' normal cron delivery, so
this only adds the start message. It never fails the run: every problem is
reported on stdout and the script exits 0.
"""
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request

NAME = Path(__file__).name


def read_env(path):
    values = {}
    try:
        lines = path.read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        return values
    for line in lines:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            key, value = line.split('=', 1)
            values[key.removeprefix('export ').strip()] = value.strip().strip('"\'')
    return values


def same_dir(a, b):
    try:
        return Path(a).expanduser().resolve() == Path(b).resolve()
    except (OSError, TypeError, ValueError):
        return False


def matching_jobs(jobs, cwd):
    """Enabled jobs that attach this script and run from the current workdir."""
    return [j for j in jobs if isinstance(j, dict) and j.get('enabled', True)
            and Path(str(j.get('script') or '')).name == NAME and same_dir(j.get('workdir') or '', cwd)]


def telegram_target(deliver):
    """(chat_id, thread_id) for a telegram:CHAT[:THREAD] route, else None."""
    for route in str(deliver or '').split(','):
        parts = route.strip().split(':')
        if len(parts) in (2, 3) and parts[0] == 'telegram' and parts[1].lstrip('-').isdigit():
            return parts[1], (parts[2] if len(parts) == 3 and parts[2].isdigit() else None)
    return None


def notice(job, repo):
    name = job.get('name') or 'Autowork'
    return f'▶️ Started: {name}\nJob {job.get("id", "?")} · {repo}\nThe report follows when this run finishes.'


def send(token, chat, thread, text, opener=urllib.request.urlopen):
    params = {'chat_id': chat, 'text': text, 'disable_web_page_preview': 'true'}
    if thread:
        params['message_thread_id'] = thread
    data = urllib.parse.urlencode(params).encode()
    with opener(f'https://api.telegram.org/bot{token}/sendMessage', data, timeout=10) as reply:
        body = json.load(reply)
    if not body.get('ok'):
        raise OSError(body.get('description', 'Telegram API error'))


def main(home=None, cwd=None, opener=urllib.request.urlopen):
    home = Path(home or os.environ.get('HERMES_HOME') or Path.home() / '.hermes')
    cwd = Path(cwd or os.getcwd())
    try:
        data = json.loads((home / 'cron/jobs.json').read_text())
    except (OSError, ValueError):
        return 'Start notice not sent: job list unreadable.'
    jobs = matching_jobs(data.get('jobs', []) if isinstance(data, dict) else data, cwd)
    if len(jobs) != 1:
        return f'Start notice not sent: {len(jobs)} enabled jobs attach {NAME} in {cwd}.'
    target = telegram_target(jobs[0].get('deliver'))
    if not target:
        return 'Start notice not sent: the job has no Telegram delivery route.'
    token = os.environ.get('TELEGRAM_BOT_TOKEN') or read_env(home / '.env').get('TELEGRAM_BOT_TOKEN')
    if not token:
        return 'Start notice not sent: this profile has no Telegram bot token.'
    try:
        send(token, *target, notice(jobs[0], cwd.name), opener=opener)
    except (OSError, ValueError) as error:
        return f'Start notice not sent: {type(error).__name__}.'
    return 'Start notice delivered to Telegram; do not send another one.'


if __name__ == '__main__':
    print(main())
