# USART HMI Roadmap 2026-05-04

This roadmap records what is already proven, what is still missing, and the
recommended order for turning the current reverse-engineered toolchain into a
usable independent page editor / TFT builder for the current 800x480
`TJC8048X543_011C` screen.

## Current Baseline

The current toolchain is no longer only an inspector. These pieces are proven on
the real `COM36` panel:

- Serial command control and runtime verification.
- HMI extraction and `0.pa` rewriting for the current seed project.
- Scene JSON/YAML loading, layout solving, and PNG preview.
- Same-layout TFT patching for text and coordinates.
- Appending multiple `t`, `b`, and `p` objects into a flashable TFT tail.
- Object-name hash generation for arbitrary ASCII names up to 14 bytes.
- Scene-to-TFT routing for appended text/button/image objects.
- PNG/JPG packing into new TFT picture resources for appended picture objects.
- Direct serial TFT upload via public `whmi-wri`.
- Safe whole-file upload skipping when the candidate exactly matches a trusted
  known-current TFT.

The important boundary is that the generator is still a current-seed V1 chain:
it patches and extends a compatible official baseline TFT instead of compiling a
fully independent project from scratch.

## P0: Make The Existing Chain Practically Usable

### 1. HMI-Side Image Resource Writer

Goal: when scene assets are packed into `output.tft`, also add matching HMI
resource entries into `output.hmi`.

Why it matters:

- Current `output.tft` can show newly packed images on the screen.
- Current `output.hmi` does not yet contain the corresponding new `*.i` and
  `*.is` entries, so it is not a complete editable/openable project artifact for
  image-heavy scenes.

Deliverables:

- Generate `N.is` with the source-resource header plus original/normalized
  source bytes.
- Generate `N.i` with the compiled-resource header plus padded JPEG payload.
- Insert the new entries into the HMI container without disturbing existing
  seed resources.
- Extend `manifest.json` so every scene asset maps to HMI entries and TFT pic
  IDs.

Acceptance:

- Build a scene with one imported JPG/PNG.
- `output.hmi` extraction shows `1.is` and `1.i`.
- `output.tft` still flashes and `get image.pic` returns the assigned ID.

### 2. Multi-State Image Button Packing

Goal: support button assets with `normal` and `pressed` images, then map them to
compiled button fields.

Status 2026-05-04: first inferred implementation is live-flashed. The builder
packs normal/pressed images as `pic=1/2`, writes button `sta=2`, and the real
screen reads back `playbtn.bco=1`, `playbtn.bco2=2`. Visual behavior still needs
manual confirmation and later official fixture comparison.

Why it matters:

- The target UI needs real buttons, not only static pictures.
- Scene schema already describes `normal / pressed / disabled`, but new image
  IDs for button states are intentionally blocked in the current TFT build.

Remaining deliverables:

- Compare against an official image-button HMI/TFT fixture when available.
- Decide whether authoring names should expose `pic/pic2` or the observed
  runtime `bco/bco2` slots for `sta=2`.
- Preserve optional `disabled` in the model; only wire it once the exact
  compiled fields are verified.
- Verify pressed visual state by touch/manual observation.

Acceptance:

- `get btn1.pic` returns the normal picture ID.
- `get btn1.picc` returns the pressed picture ID.
- Button is visible after flashing.
- Pressed visual state is checked manually or by serial-triggered touch command
  if reliable.

### 3. Number Object TFT Support

Goal: make scene `number` widgets compile into a real TFT object, not only a
preview/HMI authoring concept.

Why it matters:

- The first-stage widget list promised `text / image / button / number`.
- The current TFT tail generator supports appended `t/b/p`; `number` still
  needs a compiled template and field mapping.

Deliverables:

- Identify the seed/editor template object type for numeric display.
- Add the record template and value-field mapping to the TFT tail generator.
- Add scene build validation for numeric fields.

Acceptance:

- Flash a scene with a number widget.
- `get n1.val` or the correct numeric attribute returns the expected value.
- Changing it over serial works after flashing.

### 4. Font Resource Integration Into TFT Build

Goal: connect the existing `.zi` generation/replacement to the TFT build path.

Why it matters:

- We can generate `.zi` and replace HMI fonts.
- We can pack TFT-style font runs.
- But `tft build` does not yet automatically replace the TFT font resource used
  by the flashed UI.

Deliverables:

- Add scene build options for `font_file`, `font_name`, `font_id`, and subset
  text collection.
- Generate or reuse `.zi`.
- Replace HMI `0.zi`.
- Replace/update the TFT font resource block and resource table.

Acceptance:

- Scene title/subtitle uses a newly generated font after flashing.
- `output.hmi` and `output.tft` agree on the font resource.
- Text clipping is verified with the current Chinese/English menu strings.

### 5. Last-Flashed Manifest Tracking

Goal: make safe upload skipping automatic for our own generated artifacts.

Why it matters:

- Current skip support requires manually passing `--known-current`.
- We can store the SHA256 of the last successful upload and avoid wasting a
  3-minute download when nothing changed.

Deliverables:

- Write `.usarthmi_last_upload.json` after a successful upload.
- Add `tft upload --skip-if-current`.
- Compare port/model/file hash before deciding to skip.

Acceptance:

- Uploading the same generated TFT twice skips the second run.
- Uploading a changed TFT still performs a full public `whmi-wri` stream.

## P1: Remove Current Seed Limitations

### 6. Full Page Tail Rebuild

Goal: move from "baseline objects unchanged plus appended objects" to "compile
the whole supported page object list."

Needed capabilities:

- Rewrite existing objects.
- Delete objects.
- Reorder objects.
- Allocate IDs consistently.
- Rebuild text pools, value-offset tables, hash/index lists, user records, and
  mirror records from the page model.

Acceptance:

- A scene can replace the seed page contents instead of only appending after
  the original objects.
- Official one-variable fixtures still byte-match where expected.

### 7. Multi-Page Support

Goal: support more than `page0`.

Needed capabilities:

- Parse and write multiple `N.pa` entries in HMI.
- Generate multiple page tails / page directories in TFT.
- Support scene `project.default_page`.
- Support `page <id/name>` navigation and page-switch buttons.

Acceptance:

- Build two pages.
- Flash TFT.
- `sendme` and `page 1` work.
- Objects on both pages are queryable.

### 8. Event/Usercode Generation

Goal: generate useful touch actions and MCU-facing events, not just static
objects.

Needed capabilities:

- Button press/release event sections.
- `print`, `prints`, `click`, `page`, and user-defined serial protocol snippets.
- Optional automatic `sendme` / component ID reporting.

Acceptance:

- Pressing a generated button sends a predictable serial event or switches page.
- Event bytes are documented in `manifest.json`.

## P2: Compatibility And Polish

### 9. Preview Accuracy

Goal: keep the preview useful enough that we do not need to constantly flash for
layout mistakes.

Improvements:

- Better font metrics.
- Button pressed-state preview.
- Image scaling/cropping warnings.
- Optional visual diff between scene preview and extracted HMI preview.

### 10. Asset Constraints And Auto-Compression

Goal: make image import boring and reliable.

Improvements:

- Enforce or warn about screen/editor image dimension limits.
- Auto-resize and JPEG-quality search to fit a target budget.
- Record padded dimensions and actual payload size in manifest.

### 11. Model/Profile Normalization

Goal: make `TJC8048X543_011` versus live `TJC8048X543_011C` boring.

Improvements:

- Normalize compatible model suffixes.
- Store `mcu_code=10501`, resolution, model series, and editor version in a
  profile object.
- Refuse unsafe cross-model builds unless explicitly forced.

### 12. Regression Fixture Suite

Goal: keep reverse-engineered binary behavior from silently regressing.

Improvements:

- Add focused fixtures for HMI image entries.
- Add official button-image cases once available.
- Add number-object cases.
- Add font-replacement TFT cases.
- Keep full binary equality tests where official compiler samples exist.

## Recommended Next Step

The best next work item is P0.2: multi-state image button packing.

Reason:

- The picture packer is already proven on real hardware.
- The scene schema already has button state concepts.
- The user-facing payoff is high: real menu buttons with normal/pressed art.
- It exercises the remaining object-tail field gap without requiring a full
  compiler rewrite.

If P0.2 exposes unknown button-tail fields, fall back briefly to P0.1 HMI-side
image resource writing, because that is a cleaner container task and will make
future image-button fixtures easier to inspect.
