"""Idle in_progress claims: every activity check must pass before adoption."""
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

import parallel_claims as claims

DAY = 86400


class IdleClaimTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'repo'
        self.repo.mkdir()
        self.git('init', '-q', '-b', 'main')
        (self.repo / 'TODO.md').write_text('# TODO\n\n## Now\n\n- [ ] TASK-038 — Claimed\n  Status: in_progress\n'
                                          '- [ ] T-96 — Other\n  Status: in_progress\n')
        self.git('add', '.')
        self.commit('claim', when=1000)
        self.now = 1000 + DAY

    def git(self, *args, cwd=None, env=None):
        result = subprocess.run(['git', '-C', str(cwd or self.repo), *args], capture_output=True, text=True,
                                env={**os.environ, **(env or {})})
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def commit(self, message, when, cwd=None):
        stamp = f'@{when} +0000'
        self.git('-c', 'user.email=f@example.invalid', '-c', 'user.name=F', 'commit', '-qm', message, cwd=cwd,
                 env={'GIT_AUTHOR_DATE': stamp, 'GIT_COMMITTER_DATE': stamp})

    def idle(self, *tasks, workers=(), after=3600):
        return claims.idle_claims(self.repo, list(tasks), after, now=self.now, workers=list(workers))

    def test_an_old_claim_with_no_activity_is_idle(self):
        found = self.idle('TASK-038')
        self.assertEqual(set(found), {'TASK-038'})
        self.assertEqual(found['TASK-038']['idle_seconds'], DAY)
        self.assertEqual(found['TASK-038']['prior_work'], [])

    def test_a_recent_claim_change_is_not_idle(self):
        self.assertEqual(self.idle('TASK-038', after=DAY + 1), {})
        self.assertEqual(claims.idle_claims(self.repo, ['TASK-038'], 0, now=self.now, workers=[]), {})

    def test_a_branch_named_for_the_task_must_be_quiet_too(self):
        self.git('branch', 'agent/x/TASK-038-planning')
        self.git('checkout', '-q', 'agent/x/TASK-038-planning')
        (self.repo / 'plan.md').write_text('plan\n')
        self.git('add', '.')
        self.commit('plan', when=self.now - 60)  # committed a minute ago
        self.git('checkout', '-q', 'main')
        self.assertEqual(self.idle('TASK-038'), {})
        self.now += DAY
        work = self.idle('TASK-038')['TASK-038']['prior_work']
        self.assertEqual([w['branch'] for w in work], ['agent/x/TASK-038-planning'])
        self.assertEqual(set(self.idle('T-96')), {'T-96'})  # T-96 is not part of TASK-038's name
        self.assertEqual(self.idle('T-96')['T-96']['prior_work'], [])

    def test_uncommitted_changes_or_a_live_agent_in_its_worktree_block_adoption(self):
        tree = Path(self.temp.name) / 'wt'
        self.git('worktree', 'add', '-q', '-b', 'autowork/TASK-038', str(tree))
        self.assertEqual(set(self.idle('TASK-038')), {'TASK-038'})  # clean and old
        (tree / 'draft.txt').write_text('typing\n')
        self.now = time.time() + 1
        self.assertEqual(self.idle('TASK-038'), {})  # a file changed just now
        os.utime(tree / 'draft.txt', (1000, 1000))
        self.assertEqual(set(self.idle('TASK-038')), {'TASK-038'})
        session = {'kind': 'session', 'active': True, 'workspaces': [str(tree.resolve())]}
        self.assertEqual(self.idle('TASK-038', workers=[session]), {})
        self.assertEqual(set(self.idle('TASK-038', workers=[dict(session, active=False)])), {'TASK-038'})

    def note(self, text):
        todo = self.repo / 'TODO.md'
        todo.write_text(todo.read_text() + text)
        self.git('add', '.')
        self.commit('note', when=1000)

    def test_a_planner_note_elsewhere_holds_the_claim(self):
        """sierra: "retain TASK-030/TASK-029/TASK-014 open for that exact missing authority"; TASK-029 was adopted."""
        self.note('\n## Notes\n\n- Planner decision: retain TASK-030/TASK-038/TASK-014 open for that exact missing authority.\n')
        self.assertEqual(self.idle('TASK-038'), {})
        self.assertEqual(set(self.idle('T-96')), {'T-96'})  # T-96 is not named

    def test_a_hold_in_its_own_entry_holds_the_claim(self):
        todo = self.repo / 'TODO.md'
        todo.write_text(todo.read_text().replace('- [ ] T-96 — Other\n',
                                                 '- [ ] T-96 — Other\n  Ownership: unassigned. No worker dispatched by this entry.\n'))
        self.git('add', '.')
        self.commit('own note', when=1000)
        self.assertEqual(self.idle('T-96'), {})

    def test_a_plain_mention_does_not_hold_a_claim(self):
        self.note('\n- [ ] T-5 — Later\n  Dependencies: TASK-038.\n  Status: open\n')
        self.assertEqual(set(self.idle('TASK-038')), {'TASK-038'})

    def test_hold_note_wordings(self):
        for line in ('Keep T-7 open until the owner decides', 'T-7 is on hold', 'Do not dispatch T-7',
                     'T-7 needs explicit authorization first', 'T-7 awaiting owner approval'):
            with self.subTest(line=line):
                self.assertTrue(claims.hold_note(line + '\n', 'T-7'))
        self.assertIsNone(claims.hold_note('T-7 extends the parser; see T-8 for the format\n', 'T-7'))
        for line in ('T-7 adds the authorized schema amendment', 'T-7 preserves Agent authorization',
                     '| G-1 | T-7 held evidence | partial |', 'T-7 awaiting device access',
                     'T-7: with one post held by a synthetic event, flush returns False',
                     'T-7 shows fleet 403, pending approval, network outage'):
            with self.subTest(line=line):
                self.assertIsNone(claims.hold_note(line + '\n', 'T-7'))  # vocabulary, a table row, a condition

    def test_an_active_session_in_the_canonical_checkout_adopts_nothing(self):
        canonical = {'kind': 'session', 'active': True, 'workspaces': [str(self.repo.resolve())]}
        self.assertEqual(self.idle('TASK-038', workers=[canonical]), {})
        own_pool = {'kind': 'autowork', 'active': True, 'workspaces': [str(self.repo.resolve())]}
        self.assertEqual(set(self.idle('TASK-038', workers=[own_pool])), {'TASK-038'})


if __name__ == '__main__':
    unittest.main()
