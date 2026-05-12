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

Normalize a single image asset:

```powershell
python -m usarthmi hmi import-image .\examples\menu_demo\assets\play.png --out .\tmp_assets
```

## Scene Notes

- `canvas.width/height` are fixed to `800x480` for the current workflow.
- `project.clean_seed_objects: true` keeps seed objects in the compiled table
  for compatibility but moves them offscreen, leaving the generated scene visually
  clean.
- `assets` can define `normal`, `pressed`, and optional `disabled` image variants.
- `button` widgets map those image states to `pic`, `picc`, and `pic2/picc2`.
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
  TFT with `tft patch-font`; this safe pass replaces the first embedded `.zi`
  in place and keeps all section addresses unchanged.
- PNG/JPG picture-resource encoding now uses the recovered official JPEG settings
  (`quality=96`, 4:2:0 subsampling, 96 DPI). More official-editor fixtures are
  still useful before claiming compatibility for every image source shape, but
  the local non-official edge cases are now covered by regression tests.
