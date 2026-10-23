"""Selective review exercises committed diffs, never a worker's risk label."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import review_policy, worker


class ReviewPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.command = 'python3 check.py'
        self.put('check.py', f'''from pathlib import Path
import unittest
class Check(unittest.TestCase):
    def test_document_exists(self):
        self.assertTrue(Path('docs/usage.md').is_file())
        Path({str(self.root / 'checked')!r}).touch()
unittest.main()
''')
        self.put('AGENTS.md', 'Full check: python3 check.py\n')
        self.put('tasks/items/T-1.md', '''+++
schema = 1
id = "T-1"
title = "Explain usage"
short = "Usage"
status = "open"
goal = "G"
section = "Now"
rank = 1000
depends_on = []
touches = ["docs/usage.md"]
resources = []
kind = "implementation"
ownership = "worker"
live = "denied"
scope = "Explain usage"
acceptance = ["Usage is explained"]
checks = ["python3 check.py"]
exclusions = []
+++
Accepted documentation task.
''')
        self.put('docs/usage.md', 'Old usage.\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'base')
        self.base = self.git('rev-parse', 'HEAD')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def put(self, path, text):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def merge_candidate(self, baseline):
        candidate = self.git('rev-parse', 'HEAD')
        self.git('checkout', '--detach', baseline)
        self.git('merge', '--no-ff', '--no-edit', candidate)

    def candidate(self, path='docs/usage.md', text='New usage.\n', *, merge=True):
        baseline = self.git('rev-parse', 'HEAD')
        self.put(path, text)
        self.git('add', '.')
        self.git('commit', '-qm', 'candidate')
        if merge:
            self.merge_candidate(baseline)

    def decide(self, **kwargs):
        evidence = {'ok': True, 'tree': self.git('rev-parse', 'HEAD^{tree}'),
                    'commit': self.git('rev-parse', 'HEAD'), 'command': self.command,
                    'result': {'code': 0, 'failures': [], 'timed_out': False,
                               'skips': 0, 'resource_skips': 0}}
        options = dict(evidence=evidence, env={'PI_AUTOWORK_REVIEW': 'auto'})
        options.update(kwargs)
        return review_policy.decide(str(self.repo), 'T-1', **options)

    def test_small_prose_can_skip_only_after_the_gate(self):
        for path in ('docs/usage.md', 'README.md'):
            with self.subTest(path=path):
                self.git('reset', '--hard', self.base)
                self.candidate(path)
                self.assertFalse(self.decide()['required'])
                self.assertTrue(self.decide(evidence=None)['required'])
                self.assertTrue(self.decide(env={})['required'])
                self.assertTrue(self.decide(env={'PI_AUTOWORK_REVIEW': 'invalid'})['required'])

    def test_ordinary_multicommit_candidate_cannot_hide_earlier_code(self):
        self.put('src/auth.py', 'ENABLED = True\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'existing code')
        self.candidate('src/auth.py', 'ENABLED = False\n', merge=False)
        self.candidate(merge=False)
        self.assertEqual(self.git('diff', '--name-only', 'HEAD^1', 'HEAD'), 'docs/usage.md')
        self.assertTrue(self.decide()['required'])

    def test_merged_multicommit_candidate_reviews_earlier_code(self):
        self.put('src/auth.py', 'ENABLED = True\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'existing code')
        baseline = self.git('rev-parse', 'HEAD')
        self.candidate('src/auth.py', 'ENABLED = False\n', merge=False)
        self.candidate(merge=False)
        candidate = self.git('rev-parse', 'HEAD')
        self.git('checkout', '--detach', baseline)
        _, integrate, _ = worker.engine_modules()
        integrate.merge_candidate(str(self.repo), {'baseline': baseline, 'commit': candidate}, baseline)
        self.assertEqual(self.git('rev-list', '--parents', '-n', '1', 'HEAD').split()[1:],
                         [baseline, candidate])
        self.assertEqual(self.git('diff', '--name-only', 'HEAD^1', 'HEAD').splitlines(),
                         ['docs/usage.md', 'src/auth.py'])
        decision = self.decide()
        self.assertTrue(decision['required'])
        self.assertIn('src/auth.py', decision['reason'])

    def test_ordinary_single_commit_keeps_review_without_a_candidate_base(self):
        self.candidate(merge=False)
        self.assertTrue(self.decide()['required'])

    def test_octopus_merge_is_not_a_supported_candidate(self):
        self.candidate('docs/first.md', 'First topic.\n', merge=False)
        first = self.git('rev-parse', 'HEAD')
        self.git('checkout', '--detach', self.base)
        self.candidate('docs/second.md', 'Second topic.\n', merge=False)
        second = self.git('rev-parse', 'HEAD')
        self.git('checkout', '--detach', self.base)
        self.git('merge', '--no-ff', '--no-edit', first, second)
        self.assertEqual(len(self.git('rev-list', '--parents', '-n', '1', 'HEAD').split()), 4)
        self.assertTrue(self.decide()['required'])

    def test_merged_multicommit_prose_can_skip(self):
        self.candidate('docs/another.md', 'Another topic.\n', merge=False)
        self.candidate(merge=False)
        self.merge_candidate(self.base)
        self.assertFalse(self.decide()['required'])

    def test_actual_changed_paths_override_an_innocent_task_scope(self):
        for path in ('src/cache.py', 'src/auth.py', 'src/payments.py', 'migrations/001.sql',
                     '.github/workflows/test.yml', 'package.json', 'tests/conftest.py', 'tests/test_usage.py',
                     'docs/security.md', 'docs/plan.md', 'skills/helper/SKILL.md', 'AGENTS.md'):
            with self.subTest(path=path):
                self.git('reset', '--hard', self.base)
                self.candidate(path)
                self.assertTrue(self.decide()['required'])

    def test_modified_or_deleted_tests_and_renames_still_need_review(self):
        self.candidate('tests/test_existing.py', 'assert True\n')
        self.candidate('tests/test_existing.py', '# weakened\n')
        self.assertTrue(self.decide()['required'])
        baseline = self.git('rev-parse', 'HEAD')
        self.git('rm', 'tests/test_existing.py')
        self.git('commit', '-qm', 'delete test')
        self.merge_candidate(baseline)
        self.assertTrue(self.decide()['required'])
        baseline = self.git('rev-parse', 'HEAD')
        self.git('mv', 'docs/usage.md', 'docs/new.md')
        self.git('commit', '-qm', 'rename')
        self.merge_candidate(baseline)
        self.assertTrue(self.decide()['required'])

    def test_symlinks_and_large_changes_are_not_plain_documentation(self):
        (self.repo / 'docs/link.md').symlink_to('../check.py')
        self.git('add', '.')
        self.git('commit', '-qm', 'symlink')
        self.merge_candidate(self.base)
        self.assertTrue(self.decide()['required'])
        self.candidate(text='line\n' * 401)
        self.assertTrue(self.decide()['required'])

    def test_review_requirements_in_the_task_or_instructions_are_preserved(self):
        for path in ('tasks/items/T-1.md', 'AGENTS.md', 'docs/AGENTS.md'):
            with self.subTest(path=path):
                self.git('reset', '--hard', self.base)
                original = (self.repo / path).read_text() if (self.repo / path).exists() else ''
                self.put(path, original + '\nIndependent review is required.\n')
                self.git('add', '.')
                self.git('commit', '-qm', 'require review')
                self.candidate()
                self.assertTrue(self.decide()['required'])

    def test_live_or_owner_acceptance_and_nonregular_instructions_keep_review(self):
        for requirement in ('live device qualification', 'manual approval by the owner'):
            with self.subTest(requirement=requirement):
                self.git('reset', '--hard', self.base)
                path = self.repo / 'tasks/items/T-1.md'
                path.write_text(path.read_text() + '\nRequires ' + requirement + '.\n')
                self.git('add', '.')
                self.git('commit', '-qm', 'acceptance requirement')
                self.candidate()
                self.assertTrue(self.decide()['required'])
        self.git('reset', '--hard', self.base)
        self.put('.github/CODEOWNERS', '* @maintainers\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'owner review policy')
        self.candidate()
        self.assertTrue(self.decide()['required'])
        self.git('reset', '--hard', self.base)
        (self.repo / 'AGENTS.md').unlink()
        (self.repo / 'AGENTS.md').symlink_to('elsewhere.md')
        self.git('add', '.')
        self.git('commit', '-qm', 'indirect instructions')
        self.candidate()
        self.assertTrue(self.decide()['required'])

    def test_changed_missing_or_uncovered_task_contract_keeps_review(self):
        path = self.repo / 'tasks/items/T-1.md'
        self.put('tasks/items/T-1.md', path.read_text().replace('python3 check.py', 'python3 extra.py'))
        self.git('add', '.')
        self.git('commit', '-qm', 'extra check')
        self.candidate()
        self.assertTrue(self.decide()['required'])
        self.put('tasks/items/T-1.md', path.read_text().replace('python3 extra.py', 'python3 check.py'))
        self.candidate()
        self.assertTrue(self.decide()['required'])
        self.git('rm', 'tasks/items/T-1.md')
        self.git('commit', '-qm', 'missing task')
        self.candidate(text='Another usage.\n')
        self.assertTrue(self.decide()['required'])

    def test_affected_only_exception_and_stale_receipts_do_not_cover_a_full_check(self):
        self.candidate()
        evidence = {'ok': True, 'tree': self.git('rev-parse', 'HEAD^{tree}'),
                    'commit': self.git('rev-parse', 'HEAD'), 'command': self.command,
                    'result': {'code': 0, 'failures': [], 'timed_out': False,
                               'skips': 0, 'resource_skips': 0}}
        cases = [dict(evidence, tree='old'), dict(evidence, command='true'),
                 dict(evidence, selection={'full': False}),
                 dict(evidence, result=dict(evidence['result'], code=1)),
                 dict(evidence, result=dict(evidence['result'], skips=None)),
                 dict(evidence, result=dict(evidence['result'], timed_out=True))]
        for case in cases:
            with self.subTest(evidence=case):
                self.assertTrue(self.decide(evidence=case)['required'])

    def test_descendant_gate_does_not_prove_an_earlier_batch_step(self):
        self.candidate()
        step = self.git('rev-parse', 'HEAD')
        self.candidate('docs/another.md', 'A later change.\n')
        evidence = {'ok': True, 'tree': self.git('rev-parse', 'HEAD^{tree}'),
                    'commit': self.git('rev-parse', 'HEAD'), 'command': self.command,
                    'result': {'code': 0, 'failures': [], 'timed_out': False,
                               'skips': 0, 'resource_skips': 0}}
        self.git('checkout', '--detach', step)
        self.assertTrue(self.decide(evidence=evidence)['required'])

    def test_documentation_dependency_files_are_not_prose(self):
        for path in ('docs/requirements.txt', 'docs/constraints.txt', 'docs/CMakeLists.txt'):
            with self.subTest(path=path):
                self.git('reset', '--hard', self.base)
                self.candidate(path, 'sphinx==8.0.0\n')
                self.assertTrue(self.decide()['required'])

    def test_unparsed_instruction_obligations_retain_the_reviewer(self):
        for instruction in ('Before completion, also run python3 lint.py',
                            'Manual approval is required for documentation updates',
                            'Full check: python3 another_check.py'):
            with self.subTest(instruction=instruction):
                self.git('reset', '--hard', self.base)
                self.put('AGENTS.md', 'Full check: python3 check.py\n' + instruction + '\n')
                self.git('add', '.')
                self.git('commit', '-qm', 'repository obligations')
                self.candidate()
                self.assertTrue(self.decide()['required'])

    def test_dirty_checkout_cannot_reuse_a_committed_gate(self):
        self.candidate()
        state = self.root / 'state'
        with patch.dict(os.environ, PI_AUTOWORK_VALIDATE=self.command,
                        PI_AUTOWORK_CHECK_ROOT=str(self.root / 'slots')):
            self.assertEqual(worker.full_suite_gate(state, 'T-1', str(self.repo)), (True, ''))
            evidence = worker.review_gate_evidence(state, str(self.repo))
            self.assertIsNotNone(evidence)
            self.put('docs/usage.md', 'Changed by a test, not checked.\n')
            self.assertTrue(self.decide(evidence=evidence)['required'])
            self.assertIsNone(worker.review_gate_evidence(state, str(self.repo)))

    def test_failed_git_inspection_does_not_skip(self):
        self.assertTrue(self.decide()['required'])  # first commit has no parent
        self.assertTrue(review_policy.decide(str(self.root), 'T-1', evidence={},
                                             env={'PI_AUTOWORK_REVIEW': 'auto'})['required'])

    def test_single_and_batch_verification_record_skips_without_calling_a_model(self):
        self.candidate()
        state = self.root / 'state'
        environment = {k: v for k, v in os.environ.items() if not k.startswith('PI_AUTOWORK_')}
        environment.update(PI_AUTOWORK_REVIEW='auto', PI_AUTOWORK_VALIDATE=self.command,
                           PI_AUTOWORK_REVIEW_ROOT=str(self.root), PI_AUTOWORK_CHECK_ROOT=str(self.root / 'slots'))
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        os.chdir(self.repo)
        # Only external inference is replaced: Git inspection and the shell check run for real.
        with patch.dict(os.environ, environment, clear=True), patch.object(
                worker.pi_runtime, 'job', side_effect=AssertionError('unnecessary model review')):
            self.assertEqual(worker.verify(str(state), 'T-1'), 0)
            self.assertTrue((self.root / 'checked').exists())
            receipt = json.loads((state / 'review-policy/T-1.json').read_text())
            self.assertFalse(receipt['required'])
            self.assertEqual(receipt['tree'], self.git('rev-parse', 'HEAD^{tree}'))
            self.assertEqual(worker.batch_review(str(state), 'T-1', str(self.repo),
                                                 {'note': 'passed', 'evidence': worker.review_gate_evidence(state, str(self.repo))}), 0)
            self.assertTrue(json.loads(worker.batch_record(str(state), 'T-1').read_text())['ok'])

    def test_skipped_batch_receipts_do_not_survive_policy_or_planning_drift(self):
        self.candidate(merge=False)
        candidate = self.git('rev-parse', 'HEAD')
        self.git('checkout', '-qb', 'landing', self.base)
        self.git('merge', '--no-ff', '--no-edit', candidate)
        merged = self.git('rev-parse', 'HEAD')
        state = self.root / 'state'
        environment = {k: v for k, v in os.environ.items() if not k.startswith('PI_AUTOWORK_')}
        environment.update(PI_AUTOWORK_REVIEW='auto', PI_AUTOWORK_VALIDATE=self.command,
                           PI_AUTOWORK_CHECK_ROOT=str(self.root / 'slots'))
        with patch.dict(os.environ, environment, clear=True), patch.object(
                worker.pi_runtime, 'job', side_effect=AssertionError('unnecessary model review')):
            self.assertEqual(worker.full_suite_gate(state, 'T-1', str(self.repo)), (True, ''))
            gate = {'note': 'passed', 'evidence': worker.review_gate_evidence(state, str(self.repo))}
            self.assertEqual(worker.batch_review(state, 'T-1', str(self.repo), gate), 0)
            record = worker.batch_record(state, 'T-1')
            saved = record.read_text()
            self.assertEqual(worker.batched_verdict(state, 'T-1', str(self.repo)), (True, ''))
            for field, value in (('version', 'old-policy'), ('mode', '0'), ('command', 'true'),
                                 ('required', None)):
                data = json.loads(saved)
                data['review_policy'][field] = value
                record.write_text(json.dumps(data))
                self.assertIsNone(worker.batched_verdict(state, 'T-1', str(self.repo)))
            for path in ('docs/other.md', 'tasks/items/T-1.md', 'AGENTS.md'):
                with self.subTest(path=path):
                    self.git('reset', '--hard', self.base)
                    text = (self.repo / path).read_text() if (self.repo / path).exists() else ''
                    self.put(path, text + '\nIndependent review is required.\n')
                    self.git('add', '.')
                    self.git('commit', '-qm', 'new contract')
                    self.git('merge', '--no-ff', '--no-edit', candidate)
                    record.write_text(saved)
                    self.assertIsNone(worker.batched_verdict(state, 'T-1', str(self.repo)))
            self.git('reset', '--hard', merged)
            record.write_text(saved)
            with patch.dict(os.environ, PI_AUTOWORK_REVIEW='1'):
                self.assertIsNone(worker.batched_verdict(state, 'T-1', str(self.repo)))

    def test_optimistic_auto_without_a_gate_keeps_the_reviewer(self):
        self.candidate()
        state = self.root / 'state'
        environment = {k: v for k, v in os.environ.items() if not k.startswith('PI_AUTOWORK_')}
        environment.update(PI_AUTOWORK_REVIEW='auto', PI_AUTOWORK_OPTIMISTIC='1',
                           PI_AUTOWORK_VALIDATE=self.command, PI_AUTOWORK_REVIEW_ROOT=str(self.root),
                           PI_AUTOWORK_CHECK_ROOT=str(self.root / 'slots'))
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        os.chdir(self.repo)
        with patch.dict(os.environ, environment, clear=True), patch.object(
                worker.pi_runtime, 'job', return_value={'text': 'PI_AUTOWORK_VERIFY: fail concrete defect',
                                                       'ok': True}):
            self.assertEqual(worker.verify(str(state), 'T-1'), 1)
            self.assertFalse((self.root / 'checked').exists())
            receipt = json.loads((state / 'review-policy/T-1.json').read_text())
            self.assertTrue(receipt['required'])
            self.assertEqual(worker.batch_review(state, 'T-1', str(self.repo),
                                                 {'note': worker.OPTIMISTIC_NOTE}), 1)
            self.assertFalse(json.loads(worker.batch_record(state, 'T-1').read_text())['ok'])


if __name__ == '__main__':
    unittest.main()
