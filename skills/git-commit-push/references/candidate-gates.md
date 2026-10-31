# Candidate gate playbooks

Disclosed reference for step 4 of [Git Commit Push](../SKILL.md). Load it when the gate
you must run matches one of these branches. The step keeps the order — stage, gate,
push — and these branches keep the failure modes it meets.

- If that check flags CSV record-ending carriage returns, inspect raw bytes before
  changing content. For valid CRLF records, use the command-local check
  `git -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --cached --check`
  while retaining CSV parsing and content/hash checks. Preserve the ordinary
  whitespace checks and source bytes: CSV writers commonly emit CRLF, and
  normalizing preserved research artifacts can invalidate evidence fingerprints.

- Scope `GIT_DIR`, `GIT_WORK_TREE` and `GIT_INDEX_FILE` to individual Git/index-aware
  probes, not the entire gate environment. Never persist snapshot routing with
  `git config core.worktree`: it redirects other sessions' status, staging and
  commits even after the gate exits. Use `git -c core.worktree=<snapshot> ...`
  only for the individual guard that needs it. Build tools can invoke Git inside
  their own SDK checkout; inherited candidate overrides make those probes read
  the wrong repository and can corrupt SDK version detection. In Python, keep a separate
  `git_env` for index/export checks and strip these three keys from the environment
  passed to Flutter, npm and other build commands. For a Git-backed guard in a
  filesystem export, pass the candidate overrides only to that guard so its
  `git ls-files` sees the curated index rather than an empty parent-repo pathspec.
  Authority validators that discard `GIT_*` are different: never fabricate `.git`
  metadata for them; follow [canonical-authority validation](shared-worktree-safety.md#canonical-authority-validation-for-filesystem-exports).

- **Satisfy the snapshot's dependency inputs before gating it.** A snapshot made with
  `git worktree add` or `checkout-index` contains tracked files only: no installed module tree,
  no untracked runtime config. The gate then dies on its first check with a missing tool
  (`local <x> not found`) or the app cannot start, which reads as clean bytes failing for no
  visible reason. Reuse the already-installed module set only when the manifest and
  lockfile match. Before linking it, check whether the dev server restricts resolved
  dependency paths: an external symlink can let SSR succeed while client-entry
  requests return 403 and hydration never starts. For that demonstrated boundary,
  make a physical private dependency copy, omit generated dev-server caches,
  preserve internal symlinks and verify none escape the candidate. Keep the
  filesystem security policy unchanged; rerun the original failing browser spec
  before changing application code. Copy required untracked runtime env privately
  (never stage or commit it), and confirm the failure was a prerequisite rather
  than the payload. Record the dependency layout with the gate receipt, because
  matching lockfiles alone do not qualify different filesystem layouts. For Flutter, treat `pubspec.lock` as part of the gated
  candidate: if `flutter pub get` changes it, either include that exact lockfile delta or restore
  the lock first and rerun analysis/tests against the restored dependency graph; never ship a
  lockfile different from the one those checks exercised.

- **Decide whether a snapshot-only failure belongs to the snapshot or to the repository.** A
  guard that passes in the long-lived tree and fails in every clean checkout is resolving against
  untracked artifacts — a citation to generated output, a file only a local tool run creates.
  That is a repository defect: fix the citation to name the *tracked producer* (verify the
  producer from its own usage or argument list, never from its apparent name) or teach the guard
  to skip ignored output. Re-run it with a deliberately dangling reference injected to prove the
  guard still fails, so "it passes now" means the reference is sound and not that the check was
  neutered. Never pre-seed the missing artifact to force green. For generated
  skills/plugins, test the tracked template and exercise the actual generator
  or installer in a hermetic fixture; do not assert that an ignored installed
  payload already exists, because clean candidate exports omit it.

- Reconcile a HEAD advance during gating before committing: compare the saved base
  with fresh HEAD and inspect the intervening commits, real index and owned blobs.
  Preserve the completed gate's immutable export; prepare a new complete export for
  eligible newly committed work rather than treating it as a failed check or blindly
  accepting the new tree. Rerun affected suites and guards; reuse an unaffected suite
  only after checking its source, transitive imports, fixtures, tools and dependencies.
  An unchanged component directory alone is insufficient when it imports changed code.
  When qualification combines fresh affected-suite runs with reused unaffected
  receipts, label that composition rather than calling it one fresh full-suite run.

- Run guards **after** staging. Guards built on `git grep` cannot see untracked files, and a
  new file can turn them red the moment it is tracked.

- If the gate may outlive the terminal timeout, run one tracked background process with
  completion notification and retain its handle, pinned candidate, per-command logs and
  exit results. Do not start another suite merely because a foreground wait expires;
  distinguish a wait-window timeout from an actual process timeout. Inspect once if needed,
  then use the completion notification rather than repeated waits or pending-status messages.
  Start the final publication gate in the integration owner's session; a short-lived child's
  cleanup can kill it before its receipt is written. On an interrupted handoff verify process
  and receipt, keep partial logs as incomplete, and restart only the missing gate on unchanged
  inputs. A staged tree hash is not a commit SHA.
  A running gate is not a pass. Never push while its required checks are still running.

- After an interrupted side-effecting command, inspect `HEAD`, `MERGE_HEAD`, the staged diff,
  relevant refs and process/log/exit receipts before retrying; an interruption does not say
  whether later merge/commit steps ran. Mark missing evidence unverified rather than inferring
  success, and recheck canonical HEAD and owned blobs before landing. A switch to standalone
  planning preserves the delivery checkpoint but does not silently resume the push request.

- Preserve the complete requested delivery obligation across asynchronous handoffs:
  local commit → passing candidate gate → verified remote push → verified PR merge when
  authorized. Record the next action with the existing delivery receipt and resume from
  completion evidence; a local-commit status report does not finish a push-and-merge request.

- **Never waive a gate to ship a change that does nothing at runtime.** A guard's own escape
  hatch — an accepted-drift baseline like `KNOWN_COMMAND_DRIFT`, a `@known-failure` marker —
  exists for deliberate, permanent divergence. Spending it to push a docs-only or otherwise
  inert revision past a red gate leaves a stale waiver that hides the next real divergence.
  Record the owner's decision, leave the deploy queued, and let the blocking fix land first.

- If a push already carried a change whose canonical gate had not run, do not rewrite
  history to hide it: run the gate against the pushed bytes now, report the miss in plain
  words (naming the commit whose message does not describe what it carried), and fix
  forward with a scoped commit if it fails. A pushed message cannot be corrected without a
  force-push, so the honest record is the report plus the after-the-fact result.
