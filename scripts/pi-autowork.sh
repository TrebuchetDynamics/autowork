#!/usr/bin/env bash
# pi-autowork.sh: run Hermes Toolset Autowork one task at a time through the Pi coding agent.
#
# Pi performs one bounded task per run; this script owns the loop, model choice,
# lifecycle and recovery. TODO.md and goals.json stay the source of truth.
set -uo pipefail

usage() {
  cat <<'EOF'
Usage: pi-autowork.sh [options]

Runs Hermes Toolset Autowork through Pi, one task per Pi run, until stopped.
Targets the Git repository of the current directory (or of this script, when it
was copied into a repository). Needs TODO.md, and goals.json for continuous runs.

Options:
  --once               Run at most one task, then exit
  --until-empty        Exit when no runnable task remains
  --dry-run            Show what would run; change nothing
  --repo PATH          Use the repository at PATH
  --interval SECONDS   Idle polling interval (default 60)
  --max-cycles N       Stop after N Pi runs
  --no-fallback        Never switch to the fallback model
  --help               Show this help

Environment (optional):
  PI_AUTOWORK_PRIMARY       provider/model (default openai-codex/gpt-6.1-sol)
  PI_AUTOWORK_FALLBACK      provider/model (default openrouter/deepseek/deepseek-v4.1-flash)
  PI_AUTOWORK_TASK_TIMEOUT  seconds per Pi run (default 5400)
  PI_AUTOWORK_MAX_RETRIES   provider/crash retries per task (default 3)
  PI_AUTOWORK_MAX_FAILURES  consecutive failed runs before exiting (default 3)
  PI_AUTOWORK_COOLDOWN      seconds on the fallback before trying the primary again (default 1800)
  PI_AUTOWORK_BACKOFF       first retry delay in seconds, doubling to 600 (default 30)
  PI_AUTOWORK_MAX_RUNTIME   stop starting tasks after this many seconds (default 0, unlimited)
  PI_AUTOWORK_MAX_COST      stop after this much reported USD cost (default 0, unlimited)
  PI_AUTOWORK_STATE_DIR     state root (default ${XDG_STATE_HOME:-~/.local/state}/pi-autowork)
  PI_AUTOWORK_TOOLSET       hermes-toolset checkout or Pi package path (default: auto)
  PI_AUTOWORK_ALLOW_HERMES  1 to run although a Hermes Autowork cron job targets this repository
  PI_BIN                    Pi command (default pi)

Exit status: 0 done, 1 stopped on a failure or blocker, 2 setup error,
3 another runner holds this repository, 4 needs attention, 130 interrupted.
EOF
}

MODE=continuous DRY_RUN=0 REPO_ARG='' INTERVAL=60 MAX_CYCLES=0 FALLBACK_ENABLED=1
while (($#)); do
  case $1 in
    --once) MODE=once ;;
    --until-empty) MODE='until-empty' ;;
    --dry-run) DRY_RUN=1 ;;
    --repo) REPO_ARG=${2:?--repo needs a path}; shift ;;
    --interval) INTERVAL=${2:?--interval needs seconds}; shift ;;
    --max-cycles) MAX_CYCLES=${2:?--max-cycles needs a number}; shift ;;
    --no-fallback) FALLBACK_ENABLED=0 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown option: %s\n\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done
for value in "$INTERVAL" "$MAX_CYCLES"; do
  [[ $value =~ ^[0-9]+$ ]] || { echo "Expected a whole number, got: $value" >&2; exit 2; }
done

PI=${PI_BIN:-pi}
PRIMARY=${PI_AUTOWORK_PRIMARY:-openai-codex/gpt-6.1-sol}
FALLBACK=${PI_AUTOWORK_FALLBACK:-openrouter/deepseek/deepseek-v4.1-flash}
TASK_TIMEOUT=${PI_AUTOWORK_TASK_TIMEOUT:-5400}
MAX_RETRIES=${PI_AUTOWORK_MAX_RETRIES:-3}
MAX_FAILURES=${PI_AUTOWORK_MAX_FAILURES:-3}
COOLDOWN=${PI_AUTOWORK_COOLDOWN:-1800}
BACKOFF=${PI_AUTOWORK_BACKOFF:-30}
MAX_RUNTIME=${PI_AUTOWORK_MAX_RUNTIME:-0}
MAX_COST=${PI_AUTOWORK_MAX_COST:-0}
SCRIPT=$(readlink -f "${BASH_SOURCE[0]}")

STATE='' CHILD='' KILLER='' SLEEPER='' STOP=0 CYCLES=0 FAILURES=0 SPENT=0 STARTED=$SECONDS
declare -A SKIPPED=() RETRIES=()

say() {
  local line
  line=$(printf '[%s] %s' "$(date +%H:%M)" "$*")
  printf '%s\n' "$line"
  [[ -n $STATE && -d $STATE ]] && printf '%s %s\n' "$(date -Iseconds)" "$*" >>"$STATE/runner.log"
  return 0
}
die() { local code=$1; shift; printf 'pi-autowork: %s\n' "$*" >&2; exit "$code"; }
redact() {
  sed -E 's/(sk-[A-Za-z0-9_-]{8,}|Bearer [A-Za-z0-9._~+\/=-]+|[A-Za-z0-9_]*(KEY|TOKEN|SECRET|PASSWORD)[A-Za-z0-9_]*=[^[:space:]]+)/[redacted]/g'
}
provider_of() { printf '%s' "${1%%/*}"; }
model_of() { printf '%s' "${1#*/}"; }

for tool in git jq python3 flock setsid timeout; do
  command -v "$tool" >/dev/null 2>&1 || die 2 "Missing required command: $tool"
done
command -v "$PI" >/dev/null 2>&1 || die 2 "Pi not found ($PI). Install Pi, then: pi install git:github.com/TrebuchetDynamics/hermes-toolset"

# --- Repository ---------------------------------------------------------------
is_toolset() { [[ -f $1/skills/docs-sync/scripts/goals.py && -f $1/adapters/skills/autowork/SKILL.md ]]; }
script_repo() {
  local top
  top=$(git -C "$(dirname "$SCRIPT")" rev-parse --show-toplevel 2>/dev/null) || return 1
  is_toolset "$top" && return 1  # the shipped copy targets the caller's repository
  printf '%s' "$top"
}
if [[ -n $REPO_ARG ]]; then
  start=$REPO_ARG
elif start=$(script_repo); then
  :
else
  start=$PWD
fi
REPO=$(git -C "$start" rev-parse --show-toplevel 2>/dev/null) || die 2 "Not inside a Git repository: $start"
[[ -f $REPO/TODO.md ]] || die 2 "No TODO.md at $REPO. Create the backlog first, for example with /docs_sync in Pi."
GIT_DIR=$(git -C "$REPO" rev-parse --path-format=absolute --git-dir)
GIT_COMMON=$(git -C "$REPO" rev-parse --path-format=absolute --git-common-dir)
HAS_LEDGER=0
[[ -f $REPO/goals.json ]] && HAS_LEDGER=1
if ((!HAS_LEDGER)) && [[ $MODE != once ]]; then
  die 2 "No goals.json in $REPO, so an empty queue cannot be told apart without a model call. Use --once, or create goals.json with /docs_sync."
fi

# --- Hermes Toolset -----------------------------------------------------------
installed_toolset() {  # the hermes-toolset package Pi loads, from `pi list`
  local line
  while IFS= read -r line; do
    line=${line#"${line%%[![:space:]]*}"}
    [[ $line == /* ]] && is_toolset "$line" && { (cd "$line" && pwd); return 0; }
  done < <("$PI" list 2>/dev/null)
  return 1
}
# Prefer the package Pi has installed, so every run uses the skills Pi itself loads.
SKILL_ARGS=()
if [[ -n ${PI_AUTOWORK_TOOLSET:-} ]]; then
  is_toolset "$PI_AUTOWORK_TOOLSET" || die 2 "PI_AUTOWORK_TOOLSET is not a hermes-toolset checkout: $PI_AUTOWORK_TOOLSET"
  TOOLSET=$(cd "$PI_AUTOWORK_TOOLSET" && pwd)
  installed_toolset | grep -qxF -- "$TOOLSET" || SKILL_ARGS=(--skill "$TOOLSET/adapters/skills/autowork")
elif TOOLSET=$(installed_toolset); then
  :
elif TOOLSET=$(cd "$(dirname "$SCRIPT")/.." && pwd) && is_toolset "$TOOLSET"; then
  SKILL_ARGS=(--skill "$TOOLSET/adapters/skills/autowork")
  printf 'pi-autowork: hermes-toolset is not installed in Pi; loading Autowork from %s. Install the package for its other skills: pi install git:github.com/TrebuchetDynamics/hermes-toolset\n' "$TOOLSET" >&2
else
  die 2 "Hermes Toolset not found. Install it in Pi (pi install git:github.com/TrebuchetDynamics/hermes-toolset) or set PI_AUTOWORK_TOOLSET."
fi
GOALS=$TOOLSET/skills/docs-sync/scripts/goals.py
TOOLSET_REV=$(git -C "$TOOLSET" rev-parse --short HEAD 2>/dev/null || echo unknown)

# --- Models -------------------------------------------------------------------
in_catalog() {
  "$PI" --list-models "$(model_of "$1")" 2>/dev/null |
    awk -v p="$(provider_of "$1")" -v m="$(model_of "$1")" '$1 == p && $2 == m { found = 1 } END { exit !found }'
}
auth_ready() {  # 0 ready; never prints credentials
  local refresh=()
  ((DRY_RUN)) && refresh=(--no-refresh)
  "$PI" auth check --provider "$(provider_of "$1")" --model "$(model_of "$1")" "${refresh[@]}" >/dev/null 2>&1
}
in_catalog "$PRIMARY" || die 2 "Primary model $PRIMARY is not in Pi's model catalog (pi --list-models)."
if ((FALLBACK_ENABLED)); then
  in_catalog "$FALLBACK" || die 2 "Fallback model $FALLBACK is not in Pi's model catalog; fix PI_AUTOWORK_FALLBACK or use --no-fallback."
fi

# --- Hermes coexistence -------------------------------------------------------
hermes_jobs() {
  python3 - "${PI_AUTOWORK_HERMES_HOME:-$HOME/.hermes}" "$REPO" <<'PY'
import glob, json, os, sys
home, repo = sys.argv[1], os.path.realpath(sys.argv[2])
files = [os.path.join(home, 'cron/jobs.json')] + sorted(glob.glob(os.path.join(home, 'profiles/*/cron/jobs.json')))
for path in files:
    try:
        data = json.load(open(path))
    except (OSError, ValueError):
        continue
    jobs = data.get('jobs', []) if isinstance(data, dict) else data
    for job in jobs if isinstance(jobs, list) else []:
        if not isinstance(job, dict) or not job.get('workdir'):
            continue
        if os.path.realpath(job['workdir']) != repo or job.get('enabled') is False:
            continue
        if job.get('paused_at') or job.get('state') == 'paused':
            continue
        text = ' '.join([str(job.get('skill') or ''), *map(str, job.get('skills') or []), str(job.get('prompt') or '')])
        if 'autowork' in text.lower():
            profile = path.split('/profiles/')[1].split('/')[0] if '/profiles/' in path else 'default'
            print(f"{profile}: {job.get('name') or job.get('id')}")
PY
}
HERMES_JOBS=$(hermes_jobs)

# --- State --------------------------------------------------------------------
STATE_ROOT=${PI_AUTOWORK_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/pi-autowork}
REPO_KEY=$(printf '%s' "$GIT_COMMON" | sha256sum | cut -c1-16)
STATE_PATH=$STATE_ROOT/$REPO_KEY

self_path() {  # this script's path inside the repository, if it was copied there
  case $SCRIPT in "$REPO"/*) printf '%s' "${SCRIPT#"$REPO"/}" ;; esac
}
dirty() {
  local self
  self=$(self_path)
  git -C "$REPO" status --porcelain=v1 --untracked-files=all | { if [[ -n $self ]]; then grep -vxF "?? $self"; else cat; fi; }
}
git_busy() {
  local marker
  for marker in MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD rebase-merge rebase-apply BISECT_LOG; do
    [[ -e $GIT_DIR/$marker ]] && { printf '%s' "$marker"; return 0; }
  done
  return 1
}
task_status() { jq -r --arg id "$1" 'first(.tasks[]? | select(.id == $id) | .status) // "missing"' "$REPO/goals.json"; }
ledger_revision() { python3 "$GOALS" revision "$REPO" 2>/dev/null; }

# Prints the eligible queue as JSON; returns 0 ok, 3 priority drift, other invalid.
queue() { python3 "$GOALS" next "$REPO" --json 2>/dev/null; }

summarize() {
  local primary_auth fallback_auth
  primary_auth=$(auth_ready "$PRIMARY" && echo ready || echo 'not ready')
  echo "PI AUTOWORK"
  echo "Repository: $REPO"
  if ((${#SKILL_ARGS[@]})); then
    echo "Toolset:    $TOOLSET at $TOOLSET_REV (not a Pi package; Autowork loaded with --skill)"
  else
    echo "Toolset:    $TOOLSET at $TOOLSET_REV (Pi package)"
  fi
  echo "Primary:    $PRIMARY ($primary_auth)"
  if ((FALLBACK_ENABLED)); then
    fallback_auth=$(auth_ready "$FALLBACK" && echo ready || echo 'not ready')
    echo "Fallback:   $FALLBACK ($fallback_auth)"
  else
    echo "Fallback:   disabled"
  fi
  echo "Mode:       $MODE; state in $STATE_PATH"
}

# --- Dry run ------------------------------------------------------------------
if ((DRY_RUN)); then
  summarize
  [[ -n $HERMES_JOBS ]] && printf 'Hermes Autowork cron jobs target this repository (the runner would refuse):\n%s\n' "$HERMES_JOBS"
  if [[ -e $STATE_PATH/lock ]] && ! flock -n "$STATE_PATH/lock" true; then
    echo "Lock:       held by another runner"
  else
    echo "Lock:       free"
  fi
  if busy=$(git_busy); then echo "Git:        $busy in progress (the runner would stop)"; fi
  changes=$(dirty)
  [[ -n $changes ]] && printf 'Uncommitted changes (the runner would not start a new task):\n%s\n' "$changes"
  if ((HAS_LEDGER)); then
    list=$(queue); rc=$?
    case $rc in
      0) count=$(jq length <<<"$list")
         echo "Queue:      $count runnable task(s)"
         ((count)) && echo "Next:       $(jq -r '.[0].task | "\(.id) — \(.title)"' <<<"$list")" ;;
      3) echo "Queue:      TODO.md priority changed; run goals.py reorder (the runner would wait)" ;;
      *) echo "Queue:      goals.py could not read the ledger (the runner would stop)" ;;
    esac
  else
    echo "Queue:      no goals.json; Autowork would pick the next ready TODO.md task once"
  fi
  echo "Dry run: nothing was changed."
  exit 0
fi

[[ -n $HERMES_JOBS && ${PI_AUTOWORK_ALLOW_HERMES:-0} != 1 ]] &&
  die 4 "$(printf 'A Hermes Autowork cron job already works on this repository; two agents would write at once:\n%s\nPause it, or set PI_AUTOWORK_ALLOW_HERMES=1.' "$HERMES_JOBS")"

mkdir -p "$STATE_PATH/sessions" "$STATE_PATH/runs" || die 2 "Cannot create state directory $STATE_PATH"
STATE=$STATE_PATH
exec 9>>"$STATE/lock"
if ! flock -n 9; then
  owner=$(jq -r '"PID \(.pid), started \(.started)"' "$STATE/runner.json" 2>/dev/null || echo 'unknown owner')
  die 3 "Another pi-autowork runner holds $REPO ($owner)."
fi
jq -n --arg pid "$$" --arg started "$(date -Iseconds)" --arg repo "$REPO" '{pid: ($pid | tonumber), started: $started, repo: $repo}' >"$STATE/runner.json"

# Every git command Pi or its tools run sees this: pushes fail, fetches work.
export GIT_CONFIG_COUNT=2
export GIT_CONFIG_KEY_0=url.pi-autowork-push-disabled:///.pushInsteadOf GIT_CONFIG_VALUE_0=
export GIT_CONFIG_KEY_1=protocol.pi-autowork-push-disabled.allow GIT_CONFIG_VALUE_1=never

# --- Signals ------------------------------------------------------------------
on_signal() {
  if ((STOP)) && [[ -n $CHILD ]]; then
    kill -TERM -- "-$CHILD" 2>/dev/null
    return
  fi
  STOP=1
  say "Stopping: letting the current Pi run end (Ctrl+C again to force)"
  if [[ -n $CHILD ]]; then
    kill -INT -- "-$CHILD" 2>/dev/null
    (sleep 30; kill -TERM -- "-$CHILD" 2>/dev/null; sleep 10; kill -KILL -- "-$CHILD" 2>/dev/null) </dev/null >/dev/null 2>&1 &
    KILLER=$!
  fi
}
stop_helpers() {  # background timers must not outlive the runner or hold its output open
  local pid
  for pid in "$KILLER" "$SLEEPER"; do
    [[ -n $pid ]] || continue
    pkill -P "$pid" 2>/dev/null
    kill "$pid" 2>/dev/null
  done
  KILLER='' SLEEPER=''
}
trap on_signal INT TERM
trap 'stop_helpers; rm -f "$STATE/runner.json"' EXIT

pause() {  # interruptible sleep
  sleep "$1" >/dev/null 2>&1 &
  SLEEPER=$!
  wait "$SLEEPER" 2>/dev/null
  stop_helpers
}

# --- One Pi run ---------------------------------------------------------------
# Sets RUN_* globals describing what Pi reported.
run_pi() {
  local task=$1 title=$2 session=$3 target=$4 resume=$5 raw err prompt rc analysis
  raw=$STATE/runs/current.jsonl err=$STATE/runs/current.err
  if [[ -n $task ]]; then
    prompt="/skill:autowork Execute exactly task $task ($title) in $REPO. Do not select, start or record any other task and do not look for new work. Complete this task: implement it, run its checks, commit locally, then mark it done and archive it as the skill describes. Do not push, deploy, publish or rewrite Git history. If it cannot be completed in this run (it needs live access, a decision or another blocker), record the precise blocker in its TODO.md body, keep its status and stop."
  else
    prompt="/skill:autowork Complete the next ready task in $REPO's TODO.md, exactly one. Do not look for or record new work: if no task is ready, change nothing and say so. Commit locally; do not push, deploy, publish or rewrite Git history."
  fi
  ((resume)) && prompt+=" A previous run of this task was interrupted: first reconcile its partial work in the working tree and the latest commits, then continue."
  prompt+=" End with one line: PI_AUTOWORK_RESULT: completed|partial|blocked, then one sentence."
  RUN_START=$SECONDS
  (cd "$REPO" && exec setsid timeout -s INT -k 120 "$TASK_TIMEOUT" \
    "$PI" --mode json --provider "$(provider_of "$target")" --model "$(model_of "$target")" \
    --session-dir "$STATE/sessions" --session-id "$session" --no-approve "${SKILL_ARGS[@]}" -- "$prompt") \
    </dev/null >"$raw" 2>"$err" &
  CHILD=$!
  while :; do
    wait "$CHILD"; rc=$?
    kill -0 "$CHILD" 2>/dev/null || break
  done
  stop_helpers
  CHILD=''
  RUN_RC=$rc RUN_SECONDS=$((SECONDS - RUN_START))
  analysis=$(jq -R -s -c '
    [split("\n")[] | fromjson? | select(type == "object")] as $e
    | ($e | map(select(.type == "agent_settled")) | last) as $settled
    | ($e | map(select(.type == "message_end" and .message.role == "assistant") | .message)) as $msgs
    | ($msgs | last) as $last
    | ($e | map(select(.type == "auto_retry_end" and .success == false)) | last) as $gaveup
    | {settled: ($settled != null), aborted: ($settled.aborted // false),
       stop: ($last.stopReason // null),
       error: ($last.errorMessage // $gaveup.finalError // null),
       retries: ($e | map(select(.type == "auto_retry_start")) | length),
       tools: ($e | map(select(.type == "tool_execution_start")) | length),
       tokens: ($msgs | map(.usage.totalTokens // 0) | add // 0),
       cost: ($msgs | map(.usage.cost.total // 0) | add // 0),
       model: ($last.model // null),
       result: ([$last.content[]? | select(.type == "text") | .text] | join("\n")
                | [splits("\n")] | map(select(startswith("PI_AUTOWORK_RESULT:"))) | last // null)}' "$raw")
  [[ -n $analysis ]] || analysis='{"settled":false,"aborted":false,"stop":null,"error":null,"retries":0,"tools":0,"tokens":0,"cost":0,"model":null,"result":null}'
  RUN_SETTLED=$(jq -r .settled <<<"$analysis")
  RUN_ABORTED=$(jq -r .aborted <<<"$analysis")
  RUN_STOP=$(jq -r '.stop // ""' <<<"$analysis")
  RUN_ERROR=$(jq -r '.error // ""' <<<"$analysis" | redact | cut -c1-300)
  RUN_TOKENS=$(jq -r .tokens <<<"$analysis")
  RUN_COST=$(jq -r .cost <<<"$analysis")
  RUN_RETRIES=$(jq -r .retries <<<"$analysis")
  RUN_RESULT=$(jq -r '.result // ""' <<<"$analysis" | redact | cut -c1-300)
  if [[ -z $RUN_ERROR && $RUN_RC -ne 0 ]]; then
    RUN_ERROR=$(tail -n 5 "$err" | tr '\n' ' ' | redact | cut -c1-300)
  fi
  # Keep only the compact record; the raw stream holds prompts, code and tool output.
  rm -f "$raw"
}

is_provider_failure() {
  [[ $RUN_STOP == error ]] && return 0
  [[ $RUN_SETTLED != true ]] && grep -qiE '429|rate.?limit|quota|usage limit|overloaded|5[0-9]{2}|unavailable|timed? ?out|ECONN|ENOTFOUND|EAI_AGAIN|network|fetch failed|401|403|unauthori[sz]ed|forbidden|credential|api key|not logged in|/login|oauth|expired|no such model|model .*not (found|available)' <<<"$RUN_ERROR"
}

record() {  # outcome task model fallback_reason start_sha
  local commits
  commits=$(git -C "$REPO" rev-list --reverse "$5..HEAD" 2>/dev/null | cut -c1-12 | paste -sd, -)
  jq -cn --arg time "$(date -Iseconds)" --arg outcome "$1" --arg task "$2" --arg model "$3" \
    --arg fallback "$4" --arg commits "$commits" --arg error "$RUN_ERROR" --arg result "$RUN_RESULT" \
    --argjson seconds "$RUN_SECONDS" --argjson tokens "$RUN_TOKENS" --argjson cost "$RUN_COST" \
    --argjson retries "$RUN_RETRIES" --argjson attempt "${RETRIES[$2]:-0}" \
    '{time: $time, task: $task, outcome: $outcome, provider: ($model | split("/")[0]),
      model: ($model | split("/")[1:] | join("/")), seconds: $seconds, commits: ($commits | split(",") | map(select(. != ""))),
      pi_retries: $retries, runner_retries: $attempt, fallback_reason: (if $fallback == "" then null else $fallback end),
      tokens: $tokens, cost_usd: $cost, error: (if $error == "" then null else $error end),
      result: (if $result == "" then null else $result end)}' \
    >>"$STATE/runs.jsonl"
}

# --- Provider choice ----------------------------------------------------------
primary_cooling() {
  local until
  until=$(jq -r '.primary_unavailable_until // 0' "$STATE/provider.json" 2>/dev/null || echo 0)
  (($(date +%s) < until))
}
cool_primary() {
  jq -n --argjson until "$(($(date +%s) + COOLDOWN))" --arg reason "$1" \
    '{primary_unavailable_until: $until, reason: $reason}' >"$STATE/provider.json"
}
# Sets CHOSEN and FALLBACK_REASON; returns 1 when no model is usable.
choose_model() {
  FALLBACK_REASON=''
  if ! primary_cooling; then
    if auth_ready "$PRIMARY"; then CHOSEN=$PRIMARY; return 0; fi
    FALLBACK_REASON='primary not authenticated'
    ((FALLBACK_ENABLED)) && cool_primary "$FALLBACK_REASON"
  else
    FALLBACK_REASON=$(jq -r '.reason // "primary cooling down"' "$STATE/provider.json")
  fi
  if ((FALLBACK_ENABLED)) && auth_ready "$FALLBACK"; then CHOSEN=$FALLBACK; return 0; fi
  if ((!FALLBACK_ENABLED)) && primary_cooling; then
    CHOSEN=$PRIMARY; return 0  # no fallback: retry the primary after the backoff
  fi
  return 1
}
label() { if [[ $1 == "$PRIMARY" ]]; then printf 'primary %s' "$1"; else printf 'fallback %s' "$1"; fi; }

# --- Main loop ----------------------------------------------------------------
summarize
say "Started (PID $$). Stop with Ctrl+C."
INFLIGHT=$STATE/inflight.json
LAST_REVISION=''

finish() { say "$2"; exit "$1"; }
fail_count() {
  FAILURES=$((FAILURES + 1))
  ((FAILURES >= MAX_FAILURES)) && finish 1 "Stopping after $FAILURES consecutive failed runs; see $STATE/runs.jsonl"
}
idle() {
  case $MODE in
    once|until-empty) finish "$2" "$1" ;;
  esac
  say "$1; checking again in ${INTERVAL}s"
  pause "$INTERVAL"
}

while :; do
  ((STOP)) && finish 130 "Stopped."
  ((MAX_CYCLES && CYCLES >= MAX_CYCLES)) && finish 0 "Reached --max-cycles $MAX_CYCLES."
  ((MAX_RUNTIME && SECONDS - STARTED >= MAX_RUNTIME)) && finish 0 "Reached PI_AUTOWORK_MAX_RUNTIME."
  if [[ $MAX_COST != 0 ]] && awk -v s="$SPENT" -v m="$MAX_COST" 'BEGIN { exit !(s >= m) }'; then
    finish 0 "Reached PI_AUTOWORK_MAX_COST (\$$SPENT reported)."
  fi
  if busy=$(git_busy); then
    finish 4 "A Git $busy is in progress in $REPO; finish or abort it, then restart."
  fi

  resume=0 task='' title=''
  if [[ -f $INFLIGHT ]]; then
    task=$(jq -r .task "$INFLIGHT") title=$(jq -r .title "$INFLIGHT") resume=1
    if ((HAS_LEDGER)) && [[ -n $task && $(task_status "$task") == 'done' && -z $(dirty) ]]; then
      say "$task was already completed before the interruption; not running it again"
      rm -f "$INFLIGHT"
      continue
    fi
    say "Resuming interrupted task ${task:-'(next ready)'}: reconciling partial work first"
  else
    changes=$(dirty)
    if [[ -n $changes ]]; then
      finish 4 "$(printf 'Uncommitted changes the runner did not make; commit or move them first:\n%s' "$changes")"
    fi
    if ((HAS_LEDGER)); then
      revision=$(ledger_revision)
      if [[ $revision != "$LAST_REVISION" ]]; then
        SKIPPED=()  # TODO.md or goals.json changed: give skipped tasks another chance
        LAST_REVISION=$revision
      fi
      list=$(queue); rc=$?
      if ((rc == 3)); then
        idle "TODO.md priority changed since it was recorded; run goals.py reorder (see Autowork)" 4
        continue
      elif ((rc != 0)); then
        finish 4 "goals.py could not read the ledger in $REPO; run goals.py validate there."
      fi
      pick=$(jq -c --argjson skipped "$(printf '%s\n' "${!SKIPPED[@]}" | jq -R . | jq -s .)" \
        'map(.task) | map(select(.id as $id | $skipped | index($id) | not)) | first // empty' <<<"$list")
      if [[ -z $pick ]]; then
        total=$(jq length <<<"$list")
        if ((total)); then
          idle "No task this runner can make progress on (${!SKIPPED[*]} skipped)" 1
        else
          idle "Queue empty" 0
        fi
        continue
      fi
      task=$(jq -r .id <<<"$pick") title=$(jq -r .title <<<"$pick")
      say "Queue: $(jq length <<<"$list") runnable task(s). Selected: $task — $title"
    fi
  fi

  if ! choose_model; then
    say "No usable model (${FALLBACK_REASON:-primary and fallback not ready})"
    fail_count
    pause "$((INTERVAL > 60 ? INTERVAL : 60))"
    continue
  fi
  [[ -n $FALLBACK_REASON && $CHOSEN == "$FALLBACK" ]] && say "Using the fallback: $FALLBACK_REASON"

  key=${task:-next}
  attempt=${RETRIES[$key]:-0}
  if ((resume)); then
    session=$(jq -r .session "$INFLIGHT") start_sha=$(jq -r .start_sha "$INFLIGHT")
  else
    session="pi-autowork-$key-$(date +%Y%m%d%H%M%S)"
    start_sha=$(git -C "$REPO" rev-parse HEAD 2>/dev/null || echo HEAD)
  fi
  jq -n --arg task "$task" --arg title "$title" --arg session "$session" --arg start_sha "$start_sha" \
    --arg model "$CHOSEN" --arg started "$(date -Iseconds)" \
    '{task: $task, title: $title, session: $session, start_sha: $start_sha, model: $model, started: $started}' >"$INFLIGHT"
  CYCLES=$((CYCLES + 1))
  say "Starting Pi with $(label "$CHOSEN")"
  run_pi "$task" "$title" "$session" "$CHOSEN" "$resume"
  SPENT=$(awk -v a="$SPENT" -v b="$RUN_COST" 'BEGIN { printf "%.4f", a + b }')

  status=''
  ((HAS_LEDGER)) && [[ -n $task ]] && status=$(task_status "$task")
  new_commits=$(git -C "$REPO" rev-list --count "$start_sha..HEAD" 2>/dev/null || echo 0)
  [[ -n $RUN_RESULT ]] && say "Pi: $RUN_RESULT"

  if ((STOP)); then
    record interrupted "$key" "$CHOSEN" "$FALLBACK_REASON" "$start_sha"
    finish 130 "Stopped during $key; partial work is kept and the next start resumes it."
  fi
  if [[ $status == 'done' ]]; then
    record completed "$key" "$CHOSEN" "$FALLBACK_REASON" "$start_sha"
    rm -f "$INFLIGHT"; unset 'RETRIES[$key]'; FAILURES=0
    say "$key completed with $(label "$CHOSEN") in $((RUN_SECONDS / 60)) min; local commits: $(git -C "$REPO" rev-list --reverse "$start_sha..HEAD" | cut -c1-7 | paste -sd' ' -)"
    [[ -n $(dirty) ]] && finish 4 "$key is done but left uncommitted changes; review them."
    [[ $MODE == once ]] && finish 0 "Done (--once)."
    continue
  fi

  if ((RUN_RC == 124)); then
    record timeout "$key" "$CHOSEN" "$FALLBACK_REASON" "$start_sha"
    say "$key exceeded PI_AUTOWORK_TASK_TIMEOUT (${TASK_TIMEOUT}s)"
    SKIPPED[$key]=1
    fail_count
    if [[ -n $(dirty) ]]; then
      finish 1 "$key timed out with uncommitted partial work; review it, then restart to resume."
    fi
    rm -f "$INFLIGHT"
    [[ $MODE == once ]] && finish 1 "Done (--once); $key did not finish."
    continue
  fi

  if is_provider_failure || [[ $RUN_SETTLED != true || $RUN_ABORTED == true ]]; then
    kind=crash
    is_provider_failure && kind=provider
    attempt=$((attempt + 1)); RETRIES[$key]=$attempt
    record "${kind}_failure" "$key" "$CHOSEN" "$FALLBACK_REASON" "$start_sha"
    say "$(label "$CHOSEN") failed ($kind): ${RUN_ERROR:-no result}"
    if ((attempt > MAX_RETRIES)); then
      SKIPPED[$key]=1
      fail_count
      [[ -n $(dirty) ]] && finish 1 "$key failed $attempt times and left uncommitted work; review it, then restart to resume."
      rm -f "$INFLIGHT"
      [[ $MODE == once ]] && finish 1 "Done (--once); $key did not finish."
      continue
    fi
    if [[ $kind == provider && $CHOSEN == "$PRIMARY" ]] && ((FALLBACK_ENABLED)); then
      cool_primary "${RUN_ERROR:-provider failure}"
      say "Reconciling partial work; switching to $(label "$FALLBACK") for up to $((COOLDOWN / 60)) min"
    else
      delay=$((BACKOFF * (1 << (attempt - 1)))); ((delay > 600)) && delay=600
      say "Retrying $key in ${delay}s (attempt $attempt of $MAX_RETRIES)"
      pause "$delay"
    fi
    continue  # the in-flight record makes the next run resume this task
  fi

  # Pi finished normally without closing the task.
  if ((!HAS_LEDGER)); then
    outcome=no_ready_task
    ((new_commits > 0)) && outcome=committed_unverified
    record "$outcome" "$key" "$CHOSEN" "$FALLBACK_REASON" "$start_sha"
    rm -f "$INFLIGHT"
    [[ -n $(dirty) ]] && finish 4 "Autowork left uncommitted changes; review them."
    ((new_commits > 0)) && finish 0 "Autowork made $new_commits local commit(s); without goals.json the runner cannot confirm the task is done."
    finish 0 "Autowork made no commit (no ready task, or it stopped on a blocker)."
  fi
  if ((new_commits > 0)); then
    record partial "$key" "$CHOSEN" "$FALLBACK_REASON" "$start_sha"
    say "$key made progress ($new_commits local commit(s)) but is not done yet"
    FAILURES=0
  else
    record no_progress "$key" "$CHOSEN" "$FALLBACK_REASON" "$start_sha"
    say "$key: no commit and still ${status:-open}; skipping it until TODO.md or goals.json changes"
    SKIPPED[$key]=1
    fail_count
  fi
  [[ -n $(dirty) ]] && finish 4 "$key left uncommitted changes; review them, then restart."
  rm -f "$INFLIGHT"
  if [[ $MODE == once ]]; then
    ((new_commits > 0)) && finish 0 "Done (--once); $key is not finished yet."
    finish 1 "Done (--once); $key made no progress."
  fi
done
