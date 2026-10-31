# Record edits

Disclosed reference for step 4 of [Blockers](../SKILL.md). Load it to apply an owner
answer or supported planning repair to one task record. The skill owns the write
location, the typed-field authority guard and the marked-block guard.

- Use `autowork tasks field ID LABEL VALUE` for `scope`, `touches`, `acceptance`,
  `checks` or `depends_on`, or a note such as a short dated `Owner decision`
  (`2026-10-21: ...`) or `Blocker resolution` (`<fingerprint from the item>; <producer
  task or decision evidence>`, the only edit that restarts a repeated quick hold). Move
  the task with `autowork tasks place ID Now|Next|"Needs decision" [--decision TEXT]`
  or `autowork tasks move ID up|down`, and replace it with `autowork tasks supersede ID
  --by OTHER --reason TEXT`.
- Set `live = "authorized"` (`autowork tasks field ID live authorized`) only on the
  owner's own explicit answer in this conversation, never from a worker's request, an
  earlier summary or a recommended choice. Authority lives only in typed fields; a
  note never grants it.
- An abandoned claim established by fresh activity checks or an explicit owner release:
  `autowork tasks release ID` removes its `Held by:` note, keeping acceptance,
  dependencies, candidate references, partial delivery evidence and pending checks.
  Successors are not unlocked by this: they still need the task's acceptance. A live
  claim stays with its current worker. Add or renew a task hold only when the user
  explicitly asks for that pause, using `autowork tasks hold ID --by "<who or what>"
  --until YYYY-MM-DD`; see the [task-hold policy](../../shared/TODO-WORKCENTER.md#task-holds-require-an-explicit-user-request).
  Observing a worker is not permission to create a hold. A record with a current
  `Held by:` note is answered, not open.
- Retirement without completion: supersede it by the task that replaces it, or, with
  no replacement, place it in `Needs decision` with an `Owner decision` that says it is
  cancelled; never close it as done. Check that `autowork tasks why ID` shows it is not
  selected.
- Rework within the same task keeps its ID, acceptance and the old candidate and report
  as history; the runner works from current sources, never restores the old snapshot or
  rewrites a failed report into a pass.
- An outside condition: record the decision, or the task that now owns it.
