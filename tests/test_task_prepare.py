"""`autowork tasks prepare` and the Docs Sync task-store lifecycle on disposable repositories.

Each test drives the real CLI (`command.py tasks ...`) the way the docs-sync skill tells
every host to: prepare, reconcile through `autowork tasks`, validate the working tree,
commit, and prepare again. Nothing here runs a model; the skill's prose is checked only
for naming this lifecycle (DocsSyncInstructionTests), not for model adherence.
"""
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / 'pi-autowork/pi_autowork/command.py'
LEGACY = ROOT / 'tests/fixtures/task_migrate'
sys.path.insert(0, str(ROOT / 'pi-autowork/engine'))
sys.path.insert(0, str(ROOT / 'pi-autowork'))
from pi_autowork import task_migrate  # noqa: E402
from pi_autowork.legacy import reader  # noqa: E402
from task_store import TaskStore  # noqa: E402

PLAN = '''# Product plan

## Startup slice

Status: Accepted

The application starts and answers its health check.

## Export slice

Status: Accepted

Users export a report as CSV.

## Ideas

Status: Proposed

A plugin system, maybe.
'''


class Repo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'repo'
        self.repo.mkdir()
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 'f@example.invalid')
        self.git('config', 'user.name', 'F')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True,
                              text=True).stdout.strip()

    def commit(self, message='change'):
        self.git('add', '-A')
        self.git('commit', '-q', '--allow-empty', '-m', message)

    def write(self, path, text):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def tasks(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(COMMAND), 'tasks', *args], cwd=self.repo,
                                capture_output=True, text=True, timeout=120)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return result

    def prepare(self, *args, ok=True):
        result = self.tasks('prepare', *args, ok=False)
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode == 0, report['ok'])
        if ok:
            self.assertTrue(report['ok'], report)
        return report

    def store_bytes(self):
        return {str(p.relative_to(self.repo)): p.read_bytes()
                for p in sorted((self.repo / 'tasks').rglob('*')) if p.is_file()}

    def snapshot(self, lock=True):
        """Everything Audit must leave alone: files, refs, HEAD, index and Git metadata
        (object storage aside). ``lock=False`` leaves out the empty task-lock file a writer
        creates before it refuses."""
        files = {}
        for p in sorted(self.repo.rglob('*')):
            rel = p.relative_to(self.repo)
            if p.is_file() and 'objects' not in rel.parts[:2] and (lock or p.name != 'autowork-tasks.lock'):
                files[str(rel)] = hashlib.sha256(p.read_bytes()).hexdigest()
        return files, self.git('for-each-ref'), self.git('rev-parse', 'HEAD')

    def bootstrap(self):
        """What Docs Sync does on a repository whose accepted plan has two slices."""
        self.write('docs/plan.md', PLAN)
        self.write('src/app.py', 'print("hi")\n')
        self.commit('plan')
        self.tasks('goal', 'START', '--title', 'The application starts', '--source',
                   'docs/plan.md#startup-slice', '--priority', '1')
        self.tasks('goal', 'EXPORT', '--title', 'Reports export as CSV', '--source',
                   'docs/plan.md#export-slice', '--priority', '2', '--depends-on', 'START')
        start = self.add('START', 'Start the application', '--touches', 'src/')
        export = self.add('EXPORT', 'Export a report as CSV', '--touches', 'src/', '--depends-on', start)
        return start, export

    def add(self, goal, title, *extra):
        out = self.tasks('add', '--goal', goal, '--title', title, '--short', title[:40], '--scope', title,
                         '--acceptance', f'{title} works', '--checks', 'python3 -m unittest',
                         '--sources', f'[plan](docs/plan.md#{"startup" if goal == "START" else "export"}-slice)',
                         *extra).stdout
        return out.split()[-1]


class BootstrapTests(Repo):
    def test_a_new_repository_gets_goals_and_tasks_from_accepted_intent(self):
        self.write('docs/plan.md', PLAN)
        self.commit('plan')
        report = self.prepare()
        self.assertEqual(report['state'], 'none')
        self.assertEqual(report['accepted'], ['docs/plan.md#startup-slice', 'docs/plan.md#export-slice'])
        self.assertIn('bootstrap', report['next'])
        self.assertFalse((self.repo / 'tasks').exists(), 'prepare decides no intent itself')
        start, export = self.bootstrap()
        pending = self.prepare()
        self.assertEqual((pending['state'], pending['read']), ('uncommitted', 'worktree'))
        self.assertEqual(pending['order'], [start], 'EXPORT waits for START (goal and task dependency)')
        self.assertEqual(pending['diagnostics'], [])
        self.commit('tasks')
        report = self.prepare()
        self.assertEqual((report['state'], report['read'], report['drafts']), ('converted', 'HEAD', []))
        self.assertEqual(report['counts'], {'open:Now': 2})
        store = TaskStore.at(self.repo, 'HEAD')
        self.assertEqual(store.goals['START'].status, 'unmet', 'nothing is marked met without evidence')
        self.assertTrue(store.tasks[start].runnable)
        self.assertEqual(store.tasks[export].depends_on, (start,))

    def test_without_accepted_intent_no_queue_is_created(self):
        self.write('README.md', '# Tool\n\nIt might do things.\n')
        self.commit()
        report = self.prepare()
        self.assertEqual((report['state'], report['accepted']), ('none', []))
        self.assertIn('no heading is marked Status: Accepted', report['next'])
        self.assertFalse((self.repo / 'tasks').exists())

    def test_an_empty_store_folder_is_completed_by_the_first_goal(self):
        (self.repo / 'tasks/items').mkdir(parents=True)
        self.write('docs/plan.md', PLAN)
        self.commit()
        self.assertEqual(self.prepare()['state'], 'none')
        self.tasks('goal', 'START', '--title', 'Starts', '--source', 'docs/plan.md#startup-slice', '--priority', '1')
        self.assertEqual(self.prepare()['state'], 'uncommitted')


class LegacyTests(Repo):
    def setUp(self):
        super().setUp()
        for name in ('TODO.md', 'TODO.archive.md', 'goals.json'):
            (self.repo / name).write_bytes((LEGACY / name).read_bytes())
        self.commit('legacy queue')

    def test_a_legacy_repository_converts_without_a_separate_command(self):
        legacy = reader.order(self.repo)
        head = self.git('rev-parse', 'HEAD')
        report = self.prepare()
        self.assertEqual(report['state'], 'converted')
        action = report['actions'][0]
        self.assertEqual((action['action'], action['outcome'], action['order']), ('convert', 'CONVERTED', legacy))
        self.assertEqual(report['order'], legacy, 'selection order is unchanged')
        self.assertEqual(self.git('rev-parse', 'HEAD~1'), head, 'exactly one commit')
        self.assertIn('autowork migrate', self.git('log', '-1', '--format=%s'))
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertEqual(self.git('for-each-ref', 'refs/autowork'), '')
        self.assertFalse((self.repo / 'TODO.md').exists())
        self.assertFalse((self.repo / 'goals.json').exists())
        self.assertEqual((self.repo / 'TODO.archive.md').read_bytes(), (LEGACY / 'TODO.archive.md').read_bytes())
        t = TaskStore.at(self.repo, 'HEAD').tasks
        self.assertEqual((t['T-002'].depends_on, t['T-004'].live.value, t['T-006'].status),
                         (('T-001',), 'authorized', 'done'))
        self.assertEqual([t[i].rank for i in ('T-002', 'T-001', 'T-003')], [1000, 2000, 3000])
        # Already converted: nothing runs again.
        again = self.prepare()
        self.assertEqual((again['state'], again['actions']), ('converted', []))
        self.assertEqual(self.git('rev-parse', 'HEAD~1'), head)

    def test_without_commit_authority_the_conversion_is_staged(self):
        head = self.git('rev-parse', 'HEAD')
        report = self.prepare('--no-commit')
        self.assertEqual((report['actions'][0]['outcome'], report['state'], report['read']),
                         ('STAGED', 'uncommitted', 'worktree'))
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        staged = self.git('diff', '--cached', '--name-status').splitlines()
        self.assertIn('D\tTODO.md', staged)
        self.assertIn('A\ttasks/items/T-001.md', staged)
        self.assertEqual(self.git('diff', '--name-only'), '', 'working tree and index agree')
        # A later authorized run lands exactly the staged conversion.
        landed = self.prepare()
        self.assertEqual((landed['actions'][0]['outcome'], landed['state']), ('CONVERTED', 'converted'))
        self.assertEqual(self.git('rev-parse', 'HEAD~1'), head)
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_an_owner_commit_of_the_staged_conversion_completes_it(self):
        self.prepare('--no-commit')
        self.git('commit', '-q', '-m', 'owner commits the conversion')
        report = self.prepare()
        self.assertEqual((report['actions'][0]['outcome'], report['state']), ('ALREADY_CONVERTED', 'converted'))
        self.assertEqual(self.git('for-each-ref', 'refs/autowork'), '')

    def test_an_active_worker_refuses_without_changing_anything(self):
        folder = self.repo / '.git/autowork-execution/slots'
        folder.mkdir(parents=True)
        (folder / 'T-001.json').write_text(json.dumps({'task_id': 'T-001', 'state': 'running', 'attempt': 1}))
        before = self.snapshot(lock=False)
        report = self.prepare(ok=False)
        self.assertEqual(report['state'], 'legacy')
        self.assertIn('worker slots in flight', report['refusals'][0])
        self.assertIn('nothing was written', report['next'])
        self.assertEqual(self.snapshot(lock=False), before)

    def test_an_interrupted_conversion_resumes(self):
        head = self.git('rev-parse', 'HEAD')
        with mock.patch.object(task_migrate, 'finish', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                task_migrate.migrate(self.repo)
        candidate = self.git('rev-parse', task_migrate.CANDIDATE)
        # It stopped part-way: one file written, nothing staged, HEAD unmoved.
        self.write('tasks/items/T-001.md', self.git('show', f'{candidate}:tasks/items/T-001.md') + '\n')
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        self.assertEqual(self.prepare('--check')['would'], f'finish the recorded conversion {candidate[:12]}')
        report = self.prepare()
        self.assertEqual((report['actions'][0]['outcome'], report['actions'][0]['resumed']), ('CONVERTED', True))
        self.assertEqual(self.git('rev-parse', 'HEAD'), candidate)
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_an_interrupted_conversion_refuses_foreign_content(self):
        with mock.patch.object(task_migrate, 'finish', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                task_migrate.migrate(self.repo)
        self.write('tasks/items/T-001.md', 'someone else wrote this\n')
        before = self.snapshot(lock=False)
        report = self.prepare(ok=False)
        self.assertIn('tasks/items/T-001.md holds working-tree content', report['refusals'][0])
        self.assertEqual(self.snapshot(lock=False), before, 'the refusal writes nothing')
        (self.repo / 'tasks/items/T-001.md').unlink()
        self.assertEqual(self.prepare()['state'], 'converted')

    def test_audit_reads_a_legacy_repository_without_writing(self):
        before = self.snapshot()
        report = self.prepare('--check')
        self.assertEqual((report['state'], report['would']['convert']), ('legacy', 7))
        self.assertEqual(self.snapshot(), before)


class MaintainTests(Repo):
    def setUp(self):
        super().setUp()
        self.start, self.export = self.bootstrap()
        self.commit('tasks')

    def test_repeated_runs_are_byte_identical_and_add_nothing(self):
        first = self.prepare()
        store = self.store_bytes()
        head = self.git('rev-parse', 'HEAD')
        # A second pass re-records the same evidence: the same goal and the same task.
        self.tasks('goal', 'START', '--title', 'The application starts', '--source', 'docs/plan.md#startup-slice',
                   '--priority', '1')
        dup = self.tasks('add', '--goal', 'START', '--title', 'start the  Application', '--short', 's', ok=False)
        self.assertIn(f'{self.start} already records', dup.stderr)
        self.tasks('field', self.start, 'touches', 'src/')
        self.assertEqual(self.store_bytes(), store)
        self.assertEqual(self.git('status', '--porcelain'), '', 'nothing to commit')
        self.assertEqual(self.prepare(), first)
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)

    def test_missing_coverage_adds_only_the_missing_record(self):
        self.tasks('goal', 'DOCS', '--title', 'Documented', '--source', 'docs/plan.md#startup-slice',
                   '--priority', '3')
        self.commit()
        gap = [d for d in self.prepare()['diagnostics'] if d['code'] == 'GOAL_WITHOUT_WORK']
        self.assertEqual([d['id'] for d in gap], ['DOCS'])
        before = self.store_bytes()
        new = self.add('DOCS', 'Document startup', '--touches', 'README.md')
        after = self.store_bytes()
        self.assertEqual(set(after) - set(before), {f'tasks/items/{new}.md'})
        self.assertEqual({k: v for k, v in after.items() if k in before}, before)
        self.assertEqual(self.prepare()['diagnostics'], [])

    def test_an_incomplete_task_is_reported_and_repaired_field_by_field(self):
        path = self.repo / f'tasks/items/{self.export}.md'
        path.write_text(path.read_text().replace('checks = ["python3 -m unittest"]\n', ''))
        self.commit()
        report = self.prepare()
        self.assertIn(dict(code='DRAFT', id=self.export, detail='missing checks',
                           fix=f'autowork tasks field {self.export} <field> <value> from its accepted source; '
                               'never invent it'), report['diagnostics'])
        self.assertEqual(report['drafts'], [self.export])
        self.tasks('field', self.export, 'checks', 'python3 -m unittest')
        self.assertEqual(self.prepare()['drafts'], [])

    def test_unauthorized_live_work_stays_non_runnable(self):
        live = self.add('START', 'Deploy to staging', '--touches', 'deploy/', '--resources', 'live')
        self.commit()
        report = self.prepare()
        self.assertIn('LIVE_NOT_AUTHORIZED', [d['code'] for d in report['diagnostics'] if d['id'] == live])
        # Selection lists it (authority is admission's rule), but no worker may run it.
        self.assertFalse(TaskStore.at(self.repo, 'HEAD').tasks[live].runnable)
        self.tasks('place', live, 'Needs decision', '--decision', 'owner grants staging access')
        self.commit()
        report = self.prepare()
        self.assertNotIn(live, report['order'])
        self.assertEqual([d for d in report['diagnostics'] if d['id'] == live], [])
        self.assertEqual(TaskStore.at(self.repo, 'HEAD').tasks[live].live.value, 'denied')

    def test_an_in_flight_task_keeps_its_contract(self):
        folder = self.repo / '.git/autowork-execution/slots'
        folder.mkdir(parents=True)
        (folder / f'{self.start}.json').write_text(json.dumps({'task_id': self.start, 'state': 'running',
                                                               'attempt': 1}))
        before = self.store_bytes()
        for args in (('field', self.start, 'acceptance', 'other'), ('place', self.start, 'Next'),
                     ('done', self.start, '--evidence', 'x'), ('supersede', self.start, '--by', self.export,
                                                               '--reason', 'x')):
            refused = self.tasks(*args, ok=False)
            self.assertIn('held by a worker slot or a live lease', refused.stderr)
        self.assertEqual(self.store_bytes(), before)
        self.tasks('field', self.start, 'rank', '500')  # bookkeeping still allowed
        self.assertIn(self.start, self.prepare()['in_flight'])
        # A held (set-aside) attempt waits for exactly this repair.
        (folder / f'{self.start}.json').write_text(json.dumps({'task_id': self.start, 'state': 'held',
                                                               'attempt': 1}))
        self.tasks('field', self.start, 'acceptance', 'clarified')
        self.assertEqual(self.prepare()['in_flight'], [])

    def test_a_concurrent_edit_is_never_overwritten(self):
        shown = json.loads(self.tasks('show', self.start, '--worktree').stdout)
        path = self.repo / f'tasks/items/{self.start}.md'
        path.write_text(path.read_text().replace('scope = "Start the application"', 'scope = "Theirs"'))
        theirs = path.read_bytes()
        refused = self.tasks('field', self.start, 'scope', 'Mine', '--expect', shown['record_revision'], ok=False)
        self.assertIn('changed since revision', refused.stderr)
        self.assertEqual(path.read_bytes(), theirs)

    def test_writers_wait_for_the_task_lock(self):
        git_dir = Path(self.git('rev-parse', '--absolute-git-dir'))
        with open(git_dir / 'autowork-tasks.lock', 'a') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            writer = subprocess.Popen([sys.executable, str(COMMAND), 'tasks', 'field', self.start, 'Note', 'one'],
                                      cwd=self.repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(1)
            self.assertIsNone(writer.poll(), 'the writer waits while another holds the lock')
            fcntl.flock(handle, fcntl.LOCK_UN)
        _out, err = writer.communicate(timeout=60)
        self.assertEqual(writer.returncode, 0, err)
        self.assertIn('- Note: one', (self.repo / f'tasks/items/{self.start}.md').read_text())

    def test_audit_changes_no_file_ref_or_index(self):
        self.add('START', 'Uncommitted work', '--touches', 'src/')
        before = self.snapshot()
        report = self.prepare('--check')
        self.assertEqual((report['read'], len(report['pending'])), ('HEAD', 1))
        self.assertEqual(self.snapshot(), before)

    def test_no_completion_without_evidence(self):
        before = self.store_bytes()
        met = self.tasks('goal', 'START', '--status', 'met', ok=False)
        self.assertIn('needs --evidence', met.stderr)
        done = self.tasks('done', self.start, '--evidence', ' ', ok=False)
        self.assertIn('needs --evidence', done.stderr)
        self.assertEqual(self.store_bytes(), before)
        self.assertEqual(self.prepare()['counts'], {'open:Now': 2})

    def test_uncommitted_records_are_validated_as_the_working_tree_has_them(self):
        new = self.add('EXPORT', 'Export as JSON', '--touches', 'src/')
        report = self.prepare()
        self.assertEqual((report['read'], report['pending']), ('worktree', [f'tasks/items/{new}.md']))
        self.assertEqual((report['tasks'], report['counts']), (3, {'open:Now': 3}))
        (self.repo / f'tasks/items/{new}.md').write_text('+++\nschema = 1\nid = "OTHER"\n+++\n')
        broken = self.prepare(ok=False)
        self.assertEqual(broken['state'], 'invalid')
        self.assertIn(f'tasks/items/{new}.md', broken['refusals'][0])

    def test_broken_sources_and_duplicates_are_reported(self):
        self.tasks('goal', 'START', '--source', 'docs/plan.md#no-such-heading')
        twin = self.repo / 'tasks/items/TWIN-1.md'
        twin.write_text((self.repo / f'tasks/items/{self.start}.md').read_text()
                        .replace(f'id = "{self.start}"', 'id = "TWIN-1"'))
        self.commit()
        codes = {(d['code'], d['id']) for d in self.prepare()['diagnostics']}
        self.assertIn(('BROKEN_SOURCE', 'START'), codes)
        self.assertIn(('DUPLICATE_TASK', 'TWIN-1'), codes)  # the later ID is the duplicate

    def test_selection_follows_focus_rank_and_dependencies_after_reconciliation(self):
        # Reconciliation adds independent export work and focuses EXPORT.
        extra = self.add('EXPORT', 'Export header row', '--touches', 'src/')
        self.tasks('goal', 'EXPORT', '--focus')
        self.commit()
        order = self.prepare()['order']
        # EXPORT depends on START being met, so its tasks wait despite focus; START leads.
        self.assertEqual(order, [self.start])
        self.tasks('goal', 'EXPORT', '--no-focus', '--depends-on', 'START')
        self.tasks('goal', 'START', '--status', 'met', '--evidence', 'python3 -m unittest: pass')
        self.tasks('done', self.start, '--evidence', 'python3 -m unittest: pass')
        self.commit()
        self.assertEqual(self.prepare()['order'], [self.export, extra])
        why = json.loads(self.tasks('why', extra).stdout)
        self.assertEqual(why['reasons'][0]['code'], 'POSITION')


class DocsSyncInstructionTests(unittest.TestCase):
    """The installed instructions on every host run the same lifecycle; prose only."""

    def test_every_docs_sync_entry_runs_prepare_and_none_asks_the_owner_to_migrate(self):
        for path in ('skills/docs-sync/SKILL.md', 'adapters/skills/docs-sync/SKILL.md',
                     'skills/docs-sync/references/document-scaffold.md'):
            text = (ROOT / path).read_text()
            with self.subTest(path=path):
                self.assertIn('autowork tasks prepare', text)
                self.assertNotIn("owner's `autowork migrate`", text)
                self.assertNotIn('until the owner runs `autowork migrate', text)
                self.assertNotIn('do not convert it yourself', text)


if __name__ == '__main__':
    unittest.main()
