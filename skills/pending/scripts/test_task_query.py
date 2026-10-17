"""Behavioral query fixtures; no host, network, ledger mutation or worker inference."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import task_query


def task(tid, title='Outcome', status='open', extra=''):
    mark = 'x' if status == 'done' else ' '
    return f'- [{mark}] {tid} — {title}\n  Status: {status}\n{extra}\n'


class QueryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        self.todo = self.repo / 'TODO.md'
        self.todo.write_text('# TODO\n## Now\n')

    def query(self, mode='pending', **kw):
        return task_query.query(self.repo, mode=mode, **kw)

    def ledger(self, ids, *, focus=None, order=None):
        data = {'version': 1, 'goals': [], 'tasks': []}
        for gid in ('G', 'F'):
            members = [tid for tid, goal, status, section, deps in ids if goal == gid]
            if members:
                data['goals'].append({'id': gid, 'title': gid, 'source': 'SPEC.md',
                                      'status': 'partial', 'tasks': members, 'evidence': []})
        data['tasks'] = [dict(id=tid, title=tid, goal=goal, status=status,
                              section=section, depends_on=deps)
                         for tid, goal, status, section, deps in ids]
        data['priority_order'] = {'schema': 1, 'tasks': order or [r[0] for r in ids if r[2] != 'done']}
        if focus:
            data['primary_milestone'] = focus
        (self.repo / 'goals.json').write_text(json.dumps(data))

    def git(self, *args, date=None):
        env = dict(os.environ, GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1',
                   GIT_AUTHOR_NAME='Fixture', GIT_COMMITTER_NAME='Fixture',
                   GIT_AUTHOR_EMAIL='fixture@example.invalid', GIT_COMMITTER_EMAIL='fixture@example.invalid')
        if date:
            env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        result = subprocess.run(['git', '-C', str(self.repo), *args], env=env,
                                text=True, capture_output=True, check=True)
        return result.stdout.strip()

    def commit(self, date):
        self.git('add', '.')
        return self.git('commit', '-qm', 'fixture', date=date)

    def test_pending_retains_blocked_order_and_explains_focus_and_drift(self):
        self.todo.write_text('# TODO\n## Now\n' + task('T1', extra='  Dependencies: T9\n') +
                             task('T2') + task('T3') + task('T4') + task('T5') +
                             '## Next\n' + task('T6') + '## Needs decision\n' + task('T9'))
        ids = [(f'T{i}', 'F' if i == 6 else 'G', 'open',
                'Next' if i == 6 else 'Needs decision' if i == 9 else 'Now',
                ['T9'] if i == 1 else []) for i in (1, 2, 3, 4, 5, 6, 9)]
        self.ledger(ids, focus='F')
        result = self.query()
        self.assertEqual([r['id'] for r in result['records']], ['T1', 'T2', 'T3', 'T4', 'T5'])
        self.assertEqual((result['total'], result['remaining'], result['counts']), (7, 2, {'open': 7}))
        self.assertTrue(result['records'][0]['blocked'])
        self.assertEqual(result['selection']['next_eligible'], 'T6')
        self.assertEqual(result['selection']['focus'], 'F')
        self.assertTrue(result['selection']['notes'])
        self.todo.write_text(self.todo.read_text().replace(task('T6'), task('T6', extra='  Blocker: owner decision\n')))
        blocked = self.query()['selection']
        self.assertEqual(blocked['next_eligible'], 'T2')
        self.assertEqual(blocked['excluded'], ['T6'])
        self.todo.write_text(self.todo.read_text().replace(task('T2') + task('T3'), task('T3') + task('T2')))
        drift = self.query()
        self.assertEqual(drift['selection']['priority']['state'], 'drift')
        self.assertIsNone(drift['selection']['next_eligible'])

    def test_lookup_ranks_exact_short_ids_and_ambiguous_descriptions(self):
        self.todo.write_text('# TODO\n## Now\n' + task('APP-101-aa', 'Login UI') +
                             task('APP-102-bb', 'Login API') + task('APP-103-cc', 'Other', extra='  Scope: login\n'))
        self.assertEqual(self.query('detail', text='APP-102-bb')['records'][0]['id'], 'APP-102-bb')
        self.assertEqual(self.query('detail', text='101')['records'][0]['id'], 'APP-101-aa')
        self.assertEqual(self.query('history', text='APP-101')['records'][0]['id'], 'APP-101-aa')
        matches = self.query('search', text='login')
        self.assertTrue(matches['ambiguous'])
        self.assertEqual([r['id'] for r in matches['records']], ['APP-101-aa', 'APP-102-bb', 'APP-103-cc'])
        self.assertEqual(self.query('pending', text='login')['total'], 3)
        for filters in ({'limit': 0}, {'git_limit': 0}, {'timezone': 'not/a-zone'},
                        {'since': '2026-11-01', 'until': '2026-10-01'},
                        {'since': '2026-11-01T01:30:00', 'timezone': 'America/New_York'}):
            with self.subTest(filters=filters), self.assertRaises((ValueError, KeyError)):
                self.query('history', **filters)

    def test_archive_formats_reopen_and_supersession_are_distinct(self):
        for name in ('TODO.archive.md', 'todo.archive.md', 'docs/TODO-archive.md'):
            with self.subTest(name=name):
                archive = self.repo / name
                archive.parent.mkdir(exist_ok=True)
                archive.write_text('# History\n' + task('T1', 'Login', 'done') +
                                   '### T2 — Legacy outcome\n- Status: done (local only)\n\n' +
                                   task('T3', 'Reopened', 'done') +
                                   'Disposition: Superseded; not completed\nSuccessors: T1\n\n' + task('T4') +
                                   task('T5', status='done') + task('T5', status='done'))
                self.todo.write_text('# TODO\n## Now\n' + task('T3', 'Reopened'))
                result = self.query('history')
                self.assertEqual([r['id'] for r in result['records']], ['T1', 'T2'])
                self.assertEqual(result['recency'], 'unknown')
                self.assertEqual([r['id'] for r in self.query()['records']], ['T3'])
                self.assertTrue(self.query('detail', text='T3')['records'][0]['reopened'])
                self.assertEqual(self.query('detail', text='T4')['records'][0]['state'], 'superseded')
                archive.unlink()

    def test_latest_dates_timezone_bounds_ties_and_undated_are_not_recency_proxies(self):
        self.todo.write_text('# TODO\n## Done\n' +
                             task('T9', 'Older', 'done', '  Completed: 2026-10-15\n') +
                             task('T2', 'Tie', 'done', '  Completed: 2026-10-16T01:00:00+00:00\n') +
                             task('T1', 'Tie', 'done', '  Completed: 2026-10-16T01:00:00+00:00\n') +
                             task('T0', 'Unknown', 'done') +
                             task('T6', 'Newest receipt', 'done', '  Completion receipt: 2026-10-20\n') +
                             task('T5', 'Newer', 'done', '  Completed: 2026-10-19\n') +
                             task('T4', 'Newer', 'done', '  Completed: 2026-10-18\n'))
        result = self.query('history', timezone='America/New_York')
        self.assertEqual([r['id'] for r in result['records']], ['T6', 'T5', 'T4', 'T1', 'T2'])
        self.assertEqual((result['total'], result['remaining']), (6, 1))
        self.assertEqual(len(self.query('history', limit='all')['records']), 6)
        self.assertEqual([r['id'] for r in result['undated']], ['T0'])
        self.assertEqual(result['records'][0]['date']['kind'], 'explicit')
        bounded = self.query('history', timezone='America/New_York', since='2026-10-15', until='2026-10-16')
        self.assertEqual(bounded['total'], 3)
        self.assertEqual(bounded['interval']['until'], '2026-10-16T00:00:00-04:00')
        self.assertEqual(self.query('history', timezone='UTC', since='2026-10-16', until='2026-10-17')['total'], 2)
        completions = [('T1', '2026-11-01T01:30:00-04:00'),
                       ('T2', '2026-11-01T01:45:00-04:00'),
                       ('T3', '2026-11-01T01:00:00-05:00'),
                       ('T4', '2026-11-01T01:15:00-05:00'),
                       ('T5', '2026-11-01T01:29:59-04:00')]
        self.todo.write_text('# TODO\n## Done\n' + ''.join(
            task(tid, status='done', extra=f'  Completed: {at}\n') for tid, at in completions))
        since, until = '2026-11-01T01:30:00-04:00', '2026-11-01T01:15:00-05:00'
        folded = self.query('history', timezone='America/New_York', since=since, until=until)
        self.assertEqual([r['id'] for r in folded['records']], ['T3', 'T2', 'T1'])
        self.assertEqual(folded['interval'], {'since': since, 'until': until})
        self.assertEqual(folded['records'][0]['date']['value'], '2026-11-01T01:00:00-05:00')
        self.assertEqual([r['id'] for r in self.query('history', timezone='America/New_York')['records']],
                         ['T4', 'T3', 'T2', 'T1', 'T5'])
        for lower, upper in ((until, since), (since, since)):
            with self.subTest(since=lower, until=upper), self.assertRaises(ValueError):
                self.query('history', timezone='America/New_York', since=lower, until=upper)

    def test_git_fallback_requires_transition_not_import_and_discloses_bounds(self):
        self.assertTrue(self.query('history')['partial'])
        self.git('init', '-q')
        self.todo.write_text('# TODO\n## Now\n' + task('T1') + task('T3'))
        self.commit('2026-10-10T12:00:00+00:00')
        self.todo.write_text('# TODO\n## Done\n' + task('T1', status='done') +
                             task('T3', status='done', extra='  Completed: 2026-10-09\n'))
        self.commit('2026-10-11T12:00:00+00:00')
        completion = self.git('rev-parse', 'HEAD')
        archive = self.repo / 'TODO.archive.md'
        archive.write_text('# History\n' + task('T1', status='done') + task('T2', status='done'))
        self.todo.write_text('# TODO\n[History](TODO.archive.md)\n## Done\n' +
                             task('T3', status='done', extra='  Completed: 2026-10-09\n'))
        self.commit('2026-10-12T12:00:00+00:00')
        result = self.query('history')
        self.assertEqual([r['id'] for r in result['records']], ['T1', 'T3'])
        self.assertEqual(result['records'][0]['date']['commit'], completion)
        self.assertEqual(result['records'][0]['date']['kind'], 'git_recorded')
        self.assertEqual([r['id'] for r in result['undated']], ['T2'])
        bounded = self.query('history', git_limit=1)
        self.assertTrue(bounded['partial'])
        self.assertEqual([r['id'] for r in bounded['records']], ['T3'])
        self.assertEqual({r['id'] for r in bounded['undated']}, {'T1', 'T2'})
        archive.write_text('# History\n' + task('T2', status='done'))
        self.todo.write_text('# TODO\n## Now\n' + task('T1') + '## Done\n' +
                             task('T3', status='done', extra='  Completed: 2026-10-09\n'))
        self.commit('2026-10-13T12:00:00+00:00')
        reopened = self.query('detail', text='T1')['records'][0]
        self.assertTrue(reopened['reopened'])
        self.assertEqual(reopened['events'][0]['commit'], completion)
        self.assertIsNone(reopened['date'])
        self.assertNotIn('T1', [r['id'] for r in self.query('history')['records']])
        reopened_text = self.todo.read_text()
        self.todo.write_text(reopened_text.replace(task('T1'), task('T1', status='done')))
        cycle = self.query('history', text='T1', timezone='UTC', since='2026-10-11', until='2026-10-12')
        self.assertEqual(cycle['total'], 0)
        self.assertIsNone(cycle['undated'][0]['date'])
        self.assertEqual(cycle['undated'][0]['events'][0]['commit'], completion)
        self.assertTrue(cycle['partial'])
        self.todo.write_text(reopened_text)
        (self.repo / '.git/shallow').write_text(self.git('rev-parse', 'HEAD') + '\n')
        self.assertTrue(self.query('history')['partial'])
        (self.repo / '.git/shallow').unlink()
        self.todo.write_text(self.todo.read_text() + task('T4'))
        (self.repo / 'goals.json').write_text('')
        self.commit('2026-10-14T12:00:00+00:00')
        self.todo.write_text(self.todo.read_text().replace(task('T4'), task('T4', status='done')))
        (self.repo / 'goals.json').unlink()
        self.commit('2026-10-15T12:00:00+00:00')
        malformed = self.query('history', text='T4')
        self.assertIsNone(malformed['records'][0]['date'])
        self.assertTrue(any(w['code'] == 'historical_sources' for w in malformed['warnings']))

    def test_conflicting_malformed_duplicate_and_unsafe_sources_never_confirm(self):
        cases = ('ledger', 'malformed', 'duplicate', 'status', 'unsafe', 'empty', 'encoding', 'symlink', 'fields', 'bad_box', 'nested', 'archive_open', 'archive_superseded', 'ledger_archive_superseded', 'encoded_archive')
        for case in cases:
            with self.subTest(case=case):
                (self.repo / 'goals.json').unlink(missing_ok=True)
                (self.repo / 'TODO.archive.md').unlink(missing_ok=True)
                self.todo.write_text('# TODO\n## Done\n' + task('T1', status='done', extra='  Completed: 2026-10-15\n'))
                if case == 'ledger':
                    self.ledger([('T1', 'G', 'open', 'Now', [])])
                elif case == 'malformed':
                    (self.repo / 'goals.json').write_text('{broken')
                elif case == 'duplicate':
                    self.todo.write_text(self.todo.read_text() + task('T1', status='done'))
                elif case == 'status':
                    self.todo.write_text(self.todo.read_text() + '  Status: open\n')
                elif case == 'unsafe':
                    self.todo.write_text('[History](../private.md)\n' + self.todo.read_text())
                elif case == 'encoded_archive':
                    self.todo.write_text('[History](TODO%2Earchive.md)\n' + self.todo.read_text())
                elif case == 'empty':
                    (self.repo / 'goals.json').write_bytes(b'')
                elif case == 'encoding':
                    (self.repo / 'goals.json').write_bytes(b'\xff')
                elif case == 'fields':
                    self.todo.write_text(self.todo.read_text() + '  Goal: G\n  Goal: F\n')
                elif case == 'bad_box':
                    self.todo.write_text(self.todo.read_text() + '- [closed] T2 — Broken entry\n')
                elif case == 'nested':
                    self.todo.write_text(self.todo.read_text() + '#### Evidence: test results\n  - [ ] qualification pending\n')
                elif case in ('archive_open', 'archive_superseded', 'ledger_archive_superseded'):
                    prefix = 'Disposition: Superseded; not completed\n\n' if 'superseded' in case else ''
                    (self.repo / 'TODO.archive.md').write_text('# History\n' + prefix + task('T1'))
                    if case == 'ledger_archive_superseded':
                        self.ledger([('T1', 'G', 'done', 'Done', [])])
                else:
                    (self.repo / 'TODO.archive.md').symlink_to(self.todo)
                result = self.query('history')
                self.assertEqual(result['total'], 0)
                self.assertTrue(result['partial'])
                detail = self.query('detail', text='T1')
                self.assertTrue(detail['records'][0]['uncertain'])
                self.assertTrue(detail['records'][0]['sources'])
                self.assertIsNone(detail['selection']['next_eligible'])
                self.assertIsNone(detail['records'][0]['date'])
                for mode in ('search', 'history'):
                    self.assertEqual(self.query(mode, text='T1', since='2026-10-14', until='2026-10-16')['total'], 0)
        (self.repo / 'TODO.archive.md').unlink(missing_ok=True)
        self.todo.write_text('# TODO\n## Next\n' + task('T1', extra='  Goal: F\n'))
        self.ledger([('T1', 'G', 'open', 'Now', [])])
        self.assertIsNone(self.query()['selection']['next_eligible'])
        self.todo.write_text('# TODO\n## Now\n' + task('T1', extra='  Dependencies: T9\n') +
                             '## Needs decision\n' + task('T9'))
        self.ledger([('T1', 'G', 'open', 'Now', [])])
        unindexed = self.query()
        self.assertIsNone(unindexed['selection']['next_eligible'])
        self.assertTrue(unindexed['records'][0]['blocked'])
        self.assertTrue(unindexed['partial'])

    def test_dependency_syntax_cannot_disappear_into_an_empty_gate(self):
        self.ledger([('T1', 'G', 'open', 'Now', [])])
        for value, runnable in (('None.', True), ('', False), ('!!!', False),
                                ('???', False), ('None ???', False), ('T1 ???', False)):
            with self.subTest(value=value):
                self.todo.write_text('# TODO\n## Now\n' + task('T1', extra=f'  Dependencies: {value}\n'))
                result = self.query()
                self.assertEqual(result['selection']['next_eligible'], 'T1' if runnable else None)
                self.assertEqual(result['records'][0]['uncertain'], not runnable)
                self.assertEqual(result['records'][0]['blocked'], not runnable)

    def test_nonregular_source_is_rejected_without_waiting_for_a_writer(self):
        self.todo.unlink()
        os.mkfifo(self.todo)
        result = subprocess.run([sys.executable, str(Path(task_query.__file__)), 'pending', '--repo', str(self.repo)],
                                capture_output=True, text=True, timeout=3, check=True)
        output = json.loads(result.stdout)
        self.assertTrue(output['partial'])
        self.assertTrue(any(w['source'] == 'TODO.md' and w['code'] == 'unreadable' for w in output['warnings']))

    def test_changing_snapshot_retries_once_then_suppresses_claims(self):
        self.todo.write_text('# TODO\n## Done\n' + task('T1', status='done'))
        original = task_query.read_source
        count = 0
        def changing(repo, name):
            nonlocal count
            if name == 'TODO.md':
                count += 1
                self.todo.write_text(self.todo.read_text() + '\n')
            return original(repo, name)
        with patch.object(task_query, 'read_source', side_effect=changing):
            result = self.query('history')
        self.assertEqual(result['total'], 0)
        self.assertTrue(result['partial'])
        self.assertTrue(any(w['code'] == 'unstable' for w in result['warnings']))
        changed_once = False
        def once(repo, name):
            nonlocal changed_once
            blob = original(repo, name)
            if name == 'TODO.md' and not changed_once:
                changed_once = True
                self.todo.write_text('# TODO\n## Now\n' + task('T2'))
            return blob
        with patch.object(task_query, 'read_source', side_effect=once):
            recovered = self.query()
        self.assertEqual([r['id'] for r in recovered['records']], ['T2'])
        self.assertFalse(recovered['partial'])

    def test_all_cli_modes_leave_bytes_and_refs_unchanged_and_text_is_data(self):
        self.git('init', '-q')
        hostile = '$(touch PWNED); `exit 9`'
        self.todo.write_text('# TODO\n## Now\n' + task('T1', hostile) +
                             '## Done\n' + task('T2', status='done'))
        self.commit('2026-10-10T12:00:00+00:00')
        def snapshot():
            return {str(p.relative_to(self.repo)): p.read_bytes() for p in self.repo.rglob('*') if p.is_file()}
        before = snapshot()
        for mode in ('pending', 'detail', 'search', 'history'):
            args = [sys.executable, str(Path(task_query.__file__)), mode, '--repo', str(self.repo)]
            if mode != 'history':
                args += ['--text', hostile]
            env = dict(os.environ, GIT_TRACE=str(self.repo / 'trace.log'),
                       GIT_TRACE_SETUP=str(self.repo / 'setup.log'),
                       GIT_TRACE2_EVENT=str(self.repo / 'trace2.json'))
            result = subprocess.run(args, text=True, capture_output=True, env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['total'], 1)
            self.assertEqual(snapshot(), before)
        nested = self.repo / 'src'
        nested.mkdir()
        default = subprocess.run([sys.executable, str(Path(task_query.__file__)), 'pending'],
                                 cwd=nested, text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(default.stdout)['total'], 1)
        self.assertEqual(snapshot(), before)
        self.assertFalse((self.repo / 'PWNED').exists())


if __name__ == '__main__':
    unittest.main()
