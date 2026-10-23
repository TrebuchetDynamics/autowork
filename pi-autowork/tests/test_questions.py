"""The runner's BLOCKERS.md questions: fixed shape, easiest first, nothing else touched."""
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pi-autowork'))
sys.path.insert(0, str(ROOT / 'pi-autowork/engine'))
from pi_autowork import questions  # noqa: E402
import store_fixture  # noqa: E402

TODO = '''# TODO

## Next

- [ ] T-1 — Port the tuner
  Scope: x
  Status: open
- [ ] T-2 — Wire the radio
  Scope: y
  Held by: another session
- [ ] T-3 — Export results
  Scope: z
  Status: open
'''
OWNER = '''# BLOCKERS

Intro the owner wrote.

## Active

### BLK-1 — An owner entry

- Category: USER_DECISION

## Resolved

- old things
'''
NOW = datetime(2026, 10, 16, 20, 0, tzinfo=timezone.utc)
STORES = tempfile.TemporaryDirectory()
_made = {}


def store(todo=TODO):
    """A repository whose task store holds the fixture's tasks (one per distinct text)."""
    if todo not in _made:
        repo = Path(STORES.name) / str(len(_made))
        repo.mkdir()
        store_fixture.write_todo(repo, todo)
        _made[todo] = repo
    return _made[todo]


def tearDownModule():
    STORES.cleanup()


def snapshot():
    return {'tasks': [
        {'task': 'T-1', 'state': 'held', 'attempt': 1, 'cause': 'blocker',
         'reason': 'worker reported a blocker: needs   src/x.py   outside Touches'},
        {'task': 'T-3', 'state': 'held', 'attempt': 2, 'cause': 'validation', 'reason': 'integration validation failed'},
        {'task': 'T-4', 'state': 'held', 'attempt': 1, 'cause': 'validation', 'reason': 'will retry'},  # not a question yet
        {'task': 'T-2', 'state': 'waiting', 'blocked_by': ['T-2']},
    ], 'roots': [{'id': 'T-2', 'kind': 'claim', 'blocks': 3}, {'id': 'G1 gate review', 'kind': 'outside', 'blocks': 2},
                 {'id': 'T-1', 'kind': 'held', 'blocks': 1}]}


# T-2 with no attempt left: a question of its own beside T-1's.
EXHAUSTED = {'task': 'T-2', 'state': 'held', 'attempt': 2, 'cause': 'blocker',
             'reason': 'worker asked for an owner-supplied input'}


class QuestionTests(unittest.TestCase):
    def test_questions_are_built_easiest_first_without_a_model(self):
        found = questions.build(snapshot(), store())
        self.assertEqual([(q['id'], q['effort'], q['type'], q['unblocks']) for q in found], [
            ('COND-f8d0a75d', 'decision', 'USER_DECISION', 2), ('T-1', 'input', 'USER_INPUT', 1)])
        self.assertNotIn('T-3', [q['id'] for q in found])  # a validation hold is the engine's to recover
        self.assertEqual(found[1]['task'], 'T-1 — Port the tuner')
        self.assertEqual(found[1]['needs'], 'worker reported a blocker: needs src/x.py outside Touches')

    def test_a_technical_hold_is_never_an_owner_question(self):
        """A conflict or validation/report hold the engine can re-offer is recovery, not a decision."""
        self.assertFalse(questions.exhausted(
            {'state': 'held', 'attempt': 9, 'cause': 'validation', 'reason': 'integration validation failed'}))
        self.assertFalse(questions.exhausted(
            {'state': 'held', 'attempt': 9, 'cause': None,
             'reason': 'missing, failed, stale or mismatched integration validation'}))
        # A merge conflict is the engine's to resolve; an unresolved one stays a visible
        # engineering hold, not an owner decision.
        self.assertFalse(questions.exhausted(
            {'state': 'held', 'attempt': 9, 'cause': 'conflict', 'reason': 'merge conflict'}))
        # Unknown evidence is investigated before responsibility is assigned.
        self.assertFalse(questions.exhausted(
            {'state': 'held', 'attempt': 9, 'cause': None, 'reason': 'held with no attempt left'}))
        # A genuine owner-input hold with no attempt left is still a question.
        self.assertTrue(questions.exhausted(EXHAUSTED))

    def test_a_report_hold_with_its_resume_used_is_asked_from_the_row_classification(self):
        """The status row carries the slot's classification: a report hold whose report-only resume
        was already used needs a person (the engine keeps the retained commit and has no further
        recovery), while a fresh report hold is still the engine's to resume."""
        fresh = {'state': 'held', 'attempt': 1, 'cause': 'report', 'reason': 'report.json does not match',
                 'owner_decision_required': False}
        spent = dict(fresh, owner_decision_required=True)
        self.assertFalse(questions.exhausted(fresh))
        self.assertTrue(questions.exhausted(spent))
        status = {'tasks': [dict(spent, task='T-9')]}
        found = questions.build(status, store(), now=1000)
        self.assertEqual([(q['id'], q['effort']) for q in found], [('T-9', 'investigate')])

    def test_a_dependency_wait_stays_engineering_work_not_an_owner_question(self):
        status = {'tasks': [{'task': 'T-1', 'state': 'held', 'attempt': 2, 'cause': 'task_wait',
                             'waits_for': ['T-2'], 'wait_since': 1000,
                             'reason': 'worker waits for T-2'}]}
        self.assertEqual(questions.build(status, store(), now=1000 + 24 * 3600 - 1), [])
        self.assertEqual(questions.build(status, store(), now=1000 + 24 * 3600), [])
        from failure_policy import classify
        self.assertEqual(classify('task_wait')['resolution_owner'], 'ENGINE')

    def test_a_conflict_the_resolver_still_settles_is_not_asked(self):
        """Seven conflict holds were posted as owner questions while three resolvers cleared them."""
        held = {'task': 'T-1', 'state': 'held', 'attempt': 2, 'cause': 'conflict', 'commit': 'c',
                'reason': 'merge conflict', 'merge_adoption': {'allowed': True, 'merged_count': 1}}
        status = {'tasks': [held], 'roots': []}
        self.assertEqual([q['id'] for q in questions.build(status, store())], [])
        self.assertEqual(questions.build(status, store(), resolving={'T-1'}), [])
        from failure_policy import classify
        self.assertEqual(classify('conflict')['resolution_owner'], 'ENGINE')
        from pi_autowork.coordinator import Coordinator
        runner = Coordinator.__new__(Coordinator)
        runner.seen = {}
        self.assertEqual(runner.resolving([held]), {'T-1'})
        runner.seen['unresolved-T-1'] = 'c'  # its resolution failed: the owner answers it
        self.assertEqual(runner.resolving([held]), set())
        spent = dict(held, merge_adoption={'allowed': False, 'merged_count': 3})  # merges ran out
        runner.seen = {}
        self.assertEqual(runner.resolving([spent]), set())
        runner.resolvers['T-1'] = {}
        self.assertEqual(runner.resolving([spent]), {'T-1'})  # running now

    def test_live_authorization_becomes_one_owner_question_in_blockers(self):
        condition = 'Live authorization: T-1'
        status = {'tasks': [{'task': 'T-1', 'state': 'waiting', 'blocked_by': [condition]}],
                  'roots': [{'id': condition, 'kind': 'outside', 'blocks': 1}]}
        found = questions.build(status, store())
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['id'], 'T-1')
        self.assertEqual(found[0]['task'], 'T-1 — Port the tuner')
        text = questions.update(None, found, now=NOW)
        self.assertEqual(text.count('### Q-'), 1)
        for option in ('Run it yourself', '`live = "authorized"` in tasks/items/T-1.md', 'Needs decision',
                       'a worker\'s edit to the record never does'):
            self.assertIn(option, text)
        self.assertNotIn('### Q-', questions.update(text, questions.build({}, store()), now=NOW))

    def test_technical_producers_cannot_bypass_owner_admission(self):
        import parallel_state
        import failure_policy
        attempts = [dict(task_id='T-1', state='held', cause='contract_changed',
                         reason='task contract changed', branch='fixture', attempt=n,
                         held_seconds=1, held_at=n) for n in (1, 2, 3)]
        with tempfile.TemporaryDirectory() as folder:
            hold = parallel_state.quick_hold(Path(folder), dict(attempts[-1], previous_attempts=attempts[:-1]))
        self.assertIsNotNone(hold)
        row = dict(task='T-1', state='held', cause='contract_changed', attempt=3,
                   quick_hold=hold, **{'owner_decision_required': False})
        cases = [({'tasks': [row]}, ()),
                 ({'tasks': [dict(task='T-1', state='waiting')]},
                  [dict(task='T-1', reason='missing checks', fields=['Checks'])])]
        cases.extend(({'roots': [dict(id='T-1', kind=kind, blocks=1,
                                     resolution_owner='OWNER', owner_decision_required=True)]}, ())
                     for kind in ('cycle', 'contract'))
        for status, repairs in cases:
            with self.subTest(status=status):
                self.assertEqual(questions.build(status, store(), repairs=repairs), [])
        self.assertEqual(failure_policy.classify('contract_changed')['resolution_owner'], 'ENGINE')

    def test_a_refused_ledger_remains_engineering_work(self):
        status = {'outcome': 'ACTION_REQUIRED', 'ledger_errors': ['G: unverified goal has no open task']}
        found = questions.build(status, store())
        text = questions.update(OWNER, found, now=NOW)
        self.assertEqual(found, [])
        self.assertNotIn('### Q-LEDGER', text)
        self.assertIn('Intro the owner wrote.', text)
        self.assertEqual(questions.update(text, found, now=NOW), text)
        self.assertNotIn('### Q-LEDGER', questions.update(text, questions.build({}, store()), now=NOW))

    def test_an_unchanged_maintainer_repair_becomes_one_question_with_its_changed_fields(self):
        status = snapshot()  # T-1 already has a held/root question: enrich it, do not duplicate it.
        repairs = [dict(task='T-1', reason='not runnable: ledger dependency or disposition holds execution',
                        fields=['Checks', 'Dependencies'])]
        found = questions.build(status, store(), repairs=repairs)
        question = next(q for q in found if q['id'] == 'T-1')
        self.assertEqual(question['task'], 'T-1 — Port the tuner')
        self.assertIn(repairs[0]['reason'], question['needs'])
        self.assertIn('Checks, Dependencies', question['needs'])
        self.assertIn('DOCS-MAINTAINER', question['needs'])
        first = questions.update(OWNER, found, now=NOW)
        self.assertEqual(first.count('### Q-T-1 '), 1)
        later = datetime(2026, 10, 17, tzinfo=timezone.utc)
        self.assertEqual(questions.update(first, found, now=later), first)
        # The same unsuccessful repair is not authority to invent an owner decision.
        waiting = {'tasks': [{'task': 'T-1', 'state': 'waiting', 'reason': repairs[0]['reason']}]}
        self.assertEqual(questions.build(waiting, store(), repairs=repairs), [])
        self.assertNotIn('### Q-T-1 ', questions.update(first, questions.build(waiting, store()), now=later))

    def test_repeated_quick_holds_keep_one_question_with_attempt_times_and_resolution(self):
        status = snapshot()
        status['tasks'][0]['quick_hold'] = dict(fingerprint='abc123', reason='missing receipt', attempts=[
            dict(attempt=f'{n}/1', reason='missing receipt', seconds=60, held_at=1000 + n) for n in range(1, 4)])
        repairs = [dict(task='T-1', reason='missing receipt', fields=['Evidence'])]
        found = questions.build(status, store(), repairs=repairs)
        question = next(q for q in found if q['id'] == 'T-1')
        for detail in ('missing receipt', '1/1', '2/1', '3/1', '60s'):
            self.assertIn(detail, question['needs'])
        self.assertIn('Blocker resolution: abc123;', question['answer'])
        self.assertIn('Needs decision', question['answer'])
        first = questions.update(OWNER, found, now=NOW)
        self.assertEqual(first.count('### Q-T-1 '), 1)
        self.assertEqual(questions.update(first, found, now=NOW), first)

    def test_a_held_task_is_never_asked(self):
        """Its `Held by:` note is the answer, dated or not (TOOLSET-198-8f: the owner noted who
        holds a task and the runner kept asking); `autowork tasks release` lifts it."""
        status = {'roots': [dict(id='T-2', kind='claim', blocks=3, held_by='another session')]}
        self.assertEqual(questions.build(status, store(), now=NOW.timestamp()), [])
        self.assertNotIn('T-2', [q['id'] for q in questions.build(snapshot(), store())])

    def test_only_a_recorded_owner_deferral_answers_an_outside_task(self):
        status = {'roots': [{'id': 'D', 'kind': 'outside', 'blocks': 2}]}
        for section, decision, asked in (
                ('Needs decision', 'Owner decision: 2026-10-18: defer until hardware arrives.', False),
                ('Needs decision', '', True),
                ('Needs decision', 'Owner decision: defer until hardware arrives.', True),
                ('Needs decision', 'Owner decision: 2026-02-30: defer.', True),
                ('Next', 'Owner decision: 2026-10-18: defer.', True)):
            with self.subTest(section=section, decision=decision):
                todo = f'# TODO\n\n## {section}\n\n- [ ] D — Device check\n  {decision}\n'
                self.assertEqual([q['id'] for q in questions.build(status, store(todo))], ['D'] if asked else [])

    def test_the_block_sits_under_active_and_nothing_else_changes(self):
        text = questions.update(OWNER, questions.build(snapshot(), store()), now=NOW)
        start, end = text.index(questions.START), text.index(questions.END) + len(questions.END)
        self.assertEqual(text[:start] + text[end:], OWNER.replace('## Active\n', '## Active\n\n\n', 1))
        self.assertIn('### Q-T-1 — USER_INPUT — effort input — unblocks 1\n\n- Task: T-1 — Port the tuner\n', text)
        self.assertIn('- Since: 2026-10-16T20:00:00Z\n- Answer: Answer in tasks/items/T-1.md', text)
        self.assertNotIn('Q-T-2', text)  # held by another session: its note is the answer
        self.assertNotIn('Q-T-3', text)  # a validation hold is not a question

    def test_rewrites_keep_first_times_and_drop_answered_questions(self):
        queue = snapshot()
        queue['tasks'].append(EXHAUSTED)
        queue['roots'][1]['id'] = 'owned target and\n  capture consent'
        found = questions.build(queue, store())
        condition = next(q for q in found if q['kind'] == 'outside')
        self.assertEqual(condition['id'], 'COND-fb37fe1a')
        self.assertEqual(condition['task'], 'owned target and capture consent')
        first = questions.update(OWNER, found, now=NOW)
        self.assertIn('### Q-COND-fb37fe1a — USER_DECISION — effort decision — unblocks 2\n', first)
        later = datetime(2026, 10, 17, 8, 0, tzinfo=timezone.utc)
        for cycle in range(20):
            queue['roots'][1]['id'] = ('owned target\tand capture consent' if cycle % 2
                                     else 'owned target and\n  capture consent')
            again = questions.update(first, questions.build(queue, store()), now=later.replace(minute=cycle))
            self.assertEqual(again, first)  # unchanged bytes: no coordinator commit or log
        answered = snapshot()
        answered['tasks'] = [t for t in answered['tasks'] if t['task'] != 'T-1'] + [EXHAUSTED]
        answered['roots'] = [r for r in answered['roots'] if r['id'] != 'T-1']
        after = questions.update(first, questions.build(answered, store()), now=later)
        self.assertNotIn('Q-T-1', after)
        self.assertIn('### Q-T-2', after)
        self.assertIn('- Since: 2026-10-16T20:00:00Z', after)  # T-2 kept its first time

    def test_legacy_broken_headings_keep_first_times_without_stealing_a_neighbours(self):
        for prose, qid in [('owned target and\n  capture consent', 'COND-fb37fe1a'),
                           ('owned target and\n- capture consent', 'COND-cb187cdc'),
                           ('owned target —\n capture consent', 'COND-6bd3acf5')]:
            with self.subTest(prose=prose):
                legacy = questions.START + f'''
### Q-T-2 — USER_DECISION — effort quick — unblocks 3

- Since: 2026-10-15T09:00:00Z
### Q-{prose} — USER_DECISION — effort decision — unblocks 2

- Since: 2026-10-15T10:00:00Z
- Since: 2026-10-16T10:00:00Z
### An unrecognized heading

- Since: 2026-10-16T11:00:00Z
''' + questions.END
                queue = snapshot()
                queue['tasks'].append(EXHAUSTED)
                queue['roots'][1]['id'] = prose
                migrated = questions.update(legacy, questions.build(queue, store()), now=NOW)
                self.assertEqual(questions.previous_since(migrated), {
                    'T-2': '2026-10-15T09:00:00Z', qid: '2026-10-15T10:00:00Z',
                    'T-1': '2026-10-16T20:00:00Z'})

    def test_render_collapses_whitespace_in_every_field(self):
        q = dict(id=' T-1\n ', type=' USER_INPUT\n ', effort=' input\t ', unblocks=' 1\n ',
                 task=' Port\n the\ttuner ', needs=' needs\n a\tdecision ', answer=' Answer\n here ',
                 kind=' held\n ')
        self.assertEqual(questions.render([q], {'T-1': ' 2026-10-16T20:00:00Z\n '}),
                         questions.START + '''

### Q-T-1 — USER_INPUT — effort input — unblocks 1

- Task: Port the tuner
- Needs: needs a decision
- Since: 2026-10-16T20:00:00Z
- Answer: Answer here
- Kind: held

''' + questions.END)

    def test_no_questions_leaves_a_file_without_a_block_alone(self):
        self.assertEqual(questions.update(OWNER, [], now=NOW), OWNER)
        self.assertIsNone(questions.update(None, [], now=NOW))
        emptied = questions.update(questions.update(OWNER, questions.build(snapshot(), store()), now=NOW), [], now=NOW)
        self.assertNotIn('### Q-', emptied)
        self.assertIn(questions.START, emptied)  # the markers stay in place for next time

    def test_a_missing_file_gets_a_minimal_one(self):
        text = questions.update(None, questions.build(snapshot(), store()), now=NOW)
        self.assertTrue(text.startswith('# Blockers\n\n## Active\n\n' + questions.START))


if __name__ == '__main__':
    unittest.main()
