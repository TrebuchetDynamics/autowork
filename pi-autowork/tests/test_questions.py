"""The runner's BLOCKERS.md questions: fixed shape, easiest first, nothing else touched."""
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pi-autowork'))
sys.path.insert(0, str(ROOT / 'skills/docs-sync/scripts'))
from pi_autowork import questions  # noqa: E402
import goals  # noqa: E402

TODO = '''# TODO

## Next

- [ ] T-1 — Port the tuner
  Scope: x
  Status: open
- [ ] T-2 — Wire the radio
  Scope: y
  Status: in_progress
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


def snapshot():
    return {'tasks': [
        {'task': 'T-1', 'state': 'held', 'attempt': 1, 'cause': 'blocker',
         'reason': 'worker reported a blocker: needs   src/x.py   outside Touches'},
        {'task': 'T-3', 'state': 'held', 'attempt': 2, 'cause': 'validation', 'reason': 'integration validation failed'},
        {'task': 'T-4', 'state': 'held', 'attempt': 1, 'cause': 'validation', 'reason': 'will retry'},  # not a question yet
        {'task': 'T-2', 'state': 'waiting', 'blocked_by': ['T-2']},
    ], 'roots': [{'id': 'T-2', 'kind': 'claim', 'blocks': 3}, {'id': 'G1 gate review', 'kind': 'outside', 'blocks': 2},
                 {'id': 'T-1', 'kind': 'held', 'blocks': 1}]}


class QuestionTests(unittest.TestCase):
    def test_questions_are_built_easiest_first_without_a_model(self):
        found = questions.build(snapshot(), TODO, goals)
        self.assertEqual([(q['id'], q['effort'], q['type'], q['unblocks']) for q in found], [
            ('T-2', 'quick', 'USER_DECISION', 3), ('G1 gate review', 'decision', 'USER_DECISION', 2),
            ('T-1', 'input', 'USER_INPUT', 1), ('T-3', 'investigate', 'USER_DECISION', 0)])
        self.assertEqual(found[2]['task'], 'T-1 — Port the tuner')
        self.assertEqual(found[2]['needs'], 'worker reported a blocker: needs src/x.py outside Touches')

    def test_live_authorization_becomes_one_owner_question_in_blockers(self):
        condition = 'Live authorization: T-1'
        status = {'tasks': [{'task': 'T-1', 'state': 'waiting', 'blocked_by': [condition]}],
                  'roots': [{'id': condition, 'kind': 'outside', 'blocks': 1}]}
        found = questions.build(status, TODO, goals)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['id'], 'T-1')
        self.assertEqual(found[0]['task'], 'T-1 — Port the tuner')
        text = questions.update(None, found, now=NOW)
        self.assertEqual(text.count('### Q-'), 1)
        for option in ('Run it yourself', '`Live authorization: <record>`', 'Needs decision'):
            self.assertIn(option, text)
        self.assertNotIn('### Q-', questions.update(text, questions.build({}, TODO, goals), now=NOW))

    def test_a_claim_answered_with_its_holder_is_not_asked_again(self):
        """TOOLSET-198-8f: the owner noted who holds a claimed task, as the question asks, and the
        runner kept asking: /blockers said 0 questions, the TUI said 2."""
        from datetime import date, timedelta
        def todo_with(line):
            return TODO.replace('  Status: in_progress\n', f'  Status: in_progress\n  {line}\n')
        tomorrow, yesterday = date.today() + timedelta(days=1), date.today() - timedelta(days=1)
        ids = lambda text: [q['id'] for q in questions.build(snapshot(), text, goals)]
        self.assertNotIn('T-2', ids(todo_with(f'Held by: an isolated continuation; until {tomorrow}')))
        self.assertNotIn('T-2', ids(todo_with('Held by: the release owner')))  # no date: until removed
        expired = next(q for q in questions.build(snapshot(), todo_with(f'Held by: a continuation; until {yesterday}'),
                                                  goals) if q['id'] == 'T-2')
        self.assertIn(f'The recorded answer (Held by: a continuation; until {yesterday}) has expired', expired['needs'])
        plain = next(q for q in questions.build(snapshot(), TODO, goals) if q['id'] == 'T-2')
        self.assertIn('`Held by: <who>; until <YYYY-MM-DD>`', plain['answer'])

    def test_the_block_sits_under_active_and_nothing_else_changes(self):
        text = questions.update(OWNER, questions.build(snapshot(), TODO, goals), now=NOW)
        start, end = text.index(questions.START), text.index(questions.END) + len(questions.END)
        self.assertEqual(text[:start] + text[end:], OWNER.replace('## Active\n', '## Active\n\n\n', 1))
        self.assertIn('### Q-T-1 — USER_INPUT — effort input — unblocks 1\n\n- Task: T-1 — Port the tuner\n', text)
        self.assertIn('- Since: 2026-10-16T20:00:00Z\n- Answer: Answer in T-1\'s TODO.md entry', text)
        self.assertLess(text.index('Q-T-2'), text.index('Q-T-3'))

    def test_rewrites_keep_first_times_and_drop_answered_questions(self):
        first = questions.update(OWNER, questions.build(snapshot(), TODO, goals), now=NOW)
        later = datetime(2026, 10, 17, 8, 0, tzinfo=timezone.utc)
        again = questions.update(first, questions.build(snapshot(), TODO, goals), now=later)
        self.assertEqual(again, first)  # unchanged questions: unchanged bytes, so no commit
        answered = snapshot()
        answered['tasks'] = [t for t in answered['tasks'] if t['task'] != 'T-1']
        answered['roots'] = [r for r in answered['roots'] if r['id'] != 'T-1']
        after = questions.update(first, questions.build(answered, TODO, goals), now=later)
        self.assertNotIn('Q-T-1', after)
        self.assertIn('### Q-T-3', after)
        self.assertIn('- Since: 2026-10-16T20:00:00Z', after)  # T-3 kept its first time

    def test_no_questions_leaves_a_file_without_a_block_alone(self):
        self.assertEqual(questions.update(OWNER, [], now=NOW), OWNER)
        self.assertIsNone(questions.update(None, [], now=NOW))
        emptied = questions.update(questions.update(OWNER, questions.build(snapshot(), TODO, goals), now=NOW), [], now=NOW)
        self.assertNotIn('### Q-', emptied)
        self.assertIn(questions.START, emptied)  # the markers stay in place for next time

    def test_a_missing_file_gets_a_minimal_one(self):
        text = questions.update(None, questions.build(snapshot(), TODO, goals), now=NOW)
        self.assertTrue(text.startswith('# Blockers\n\n## Active\n\n' + questions.START))


if __name__ == '__main__':
    unittest.main()
