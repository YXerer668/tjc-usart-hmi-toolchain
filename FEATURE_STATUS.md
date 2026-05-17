# Feature Status

This project is evidence-driven. A feature is marked "implemented" only when it
has code plus at least one useful proof point such as a parser regression test,
fixture byte comparison, checksum validation, serial readback, or live-panel
camera verification.

Legend:

- **Stable**: intended for normal use in this repository's current workflow.
- **Experimental**: implemented, but narrow, fixture-shaped, or current-panel
  specific.
- **Authoring only**: scene/HMI/preview support exists, but independent TFT
  output is not considered flashable.
- **Research only**: useful reverse-engineering code or notes exist, but this is
  not a supported workflow.
- **Not implemented**: intentionally not available yet.

## Core Toolchain

| Area | Status | Notes |
| --- | --- | --- |
| Serial runtime CLI | Stable | `connect`, `sendme`, `get`, `set`, `page`, `ref`, `vis`, `tsw`, `click`, and `dim` use the public string protocol. |
| `.HMI` inspect/extract | Stable | Reads the recovered container layout and parses useful `0.pa` page/object/event metadata. |
| Scene JSON/YAML model | Stable | Supports validation, normalization, layout solving, and JSON/YAML round-trips. |
| Preview renderer | Stable | Renders scenes, extracted `.pa` pages, and `.HMI` files; can use real `.zi` glyphs. |
| Layout engine | Stable | `absolute`, `row`, `column`, `grid`, `stack`, and `anchor` resolve to fixed 800x480 coordinates. |
| Full serial upload | Stable | Uses the public upload protocol; slower than official smart download, but much safer to reproduce. |
| Last-upload manifest tracking | Stable | Successful CLI uploads atomically write `.usarthmi_last_upload.json`; `tft upload --skip-if-current` skips only when SHA256/size, port, baud, and expected model match that manifest. |
| Post-upload verification | Stable | `tft upload --verify-after-upload` can combine serial health, `--verify-get`, repeatable runtime `--verify-step`, and optional camera capture; failures return non-zero and block manifest updates. |
| TFT checksum / inspection | Stable | Uses the recovered checksum path and a small vendored TFTTool helper. |
| Same-layout TFT patch | Stable | Live-proven for text/coordinate style changes on the current panel. |
| Page0 appended-object TFT build | Experimental | Can rebuild the current seed page tail and append known object records. |
| Page0 full-page rebuild | Experimental | Minimal P1.6 slice is live-proven for `examples/number_demo/full_page_rebuild_scene.json`: `drop_seed_objects` rebuilt the page as `page0/title/incbtn/numval`, removed seed objects `t0/b0/p0`, preserved a forward object-reference event from `incbtn` to `numval.val`, passed checksum, full COM36 upload, serial readback, and camera visual proof. The accepted proof uses the full GB2312 `UiCNEN32GBFull.zi` font and `numval.lenth=3`; the earlier UTF-8 sparse font build was serial-good but visually wrong. Built-in clean-rebuild coverage for text/button/number/image/timer is in `examples/builtin_controls_demo/scene.json`, with evidence in `examples/builtin_controls_demo/full_rebuild_offline_verified_2026-05-17.json`. Offline reorder broadening is covered by `examples/number_demo/reorder_broadening_scene.json` for text/button/number objects. Offline full-rebuild broadening now covers the fixture-backed non-media controls in `examples/new_controls_demo/scene.json`: progress, slider, gauge, QR code, scrolling text, dual/state button, checkbox, radio, hotspot, crop image, variable, and waveform; evidence is in `examples/new_controls_demo/full_rebuild_offline_verified_2026-05-17.json`. The next offline broadening covers clean rebuild for `examples/xfloat_combobox_demo/scene.json`, `examples/external_picture_demo/scene.json`, a minimal touch-capture page, and single-media GMOV/video/audio smoke pages; mixed media clean rebuilds are deliberately rejected until scheduling is proven. Evidence is in `examples/full_rebuild_control_broadening_2026-05-17.json`. This is still not broad arbitrary-page support yet. |
| Picture-resource packing | Experimental | Packs local PNG/JPG assets into TFT picture resources; committed COM36 evidence for a normal image widget is in `examples/image_resource_demo/hardware_verified_2026-05-17.json`; two-state image buttons are also live-proven separately. |
| Custom `.zi` font generation/patching | Experimental | Full GB2312 Chinese/English baseline is live-proven; `scene/hmi/tft build --font-zi` now patches the same `.zi` into `output.hmi` and the safe in-place TFT font slot. Sparse Chinese subsets are not reliable yet. |
| Multi-page TFT build | Experimental | Limited to the recovered two-page layout and plain page1 controls, including image widgets that reference an existing picture ID plus checkbox/radio values. Seed page0 existing-button event patching is live-proven for two-way navigation through `patch_seed_page0_widgets`. |
| Event bytecode compiler | Experimental | Can emit/decode some `page`/`printh`/`click`/`ref`/`vis`/`tsw`/`play`/assignment bytecode. Page0 button `ref obj`, `tsw obj,0/1`, ordered multi-line numeric scripts, timer `codestimer-` numeric increment after runtime `tm0.en=1`, button-script `tm0.en=1` timer start, and the `examples/number_demo` `incbtn` down event (`numval.val++` plus `printh 23 02 4e 31`) are live-proven from scene DSL through TFT upload/manifest skip and serial readback; the number demo proof verified `numval.val` `123 -> 124 -> 125` with repeatable `--verify-step` shorthand. Offline clean-rebuild event preservation is covered by `examples/number_demo/event_matrix_scene.json` for same-page `ref`, `vis`, `tsw`, and numeric `++` payloads against rebuilt text/number targets. The single-family `examples/number_demo/vis_promotion_scene.json` slice is now live-proven for page0 clean rebuild: `hidebtn/showbtn` execute `vis label0,0/1`, emit fixed `printh 23 02 56 30/31`, and USB Cam shows `label0` hidden then restored. The single-family `examples/number_demo/tsw_promotion_scene.json` slice is now live-tested for serial command dispatch: `disablebtn/enablebtn` emit T0/T1 markers after COM36 upload, but serial `click targetbtn,1` still emits TG after `tsw targetbtn,0`; a same-session 0/10/20/50/100/200 ms fast timing scan repeated 18 critical trials and still saw T0 then TG every time, so the serial-click-path negative result is not explained by slow command timing. This is not a physical touch-disable proof. Page1 normal-button events are live-proven for `page 1`, explicit-hex `printh`, one-level same-page `click` cascade, numeric field `++` / `=` / `--`, and same-page `vis obj,0/1` visibility operations. Media/audio events such as `wav0.vid=0`, `wav0.en=1`, and `play 0,0,0` are byte-aligned against official fixtures. Page-load probes are classified by `scheduler_path`/`upload_risk`; `page_event_oracle_batch.py` finds only one complete page-load oracle in current `case_for_codex`, and official audio page-load is identified as a `post_primary_page_event` chunk. Normal-table page-load builds still must stay fixture-gated because they did not fire live. |
| Official smart/sparse download | Research only | Captured and partially understood, but not recommended after USB/PnP instability on the test machine. |
| Full `.HMI` decompiler/editor replacement | Not implemented | The tool edits through a recovered scene model and seed project; it does not reconstruct every official editor feature. |
| Generic all-model TFT compiler | Not implemented | Current writer targets the recovered 800x480 `TJC8048X543_011C` seed layout. |

## Widget Status

Current-target scene support is guarded by
`test_current_target_supported_widget_types_have_tft_writer_path`: every
`SUPPORTED_WIDGET_TYPES` entry must either use a built-in writer path or a
fixture-backed template in `FIXTURE_WIDGET_TEMPLATE_CASES`, and the
current-target unsupported controls must stay outside the supported set. The
2026-05-17 matrix snapshot is in
`examples/widget_capability_matrix_2026-05-17.json`; its `scene_examples`
section maps every supported widget type to a concrete scene and evidence file.
The current-target completion audit is
`examples/all_supported_controls_completion_audit_2026-05-17.json`: it verifies
writer paths plus clean full-page rebuild offline coverage for all supported
widget types, while explicitly excluding controls that the current target's
official compiler drops. This is not live COM36 behavior proof for every widget.
The live-proof gap is tracked separately in
`examples/live_widget_proof_matrix_2026-05-17.json`.

| Widget / feature | Scene/HMI | Independent TFT | Evidence level |
| --- | --- | --- | --- |
| Page object | Implemented | Experimental | Required by all page builds. |
| Text | Implemented | Stable for current seed | Live serial readback and font tests. |
| Button | Implemented | Stable for current seed | Live multi-object tests. |
| Number | Implemented | Experimental | Fixture-backed and included in page1 plain-control path. |
| Image / picture | Implemented | Experimental | Live-proven with packed JPG resources. |
| Two-state image button | Implemented | Experimental | Live-proven with normal/pressed PLAY assets. |
| External picture / SD image | Implemented | Experimental | Committed COM36 upload/readback/camera evidence in `examples/external_picture_demo/hardware_verified_2026-05-17.json` against healthy `case_00_baseline`; `case_46` is fixture/reference only. |
| Custom font display | Implemented | Experimental | ASCII and full GB2312 baseline fonts visually verified. |
| Virtual float / xfloat | Implemented | Experimental | Byte-aligned fixture tests plus committed COM36 readback evidence in `examples/xfloat_combobox_demo/hardware_verified_2026-05-17.json` for `xval.val` and `xval.vvs1`; `xval.vvs0` runtime semantics remain separate. |
| Combo box | Implemented | Experimental | Byte-aligned fixture tests plus committed COM36 readback evidence in `examples/xfloat_combobox_demo/hardware_verified_2026-05-17.json` for `cbval.val/down/txt`; dropdown interaction and `cbval.qty` runtime readability remain separate. |
| Slider | Implemented | Experimental | Fixture-backed record generation; allowed in page1 plain controls. |
| Gauge | Implemented | Experimental | Fixture-backed record generation; allowed in page1 plain controls. |
| Progress bar | Implemented | Experimental | Fixture-backed record generation; allowed in page1 plain controls. |
| QR code | Implemented | Experimental | Fixture-backed record generation. |
| Timer | Implemented | Experimental | Fixture-backed; 2026-05-15 live-proven for `tm0.codestimer- -> numval.val++` after runtime enable toggle. `page 0` reload restores `tm0.en=1` but does not start scheduling, so boot/page-load autorun remains open. |
| Variable | Implemented | Experimental | Fixture-backed record generation. |
| Dual-state button | Implemented | Experimental | Fixture-backed record generation. |
| State button / switch | Implemented | Experimental | Fixture-backed record generation. |
| Hotspot / touch area | Implemented | Experimental | Fixture-backed record generation. |
| Waveform | Implemented | Experimental | Fixture-backed record generation; broad runtime drawing helpers are not complete. |
| Checkbox | Implemented | Experimental | Fixture-backed record generation. |
| Radio | Implemented | Experimental | Fixture-backed record generation. |
| Crop image | Implemented | Experimental | Fixture-backed record generation. |
| Scrolling text (`case_22`) | Implemented | Experimental | Fixture-backed record generation. |
| Touch capture (`case_45`) | Implemented | Experimental | Current-editor fixture-backed record generation. |
| GMOV animation | Implemented | Experimental | Single internal GMOV smoke path is the recommended media test. |
| Video | Implemented | Experimental | Single SD-path video object tail is TFT-buildable and live serial-readback proven; broad playback/resource scheduling is not closed. |
| Audio / WAV | Implemented | Experimental | Single SD-path audio object tail is TFT-buildable; live readback and `wav0.en` start/stop control are proven, but speaker validation is still open. |
| Text select (`case_38`) | Authoring probe only | Not implemented | Current target/editor compile dropped the grafted object. |
| Sliding text / `sltext` (`case_41`) | Authoring probe only | Not implemented | Current target/editor compile dropped the grafted object. |
| Data record | Authoring probe only | Not implemented | Current target/editor compile dropped the grafted object. |
| File browser | Authoring probe only | Not implemented | Current target/editor compile dropped the grafted object. |
| File stream | Authoring probe only | Not implemented | Current target/editor compile dropped the grafted object. |

## Practical Recommendations

- Use `examples/menu_demo` or `examples/external_picture_demo` to understand
  the stable scene flow.
- Use `examples/all_supported_controls_completion_audit_2026-05-17.json` as the
  "all current-target supported controls" boundary. `legacy_basic_controls_demo`
  is only a basic visual smoke scene, not all-controls coverage.
- Use `examples/live_widget_proof_matrix_2026-05-17.json` before claiming
  runtime/live completion for a widget. It records which supported widgets have
  committed live artifacts and which still only have smoke recipes or offline
  coverage.
- Use `examples/number_demo/full_page_rebuild_scene.json` when you need the
  smallest live-proven P1.6 full-page rebuild example. It deliberately drops
  seed objects and rebuilds `page0/title/incbtn/numval`. For visual proof, build
  it with `reverse_usarthmi/font_baselines/ui_cn_en_32/UiCNEN32GBFull.zi` and
  keep `numval` at `length: 3`; do not generalize that result to arbitrary
  widgets without a focused fixture or live check.
- Use `examples/number_demo/reorder_broadening_scene.json` for the offline
  reorder-broadening fixture: it rebuilds `page0/status/incbtn/title/footer/numval`
  and keeps the button's forward reference to the later `numval` object.
- Use `examples/builtin_controls_demo/scene.json` for the offline clean
  full-page rebuild fixture that exercises the built-in writer controls:
  text, button, number, image, and timer. It checks object order, selected
  fields, checksum, and button/timer references to a rebuilt number target.
- Use `examples/new_controls_demo/scene.json` for the offline clean full-page
  rebuild fixture that exercises fixture-backed non-media controls in one page.
  It removes seed objects and verifies the rebuilt page object table and TFT
  checksum, but it is not a live visual/control-behavior proof.
- Use `examples/number_demo/event_matrix_scene.json` for the offline
  same-page event-preservation fixture on clean rebuilt pages. It covers
  `ref`, `vis`, `tsw`, and numeric `++` payloads without making a new live claim.
- Use `examples/number_demo/live_promotion_candidate_2026-05-16.json` before
  deciding to flash that event matrix. The current decision is to avoid a mixed
  ref/vis/tsw/numeric flash until one event family has a tight runtime readback
  or camera proof plan.
- Use `examples/number_demo/vis_promotion_scene.json` for the live-proven
  single-family `vis` slice. Hardware proof is in
  `examples/number_demo/vis_promotion_hardware_verified_2026-05-16.json`; it
  builds `page0/title/hidebtn/showbtn/label0`, verifies `vis label0,0/1`,
  fixed `printh` markers, and USB Cam hide/show evidence. Do not generalize it
  to `ref`, `tsw`, the mixed event matrix, or arbitrary widgets.
- Use `examples/number_demo/tsw_promotion_scene.json` for the single-family
  `tsw` candidate. Offline evidence is in
  `examples/number_demo/tsw_promotion_offline_verified_2026-05-16.json`; it
  verifies `tsw targetbtn,0/1` and fixed `printh` markers against a rebuilt
  `targetbtn`, but does not prove runtime touch disable yet. Existing page1
  evidence says serial `click` is not the same path as finger touch, so a future
  `tsw` live proof needs real touch input or a separately proven click-equivalence
  check. The follow-up batch in
  `examples/number_demo/tsw_touch_gate_batch_2026-05-16.json` confirmed COM36 and
  USB Cam are available, but found no existing automated physical-touch or
  equivalent injection path; therefore the `tsw` candidate could not be burned
  as a physical touch-disable proof in that batch. The current controlled path
  is the segmented runner `tools/tsw_physical_touch_proof.py`, which blocks on
  user acknowledgement, captures baseline TG first, avoids writing/ref'ing
  `targetbtn` after disable, and records disabled/recovery windows separately.
- The 2026-05-16 serial-click fallback burn is recorded in
  `examples/number_demo/tsw_promotion_serial_click_hardware_verified_2026-05-16.json`:
  upload/readback/camera passed, `disablebtn` and `enablebtn` emitted T0/T1, but
  `click targetbtn,1` still emitted TG after `tsw targetbtn,0`; the explicit
  `click 1` then `click 0` retest confirmed release is needed for visual state
  but did not change the TG result. A same-session fast timing scan then tested
  0/10/20/50/100/200 ms between disable and target, 18 critical trials total;
  every trial saw T0 followed by TG, so the result is not a slow-command artifact.
  This is live proof that the tested serial click path is not suppressed by that
  `tsw` state. The user's later manual touch was captured with a 90 s serial listener, producing real-touch-path
  TG/T0/T1 markers, and the user then reported that after pressing DISABLE by
  hand, TARGET could no longer be pressed. That supports the physical touch path
  behaving differently from serial click, but two follow-up segmented listeners
  missed baseline/recovery TG and are logged as synchronization failures, not
  as negative physical-lockout evidence. A later panel-visible title+target-text
  prompt captured baseline/recovery TG, but it also wrote/refreshed `targetbtn`
  after disabling, so its disabled-window TG is treated as contaminated. Keep the
  next real-touch pass segmented through `tools/tsw_physical_touch_proof.py`: use
  a blocking confirmation popup, screen-visible title-only prompts that never
  write or `ref targetbtn` after disable, first capture baseline TG as the
  user-sync gate, then test disable/recovery.
- Use `examples/media_single_gmov_smoke` for animation work; do not mix GMOV,
  video, and audio in one flashable TFT until the scheduler is recovered.
- Use full `tft upload` for live-panel testing. Treat official smart download
  as reverse-engineering material, not the default deployment path.
- Use `tft upload --skip-if-current` to avoid repeating an identical upload
  from this tool, but treat SD-card flashes, official downloads, or other
  machines as outside the manifest's proof boundary.
- Use `tft upload --verify-after-upload --verify-get obj.attr=value` for
  burn-and-check loops. The serial verification runs after real upload and
  after a manifest skip, and failed verification prevents updating the
  known-current manifest. Add repeatable `--verify-step` runtime commands for
  action/readback sequences such as `get numval.val => 124`,
  `click incbtn,1 => hex:23 02 4e 31`, or media enable toggles, and add
  `--verify-capture` to include camera evidence in the same post-upload
  verification result.
- Keep private official fixtures and generated binaries outside git. If you add
  a new widget, add the smallest testable fixture notes and avoid committing
  large/proprietary payloads.
