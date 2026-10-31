# TOOLSET-409-95ccc944: installed Graphify link in the Unused Code skill

## Reported main failure

The DOCS-MAINTAINER trigger reports MAIN red with one failing test. Read the bundle
in place; do not copy runtime evidence into a worktree or a commit:

`<git-common-dir>/autowork-execution/main-evidence/2c3767c07575d30d2d212d79d986c69a8e1521c7/`

Resolve `<git-common-dir>` with
`git rev-parse --path-format=absolute --git-common-dir` from this repository,
including linked worktrees.

- `main_check.json`: state `red`, result class `TEST_FAILURE`, checked revision
  `2c3767c07575d30d2d212d79d986c69a8e1521c7`, last green
  `4c1fd8c45afb42b9ad36ab50812d497e3b7142e7`, `flaky = []`, `repair_pending = []`,
  `revert_pending = false`.
- `main-check.exit`: `1`. `main-check.log` ends with
  `Offline result: 4 test directories passed; 1 failed; 3 modules excluded`, so the
  check reached test results rather than crashing.
- `main-check-reruns.log`: the failing test also fails alone, so this is neither
  three-revision flakiness nor a checker crash.
- `flaky_history.json`: the failing test ID has no recorded isolated-pass history.

Failing test:

`test_pi_toolset_bundle.PiToolsetBundleTests.test_native_profile_receives_self_contained_specialists_and_preserves_edits`

Commits since last green:

```text
2c3767c0 docs(tasks): close TOOLSET-408-38a6a41f
f893439b Add a Graphify workflow and retire the legacy graph pass
```

## Reproduction and cause

From this checkout at `da67135c`, the failure reproduces alone:

```sh
cd tests && python3 -m unittest \
  test_pi_toolset_bundle.PiToolsetBundleTests.test_native_profile_receives_self_contained_specialists_and_preserves_edits
```

```text
AssertionError: False is not true : (PosixPath('/tmp/.../skills/unused-code/SKILL.md'),
'../../adapters/skills/graphify/SKILL.md')
```

`tests/test_pi_toolset_bundle.py:69-74` installs the four pinned specialists into a
temporary profile and then requires every relative Markdown link in each installed
skill to resolve. `skills/unused-code/SKILL.md:21` links
`../../adapters/skills/graphify/SKILL.md` (added by `f893439b`). Inside the repository
that path is `adapters/skills/graphify/SKILL.md`, which exists; inside an installed
profile it is `<profile>/adapters/skills/graphify/SKILL.md`, which never exists.

`Src/autowork_runtime/install_skills.py` copies only the skill folders it is given
(`shutil.copytree` per selected skill, `install()`), and rejects symlinks inside
source skills. The installed specialists are therefore self-contained by design, and
the test name states that invariant.

## Repair boundary

Fix the reference in `skills/unused-code/SKILL.md` so an installed profile resolves
it, keeping the pointer to the current-graph ranking workflow and the pinned
Understand Anything pass as the legacy fallback. Either state the workflow without a
relative link that leaves the skill, or link to material the installed closure
contains.

Do not copy the portable adapter into `skills/`, change the installer's installed
set, edit pinned upstream bytes, or weaken the link loop. No skips, expected
failures or retries.

## Checks

```sh
python3 scripts/check.py tests/test_pi_toolset_bundle.py
python3 scripts/check.py
git diff --check
```

Offline instruction and packaging evidence only: this proves nothing about a live
graph build, dead-code findings, model behaviour or live host installation.
