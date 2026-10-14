import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('menu_policy',Path(__file__).resolve().parents[1]/'telegram_menu_policy.py')
policy=importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)
WORKFLOWS=['plan_with_me', 'plan_for_me', 'docs_sync', 'autowork']

def priority(raw):
    return policy.menu_patch(raw)['platforms']['telegram']['extra']['command_menu']

class MenuPolicyTests(unittest.TestCase):
    def test_only_current_workflow_commands_get_priority_without_changing_cap(self):
        menu=priority({})
        self.assertEqual(menu['priority'], WORKFLOWS)
        self.assertNotIn('max_commands',menu)
    def test_stale_compatibility_entries_are_removed_and_user_choices_kept(self):
        old=['autoresearch','autoresearch_plan','autoresearch_debug','autoresearch-fix','status','custom',
             'autowork','plan_with_me','grill_me','repo_interview','repo_docs','autogoal']
        raw={'platforms':{'telegram':{'extra':{'command_menu':{'priority':old,
             'max_commands':40,'priority_mode':'append'}}}}}
        menu=priority(raw)
        self.assertEqual(menu['priority'], ['status','custom','autowork','plan_with_me','plan_for_me','docs_sync'])
        raw['platforms']['telegram']['extra']['command_menu'].update(menu)
        self.assertEqual(priority(raw), menu)
        self.assertEqual(raw['platforms']['telegram']['extra']['command_menu']['priority_mode'],'append')

class SelfHealTests(unittest.TestCase):
    def test_old_profile_menu_is_detected_and_expected_settings_heal_it(self):
        import sys, types
        root=Path(__file__).resolve().parents[1]
        pkg=types.ModuleType('toolset_pkg'); pkg.__path__=[str(root)]
        sys.modules['toolset_pkg']=pkg
        bundle=types.ModuleType('toolset_pkg.bundle')
        bundle.defaults=lambda: {'hermes': {'approvals_mode':'off','destructive_slash_confirm':False,
                                            'mcp_reload_confirm':False,'allow_gateway_injection':True}}
        sys.modules['toolset_pkg.bundle']=bundle
        self.addCleanup(lambda: [sys.modules.pop(k,None) for k in list(sys.modules) if k.startswith('toolset_pkg')])
        spec=importlib.util.spec_from_file_location('toolset_pkg.runtime_defaults', root/'runtime_defaults.py')
        rd=importlib.util.module_from_spec(spec); sys.modules[spec.name]=rd; spec.loader.exec_module(rd)
        old={'approvals':{'mode':'off','destructive_slash_confirm':False,'mcp_reload_confirm':False},
             'plugins':{'entries':{'hermes-toolset':{'allow_gateway_injection':True}}},
             'platforms':{'telegram':{'extra':{'command_menu':{'priority':['autoresearch','autoresearch_plan','autowork']}}}}}
        self.assertEqual(rd.settings_drift(old, rd.expected_settings(old)), ['platforms.telegram.extra.command_menu.priority'])
        healed=rd.expected_settings(old)
        old['platforms']['telegram']['extra']['command_menu'].update(healed['platforms']['telegram']['extra']['command_menu'])
        self.assertEqual(rd.settings_drift(old, rd.expected_settings(old)), [])
        self.assertTrue(rd._opted_out({'plugins':{'entries':{'hermes-toolset':{'apply_runtime_defaults':False}}}}))


class CompatibilityRegistrationTests(unittest.TestCase):
    def test_autoresearch_spellings_require_text_so_telegram_menus_omit_them(self):
        spec=importlib.util.spec_from_file_location('ar_commands',Path(__file__).resolve().parents[1]/'autoresearch_commands.py')
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        hints={}
        class Ctx:
            def register_command(self, name, handler, description='', args_hint=''):
                hints[name]=args_hint
        import sys, types
        commands=types.ModuleType('hermes_cli.commands'); commands.resolve_command=lambda name: None
        plugins=types.ModuleType('hermes_cli.plugins'); plugins.get_plugin_commands=lambda: {}
        saved={k: sys.modules.get(k) for k in ('hermes_cli','hermes_cli.commands','hermes_cli.plugins')}
        sys.modules.update({'hermes_cli': types.ModuleType('hermes_cli'), 'hermes_cli.commands': commands,
                            'hermes_cli.plugins': plugins})
        try:
            module.register(Ctx(), [('autoresearch','autoresearch',Path('x'))], lambda *a: None)
        finally:
            for k,v in saved.items():
                if v is None: sys.modules.pop(k,None)
                else: sys.modules[k]=v
        self.assertEqual(len(hints), 2*len(module.COMMANDS))
        self.assertTrue(all(hint.startswith('<') for hint in hints.values()), hints)
