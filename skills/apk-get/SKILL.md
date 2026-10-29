---
name: apk-get
description: Use when requesting Flutter or React Native ARM64 APKs.
license: MIT
---

# APK Get

Build the repository's existing Android application as a release APK containing
only `arm64-v8a` native libraries. Release mode and signing identity are separate.

Apply the [shared Ponytail method](../shared/PONYTAIL.md) and
[communication rules](../shared/COMMUNICATION.md) within this build-only scope.
Invocation authorizes discovery, dependency restoration and local builds. Preserve
user changes and network/read-only limits. No source rewrites, global SDK installs,
new keystores, credential disclosure, uploads, publication, device installs or Git delivery.

## 1. Select the application

Read repository instructions and status. Honor an explicit app path, flavor or
entrypoint. Otherwise inspect tracked and nonignored project manifests, excluding
vendored dependencies, build output, caches and linked worktrees.

- Flutter: confirm a Flutter application, Android target and entrypoint, not merely
  a Dart library or Flutter plugin. Inspect `pubspec.yaml` and Android build files.
- React Native: confirm `react-native` in `package.json` and an Android application
  module. React web alone is not React Native. Inspect workspace scripts and Gradle.
- No app: report **no supported Android app found**, without scaffolding one.
- Multiple apps without a selection: list their paths and ask which to build.
- Expo without native Android files: use an existing documented local APK workflow
  only. Ask before prebuild/native generation; do not start a remote EAS build.

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

## 3. Verify and return the APK

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

Return: app/framework, exact build command/result, absolute APK path, ABI evidence,
size/hash, release-variant evidence and signing status. A produced unsigned APK is
still a release artifact: return it explicitly **unsigned; not install-ready**.
A debug-key-signed release is not production-signed. Never invent signing material
or withhold a produced unsigned artifact merely because no release key exists.

[Flutter release guide](https://docs.flutter.dev/deployment/android) ·
[React Native release guide](https://reactnative.dev/docs/signed-apk-android)
