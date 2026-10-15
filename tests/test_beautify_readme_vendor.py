"""The vendored Beautify GitHub README skill stays byte-exact and correctly adapted."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/beautify-github-readme'


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


if __name__ == '__main__':
    unittest.main()
