---
name: git-commit-push
description: "Validate, commit and push attributable changes, or pull and merge upstream changes, when requested."
disable-model-invocation: true
---

# Git Commit Push

Read the [host contract](../COMMON.md).

Inspect status, diff, untracked files and upstream. Preserve unrelated edits and secrets. Run appropriate checks, stage explicit owned paths, inspect staged diff and commit coherent work. Push the configured upstream when authorized by this invocation; honor no-push/local-only. No force push, history rewriting, auto-stash or guessed merge resolution. Verify status and report exact commit/push and remaining paths. Use native Git, not Hermes worker commit helpers.

For pull, sync or merge requests (or arguments starting with `pull`, `sync` or `merge`), follow the bundled [pull and merge procedure](../../../skills/git-commit-push/references/pull-merge.md): fetch, check incoming files against dirty work, fast-forward or merge without rebasing, stashing or resetting, resolve conflicts without dropping either side's tests, re-run checks, and push only when the request asks for it.
