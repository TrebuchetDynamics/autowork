"""Shared confirmation dialog for planning and fleet screens, without app imports."""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class Confirm(ModalScreen[bool]):
    BINDINGS = [Binding('y', 'answer(True)', 'yes'), Binding('n,escape', 'answer(False)', 'no')]
    DEFAULT_CSS = '''
    Confirm { align: center middle; }
    Confirm > Vertical { width: 76; max-width: 100%; height: auto; max-height: 95%; border: thick $warning; background: $surface; padding: 1 2; }
    #confirm-body { height: 1fr; }
    Confirm Horizontal { height: auto; align-horizontal: right; margin-top: 1; }
    Confirm Button { margin-left: 2; }
    '''

    def __init__(self, question):
        super().__init__()
        self.question = question

    def compose(self) -> ComposeResult:
        with Vertical():
            with VerticalScroll(id='confirm-body'):
                yield Label(self.question, markup=False)
            with Horizontal():
                yield Button('Yes (y)', variant='warning', id='yes')
                yield Button('No (n)', id='no')

    def _answer(self, value):
        # A button event can arrive after the confirmation was already dismissed (a double
        # click, a queued key, or a refresh that removed the modal). dismiss() would then pop
        # the last remaining screen and crash the whole TUI with ScreenStackError.
        if self.is_current:
            self.dismiss(value)

    def on_button_pressed(self, event):
        self._answer(event.button.id == 'yes')

    def action_answer(self, value):
        self._answer(value)
