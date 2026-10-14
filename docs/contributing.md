# Adding and updating skills

Source: [command discovery](../__init__.py) and [native provisioning](../install_skills.py).

## Work on a repository task

Read README.md, AGENTS.md and TODO.md. TODO owns scope, acceptance, dependencies
and progress; an existing goals.json is its synchronized index, not another board.
Select a ready task within the accepted scope, inspect actual workspace/process
activity and preserve unrelated changes. Use an isolated branch/worktree when
concurrent work needs isolation. No Hermes profile, Kanban card, native worker or
additional public tracking file is required, including recovery of older work.

Make a scoped change, run the task's acceptance checks and affected offline tests,
and submit normal repository review. Required independent review remains required;
review-requested changes and integration use ordinary Git/project tools. Commit only
attributable verified work under existing authority, then reconcile task evidence and
any existing index. Archive a completed body only when its acceptance is verified.
Do not equate a local commit or successful check with live qualification or publication.

Autowork automates that same current-session path. Its private coordination receipts
are not product requirements. Honor explicit task/caller limits and real runtime
controls; recurring jobs cannot replenish exhausted allocations. Local advisory
locks do not exclude manual writers ignoring them or provide cross-host exclusion.

## Add or update a skill

```text
skills/
  my-skill/
    SKILL.md
    references/   # optional
    scripts/      # optional
```

Use a folder name of 1–32 lowercase letters, digits, hyphens, or underscores,
starting with a letter or digit. The folder determines the command name; keep
the skill's frontmatter `name` consistent with it. Workflow commands and their
aliases are registered explicitly in `workflow_commands.py`. Underscores become hyphens
in CLI commands and Telegram uses underscores: `my_skill` becomes `/my-skill`
in CLI chat and `/my_skill` in Telegram. `my-skill` and `my_skill` cannot coexist.

Every immediate child containing `SKILL.md` is discovered at plugin startup.
Folders without that file are ignored. Invalid names, ambiguous aliases, or
skill paths pointing outside the bundle cause an explicit plugin-load error.

For a GitHub installation, publish your skill changes and run:

```sh
hermes plugins update hermes-toolset
hermes gateway restart
```

Follow any Hermes request to stop a running gateway before updating. For a local
symlink installation, edit this checkout and restart instead. New commands are
discovered on startup, not watched live. Telegram's menu has limited capacity;
Hermes controls which commands appear there.


## Portable hosts

Codex and Pi load [portable adapters](../adapters/skills/COMMON.md), not the Hermes
entry point. Add or update the corresponding adapter and its local references;
Pi commands are declared in [adapters/pi.mjs](../adapters/pi.mjs). Validate both
package metadata and command dispatch using [the cross-host checks](cross-host.md#behavior-and-verification).
Installing or updating Hermes does not install the Codex or Pi package.
