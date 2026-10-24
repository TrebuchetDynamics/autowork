"""App-owned planning turns. No widget references and no second execution daemon."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
import threading

from .planning_views import event_text


@dataclass
class Turn:
    cancel: threading.Event = field(default_factory=threading.Event)
    status: str = 'running'
    text: str = ''
    result: dict = field(default_factory=dict)
    future: object = None


class PlanningHub:
    def __init__(self, *, max_text=200_000):
        self.max_text = max_text
        self.turns = {}
        self.planners = {}
        self._lock = threading.RLock()
        self._pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='autowork-plan')
        self.closed = False

    def controller(self, repo, factory):
        """Canonicalize via the backend before registering; aliases share a live controller."""
        with self._lock:
            found = self.planners.get(repo)
        if found is not None:
            return found
        candidate = factory(repo)  # Git/disk reads must not hold the UI's projection lock.
        canonical = str(Path(candidate.repo).resolve())
        with self._lock:
            found = self.planners.setdefault(canonical, candidate)
            self.planners[repo] = found
            return found

    def start(self, repo, planner, sid, message):
        key = (repo, sid)
        with self._lock:
            if self.closed:
                raise ValueError('planning console is closing')
            if key in self.turns and self.turns[key].status == 'running':
                raise ValueError('this planning session is already running; use Steer or Cancel')
            if sum(t.status == 'running' for t in self.turns.values()) >= 4:
                raise ValueError('four planning turns are running; cancel or wait for one')
            turn = self.turns[key] = Turn()
            turn.future = self._pool.submit(self._run, planner, sid, message, turn)
        return turn

    def _run(self, planner, sid, message, turn):
        def event(value):
            text = event_text(value)
            if text:
                with self._lock:
                    turn.text = (turn.text + text)[-self.max_text:]
        try:
            result = planner.send(sid, message, on_event=event, cancel=turn.cancel)
            with self._lock:
                turn.result = result
                turn.text = str(result.get('text', turn.text))[-self.max_text:]
                turn.status = result.get('status', 'ready')
                if turn.status == 'running':
                    turn.status = 'failed'
                    turn.text += '\nPlanner returned without settling.'
        except Exception as error:
            with self._lock:
                turn.status, turn.text = 'failed', str(error)

    def snapshot(self, repo, sid):
        with self._lock:
            turn = self.turns.get((repo, sid))
            return {'status': turn.status, 'text': turn.text, 'result': dict(turn.result)} if turn else None

    def cancel(self, repo, sid):
        with self._lock:
            turn = self.turns.get((repo, sid))
            if turn:
                turn.cancel.set()

    def close(self):
        with self._lock:
            self.closed = True
            for turn in self.turns.values():
                turn.cancel.set()
        self._pool.shutdown(wait=True, cancel_futures=True)
