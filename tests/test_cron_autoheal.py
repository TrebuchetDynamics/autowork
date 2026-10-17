"""Bounded self-repair of one saved cron, never a replacement schedule."""
import fcntl
import importlib.util
import sys
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location('cron_autoheal', ROOT / 'scripts/heal-owner-cron.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AutohealTests(unittest.TestCase):
    def setUp(self):
        self.module = load()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.home = self.root / 'profiles/alpha'
        (self.home / 'cron').mkdir(parents=True)
        (self.home / 'config.yaml').touch()
        self.path = self.home / 'cron/jobs.json'
        self.job = dict(id='job-1', name='Autowork', enabled=True, workdir=str(self.repo),
                        prompt='Scope: ONLY A-1; no push.' + self.module.wiring.MARKER + 'old instructions',
                        skills=['autogoal', 'custom'], skill='autogoal', deliver='local',
                        schedule={'minutes': 10}, repeat={'times': None, 'completed': 1},
                        model='existing', script=None, no_agent=False)
        self.write(self.job)

    def write(self, job):
        self.path.write_text(json.dumps({'jobs': [job, {'id': 'unrelated', 'prompt': 'retain'}]}))

    def read(self):
        return json.loads(self.path.read_text())['jobs'][0]

    def run_heal(self, **kw):
        return self.module.heal(self.root, 'alpha', 'job-1', self.repo, **kw)

    def edit(self, command, **kwargs):
        self.assertEqual(command[:6], ['hermes', '-p', 'alpha', 'cron', 'edit', 'job-1'])
        self.assertEqual(kwargs['env']['HERMES_HOME'], str(self.root))
        self.assertNotIn('HERMES_PROFILE', kwargs['env'])
        job = self.read()
        job['prompt'] = command[command.index('--prompt') + 1]
        job['skills'] = [command[i + 1] for i, item in enumerate(command) if item == '--skill']
        job['skill'] = job['skills'][0]
        job['repeat']['completed'] += 1  # An occurrence can finish during readback.
        self.write(job)
        return subprocess.CompletedProcess(command, 0, '', '')

    def test_repairs_exact_job_once_and_next_run_is_noop(self):
        with patch.object(self.module, 'run_edit', side_effect=self.edit) as run:
            first = self.run_heal(apply=True)
            second = self.run_heal(apply=True)
        self.assertEqual(first['state'], 'updated_verified')
        self.assertEqual(second['state'], 'unchanged')
        self.assertEqual(run.call_count, 1)
        after = self.read()
        self.assertTrue(after['prompt'].startswith('Scope: ONLY A-1; no push.'))
        self.assertIn('heal-owner-cron.py', after['prompt'])
        self.assertEqual(after['skills'], ['autowork:autowork', 'custom'])
        for key in ('schedule', 'enabled', 'deliver', 'model', 'workdir', 'script'):
            self.assertEqual(self.job[key], after[key])
        self.assertEqual(json.loads(self.path.read_text())['jobs'][1], {'id': 'unrelated', 'prompt': 'retain'})

    def test_preview_and_paused_job_do_not_write(self):
        before = self.path.read_bytes()
        with patch.object(self.module, 'run_edit') as run:
            self.assertEqual(self.run_heal()['state'], 'would_update')
            self.assertFalse((self.home / 'autowork/cron-heal').exists())
            self.job['enabled'] = False
            self.write(self.job)
            paused = self.path.read_bytes()
            self.assertEqual(self.run_heal(apply=True)['state'], 'paused')
            self.assertEqual(self.path.read_bytes(), paused)
        run.assert_not_called()
        self.assertNotEqual(before, paused)

    def test_scheduler_observations_can_advance_during_edit(self):
        self.write({**self.job, 'manual_run_at': 'now', 'manual_run_prompt': 'one occurrence'})
        def completed(command, **kwargs):
            result = self.edit(command, **kwargs)
            job = self.read()
            job.update(last_failure={'at': 'later', 'detail': 'failure'}, failure_streak=2,
                       fire_claim=None, run_claim=None, last_dispatch={'kind': 'on-time'},
                       last_fire_error={'at': 'later'}, preflight_alerted=True,
                       last_delivery_unverified={'at': 'later'}, last_delivery_queued=True,
                       monitor_state={'hash': 'new'}, quota_hold_until='later',
                       quota_hold_cron_expr='*/10 * * * *', unreachable_retry={'attempt': 1})
            job.pop('manual_run_at')
            job.pop('manual_run_prompt')
            self.write(job)
            return result
        with patch.object(self.module, 'run_edit', side_effect=completed):
            self.assertEqual(self.run_heal(apply=True)['state'], 'updated_verified')

    def test_timeout_readback_can_prove_edit_without_second_attempt(self):
        def timeout(command, **kwargs):
            self.edit(command, **kwargs)
            raise subprocess.TimeoutExpired(command, 60)
        with patch.object(self.module, 'run_edit', side_effect=timeout) as run:
            self.assertEqual(self.run_heal(apply=True)['state'], 'updated_verified')
            self.assertEqual(self.run_heal(apply=True)['state'], 'unchanged')
        self.assertEqual(run.call_count, 1)

    def test_uncertain_write_is_not_replayed_on_next_tick(self):
        with patch.object(self.module, 'run_edit', side_effect=subprocess.TimeoutExpired('hermes', 60)) as run:
            first = self.run_heal(apply=True)
            second = self.run_heal(apply=True)
        self.assertEqual(first['state'], 'edit_uncertain')
        self.assertEqual(second['state'], 'edit_uncertain')
        self.assertEqual(run.call_count, 1)

    def test_late_success_reconciles_saved_attempt(self):
        with patch.object(self.module, 'run_edit', side_effect=subprocess.TimeoutExpired('hermes', 60)):
            self.run_heal(apply=True)
        job = self.read()
        job['prompt'] = self.module.wiring.owner_prompt(job['prompt'], True)
        job['skills'] = self.module.wiring.autowork_skills(job)
        job['skill'] = job['skills'][0]
        self.write(job)
        with patch.object(self.module, 'run_edit') as run:
            self.assertEqual(self.run_heal(apply=True)['state'], 'updated_verified')
        run.assert_not_called()

    def test_wrong_repository_unmanaged_and_duplicate_jobs_are_refused(self):
        with patch.object(self.module, 'run_edit') as run:
            with self.assertRaises(ValueError):
                self.module.heal(self.root, 'alpha', 'job-1', self.root, apply=True)
            self.write({**self.job, 'prompt': 'Custom unmanaged instructions'})
            with self.assertRaises(ValueError):
                self.run_heal(apply=True)
            self.path.write_text(json.dumps([self.job, self.job]))
            with self.assertRaises(ValueError):
                self.run_heal(apply=True)
        run.assert_not_called()

    def test_cli_names_its_own_refusals_but_hides_other_error_text(self):
        import contextlib, io, sys
        argv = ['heal', '--root', str(self.root), '--profile', 'alpha', '--job-id', 'job-1', '--repo', str(self.root)]
        def cli(**patched):
            out = io.StringIO()
            with patch.object(sys, 'argv', argv), contextlib.redirect_stdout(out), \
                 patch.object(self.module, 'heal', **patched):
                self.assertEqual(self.module.main(), 1)
            return json.loads(out.getvalue())
        refusal = cli(side_effect=self.module.Refused('saved workdir must match the explicit existing repository'))
        self.assertEqual(refusal, {'state': 'refused', 'reason': 'saved workdir must match the explicit existing repository'})
        leaked = cli(side_effect=ValueError('prompt text: SECRET'))
        self.assertEqual(leaked, {'state': 'refused', 'reason': 'ValueError'})

    def test_readback_protects_delivery_and_future_configuration_fields(self):
        for field in ('deliver', 'future_policy'):
            with self.subTest(field=field):
                self.write(self.job)
                def bad_edit(command, **kwargs):
                    result = self.edit(command, **kwargs)
                    self.write({**self.read(), field: 'changed'})
                    return result
                with patch.object(self.module, 'run_edit', side_effect=bad_edit):
                    result = self.run_heal(apply=True)
                self.assertEqual(result['state'], 'edit_uncertain')
                # Keep an uncertain edit pinned; do not silently adopt changed config.
                with patch.object(self.module, 'run_edit') as run:
                    self.assertEqual(self.run_heal(apply=True)['state'], 'edit_uncertain')
                run.assert_not_called()

    def test_script_only_and_other_roles_are_not_development_jobs(self):
        for changes in ({'no_agent': True}, {'prompt': self.module.wiring.ROLE_MARKER + 'delivery-sync\n'},
                        {'prompt': self.module.wiring.ROLE_MARKER + 'research-design\n'}):
            self.write({**self.job, **changes})
            with self.assertRaises(ValueError):
                self.run_heal(apply=True)

    def test_cli_runs_real_scoped_subprocess_and_second_run_is_noop(self):
        binary = self.root / 'bin'
        binary.mkdir()
        cli = binary / 'hermes'
        cli.write_text("#!" + sys.executable + "\n" + """
import json, os, pathlib, sys
args = sys.argv[1:]
assert args[:5] == ['-p', 'alpha', 'cron', 'edit', 'job-1']
assert 'HERMES_PROFILE' not in os.environ
home = pathlib.Path(os.environ['HERMES_HOME']) / 'profiles' / args[1]
path = home / 'cron/jobs.json'
data = json.loads(path.read_text())
job = data['jobs'][0]
job['prompt'] = args[args.index('--prompt') + 1]
job['skills'] = [args[i + 1] for i, arg in enumerate(args) if arg == '--skill']
job['skill'] = job['skills'][0]
path.write_text(json.dumps(data))
""")
        cli.chmod(0o700)
        command = [sys.executable, str(ROOT / 'scripts/heal-owner-cron.py'),
                   '--root', str(self.root), '--profile', 'alpha', '--job-id', 'job-1',
                   '--repo', str(self.repo), '--apply']
        env = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ.get('PATH', ''),
                   HERMES_PROFILE='wrong')
        for expected in ('updated_verified', 'unchanged'):
            proc = subprocess.run(command, env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)['state'], expected)

    def test_overlapping_healers_and_changed_configuration_never_write(self):
        directory = self.home / 'autowork/cron-heal'
        directory.mkdir(parents=True)
        with (directory / 'job-1.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with patch.object(self.module, 'run_edit') as run:
                self.assertEqual(self.run_heal(apply=True)['state'], 'busy')
            run.assert_not_called()
        actual = self.module.exact_job
        count = 0
        def concurrent(home, job_id):
            nonlocal count
            count += 1
            if count == 2:
                self.write({**self.job, 'deliver': 'new-user-destination'})
            return actual(home, job_id)
        with patch.object(self.module, 'exact_job', side_effect=concurrent), patch.object(self.module, 'run_edit') as run:
            self.assertEqual(self.run_heal(apply=True)['state'], 'configuration_changed')
        run.assert_not_called()

    def test_invalid_executable_does_not_poison_future_repair(self):
        executable = self.root / 'invalid-hermes'
        executable.write_text('not an executable format')
        executable.chmod(0o700)
        self.assertEqual(self.run_heal(apply=True, hermes=str(executable))['state'], 'launcher_unavailable')
        with patch.object(self.module, 'run_edit', side_effect=self.edit):
            self.assertEqual(self.run_heal(apply=True)['state'], 'updated_verified')

    def test_missing_cli_does_not_poison_future_repair(self):
        with patch.object(self.module, 'run_edit', side_effect=self.module.NotLaunched('hermes')):
            self.assertEqual(self.run_heal(apply=True)['state'], 'launcher_unavailable')
        with patch.object(self.module, 'run_edit', side_effect=self.edit) as run:
            self.assertEqual(self.run_heal(apply=True)['state'], 'updated_verified')
        self.assertEqual(run.call_count, 1)

    def test_ambiguous_pause_and_duplicate_fields_refuse_before_write(self):
        with patch.object(self.module, 'run_edit') as run:
            self.write({**self.job, 'enabled': 1})
            with self.assertRaises(ValueError):
                self.run_heal(apply=True)
            self.path.write_text(json.dumps([self.job]).replace('"enabled": true', '"enabled": false, "enabled": true'))
            with self.assertRaises(ValueError):
                self.run_heal(apply=True)
        run.assert_not_called()

    def test_profile_traversal_and_symlink_state_are_refused(self):
        with self.assertRaises(ValueError):
            self.module.heal(self.root, '../alpha', 'job-1', self.repo, apply=True)
        (self.home / 'autowork').symlink_to(self.repo, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.run_heal(apply=True)


if __name__ == '__main__':
    unittest.main()
