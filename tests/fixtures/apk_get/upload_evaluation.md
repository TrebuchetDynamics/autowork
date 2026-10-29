# APK Get default-upload evaluation

The user changed the contract: bare `/apk-get` discovers the app in the current
repository and uploads its verified release APK with the installed `s3upload`.
No app-path argument, new uploader installation or storage setup is required.

## Red: previous build-only guidance

Five fresh-context samples each answered the five
[upload scenarios](upload_scenarios.md) with the previous complete skill text.
All five returned the local Flutter artifact without uploading. One exact response
was: “Uploads are outside this skill’s authorization. Do not invoke `s3upload`
in any snapshot.” This obeyed the old contract but failed the new default-upload
requirement. No sample required a path when one app was already discovered.

## Green: revised build-and-upload guidance

Five fresh-context samples each answered the same scenarios with revised skill
text and its build reference. All five:

- discovered the sole app without requiring a path argument;
- selected `s3upload` for the verified artifact and used existing configuration;
- included expiry/deletion/signing information and a final raw download URL;
- retained the verified unsigned local APK when uploader configuration failed;
- avoided uploading in no-app, ambiguous-app and explicit no-network cases;
- did not configure storage, create credentials or substitute another uploader.

All five candidate success receipts ended with the supplied fake URL. The actual
host's `command -v s3upload` and `s3upload help` confirmed the CLI exists and its
current argument contract. No configuration secrets were read.

## Limits

These are five control and five guided samples from one configured delegate
model, not ten real application builds or uploads. Fake URLs use example.invalid.
No network upload, signing operation, SDK build, device install or storage
configuration was performed. The no-argument Pi command and packed reference
files have separate executable tests in `tests/portable_pi.test.mjs`.
