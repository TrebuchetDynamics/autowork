---
name: git-commit-push
description: "Validate, commit and push attributable repository changes when delivery is requested."
disable-model-invocation: true
---

# Git Commit Push

Read the [host contract](../COMMON.md).

Inspect status, diff, untracked files and upstream. Preserve unrelated edits and secrets. Run appropriate checks, stage explicit owned paths, inspect staged diff and commit coherent work. Push the configured upstream when authorized by this invocation; honor no-push/local-only. No force push, history rewriting, auto-stash or guessed merge resolution. Verify status and report exact commit/push and remaining paths. Use native Git, not Hermes worker commit helpers.
