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
was copied into a repository), which must have its main branch checked out.
Needs TODO.md, and goals.json for continuous runs.

Each session builds on an integration branch (pi-autowork/<session>) in its own
worktree; each task runs in a fresh worktree branched from it. Finished tasks join
the integration branch, and when the queue empties or the runner stops, the session
is merged into main. Nothing is pushed.

Options:
  --once               Run at most one task, then exit
  --until-empty        Exit when no runnable task remains
  --dry-run            Show what would run; change nothing
  --repo PATH          Use the repository at PATH
  --interval SECONDS   Idle polling interval (default 60)
  --max-cycles N       Stop after N Pi runs
  --no-fallback        Never switch to the fallback model
  --allow-hermes       Run although a Hermes Autowork cron job targets this repository
  --install-service    Install and start a systemd user service running this for the repository
  --remove-service     Stop and remove the repository's service
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

MODE=continuous DRY_RUN=0 REPO_ARG='' INTERVAL=60 MAX_CYCLES=0 FALLBACK_ENABLED=1 SERVICE=''
while (($#)); do
  case $1 in
    --once) MODE=once ;;
    --until-empty) MODE='until-empty' ;;
    --dry-run) DRY_RUN=1 ;;
    --repo) REPO_ARG=${2:?--repo needs a path}; shift ;;
    --interval) INTERVAL=${2:?--interval needs seconds}; shift ;;
    --max-cycles) MAX_CYCLES=${2:?--max-cycles needs a number}; shift ;;
    --no-fallback) FALLBACK_ENABLED=0 ;;
    --allow-hermes) export PI_AUTOWORK_ALLOW_HERMES=1 ;;
    --install-service) SERVICE=install ;;
    --remove-service) SERVICE=remove ;;
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
BASE=$(git -C "$REPO" symbolic-ref --short -q HEAD) || die 2 "$REPO has a detached HEAD; check out its main branch first."
DEFAULT=$(git -C "$REPO" symbolic-ref --short -q refs/remotes/origin/HEAD 2>/dev/null)
DEFAULT=${DEFAULT#origin/}
if [[ $BASE != "${DEFAULT:-main}" && $BASE != main && $BASE != master ]]; then
  die 2 "$REPO is on branch $BASE. Run the runner from the checkout of the main branch${DEFAULT:+ ($DEFAULT)}; task work happens in worktrees and is merged back there."
fi
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
  installed_toolset | grep -qxF -- "$TOOLSET" || SKILL_ARGS=(--skill "$TOOLSET/adapters/skills/autowork" --skill "$TOOLSET/adapters/skills/git-commit-push")
elif TOOLSET=$(installed_toolset); then
  :
elif TOOLSET=$(cd "$(dirname "$SCRIPT")/.." && pwd) && is_toolset "$TOOLSET"; then
  SKILL_ARGS=(--skill "$TOOLSET/adapters/skills/autowork" --skill "$TOOLSET/adapters/skills/git-commit-push")
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

# --- Service ------------------------------------------------------------------
# One systemd user template serves every repository: pi-autowork@<escaped path>.service.
# SIGINT is the runner's Ctrl+C: the current Pi run ends, finished work merges, and the
# next start resumes. Deliberate exits (1, 3, 4) do not restart; crashes and kills do.
if [[ -n $SERVICE ]]; then
  ((DRY_RUN)) && die 2 "--dry-run cannot be combined with --install-service or --remove-service"
  SYSTEMCTL=${PI_AUTOWORK_SYSTEMCTL:-systemctl}
  UNIT_DIR=${PI_AUTOWORK_UNIT_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user}
  ENV_DIR=${PI_AUTOWORK_ENV_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/pi-autowork}
  INSTANCE=$(systemd-escape --path "$REPO") || die 2 "systemd-escape is not available"
  UNIT="pi-autowork@$INSTANCE.service"
  if [[ $SERVICE == remove ]]; then
    "$SYSTEMCTL" --user disable --now "$UNIT" || die 1 "Could not stop $UNIT"
    rm -f "$ENV_DIR/$INSTANCE.env"
    echo "Removed $UNIT. Its state, kept worktrees and any unmerged session stay in ${PI_AUTOWORK_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/pi-autowork}."
    exit 0
  fi
  [[ -n $HERMES_JOBS && ${PI_AUTOWORK_ALLOW_HERMES:-0} != 1 ]] &&
    die 4 "$(printf 'A Hermes Autowork cron job already works on this repository:\n%s\nPause it, or install with --allow-hermes.' "$HERMES_JOBS")"
  mkdir -p "$UNIT_DIR" "$ENV_DIR" || die 2 "Cannot create $UNIT_DIR or $ENV_DIR"
  cat >"$UNIT_DIR/pi-autowork@.service.tmp" <<UNIT
[Unit]
Description=pi-autowork for %I
Documentation=https://github.com/TrebuchetDynamics/hermes-toolset/blob/main/docs/cross-host.md#run-autowork-continuously
After=network-online.target

[Service]
WorkingDirectory=%I
EnvironmentFile=-$ENV_DIR/%i.env
ExecStart=/bin/bash $SCRIPT
KillMode=mixed
KillSignal=SIGINT
TimeoutStopSec=120
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
    printf 'PATH=%s\n' "$PATH"
    [[ ${PI_AUTOWORK_ALLOW_HERMES:-0} == 1 ]] && echo 'PI_AUTOWORK_ALLOW_HERMES=1'
    for name in PI_AUTOWORK_PRIMARY PI_AUTOWORK_FALLBACK PI_AUTOWORK_TASK_TIMEOUT PI_AUTOWORK_MAX_RETRIES \
                PI_AUTOWORK_MAX_FAILURES PI_AUTOWORK_COOLDOWN PI_AUTOWORK_BACKOFF PI_AUTOWORK_MAX_RUNTIME \
                PI_AUTOWORK_MAX_COST PI_AUTOWORK_STATE_DIR PI_AUTOWORK_TOOLSET; do
      [[ -n ${!name:-} ]] && printf '%s=%s\n' "$name" "${!name}"
    done
  } >"$ENV_DIR/$INSTANCE.env"
  "$SYSTEMCTL" --user daemon-reload || die 1 "systemctl --user daemon-reload failed"
  "$SYSTEMCTL" --user enable "$UNIT" >/dev/null 2>&1 || die 1 "Could not enable $UNIT"
  "$SYSTEMCTL" --user restart "$UNIT" || die 1 "Could not start $UNIT"
  echo "Installed and started $UNIT for $REPO (merges into $BASE)."
  echo "Runs: $SCRIPT"
  echo "Logs: journalctl --user -u '$UNIT' -f"
  echo "Stop: systemctl --user stop '$UNIT' (finishes the current step and merges); remove: $0 --remove-service --repo $REPO"
  linger=$(loginctl show-user "$USER" -p Linger --value 2>/dev/null)
  [[ $linger == yes ]] || echo "Note: user lingering is off, so the service stops at logout; enable it with: loginctl enable-linger $USER"
  exit 0
fi

# --- State --------------------------------------------------------------------
STATE_ROOT=${PI_AUTOWORK_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/pi-autowork}
REPO_KEY=$(printf '%s' "$GIT_COMMON" | sha256sum | cut -c1-16)
STATE_PATH=$STATE_ROOT/$REPO_KEY
WT_ROOT=$STATE_PATH/worktrees

dirty() { git -C "$1" status --porcelain=v1 --untracked-files=all 2>/dev/null; }
git_busy() {  # an unfinished merge, rebase or similar in the checkout at $1
  local marker path
  for marker in MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD rebase-merge rebase-apply; do
    path=$(git -C "$1" rev-parse --path-format=absolute --git-path "$marker" 2>/dev/null) || continue
    [[ -e $path ]] && { printf '%s' "$marker"; return 0; }
  done
  return 1
}
task_status() { jq -r --arg id "$2" 'first(.tasks[]? | select(.id == $id) | .status) // "missing"' "$1/goals.json" 2>/dev/null; }
ledger_revision() { python3 "$GOALS" revision "$1" 2>/dev/null; }
# Prints the eligible queue as JSON; returns 0 ok, 3 priority drift, other invalid.
queue() { python3 "$GOALS" next "$1" --json 2>/dev/null; }
safe_name() { printf '%s' "$1" | tr -c 'A-Za-z0-9._-' '-'; }

summarize() {
  local primary_auth fallback_auth
  primary_auth=$(auth_ready "$PRIMARY" && echo ready || echo 'not ready')
  echo "PI AUTOWORK"
  echo "Repository: $REPO (merges into $BASE)"
  if ((${#SKILL_ARGS[@]})); then
    echo "Toolset:    $TOOLSET at $TOOLSET_REV (not a Pi package; skills loaded with --skill)"
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
  echo "Mode:       $MODE; state and worktrees in $STATE_PATH"
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
  if [[ -f $STATE_PATH/session.json ]]; then
    echo "Session:    $(jq -r .branch "$STATE_PATH/session.json") continues (not yet merged into $BASE)"
    source_dir=$(jq -r .path "$STATE_PATH/session.json")
  else
    echo "Session:    a new integration branch would start from $BASE"
    source_dir=$REPO
  fi
  for kept in "$WT_ROOT"/task-*; do
    [[ -d $kept ]] && echo "Kept:       $kept (unfinished task work)"
  done
  changes=$(dirty "$REPO")
  [[ -n $changes ]] && echo "Note:       $REPO has uncommitted changes; the final merge stops if it would touch them"
  if ((HAS_LEDGER)); then
    list=$(queue "$source_dir"); rc=$?
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

mkdir -p "$STATE_PATH/sessions" "$STATE_PATH/runs" "$WT_ROOT" || die 2 "Cannot create state directory $STATE_PATH"
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
    # Helpers never inherit the lock (fd 9): a lingering timer must not block the next runner.
    (sleep 30; kill -TERM -- "-$CHILD" 2>/dev/null; sleep 10; kill -KILL -- "-$CHILD" 2>/dev/null) </dev/null >/dev/null 2>&1 9>&- &
    KILLER=$!
  fi
}
stop_helpers() {  # background timers must not outlive the runner or hold its output open
  local pid
  for pid in "$KILLER" "$SLEEPER"; do
    [[ -n $pid ]] || continue
    kill -STOP "$pid" 2>/dev/null  # freeze it so it cannot start another child
    pkill -P "$pid" 2>/dev/null
    kill "$pid" 2>/dev/null
    kill -CONT "$pid" 2>/dev/null
  done
  KILLER='' SLEEPER=''
}
trap on_signal INT TERM
trap 'stop_helpers; rm -f "$STATE/runner.json"' EXIT

pause() {  # interruptible sleep
  sleep "$1" >/dev/null 2>&1 9>&- &
  SLEEPER=$!
  wait "$SLEEPER" 2>/dev/null
  stop_helpers
}

# --- Worktrees ----------------------------------------------------------------
# The session's integration branch lives in its own worktree; the queue is read there.
INTEG='' INTEG_BRANCH='' MERGE_PENDING='' RESOLVED_ONCE=0
load_session() {
  [[ -f $STATE/session.json ]] || return 1
  INTEG_BRANCH=$(jq -r .branch "$STATE/session.json") INTEG=$(jq -r .path "$STATE/session.json")
  git -C "$REPO" show-ref --verify -q "refs/heads/$INTEG_BRANCH" || { rm -f "$STATE/session.json"; INTEG='' INTEG_BRANCH=''; return 1; }
  if [[ ! -d $INTEG ]]; then
    git -C "$REPO" worktree prune
    git -C "$REPO" worktree add -q "$INTEG" "$INTEG_BRANCH" || die 1 "Cannot restore the integration worktree for $INTEG_BRANCH"
  fi
}
ensure_session() {
  [[ -n $INTEG ]] && return 0
  load_session && return 0
  INTEG_BRANCH="pi-autowork/$(date +%Y%m%d-%H%M%S)" INTEG=$WT_ROOT/integration
  git -C "$REPO" worktree prune
  [[ -e $INTEG ]] && die 1 "$INTEG exists but belongs to no session; remove it after checking its contents."
  git -C "$REPO" worktree add -q -b "$INTEG_BRANCH" "$INTEG" "$BASE" || die 1 "Cannot create the integration worktree"
  jq -n --arg branch "$INTEG_BRANCH" --arg path "$INTEG" --arg base "$BASE" --arg started "$(date -Iseconds)" \
    '{branch: $branch, path: $path, base: $base, started: $started}' >"$STATE/session.json"
  say "Session $INTEG_BRANCH started from $BASE"
}
end_session() {
  git -C "$REPO" worktree remove "$INTEG" 2>/dev/null || git -C "$REPO" worktree remove --force "$INTEG"
  git -C "$REPO" branch -q -D "$INTEG_BRANCH" 2>/dev/null
  rm -f "$STATE/session.json"
  INTEG='' INTEG_BRANCH='' RESOLVED_ONCE=0
}
# Sets TASK_WT and TASK_BRANCH, creating the task worktree from the integration tip if needed.
task_worktree() {
  local name
  name=$(safe_name "${1:-next}")
  TASK_WT=$WT_ROOT/task-$name TASK_BRANCH="pi-autowork-task/${INTEG_BRANCH#pi-autowork/}/$name"
  if [[ -d $TASK_WT ]]; then
    TASK_BRANCH=$(git -C "$TASK_WT" symbolic-ref --short -q HEAD) || TASK_BRANCH=''
    return 0
  fi
  git -C "$REPO" worktree prune
  git -C "$REPO" branch -q -D "$TASK_BRANCH" 2>/dev/null
  git -C "$REPO" worktree add -q -b "$TASK_BRANCH" "$TASK_WT" "$INTEG_BRANCH" || die 1 "Cannot create worktree $TASK_WT"
}
# Brings a task branch's commits onto the integration branch; 1 when it cannot.
absorb() {
  [[ -n $TASK_BRANCH ]] || return 1
  [[ -z $(git -C "$REPO" rev-list "$INTEG_BRANCH..$TASK_BRANCH") ]] && return 0
  git -C "$INTEG" merge -q --ff-only "$TASK_BRANCH" 2>/dev/null && return 0
  if git -C "$INTEG" merge -q --no-edit "$TASK_BRANCH" >/dev/null 2>&1; then
    return 0
  fi
  git -C "$INTEG" merge --abort 2>/dev/null
  return 1
}
drop_task_worktree() {  # removes a clean task worktree whose work is on the integration branch
  [[ -z $(dirty "$TASK_WT") ]] || return 1
  if [[ -n $TASK_BRANCH && -n $(git -C "$REPO" rev-list "$INTEG_BRANCH..$TASK_BRANCH" 2>/dev/null) ]]; then
    return 1
  fi
  git -C "$REPO" worktree remove "$TASK_WT" && { [[ -n $TASK_BRANCH ]] && git -C "$REPO" branch -q -D "$TASK_BRANCH"; }
  return 0
}

# --- One Pi run ---------------------------------------------------------------
# Runs Pi in directory $1 with prompt $2; sets RUN_* globals describing what Pi reported.
run_pi() {
  local dir=$1 prompt=$2 session=$3 target=$4 raw err rc analysis
  raw=$STATE/runs/current.jsonl err=$STATE/runs/current.err
  RUN_START=$SECONDS
  (cd "$dir" && exec setsid timeout -s INT -k 120 "$TASK_TIMEOUT" \
    "$PI" --mode json --provider "$(provider_of "$target")" --model "$(model_of "$target")" \
    --session-dir "$STATE/sessions" --session-id "$session" --no-approve "${SKILL_ARGS[@]}" -- "$prompt") \
    </dev/null >"$raw" 2>"$err" &  # Pi keeps the lock (fd 9) while it runs
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
       tokens: ($msgs | map(.usage.totalTokens // 0) | add // 0),
       cost: ($msgs | map(.usage.cost.total // 0) | add // 0),
       result: ([$last.content[]? | select(.type == "text") | .text] | join("\n")
                | [splits("\n")] | map(select(startswith("PI_AUTOWORK_RESULT:"))) | last // null)}' "$raw")
  [[ -n $analysis ]] || analysis='{"settled":false,"aborted":false,"stop":null,"error":null,"retries":0,"tokens":0,"cost":0,"result":null}'
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
  SPENT=$(awk -v a="$SPENT" -v b="$RUN_COST" 'BEGIN { printf "%.4f", a + b }')
  # Keep only the compact record; the raw stream holds prompts, code and tool output.
  rm -f "$raw"
}

task_prompt() {  # task title worktree branch resume
  local prompt
  if [[ -n $1 ]]; then
    prompt="/skill:autowork Execute exactly task $1 ($2) in $3. Do not select, start or record any other task and do not look for new work. Complete this task: implement it, run its checks, commit locally, then mark it done and archive it as the skill describes."
  else
    prompt="/skill:autowork Complete the next ready task in $3's TODO.md, exactly one. Do not look for or record new work: if no task is ready, change nothing and say so. Commit locally."
  fi
  prompt+=" This directory is a task worktree on branch $4; commit here only. Do not merge, rebase, switch branches, create other worktrees or touch $REPO: the runner merges finished work into $BASE. Do not push, deploy or publish. If the task cannot be completed in this run (it needs live access, a decision or another blocker), record the precise blocker in its TODO.md body, commit that, keep its status and stop."
  (($5)) && prompt+=" A previous run of this task was interrupted: first reconcile its partial work in the working tree and the latest commits, then continue."
  printf '%s End with one line: PI_AUTOWORK_RESULT: completed|partial|blocked, then one sentence.' "$prompt"
}

is_provider_failure() {
  [[ $RUN_STOP == error ]] && return 0
  [[ $RUN_SETTLED != true ]] && grep -qiE '429|rate.?limit|quota|usage limit|overloaded|5[0-9]{2}|unavailable|timed? ?out|ECONN|ENOTFOUND|EAI_AGAIN|network|fetch failed|401|403|unauthori[sz]ed|forbidden|credential|api key|not logged in|/login|oauth|expired|no such model|model .*not (found|available)' <<<"$RUN_ERROR"
}

record() {  # outcome task model fallback_reason start_sha [worktree]
  local commits
  commits=$(git -C "${6:-$TASK_WT}" rev-list --reverse "$5..HEAD" 2>/dev/null | cut -c1-12 | paste -sd, -)
  jq -cn --arg time "$(date -Iseconds)" --arg outcome "$1" --arg task "$2" --arg model "$3" \
    --arg fallback "$4" --arg commits "$commits" --arg error "$RUN_ERROR" --arg result "$RUN_RESULT" \
    --arg branch "$TASK_BRANCH" --arg session "$INTEG_BRANCH" \
    --argjson seconds "$RUN_SECONDS" --argjson tokens "$RUN_TOKENS" --argjson cost "$RUN_COST" \
    --argjson retries "$RUN_RETRIES" --argjson attempt "${RETRIES[$2]:-0}" \
    '{time: $time, task: $task, outcome: $outcome, provider: ($model | split("/")[0]),
      model: ($model | split("/")[1:] | join("/")), seconds: $seconds, session: $session, branch: $branch,
      commits: ($commits | split(",") | map(select(. != ""))),
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

# --- Merge into the main branch -----------------------------------------------
# Merges the session into $BASE: first $BASE into the integration branch (Pi resolves
# conflicts once per session), then a fast-forward of $BASE in the main checkout.
integrate() {
  local ahead files out current
  MERGE_PENDING=''
  [[ -n $INTEG ]] || load_session || return 0
  ahead=$(git -C "$REPO" rev-list --count "$BASE..$INTEG_BRANCH")
  if ((ahead == 0)); then
    end_session
    return 0
  fi
  if ! git -C "$INTEG" merge -q --no-edit "$BASE" >/dev/null 2>&1; then
    files=$(git -C "$INTEG" diff --name-only --diff-filter=U | paste -sd' ' -)
    if ((!STOP && !RESOLVED_ONCE)) && choose_model; then
      RESOLVED_ONCE=1
      say "$BASE moved and conflicts with this session in: $files; asking Pi to resolve the merge"
      run_pi "$INTEG" "/skill:git-commit-push This worktree is on branch $INTEG_BRANCH with an unfinished merge of $BASE that conflicts in: $files. Resolve every conflict keeping both sides' work: keep both task entries in TODO.md and TODO.archive.md, keep every task record in goals.json and run python3 $GOALS validate . to confirm the ledger, then run the checks that cover the conflicted files and conclude the merge with a commit. Do not push, rebase, switch branches or touch $REPO. End with one line: PI_AUTOWORK_RESULT: completed|blocked, then one sentence." \
        "pi-autowork-merge-$(date +%Y%m%d%H%M%S)" "$CHOSEN"
      record merge_resolution "${INTEG_BRANCH#pi-autowork/}" "$CHOSEN" '' "$BASE" "$INTEG"
    fi
    if git_busy "$INTEG" >/dev/null || ! git -C "$REPO" merge-base --is-ancestor "$BASE" "$INTEG_BRANCH" \
        || [[ -n $(dirty "$INTEG") ]]; then
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
  end_session
}

# --- Main loop ----------------------------------------------------------------
summarize
say "Started (PID $$). Stop with Ctrl+C."
INFLIGHT=$STATE/inflight.json
LAST_REVISION='' TASK_WT='' TASK_BRANCH=''

finish() {
  local code=$1
  integrate
  if [[ -n $MERGE_PENDING && $code == 0 ]]; then code=4; fi
  for kept in "$WT_ROOT"/task-*; do
    [[ -d $kept ]] && say "Kept for review: $kept"
  done
  say "$2"
  exit "$code"
}
fail_count() {
  FAILURES=$((FAILURES + 1))
  ((FAILURES >= MAX_FAILURES)) && finish 1 "Stopping after $FAILURES consecutive failed runs; see $STATE/runs.jsonl"
}
idle() {
  case $MODE in
    once|until-empty) finish "$2" "$1" ;;
  esac
  integrate
  say "$1; checking again in ${INTERVAL}s"
  pause "$INTERVAL"
}
keep_or_drop() {  # after a task stops without finishing: keep unfinished work for review
  if drop_task_worktree; then
    return 0
  fi
  say "$key: unfinished work kept in $TASK_WT for review; continuing with other tasks"
  return 1
}

if [[ -f $INFLIGHT ]] && ! jq -e .worktree "$INFLIGHT" >/dev/null 2>&1; then
  say "Discarding an in-flight record from an older runner version"
  rm -f "$INFLIGHT"
fi

while :; do
  ((STOP)) && finish 130 "Stopped."
  ((MAX_CYCLES && CYCLES >= MAX_CYCLES)) && finish 0 "Reached --max-cycles $MAX_CYCLES."
  ((MAX_RUNTIME && SECONDS - STARTED >= MAX_RUNTIME)) && finish 0 "Reached PI_AUTOWORK_MAX_RUNTIME."
  if [[ $MAX_COST != 0 ]] && awk -v s="$SPENT" -v m="$MAX_COST" 'BEGIN { exit !(s >= m) }'; then
    finish 0 "Reached PI_AUTOWORK_MAX_COST (\$$SPENT reported)."
  fi
  ensure_session

  resume=0 task='' title=''
  if [[ -f $INFLIGHT ]]; then
    task=$(jq -r .task "$INFLIGHT") title=$(jq -r .title "$INFLIGHT") resume=1
    TASK_WT=$(jq -r .worktree "$INFLIGHT") TASK_BRANCH=$(jq -r .branch "$INFLIGHT")
    if [[ ! -d $TASK_WT ]]; then
      say "The worktree of interrupted task $task is gone; starting it again"
      rm -f "$INFLIGHT"
      continue
    fi
    if ((HAS_LEDGER)) && [[ -n $task && $(task_status "$TASK_WT" "$task") == 'done' && -z $(dirty "$TASK_WT") ]]; then
      say "$task was already completed before the interruption; not running it again"
      absorb || say "Could not bring $task onto $INTEG_BRANCH; its branch $TASK_BRANCH is kept"
      drop_task_worktree
      rm -f "$INFLIGHT"
      continue
    fi
    say "Resuming interrupted task ${task:-'(next ready)'} in $TASK_WT"
  elif ((HAS_LEDGER)); then
    revision=$(ledger_revision "$INTEG")
    if [[ $revision != "$LAST_REVISION" ]]; then
      SKIPPED=()  # TODO.md or goals.json changed: give skipped tasks another chance
      LAST_REVISION=$revision
    fi
    list=$(queue "$INTEG"); rc=$?
    if ((rc == 3)); then
      idle "TODO.md priority changed since it was recorded; run goals.py reorder (see Autowork)" 4
      continue
    elif ((rc != 0)); then
      finish 4 "goals.py could not read the ledger on $INTEG_BRANCH; run goals.py validate in $INTEG."
    fi
    pick=$(jq -c --argjson skipped "$(printf '%s\n' "${!SKIPPED[@]}" | jq -R . | jq -s .)" \
      'map(.task) | map(select(.id as $id | $skipped | index($id) | not)) | first // empty' <<<"$list")
    if [[ -z $pick ]]; then
      if (($(jq length <<<"$list"))); then
        idle "No task this runner can make progress on (${!SKIPPED[*]} skipped)" 1
      else
        idle "Queue empty" 0
      fi
      continue
    fi
    task=$(jq -r .id <<<"$pick") title=$(jq -r .title <<<"$pick")
    say "Queue: $(jq length <<<"$list") runnable task(s). Selected: $task — $title"
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
    task_worktree "$task"
    [[ -n $(dirty "$TASK_WT") ]] && resume=1  # earlier unfinished work kept in this worktree
    session="pi-autowork-$(safe_name "$key")-$(date +%Y%m%d%H%M%S)"
    start_sha=$(git -C "$TASK_WT" rev-parse HEAD)
  fi
  jq -n --arg task "$task" --arg title "$title" --arg session "$session" --arg start_sha "$start_sha" \
    --arg model "$CHOSEN" --arg worktree "$TASK_WT" --arg branch "$TASK_BRANCH" --arg started "$(date -Iseconds)" \
    '{task: $task, title: $title, session: $session, start_sha: $start_sha, model: $model,
      worktree: $worktree, branch: $branch, started: $started}' >"$INFLIGHT"
  CYCLES=$((CYCLES + 1))
  say "Starting Pi with $(label "$CHOSEN") in $TASK_WT"
  run_pi "$TASK_WT" "$(task_prompt "$task" "$title" "$TASK_WT" "$TASK_BRANCH" "$resume")" "$session" "$CHOSEN"

  status=''
  ((HAS_LEDGER)) && [[ -n $task ]] && status=$(task_status "$TASK_WT" "$task")
  new_commits=$(git -C "$TASK_WT" rev-list --count "$start_sha..HEAD" 2>/dev/null || echo 0)
  [[ -n $RUN_RESULT ]] && say "Pi: $RUN_RESULT"

  if ((STOP)); then
    record interrupted "$key" "$CHOSEN" "$FALLBACK_REASON" "$start_sha"
    finish 130 "Stopped during $key; its work stays in $TASK_WT and the next start resumes it."
  fi
  if [[ $status == 'done' ]]; then
    record completed "$key" "$CHOSEN" "$FALLBACK_REASON" "$start_sha"
    rm -f "$INFLIGHT"; unset 'RETRIES[$key]'; FAILURES=0
    say "$key completed with $(label "$CHOSEN") in $((RUN_SECONDS / 60)) min; commits: $(git -C "$TASK_WT" rev-list --reverse "$start_sha..HEAD" | cut -c1-7 | paste -sd' ' -)"
    if absorb; then
      drop_task_worktree || say "$key left uncommitted changes in $TASK_WT; kept for review"
    else
      SKIPPED[$key]=1
      say "Could not bring $key onto $INTEG_BRANCH; its branch $TASK_BRANCH and worktree are kept"
    fi
    [[ $MODE == once ]] && finish 0 "Done (--once)."
    continue
  fi

  if ((RUN_RC == 124)); then
    record timeout "$key" "$CHOSEN" "$FALLBACK_REASON" "$start_sha"
    say "$key exceeded PI_AUTOWORK_TASK_TIMEOUT (${TASK_TIMEOUT}s)"
    SKIPPED[$key]=1
    rm -f "$INFLIGHT"
    absorb || true
    keep_or_drop
    fail_count
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
      rm -f "$INFLIGHT"
      keep_or_drop
      fail_count
      [[ $MODE == once ]] && finish 1 "Done (--once); $key did not finish."
      continue
    fi
    if [[ $kind == provider && $CHOSEN == "$PRIMARY" ]] && ((FALLBACK_ENABLED)); then
      cool_primary "${RUN_ERROR:-provider failure}"
      say "Switching to $(label "$FALLBACK") for up to $((COOLDOWN / 60)) min; it resumes this task in $TASK_WT"
    else
      delay=$((BACKOFF * (1 << (attempt - 1)))); ((delay > 600)) && delay=600
      say "Retrying $key in ${delay}s (attempt $attempt of $MAX_RETRIES)"
      pause "$delay"
    fi
    continue  # the in-flight record makes the next run resume this task
  fi

  # Pi finished normally without closing the task.
  rm -f "$INFLIGHT"
  if ((!HAS_LEDGER)); then
    outcome=no_ready_task
    ((new_commits > 0)) && outcome=committed_unverified
    record "$outcome" "$key" "$CHOSEN" "$FALLBACK_REASON" "$start_sha"
    absorb || say "Could not bring the commits onto $INTEG_BRANCH; branch $TASK_BRANCH is kept"
    keep_or_drop
    ((new_commits > 0)) && finish 0 "Autowork made $new_commits commit(s); without goals.json the runner cannot confirm the task is done."
    finish 0 "Autowork made no commit (no ready task, or it stopped on a blocker)."
  fi
  if ((new_commits > 0)); then
    record partial "$key" "$CHOSEN" "$FALLBACK_REASON" "$start_sha"
    say "$key made progress ($new_commits commit(s)) but is not done yet"
    FAILURES=0
    absorb || { SKIPPED[$key]=1; say "Could not bring $key's progress onto $INTEG_BRANCH; branch $TASK_BRANCH is kept"; }
  else
    record no_progress "$key" "$CHOSEN" "$FALLBACK_REASON" "$start_sha"
    say "$key: no commit and still ${status:-open}; skipping it until TODO.md or goals.json changes"
    SKIPPED[$key]=1
    fail_count
  fi
  keep_or_drop
  if [[ $MODE == once ]]; then
    ((new_commits > 0)) && finish 0 "Done (--once); $key is not finished yet."
    finish 1 "Done (--once); $key made no progress."
  fi
done
