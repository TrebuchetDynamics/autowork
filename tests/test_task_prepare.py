"""`autowork tasks prepare` and the Docs Sync task-store lifecycle on disposable repositories.

Each test drives the real CLI (`command.py tasks ...`) the way the docs-sync skill tells
every host to: prepare, reconcile through `autowork tasks`, validate the working tree,
commit, and prepare again. Nothing here runs a model; the skill's prose is checked only
for naming this lifecycle (DocsSyncInstructionTests), not for model adherence.
"""
import ast
import fcntl
from graphlib import CycleError, TopologicalSorter
import hashlib
from importlib.util import resolve_name
import json
import os
from pathlib import Path
import shutil
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

    def test_a_lone_legacy_file_is_reported_for_bootstrap_without_writes(self):
        self.write('docs/plan.md', PLAN)
        self.commit('plan')
        for name in ('TODO.md', 'goals.json'):
            (self.repo / name).write_bytes((LEGACY / name).read_bytes())
            for location in ('worktree', 'committed', 'HEAD only'):
                if location == 'committed':
                    self.commit('lone legacy file')
                elif location == 'HEAD only':
                    (self.repo / name).unlink()
                for args in ((), ('--force',), ('--check',)):
                    with self.subTest(name=name, location=location, args=args):
                        before = self.snapshot(lock=False)
                        report = self.prepare(*args)
                        self.assertEqual((report['state'], report['outcome']), ('none', 'NO_STORE'))
                        self.assertEqual(report['legacy_content'], [name])
                        self.assertEqual(report['accepted'],
                                         ['docs/plan.md#startup-slice', 'docs/plan.md#export-slice'])
                        self.assertEqual((report['actions'], report['refusals']), ([], []))
                        self.assertEqual(self.snapshot(lock=False), before)
            self.commit('remove lone legacy file')

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

    def slot(self, tid='T-001', state='running'):
        folder = self.repo / '.git/autowork-execution/slots'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f'{tid}.json').write_text(json.dumps({'task_id': tid, 'state': state, 'attempt': 1}))

    def without_intent(self, snapshot):
        files, refs, head = snapshot
        return {k: v for k, v in files.items() if not k.endswith('convert-intent.json')}, refs, head

    def test_an_active_worker_defers_the_conversion_to_the_runner(self):
        self.slot()
        before = self.snapshot(lock=False)
        result = self.tasks('prepare', ok=False)
        report = json.loads(result.stdout)
        self.assertEqual((result.returncode, report['ok'], report['outcome']), (3, False, 'MIGRATION_DEFERRED'))
        self.assertEqual(report['state'], 'legacy')
        self.assertIn('worker slots in flight', report['refusals'][0])
        self.assertIn('conversion deferred', report['next'])
        # Only the request is recorded, in the execution state: no file, ref, index or HEAD.
        self.assertEqual(self.without_intent(self.snapshot(lock=False)), self.without_intent(before))
        self.assertEqual(task_migrate.intent(self.repo)['requested_by'], 'autowork tasks prepare')
        # Repeating it records nothing new.
        recorded = (self.repo / '.git/autowork-execution/convert-intent.json').read_bytes()
        self.tasks('prepare', ok=False)
        self.assertEqual((self.repo / '.git/autowork-execution/convert-intent.json').read_bytes(), recorded)

    def test_without_commit_authority_work_in_flight_blocks_and_records_nothing(self):
        self.slot()
        before = self.snapshot(lock=False)
        report = self.prepare('--no-commit', ok=False)
        self.assertEqual(report['outcome'], 'MIGRATION_BLOCKED')
        self.assertIsNone(task_migrate.intent(self.repo))
        self.assertEqual(self.snapshot(lock=False), before)

    def test_audit_reports_a_deferral_without_recording_it(self):
        self.slot()
        before = self.snapshot()
        report = self.prepare('--check', ok=False)
        self.assertEqual(report['outcome'], 'MIGRATION_DEFERRED')
        self.assertNotIn('deferred', report)
        self.assertEqual(self.snapshot(), before)

    def test_uncommitted_planning_blocks_rather_than_defers(self):
        self.slot()
        (self.repo / 'TODO.md').write_text((self.repo / 'TODO.md').read_text() + '\n')
        report = self.prepare(ok=False)
        self.assertEqual(report['outcome'], 'MIGRATION_BLOCKED')
        self.assertIsNone(task_migrate.intent(self.repo))

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

    def test_prepare_lists_legacy_references_and_diagnoses_them_after_conversion(self):
        self.write('Makefile', 'check:\n\tcat TODO.md\n')
        self.write('tests/test_queue.py', 'open("goals.json")\n')
        self.write('README.md', 'See TODO.md.\n')
        self.commit()
        before = self.snapshot()
        report = self.prepare('--check', ok=False)
        self.assertEqual(report['outcome'], 'MIGRATION_BLOCKED')
        self.assertEqual([h['path'] for h in report['consumers']], ['Makefile', 'tests/test_queue.py'])
        self.assertEqual([h['path'] for h in report['documentation_drift']], ['README.md'])
        self.assertEqual(self.snapshot(), before)
        refused = self.prepare(ok=False)
        self.assertIn('--accept-consumers', refused['refusals'][0])
        self.assertFalse(refused['runner']['running'])
        self.assertIn('autowork tasks prepare --force', refused['next'])
        accepted = subprocess.run([sys.executable, str(COMMAND), 'migrate', str(self.repo), '--accept-consumers'],
                                  capture_output=True, text=True, timeout=120)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        after = self.prepare('--check')
        diagnostics = {(d['code'], d['id']) for d in after['diagnostics']}
        self.assertIn(('LEGACY_CONSUMER', 'Makefile'), diagnostics)
        self.assertIn(('LEGACY_CONSUMER', 'tests/test_queue.py'), diagnostics)
        self.assertIn(('LEGACY_DOCUMENTATION', 'README.md'), diagnostics)
        self.assertEqual(self.prepare('--check'), after)

    def test_prepare_reports_git_metadata_without_refusing_conversion_but_still_blocks_scripts(self):
        attributes = 'TODO.md merge=union\ngoals.json -diff\n'
        metadata = [dict(path='.gitattributes', line=1, names=['TODO.md']),
                    dict(path='.gitattributes', line=2, names=['goals.json'])]
        self.write('.gitattributes', attributes)
        self.commit('tracked Git metadata')
        checked = self.prepare('--check')
        self.assertEqual((checked['consumers'], checked['refusals']), ([], []))
        self.assertEqual(checked['git_metadata'], metadata)

        self.write('scripts/queue.sh', '#!/bin/sh\ncat TODO.md\n')
        self.commit('tracked script consumer alongside metadata')
        blocked = self.prepare('--check', ok=False)
        self.assertEqual(blocked['outcome'], 'MIGRATION_BLOCKED')
        self.assertEqual(blocked['consumers'], [dict(path='scripts/queue.sh', line=2, names=['TODO.md'])])
        self.assertEqual(blocked['git_metadata'], metadata)
        self.assertTrue(any('tracked legacy consumers' in r for r in blocked['refusals']))

        (self.repo / 'scripts/queue.sh').unlink()
        self.commit('remove the script consumer')
        converted = self.prepare()
        self.assertEqual(converted['state'], 'converted')
        self.assertEqual((converted['consumers'], converted['refusals']), ([], []))
        self.assertEqual(converted['git_metadata'], metadata)
        self.assertFalse(any(d['id'] == '.gitattributes' for d in converted['diagnostics']))
        self.assertEqual((self.repo / '.gitattributes').read_text(), attributes)
        self.assertEqual(self.git('show', 'HEAD:.gitattributes') + '\n', attributes)

    def test_prepare_preserves_content_and_reports_the_new_document(self):
        source = b'# Product checklist\n\nKeep TODO.md owner answers here.\n\n' + (self.repo / 'TODO.md').read_bytes()
        (self.repo / 'TODO.md').write_bytes(source)
        self.commit()
        checked = self.prepare('--check')
        self.assertEqual(checked['preserved'], dict(path='CHECKLIST.md', line_ranges=[[1, 3]]))
        converted = self.prepare()
        self.assertEqual((self.repo / 'CHECKLIST.md').read_bytes(), source)
        self.assertIn(dict(path='CHECKLIST.md', line=3, names=['TODO.md']), converted['documentation_drift'])
        self.assertEqual(converted['diagnostics'], self.prepare('--check')['diagnostics'])

    def test_audit_reads_a_legacy_repository_without_writing(self):
        before = self.snapshot()
        report = self.prepare('--check')
        self.assertEqual((report['state'], report['would']['convert']), ('legacy', 7))
        self.assertEqual(self.snapshot(), before)


class DeferredConversionTests(Repo):
    """A legacy repository a dead runner left with an attempt in flight and a claim: prepare
    defers, and the runner (task_migrate.convert_after_drain) drains and converts it."""

    def setUp(self):
        super().setUp()
        self.mid_attempt()

    def mid_attempt(self):
        """The legacy queue, T-001 claimed, and its attempt's worktree with committed and
        uncommitted work under a slot no live worker holds; prepare has deferred."""
        for name in ('TODO.md', 'TODO.archive.md', 'goals.json'):
            (self.repo / name).write_bytes((LEGACY / name).read_bytes())
        self.unclaimed = reader.order(self.repo)  # the queue before the legacy runner's claim
        ledger = json.loads((self.repo / 'goals.json').read_text())
        for task in ledger['tasks']:
            if task['id'] == 'T-001':
                task['status'] = 'in_progress'  # the legacy runner's claim
        (self.repo / 'goals.json').write_text(json.dumps(ledger, indent=2) + '\n')
        self.commit('the legacy runner claims T-001')
        (self.repo / '.git/info/exclude').write_text('/.worktrees/\n')  # as every runner repository
        self.worktree = self.repo / '.worktrees/autowork-T-001'
        self.git('worktree', 'add', '-q', '-b', 'autowork/T-001', str(self.worktree))
        (self.worktree / 'work.txt').write_text('committed work\n')
        subprocess.run(['git', '-C', str(self.worktree), 'add', 'work.txt'], check=True)
        subprocess.run(['git', '-C', str(self.worktree), 'commit', '-qm', 'T-001 work'], check=True)
        self.work = subprocess.run(['git', '-C', str(self.worktree), 'rev-parse', 'HEAD'], check=True,
                                   capture_output=True, text=True).stdout.strip()
        (self.worktree / 'draft.txt').write_text('uncommitted work\n')
        folder = self.repo / '.git/autowork-execution/slots'
        folder.mkdir(parents=True)
        (folder / 'T-001.json').write_text(json.dumps({
            'task_id': 'T-001', 'state': 'running', 'attempt': 1, 'worktree': str(self.worktree),
            'branch': 'autowork/T-001', 'baseline': self.git('rev-parse', 'HEAD')}))
        self.assertEqual(self.prepare(ok=False)['outcome'], 'MIGRATION_DEFERRED')

    def after_drain(self):
        """The runner's step, as it runs it: a helper whose lease owner is its parent (us)."""
        result = subprocess.run([sys.executable, str(COMMAND), 'migrate', str(self.repo), '--after-drain',
                                 '--owner-pid', str(os.getpid())], capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_the_runner_drains_and_converts_keeping_the_work(self):
        step = self.after_drain()
        self.assertEqual((step['outcome'], step['set_aside']), ('CONVERTED', ['T-001']), step)
        store = TaskStore.at(self.repo, 'HEAD')
        self.assertEqual(store.tasks['T-001'].status, 'open', 'the released claim converts open')
        # Its task is selectable again, where it was before the claim.
        self.assertEqual([t.id for t in __import__('task_select').order(store)], self.unclaimed)
        self.assertFalse((self.repo / 'TODO.md').exists())
        # The attempt's work is kept under its -set-aside name, committed and uncommitted.
        self.assertEqual(self.git('rev-parse', 'autowork/T-001-set-aside-1'), self.work)
        kept = Path(str(self.worktree) + '-set-aside-1')
        self.assertEqual((kept / 'draft.txt').read_text(), 'uncommitted work\n')
        self.assertFalse((self.repo / '.git/autowork-execution/slots/T-001.json').exists())
        self.assertIsNone(task_migrate.intent(self.repo))
        self.assertEqual(self.git('status', '--porcelain'), '')
        # The lease the drain took is released, so the runner's engine claims its own.
        import parallel_state
        self.assertIsNone(parallel_state.live_coordinator(parallel_state.common_dir(self.repo)))
        self.assertEqual(self.prepare()['outcome'], 'READY')

    def test_a_merge_already_in_main_is_named_not_silently_redone(self):
        record = self.repo / '.git/autowork-execution/slots/T-001.json'
        slot = json.loads(record.read_text())
        record.write_text(json.dumps(dict(slot, state='integrated',
                                          integration={'commit': self.git('rev-parse', 'HEAD')})))
        step = self.after_drain()
        self.assertEqual((step['outcome'], step['set_aside'], step['landed']), ('CONVERTED', ['T-001'], ['T-001']))

    def test_a_finished_slot_is_left_alone(self):
        record = self.repo / '.git/autowork-execution/slots/T-001.json'
        record.write_text(json.dumps(dict(json.loads(record.read_text()), state='released')))
        step = self.after_drain()
        self.assertEqual((step['outcome'], step['set_aside']), ('CONVERTED', []), step)
        self.assertTrue(record.exists())

    def test_a_live_worker_is_waited_for_never_stopped(self):
        import task_execution
        worker = subprocess.Popen(['sleep', '60'])
        self.addCleanup(worker.kill)
        record = self.repo / '.git/autowork-execution/slots/T-001.json'
        slot = json.loads(record.read_text())
        record.write_text(json.dumps(dict(slot, worker=task_execution.identity(worker.pid))))
        head = self.git('rev-parse', 'HEAD')
        step = self.after_drain()
        self.assertEqual((step['outcome'], step['set_aside']), ('WAITING', []), step)
        self.assertIn('T-001', step['detail'])
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        self.assertTrue(record.exists())
        self.assertTrue(worker.poll() is None, 'the worker keeps running')
        self.assertTrue(task_migrate.intent(self.repo), 'the request stays until it is done')
        # Once the worker has finished, the next cycle converts.
        worker.kill()
        worker.wait()
        self.assertEqual(self.after_drain()['outcome'], 'CONVERTED')

    def test_another_live_coordinator_is_never_broken(self):
        import parallel_state
        import task_execution
        other = subprocess.Popen(['sleep', '60'])
        self.addCleanup(other.kill)
        common = parallel_state.common_dir(self.repo)
        task_execution.save(common / 'coordinator.json', dict(
            owner=task_execution.identity(other.pid), workspace=str(self.repo.resolve()), profile='',
            max_workers=2, started_at=time.time()))
        head = self.git('rev-parse', 'HEAD')
        step = self.after_drain()
        self.assertEqual(step['outcome'], 'BLOCKED', step)
        self.assertIn('Live parallel coordinator', step['detail'])
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        self.assertTrue((self.repo / '.git/autowork-execution/slots/T-001.json').exists())


class ActivationTests(Repo):
    """A ready store under a runner whose release predates tasks/ is not executable yet."""

    def runner_on(self, release):
        """Fake this repository's running runner: its state lock held and the release it runs."""
        common = self.git('rev-parse', '--path-format=absolute', '--git-common-dir')
        state_root = Path(self.tmp.name) / f'state-{release[:12]}'
        state = state_root / hashlib.sha256(common.encode()).hexdigest()[:16]
        state.mkdir(parents=True)
        (state / 'runner.json').write_text(json.dumps({'pid': '1', 'toolset_rev': release}))
        holder = subprocess.Popen([sys.executable, '-c', 'import fcntl,sys,time\n'
                                   'h=open(sys.argv[1],"a");fcntl.flock(h,fcntl.LOCK_EX);print(1,flush=True);'
                                   'time.sleep(60)', str(state / 'lock')], stdout=subprocess.PIPE, text=True)
        self.addCleanup(holder.kill)
        holder.stdout.readline()
        return state_root

    def test_a_runner_on_a_release_before_the_task_store_is_activation_pending(self):
        self.bootstrap()
        self.git('add', '-A')
        self.commit('store')
        # A shallow clone (CI's checkout) has no history before the task store: nothing to compare.
        old = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--verify', '-q', '71e1a385^^{commit}'],
                             capture_output=True, text=True).stdout.strip()
        if not old:
            self.skipTest('the toolset history before the task store is not available here')
        with mock.patch.dict(os.environ, {'PI_AUTOWORK_STATE_DIR': str(self.runner_on(old))}):
            report = self.prepare()
            self.assertEqual((report['runner']['running'], report['runner']['reads_tasks']), (True, False))
            self.assertEqual(report['outcome'], 'ACTIVATION_PENDING')
        current = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True,
                                 text=True).stdout.strip()
        with mock.patch.dict(os.environ, {'PI_AUTOWORK_STATE_DIR': str(self.runner_on(current))}):
            self.assertEqual(self.prepare()['outcome'], 'READY')


def detached_sleep():
    """A process in its own session that init reaps once killed (no zombie keeps it 'live')."""
    out = subprocess.run(['sh', '-c', 'setsid sleep 120 >/dev/null 2>&1 & echo $!'], capture_output=True,
                         text=True, check=True).stdout.strip()
    pid = int(out)
    deadline = time.time() + 5
    while time.time() < deadline and Path(f'/proc/{pid}/stat').read_text().split()[5] != str(pid):
        time.sleep(0.05)  # setsid has made it its own session and group leader
    return pid


class ForceTests(Repo):
    """`/docs_sync force` (prepare --force) converts now instead of deferring, keeping all work."""

    def setUp(self):
        super().setUp()
        DeferredConversionTests.mid_attempt(self)
        self.calls = Path(self.tmp.name) / 'systemctl.log'
        fake = Path(self.tmp.name) / 'systemctl'
        fake.write_text(f'#!/bin/sh\necho "$@" >> {self.calls}\n')
        fake.chmod(0o755)
        self.env = {'PI_AUTOWORK_SYSTEMCTL': str(fake), 'PI_AUTOWORK_ENV_DIR': str(Path(self.tmp.name) / 'env'),
                    'PI_AUTOWORK_UNIT_DIR': str(Path(self.tmp.name) / 'units')}

    def force(self):
        with mock.patch.dict(os.environ, self.env):
            return self.prepare('--force', ok=False)

    def kill_later(self, pid):
        def end():
            try:
                os.kill(pid, 9)
            except ProcessLookupError:
                pass
        self.addCleanup(end)

    def test_force_stops_the_service_and_a_live_worker_and_converts_keeping_the_work(self):
        import task_execution
        pid = detached_sleep()
        self.kill_later(pid)
        record = self.repo / '.git/autowork-execution/slots/T-001.json'
        record.write_text(json.dumps(dict(json.loads(record.read_text()), worker=task_execution.identity(pid))))
        (self.repo / 'TODO.md').write_text((self.repo / 'TODO.md').read_text() + '\n')  # owner's edit
        report = self.force()
        self.assertEqual((report['ok'], report['outcome']), (True, 'MIGRATED'), report)
        step = report['forced']['step']
        self.assertEqual((step['stopped'], step['set_aside'], step['committed']), (['T-001'], ['T-001'], ['TODO.md']))
        self.assertIsNone(task_execution.identity(pid), 'the live worker was stopped')
        self.assertEqual(self.git('rev-parse', 'autowork/T-001-set-aside-1'), self.work)
        self.assertEqual((Path(str(self.worktree) + '-set-aside-1') / 'draft.txt').read_text(), 'uncommitted work\n')
        self.assertIn('owner planning before a forced conversion', self.git('log', '--format=%s', '-3'))
        self.assertTrue(self.git('ls-tree', '--name-only', 'HEAD', 'tasks'))
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertIsNone(task_migrate.intent(self.repo))

    def test_force_reports_drift_and_uses_todo_order(self):
        (self.repo / '.git/autowork-execution/slots/T-001.json').unlink()
        ledger = json.loads((self.repo / 'goals.json').read_text())
        ledger['tasks'][0]['status'] = 'open'
        ledger['priority_order']['tasks'] = ['T-003', 'T-001', 'T-002', 'T-004', 'T-005', 'T-007']
        self.write('goals.json', json.dumps(ledger))
        self.commit('stale order')
        plain = self.prepare(ok=False)
        self.assertEqual(plain['outcome'], 'MIGRATION_BLOCKED')
        self.assertIn('order differs from the recorded priority', ' '.join(plain['refusals']))
        report = self.force()
        self.assertEqual(report['outcome'], 'MIGRATED', report)
        step = report['forced']['step']
        self.assertIn('T-003', step['drift'])
        self.assertEqual(step['order'], ['T-004', 'T-001', 'T-003', 'T-005'])
        tasks = TaskStore.at(self.repo, 'HEAD').tasks
        self.assertEqual([tasks[tid].rank for tid in ('T-002', 'T-001', 'T-003')], [1000, 2000, 3000])

    def test_force_accepts_consumers_over_a_dead_held_slot_and_reports_them(self):
        script = '#!/bin/sh\ncat TODO.md\n'
        self.write('scripts/queue.sh', script)
        self.commit('tracked consumer')
        record = self.repo / '.git/autowork-execution/slots/T-001.json'
        record.write_text(json.dumps(dict(json.loads(record.read_text()), state='held', cause='validation')))
        refused = self.prepare(ok=False)
        self.assertEqual(refused['outcome'], 'MIGRATION_BLOCKED')
        self.assertTrue(any('worker slots in flight' in r for r in refused['refusals']))
        self.assertTrue(any('tracked legacy consumers' in r and 'scripts/queue.sh:2' in r
                            for r in refused['refusals']))
        self.assertIn('autowork tasks prepare --force', refused['next'])
        head = self.git('rev-parse', 'HEAD')
        report = self.force()
        self.assertEqual((report['ok'], report['outcome']), (True, 'MIGRATED'), report)
        self.assertEqual(report['forced']['step']['set_aside'], ['T-001'])
        self.assertEqual(self.git('rev-parse', 'HEAD~1'), head)
        diagnostic = next(d for d in report['diagnostics'] if d['code'] == 'LEGACY_CONSUMER')
        self.assertEqual((diagnostic['id'], diagnostic['detail']),
                         ('scripts/queue.sh', 'scripts/queue.sh:2 names TODO.md'))
        self.assertEqual((self.repo / 'scripts/queue.sh').read_text(), script)
        self.assertEqual(self.git('show', 'HEAD:scripts/queue.sh') + '\n', script)
        self.assertEqual((Path(str(self.worktree) + '-set-aside-1') / 'draft.txt').read_text(), 'uncommitted work\n')
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_force_ends_another_runner_holding_the_lease(self):
        import parallel_state
        import task_execution
        pid = detached_sleep()
        self.kill_later(pid)
        common = parallel_state.common_dir(self.repo)
        task_execution.save(common / 'coordinator.json', dict(
            owner=task_execution.identity(pid), workspace=str(self.repo.resolve()), profile='',
            max_workers=2, started_at=time.time()))
        report = self.force()
        self.assertEqual(report['outcome'], 'MIGRATED', report)
        self.assertIn(f'PID {pid}', report['forced']['step']['ended'][0])
        self.assertIsNone(task_execution.identity(pid))

    def test_a_running_service_is_stopped_then_started_again(self):
        fake = Path(self.env['PI_AUTOWORK_SYSTEMCTL'])
        fake.write_text(f'#!/bin/sh\necho "$@" >> {self.calls}\n'
                        'case "$*" in *is-active*) exit 0;; esac\nexit 0\n')
        report = self.force()
        self.assertEqual(report['outcome'], 'MIGRATED', report)
        self.assertEqual((report['forced']['service_stopped'], report['forced']['service_started']), (True, True))
        calls = self.calls.read_text().splitlines()
        stop = next(i for i, c in enumerate(calls) if c.startswith('--user stop pi-autowork@'))
        start = next(i for i, c in enumerate(calls) if c.startswith('--user start pi-autowork@'))
        self.assertLess(stop, start)

    def test_force_never_overwrites_content_it_cannot_account_for(self):
        with mock.patch.object(task_migrate, 'finish', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                with mock.patch.object(task_migrate, 'refusals', return_value=[]):
                    task_migrate.convert(self.repo, released=task_migrate.claimed(self.repo))
        self.write('tasks/items/T-001.md', 'someone else wrote this\n')
        report = self.force()
        self.assertEqual((report['ok'], report['outcome']), (False, 'MIGRATION_BLOCKED'), report)
        self.assertEqual((self.repo / 'tasks/items/T-001.md').read_text(), 'someone else wrote this\n')
        self.assertTrue((self.repo / 'TODO.md').exists())


class PackageImportTests(unittest.TestCase):
    def test_every_module_imports_in_isolation_and_all_import_edges_are_acyclic(self):
        package = ROOT / 'Src/pi_autowork'
        modules = {}
        for path in sorted(package.rglob('*.py')):
            if 'engine' in path.relative_to(package).parts:
                continue  # retain the runner/legacy graph boundary; engine has its own guards
            parts = path.relative_to(package.parent).with_suffix('').parts
            name = '.'.join(parts[:-1] if parts[-1] == '__init__' else parts)
            modules[name] = path
        graph = {name: set() for name in modules}
        for name, path in modules.items():
            parent = name if path.name == '__init__.py' else name.rpartition('.')[0]
            # Walk function bodies too: deferred imports must not hide a cycle.
            for node in ast.walk(ast.parse(path.read_text())):
                targets = []
                if isinstance(node, ast.Import):
                    targets = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    base = node.module or ''
                    if node.level:
                        base = resolve_name('.' * node.level + base, parent)
                    targets = [base, *(f'{base}.{alias.name}' for alias in node.names)]
                # Frozen legacy readers use bare sibling names via their own sys.path.
                for target in targets:
                    if target not in modules:
                        target = f'pi_autowork.legacy.{target}'
                    if target in modules:
                        graph[name].add(target)
        try:
            list(TopologicalSorter(graph).static_order())
        except CycleError as exc:
            self.fail(f'pi_autowork import cycle (including deferred imports): {exc}')
        script = ('import importlib,sys; sys.path[:0] = sys.argv[1:4]; '
                  'importlib.import_module(sys.argv[4])')
        for name in modules:
            with self.subTest(module=name):
                python = [sys.executable]
                if name == 'pi_autowork.tui':
                    if not shutil.which('uv'):
                        self.skipTest('uv is not installed (optional Textual UI)')
                    python = ['uv', 'run', '--offline', '--quiet', '--no-project', '--with',
                              'textual==8.2.8', 'python3']
                result = subprocess.run([*python, '-c', script, str(ROOT / 'pi-autowork'),
                                         str(ROOT / 'pi-autowork/engine'), str(package / 'legacy'), name],
                                        capture_output=True, text=True, timeout=60)
                if name == 'pi_autowork.tui' and result.returncode == 2 and \
                        'textual' in result.stderr.lower() and 'offline' in result.stderr.lower():
                    self.skipTest('textual==8.2.8 is not in the uv cache (offline)')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class CapabilityTests(unittest.TestCase):
    """The handshake a skill runs before it writes: this executable's commands and prepare API."""

    def test_capabilities_name_the_release_tasks_verbs_and_prepare_api(self):
        result = subprocess.run([sys.executable, str(COMMAND), 'capabilities'], capture_output=True, text=True,
                                timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        found = json.loads(result.stdout)
        self.assertIn('tasks', found['commands'])
        self.assertTrue({'prepare', 'add', 'goal', 'validate'} <= set(found['tasks']))
        self.assertGreaterEqual(found['prepare_api'], 2)
        self.assertIn('MIGRATION_DEFERRED', found['prepare_outcomes'])
        self.assertEqual(Path(found['toolset']), ROOT)

    def test_an_older_cli_fails_the_handshake_instead_of_being_used(self):
        """A release without the handshake exits non-zero on it; the skill stops there."""
        result = subprocess.run([sys.executable, str(COMMAND), 'no-such-capability'], capture_output=True,
                                text=True, timeout=60)
        self.assertNotEqual(result.returncode, 0)


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
                     ('done', self.start, '--by', 'owner', '--reason', 'x'), ('supersede', self.start, '--by', self.export,
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

    def test_no_completion_without_a_manual_reason_or_goal_evidence(self):
        before = self.store_bytes()
        met = self.tasks('goal', 'START', '--status', 'met', ok=False)
        self.assertIn('needs --evidence', met.stderr)
        done = self.tasks('done', self.start, '--by', 'owner', '--reason', ' ', ok=False)
        self.assertIn('nonempty --by and --reason', done.stderr)
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
        self.tasks('done', self.start, '--by', 'owner', '--reason', 'Start checked offline')
        self.tasks('field', self.start, 'owner_qualification', 'Owner: python3 -m unittest: pass')
        self.tasks('goal', 'START', '--status', 'met', '--evidence', 'python3 -m unittest: pass')
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
                if path.startswith(('skills/docs-sync/SKILL', 'adapters/')):
                    # The handshake comes first, and a mismatch never falls back to TODO.md.
                    self.assertLess(text.index('autowork capabilities'), text.index('autowork tasks prepare .')
                                    if 'autowork tasks prepare .' in text else text.index('### Prepare the store'))
                    self.assertIn('TOOLCHAIN_MISMATCH', text)
                    self.assertIn('MIGRATION_DEFERRED', text)
                self.assertNotIn("owner's `autowork migrate`", text)
                self.assertNotIn('until the owner runs `autowork migrate', text)
                self.assertNotIn('do not convert it yourself', text)


if __name__ == '__main__':
    unittest.main()
