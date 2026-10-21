"""DOCS-MAINTAINER triggers, trigger-set key and run record (TOOLSET-164-f1)."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import maintainer  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'skills/docs-sync/scripts'))
import goals  # noqa: E402


class MaintainerTests(unittest.TestCase):
    def test_tasks_waiting_on_a_shared_file_are_re_cut_while_worker_slots_idle(self):
        """Tasks naming one file collided at merge all afternoon; the dispatcher now holds them,
        and with slots idle the maintainer may merge, split or supersede them before they run."""
        rows = [{'task': 'A', 'state': 'running'},
                {'task': 'B', 'state': 'waiting', 'reason': 'shares x.py with A; starts after it lands'},
                {'task': 'C', 'state': 'waiting', 'reason': 'shares y.py with B, which goes first'},
                {'task': 'D', 'state': 'waiting', 'reason': 'all 8 worker slots busy'}]
        found = maintainer.overlaps(rows)
        self.assertEqual([(t, k) for t, k, _ in found], [('B', 'overlap'), ('C', 'overlap')])
        text = maintainer.prompt(found, '/repo', 'goals.py')
        for phrase in ('merge it into the other task', 'split the shared-file part', 'never widen product scope',
                       'Never edit the entry of a task that is running'):
            self.assertIn(phrase, text)
        from pi_autowork.coordinator import Coordinator
        runner = Coordinator.__new__(Coordinator)
        runner.workers, runner.seen = '2', {}
        runner.tasks = lambda: rows
        os.environ['PI_AUTOWORK_OVERLAP_EVERY'] = '0'  # these checks are about idle slots, not the interval
        self.addCleanup(os.environ.pop, 'PI_AUTOWORK_OVERLAP_EVERY', None)
        self.assertTrue(runner.overlap_idles())  # one of two slots runs
        runner.workers = '1'
        self.assertFalse(runner.overlap_idles())  # every slot busy: the pool limits, not the queue
        runner.workers = '2'
        runner.tasks = lambda: [r for r in rows if not maintainer.overlap(r)]
        self.assertFalse(runner.overlap_idles())

    def test_planning_holds_and_unrunnable_tasks_trigger_and_nothing_else_does(self):
        rows = [
            {'task': 'A', 'state': 'held', 'cause': 'scope', 'reason': 'changed files violate Touches'},
            {'task': 'B', 'state': 'held', 'cause': 'blocker', 'reason': 'worker reported a blocker: which API?'},
            {'task': 'C', 'state': 'waiting', 'reason': 'not runnable: missing Checks'},
            {'task': 'D', 'state': 'held', 'cause': 'crash', 'reason': 'dead worker'},          # not planning
            {'task': 'E', 'state': 'held', 'cause': 'scope', 'worker_live': True},              # still working
            {'task': 'F', 'state': 'waiting', 'reason': 'dependency: A'},
            {'task': 'G', 'state': 'running'},
        ]
        found = maintainer.triggers(rows)
        self.assertEqual([t for t, _, _ in found], ['A', 'B', 'C'])
        self.assertEqual(maintainer.key(found), maintainer.key(maintainer.triggers(list(reversed(rows)))))
        self.assertEqual(maintainer.triggers([r for r in rows if r['task'] in 'DEFG']), [])

    def test_dropped_ledger_proposals_are_reviewed_once_before_draining_exits(self):
        from pi_autowork.coordinator import Coordinator, Finish

        with tempfile.TemporaryDirectory() as state:
            root = Path(state)
            (root / 'TODO.md').write_text('# TODO\n')  # source task already archived
            evidence = root / 'ledger-edit.patch'
            evidence.write_text('--- a/TODO.md\n+++ b/TODO.md\n-old link\n+fixed link\n' + 'x' * 1000)
            row = dict(task='A', state='reported', reason='',
                       ledger_edit_dropped=dict(paths=['TODO.md'], patch=str(evidence)))
            self.assertEqual(maintainer.triggers([row]), [])
            row['state'] = 'integrated'
            found = maintainer.triggers([row])
            self.assertEqual([(t, kind) for t, kind, _ in found], [('A', 'ledger edit')])
            self.assertIn('+fixed link', found[0][2])
            self.assertLessEqual(len(found[0][2]), 900)
            row['state'] = 'closed'
            runner = Coordinator.__new__(Coordinator)
            runner.state, runner.repo, runner.integ, runner.stop = root, state, state, False
            runner.toolset, runner.goals, runner.verify_timeout = Path(__file__).resolve().parents[2], 'goals.py', 1
            runner.in_flight = runner.session_busy = lambda: False
            rows = [row] + [dict(row, task=f'Z{i:02}') for i in range(maintainer.LIMIT)]
            runner.tasks = lambda: rows
            runner.scratch_checkout, runner.drop_scratch = lambda _: state, lambda _: None
            prompts = []
            runner.pi_job = lambda *args: (prompts.append(args[3]) or True, '')
            runner.draining, runner.mode, runner.once_done, runner.once_task = True, 'once', True, 'A'
            runner.seen, runner.settled = {'synced-at-start': True}, False
            runner.plan_signature, runner.planning_ready = lambda: '', lambda: True
            for method in ('restart_if_updated', 'ensure_session', 'follow_base', 'sweep_tmp', 'check_main',
                           'land_planning', 'settle', 'handle_requests', 'health_update'):
                setattr(runner, method, lambda: None)  # external lifecycle, not the handoff
            def finish(code, text):
                raise Finish(code, text)
            runner.finish = finish
            with patch('pi_autowork.coordinator.dirty', return_value=False):
                self.assertTrue(runner.maintain())  # IDLE must continue even after discarding a batch
                self.assertEqual(len(prompts), 1)
                for _ in range(2):
                    with self.assertRaises(Finish) as done:
                        runner.cycle()
                    self.assertEqual(done.exception.code, 0)
                    (root / 'TODO.md').write_text('# TODO\n\nUnrelated planning edit\n')
            self.assertEqual(len(prompts), 2)
            self.assertTrue(all('+fixed link' in message for message in prompts))
            self.assertEqual((root / 'TODO.md').read_text(), '# TODO\n\nUnrelated planning edit\n')

    def test_repeated_quick_hold_is_repaired_once_even_after_cosmetic_entry_edits(self):
        row = dict(task='A', state='held', cause='blocker', reason='missing receipt',
                   quick_hold=dict(fingerprint='abc123', reason='missing receipt', attempts=[]))
        found = maintainer.triggers([row])
        self.assertEqual([(task, kind) for task, kind, _ in found], [('A', 'repeated quick hold')])
        self.assertIn('abc123', found[0][2])
        with tempfile.TemporaryDirectory() as state:
            entries = {'A': dict(digest='original', fields={})}
            self.assertEqual(maintainer.pending(state, found, entries=entries), found)
            maintainer.remember(state, trigger_key=maintainer.key(found), found=found, entries=entries,
                                outcome='no change')
            maintainer.remember(state, trigger_key='other', found=[('MAIN', 'main red', 'x')], outcome='merged')
            entries['A']['digest'] = 'cosmetic edit'
            self.assertEqual(maintainer.pending(state, found, entries=entries), [])
            row['quick_hold']['fingerprint'] = 'different'
            changed = maintainer.triggers([row])
            self.assertEqual(maintainer.pending(state, changed, entries=entries), changed)

    def test_a_last_attempt_reviewed_and_found_wanting_is_a_trigger_with_its_findings(self):
        rows = [{'task': 'A', 'state': 'held', 'cause': 'validation', 'attempt': 2},
                {'task': 'B', 'state': 'held', 'cause': 'validation', 'attempt': 1},   # it gets a fresh retry
                {'task': 'C', 'state': 'held', 'cause': 'validation', 'attempt': 2}]   # no findings recorded
        found = maintainer.triggers(rows, findings={'A': 'PI_AUTOWORK_VERIFY: fail — Back is not handled',
                                                    'B': 'PI_AUTOWORK_VERIFY: fail — x'})
        self.assertEqual(found, [('A', 'review findings', 'PI_AUTOWORK_VERIFY: fail — Back is not handled')])

    def test_main_evidence_refreshes_the_same_repair_identity_once_per_revision(self):
        for kind in ('red', 'flaky'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as state:
                main = dict(state='red' if kind == 'red' else 'green', rev='abc',
                            failures=['test_sample.Sample.test_fail', 'test_other.Other.test_fail'] if kind == 'red' else [],
                            flaky=['test_sample.Sample.test_fail'] if kind == 'flaky' else [],
                            flaky_history={'test_sample.Sample.test_fail': ['a', 'b', 'c']} if kind == 'flaky' else {},
                            commits=['abc first'], evidence='/git/autowork-execution/main-evidence/abc')
                first = maintainer.triggers([], main)
                self.assertIn(main['evidence'], first[0][2])
                identity = maintainer.item_key(first[0])
                maintainer.remember(state, trigger_key=maintainer.key(first), found=first, outcome='merged')
                reported = maintainer.last(state).get('flaky_tests', [])
                self.assertEqual(maintainer.pending(state, maintainer.triggers([], main, reported_flakes=reported)), [])
                main.update(rev='def', evidence='/git/autowork-execution/main-evidence/def', commits=['def next'],
                            failures=list(reversed(main['failures'])))
                fresh = maintainer.triggers([], main, reported_flakes=reported)
                self.assertEqual(maintainer.item_key(fresh[0]), identity)
                self.assertEqual(maintainer.pending(state, fresh), fresh)
                message = maintainer.prompt(fresh, '/repo', 'goals.py')
                self.assertIn(main['evidence'], message)
                self.assertIn('update its Evidence', message)
                self.assertIn('never add a second task', message)
                maintainer.remember(state, trigger_key=maintainer.key(fresh), found=fresh, outcome='merged')
                self.assertEqual(maintainer.pending(state, fresh), [])
                self.assertEqual(len(maintainer.last(state)['items']), 1)

    def test_main_evidence_refresh_does_not_retrigger_itself_but_owner_changes_do(self):
        from pi_autowork import main_check
        from pi_autowork.coordinator import Coordinator
        from pi_autowork.common import git, git_ok

        with tempfile.TemporaryDirectory() as tmp:
            repo, state = Path(tmp) / 'repo', Path(tmp) / 'state'
            repo.mkdir()
            state.mkdir()
            for args in [('init', '-q'), ('config', 'user.name', 'Test'),
                         ('config', 'user.email', 'test@example.invalid')]:
                self.assertTrue(git_ok(repo, *args))
            (repo / '.gitignore').write_text('/.worktrees/\n')
            entry = repo / 'TODO.md'
            entry.write_text('- [ ] FIX — Repair main\n  Evidence: original\n')
            self.assertTrue(git_ok(repo, 'add', '.'))
            self.assertTrue(git_ok(repo, 'commit', '-qm', 'base'))
            runner = Coordinator.__new__(Coordinator)
            runner.state, runner.repo, runner.integ, runner.stop = state, repo, repo, False
            runner.toolset, runner.goals, runner.verify_timeout = Path(__file__).resolve().parents[2], 'goals.py', 1
            runner.in_flight = runner.session_busy = lambda: False
            prompts = []
            def check():
                rev = git(repo, 'rev-parse', 'HEAD')
                tests = [f'test_sample.Sample.test_{i:02}' for i in range(maintainer.LIMIT + 1)]
                main_check.write(state, dict(state='green', rev=rev, flaky=tests,
                                              flaky_history={test: ['a', 'b', 'c'] for test in tests},
                                              evidence=str(repo / '.git/autowork-execution/main-evidence' / rev)))
            def model(role, task, scratch, message, *args):
                prompts.append(message)
                path = Path(scratch) / 'TODO.md'
                path.write_text('- [ ] FIX — Repair main\n  Evidence: ' + main_check.read(state)['evidence']
                                + f'\n  Maintenance batch: {len(prompts)}\n')
                self.assertTrue(git_ok(scratch, 'commit', '-qam', 'refresh existing repair evidence'))
                return True, ''
            runner.pi_job = model
            check()
            self.assertTrue(runner.maintain(main_only=True))
            self.assertTrue(runner.maintain(main_only=True))  # overflow is a second maintenance commit
            check()  # main changed only because the maintainer refreshed Evidence
            self.assertFalse(runner.maintain(main_only=True))
            for path in (entry, repo / 'implementation.py'):
                path.write_text(path.read_text() + '\nOwner change\n' if path.exists() else '# changed\n')
                self.assertTrue(git_ok(repo, 'add', '.'))
                self.assertTrue(git_ok(repo, 'commit', '-qm', 'independent owner change'))
                check()
                self.assertTrue(runner.maintain(main_only=True))
                self.assertTrue(runner.maintain(main_only=True))
                check()
                self.assertFalse(runner.maintain(main_only=True))
            self.assertEqual(len(prompts), 6)
            self.assertEqual(entry.read_text().count('- [ ] FIX'), 1)

    def test_a_run_refused_because_the_session_moved_is_tried_again_once(self):
        with tempfile.TemporaryDirectory() as state:
            found = [('A', 'held: scope', 'x')]
            self.assertTrue(maintainer.due(state, 'k1'))
            maintainer.remember(state, trigger_key='k1', found=found, outcome=maintainer.RETRYABLE)
            self.assertTrue(maintainer.due(state, 'k1', found=found))  # session moved: try again
            maintainer.remember(state, trigger_key='k1', found=found, outcome=maintainer.RETRYABLE)
            self.assertFalse(maintainer.due(state, 'k1', found=found))  # twice is enough
            maintainer.remember(state, trigger_key='other', found=[('B', 'held: scope', 'x')], outcome='merged')
            self.assertFalse(maintainer.due(state, 'k1', found=found))  # unrelated batches cannot reset retries
            maintainer.remember(state, trigger_key='k2', found=found, outcome='merged')
            self.assertFalse(maintainer.due(state, 'k2'))      # done: never again for the same set
            self.assertTrue(maintainer.due(state, 'k3'))

    def test_ledger_errors_are_one_trigger_and_each_error_set_is_tried_only_once(self):
        errors = ['B: unverified goal has no open task', 'A: missing evidence']
        found = maintainer.triggers([{'task': 'T', 'state': 'waiting', 'reason': 'not runnable: Checks'}],
                                    ledger_errors=errors + errors[:1])
        self.assertEqual(found, [('LEDGER', 'invalid goals.json',
                                 'A: missing evidence\nB: unverified goal has no open task')])
        key = maintainer.key(found)
        self.assertEqual(key, maintainer.key(maintainer.triggers([], ledger_errors=list(reversed(errors)))))
        with tempfile.TemporaryDirectory() as state:
            maintainer.remember(state, trigger_key=key, found=found, outcome='no change')
            maintainer.remember(state, trigger_key='other', found=[('MAIN', 'main red', 'x')], outcome='merged')
            self.assertFalse(maintainer.due(state, key))
            changed = maintainer.triggers([], ledger_errors=['A: different error'])
            self.assertTrue(maintainer.due(state, maintainer.key(changed)))

    def test_handled_items_stay_handled_across_overlapping_batches(self):
        from pi_autowork.coordinator import Coordinator

        with tempfile.TemporaryDirectory() as state:
            todo = ''.join(f'- [ ] {task} — Proof\n  Scope: device proof\n' for task in 'ABCD')
            (Path(state) / 'TODO.md').write_text(todo)
            entries = maintainer.entries(todo, goals)
            rows = [dict(task=task, state='waiting', reason='not runnable: missing Checks') for task in 'ABCD']
            abc = maintainer.triggers(rows[:3])
            maintainer.remember(state, trigger_key=maintainer.key(abc), found=abc, outcome='merged', entries=entries)
            runner = Coordinator.__new__(Coordinator)
            runner.state, runner.repo, runner.integ, runner.stop = Path(state), state, state, False
            runner.toolset = Path(__file__).resolve().parents[2]
            runner.goals, runner.verify_timeout = 'goals.py', 1
            runner.in_flight = runner.session_busy = lambda: False
            runner.scratch_checkout, runner.drop_scratch = lambda _: state, lambda _: None
            prompts = []
            def model(*args):
                prompts.append(args[3])
                return True, ''  # external model leaves D unchanged; no Git commit to merge
            runner.pi_job = model
            with patch('pi_autowork.coordinator.dirty', return_value=False):
                for batch in (rows, rows[:3], rows):
                    runner.tasks = lambda: batch
                    runner.maintain()
            self.assertEqual(len(prompts), 1)
            self.assertIn('- D (not runnable): not runnable: missing Checks', prompts[0])
            for task in 'ABC':
                self.assertNotIn(f'- {task} (', prompts[0])
            self.assertEqual(maintainer.pending(state, maintainer.triggers(rows), entries=entries), [])

    def test_unchanged_repair_is_suppressed_until_an_owner_edit_or_a_new_reason(self):
        from pi_autowork.coordinator import Coordinator
        from pi_autowork.common import git_ok
        from pi_autowork import worker

        with tempfile.TemporaryDirectory() as tmp:
            repo, state = Path(tmp) / 'repo', Path(tmp) / 'state'
            repo.mkdir()
            state.mkdir()
            for args in [('init', '-q'), ('config', 'user.name', 'Test'), ('config', 'user.email', 'test@example.invalid')]:
                self.assertTrue(git_ok(repo, *args))
            (repo / '.gitignore').write_text('/.worktrees/\n')
            path = repo / 'TODO.md'
            path.write_text('- [ ] A — Device proof\n  Dependencies: B-12\n  Checks: manual\n'
                            '- [ ] alpha — Alpha\n- [ ] beta — Beta\n'
                            '- [ ] 1alpha — Numeric alpha\n- [ ] 2beta — Numeric beta\n')
            git_ok(repo, 'add', '.')
            self.assertTrue(git_ok(repo, 'commit', '-qm', 'plan'))
            evidence = worker.findings_path(state, 'A')
            evidence.parent.mkdir(parents=True)
            evidence.write_text(json.dumps({'verdict': 'PI_AUTOWORK_VERIFY: fail — proof missing'}))
            row = dict(task='A', state='held', cause='validation', attempt=2,
                       reason='not runnable: waiting for B-12; 2 dependents')
            runner = Coordinator.__new__(Coordinator)
            runner.state, runner.repo, runner.integ, runner.stop = state, repo, repo, False
            runner.toolset, runner.goals, runner.verify_timeout = Path(__file__).resolve().parents[2], 'goals.py', 1
            runner.in_flight = runner.session_busy = lambda: False
            runner.tasks = lambda snapshot=None: [row]
            prompts = []
            def model(role, task, scratch, message, *args):
                prompts.append(message)
                entry = Path(scratch) / 'TODO.md'
                entry.write_text(entry.read_text().replace('Dependencies: B-12', 'Dependencies: None.'))
                self.assertTrue(git_ok(scratch, 'commit', '-qam', 'repair Dependencies'))
                return True, ''
            runner.pi_job = model
            self.assertTrue(runner.maintain())
            # Other runs cannot erase the receipt; IDs/counts do not change the reason class.
            maintainer.remember(state, trigger_key='main', found=[('MAIN', 'main red', 'broken')], outcome='merged')
            for dependency in ('C-93', 'A1', 'B2', '1alpha', '2beta', 'alpha', 'beta'):
                row['reason'] = f'not runnable: waiting for {dependency}; 6 dependents'
                self.assertFalse(runner.maintain())
            path.write_text(path.read_text().replace('- [ ] beta — Beta\n', ''))
            self.assertTrue(git_ok(repo, 'commit', '-qam', 'archive an unrelated task'))
            self.assertFalse(runner.maintain())  # removing a referenced ID cannot erase the receipt
            self.assertEqual(len(prompts), 1)
            snapshot = dict(outcome='PARALLEL_STATUS', tasks=[row], roots=[dict(id='A', kind='held', blocks=1)])
            runner.update_questions(snapshot)
            first = (repo / 'BLOCKERS.md').read_text()
            self.assertEqual(first.count('### Q-A '), 1)
            self.assertIn(row['reason'], first)
            self.assertIn('DOCS-MAINTAINER already changed Dependencies', first)
            runner.update_questions(snapshot)
            self.assertEqual((repo / 'BLOCKERS.md').read_text(), first)
            found = maintainer.triggers([row], findings={'A': worker.review_findings(state, 'A')})
            after = maintainer.entries(path.read_text(), goals)
            for entry, reason in ((after, 'not runnable: missing live authorization'),
                                  (maintainer.entries(path.read_text().replace('Checks: manual', 'Checks: attach device'), goals),
                                   row['reason'])):
                reasons = {'A': reason}
                self.assertEqual(maintainer.pending(state, found, entries=entry, reasons=reasons), found)
                self.assertEqual(maintainer.stalled(state, found, entries=entry, reasons=reasons), [])

    def test_legacy_records_preserve_handling_and_exhausted_retries_on_upgrade(self):
        found = [('A', 'not runnable', 'not runnable: missing Checks')]
        for outcome, tries, expected in [('merged', 1, []), (maintainer.RETRYABLE, 2, []),
                                          (maintainer.RETRYABLE, 1, found)]:
            with self.subTest(outcome=outcome, tries=tries), tempfile.TemporaryDirectory() as state:
                maintainer.record_path(state).write_text(json.dumps(dict(key=maintainer.key(found), outcome=outcome,
                                                                        tries=tries, triggers=['A'])))
                entries = {'A': dict(digest='original', fields={})}
                self.assertEqual(maintainer.pending(state, found, entries=entries), expected)
                entries['A']['digest'] = 'owner edit'
                self.assertEqual(maintainer.pending(state, found, entries=entries), found)

    def test_ready_planning_entries_run_one_at_a_time_without_changing_other_triggers(self):
        rows = [dict(task=t, state='waiting', reason='ready for planning') for t in ('P', 'Q')]
        found = maintainer.triggers(rows + [dict(task='A', state='held', cause='scope')])
        self.assertEqual([x for x in found if x[1] == 'plan'],
                         [('P', 'plan', 'ready for planning'), ('Q', 'plan', 'ready for planning')])
        with tempfile.TemporaryDirectory() as state:
            first = maintainer.pending(state, found)
            self.assertEqual(first, [('P', 'plan', 'ready for planning')])
            maintainer.remember(state, trigger_key=maintainer.key(first), found=first, outcome='failed')
            self.assertEqual(maintainer.pending(state, found), [('Q', 'plan', 'ready for planning')])

    def test_planning_landing_refuses_malformed_chains_and_stops_for_a_met_goal(self):
        from pi_autowork.touches_inference import modules
        _, dispatch = modules(Path(__file__).resolve().parents[2])
        def entry(kind='', round_='', goal='G', section='Next', mark=' '):
            return dict(fields={'Kind': kind, 'Plan round': round_, 'Goal': goal,
                                'Section': section, 'Checkbox': mark, 'Status': 'done' if mark == 'x' else 'open'})
        before = {'P': entry('plan', '1 of 10')}
        for case in ('met', 'unclosed', 'wrong_round', 'missing_dependency', 'wrong_goal',
                     'missing_question', 'invalid_round', 'duplicate', 'missing_decision_question', 'none_dependency'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                old = {'P': entry('plan', '1 of 10')}
                new = {'P': entry('plan', '1 of 10', mark='x')}
                if case != 'met':
                    new['B'] = entry()
                    new['NEXT'] = entry('plan', '2 of 10')
                    new['NEXT']['fields']['Dependencies'] = 'B'
                if case == 'invalid_round':
                    old['P']['fields']['Plan round'] = '11 of 10'
                if case == 'duplicate':
                    new['B']['count'] = 2
                if case == 'missing_decision_question':
                    new['B'] = entry(section='Needs decision')
                if case == 'unclosed':
                    new['P'] = before['P']
                if case == 'wrong_round':
                    new['NEXT']['fields']['Plan round'] = '3 of 10'
                if case in ('missing_dependency', 'none_dependency'):
                    new['NEXT']['fields']['Dependencies'] = 'None.' if case == 'missing_dependency' else 'None. B'
                if case == 'wrong_goal':
                    new['B']['fields']['Goal'] = 'OTHER'
                if case == 'missing_question':
                    new.pop('NEXT')
                ledger = dict(goals=[dict(id='G', status='met', evidence=[dict(kind='executed', result='pass')])], tasks=[])
                (repo / 'goals.json').write_text(json.dumps(ledger if case == 'met' else {'goals': []}))
                error = maintainer.plan_error([('P', 'plan', '')], old, new, repo,
                                              dispatch.parallel_plan.dependency_ids)
                if case == 'met':
                    self.assertIsNone(error)
                else:
                    self.assertTrue(error, case)

    def test_prompt_prefers_independent_parts_when_unblocking_a_chain(self):
        message = maintainer.prompt([('A', 'not runnable', 'not runnable: dependency chain')], '/repo', 'goals.py')
        self.assertIn('re-sort to unblock a dependency chain, preferring to split off independent parts '
                      'with disjoint Touches', message)

    def test_only_planning_files_may_change(self):
        self.assertTrue(maintainer.planning_only(['TODO.md', 'goals.json', 'docs/tasks/A.md']))
        self.assertFalse(maintainer.planning_only(['TODO.md', 'src/app.py']))
        self.assertFalse(maintainer.planning_only([]))

    def test_the_last_run_is_recorded_for_status(self):
        with tempfile.TemporaryDirectory() as state:
            found = [('A', 'held: scope', 'x')]
            maintainer.remember(state, trigger_key='k1', found=found, outcome='merged', changed=['A'], now=100)
            record = maintainer.last(state)
            self.assertEqual({k: record[k] for k in ('role', 'key', 'at', 'outcome', 'triggers', 'changed', 'tries')},
                             {'role': 'DOCS-MAINTAINER', 'key': 'k1', 'at': 100, 'outcome': 'merged',
                              'triggers': ['A'], 'changed': ['A'], 'tries': 1})
            self.assertIn('- A (held: scope): x', maintainer.prompt(found, '/repo', 'goals.py'))


if __name__ == '__main__':
    unittest.main()
