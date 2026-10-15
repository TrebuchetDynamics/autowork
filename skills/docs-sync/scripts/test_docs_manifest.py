"""Document role manifest checks through the actual docs.py CLI."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('docs.py')
BASELINE = ('readme', 'prd', 'architecture', 'spec', 'test-plan', 'runbook', 'changelog')


class DocsManifestTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        (self.repo / 'docs').mkdir()
        (self.repo / 'scripts').mkdir()
        (self.repo / 'scripts' / 'check.py').write_text('')
        (self.repo / 'README.md').write_text(
            '# Tool\n\nRun `python3 scripts/check.py`. See [design](docs/design.md#data-flow)\n'
            'and [tests](#tests).\n\n## Tests\n\n```sh\npython3 scripts/fenced-only.py [x](missing.md)\n```\n')
        (self.repo / 'docs' / 'design.md').write_text(
            '# Design\n\n## Current — map\n\n## Data flow\n\nBack to [readme](../README.md).\n')
        (self.repo / 'CHANGELOG.md').write_text('# Changelog\n')
        self.roles = {
            'readme': {'status': 'maintained', 'path': 'README.md', 'covers': ['scripts'],
                       'verified_at': 'fb2798f'},
            'prd': {'status': 'not_applicable', 'reason': 'Internal tool without product scope.'},
            'architecture': {'status': 'maintained', 'path': 'docs/design.md#current--map'},
            'spec': {'status': 'created', 'path': 'docs/design.md#data-flow'},
            'test-plan': {'status': 'unchanged_verified', 'path': 'README.md#tests'},
            'runbook': {'status': 'conditional_not_applicable', 'reason': 'No deployed service.'},
            'changelog': {'status': 'maintained', 'path': 'CHANGELOG.md'},
        }
        self.write()

    def write(self, data=None):
        data = data if data is not None else {'version': 1, 'roles': self.roles}
        (self.repo / 'docs' / 'roles.json').write_text(json.dumps(data))

    def cli(self, command, *args, expected=0):
        result = subprocess.run([sys.executable, str(SCRIPT), command, str(self.repo), *args],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        return result.stdout + result.stderr

    def test_valid_manifest_passes_validate_and_check_without_writing(self):
        before = {p: p.read_bytes() for p in self.repo.rglob('*') if p.is_file()}
        self.assertEqual(self.cli('validate').strip(), 'ok')
        self.assertEqual(self.cli('check').strip(), 'ok')
        self.assertEqual(before, {p: p.read_bytes() for p in self.repo.rglob('*') if p.is_file()})

    def test_missing_manifest_keeps_current_behavior(self):
        (self.repo / 'docs' / 'roles.json').unlink()
        self.assertIn('no manifest', self.cli('check'))
        self.assertIn('no manifest', self.cli('validate'))

    def test_broken_link_and_anchor_name_role_and_path(self):
        (self.repo / 'CHANGELOG.md').write_text(
            '# Changelog\n\n[gone](docs/missing.md) [bad](docs/design.md#nowhere) '
            '[self](#absent) [web](https://example.invalid/x) [mail](mailto:a@b.c)\n')
        out = self.cli('check', expected=1)
        self.assertIn('changelog: CHANGELOG.md: broken link docs/missing.md', out)
        self.assertIn('changelog: CHANGELOG.md: missing anchor docs/design.md#nowhere', out)
        self.assertIn('changelog: CHANGELOG.md: missing anchor #absent', out)
        self.assertNotIn('example.invalid', out)
        self.assertNotIn('mailto', out)

    def test_mapped_path_and_anchor_must_exist(self):
        self.roles['spec']['path'] = 'docs/spec.md'
        self.roles['architecture']['path'] = 'docs/design.md#missing-section'
        self.write()
        out = self.cli('check', expected=1)
        self.assertIn('spec: docs/spec.md: mapped document does not exist', out)
        self.assertIn('architecture: docs/design.md#missing-section: missing anchor', out)

    def test_documented_script_path_must_exist(self):
        (self.repo / 'README.md').write_text('# Tool\n\nRun `python3 scripts/gone.py --x` and '
                                             '`sh scripts/check.py` and `python3 /abs/tool.py`.\n\n## Tests\n')
        out = self.cli('check', expected=1)
        self.assertIn('readme: README.md: documented script scripts/gone.py does not exist', out)
        self.assertNotIn('scripts/check.py', out)
        self.assertNotIn('/abs/tool.py', out)

    def test_unmapped_baseline_role_fails(self):
        del self.roles['runbook']
        self.write()
        out = self.cli('check', expected=1)
        self.assertIn('runbook: baseline role is neither mapped nor recorded as not applicable', out)
        self.assertEqual(self.cli('validate').strip(), 'ok')

    def test_covered_paths_must_exist(self):
        self.roles['readme']['covers'] = ['src/absent']
        self.write()
        self.assertIn('readme: covered path src/absent does not exist', self.cli('check', expected=1))

    def test_malformed_entries_name_the_role(self):
        cases = [
            ({'status': 'done', 'path': 'README.md'}, 'unknown status'),
            ({'status': 'maintained'}, 'path is required'),
            ({'status': 'not_applicable'}, 'reason is required'),
            ({'status': 'not_applicable', 'reason': 'x', 'path': 'README.md'}, 'must not map a path'),
            ({'status': 'maintained', 'path': '../outside.md'}, 'must stay inside the repository'),
            ({'status': 'maintained', 'path': '/etc/passwd'}, 'must stay inside the repository'),
            ({'status': 'maintained', 'path': 'README.md', 'covers': 'src'}, 'covers must be a list'),
            ({'status': 'maintained', 'path': 'README.md', 'verified_at': 'HEAD~1'}, 'verified_at'),
            ({'status': 'maintained', 'path': 'README.md', 'owner': 'x'}, 'unknown field owner'),
            ('README.md', 'must be an object'),
        ]
        for entry, message in cases:
            with self.subTest(message=message):
                self.roles['readme'] = entry
                self.write()
                out = self.cli('validate', expected=1)
                self.assertIn('readme:', out)
                self.assertIn(message, out)

    def test_malformed_manifest_shapes_fail_cleanly(self):
        for data, message in (([], 'object'), ({'version': 2, 'roles': {}}, 'version'),
                              ({'version': 1, 'roles': []}, 'roles')):
            with self.subTest(message=message):
                self.write(data)
                self.assertIn(message, self.cli('validate', expected=1))
        (self.repo / 'docs' / 'roles.json').write_text('{bad json')
        self.assertIn('invalid JSON', self.cli('validate', expected=1))

    @unittest.skipUnless(hasattr(os, 'symlink'), 'symlinks unavailable')
    def test_symlinked_manifest_and_documents_are_refused(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        target = Path(outside.name) / 'secret.md'
        target.write_text('# Secret\n')
        (self.repo / 'docs' / 'linked.md').symlink_to(target)
        self.roles['spec']['path'] = 'docs/linked.md'
        self.write()
        self.assertIn('spec: docs/linked.md: refusing symlinked path', self.cli('check', expected=1))
        manifest = self.repo / 'docs' / 'roles.json'
        real = Path(outside.name) / 'roles.json'
        real.write_bytes(manifest.read_bytes())
        manifest.unlink()
        manifest.symlink_to(real)
        self.assertIn('refusing symlinked manifest', self.cli('validate', expected=1))

    def test_review_edge_cases_fail_cleanly_or_pass(self):
        (self.repo / 'docs' / 'design.md').write_text(
            '# Design\n\n## Current — map\n\n## Data flow\n\n## See [API](design.md) `notes`\n\n'
            '<a id="custom-anchor"></a>\n\nBack to [readme](../README.md).\n')
        (self.repo / 'CHANGELOG.md').write_text(
            '# Changelog\n\n[linked](docs/design.md#see-api-notes) [html](docs/design.md#custom-anchor)\n')
        self.assertEqual(self.cli('check').strip(), 'ok')
        self.roles['spec']['path'] = 'docs'
        self.write()
        self.assertIn('spec: docs: mapped document is not a file', self.cli('check', expected=1))
        self.write({'version': True, 'roles': {}})
        self.assertIn('version', self.cli('validate', expected=1))
        (self.repo / 'docs' / 'roles.json').unlink()
        (self.repo / 'docs' / 'roles.json').mkdir()
        self.assertIn('manifest: cannot read', self.cli('validate', expected=1))

    def test_absolute_links_resolve_from_repository_root_never_outside(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        secret = Path(outside.name) / 'outside.md'
        secret.write_text('# Real\n')
        (self.repo / 'CHANGELOG.md').write_text(
            f'# Changelog\n\n[root](/docs/design.md#data-flow) [dir](/scripts) '
            f'[escape]({secret}#real) [up](../../outside.md)\n')
        out = self.cli('check', expected=1)
        self.assertNotIn('/docs/design.md', out)
        self.assertNotIn('/scripts', out)
        self.assertIn(f'broken link {secret}#real', out)
        self.assertIn('broken link ../../outside.md', out)

    def test_review_markdown_forms_do_not_false_positive(self):
        (self.repo / 'scripts' / 'sub').mkdir()
        (self.repo / 'scripts' / 'sub' / 'tool.py').write_text('')
        (self.repo / 'CHANGELOG.md').write_text(
            '# Changelog\n\n## my_var option\n\nSetext Only\n===========\n\nText\n\n---\n\n'
            '[u](#my_var-option) [s](#setext-only) [q](README.md?plain=1#tests)\n'
            'Run `cd scripts/sub && python3 tool.py` and `cd $HOME && python3 x.py`.\n\n'
            '````md\n```\n[nested](gone.md)\n```\n````\n')
        self.assertEqual(self.cli('check').strip(), 'ok')

    def test_reference_links_and_unclosed_fences(self):
        (self.repo / 'CHANGELOG.md').write_text(
            '# Changelog\n\n[ref]: docs/missing-ref.md\n\n```sh\n[x](zz.md)\n')
        out = self.cli('check', expected=1)
        self.assertIn('broken link docs/missing-ref.md', out)
        self.assertNotIn('zz.md', out)

    def test_overlong_paths_report_instead_of_crashing(self):
        long = 'b' * 300
        (self.repo / 'CHANGELOG.md').write_text(f'# Changelog\n\n[x]({long}.md)\n')
        self.roles['readme']['covers'] = [long]
        self.write()
        out = self.cli('check', expected=1)
        self.assertIn('broken link', out)
        self.assertIn('cannot be inspected', out)

    def test_escaping_entry_paths_are_named_and_missing_repo_fails(self):
        self.roles['readme'] = {'status': 'maintained', 'path': '../x.md', 'covers': ['/etc']}
        self.write()
        out = self.cli('validate', expected=1)
        self.assertIn("readme: path '../x.md' must stay inside", out)
        self.assertIn("readme: covered path '/etc' must stay inside", out)
        result = subprocess.run([sys.executable, str(SCRIPT), 'check', str(self.repo / 'absent')],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn('is not a directory', result.stdout)

    def test_custom_manifest_location(self):
        (self.repo / 'docs' / 'roles.json').rename(self.repo / 'doc-roles.json')
        self.assertEqual(self.cli('check', '--manifest', 'doc-roles.json').strip(), 'ok')


if __name__ == '__main__':
    unittest.main()
