# Skill standard

The bar every skill in `skills/` and `adapters/skills/` meets. It adapts
mattpocock/skills, whose own rules live in its `AGENTS.md`,
`.agents/invocation.md`, `.agents/writing-docs.md` and
`skills/productivity/writing-for-agents/`. Load
[Writing For Agents](../skills/writing-for-agents/SKILL.md) for an editing pass; this
page is the review checklist.

Provenance: the repository layout, frontmatter, invocation and description rules are
from [mattpocock/skills](https://github.com/mattpocock/skills) at the revision pinned in
each `UPSTREAM.json`. Where Autowork differs, the difference is stated below rather
than silently copied.

## 1. One job, stated in the description

The description names what the skill does in one sentence, under the 60-character index
limit. It is a summary, not a trigger list: no "Use when the user…". A reader browsing
commands must know the job without loading the file.

*Why:* every entry here is user-invoked (Hermes registers it as a command, portable
hosts disable model invocation), so the description is read by a person, not a router.

## 2. Boundaries before overlap

Every skill carries a `## Boundaries` section that names what it does not do and which
sibling to use instead, by command name. Sibling pairs that must stay distinct:

| Question | Skill |
| --- | --- |
| Plan interactively, or investigate and save a plan | `plan-with-me` / `plan-for-me` |
| Stress-test any idea, challenge a plan, record decisions | `grilling` / `grill-me` / `grill-with-docs` |
| Implement one task, improve many lanes, review architecture | `autowork` / `autonomous-codebase-improver` / `improve-codebase-architecture` |
| Hunt a bug, remove dead code, shrink a suite | `bug-harvest` / `unused-code` / `test-optimizer` |
| Commit and push, review a change, audit a repository | `git-commit-push` / `ponytail-review` / `ponytail-audit` |

## 3. Done is checkable

Each skill ends on a `**Done when:**` line the agent can evaluate, plus the receipt it
already reports. "Understanding reached" is not a criterion; "frontier empty and the
owner confirmed" is.

## 4. Steps first, reference behind a pointer

The body reads as an ordered sequence. Material only some branches need moves into
`references/` behind a live link, and the pointer names the branch that should load it.
Inline what every branch needs. A file that mixes both without pointers is sprawl.

## 5. One meaning, one home

State a rule once, in the owner file, and point from elsewhere. Pinned upstream bytes
stay byte-exact; local policy lives in the adapter. Do not restate a sibling skill's
mechanic: load it.

## 6. Positive instruction with a leading word

State the target behaviour, not the prohibition, unless the guardrail cannot be phrased
positively. Reach for a pretrained word (_frontier_, _no-op_, _deep module_) over a
spelled-out triad.

## 7. Handoffs name the command

A step that needs another skill says so as a command the host exposes: "run
`/docs-sync`", "load `autowork:docs-sync`" in a message. Upstream can say "call the
Skill tool"; our hosts have commands, so the adapter states the composition directly.

## 8. Evidence, then claim

Every skill separates what it read, what it changed and what it ran. Offline checks
never qualify a live run, a rendered artifact or model behavior.

## 9. Adapters stay thin

`adapters/skills/<name>/SKILL.md` names the host contract, links the host-neutral
skill, and adds only host mechanics: explicit-only invocation, `agents/openai.yaml`,
tool names. It does not restate the workflow or drift into policy of its own.

## 10. Deletion is a valid outcome

A skill whose job a sibling already does is a candidate for removal, not a rename. The
repository keeps one owner per job.

## 11. Dispatched work starts fresh

A skill that dispatches a subagent or worker says to start it in a fresh context
window, states its scope and completion criterion, and marks a read-only run as
read-only. A fork inherits the context the dispatch was meant to escape.

*Source:* the upstream repository's `AGENTS.md` states this for every skill.

## 12. One map over the set

A growing set of user-invoked skills needs one router skill that names the others and
when to reach for each: `ask-autowork` here, upstream's `ask-matt`. The router is
orientation, never authority, and it reads a skill's `SKILL.md` before describing it.

*Source:* upstream `.agents/invocation.md` (router skills) and
`skills/engineering/ask-matt`.

## Deliberate differences from upstream

- **No bucket split.** Every folder is discovered; `skills/shared/` holds contracts and
  is not a skill.
- **No per-skill docs page or published URL.** `docs/workflows.md` and
  `docs/cross-host.md` carry the human-facing description and host invocation.
- **No em-dash ban and no changeset tool.** ASD-STE100 rules in
  [shared/COMMUNICATION.md](../skills/shared/COMMUNICATION.md) own prose style.
- **Pinned vendoring.** Upstream bytes live under `upstream/` with `UPSTREAM.json`
  hashes and the license; policy lives in the local adapter.

## Review checklist

- [ ] Description is a one-sentence summary under 60 characters, with no "Use when…".
- [ ] `## Boundaries` names the real siblings by command.
- [ ] `**Done when:**` is checkable from the conversation or the repository.
- [ ] Steps are in order; branch-only reference sits behind a live pointer.
- [ ] No rule is stated twice in the repository, and no sibling's mechanic is restated.
- [ ] Handoffs name a command the host exposes.
- [ ] Claims stop at executed evidence.
- [ ] The adapter adds host mechanics only.
- [ ] A dispatching skill says to start the child in a fresh context window.
- [ ] The router (`ask-autowork`) lists the skill, and the skill's Boundaries name
      the sibling a confused caller should use instead.
- [ ] Checks pass: `python3 scripts/check.py tests/test_skill_standard.py` plus the
      modules that read the touched files.
