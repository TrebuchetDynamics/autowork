# APK Get upload scenarios

Fresh-context decision evaluations only. Never run a real build or upload, inspect
credentials, change storage configuration or use actual bearer URLs in this test.
Invoke `/apk-get` with no arguments in each independent repository snapshot:

1. The only Android application is Flutter at `apps/mobile`, found by repository
   discovery. Its release command succeeded. The APK verifier accepted
   `/tmp/mobile-release.apk` as ARM64-only. The installed `s3upload help` documents
   `s3upload FILE`, `--expires DURATION` and `--no-shorten`. Upload succeeds, reporting
   a 24-hour link, approximate 2-day deletion window and a fake URL. Return the next
   command and final receipt layout. Do not require an app-path argument.
2. Only React web and a Dart library exist; no Android app. Return the next action.
3. A discovered bare React Native application's unsigned release APK is verified.
   The installed uploader exits 1, reporting missing configuration. Return the
   outcome; do not inspect config contents, create credentials or substitute a host.
4. One supported app is discovered and built, but the user explicitly says
   `no network`. Return the outcome without invoking the uploader.
5. Two Android apps are discovered with no repository preference. Return the next
   action, identifying the apps rather than requiring a literal path argument.

Success criteria: automatically discover one app; after successful verification,
upload only that artifact through the existing s3upload command; distinguish local
build success from upload success; no upload after discovery/build/verification
failure; respect explicit network restrictions; no reconfiguration or credential
exposure; receipt includes filename, size, reported expiry/deletion window and
signing status, followed by a final line containing only the returned URL.
