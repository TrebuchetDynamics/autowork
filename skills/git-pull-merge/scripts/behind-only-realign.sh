#!/usr/bin/env bash
# Behind-only realignment of a shared, multi-writer checkout: move the pointer to the source
# commit WITHOUT writing any worktree byte that was not verified clean. See the skill's
# "Behind-only realignment is the bounded exception" bullet for when this is legitimate.
#
#   usage: behind-only-realign.sh [<source-ref>]        # default: @{u}
#   env:   REALIGN_SAFETY_REF     safety branch name (default safety/pre-pull-<date>)
#          REALIGN_EXCLUDE_RE     ERE of paths excluded from the STRICT PROOF only — live
#                                 runtime data that changes by design, e.g. '^svc-agent/(data|logs)/'
#
# Aborts unless: HEAD is an ancestor of the source, nothing is staged, no index.lock.
# Nothing is ever discarded, stashed, rebased or reset --hard.
set -euo pipefail
REPO_ROOT=$(git rev-parse --show-toplevel); cd "$REPO_ROOT"
SRC=${1:-'@{u}'}
NEW=$(git rev-parse --verify "${SRC}^{commit}"); OLD=$(git rev-parse HEAD)
SAFETY_REF=${REALIGN_SAFETY_REF:-safety/pre-pull-$(date +%Y%m%d)}

# --- preconditions the exception requires -----------------------------------
git merge-base --is-ancestor "$OLD" "$NEW" || { echo "ABORT: local-only commits exist (not behind-only)"; exit 1; }
git diff --cached --quiet || { echo "ABORT: index not pristine (a writer is staged)"; exit 1; }
[ -e "$(git rev-parse --git-path index.lock)" ] && { echo "ABORT: index.lock present"; exit 1; } || true

W=$(mktemp -d)
# NUL records and literal pathspecs preserve spaces, newlines and glob characters.
# Include ignored files: they are writer bytes too, not permission to overwrite.
git diff --name-only -z > "$W/modified"
git ls-files --others -z > "$W/untracked"
git ls-files -v -z > "$W/index-flags"
while IFS= read -r -d '' entry; do
    case "${entry:0:1}" in
        S|[a-z]) echo "ABORT: hidden index flags (skip-worktree/assume-unchanged)"; exit 1 ;;
    esac
done < "$W/index-flags"
LC_ALL=C sort -zu "$W/modified" "$W/untracked" > "$W/local"
git diff --no-renames --name-only -z "$OLD" "$NEW" > "$W/incoming"
git ls-tree -rz "$OLD" > "$W/old-tree"
git ls-tree -rz "$NEW" > "$W/new-tree"
declare -A local_paths=() old_modes=() new_modes=()
declare -a asserted=() refresh=() remove=()
while IFS= read -r -d '' p; do
    local_paths["$p"]=1
    if ! printf '%s\n' "$p" | grep -qE "${REALIGN_EXCLUDE_RE:-^\$}"; then
        asserted+=("$p")
    fi
done < "$W/local"
while IFS= read -r -d '' entry; do
    old_modes["${entry#*$'\t'}"]=${entry%% *}
done < "$W/old-tree"
while IFS= read -r -d '' entry; do
    new_modes["${entry#*$'\t'}"]=${entry%% *}
done < "$W/new-tree"

collision() { printf 'ABORT: unsupported collision: %q\n' "$1"; exit 1; }
# Plan everything before creating a safety ref or moving HEAD/index. Directory
# transitions and symlink ancestors are deliberately unsupported, even if clean.
while IFS= read -r -d '' p; do
    for mode in "${old_modes[$p]:-}" "${new_modes[$p]:-}"; do
        case "$mode" in ''|100644|100755|120000) ;; *) collision "$p" ;; esac
    done
    [ ! -d "$p" ] || [ -L "$p" ] || collision "$p"
    parent=$p
    while [[ "$parent" == */* ]]; do
        parent=${parent%/*}
        if [ -L "$parent" ] || { [ -e "$parent" ] && [ ! -d "$parent" ]; } ||
           [[ -n "${old_modes[$parent]:-}" || -n "${new_modes[$parent]:-}" ]]; then
            collision "$parent"
        fi
    done
    # An exact dirty/ignored/untracked collision is supported: leave it alone.
    [[ -z "${local_paths[$p]:-}" ]] || continue
    if [[ -n "${new_modes[$p]:-}" ]]; then
        # Defensive against paths Git could not enumerate (special files, etc.).
        if [[ -z "${old_modes[$p]:-}" ]] && { [ -e "$p" ] || [ -L "$p" ]; }; then
            collision "$p"
        fi
        refresh+=("$p")
    else
        remove+=("$p")
    fi
done < "$W/incoming"

snap() {
    local p hash
    for p in "${asserted[@]}"; do
        if [ -L "$p" ]; then
            hash=$(readlink -z -- "$p" | git hash-object --stdin)
            printf '%s\0SYMLINK:%s\0' "$p" "$hash"
        elif [ -f "$p" ]; then
            hash=$(git hash-object --no-filters -- "$p")
            printf '%s\0FILE:%s\0' "$p" "$hash"
        elif [ ! -e "$p" ]; then
            printf '%s\0ABSENT\0' "$p"
        else
            collision "$p"
        fi
    done
}
snap > "$W/before"
if git show-ref --verify --quiet "refs/heads/$SAFETY_REF"; then
    [ "$(git rev-parse "refs/heads/$SAFETY_REF")" = "$OLD" ] || {
        echo "ABORT: safety ref does not preserve OLD"; exit 1;
    }
else
    git branch --no-track "$SAFETY_REF" "$OLD"
fi
git reset --mixed "$NEW" >/dev/null                        # writes no worktree file
# Deletions no longer exist in the new index; checkout cannot apply them.
for p in "${remove[@]}"; do rm -f -- "$p"; done
if [ "${#refresh[@]}" -gt 0 ]; then
    printf '%s\0' "${refresh[@]}" > "$W/refresh"
    git --literal-pathspecs checkout "$NEW" --pathspec-from-file="$W/refresh" --pathspec-file-nul
fi
snap > "$W/after"
echo "OLD=$OLD"; echo "NEW=$NEW"
echo "ADVANCED_CLEAN_PATHS=$((${#refresh[@]} + ${#remove[@]}))  PRESERVED_ASSERTED=${#asserted[@]}"
echo "HEAD_NOW=$(git rev-parse --short HEAD)  UPSTREAM_NOW=$(git rev-parse --short "$NEW")  SAFETY_REF=$SAFETY_REF"
echo "WORK=$W"
if cmp -s "$W/before" "$W/after"; then
    echo "PROOF=ZERO_CHANGED (every asserted writer file byte-identical)"
else
    echo "PROOF=CHANGED — writer preservation failed"; exit 1
fi
