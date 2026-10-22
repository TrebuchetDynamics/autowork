# Pi Autowork component

The `pi-autowork` runner. `scripts/pi-autowork.sh` is a thin entry point and the
service command: it finds this component and runs `pi_autowork/cli.py`, which then
continues in the toolset release it resolves. The generic task lifecycle (admission, slots,
integration, closure) stays in the shared engine under `pi-autowork/engine`,
which is the only authority for task state. Runtime state lives outside the
repository, under `${XDG_STATE_HOME:-~/.local/state}/pi-autowork/<repository key>/`.

| Module | Role |
| --- | --- |
| `engine/task_store.py` | Read-only, pinned-commit TaskStore; [schema and API](task-store.md). Not yet wired into consumers |
| `pi_autowork/cli.py` | Options, repository and toolset resolution (one release per run), `--status`, `--dry-run`, `--fleet`, `--set-aside`, the runner lock |
| `pi_autowork/coordinator.py` | The loop: engine lease owner, session branch and final merge, settle and close, requests, priority drift, Touches proposals and widening, health, self-update and restart, graceful stop |
| `pi_autowork/worker.py` | The engine-launched `--worker` and `--verify` modes |
| `pi_autowork/service.py` | `--install-service` / `--remove-service` for `pi-autowork@<repository>.service` |
| `pi_autowork/common.py` | Logging, Git helpers and task lifecycle words |
| `pi_autowork/pi_runtime.py` | Runs one Pi job: model choice and fallback, bounded retries, timeouts, redacted `runs.jsonl` records of each run's tokens and billing provenance (the production CLI path; the TOOLSET-117-cb boundary is an isolated comparison spike, not wired into this runner) |
| `pi_autowork/accounting.py`, `scorecard.py` | Private run/owner-time accounting and read-only scorecard aggregation; unknown billing is never priced or treated as zero |
| `pi_autowork/health.py` | Per-runner `status.json`, one stall announcement per episode with its root blockers, and the `--fleet` view |
| `pi_autowork/workspaces.py` | Mirrors `PI_AUTOWORK_LINK_PATHS` gitignored dependencies into task and review worktrees (real directories, hard-linked files) |
| `pi_autowork/fleet_view.py` | Every runner on the machine (tmux sessions, `pi-autowork@` services, `status.json` health), its worker lanes (engine slots in flight, the runner's latest phase line, the Pi transcript's last action), its blockers grouped by kind, recent logs, and the exact existing command behind each action; standard library only |
| `bin/autowork`, `pi_autowork/command.py` | The `autowork` command (below), standard library only |
| `pi_autowork/tui.py` | The `autowork` TUI (Textual, run through `uv`): live runners with what each needs (the owner's open BLOCKERS.md questions, else its first blocker), worker lanes, model and log, stacked full width so it reads on an 80-column terminal, a directory browser that starts services, and keys that run `autowork` commands; `--view-only` disables the keys |
| `pi_autowork/tui_web.py` | `autowork web`: serves the TUI to a browser with textual-serve, on 127.0.0.1 by default |
| `pi_autowork/questions.py` | The owner's questions block in `BLOCKERS.md`, built from the engine status without a model |
| `pi_autowork/release.py` | Safe-checkpoint test before a self-update: fleet idle, and the new release reads current state |

## The autowork command

`autowork` runs, watches and controls the runners on this machine. A repository's
runner is a systemd user service, `pi-autowork@<repository name>`; a target is a runner
name, a repository path or `.`. Nothing here calls a model.

| Command | What it does |
|---|---|
| `autowork` | The live TUI on a terminal (help otherwise) |
| `autowork start [dir]` | Install (if needed) and start the repository's service; refuses a directory without a committed `tasks/` store and its main branch checked out, saying what is missing (an unconverted repository: `autowork migrate`). Services run from the Pi package installed from `git:github.com/TrebuchetDynamics/autowork`; a service on another copy (a package under an older name) is moved onto it and restarted, and the others follow at their next restart |
| `autowork stop [target]` | Stop the service; workers pause and resume on the same attempt |
| `autowork restart [target] [--stop-workers]` | Reload the runner in place on its current release and settings; running workers keep running. `--stop-workers` restarts the service instead, pausing them |
| `autowork pause` / `resume [target]` | Stop the service and keep it off, also after a reboot (disable), or start it again (enable); only a paused service is listed as `paused`, any other stopped one as `not running` |
| `autowork model [target] [provider/model] [--fallback provider/model]` | Show or set this service's Pi model (checked against Pi's list), then reload it |
| `autowork models [search]` | Pi's model list (`pi --list-models`); an empty catalog is an actionable error, never `No/models` |
| `autowork setup-portal --provider NAME --model ID [--endpoint URL] [--apply] [--json]` | Preview a selected Pi provider for the local Hermes Nous proxy; only `--apply` consents to configuration, never a proxy/service start |
| `autowork ls [--long]` | One colored line per runner; `--long` adds its workers in flight, blockers and model |
| `autowork status [target]` / `logs [-f] [target]` | The runner's full status; its journal |
| `autowork remove [target]` | Stop and remove the service; state and worktrees stay |
| `autowork run [dir]` | Run the runner in the foreground here, for debugging |
| `autowork web [--port N] [--host H] [--view-only]` | The TUI in a browser at `http://127.0.0.1:8765` (this machine only); `--view-only` disables control keys |
| `autowork blockers [dir]` | `/autowork blockers` in an agent (`AUTOWORK_AGENT`, else `claude`, else `pi`); records the session's elapsed owner minutes privately when the agent exits |
| `autowork attention MINUTES [--task ID] [--note TEXT] [target]` | Record other owner time (finite, nonnegative minutes); defaults to this repository, optionally attributed to one task. Notes stay private |
| `autowork tasks list\|validate\|new-id [target]`, `autowork tasks show\|why TASK [target]` | Read the `tasks/` store at HEAD (`validate --worktree`: uncommitted edits too) |
| `autowork tasks add\|field\|place\|move\|hold\|release\|done\|supersede\|goal ... [target]` | Edit task and goal files in the working tree, never committing: an owner answer (`field TASK "Owner decision" TEXT`, `"Blocker resolution"`), a section (`place`, optionally `--decision`), the priority (`move TASK up\|down` changes its rank), a hold (`hold --by`, `release`), a manual close (`done ID --by WHO --reason TEXT [--evidence REF]`, not verification), a new task or goal. Each write validates the whole store |
| `autowork tasks prepare [target] [--check\|--no-commit]` | What Docs Sync runs first: detect the store's state, convert or finish converting a TODO.md + goals.json repository, and report diagnostics with the command that repairs each, as JSON; `--check` writes nothing ([task store](task-store.md#preparing-a-repository-autowork-tasks-prepare)) |
| `autowork migrate [target] [--dry-run] [--no-commit]` | Convert a TODO.md + goals.json repository to `tasks/` once, in one local commit (`--no-commit`: staged); an interrupted run resumes; it refuses while work is in flight |
| `autowork scorecard [--days N] [--json \| --csv] [--baseline FILE] [target...]` | Per runner and overall over 1–30 days (default 7): labelled evaluation metrics, weekly breakdown and first-to-last-week changes; JSON retains closure, held-share, questions and task/attempt accounting details; no model call |

Before reusing an installed or running service, `autowork start` refuses if an
explicitly supplied supported service setting differs from its saved env file
(including a setting absent there).
For example, `PI_AUTOWORK_PUSH=0 autowork start` cannot silently start a service saved
with push enabled. The error names the conflicting settings and file and prints the
`--install-service` command to apply them; run it with the requested environment.
A refusal leaves the service and its pause marker unchanged. Matching settings keep
start idempotent; the default remains push enabled.

In the TUI each key is the first letter of its word, highlighted in the detail pane:
`l` (or Enter) **L**og, `p` **P**lay/**P**ause (starts a stopped service, resumes a
paused one, pauses a running one), `s` **S**top, `r` **R**estart, `m` **M**odel and
`f` **F**allback (from Pi's list, type to filter), `t` **T**asks, `u` **U**ninstall the
service, `n` **N**ew: browse directories (from `~/git`, `AUTOWORK_BROWSE_ROOT`), see which
repositories are ready or what they need, and `p` there plays one; `q` **Q**uit. The Tasks
window lists open tasks in priority order (section, then rank) with their short title, state and reason,
followed in All by closed tasks: **Verified** with the receipt, or **Manual** with the reason
(a missing/invalid verified receipt is explicitly warned, never relabelled Manual);
`1`–`5` (or Tab) show All, Working, Held, Waiting or Questions; on the selected task `u`/`d`
move it **U**p or **D**own (its rank is the priority), `s` to another **S**ection (Now,
Next, Needs decision), `c` **C**lears its hold, `a` sets it **A**side, `b` answers the
owner's **B**lockers in an agent, and `n` adds a **N**ew task from a form. Enter opens the
task: its question and the runner's suggested answer, its whole task record and its
worker's last actions. Answer it there, written to the task's record where the runner reads
it: `w` **W**rite a dated `Owner decision:` note, `d` **D**efer it to Needs decision with your
reason; a repeated quick hold takes `r` **R**esolve with the producer or decision. Stop,
restart, pause, uninstall, clear, set-aside and model changes ask first.
Terminal text can be selected by dragging with the mouse, then copied with your
terminal's copy shortcut (often Ctrl+Shift+C). Mouse capture is off by default;
keyboard navigation and controls remain available. Use `autowork tui --mouse` to
restore clickable rows/buttons instead; hold Shift while dragging if your terminal
or tmux intercepts selection. The browser view retains mouse controls.

The main-check line in runner status and the TUI reads the current check receipt,
not just the runner's cached health snapshot. A missing process or a reused PID
(with different process start ticks) reads `main check interrupted`, even if the
runner stopped before recording a result. A process without recorded start ticks
cannot be verified live and also reads `interrupted`. A verified live check reads
`running`; one queued for admission reads `waiting for a check slot`. A live check
past its execution budget reads `overdue` and `past timeout`; waiting does not
consume that budget. New slot receipts carry the command's configured timeout;
older receipts fall back to 3600 seconds. Each line names the checked revision;
a check of an older revision also reads `superseded by main at REV`.
A green result reads `main check passed at REV` for that revision only. If HEAD
has advanced, it reads `Last green: OLD · HEAD: NEW · verification pending`.
These are read-only displays: rendering never signals, cancels or restarts a check.

Manual closure is available for implementation, plan and inspection tasks, but writes no
receipt or passing-check claim. It alone qualifies neither a goal nor a prerequisite
explicitly listed in `verified_depends_on`. An authorized owner can record
`owner_waiver` or `owner_qualification` through `tasks field`; a met-goal write names
these exceptions. See [closure provenance and owner qualification](task-store.md#writing-and-autowork-tasks).

A task someone works on outside the runner carries a `Held by:` note
(`autowork tasks hold TASK --by WHO [--until DATE]`); the runner never starts it and asks
nothing about it. `autowork tasks release TASK` lifts the hold; a dated hold ends by itself.

The fleet lists runners with open owner questions or task-store setup/repair first,
then other runners; each group is alphabetical. An idle runner with open questions
reads `Waiting on you`, not `Idle`. The headline and Needs field follow the
read-only `autowork tasks prepare --check` result: no store reads
`Setup required — run /docs_sync`; a legacy TODO.md + goals.json
queue reads `Migration required — run /docs_sync`; an invalid store or interrupted
conversion reads `Task store needs repair`. Docs Sync prepares and reconciles the
store; `autowork migrate` remains available as direct CLI conversion recovery.

The TUI and web view run Textual 8.2.8 (and textual-serve 1.1.3) through `uv`.

## Nous Portal setup (opt-in)

Pi remains the executor; Hermes owns the Portal login and subscription proxy.
Installing Autowork does not configure this route. With a current Hermes supporting
`hermes proxy` and Pi's compatible-endpoint `models.json` format:

```sh
# Replace with an exact model ID available on your Portal plan (may contain /).
MODEL_ID='model-from-your-plan'
autowork setup-portal --provider nous-local --model "$MODEL_ID"
# Review the proposal, then explicitly consent to that provider edit only:
autowork setup-portal --provider nous-local --model "$MODEL_ID" --apply
```

In the TUI, **o — Nous Portal** opens the same setup before any service is required.
Enter the provider, exact model ID and endpoint, then Preview. The separate Yes/No
confirmation shows the proposal; No or Escape leaves configuration bytes unchanged.
View-only mode disables setup. `--json` exposes the same path, provider/model,
endpoint, prerequisite diagnostics, proxy state and applied flag to automation.

The default endpoint is `http://127.0.0.1:8645/v1`. `--endpoint` accepts only literal
`127.0.0.1` or `[::1]` HTTP addresses with a port and `/v1`; no remote hosts,
credentials, queries or redirects. Setup reads only local `/health`, without an
Authorization header or environment HTTP proxy. It does **not** request the upstream
model catalog, authenticate, refresh credentials, start/stop anything or call a model.
`available` means the expected Nous proxy reports stored authentication, **not** that
refresh, model access, billing or inference succeeded. Missing Pi/Hermes executables,
unavailable proxy, missing login and incompatible health responses have separate
messages. An unavailable proxy does not prevent preparing configuration for later use.

Only the selected provider under `${PI_CODING_AGENT_DIR:-~/.pi/agent}/models.json`
is prepared, using `openai-completions`, a non-secret `local-proxy-placeholder` key
and the exact model ID. Real credentials stay in Hermes. Other providers and settings
are preserved as JSON values (formatting may change). Existing models in that provider
are retained; changing its endpoint affects **all** its models. Only an existing entry
with this placeholder, compatible API and supported structure can be updated. Retained
model entries support `id`, `name`, `reasoning`, `input`, `contextWindow`, `maxTokens`
and complete nonnegative `cost` metadata. Other model fields, including `baseUrl`,
`api` and executable `headers`, are refused rather than silently overriding the
selected provider route. Provider-level `modelOverrides` are also refused. The same
validation runs before runtime model selection, including after manual config edits.
Conflicting keys/headers/API settings, malformed/duplicate-key JSON, symlinked files and edits since
the displayed proposal refuse without replacement. Writes use a private temporary file,
fsync and atomic replacement; repeated identical application preserves the file bytes.
No Pi defaults or runner model choices are changed by setup.

Use the same **absolute** `PI_CODING_AGENT_DIR` for setup and service installation
if you do not use Pi's default directory. The installer saves it and preserves it
on reinstall; foreground runners load it from repository settings unless explicitly
overridden. CLI/TUI service-model selection uses the saved directory, so it validates
against that service's catalog. An existing service without a saved directory uses
Pi's default directory, not the model picker's shell override. Relative agent directories
are refused to prevent resolution differences between setup and services.
Setup itself always targets the calling process's Pi
directory, displayed in the proposal; it never edits an unrelated service/profile.
Existing services need explicit reinstallation to adopt a different directory.

Starting a runner is a **separate operation that makes model calls**. For a new
service, set `PI_AUTOWORK_PRIMARY="nous-local/$MODEL_ID"` and
`PI_AUTOWORK_NO_FALLBACK=1` when running `autowork start /path/to/project`, or supply
an explicit available `PI_AUTOWORK_FALLBACK` instead. No Codex/OpenRouter login is
required for a proxy-only choice. Existing services use `autowork model` and the
supported installer for changed service settings. A missing proxy on a prepared
entry is diagnosed before worker/model selection, never delegated to workers for
repeated configuration approvals.

Offline coverage: `tests/test_autowork_command.py`, `pi-autowork/tests/test_portal.py`
and the headless `tui_pilot.py` use disposable configurations and health-only stubs;
no real proxy, auth, service lifecycle or inference is qualified. For manual
prerequisites and the separately opt-in live probe, see
[the cross-host guide](../docs/cross-host.md#nous-portal-through-the-local-proxy).
Contracts verified against [Hermes subscription proxy documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/subscription-proxy),
[Hermes health implementation](https://github.com/NousResearch/hermes-agent/blob/3a9d585e4f1a60588237587a72d365d187094c74/hermes_cli/proxy/server.py)
and [Pi compatible endpoints](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/models.md#configure-a-compatible-endpoint)
(Pi 1.3.0 installed documentation); earlier Pi versions are not newly qualified.

## Cost and owner attention

```sh
autowork attention 15 --task CACHE-01 --note 'Reviewed behavior'
autowork attention 5 /path/to/repository   # repository-level time
autowork scorecard --days 30 --json .
autowork scorecard --days 30 --csv . > evaluation.csv
autowork scorecard --days 30 --baseline /private/baseline.json .
```

### Evaluation report

Text, `--json` and `--csv` render the same evaluation metrics. JSON adds
`runners.<name>.evaluation` and `overall`, while retaining the existing runner
counters and `usage`. Each evaluation contains `summary`, `weeks`, `change`,
`baseline` and `baseline_change`. Each metric has `value`, `unit` and `status`:
`measured`, `estimate` or `missing`; missing JSON values are `null`, CSV values
are empty, and text says `missing`. Metadata (names, window bounds and week
numbers) is not a metric. CSV is long-form: one row per scope, runner, period
and metric, with the same labels and values as JSON. Periods are `summary`,
`week-1` onward, `change`, `baseline` and `baseline_change`.

Weeks are consecutive seven-day intervals from the window's start, oldest first;
the final week can be shorter (two days for a 30-day window). Boundaries are epoch
seconds: start inclusive, end exclusive except the final end. Changes are absolute
last-week minus first-week values, not relative percentages; percentage changes
use percentage points. A single-week window compares that week with itself.
Overall metrics pool task counts, duration samples and denominators across unique
repositories; runner medians and percentages are never averaged. Repeated targets
for one repository count once.

| Metric | Definition and limits |
| --- | --- |
| `verified_tasks`, `verified_tasks_per_day` | Distinct currently closed tasks with valid coordinator receipts and a close transition in the window, divided by actual period days. A reopened/reclosed task counts once in its latest close's week. A lifecycle close observation dates that transition when available; otherwise its Git timestamp does. Conversion itself closes nothing. |
| `manual_closed`, `owner_interventions` | Manual/legacy hand closes are separate, never verified. Each counts as one intervention even without telemetry. Other interventions are explicit `blocker_answered`, `contract_edited` and `hand_closed` facts, not retries or inferred Git authorship. |
| `unattended_completion_percentage` | Percentage of verified completions with no recorded lifecycle intervention or positive task-attributed owner time before closure, including observations before the window. Requires accepted/dispatch/close telemetry for every counted task. Unattributed positive owner time overlapping a task's lifecycle, or invalid attention records, makes this unknown. Manual closes enter neither numerator nor denominator. |
| `accepted_to_delivered_{median,p95}_minutes` | First acceptance to first delivery for each verified completion in the period; delivery is observed by the coordinator, not inferred from a candidate commit. |
| `dispatch_to_integrated_{median,p95}_minutes` | First dispatch to first integration, including retry delays. Both duration metrics are missing if any verified completion lacks ordered endpoints. p95 uses nearest rank, with no extrapolation for small cohorts. |
| `cost_per_verified_task_usd`, `owner_minutes_per_verified_task` | All window spend / recorded owner time divided by verified completions, including unattributed overhead and work not yet completed. Missing billing or missing attention for a verified task leaves the corresponding ratio missing. These are period ratios, not lifetime task bills; costs just before a week's boundary remain in that earlier week. |
| `recovery_success_rate` | Fraction of observed restart/interruption episodes followed by `worker_adopted`/`resumed` for the same task and attempt by the report end. A success means execution recovered, not that the task subsequently passed. Episodes belong to their trigger's week; no episodes means missing. |
| `regression_rate` | Fraction of the period's verified completion cohort with at least one explicit receipt-linked regression discovered during the selected window, observed through the report end. Multiple notes/reverts for one task count once. Older deliveries' discoveries remain visible in runner `regressions`, but do not inflate the completion cohort's rate. This is observed attribution, not proof that all regressions were found. |

With no verified completion, all rates and per-task ratios are **missing**, not
zero. Counts (including manual closes and interventions) remain measured. A
measured unattended result means no *recorded* intervention, not proof of complete
human-activity coverage. Recorded owner time is likewise not an inferred total.
An undated torn attention record cannot be proved outside a task's lifecycle, so
it conservatively leaves unattended results missing. Missing values propagate into
changes; no guessed zero fills a gap.

An optional private baseline file is a JSON object with finite nonnegative values:

```json
{"cost_per_verified_task_usd": 5, "owner_minutes_per_verified_task": 15}
```

`baseline.metrics` labels these owner-supplied values `estimate`, beside the
unchanged measured summary metrics. `baseline_change` is measured summary minus
baseline, also labelled `estimate` (or `missing` when measurement is unavailable).
Without `--baseline`, every format says `no baseline` and comparison values are
missing. Keep baseline files and exported reports private; they can reveal
repository names and operating costs. No evaluation output proves a live 30-day
run; [the evaluation plan](../docs/evaluation.md#30-day-evaluation) keeps that separate.

### Accounting details

The scorecard's JSON `usage` contains `tasks`, each with `attempts`, `roles`
(worker, reviewer, coordinator), `host_models`, token totals, billing and
`owner_minutes`. Runtime roles `verify` map to reviewer; merge, triage,
provision and maintainer map to coordinator. Repository-wide merge and maintainer
jobs stay unattributed rather than becoming invented tasks. New runs carry a unique `run_id`
and the engine `attempt_id` when available. Replayed IDs count once; distinct
retry runs add spend but not another verified or delivered task. Older records
without attempt/host metadata retain explicit `unknown` attribution. Records
missing a task or role count under `unattributed`, never disappear. Torn records
and replayed IDs are counted in `diagnostics`, with separate invalid-run and
invalid-attention counts. Unreadable run records invalidate the complete window
bill and cost-per-task ratios, but retain the valid measured subtotal.

`input_tokens`, `output_tokens` and `tokens` are observed counts, or `null` when
missing. `cost_usd` is `null` and `cost_status` is `missing` if any run lacks
provider-reported billing; `measured_cost_usd` retains the known subtotal, not
an estimate of the missing spend. `unknown_cost_tasks` lists tasks with missing
billing/usage. Subscription usage reports tokens with cost unknown. Pi's ordinary
`usage.cost` is catalog-derived, **not provider billing**, so neither it nor older
unlabelled `runs.jsonl` costs establish measured spend. Only amounts explicitly
labelled `cost_source: provider_reported` by a billing-aware adapter are accepted;
stock Pi output without that provenance remains unknown. There are no pricing
tables, billing API calls or budget changes here.

`cost_per_verified_task_usd` and `cost_per_delivered_task_usd` divide the window's
total spend by distinct verified closures and lifecycle delivery observations,
respectively. A retry does not add a completion. Missing billing, missing usage
for a counted completion, or a zero denominator leaves the ratio `null`.
The measured subtotal includes unattributed runs so their spend cannot vanish.

`owner_minutes` means **recorded** time, not complete coverage: unrecorded time
stays unknown. A task with no attention record reports `null`, never zero.
`autowork blockers` measures wall-clock time until its agent exits (including
idle time and failed/interrupted sessions); it records repository-level time,
not a guessed division among tasks. A forcibly killed wrapper cannot record its
duration. Other time must be logged with `autowork attention`; avoid logging the
same blocker session twice. `unattributed_owner_minutes` keeps repository-level
time separate. `interventions` counts the lifecycle categories `blocker_answered`,
`contract_edited` and `hand_closed`, without inferring human activity from model
retries or commit authorship.

Usage and attention logs live only in private runner state (`runs.jsonl` and
`attention.jsonl` under the repository's state key), including optional notes.
No usage records or attention logs belong in Git. These are offline accounting
facilities, not evidence that a live task was delivered or that a bill was paid.

## Runner health reads

Engine status reads wait up to two seconds for the writer lock, so brief dispatch
or integration writes do not immediately fail a read. If a read still fails,
health keeps its last observed state for that one failure, with the snapshot's
original timestamp and the read error. A second consecutive failure marks health
`unavailable`; without a previous snapshot it is unavailable immediately. A
successful read clears the failure episode without resetting an unchanged state's
stall clock. In `autowork status`, an unavailable Health line shows when reads
began failing, not when the previous healthy or blocked state began.

## Session merge recovery

Before merging main, the coordinator tries to commit edits left in its own session.
If Git refuses a bookkeeping commit, the warning includes Git's output (including
hook diagnostics). When all staged paths are runner bookkeeping (`BLOCKERS.md`,
task-store files or frozen history), it unstages those paths without changing their
working contents so unrelated main fixes can merge. The edits stay in the session
for a later commit; they are not landed uncommitted. A refused work commit still
holds the landing. Repository hooks are never disabled for this recovery.

A merge refusal without unmerged paths is reported as `Merge pending` with Git's
message, not as an unknown-file conflict. Only actual unmerged paths trigger the
Pi conflict resolver. Overlapping uncommitted bookkeeping can still prevent the
merge; its contents and session worktree are kept for retry.

If a merge invents a task/goal status, Evidence or closure value, or synthesizes a
contract field absent from both parents, the runner rejects it before landing or
adoption. The diagnostic names the record and field; the pre-merge head is restored
and main stays unchanged. Resolve by selecting parent values, combining only ordinary
notes; record intentional task transitions separately. See the
[merge and closure rules](task-store.md#integration-and-closure).

## Isolated runtime comparison

The [TOOLSET-117-cb spike](spikes/runtime-comparison/README.md) compares the current
CLI path, pinned AgwaB `runSubagent` headless execution and experimental pi-durable
on identical offline fixtures. It defines launch/observe/stop/resume and explicit
replay capabilities without changing the default worker. Measurements and limits
are in the [research comparison](../docs/research/pi-autowork-reference-architectures.md#worker-runtime-comparison-toolset-117-cb).
Do not configure services to load the spike; adoption requires an owner decision.

Design: [coordinator redesign](../docs/plans/2026-10-16-pi-autowork-coordinator.md),
[component layout](../docs/plans/pi-autowork-component-layout.md). Tests run from
`python3 scripts/check.py` (`pi-autowork/tests`).
