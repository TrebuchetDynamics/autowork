---
name: apk-get
description: Use when requesting Flutter or React Native ARM64 APKs.
license: MIT
---

# APK Get

Build the repository's existing Android application as a release APK containing
only `arm64-v8a` native libraries, then upload it using the host's installed
`s3upload`.

Apply the [shared Ponytail method](../shared/PONYTAIL.md) and
[communication rules](../shared/COMMUNICATION.md) within this build-and-upload scope.
Invocation authorizes dependency restoration, local builds and uploading only the
verified APK with existing `s3upload` configuration. Preserve user
changes and explicit read-only/no-network/no-upload limits. No source rewrites,
global SDK installs, new keystores, credential disclosure, storage reconfiguration,
app-store publication, device installs or Git delivery.

## 1. Select the application

`/apk-get` needs no arguments: find the app in the current repository. Read
instructions/status; honor explicit app/flavor/entrypoint choices. Inspect tracked
and nonignored manifests, excluding vendored dependencies, caches, build output
and linked worktrees.

- Flutter: inspect `pubspec.yaml`, Android application target and entrypoint;
  exclude Dart libraries and Flutter plugins.
- React Native: require `react-native` in `package.json` plus an Android application
  module; inspect Gradle/workspace scripts. React web alone is unsupported.
- No app: report **no supported Android app found**, without scaffolding one.
- Multiple apps without a default: list discovered names/locations and ask which;
  do not require the user to supply a literal path.
- Expo without native Android files: use an existing documented local APK workflow
  only. Ask before prebuild/native generation; do not start a remote EAS build.

## 2. Build and verify

Read the [build and verification procedure](BUILD.md) before running build commands.
Use the discovered app and its existing release/flavor/signing configuration.
Verify the matching APK with the bundled ABI checker. A build command or filename
alone does not prove ARM64-only output. Do not upload debug, multi-ABI, AAB, stale
or unverifiable artifacts. Keep unsigned release artifacts clearly labeled.

## 3. Upload with s3upload

After successful build and ABI verification, check `command -v s3upload` and
`s3upload help`. Use the installed tool and its existing configured destination,
not an AWS CLI substitute. Do not reinstall it or inspect configuration secrets.
Run one upload of the verified APK's absolute path:

```sh
s3upload "$APK"
```

Use `--expires DURATION` for a requested lifetime (`48 hours` becomes `48h`);
otherwise use its 24-hour default. Add `--no-shorten` when the user forbids
third-party shortening or requests the original URL. Do not upload any keystore,
credentials, logs, another app or an artifact left by a failed build. No listing,
deletion, alternate uploader or storage configuration follows from this command.

If the tool/config is missing or upload fails, report **build succeeded; upload
failed/blocked**, retain the local APK path, and state the exact cause. Never
invent a link or claim remote delivery from local build success. Explicit network
or upload restrictions mean local delivery only, with upload reported as blocked.

On success return filename, size, link expiry and reported deletion window, plus
build/ABI/signing evidence. Distinguish link expiry from approximate lifecycle
deletion; disclose an unreported window. The download URL is a bearer secret:
return it only to the requesting user, never commit or post it elsewhere.
The final line contains **only the raw URL returned by s3upload**.
