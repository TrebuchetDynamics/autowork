"""Offline planning sessions and explicit local application in disposable Git repos."""
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pi-autowork'))
from pi_autowork.planning import Planner, PlanningError


def git(repo, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    return subprocess.check_output(['git', '-C', str(repo), *args], env=env, stderr=subprocess.PIPE).decode().strip()


class PlanningTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.repo = self.root / 'repo'
        shutil.copytree(ROOT / 'pi-autowork/engine/fixtures/task_store', self.repo)
        (self.repo / '.gitignore').write_text('/.worktrees/\n')
        git(self.repo, 'init', '-q', '-b', 'main')
        git(self.repo, 'config', 'user.name', 'Fixture')
        git(self.repo, 'config', 'user.email', 'fixture@example.invalid')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-qm', 'fixture')
        self.planner = Planner(self.repo, state_root=self.root / 'state')
        self.session = self.planner.create('Improve the plan')
        self.id = self.session['id']
        self.worktree = Path(self.session['worktree'])

    def test_create_resume_private_and_canonical_identity(self):
        self.assertEqual(self.session['repo'], str(self.repo))
        self.assertEqual(self.worktree.parent, self.repo / '.worktrees')
        self.assertEqual(git(self.worktree, 'rev-parse', 'HEAD'), self.session['base'])
        resumed = Planner(self.worktree, state_root=self.root / 'state')
        self.assertEqual(resumed.get(self.id), self.session)
        self.assertEqual(resumed.sessions(), [self.session])
        for path in (self.root / 'state').rglob('*'):
            self.assertEqual(path.stat().st_mode & 0o777, 0o700 if path.is_dir() else 0o600)

    def test_preview_and_apply_scoped_local_commit_preserves_unrelated_edits(self):
        (self.repo / 'owner.txt').write_text('keep me\n')
        preview = self.planner.stage(self.id, {'docs/plans/cache.md': '# Cache plan\n'})
        self.assertTrue(preview['valid'], preview['errors'])
        self.assertIn('+# Cache plan', preview['diff'])
        self.assertEqual(preview['files'], ['docs/plans/cache.md'])
        result = self.planner.apply(self.id, preview['revision'])
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), result['commit'])
        self.assertEqual((self.repo / 'docs/plans/cache.md').read_text(), '# Cache plan\n')
        self.assertEqual((self.repo / 'owner.txt').read_text(), 'keep me\n')
        self.assertEqual(git(self.repo, 'diff', '--cached', '--name-only'), '')
        self.assertEqual(self.planner.get(self.id)['status'], 'applied')

    def test_stale_proposal_and_source_revisions_refused(self):
        preview = self.planner.stage(self.id, {'docs/plans/x.md': 'first\n'})
        self.planner.stage(self.id, {'docs/plans/x.md': 'second\n'})
        with self.assertRaisesRegex(PlanningError, 'revision|changed'):
            self.planner.apply(self.id, preview['revision'])
        preview = self.planner.preview(self.id)
        (self.repo / 'new').write_text('new')
        git(self.repo, 'add', 'new')
        git(self.repo, 'commit', '-qm', 'advance')
        with self.assertRaisesRegex(PlanningError, 'base|changed|source'):
            self.planner.apply(self.id, preview['revision'])
        self.assertTrue(self.worktree.exists())

    def test_path_symlink_size_and_authority_refusals(self):
        for path in ('../escape.md', 'tasks/evidence/X.md', '.git/config', 'docs/plans/../x.md',
                     'docs/plans/credentials.md', 'tasks/items/a/b.md'):
            with self.subTest(path=path), self.assertRaises(PlanningError):
                self.planner.stage(self.id, {path: 'bad'})
        (self.worktree / 'docs/plans').mkdir(parents=True, exist_ok=True)
        (self.worktree / 'docs/plans/link.md').symlink_to(self.repo / 'outside')
        with self.assertRaises(PlanningError):
            self.planner.stage(self.id, {'docs/plans/link.md': 'bad'})
        (self.worktree / 'docs/plans/link.md').unlink()
        with self.assertRaises(PlanningError):
            self.planner.stage(self.id, {'docs/plans/big.md': 'x' * (1024 * 1024)})
        original = (self.worktree / 'tasks/items/T-1.md').read_text()
        for changed in (original.replace('status = "open"', 'status = "done"'),
                        original.replace('live = "denied"', 'live = "authorized"')):
            preview = self.planner.stage(self.id, {'tasks/items/T-1.md': changed})
            self.assertFalse(preview['valid'])
            with self.assertRaises(PlanningError):
                self.planner.apply(self.id, preview['revision'])

    def test_live_resource_denial_cannot_be_removed_by_a_proposal(self):
        from pi_autowork import task_commands
        path = self.repo / 'tasks/items/T-1.md'
        source = path.read_text().replace('resources = []', 'resources = ["live"]')
        path.write_text(source)
        git(self.repo, 'add', 'tasks/items/T-1.md')
        git(self.repo, 'commit', '-qm', 'live gate')
        session = self.planner.create('Refine the live task')
        before = task_commands.TaskStore.at(self.repo, 'HEAD').tasks['T-1']
        self.assertFalse(before.runnable)
        shown = self.planner.stage(session['id'], {
            'tasks/items/T-1.md': source.replace('resources = ["live"]', 'resources = []')})
        self.assertFalse(shown['valid'], shown)
        with self.assertRaisesRegex(PlanningError, 'live'):
            self.planner.apply(session['id'], shown['revision'])
        self.assertEqual(path.read_text(), source)
        self.assertFalse(task_commands.TaskStore.at(self.repo, 'HEAD').tasks['T-1'].runnable)

    def test_cancel_at_settlement_does_not_stage_or_succeed(self):
        planner, _ = self.fake_planner('planner')
        cancel = threading.Event()
        def event(record):
            if record.get('type') == 'agent_settled':
                cancel.set()
        result = planner.send(self.id, cancel=cancel, on_event=event)
        self.assertEqual(result['status'], 'cancelled')
        self.assertFalse((self.worktree / 'docs/plans/proposed.md').exists())
        self.assertEqual(planner.get(self.id)['status'], 'cancelled')
        self.assertEqual(planner.preview(self.id)['files'], [])

    def test_execution_state_and_index_guards(self):
        preview = self.planner.stage(self.id, {'docs/plans/x.md': 'plan\n'})
        runtime = self.repo / '.git/autowork-execution'
        (runtime / 'slots').mkdir(parents=True)
        slot = runtime / 'slots/T-1.json'
        slot.write_text(json.dumps({'task_id': 'T-1', 'state': 'running', 'attempt': 1}))
        with self.assertRaisesRegex(PlanningError, 'execution guard'):
            self.planner.apply(self.id, preview['revision'])
        slot.unlink()
        lease = runtime / 'coordinator.json'
        lease.write_text('{broken')
        with self.assertRaisesRegex(PlanningError, 'execution guard'):
            self.planner.apply(self.id, preview['revision'])
        lease.unlink()
        with (runtime / 'writer.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(PlanningError, 'busy'):
                self.planner.apply(self.id, preview['revision'])
        (self.repo / '.git/MERGE_HEAD').write_text(self.session['base'])
        with self.assertRaisesRegex(PlanningError, 'progress'):
            self.planner.apply(self.id, preview['revision'])
        (self.repo / '.git/MERGE_HEAD').unlink()
        (self.worktree / 'docs/plans/x.md').chmod(0o755)
        self.assertFalse(self.planner.preview(self.id)['valid'])
        (self.worktree / 'docs/plans/x.md').chmod(0o600)
        git(self.worktree, 'add', 'docs/plans/x.md')
        with self.assertRaisesRegex(PlanningError, 'staged'):
            self.planner.apply(self.id, preview['revision'])
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), self.session['base'])

    def test_unrelated_staged_changes_are_preserved(self):
        (self.repo / 'owner.txt').write_text('owner staged\n')
        git(self.repo, 'add', 'owner.txt')
        before = git(self.repo, 'diff', '--cached')
        preview = self.planner.stage(self.id, {'docs/plans/x.md': 'plan\n'})
        self.planner.apply(self.id, preview['revision'])
        self.assertEqual(git(self.repo, 'diff', '--cached'), before)
        self.assertEqual(git(self.repo, 'show', 'HEAD:docs/plans/x.md'), 'plan')
        self.assertNotIn('owner.txt', git(self.repo, 'ls-tree', '--name-only', 'HEAD'))

    def test_dirty_overlap_and_checkout_writer_refused(self):
        preview = self.planner.stage(self.id, {'docs/plans/x.md': 'plan\n'})
        target = self.repo / 'docs/plans/x.md'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('owner\n')
        with self.assertRaisesRegex(PlanningError, 'overlap|dirty'):
            self.planner.apply(self.id, preview['revision'])
        self.assertEqual(target.read_text(), 'owner\n')
        target.unlink()
        lock = self.repo / '.git/interactive-writer.json'
        lock.write_text(json.dumps({'session': 'other', 'files': ['owner.txt']}))
        with self.assertRaisesRegex(PlanningError, 'writer|checkout'):
            self.planner.apply(self.id, preview['revision'])

    def test_duplicate_writer_refused(self):
        # Hold the public operation in validation, then a second instance must not write.
        from pi_autowork import planning
        original = planning.proposals.preview
        def overlap(*args, **kwargs):
            other = Planner(self.repo, state_root=self.root / 'state')
            with self.assertRaisesRegex(PlanningError, 'busy|writer'):
                other.stage(self.id, {'docs/plans/race.md': 'bad'})
            return original(*args, **kwargs)
        with patch.object(planning.proposals, 'preview', overlap):
            self.planner.stage(self.id, {'docs/plans/x.md': 'good'})
        self.assertFalse((self.worktree / 'docs/plans/race.md').exists())

    def test_refused_landing_keeps_candidate_and_can_retry_same_revision(self):
        preview = self.planner.stage(self.id, {'docs/plans/x.md': 'plan\n'})
        lock = self.repo / '.git/index.lock'
        lock.write_text('other Git writer')
        with self.assertRaisesRegex(PlanningError, 'index.*locked'):
            self.planner.apply(self.id, preview['revision'])
        candidate = git(self.worktree, 'rev-parse', 'HEAD')
        self.assertNotEqual(candidate, self.session['base'])
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), self.session['base'])
        lock.unlink()
        resumed = Planner(self.repo, state_root=self.root / 'state')
        result = resumed.apply(self.id, preview['revision'])
        self.assertEqual(result['commit'], candidate)

    def test_hook_tampering_never_lands_unaccepted_tree(self):
        preview = self.planner.stage(self.id, {'docs/plans/x.md': 'accepted\n'})
        hook = self.repo / '.git/hooks/pre-commit'
        hook.write_text('#!/bin/sh\nprintf injected > injected.txt\ngit add injected.txt\n')
        hook.chmod(0o700)
        with self.assertRaisesRegex(PlanningError, 'commit|tree|changed'):
            self.planner.apply(self.id, preview['revision'])
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), self.session['base'])
        self.assertFalse((self.repo / 'injected.txt').exists())

    def test_roadmap_and_invalid_store(self):
        roadmap = self.planner.roadmap(self.id)
        self.assertEqual(roadmap['errors'], [])
        self.assertIn('T-1', [t['id'] for t in roadmap['tasks']])
        preview = self.planner.stage(self.id, {'tasks/items/BAD.md': 'not a task'})
        self.assertFalse(preview['valid'])
        self.assertTrue(self.planner.roadmap(self.id)['errors'])

    def test_canonical_overlap_appearing_inside_landing_is_not_rebased(self):
        from pi_autowork import planning_proposals
        source = (self.worktree / 'tasks/items/T-1.md').read_text()
        preview = self.planner.stage(self.id, {'tasks/items/T-1.md': source.replace('rank = 1', 'rank = 5')})
        original = planning_proposals.landing.land_around_edits
        def edit_then_land(*args, **kwargs):
            (self.repo / 'tasks/items/T-1.md').write_text(source.replace('Free notes.', 'Owner notes.'))
            return original(*args, **kwargs)
        with patch.object(planning_proposals.landing, 'land_around_edits', edit_then_land):
            with self.assertRaisesRegex(PlanningError, 'dirty|overlap'):
                self.planner.apply(self.id, preview['revision'])
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), self.session['base'])
        self.assertIn('Owner notes.', (self.repo / 'tasks/items/T-1.md').read_text())

    def fake_planner(self, mode):
        from test_planning_rpc import FAKE
        script = self.root / mode
        script.write_text(FAKE)
        script.chmod(0o700)
        return Planner(self.repo, state_root=self.root / 'state', pi=script), script.with_suffix('.log')

    def test_send_resume_flags_literal_chat_and_private_history(self):
        planner, log = self.fake_planner('planner')
        events = []
        first = planner.send(self.id, on_event=events.append)
        self.assertEqual(first['status'], 'ready')
        self.assertTrue(first['preview']['valid'])
        self.assertFalse((self.repo / 'docs/plans/proposed.md').exists())
        resumed, _ = self.fake_planner('planner')
        second = resumed.send(self.id, '/skill:do-not-expand')
        self.assertEqual(second['status'], 'ready')
        self.assertEqual([r['role'] for r in resumed.history(self.id)], ['user', 'assistant', 'user', 'assistant'])
        records = [json.loads(line) for line in log.read_text().splitlines()]
        starts = [r['argv'] for r in records if 'argv' in r]
        self.assertEqual(len(starts), 2)
        for argv in starts:
            self.assertEqual(argv[argv.index('--session-id') + 1], self.id)
            self.assertEqual(argv[argv.index('--tools') + 1], 'read,grep,find,ls')
            for flag in ('--no-extensions', '--no-mcp', '--no-skills', '--no-context-files', '--no-approve'):
                self.assertIn(flag, argv)
            self.assertEqual(argv.count('--skill'), 3)
        prompts = [r['message'] for r in records if r.get('type') == 'prompt']
        self.assertTrue(prompts[0].startswith('/skill:plan-for-me '))
        self.assertFalse(prompts[1].startswith('/'))
        self.assertIn('/skill:do-not-expand', prompts[1])
        self.assertNotIn('sk-not-for-stdout-test', json.dumps(events))
        for path in (self.root / 'state').rglob('*'):
            self.assertEqual(path.stat().st_mode & 0o777, 0o700 if path.is_dir() else 0o600)

    def test_send_error_is_cli_compatible_and_persisted(self):
        planner, _ = self.fake_planner('missing_commands')
        with self.assertRaises(RuntimeError):
            planner.send(self.id)
        resumed = Planner(self.repo, state_root=self.root / 'state')
        self.assertIn('skill not discovered', resumed.get(self.id)['last_error'])

    def test_task_prompt_captures_pinned_blocker_context(self):
        (self.repo / 'BLOCKERS.md').write_text('## T-1: question\nNeed a cache size decision.\n\n## T-2\nOther question.\n')
        git(self.repo, 'add', 'BLOCKERS.md')
        git(self.repo, 'commit', '-qm', 'blocker context')
        planner, log = self.fake_planner('planner')
        session = planner.create(task='T-1')
        planner.send(session['id'])
        records = [json.loads(line) for line in log.read_text().splitlines()]
        message = next(r['message'] for r in records if r.get('type') == 'prompt')
        self.assertIn('Need a cache size decision.', message)
        self.assertNotIn('Other question.', message)

    def test_missing_skill_or_old_version_never_prompts(self):
        for mode in ('missing_commands', 'old_version'):
            planner, log = self.fake_planner(mode)
            with self.subTest(mode=mode), self.assertRaises(PlanningError):
                planner.send(self.id)
            if log.exists():
                self.assertFalse(any(json.loads(line).get('type') == 'prompt' for line in log.read_text().splitlines()))
            self.assertEqual(planner.get(self.id)['status'], 'error')

    def test_controller_cancellation_and_active_steer(self):
        planner, log = self.fake_planner('wait')
        cancel = threading.Event()
        results = []
        thread = threading.Thread(target=lambda: results.append(planner.send(self.id, cancel=cancel)))
        thread.start()
        try:
            deadline = time.monotonic() + 5
            while not log.exists() or '"type": "prompt"' not in log.read_text():
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.02)
            self.assertEqual(planner.steer(self.id, '/literal')['disposition'], 'queued')
        finally:
            cancel.set()
            thread.join(10)
        self.assertFalse(thread.is_alive())
        self.assertEqual(results[0]['status'], 'cancelled')
        self.assertEqual(planner.get(self.id)['status'], 'cancelled')
        with self.assertRaisesRegex(PlanningError, 'not active'):
            planner.steer(self.id, 'late')
        records = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertIn('abort', [r.get('type') for r in records])
        self.assertFalse(next(r['message'] for r in records if r.get('type') == 'steer').startswith('/'))

    def test_creation_requires_existing_ignore(self):
        (self.repo / '.gitignore').write_text('')
        with self.assertRaisesRegex(PlanningError, 'ignored'):
            self.planner.create()


if __name__ == '__main__':
    unittest.main()
