"""Opt-in admission at the canonical landing and background-check public seams."""
import json
import os
from pathlib import Path
import sys
import subprocess
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import main_check
from test_landing import LandingFixture


class PostMergeBarrierTests(LandingFixture):
    def setUp(self):
        super().setUp()
        self.runner.integration = None
        self.runner.state = self.repo.parent / 'state'
        self.runner.state.mkdir()
        self.runner.stop = False
        self.runner.toolset = str(Path(__file__).resolve().parents[2])
        self.runner.resolved_for = ''
        self.runner.train = None
        self.runner.prefix_landing = None
        self.runner.MAIN_CHECK_WAIT = 0
        policy = patch.dict(os.environ, PI_AUTOWORK_POST_MERGE_POLICY='revision-barrier',
                            PI_AUTOWORK_MAIN_CHECK='python3 check.py', PI_AUTOWORK_OPTIMISTIC='1')
        policy.start()
        self.addCleanup(policy.stop)

    def verdict(self, rev, **changes):
        value = dict(schema=1, revision=rev, run_id='attempt', complete=True, status='green', failures=[])
        value.update(changes)
        path = self.runner.state / 'post-merge-verdict.json'
        path.write_text(json.dumps(value))
        record = dict(state='green', rev=rev, green=rev, finished=1, policy='revision-barrier',
                      command='python3 check.py', timeout=900, run_id='attempt', exit_code=0,
                      verdict_path=str(path))
        main_check.write(self.runner.state, record)
        return record

    def test_each_landing_requires_its_exact_completed_verdict_even_after_restart(self):
        original = self.head('main')
        self.assertTrue(self.runner.fast_forward_main())  # no baseline verdict yet
        self.verdict(original)
        self.assertEqual(self.runner.fast_forward_main(), '')  # merge A
        a = self.head('main')
        self.git(self.integ, 'commit', '-q', '--allow-empty', '-m', 'B')
        b = self.head('pi-autowork/s')
        self.runner = type(self.runner).__new__(type(self.runner))  # restart: disk is authoritative
        self.runner.repo, self.runner.base = str(self.repo), 'main'
        self.runner.integ_branch, self.runner.state = 'pi-autowork/s', self.repo.parent / 'state'
        for changes in ({}, {'revision': original}, {'complete': False}, {'status': 'red', 'failures': ['failed']},
                        {'run_id': 'stale'}, {'status': 'green', 'failures': ['failed']}, {'schema': True}):
            with self.subTest(changes=changes):
                self.verdict(a, **changes)
                if not changes:
                    (self.runner.state / 'post-merge-verdict.json').unlink()
                self.assertTrue(self.runner.fast_forward_main())
                self.assertEqual(self.head('main'), a)
        self.verdict(a)
        (self.runner.state / 'post-merge-verdict.json').write_text('[]')
        self.assertTrue(self.runner.fast_forward_main())
        for state in ('running', 'red', 'broken', 'aborted'):
            record = self.verdict(a)
            main_check.write(self.runner.state, dict(record, state=state))
            self.assertTrue(self.runner.fast_forward_main())
        record = self.verdict(a)
        main_check.write(self.runner.state, dict(record, exit_code=137))
        self.assertTrue(self.runner.fast_forward_main())
        self.verdict(a)
        self.assertEqual(self.runner.fast_forward_main(), '')
        self.assertEqual(self.head('main'), b)
        self.assertEqual(self.runner.fast_forward_main(), '')  # no-op is not a new merge

    def test_main_advance_during_landing_cannot_spend_an_older_green(self):
        original = self.head('main')
        self.verdict(original)
        from pi_autowork import landing
        real = landing.land_around_edits
        def advance(*args, **kwargs):
            self.git(self.repo, 'commit', '-q', '--allow-empty', '-m', 'outside advance')
            return real(*args, **kwargs)
        with patch.object(landing, 'land_around_edits', advance):
            self.assertTrue(self.runner.fast_forward_main())
        self.assertNotEqual(self.head('main'), original)
        self.assertNotEqual(self.head('main'), self.head('pi-autowork/s'))

    def test_terminal_command_and_verdict_must_agree(self):
        rev = self.head('main')
        for code, changes, expected in ((0, {}, 'green'), (1, {}, 'broken'), (137, {}, 'broken'),
                                         (0, {'complete': False}, 'broken'),
                                         (0, {'status': 'red', 'failures': ['failed']}, 'broken')):
            with self.subTest(code=code, changes=changes):
                record = self.verdict(rev, **changes)
                self.runner.finish_main_check_result(record, code, '', {})
                self.assertEqual(main_check.read(self.runner.state)['state'], expected)
                self.assertEqual(bool(self.runner.fast_forward_main()), expected != 'green')
                if expected == 'green':
                    # The successful landing now itself requires a new revision verdict.
                    self.assertNotEqual(self.head('main'), rev)
                    rev = self.head('main')
                    self.git(self.integ, 'commit', '-q', '--allow-empty', '-m', 'next candidate')

    def test_barrier_does_not_automatically_migrate_canonical_main(self):
        from pi_autowork import task_migrate
        before = self.head('main')
        with patch.object(task_migrate, 'intent', return_value=True), \
                patch('pi_autowork.coordinator.subprocess.run', side_effect=AssertionError('automatic migration')):
            self.assertFalse(self.runner.convert_deferred())
        self.assertEqual(self.head('main'), before)
        self.assertIn('revision-barrier', self.runner.conversion_blocker)

    def prepare_command(self):
        """The fixture command consumes the same environment as a consumer's real check."""
        from pi_autowork import task_commands
        for repo in (self.repo, self.integ):
            self.git(repo, 'config', 'user.name', 'T')
            self.git(repo, 'config', 'user.email', 't@example.invalid')
        task_commands.cmd_goal(self.integ, 'G', title='Fixture', source='fixture', priority=1)
        script = self.integ / 'check.py'
        script.write_text('import json, os, time\ntime.sleep(.1)\n'
                          'v = dict(schema=1, revision=os.environ["AUTOWORK_POST_MERGE_REVISION"], '
                          'run_id=os.environ["AUTOWORK_POST_MERGE_RUN_ID"], complete=True, '
                          'status=os.environ.get("TEST_POST_STATUS", "red"), '
                          'failures=[] if os.environ.get("TEST_POST_STATUS") == "green" else ["project:test_value"])\n'
                          'open(os.environ["AUTOWORK_POST_MERGE_VERDICT"], "w").write(json.dumps(v))\n'
                          'raise SystemExit(0 if v["status"] == "green" else 1)\n')
        self.git(self.integ, 'add', '.')
        self.git(self.integ, 'commit', '-qm', 'check command')
        rev = self.head('main')
        # Install the fixture command on main as an external advance, not a barrier bypass.
        self.git(self.repo, 'merge', '--ff-only', 'pi-autowork/s')
        rev = self.head('main')
        self.runner.scratch_checkout = lambda name, revision: str(self.integ)
        self.runner.main_check_port_lease = lambda: None
        self.runner.job_environment = lambda **extra: dict(os.environ, **extra)
        return script, rev

    def drain_check(self):
        end = time.monotonic() + 10
        while main_check.read(self.runner.state).get('state') == 'running' and time.monotonic() < end:
            time.sleep(.05)
            self.runner.check_main()

    def test_background_command_adopts_and_records_one_red_repair_without_reverting(self):
        from pi_autowork import task_commands
        script, rev = self.prepare_command()
        with patch.dict(os.environ, PI_AUTOWORK_CHECK_SLOTS='0'):
            self.runner.check_main()
            running = main_check.read(self.runner.state)
            self.assertEqual(running['state'], 'running')
            # Adopt using the same durable identity as a reloaded coordinator.
            self.runner.check_main()
            self.assertEqual(main_check.read(self.runner.state)['run_id'], running['run_id'])
            self.drain_check()
            self.assertEqual(main_check.read(self.runner.state)['state'], 'red')
            self.runner.check_main()
        tasks = task_commands.cmd_list(self.integ, worktree=True)
        self.assertEqual(len(tasks), 1)
        task = task_commands.cmd_show(self.integ, tasks[0]['id'], worktree=True)
        self.assertIn(rev, task['scope'])
        self.assertIn('project:test_value', task['notes'])
        self.assertFalse(task['draft'], task['missing_fields'])
        self.assertTrue(task_commands.cmd_why(self.integ, task['id'])['eligible'])
        self.assertEqual(self.head('main'), rev)
        self.assertEqual((self.repo / 'check.py').read_bytes(), script.read_bytes())
        self.assertTrue(self.runner.fast_forward_main())
        before = (self.runner.state / 'post-merge-verdict.json').read_bytes()
        candidate = subprocess.run(task['checks'][0], shell=True, cwd=self.integ,
                                   env=dict(os.environ, TEST_POST_STATUS='green'), capture_output=True, text=True)
        self.assertEqual(candidate.returncode, 0, candidate.stderr)
        self.assertEqual((self.runner.state / 'post-merge-verdict.json').read_bytes(), before)
        request = self.runner.state / 'requests/recheck-main'
        request.parent.mkdir(exist_ok=True)
        request.write_text(rev + '\n')
        with patch.dict(os.environ, PI_AUTOWORK_CHECK_SLOTS='0', TEST_POST_STATUS='green'):
            end = time.monotonic() + 10
            while (request.exists() or main_check.read(self.runner.state).get('state') != 'green') and time.monotonic() < end:
                time.sleep(.05)
                self.runner.check_main()
        self.assertEqual(main_check.read(self.runner.state)['state'], 'green')
        self.assertEqual(len(task_commands.cmd_list(self.integ, worktree=True)), 1)
        self.assertEqual(self.runner.fast_forward_main(), '')

    def test_deferred_red_repair_survives_a_recheck_and_refused_commit(self):
        from pi_autowork import task_commands
        _, rev = self.prepare_command()
        self.runner.session_busy = lambda: True
        with patch.dict(os.environ, PI_AUTOWORK_CHECK_SLOTS='0'):
            self.runner.check_main()
            self.drain_check()
        self.assertEqual(len(main_check.read(self.runner.state)['repair_pending']), 1)
        request = self.runner.state / 'requests/recheck-main'
        request.parent.mkdir(exist_ok=True)
        request.write_text(rev)
        with patch.dict(os.environ, PI_AUTOWORK_CHECK_SLOTS='0', TEST_POST_STATUS='green'):
            end = time.monotonic() + 10
            while request.exists() and time.monotonic() < end:
                time.sleep(.05)
                self.runner.check_main()
            self.drain_check()
        self.assertEqual(main_check.read(self.runner.state)['state'], 'green')
        self.assertEqual(len(main_check.read(self.runner.state)['repair_pending']), 1)
        self.runner.session_busy = lambda: False
        hook = self.repo / '.git/hooks/pre-commit'
        hook.write_text('#!/bin/sh\nexit 1\n')
        hook.chmod(0o755)
        self.runner.check_main()  # task writes survive the refused bookkeeping commit
        self.assertEqual(len(main_check.read(self.runner.state)['repair_pending']), 1)
        self.assertEqual(len(task_commands.cmd_list(self.integ, worktree=True)), 1)
        hook.unlink()
        self.runner.check_main()
        self.assertEqual(main_check.read(self.runner.state)['repair_pending'], [])
        self.assertEqual(len(task_commands.cmd_list(self.integ)), 1)
        self.assertEqual(self.git(self.integ, 'status', '--porcelain'), '')


if __name__ == '__main__':
    import unittest
    unittest.main()
