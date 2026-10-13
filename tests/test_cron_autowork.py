"""Scheduling guidance must bind reporting independently of the invoking surface."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CronAutoworkContractTests(unittest.TestCase):
    def setUp(self):
        self.native = (ROOT / 'skills/cron-autowork/SKILL.md').read_text()
        self.portable = (ROOT / 'adapters/skills/cron-autowork/SKILL.md').read_text()
        self.prose = ' '.join(self.native.split())

    def test_telegram_routing_is_explicit_and_profile_scoped(self):
        for value in ('telegram:CHAT_ID:THREAD_ID', 'TELEGRAM_HOME_CHANNEL',
                      'TELEGRAM_CRON_THREAD_ID', 'failure_deliver'):
            self.assertIn(value, self.native)
        self.assertIn('same verified profile', self.prose)
        self.assertIn('existing explicit delivery restriction', self.prose)

    def test_setup_confirmation_is_separate_from_running_the_job(self):
        self.assertIn('send_message', self.native)
        self.assertIn('setup confirmation', self.native)
        self.assertIn('message_id', self.native)
        self.assertIn('Do not run the job immediately unless requested', self.native)
        self.assertIn('Preview/read-only', self.native)
        self.assertIn('do not blindly resend', self.native)

    def test_generated_prompt_requires_a_nonempty_report_every_occurrence(self):
        template = re.search(r'```text\n(.*?)\n```', self.native, re.S)[1]
        for value in ('every occurrence', 'nonempty', 'unchanged blocker',
                      '[SILENT]', 'automatic cron delivery', 'messaging tool'):
            self.assertIn(value, template)

    def test_portable_host_cannot_silently_fall_back_to_local_reporting(self):
        self.assertIn('Telegram', self.portable)
        self.assertIn('setup confirmation', self.portable)
        self.assertIn('not scheduled', self.portable)
        self.assertIn('not delivered', self.portable)
        self.assertIn('run it immediately', self.portable)

    def test_non_telegram_preferences_do_not_authorize_a_telegram_copy(self):
        self.assertIn('do not add a Telegram copy', self.prose)
        self.assertIn("selected profile's Telegram transport", self.prose)


if __name__ == '__main__':
    unittest.main()
