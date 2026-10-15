"""The vendored Beautify GitHub README skill stays byte-exact and correctly adapted."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/beautify-github-readme'
AUDIT = SKILL / 'scripts/audit_readme.py'
SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><title>t</title></svg>'


def audit(readme_text, files=('assets/ok.svg',)):
    """Run the toolset audit on a README inside a throwaway Git-like repository."""
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        (repo / '.git').mkdir()
        for name in files:
            (repo / name).parent.mkdir(parents=True, exist_ok=True)
            (repo / name).write_text(SVG)
        (repo / 'docs').mkdir(exist_ok=True)
        readme = repo / 'docs/README.md'
        readme.write_text(readme_text)
        result = subprocess.run([sys.executable, str(AUDIT), str(readme)], capture_output=True, text=True, timeout=60)
        return result.returncode, result.stdout + result.stderr


class BeautifyReadmeVendorTests(unittest.TestCase):
    def test_pinned_files_match_recorded_hashes_and_license(self):
        manifest = json.loads((SKILL / 'UPSTREAM.json').read_text())
        self.assertEqual(manifest['revision'], 'd6562a5f5c484d069f8560b39c215c9cda4b5a55')
        self.assertEqual(manifest['license'], 'MIT')
        upstream = SKILL / 'upstream'
        on_disk = {p.relative_to(upstream).as_posix() for p in upstream.rglob('*') if p.is_file()}
        self.assertEqual(on_disk, set(manifest['files']), 'unrecorded or missing vendored files')
        for name, digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256((upstream / name).read_bytes()).hexdigest(), digest, name)
        self.assertIn('MIT License', (upstream / 'LICENSE').read_text())

    def test_only_the_adapter_registers_as_a_skill(self):
        self.assertEqual(sorted(p.relative_to(SKILL).as_posix() for p in SKILL.rglob('SKILL.md')), ['SKILL.md'])
        adapter = (SKILL / 'SKILL.md').read_text()
        self.assertIn('name: beautify-github-readme', adapter)
        for rule in ('upstream/PROTOCOL.md', 'Pure SVG by default', 'No unsolicited promotion',
                     'docs.py check', 'audit only unless'):
            self.assertIn(rule, adapter)

    def test_vendored_audit_script_runs(self):
        result = subprocess.run([sys.executable, str(SKILL / 'upstream/scripts/audit_readme.py'), str(ROOT / 'README.md')],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_toolset_audit_passes_this_readme(self):
        result = subprocess.run([sys.executable, str(AUDIT), str(ROOT / 'README.md')],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_toolset_audit_finds_images_the_upstream_audit_misses(self):
        cases = {
            'dark-mode source': '<picture><source media="(prefers-color-scheme: dark)" '
                                'srcset="../assets/gone-dark.svg 1x, ../assets/ok.svg 2x">'
                                '<img src="../assets/ok.svg" alt="logo"></picture>\n',
            'reference image': '![hero][art]\n\n[art]: ../assets/gone.svg "Hero"\n',
            'collapsed reference': '![Art][]\n\n[art]: <../assets/gone.svg>\n',
            'shortcut reference': '![art]\n\n[ART]: ../assets/gone.svg\n',
            'undefined reference': '![hero][nowhere]\n',
            'root-relative': '![hero](/assets/gone.svg)\n',
        }
        for name, text in cases.items():
            with self.subTest(name):
                code, output = audit(text)
                self.assertEqual(code, 1, output)
                self.assertIn('gone' if name != 'undefined reference' else 'nowhere', output)

    def test_toolset_audit_resolves_github_paths(self):
        text = ('![root](/assets/ok.svg)\n\n![spaced](<../assets/my logo.svg>)\n\n'
                '![ref][a]\n\n[a]: /assets/ok.svg\n\n```md\n![example](missing.png)\n```\n'
                '<picture><source srcset="../assets/ok.svg"><img src="../assets/ok.svg" alt="x"></picture>\n')
        code, output = audit(text, files=('assets/ok.svg', 'assets/my logo.svg'))
        self.assertEqual(code, 0, output)
        self.assertIn('Local images checked: 2', output)

    def test_toolset_audit_keeps_upstream_svg_checks(self):
        code, output = audit('![hero](../assets/bad.svg)\n', files=())
        self.assertEqual(code, 1, output)
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / '.git').mkdir()
            (Path(td) / 'bad.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>')
            (Path(td) / 'README.md').write_text('![bad](bad.svg)\n')
            result = subprocess.run([sys.executable, str(AUDIT), str(Path(td) / 'README.md')],
                                    capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 1)
        for issue in ('missing viewBox', 'missing <title>', 'unsupported <script>'):
            self.assertIn(issue, result.stdout)

    def test_adapters_run_the_toolset_audit(self):
        adapter = (SKILL / 'SKILL.md').read_text()
        self.assertIn('<beautify-github-readme-skill-dir>/scripts/audit_readme.py', adapter)
        self.assertNotIn('upstream/scripts/audit_readme.py" /path', adapter)
        portable = (ROOT / 'adapters/skills/beautify-github-readme/SKILL.md').read_text()
        self.assertIn('scripts/audit_readme.py', portable)


if __name__ == '__main__':
    unittest.main()
