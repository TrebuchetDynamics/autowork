"""Embedded planning workspace. Controllers/turns belong to the app, not this screen."""
import asyncio
import os
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen, ModalScreen
from textual.widgets import Button, Header, Input, Label, Select, Static, TabbedContent, TabPane, TextArea

from .planning_hub import PlanningHub
from .planning_views import history_text, preview_text, roadmap_text


class DecisionPrompt(ModalScreen[dict]):
    """A manual owner decision is distinct from an AI proposal or a verified close."""
    BINDINGS = [Binding('escape', 'dismiss(None)', 'Cancel')]
    DEFAULT_CSS = '''
    DecisionPrompt { align: center middle; }
    #decision-form { width: 76; max-width: 100%; height: auto; padding: 1 2; background: $surface; border: thick $accent; }
    #decision-text { height: 6; }
    #decision-form Horizontal { height: 3; }
    '''

    def __init__(self, task):
        super().__init__()
        self.task_id = task

    def compose(self):
        from textual.containers import Vertical
        with Vertical(id='decision-form'):
            yield Label(f'Decide {self.task_id}: dated owner direction (not verification)', markup=False)
            yield TextArea(id='decision-text')
            yield Select([('Keep section', ''), ('Now', 'Now'), ('Next', 'Next'), ('Defer', 'Needs decision')],
                         value='', allow_blank=False, id='decision-section')
            with Horizontal():
                yield Button('Record decision', id='decision-save', variant='primary')
                yield Button('Cancel', id='decision-cancel')

    def on_mount(self):
        self.query_one('#decision-text', TextArea).focus()

    def on_button_pressed(self, event):
        event.stop()
        if event.button.id == 'decision-cancel':
            self.dismiss(None)
            return
        text = self.query_one('#decision-text', TextArea).text.strip()
        if not text:
            self.notify('Enter the decision first.', severity='warning')
            return
        self.dismiss({'text': text, 'section': self.query_one('#decision-section', Select).value})


class PlanScreen(Screen):
    BINDINGS = [Binding('escape', 'back', 'Back'),
                Binding('ctrl+enter', 'send', 'Send', priority=True),
                Binding('ctrl+x', 'cancel', 'Cancel turn', priority=True),
                Binding('f2', 'review', 'Review', priority=True)]
    DEFAULT_CSS = '''
    PlanScreen .plan-line { height: 3; }
    #plan-repository { width: 1fr; }
    #plan-load, #plan-new { width: 10; min-width: 8; }
    #plan-mode { width: 18; }
    #plan-task { width: 18; }
    #plan-session { width: 1fr; }
    #plan-state { height: 2; padding: 0 1; }
    #plan-tabs { height: 1fr; min-height: 6; }
    #plan-tabs ContentSwitcher { height: 1fr; }
    #plan-tabs TabPane { padding: 0; }
    #plan-tabs TextArea { height: 1fr; }
    #plan-input { height: 4; }
    #plan-controls { height: 3; }
    #plan-controls Button { min-width: 8; width: 1fr; padding: 0; }
    '''

    def __init__(self, repo, task=None, mode='plan', *, planner_factory=None):
        super().__init__()
        self.repo = str(Path(repo).resolve())
        self.initial_task, self.initial_mode = task or '', mode
        self.factory = planner_factory
        self.planner = None
        self.session_id = None
        self.preview = None
        self._busy = False
        self._epoch = 0
        self._history = ''
        self._turn_display = None
        self._known_sessions = []

    @property
    def hub(self):
        if not hasattr(self.app, 'planning_hub'):
            self.app.planning_hub = PlanningHub()
        return self.app.planning_hub

    @property
    def readonly(self):
        return bool(getattr(self.app, 'view_only', False))

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(classes='plan-line'):
            yield Input(self.repo, placeholder='Project path (service may be paused or absent)', id='plan-repository')
            yield Button('Load', id='plan-load')
        with Horizontal(classes='plan-line'):
            yield Select([('Plan', 'plan'), ('Discuss', 'discuss'), ('Investigate', 'investigate')],
                         value=self.initial_mode, allow_blank=False, id='plan-mode')
            yield Input(self.initial_task, placeholder='Task ID (optional)', id='plan-task')
            yield Select([], prompt='New session', id='plan-session')
            yield Button('New', id='plan-new')
        yield Static('Loading project…', id='plan-state', markup=False)
        with TabbedContent(id='plan-tabs'):
            with TabPane('Chat', id='plan-chat-tab'):
                yield TextArea(read_only=True, id='plan-chat')
            with TabPane('Proposal', id='plan-proposal-tab'):
                yield TextArea('Review a proposal before Apply.', read_only=True, id='plan-proposal')
            with TabPane('Roadmap', id='plan-roadmap-tab'):
                yield TextArea(read_only=True, id='plan-roadmap')
            with TabPane('History', id='plan-history-tab'):
                yield TextArea(read_only=True, id='plan-history')
        yield TextArea(id='plan-input')
        with Horizontal(id='plan-controls'):
            for label, key in [('Send', 'send'), ('Steer', 'steer'), ('Cancel', 'cancel'),
                               ('Review', 'review'), ('Apply', 'apply'), ('Back', 'back')]:
                yield Button(label, id='plan-' + key, variant='warning' if key == 'apply' else 'default')

    def on_mount(self):
        self.title = 'Plan · ' + Path(self.repo).name
        self._load_project()
        self.set_interval(.2, self.poll_turn)

    def note(self, message):
        if self.is_mounted:
            self.query_one('#plan-state', Static).update(message)

    def _operation(self, load, done):
        """Run disk/Git/RPC commands off the UI loop, guard stale widget publications."""
        if self._busy:
            return
        self._busy = True
        epoch = self._epoch
        self.controls()
        async def run():
            try:
                result = await asyncio.to_thread(load)
                if self.is_mounted and epoch == self._epoch:
                    done(result)
            except Exception as error:
                if self.is_mounted and epoch == self._epoch:
                    self.note(str(error))
                    self.notify(str(error), severity='error')
            finally:
                self._busy = False
                if self.is_mounted:
                    self.controls()
        self.app.run_worker(run(), group='planning-controls', exit_on_error=False)

    def controls(self):
        if not self.is_mounted:
            return
        turn = self.hub.snapshot(self.repo, self.session_id)
        running = bool(turn and turn['status'] == 'running')
        for key in ('send', 'new', 'load'):
            self.query_one('#plan-' + key, Button).disabled = (self.readonly or self._busy
                                                               or (key == 'send' and (running or self.planner is None)))
        self.query_one('#plan-session', Select).disabled = self._busy
        for key in ('plan-task', 'plan-mode'):
            self.query_one('#' + key).disabled = self.readonly or self._busy or self.session_id is not None
        self.query_one('#plan-steer', Button).disabled = self.readonly or self._busy or not running
        self.query_one('#plan-cancel', Button).disabled = self.readonly or not running
        self.query_one('#plan-review', Button).disabled = self._busy or running or not self.session_id
        self.query_one('#plan-apply', Button).disabled = (self.readonly or self._busy or running or not self.preview
                                                       or not self.preview.get('valid') or not self.preview.get('files'))

    def _load_project(self):
        if self._busy:
            return
        self._epoch += 1
        repo = self.repo
        # Never keep controls for the preceding project under the new project name,
        # even when acquisition fails. Its app-owned turn still lives in the hub.
        self.planner, self.session_id, self.preview = None, None, None
        self._history, self._turn_display, self._known_sessions = '', None, []
        self.query_one('#plan-session', Select).set_options([])
        for pane in ('chat', 'history', 'proposal', 'roadmap'):
            self.query_one('#plan-' + pane, TextArea).load_text('Loading ' + repo + '…')
        self.title = 'Plan · ' + Path(repo).name
        self.note('Loading ' + repo + '…')
        def load():
            factory = self.factory
            if factory is None:
                from .planning import Planner
                factory = Planner
            planner = self.hub.controller(repo, lambda path: factory(
                path, state_root=self.app.state_root, pi=os.environ.get('AUTOWORK_PI', 'pi')))
            return planner, planner.sessions(), planner.roadmap()
        def done(result):
            self.planner, sessions, roadmap = result
            self.repo = str(Path(self.planner.repo).resolve())
            self.query_one('#plan-repository', Input).value = self.repo
            self.title = 'Plan · ' + Path(self.repo).name
            self._known_sessions = sessions
            self.query_one('#plan-session', Select).set_options(
                [(s['id'] + ' · ' + s.get('status', ''), s['id']) for s in sessions])
            self.query_one('#plan-roadmap', TextArea).load_text(roadmap_text(roadmap))
            self.session_id, self.preview = None, None
            self._history = ''
            self.query_one('#plan-chat', TextArea).load_text('New session. Optional objective below; Send starts discovery.')
            self.query_one('#plan-history', TextArea).load_text('No session selected.')
            self.query_one('#plan-proposal', TextArea).load_text('No reviewed proposal. Send, then Review before Apply.')
            self.note('New session: optional objective below. Proposals only; Apply is a separate local commit.')
            if sessions and not self.initial_task:
                self.query_one('#plan-session', Select).value = sessions[0]['id']
        self._operation(load, done)

    def on_select_changed(self, event):
        if event.select.id != 'plan-session' or event.value is Select.BLANK or self.planner is None:
            return
        sid = str(event.value)
        if sid == self.session_id:
            return
        # Select changes emitted while initial load completes are processed on next tick.
        self.call_after_refresh(self._select_session, sid, self._epoch)

    def _select_session(self, sid, epoch):
        if epoch != self._epoch or not self.is_mounted or self.planner is None:
            return
        if str(self.query_one('#plan-session', Select).value) != sid:
            return
        if self._busy:
            self.set_timer(.05, lambda: self._select_session(sid, epoch))
            return
        self.session_id, self.preview, self._turn_display = sid, None, None
        self.query_one('#plan-proposal', TextArea).load_text('Review session ' + sid + ' before Apply.')
        self.query_one('#plan-roadmap', TextArea).load_text('Loading this session’s roadmap…')
        planner = self.planner
        def done(result):
            messages, meta, roadmap = result
            self.query_one('#plan-roadmap', TextArea).load_text(roadmap_text(roadmap))
            self.query_one('#plan-mode', Select).value = meta.get('mode', 'plan')
            self.query_one('#plan-task', Input).value = meta.get('task') or ''
            self._history = history_text(messages)
            self.query_one('#plan-history', TextArea).load_text(self._history)
            self.query_one('#plan-chat', TextArea).load_text(self._history)
            state = self.hub.snapshot(self.repo, sid)
            if state and state['status'] not in ('running', 'failed', 'error', 'cancelled'):
                self._turn_display = state['status'], state['text']
            self.note('Session ' + sid + ' · ' + meta.get('status', 'unknown')
                      + (' · ' + meta['last_error'] if meta.get('last_error') else '')
                      + ' · Send continues; Review validates its proposal.')
            self.poll_turn()
        self._operation(lambda: (planner.history(sid), planner.get(sid), planner.roadmap(sid)), done)

    def action_send(self):
        if self.readonly or self._busy or self.planner is None:
            return
        text = self.query_one('#plan-input', TextArea).text.strip()
        planner, sid = self.planner, self.session_id
        if sid and not text:
            self.note('Enter a message to continue this session.')
            return
        task = self.query_one('#plan-task', Input).value.strip() or None
        mode = self.query_one('#plan-mode', Select).value
        repo = self.repo
        def load():
            selected = sid or planner.create(objective=text, task=task, mode=mode)['id']
            return selected, planner.history(selected)
        def done(result):
            selected, messages = result
            if self.readonly:
                self.note('View only: session retained; no model turn started.')
                return
            self.session_id, self.preview = selected, None
            self._turn_display = None
            self._history = history_text(messages)
            if text:
                self._history += '\n\nYou\n' + text
            if selected not in {s['id'] for s in self._known_sessions}:
                self._known_sessions.insert(0, {'id': selected, 'status': 'ready'})
                self.query_one('#plan-session', Select).set_options([(s['id'], s['id']) for s in self._known_sessions])
            self.query_one('#plan-session', Select).value = selected
            self.hub.start(repo, planner, selected, text if sid else '')
            self.query_one('#plan-input', TextArea).load_text('')
            self.query_one('#plan-tabs', TabbedContent).active = 'plan-chat-tab'
            self.note('Investigating · ' + selected + ' · navigation keeps this turn; closing cancels it.')
        self._operation(load, done)

    def poll_turn(self):
        if not self.is_mounted or not self.session_id:
            return
        state = self.hub.snapshot(self.repo, self.session_id)
        if state and (state['status'], state['text']) != self._turn_display:
            self._turn_display = state['status'], state['text']
            chat = self.query_one('#plan-chat', TextArea)
            follow, scroll = chat.is_vertical_scroll_end, chat.scroll_y
            chat.load_text((self._history + '\n\nPlanner\n' + state['text'])[-250_000:])
            chat.scroll_to(y=chat.max_scroll_y if follow else scroll, animate=False)
            self.note(state['status'].capitalize() + ' · ' + self.session_id + ' · unaccepted proposal; Review before Apply')
        self.controls()

    def action_steer(self):
        if self.readonly or self._busy or not self.session_id:
            return
        message = self.query_one('#plan-input', TextArea).text.strip()
        if not message:
            return
        planner, sid = self.planner, self.session_id
        self._operation(lambda: planner.steer(sid, message), lambda _: self._steered(message))

    def _steered(self, message):
        self._history += '\n\nYou (steering queued)\n' + message
        self.query_one('#plan-input', TextArea).load_text('')
        self._turn_display = None
        self.note('Steering queued, not yet a completed decision.')

    def action_cancel(self):
        if not self.readonly and self.session_id:
            self.hub.cancel(self.repo, self.session_id)
            self.note('Cancellation requested; waiting for Pi to stop. History/proposal retained.')

    def action_review(self):
        if self._busy or not self.session_id:
            return
        turn = self.hub.snapshot(self.repo, self.session_id)
        if turn and turn['status'] == 'running':
            self.note('Wait for or cancel the active turn before reviewing.')
            return
        planner, sid = self.planner, self.session_id
        def done(result):
            preview, roadmap, history = result
            self.preview = preview
            self.query_one('#plan-proposal', TextArea).load_text(preview_text(preview))
            self.query_one('#plan-roadmap', TextArea).load_text(roadmap_text(roadmap))
            self.query_one('#plan-history', TextArea).load_text(history_text(history))
            self.query_one('#plan-tabs', TabbedContent).active = 'plan-proposal-tab'
            self.note('Reviewed ' + preview.get('revision', '') + ' · Apply is a local commit, never a push.')
        self._operation(lambda: (planner.preview(sid), planner.roadmap(sid), planner.history(sid)), done)

    def action_apply(self):
        if self.readonly or self._busy or not self.preview or not self.preview.get('valid') or not self.preview.get('files'):
            return
        from .tui import Confirm
        planner, sid, revision, repo = self.planner, self.session_id, self.preview['revision'], self.repo
        def confirmed(yes):
            if yes and not self.readonly and (repo, sid) == (self.repo, self.session_id):
                def done(result):
                    self.preview = None
                    self.note('Applied locally: ' + str(result.get('commit', '')) + ' · not pushed; runner state unchanged.')
                self._operation(lambda: planner.apply(sid, revision), done)
        self.app.push_screen(Confirm(f'Apply reviewed proposal {revision[:16]} to {repo}? '
                                     'Creates a local commit. An already-running scheduler may pick up accepted tasks. '
                                     'No service starts or push.'), confirmed)

    def action_back(self):
        self.app.pop_screen()

    def on_button_pressed(self, event):
        key = event.button.id
        if not key or not key.startswith('plan-'):
            return
        event.stop()
        if key == 'plan-load':
            if not self.readonly and not self._busy:
                self.repo = str(Path(self.query_one('#plan-repository', Input).value).expanduser().resolve())
                self.initial_task = ''
                self.query_one('#plan-task', Input).value = ''
                self._load_project()
        elif key == 'plan-new':
            if not self.readonly and not self._busy:
                self.session_id, self.preview, self._history = None, None, ''
                self.query_one('#plan-session', Select).value = Select.BLANK
                self.query_one('#plan-chat', TextArea).load_text('New session. Optional objective below; Send starts discovery.')
                for pane in ('history', 'proposal', 'roadmap'):
                    self.query_one('#plan-' + pane, TextArea).load_text('No session selected.')
                self.controls()
        else:
            action = getattr(self, 'action_' + key[5:], None)
            if action:
                action()
