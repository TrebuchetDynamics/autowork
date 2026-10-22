"""`autowork migrate`: a TODO.md + goals.json repository converts to tasks/ once, losslessly."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / 'pi-autowork/pi_autowork/command.py'
sys.path.insert(0, str(ROOT / 'pi-autowork/engine'))
sys.path.insert(0, str(ROOT / 'pi-autowork'))
from pi_autowork.legacy import reader  # noqa: E402
import task_execution  # noqa: E402
from task_store import TaskStore  # noqa: E402

EVIDENCE = [{'kind': 'executed', 'ref': 'fixture check', 'result': 'pass'}]


def entry(tid, title, goal, done=False, **fields):
    lines = [f'### {tid} — {title}', '', f'- [{"x" if done else " "}] {tid} — {title}',
             f'- Short: {title}', f'- Status: {"done" if done else "open"}', f'- Goal: {goal}',
             '- Scope: change it', '- Acceptance: it works', '- Checks: python3 -m unittest']
    lines += [f'- {label.replace("_", " ")}: {value}' for label, value in fields.items()]
    return '\n'.join(lines) + '\n\n'


# A queue as the last Docs Sync left it: T-006 archived, its priority order recorded. Frozen
# as files, since goals.py, which wrote them, is gone.
FIXTURE = ROOT / 'tests/fixtures/task_migrate'


class MigrateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        for name in ('TODO.md', 'TODO.archive.md', 'goals.json'):
            (self.repo / name).write_bytes((FIXTURE / name).read_bytes())
        self.commit()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), '-c', 'user.email=f@example.invalid',
                               '-c', 'user.name=F', *args], check=True, capture_output=True, text=True).stdout

    def commit(self):
        self.git('add', '-A')
        self.git('commit', '-q', '--allow-empty', '-m', 'fixture')

    def migrate(self, *args):
        return subprocess.run([sys.executable, str(COMMAND), 'migrate', str(self.repo), *args],
                              capture_output=True, text=True, timeout=120)

    def test_migration_keeps_order_and_fields(self):
        legacy = reader.order(self.repo)
        recorded = json.loads((self.repo / 'goals.json').read_text())['priority_order']['tasks']
        # Focus G2 first (T-004, though in Next; T-002 waits for T-001), then Now, then Next.
        self.assertEqual(legacy, ['T-004', 'T-001', 'T-003', 'T-005'])
        result = self.migrate()
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual((summary['outcome'], summary['order']), ('CONVERTED', legacy))
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertFalse((self.repo / 'TODO.md').exists())
        self.assertFalse((self.repo / 'goals.json').exists())
        self.assertTrue((self.repo / 'TODO.archive.md').exists())
        self.assertFalse((self.repo / 'CHECKLIST.md').exists(), 'a plain queue needs no snapshot')
        self.assertIn('autowork migrate', self.git('log', '-1', '--format=%s'))
        store = TaskStore.at(self.repo, 'HEAD')
        t = store.tasks
        # The engine reads `port:8080 — ...` as the resource `port`; conversion keeps that meaning.
        self.assertEqual((t['T-001'].touches, t['T-001'].resources), (('src/a.py',), ('port',)))
        self.assertIn('- Resources: port:8080 — the dev server', t['T-001'].body)
        self.assertIn('- Sources: [plan](docs/plan.md)', t['T-001'].body)
        self.assertEqual((t['T-002'].depends_on, t['T-003'].kind.value, t['T-003'].touches), (('T-001',), 'plan', ('**',)))
        self.assertEqual((t['T-004'].ownership.value, t['T-004'].live.value, t['T-004'].section), ('worker', 'authorized', 'Next'))
        self.assertIn('- Ownership: Owner only', t['T-004'].body)
        self.assertEqual((t['T-005'].depends_on, t['T-006'].status), (('T-006',), 'done'))
        self.assertEqual((t['T-007'].section, t['T-007'].scope, t['T-007'].acceptance), ('Needs decision', 'change it', ('it works',)))
        self.assertIn('- Owner decision: 2026-10-20: later', t['T-007'].body)
        self.assertEqual([t[tid].rank for tid in recorded], [1000 * (n + 1) for n in range(len(recorded))])
        g = store.goals
        self.assertEqual((g['G2'].focus, g['G1'].focus, g['G3'].status), (True, False, 'met'))
        self.assertIn('- Evidence: executed: fixture check (pass)', g['G3'].body)
        self.assertEqual(self.migrate().returncode, 1, 'a converted repository is refused')
        # Only the durable conversion belongs in the object database, never its proof.
        self.assertEqual(self.git('fsck', '--unreachable', '--no-reflogs'), '')

    def test_conversion_requires_acceptance_of_tracked_consumers(self):
        (self.repo / 'Makefile').write_text('check:\n\tcat TODO.md\n')
        (self.repo / 'test_queue.py').write_text('open("TODO.md").read()\n')
        (self.repo / 'hook').write_text('cat goals.json\n')
        self.commit()
        objects = self.git('count-objects', '-v')
        dry = self.migrate('--dry-run')
        self.assertEqual(dry.returncode, 0, dry.stderr)
        hits = json.loads(dry.stdout)['consumers']
        self.assertEqual([(h['path'], h['line'], h['names']) for h in hits],
                         [('Makefile', 2, ['TODO.md']), ('hook', 1, ['goals.json']),
                          ('test_queue.py', 1, ['TODO.md'])])
        self.assertEqual(self.git('count-objects', '-v'), objects, 'dry run persists no proof objects')
        refused = self.migrate()
        self.assertEqual(refused.returncode, 1)
        for name in ('Makefile:2', 'test_queue.py:1', 'hook:1', '--accept-consumers'):
            self.assertIn(name, refused.stderr)
        self.assertTrue((self.repo / 'TODO.md').exists())
        self.assertFalse((self.repo / 'tasks').exists())
        staged = self.migrate('--accept-consumers', '--no-commit')
        self.assertEqual(staged.returncode, 0, staged.stderr)
        self.assertEqual(json.loads(staged.stdout)['outcome'], 'STAGED')
        self.assertEqual(self.migrate().returncode, 1, 'resume also requires explicit consumer acceptance')
        accepted = self.migrate('--accept-consumers')
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual(json.loads(accepted.stdout)['consumers'], hits)

    def test_uncommitted_repairs_do_not_hide_retained_consumers(self):
        # Discarded staging must not hide a newer HEAD behind its stale candidate.
        self.assertEqual(self.migrate('--no-commit').returncode, 0)
        self.git('restore', '--source=HEAD', '--staged', '--worktree', '--', '.')
        (self.repo / 'Makefile').write_text('check:\n\tcat TODO.md\n')
        self.commit()
        for repair in ('check:\n\ttrue\n', None):
            with self.subTest(repair=repair):
                if repair is None:
                    (self.repo / 'Makefile').unlink()
                else:
                    (self.repo / 'Makefile').write_text(repair)
                dry = self.migrate('--dry-run')
                self.assertEqual(dry.returncode, 0, dry.stderr)
                self.assertEqual([h['path'] for h in json.loads(dry.stdout)['consumers']], ['Makefile'])
                self.assertIn('Makefile:2', self.migrate().stderr)
        self.commit()
        self.assertEqual(self.migrate().returncode, 0, 'a committed repair is safe')

    def test_resumed_conversion_rechecks_new_consumers(self):
        self.assertEqual(self.migrate('--no-commit').returncode, 0)
        (self.repo / 'Makefile').write_text('check:\n\tcat TODO.md\n')
        self.git('add', 'Makefile')
        head = self.git('rev-parse', 'HEAD')
        checked = subprocess.run([sys.executable, str(COMMAND), 'tasks', 'prepare', str(self.repo), '--check'],
                                 capture_output=True, text=True, timeout=120)
        self.assertEqual(json.loads(checked.stdout)['outcome'], 'MIGRATION_BLOCKED')
        refused = self.migrate()
        self.assertEqual(refused.returncode, 1)
        self.assertIn('Makefile:2', refused.stderr)
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        accepted = self.migrate('--accept-consumers')
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual([h['path'] for h in json.loads(accepted.stdout)['consumers']], ['Makefile'])

    def test_documentation_mentions_do_not_block_conversion(self):
        (self.repo / 'README.md').write_text('See TODO.md and goals.json.\n')
        self.commit()
        result = self.migrate()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['consumers'], [])
        self.assertEqual(report['documentation_drift'],
                         [dict(path='README.md', line=1, names=['TODO.md', 'goals.json'])])

    def test_checklist_and_backlog_survive_with_source_line_numbers(self):
        prefix = '# Product checklist\r\n\r\n- [x] MVP accepted — café\r\nOwner answers: keep\u2028this.\r\n\r\n'
        queue = (self.repo / 'TODO.md').read_text()
        tail = '## Backlog (not ready)\r\n\r\n- Better onboarding\r\n- [ ] Explore export\r\n'
        coverage = '<!-- goals:coverage:begin -->\r\nGenerated table\r\n<!-- goals:coverage:end -->\r\n'
        source = (prefix + queue + tail + coverage).encode()
        (self.repo / 'TODO.md').write_bytes(source)
        self.commit()
        objects = self.git('count-objects', '-v')
        dry = self.migrate('--dry-run')
        self.assertEqual(dry.returncode, 0, dry.stderr)
        kept = json.loads(dry.stdout)['preserved']
        self.assertEqual(kept['path'], 'CHECKLIST.md')
        self.assertIn([1, 4], kept['line_ranges'])
        tail_start = 6 + queue.count('\n')
        self.assertIn([tail_start, tail_start + 3], kept['line_ranges'])
        self.assertEqual(self.git('count-objects', '-v'), objects)
        self.assertFalse((self.repo / 'CHECKLIST.md').exists())
        (self.repo / 'CHECKLIST.md').write_text('existing document\n')
        self.commit()
        refused = self.migrate()
        self.assertEqual(refused.returncode, 1)
        self.assertIn('CHECKLIST.md', refused.stderr)
        self.assertIn('1-4', refused.stderr)
        self.assertEqual((self.repo / 'CHECKLIST.md').read_text(), 'existing document\n')
        (self.repo / 'CHECKLIST.md').unlink()
        self.commit()
        staged = self.migrate('--no-commit')
        self.assertEqual(staged.returncode, 0, staged.stderr)
        self.assertEqual((self.repo / 'CHECKLIST.md').read_bytes(), (prefix + queue + tail + '\r\n' * 3).encode())
        self.assertEqual(self.git('rev-parse', ':CHECKLIST.md'), self.git('hash-object', 'CHECKLIST.md'))
        resumed = self.migrate()
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        self.assertEqual(json.loads(resumed.stdout)['preserved']['path'], 'CHECKLIST.md')
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_task_annotations_and_continuations_are_not_silently_discarded(self):
        original = (self.repo / 'TODO.md').read_text()
        changes = (
            ('- Goal: G2\n', '- Goal: G2\n  <!-- owner evidence: exact  bytes\tremain -->\n'),
            ('- Scope: change it\n', '- Scope: change it\n  and preserve this continuation\n'),
            ('- Acceptance: it works\n', '- Acceptance: it works\r  Owner answers: keep  exact\tbytes\n'),
            ('- Dependencies: None.\n', '- Dependencies: None for this slice; Owner answer: exact\t  evidence\n'),
            ('- Checks: python3 -m unittest\n', '- Checks: python3 -m unittest\n- Verification: test -s report.txt\n'),
        )
        for before, after in changes:
            with self.subTest(annotation=after):
                (self.repo / 'TODO.md').write_text(original.replace(before, after, 1))
                self.commit()
                dry = self.migrate('--dry-run')
                self.assertEqual(dry.returncode, 0, dry.stderr)
                self.assertIn('preserved', json.loads(dry.stdout))
        text = original
        for before, after in changes:
            text = text.replace(before, after, 1)
        (self.repo / 'TODO.md').write_text(text)
        self.commit()
        result = self.migrate()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.repo / 'CHECKLIST.md').read_bytes(), text.encode())
        store = TaskStore.at(self.repo, 'HEAD')
        self.assertEqual(store.tasks['T-002'].scope, 'change it\n  and preserve this continuation')

    def test_migration_refuses_unsafe_states(self):
        common = self.repo / '.git/autowork-execution'
        cases = {
            'uncommitted planning files': lambda: (self.repo / 'TODO.md').write_text(
                (FIXTURE / 'TODO.md').read_text() + '\n'),
            'worker slots in flight': lambda: self.slot('running'),
            'unfinished integration/closure': lambda: self.slot('integrating'),
            'claimed tasks': lambda: self.claim(),
            'already converted': lambda: self.commit_store(),
        }
        for message, make in cases.items():
            with self.subTest(state=message):
                make()
                head = self.git('rev-parse', 'HEAD')
                result = self.migrate('--dry-run')
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn(message.split(' (')[0].split('/')[0], result.stderr)
                self.assertEqual(self.git('rev-parse', 'HEAD'), head)
                self.git('checkout', '-q', '--', '.')
                for leftover in (self.repo / 'tasks', common / 'slots'):
                    if leftover.exists():
                        subprocess.run(['rm', '-rf', str(leftover)], check=True)

    def commit_store(self):
        (self.repo / 'tasks').mkdir()
        (self.repo / 'tasks/notes.md').write_text('a committed tasks/ tree\n')
        self.commit()

    def slot(self, state, **fields):
        folder = self.repo / '.git/autowork-execution/slots'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'T-001.json').write_text(json.dumps({'task_id': 'T-001', 'state': state, 'attempt': 1, **fields}))

    def blocker_slot(self, worker=None):
        """A held slot that only waits for the owner's answer to a worker-reported blocker."""
        dead = {'pid': 2 ** 22 + 7, 'start_ticks': 1, 'boot_id': 'gone'}
        self.slot('held', cause='blocker', reason='worker reported a blocker: allowance spent',
                  worker=worker or dead, held_at=1.0, held_seconds=60.0)

    def test_a_slot_waiting_on_an_owner_answer_is_set_aside(self):
        """2026-10-21: a repository whose runner could not start before conversion had one task
        held on a worker-reported blocker; no supported path released it, so neither could run."""
        self.blocker_slot()
        common = self.repo / '.git/autowork-execution'
        objects = self.git('count-objects', '-v')
        index = (self.repo / '.git/index').read_bytes()
        refs = self.git('show-ref', '--head')
        dry = self.migrate('--dry-run')
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(json.loads(dry.stdout)['would_set_aside'], ['T-001'])
        self.assertEqual(json.loads(dry.stdout)['order'], ['T-004', 'T-001', 'T-003', 'T-005'])
        self.assertEqual(self.git('count-objects', '-v'), objects)
        self.assertEqual((self.repo / '.git/index').read_bytes(), index)
        self.assertEqual(self.git('show-ref', '--head'), refs)
        self.assertTrue((common / 'slots/T-001.json').exists(), 'a dry run sets nothing aside')
        result = self.migrate()
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual((summary['outcome'], summary['set_aside']), ('CONVERTED', ['T-001']))
        self.assertFalse((common / 'slots/T-001.json').exists())
        kept = json.loads((common / 'slot-history/T-001/1/slot.json').read_text())
        self.assertEqual((kept['state'], kept['cause']), ('held', 'blocker'))
        self.assertIn('"slot_set_aside"', (common / 'journal.jsonl').read_text())
        self.assertEqual(TaskStore.at(self.repo, 'HEAD').tasks['T-001'].status, 'open')

    def test_a_numbered_acceptance_over_several_lines_becomes_one_item_per_point(self):
        """2026-10-21: twelve entries of one repository wrote Acceptance as a numbered list, and
        conversion refused each as a line break it could not write."""
        text = (self.repo / 'TODO.md').read_text()
        alpha = text.index('### T-001')
        listed = ('- Acceptance:\n  1. Given a run, the report validates;\n     its hashes match.\n'
                  '  2. Given a tampered file, it is rejected.\n')
        text = text[:alpha] + text[alpha:].replace('- Acceptance: it works\n', listed, 1)
        (self.repo / 'TODO.md').write_text(text)
        self.commit()
        result = self.migrate()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(TaskStore.at(self.repo, 'HEAD').tasks['T-001'].acceptance,
                         ('Given a run, the report validates; its hashes match.', 'Given a tampered file, it is rejected.'))

    def test_other_held_slots_still_refuse(self):
        alive = task_execution.identity(os.getpid())
        for name, make in (('a held finished commit', lambda: self.slot('held', cause='validation', commit='abc')),
                           ('a live worker', lambda: self.blocker_slot(worker=alive))):
            with self.subTest(slot=name):
                make()
                result = self.migrate()
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn('worker slots in flight', result.stderr)
                self.assertTrue((self.repo / 'TODO.md').exists())
                self.assertFalse((self.repo / '.git/autowork-execution/slot-history').exists())

    def claim(self):
        data = json.loads((self.repo / 'goals.json').read_text())
        data['tasks'][0]['status'] = 'in_progress'
        (self.repo / 'goals.json').write_text(json.dumps(data, indent=2))
        self.commit()

    def test_a_placeholder_live_authorization_is_not_a_grant(self):
        text = (self.repo / 'TODO.md').read_text()
        grant = '- Live authorization: granted 2026-10-20 for the staging deploy'
        for value in ('none', 'n/a', 'Pending owner review', 'not yet', 'TBD', 'denied', 'unknown (ask owner)'):
            with self.subTest(value=value):
                (self.repo / 'TODO.md').write_text(text.replace(grant, f'- Live authorization: {value}'))
                self.commit()
                refused = self.migrate('--dry-run')
                self.assertEqual(refused.returncode, 1, refused.stdout)
                self.assertIn(f'T-004: "Live authorization: {value}" is not a grant', refused.stderr)
        (self.repo / 'TODO.md').write_text(text)
        self.commit()
        self.assertEqual(self.migrate().returncode, 0)
        self.assertEqual(TaskStore.at(self.repo, 'HEAD').tasks['T-004'].live.value, 'authorized')

    def test_a_repeated_note_is_kept_and_a_repeated_typed_field_refused(self):
        text = (self.repo / 'TODO.md').read_text()
        alpha = '- Sources: [plan](docs/plan.md)'
        (self.repo / 'TODO.md').write_text(text.replace(alpha, alpha + '\n- Evidence: first run\n- Evidence: second run'))
        self.commit()
        self.assertEqual(self.migrate().returncode, 0)
        body = TaskStore.at(self.repo, 'HEAD').tasks['T-001'].body
        self.assertIn('- Evidence: first run\n- Evidence: second run', body)

    def test_two_entries_for_one_task_refuse(self):
        text = (self.repo / 'TODO.md').read_text()
        (self.repo / 'TODO.md').write_text(text.replace('## Next', entry('T-001', 'Alpha again', 'G1') + '## Next'))
        self.commit()
        refused = self.migrate('--dry-run')
        self.assertEqual(refused.returncode, 1)
        self.assertIn('T-001', refused.stderr)

    def test_a_repeated_typed_field_refuses(self):
        text = (self.repo / 'TODO.md').read_text()
        (self.repo / 'TODO.md').write_text(text.replace('- Touches: src/a.py', '- Touches: src/a.py\n- Touches: src/z.py'))
        self.commit()
        refused = self.migrate('--dry-run')
        self.assertEqual(refused.returncode, 1)
        self.assertIn('T-001: Touches written more than once', refused.stderr)

    def test_migration_refuses_unlossless_input(self):
        dry = self.migrate('--dry-run')
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(json.loads(dry.stdout)['outcome'], 'DRY_RUN')
        self.assertEqual(self.git('status', '--porcelain', '--untracked-files=all'), '')
        self.assertTrue((self.repo / 'TODO.md').exists())
        text = (self.repo / 'TODO.md').read_text()
        (self.repo / 'TODO.md').write_text(text.replace('- Touches: src/a.py', '- Touches: /etc/passwd'))
        self.commit()
        refused = self.migrate()
        self.assertEqual(refused.returncode, 1)
        self.assertIn('T-001: Touches cannot be converted', refused.stderr)
        self.assertFalse((self.repo / 'tasks').exists())


if __name__ == '__main__':
    unittest.main()
