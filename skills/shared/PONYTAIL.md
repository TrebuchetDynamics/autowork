# Ponytail for every Autowork skill

Apply Ponytail's **smallest complete change** method within the selected workflow,
including planning, documentation, design, review and operations. This is shared
instruction, not a second workflow or permission to implement. Questions-only,
read-only, task scope, approval, review and delivery limits still govern.

## Choose the smallest complete result

Read the task and the connected source first. Account for callers, tests, fixtures,
exports and configuration. Omit unrequested extras; reuse existing project code
and document owners; then prefer standard library/platform features, installed
dependencies, and finally minimal readable new code. Preserve project conventions.
Never cut accepted behavior, trust-boundary validation, data-loss handling,
security, accessibility or required checks to make the result smaller.

For material coding/design choices, read the pinned
[Ponytail protocol](../ponytail/upstream/skills/ponytail/PROTOCOL.md) once per task;
apply it to the proposal when implementation is not authorized. For non-code work,
apply the same reuse/scope principle to its existing artifacts; do not invent code,
tests, audits or debt ledgers. Trivial work needs no extra ceremony. Record material
reuse/omission decisions in the existing plan or receipt, not a new tracking system.
Report checks actually run, anything important not checked, and residual risk.

## Scope and levels

Default to `full` within Autowork workflows. An explicit `lite`, `full`, `ultra` or
`off` preference wins and travels with delegated work. `off` disables this optional
method, not repository safety or acceptance requirements. With no argument,
`ponytail` reports the current preference (or `full`); an explicit level changes
only the conversation's Autowork preference. Do not write mode/config files or
change unrelated skills. No startup hook, persistent activation, band UI, transcript
import, telemetry or upstream plugin installation is part of this bundle.

These scope rules override upstream session-wide activation and host-specific setup
instructions. Resolve resources from this file's directory, never another profile
or an assumed plugin namespace. A separately installed Ponytail plugin is neither
required nor removed. Use this pinned copy unless the user explicitly selects an
alternative, then identify its verified source and gaps.

## Review and discovery

Apply the pinned [review criteria](../ponytail/upstream/skills/ponytail-review/PROTOCOL.md)
in the existing required review lane: correctness, safety, expected load, tests,
speed, then unnecessary complexity. Do not spawn an extra reviewer or claim approval
merely because the diff is lean. Standalone review/audit/debt commands report only;
`Ship` is an assessment, not permission to commit, push, deploy or close a task.

Prefer the host's repository search. When a compact reuse index would help and Node
is available, optionally run the bundled read-only helper (resolve to an absolute
script path; quote both paths):

```sh
node "<loaded skills>/ponytail/upstream/scripts/ponytail-map.cjs" "/path/to/project"
```

It is a regex hint, not a complete parser or security audit. In Git it lists tracked
files; with no tracked files or a Git failure it falls back to a bounded directory
walk that does not honor all ignore rules. It can omit symbols, filenames and
untracked work. Use it only on the intended source tree, inspect relevant callers
with normal search, and never infer absence from an empty map. No Node: use native
search; the skills themselves need no runtime dependency.

[Pin and hashes](../ponytail/UPSTREAM.json) · [MIT license](../ponytail/upstream/LICENSE).
Offline routing tests prove instruction delivery, not model adherence or savings.
