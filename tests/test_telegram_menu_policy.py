import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('menu_policy',Path(__file__).resolve().parents[1]/'telegram_menu_policy.py')
policy=importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)

class MenuPolicyTests(unittest.TestCase):
    def test_all_autoresearch_commands_get_priority_without_changing_cap(self):
        patch=policy.menu_patch({})
        menu=patch['platforms']['telegram']['extra']['command_menu']
        self.assertEqual(len(menu['priority']),18)
        self.assertEqual(menu['priority'][:4], ['plan_with_me', 'plan_for_me', 'docs_sync', 'autowork'])
        self.assertIn('autoresearch_plan',menu['priority'])
        self.assertIn('autowork',menu['priority'])
        self.assertNotIn('max_commands',menu)
    def test_existing_choices_preserved_and_idempotent(self):
        raw={'platforms':{'telegram':{'extra':{'command_menu':{'priority':['status','custom'],
             'max_commands':40,'priority_mode':'append'}}}}}
        patch=policy.menu_patch(raw)
        menu=patch['platforms']['telegram']['extra']['command_menu']
        self.assertEqual(menu['priority'][:2],['status','custom'])
        raw['platforms']['telegram']['extra']['command_menu'].update(menu)
        self.assertEqual(policy.menu_patch(raw),patch)
        self.assertEqual(raw['platforms']['telegram']['extra']['command_menu']['priority_mode'],'append')
