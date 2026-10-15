---
name: git-pull-merge
description: "Fetch and integrate upstream changes into the current repository when requested."
disable-model-invocation: true
---

# Git Pull Merge

Read the [host contract](../COMMON.md).

Inspect status and branches before fetching. Preserve dirty work; never automatically stash, reset or discard it. Fast-forward when possible. For divergence, inspect history and apply the user-authorized merge with focused conflict resolution and checks; otherwise ask for the exact merge decision. Do not rebase or force-push implicitly. Report actual integration and unresolved conflicts.
