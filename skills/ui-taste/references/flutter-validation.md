# Flutter/Android presentation validation

Use for compact onboarding/forms, widget-rendered previews or a requested Android
APK handoff. Keep transport/domain authority unchanged during presentation polish.

## 1. Trace shared presentation and preserve behavior

Find the production screen, shared form, localization input and nearest tests before
editing. Inspect all callers before moving labels or fields: a shared form can also
serve desktop and direct widget tests. Reuse existing controls and scoped fake
providers rather than adding a parallel demo implementation.

- Remove a duplicate body heading only where the enclosing app bar already owns it.
- Keep selection semantics when removing a chip checkmark that overlaps its avatar.
- Pair short fields only when width and text scale permit; stack them at large text.
- Keep required credentials and encrypted-key passphrases available. Disclose long
  public-key/fingerprint text without removing full inspection or public-only copy.
- Dismiss the keyboard only after the existing submit validation accepts the action;
  route the last field's Done action through the same busy/validation guard.

Change localization inputs and regenerate outputs with the project's normal
generator; do not edit generated Dart copy by hand.

For connection-first refinements, inspect the composed screen before choosing a
fix. Remove redundant self-confirmation gates, then render again: nested shared
checks can contain another expanded wizard and still push the primary action off
screen. Keep optional checks and full manual/security guidance reachable after the
primary form; suppress only context-inappropriate guidance, preserving defaults
for other callers. Delete obsolete local step state and copy rather than retaining
a hidden second flow.

Test a fresh form with no saved configuration as well as a hydrated different
origin. When a phone screen displays a fixed loopback address, bind enablement,
explicit connection and optional diagnostic reads to that visible identity; a
hidden empty URL can disable a valid form, while a hydrated remote URL can send a
local token to the wrong host. Preserve credential-origin ownership checks rather
than merely changing the displayed address. Require the initial token field and
primary action to be reachable, enter a synthetic token and verify enablement,
then prove opening help makes no connection/save and preserves the masked draft.
Use wrapping helper widgets where fixed helper-line caps truncate security guidance
at large text; keep the ordinary production theme for these assertions.

## 2. Update disclosure tests without losing assertions

When content intentionally becomes collapsed, first assert it is absent from the
visible tree. Activate the actual disclosure, then retain the prior warning,
fingerprint, clipboard, failure and ownership assertions. Scroll the disclosure
header into view before pointer activation at small widths/large text. Target its
visible title/header, not the center of an expanded ExpansionTile: the keyed root
also includes the body, so a center tap may hit documentation or whitespace.
Assert keyboard focus on the header's semantics rather than the composite expanded
subtree, which may contain independently focusable links. Keep keyboard activation
coverage instead of invoking callbacks directly.

For idle forms, settle pending input-driven rebuilds before `ensureVisible`, then
activate the settled target and assert hit-testability. Settling only after scrolling
can let a deferred field reveal move the button offscreen. Keep this local to the
idle fixture; held-stream tests need bounded pumps rather than `pumpAndSettle`.
Do not suppress missed-tap warnings or call callbacks to hide this ordering error.
Scope heading assertions to the AppBar/header: a legitimate primary button can
share its text without being a duplicate heading.

Use `TargetPlatformVariant.only(TargetPlatform.android)` for Android widget cases
where available. Do not leave a global platform override set until ordinary suite
teardown: binding invariants can run before that cleanup. Match provider ownership
when disposing fakes; an override may already arrange disposal, so a second manual
disposal can make a passing body fail during cleanup.

## 3. Test viewport safety, not fortunate content placement

Exercise normal and 200% text, compact and wide callers, bottom system padding,
and a keyboard inset. After scrolling to final actions, assert both reachability
and that the enclosing scroll viewport ends above the reserved system area. A
button-only bound can pass after SafeArea is removed because content happens to
be short.

Make a complete private candidate export for the negative control, remove only
the protection under test, run the focused case and require its intended assertion
to fail. Restore in `finally`; never mutate a concurrently reviewed workspace.
If the mutation stays green, inspect whether an upstream guard masks it or the
oracle misses the defect. Strengthen the relevant assertion, then rerun the
non-equivalent mutation and restored positive case. Keep both outcomes honest.

## 4. Produce readable, accurately labeled captures

Capture real production widgets in a `RepaintBoundary`, with deterministic public
fakes and no live host access. Load available SDK fonts through `FontLoader` inside
`tester.runAsync`; resolve the SDK path from the active build environment. Precache
existing image assets before capture so a pending decode does not look like a
missing logo.

Widget tests may use Ahem for component styles even when body text renders with
the intended font. Loading Roboto alone does not ensure every label resolves it.
Inspect chips, list tiles and disclosure titles in the actual PNG. For captures
only, explicitly resolve otherwise unspecified component font families to the
loaded native font; keep ordinary geometry/behavior tests on the unmodified
production theme. Disclose that substitution, and do not change production theme
or shrink labels solely to silence a test-font artifact.

Label component-only views as components. A simulated keyboard inset is not an
actual IME screenshot. Widget renders do not qualify native Android font metrics,
system navigation, TalkBack, SSH authentication or process-death behavior.

## 5. Build and verify a requested test APK

Inspect existing signing and isolated-package rules first. Pin source in a private
checkout/export and preserve the main app's data/package. Use the production entry
point, not the E2E fixture entry point. Resolve locked dependencies without changing
the lockfile. Typical commands, only when supported by the project, are:

```sh
flutter pub get --offline --enforce-lockfile
flutter build apk --debug --split-per-abi --target-platform android-arm64 --no-pub
```

Measure the APK before selecting delivery. If a debug APK is too large for the
channel, profile mode can produce a smaller test artifact without pretending it
is a production release. Verify that profile mode gets the isolated package suffix:
Flutter may initialize it from debug before later project settings apply. If
necessary, use a documented build-only suffix overlay in the private export; do
not modify canonical packaging or weaken signing policy merely to send a file.
Do not distribute a debug-signed release where repository policy forbids it.

Before attaching the APK:

1. Use the installed SDK's `aapt dump badging` to verify package, version, minimum
   SDK and ABI; do not infer an isolated ID from an environment flag alone.
2. Run `apksigner verify`, ZIP integrity checking and SHA-256 calculation.
3. Bind the artifact to the source tree and any packaging-only overlay. Compare
   packaged AOT hashes or recognizable changed copy when cache reuse is suspect;
   APK size alone cannot prove that the new UI was compiled.
4. Copy the verified artifact to a durable task artifact location and attach that
   exact file. Preserve the verification record privately, not in product source.
5. Distinguish development/profile signing, an existing QA installation that may be
   updated, and the main production package. Building is not installation or device
   qualification. Disclose unresolved build warnings without inventing a runtime pass.

Do not install on a device, probe a private SSH host, copy credentials or claim
that UI polish fixed authentication unless separately authorized and verified.
