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
- Two-state full-image button packing, including official case13/case14 byte
  matches and live-proven normal/pressed PLAY assets.
- Direct serial TFT upload via public `whmi-wri`.
- Safe whole-file upload skipping when the candidate exactly matches a trusted
  known-current manifest, plus post-upload serial/runtime/camera verification.

The important boundary is that the generator is still a current-seed V1 chain:
it patches and extends a compatible official baseline TFT instead of compiling a
fully independent project from scratch.

## P0: Make The Existing Chain Practically Usable

### 1. HMI-Side Image Resource Writer

Status 2026-05-16: implemented. `build_scene` writes matching HMI `N.i` and
`N.is` picture-resource entries for scene assets, records them in
`manifest["hmi_picture_resources"]`, and current tests compare generated
case14 image-button resources against official extracted entries.

Goal: when scene assets are packed into `output.tft`, also add matching HMI
resource entries into `output.hmi`.

Why it matters:

- Current `output.tft` can show newly packed images on the screen.
- Editable/openable HMI artifacts need the same `*.i` and `*.is` entries that
  the flashable TFT path uses.

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

Status 2026-05-16: the main two-state image-button path is implemented. The
builder packs normal/pressed images, writes full-image button `sta=2`, matches
official case13/case14 TFT fixtures byte-for-byte, and is live-proven with PLAY
assets on the real panel. At runtime this panel exposes the compiled full-image
slots through `bco/bco2`, even though the authoring model keeps the clearer
`normal/pressed` asset names.

Why it matters:

- The target UI needs real buttons, not only static pictures.
- Scene schema describes `normal / pressed / disabled`; normal/pressed are now
  mapped into the flashable TFT path.

Remaining deliverables:

- Preserve optional `disabled` in the model; only wire it once the exact
  compiled fields are verified.
- Keep documenting the authoring-vs-runtime name split: scene authors use
  normal/pressed, while live serial readback for `sta=2` may report `bco/bco2`.

Acceptance:

- Generated case13/case14 TFTs match the official image-button fixtures.
- Runtime readback confirms the normal/pressed compiled slots on the live panel
  through the observed `bco/bco2` attributes.
- Button is visible after flashing.
- Pressed visual state is checked manually or by serial-triggered touch command
  if reliable.

### 3. Number Object TFT Support

Status 2026-05-16: implemented for the current fixture-backed path. Number
widgets are included in the supported page1 plain-control path and have
fixture-backed compiled-record generation. Broader all-model behavior remains
under the current-seed limitation.

Goal: make scene `number` widgets compile into a real TFT object, not only a
preview/HMI authoring concept.

Why it matters:

- The first-stage widget list promised `text / image / button / number`.
- Numeric display is part of the practical widget surface, but still depends on
  recovered current-model templates.

Deliverables:

- Identify the seed/editor template object type for numeric display.
- Add the record template and value-field mapping to the TFT tail generator.
- Add scene build validation for numeric fields.

Acceptance:

- Flash a scene with a number widget.
- `get n1.val` or the correct numeric attribute returns the expected value.
- Changing it over serial works after flashing.

### 4. Font Resource Integration Into TFT Build

Status 2026-05-16: minimum build-path integration is implemented. The separate
font tools can generate `.zi`; `scene build`, `hmi build`, and `tft build` can
now take `--font-zi` to replace `0.zi` in `output.hmi` and patch the same
same-or-smaller embedded TFT `.zi` in place before the final page/object patch.
Fully automatic font generation from scene font settings remains future work.

Goal: connect the existing `.zi` generation/replacement to the TFT build path.

Why it matters:

- We can generate `.zi`, replace HMI fonts, and patch the TFT font slot.
- Build commands now expose the safe existing-`.zi` path directly.
- Automatic generation from font settings would make the workflow less manual.

Deliverables:

- Add scene build options for an existing `.zi` and target HMI font entry.
- Generate or reuse `.zi`.
- Replace HMI `0.zi`.
- Replace/update the TFT font resource block and resource table.

Acceptance:

- `tft build --font-zi <file.zi>` emits `hmi_font_patch` and `tft_font_patch`
  manifest records.
- `output.hmi` contains the replacement `0.zi`.
- `output.tft` checksum remains valid after font patching and object patching.
- A built font demo can be flashed and read back over serial.

### 5. Last-Flashed Manifest Tracking

Status 2026-05-16: implemented. `tft upload` records
`.usarthmi_last_upload.json` after a successful public upload, and
`--skip-if-current` skips only when the candidate hash/size, port, baud, and
expected model match that manifest. This record is deliberately scoped to this
tool's last successful upload and does not claim the panel was not changed by SD
card, the official downloader, or another machine.

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

2026-05-16 status:

- Minimal P1.6 closed for the number-demo path. `examples/number_demo/full_page_rebuild_scene.json`
  uses `drop_seed_objects` to rebuild page0 as `page0/title/incbtn/numval`,
  removes seed objects `t0/b0/p0`, and changes the object order so `incbtn`
  references the later `numval` object by name.
- The final accepted TFT checksum was valid (`0x771EF87C`) and a full COM36 upload
  sent `11,408,540` bytes. Post-upload serial verification proved
  `title.txt=NUMBER DEMO`, `numval.val` `123 -> 124 -> 125`, and two
  `printh 23 02 4e 31` responses; camera capture visually confirmed
  `NUMBER DEMO`, `125`, and `+1`. This accepted proof uses
  `UiCNEN32GBFull.zi` and `numval.lenth=3`.
- The earlier `build_font_scene.zi` UTF-8 sparse-font variant was a useful
  negative proof: serial checks passed, but the panel rendered wrong U-like
  glyphs. A no-font rebuild attempt uploaded but failed post-upload runtime
  checks, so neither variant counts as the visual proof.
- Evidence lives in
  `examples/number_demo/full_page_rebuild_hardware_verified_2026-05-16.json`.
  This is still a narrow proof, not arbitrary full-page rebuild support.
- Follow-up offline reorder broadening is covered by
  `examples/number_demo/reorder_broadening_scene.json`. It rebuilds
  `page0/status/incbtn/title/footer/numval`, keeps `incbtn` before the later
  `numval` object, preserves the known-good `numval.val++` plus
  `printh 23 02 4e 31` event tokens, patches `UiCNEN32GBFull.zi`, and emits a
  valid TFT checksum (`0x6E54CC25`). This was not flashed; it extends structural
  coverage only.
- Follow-up offline event-preservation coverage is in
  `examples/number_demo/event_matrix_scene.json`. It rebuilds
  `page0/refbtn/visbtn/tswbtn/incbtn/label0/numval`, keeps the event buttons
  before their rebuilt targets, checks same-page `ref`, `vis`, `tsw`, and
  numeric `++` payloads, patches `UiCNEN32GBFull.zi`, and emits a valid TFT
  checksum (`0x59354ECE`). This was not flashed; it is bytecode/structure
  evidence only.
- Live-promotion evaluation is recorded in
  `examples/number_demo/live_promotion_candidate_2026-05-16.json`. The decision
  is not to flash the mixed event matrix yet: numeric update already has clear
  COM36 serial proof, while `ref`/`vis`/`tsw` need narrower single-family runtime
  probes with camera or touch-state evidence.
- The first single-family promotion is now live-proven in
  `examples/number_demo/vis_promotion_scene.json`, with evidence in
  `examples/number_demo/vis_promotion_hardware_verified_2026-05-16.json`. It
  selects `vis` over `ref` because hide/show is reversible and camera-visible.
  The TFT checksum is `0xE9DE787A`; COM36 upload sent `11,409,856` bytes in
  `2,786` chunks, serial clicks returned `23 02 56 30/31`, and USB Cam showed
  `label0` hidden then restored.
- The single-family `tsw` candidate is `examples/number_demo/tsw_promotion_scene.json`,
  with initial offline evidence in
  `examples/number_demo/tsw_promotion_offline_verified_2026-05-16.json`. It
  chooses `tsw` over `ref` because a target-button marker can form a later
  positive/negative runtime probe. The TFT checksum is `0x8AA3D6C3`. Existing page1 evidence says
  serial `click` is not equivalent to physical touch for proving lockout, so the
  live gate is blocked until real touch input or click-equivalence is available.
  The follow-up batch
  `examples/number_demo/tsw_touch_gate_batch_2026-05-16.json` checked local tools,
  COM36, USB Cam, checksum, and the related pytest slice; it found the hardware
  available but no automated physical-touch or proven equivalent input path, so
  the decision was no-burn until that gap was closed. The current controlled
  path is `tools/tsw_physical_touch_proof.py`: it waits for user acknowledgement,
  gates on baseline TG, avoids writing/ref'ing `targetbtn` after disable, and
  records only `physical_touch_lockout_live_observed` when baseline, disabled,
  and recovery windows all match the narrow rule. The follow-up burn in
  `examples/number_demo/tsw_promotion_serial_click_hardware_verified_2026-05-16.json`
  uploaded the isolated `tsw` TFT, proved page readback/camera health and T0/T1
  dispatch, then showed the fallback is a negative result: serial
  `click targetbtn,1` still emits TG after `tsw targetbtn,0`. A later explicit
  `click 1`/`click 0` retest confirmed that release is needed for visual state,
  but the TG-after-disable result remains. A same-session fast timing scan then
  tested 0/10/20/50/100/200 ms delay windows across 18 critical disable->target
  trials and every one saw T0 followed by TG, so the serial-click negative result
  is not explained by slow command timing. The user's manual touch is captured in
  `reverse_usarthmi/number_demo_tsw_promotion_gb2312font_20260516/real_touch_listen_20260516_2020.json`:
  a 90 s listener saw real-touch TG/T0/T1 markers, proving the user's finger path
  reaches the scripted events. The user then reported that after pressing DISABLE
  by hand, TARGET could no longer be pressed, which supports physical touch
  behaving differently from serial click. Two subsequent segmented listeners did
  not capture baseline/recovery TG and are recorded as synchronization failures,
  not as evidence against lockout. A panel-visible prompt pass captured baseline
  and recovery TG, but it also wrote/refreshed `targetbtn` after disable and is
  treated as contaminated for the disabled window; the fully machine-captured
  proof still needs a synchronized pass that first gates on baseline TG without
  touching `targetbtn` after disable.

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

2026-05-16 status:

- `P1-event-001` is closed for the current number-demo path. The generated
  `examples/number_demo` page0 `incbtn` down event was verified on
  `COM36`/`TJC8048X543_011C` after a manifest skip: `get numval.val => 123`,
  `click incbtn,1 => hex:23 02 4e 31`, `get numval.val => 124`,
  another click, then `get numval.val => 125`.
- The hardware evidence is recorded in
  `examples/number_demo/hardware_verified_2026-05-16.json`. This proves the
  button event and serial side channel; it does not claim page-load scheduling.

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

The best next work item is still P1.6/P1.8 cleanup: full page rebuild plus event
generation hardening, but only against fixture-backed cases. After the
2026-05-16 `P1-event-001`, the minimal P1.6 full-page rebuild closeout, offline
reorder broadening, and offline same-page event matrix, the lowest-risk next
slice is to promote one more event family only with the same narrow discipline:
do not flash the mixed matrix. Either design a similarly isolated `ref` or
`tsw` fixture with an unambiguous serial/camera proof, or continue with
fixture-backed bytecode comparison for more commands.

Reason:

- P0.1 image resources, P0.2 two-state image buttons, P0.3 numbers, P0.4
  `--font-zi`, and P0.5 last-upload tracking are now implemented in the current
  tree.
- The practical gaps are no longer the first-pass build artifacts; they are
  removing current-seed limitations and making generated events broader without
  regressing proven cases.
- Page-load and scheduler behavior still need fixture evidence, so new event
  work should stay tied to official examples or live smoke tests.

If the goal is only a live-panel demo rather than an editable HMI package, the
next practical branch is media runtime proof tightening, especially speaker
validation for audio and broader playback/resource scheduling evidence.
