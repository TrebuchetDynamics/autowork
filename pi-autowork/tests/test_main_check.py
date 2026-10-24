"""Main's full offline check after a landing (TOOLSET-176-98)."""
import ast
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import main_check  # noqa: E402


class MainCheckTests(unittest.TestCase):
    def test_coordinator_settle_and_main_check_phases_stay_bounded(self):
        """Keep these orchestration flows and their named phases small enough to review."""
        source = Path(__file__).resolve().parents[2] / 'Src/pi_autowork/coordinator.py'
        coordinator = next(node for node in ast.parse(source.read_text()).body
                           if isinstance(node, ast.ClassDef) and node.name == 'Coordinator')
        roots = ('settle', 'check_main', 'finish_main_check')
        methods = [node for node in coordinator.body if isinstance(node, ast.FunctionDef)
                   and any(node.name == name or node.name.startswith(name + '_') for name in roots)]
        self.assertTrue(set(roots).issubset(node.name for node in methods))
        for method in methods:
            with self.subTest(method=method.name):
                complexity = 1
                for node in ast.walk(method):
                    if isinstance(node, (ast.If, ast.IfExp, ast.For, ast.AsyncFor, ast.While,
                                         ast.ExceptHandler, ast.comprehension)):
                        complexity += 1
                    elif isinstance(node, ast.BoolOp):
                        complexity += len(node.values) - 1
                self.assertLessEqual(method.end_lineno - method.lineno + 1, 80)
                self.assertLessEqual(complexity, 40)

    def test_failures_are_read_from_unittest_and_check_output(self):
        log = ('CHECK tests (50 modules)\n'
               'FAIL: test_core_plan (test_preflight.PreflightTests.test_core_plan)\n'
               'ERROR: test_bundle (test_ui_taste_bundle.UiTasteBundleTests.test_bundle)\n'
               'FAIL: test_core_plan (test_preflight.PreflightTests.test_core_plan)\n'
               'UNEXPECTED SUCCESS: test_fixed (test_other.OtherTests.test_fixed)\n'
               'TIMEOUT: /repo/tests after 1800s\n')
        self.assertEqual(main_check.failures(log), ['test_preflight.PreflightTests.test_core_plan',
                                                     'test_ui_taste_bundle.UiTasteBundleTests.test_bundle',
                                                     'test_other.OtherTests.test_fixed', '/repo/tests (timed out)'])

    def test_flutter_failures_are_named_before_the_process_exits_abnormally(self):
        """A Flutter failure line followed by a crash is a TEST_FAILURE, not 'no result'."""
        log = ('00:02 +0 -1: opening the database [E]\n'
               '  Expected: a row\n'
               '  Actual: no rows\n'
               '00:02 +0 -1: Some tests failed.\n'
               'Oops; flutter has exited unexpectedly: "Bad state: No element".\n')
        self.assertEqual(main_check.failures(log), ['opening the database'])
        self.assertEqual(main_check.result_class(log, 1), 'TEST_FAILURE')
        self.assertEqual(main_check.result_class(log, -6), 'TEST_FAILURE')
        self.assertEqual(main_check.result_class(log, -6, timed_out=True), 'TIMEOUT')
        self.assertEqual(main_check.result_class(log, None), 'TEST_FAILURE')

    def test_a_flutter_check_is_complete_at_its_terminal_line(self):
        """A consumer whose Full check is `flutter test` could never read as complete, so its gate
        called every run incomplete and the consumer started wrapping the suite in a Python harness
        (a Flutter consumer, 2026-10-22). Flutter's last line says the suite ran to its end."""
        cmd = 'flutter pub get --offline --enforce-lockfile && flutter test --no-pub --concurrency=1'
        root = Path(tempfile.mkdtemp(prefix='flutter-check-'))
        self.addCleanup(lambda: subprocess.run(['rm', '-rf', str(root)]))
        passed = 'Resolving dependencies...\n00:01 +0: loading test/a_test.dart\n00:12 +125: All tests passed!\n'
        failed = ('00:02 +0 -1: opening the database [E]\n  Expected: a row\n'
                  '00:12 +123 ~1 -2: Some tests failed.\n')
        crashed = ('00:02 +0 -1: opening the database [E]\n'
                   'Oops; flutter has exited unexpectedly: "Bad state: No element".\n')
        self.assertTrue(main_check.complete_results(passed, root, cmd))
        self.assertTrue(main_check.complete_results(failed, root, cmd))  # complete, with named failures
        self.assertFalse(main_check.complete_results(crashed, root, cmd))  # died before its summary
        self.assertFalse(main_check.complete_results(passed + passed, root, cmd))  # two runs in one log
        # A Python unittest command still needs its own summary, not Flutter's.
        self.assertFalse(main_check.complete_results(passed, root, 'python3 -m unittest discover -s tests'))

    def test_a_harness_crash_without_a_test_result_is_not_a_pass_or_test_failure(self):
        log = 'Oops; flutter has exited unexpectedly: "Bad state: No element".\n'
        for code, expected in ((-6, 'HARNESS_ERROR'), (1, 'INCOMPLETE'), (0, 'PASS')):
            with self.subTest(code=code):
                self.assertEqual(main_check.result_class(log, code), expected)
        self.assertEqual(main_check.result_class(log, 0, complete=False), 'INCOMPLETE')
        self.assertEqual(main_check.result_class(log, -6, stopped=True), 'PROCESS_INTERRUPTED')
        self.assertEqual(main_check.result_class(log, -6, environment=True), 'ENVIRONMENT_FAILURE')

    def test_a_background_main_check_yields_to_reviews(self):
        """It re-checks what already landed; the review that lands the next task goes first."""
        with tempfile.TemporaryDirectory() as folder, \
                patch.dict(os.environ, PI_AUTOWORK_CHECK_ROOT=str(Path(folder) / 'slots')):
            (Path(folder) / 'slots').mkdir(mode=0o700)
            seen = {}
            for background in (False, True):
                out = Path(folder) / f'nice-{background}'
                result = main_check.run_command(f'{sys.executable} -c "import os; print(os.nice(0))" > {out}', folder, 30,
                                                Path(folder) / 'progress.json', background=background)
                self.assertEqual(result, (0, False), f'child did not finish: background={background}')
                seen[background] = int(out.read_text())
            self.assertEqual(seen[False], os.nice(0))
            # The kernel caps niceness at 19: inside main's own niced check this test starts at 10.
            self.assertEqual(seen[True], min(19, seen[False] + main_check.BACKGROUND_NICE),
                             f'parent={os.nice(0)}, ready children={seen}')

    def test_a_background_main_check_yields_to_reviews_with_inherited_niceness(self):
        """Re-run the ordinary fixture as main does; never renice the suite itself."""
        script = ('import os, sys, unittest; '
                  'print(os.nice(max(0, int(sys.argv[1]) - os.nice(0))), flush=True); '
                  'unittest.main(module="test_main_check", argv=["unittest", '
                  '"MainCheckTests.test_a_background_main_check_yields_to_reviews"])')
        for niceness in (10, 19):
            with self.subTest(niceness=niceness):
                result = subprocess.run([sys.executable, '-c', script, str(niceness)],
                                        cwd=Path(__file__).resolve().parent, capture_output=True, text=True,
                                        timeout=90)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(int(result.stdout), max(niceness, os.nice(0)))

    def test_the_full_check_comes_from_validate_or_agents_md(self):
        """TOOLSET-180-72: the repository declares its whole offline suite once."""
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(main_check.full_check(root, {}), '')
            Path(root, 'AGENTS.md').write_text('# Rules\n\n- Full check: `python3 scripts/check.py`\n')
            self.assertEqual(main_check.full_check(root, {}), 'python3 scripts/check.py')
            self.assertEqual(main_check.full_check(root, {'PI_AUTOWORK_VALIDATE': 'make test'}), 'make test')
            self.assertEqual(main_check.command({}, root), 'python3 scripts/check.py')  # main check falls back
            self.assertEqual(main_check.command({'PI_AUTOWORK_MAIN_CHECK': 'x'}, root), 'x')
        self.assertEqual(main_check.failures('FAILED tests/test_a.py::test_b - x\n    --- FAIL: TestC (0.1s)\n'),
                         ['tests/test_a.py::test_b', 'TestC'])

    def test_the_check_slot_pool_does_not_follow_the_environment(self):
        """One host-wide pool: a cron job or a systemd unit without XDG_RUNTIME_DIR derived a
        second pool, with its own PI_AUTOWORK_CHECK_SLOTS, so the limit was never host-wide."""
        uid = os.getuid()
        runtime = Path(f'/run/user/{uid}')
        expected = (runtime if runtime.is_dir() else Path('/var/tmp')) / f'autowork-checks-{uid}'
        self.assertEqual(main_check.slot_home(), expected)
        with tempfile.TemporaryDirectory() as elsewhere, patch.dict(
                os.environ, XDG_RUNTIME_DIR=str(Path(elsewhere) / 'stale'), PI_AUTOWORK_CHECK_ROOT=elsewhere):
            self.assertEqual(main_check.slot_home(), expected, 'the environment cannot move the pool')
            self.assertEqual(main_check.slot_root(), Path(elsewhere), 'the override names it')
        with tempfile.TemporaryDirectory() as loose, patch.dict(os.environ, PI_AUTOWORK_CHECK_ROOT=loose):
            os.chmod(loose, 0o777)
            self.assertRaises(ValueError, main_check.slot_root)  # the pool stays private

    def test_a_review_is_admitted_before_waiting_main_checks_until_one_has_waited_half_an_hour(self):
        """Every runner's main check held the host's slots while a review that lands work
        waited behind them."""
        import fcntl

        class Asked(Exception):
            pass

        def ahead(background):
            seen = []
            def waiting(count):
                seen.append(count)
                raise Asked
            with self.assertRaises(Asked), main_check.check_slot(waiting, background):
                pass
            return seen[0]

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, PI_AUTOWORK_CHECK_ROOT=tmp,
                                                               PI_AUTOWORK_CHECK_SLOTS='1'):
            os.chmod(tmp, 0o700)
            held = []
            def hold(name):
                f = open(Path(tmp) / name, 'a')
                fcntl.flock(f, fcntl.LOCK_EX)
                held.append(f)
            try:
                hold('slot-0')  # a running check
                hold(f'wait-1-{time.monotonic_ns() - 10**9:020d}-1')  # a main check queued first
                self.assertEqual(ahead(background=False), 1)  # only the running check
                self.assertEqual(ahead(background=True), 2)
                hold(f'wait-1-{time.monotonic_ns() - 1801 * 10**9:020d}-2')  # waited over half an hour
                self.assertEqual(ahead(background=False), 2)
            finally:
                for f in held:
                    f.close()

    def test_reruns_are_alone_in_their_directory_and_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tests = root / 'tests'
            tests.mkdir()
            (tests / 'test_sample.py').write_text(
                'from pathlib import Path\nimport time, unittest\n'
                'class Sample(unittest.TestCase):\n'
                '    def test_pass(self): Path("ran").touch()\n'
                '    def test_fail(self): self.fail("still broken")\n'
                '    @unittest.skip("not exercised")\n'
                '    def test_skip(self): pass\n'
                '    def test_slow(self): time.sleep(30)\n')
            log, receipt = root / 'check.log', root / 'reruns.json'
            for ids, want in [(['test_pass', 'test_fail', 'test_skip', 'test_slow'], ['test_pass']),
                              ([f'test_missing_{i}' for i in range(10)] + ['test_pass'], [])]:
                with self.subTest(ids=ids):
                    (tests / 'ran').unlink(missing_ok=True)
                    log.write_text('CHECK tests (1 modules)\n' + ''.join(
                        f'FAIL: {name} (test_sample.Sample.{name})\n' for name in ids)
                        + 'Ran 4 tests in 0.01s\n\nFAILED (failures=4)\n')
                    main_check.rerun_failures(log, root, receipt, 'abc123', timeout=1)
                    self.assertEqual(json.loads(receipt.read_text())['flaky'],
                                     [f'test_sample.Sample.{name}' for name in want])
                    self.assertEqual((tests / 'ran').exists(), bool(want))
                    self.assertFalse((root / 'ran').exists())

    def test_red_main_publishes_read_only_evidence_and_keeps_the_last_five_revisions(self):
        from pi_autowork.coordinator import Coordinator
        from pi_autowork.common import git, git_ok

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, state = root / 'repo', root / 'state'
            repo.mkdir()
            state.mkdir()
            self.assertTrue(git_ok(repo, 'init', '-q'))
            runner = Coordinator.__new__(Coordinator)
            runner.repo, runner.state = repo, state
            runner.maintain = lambda **_: None
            (repo / 'test_sample.py').write_text(
                'import unittest\nclass Sample(unittest.TestCase):\n'
                '    def test_fail(self): self.fail("still broken")\n')
            log = state / 'main-check.log'
            log.write_text('FAIL: test_fail (test_sample.Sample.test_fail)\n'
                           'Ran 1 test in 0.01s\n\nFAILED (failures=1)\n')
            (state / 'main-check.exit').write_text('1\n')
            common = Path(git(repo, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
            evidence = common / 'autowork-execution/main-evidence'
            try:
                for index in range(7):
                    rev = f'{index:040x}'
                    main_check.rerun_failures(log, repo, state / 'main-check-reruns.json', rev)
                    runner.finish_main_check(dict(rev=rev, green='last-green'))
                    bundle = evidence / rev
                    self.assertEqual(main_check.read(state)['evidence'], str(bundle))
                    saved = json.loads((bundle / 'main_check.json').read_text())
                    self.assertEqual((saved['rev'], saved['green'], saved['state']), (rev, 'last-green', 'red'))
                    self.assertEqual((bundle / 'main-check.log').read_text(), log.read_text())
                    self.assertEqual((bundle / 'main-check.exit').read_text(), '1\n')
                    reruns = (bundle / 'main-check-reruns.log').read_text()
                    self.assertIn('-m unittest test_sample.Sample.test_fail', reruns)
                    self.assertIn('exit code: 1', reruns)
                    self.assertIn('still broken', reruns)
                    self.assertEqual(json.loads((bundle / 'flaky_history.json').read_text()), {})
                    self.assertFalse(bundle.stat().st_mode & 0o222)
                    self.assertTrue(all(not path.stat().st_mode & 0o222 for path in bundle.iterdir()))
                self.assertEqual(sorted(path.name for path in evidence.iterdir()),
                                 [f'{index:040x}' for index in range(2, 7)])
                # A recheck of the same revision replaces its snapshot, not a sixth directory.
                (state / 'main-check.exit').write_text('0\n')
                runner.finish_main_check(dict(rev=rev))
                self.assertEqual(json.loads((bundle / 'main_check.json').read_text())['state'], 'green')
                self.assertEqual((bundle / 'main-check-reruns.log').read_text(), '')
                log.write_text('Fatal error\n')
                (state / 'main-check.exit').write_text('137\n')
                (state / 'main-check-reruns.log').unlink()
                runner.finish_main_check(dict(rev=rev))
                crashed = json.loads((bundle / 'main_check.json').read_text())
                self.assertEqual(crashed['state'], 'recheck')
                self.assertEqual(crashed['checked_rev'], rev)
            finally:
                if evidence.exists():
                    for path in evidence.iterdir():
                        path.chmod(0o700)  # allow TemporaryDirectory to remove read-only snapshots

    def test_a_validation_hold_is_cleared_once_when_main_repairs_its_named_failures(self):
        from pi_autowork.coordinator import Coordinator

        failure = 'test_sample.Sample.test_fail'
        prefix = 'the full check has new failures the base does not: '
        long_failure = 'test_' + 'x' * (600 - len(prefix) - 5)
        cases = [
            ('intervening reused green', [failure], prefix + failure, 'validation', 20, 'green', False),
            ('truncated at name boundary', [long_failure], prefix + long_failure, 'validation', 20, 'green', False),
            ('retained full verdict', [long_failure], prefix + long_failure, 'validation', 20, 'green', True),
            ('retained unmatched failure', [long_failure], prefix + long_failure, 'validation', 20, 'green', False),
            ('matching subset', [failure, 'test_other.Other.test_fail'], prefix + failure, 'validation', 20, 'green', True),
            ('unrelated red', ['test_other.Other.test_fail'], prefix + failure, 'validation', 20, 'green', False),
            ('one unmatched failure', [failure], prefix + failure + ', test_new.New.test_fail', 'validation', 20, 'green', False),
            ('unnamed failure', [failure], 'the full check crashed', 'validation', 20, 'green', False),
            ('truncated failures', [failure], prefix + failure + ' (+1 more)', 'validation', 20, 'green', False),
            ('other cause', [failure], prefix + failure, 'blocker', 20, 'green', False),
            ('hold predates red', [failure], prefix + failure, 'validation', 5, 'green', False),
            ('hold follows green', [failure], prefix + failure, 'validation', 40, 'green', False),
            ('main still red', [failure], prefix + failure, 'validation', 20, 'red', False),
        ]
        for label, failures, reason, cause, held_at, state, cleared in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                runner = Coordinator.__new__(Coordinator)
                runner.state, runner.cfg = root, {'git_common': str(root / 'common')}
                runner.stop = runner.restart_pending = False
                runner.reviewer_version = lambda: 'unchanged-reviewer'
                runner.provision_and_reverify = lambda *args: False
                runner.seen = {'reverify-T': 'unchanged-reviewer'}
                row = dict(task='T', state='held', cause=cause, reason=reason, commit='candidate', attempt=2)
                slots = root / 'common/autowork-execution/slots'
                slots.mkdir(parents=True)
                (slots / 'T.json').write_text(json.dumps(dict(row, held_at=held_at)))
                evidence = root / 'common/autowork-execution/main-evidence'
                for rev, record in [('red-revision', dict(state='red', failures=failures, finished=10)),
                                    ('green-revision', dict(state=state, finished=30))]:
                    bundle = evidence / rev
                    bundle.mkdir(parents=True)
                    main_check.write(bundle, dict(record, rev=rev))
                if label == 'intervening reused green':
                    runner.passed_on_tree = lambda *args: 'batch'
                    with patch('pi_autowork.coordinator.time.time', return_value=15), \
                            patch('pi_autowork.coordinator.LOG.say'):
                        runner.check_main_reuse_result({'state': 'red'}, 'intermediate-green', 'check')
                if label.startswith('retained'):
                    verdict = prefix + long_failure
                    if label == 'retained unmatched failure':
                        verdict += ', test_new.New.test_fail'
                    log_path = root / 'validation.log'
                    log_path.write_text('AUTOWORK_HOLD_REASON: ' + verdict + '\n')
                    row['checks'] = {'command_receipt': {'log': str(log_path)}}
                main_check.write(root, dict(state=state, rev='green-revision', finished=30))
                calls = []

                def engine(*argv):
                    calls.append(argv)
                    return {'outcome': 'CLEARED', 'tasks': ['T']}

                runner.engine = engine
                with patch('pi_autowork.coordinator.LOG.say') as log:
                    runner.reverify_held([row])
                    self.assertEqual(calls, [('--parallel-clear-held', 'T')] if cleared else [])
                    if cleared:
                        self.assertEqual(runner.seen['T'], 'pending')
                        self.assertTrue(runner.settled)
                        self.assertIn('green-r', log.call_args.args[0])
                        self.assertIn('T', log.call_args.args[0])
                    # Even if validation holds again, including after a coordinator reload,
                    # the same green revision must not clear the slot a second time.
                    runner.seen = {'reverify-T': 'unchanged-reviewer'}
                    runner.reverify_held([row])
                    self.assertEqual(len(calls), int(cleared))
                    self.assertEqual(log.call_count, int(cleared))

    def test_three_distinct_flaky_revisions_make_one_hardening_trigger(self):
        from pi_autowork import maintainer
        from pi_autowork.coordinator import Coordinator

        test_id = 'test_sample.Sample.test_pass'
        with tempfile.TemporaryDirectory() as tmp:
            runner = Coordinator.__new__(Coordinator)
            runner.state, runner.repo = Path(tmp), tmp
            runner.maintain = lambda **_: None
            (runner.state / 'main-check.exit').write_text('1\n')
            (runner.state / 'main-check.log').write_text(f'FAIL: test_pass ({test_id})\n')
            record = {}
            for rev, count in [('a', 1), ('a', 1), ('b', 2), ('c', 3), ('d', 3)]:
                (runner.state / 'main-check-reruns.json').write_text(json.dumps({'rev': rev, 'flaky': [test_id]}))
                runner.finish_main_check(dict(record, rev=rev))
                record = main_check.read(runner.state)
                self.assertEqual(record['state'], 'green')
                self.assertEqual(len(record['flaky_history'][test_id]), count)
                found = maintainer.triggers([], record,
                    reported_flakes=maintainer.last(runner.state).get('flaky_tests', []))
                self.assertEqual(len(found), int(rev == 'c'))
                if found:
                    self.assertEqual(found[0][:2], ('MAIN', 'flaky test'))
                    self.assertIn(test_id, maintainer.prompt(found, '/repo', 'autowork tasks'))
                    maintainer.remember(runner.state, trigger_key=maintainer.key(found),
                                        found=found, outcome='merged')

    def test_flaky_batches_handle_overflow_without_repeating_main_repairs(self):
        from pi_autowork import maintainer
        from pi_autowork.coordinator import Coordinator

        for count, acknowledged, red, calls in [(1, 0, True, 1), (12, 12, True, 1),
                                                 (13, 12, False, 1), (12, 0, True, 2)]:
            with self.subTest(count=count, acknowledged=acknowledged), tempfile.TemporaryDirectory() as tmp:
                subprocess.run(['git', 'init', '-q', tmp], check=True)
                runner = Coordinator.__new__(Coordinator)
                runner.state, runner.repo, runner.integ, runner.stop = Path(tmp), tmp, tmp, False
                runner.in_flight = runner.session_busy = lambda: False
                runner.scratch_checkout, runner.drop_scratch = lambda _: tmp, lambda _: None
                runner.toolset, runner.tasks_cli, runner.verify_timeout = Path(__file__).resolve().parents[2], 'autowork tasks', 1
                prompts = []
                runner.pi_job = lambda *args: (not prompts.append(args[3]), '')
                history = {f'test_sample.Sample.test_{i:02}': ['a', 'b', 'c'] for i in range(count)}
                if acknowledged:
                    previous = dict(list(history.items())[:acknowledged])
                    found = maintainer.triggers([], {'flaky_history': previous})
                    maintainer.remember(runner.state, trigger_key=maintainer.key(found),
                                        found=found, outcome='merged')
                main_check.write(runner.state, dict(state='red' if red else 'green', flaky_history=history,
                                                   failures=['test_other.Other.test_broken'] if red else []))
                with patch('pi_autowork.coordinator.dirty', return_value=False):
                    for _ in range(3):
                        runner.maintain(main_only=True)
                self.assertEqual(len(prompts), calls)
                if red:
                    self.assertIn('(main red)', prompts[-1])

    def test_unfinished_or_wrong_revision_reruns_cannot_excuse_main(self):
        from pi_autowork.coordinator import Coordinator

        test_id = 'test_sample.Sample.test_pass'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tests = root / 'tests'
            tests.mkdir()
            (tests / 'test_sample.py').write_text(
                'import os, unittest\nclass Sample(unittest.TestCase):\n'
                '    def test_pass(self): self.assertNotIn("FULL_RUN", os.environ)\n'
                '    @unittest.expectedFailure\n    def test_unexpected(self): pass\n')
            log = root / 'main-check.log'
            receipt = root / 'main-check-reruns.json'
            (root / 'main-check.exit').write_text('1\n')
            runner = Coordinator.__new__(Coordinator)
            runner.state, runner.repo = root, tmp
            runner.maintain = lambda **_: None
            for modules in [1, 2]:
                with self.subTest(modules=modules), log.open('w') as output:
                    # modules=2 represents another process dying without a summary.
                    output.write(f'CHECK tests ({modules} modules)\n')
                    output.flush()
                    subprocess.run([sys.executable, '-m', 'unittest', 'test_sample'], cwd=tests,
                                   env=dict(os.environ, FULL_RUN='1'), stdout=output, stderr=output, check=False)
                main_check.rerun_failures(log, root, receipt, 'abc')
                for revision in ['abc', 'different']:
                    with self.subTest(revision=revision):
                        runner.finish_main_check({'rev': revision})
                        self.assertEqual(main_check.read(root)['state'], 'red')

    def test_a_check_that_crashes_before_any_result_is_broken_not_red(self):
        """TOOLSET-237-35: a tool crash made main red with placeholder 'failing tests'."""
        from pi_autowork import maintainer
        from pi_autowork.coordinator import Coordinator

        crash = ('[warn][wallpaper] Set wallpaper failed {"error":"Bad state: channel unavailable"}\n'
                 'Analyzing app...\nNo issues found! (ran in 24.5s)\n\n'
                 'Oops; flutter has exited unexpectedly: "Bad state: No element".\n'
                 'A crash report has been written to /x/flutter_01.log\n')
        self.assertEqual(main_check.crash_line(crash), 'Oops; flutter has exited unexpectedly: "Bad state: No element".')
        self.assertEqual(main_check.crash_line('a\nlast words\n'), 'last words')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = Coordinator.__new__(Coordinator)
            runner.state, runner.repo = root, tmp
            maintained = []
            runner.maintain = lambda **_: maintained.append(main_check.read(root)['state'])
            (root / 'main-check.log').write_text(crash)
            (root / 'main-check.exit').write_text('1\n')
            runner.finish_main_check({'rev': 'abc123'})
            first = main_check.read(root)
            self.assertEqual((first['state'], first.get('crashed')), ('recheck', 'abc123'))  # once more
            self.assertEqual(maintained, [])
            runner.finish_main_check(dict(first, rev='abc123'))
            record = main_check.read(root)
            self.assertEqual(record['state'], 'broken')
            self.assertIn('Bad state: No element', record['crash'])
            self.assertFalse(record.get('failures'))  # no placeholder test IDs
            self.assertEqual(maintained, ['broken'])
            self.assertEqual(main_check.line(record), 'main check broken at abc123: ' + record['crash'])
            found = maintainer.triggers([], record)
            self.assertEqual([kind for _, kind, _ in found], ['check broken'])
            self.assertIn('Never add a repair task for test names', maintainer.prompt(found, '/repo', 'autowork tasks'))

    def test_crash_line_ranks_terminal_messages_and_uses_the_last_match(self):
        cases = [
            ('Bad state: earlier\nSegmentation fault\nreport saved\n', 'Segmentation fault'),
            ('Fatal error: first\nAborted\nreport saved\n', 'Fatal error: first'),
            ('panic: first\nKilled\nreport saved\n', 'Killed'),
            ('Aborted\nout of memory\nreport saved\n', 'out of memory'),
            ('Bad state: earlier\nTraceback (most recent call last):\n'
             '  File "check.py", line 1, in <module>\n'
             '    raise RuntimeError("broken")\nRuntimeError: broken\nreport saved\n',
             'RuntimeError: broken'),
            ('Traceback (most recent call last):\n  run()\nKeyboardInterrupt\nreport saved\n',
             'KeyboardInterrupt'),
            ('example.Error: not a traceback\nAborted\nreport saved\n', 'Aborted'),
        ]
        for prefix in ('[warn][wallpaper]', '[info]', 'WARNING:'):
            cases.append((f'{prefix} Fatal error: Bad state\nlast words\n\n', 'last words'))
            cases.append((f'core dumped\n{prefix} Killed\nreport saved\n', 'core dumped'))
        for log, expected in cases:
            with self.subTest(log=log):
                self.assertEqual(main_check.crash_line(log), expected)

    def test_alive_rejects_zombies_and_reused_pids(self):
        pid = os.fork()
        if pid == 0:
            os.kill(os.getpid(), signal.SIGSTOP)
            os._exit(0)
        try:
            os.waitpid(pid, os.WUNTRACED)
            start = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]
            self.assertTrue(main_check.alive(pid))  # pre-upgrade records have no start time
            self.assertTrue(main_check.alive(pid, start))
            self.assertFalse(main_check.alive(pid, str(int(start) + 1)))
            os.kill(pid, signal.SIGCONT)
            deadline = time.monotonic() + 5
            while Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0] != 'Z':
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.01)
            self.assertFalse(main_check.alive(pid))
        finally:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        self.assertFalse(main_check.alive(pid, start))

    def test_the_main_check_leases_its_own_port_block(self):
        """Main's check ran with no AUTOWORK_PORT_BASE, so its fixtures defaulted to a block another
        runner's worker had leased on this host; that worker's database container answered on the
        fixture's port and main went red for nothing. The check now leases a block like a worker."""
        import fcntl
        from pi_autowork import coordinator, worker
        from pi_autowork.coordinator import Coordinator
        dispatch, _, _ = worker.engine_modules()
        seen = {}

        class FakeChild:
            pid = os.getpid()

        def fake_popen(argv, **kwargs):
            seen.update(kwargs)
            base = int(kwargs['env']['AUTOWORK_PORT_BASE'])
            block = dispatch.port_lease_dir() / str((base - 20100) // 100 + 1)
            probe = os.open(block, os.O_RDWR)
            try:  # the lease is held through the file descriptor the child inherits
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                os.close(probe)
            return FakeChild()

        with tempfile.TemporaryDirectory() as tmp:
            runner = Coordinator.__new__(Coordinator)
            runner.state, runner.stop, runner.repo, runner.base = Path(tmp), False, tmp, 'main'
            runner.cfg = {'git_common': tmp}
            with patch.object(Coordinator, 'scratch_checkout', return_value=tmp), \
                    patch.object(coordinator.subprocess, 'Popen', side_effect=fake_popen), \
                    patch.object(coordinator.LOG, 'say'):
                runner.check_main_start({}, 'abcdef1234567', 'true')
        base = int(seen['env']['AUTOWORK_PORT_BASE'])
        self.assertTrue(20100 <= base < 20100 + 100 * dispatch.PORT_BLOCKS, base)
        self.assertEqual(len(seen['pass_fds']), 1)
        with self.assertRaises(OSError):
            os.fstat(seen['pass_fds'][0])  # the parent closed its copy: only the child holds the block

    def test_an_exit_receipt_finishes_even_while_the_pid_is_alive(self):
        from pi_autowork.coordinator import Coordinator

        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(write_fd)
            os.read(read_fd, 1)
            os._exit(0)
        os.close(read_fd)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                runner = Coordinator.__new__(Coordinator)
                runner.state, runner.stop = Path(tmp), False
                runner.repo, runner.base = tmp, 'main'
                main_check.write(runner.state, dict(state='running', rev='abcdef123', pid=pid,
                                                    start_time=main_check.start_time(pid)))
                (runner.state / 'main-check.exit').touch()  # shell redirection opens before echo writes
                with patch.dict(os.environ, PI_AUTOWORK_MAIN_CHECK='true'):
                    runner.check_main()
                    self.assertEqual(main_check.read(runner.state)['state'], 'running')
                    (runner.state / 'main-check.exit').write_text('0\n')
                    runner.check_main()
                    self.assertEqual(main_check.read(runner.state)['state'], 'green')
                    os.write(write_fd, b'x')  # bash may exit just after writing its receipt
                    os.waitid(os.P_PID, pid, os.WEXITED | os.WNOWAIT)
                    runner.check_main()
                with self.assertRaises(ChildProcessError):
                    os.waitpid(pid, os.WNOHANG)
        finally:
            os.close(write_fd)
            try:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
            except ProcessLookupError:
                pass

    def test_a_busy_host_delays_the_main_check_at_most_half_an_hour(self):
        """With eight workers a review or a loaded host was nearly always there: main went
        unchecked for hours while it was red."""
        from pi_autowork.coordinator import Coordinator

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, PI_AUTOWORK_MAIN_CHECK='true'):
            runner = Coordinator.__new__(Coordinator)
            runner.state, runner.repo, runner.base, runner.stop = Path(tmp), tmp, 'main', False
            runner.tasks = lambda: [{'task': 'A', 'state': 'integrating'}]
            started = []
            runner.scratch_checkout = lambda *args: started.append(args) and None
            with patch('pi_autowork.coordinator.git', return_value='new'), \
                    patch('os.getloadavg', return_value=(99, 99, 99)):
                for finished, starts in ((time.time() - 60, False), (time.time() - 3600, True)):
                    with self.subTest(finished_ago=round(time.time() - finished)):
                        started.clear()
                        main_check.write(runner.state, {'state': 'green', 'rev': 'old', 'finished': finished})
                        runner.check_main()
                        self.assertEqual(bool(started), starts)

    def test_a_batch_that_passed_on_mains_tree_stands_in_for_the_main_check(self):
        """TOOLSET-336-3c: the runner ran a full main check beside every batch check of main plus
        its candidates, two full suites at once on a loaded host."""
        from pi_autowork.coordinator import Coordinator

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, PI_AUTOWORK_MAIN_CHECK='true'):
            runner = Coordinator.__new__(Coordinator)
            runner.state, runner.repo, runner.base, runner.stop = Path(tmp), tmp, 'main', False
            runner.tasks = lambda: []
            started = []
            runner.scratch_checkout = lambda *args: started.append(args) and None
            receipts = Path(tmp) / 'full-check'
            receipts.mkdir()
            git = lambda repo, *args: 'tree1' if args[-1].endswith('^{tree}') else 'new'
            for receipt, reused in ((dict(ok=True, tree='tree1', command='true', task='batch'), True),
                                    (dict(ok=False, tree='tree1', command='true', task='batch'), False),
                                    (dict(ok=True, tree='tree1', command='python3 other.py', task='batch'), False),
                                    (dict(ok=True, tree='tree2', command='true', task='batch'), False),
                                    (dict(ok=True, tree='tree1', command='true', task='batch',
                                          selection=dict(full=False)), False),
                                    (dict(ok=True, tree='tree1', command='true --affected old..new',
                                          full_command='true', task='batch',
                                          selection=dict(full=False, base='old', head='new')), False),
                                    (dict(ok=True, tree='tree1', command='true --affected old..new',
                                          full_command='true', task='batch',
                                          selection=dict(full=True, base='old', head='new')), True)):
                with self.subTest(receipt=receipt):
                    started.clear()
                    (receipts / 'tree-tree1.json').write_text(json.dumps(receipt))
                    main_check.write(runner.state, {'state': 'green', 'rev': 'old', 'green': 'old', 'finished': 0})
                    with patch('pi_autowork.coordinator.git', side_effect=git), \
                            patch('os.getloadavg', return_value=(0, 0, 0)):
                        runner.check_main()
                    record = main_check.read(runner.state)
                    self.assertEqual(bool(started), not reused)
                    if reused:
                        self.assertEqual((record['state'], record['rev'], record['green'], record['from_receipt']),
                                         ('green', 'new', 'new', 'batch'))

    def test_main_waits_for_a_running_batch_instead_of_checking_beside_it(self):
        from pi_autowork.coordinator import Coordinator

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, PI_AUTOWORK_MAIN_CHECK='true'):
            runner = Coordinator.__new__(Coordinator)
            runner.state, runner.repo, runner.base, runner.stop = Path(tmp), tmp, 'main', False
            runner.tasks = lambda: []
            started = []
            runner.scratch_checkout = lambda *args: started.append(args) and None
            with patch('pi_autowork.coordinator.git', return_value='new'), \
                    patch('os.getloadavg', return_value=(0, 0, 0)):
                # After a restart the record is 'aborted' and carries the last finish as last_finished.
                runner.integration, runner.train = {'task': Coordinator.BATCH}, None
                started.clear()
                main_check.write(runner.state, {'state': 'aborted', 'rev': '', 'last_finished': time.time() - 600})
                runner.check_main()
                self.assertEqual(started, [], 'an aborted record still remembers the last check')
                for job, train, ago, starts in (({'task': Coordinator.BATCH}, None, 600, False),
                                                (None, {'task': Coordinator.BATCH}, 600, False),
                                                ({'task': 'A'}, None, 600, True),
                                                ({'task': Coordinator.BATCH}, None, 3 * Coordinator.MAIN_CHECK_WAIT, True)):
                    with self.subTest(job=job, train=train, ago=ago):
                        started.clear()
                        runner.integration, runner.train = job, train
                        main_check.write(runner.state, {'state': 'green', 'rev': 'old', 'finished': time.time() - ago})
                        runner.check_main()
                        self.assertEqual(bool(started), starts)

    def test_a_green_result_carries_over_planning_only_commits_and_not_code(self):
        """The runner's questions commits moved main 8 times in a day: each took a host check
        slot from a waiting review to check the same code."""
        from pi_autowork.coordinator import Coordinator

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, PI_AUTOWORK_MAIN_CHECK='true'):
            runner = Coordinator.__new__(Coordinator)
            runner.state, runner.repo, runner.base, runner.stop = Path(tmp), tmp, 'main', False
            runner.tasks = lambda: []
            started = []
            runner.scratch_checkout = lambda *args: started.append(args) and None
            for changed, carried in (('BLOCKERS.md\ntasks/items/T.md\ntasks/goals/G.md', True), ('tasks/items/T.md\nREADME.md', False)):
                with self.subTest(changed=changed):
                    started.clear()
                    main_check.write(runner.state, {'state': 'green', 'rev': 'old', 'green': 'old', 'finished': 0})
                    git = lambda *args: changed if args[1] == 'diff' else 'new'
                    with patch('pi_autowork.coordinator.git', side_effect=git):
                        runner.check_main()
                    record = main_check.read(runner.state)
                    self.assertEqual((record['rev'], record['green']) == ('new', 'new'), carried)
                    self.assertEqual(bool(started), not carried)
            # A red main is checked again: its repair may be the planning change.
            started.clear()
            main_check.write(runner.state, {'state': 'red', 'rev': 'old', 'green': 'older', 'finished': 0})
            with patch('pi_autowork.coordinator.git', side_effect=lambda *a: 'tasks/items/T.md' if a[1] == 'diff' else 'new'):
                runner.check_main()
            self.assertTrue(started)

    def test_main_check_waiting_is_visible_and_does_not_consume_its_timeout(self):
        from pi_autowork.coordinator import Coordinator

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,
                PI_AUTOWORK_CHECK_ROOT=tmp, PI_AUTOWORK_CHECK_SLOTS='1',
                PI_AUTOWORK_MAIN_CHECK='sleep .1; touch ran', PI_AUTOWORK_VALIDATE_TIMEOUT='.5'):
            root = Path(tmp)
            runner = Coordinator.__new__(Coordinator)
            runner.state, runner.repo, runner.base, runner.stop = root, tmp, 'main', False
            runner.tasks = lambda: []
            runner.scratch_checkout = lambda *args: tmp
            runner.job_environment = lambda **values: dict(os.environ, **values)
            children, popen = [], subprocess.Popen

            def launch(*args, **kwargs):
                process = popen(*args, **kwargs)
                children.append(process)  # retain Popen while the coordinator adopts/reaps its persisted PID
                return process

            def git_result(repo, *args):
                return str(root / 'common') if '--git-common-dir' in args else 'abc123'

            with patch('pi_autowork.coordinator.git', side_effect=git_result), \
                    patch('subprocess.Popen', side_effect=launch), patch('os.getloadavg', return_value=(0, 0, 0)):
                try:
                    with main_check.check_slot(lambda _: None):
                        runner.check_main()
                        pid = main_check.read(root)['pid']
                        deadline = time.monotonic() + 10
                        while main_check.read(root).get('check_slot', {}).get('state') != 'waiting':
                            self.assertTrue(main_check.alive(pid))
                            self.assertLess(time.monotonic(), deadline)
                            time.sleep(.01)
                        time.sleep(.7)
                        runner.check_main()  # still one running job, not aborted or rescheduled
                        self.assertEqual(main_check.read(root)['pid'], pid)
                        self.assertIn('waiting for a check slot, 1 ahead', main_check.line(main_check.read(root)))
                        self.assertFalse((root / 'ran').exists())
                    deadline = time.monotonic() + 10
                    while main_check.exit_code(root) is None:
                        self.assertLess(time.monotonic(), deadline)
                        time.sleep(.01)
                    self.assertEqual(main_check.read(root)['check_slot']['timeout'], .5)
                    runner.check_main()
                    self.assertEqual(main_check.read(root)['state'], 'green')
                    self.assertTrue((root / 'ran').exists())
                finally:
                    record = main_check.read(root)
                    if main_check.alive(record.get('pid')):
                        os.killpg(record['pid'], signal.SIGKILL)
                    for child in children:
                        child.wait(timeout=10)

    def test_a_live_check_flags_its_execution_timeout_but_not_slot_waiting(self):
        record = dict(state='running', rev='abcdef123', started=0,
                      pid=os.getpid(), start_time=main_check.start_time(os.getpid()))
        for progress, overdue in (({}, True),
                ({'state': 'running', 'started': 3500, 'timeout': 60}, True),
                ({'state': 'running', 'started': 3590, 'timeout': 60}, False),
                ({'state': 'waiting', 'ahead': 1}, False),
                ({'state': 'finished'}, False)):
            with self.subTest(progress=progress):
                with patch.object(os, 'kill', side_effect=AssertionError('render sent a signal')), \
                        patch.object(os, 'killpg', side_effect=AssertionError('render sent a group signal')):
                    text = main_check.line(dict(record, check_slot=progress), now=3601)
                self.assertEqual('overdue' in text, overdue, text)
                self.assertEqual('past timeout' in text, overdue, text)

    def test_the_status_line(self):
        self.assertEqual(main_check.line({'state': 'red', 'rev': 'abcdef123', 'failures': ['a', 'b']}),
                         'main red since abcdef1: 2 failing')
        running = dict(state='running', rev='abcdef123', started=0,
                       pid=os.getpid(), start_time=main_check.start_time(os.getpid()))
        for record, want in (
                (running, 'main check running on abcdef1 (10m)'),
                (dict(running, check_slot={'state': 'waiting', 'ahead': 2}),
                 'main check waiting for a check slot, 2 ahead on abcdef1'),
                (dict(running, start_time='wrong-process'), 'main check interrupted on abcdef1'),
                (dict(running, start_time=None), 'main check interrupted on abcdef1'),
                (dict(running, check_slot={'state': 'running', 'started': 0, 'timeout': 60}),
                 'main check overdue on abcdef1 (10m); past timeout'),
                (dict(running, main_head='123456789'),
                 'main check running on abcdef1 (10m); superseded by main at 1234567'),
                ({'state': 'green', 'rev': 'abcdef123', 'main_head': 'abcdef123'},
                 'main check passed at abcdef1'),
                ({'state': 'green', 'rev': 'abcdef123', 'flaky': ['a']},
                 'main check passed at abcdef1 (1 flaky)')):
            with self.subTest(record=record):
                self.assertEqual(main_check.line(record, now=600), want)
        self.assertEqual(main_check.line({}), '')
        self.assertEqual(main_check.command({'PI_AUTOWORK_MAIN_CHECK': ' python3 scripts/check.py '}),
                         'python3 scripts/check.py')


if __name__ == '__main__':
    unittest.main()
