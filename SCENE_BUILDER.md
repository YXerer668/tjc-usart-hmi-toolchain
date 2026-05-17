# USART HMI Scene Builder

## Quick Start

Build the bundled example scene against the current seed project:

```powershell
python -m usarthmi scene build examples\menu_demo\scene.json `
  --seed "D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI" `
  --out .\build_menu_demo_v2
```

Build a flashable experimental TFT from the scene by supplying a compatible
official baseline TFT:

```powershell
python -m usarthmi --json tft build `
  --scene reverse_usarthmi\live_scene_build\scene_multi.json `
  --seed "D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI" `
  --baseline-tft "C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft" `
  --out reverse_usarthmi\live_scene_build
```

Validate a scene file:

```powershell
python -m usarthmi scene validate examples\menu_demo\scene.yaml
```

Build the live-safe SD external-picture demo:

```powershell
python -m usarthmi --json scene build examples\external_picture_demo\scene.json `
  --seed "D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI" `
  --baseline-tft "C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft" `
  --out reverse_usarthmi\external_picture_demo_build
```

Or use the dedicated runner. It builds and verifies the TFT checksum by default,
without opening the serial port:

```powershell
python tools\external_picture_demo_runner.py
```

Replay the live serial checks for that flashed demo:

```powershell
python tools\live_tft_smoke.py `
  --file reverse_usarthmi\external_picture_demo_build\output.tft `
  --out-dir reverse_usarthmi\external_picture_demo_build\smoke `
  --expect-json examples\external_picture_demo\smoke.expect.json
```

Add `--capture` to the same command when visual evidence is needed. The default
capture backend is the known-good DirectShow `USB Cam` path on this workstation.

Build the first-pass media widget HMI/preview demo:

```powershell
python -m usarthmi --json scene build examples\media_widgets_demo\scene.json `
  --seed "D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI" `
  --out reverse_usarthmi\media_widgets_demo_build
```

Append media widgets to an existing scene file:

```powershell
python -m usarthmi --json hmi add-animation --scene my_scene.json `
  --id gm0 --x 40 --y 80 --w 300 --h 170 `
  --path sd0/anim/official_0.gmov --enabled --loop 1

python -m usarthmi --json hmi add-video --scene my_scene.json `
  --id v0 --x 420 --y 80 --w 300 --h 170 `
  --path sd0/video/official_0.video --enabled

python -m usarthmi --json hmi add-audio --scene my_scene.json `
  --id wav0 --path sd0/music/official_0.wav --disabled
```

For controls that do not have a dedicated `hmi add-*` helper yet, use the
generic authoring entrypoint:

```powershell
python -m usarthmi --json hmi add-widget --scene my_scene.json `
  --id exp0 --type expic --x 20 --y 260 --w 180 --h 120 `
  --resource path=sd0/1.jpg --style path_m=24
```

Normalize a single image asset:

```powershell
python -m usarthmi hmi import-image .\examples\menu_demo\assets\play.png --out .\tmp_assets
```

## Scene Notes

- `canvas.width/height` are fixed to `800x480` for the current workflow.
- `project.clean_seed_objects: true` keeps seed objects in the compiled table
  for compatibility but shrinks them to a 1x1 in-bounds placeholder, leaving the
  generated scene visually clean without producing off-screen coordinates.
- `assets` can define `normal`, `pressed`, and optional `disabled` image variants.
- `button` widgets map those image states to `pic`, `picc`, and `pic2/picc2`.
- `external-picture` / `expicture` widgets use a runtime path such as
  `sd0/1.jpg`; for live builds, keep `case_00_baseline/lcd_test.tft` as the
  resource baseline. `case_46_expicture_current_gui` is a tail/reference
  fixture only and its compact resource layout is not a safe live baseline for
  the current X543 panel.
- `animation`/`gmov`, `video`, and `audio`/`wav` are available as HMI/preview
  authoring controls. The single-GMOV smoke path can emit a TFT for the current
  recovered layout; mixed GMOV/video/audio scheduling is still not closed, so
  do not pass `--baseline-tft` for `media_widgets_demo`.
- Layout authoring supports `absolute`, `row`, `column`, `grid`, `stack`, and `anchor`.
- Output files are:
  - `output.hmi`
  - `output.tft` when `--baseline-tft` is provided and the added widgets are supported
  - `scene.normalized.json`
  - `manifest.json`
  - normalized image files under `assets\`

## Current Limits

- The `.HMI` writer now rebuilds the seed container directory, rewrites `0.pa`,
  and appends generated `N.i` / `N.is` picture resource pairs.
- Image files are normalized, assigned resource IDs in `manifest.json`, and
  embedded into both `output.hmi` and `output.tft` when referenced by widgets.
- The TFT path can append scene-generated `text`, `button`, and `image` widgets
  to the current 800x480 seed layout.
- `drop_seed_objects` can now be used for the smallest live-proven full-page
  rebuild slice in `examples/number_demo/full_page_rebuild_scene.json`. That
  proof replaces the seed page object list with `page0/title/incbtn/numval`,
  removes `t0/b0/p0`, and verifies the button event on COM36. The visually
  accepted proof uses the full GB2312 `UiCNEN32GBFull.zi` font and
  `numval.lenth=3`; a UTF-8 sparse font build passed serial checks but rendered
  wrong glyphs. Keep broader rebuild claims fixture-gated.
- `examples/number_demo/reorder_broadening_scene.json` is the next offline
  reorder fixture. It broadens the same full-page rebuild path to
  `page0/status/incbtn/title/footer/numval`, keeping the button before its
  later number target and preserving the known-good event tokens without making
  a new live-panel claim.
- `examples/number_demo/event_matrix_scene.json` is an offline event-preservation
  fixture for clean rebuilt pages. It rebuilds same-page `ref`, `vis`, `tsw`,
  and numeric `++` button events against later rebuilt text/number targets and
  checks compiled payload bytes without making page-load, media, timer, or live
  runtime claims.
- `examples/number_demo/vis_promotion_scene.json` is the narrower single-family
  live-proven promotion after the event matrix. It rebuilds
  `page0/title/hidebtn/showbtn/label0`, checks `vis label0,0/1` plus fixed
  `printh 23 02 56 30/31` click markers against the later rebuilt `label0`,
  and has COM36 plus USB Cam hide/show evidence. This only promotes `vis` for
  the isolated page0 clean-rebuild fixture.
- `examples/number_demo/tsw_promotion_scene.json` is the single-family `tsw`
  candidate. It rebuilds `page0/title/disablebtn/enablebtn/targetbtn`,
  checks `tsw targetbtn,0/1` plus fixed `printh 23 02 54 30/31/47` markers
  against the later rebuilt `targetbtn`, and deliberately avoids claiming that
  runtime touch-disable behavior is proven. The touch-gate follow-up evidence in
  `examples/number_demo/tsw_touch_gate_batch_2026-05-16.json` keeps that boundary:
  COM36 and USB Cam are usable, but no current repo tool can provide physical
  touch or a proven equivalent input path. The current operational path is
  `tools/tsw_physical_touch_proof.py`: block on user acknowledgement, capture a
  baseline TG marker before disable, avoid writing/ref'ing `targetbtn` after
  disable, and record disabled/recovery windows separately.
  The serial-click fallback burn is recorded in
  `examples/number_demo/tsw_promotion_serial_click_hardware_verified_2026-05-16.json`;
  it proves T0/T1 dispatch on hardware but shows serial `click targetbtn,1` still
  emits TG after `tsw targetbtn,0`. A fast timing scan in the same serial session
  tested 0/10/20/50/100/200 ms delay windows, 18 critical trials total, and still
  saw T0 followed by TG every time; this rules out slow serial command timing for
  the serial-click-path result. A later 90 s real-touch listener captured TG/T0/T1
  markers from the user's finger touches, and the user reported that after pressing
  DISABLE by hand, TARGET could no longer be pressed. Two follow-up segmented
  listeners did not catch baseline/recovery TG, so they are synchronization misses,
  not physical-lockout negatives. A panel-visible prompt pass did catch baseline
  and recovery TG, but that version wrote/refreshed `targetbtn` after disable and
  is treated as contaminated for the disabled window. The next controlled path is
  `tools/tsw_physical_touch_proof.py`: it blocks on `tools/wait_user_ack.ps1`,
  uses title-only prompts, aborts before disable unless baseline TG is captured,
  never writes or refs `targetbtn` after disable, and restores `page 0` at exit.
- New PNG/JPG assets are packed into TFT picture resources for appended `image`
  widgets and assigned sequential `pic` ids after the seed resources.
- Picture imports now preserve original JPG/JPEG payloads in `.is`, flatten
  transparent PNGs to black-backed RGB, pad stored JPEG dimensions to 16-pixel
  boundaries, and can reduce JPEG quality/scale to fit the fixed TFT resource
  budget.
- TFT picture records are emitted sorted by `pic` id; the live panel appears to
  resolve pictures by table order, so out-of-order resource records can swap
  image contents even when object properties read back correctly.
- Multi-state image buttons use the recovered official `sta=2` object-tail
  layout: normal maps to `pic`, pressed maps to `pic2`, and generated `case13`
  / `case14` TFT files now match official outputs byte-for-byte for the current
  PLAY image fixtures.
- Custom fonts can be generated with `font generate-zi` and patched into a built
  TFT with `tft patch-font`; `scene build`, `hmi build`, and `tft build` can
  also take `--font-zi` to patch the same file into `output.hmi` and the safe
  in-place TFT font slot during the build. This safe pass replaces the first
  embedded `.zi` in place and keeps all section addresses unchanged.
- PNG/JPG picture-resource encoding now uses the recovered official JPEG settings
  (`quality=96`, 4:2:0 subsampling, 96 DPI). More official-editor fixtures are
  still useful before claiming compatibility for every image source shape, but
  the local non-official edge cases are now covered by regression tests.
