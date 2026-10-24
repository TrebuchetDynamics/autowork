"""The explicit RPC dependency installer must not mutate global Python or services."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]


class InstallTests(unittest.TestCase):
    def test_preview_is_read_only_and_names_exact_hash_pinned_environment(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'state'
            done=subprocess.run([sys.executable,str(ROOT/'scripts/install-pi-rpc.py'),
                                 '--state-root',str(root),'--dry-run'],capture_output=True,text=True)
            self.assertEqual(done.returncode,0,done.stderr)
            self.assertIn('pi-rpc-0.2.6',done.stdout)
            self.assertIn('--require-hashes',done.stdout)
            self.assertFalse(root.exists())

    def test_autowork_install_plan_includes_pinned_runtime(self):
        done=subprocess.run([sys.executable,str(ROOT/'scripts/install_menu.py'),
                             '--only','autowork','--dry-run'],capture_output=True,text=True)
        self.assertEqual(done.returncode,0,done.stderr)
        self.assertIn('install-pi-rpc.py',done.stdout)

    def test_venv_is_built_at_its_final_path_not_relocated(self):
        spec=importlib.util.spec_from_file_location('rpc_installer',ROOT/'scripts/install-pi-rpc.py')
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            target=Path(temporary)/'runtimes/pi-rpc-0.2.6'
            with patch.object(module.sys,'argv',['installer','--state-root',temporary]), \
                    patch.object(module.venv,'EnvBuilder') as builder, \
                    patch.object(module.subprocess,'run',return_value=SimpleNamespace(stdout='0.2.6')):
                builder.return_value.create.side_effect=lambda p: Path(p).mkdir(parents=True,exist_ok=True)
                self.assertEqual(module.main(),0)
                builder.return_value.create.assert_called_once_with(target)

    def test_unrelated_status_import_does_not_require_sdk(self):
        done=subprocess.run([sys.executable,'-S','-c',
                             'from pi_autowork import pi_runtime; print(pi_runtime.Settings("/unused").transport)'],
                            cwd=ROOT/'pi-autowork',capture_output=True,text=True)
        self.assertEqual(done.returncode,0,done.stderr)
        self.assertEqual(done.stdout.strip(),'rpc')


if __name__=='__main__': unittest.main()
