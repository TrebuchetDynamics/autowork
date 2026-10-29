# APK Get evaluation receipt

Evaluated the five [scenarios](scenarios.md) in five fresh-context samples without
the new skill, then five fresh-context samples with its complete text. Each sample
answered all five snapshots. These were read-only decision/command simulations;
no Flutter, Gradle, signing, device or remote build ran.

## Baseline

All five samples correctly rejected no-app, ambiguous-app and stale-output cases.
Their Flutter commands used `--target-platform android-arm64` without the more
explicit split-per-ABI recipe. They already required actual ABI inspection.
Do not count this omission alone as a demonstrated invalid APK.

One sample unnecessarily required signing availability before returning a release
artifact. Its exact response included: “Blocked if release signing is unavailable.”
The other samples allowed or accurately labeled unsigned output. This distinction,
not universal baseline failure, motivated the explicit release-versus-signing rule.

## With the skill

All five samples selected the explicit Flutter release/ARM64/split-per-ABI recipe
and the React Native release APK task with the ARM64 architecture property. All
included actual artifact verification, app-choice/no-app handling and stale-output
rejection. All five explicitly labeled unsigned output as “unsigned; not
install-ready” instead of creating credentials or requiring production signing.
They also distinguished debug-key signing from production signing.

## Limits and executable checks

These are 10 samples from the configured delegate model, not qualification across
all models or SDK versions. Raw child outputs are harness session artifacts; this
receipt retains only the relevant observations. No general reliability percentage
or real application build success is inferred.

`tests/test_apk_get.py` executes the bundled verifier against disposable ZIP
fixtures, including mixed/wrong ABIs, malformed/missing outputs and missing root
manifest. `tests/portable_pi.test.mjs` exercises command dispatch, literal argument
preservation and packed-package resource discovery. The APK helper deliberately
does not attest release mode, signing, application behavior or installability.
