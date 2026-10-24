"""Setup readiness checks against controlled native gateway receipts."""
import importlib.util
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch, Mock

from src_fixture import copy_sources

class RuntimeSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.home=self.root/'profiles/sample'
        repo = copy_sources(self.root / 'repo')
        spec=importlib.util.spec_from_file_location('setup_runtime', repo/'setup_runtime.py')
        self.mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(self.mod)
        self.bundle=self.root/'bundle'; (self.bundle/'skills/grill-me').mkdir(parents=True)
        (self.bundle/'skills/grill-me/SKILL.md').write_text('fixture')
        self.report={'missing_plugins':[], 'missing_skills':[], 'unchecked_skill_sources':[],
                     'plugins':[{'name':'autowork','enabled':True,'error':None}],
                     'commands':[{'command':'grill-me','kind':'plugin','source':'autowork'}]}
        self.query=Mock(return_value={'answering_pid':42})
        self.reload=Mock(return_value={'reloaded':True,'home':str(self.home),'adapters_rewired':1,
            'activations':[{'name':'autowork','activated_now':{'gateway_commands':['grill-me']}}]})
        self.pid=Mock(return_value=None)
        modules={'gateway.control_socket':types.SimpleNamespace(query_gateway_control=self.query,reload_gateway_plugins=self.reload),
                 'gateway.status':types.SimpleNamespace(get_running_pid=self.pid)}
        p=patch.dict('sys.modules',modules); p.start(); self.addCleanup(p.stop)

    def finish(self, **kw):
        return self.mod.finish_profile(self.bundle,self.home,self.root,self.report,**kw)

    def test_live_gateway_requires_exact_command_activation_receipt(self):
        report,code=self.finish(); self.assertEqual(code,0,report)
        self.assertEqual(report['gateway'],'commands_reloaded')
        self.reload.assert_called_once()

    def test_settings_left_unhealed_after_load_fail_the_profile(self):
        report,code=self.finish(verify_settings=lambda: ['platforms.telegram.extra.command_menu.priority'])
        self.assertEqual((code,report['status'],report['settings']),(1,'incomplete','drift'))
        self.assertTrue(any('not healed' in e for e in report['errors']), report)
        report,code=self.finish(verify_settings=lambda: [])
        self.assertEqual((code,report['settings']),(0,'current'))

    def test_reload_true_without_registered_command_is_failure(self):
        self.reload.return_value['activations']=[]
        report,code=self.finish(); self.assertEqual(code,1)
        self.assertIn('grill-me',' '.join(report['errors']))

    def test_wrong_home_or_unserved_home_never_claims_success(self):
        for change in ({'home':str(self.root)}, {'reloaded':False,'error':'not served'}):
            self.reload.return_value.update(change)
            self.assertEqual(self.finish()[1],1)

    def test_no_gateway_is_distinct_from_unreachable_live_process(self):
        self.query.return_value=None
        report,code=self.finish(); self.assertEqual(code,0,report)
        self.assertEqual(report['gateway'],'not_running')
        self.pid.return_value=42
        report,code=self.finish(); self.assertEqual(code,1)
        self.assertEqual(report['gateway'],'unreachable')

    def test_partial_source_failure_still_reloads_but_returns_incomplete(self):
        self.report['missing_skills']=['blocked-skill']
        report,code=self.finish(); self.assertEqual(code,1)
        self.assertEqual(report['gateway'],'commands_reloaded')
        self.reload.assert_called_once()

    def test_bundle_only_still_requires_own_skills_but_not_external_sources(self):
        self.report['missing_skills']=['external']
        self.assertEqual(self.finish(bundle_only=True)[1],0)
        self.report['commands']=[]
        self.assertEqual(self.finish(bundle_only=True)[1],1)

    def test_foreign_command_cannot_satisfy_bundle_registration(self):
        self.report['commands']=[{'command':'grill-me','kind':'skill','source':'unrelated'}]
        self.reload.return_value['activations']=[]
        self.assertEqual(self.finish(bundle_only=True)[1],1)

    def test_foreign_gateway_plugin_cannot_satisfy_local_registration(self):
        self.reload.return_value['activations'][0]['name']='foreign'
        self.assertEqual(self.finish()[1],1)

    def test_explicit_no_reload_does_not_contact_gateway(self):
        report,code=self.finish(no_reload=True)
        self.assertEqual(code,0,report); self.assertEqual(report['gateway'],'deferred_by_request')
        self.query.assert_not_called(); self.reload.assert_not_called()


if __name__=='__main__':unittest.main()
