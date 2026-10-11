"""Public shell entry points route to the same complete setup implementation."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class InstallTests(unittest.TestCase):
    def test_both_entrypoints_forward_all_flags_and_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)/'repo with spaces';repo.mkdir()
            (repo/'setup_bundle.py').write_text(
                'import sys,json; print(json.dumps(sys.argv[1:])); sys.exit(7)')
            for name in ('install.sh','install-plugins.sh'):
                shutil.copy2(ROOT/name,repo/name)
                result=subprocess.run(['bash',str(repo/name),'--hermes-home','/tmp/home with spaces',
                                       '--yes-deps','--dry-run'],cwd=tmp,capture_output=True,text=True)
                self.assertEqual(result.returncode,7,result.stderr)
                self.assertIn('"/tmp/home with spaces"',result.stdout)
                self.assertIn('"--yes-deps"',result.stdout)

if __name__=='__main__':unittest.main()
