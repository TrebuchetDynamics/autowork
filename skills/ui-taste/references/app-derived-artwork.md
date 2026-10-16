# Brand artwork: approved source to icon proof

Use when supplied or app-rendered content becomes a logo, launcher or store icon.
Reuse the repository's renderer, capture/export tools, icon generator and provenance
owner; do not build another rendering implementation or add dependencies for resizing.
Choose the source branch first: supplied artwork uses the procedure below;
app-generated artwork continues with the renderer-specific capture steps.

## Supplied artwork: preserve, inventory, derive, verify

1. Inspect the supplied image and the current runtime logo and launcher icons
   separately. Record the owner's source selection; do not infer authorship,
   licensing or approval from an asset already being in the repository. Do not
   generate competing drafts when the owner has designated the actual artwork.
2. Preserve the untouched source and its SHA-256. Check EXIF/comments before
   committing it: if they contain private metadata, keep the original private and
   record a sanitized derivative with its distinct hash. Do not claim a sanitized
   copy is byte-identical to the original.
3. Enumerate actual asset consumers and packaging references before replacing
   anything: runtime bundle entry, Android mipmaps/adaptive XML, web favicon and
   manifest icons, Apple asset catalogs and Windows ICO frames where present.
   Preserve existing sizes and identities; do not invent a platform resource that
   the application does not use. Keep an existing runtime filename when replacing
   its bytes is sufficient and avoids an unrelated caller migration.
4. Derive each requested resource from the selected master with a recorded
   resampler. Use a house generator first, otherwise an already installed image
   library. Preserve composition and color; do not trace, crop, remove backgrounds
   or add a new mask without authority. Keep platform padding a documented
   derivative, not a silently altered master.
5. For a square image that must fit wholly inside a maskable icon's circular safe
   area, a centered 56% square is a tested conservative framing. Retain the full
   image on the recorded background and verify the rounded size rather than
   relying on the percentage label:

   ```python
   side = round(width * 0.56)
   assert 2 * (side / 2) ** 2 <= (width * 0.4) ** 2
   ```

   Apply this only to the relevant maskable resources, not ordinary full-image
   launcher/store artwork. Check the target's current safe-area requirements.
6. Compare decoded PNG pixels and every ICO frame with the expected transformed
   master; checking only the first ICO image misses stale smaller frames. Record
   source/output hashes, dimensions, frame sizes and transformations in one
   provenance manifest. Pin the approved source in a small regression and verify
   output hashes/headers so a partial icon update cannot pass unnoticed.
7. Render the actual welcome/logo consumer and native-size icon proofs. Inspect
   loading completion, aspect-ratio containment and masks. Resource coverage and
   a widget capture are not installed-device or cross-platform qualification.
   Build an APK only within the requested handoff scope and read its bundled
   branding back before attaching it.

## 1. Establish the real app-rendered source

- Inspect the registered module, actual shader and controller API before writing
  a capture test. Resolve symbols and preset constructor requirements from source,
  rather than guessing getters or reconstructing their API from examples.
- Read the capture runner's sizing and output-directory branches. A high-resolution
  mode may ignore a general staging override; run it in an isolated workspace and
  copy only its selected image/report after success.
- Save module/shader identity, complete parameters, view, palette, fixed time,
  relevant effect state and an importable app preset. Bind the capture to source
  revision plus changed-file hashes, SDK/lockfile and observed rendering backend.
- Require a real rendered frame before capture. Disable animation and renderer
  badges for the clean master; never replace a failed frame with synthetic pixels.
  Renderer flags and a nonempty PNG alone do not establish GPU or app authenticity.
- Inspect the image before iterating. When the reference has spiral texture but the
  default shows broad flat regions, investigate seed, view and actual iteration
  caps before trying more colors; palette changes cannot recover missing geometry.
  Record parameter-tuned results as custom saved states, not unchanged defaults.

## 2. Capture actual resolution, not an enlarged window

A Flutter `SizedBox` under a constrained application root can remain window-sized.
A later PNG resize can report the requested dimensions without capturing that
resolution. Use an explicitly unconstrained capture subtree, such as a fixed-size
`OverflowBox` around the production renderer's `RepaintBoundary`, and assert the
boundary size **before** capturing:

```dart
expect(boundary.size, const Size(2048, 2048));
final image = await boundary.toImage(pixelRatio: 1);
expect(image.width, 2048);
expect(image.height, 2048);
```

Do not upscale a smaller raster to satisfy these assertions. Reopen the saved state
through the actual app viewer and compare the effective rendered parameters; this
catches a harness that selects the right name but paints a different state.

## 3. Rotate only genuine pixels

Trace the requested rotation through the painter/shader: a persisted rotation value
may not be consumed by a 2D renderer. If the owner permits post-capture rotation,
preserve the raw image and describe the operation as a derivative, not app behavior.

For a square capture rotated 45 degrees, use a centered inscribed crop to avoid
black/transparent fill corners. This tested Pillow recipe retains source pixels:

```python
rotated = raw.convert('RGBA').rotate(
    -45, resample=Image.Resampling.BICUBIC, expand=True)
side = math.floor(raw.width / math.sqrt(2)) - 4
left = (rotated.width - side) // 2
top = (rotated.height - side) // 2
working = rotated.crop((left, top, left + side, top + side))
assert working.getchannel('A').getextrema() == (255, 255)
```

The small inset avoids interpolated edge pixels. Require a square opaque input;
this recipe is specific to a 45-degree rotation, not a general-angle crop formula.
Record the angle convention, expanded dimensions and exact crop rectangle.
Downsample the working crop for delivery; do not enlarge it back to the raw
size and call that a native-resolution master.

## 4. Derive and inspect the selected candidate

- Produce the existing launcher, adaptive foreground, store and in-app sizes from
  one selected working image with a documented high-quality resampler. Avoid alpha
  extraction unless it produces clean edges; an opaque full-image foreground can
  preserve the app artwork without halos.
- Show true native 32/48/64px previews on light/dark surfaces and representative
  circle/squircle/rounded-square masks. Keep labels outside the artwork; do not
  silently enlarge the small previews. Inspect adaptive safe areas separately
  from full-image store masks because they represent different framing.
- Keep store artwork full-square without a baked platform mask or outer shadow.
  Check current primary specifications, PNG mode/opacity/color space/file size and
  the repository's validator. If a new opaque RGBA icon conflicts with an RGB-only
  validator, scope compatibility changes to the icon group and preserve the other
  image groups' requirements.
- Test raw-image preservation, deterministic derivation, output sizes/modes,
  opacity, source/output hashes, rotation/crop lineage and invalid inputs. Exercise
  the same tests against the genuine staged candidate, not only synthetic fixtures.
  Label synthetic fixtures as such: a plausible receipt is not proof of origin.
- Make generated bytes deterministic when claiming reproducibility. ICC profile
  creation timestamps can vary between runs; normalize that metadata or use a
  stable color-space declaration, and test across a timestamp boundary.

## 5. Package only the chosen draft

Regenerate resources and build requested previews in a disposable worktree;
keep current branding unchanged until its replacement gate is satisfied. After a
selection changes, preserve the previous package separately before rebuilding so
an old receipt cannot point at a different binary under the same path.

Read back the APK ZIP and compare bundled source PNG hashes with the selected
staging directory. Record package hash, generated launcher resources and build
result separately from installation, device appearance and publication. Never
uninstall or clear an existing user app merely to inspect a preview.

Primary references:
- [Google Play icon specifications](https://developer.android.com/distribute/google-play/resources/icon-design-specifications)
- [Android adaptive icons](https://developer.android.com/develop/ui/compose/system/icon_design_adaptive)
