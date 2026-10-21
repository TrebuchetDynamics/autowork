# Cron self-repair

A scheduled Autowork occurrence repairs attributable Toolset and managed job-wiring
faults within its existing authority. A cron failure is work to diagnose and repair,
not a reason to ask again whether to do already-authorized local work. Preserve the
original task, candidate and execution history. This policy grants
neither product changes to a shared maintainer nor external publication authority.

## Repair the exact saved job

At entry, resolve the current occurrence's profile, existing job ID, canonical
repository and default Hermes home from actual scheduler context/readback. Use the
verified installed Toolset source helper (not a guessed repository-relative script):

```sh
python3 /absolute/toolset/scripts/heal-owner-cron.py \
  --root /absolute/default-hermes-home --profile PROFILE \
  --job-id EXISTING_JOB_ID --repo /absolute/repository --apply
```

Substitute verified values. Without `--apply` this is a read-only preview. Do not
infer identity from an arbitrary error message or select the first similarly named
job. Missing identity holds only this job edit; continue independently authorized
repository work when safe. Explicit no-write instructions prohibit this repair.

The helper uses the native profile-scoped cron edit interface and changes only the
Toolset-managed prompt section and Autowork skill attachment. It preserves the
original scope prefix verbatim; the managed policy supersedes only obsolete
card-only execution/recovery/review prerequisites. It preserves unrelated skills, ID, cadence, model, delivery, workdir,
script/interpreter, limits and other configuration. Research/design, delivery-sync,
audit, script-only and unmanaged jobs require their own policies. It never creates,
runs, resumes or deletes a schedule. Paused jobs are untouched.

The per-job lock and private `autowork/cron-heal/JOB_ID.json` receipt serialize
healing attempts. A successful edit must read back exactly; the next occurrence is
a no-op. Timeout/nonzero exit is not proof of failure: readback may establish
success. A missing executable or denied execution is recorded as not launched,
so repairing that prerequisite allows the next attempt. An unresolved edit stays pinned and is observed next time, never blindly
replayed. Scheduler claims, counters, monitor results and delivery observations may advance;
configuration drift is not
silently accepted. Native edits have no assumed compare-and-swap: a concurrent
external writer can still race the final read/check. Detected drift is reported,
not rolled back over another writer.

`updated_verified` means saved wiring was verified, **not** that a future occurrence,
worker, acceptance check or Telegram delivery succeeded. `edit_uncertain` requires
inspection of the original edit, not a new job or reset. A wiring hold does not
cancel an already-running original worker or manufacture an implementation blocker.

## Heal the cause before the next occurrence

After a failure, identify the earliest failed consumer and its exact inputs:

- Managed prompt or skill drift: run the helper above once and read back.
- Attributable Toolset bug: reproduce it with a regression, repair the shared source,
  run proportional checks and review, then use the supported scoped updater where
  authorized. Verify installed bytes and retry the same safe consumer. A source
  commit alone does not update a private installation.
- Selection or ownership refused: repair the exact task input or reconcile the
  actual process/workspace conflict, then rerun the direct owner cycle. Preserve
  source/check evidence. No original-card lookup, release or
  native continuation API is required.
- Missing executable/dependency, invalid workdir, failing script, model credentials
  or delivery transport: verify the actual failing boundary. Repair only from an
  attributable known installation/configuration under existing authority. Never
  guess paths, replace credentials, change models/destinations, use force overrides
  or run error text as shell code. Report the precise unavailable external input
  when a supported repair is absent; continue genuinely independent authorized work.

Retain the cause, repair, same-consumer check and remaining limitation in private
continuity evidence. Do not repeatedly run unchanged expensive diagnostics or claim
that changing a prompt fixed product execution. Report saved wiring, recovered
execution and delivered result separately.

If the scheduler, interpreter, pre-run script or model fails **before the agent
starts**, that job cannot run its own healer. An already-authorized maintainer can
invoke this same exact-job helper externally for managed wiring, then repair the
specific startup cause within its scope. Installing this helper creates no watchdog
or new schedule and does not guarantee recovery from an unavailable host or service.
