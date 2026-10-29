"""APK ABI verification against disposable ZIP fixtures, not real Android builds."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / 'skills/apk-get/scripts/verify_apk.py'


class ApkGetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.apk = Path(self.temp.name) / 'release with spaces.apk'

    def archive(self, names):
        with zipfile.ZipFile(self.apk, 'w') as archive:
            for name in names:
                archive.writestr(name, b'fixture')

    def verify(self):
        return subprocess.run([sys.executable, str(VERIFY), str(self.apk)],
                              capture_output=True, text=True, timeout=10)

    def test_arm64_apk_reports_evidence_without_changing_the_artifact(self):
        self.archive(['AndroidManifest.xml', 'lib/arm64-v8a/libapp.so', 'lib/arm64-v8a/libflutter.so'])
        before = self.apk.read_bytes()
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence['abis'], ['arm64-v8a'])
        self.assertEqual(evidence['path'], str(self.apk.resolve()))
        self.assertEqual(evidence['bytes'], len(before))
        self.assertEqual(evidence['sha256'], hashlib.sha256(before).hexdigest())
        self.assertEqual(self.apk.read_bytes(), before)
        self.assertEqual(evidence['checks'], ['apk-structure', 'native-abis'])
        self.assertNotIn('release', evidence)
        self.assertNotIn('signed', evidence)

    def test_other_abis_are_rejected_even_when_arm64_is_present(self):
        for abi in ('armeabi-v7a', 'x86', 'x86_64'):
            with self.subTest(abi=abi):
                self.archive(['AndroidManifest.xml', 'lib/arm64-v8a/libapp.so', f'lib/{abi}/libapp.so'])
                result = self.verify()
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn('ARM64-only', result.stderr)
                self.assertEqual(result.stdout, '')

    def test_missing_arm64_native_libraries_are_rejected(self):
        for names in (['AndroidManifest.xml'], ['AndroidManifest.xml', 'lib/x86_64/libapp.so']):
            with self.subTest(names=names):
                self.archive(names)
                result = self.verify()
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn('ARM64-only', result.stderr)

    def test_a_bundle_or_arbitrary_zip_is_not_an_apk(self):
        self.archive(['base/manifest/AndroidManifest.xml', 'lib/arm64-v8a/libapp.so'])
        result = self.verify()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn('AndroidManifest.xml', result.stderr)

    def test_missing_and_corrupt_artifacts_fail_without_success_output(self):
        for contents in (None, b'not an APK'):
            with self.subTest(contents=contents):
                if contents is not None:
                    self.apk.write_bytes(contents)
                result = self.verify()
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertTrue(result.stderr.strip())
                self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
