# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in the [`tasks/`](tasks/) store. This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-401-cd15e01e — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-401-cd15e01e — Repair the headless fleet pilot label-publication timeout that also fails alone
- Needs: worker reported a blocker: Scope decision required: authorize a bounded product lifecycle repair in Src/pi_autowork/tui.py and deterministic regression coverage. Investigation establishes directory-label results are admitted while BrowseScreen is current but still mounting, then discarded by ReadScreen._read_done at lines 128-130 because is_mounted is false. RepoTree._populate_node at lines 984-992 submits the work, ReadScr…
- Since: 2026-10-27T19:06:43Z
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
