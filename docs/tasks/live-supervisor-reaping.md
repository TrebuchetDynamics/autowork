# Live supervisor reaping

Status: Accepted

Owner direction: Autowork must resolve stalls through implementation and production releases, not stop at diagnosis. This bounded repair implements the existing supervisor contract; it does not weaken cleanup, task checks or publication gates.

## Evidence and decision

At source baseline 4462f2fa, the batch supervisor remains alive while its verification payload runs. Exited orphan workers from nested offline runner fixtures are adopted by that supervisor. `Src/pi_autowork/pi_process.py` only polls its direct payload during the live wait; its authoritative `waitpid` reaping runs only at final cleanup. Adopted zombies therefore remain while fixtures wait for their process groups to disappear (`parallel_state.group_live`). The batch cannot reach final cleanup because those fixtures wait and time out first. Existing `task_execution.reap_exited` documents a related supervisor obligation.

Chosen repair: nonblocking authoritative reaping during the live supervisor wait, preserving the direct payload's real exit status if reaped. Do not ignore zombies in liveness checks, signal unrelated processes, reap another parent's children or publish cleanup-complete before final cleanup. Preserve signal/deadline/nonzero-exit and permission-denial behavior. No new runtime setting or dependency.

## Acceptance and checks

A real isolated Linux process regression creates an exited adopted descendant while the payload remains alive and waits for its disappearance. It must disappear before payload exit, its process group must cease appearing live, and the final guard record must preserve the payload exit code and complete cleanup. Retain live descendant, signal, parent-death and uncertain-cleanup negative cases.

Proposed commands: `python3 scripts/check.py pi-autowork/tests/test_pi_process.py pi-autowork/tests/test_pi_rpc.py`; from `tests/`, `python3 -m unittest test_pi_autowork.EngineTests.test_independent_tasks_run_in_parallel_and_merge_verified_into_main`. Run affected selection on the implementation base; inspect selection before executing to avoid the planning document's unmapped-full fallback. Independent review precedes integration. Main's full check still belongs to the runner.

Write set: `Src/pi_autowork/pi_process.py`, `pi-autowork/tests/test_pi_process.py`, and the supervisor lifecycle section of `docs/pi-rpc.md`. Parent owns this plan and task record. Existing worker candidates, their scopes and cleanup receipts are preserved. After validated integration, use supported in-place toolset reload; an already-running old supervisor does not acquire new code merely because its coordinator reloaded. Recover its batch only through supported coordinator controls and fresh cleanup/admission proof. Push the verified scoped delivery through the existing Git distribution; do not claim production adoption without checking installed/runtime revisions.
