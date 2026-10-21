"""`autowork scorecard`: closes, held share, start to merge and owner questions per runner."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import scorecard  # noqa: E402

DAY = 86400
GOAL = ('+++\nschema = 1\nid = "G"\ntitle = "g"\npriority = 1\nsource = "docs/plan.md#g"\n'
        'status = "unmet"\nfocus = false\n+++\n')


def record(tid, status):
    return '\n'.join(['+++', 'schema = 1', f'id = "{tid}"', f'title = "{tid}"', f'short = "{tid}"',
                      f'status = "{status}"', 'goal = "G"', 'section = "Now"', 'rank = 1000', 'depends_on = []',
                      'touches = ["a.py"]', 'resources = []', 'kind = "implementation"', 'ownership = "worker"',
                      'scope = "x"', 'acceptance = ["x"]', 'checks = ["true"]', 'exclusions = []', '+++', ''])


def store(**statuses):
    return {'tasks/goals/G.md': GOAL, **{f"tasks/items/{t.replace('_', '-')}.md": record(t.replace('_', '-'), status)
                                         for t, status in statuses.items()}}


class ScorecardTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name)
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.repo)], check=True)
        self.now = time.time()

    def commit(self, path, text, age_days):
        self.commit_files({path: text}, age_days)

    def commit_files(self, files, age_days):
        for path, text in files.items():
            (self.repo / path).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / path).write_text(text)
        when = f'@{int(self.now - age_days * DAY)} +0000'
        env = dict(os.environ, GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
        path = ' '.join(sorted(files))
        subprocess.run(['git', '-C', str(self.repo), 'add', '--', *files], check=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=t', '-c', 'user.email=t@example.invalid',
                        'commit', '-q', '-m', f'update {path}'], check=True, env=env)

    def journal(self, *events):
        path = self.repo / '.git/autowork-execution/journal.jsonl'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join(json.dumps({'event': 'slot_changed', 'timestamp': self.now - age * 60,
                                            'task_id': task, 'previous_state': before, 'state': after}) + '\n'
                                for age, task, before, after in events))

    def test_a_week_of_one_runner(self):
        self.commit_files(store(OLD_1='done', T_2='open', T_3='open', T_4='open'), age_days=10)
        # Closed this week, however: a task already done before the window does not count.
        self.commit_files(store(OLD_1='done', T_2='done', T_3='done', T_4='open'), age_days=1)
        self.commit('BLOCKERS.md', '### Q-T-5 — USER_DECISION\n### Q-T-6 — USER_DECISION\n', age_days=2)
        self.commit('BLOCKERS.md', '### Q-T-5 — USER_DECISION\n', age_days=1)  # a repeat is one question
        self.journal((300, 'T-2', None, 'dispatched'), (290, 'T-2', 'dispatched', 'running'),
                     (200, 'T-2', 'reported', 'integrating'), (180, 'T-2', 'integrating', 'held'),
                     (150, 'T-2', 'reported', 'integrating'), (120, 'T-2', 'integrating', 'integrated'),
                     (100, 'T-3', None, 'dispatched'), (40, 'T-3', 'reported', 'integrating'),
                     (20, 'T-3', 'integrating', 'integrated'),
                     (60 * 24 * 9, 'T-9', 'integrating', 'held'))  # before the window
        row = scorecard.measure(self.repo, 7, now=self.now)
        self.assertEqual(row['closed'], 2)
        self.assertEqual((row['integrations'], row['held_share']), (3, 0.33))
        self.assertEqual(row['start_to_merge_minutes'], 130)  # median of 180 and 80 minutes
        self.assertEqual(row['questions'], 2)

    def test_a_window_across_the_conversion_counts_from_it(self):
        self.commit('TODO.archive.md', '- [x] **OLD-1** — closed long ago\n', age_days=10)
        self.commit_files(store(OLD_1='done', T_2='open'), age_days=5)  # the conversion closes nothing
        self.commit_files(store(OLD_1='done', T_2='done'), age_days=1)
        self.assertEqual(scorecard.measure(self.repo, 7, now=self.now)['closed'], 1)

    def test_a_repository_without_history_or_journal_scores_zero(self):
        row = scorecard.measure(self.repo, 7, now=self.now)
        self.assertEqual((row['closed'], row['integrations'], row['held_share'], row['start_to_merge_minutes'],
                          row['questions']), (0, 0, None, None, 0))

    def test_the_table_lists_each_runner_and_the_totals(self):
        rows = {'alpha': {'closed': 3, 'integrations': 4, 'held_share': 0.25, 'start_to_merge_minutes': 40,
                          'questions': 1},
                'beta': {'closed': 0, 'integrations': 0, 'held_share': None, 'start_to_merge_minutes': None,
                         'questions': 0}}
        text = '\n'.join(scorecard.table(rows, 7))
        self.assertIn('last 7 day(s)', text)
        self.assertIn('25% of 4', text)
        self.assertIn('2 runner(s): 3 task(s) closed, 1 question(s) for the owner', text)


if __name__ == '__main__':
    unittest.main()
