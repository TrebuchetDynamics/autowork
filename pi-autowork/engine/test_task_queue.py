"""task_queue's contract view: only a record's typed values grant or limit anything."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import parallel_plan
import task_queue
from task_store import StoreError, TaskStore

GOAL = ('+++\nschema = 1\nid = "G"\ntitle = "g"\npriority = 1\nsource = "docs/plan.md#g"\n'
        'status = "unmet"\nfocus = false\n+++\n')


def record(extra_header='', body=''):
    return ('+++\nschema = 1\nid = "T-1"\ntitle = "Live migration"\nshort = "Live migration"\nstatus = "open"\n'
            'goal = "G"\nsection = "Now"\nrank = 1000\ndepends_on = []\ntouches = ["src/a.py"]\n'
            'resources = []\nkind = "implementation"\nownership = "owner"\nlive = "denied"\n'
            'scope = "migrate"\nacceptance = ["verified"]\nchecks = ["true"]\nexclusions = []\n'
            + extra_header + '+++\n' + body)


class ContractViewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        (self.repo / 'tasks/items').mkdir(parents=True)
        (self.repo / 'tasks/goals').mkdir()
        (self.repo / 'tasks/goals/G.md').write_text(GOAL)
        self.git('init', '-q')

    def git(self, *args):
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.email=f@example.invalid', '-c', 'user.name=F', *args],
                       check=True, capture_output=True)

    def store(self, text):
        (self.repo / 'tasks/items/T-1.md').write_text(text)
        self.git('add', '-A')
        self.git('commit', '-q', '--allow-empty', '-m', 'tasks')
        return task_queue.store(self.repo)

    def test_body_note_never_grants_authority(self):
        notes = '- Live authorization: yes\n- Ownership: worker\n- Resources: port:1\n- Kind: plan\n- Touches: **\n'
        snapshot = self.store(record(body=notes))
        contract = task_queue.contract(snapshot.tasks['T-1'], snapshot)
        fields = contract['fields']
        self.assertEqual(fields['Ownership'], 'Owner only', 'the typed owner-only value wins over the note')
        self.assertNotIn('Live authorization', fields)
        self.assertNotIn('Resources', fields)
        self.assertNotIn('Kind', fields)
        self.assertEqual(fields['Touches'], 'src/a.py')
        for value in ('Live authorization: yes', 'Ownership: worker', 'port:1', 'Kind: plan'):
            self.assertNotIn(value, contract['contract'])
        # At dispatch it still waits for a recorded authorization.
        gate = parallel_plan.authorization_wait(contract)
        self.assertIsNotNone(gate)
        self.assertIn('Live authorization', gate['reason'] + str(gate.get('id', '')))
        planned = parallel_plan.plan([contract])
        self.assertEqual(planned['dispatch'], [])

    def test_a_live_resource_waits_whatever_its_note_says(self):
        text = record(body='- Live authorization: approved by the owner\n').replace(
            'resources = []', 'resources = ["live"]').replace('ownership = "owner"', 'ownership = "worker"')
        snapshot = self.store(text)
        contract = task_queue.contract(snapshot.tasks['T-1'], snapshot)
        self.assertEqual(contract['fields']['Resources'], 'live')
        self.assertIsNotNone(parallel_plan.authorization_wait(contract))
        granted = self.store(text.replace('live = "denied"', 'live = "authorized"'))
        self.assertIsNone(parallel_plan.authorization_wait(task_queue.contract(granted.tasks['T-1'], granted)))

    def test_revision_discovery_ignores_git_routing_and_replace_refs_but_reports_errors(self):
        self.assertIsNone(task_queue.commit(self.repo))  # unborn, not a read failure
        first = self.store(record())
        second = self.store(record().replace('scope = "migrate"', 'scope = "changed"'))
        self.git('replace', first.rev, second.rev)
        foreign = self.repo / 'foreign'
        foreign.mkdir()
        subprocess.run(['git', 'init', '-q', str(foreign)], check=True)
        env = dict(GIT_DIR=str(foreign / '.git'), GIT_WORK_TREE=str(foreign),
                   GIT_INDEX_FILE=str(foreign / 'hostile-index'))
        with patch.dict('os.environ', env):
            self.assertEqual(task_queue.commit(self.repo, first.rev), first.rev)
            self.assertEqual(task_queue.store(self.repo, first.rev).tasks['T-1'].scope, 'migrate')
            self.assertEqual(task_queue.commit(self.repo), second.rev)
            self.assertIsNone(task_queue.commit(self.repo, 'missing-ref'))
            with self.assertRaises(StoreError):
                task_queue.commit(self.repo / 'missing-directory')
        self.assertFalse((foreign / 'hostile-index').exists())
        # An existing ref whose object disappeared is corruption, not an unborn branch.
        (self.repo / '.git/objects' / second.rev[:2] / second.rev[2:]).unlink()
        with self.assertRaises(StoreError):
            task_queue.commit(self.repo)
        ref = subprocess.check_output(['git', '-C', str(self.repo), 'symbolic-ref', 'HEAD'], text=True).strip()
        (self.repo / '.git' / ref).write_text('not-an-object\n')
        with self.assertRaises(StoreError):
            task_queue.commit(self.repo)

    def test_a_duplicate_key_fails_closed(self):
        text = record().replace('live = "denied"\n', 'live = "denied"\nlive = "authorized"\n')
        (self.repo / 'tasks/items/T-1.md').write_text(text)
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'duplicate')
        with self.assertRaisesRegex(StoreError, r'tasks/items/T-1.md:\d+: malformed TOML'):
            TaskStore.at(self.repo, 'HEAD')


if __name__ == '__main__':
    unittest.main()
