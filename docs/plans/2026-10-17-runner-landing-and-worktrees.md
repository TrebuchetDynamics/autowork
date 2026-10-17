# Runner landing and worktree hygiene (plan, 2026-10-17)

Owner request (2026-10-17): audit whether the fleet's runners use `.worktrees/`
correctly and merge into main after each task, then plan improvements. Everything
below the audit is the planner's call unless marked otherwise.

## Audit (read-only, 2026-10-16 23:47 to 2026-10-17 00:05)

Runners: five `pi-autowork@` services (charlie, bravo, india,
sierra, and hermes-toolset itself since 22:58), all on the Pi package at `4192b13`
since about 23:47. That release has `.worktrees/` placement (`adedf58`) and landing
after each closed task (`fd7ec65`), not `c00a110` (auto-work commits, atomic close).
From 22:36 to 23:47 all four fleet runners ran a pinned candidate (`3848aaa`) that
had neither.

| Repository | Worktrees (`.worktrees` / state dir / set-aside) | Session vs main | main vs origin | Uncommitted in main |
|---|---|---|---|---|
| charlie | 31 (8 / 15 / 11) | 7 ahead, 4 behind | 72 ahead | 0 |
| bravo | 39 (1 / 15 / 8) | 29 ahead | 5 ahead, 19 behind | 10 |
| india | 27 (5 / 5 / 4) | level | 39 ahead | 0 |
| sierra | 37 (4 / 16 / 11) | 20 ahead, 2 behind | 46 ahead | 4 |
| hermes-toolset | 18 (13 / 3 / 0) | 4 ahead, 6 behind | level | 7 |

Findings:

1. **Placement is partial.** New sessions and task worktrees go in `.worktrees/`
   (charlie, india). Sessions started before `adedf58` (bravo,
   sierra, hermes-toolset) and every older task worktree stay in the state directory;
   [worktree placement](../worktree-placement.md) keeps existing paths "until
   explicitly moved", and nothing moves them.
2. **Set-aside worktrees pile up.** 34 worktrees exist only for `-set-aside-N`
   branches, whose work is already preserved on the branch. Cleanup of merged task
   worktrees works (one leftover, bravo).
3. **Landing after each task is not yet observed.** In the two hours audited, every
   merge into main happened at a runner's stop (the shutdown merge of the pinned
   code, "not pushed"); no task closed between the 23:47 restart and the audit, so
   `fd7ec65`'s land-after-close has no live evidence yet.
4. **Merges stay pending for hours with no alarm.** bravo (8 pending merges in
   2 h: the owner's uncommitted README.md, TODO.md, goals.json and plans in the main
   checkout) and sierra ("conflicts with main in: ." from an uncommitted
   `tasks/plan.md` left in its session worktree). Health and the TUI show neither.
   `c00a110` commits both kinds once the runners update to it.
5. **Nothing was ever pushed.** Three mains are 39 to 72 commits ahead of origin;
   bravo's main has diverged from origin (5 ahead, 19 behind). The first push
   after the update will carry dozens of commits, and bravo's will be
   rejected and need the fetch-merge retry.

## Goals and anti-goals

- Goal: every closed task reaches main and origin within one cycle, or the owner
  sees exactly why in health, the TUI and BLOCKERS.md.
- Goal: every runner-created worktree lives in `.worktrees/`, and none outlives the
  work it holds.
- Anti-goal: deleting unpushed or uncommitted work to tidy up; force-pushing;
  editing the owner's files to make a merge pass.
- Constraint: ht2 owns the runner log output and the TUI log view (`fleet_view.py`,
  `tui.py` log parts) and `update_toolset`/`release.py`; these tasks avoid them.

## Approach (planner's calls)

- Record landing state where health already lives (`status.json`): commits ahead of
  main, since when, the last merge result and the last push result. Alarm on age,
  not on a single failed merge, because a quiet-period wait is normal.
- Move rather than recreate: `git worktree move` the session when nothing is in
  flight; remove set-aside worktrees once their branch is preserved. Dirty worktrees
  are never removed, only reported.
- One read-only `autowork audit` command reproduces this audit, so the next audit
  is one command, not an hour of shell.
- Qualify on the live fleet separately; offline tests do not prove landing.

## Tasks

TOOLSET-125-3c (landing health), TOOLSET-126-02 (worktree hygiene), TOOLSET-127-8f
(`autowork audit`), TOOLSET-128-89 (first push of a long-local main) and
TOOLSET-129-6c (fleet qualification) in [TODO.md](../../TODO.md).
