# Ponytail inside Autowork

Apply the bundled [shared Ponytail method](../../shared/PONYTAIL.md) to the selected
task. Autowork keeps task ownership, acceptance, the existing review lane and
delivery authority. The pinned suite ships with every host; no separate plugin,
profile change or persistent mode is needed.

For material implementation choices, load the bundled
[Ponytail protocol](../../ponytail/upstream/skills/ponytail/PROTOCOL.md) once.
Respect an explicit level (including `off`) in delegated contracts and review;
otherwise use `full` within the task. Reuse instructions already read for the same
task and revision. Trivial edits use the shared method without ceremonial receipts.

Carry a material decision in the existing contract/receipt:
`Ponytail: source=<verified revision>; decision=<choice>; reuse=<paths>;
omitted=<unneeded extras or none>; check=<command/result or pending>.`
Record actual checks only after running them. Revisit decisions only when the
inputs or evidence change; no separate ledger or repeated repository audit.

The existing reviewer uses the bundled
[review protocol](../../ponytail/upstream/skills/ponytail-review/PROTOCOL.md), not an
extra review agent. Findings name a concrete failing case, location, smallest fix
and consequence. Fix in-scope acceptance failures and rerun affected checks.
Optional or out-of-scope findings return to the coordinator for deduplication in
the existing backlog. Retain exact candidate identity, independent review and
completion gates; a leaner diff is not review approval.

If bundled resources are missing, report the packaging gap and use the shared
method and repository checks without claiming upstream execution. Missing required
execution/review capability still blocks its own gate. A user-selected external
version needs verified provenance and disclosed gaps, not an assumed namespace.
Offline tests verify instruction delivery, not live worker adherence, product
acceptance or measured token/time savings.
