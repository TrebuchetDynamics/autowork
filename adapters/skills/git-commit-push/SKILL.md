---
name: git-commit-push
description: "Validate, commit and push attributable changes, or pull and merge upstream changes, when requested."
disable-model-invocation: true
---

# Git Commit Push

Apply the [shared Ponytail method](../../../skills/shared/PONYTAIL.md) within this workflow's scope.

Use the [ASD-STE100 and project language rules](../../../skills/shared/COMMUNICATION.md) for user-facing text.

Read the [host contract](../COMMON.md).

Inspect status, diff, untracked files and upstream. Preserve unrelated edits and secrets. Run appropriate checks, stage explicit owned paths, inspect staged diff and commit coherent work. Before pushing, sync by default: fetch and merge the upstream (fast-forward, else a merge commit; never rebase or stash) and re-run checks on the merged tree, unless the request says no pull, no sync or ff-only. Push the configured upstream when authorized by this invocation; honor no-push/local-only. No force push, history rewriting, auto-stash or guessed merge resolution. Verify status and report exact commit/push and remaining paths. Use native Git, not Hermes worker commit helpers.

For pull, sync or merge requests (or arguments starting with `pull`, `sync` or `merge`), and for the default sync, follow the bundled [pull and merge procedure](../../../skills/git-commit-push/references/pull-merge.md): fetch, check incoming files against dirty work, fast-forward or merge without rebasing, stashing or resetting, resolve conflicts without dropping either side's tests, re-run checks, and push only when the request asks for it.
