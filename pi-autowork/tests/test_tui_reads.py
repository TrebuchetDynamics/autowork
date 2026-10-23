"""Deterministic read scheduler contracts, without Textual or live services."""
import asyncio
from pathlib import Path
import sys
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class ReadTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from pi_autowork.tui_reads import ReadCoordinator
        self.reads = ReadCoordinator()
        self.results = []
        self.owner = self.reads.owner(lambda token, value, error: self.results.append((value, error)))
        self.releases = []

    async def asyncTearDown(self):
        for event in self.releases:
            event.set()
        self.reads.close()
        await asyncio.sleep(0)

    def blocked(self, value):
        entered, release = threading.Event(), threading.Event()
        self.releases.append(release)
        def load():
            entered.set()
            if not release.wait(5):
                raise AssertionError('deadlock watchdog')
            return value
        return load, entered, release

    async def entered(self, event):
        self.assertTrue(await asyncio.to_thread(event.wait, 3), 'reader not entered')

    async def test_poll_coalesces_without_starving_active_publication(self):
        load, entered, release = self.blocked('first')
        first = self.owner.request('fleet', 'repo', 0, load)
        await self.entered(entered)
        for i in range(20):
            last = self.owner.request('fleet', 'repo', 0, lambda i=i: i)
        release.set()
        await first.wait()
        await last.wait()
        self.assertEqual(self.results, [('first', None), (19, None)])

    async def test_cancelled_wrapper_keeps_physical_slot_across_reopen(self):
        load, entered, release = self.blocked('obsolete')
        token = self.owner.request('log', 'repo', 0, load)
        await self.entered(entered)
        wrapper = asyncio.create_task(token.wait())
        await asyncio.sleep(0)
        wrapper.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await wrapper
        self.owner.close()
        replacement = self.reads.owner(lambda t, v, e: self.results.append((v, e)))
        load2, entered2, release2 = self.blocked('current')
        token2 = replacement.request('log', 'repo', 0, load2)
        await asyncio.sleep(0)
        self.assertFalse(entered2.is_set())
        release.set()
        await self.entered(entered2)
        release2.set()
        await token2.wait()
        self.assertEqual(self.results, [('current', None)])

    async def test_four_physical_reads_and_retired_queue(self):
        tokens = []
        for i in range(4):
            load, entered, release = self.blocked(i)
            tokens.append(self.owner.request(str(i), i, 0, load))
            await self.entered(entered)
        load, entered, release = self.blocked('retired')
        queued = self.reads.owner(lambda *args: self.fail('closed publication'))
        queued.request('fifth', 5, 0, load)
        queued.close()
        self.releases[0].set()
        await tokens[0].wait()
        await asyncio.sleep(0)
        self.assertFalse(entered.is_set())

    async def test_selection_epoch_and_errors_allow_retry(self):
        load, entered, release = self.blocked('stale')
        old = self.owner.request('task', 'old', 0, load)
        await self.entered(entered)
        self.owner.request('task', 'new', 0, lambda: 'also obsolete')
        current = self.owner.request('task', 'old', 0, lambda: 'back to old')
        release.set()
        await old.wait()
        await current.wait()
        self.assertEqual(self.results, [('back to old', None)])
        load, entered, release = self.blocked('old epoch')
        old = self.owner.request('task', 'new', 1, load)
        await self.entered(entered)
        def fail():
            raise ValueError('unreadable')
        bad = self.owner.request('task', 'new', 2, fail)
        release.set()
        await old.wait()
        await bad.wait()
        self.assertIsInstance(self.results[-1][1], ValueError)
        good = self.owner.request('task', 'new', 2, lambda: 'recovered')
        await good.wait()
        self.assertEqual(self.results[-1], ('recovered', None))


if __name__ == '__main__':
    unittest.main()
