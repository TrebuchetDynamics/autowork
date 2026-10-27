# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in the [`tasks/`](tasks/) store. This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-401-cd15e01e — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-401-cd15e01e — Repair the headless fleet pilot label-publication timeout that also fails alone
- Needs: worker reported a blocker: Explicit product-scope authorization is still required. Permit a bounded lifecycle/publication repair in Src/pi_autowork/tui.py plus one deterministic regression case, and remove the conflicting product-repair exclusion. ReadScreen.read (lines 119-125) admits label work while BrowseScreen is current but mounting; ReadScreen._read_done (lines 128-130) discards its valid completion while is_mounted …
- Since: 2026-10-27T22:28:20Z
- Answer: Answer in tasks/items/TOOLSET-401-cd15e01e.md with the evidence or a dated `Owner decision:` deferral. Supply the actual missing input, handoff or evidence described in the failure reason; add a producer task and dependency if needed. Keep the task in Needs decision if the input is unavailable; preserve the acceptance criteria, live authorization and ownership gates. A record edit does not supply signatures or transfer live ownership, and does not by itself establish that the blocker is resolved.
- Kind: held

<!-- pi-autowork:questions:end -->

None.

## Engineering holds

Technical incidents remain visible in the runner status and fleet view; they are not owner
questions. A failed review, a dead worker, a merge conflict or exhausted reviewer rework
stays here as Agent repair until normal verification clears it. No such incident asks the
owner to decide whether incorrect work is acceptable.

## Resolved

None.
