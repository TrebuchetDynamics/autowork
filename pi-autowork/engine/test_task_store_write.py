"""The TaskStore writer: canonical new records, minimal edits, refusal over loss."""
from pathlib import Path
import tomllib
import unittest

import task_store
from task_store import WriteError, edit, render, set_note

FIXTURES = Path(__file__).parent / 'fixtures' / 'task_store' / 'tasks'


def split(text):
    lines = text.splitlines(keepends=True)
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == '+++')
    return tomllib.loads(''.join(lines[1:end])), ''.join(lines[end + 1:])


def variants():
    """Every fixture record, plus forms people write by hand."""
    for path in sorted(FIXTURES.rglob('*.md')):
        yield path.name, path.read_text(), path.parent.name == 'goals'
    task = (FIXTURES / 'items/T-1.md').read_text()
    yield 'unicode', task.replace('title = "Read tasks"', 'title = "Lire les tâches — «vite»"'), False
    yield 'quotes', task.replace('scope = "Read only"', 'scope = "Read \\"only\\" \\\\ here"'), False
    yield 'literal string', task.replace('scope = "Read only"', "scope = 'Read only'"), False
    yield 'tight array', task.replace('touches = ["src/"]', 'touches=["src/","docs/a b.md"]'), False
    yield 'empty body', task.split('+++\nFree notes.')[0] + '+++\n', False


class WriterTests(unittest.TestCase):
    def test_round_trips_every_fixture(self):
        for name, text, goal in variants():
            with self.subTest(fixture=name):
                fields, body = split(text)
                rendered = render(fields, body, goal=goal)
                self.assertEqual(split(rendered), (fields, body))
                self.assertEqual(split(render(*split(rendered), goal=goal)), (fields, body))
                if not goal:
                    edited = edit(text, {'rank': 7000})
                    self.assertEqual(split(edited)[0], {**fields, 'rank': 7000})
                    changed = [(a, b) for a, b in zip(text.splitlines(), edited.splitlines()) if a != b]
                    self.assertEqual(len(changed), 1, 'only the rank line changes')
                    self.assertEqual(len(text.splitlines()), len(edited.splitlines()))

    def test_edit_adds_and_removes_one_line(self):
        text = (FIXTURES / 'items/T-1.md').read_text()
        added = edit(text.replace('live = "denied"\n', ''), {'live': 'denied'})
        self.assertEqual(split(added)[0], split(text)[0])
        removed = edit(text, {'live': None})
        self.assertNotIn('live =', removed)
        self.assertEqual(split(removed)[1], split(text)[1])

    def test_refuses_input_it_cannot_preserve(self):
        text = (FIXTURES / 'items/T-1.md').read_text()
        refusals = (
            (text.replace('rank = 1', 'rank = 1 # keep'), {'rank': 2}, 'comment'),
            (text.replace('touches = ["src/"]', 'touches = [\n  "src/",\n]'), {'touches': ['a/']}, 'several lines'),
            (text, {'scope': 'two\nlines'}, 'line breaks'),
            (text, {'title': 'tab\there'}, 'control characters'),
            (text, {'id': 'T-2'}, 'cannot be set'),
            (text, {'unknown': 'x'}, 'cannot be set'),
            (text, {'rank': 1.5}, 'unsupported'),
            (text.replace('rank = 1', 'rank = 1\nrank = 2'), {'rank': 3}, None),
        )
        for source, changes, message in refusals:
            with self.subTest(changes=changes, message=message):
                with self.assertRaises((WriteError, tomllib.TOMLDecodeError)) as caught:
                    edit(source, changes)
                if message:
                    self.assertIn(message, str(caught.exception))
        with self.assertRaisesRegex(WriteError, 'unknown field'):
            render({'schema': 1, 'id': 'T', 'extra': 'x'})
        with self.assertRaisesRegex(WriteError, 'line breaks'):
            set_note(text, 'Held by', 'a\nb')

    def test_notes_replace_their_line(self):
        text = (FIXTURES / 'items/T-1.md').read_text()
        once = set_note(text, 'Held by', 'me; until 2026-10-27')
        twice = set_note(once, 'Held by', 'you')
        self.assertEqual(twice.count('- Held by:'), 1)
        self.assertTrue(twice.endswith('- Held by: you\n'))
        self.assertEqual(split(twice)[0], split(text)[0])
        self.assertEqual(task_store.toml_value('k', ['a', 'b"c']), '["a", "b\\"c"]')


if __name__ == '__main__':
    unittest.main()
