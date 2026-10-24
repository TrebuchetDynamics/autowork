"""`autowork scorecard`: closes, held share, start to merge and owner questions per runner."""
import contextlib
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import accounting, command, scorecard  # noqa: E402

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
        env = mock.patch.dict(os.environ, {'PI_AUTOWORK_STATE_DIR': str(self.repo / 'private-state')})
        env.start()
        self.addCleanup(env.stop)
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.repo)], check=True)
        self.now = time.time()

    def commit(self, path, text, age_days):
        self.commit_files({path: text}, age_days)

    def commit_files(self, files, age_days, message=None):
        for path, text in files.items():
            (self.repo / path).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / path).write_text(text)
        when = f'@{int(self.now - age_days * DAY)} +0000'
        env = dict(os.environ, GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
        path = ' '.join(sorted(files))
        subprocess.run(['git', '-C', str(self.repo), 'add', '--', *files], check=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=t', '-c', 'user.email=t@example.invalid',
                        'commit', '-q', '-m', message or f'update {path}'], check=True, env=env)
        return subprocess.check_output(['git', '-C', str(self.repo), 'rev-parse', 'HEAD'], text=True).strip()

    def journal(self, *events):
        path = self.repo / '.git/autowork-execution/journal.jsonl'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join(json.dumps({'event': 'slot_changed', 'timestamp': self.now - age * 60,
                                            'task_id': task, 'previous_state': before, 'state': after}) + '\n'
                                for age, task, before, after in events))

    def test_a_week_of_one_runner(self):
        self.commit_files(store(OLD_1='done', T_2='open', T_3='open', T_4='open'), age_days=10)
        # Closed this week, however: a task already done before the window does not count.
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
        from task_store import TaskStore
        snapshot = TaskStore.at(self.repo, 'HEAD')
        candidate = self.commit_files({'work.txt': 'fixture'}, age_days=9)
        git = ['git', '-C', str(self.repo), '-c', 'user.name=t', '-c', 'user.email=t@example.invalid']
        tree = subprocess.check_output([*git, 'rev-parse', 'HEAD^{tree}'], text=True).strip()
        integration = subprocess.check_output([*git, 'commit-tree', tree, '-p', snapshot.rev, '-p', candidate,
                                               '-m', 'integration'], text=True).strip()
        subprocess.run([*git, 'update-ref', 'HEAD', integration, candidate], check=True)
        files = store(OLD_1='done', T_2='done', T_3='done', T_4='done')
        files['tasks/evidence/T-2.toml'] = (f'schema = 1\ntask = "T-2"\ncontract_hash = "{snapshot.tasks["T-2"].contract_hash}"\n'
                                          f'candidate = "{candidate}"\nintegration = "{integration}"\n'
                                          f'tree = "{tree}"\nresult = "pass"\nreview = "passed"\n')
        files['tasks/items/T-4.md'] = files['tasks/items/T-4.md'].replace(
            'status = "done"', 'status = "done"\nclosure = "coordinator_verified"\nclosure_evidence = "tasks/evidence/T-4.toml"')
        files['tasks/items/T-2.md'] = files['tasks/items/T-2.md'].replace(
            'status = "done"', 'status = "done"\nclosure = "coordinator_verified"\nclosure_evidence = "tasks/evidence/T-2.toml"')
        files['tasks/items/T-3.md'] = files['tasks/items/T-3.md'].replace(
            'status = "done"', 'status = "done"\nclosure = "manual"\nclosure_actor = "owner"\n'
            'closure_timestamp = "2026-10-21T00:00:00+00:00"\nclosure_reason = "Hand closed"')
        self.commit_files(files, age_days=1)
        self.commit('BLOCKERS.md', '### Q-T-5 — USER_DECISION\n### Q-T-6 — USER_DECISION\n', age_days=2)
        self.commit('BLOCKERS.md', '### Q-T-5 — USER_DECISION\n', age_days=1)  # a repeat is one question
        self.journal((300, 'T-2', None, 'dispatched'), (290, 'T-2', 'dispatched', 'running'),
                     (200, 'T-2', 'reported', 'integrating'), (180, 'T-2', 'integrating', 'held'),
                     (150, 'T-2', 'reported', 'integrating'), (120, 'T-2', 'integrating', 'integrated'),
                     (100, 'T-3', None, 'dispatched'), (40, 'T-3', 'reported', 'integrating'),
                     (20, 'T-3', 'integrating', 'integrated'),
                     (60 * 24 * 9, 'T-9', 'integrating', 'held'))  # before the window
        state = accounting.state_dir(self.repo)
        state.mkdir(parents=True)
        runs = [dict(run_id=identity, time=self.now - 3600, task='T-2', attempt_id=attempt,
                     role=role, host=host, model=model, input_tokens=10, output_tokens=2,
                     tokens=12, cost_usd=cost, cost_source='provider_reported')
                for identity, attempt, role, host, model, cost in (
                    ('w1', 'a1', 'worker', 'pi', 'm1', 1), ('r1', 'a1', 'verify', 'pi', 'm2', 2),
                    ('w2', 'a2', 'worker', 'claude', 'm3', 3), ('c1', 'a2', 'merge', 'pi', 'm2', 4))]
        (state / 'runs.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in [*runs, runs[0]]))
        journal = self.repo / '.git/autowork-execution/journal.jsonl'
        facts = [dict(event_id=kind, task_id='T-2', event=kind, timestamp=self.now - 60)
                 for kind in ('closed', 'delivered', 'blocker_answered', 'contract_edited')]
        with journal.open('a') as stream:
            stream.write(json.dumps(dict(event='task_lifecycle', timestamp=self.now - 60,
                                         lifecycle=[*facts, facts[-1]])) + '\n')
        row = scorecard.measure(self.repo, 7, now=self.now)
        usage = row['usage']
        task = usage['tasks']['T-2']
        self.assertEqual((task['runs'], task['cost_usd'], task['input_tokens'], task['output_tokens']),
                         (4, 10, 40, 8))
        self.assertEqual({r: v['cost_usd'] for r, v in task['roles'].items()},
                         {'worker': 4, 'reviewer': 2, 'coordinator': 4})
        self.assertEqual({a: v['cost_usd'] for a, v in task['attempts'].items()}, {'a1': 3, 'a2': 7})
        self.assertEqual({(r['host'], r['model']) for r in task['host_models']},
                         {('pi', 'm1'), ('pi', 'm2'), ('claude', 'm3')})
        self.assertEqual((usage['verified_tasks'], usage['delivered_tasks'],
                          usage['cost_per_verified_task_usd'], usage['cost_per_delivered_task_usd']), (1, 1, 10, 10))
        self.assertEqual(task['interventions'], {'blocker_answered': 1, 'contract_edited': 1})
        self.assertIsNone(task['owner_minutes'])
        self.assertEqual(usage['diagnostics']['duplicate_runs'], 1)
        self.assertEqual(row['closed'], 3)
        self.assertEqual((row['verified_closed'], row['manual_closed'], row['unverified_closed']), (1, 1, 1))
        table = '\n'.join(scorecard.table({'fixture': row}, 7))
        self.assertIn('verified', table)
        self.assertIn('manual', table)
        self.assertEqual((row['integrations'], row['held_share']), (3, 0.33))
        self.assertEqual(row['start_to_merge_minutes'], 130)  # median of 180 and 80 minutes
        self.assertEqual(row['questions'], 2)

    def test_unknown_billing_and_incomplete_runs_are_reported_apart_from_measured_spend(self):
        self.commit_files(store(A='open', B='open'), age_days=1)
        state = accounting.state_dir(self.repo)
        state.mkdir(parents=True)
        records = [dict(time=self.now - 60, run_id=str(i), task=task, role=role, tokens=10,
                        cost_usd=cost, cost_source=source, billing=billing)
                   for i, (task, role, cost, source, billing) in enumerate((
                       ('A', 'worker', 2, 'provider_reported', 'api'),
                       ('A', 'verify', None, 'missing', 'api'),
                       ('B', 'worker', 0, 'provider_reported', 'subscription'),
                       ('B', None, 3, 'provider_reported', 'api'),
                       (None, 'worker', 4, 'provider_reported', 'api'),
                       ('A', 'worker', 99, None, 'api'),
                       ('DOCS-MAINTAINER', 'maintainer', 5, 'provider_reported', 'api'),
                       ('20261021-100000', 'merge', 6, 'provider_reported', 'api')))]  # old catalog-based record
        (state / 'runs.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in records) + '{torn')
        usage = scorecard.measure(self.repo, 7, now=self.now)['usage']
        self.assertIsNone(usage['cost_usd'])
        self.assertEqual(usage['measured_cost_usd'], 20)
        self.assertEqual(usage['unknown_cost_tasks'], ['A', 'B'])
        self.assertEqual(usage['unattributed']['runs'], 4)
        self.assertEqual(usage['unattributed']['measured_cost_usd'], 18)
        self.assertNotIn('DOCS-MAINTAINER', usage['tasks'])
        self.assertNotIn('20261021-100000', usage['tasks'])
        self.assertEqual(usage['diagnostics']['invalid_records'], 1)
        self.assertIsNone(usage['tasks']['A']['cost_usd'])
        self.assertIsNone(usage['tasks']['B']['cost_usd'])
        self.assertIsNone(usage['tasks']['B']['owner_minutes'])
        self.assertIsNone(usage['tasks']['A']['input_tokens'])
        # An unreadable run must also invalidate an otherwise fully measured bill.
        (state / 'runs.jsonl').write_text(json.dumps(records[0]) + '\n{torn')
        usage = accounting.measure(self.repo, self.now - DAY, self.now, verified=['A'])
        self.assertEqual(usage['measured_cost_usd'], 2)
        self.assertIsNone(usage['cost_usd'])
        self.assertIsNone(usage['cost_per_verified_task_usd'])
        self.assertEqual(usage['diagnostics']['invalid_run_records'], 1)
        # An attention-log error does not make a known bill unknown.
        (state / 'runs.jsonl').write_text(json.dumps(records[0]) + '\n')
        (state / 'attention.jsonl').write_text('{torn')
        usage = accounting.measure(self.repo, self.now - DAY, self.now, verified=['A'])
        self.assertEqual(usage['cost_per_verified_task_usd'], 2)
        self.assertEqual(usage['diagnostics']['invalid_attention_records'], 1)

    def test_a_window_across_the_conversion_counts_from_it(self):
        self.commit('TODO.archive.md', '- [x] **OLD-1** — closed long ago\n', age_days=10)
        self.commit_files(store(OLD_1='done', T_2='open'), age_days=5)  # the conversion closes nothing
        self.commit_files(store(OLD_1='done', T_2='done'), age_days=1)
        self.assertEqual(scorecard.measure(self.repo, 7, now=self.now)['closed'], 1)

    def test_a_repository_without_history_or_journal_scores_zero(self):
        row = scorecard.measure(self.repo, 7, now=self.now)
        self.assertEqual((row['closed'], row['integrations'], row['held_share'], row['start_to_merge_minutes'],
                          row['questions']), (0, 0, None, None, 0))

    def test_only_a_revert_of_the_receipt_integration_attributes_a_regression(self):
        self.commit_files(store(A='open'), age_days=12)
        delivered = self.commit_files({'a.py': 'broken\n'}, age_days=10)
        unrelated = self.commit_files({'other.py': 'unrelated\n'}, age_days=9)
        self.commit_files({**store(A='done'), 'tasks/evidence/A.toml':
                           f'schema = 1\ntask = "A"\ncandidate = "{unrelated}"\nintegration = "{delivered}"\n'},
                          age_days=8)
        # Same-file edits and a revert of the candidate (not integration) count nothing.
        self.commit_files({'a.py': 'edited\n'}, age_days=6,
                          message=f'Revert unrelated\n\nThis reverts commit {unrelated}.')
        self.assertEqual(scorecard.measure(self.repo, 7, now=self.now)['regressions'], [])
        reverted = self.commit_files({'a.py': 'fixed\n'}, age_days=5,
                                    message=f'Revert delivery\n\nThis reverts commit {delivered}.')
        rows = scorecard.measure(self.repo, 7, now=self.now)['regressions']
        self.assertEqual([(r['task'], r['delivered_commit'], r['discovery_commit'],
                           r['time_to_discovery_seconds'], r['severity'], r['found_by'], r['found_by_owner'])
                          for r in rows], [('A', delivered, reverted, 5 * DAY, None, None, None)])

    def test_regression_notes_keep_first_discovery_and_report_malformed_links(self):
        self.commit_files(store(A='open', FIX='open', CHECK='open', BAD='open'), age_days=12)
        delivered = self.commit_files({'a.py': 'broken\n'}, age_days=10)
        self.commit_files({**store(A='done', FIX='open', CHECK='open', BAD='open'), 'tasks/evidence/A.toml':
                           f'schema = 1\ntask = "A"\nintegration = "{delivered}"\n'}, age_days=9)
        note = f'- Regression of: A; commit {delivered}; severity high; found by owner\n'
        noted = self.commit_files({'tasks/items/FIX.md': record('FIX', 'open') + note,
                                   'tasks/items/CHECK.md': record('CHECK', 'open') +
                                   note.replace('high', 'low').replace('owner', 'check')}, age_days=4)
        self.commit_files({'tasks/items/FIX.md': record('FIX', 'done') + note.replace('high', 'medium'),
                           'tasks/items/BAD.md': record('BAD', 'open') +
                           f'- Regression of: UNKNOWN; commit {delivered}; severity low; found by check\n' +
                           f'- Regression of: A; commit {"0" * 40}; severity low; found by check\n' +
                           '- Regression of: A; malformed\n'}, age_days=1)
        row = scorecard.measure(self.repo, 7, now=self.now)
        self.assertEqual([(r['task'], r['delivered_commit'], r['discovery_commit'],
                           r['time_to_discovery_seconds'], r['severity'], r['found_by'], r['found_by_owner'], r['source_task'])
                          for r in row['regressions']],
                         [('A', delivered, noted, 6 * DAY, 'low', 'check', False, 'CHECK'),
                          ('A', delivered, noted, 6 * DAY, 'high', 'owner', True, 'FIX')])
        self.assertEqual([(r['task'], r['note']) for r in row['regressions_incomplete']],
                         [('BAD', '- Regression of: A; malformed')])
        # A note before a smaller window is not rediscovered by a severity edit.
        self.assertEqual(scorecard.measure(self.repo, 2, now=self.now)['regressions'], [])

    def test_a_revert_with_a_note_counts_once_with_explicit_metadata(self):
        self.commit_files(store(A='open', FIX='open'), age_days=12)
        delivered = self.commit_files({'a.py': 'broken\n'}, age_days=10)
        self.commit_files({**store(A='done', FIX='open'), 'tasks/evidence/A.toml':
                           f'schema = 1\ntask = "A"\nintegration = "{delivered}"\n'}, age_days=9)
        self.commit_files({'a.py': 'fixed\n', 'tasks/items/FIX.md': record('FIX', 'open') +
                           f'- Regression of: A; commit {delivered}; severity medium; found by check\n'},
                          age_days=1, message=f'Revert delivery\n\nThis reverts commit {delivered}.')
        rows = scorecard.measure(self.repo, 7, now=self.now)['regressions']
        self.assertEqual([(r['task'], r['severity'], r['found_by'], r['time_to_discovery_seconds'])
                          for r in rows], [('A', 'medium', 'check', 9 * DAY)])

    def test_git_diff_display_configuration_does_not_hide_regression_notes(self):
        self.commit_files(store(A='open', FIX='open'), age_days=12)
        delivered = self.commit_files({'a.py': 'broken\n'}, age_days=10)
        self.commit_files({**store(A='done', FIX='open'), 'tasks/evidence/A.toml':
                           f'schema = 1\ntask = "A"\nintegration = "{delivered}"\n'}, age_days=9)
        self.commit_files({'tasks/items/FIX.md': record('FIX', 'open') +
                           f'- Regression of: A; commit {delivered}; severity low; found by check\n'}, age_days=1)
        subprocess.run(['git', '-C', str(self.repo), 'config', 'diff.noprefix', 'true'], check=True)
        subprocess.run(['git', '-C', str(self.repo), 'config', 'color.ui', 'always'], check=True)
        rows = scorecard.measure(self.repo, 7, now=self.now)['regressions']
        self.assertEqual([(r['task'], r['source_task']) for r in rows], [('A', 'FIX')])

    def evaluation_fixture(self):
        """Two verified deliveries, one with two retries; one manual closure."""
        self.commit_files(store(A='open', B='open', MANUAL='open'), age_days=31)
        from task_store import TaskStore
        snapshot = TaskStore.at(self.repo, 'HEAD')
        facts, runs, attention = [], [], []
        for task, age, hours, costs in (('A', 28, 1, [1, 2, 3]), ('B', 1, 3, [2])):
            base = subprocess.check_output(['git', '-C', str(self.repo), 'rev-parse', 'HEAD'], text=True).strip()
            candidate = self.commit_files({f'{task}.txt': 'work'}, age_days=age)
            tree = subprocess.check_output(['git', '-C', str(self.repo), 'rev-parse', 'HEAD^{tree}'], text=True).strip()
            env = dict(os.environ, GIT_AUTHOR_DATE=f'@{int(self.now - age * DAY)} +0000',
                       GIT_COMMITTER_DATE=f'@{int(self.now - age * DAY)} +0000')
            git = ['git', '-C', str(self.repo), '-c', 'user.name=t', '-c', 'user.email=t@example.invalid']
            integration = subprocess.check_output([*git, 'commit-tree', tree, '-p', base,
                                                   '-p', candidate, '-m', 'integrate'], env=env, text=True).strip()
            subprocess.run([*git, 'update-ref', 'HEAD', integration, candidate], check=True)
            self.commit_files({f'tasks/items/{task}.md': record(task, 'done').replace(
                'status = "done"', 'status = "done"\nclosure = "coordinator_verified"\n'
                f'closure_evidence = "tasks/evidence/{task}.toml"'), f'tasks/evidence/{task}.toml':
                f'schema = 1\ntask = "{task}"\ncontract_hash = "{snapshot.tasks[task].contract_hash}"\n'
                f'candidate = "{candidate}"\nintegration = "{integration}"\ntree = "{tree}"\n'
                'result = "pass"\nreview = "passed"\n'}, age_days=age)
            end = self.now - age * DAY
            for kind, stamp in [('accepted', end - hours * 7200), ('dispatched', end - hours * 3600),
                                ('integrated', end), ('closed', end), ('delivered', end)]:
                facts.append(dict(event_id=f'{task}-{kind}', task_id=task, attempt_id='a1', event=kind, timestamp=stamp))
            for i, cost in enumerate(costs):
                runs.append(dict(run_id=f'{task}-{i}', task=task, attempt_id=f'a{i}', role='worker',
                                 time=end - 60, cost_usd=cost, cost_source='provider_reported'))
            attention.append(dict(event_id=task, task=task, time=end - 60, minutes=0 if task == 'A' else 8))
        # A recovery episode is not an owner intervention. An unanswered restart is not success.
        for identity, task, kind, age in [('restart-1', 'A', 'restart', 28.03), ('adopt', 'A', 'worker_adopted', 28.02),
                                         ('restart-2', 'B', 'restart', 1.03), ('answer', 'B', 'blocker_answered', 1.1)]:
            facts.append(dict(event_id=identity, task_id=task, attempt_id='a1', event=kind, timestamp=self.now - age * DAY))
        self.commit_files({'tasks/items/MANUAL.md': record('MANUAL', 'done').replace(
            'status = "done"', 'status = "done"\nclosure = "manual"\nclosure_actor = "owner"\n'
            'closure_timestamp = "2026-10-21T00:00:00+00:00"\nclosure_reason = "hand closed"')}, age_days=1)
        self.commit_files({'tasks/items/MANUAL.md': (self.repo / 'tasks/items/MANUAL.md').read_text() +
                          f'- Regression of: A; commit {self.integration_for("A")}; severity low; found by check\n'},
                          age_days=0.5)
        journal = self.repo / '.git/autowork-execution/journal.jsonl'
        journal.parent.mkdir(parents=True, exist_ok=True)
        journal.write_text(json.dumps(dict(event='task_lifecycle', timestamp=self.now, lifecycle=[*facts, facts[0]])) + '\n')
        state = accounting.state_dir(self.repo)
        state.mkdir(parents=True)
        (state / 'runs.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in [*runs, runs[0]]))
        (state / 'attention.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in attention))

    def integration_for(self, task):
        import tomllib
        return tomllib.loads((self.repo / f'tasks/evidence/{task}.toml').read_text())['integration']

    def scorecard_command(self, *args):
        output = io.StringIO()
        with mock.patch.object(command, 'resolve', return_value=(str(self.repo), 'fixture')), \
                mock.patch.object(scorecard.time, 'time', return_value=self.now), contextlib.redirect_stdout(output):
            self.assertEqual(command.main(['scorecard', '--days', '30', *args, str(self.repo)]), 0)
        return output.getvalue()

    def test_evaluation_exports_share_labelled_weekly_metrics_and_pool_observations(self):
        self.evaluation_fixture()
        report = json.loads(self.scorecard_command('--json'))
        evaluation = report['runners']['fixture']['evaluation']
        expected = {'verified_tasks': 2, 'manual_closed': 1, 'owner_interventions': 2,
                    'verified_tasks_per_day': 2 / 30, 'unattended_completion_percentage': 50,
                    'accepted_to_delivered_median_minutes': 240, 'accepted_to_delivered_p95_minutes': 360,
                    'dispatch_to_integrated_median_minutes': 120, 'dispatch_to_integrated_p95_minutes': 180,
                    'cost_per_verified_task_usd': 4, 'owner_minutes_per_verified_task': 4,
                    'recovery_success_rate': 0.5, 'regression_rate': 0.5}
        self.assertEqual({k: v['value'] for k, v in evaluation['summary'].items()}, expected)
        self.assertTrue(all(m['status'] == 'measured' for m in evaluation['summary'].values()))
        self.assertEqual([w['metrics']['verified_tasks']['value'] for w in evaluation['weeks']], [1, 0, 0, 0, 1])
        self.assertEqual(evaluation['change']['cost_per_verified_task_usd']['value'], -4)
        self.assertEqual(evaluation['baseline']['description'], 'no baseline')
        self.assertEqual(report['overall'], evaluation)
        # The CSV is a lossless metric projection of JSON, including missing values and changes.
        exported = list(csv.DictReader(io.StringIO(self.scorecard_command('--csv'))))
        for scope, runner, card in [('runner', 'fixture', evaluation), ('overall', '', report['overall'])]:
            periods = [('summary', card['summary']), ('change', card['change']),
                       ('baseline', card['baseline']['metrics']), ('baseline_change', card['baseline_change'])]
            periods += [(f'week-{w["week"]}', w['metrics']) for w in card['weeks']]
            self.assertIn('phase_diagnostics', card)
            periods += [(f'phase_diagnostics.{name}', row['metrics'])
                        for name, row in card['phase_diagnostics'].items()]
            for period, metrics in periods:
                for name, metric in metrics.items():
                    matches = [r for r in exported if (r['scope'], r['runner'], r['period'], r['metric']) ==
                               (scope, runner, period, name)]
                    self.assertEqual(len(matches), 1)
                    row = matches[0]
                    self.assertEqual((row['status'], row['unit']), (metric['status'], metric['unit']))
                    self.assertEqual(float(row['value']) if row['value'] else None, metric['value'])
                    if period.startswith('phase_diagnostics.'):
                        phase = card['phase_diagnostics'][period.split('.', 1)[1]]
                        for label in ('cohort', 'identity', 'rules'):
                            self.assertEqual(row[label], phase[label])
        text = self.scorecard_command()
        for name, phase in evaluation['phase_diagnostics'].items():
            self.assertIn(f'phase_diagnostics.{name}', text)
            for label in ('cohort', 'identity', 'rules'):
                self.assertIn(phase[label], text)
            for key, value in phase['metrics'].items():
                rendered = (f'{key}={value["value"]:g} {value["unit"]} [{value["status"]}]'
                            if value['value'] is not None else f'{key}=missing [missing]')
                self.assertIn(rendered, text)
        self.assertIn('no baseline', text)
        self.assertIn('week-5', text)
        # A Git close exactly at the inclusive start belongs to the window.
        boundary = scorecard.report([(self.repo, 'fixture')], 28, now=int(self.now))
        self.assertEqual(boundary['overall']['summary']['verified_tasks']['value'], 2)

    def test_phase_diagnostics_keep_attempt_identity_and_coverage(self):
        self.evaluation_fixture()
        start = self.now - 30 * DAY
        # Minutes from window start; A's starts predate the window. Slot states
        # supply running/reported/integrating, which lifecycle facts do not collect.
        rows = [
            ('A', 'a1', [('accepted', -1440), ('dispatched', -720), ('running', -600),
                         ('reported', -540), ('integrating', -570), ('integrating', -510)]),
            ('A', 'a2', [('dispatched', 60), ('running', 120), ('reported', 180),
                         ('integrating', 240), ('integrated', 300), ('closed', 2880)]),
            ('A', 'a3', [('reported', 360)]),
            ('B', 'b1', [('running', 41600), ('reported', 41660), ('integrating', 41680),
                         ('integrated', 41700), ('dispatched', 41760), ('closed', 41760),
                         ('integrated', 41800)]),  # later end cannot repair reversal
            ('OPEN', 'o1', [('running', 400), ('reported', 460)]),
            ('OPEN', 'o2', [('running', 500), ('held', 510)]),  # later attempt => terminal
            ('OPEN', 'o3', [('running', 600), ('interrupted', 610)]),
            ('HELD', None, [('closed', -10)]),  # old close cannot terminate later work
            ('HELD', 'h', [('running', 700), ('held', 710)]),  # hold alone is not terminal
            ('HELD', 'future', [('running', 43201)]),  # cannot terminate h at cutoff
            ('NO-START', 'u', [('reported', 800), ('closed', 810)]),
            ('REVERSED', 'r', [('running', 900), ('reported', 850), ('reported', 950)]),
            ('FUTURE', 'f', [('running', 1000), ('reported', 43201)]),
            ('BOUNDARY', 'z', [('running', 43200), ('reported', 43200)]),
            ('BOUNDARY', 'start', [('running', 0), ('reported', 0)]),
            ('MANUAL', 'm', [('running', 1100), ('reported', 1220)]),
            ('LEGACY', None, [('running', 1300), ('reported', 1360)]),
        ]
        envelopes = []
        for task, attempt, endpoints in rows:
            for kind, minute in endpoints:
                stamp = start + minute * 60
                fact = dict(event_id=f'{task}-{attempt}-{kind}-{minute}', task_id=task,
                            attempt_id=attempt, event=kind, timestamp=stamp,
                            scope='task' if kind in ('accepted', 'closed') else 'attempt')
                if kind in ('running', 'reported', 'integrating', 'held'):
                    envelopes.append(dict(event='slot_changed', timestamp=stamp, task_id=task,
                                          state=kind, slot=dict(attempt_id=attempt)))
                else:
                    envelopes.append(dict(event='task_lifecycle', timestamp=stamp, lifecycle=[fact, fact]))
        journal = self.repo / '.git/autowork-execution/journal.jsonl'
        journal.write_text(''.join(json.dumps(e) + '\n' for e in reversed(envelopes + envelopes)))
        result = scorecard.report([(self.repo, 'fixture')], 30, now=self.now)
        self.assertIn('phase_diagnostics', result['overall'])
        phases = result['overall']['phase_diagnostics']
        # eligible, observed, missing start, terminal missing end, censored, reversed, median, p95
        expected = {
            'task_accepted_to_dispatched': (2, 1, 1, 0, 0, 0, 720, 720),
            'task_dispatched_to_integrated': (2, 1, 0, 0, 0, 1, 1020, 1020),
            'attempt_running_to_reported': (4, 3, 1, 0, 0, 0, 60, 60),
            'attempt_reported_to_integrating': (4, 2, 0, 1, 0, 1, 40, 60),
            'attempt_integrating_to_integrated': (4, 2, 1, 1, 0, 0, 40, 60),
            'attempt_integrated_to_closed': (4, 2, 2, 0, 0, 0, 1320, 2580),
            'all_attempt_exposure': (11, 6, 2, 1, 3, 1, 60, 120),
        }
        fields = ('eligible', 'observed_pairs', 'missing_start', 'missing_end_terminal',
                  'right_censored', 'reversed', 'median_minutes', 'p95_minutes')
        for name, want in expected.items():
            with self.subTest(phase=name):
                row = phases[name]
                self.assertEqual(tuple(row['metrics'][k]['value'] for k in fields), want)
                self.assertEqual(row['identity'], 'task_id' if name.startswith('task_') else 'task_id+attempt_id')
                for rule in ('first timestamp', 'missing start first', 'later attempt', 'closed state', 'held', 'cutoff'):
                    self.assertIn(rule, row['rules'])
                if name != 'all_attempt_exposure':
                    self.assertIn('latest receipt-valid verified close', row['cohort'])
                    self.assertIn('starts may predate window', row['cohort'])
        exposure = phases['all_attempt_exposure']
        self.assertIn('across all outcomes', exposure['cohort'])
        self.assertIn('missing_start and left_excluded are outside eligible', exposure['rules'])
        self.assertEqual(exposure['metrics']['left_excluded']['value'], 1)
        self.assertEqual(exposure['metrics']['observed_completed_attempt_span_hours']['value'], 5)
        self.assertEqual(result['runners']['fixture']['usage']['delivered_tasks'], 0)
        # A's older close is outside a shorter completion window, but B still qualifies.
        narrow = scorecard.report([(self.repo, 'fixture')], 7, now=self.now)['overall']['phase_diagnostics']
        self.assertEqual(narrow['task_accepted_to_dispatched']['metrics']['eligible']['value'], 1)
        for field in ('median_minutes', 'p95_minutes'):
            self.assertEqual(narrow['task_accepted_to_dispatched']['metrics'][field]['status'], 'missing')
        self.assertEqual(narrow['attempt_running_to_reported']['metrics']['eligible']['value'], 1)
        # Git verifies A's close, but retained telemetry has no dispatch/close.
        # Later attempts still prove its missing dispatch is terminal, not censored.
        without_ends = [e for e in envelopes if not any(
            f['task_id'] == 'A' and f['event'] in ('dispatched', 'closed') for f in e.get('lifecycle', []))]
        journal.write_text(''.join(json.dumps(e) + '\n' for e in without_ends))
        phase = scorecard.report([(self.repo, 'fixture')], 30, now=self.now)['overall'][
            'phase_diagnostics']['task_accepted_to_dispatched']['metrics']
        self.assertEqual((phase['missing_end_terminal']['value'], phase['right_censored']['value']), (1, 0))

    def test_missing_delivery_and_uptime_stay_unknown(self):
        self.evaluation_fixture()
        journal = self.repo / '.git/autowork-execution/journal.jsonl'
        envelope = json.loads(journal.read_text())
        envelope['lifecycle'] = [f for f in envelope['lifecycle'] if f['event'] != 'delivered']
        journal.write_text(json.dumps(envelope) + '\n')
        with journal.open('a') as stream:
            for kind, age in [('running', 180), ('reported', 60)]:
                stream.write(json.dumps(dict(event='slot_changed', timestamp=self.now - age * 60,
                                            task_id='B', state=kind, slot=dict(attempt_id='a1'))) + '\n')
        result = scorecard.report([(self.repo, 'fixture')], 30, now=self.now)
        usage = result['runners']['fixture']['usage']
        self.assertEqual(usage['delivered_tasks'], 0)
        self.assertIsNone(usage['cost_per_delivered_task_usd'])
        card = result['overall']
        self.assertIsNone(card['summary']['accepted_to_delivered_median_minutes']['value'])
        self.assertIsNone(card['summary']['accepted_to_delivered_p95_minutes']['value'])
        self.assertIn('phase_diagnostics', card)
        exposure = card['phase_diagnostics']['all_attempt_exposure']['metrics']
        self.assertEqual(exposure['observed_completed_attempt_span_hours']['value'], 2)
        # There is no availability collector: exposure must not create a throughput
        # or uptime summary metric. Existing dispatch timing remains unchanged.
        self.assertFalse(any('runner_hour' in k or 'uptime' in k for k in card['summary']))
        self.assertEqual(card['summary']['dispatch_to_integrated_median_minutes']['value'], 120)

    def test_empty_evaluation_rates_are_missing_and_manual_closure_is_an_intervention(self):
        self.commit_files(store(A='open'), age_days=31)
        self.commit_files(store(A='done'), age_days=2)  # legacy hand close, no telemetry
        card = json.loads(self.scorecard_command('--json'))['overall']
        self.assertEqual((card['summary']['verified_tasks']['value'], card['summary']['manual_closed']['value'],
                          card['summary']['owner_interventions']['value']), (0, 1, 1))
        for name in ('verified_tasks_per_day', 'unattended_completion_percentage', 'regression_rate',
                     'recovery_success_rate', 'cost_per_verified_task_usd', 'owner_minutes_per_verified_task'):
            self.assertEqual((card['summary'][name]['value'], card['summary'][name]['status']), (None, 'missing'))

    def test_overall_pools_tasks_cost_and_duration_samples_not_runner_averages(self):
        self.evaluation_fixture()
        other = self.repo / 'second'
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(other)], check=True)
        with mock.patch.object(self, 'repo', other):
            self.evaluation_fixture()
            self.commit_files({'tasks/items/B.md': record('B', 'open')}, age_days=0.25)
        report = scorecard.report([(self.repo, 'first'), (other, 'second'), (self.repo, 'alias')], 30, now=self.now)
        self.assertEqual(len(report['runners']), 2)  # aliases cannot double-count the same runner
        metrics = report['overall']['summary']
        self.assertEqual(metrics['verified_tasks']['value'], 3)
        self.assertEqual(metrics['dispatch_to_integrated_median_minutes']['value'], 60)
        self.assertEqual(metrics['cost_per_verified_task_usd']['value'], 16 / 3)
        self.assertEqual(metrics['unattended_completion_percentage']['value'], 200 / 3)
        self.assertEqual(metrics['regression_rate']['value'], 2 / 3)
        phase = report['overall']['phase_diagnostics']['task_dispatched_to_integrated']['metrics']
        self.assertEqual((phase['eligible']['value'], phase['median_minutes']['value'], phase['p95_minutes']['value']),
                         (3, 60, 180))

    def test_reopened_task_reclosed_in_window_is_counted_once_in_its_latest_week(self):
        self.evaluation_fixture()
        verified = (self.repo / 'tasks/items/A.md').read_text()
        self.commit_files({'tasks/items/A.md': record('A', 'open')}, age_days=0.4)
        self.commit_files({'tasks/items/A.md': verified}, age_days=0.2)
        report = scorecard.report([(self.repo, 'fixture')], 7, now=self.now)
        self.assertEqual(report['runners']['fixture']['verified_closed'], 2)
        self.assertEqual(report['overall']['summary']['verified_tasks']['value'], 2)
        report = scorecard.report([(self.repo, 'fixture')], 30, now=self.now)
        self.assertEqual(report['overall']['summary']['verified_tasks']['value'], 2)
        self.assertEqual([w['metrics']['verified_tasks']['value'] for w in report['overall']['weeks']], [0, 0, 0, 0, 2])

    def test_recorded_owner_time_cannot_be_called_unattended(self):
        self.evaluation_fixture()
        path = accounting.state_dir(self.repo) / 'attention.jsonl'
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows[0]['minutes'] = 5
        path.write_text(''.join(json.dumps(r) + '\n' for r in rows))
        metrics = scorecard.report([(self.repo, 'fixture')], 30, now=self.now)['overall']['summary']
        self.assertEqual(metrics['unattended_completion_percentage']['value'], 0)

    def test_baseline_is_an_estimate_beside_measured_cost_and_owner_minutes(self):
        self.evaluation_fixture()
        baseline = self.repo / 'baseline.json'
        baseline.write_text(json.dumps({'cost_per_verified_task_usd': 10, 'owner_minutes_per_verified_task': 20}))
        card = json.loads(self.scorecard_command('--json', '--baseline', str(baseline)))['overall']
        self.assertEqual((card['summary']['cost_per_verified_task_usd']['value'],
                          card['summary']['owner_minutes_per_verified_task']['value']), (4, 4))
        self.assertEqual({k: (m['value'], m['status']) for k, m in card['baseline']['metrics'].items()},
                         {'cost_per_verified_task_usd': (10, 'estimate'),
                          'owner_minutes_per_verified_task': (20, 'estimate')})
        self.assertEqual({k: (m['value'], m['status']) for k, m in card['baseline_change'].items()},
                         {'cost_per_verified_task_usd': (-6, 'estimate'),
                          'owner_minutes_per_verified_task': (-16, 'estimate')})
        baseline.write_text('{"cost_per_verified_task_usd": -1}')
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(command.main(['scorecard', '--baseline', str(baseline), str(self.repo)]), 1)
        for days in ('0', '31'):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                command.main(['scorecard', '--days', days])

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
