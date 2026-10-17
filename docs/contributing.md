# Adding and updating skills

Source: [command discovery](../__init__.py) and [native provisioning](../install_skills.py).

## Work on a repository task

Read README.md, AGENTS.md and TODO.md. TODO owns scope, acceptance, dependencies
and progress; an existing goals.json is its synchronized index, not another board.
Select a ready task within the accepted scope, inspect actual workspace/process
activity and preserve unrelated changes. Use an isolated branch/worktree when
concurrent work needs isolation. No Hermes profile, Kanban card, native worker or
additional public tracking file is required, including recovery of older work.

Make a scoped change, run the task's acceptance checks and affected offline tests
(`python3 scripts/check.py`; it does not run `node --test tests/portable_pi.test.mjs`),
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
the skill's frontmatter `name` consistent with it (enforced only for portable
adapters). Most folders are registered automatically; `workflow_commands.py`
registers both spellings for Plan With Me, Plan For Me and Docs Sync, and
`autoresearch_commands.py` registers the research selectors. Underscores become hyphens
in CLI commands and Telegram uses underscores: `my_skill` becomes `/my-skill`
in CLI chat and `/my_skill` in Telegram. `my-skill` and `my_skill` cannot coexist.

Every immediate child containing `SKILL.md` is discovered at plugin startup, except
the retired `repo-docs` and `repo-interview`; `grill-me` gets a command but no
separate skill identity while `plan-with-me` exists. Folders without `SKILL.md` are
ignored. Invalid names, ambiguous aliases inside the bundle, or skill paths pointing
outside it cause an explicit plugin-load error. A clash with an existing Hermes or
plugin command only logs a warning and skips that command.

For a GitHub installation, publish your skill changes and run:

```sh
hermes plugins update autowork
hermes gateway restart
```

For a local symlink installation, edit this checkout and restart instead. New commands are
discovered on startup, not watched live. A restart does not refresh a skill already
copied into the profile's native skill directory; use `/autowork update` for that.
Telegram's menu has limited capacity; the bundle prioritizes only the five workflow
commands in [`telegram_menu_policy.py`](../telegram_menu_policy.py).


## Portable hosts

Claude Code, Codex and Pi load [portable adapters](../adapters/skills/COMMON.md), not
the Hermes entry point. Add or update the corresponding adapter and its local
references; every adapter keeps `disable-model-invocation: true` and an explicit-only
`agents/openai.yaml`. Pi commands are declared in [adapters/pi.mjs](../adapters/pi.mjs);
the Claude Code marketplace entry in `.claude-plugin/marketplace.json` lists the
adapters folder. Validate both
package metadata and command dispatch using [the cross-host checks](cross-host.md#behavior-and-verification).
Installing or updating Hermes does not install the Codex or Pi package.
