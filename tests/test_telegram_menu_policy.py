import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('menu_policy',Path(__file__).resolve().parents[1]/'telegram_menu_policy.py')
policy=importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)
WORKFLOWS=['plan_with_me', 'plan_for_me', 'docs_sync', 'autowork', 'cron_autowork',
           'ui_taste', 'beautify_github_readme']

def priority(raw):
    return policy.menu_patch(raw)['platforms']['telegram']['extra']['command_menu']

class MenuPolicyTests(unittest.TestCase):
    def test_only_current_workflow_commands_get_priority_without_changing_cap(self):
        menu=priority({})
        self.assertEqual(menu['priority'], WORKFLOWS)
        self.assertNotIn('max_commands',menu)
    def test_every_advertised_skill_command_is_a_bundled_skill(self):
        # Telegram spells a skill's hyphens as underscores; workflow aliases are registered separately.
        skills={p.name.replace('-','_') for p in (Path(policy.__file__).parent/'skills').iterdir() if (p/'SKILL.md').is_file()}
        self.assertTrue({'ui_taste','beautify_github_readme'} <= skills)
        self.assertLessEqual(set(WORKFLOWS) - skills, {'plan_with_me','plan_for_me','docs_sync'})
    def test_stale_compatibility_entries_are_removed_and_user_choices_kept(self):
        old=['autoresearch','autoresearch_plan','autoresearch_debug','autoresearch-fix','status','custom',
             'autowork','plan_with_me','grill_me','repo_interview','repo_docs','autogoal']
        raw={'platforms':{'telegram':{'extra':{'command_menu':{'priority':old,
             'max_commands':40,'priority_mode':'append'}}}}}
        menu=priority(raw)
        self.assertEqual(menu['priority'], ['status','custom','autowork','plan_with_me','plan_for_me','docs_sync','cron_autowork',
                                           'ui_taste','beautify_github_readme'])
        raw['platforms']['telegram']['extra']['command_menu'].update(menu)
        self.assertEqual(priority(raw), menu)
        self.assertEqual(raw['platforms']['telegram']['extra']['command_menu']['priority_mode'],'append')

class ChatMenuTests(unittest.TestCase):
    def fake(self, menus):
        calls=[]
        def call(method, scope):
            calls.append((method, scope['chat_id']))
            if method=='deleteMyCommands':
                menus.pop(scope['chat_id'], None); return True
            return [{'command': c} for c in menus.get(scope['chat_id'], [])]
        return call, calls
    def test_only_chat_menus_with_retired_commands_are_cleared(self):
        menus={11:['autowork','autogoal'], 22:['custom'], -33:['autoresearch_fix']}
        call, calls=self.fake(menus)
        env={'TELEGRAM_ALLOWED_USERS':'11, 22,bad,11','TELEGRAM_HOME_CHANNEL':'-33'}
        self.assertEqual(policy.stale_chat_menus(env, call), [11, -33])
        self.assertEqual(menus, {22:['custom']})
        self.assertEqual(policy.stale_chat_menus(env, call), [])
        self.assertNotIn(('deleteMyCommands', 22), calls)
    def test_no_owner_chats_means_no_api_calls(self):
        call, calls=self.fake({})
        self.assertEqual(policy.stale_chat_menus({}, call), [])
        self.assertEqual(calls, [])

class ChatMenuRobustnessTests(unittest.TestCase):
    def test_only_ascii_integer_chat_ids_are_accepted(self):
        env={'TELEGRAM_ALLOWED_USERS':'--5,²,٣,1-2,+7,11','TELEGRAM_HOME_CHANNEL':'-33'}
        self.assertEqual(policy.chat_ids(env), [11, -33])
    def test_a_failing_chat_does_not_stop_the_remaining_chats(self):
        menus={11:['autogoal'], 7:['autogoal'], 22:['autogoal'], -33:['autoresearch_plan']}
        def call(method, scope):
            chat=scope['chat_id']
            if chat==7: raise OSError('Bad Request: chat not found')
            if method=='deleteMyCommands':
                menus.pop(chat); return True
            return [{'command': c} for c in menus.get(chat, [])]
        failed=[]
        env={'TELEGRAM_ALLOWED_USERS':'11,7,22','TELEGRAM_HOME_CHANNEL':'-33'}
        self.assertEqual(policy.stale_chat_menus(env, call, failed), [11, 22, -33])
        self.assertEqual(failed, [(7, 'OSError')])
        self.assertEqual(menus, {7:['autogoal']})

class SelfHealTests(unittest.TestCase):
    def test_old_profile_menu_is_detected_and_expected_settings_heal_it(self):
        import sys, types
        root=Path(__file__).resolve().parents[1]
        pkg=types.ModuleType('toolset_pkg'); pkg.__path__=[str(root)]
        sys.modules['toolset_pkg']=pkg
        bundle=types.ModuleType('toolset_pkg.bundle')
        bundle.defaults=lambda: {'hermes': {'approvals_mode':'off','destructive_slash_confirm':False,
                                            'mcp_reload_confirm':False,'max_turns':'unlimited','allow_gateway_injection':True}}
        sys.modules['toolset_pkg.bundle']=bundle
        self.addCleanup(lambda: [sys.modules.pop(k,None) for k in list(sys.modules) if k.startswith('toolset_pkg')])
        spec=importlib.util.spec_from_file_location('toolset_pkg.runtime_defaults', root/'runtime_defaults.py')
        rd=importlib.util.module_from_spec(spec); sys.modules[spec.name]=rd; spec.loader.exec_module(rd)
        old={'approvals':{'mode':'off','destructive_slash_confirm':False,'mcp_reload_confirm':False},
             'agent':{'max_turns':90},
             'plugins':{'entries':{'hermes-toolset':{'allow_gateway_injection':True}}},
             'platforms':{'telegram':{'extra':{'command_menu':{'priority':['autoresearch','autoresearch_plan','autowork']}}}}}
        self.assertEqual(rd.settings_drift(old, rd.expected_settings(old)),
                         ['agent.max_turns', 'platforms.telegram.extra.command_menu.priority'])
        healed=rd.expected_settings(old)
        old['agent'].update(healed['agent'])
        old['platforms']['telegram']['extra']['command_menu'].update(healed['platforms']['telegram']['extra']['command_menu'])
        self.assertEqual(rd.settings_drift(old, rd.expected_settings(old)), [])
        # Hermes never reads an entry-level key, so it is not an opt-out (TOOLSET-033).
        self.assertFalse(rd._opted_out({'plugins':{'entries':{'hermes-toolset':{'apply_runtime_defaults':False}}}}))



class RuntimePolicyOptOutTests(unittest.TestCase):
    """Verification must honor the opt-out at the path Hermes' get_config reads (TOOLSET-033)."""

    def setUp(self):
        import sys, types
        root=Path(__file__).resolve().parents[1]
        pkg=types.ModuleType('toolset_pkg'); pkg.__path__=[str(root)]
        bundle=types.ModuleType('toolset_pkg.bundle')
        bundle.defaults=lambda: {'hermes': {'approvals_mode':'off','destructive_slash_confirm':False,
                                            'mcp_reload_confirm':False,'max_turns':'unlimited','allow_gateway_injection':True}}
        self.raw={}
        config=types.ModuleType('hermes_cli.config'); config.read_raw_config=lambda: self.raw
        cli=types.ModuleType('hermes_cli'); cli.config=config
        saved={k: sys.modules.get(k) for k in ('hermes_cli','hermes_cli.config')}
        sys.modules.update({'toolset_pkg':pkg,'toolset_pkg.bundle':bundle,'hermes_cli':cli,'hermes_cli.config':config})
        def restore():
            for k in list(sys.modules):
                if k.startswith('toolset_pkg'): sys.modules.pop(k,None)
            for k,v in saved.items():
                if v is None: sys.modules.pop(k,None)
                else: sys.modules[k]=v
        self.addCleanup(restore)
        spec=importlib.util.spec_from_file_location('toolset_pkg.runtime_defaults', root/'runtime_defaults.py')
        self.rd=importlib.util.module_from_spec(spec); sys.modules[spec.name]=self.rd; spec.loader.exec_module(self.rd)

    def entry(self, value):
        return {'plugins':{'entries':{'hermes-toolset':value}}}

    def test_opt_out_follows_hermes_settings_then_legacy_config(self):
        rd=self.rd
        self.assertTrue(rd._opted_out(self.entry({'settings':{'apply_runtime_defaults':False}})))
        self.assertTrue(rd._opted_out(self.entry({'config':{'apply_runtime_defaults':False}})))
        self.assertFalse(rd._opted_out(self.entry({'settings':{'apply_runtime_defaults':True},
                                                   'config':{'apply_runtime_defaults':False}})))
        self.assertTrue(rd._opted_out(self.entry({'settings':{},'config':{'apply_runtime_defaults':False}})))
        for value in ({}, {'settings':{'apply_runtime_defaults':'false'}}, {'settings':None},
                      {'apply_runtime_defaults':False}, None, 'x'):
            with self.subTest(value=value):
                self.assertFalse(rd._opted_out(self.entry(value)))
        self.assertFalse(rd._opted_out(None))

    def test_setup_reader_uses_the_same_rule_and_never_hides_bad_configs(self):
        import sys, tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'config.yaml'
            self.assertFalse(self.rd.setup_opted_out(path))  # missing
            path.write_text('plugins:\n  entries:\n    hermes-toolset:\n      config:\n        apply_runtime_defaults: false\n')
            self.assertTrue(self.rd.setup_opted_out(path))
            path.write_text('plugins: [\n  apply_runtime_defaults: false\n')  # malformed: Hermes refuses later
            self.assertFalse(self.rd.setup_opted_out(path))
            with patch.dict(sys.modules, {'yaml': None}):
                self.assertIsNone(self.rd.setup_opted_out(path))
                path.write_text('approvals:\n  mode: manual\n')
                self.assertFalse(self.rd.setup_opted_out(path))

    def test_documented_opt_out_with_restored_values_reports_no_drift(self):
        self.raw={'approvals':{'mode':'manual','destructive_slash_confirm':True},
                  'plugins':{'entries':{'hermes-toolset':{'settings':{'apply_runtime_defaults':False}}}}}
        self.assertEqual(self.rd.verify_runtime_defaults(), [])
        self.raw['plugins']['entries']['hermes-toolset']['settings']['apply_runtime_defaults']=True
        self.assertIn('approvals.mode', self.rd.verify_runtime_defaults())
        del self.raw['plugins']['entries']['hermes-toolset']['settings']
        self.assertIn('approvals.mode', self.rd.verify_runtime_defaults())


    def test_native_registration_probe_config_opts_out(self):
        import yaml
        spec=importlib.util.spec_from_file_location(
            'native_probe', Path(__file__).resolve().parents[1]/'update_bundle_native.py')
        native=importlib.util.module_from_spec(spec); spec.loader.exec_module(native)
        probe=yaml.safe_load(native.PROBE_CONFIG)
        self.assertEqual(probe['plugins']['enabled'], ['hermes-toolset'])
        self.assertTrue(self.rd._opted_out(probe))


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
