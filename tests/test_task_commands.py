"""`autowork tasks ...` against a real Git repository built from the TaskStore fixture."""
from datetime import date
import json
from pathlib import Path
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / 'pi-autowork/pi_autowork/command.py'
FIXTURE = ROOT / 'pi-autowork/engine/fixtures/task_store'
sys.path.insert(0, str(ROOT / 'pi-autowork/engine'))
sys.path.insert(0, str(ROOT / 'pi-autowork'))
from task_store import TaskStore, edit  # noqa: E402
from pi_autowork import task_commands as commands  # noqa: E402


class TaskCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'repo'
        shutil.copytree(FIXTURE, self.repo)
        self.git('init', '-q')
        self.commit()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), '-c', 'user.email=f@example.invalid',
                               '-c', 'user.name=F', *args], check=True, capture_output=True, text=True).stdout

    def commit(self):
        self.git('add', '-A')
        self.git('commit', '-q', '--allow-empty', '-m', 'tasks')

    def tasks(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(COMMAND), 'tasks', *args], cwd=self.repo,
                                capture_output=True, text=True, timeout=60)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def show(self, tid):
        self.commit()
        return json.loads(self.tasks('show', tid).stdout)

    def add(self, title, *extra):
        out = self.tasks('add', '--goal', 'G-1', '--title', title, '--short', title, '--scope', 'x',
                         '--acceptance', 'done', '--checks', 'true', '--touches', 'src/', *extra).stdout
        return out.split()[-1]

    def test_worktree_validation_and_writes_leave_no_git_objects(self):
        # Exercise common-dir lookup and C-quoted alternates in a linked checkout.
        origin = self.repo.with_name('repo:\x01with-"quotes"')
        self.repo.rename(origin)
        self.repo = origin
        linked = origin / '.worktrees/validation'
        self.git('worktree', 'add', '-qb', 'validation', str(linked))
        self.repo = linked
        index_path = Path(self.git('rev-parse', '--absolute-git-dir').strip()) / 'index'
        # A private index alone still leaks add/write-tree/commit-tree objects.
        (self.repo / 'staged.txt').write_text('unrelated staged content\n')
        self.git('add', 'staged.txt')
        index = index_path.read_bytes()
        refs = self.git('show-ref', '--head')
        objects = self.git('count-objects', '-v')
        path = self.repo / 'tasks/items/T-1.md'
        path.write_text(path.read_text().replace('Read tasks', 'Edited task'))
        for args in (('validate', '--worktree'), ('prepare',),
                     ('field', 'T-1', 'title', 'Written task'),
                     ('show', 'T-1', '--worktree')):
            with self.subTest(command=args):
                result = self.tasks(*args)
                if args[0] == 'show':
                    self.assertEqual(json.loads(result.stdout)['title'], 'Written task')
                self.assertEqual(self.git('count-objects', '-v'), objects)
                self.assertEqual(index_path.read_bytes(), index)
                self.assertEqual(self.git('show-ref', '--head'), refs)
        path.write_text('invalid frontmatter\n')
        self.assertNotEqual(self.tasks('validate', '--worktree', ok=False).returncode, 0)
        self.assertEqual(self.git('count-objects', '-v'), objects)

    def test_add_then_show(self):
        legacy = self.add('Legacy task', '--id', 'T-010-ab')
        legacy_path = self.repo / 'tasks/items' / f'{legacy}.md'
        legacy_bytes = legacy_path.read_bytes()
        tid = self.add('Second task')
        text = (self.repo / f'tasks/items/{tid}.md').read_text()
        self.assertTrue(text.endswith('+++\n'), repr(text[-20:]))
        self.git('add', '--', f'tasks/items/{tid}.md')
        self.git('diff', '--cached', '--check')
        record = self.show(tid)
        self.assertEqual((record['title'], record['section'], record['status'], record['rank']),
                         ('Second task', 'Now', 'open', 2000))
        self.assertFalse(record['draft'])
        self.assertEqual((record['resources'], record['live']), ([], 'denied'))
        self.assertRegex(tid, r'^T-011-[0-9a-f]{8}$')
        self.assertRegex(self.tasks('new-id').stdout.strip(), r'^T-012-[0-9a-f]{8}$')
        self.assertEqual(legacy_path.read_bytes(), legacy_bytes)
        # Equal ranks exercise the ID tie-break with both suffix lengths.
        self.tasks('field', legacy, 'rank', '2000')
        self.assertTrue(json.loads(self.tasks('validate', '--worktree').stdout)['ok'])
        self.commit()
        self.assertTrue(json.loads(self.tasks('validate').stdout)['ok'])
        rows = json.loads(self.tasks('list').stdout)
        self.assertEqual([row['id'] for row in rows], ['T-1', legacy, tid])
        self.assertEqual([row['position'] for row in rows], [1, 2, 3])
        (self.repo / 'TODO.archive.md').write_text('- T-020-deadbeef — archived\n')
        self.assertRegex(self.tasks('new-id').stdout.strip(), r'^T-021-[0-9a-f]{8}$')
        self.assertFalse((self.repo / 'TODO.md').exists())
        self.assertFalse((self.repo / 'goals.json').exists())

    def test_add_list_flags_accept_json_arrays_and_repeated_items(self):
        self.add('Other prerequisite', '--id', 'T-2')
        expected = dict(touches=['[ab].py', 'b'], acceptance=['done, checked', 'proven'],
                        checks=['[ -f README.md ]', 'true'], depends_on=['T-1', 'T-2'],
                        verified_depends_on=['T-1', 'T-2'], resources=['exclusive', 'test-db'],
                        exclusions=['no push', 'no live'])
        for mode in ('repeated', 'json', 'mixed'):
            with self.subTest(mode=mode):
                flags = []
                for field, values in expected.items():
                    inputs = (values if mode == 'repeated' else [json.dumps(values)] if mode == 'json'
                              else [json.dumps(values[:1]), values[1], '[]'])
                    for value in inputs:
                        flags.extend(['--' + field.replace('_', '-'), value])
                tid = self.tasks('add', '--goal', 'G-1', '--title', mode, '--short', mode,
                                 '--scope', 'x', *flags).stdout.split()[-1]
                record = json.loads(self.tasks('show', tid, '--worktree').stdout)
                self.assertEqual({key: record[key] for key in expected}, expected)

    def test_add_refuses_nonstring_json_list_items_without_writing(self):
        before = self.git('status', '--porcelain', '--', 'tasks')
        for value in ('[1]', '[["a"]]', '[true]', '[null]'):
            with self.subTest(value=value):
                refused = self.tasks('add', '--goal', 'G-1', '--title', 'Bad list', '--short', 'Bad list',
                                     '--touches', value, ok=False)
                self.assertEqual(refused.returncode, 1)
                self.assertIn('touches', refused.stderr)
                self.assertNotIn('Traceback', refused.stderr)
                self.assertEqual(self.git('status', '--porcelain', '--', 'tasks'), before)

    def test_json_input_round_trips_literal_prose_without_shell_execution(self):
        # Run the documented shell form; expanding either command would leave a marker.
        prose = '  `touch backtick-ran` $(touch substitution-ran) $VAR "double" \'single\' café\nnext line  '
        bin_dir = self.repo / 'bin'
        bin_dir.mkdir()
        wrapper = bin_dir / 'autowork'
        wrapper.write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(COMMAND))} "$@"\n')
        wrapper.chmod(0o755)
        env = {**os.environ, 'PATH': str(bin_dir) + os.pathsep + os.environ['PATH'], 'VAR': 'expanded'}
        for index, source in enumerate(('payload.json', '- < payload.json')):
            with self.subTest(source=source):
                def invoke(verb, payload):
                    (self.repo / 'payload.json').write_text(json.dumps(payload), encoding='utf-8')
                    result = subprocess.run(['/bin/sh', '-c', f'autowork tasks {verb} --json {source}'],
                                            cwd=self.repo, env=env, capture_output=True, text=True, timeout=60)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertFalse((self.repo / 'backtick-ran').exists())
                    self.assertFalse((self.repo / 'substitution-ran').exists())
                    return result.stdout.strip()

                gid = f'JSON-{index}'
                invoke(f'goal {gid}', dict(title=prose, source='docs/plan.md#json', priority=2))
                tid = invoke('add', dict(goal=gid, title=f'Literal {index}', short='Literal', scope=prose,
                                         acceptance=[prose], notes=prose, checks=['true'], touches=['src/'])).split()[-1]
                record = json.loads(self.tasks('show', tid, '--worktree').stdout)
                self.assertEqual((record['scope'], record['acceptance'], record['notes']), (prose, [prose], prose))
                changed = prose + '\nupdated'
                for label, value in (('scope', changed), ('acceptance', [changed]), ('notes', changed)):
                    invoke(f'field {tid}', dict(label=label, value=value))
                record = self.show(tid)
                self.assertEqual((record['scope'], record['acceptance'], record['notes']),
                                 (changed, [changed], changed))
                self.assertEqual(TaskStore.at(self.repo, 'HEAD').goals[gid].title, prose)

    def test_json_input_refuses_invalid_or_ambiguous_values_without_writing(self):
        path = self.repo / 'payload.json'
        before = self.git('status', '--porcelain', '--', 'tasks')
        for verb, payload in (
            (['add'], '{'), (['add'], '[]'), (['add'], '{"goal": "G-1"}'),
            (['add'], '{"goal": "G-1", "title": "x", "short": "x", "acceptance": "not an array"}'),
            (['add', '--title', 'flag'], '{"goal": "G-1", "title": "json", "short": "x"}'),
            (['field', 'T-1'], '{"label": "rank", "value": true}'),
            (['field', 'T-1'], '{"label": "scope", "value": 1}'),
            (['field', 'T-1'], '{"label": "acceptance", "value": [1]}'),
            (['goal', 'G-1'], '{"focus": "false"}'),
            (['goal', 'G-1'], '{"priority": true}'),
            (['goal', 'G-1'], '{"unknown": "x"}'),
            (['add'], '{"goal": "G-1", "title": "x", "short": "x", "notes": "raw", "sources": "docs/plan.md"}'),
        ):
            with self.subTest(verb=verb, payload=payload):
                path.write_text(payload)
                refused = self.tasks(*verb, '--json', str(path), ok=False)
                self.assertNotEqual(refused.returncode, 0)
                self.assertNotIn('Traceback', refused.stderr)
                self.assertEqual(self.git('status', '--porcelain', '--', 'tasks'), before)
        self.assertNotEqual(self.tasks('field', 'T-1', '--json', 'missing.json', ok=False).returncode, 0)

    def test_field_sets_a_typed_field_or_a_note(self):
        self.tasks('field', 'T-1', 'touches', 'src/, docs/')
        self.tasks('field', 'T-1', 'Held by', 'the owner; until 2026-10-27')
        self.tasks('field', 'T-1', 'notes', 'legacy note')
        record = self.show('T-1')
        self.assertEqual(record['touches'], ['src/', 'docs/'])
        self.assertIn('- Held by: the owner; until 2026-10-27', record['notes'])
        self.assertIn('- notes: legacy note', record['notes'])
        self.assertEqual(self.tasks('field', 'T-1', 'rank', 'high', ok=False).returncode, 1)
        self.assertEqual(self.tasks('field', 'T-1', 'status', 'done', ok=False).returncode, 1)

    def test_place_into_needs_decision_changes_the_contract(self):
        sys.path.insert(0, str(ROOT / 'pi-autowork'))
        import parallel_status
        from pi_autowork import questions
        self.add('Waiting for decision', '--depends-on', 'T-1')
        before = self.show('T-1')
        self.tasks('place', 'T-1', 'Needs decision')
        after = self.show('T-1')
        self.assertEqual(after['section'], 'Needs decision')
        self.assertNotEqual(after['contract_hash'], before['contract_hash'])
        self.assertEqual(json.loads(self.tasks('why', 'T-1').stdout)['reasons'][0]['code'], 'NEEDS_DECISION')
        blockers = questions.update('', questions.build(parallel_status.snapshot(self.repo), self.repo))
        self.assertIn('### Q-T-1 ', blockers)
        for decision, dated in (('deferred', f'{date.today().isoformat()}: deferred'),
                                ('2001-02-03: deferred', '2001-02-03: deferred')):
            with self.subTest(decision=decision):
                self.tasks('place', 'T-1', 'Needs decision', '--decision', decision)
                self.assertIn(f'- Owner decision: {dated}\n', self.show('T-1')['notes'])
                updated = questions.update(blockers, questions.build(parallel_status.snapshot(self.repo), self.repo))
                self.assertNotIn('### Q-T-1 ', updated)

    def test_move_changes_only_the_rank(self):
        second = self.add('Second')
        before = self.show(second)
        self.tasks('move', second, 'up')
        after = self.show(second)
        self.assertLess(after['rank'], self.show('T-1')['rank'])
        self.assertEqual(after['contract_hash'], before['contract_hash'])
        self.assertEqual(self.git('status', '--porcelain'), '')
        first = json.loads(self.tasks('why', second).stdout)
        self.assertEqual((first['eligible'], first['first']), (True, True))

    def test_move_without_a_gap_rebalances_locally(self):
        ids = [self.add(f'Task {n}') for n in range(4)]
        for tid, rank in zip(['T-1', *ids], (1, 2, 3, 4, 5000)):
            self.tasks('field', tid, 'rank', str(rank))
        self.commit()
        out = self.tasks('move', ids[2], 'up').stdout
        changed = {line.split()[0] for line in out.removeprefix('ok ').split(', ')}
        ranks = {tid: self.show(tid)['rank'] for tid in ['T-1', *ids]}
        order = sorted(ranks, key=lambda tid: (ranks[tid], tid))
        self.assertEqual(order, ['T-1', ids[0], ids[2], ids[1], ids[3]])
        self.assertNotIn('T-1', changed, 'the run before the moved task keeps its ranks')
        self.assertNotIn(ids[0], changed)
        self.assertEqual(ranks[ids[3]], 5000, 'a neighbour with room is not renumbered')

    def test_hold_keeps_the_runner_off_until_release(self):
        before = self.show('T-1')
        self.tasks('hold', 'T-1', '--by', 'an interactive session', '--until', '2999-01-01')
        held = self.show('T-1')
        self.assertEqual((held['status'], held['contract_hash']), ('open', before['contract_hash']))
        self.assertIn('- Held by: an interactive session; until 2999-01-01', held['notes'])
        why = json.loads(self.tasks('why', 'T-1').stdout)
        self.assertEqual(why['reasons'], [{'code': 'HELD', 'detail': 'an interactive session; until 2999-01-01'}])
        self.assertEqual(self.tasks('hold', 'T-1', '--by', 'x', '--until', 'soon', ok=False).returncode, 1)
        self.tasks('release', 'T-1')
        self.assertNotIn('Held by', self.show('T-1')['notes'])
        self.assertTrue(json.loads(self.tasks('why', 'T-1').stdout)['first'])
        self.assertEqual(self.tasks('release', 'T-1', ok=False).returncode, 1)

    def test_manual_closure_records_provenance_without_verification(self):
        sys.path.insert(0, str(ROOT / 'pi-autowork'))
        from pi_autowork import fleet_view
        for kind in ('implementation', 'plan', 'inspection'):
            with self.subTest(kind=kind):
                tid = self.add(kind, '--kind', kind)
                before = self.show(tid)
                evidence = None if kind == 'inspection' else 'docs/review.md'
                self.tasks('done', tid, '--by', 'owner', '--reason', 'Stopped after review',
                           *(['--evidence', evidence] if evidence else []))
                record = self.show(tid)
                self.assertEqual(record['contract_hash'], before['contract_hash'])
                closure = record['closure']
                self.assertEqual((closure['provenance'], closure['actor'], closure['reason'], closure['evidence']),
                                 ('manual', 'owner', 'Stopped after review', evidence))
                self.assertRegex(closure['timestamp'], r'^\d{4}-\d\d-\d\dT.*\+00:00$')
                self.assertFalse((self.repo / 'tasks/evidence').exists())
                self.assertNotIn('Evidence:', record['notes'])
                listed = next(r for r in json.loads(self.tasks('list').stdout) if r['id'] == tid)
                why = json.loads(self.tasks('why', tid).stdout)
                self.assertEqual(listed['closure'], closure)
                self.assertEqual(why['closure'], closure)
                rows = fleet_view.task_rows(fleet_view.Runner('fixture', repo=str(self.repo)), include_closed=True)
                row = next(r for r in rows if r.task == tid)
                self.assertEqual(row.state, 'Manual')
                self.assertEqual(row.why, f'Manually closed by owner at {closure["timestamp"]}; '
                                 'not coordinator-verified. Stopped after review')
                actions = fleet_view.task_actions(fleet_view.Runner('fixture'), row,
                                                   command='aw', script='aw.sh')
                self.assertEqual([(action.key, action.argv) for action in actions],
                                 [('x', ['aw', 'tasks', 'delete', tid, 'fixture'])])

    def test_verified_dependencies_require_verification_or_an_owner_waiver(self):
        ordinary = self.add('Ordinary', '--depends-on', 'T-1')
        verified = self.add('Verified consumer', '--depends-on', 'T-1', '--verified-depends-on', 'T-1')
        self.tasks('done', 'T-1', '--by', 'owner', '--reason', 'Not verified')
        self.commit()
        self.assertTrue(json.loads(self.tasks('why', ordinary).stdout)['eligible'])
        why = json.loads(self.tasks('why', verified).stdout)
        self.assertEqual(why['reasons'], [{'code': 'DEPENDENCY_UNVERIFIED', 'detail': 'T-1'}])
        self.tasks('field', 'T-1', 'owner_waiver', 'Owner 2026-10-21: waive prerequisite proof for this scope')
        self.commit()
        self.assertTrue(json.loads(self.tasks('why', verified).stdout)['eligible'])

    def test_goal_met_requires_qualification_of_manual_closures(self):
        self.tasks('done', 'T-1', '--by', 'owner', '--reason', 'Hand closed')
        refused = self.tasks('goal', 'G-1', '--status', 'met', '--evidence', 'goal check: pass', ok=False)
        self.assertEqual(refused.returncode, 1)
        self.assertIn('T-1', refused.stderr)
        self.tasks('field', 'T-1', 'owner_qualification', 'Owner 2026-10-21: inspected result docs/review.md')
        accepted = self.tasks('goal', 'G-1', '--status', 'met', '--evidence', 'goal check: pass')
        self.assertIn('T-1', accepted.stdout)
        self.assertIn('docs/review.md', accepted.stdout)
        self.commit()
        self.assertIn('docs/review.md', TaskStore.at(self.repo, 'HEAD').goals['G-1'].body)

    def test_decide_records_direction_without_inventing_authority(self):
        path = self.repo / 'tasks/items/T-1.md'
        original = json.loads(self.tasks('show', 'T-1', '--worktree').stdout)
        self.tasks('decide', 'T-1', 'Use the smaller design')
        record = json.loads(self.tasks('show', 'T-1', '--worktree').stdout)
        self.assertIn(f'Owner decision: {date.today().isoformat()}: Use the smaller design', record['notes'])
        self.assertEqual((record['rank'], record['contract_hash'], record['status'], record['live']),
                         (original['rank'], original['contract_hash'], 'open', 'denied'))
        before = path.read_bytes()
        self.assertEqual(self.tasks('decide', 'T-1', '  ', ok=False).returncode, 1)
        self.assertEqual(self.tasks('decide', 'T-1', 'Changed', '--expect', original['record_revision'],
                                    ok=False).returncode, 1)
        self.assertEqual(path.read_bytes(), before)
        self.tasks('decide', 'T-1', 'Wait for input', '--section', 'Needs decision')
        record = json.loads(self.tasks('show', 'T-1', '--worktree').stdout)
        self.assertEqual(record['section'], 'Needs decision')
        self.tasks('decide', 'T-1', 'Input supplied; proceed', '--section', 'Next')
        record = json.loads(self.tasks('show', 'T-1', '--worktree').stdout)
        self.assertEqual(record['section'], 'Next')
        self.assertEqual(record['live'], 'denied')

    def test_decide_refuses_closed_task_without_rewriting_history(self):
        self.tasks('done', 'T-1', '--by', 'owner', '--reason', 'manual closure')
        path = self.repo / 'tasks/items/T-1.md'
        before = path.read_bytes()
        refused = self.tasks('decide', 'T-1', 'Changed direction', ok=False)
        self.assertEqual(refused.returncode, 1)
        self.assertIn('open task', refused.stderr)
        self.assertEqual(path.read_bytes(), before)

    def test_supersede_names_its_successor(self):
        successor = self.add('Successor')
        self.tasks('supersede', 'T-1', '--by', successor, '--reason', 'replaced')
        record = self.show('T-1')
        self.assertEqual(record['status'], 'superseded')
        self.assertIn(f'- Superseded by: {successor}; replaced', record['notes'])

    def test_delete_removes_any_task_and_warns_without_refusing(self):
        dependent = self.add('Dependent', '--depends-on', 'T-1')
        path = self.repo / 'tasks/items/T-1.md'
        with patch.object(commands, 'in_flight', return_value=({'T-1'}, ['a live coordinator lease'])):
            warnings = commands.cmd_delete(self.repo, 'T-1')
        self.assertFalse(path.exists())
        self.assertTrue((self.repo / f'tasks/items/{dependent}.md').exists())
        self.assertTrue(any('T-1' in warning and 'held' in warning for warning in warnings), warnings)
        self.assertIn('a live coordinator lease', warnings)
        self.assertTrue(any(dependent in warning for warning in warnings), warnings)
        self.commit()
        self.assertTrue(json.loads(self.tasks('validate').stdout)['ok'])
        self.assertEqual(self.tasks('show', 'T-1', ok=False).returncode, 1)

    def test_delete_cli_reports_dependents_and_proceeds(self):
        dependent = self.add('Dependent', '--depends-on', 'T-1')
        result = self.tasks('delete', 'T-1')
        self.assertIn('deleted', result.stdout)
        self.assertIn(dependent, result.stdout)
        self.assertFalse((self.repo / 'tasks/items/T-1.md').exists())
        self.commit()
        self.assertEqual(self.tasks('show', 'T-1', ok=False).returncode, 1)

    def test_why_and_list_name_their_reasons(self):
        before = self.git('status', '--porcelain', '--', 'tasks')
        for flags in (('--depends-on', 'T-404'), ('--depends-on', '["T-404"]')):
            with self.subTest(flags=flags):
                refused = self.tasks('add', '--goal', 'G-1', '--title', 'Missing dependency',
                                     '--short', 'Missing dependency', *flags, ok=False)
                self.assertEqual(refused.returncode, 1)
                self.assertIn('T-404', refused.stderr)
                self.assertEqual(self.git('status', '--porcelain', '--', 'tasks'), before)
        blocked = self.add('Blocked', '--depends-on', 'T-1')
        self.assertEqual(self.tasks('validate', '--worktree', ok=False).returncode, 0)
        self.commit()
        reasons = json.loads(self.tasks('why', blocked).stdout)
        self.assertEqual(reasons['reasons'], [{'code': 'DEPENDENCY_UNFINISHED', 'detail': 'T-1'}])
        rows = {row['id']: row for row in json.loads(self.tasks('list').stdout)}
        self.assertEqual((rows['T-1']['position'], rows[blocked]['blocked_by']), (1, 'DEPENDENCY_UNFINISHED'))

    def test_validate_fails_on_a_broken_file(self):
        self.assertEqual(json.loads(self.tasks('validate').stdout)['tasks'], 1)
        path = self.repo / 'tasks/items/T-1.md'
        path.write_text(path.read_text().replace('rank = 1', 'rank = ['))
        broken = self.tasks('validate', '--worktree', ok=False)
        self.assertEqual(broken.returncode, 1)
        self.assertRegex(broken.stderr, r'tasks/items/T-1.md:\d+:')
        self.commit()
        self.assertEqual(self.tasks('validate', ok=False).returncode, 1)

    def test_validate_refuses_json_encoded_list_items(self):
        path = self.repo / 'tasks/items/T-1.md'
        original = path.read_text()
        for field in ('touches', 'acceptance', 'checks', 'depends_on', 'resources', 'exclusions',
                      'verified_depends_on'):
            with self.subTest(field=field):
                path.write_text(edit(original, {field: ['["a", "b"]']}))
                refused = self.tasks('validate', '--worktree', ok=False)
                self.assertEqual(refused.returncode, 1)
                self.assertRegex(refused.stderr, rf'tasks/items/T-1.md:\d+:.*{field}')
                self.assertIn('JSON', refused.stderr)

    def test_a_write_that_breaks_the_store_is_undone(self):
        path = self.repo / 'tasks/items/T-1.md'
        before = path.read_bytes()
        result = self.tasks('field', 'T-1', 'goal', 'NOPE', ok=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn('unknown goal', result.stderr)
        self.assertEqual(path.read_bytes(), before)

    def test_goal_adds_and_changes_a_goal_and_moves_focus(self):
        self.assertIn('needs --source, --priority', self.tasks('goal', 'G-2', '--title', 'Two', ok=False).stderr)
        self.assertEqual(self.tasks('goal', 'G-2', '--title', 'Two', '--source', 'docs/plan.md#two',
                                    '--priority', '2', '--depends-on', 'G-1').stdout.strip(), 'added goal G-2')
        refused = self.tasks('goal', 'G-2', '--status', 'met', ok=False)
        self.assertIn('needs --evidence', refused.stderr)
        self.tasks('goal', 'G-2', '--status', 'met', '--evidence', 'python3 -m unittest passed (offline)')
        self.tasks('goal', 'G-2', '--focus')
        self.commit()
        store = TaskStore.at(self.repo, 'HEAD')
        two = store.goals['G-2']
        self.assertEqual((two.title, two.priority, two.status, two.focus, two.depends_on),
                         ('Two', 2, 'met', True, ('G-1',)))
        self.assertIn('- Evidence: python3 -m unittest passed (offline)', two.body)
        self.assertEqual([g.id for g in store.goals.values() if g.focus], ['G-2'])  # at most one
        self.assertIn('is a task', self.tasks('goal', 'T-1', '--title', 'x', ok=False).stderr)

    def test_the_first_goal_starts_a_new_store(self):
        shutil.rmtree(self.repo / 'tasks')
        self.commit()
        self.assertEqual(self.tasks('goal', 'G-1', '--title', 'One', '--source', 'docs/plan.md#one',
                                    '--priority', '1').stdout.strip(), 'added goal G-1')
        first = self.add('First task')
        self.assertEqual(json.loads(self.tasks('validate', '--worktree').stdout)['tasks'], 1)
        self.assertEqual(self.show(first)['goal'], 'G-1')

    def test_an_unconverted_repository_is_refused(self):
        shutil.rmtree(self.repo / 'tasks')
        self.commit()
        result = self.tasks('list', ok=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn('no task store', result.stderr)


if __name__ == '__main__':
    unittest.main()
