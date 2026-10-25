"""Offline overlap policy at the runner's startup/install classification seam."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pi-autowork'))
from pi_autowork.cli import hermes_jobs


def binding(job):
    # Independent encoding of the documented contract, not the production helper.
    return hashlib.sha256(json.dumps(job, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'project'
        self.home = self.root / 'hermes'
        self.store = self.home / 'profiles/monitor/cron/jobs.json'
        self.store.parent.mkdir(parents=True)
        self.observer = dict(id='observer', name='Progress', workdir=str(self.repo), enabled=True,
                             prompt='Report autowork progress. No edits, dispatch, claims or service actions.',
                             skills=[], enabled_toolsets=['read'])
        self.policy = self.root / 'observers.json'
        self.review = dict(version=1, repo=str(self.repo), hermes_home=str(self.home), observers=[
            dict(profile='monitor', id='observer', sha256=binding(self.observer))])
        self.env = patch.dict(os.environ, {'PI_AUTOWORK_HERMES_HOME': str(self.home),
                                           'PI_AUTOWORK_HERMES_OBSERVERS': str(self.policy)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.save([self.observer])

    def save(self, jobs, review=None):
        self.store.write_text(json.dumps({'jobs': jobs}))
        self.policy.write_text(json.dumps(self.review if review is None else review))

    def test_reviewed_observer_does_not_hide_another_writer(self):
        with patch.dict(os.environ, {'PI_AUTOWORK_HERMES_OBSERVERS': ''}):
            self.assertEqual(hermes_jobs(self.repo), 'monitor: Progress')
        self.assertEqual(hermes_jobs(self.repo), '')
        writer = dict(id='writer', name='Development', workdir=str(self.repo), skills=['autowork:autowork'])
        self.save([self.observer, writer])
        self.assertEqual(hermes_jobs(self.repo), 'monitor: Development')

    def test_every_execution_contract_change_invalidates_review(self):
        for key, value in [('prompt', 'Run autowork'), ('workdir', str(self.root / 'elsewhere')),
                           ('skills', ['other']), ('skill', 'other'), ('enabled_toolsets', ['terminal']),
                           ('tools', ['write']), ('future_execution_option', True),
                           ('workdir', '/invalid\x00/project')]:
            with self.subTest(key=key):
                changed = {**self.observer, key: value}
                self.save([changed])
                self.assertTrue(hermes_jobs(self.repo))

    def test_bad_or_ambiguous_review_fails_closed(self):
        invalid = [[], {**self.review, 'version': True}, {**self.review, 'repo': '/other'},
                   {**self.review, 'hermes_home': '/other'},
                   {**self.review, 'observers': self.review['observers'] * 2}]
        for fields in [dict(id='unknown'), dict(profile='unknown'), dict(sha256='broken'),
                       dict(extra='unknown')]:
            review = copy.deepcopy(self.review)
            review['observers'][0].update(fields)
            invalid.append(review)
        for review in invalid:
            with self.subTest(review=review):
                self.save([self.observer], review)
                self.assertTrue(hermes_jobs(self.repo))
        self.save([self.observer, dict(self.observer, enabled=False)])
        self.assertTrue(hermes_jobs(self.repo))
        for text in ['{', '{"version":1,"version":1}', 'NaN']:
            with self.subTest(text=text):
                self.policy.write_text(text)
                self.assertTrue(hermes_jobs(self.repo))

    def test_explicit_development_skill_cannot_be_reviewed_as_observer(self):
        skill_dir = self.root / 'skills/autowork'
        skill_dir.mkdir(parents=True)
        (skill_dir / 'SKILL.md').write_text('Development skill')
        alias = self.root / 'skill-alias'
        alias.symlink_to(skill_dir, target_is_directory=True)
        for fields in [dict(skills=['autowork:autowork']), dict(skill='autowork'),
                       dict(skills=['/skills/autowork/SKILL.md']),
                       dict(skills=[str(skill_dir) + '/./SKILL.md']),
                       dict(skills=[str(skill_dir) + '/../autowork/SKILL.md']),
                       dict(skills=[str(alias / 'SKILL.md')]),
                       dict(skills=['/skills/invalid\x00/SKILL.md']), dict(skills='autowork')]:
            with self.subTest(fields=fields):
                job = {**self.observer, **fields}
                review = copy.deepcopy(self.review)
                review['observers'][0]['sha256'] = binding(job)
                self.save([job], review)
                self.assertTrue(hermes_jobs(self.repo))

    def test_scheduler_observations_do_not_invalidate_but_inactive_jobs_stay_ignored(self):
        self.save([{**self.observer, 'last_run_at': 'later', 'next_run_at': 'next', 'last_status': 'ok'}])
        self.assertEqual(hermes_jobs(self.repo), '')
        for fields in [dict(enabled=False), dict(paused_at='earlier'), dict(state='paused')]:
            with self.subTest(fields=fields):
                self.save([{**self.observer, **fields, 'prompt': 'Changed autowork contract'}])
                self.assertEqual(hermes_jobs(self.repo), '')


if __name__ == '__main__':
    unittest.main()
