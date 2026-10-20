"""Unit tests for plan_lint.py and `goals.py plan-lint` (no network, no LLM)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import plan_lint  # noqa: E402

GOALS = HERE / 'goals.py'

FILES = {
    'src/a.py': 'a = 1\n',
    'src/b.py': 'b = 1\n',
    'src/c.py': 'c = 1\n',
    'tests/__init__.py': '',
    'tests/test_a.py': 'import unittest\n',
    'tests/test_b.py': 'import unittest\n',
    'web/app.test.js': '',
    'scripts/check.py': '',
}


def task(tid, *, touches='src/a.py, tests/test_a.py', scope='Change the thing.',
         acceptance='`test_a` covers the change.',
         checks='python3 -m unittest discover -s tests -p test_a.py', deps='None.', extra=''):
    lines = [f'- [ ] {tid} — Title of {tid}', '- Status: open']
    if touches is not None:
        lines.append(f'- Touches: {touches}')
    if scope is not None:
        lines.append(f'- Scope: {scope}')
    if acceptance is not None:
        lines.append(f'- Acceptance: {acceptance}')
    if checks is not None:
        lines.append(f'- Checks: {checks}')
    if deps is not None:
        lines.append(f'- Dependencies: {deps}')
    if extra:
        lines.append(extra)
    return '\n'.join(lines) + '\n\n'


def make_repo(folder, now='', nxt='', decision='', files=None):
    repo = Path(folder)
    for name, text in {**FILES, **(files or {})}.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    (repo / 'TODO.md').write_text('# Work queue\n\n## Now\n\n' + now + '## Next\n\n' + nxt
                                  + '## Needs decision\n\n' + decision)
    return repo


def codes(result, kind='errors'):
    return sorted({f['code'] for f in result[kind]})


def findings(result, code, kind='errors'):
    return [f for f in result[kind] if f['code'] == code]


class CleanTests(unittest.TestCase):
    def test_clean_plan_has_no_findings(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = make_repo(folder, now=task('T-1'),
                             nxt=task('T-2', touches='src/b.py, tests/test_b.py',
                                      acceptance='`test_b` passes.',
                                      checks='python3 -m unittest discover -s tests -p test_b.py'))
            result = plan_lint.lint(repo)
            self.assertEqual(result, {'errors': [], 'warnings': []})

    def test_cli_clean_exit_zero_and_json_shape(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = make_repo(folder, now=task('T-1'))
            out = subprocess.run([sys.executable, str(GOALS), 'plan-lint', str(repo), '--json'],
                                 capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(json.loads(out.stdout), {'errors': [], 'warnings': []})


class ErrorTests(unittest.TestCase):
    def lint(self, **kwargs):
        with tempfile.TemporaryDirectory() as folder:
            return plan_lint.lint(make_repo(folder, **kwargs))

    def test_missing_required_fields(self):
        result = self.lint(now=task('T-1', scope=None) + task('T-2', acceptance=None)
                           + task('T-3', checks=None))
        missing = findings(result, 'missing-field')
        self.assertEqual(sorted(f['task'] for f in missing), ['T-1', 'T-2', 'T-3'])
        self.assertIn('Scope', missing[0]['message'])

    def test_verification_is_an_accepted_checks_spelling(self):
        body = task('T-1', checks=None, extra='- Verification: python3 -m unittest discover -s tests -p test_a.py')
        self.assertEqual(self.lint(now=body)['errors'], [])

    def test_duplicate_field(self):
        result = self.lint(now=task('T-1', extra='- Scope: again.'))
        self.assertEqual(codes(result), ['duplicate-field'])
        self.assertIn('Scope', result['errors'][0]['message'])

    def test_checks_and_verification_together_are_duplicate(self):
        result = self.lint(now=task('T-1', extra='- Verification: python3 scripts/check.py'))
        self.assertEqual(codes(result), ['duplicate-field'])

    def test_missing_touches(self):
        result = self.lint(now=task('T-1', touches=None))
        self.assertEqual(codes(result), ['missing-touches'])
        self.assertIn('Touches:', result['errors'][0]['message'])

    def test_exclusive_with_reason_needs_no_touches(self):
        body = task('T-1', touches=None, extra='- Resources: exclusive — rewrites the whole tree.')
        self.assertEqual(self.lint(now=body)['errors'], [])

    def test_bare_exclusive_still_needs_touches(self):
        body = task('T-1', touches=None, extra='- Resources: exclusive')
        self.assertEqual(codes(self.lint(now=body)), ['missing-touches'])

    def test_unparseable_touches(self):
        body = task('T-1', touches='whatever the worker needs to change here')
        self.assertEqual(codes(self.lint(now=body)), ['invalid-touches'])
        body = task('T-2', touches='../outside.py')
        self.assertEqual(codes(self.lint(now=body)), ['invalid-touches'])

    def test_coordinator_file_in_touches(self):
        for name in ('TODO.md', 'TODO.archive.md', 'goals.json', 'BLOCKERS.md', 'CHANGELOG.md'):
            result = self.lint(now=task('T-1', touches=f'src/a.py, {name}'))
            self.assertEqual(codes(result), ['coordinator-touches'], name)
            self.assertIn(name, result['errors'][0]['message'])

    def test_unknown_dependency(self):
        result = self.lint(now=task('T-1', deps='TASK-404.'))
        self.assertEqual(codes(result), ['unknown-dependency'])
        self.assertIn('TASK-404', result['errors'][0]['message'])

    def test_dependency_on_archived_task_is_known(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = make_repo(folder, now=task('T-1', deps='TASK-9.'))
            (repo / 'TODO.archive.md').write_text('# Completed tasks\n\n## Done\n\n- [x] TASK-9 — Old\n')
            self.assertEqual(plan_lint.lint(repo)['errors'], [])

    def test_outside_condition_dependency_is_not_an_id(self):
        self.assertEqual(self.lint(now=task('T-1', deps='approved device access.'))['errors'], [])

    def test_dependency_cycle(self):
        result = self.lint(now=task('T-1', deps='T-2.') + task('T-2', touches='src/b.py', deps='T-1.'))
        self.assertIn('dependency-cycle', codes(result))
        message = findings(result, 'dependency-cycle')[0]['message']
        self.assertIn('T-1', message)
        self.assertIn('T-2', message)

    def test_missing_check_target(self):
        result = self.lint(now=task('T-1', checks='python3 -m unittest discover -s tests -p test_nope.py'))
        self.assertEqual(codes(result), ['missing-check-target'])
        self.assertIn('test_nope.py', result['errors'][0]['message'])

    def test_check_target_created_by_touches_is_allowed(self):
        body = task('T-1', touches='src/a.py, tests/test_new.py',
                    checks='python3 -m unittest discover -s tests -p test_new.py')
        self.assertEqual(self.lint(now=body)['errors'], [])

    def test_duplicate_task_id(self):
        result = self.lint(now=task('T-1'), nxt=task('T-1'))
        self.assertIn('duplicate-task', codes(result))

    def test_closed_and_decision_tasks_are_not_scoped(self):
        closed = task('T-1', scope=None).replace('- [ ]', '- [x]')
        held = task('T-2', scope=None)
        self.assertEqual(self.lint(now=closed, decision=held)['errors'], [])


class WarningTests(unittest.TestCase):
    def lint(self, **kwargs):
        with tempfile.TemporaryDirectory() as folder:
            return plan_lint.lint(make_repo(folder, **kwargs))

    def test_overlap_without_dependency(self):
        result = self.lint(now=task('T-1') + task('T-2', touches='src/a.py, src/b.py'))
        found = findings(result, 'touches-overlap', 'warnings')
        # One line per (scoped task, shared path): each side names the other.
        self.assertEqual([(f['task'], f['others']) for f in found], [('T-1', ['T-2']), ('T-2', ['T-1'])])
        self.assertIn('src/a.py', found[1]['message'])
        self.assertIn('Dependencies: T-1', found[1]['message'])
        self.assertEqual(result['errors'], [])

    def test_overlap_groups_others_per_path(self):
        others = ''.join(task(f'T-{n}', touches='src/a.py') for n in range(2, 10))
        result = self.lint(now=task('T-1', touches='src/a.py, src/b.py') + others)
        found = [f for f in findings(result, 'touches-overlap', 'warnings') if f['task'] == 'T-1']
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['others'], [f'T-{n}' for n in range(2, 10)])
        message = found[0]['message']
        self.assertIn('hot file src/a.py (named by 9 open tasks) is also in Touches of 8 independent open tasks', message)
        self.assertIn('T-2, T-3, T-4, T-5, T-6, +3', message)
        self.assertNotIn('T-7', message)

    def test_hot_overlap_is_one_line(self):
        result = self.lint(now=task('T-1', touches='src/a.py') + task('T-2', touches='src/a.py')
                           + task('T-3', touches='src/a.py'))
        self.assertEqual(findings(result, 'hot-file', 'warnings'), [])
        found = [f for f in findings(result, 'touches-overlap', 'warnings') if f['task'] == 'T-1']
        self.assertEqual(len(found), 1)
        self.assertIn('hot file src/a.py (named by 3 open tasks)', found[0]['message'])

    def test_overlap_with_transitive_dependency_is_fine(self):
        result = self.lint(now=task('T-1') + task('T-2', touches='src/b.py', deps='T-1.')
                           + task('T-3', touches='src/a.py', deps='T-2.'))
        self.assertEqual(findings(result, 'touches-overlap', 'warnings'), [])

    def test_hot_file_named_by_three_tasks(self):
        result = self.lint(now=task('T-1', touches='src/a.py') + task('T-2', touches='src/a.py', deps='T-1.')
                           + task('T-3', touches='src/a.py', deps='T-2.'))
        found = findings(result, 'hot-file', 'warnings')
        self.assertTrue(found)
        self.assertIn('src/a.py', found[0]['message'])

    def test_hot_file_by_length(self):
        result = self.lint(now=task('T-1', touches='src/big.py'), files={'src/big.py': 'x = 1\n' * 1600})
        self.assertIn('hot-file', codes(result, 'warnings'))

    def test_directory_in_touches(self):
        result = self.lint(now=task('T-1', touches='src/'))
        self.assertIn('directory-touches', codes(result, 'warnings'))
        result = self.lint(now=task('T-2', touches='src'))
        self.assertIn('directory-touches', codes(result, 'warnings'))

    def test_serial_path(self):
        result = self.lint(now=task('T-1', touches='src/a.py, package.json'))
        self.assertIn('serial-path', codes(result, 'warnings'))
        self.assertEqual(result['errors'], [])

    def test_wide_task(self):
        result = self.lint(now=task('T-1', touches='src/a.py, src/b.py, src/c.py, tests/test_a.py, '
                                    'tests/test_b.py, web/app.test.js'))
        self.assertIn('too-many-touches', codes(result, 'warnings'))
        result = self.lint(now=task('T-2', acceptance='(1) `test_a` one; (2) two; (3) three; (4) four.'))
        self.assertIn('too-many-acceptance', codes(result, 'warnings'))

    def test_acceptance_names_no_test(self):
        result = self.lint(now=task('T-1', acceptance='It works well.'))
        self.assertEqual(codes(result, 'warnings'), ['acceptance-no-test'])
        result = self.lint(now=task('T-2', acceptance='tests/test_a.py::test_one passes.'))
        self.assertEqual(result['warnings'], [])

    def test_long_body(self):
        result = self.lint(now=task('T-1', extra='- Notes: ' + 'word ' * 1300))
        self.assertIn('long-body', codes(result, 'warnings'))

    def test_strict_turns_warnings_into_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = make_repo(folder, now=task('T-1', acceptance='It works.'))
            plain = subprocess.run([sys.executable, str(GOALS), 'plan-lint', str(repo)], capture_output=True, text=True)
            strict = subprocess.run([sys.executable, str(GOALS), 'plan-lint', str(repo), '--strict'],
                                    capture_output=True, text=True)
            self.assertEqual(plain.returncode, 0, plain.stderr)
            self.assertEqual(strict.returncode, 1)
            self.assertEqual(len(plain.stdout.strip().splitlines()), 1)
            self.assertIn('acceptance-no-test', plain.stdout)


class DegradedTests(unittest.TestCase):
    def test_without_engine_the_lint_still_runs_and_says_so(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder, patch.object(plan_lint, 'engine', return_value=None):
            repo = make_repo(folder, now=task('T-1', scope=None))
            result = plan_lint.lint(repo)
            self.assertEqual(codes(result), ['missing-field'])
            self.assertEqual(codes(result, 'warnings'), ['engine-unavailable'])


class ScopeTests(unittest.TestCase):
    def test_tasks_option_limits_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = make_repo(folder, now=task('T-1', scope=None) + task('T-2', touches='src/b.py'))
            self.assertEqual(plan_lint.lint(repo, ['T-2'])['errors'], [])
            self.assertEqual(codes(plan_lint.lint(repo, ['T-1'])), ['missing-field'])

    def test_tasks_option_reaches_decision_tasks_and_overlap_context(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = make_repo(folder, now=task('T-1'), decision=task('T-2', touches='src/b.py', scope=None))
            self.assertEqual(codes(plan_lint.lint(repo, ['T-2'])), ['missing-field'])
            # T-3 overlaps out-of-scope T-1: still reported, because all open tasks are context.
            repo = make_repo(folder, now=task('T-1') + task('T-3'))
            found = findings(plan_lint.lint(repo, ['T-3']), 'touches-overlap', 'warnings')
            self.assertEqual({f['task'] for f in found}, {'T-3'})

    def test_unknown_requested_task(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = make_repo(folder, now=task('T-1'))
            self.assertEqual(codes(plan_lint.lint(repo, ['T-9'])), ['unknown-task'])

    def test_cli_tasks_and_json_error_exit(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = make_repo(folder, now=task('T-1', scope=None) + task('T-2', touches='src/b.py'))
            out = subprocess.run([sys.executable, str(GOALS), 'plan-lint', str(repo), '--tasks', 'T-1,T-2',
                                  '--json'], capture_output=True, text=True)
            self.assertEqual(out.returncode, 1)
            report = json.loads(out.stdout)
            self.assertEqual(set(report), {'errors', 'warnings'})
            self.assertEqual(set(report['errors'][0]), {'task', 'code', 'message'})
            self.assertEqual(report['errors'][0]['task'], 'T-1')


class CheckTargetTests(unittest.TestCase):
    def missing(self, checks, touches=()):
        with tempfile.TemporaryDirectory() as folder:
            repo = make_repo(folder, files={'pkg/__init__.py': '', 'pkg/test_mod.py': '',
                                            'tests/test_suite/__init__.py': ''})
            return plan_lint.missing_check_targets(repo, checks, list(touches))

    def test_discover_forms(self):
        self.assertEqual(self.missing('python3 -m unittest discover -s tests -p test_a.py'), [])
        self.assertEqual(self.missing("python3 -m unittest discover -s tests -p 'test_*.py'"), [])
        self.assertEqual(self.missing('python3 -m unittest discover -s tests'), [])
        self.assertEqual(self.missing('python3 -m unittest discover tests test_b.py'), [])
        self.assertEqual(len(self.missing('python3 -m unittest discover -s tests -p test_zz.py')), 1)
        self.assertEqual(len(self.missing('python3 -m unittest discover -s nowhere')), 1)
        self.assertEqual(len(self.missing("python3 -m unittest discover -s tests -p 'test_q*.py'")), 1)

    def test_module_forms(self):
        self.assertEqual(self.missing('python3 -m unittest tests.test_a'), [])
        self.assertEqual(self.missing('python3 -m unittest tests.test_a.Case.test_one -v'), [])
        self.assertEqual(self.missing('python3 -m unittest pkg.test_mod tests.test_suite'), [])
        self.assertEqual(self.missing('python3 -m unittest tests/test_a.py'), [])
        self.assertEqual(len(self.missing('python3 -m unittest tests.test_gone')), 1)
        self.assertEqual(len(self.missing('python3 -m unittest tests/test_gone.py')), 1)
        # An installed or stdlib module the repository does not hold is not judged.
        self.assertEqual(self.missing('python3 -m unittest json.tests'), [])

    def test_script_forms(self):
        self.assertEqual(self.missing('python3 scripts/check.py tests/test_a.py'), [])
        self.assertEqual(self.missing('python3 scripts/check.py with TMPDIR set to a fresh directory'), [])
        self.assertEqual(len(self.missing('python3 scripts/nope.py')), 1)
        self.assertEqual(len(self.missing('python3 scripts/check.py tests/test_gone.py')), 1)

    def test_node_and_pytest_forms(self):
        self.assertEqual(self.missing('node --test web/app.test.js'), [])
        self.assertEqual(len(self.missing('node --test web/gone.test.js')), 1)
        self.assertEqual(self.missing('pytest tests/test_a.py::test_one -q'), [])
        self.assertEqual(self.missing('python3 -m pytest tests/test_a.py::Case::test_one'), [])
        self.assertEqual(len(self.missing('pytest tests/test_gone.py::test_one')), 1)

    def test_separators_quotes_and_prose(self):
        checks = ('`python3 -m unittest tests/test_a.py` (34 pass); engine tests in `skills/x`; '
                  'python3 -m unittest tests.test_a && python3 -m unittest tests.test_gone; git diff --check')
        self.assertEqual(len(self.missing(checks)), 1)
        self.assertEqual(self.missing('Planned after implementation: python3 scripts/check.py tests/test_a.py.'), [])
        self.assertEqual(self.missing('run python3 -m unittest discover -s tests -p test_a.py, bash -n x.sh'), [])

    def test_unparseable_commands_are_ignored(self):
        self.assertEqual(self.missing("python3 -c 'import x'; cd sub && python3 -m unittest tests.test_gone; "
                                      'python3 -m unittest discover -s "unterminated'), [])

    def test_touches_create_target(self):
        self.assertEqual(self.missing('python3 -m unittest tests.test_new', ['tests/test_new.py']), [])
        self.assertEqual(self.missing('node --test web/new.test.js', ['web/']), [])
        self.assertEqual(self.missing('python3 -m unittest discover -s newdir -p test_x.py',
                                      ['newdir/test_x.py']), [])


if __name__ == '__main__':
    unittest.main()
