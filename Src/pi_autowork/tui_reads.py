"""UI-loop-owned, bounded read scheduling; executor threads only run plain loaders.

Cancellation retires a subscription, not its physical thread. No executor queue is
used: four physical reads and one replaceable pending token per live resource are
admitted here, on the event loop. Timer requests do not invalidate active results.
"""
import asyncio
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from dataclasses import dataclass, field
from itertools import count


@dataclass(eq=False)
class Token:
    owner: 'ReadOwner'
    kind: str
    identity: object
    epoch: object
    generation: int
    loader: object = field(repr=False)
    done: asyncio.Future = field(repr=False)
    cancelled: bool = False

    def cancel(self):
        self.cancelled = True
        if not self.done.done():
            self.done.set_result(None)

    async def wait(self):
        try:
            await asyncio.shield(self.done)
        except asyncio.CancelledError:
            self.cancel()
            raise


class ReadOwner:
    """One app/screen lifetime. ``publish(token, value, error)`` runs on the UI loop."""
    def __init__(self, coordinator, publish):
        self.coordinator, self.publish = coordinator, publish
        self.current, self.applied = {}, {}
        self.closed = False

    def request(self, kind, identity, epoch, loader):
        if self.closed:
            raise RuntimeError('read owner closed')
        self.current[kind] = (identity, epoch)
        self.coordinator.retire()
        return self.coordinator.request(self, kind, identity, epoch, loader)

    def accepts(self, token):
        return (not self.closed and not token.cancelled
                and self.current.get(token.kind) == (token.identity, token.epoch)
                and token.generation > self.applied.get(token.kind, -1))

    def invalidate(self):
        self.current.clear()
        self.coordinator.retire()

    def close(self):
        self.closed = True
        self.invalidate()


class ReadCoordinator:
    def __init__(self):
        self.loop = asyncio.get_running_loop()
        self.context = copy_context()
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='tui-read')
        self.sequence = count(1)
        self.active, self.pending = {}, OrderedDict()
        self.closed = False

    def owner(self, publish):
        return ReadOwner(self, publish)

    def request(self, owner, kind, identity, epoch, loader):
        token = Token(owner, kind, identity, epoch, next(self.sequence), loader, self.loop.create_future())
        key = (kind, identity)
        old = self.pending.pop(key, None)
        if old:
            old.cancel()
        self.pending[key] = token
        self._pump()
        return token

    def retire(self):
        # Retire active subscriptions permanently as well: selecting A -> B -> A
        # must not resurrect A's original result. Its physical slot stays active.
        for token in self.active.values():
            if not token.owner.accepts(token):
                token.cancel()
        for key, token in list(self.pending.items()):
            if not token.owner.accepts(token):
                self.pending.pop(key)
                token.cancel()

    def _pump(self):
        if self.closed:
            return
        self.retire()
        for key, token in list(self.pending.items()):
            if len(self.active) >= 4:
                break
            if key in self.active:
                continue
            self.pending.pop(key)
            self.active[key] = token
            future = self.executor.submit(token.loader)
            # This callback observes physical completion, never an asyncio wrapper.
            future.add_done_callback(lambda future, key=key, token=token: self._completed(key, token, future))

    def _completed(self, key, token, future):
        try:
            self.loop.call_soon_threadsafe(self._finish, key, token, future, context=self.context)
        except RuntimeError:
            pass  # loop already shut down; there can be no publication

    def _finish(self, key, token, future):
        self.active.pop(key)
        try:
            value, error = future.result(), None
        except Exception as exc:
            value, error = None, exc
        try:
            if not self.closed and token.owner.accepts(token):
                token.owner.applied[token.kind] = token.generation
                token.owner.publish(token, value, error)
        finally:
            if not token.done.done():
                token.done.set_result(None)
            self._pump()

    def close(self):
        self.closed = True
        for token in (*self.pending.values(), *self.active.values()):
            token.cancel()
        self.pending.clear()
        self.executor.shutdown(wait=False, cancel_futures=True)
