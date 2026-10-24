"""Offline Hermes overlap classification through the shared install/start seam."""
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


def digest(job):
    # Independent encoding of the documented execution-contract format.
    return hashlib.sha256(json.dumps(job, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'project'
        self.home = self.root / 'hermes'
        self.store = self.home / 'profiles/monitor/cron/jobs.json'
        self.store.parent.mkdir(parents=True)
        self.job = dict(id='observer', name='Progress', workdir=str(self.repo), enabled=True,
                        prompt='Report autowork progress; no edits, dispatch, claims or service actions.',
                        skills=[], enabled_toolsets=['read'])
        self.policy = self.root / 'observers.json'
        self.review = dict(version=1, repo=str(self.repo), hermes_home=str(self.home), observers=[
            dict(profile='monitor', id='observer', sha256=digest(self.job))])
        env = patch.dict(os.environ, PI_AUTOWORK_HERMES_HOME=str(self.home),
                         PI_AUTOWORK_HERMES_OBSERVERS=str(self.policy))
        env.start()
        self.addCleanup(env.stop)
        self.save([self.job])

    def save(self, jobs, review=None):
        self.store.write_text(json.dumps({'jobs': jobs}))
        self.policy.write_text(json.dumps(self.review if review is None else review))

    def test_exact_review_exempts_only_the_observer(self):
        with patch.dict(os.environ, PI_AUTOWORK_HERMES_OBSERVERS=''):
            self.assertEqual(hermes_jobs(self.repo), 'monitor: Progress')
        self.assertEqual(hermes_jobs(self.repo), '')
        self.save([self.job, dict(id='writer', name='Development', workdir=str(self.repo), skill='autowork')])
        self.assertEqual(hermes_jobs(self.repo), 'monitor: Development')

    def test_execution_contract_drift_requires_new_review(self):
        for key, value in [('workdir', str(self.root / 'other')), ('prompt', 'Observe only'),
                           ('skills', ['other']), ('skill', 'other'), ('enabled_toolsets', ['terminal']),
                           ('tools', ['write']), ('script', 'other.py'), ('future_option', True)]:
            with self.subTest(key=key):
                self.save([{**self.job, key: value}])
                self.assertTrue(hermes_jobs(self.repo))

    def test_unknown_malformed_or_ambiguous_review_refuses(self):
        reviews = [[], {**self.review, 'version': True}, {**self.review, 'repo': '/other'},
                   {**self.review, 'hermes_home': '/other'},
                   {**self.review, 'observers': self.review['observers'] * 2}]
        for fields in [dict(id='unknown'), dict(profile='unknown'), dict(sha256='invalid'), dict(extra=1)]:
            review = copy.deepcopy(self.review)
            review['observers'][0].update(fields)
            reviews.append(review)
        for review in reviews:
            with self.subTest(review=review):
                self.save([self.job], review)
                self.assertTrue(hermes_jobs(self.repo))
        self.save([self.job, dict(self.job, enabled=False)])
        self.assertTrue(hermes_jobs(self.repo))
        for text in ['{', '{"version":1,"version":1}', 'NaN', '1e999']:
            with self.subTest(policy=text):
                self.policy.write_text(text)
                self.assertTrue(hermes_jobs(self.repo))

    def test_development_skill_is_never_an_observer(self):
        skill = self.root / 'skills/autowork'
        skill.mkdir(parents=True)
        alias = self.root / 'alias'
        alias.symlink_to(skill, target_is_directory=True)
        for fields in [dict(skill='autowork'), dict(skills=['autowork:autowork']),
                       dict(skills=['/skills/autowork/./SKILL.md']),
                       dict(skills=[str(alias / 'SKILL.md')]), dict(skills='autowork')]:
            with self.subTest(fields=fields):
                job = {**self.job, 'prompt': 'Observe progress only', **fields}
                review = copy.deepcopy(self.review)
                review['observers'][0]['sha256'] = digest(job)
                self.save([job], review)
                self.assertTrue(hermes_jobs(self.repo))
                with patch.dict(os.environ, PI_AUTOWORK_HERMES_OBSERVERS=''):
                    self.assertTrue(hermes_jobs(self.repo))

    def test_observations_and_inactive_jobs_preserve_behavior(self):
        self.save([{**self.job, 'last_run_at': 'later', 'next_run_at': 'next', 'last_status': 'ok'}])
        self.assertEqual(hermes_jobs(self.repo), '')
        for fields in [dict(enabled=False), dict(paused_at='earlier'), dict(state='paused')]:
            with self.subTest(fields=fields):
                self.save([{**self.job, **fields, 'prompt': 'Changed autowork contract'}])
                self.assertEqual(hermes_jobs(self.repo), '')

    def test_broken_discovery_links_refuse_but_absent_stores_do_not(self):
        paths = [self.home / 'cron', self.home / 'profiles/broken-profile',
                 self.home / 'profiles/broken-cron/cron', self.home / 'profiles/broken-store/cron/jobs.json']
        for policy in ('', str(self.policy)):
            self.save([self.job] if policy else [])
            with patch.dict(os.environ, PI_AUTOWORK_HERMES_OBSERVERS=policy):
                for path in paths:
                    with self.subTest(policy=bool(policy), path=str(path.relative_to(self.home))):
                        path.parent.mkdir(parents=True, exist_ok=True)
                        self.assertEqual(hermes_jobs(self.repo), '')
                        path.symlink_to(self.root / 'missing')
                        try:
                            self.assertTrue(hermes_jobs(self.repo))
                        finally:
                            path.unlink()

    def test_malformed_cron_store_never_becomes_no_competing_jobs(self):
        writer = dict(id='writer', workdir=str(self.repo), skill='autowork')
        malformed = ['{', '{}', 'null', '{"jobs":null}', '{"jobs":{}}', '{"jobs":[null]}',
                     '{"jobs":[],"jobs":[]}', '{"jobs":[],"unknown":NaN}',
                     '{"jobs":[],"unknown":1e999}',
                     json.dumps({'jobs': [writer, 'bad row']})]
        for fields in [dict(workdir=123), dict(workdir='/bad\x00/path'), dict(skills='autowork'),
                       dict(prompt=[]), dict(enabled='false'), dict(paused_at=[]), dict(state=[]), dict(id=[])]:
            malformed.append(json.dumps({'jobs': [{**writer, **fields}]}))
        # A damaged unrelated profile cannot silently hide an additional writer,
        # with or without a valid observer policy.
        broken = self.home / 'profiles/other/cron/jobs.json'
        broken.parent.mkdir(parents=True)
        for policy in ('', str(self.policy)):
            self.save([self.job] if policy else [])
            with patch.dict(os.environ, PI_AUTOWORK_HERMES_OBSERVERS=policy):
                for content in malformed:
                    with self.subTest(policy=bool(policy), content=content):
                        broken.write_text(content)
                        self.assertTrue(hermes_jobs(self.repo))
        broken.unlink()
        self.assertEqual(hermes_jobs(self.repo), '')


if __name__ == '__main__':
    unittest.main()
