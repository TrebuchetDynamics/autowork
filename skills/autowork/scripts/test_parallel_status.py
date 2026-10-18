"""Large queue regression at the status and dispatch entry points; no live workers."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import parallel_status as status
import task_execution as execution


class LargeQueueTests(unittest.TestCase):
    def test_large_queue_status_is_unchanged_and_dispatch_releases_its_lock_promptly(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            todo = '## Now\n' + ''.join(
                f'- [ ] T-{i:03} — task {i}\n  Scope: file{i}.py\n  Acceptance: works\n'
                f'  Checks: test {i}\n  Dependencies: OLD\n'
                f'  Evidence: {"." * 3072}\n' for i in range(80))
            self.assertGreater(len(todo.encode()), 250_000)
            (repo / 'TODO.md').write_text(todo)
            (repo / 'TODO.archive.md').write_text('## Done\n- [x] OLD — prerequisite\n')
            subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Fixture',
                            '-c', 'user.email=fixture@local', 'commit', '-qm', 'fixture'], check=True)
            start = time.monotonic()
            with patch.object(execution, 'select', wraps=execution.select) as select:
                value = status.snapshot(repo, now=100)
            self.assertLess(time.monotonic() - start, 1.5)
            rows = [dict(task=f'T-{i:03}', state='waiting', slot=None, elapsed_seconds=0,
                         reason='awaiting dispatch', worktree=None, checks=None, commit=None,
                         integration=None, attempt=0, worker_live=False, blocked_by=[]) for i in range(80)]
            self.assertEqual(value, dict(outcome='PARALLEL_STATUS', workspace=str(repo),
                active_workers=0, max_workers=0, tasks=rows, roots=[], completed=0, failed=0,
                integration_queue=0, metrics=dict(wall_seconds=0.0, worker_seconds=0.0,
                integration_seconds=0.0, waiting_seconds=0.0, peak_workers=0, conflicts=0, retries=0)))
            self.assertEqual(select.call_count, 0)  # one eligibility pass, not 80 selections
            start = time.monotonic()
            process = subprocess.run([sys.executable, str(Path(execution.__file__).with_name('owner_cycle.py')),
                str(repo), '--apply', '--parallel', '2', '--owner-pid', str(os.getpid()),
                '--worker-command', '["python3", "-c", "pass"]', '--min-free-mem-mb', str(2 ** 50)],
                capture_output=True, text=True, timeout=15)
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            self.assertEqual(json.loads(process.stdout)['dispatched'], [])
            self.assertLess(time.monotonic() - start, 3)
            with execution.lock(repo / '.git/autowork-execution/dispatch.lock'):
                pass


if __name__ == '__main__':
    unittest.main()
