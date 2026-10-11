# Adding and updating skills

Source: [command discovery](../__init__.py) and [native provisioning](../install_skills.py).

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
the skill's frontmatter `name` consistent with it. Underscores become hyphens
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

