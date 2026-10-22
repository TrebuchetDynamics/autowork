# Unreachable Git objects: October 2026 report

Task: TOOLSET-315-36. Source: [Task Store v2](../project.md#task-store-v2-2026-10-20).

## Conclusion

Task-store validation now builds disposable objects outside the repository object
database. Existing unreachable objects remain. **Safety to re-enable automatic GC
is not established:** not every recorded worker candidate is reachable from a ref.
All discovered set-aside refs and recovery-checkpoint refs are reachable, but 58
recorded candidate IDs are reflog-only and one historical candidate is missing.

This is an inspection report, not cleanup or permission to change GC settings.
The audit ran no GC, prune, repack or ref deletion and did not remove `gc.log`.
No task records were changed for this report.

## Snapshot and method

The read-only snapshot completed at **2026-10-22 10:38:29 UTC**, using source baseline
`e7de9a6c71f36ceacf911d30e434db015b843816`. It inspected the canonical repository's
shared object database and refs from a linked task worktree. Concurrent writers
make the observations non-atomic; they are not a permanent inventory.

Commands used, with inherited `GIT_*` overrides removed and optional locks and
replacement objects disabled:

```sh
git count-objects -v
git fsck --full --unreachable --no-reflogs
git for-each-ref --format='%(objectname) %(refname)'
git rev-list --all
git rev-list --all --reflog
git cat-file --batch-check='%(objecttype)'
```

Unreachable commit subjects were read with `git log --no-walk=unsorted --stdin`.
Candidate membership was checked against the commit sets from `rev-list`, not
merely against object existence or a branch name saved in metadata. JSON discovery
covered 779 files in private worker slots, slot history and worker reports,
including previous attempts. Candidate IDs came from fields named `commit`,
`candidate` or `candidate_commit`; baseline and integration-only fields were not
counted as candidates. Raw runtime payloads, local identities and paths are not
published here.

## Object inventory

| Observation | Count |
| --- | ---: |
| Loose objects | 3,082 |
| Loose-object storage, KiB | 25,564 |
| Packed objects | 27,856 |
| Packs | 2 |
| Prune-packable objects | 58 |
| Garbage objects | 0 |
| Commits unreachable without reflogs | 2,046 |
| Trees unreachable without reflogs | 4,926 |
| Blobs unreachable without reflogs | 1,982 |

Of the 2,046 commits unreachable without reflogs, 133 are reachable through
reflogs and 1,913 are not. Unreachable totals include packed objects; they are
not a subset count of the loose-object row. `fsck` exited successfully; that does
not mean the repository contains no unreachable objects. `gc.log` was present
and left untouched.

## Remaining sources

Observed unreachable commit subjects:

| Subject category | Commits |
| --- | ---: |
| `worktree tasks` | 537 |
| `migration proof` | 2 |
| `production code under test` | 792 |
| `update` | 164 |
| `On main: autostash` | 40 |
| Other subjects, including merge histories | 511 |

The first two categories are historical outputs of the validation paths fixed
by this task. The remaining subjects show other retained histories, including
stash histories, but a subject alone does not identify the writer or establish
that its contents are disposable. Merge/rewrite-like histories are not assumed
to be failed probes simply because they are unreachable.

Source inspection identifies additional object-producing mechanisms outside
this task's fix:

- [`parallel_integrate.head_conflicts`](../../pi-autowork/engine/parallel_integrate.py)
  uses `merge-tree --write-tree` to inspect conflicts. Such probes can leave trees
  and conflict objects without publishing a ref.
- The [coordinator's stale-candidate check](../../pi-autowork/pi_autowork/coordinator.py)
  also uses `merge-tree --write-tree` to test mergeability.
- [`worker.base_tree`](../../pi-autowork/pi_autowork/worker.py) uses `mktree` to
  compute a planning-stripped tree for check caching. A tree ID in runtime metadata
  is not itself a Git ref.
- [Worktree closeout](../../pi-autowork/engine/worktree_closeout.py) builds snapshot
  blobs, trees and commits before publishing archive refs. Completed archives
  protect their contents; interruption before ref publication can leave objects
  without that protection.

These are verified mechanisms, not exact attribution of every unreachable object.
They were inspected, not changed or executed as cleanup by this task.

## Ref reachability

“Ref-reachable” means membership in the ancestry of the refs enumerated for the
snapshot. “Reflog-only” means membership in the reflog-inclusive commit set but
not the ref-only set. Missing objects are distinguished from existing unreachable
objects.

| Discovered preservation refs | Refs checked | Ref-reachable |
| --- | ---: | ---: |
| Set-aside refs | 150 | 150 |
| Archive refs | 4 | 4 |
| Recovery/checkpoint refs, including scrub checkpoints | 9 | 9 |

Every discovered set-aside tip and recovery checkpoint is therefore protected by
a ref in this snapshot, as are their ancestors. This does not prove coverage of
unrecorded or external checkpoints.

| Recorded candidate/commit IDs | Distinct IDs | Ref-reachable | Reflog-only | Missing |
| --- | ---: | ---: | ---: | ---: |
| All scanned sources, deduplicated | 354 | 295 | 58 | 1 |
| Slots, including previous attempts | 184 | 176 | 8 | 0 |
| Slot history | 169 | 118 | 50 | 1 |
| Worker reports | 93 | 93 | 0 | 0 |

Source groups overlap and must not be summed. The missing historical candidate
is `aa2ebce061bcef33f7a52fbc561af766505c6037`. Its presence in historical metadata
does not by itself establish corruption of current refs. Nevertheless, neither
a reflog-only candidate nor a missing candidate satisfies ref-backed retention.

## Validation fix and verification

The implementation retained from `0d1198ae` uses a temporary object directory,
with the repository object database as a read-only alternate, plus a temporary
index. All record, receipt and ancestry reads complete before temporary objects
are removed. Real migrations rebuild their durable tree and candidate normally;
the proof commit is never persisted. See the [TaskStore reference](../../pi-autowork/task-store.md).

Checks rerun against this attempt's source:

- `python3 -m unittest discover -s tests -p 'test_task_*.py'`: **70 passed**.
- `python3 -m unittest discover -s pi-autowork/engine -p test_task_store.py`:
  **10 passed**.

The CLI regression checks unchanged object counts, index bytes and refs during
working-tree validation, pending-edit preparation and task writes in a linked
checkout, and checks rejected validation. Migration cases verify no new objects
from a dry run and no unreachable proof commit after real conversion. These are
offline fixture results, not a claim that historical objects were removed.

## Remaining qualification

Before any separate decision to re-enable automatic GC, retention must be
reconciled for the reflog-only and missing historical candidates, and the
inventory must be refreshed. Non-JSON and external recovery artifacts were not
exhaustively searched. No preservation ref was added, moved or deleted by this
audit, and this report does not authorize any such operation. The task's full
merged-tree check and integration remain the coordinator's responsibility.
