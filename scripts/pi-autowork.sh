#!/usr/bin/env bash
# pi-autowork.sh: run Hermes Toolset's Parallel Autowork engine with Pi workers.
#
# The engine (skills/autowork/scripts/owner_cycle.py --parallel) plans, dispatches,
# verifies and closes tasks; this script drives its coordinator loop and supplies
# what the engine leaves to the host: Pi workers with model choice and fallback, an
# independent verification step, budgets, a session branch merged into the main
# branch at the end, locking, graceful shutdown and a systemd service.
set -uo pipefail

usage() {
  cat <<'EOF'
Usage: pi-autowork.sh [options]

Runs Hermes Toolset Autowork through Pi until stopped: the toolset's Parallel
Autowork engine runs up to N tasks at once (default 2), each Pi worker in its own Git
worktree, and integrates verified results one at a time. Targets the Git repository
of the current directory (or of this script, when it was copied into a repository),
which must have its main branch checked out and a TODO.md.

Each session builds on an integration branch (pi-autowork/<session>) in its own
worktree; when the queue drains or the runner stops, the session is merged into the
main branch. Nothing is pushed.

Options:
  --once               Run at most one task, then exit
  --until-empty        Exit when no runnable task remains
  --dry-run            Show what would run; change nothing
  --status             Show the session, budget and each task's state; change nothing
  --fleet              One line per pi-autowork runner on this machine: service, health
                       (working, blocked, stalled, paused, not running) and root blockers
  --set-aside TASK     Ask this repository's runner to retire TASK's stuck slot (held with
                       no attempt left, or merged with a changed TODO entry); its work is
                       kept under renamed branches and the task runs fresh
  --repo PATH          Use the repository at PATH
  --workers N          Tasks run at once, 1-8 (default 8; PI_AUTOWORK_WORKERS); the engine's
                       memory and load gate starts fewer when the machine is busy
  --interval SECONDS   Idle polling interval (default 60)
  --max-cycles N       Start at most N Pi workers, then finish
  --no-fallback        Never switch to the fallback model
  --allow-hermes       Run although a Hermes Autowork cron job targets this repository
  --install-service    Install and start a systemd user service running this for the repository
  --remove-service     Stop and remove the repository's service
  --help               Show this help

Environment (optional):
  PI_AUTOWORK_PRIMARY       provider/model (default openai-codex/gpt-6.1-sol)
  PI_AUTOWORK_FALLBACK      provider/model (default openrouter/deepseek/deepseek-v4.1-flash)
  PI_AUTOWORK_WORKERS       default for --workers (default 8)
  PI_AUTOWORK_INFER_TOUCHES 0 to stop proposing Touches: for tasks that lack them
  PI_AUTOWORK_UPDATE_INTERVAL seconds between idle `pi update` runs of the toolset package;
                            new toolset code restarts the runner (default 3600; 0 off)
  PI_AUTOWORK_TASK_TIMEOUT  seconds per worker (default 5400)
  PI_AUTOWORK_VERIFY_TIMEOUT seconds for verifying one task (default 1800)
  PI_AUTOWORK_VALIDATE      command run before the Pi reviewer on every integrated task
  PI_AUTOWORK_REVIEW        0 to skip the Pi reviewer (PI_AUTOWORK_VALIDATE alone decides)
  PI_AUTOWORK_MAX_RETRIES   provider/crash retries per Pi run (default 3)
  PI_AUTOWORK_MAX_FAILURES  consecutive failed tasks before stopping (default 3); a service
                            pauses new tasks for PI_AUTOWORK_FAILURE_PAUSE seconds (3600) instead
  PI_AUTOWORK_CLAIM_IDLE    adopt another session's in_progress claim after this many seconds
                            with no task, branch or worktree change and no live agent
                            (default 21600; 0 never adopts)
  PI_AUTOWORK_LINK_PATHS    comma-separated gitignored paths (say vendor/sdk) to link from the
                            main checkout into each task and review worktree; only paths Git
                            ignores there, and the link is cooperative, not write-protected
  PI_AUTOWORK_STALL_AFTER   seconds with nothing running while work waits before the runner
                            announces STALLED with its root blockers (default 1800)
  PI_AUTOWORK_COOLDOWN      seconds on the fallback before trying the primary again (default 1800)
  PI_AUTOWORK_BACKOFF       first retry delay in seconds, doubling to 600 (default 30)
  PI_AUTOWORK_MAX_RUNTIME   stop starting tasks after this many seconds (default 0, unlimited)
  PI_AUTOWORK_MAX_COST      USD limit on reported cost within the budget window (default 0, unlimited)
  PI_AUTOWORK_COST_WINDOW   budget window in hours, counted across restarts (default 24)
  PI_AUTOWORK_MIN_FREE_MB   free memory each running worker needs (default 3000)
  PI_AUTOWORK_STATE_DIR     state root (default ${XDG_STATE_HOME:-~/.local/state}/pi-autowork)
  PI_AUTOWORK_TOOLSET       hermes-toolset checkout or Pi package path (default: auto)
  PI_AUTOWORK_ALLOW_HERMES  1 to run although a Hermes Autowork cron job targets this repository
  PI_BIN                    Pi command (default pi)

Exit status: 0 done, 1 stopped on a failure or blocker, 2 setup error,
3 another runner holds this repository, 4 needs attention, 130 interrupted.
EOF
}

# --- Common -------------------------------------------------------------------
PI=${PI_BIN:-pi}
PRIMARY=${PI_AUTOWORK_PRIMARY:-openai-codex/gpt-6.1-sol}
FALLBACK=${PI_AUTOWORK_FALLBACK:-openrouter/deepseek/deepseek-v4.1-flash}
TASK_TIMEOUT=${PI_AUTOWORK_TASK_TIMEOUT:-5400}
VERIFY_TIMEOUT=${PI_AUTOWORK_VERIFY_TIMEOUT:-1800}
MAX_RETRIES=${PI_AUTOWORK_MAX_RETRIES:-3}
MAX_FAILURES=${PI_AUTOWORK_MAX_FAILURES:-3}
FAILURE_PAUSE=${PI_AUTOWORK_FAILURE_PAUSE:-3600} PAUSE_UNTIL=0 RUNNER_BLOCKER=''
DRIFT_TRIED='' DRIFT_LAST_REASON='' DRIFT_REASON=''
CLAIM_IDLE=${PI_AUTOWORK_CLAIM_IDLE:-21600}
COOLDOWN=${PI_AUTOWORK_COOLDOWN:-1800}
BACKOFF=${PI_AUTOWORK_BACKOFF:-30}
MAX_RUNTIME=${PI_AUTOWORK_MAX_RUNTIME:-0}
MAX_COST=${PI_AUTOWORK_MAX_COST:-0}
COST_WINDOW=${PI_AUTOWORK_COST_WINDOW:-24}
MIN_FREE_MB=${PI_AUTOWORK_MIN_FREE_MB:-3000}
SCRIPT=$(readlink -f "${BASH_SOURCE[0]}")
STATE='' CHILD='' KILLER='' SLEEPER='' STOP=0 PAUSED=0 FALLBACK_ENABLED=1 DRY_RUN=0

say() {
  local line
  line=$(printf '[%s] %s' "$(date +%H:%M)" "$*")
  printf '%s\n' "$line"
  [[ -n $STATE && -d $STATE ]] && printf '%s %s\n' "$(date -Iseconds)" "$*" >>"$STATE/runner.log"
  return 0
}
# A warning-priority journal line under systemd (journald reads the <4> prefix).
warn() {
  if [[ -n ${INVOCATION_ID:-} ]]; then
    printf '<4>[%s] %s\n' "$(date +%H:%M)" "$*"
    [[ -n $STATE && -d $STATE ]] && printf '%s %s\n' "$(date -Iseconds)" "$*" >>"$STATE/runner.log"
  else
    say "$*"
  fi
  return 0
}
die() { local code=$1; shift; printf 'pi-autowork: %s\n' "$*" >&2; exit "$code"; }
redact() {
  sed -E 's/(sk-[A-Za-z0-9_-]{8,}|Bearer [A-Za-z0-9._~+\/=-]+|[A-Za-z0-9_]*(KEY|TOKEN|SECRET|PASSWORD)[A-Za-z0-9_]*=[^[:space:]]+)/[redacted]/g'
}
provider_of() { printf '%s' "${1%%/*}"; }
model_of() { printf '%s' "${1#*/}"; }
safe_name() { printf '%s' "$1" | tr -c 'A-Za-z0-9._-' '-'; }
dirty() { git -C "$1" status --porcelain=v1 --untracked-files=all 2>/dev/null; }
# Pushes from any git the runner, its workers or Pi's tools start fail; fetches work.
push_guard() {
  export GIT_CONFIG_COUNT=2
  export GIT_CONFIG_KEY_0=url.pi-autowork-push-disabled:///.pushInsteadOf GIT_CONFIG_VALUE_0=
  export GIT_CONFIG_KEY_1=protocol.pi-autowork-push-disabled.allow GIT_CONFIG_VALUE_1=never
}

auth_ready() {  # 0 ready; never prints credentials
  local refresh=()
  ((DRY_RUN)) && refresh=(--no-refresh)
  "$PI" auth check --provider "$(provider_of "$1")" --model "$(model_of "$1")" "${refresh[@]}" >/dev/null 2>&1
}
primary_cooling() {
  local until
  until=$(jq -r '.primary_unavailable_until // 0' "$STATE/provider.json" 2>/dev/null || echo 0)
  (($(date +%s) < until))
}
cool_primary() {
  jq -n --argjson until "$(($(date +%s) + COOLDOWN))" --arg reason "$1" \
    '{primary_unavailable_until: $until, reason: $reason}' >"$STATE/provider.json.$$" && mv "$STATE/provider.json.$$" "$STATE/provider.json"
}
# Sets CHOSEN and FALLBACK_REASON; returns 1 when no model is usable.
choose_model() {
  FALLBACK_REASON=''
  if ((!FALLBACK_ENABLED)); then  # nothing to switch to: the primary when ready, else nothing
    auth_ready "$PRIMARY" && { CHOSEN=$PRIMARY; return 0; }
    FALLBACK_REASON='primary not authenticated and the fallback is disabled'
    return 1
  fi
  if ! primary_cooling; then
    if auth_ready "$PRIMARY"; then CHOSEN=$PRIMARY; return 0; fi
    FALLBACK_REASON='primary not authenticated'
    cool_primary "$FALLBACK_REASON"
  else
    FALLBACK_REASON=$(jq -r '.reason // "primary cooling down"' "$STATE/provider.json")
  fi
  auth_ready "$FALLBACK" && { CHOSEN=$FALLBACK; return 0; }
  return 1
}
label() { if [[ $1 == "$PRIMARY" ]]; then printf 'primary %s' "$1"; else printf 'fallback %s' "$1"; fi; }

# Spending within the budget window, from every run recorded by any process.
spent() {
  local since
  since=$(date -d "-$COST_WINDOW hours" -Iseconds)
  jq -rs --arg since "$since" '[.[] | select(.time >= $since) | .cost_usd // 0] | add // 0' "${STATE:-$STATE_PATH}/runs.jsonl" 2>/dev/null || echo 0
}
over_budget() {
  [[ $MAX_COST != 0 ]] && awk -v s="$(spent)" -v m="$MAX_COST" 'BEGIN { exit !(s >= m) }'
}

# Runs Pi in directory $1 with message $2 (and extra Pi arguments after $4);
# sets RUN_* globals describing what Pi reported.
run_pi() {
  local dir=$1 message=$2 session=$3 target=$4 limit=$5 raw err rc analysis
  shift 5
  raw=$(mktemp "$STATE/runs/run.XXXXXX") err=$raw.err
  RUN_START=$SECONDS
  # --foreground keeps Pi and its tools in the worker's process group, which the engine stops as a whole.
  (cd "$dir" && exec timeout --foreground -s INT -k 120 "$limit" \
    "$PI" --mode json --provider "$(provider_of "$target")" --model "$(model_of "$target")" \
    --session-dir "$STATE/sessions" --session-id "$session" --no-approve "${SKILL_ARGS[@]}" "$@" -- "$message") \
    </dev/null >"$raw" 2>"$err" &
  CHILD=$!
  while :; do
    wait "$CHILD"; rc=$?
    kill -0 "$CHILD" 2>/dev/null || break
  done
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
       tokens: ($msgs | map(.usage.totalTokens // 0) | add // 0),
       cost: ($msgs | map(.usage.cost.total // 0) | add // 0),
       text: ([$last.content[]? | select(.type == "text") | .text] | join("\n"))}' "$raw")
  [[ -n $analysis ]] || analysis='{"settled":false,"aborted":false,"stop":null,"error":null,"retries":0,"tokens":0,"cost":0,"text":""}'
  RUN_SETTLED=$(jq -r .settled <<<"$analysis")
  RUN_ABORTED=$(jq -r .aborted <<<"$analysis")
  RUN_STOP=$(jq -r '.stop // ""' <<<"$analysis")
  RUN_ERROR=$(jq -r '.error // ""' <<<"$analysis" | redact | cut -c1-300)
  RUN_TOKENS=$(jq -r .tokens <<<"$analysis")
  RUN_COST=$(jq -r .cost <<<"$analysis")
  RUN_RETRIES=$(jq -r .retries <<<"$analysis")
  RUN_TEXT=$(jq -r .text <<<"$analysis")
  if [[ -z $RUN_ERROR && $RUN_RC -ne 0 ]]; then
    RUN_ERROR=$(tail -n 5 "$err" | tr '\n' ' ' | redact | cut -c1-300)
  fi
  # Keep only the compact record; the raw stream holds prompts, code and tool output.
  rm -f "$raw" "$err"
}
is_provider_failure() {
  [[ $RUN_STOP == error ]] && return 0
  [[ $RUN_SETTLED != true ]] && grep -qiE '429|rate.?limit|quota|usage limit|overloaded|5[0-9]{2}|unavailable|timed? ?out|ECONN|ENOTFOUND|EAI_AGAIN|network|fetch failed|401|403|unauthori[sz]ed|forbidden|credential|api key|not logged in|/login|oauth|expired|no such model|model .*not (found|available)' <<<"$RUN_ERROR"
}
# One line per Pi run in runs.jsonl (appends are atomic): role, task, outcome, model, cost.
record() {  # role task outcome model fallback_reason [result]
  jq -cn --arg time "$(date -Iseconds)" --arg role "$1" --arg task "$2" --arg outcome "$3" --arg model "$4" \
    --arg fallback "$5" --arg result "$(redact <<<"${6:-}" | cut -c1-300)" --arg error "$RUN_ERROR" \
    --arg session "${INTEG_BRANCH:-${PI_AUTOWORK_SESSION:-}}" \
    --argjson seconds "${RUN_SECONDS:-0}" --argjson tokens "${RUN_TOKENS:-0}" --argjson cost "${RUN_COST:-0}" \
    --argjson retries "${RUN_RETRIES:-0}" \
    '{time: $time, role: $role, task: $task, outcome: $outcome, provider: ($model | split("/")[0]),
      model: ($model | split("/")[1:] | join("/")), seconds: $seconds, session: $session,
      pi_retries: $retries, fallback_reason: (if $fallback == "" then null else $fallback end),
      tokens: $tokens, cost_usd: $cost, error: (if $error == "" then null else $error end),
      result: (if $result == "" then null else $result end)}' >>"$STATE/runs.jsonl"
}

# Runs one Pi job with provider fallback and bounded retries, resuming the same
# session after a failure. Sets JOB_OK (1 when Pi finished normally) and JOB_TEXT.
pi_job() {  # role task dir message session limit [extra pi args...]
  local role=$1 task=$2 dir=$3 message=$4 session=$5 limit=$6 attempt=0 kind delay note=''
  shift 6
  JOB_OK=0 JOB_TEXT=''
  while :; do
    if over_budget; then
      say "$role $task: budget reached (\$$(spent) of \$$MAX_COST in ${COST_WINDOW} h); not starting Pi"
      return 0
    fi
    if ! choose_model; then
      RUN_SECONDS=0 RUN_TOKENS=0 RUN_COST=0 RUN_RETRIES=0 RUN_ERROR="${FALLBACK_REASON:-no model ready}"
      record "$role" "$task" no_model "$PRIMARY" "$FALLBACK_REASON"
      return 0
    fi
    run_pi "$dir" "$message$note" "$session" "$CHOSEN" "$limit" "$@"
    ((STOP)) && { record "$role" "$task" interrupted "$CHOSEN" "$FALLBACK_REASON"; return 0; }
    if ((RUN_RC == 124)); then
      record "$role" "$task" timeout "$CHOSEN" "$FALLBACK_REASON"
      return 0
    fi
    if is_provider_failure || [[ $RUN_SETTLED != true || $RUN_ABORTED == true ]]; then
      kind=crash
      is_provider_failure && kind=provider
      attempt=$((attempt + 1))
      record "$role" "$task" "${kind}_failure" "$CHOSEN" "$FALLBACK_REASON"
      ((attempt > MAX_RETRIES)) && return 0
      if [[ $kind == provider && $CHOSEN == "$PRIMARY" ]] && ((FALLBACK_ENABLED)); then
        cool_primary "${RUN_ERROR:-provider failure}"
      else
        delay=$((BACKOFF * (1 << (attempt - 1)))); ((delay > 600)) && delay=600
        sleep "$delay"
      fi
      note=' A previous attempt in this session was interrupted by a model or provider failure: first reconcile its partial work, then continue.'
      continue
    fi
    JOB_OK=1 JOB_TEXT=$RUN_TEXT
    record "$role" "$task" finished "$CHOSEN" "$FALLBACK_REASON" "$(grep -m1 -E '^PI_AUTOWORK_(RESULT|VERIFY):' <<<"$RUN_TEXT")"
    return 0
  done
}

# --- Worker and verifier (started by the engine) -------------------------------
# --worker STATE WORKTREE PROMPT REPORT TIMEOUT: one Pi worker for one engine slot.
# --verify STATE TASK: the engine's validation command for an integrated merge.
if [[ ${1:-} == --worker || ${1:-} == --verify ]]; then
  role=${1#--}
  STATE=${2:?state directory}
  [[ ${PI_AUTOWORK_NO_FALLBACK:-0} == 1 ]] && FALLBACK_ENABLED=0
  read -r -a SKILL_ARGS <<<"${PI_AUTOWORK_SKILL_ARGS:-}"
  push_guard  # the engine removes GIT_* from workers' environments
  # Stops reach the whole process group (engine and runner signal it), Pi included.
  trap 'STOP=1' INT TERM
  # Gitignored dependencies the service names (PI_AUTOWORK_LINK_PATHS) are linked from
  # the canonical checkout into this worktree first; a fresh worktree has none of them.
  link_ignored() {
    local helper
    helper=$(dirname "$SCRIPT")/../pi-autowork/pi_autowork/workspaces.py
    [[ -n ${PI_AUTOWORK_LINK_PATHS:-} && -n ${PI_AUTOWORK_REPO:-} && -f $helper ]] || return 0
    python3 "$helper" link "$PI_AUTOWORK_REPO" "$1" "$PI_AUTOWORK_LINK_PATHS" | sed 's/^/pi-autowork: linked path /' >&2
  }
  if [[ $role == worker ]]; then
    worktree=$3 prompt_file=$4 report=$5 limit=${6:-$TASK_TIMEOUT}
    link_ignored "$worktree"
    task=$(sed -n 's/^Task: //p' "$prompt_file" | head -n1)
    attempt=$(basename "$(dirname "$report")")
    pi_job worker "$task" "$worktree" "Follow the instructions in this file exactly: @$prompt_file" \
      "pi-autowork-$(safe_name "$task")-$attempt" "$limit" "@$prompt_file"
    ((JOB_OK)) && [[ -f $report ]] && exit 0
    exit 1
  fi
  task=$3
  checkout=$PWD
  link_ignored "$checkout"
  if [[ -n ${PI_AUTOWORK_VALIDATE:-} ]]; then
    if ! bash -c "$PI_AUTOWORK_VALIDATE"; then
      echo "pi-autowork: PI_AUTOWORK_VALIDATE failed for $task" >&2
      exit 1
    fi
  fi
  [[ ${PI_AUTOWORK_REVIEW:-1} == 0 ]] && exit 0
  head_before=$(git -C "$checkout" rev-parse HEAD)
  pi_job verify "$task" "$checkout" \
    "You are an independent reviewer verifying task $task in $checkout, which holds a worker's commit merged onto the session branch (see git log -1 and git diff HEAD^1 HEAD). Read the task's entry in TODO.md (its Acceptance and Checks), run the offline checks it lists, and judge the merged change against the acceptance criteria. Do not edit, create or delete files, commit, push or change branches; temporary files go in \$TMPDIR only. End with exactly one line: PI_AUTOWORK_VERIFY: pass or PI_AUTOWORK_VERIFY: fail, then the reason." \
    "pi-autowork-verify-$(safe_name "$task")-$(date +%Y%m%d%H%M%S)" "$VERIFY_TIMEOUT" --tools read,bash,grep,find,ls
  verdict=$(grep -m1 -oE '^PI_AUTOWORK_VERIFY: (pass|fail)' <<<"$JOB_TEXT" | awk '{print $2}')
  if [[ -n $(dirty "$checkout") || $(git -C "$checkout" rev-parse HEAD) != "$head_before" ]]; then
    # The engine owns this disposable integration worktree: it keeps the changes as a
    # patch for diagnosis and resets it before the next integration.
    echo "pi-autowork: the reviewer changed the checkout; verification fails" >&2
    exit 1
  fi
  ((JOB_OK)) && [[ $verdict == pass ]] && exit 0
  echo "pi-autowork: review of $task: ${verdict:-no verdict} $(grep -m1 '^PI_AUTOWORK_VERIFY:' <<<"$JOB_TEXT" | cut -c1-200)" >&2
  exit 1
fi

# --- Options ------------------------------------------------------------------
ORIGINAL_ARGS=("$@")
MODE=continuous REPO_ARG='' INTERVAL=60 MAX_CYCLES=0 SERVICE='' STATUS=0 SET_ASIDE='' FLEET=0
WORKERS=${PI_AUTOWORK_WORKERS:-8}
while (($#)); do
  case $1 in
    --once) MODE=once ;;
    --until-empty) MODE='until-empty' ;;
    --dry-run) DRY_RUN=1 ;;
    --status) STATUS=1 ;;
    --fleet) FLEET=1 ;;
    --set-aside) SET_ASIDE=${2:?--set-aside needs a task ID}; shift ;;
    --repo) REPO_ARG=${2:?--repo needs a path}; shift ;;
    --workers) WORKERS=${2:?--workers needs a number}; shift ;;
    --interval) INTERVAL=${2:?--interval needs seconds}; shift ;;
    --max-cycles) MAX_CYCLES=${2:?--max-cycles needs a number}; shift ;;
    --no-fallback) FALLBACK_ENABLED=0; export PI_AUTOWORK_NO_FALLBACK=1 ;;
    --allow-hermes) export PI_AUTOWORK_ALLOW_HERMES=1 ;;
    --install-service) SERVICE=install ;;
    --remove-service) SERVICE=remove ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown option: %s\n\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done
for value in "$INTERVAL" "$MAX_CYCLES" "$WORKERS" "$CLAIM_IDLE"; do
  [[ $value =~ ^[0-9]+$ ]] || { echo "Expected a whole number, got: $value" >&2; exit 2; }
done
((WORKERS >= 1 && WORKERS <= 8)) || die 2 "--workers must be 1 to 8"
[[ $MODE == once ]] && WORKERS=1

for tool in git jq python3 flock timeout systemd-escape; do
  command -v "$tool" >/dev/null 2>&1 || die 2 "Missing required command: $tool"
done
command -v "$PI" >/dev/null 2>&1 || die 2 "Pi not found ($PI). Install Pi, then: pi install git:github.com/TrebuchetDynamics/hermes-toolset"

STATE_ROOT=${PI_AUTOWORK_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/pi-autowork}
# Health ships beside this script in the same release.
HEALTH=$(dirname "$SCRIPT")/../pi-autowork/pi_autowork/health.py
[[ -f $HEALTH || -z ${PI_AUTOWORK_TOOLSET:-} ]] || HEALTH=$PI_AUTOWORK_TOOLSET/pi-autowork/pi_autowork/health.py
if ((FLEET)); then
  [[ -f $HEALTH ]] || die 2 "Runner health component not found next to $SCRIPT; run the installed pi-autowork.sh"
  exec python3 "$HEALTH" fleet "$STATE_ROOT"
fi

# --- Repository ---------------------------------------------------------------
is_toolset() { [[ -f $1/skills/autowork/scripts/owner_cycle.py && -f $1/skills/docs-sync/scripts/goals.py ]]; }
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
BASE=$(git -C "$REPO" symbolic-ref --short -q HEAD) || die 2 "$REPO has a detached HEAD; check out its main branch first."
DEFAULT=$(git -C "$REPO" symbolic-ref --short -q refs/remotes/origin/HEAD 2>/dev/null)
DEFAULT=${DEFAULT#origin/}
if [[ $BASE != "${DEFAULT:-main}" && $BASE != main && $BASE != master ]]; then
  die 2 "$REPO is on branch $BASE. Run the runner from the checkout of the main branch${DEFAULT:+ ($DEFAULT)}; task work happens in worktrees and is merged back there."
fi
GIT_COMMON=$(git -C "$REPO" rev-parse --path-format=absolute --git-common-dir)

# --- Hermes Toolset -----------------------------------------------------------
installed_toolset() {  # the hermes-toolset package Pi loads, from `pi list`
  local line
  while IFS= read -r line; do
    line=${line#"${line%%[![:space:]]*}"}
    [[ $line == /* ]] && is_toolset "$line" && { (cd "$line" && pwd); return 0; }
  done < <("$PI" list 2>/dev/null)
  return 1
}
# Prefer the package Pi has installed, so every run uses the skills and engine Pi loads.
SKILL_ARGS=()
if [[ -n ${PI_AUTOWORK_TOOLSET:-} ]]; then
  is_toolset "$PI_AUTOWORK_TOOLSET" || die 2 "PI_AUTOWORK_TOOLSET is not a hermes-toolset checkout: $PI_AUTOWORK_TOOLSET"
  TOOLSET=$(cd "$PI_AUTOWORK_TOOLSET" && pwd)
  installed_toolset | grep -qxF -- "$TOOLSET" || SKILL_ARGS=(--skill "$TOOLSET/adapters/skills/git-commit-push")
elif TOOLSET=$(installed_toolset); then
  :
elif TOOLSET=$(cd "$(dirname "$SCRIPT")/.." && pwd) && is_toolset "$TOOLSET"; then
  SKILL_ARGS=(--skill "$TOOLSET/adapters/skills/git-commit-push")
  printf 'pi-autowork: hermes-toolset is not installed in Pi; using %s. Install the package: pi install git:github.com/TrebuchetDynamics/hermes-toolset\n' "$TOOLSET" >&2
else
  die 2 "Hermes Toolset not found. Install it in Pi (pi install git:github.com/TrebuchetDynamics/hermes-toolset) or set PI_AUTOWORK_TOOLSET."
fi
export PI_AUTOWORK_SKILL_ARGS="${SKILL_ARGS[*]}"
# Workers and the reviewer link gitignored dependencies from here (PI_AUTOWORK_LINK_PATHS).
export PI_AUTOWORK_REPO=$REPO
ENGINE=$TOOLSET/skills/autowork/scripts/owner_cycle.py
# Health comes from the same release as the engine.
[[ -f $TOOLSET/pi-autowork/pi_autowork/health.py ]] && HEALTH=$TOOLSET/pi-autowork/pi_autowork/health.py
TOOLSET_REV=$(git -C "$TOOLSET" rev-parse --short HEAD 2>/dev/null || echo unknown)

# --- Models -------------------------------------------------------------------
in_catalog() {
  "$PI" --list-models "$(model_of "$1")" 2>/dev/null |
    awk -v p="$(provider_of "$1")" -v m="$(model_of "$1")" '$1 == p && $2 == m { found = 1 } END { exit !found }'
}
if ((!STATUS)) && [[ -z $SERVICE ]]; then
  in_catalog "$PRIMARY" || die 2 "Primary model $PRIMARY is not in Pi's model catalog (pi --list-models)."
  if ((FALLBACK_ENABLED)); then
    in_catalog "$FALLBACK" || die 2 "Fallback model $FALLBACK is not in Pi's model catalog; fix PI_AUTOWORK_FALLBACK or use --no-fallback."
  fi
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
            relative = os.path.relpath(path, home).split(os.sep)
            profile = relative[1] if relative[0] == 'profiles' else 'default'
            print(f"{profile}: {job.get('name') or job.get('id')}")
PY
}
HERMES_JOBS=$(hermes_jobs)
REPO_KEY=$(printf '%s' "$GIT_COMMON" | sha256sum | cut -c1-16)
STATE_PATH=$STATE_ROOT/$REPO_KEY
WT_ROOT=$STATE_PATH/worktrees
# A request for the running runner, which owns the engine lease; it acts within one cycle
# (or the next start) and logs the result. Nothing else is changed here.
if [[ -n $SET_ASIDE ]]; then
  [[ $SET_ASIDE =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || die 2 "Not a task ID: $SET_ASIDE"
  mkdir -p "$STATE_PATH/requests" || die 2 "Cannot create $STATE_PATH/requests"
  : >"$STATE_PATH/requests/set-aside-$SET_ASIDE"
  echo "Requested: set aside $SET_ASIDE. The runner for $REPO acts on it within one cycle; see its log."
  exit 0
fi

# --- Service ------------------------------------------------------------------
# One systemd user template serves every repository: pi-autowork@<repository name>.service;
# the instance's env file names the repository path.
# SIGINT is the runner's Ctrl+C: workers are interrupted, finished work merges, and
# the next start resumes. Deliberate exits (1, 3, 4) do not restart; crashes and kills do.
if [[ -n $SERVICE ]]; then
  ((DRY_RUN)) && die 2 "--dry-run cannot be combined with --install-service or --remove-service"
  SYSTEMCTL=${PI_AUTOWORK_SYSTEMCTL:-systemctl}
  UNIT_DIR=${PI_AUTOWORK_UNIT_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user}
  ENV_DIR=${PI_AUTOWORK_ENV_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/pi-autowork}
  INSTANCE=$(basename "$REPO")
  [[ $INSTANCE =~ ^[A-Za-z0-9._-]+$ ]] || INSTANCE=$(systemd-escape "$INSTANCE")
  UNIT="pi-autowork@$INSTANCE.service"
  OWNER=$(sed -n 's/^PI_AUTOWORK_REPO=//p' "$ENV_DIR/$INSTANCE.env" 2>/dev/null)
  if [[ -n $OWNER && $OWNER != "$REPO" ]]; then
    die 2 "$UNIT already runs $OWNER; two repositories cannot share the name $INSTANCE. Remove that service first."
  fi
  # Earlier releases named instances after the escaped path; replace such a unit.
  LEGACY=$(systemd-escape --path "$REPO")
  retire_legacy() {
    if [[ -e $ENV_DIR/$LEGACY.env ]] || "$SYSTEMCTL" --user is-enabled --quiet "pi-autowork@$LEGACY.service" 2>/dev/null; then
      "$SYSTEMCTL" --user disable --now "pi-autowork@$LEGACY.service" >/dev/null 2>&1
      rm -f "$ENV_DIR/$LEGACY.env"
      echo "Replaced the earlier unit pi-autowork@$LEGACY.service."
    fi
  }
  if [[ $SERVICE == remove ]]; then
    "$SYSTEMCTL" --user disable --now "$UNIT" || die 1 "Could not stop $UNIT"
    rm -f "$ENV_DIR/$INSTANCE.env"
    retire_legacy
    echo "Removed $UNIT. Its state, kept worktrees and any unmerged session stay in $STATE_ROOT."
    exit 0
  fi
  [[ -n $HERMES_JOBS && ${PI_AUTOWORK_ALLOW_HERMES:-0} != 1 ]] &&
    die 4 "$(printf 'A Hermes Autowork cron job already works on this repository:\n%s\nPause it, or install with --allow-hermes.' "$HERMES_JOBS")"
  mkdir -p "$UNIT_DIR" "$ENV_DIR" || die 2 "Cannot create $UNIT_DIR or $ENV_DIR"
  cat >"$UNIT_DIR/pi-autowork@.service.tmp" <<UNIT
[Unit]
Description=pi-autowork for %i
Documentation=https://github.com/TrebuchetDynamics/hermes-toolset/blob/main/docs/cross-host.md#run-autowork-continuously
After=network-online.target

[Service]
WorkingDirectory=~
EnvironmentFile=$ENV_DIR/%i.env
ExecStart=/bin/bash $SCRIPT --repo \${PI_AUTOWORK_REPO}
KillMode=mixed
KillSignal=SIGINT
TimeoutStopSec=150
SuccessExitStatus=130
Restart=on-abnormal
RestartSec=60

[Install]
WantedBy=default.target
UNIT
  mv "$UNIT_DIR/pi-autowork@.service.tmp" "$UNIT_DIR/pi-autowork@.service"
  # The service sees this login's PATH (Pi, Node, Flutter and other tools); credentials stay in Pi.
  umask 077
  {
    printf 'PI_AUTOWORK_REPO=%s\n' "$REPO"
    printf 'PATH=%s\n' "$PATH"
    [[ ${PI_AUTOWORK_ALLOW_HERMES:-0} == 1 ]] && echo 'PI_AUTOWORK_ALLOW_HERMES=1'
    [[ ${PI_AUTOWORK_NO_FALLBACK:-0} == 1 ]] && echo 'PI_AUTOWORK_NO_FALLBACK=1'
    [[ $WORKERS != 8 ]] && echo "PI_AUTOWORK_WORKERS=$WORKERS"
    for name in PI_AUTOWORK_PRIMARY PI_AUTOWORK_FALLBACK PI_AUTOWORK_TASK_TIMEOUT PI_AUTOWORK_VERIFY_TIMEOUT \
                PI_AUTOWORK_VALIDATE PI_AUTOWORK_REVIEW PI_AUTOWORK_MAX_RETRIES PI_AUTOWORK_MAX_FAILURES PI_AUTOWORK_FAILURE_PAUSE PI_AUTOWORK_STALL_AFTER PI_AUTOWORK_CLAIM_IDLE PI_AUTOWORK_LINK_PATHS \
                PI_AUTOWORK_COOLDOWN PI_AUTOWORK_BACKOFF PI_AUTOWORK_MAX_RUNTIME PI_AUTOWORK_MAX_COST \
                PI_AUTOWORK_COST_WINDOW PI_AUTOWORK_MIN_FREE_MB PI_AUTOWORK_STATE_DIR PI_AUTOWORK_TOOLSET \
                PI_AUTOWORK_INFER_TOUCHES PI_AUTOWORK_UPDATE_INTERVAL; do
      [[ -n ${!name:-} ]] && printf '%s=%s\n' "$name" "${!name}"
    done
  } >"$ENV_DIR/$INSTANCE.env"
  "$SYSTEMCTL" --user daemon-reload || die 1 "systemctl --user daemon-reload failed"
  retire_legacy  # stops it gracefully: finished work merges, the new unit resumes the rest
  "$SYSTEMCTL" --user enable "$UNIT" >/dev/null 2>&1 || die 1 "Could not enable $UNIT"
  "$SYSTEMCTL" --user restart "$UNIT" || die 1 "Could not start $UNIT"
  echo "Installed and started $UNIT for $REPO (merges into $BASE)."
  echo "Runs: $SCRIPT"
  echo "Logs: journalctl --user -u '$UNIT' -f"
  echo "Stop: systemctl --user stop '$UNIT' (interrupts workers and merges finished work); remove: $0 --remove-service --repo $REPO"
  linger=$(loginctl show-user "$USER" -p Linger --value 2>/dev/null)
  [[ $linger == yes ]] || echo "Note: user lingering is off, so the service stops at logout; enable it with: loginctl enable-linger $USER"
  exit 0
fi

# --- Engine -------------------------------------------------------------------
INTEG='' INTEG_BRANCH='' MERGE_PENDING='' RESOLVED_ONCE=0
# Runs owner_cycle.py on the session checkout; prints its JSON result.
# Helpers never inherit the runner lock (fd 9), so a killed runner releases it at once.
engine() { python3 "$ENGINE" "$INTEG" "$@" 2>>"$STATE/engine.err" 9>&-; }
owned() { engine --owner-pid "$$" "$@"; }
WORKER_COMMAND=$(jq -cn --arg script "$SCRIPT" --arg state "$STATE_PATH" \
  '["/bin/bash", $script, "--worker", $state, "{worktree}", "{prompt_file}", "{report_file}", "{timeout}"]')
# Task lifecycle words for the engine's slot states.
lifecycle() {
  case $1 in
    waiting|pending|'') echo pending ;;
    dispatched|running) echo running ;;
    reported) echo implemented ;;
    integrating) echo verifying ;;
    integrated) echo integrated ;;
    closed) echo 'done' ;;
    held|interrupted|released) echo failed ;;
    *) echo "$1" ;;
  esac
}
status_json() {
  local dir=${1:-$INTEG}
  python3 "$ENGINE" "$dir" --parallel-status --json 2>/dev/null 9>&-
}

forget_missing_worktree() {  # drop only this path's stale registration; other worktrees are not ours to prune
  [[ -e $1 ]] && return 0
  git -C "$REPO" worktree list --porcelain | grep -qxF "worktree $1" || return 0
  git -C "$REPO" worktree remove "$1"
}

load_session() {  # "ro" never recreates a missing worktree
  [[ -f $STATE_PATH/session.json ]] || return 1
  INTEG_BRANCH=$(jq -r .branch "$STATE_PATH/session.json") INTEG=$(jq -r .path "$STATE_PATH/session.json")
  git -C "$REPO" show-ref --verify -q "refs/heads/$INTEG_BRANCH" || { rm -f "$STATE_PATH/session.json"; INTEG='' INTEG_BRANCH=''; return 1; }
  if [[ ! -d $INTEG ]]; then
    [[ ${1:-} == ro ]] && return 1
    forget_missing_worktree "$INTEG"
    git -C "$REPO" worktree add -q "$INTEG" "$INTEG_BRANCH" || die 1 "Cannot restore the integration worktree for $INTEG_BRANCH"
  fi
  export PI_AUTOWORK_SESSION=$INTEG_BRANCH
}

# --- Status and dry run ---------------------------------------------------------
summarize() {
  echo "PI AUTOWORK"
  echo "Repository: $REPO (merges into $BASE)"
  if ((${#SKILL_ARGS[@]})); then
    echo "Toolset:    $TOOLSET at $TOOLSET_REV (not a Pi package)"
  else
    echo "Toolset:    $TOOLSET at $TOOLSET_REV (Pi package)"
  fi
  echo "Engine:     Parallel Autowork, up to $WORKERS worker(s)"
  echo "Primary:    $PRIMARY ($(auth_ready "$PRIMARY" && echo ready || echo 'not ready'))"
  if ((FALLBACK_ENABLED)); then
    echo "Fallback:   $FALLBACK ($(auth_ready "$FALLBACK" && echo ready || echo 'not ready'))"
  else
    echo "Fallback:   disabled"
  fi
  if [[ $MAX_COST != 0 ]]; then
    echo "Budget:     \$$(spent) of \$$MAX_COST in the last $COST_WINDOW h"
  fi
  echo "Mode:       $MODE; state and worktrees in $STATE_PATH"
}
if ((STATUS || DRY_RUN)); then
  summarize
  [[ -n $HERMES_JOBS ]] && printf 'Hermes Autowork cron jobs target this repository%s:\n%s\n' \
    "$([[ ${PI_AUTOWORK_ALLOW_HERMES:-0} == 1 ]] && echo ' (allowed; the engine lease keeps them apart)' || echo ' (the runner would refuse)')" "$HERMES_JOBS"
  if [[ -e $STATE_PATH/lock ]] && ! flock -n "$STATE_PATH/lock" true; then
    echo "Runner:     running ($(jq -r '"PID \(.pid), since \(.started)"' "$STATE_PATH/runner.json" 2>/dev/null))"
  else
    echo "Runner:     not running"
  fi
  view=$REPO
  if load_session ro; then
    echo "Session:    $INTEG_BRANCH, $(git -C "$REPO" rev-list --count "$BASE..$INTEG_BRANCH") commit(s) not yet merged into $BASE"
    view=$INTEG
  else
    echo "Session:    none; a new integration branch would start from $BASE"
  fi
  [[ -n $(dirty "$REPO") ]] && echo "Note:       $REPO has uncommitted changes; the final merge stops if it would touch them"
  snapshot=$(status_json "$view")
  if [[ -n $snapshot ]]; then
    echo "Workers:    $(jq -r '"\(.active_workers // 0) running; \(.completed // 0) done, \(.failed // 0) failed, \(.integration_queue // 0) awaiting integration"' <<<"$snapshot")"
    if [[ -f $STATE_PATH/status.json ]]; then
      jq -r '"Health:     \(.state) since \(.since | floor | strflocaltime("%Y-%m-%d %H:%M"))"
        + ([.roots[]? | select(.kind | IN("runner", "held", "claim", "outside", "cycle"))][:3]
           | if length == 0 then "" else "; blocked by " + (map("\(.id | gsub("\\s+"; " ") | .[:60]) (\(.kind), holds \(.blocks))") | join("; ")) end)' \
        "$STATE_PATH/status.json" 2>/dev/null
    fi
    while IFS=$'\t' read -r id state reason; do
      printf '  %-12s %-12s %s\n' "$id" "$(lifecycle "$state")" "$reason"
    done < <(jq -r '.tasks[]? | [.task, .state, (.reason // .blocked_reason // "")] | @tsv' <<<"$snapshot" | head -40)
  fi
  ((STATUS)) && exit 0
  echo "Dry run: nothing was changed."
  exit 0
fi

[[ -n $HERMES_JOBS && ${PI_AUTOWORK_ALLOW_HERMES:-0} != 1 ]] &&
  die 4 "$(printf 'A Hermes Autowork cron job already works on this repository; two agents would write at once:\n%s\nPause it, or set PI_AUTOWORK_ALLOW_HERMES=1 (the engine lease then lets only one of them work at a time).' "$HERMES_JOBS")"

mkdir -p "$STATE_PATH/sessions" "$STATE_PATH/runs" "$WT_ROOT" || die 2 "Cannot create state directory $STATE_PATH"
STATE=$STATE_PATH
exec 9>>"$STATE/lock"
# A coordinator that was just killed can leave a helper holding the lock for a few seconds.
if ! flock -w 15 9; then
  owner=$(jq -r '"PID \(.pid), started \(.started)"' "$STATE/runner.json" 2>/dev/null || echo 'unknown owner')
  die 3 "Another pi-autowork runner holds $REPO ($owner)."
fi
jq -n --arg pid "$$" --arg started "$(date -Iseconds)" --arg repo "$REPO" '{pid: ($pid | tonumber), started: $started, repo: $repo}' >"$STATE/runner.json"
push_guard

# --- Signals ------------------------------------------------------------------
worker_groups() {  # process groups of this repository's live engine workers
  local slots=$GIT_COMMON/autowork-execution/slots
  [[ -d $slots ]] || return 0
  jq -r 'select(.state == "running" or .state == "dispatched") | .worker.pid // empty' "$slots"/*.json 2>/dev/null
}
on_signal() {
  if ((STOP)); then
    for pgid in $(worker_groups); do kill -TERM -- "-$pgid" 2>/dev/null; done
    [[ -n $CHILD ]] && kill -TERM "$CHILD" 2>/dev/null
    return
  fi
  STOP=1
  say "Stopping: pausing workers so they resume on the next start, then merging finished work (Ctrl+C again to force)"
  # Workers are interrupted by the main loop after the engine marks them paused, so a
  # deliberate stop or restart neither spends a task's retry nor holds a second attempt.
  [[ -n $CHILD ]] && kill -INT "$CHILD" 2>/dev/null
}
stop_helpers() {
  local pid
  for pid in "$KILLER" "$SLEEPER"; do
    [[ -n $pid ]] || continue
    kill -STOP "$pid" 2>/dev/null
    pkill -P "$pid" 2>/dev/null
    kill "$pid" 2>/dev/null
    kill -CONT "$pid" 2>/dev/null
  done
  KILLER='' SLEEPER=''
}
trap on_signal INT TERM
trap 'stop_helpers; rm -f "$STATE/runner.json"' EXIT
pause() {  # interruptible sleep that never holds the lock
  sleep "$1" >/dev/null 2>&1 9>&- &
  SLEEPER=$!
  wait "$SLEEPER" 2>/dev/null
  stop_helpers
}

# --- Session ------------------------------------------------------------------
ensure_session() {
  [[ -n $INTEG ]] && return 0
  load_session && return 0
  INTEG_BRANCH="pi-autowork/$(date +%Y%m%d-%H%M%S)" INTEG=$WT_ROOT/integration
  forget_missing_worktree "$INTEG"
  [[ -e $INTEG ]] && die 1 "$INTEG exists but belongs to no session; remove it after checking its contents."
  git -C "$REPO" worktree add -q -b "$INTEG_BRANCH" "$INTEG" "$BASE" || die 1 "Cannot create the integration worktree"
  jq -n --arg branch "$INTEG_BRANCH" --arg path "$INTEG" --arg base "$BASE" --arg started "$(date -Iseconds)" \
    '{branch: $branch, path: $path, base: $base, started: $started}' >"$STATE/session.json"
  export PI_AUTOWORK_SESSION=$INTEG_BRANCH
  say "Session $INTEG_BRANCH started from $BASE"
}
end_session() {  # only a clean, fully merged session is removed
  if [[ -n $(dirty "$INTEG") ]]; then
    say "Session worktree $INTEG has uncommitted changes; keeping it and $INTEG_BRANCH"
    return 1
  fi
  git -C "$REPO" worktree remove "$INTEG" || return 1
  git -C "$REPO" branch -q -D "$INTEG_BRANCH" 2>/dev/null
  rm -f "$STATE/session.json"
  INTEG='' INTEG_BRANCH='' RESOLVED_ONCE=0
}

# Merges the session into $BASE: $BASE into the session branch first (Pi resolves
# conflicts once per session), then a fast-forward of $BASE in the main checkout.
merge_main() {
  local ahead files out current
  MERGE_PENDING=''
  [[ -n $INTEG ]] || load_session || return 0
  ahead=$(git -C "$REPO" rev-list --count "$BASE..$INTEG_BRANCH")
  if ((ahead == 0)); then
    return 0
  fi
  if ! git -C "$INTEG" merge -q --no-edit "$BASE" >/dev/null 2>&1; then
    files=$(git -C "$INTEG" diff --name-only --diff-filter=U | paste -sd' ' -)
    if ((!STOP && !RESOLVED_ONCE)); then
      RESOLVED_ONCE=1
      say "$BASE moved and conflicts with this session in: $files; asking Pi to resolve the merge"
      pi_job merge "${INTEG_BRANCH#pi-autowork/}" "$INTEG" "/skill:git-commit-push This worktree is on branch $INTEG_BRANCH with an unfinished merge of $BASE that conflicts in: $files. Resolve every conflict keeping both sides' work: keep both task entries in TODO.md and TODO.archive.md, keep every task record in goals.json and run python3 $TOOLSET/skills/docs-sync/scripts/goals.py validate . if it exists, then run the checks that cover the conflicted files and conclude the merge with a commit. Do not push, rebase, switch branches or touch $REPO. End with one line: PI_AUTOWORK_RESULT: completed|blocked, then one sentence." \
        "pi-autowork-merge-$(date +%Y%m%d%H%M%S)" "$VERIFY_TIMEOUT"
    fi
    local marker
    marker=$(git -C "$INTEG" rev-parse --path-format=absolute --git-path MERGE_HEAD)
    if [[ -e $marker ]] || ! git -C "$REPO" merge-base --is-ancestor "$BASE" "$INTEG_BRANCH" || [[ -n $(dirty "$INTEG") ]]; then
      git -C "$INTEG" merge --abort 2>/dev/null
      MERGE_PENDING="$INTEG_BRANCH conflicts with $BASE in: $files"
      say "Merge pending: $MERGE_PENDING. The branch and its worktree ($INTEG) are kept."
      return 1
    fi
  fi
  current=$(git -C "$REPO" symbolic-ref --short -q HEAD)
  if [[ $current != "$BASE" ]]; then
    MERGE_PENDING="$REPO is on ${current:-a detached HEAD}, not $BASE"
  elif ! out=$(git -C "$REPO" merge --ff-only "$INTEG_BRANCH" 2>&1); then
    MERGE_PENDING="$BASE in $REPO could not take $INTEG_BRANCH: $(grep -m1 -iE 'error|fatal|abort' <<<"$out" || head -n1 <<<"$out")"
  fi
  if [[ -n $MERGE_PENDING ]]; then
    say "Merge pending: $MERGE_PENDING. Branch $INTEG_BRANCH is kept; the next run retries."
    return 1
  fi
  say "Merged $INTEG_BRANCH into $BASE ($ahead commit(s), not pushed)"
}

# --- Coordinator ----------------------------------------------------------------
STARTED=$SECONDS STARTED_WORKERS=0 FAILURES=0 DRAINING=0 ONCE_TASK='' ONCE_DONE=0 LAST_WAITING=''
declare -A SEEN=()

note_state() {  # log each task's lifecycle change once
  local id=$1 state=$2 reason=$3 word
  word=$(lifecycle "$state")
  [[ ${SEEN[$id]:-} == "$word" ]] && return
  SEEN[$id]=$word
  say "$id: $word${reason:+ — $reason}"
}

close_task() {  # archive an integrated task and commit the coordinator files
  local id=$1 result file followup
  result=$(owned --parallel-close "$id")
  if [[ $(jq -r .outcome <<<"$result" 2>/dev/null) == CLOSED ]]; then
    # Exactly the files the close wrote (TODO.md, goals.json, the archive it chose).
    while IFS= read -r file; do
      [[ -n $file ]] && git -C "$INTEG" add -A -- "$file"
    done < <(jq -r '.files[]?' <<<"$result" 2>/dev/null)
    git -C "$INTEG" diff --cached --quiet ||
      git -C "$INTEG" commit -q -m "docs(tasks): close $id (pi-autowork)" -m "Integrated, verified and closed by the Parallel Autowork engine."
    note_state "$id" closed ''
    followup=$(jq -r '.live_followup // empty' <<<"$result" 2>/dev/null)
    [[ -n $followup ]] && say "$id: done offline; its live checks are recorded as $followup (Needs decision)"
    FAILURES=0
    [[ $id == "$ONCE_TASK" ]] && ONCE_DONE=1
    SETTLED=1
  else
    result=$(jq -r '.reason // .outcome' <<<"$result" 2>/dev/null || echo "$result")
    # Its TODO entry was rewritten after the merge: the merge stays in main and the
    # new entry is new work, so retire the slot instead of blocking on it forever.
    if [[ $result == 'task contract changed since integration; no close' ]] &&
        [[ $(owned --parallel-set-aside "$id" | jq -r .outcome 2>/dev/null) == SET_ASIDE ]]; then
      say "$id: its TODO entry changed after integration; the merged work stays in main and the task is queued again under its new entry"
      SEEN[$id]=pending
      SETTLED=1
      return
    fi
    [[ ${SEEN["close-$id"]:-} == "$result" ]] || say "$id: could not close: $result"
    SEEN["close-$id"]=$result
  fi
}

# Integrates, verifies and closes every reported task, in the engine's priority order.
settle() {
  local snapshot id result outcome reason before
  SETTLED=0
  snapshot=$(status_json) || return 0
  while IFS=$'\t' read -r id state reason; do
    before=${SEEN[$id]:-}
    note_state "$id" "$state" "$reason"
    [[ $id == "$ONCE_TASK" && $state == held ]] && DRAINING=1
    # Only a failure this run watched happen counts toward the streak; holds found at
    # start (say after a self-restart) were counted, if at all, by the run that saw them.
    [[ $state == held && -n $before && $before != failed ]] && count_failure "$id"
  done < <(jq -r '.tasks[]? | [.task, .state, (.reason // "")] | @tsv' <<<"$snapshot")
  ((STOP)) && return 0
  # Integrated but not closed (a close that failed earlier, or a restart in between).
  for id in $(jq -r '.tasks[]? | select(.state == "integrated") | .task' <<<"$snapshot"); do
    ((STOP)) && return 0
    close_task "$id"
  done
  for id in $(jq -r '.tasks[]? | select(.state == "reported" or .state == "integrating") | .task' <<<"$snapshot"); do
    ((STOP)) && return 0
    note_state "$id" integrating ''
    result=$(owned --integrate "$id" --timeout "$VERIFY_TIMEOUT" --run /bin/bash "$SCRIPT" --verify "$STATE" "$id")
    outcome=$(jq -r '.outcome // "ACTION_REQUIRED"' <<<"$result" 2>/dev/null)
    reason=$(jq -r '.reason // ""' <<<"$result" 2>/dev/null)
    case $outcome in
      INTEGRATED)
        SETTLED=1
        note_state "$id" integrated ''
        close_task "$id" ;;
      HELD)
        SETTLED=1
        if [[ $(jq -r '.cause // ""' <<<"$result") == scope ]] &&
           widen_inferred "$id" "$(jq -r '(.outside // []) | join(", ")' <<<"$result")"; then
          continue  # the next refill verifies the same commit again (RESCOPED)
        fi
        note_state "$id" held "$reason"
        count_failure "$id"
        [[ $id == "$ONCE_TASK" ]] && DRAINING=1 ;;
      *)
        [[ $reason == *highest-priority* ]] && continue  # another reported task goes first
        say "$id: integration needs attention: ${reason:-$outcome}" ;;
    esac
  done
}

finish() {
  local code=$1
  if [[ -n $INTEG ]]; then
    merge_main
    if [[ -z $MERGE_PENDING ]] && ! status_json | jq -e '.tasks[]? | select(.state as $s | ["dispatched","running","reported","integrating","integrated"] | index($s))' >/dev/null 2>&1; then
      owned --parallel "$WORKERS" --max-workers 8 --release >/dev/null
      [[ $(git -C "$REPO" rev-list --count "$BASE..$INTEG_BRANCH" 2>/dev/null) == 0 ]] && end_session
    fi
  fi
  if [[ -n $MERGE_PENDING && $code == 0 ]]; then code=4; fi
  say "$2"
  exit "$code"
}

# --- Self-update ----------------------------------------------------------------
# A long-running service would otherwise keep the release it started with until someone
# runs `pi update`. While nothing is in flight, update the hermes-toolset package Pi
# loads, at most once per interval and one runner at a time across repositories; the
# main loop then restarts on the new release.
UPDATE_INTERVAL=${PI_AUTOWORK_UPDATE_INTERVAL:-3600}
LAST_UPDATE_NOTE=''
LAST_UPDATE=$SECONDS
update_toolset() {
  local source
  [[ $MODE == continuous && $UPDATE_INTERVAL != 0 ]] || return 0
  ((SECONDS - LAST_UPDATE >= UPDATE_INTERVAL)) || return 0
  LAST_UPDATE=$SECONDS
  ((${#SKILL_ARGS[@]})) && return 0  # not the package Pi loads: a checkout is updated by its owner
  source=$(git -C "$TOOLSET" remote get-url origin 2>/dev/null) || return 0
  local release=$TOOLSET/pi-autowork/pi_autowork/release.py check reason
  # One updater at a time; the safety check runs under the same lock as the update.
  exec 8>>"$STATE_ROOT/toolset-update.lock"
  if ! flock -w 600 8; then exec 8>&-; return 0; fi
  if [[ -f $release ]] && ! check=$(python3 "$release" check "$STATE_ROOT" "$STATE" "$TOOLSET" 2>>"$STATE/engine.err" 8>&- 9>&-); then
    # Another runner's work in flight, or a release that cannot read this state.
    reason=$(jq -r '.reason // "update check failed"' <<<"$check" 2>/dev/null)
    if ! jq -e '.current' <<<"$check" >/dev/null 2>&1 && [[ $reason != "$LAST_UPDATE_NOTE" ]]; then
      say "Toolset update deferred: $reason"
    fi
    LAST_UPDATE_NOTE=$reason
  else
    LAST_UPDATE_NOTE=''
    timeout 300 "$PI" update "$source" >>"$STATE/engine.err" 2>&1 8>&- 9>&- ||
      say "Toolset update failed (see $STATE/engine.err); keeping $TOOLSET_REV"
  fi
  exec 8>&-
}

# --- Health ---------------------------------------------------------------------
# Records this runner's state in $STATE/status.json each cycle; announces a stall once
# (no task running while work waits for PI_AUTOWORK_STALL_AFTER seconds) with its roots.
health_update() {
  local line paused=0
  [[ -f $HEALTH ]] || return 0
  ((PAUSE_UNTIL > SECONDS)) && paused=$(($(date +%s) + PAUSE_UNTIL - SECONDS))
  line=$(status_json | PI_AUTOWORK_HEALTH_REPO=$REPO PI_AUTOWORK_HEALTH_PID=$$ \
    PI_AUTOWORK_HEALTH_TOOLSET_REV=$TOOLSET_REV PI_AUTOWORK_HEALTH_MODE=$MODE \
    PI_AUTOWORK_HEALTH_PAUSED_UNTIL=$paused PI_AUTOWORK_HEALTH_STALL_AFTER=${PI_AUTOWORK_STALL_AFTER:-1800} \
    PI_AUTOWORK_HEALTH_BLOCKER=$RUNNER_BLOCKER \
    python3 "$HEALTH" update "$STATE" 2>>"$STATE/engine.err") || return 0
  [[ -n $line ]] && warn "$line"
  return 0
}

count_failure() {
  [[ ${SEEN["counted-$1"]:-} == 1 ]] && return 0
  SEEN["counted-$1"]=1
  FAILURES=$((FAILURES + 1))
}

# --- Scope ----------------------------------------------------------------------
# Touches this runner inferred are a guess. When a worker's commit is held only for
# changing files outside them, widen the guess to those files once and let the engine
# verify the same commit again (RESCOPED); every other check still applies. Touches a
# person wrote, or edited since, are never changed: the helper refuses.
remember_inferred() {  # $1 task, $2 recorded Touches
  local merged
  merged=$(jq -c --arg id "$1" --arg t "$2" '.[$id] = $t' "$TOUCHES_INFERRED" 2>/dev/null || jq -cn --arg id "$1" --arg t "$2" '{($id): $t}')
  printf '%s\n' "$merged" >"$TOUCHES_INFERRED.tmp" && mv "$TOUCHES_INFERRED.tmp" "$TOUCHES_INFERRED"
}
widen_inferred() {  # $1 task, $2 comma-separated files outside its Touches
  local recorded widened
  recorded=$(jq -r --arg id "$1" '.[$id] // empty' "$TOUCHES_INFERRED" 2>/dev/null)
  [[ -n $recorded && -n $2 && -z $(dirty "$INTEG") ]] || return 1
  [[ ${SEEN["widened-$1"]:-} == 1 ]] && return 1  # once per task in this run
  widened=$(python3 "$TOUCHES_HELPER" widen "$INTEG" "$TOOLSET" "$1" "$recorded" "$2" 2>>"$STATE/engine.err") || return 1
  git -C "$INTEG" add -- TODO.md
  git -C "$INTEG" commit -q -m "docs(tasks): widen inferred Touches for $1 (pi-autowork)" \
    -m "The worker's commit changed $2, outside the inferred Touches; the engine verifies it again."
  remember_inferred "$1" "$widened"
  SEEN["widened-$1"]=1
  say "$1: its commit changed files outside the inferred Touches ($2); widened them and verifying again"
  return 0
}

# --- Priority -------------------------------------------------------------------
# TODO.md order is the human priority; goals.json records it. On drift, record the order
# in the session with the documented guarded command, commit only goals.json, and select
# again. One attempt per TODO.md revision; a refusal is reported, never retried blindly.
reconcile_priority() {
  local goals=$TOOLSET/skills/docs-sync/scripts/goals.py revision out
  DRIFT_REASON=''
  revision=$(python3 "$goals" revision "$INTEG" 2>>"$STATE/engine.err") || { DRIFT_REASON='no ledger revision'; return 1; }
  if [[ $revision == "$DRIFT_TRIED" ]]; then
    DRIFT_REASON=${DRIFT_LAST_REASON:-'drift remains after recording the order'}
    return 1
  fi
  DRIFT_TRIED=$revision
  if [[ -n $(dirty "$INTEG") ]]; then
    DRIFT_REASON='the session checkout has uncommitted changes'
  elif ! out=$(python3 "$goals" reorder "$INTEG" --expected-revision "$revision" 2>&1); then
    DRIFT_REASON=$(printf '%s' "$out" | tail -n 3 | tr '\n' ' ' | cut -c1-300)
  else
    git -C "$INTEG" add -- goals.json
    git -C "$INTEG" diff --cached --quiet ||
      git -C "$INTEG" commit -q -m "docs(tasks): record TODO.md priority order (pi-autowork)" -m "TODO.md order is the human priority; recorded with goals.py reorder."
    # Drift that survives the recording is not something another reorder fixes.
    DRIFT_TRIED=$(python3 "$goals" revision "$INTEG" 2>/dev/null)
    DRIFT_LAST_REASON='drift remains after recording the order (duplicate task IDs?)'
    say "TODO.md priority changed; recorded the new order and selecting again"
    return 0
  fi
  DRIFT_LAST_REASON=$DRIFT_REASON
  return 1
}

# --- Requests -------------------------------------------------------------------
# `pi-autowork.sh --set-aside TASK` leaves a request here; only this runner holds the
# engine lease, so it performs the request and reports the engine's answer.
handle_requests() {
  local request id result
  for request in "$STATE"/requests/set-aside-*; do
    [[ -e $request ]] || continue
    id=${request##*/set-aside-}
    result=$(owned --parallel-set-aside "$id")
    # Before this runner's first dispatch it holds no lease yet: keep the request.
    [[ $result == *'live parallel coordinator owner'* ]] && continue
    rm -f -- "$request"
    if [[ $(jq -r .outcome <<<"$result" 2>/dev/null) == SET_ASIDE ]]; then
      SEEN[$id]=pending
      SETTLED=1
      say "$id: set aside on request; its earlier work is kept as $(jq -r '[.renamed[]? | .branch_now // empty] | join(", ")' <<<"$result"); the task will run fresh"
    else
      say "$id: could not set aside: $(jq -r '.reason // .outcome' <<<"$result" 2>/dev/null || echo "$result")"
    fi
  done
}

# --- Scratch checkouts -----------------------------------------------------------
# Read-only passes get a detached worktree of the session HEAD under $STATE/scratch.
# Only such a path, created here, is ever force-removed.
scratch_checkout() {  # $1 purpose; prints the path
  local path
  mkdir -p "$STATE/scratch"
  path=$(mktemp -d "$STATE/scratch/$1-XXXXXX") && rmdir "$path" &&
    git -C "$INTEG" worktree add -q --detach "$path" HEAD >/dev/null 2>>"$STATE/engine.err" && printf '%s' "$path"
}
drop_scratch() {
  [[ $1 == "$STATE"/scratch/* ]] || return 0
  git -C "$INTEG" worktree remove --force "$1" 2>>"$STATE/engine.err" || rm -rf -- "$1"
  git -C "$INTEG" worktree prune 2>/dev/null
}

# --- Touches ------------------------------------------------------------------
# A task without Touches: must run alone, so most backlogs would run one task at a
# time. For the top runnable tasks lacking it, a read-only Pi pass proposes the paths
# and the runner records them in the session branch. The engine enforces them: a
# worker that changes files outside its Touches is held, never silently merged.
TOUCHES_HELPER=$TOOLSET/pi-autowork/pi_autowork/touches_inference.py
[[ -f $TOUCHES_HELPER ]] || TOUCHES_HELPER=$(dirname "$SCRIPT")/../pi-autowork/pi_autowork/touches_inference.py
# Touches this runner recorded itself, per task: only those may be widened later.
TOUCHES_INFERRED=$STATE/touches-inferred.json
declare -A TOUCHES_TRIED=()
touches_prompt() {  # $1 task, $2 checkout
  printf '%s' "Plan the file scope of task $1 in $2 so it can run beside other tasks. Read its entry in TODO.md, then the files and directories its Sources, Scope and acceptance name, and the repository layout around them. List the repository-relative files, directories (ending in /) or globs the task's change will edit, including its tests and docs; prefer a component's directory over guessing single files, and when unsure widen to the owning directories rather than give up: a worker that edits outside the list is only held and retried alone. Scope is about which files change, not how the result is checked: a task verified on a device, emulator, screenshot harness or live service still lists the code and test files it edits. Never list TODO.md, TODO.archive.md, goals.json or CHANGELOG.md. Answer NONE only when the task edits no repository file (purely live, manual or device operation) or would edit files across most of the repository, and give the reason. Do not change any file. End with exactly one line: PI_AUTOWORK_TOUCHES: path, path, ... or PI_AUTOWORK_TOUCHES: NONE - reason"
}
# Answers are remembered per prompt version: a changed prompt asks every task again.
TOUCHES_CACHE=touches-$(touches_prompt TASK DIR | sha256sum | cut -c1-12).json
touches_hold() {  # $1 task, $2 seconds before it is asked again
  local cache=$STATE/$TOUCHES_CACHE
  jq -n --slurpfile old <(cat "$cache" 2>/dev/null || echo '{}') --arg id "$1" --argjson until "$(($(date +%s) + $2))" \
    '($old[0] // {}) + {($id): $until}' >"$cache.$$" && mv "$cache.$$" "$cache"
}
infer_touches() {
  local list id answer recorded scratch
  [[ ${PI_AUTOWORK_INFER_TOUCHES:-1} == 0 || ! -f $TOUCHES_HELPER ]] && return 0
  list=$(python3 "$TOUCHES_HELPER" missing "$INTEG" "$TOOLSET" "$WORKERS" 2>>"$STATE/engine.err") || return 0
  for id in $(jq -r '.[].id' <<<"$list" 2>/dev/null); do
    ((STOP)) && return 0
    [[ -n ${TOUCHES_TRIED[$id]:-} ]] && continue
    TOUCHES_TRIED[$id]=1
    # A task judged unboundable is asked again after a day, not every cycle.
    jq -e --arg id "$id" --arg now "$(date +%s)" '.[$id] // 0 | . > ($now | tonumber)' "$STATE/$TOUCHES_CACHE" >/dev/null 2>&1 && continue
    # A planning pass reads a disposable copy of the session, so nothing it does can
    # touch the session checkout; the copy is removed afterwards.
    scratch=$(scratch_checkout touches) || { say "$id: could not create a scratch checkout; skipping the Touches pass"; continue; }
    pi_job touches "$id" "$scratch" "$(touches_prompt "$id" "$scratch")" \
      "pi-autowork-touches-$(safe_name "$id")-$(date +%Y%m%d%H%M%S)" 900 --tools read,grep,find,ls
    drop_scratch "$scratch"
    answer=$(grep -m1 '^PI_AUTOWORK_TOUCHES:' <<<"$JOB_TEXT" | sed 's/^PI_AUTOWORK_TOUCHES:[[:space:]]*//')
    if ((JOB_OK)) && [[ -n $answer && ! $answer =~ ^NONE([^[:alnum:]_./]|$) ]] &&
       recorded=$(python3 "$TOUCHES_HELPER" apply "$INTEG" "$TOOLSET" "$id" "$answer" 2>>"$STATE/engine.err"); then
      git -C "$INTEG" add -- TODO.md
      git -C "$INTEG" commit -q -m "docs(tasks): declare Touches for $id (pi-autowork)" -m "Proposed by a read-only planning pass; the engine holds any change outside it."
      remember_inferred "$id" "$recorded"
      say "$id: can run beside others; Touches: $recorded"
    elif ((!JOB_OK)) || [[ -z $answer ]]; then
      # No answer (provider failure, timeout, missing result line) is not a judgment.
      touches_hold "$id" 3600
      unset "TOUCHES_TRIED[$id]"
      say "$id: runs alone for now (the Touches pass gave no answer; asking again within the hour)"
    else
      touches_hold "$id" 86400
      say "$id: runs alone (no Touches proposed: $answer)"
    fi
  done
}

summarize
say "Started (PID $$). Stop with Ctrl+C."
while :; do
  if ((STOP)); then
    if ((!PAUSED)); then
      PAUSED=1
      owned --parallel-pause >/dev/null
      for pgid in $(worker_groups); do kill -INT -- "-$pgid" 2>/dev/null; done
    fi
    # Interrupted workers stay in their worktrees; the next start resumes them.
    for _ in 1 2 3 4; do owned --parallel "$WORKERS" --max-workers 8 --wait --timeout 5 >/dev/null; done
    settle
    finish 130 "Stopped. Unfinished tasks keep their worktrees and resume on the next start."
  fi
  # Idle: let `pi update` bring in a newer toolset (rate-limited, one runner at a time).
  if ((!DRAINING)) && ! status_json | jq -e '.tasks[]? | select(.state as $s | ["dispatched","running","reported","integrating","integrated"] | index($s))' >/dev/null 2>&1; then
    update_toolset
  fi
  # `pi update` replaces the script and the engine under a running runner, and the
  # engine is loaded afresh on every call: continue on the new release instead of
  # mixing the two. State is durable and a restart adopts live workers.
  if [[ $MODE == continuous && $TOOLSET_REV != unknown ]] &&
     rev=$(git -C "$TOOLSET" rev-parse --short HEAD 2>/dev/null) && [[ $rev != "$TOOLSET_REV" ]]; then
    if bash -n "$SCRIPT" 2>>"$STATE/engine.err"; then
      say "Toolset updated to $rev; restarting on it"
      stop_helpers
      trap - EXIT INT TERM
      rm -f "$STATE/runner.json"
      exec 9>&-
      exec /bin/bash "$SCRIPT" "${ORIGINAL_ARGS[@]}"
    fi
    say "Toolset changed to $rev, but $SCRIPT does not parse; keeping the running $TOOLSET_REV"
    TOOLSET_REV=$rev
  fi
  ensure_session
  # While nothing is in flight the session follows the main branch (fast-forward, or a
  # merge once it has commits of its own), so tasks committed meanwhile are seen.
  # Only while nothing is in flight: moving the base under a running worker would make
  # its integration conflict.
  if [[ -n $(git -C "$REPO" rev-list "$INTEG_BRANCH..$BASE" 2>/dev/null) && -z $(dirty "$INTEG") ]] &&
     ! status_json | jq -e '.tasks[]? | select(.state as $s | ["dispatched","running","reported","integrating","integrated"] | index($s))' >/dev/null 2>&1; then
    if ! git -C "$INTEG" merge -q --no-edit "$BASE" >/dev/null 2>&1; then
      git -C "$INTEG" merge --abort 2>/dev/null  # a conflicting main waits for the end-of-session merge
    fi
  fi
  if ((!DRAINING)); then
    ((MAX_CYCLES && STARTED_WORKERS >= MAX_CYCLES)) && { DRAINING=1; say "Reached --max-cycles $MAX_CYCLES; finishing running tasks"; }
    ((MAX_RUNTIME && SECONDS - STARTED >= MAX_RUNTIME)) && { DRAINING=1; say "Reached PI_AUTOWORK_MAX_RUNTIME; finishing running tasks"; }
    over_budget && { DRAINING=1; say "Budget reached (\$$(spent) of \$$MAX_COST in $COST_WINDOW h); finishing running tasks"; }
    if ((FAILURES >= MAX_FAILURES)); then
      if [[ $MODE == continuous ]]; then
        # A service that exits on its own is a silent stop; pause new work instead.
        say "$FAILURES tasks failed in a row; pausing new tasks for ${FAILURE_PAUSE}s (running ones continue)"
        FAILURES=0
        PAUSE_UNTIL=$((SECONDS + FAILURE_PAUSE))
      else
        DRAINING=1; say "Stopping after $FAILURES failed tasks in a row; finishing running tasks"
      fi
    fi
  fi
  if ((!DRAINING)) && ! choose_model; then
    case $MODE in
      once|until-empty) finish 1 "No usable model: ${FALLBACK_REASON:-primary and fallback not ready}" ;;
    esac
    say "No usable model (${FALLBACK_REASON:-primary and fallback not ready}); checking again in ${INTERVAL}s"
    RUNNER_BLOCKER="no usable model: ${FALLBACK_REASON:-primary and fallback not ready}"
    health_update
    pause "$INTERVAL"
    continue
  fi
  RUNNER_BLOCKER=''
  if ((!DRAINING && SECONDS < PAUSE_UNTIL)); then
    outcome=PAUSED  # after a failure streak: settle running work, start nothing new
  elif ((!DRAINING)); then
    infer_touches
    result=$(owned --apply --parallel "$WORKERS" --max-workers 8 --worker-command "$WORKER_COMMAND" \
      --worker-timeout "$TASK_TIMEOUT" --min-free-mem-mb "$MIN_FREE_MB" --adopt-idle-claims "$CLAIM_IDLE")
    outcome=$(jq -r '.outcome // "ACTION_REQUIRED"' <<<"$result" 2>/dev/null || echo ACTION_REQUIRED)
  elif ((DRAINING)); then
    outcome=DRAINING
  fi
  case $outcome in
    DISPATCHED|RETRIED)
      for id in $(jq -r '(.dispatched // [])[]?.task, (.retried // empty | .task? // empty)' <<<"$result" 2>/dev/null); do
        STARTED_WORKERS=$((STARTED_WORKERS + 1))
        [[ $MODE == once && -z $ONCE_TASK ]] && { ONCE_TASK=$id; DRAINING=1; }  # no second task
        if jq -e --arg id "$id" '(.adopted // []) | index($id)' <<<"$result" >/dev/null 2>&1; then
          note_state "$id" running "worker started; adopted an idle claim (no activity for $((CLAIM_IDLE / 3600)) h or more)"
        else
          note_state "$id" running "worker started"
        fi
      done ;;
    READOPTED)
      id=$(jq -r .task <<<"$result")
      SEEN[$id]=''
      say "$id: the retry made no change; re-verifying the first attempt's commit" ;;
    RESCOPED)
      id=$(jq -r .task <<<"$result")
      SEEN[$id]='' ;;
    WAITING)
      waiting=$(jq -r '[(.waiting // [])[]? | "\(.id // .task): \(.reason)"] | (.[:4] | join("; ")) + (if length > 4 then " (+\(length - 4) more; see --status)" else "" end)' <<<"$result" 2>/dev/null)
      [[ $waiting != "$LAST_WAITING" && -n $waiting ]] && say "Waiting: $waiting"
      LAST_WAITING=$waiting ;;
    IDLE)
      # IDLE only means no worker is running: tasks may still be waiting on something.
      blocked=$(jq -r '[(.waiting // [])[]? | "\(.id // .task): \(.reason)"] | (.[:4] | join("; ")) + (if length > 4 then " (+\(length - 4) more; see --status)" else "" end)' <<<"$result" 2>/dev/null)
      if [[ -z $blocked ]]; then
        # Tasks that are not runnable contracts yet (dependencies, human input) still count.
        blocked=$(status_json | jq -r '[.tasks[]? | select(.state == "waiting") | "\(.task): \(.reason // "waiting")"]
          | if length == 0 then "" else (.[:4] | join("; ")) + (if length > 4 then " (+\(length - 4) more; see --status)" else "" end) end' 2>/dev/null)
      fi
      if [[ -n $blocked ]]; then
        outcome=BLOCKED
        [[ $blocked != "$LAST_WAITING" ]] && say "No task can start now: $blocked"
        LAST_WAITING=$blocked
      fi ;;
    DRAINING|PAUSED) ;;
    BUSY)
      reason=$(jq -r '.reason // "busy"' <<<"$result")
      case $MODE in
        once|until-empty) finish 4 "Repository busy: $reason" ;;
      esac
      say "Repository busy ($reason); checking again in ${INTERVAL}s"
      RUNNER_BLOCKER="repository busy: $reason"
      health_update
      pause "$INTERVAL"
      continue ;;
    PRIORITY_DRIFT)
      # Scheduled runs record the human order themselves (Autowork SKILL.md), once per change.
      reconcile_priority && continue
      case $MODE in
        once|until-empty) finish 4 "TODO.md priority changed and could not be recorded: $DRIFT_REASON" ;;
      esac
      [[ $LAST_WAITING == "drift:$DRIFT_REASON" ]] ||
        say "TODO.md priority changed and could not be recorded ($DRIFT_REASON); checking again in ${INTERVAL}s"
      LAST_WAITING="drift:$DRIFT_REASON"
      RUNNER_BLOCKER="TODO.md priority changed and goals.py reorder refused: $DRIFT_REASON"
      health_update
      pause "$INTERVAL"
      continue ;;
    *)
      reason=$(jq -r '.reason // .outcome' <<<"$result" 2>/dev/null || echo "$result")
      [[ $MODE == continuous ]] || finish 4 "The engine needs attention: $reason"
      # A service that exits here stops silently (deliberate exits are not restarted):
      # report it once, keep it visible in health, and look again next interval.
      [[ $LAST_WAITING == "engine:$reason" ]] || say "The engine needs attention: $reason; checking again in ${INTERVAL}s"
      LAST_WAITING="engine:$reason"
      RUNNER_BLOCKER="the engine needs attention: $reason"
      health_update
      pause "$INTERVAL"
      continue ;;
  esac
  settle
  handle_requests
  health_update
  ((SETTLED)) && continue  # closing work can make dependents runnable: dispatch again first
  active=$(status_json | jq '[.tasks[]? | select(.state as $s | ["dispatched","running","reported","integrating","integrated"] | index($s))] | length' 2>/dev/null || echo 0)
  if ((active > 0)); then
    owned --parallel "$WORKERS" --max-workers 8 --wait --timeout 5 >/dev/null  # short: a stop is handled between waits
    continue
  fi
  if [[ $outcome == WAITING || $outcome == BLOCKED || $outcome == PAUSED ]]; then
    # Tasks remain, but none can start now (held work, dependencies or the resource gate).
    [[ $MODE != continuous ]] && finish 1 "No runnable task can start: ${LAST_WAITING:-see --status}"
    pause "$INTERVAL"
    continue
  fi
  # Nothing running, nothing to integrate and nothing waiting: the session ends here.
  if ((DRAINING)) || [[ $MODE != continuous ]]; then
    if [[ $MODE == once && -z $ONCE_TASK && $outcome == IDLE ]]; then finish 0 "Queue empty"; fi
    [[ $outcome == IDLE && $MODE == until-empty ]] && finish 0 "Queue empty"
    if [[ $MODE == once ]]; then
      ((ONCE_DONE)) && finish 0 "Done (--once): $ONCE_TASK"
      finish 1 "Done (--once): $ONCE_TASK did not finish; see --status"
    fi
    ((DRAINING)) && finish "$( ((FAILURES >= MAX_FAILURES)) && echo 1 || echo 0)" "Finished."
  fi
  if [[ $outcome == IDLE ]]; then
    merge_main
    if [[ -z $MERGE_PENDING ]]; then
      owned --parallel "$WORKERS" --max-workers 8 --release >/dev/null
      end_session
    fi
    say "Queue empty; checking again in ${INTERVAL}s"
    pause "$INTERVAL"
  fi
done
