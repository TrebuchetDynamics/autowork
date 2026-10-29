# Android release build and verification

Read this from APK Get before running a build. Script paths resolve from this
file's directory, not the app directory. No upload is allowed before these
build and ABI checks pass.

## 2. Build release for ARM64

Use project-pinned wrappers and lockfile-aware setup. Reuse signing without exposing
credentials. Report missing Flutter/Node/Java/Android tools precisely. Ask about
ambiguous flavors/entrypoints. Inspect scripts before running: APK, not AAB or deployment.

For ordinary projects, adapt these commands to the selected app:

```sh
# Flutter app root; preserve a configured FVM wrapper when present.
flutter build apk --release --target-platform android-arm64 --split-per-abi
# Bare React Native: run from android/; use the actual application module/variant.
./gradlew :app:assembleRelease -PreactNativeArchitectures=arm64-v8a
```

Inspect React Native Gradle configuration for architecture-property support.
Existing ABI splits/filters can affect output; flags alone are not verification.
If compilation fails, report its cause and next action. Never substitute debug,
universal/multi-ABI, AAB, or an old APK left by a failed build.

## 3. Verify the APK

Require a successful release command. Locate its matching variant output using
build logs/metadata, not a guessed filename. An up-to-date Gradle output is valid
when the successful build validated it. Typical directories are
`build/app/outputs/flutter-apk/` and `android/app/build/outputs/apk/`.

Run `python3 scripts/verify_apk.py APK` using the script's absolute path resolved
from **this skill directory**, not the app directory. It checks ZIP integrity,
root manifest and ARM64-only native libraries, and returns path, size and SHA-256.
It does not prove release mode or signing. Confirm release variant from build
logs/configuration; check the manifest with SDK `apkanalyzer` when available.
Inspect signing with `apksigner` when available. Disclose unknown verification.

Retain app/framework, command/result, absolute path, ABI evidence, size/hash,
release evidence and signing status for the receipt. A produced unsigned APK is
still a release artifact: label it **unsigned; not install-ready**. Debug-key signing
is not production signing. Do not create keys or withhold an unsigned artifact.

[Flutter release guide](https://docs.flutter.dev/deployment/android) ·
[React Native release guide](https://reactnative.dev/docs/signed-apk-android)
