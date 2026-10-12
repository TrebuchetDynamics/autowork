#!/usr/bin/env python3
"""Real filesystem/CLI fixtures; never initialize a Hermes profile."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('audit_profiles.py')


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'hermes'
        self.root.mkdir()
        self.state = self.root / 'maintenance/audit'

    def profile(self, name):
        home = self.root if name == 'default' else self.root / 'profiles' / name
        home.mkdir(parents=True, exist_ok=True)
        (home / 'config.yaml').write_text('terminal:\n  cwd: .\n')
        return home

    def run_collector(self, *args, success=True):
        result = subprocess.run([sys.executable, str(SCRIPT), '--root', str(self.root),
                                 '--state-dir', str(self.state), *args], capture_output=True, text=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        return result, json.loads(result.stdout) if result.stdout else {}

    def receipt(self, summary):
        return json.loads(Path(summary['receipt']).read_text())

    def test_default_all_real_profiles_and_missing_sources(self):
        self.profile('default')
        for name in ('one', 'two', 'added-later', '.hidden', 'gone'):
            self.profile(name)
        (self.root / 'profiles/ghost/logs').mkdir(parents=True)
        (self.root / 'profiles/.deleted').mkdir()
        (self.root / 'profiles/.deleted/gone').touch()
        _, summary = self.run_collector()
        self.assertEqual([p['profile'] for p in summary['profiles']],
                         ['default', 'added-later', 'one', 'two'])
        rows = self.receipt(summary)['profiles']
        self.assertTrue(all(p['gaps'] for p in rows))
        self.assertTrue(all(p['repo']['state'] == 'unknown_relative_cwd' for p in rows))
        self.assertTrue(all(p['live_ownership'] == 'unknown' for p in rows))

    def test_owner_cycle_receipt_is_collected_without_claiming_live_progress(self):
        home=self.profile('default')
        (home/'autowork').mkdir()
        (home/'autowork/unblock-latest.json').write_text(json.dumps({'version':1,'run_id':'run',
            'task_ids':['T1'],'outcome':'BLOCKED','action':'owner_followup_required',
            'request_status':'pending','integration_request':'/private/request', 'unchanged_runs':3}))
        _,summary=self.run_collector()
        row=self.receipt(summary)['profiles'][0]
        self.assertEqual(row['owner_cycle']['task_ids'],['T1'])
        self.assertEqual(row['owner_cycle']['outcome'],'BLOCKED')
        self.assertEqual(row['live_ownership'],'unknown')

    def test_rejects_named_profile_alias_state_and_emits_errors(self):
        home = self.profile('one')
        (self.root / 'maintenance').mkdir()
        (self.root / 'maintenance/alias').symlink_to(home, target_is_directory=True)
        _, summary = self.run_collector('--state-dir', str(self.root / 'maintenance/alias/audit'), success=False)
        self.assertEqual(summary['state'], 'collector_failed')
        self.assertFalse((home / 'audit').exists())
        result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)['state'], 'collector_failed')

    def test_logs_cursor_suffix_rotation_and_no_sibling_writes(self):
        home = self.profile('one')
        (home / 'logs').mkdir()
        log = home / 'logs/agent.log'
        log.write_bytes(b'token=secret-value\n' + b'x' * 30)
        before = {str(p): p.read_bytes() for p in home.rglob('*') if p.is_file()}
        _, summary = self.run_collector('--log-bytes', '10')
        row = self.receipt(summary)['profiles'][1]['logs'][0]
        self.assertEqual((row['start'], row['cursor'], row['remaining_bytes']), (0, 10, log.stat().st_size - 10))
        self.assertEqual(row['analysis'], 'not_analyzed')
        _, summary = self.run_collector('--log-bytes', '10')
        row = self.receipt(summary)['profiles'][1]['logs'][0]
        self.assertEqual((row['start'], row['cursor']), (10, 20))
        self.assertNotIn('secret-value', Path(summary['receipt']).read_text())
        self.assertEqual(before, {str(p): p.read_bytes() for p in home.rglob('*') if p.is_file()})
        log.rename(log.with_name('agent.log.1'))
        log.write_bytes(b'new file')
        _, summary = self.run_collector('--log-bytes', '10')
        rows = self.receipt(summary)['profiles'][1]['logs']
        current = next(r for r in rows if r['file'] == 'agent.log')
        self.assertEqual(current['start'], 0)
        self.assertTrue(current['history_gaps'])
        log.write_bytes(b'z')
        _, summary = self.run_collector('--log-bytes', '10')
        current = next(r for r in self.receipt(summary)['profiles'][1]['logs'] if r['file'] == 'agent.log')
        self.assertTrue(any('truncated' in g for g in current['history_gaps']))

    def test_completed_new_run_no_progress_and_unrelated_dirt(self):
        import sqlite3
        home = self.profile('default')
        repo = Path(self.tmp.name) / 'repo'
        repo.mkdir()
        def git(*argv):
            subprocess.run(['git', '-C', str(repo), *argv], check=True, capture_output=True)
        git('init'); git('config', 'user.email', 'fixture@example.test'); git('config', 'user.name', 'Fixture')
        (repo / 'a').write_text('first\n')
        (repo / 'goals.json').write_text('{}')
        (repo / 'TODO.md').write_text('# backlog')
        git('add', '.'); git('commit', '-m', 'fixture')
        (home / 'config.yaml').write_text('terminal:\n  cwd: ' + str(repo) + '\n')
        (home / 'autowork').mkdir()
        (home / 'autowork/state.json').write_text(json.dumps({'task_id': 't1', 'blocker': 'needs check', 'checks': ['failed']}))
        (home / 'cron').mkdir()
        with sqlite3.connect(home / 'cron/executions.db') as db:
            db.execute('create table executions(id text, job_id text, status text, started_at text, finished_at text)')
            db.execute("insert into executions values('run1','job','completed','1','1')")
        _, summary = self.run_collector()
        self.assertEqual(summary['profiles'][0]['no_progress']['consecutive'], 0)
        (repo / 'unrelated-untracked').write_text('foreign work\n')
        _, summary = self.run_collector()
        self.assertEqual(summary['profiles'][0]['no_progress']['consecutive'], 0)
        with sqlite3.connect(home / 'cron/executions.db') as db:
            db.execute("insert into executions values('run2','job','completed','2','2')")
        _, summary = self.run_collector()
        self.assertEqual(summary['profiles'][0]['no_progress']['consecutive'], 1)
        _, summary = self.run_collector()
        self.assertEqual(summary['profiles'][0]['no_progress']['consecutive'], 1)
        (home / 'autowork/state.json').write_text(json.dumps({'task_id': 't1', 'blocker': 'needs check',
                                                            'checks': ['failed'], 'worker_session_id': 'new-worker'}))
        with sqlite3.connect(home / 'cron/executions.db') as db:
            db.execute("insert into executions values('run3','different-job','completed','3','3')")
        _, summary = self.run_collector()
        self.assertEqual(summary['profiles'][0]['no_progress']['consecutive'], 2)
        self.assertEqual(summary['profiles'][0]['no_progress']['state'], 'repeated_no_progress')
        (repo / 'a').write_text('real changed bytes\n')
        with sqlite3.connect(home / 'cron/executions.db') as db:
            db.execute("insert into executions values('run4','job','completed','4','4')")
        _, summary = self.run_collector()
        self.assertEqual(summary['profiles'][0]['no_progress']['consecutive'], 3)
        row = self.receipt(summary)['profiles'][0]
        self.assertIn('untracked content not inspected', row['gaps'])
        (home / 'autowork/state.json').write_text(json.dumps({'task_id': 't1', 'blocker': 'new blocker', 'checks': ['passed']}))
        _, summary = self.run_collector()
        self.assertEqual(summary['profiles'][0]['no_progress']['consecutive'], 0)

    def test_rename_status_counts_one_record_and_backlog_readiness_is_read_only(self):
        home = self.profile('default')
        repo = Path(self.tmp.name) / 'repo'
        repo.mkdir()
        def git(*argv):
            subprocess.run(['git', '-C', str(repo), *argv], check=True, capture_output=True)
        git('init'); git('config', 'user.email', 'fixture@example.test'); git('config', 'user.name', 'Fixture')
        (repo / 'old').write_text('same content\n')
        ledger = {'version': 1, 'primary_milestone': 'G1', 'goals': [
            {'id': 'G1', 'title': 'fixture', 'source': 'SPEC.md#accepted', 'status': 'unmet', 'tasks': ['T1']}],
            'tasks': [{'id': 'T1', 'title': 'fixture task', 'goal': 'G1', 'status': 'open', 'section': 'Now'}]}
        (repo / 'goals.json').write_text(json.dumps(ledger))
        (repo / 'TODO.md').write_text('# TODO\n')
        git('add', '.'); git('commit', '-m', 'fixture'); git('mv', 'old', 'new')
        (home / 'config.yaml').write_text('terminal:\n  cwd: ' + str(repo) + '\n')
        index = (repo / '.git/index').read_bytes()
        before = (repo / 'goals.json').read_bytes()
        _, summary = self.run_collector()
        row = self.receipt(summary)['profiles'][0]['repo']
        self.assertEqual(row['dirty_records'], 1)
        self.assertEqual(row['backlog_readiness']['state'], 'ledger_eligible_only')
        self.assertEqual(row['backlog_readiness']['eligible_task_ids'], ['T1'])
        self.assertEqual(before, (repo / 'goals.json').read_bytes())
        self.assertEqual(index, (repo / '.git/index').read_bytes())

    def test_job_delivery_and_response_coverage_are_not_silently_omitted(self):
        home = self.profile('default')
        (home / 'cron/output/j1').mkdir(parents=True)
        (home / 'cron/jobs.json').write_text(json.dumps({'jobs': [
            {'id': 'j1', 'enabled': True, 'last_delivery_error': 'permission denied',
             'last_delivery_unverified': True, 'last_fire_error': 'preflight denied'}]}))
        output = home / 'cron/output/j1/2026-10-11_10-00-00.md'
        output.write_text('Blocked: token=never-show-this\n')
        before = output.read_bytes()
        _, summary = self.run_collector()
        row = self.receipt(summary)['profiles'][0]
        self.assertEqual(row['jobs'][0]['last_delivery_error'], 'permission denied')
        self.assertTrue(row['jobs'][0]['last_delivery_unverified'])
        self.assertEqual(row['jobs'][0]['last_fire_error'], 'preflight denied')
        self.assertEqual(row['cron_responses'][0]['analysis'], 'not_analyzed')
        self.assertEqual(row['cron_responses'][0]['path'], str(output))
        self.assertNotIn('never-show-this', Path(summary['receipt']).read_text())
        self.assertEqual(before, output.read_bytes())

    def test_git_observation_does_not_execute_repository_fsmonitor(self):
        home = self.profile('default')
        repo = Path(self.tmp.name) / 'repo'
        repo.mkdir()
        def git(*argv):
            subprocess.run(['git', '-C', str(repo), *argv], check=True, capture_output=True)
        git('init'); git('config', 'user.email', 'fixture@example.test'); git('config', 'user.name', 'Fixture')
        (repo / 'a').write_text('fixture\n')
        git('add', '.'); git('commit', '-m', 'fixture')
        marker = Path(self.tmp.name) / 'fsmonitor-ran'
        monitor = Path(self.tmp.name) / 'monitor.py'
        monitor.write_text('from pathlib import Path\nPath(' + repr(str(marker)) + ').touch()\n')
        import shlex
        git('config', 'core.fsmonitor', shlex.quote(sys.executable) + ' ' + shlex.quote(str(monitor)))
        (home / 'config.yaml').write_text('terminal:\n  cwd: ' + str(repo) + '\n')
        self.run_collector()
        self.assertFalse(marker.exists(), 'read-only audit executed repository fsmonitor')

    def test_ro_sqlite_allowlist_and_state_lock_boundary(self):
        import sqlite3
        import fcntl
        home = self.profile('default')
        with sqlite3.connect(home / 'state.db') as db:
            db.execute('create table sessions(id text, started_at real, source text, system_prompt text)')
            db.execute("insert into sessions values('s', 1, 'cli', 'VERY_PRIVATE_PROMPT')")
        _, summary = self.run_collector()
        self.assertNotIn('VERY_PRIVATE_PROMPT', Path(summary['receipt']).read_text())
        with (self.state / 'collector.lock').open('a') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result, summary = self.run_collector(success=False)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(summary['state'], 'overlap_refused')
        sibling = self.root / 'profiles/one/state'
        result = subprocess.run([sys.executable, str(SCRIPT), '--root', str(self.root),
                                 '--state-dir', str(sibling)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(sibling.exists())


if __name__ == '__main__':
    unittest.main()
