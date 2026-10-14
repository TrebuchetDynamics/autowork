import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/cron-autowork/scripts/autowork-start-notice.py'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


notice = load('start_notice', SCRIPT)
defaults = load('runtime_defaults_under_test', ROOT / 'runtime_defaults.py')


class Reply(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *_): return False


class StartNoticeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name) / 'home'; self.repo = Path(tmp.name) / 'repo'
        (self.home / 'cron').mkdir(parents=True); self.repo.mkdir()
        (self.home / '.env').write_text('TELEGRAM_BOT_TOKEN="secret"\n')
        self.sent = []

    def jobs(self, *jobs):
        (self.home / 'cron/jobs.json').write_text(json.dumps({'jobs': list(jobs)}))

    def job(self, **kw):
        return {'id': 'abc123', 'name': 'Repo autowork', 'enabled': True, 'workdir': str(self.repo),
                'script': 'autowork-start-notice.py', 'deliver': 'telegram:-100200:7', **kw}

    def opener(self, url, data, timeout):
        self.sent.append((url, dict(p.split('=', 1) for p in data.decode().split('&'))))
        return Reply(b'{"ok": true, "result": {}}')

    def run_notice(self):
        with patch.dict('os.environ', {}, clear=False) as env:
            env.pop('TELEGRAM_BOT_TOKEN', None)
            return notice.main(self.home, self.repo, opener=self.opener)

    def test_sends_one_message_to_the_job_chat_and_topic(self):
        self.jobs(self.job(), self.job(id='sync', script=None), self.job(id='off', enabled=False))
        self.assertIn('delivered', self.run_notice())
        (url, params), = self.sent
        self.assertTrue(url.endswith('/botsecret/sendMessage'))
        self.assertEqual((params['chat_id'], params['message_thread_id']), ('-100200', '7'))
        self.assertIn('abc123', notice.notice(self.job(), 'repo'))

    def test_problems_are_reported_without_sending_or_failing(self):
        cases = [((), '0 enabled jobs'),
                 ((self.job(), self.job(id='two')), '2 enabled jobs'),
                 ((self.job(deliver='local'),), 'no Telegram delivery'),
                 ((self.job(workdir='/elsewhere'),), '0 enabled jobs')]
        for jobs, expected in cases:
            with self.subTest(expected=expected):
                self.jobs(*jobs)
                self.assertIn(expected, self.run_notice())
        self.assertEqual(self.sent, [])
        self.jobs(self.job()); (self.home / '.env').unlink()
        self.assertIn('no Telegram bot token', self.run_notice())
        (self.home / 'cron/jobs.json').write_text('{broken')
        self.assertIn('unreadable', self.run_notice())

    def test_api_failure_does_not_raise(self):
        self.jobs(self.job())
        def offline(*_, **__): raise OSError('down')
        with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'env-token'}):
            self.assertEqual(notice.main(self.home, self.repo, opener=offline), 'Start notice not sent: OSError.')

    def test_route_parsing(self):
        self.assertEqual(notice.telegram_target('telegram:42'), ('42', None))
        self.assertEqual(notice.telegram_target('local, telegram:-5:9'), ('-5', '9'))
        self.assertIsNone(notice.telegram_target('discord:42'))
        self.assertIsNone(notice.telegram_target(None))


class ProvisionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        self.target = self.home / 'scripts/autowork-start-notice.py'

    def test_copies_refreshes_and_keeps_user_files(self):
        self.assertEqual(defaults.provision_cron_scripts(ROOT / 'skills', self.home), [])
        self.assertEqual(self.target.read_bytes(), SCRIPT.read_bytes())
        self.assertTrue(self.target.stat().st_mode & 0o100)
        self.target.write_text('#!/usr/bin/env python3\n# hermes-toolset: old copy\n')
        defaults.provision_cron_scripts(ROOT / 'skills', self.home)
        self.assertEqual(self.target.read_bytes(), SCRIPT.read_bytes())
        self.target.write_text('my own script\n')
        self.assertEqual(defaults.provision_cron_scripts(ROOT / 'skills', self.home), ['autowork-start-notice.py'])
        self.assertEqual(self.target.read_text(), 'my own script\n')


if __name__ == '__main__':
    unittest.main()
