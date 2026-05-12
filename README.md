# usarthmi

Experimental Python tooling for TJC / USART HMI serial screens.

This repository started from a live reverse-engineering session around a
`TJC8048X543_011C` 800x480 screen and the `USART HMI` editor. The practical
goal is to control the screen from the command line and progressively replace
the GUI-only workflow with scriptable HMI/TFT tooling.

## Current Capabilities

- Serial command CLI for `connect`, `sendme`, `get`, `set`, `page`, `ref`,
  `vis`, `tsw`, `click`, and `dim`.
- Lightweight `.HMI` inspection and extraction helpers, including structured
  `0.pa` object/event summaries for official TJC sample projects.
- Scene JSON/YAML authoring helpers and PNG preview rendering.
- Direct `.HMI` / extracted `.pa` page preview rendering with object labels and
  embedded picture resource support.
- Preview rendering can use real `.zi` glyph data, including GB2312 Chinese
  fonts, instead of approximating text with Windows fonts.
- Runtime serial preview for simple scene layouts.
- Font subset generation helpers around the local ZiCli tool.
- Full-codepage GB2312 font generation for practical Chinese/English UI
  baselines.
- Experimental in-place TFT font replacement: a generated `.zi` can replace the
  embedded font resource in a TFT while preserving section addresses.
- TFT inspection/checksum helpers using a small vendored copy of TFTTool.
- Experimental same-layout TFT patching for text/coordinate changes.
- Experimental appended-object TFT tail generation for the current seed layout:
  adding one or more `t`, `b`, or `p` objects can be compiled into a flashable
  TFT tail.
- Scene builds can now route through that appended-object TFT generator when a
  compatible baseline TFT is supplied, emitting `output.hmi`, `output.tft`,
  `manifest.json`, and previews from one JSON/YAML scene.
- Experimental TFT picture-resource packing for scene `image` widgets: local
  PNG/JPG assets can be compiled into new `pic` resources inside the fixed TFT
  resource area and referenced by appended picture objects.
- Picture resource import handles JPG/JPEG source preservation, EXIF-oriented
  image loading, transparent PNG flattening to the screen's RGB format, 16-pixel
  storage padding, and automatic quality/scale reduction when the fixed TFT
  resource budget is tight.
- Experimental multi-state image-button packing: normal/pressed button assets
  can be packed into TFT picture resources and written into the compiled button
  background slots for live-screen testing.

## What Is Not Included

Large or potentially proprietary artifacts are intentionally not committed:

- official `.HMI` / `.TFT` / `.zi` payloads
- extracted USART HMI editor binaries
- generated build directories
- local screenshots and serial upload logs
- third-party example HMI/TFT repositories used as research references

Some local tests are skipped automatically when those optional fixtures are not
present.

## Install

```powershell
python -m pip install -e .
```

Dependencies are declared in `pyproject.toml`.

## Serial Examples

```powershell
python -m usarthmi --json connect --port COM36 --baud 9600
python -m usarthmi --json sendme --port COM36 --baud 9600
python -m usarthmi --json get t0.txt --port COM36 --baud 9600
python -m usarthmi --json set t0.txt '"hello"' --port COM36 --baud 9600
python -m usarthmi --json dim 30 --port COM36 --baud 9600
```

## HMI / Scene Examples

```powershell
python -m usarthmi --json inspect-hmi path\to\lcd_test.HMI
python -m usarthmi --json extract-hmi path\to\lcd_test.HMI --out hmi_extract
python -m usarthmi --json hmi preview --hmi path\to\lcd_test.HMI --out hmi_preview.png
python -m usarthmi --json hmi preview-pa --pa hmi_extract\0.pa --assets-dir hmi_extract --out pa_preview.png
python -m usarthmi --json scene validate examples\menu_demo\scene.json
python -m usarthmi --json scene preview examples\menu_demo\scene.json --out preview.png
python -m usarthmi --json hmi preview-pa `
  --pa reverse_usarthmi\font_baselines\ui_cn_en_32\build_stock\target_0.pa `
  --out reverse_usarthmi\font_baselines\ui_cn_en_32\preview_zi_font.png `
  --font 0=reverse_usarthmi\font_baselines\ui_cn_en_32\UiCNEN32GBFull.zi `
  --no-labels
python -m usarthmi --json tft build `
  --scene reverse_usarthmi\live_scene_build\scene_multi.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\live_scene_build
```

`inspect-hmi` reports raw strings plus parsed page/object event scripts such as
`codesload-*`, `codesdown-*`, `codesup-*`, and `codestimer-*` when `0.pa` is a
known layout.

## TFT Patch Examples

Same-layout patch:

```powershell
python -m usarthmi --json tft patch-basic `
  --baseline-tft path\to\baseline.tft `
  --baseline-pa path\to\baseline\0.pa `
  --target-pa path\to\target\0.pa `
  --out patched.tft
```

One or more appended objects, current seed layout only:

```powershell
python -m usarthmi --json tft patch-add-object `
  --baseline-tft path\to\baseline.tft `
  --baseline-pa path\to\baseline\0.pa `
  --target-pa path\to\target_with_one_or_more_added_objects\0.pa `
  --out added_object.tft
```

Upload:

```powershell
python -m usarthmi --json tft upload `
  --file added_object.tft `
  --port COM36 `
  --baud 9600 `
  --download-baud 921600 `
  --progress
```

Replace the embedded TFT font with a generated `.zi`:

```powershell
python -m usarthmi --json tft patch-font `
  --baseline-tft output.tft `
  --font custom.zi `
  --out output_custom_font.tft
```

Generate the verified Chinese/English 32px baseline font:

```powershell
python -m usarthmi font generate-zi `
  --out reverse_usarthmi\font_baselines\ui_cn_en_32\UiCNEN32GBFull.zi `
  --font-file C:\Windows\Fonts\SourceHanSansCN-Normal.ttf `
  --name UiCNEN32GBFull `
  --height 32 `
  --font-size 34 `
  --codepage gb2312 `
  --full-codepage `
  --no-ascii
```

## Verification Status

The local development session verified:

- same-layout text patch `nihao -> buhao` was flashed and read back from a real
  `TJC8048X543_011C` panel.
- one added text object `t1` was flashed and queried successfully with
  `get t1.txt` and `get t1.x`.
- arbitrary object name `note1` was flashed and queried successfully with
  `get note1.txt`, proving the recovered object-name hash algorithm live.
- three appended objects `note1`, `btn1`, and `pic1` were flashed together and
  queried successfully from the real panel.
- scene-driven build emitted a valid multi-object `output.tft` with
  `note1/btn1/pic1` via the same generator.
- scene-driven image build packed a new JPG resource as `pic=1`, flashed it,
  and read back `photo1.pic == 1` from the real panel.
- an inferred image-button build packed normal/pressed PLAY assets, flashed the
  result, and read back `playbtn.sta == 2`, `playbtn.bco == 1`, and
  `playbtn.bco2 == 2` from the real panel.
- custom `.zi` font replacement is now visually confirmed: an ordered ASCII
  `Impact56Ordered` font was generated, patched into a scene TFT, flashed, and
  photographed on the real panel with correct text and changed glyph shapes.
  Earlier unordered/UTF-8 generated fonts were loaded by the panel but produced
  wrong glyph mapping, which exposed and fixed the ZiCli glyph-order bug.
- Chinese/English 32px baseline font replacement is visually confirmed with
  `UiCNEN32GBFull.zi`: the generated full GB2312 font was patched into a scene
  TFT, flashed to `COM36`, and photographed with correct `主菜单`,
  `开始/设置/系统/返回`, `状态/正常/温度`, and mixed ASCII text. A sparse GB2312
  subset test rendered Chinese as repeated wrong glyphs, so Chinese currently
  uses `--full-codepage`.
- `.zi`-backed preview rendering is now available: `preview-pa`, `hmi preview`,
  and `scene preview` accept `--font 0=path\to\font.zi`; `hmi preview` also
  auto-loads embedded `N.zi` entries from the HMI container.
- the same `FONT TEST 123` object was rebuilt with the stock embedded font,
  flashed, and read back with `fontmsg.txt_maxl == 13`,
  `fontmsg.style == 1`, and `fontmsg.bco == 65504`.
- the picture-resource packer was corrected to preserve the official
  `unknown_objects_address == 0xAE0000` layout; a `PLAY + newtxt` scene was
  flashed, photographed, and read back with `fontmsg.txt == "newtxt"` and
  `playbtn.txt == "PLAY"`.
- official PLAY image resources are now reproduced byte-for-byte in both TFT
  and HMI forms: scene-generated `case13` / `case14` TFT files match the
  official editor outputs, and `output.hmi` contains matching `1.i`, `2.i`,
  `1.is`, and `2.is` entries for the current fixtures.
- a mixed JPG + transparent PNG + image-button stress scene was flashed to the
  real panel; an initial resource-table ordering bug swapped images on-screen,
  then sorting TFT picture records by `pic` id fixed the live display.
- local test suite passed with the available fixtures.

See `USART_HMI_STATUS_2026-05-04.md` for the detailed working log.
See `USART_HMI_ROADMAP_2026-05-04.md` for the remaining work plan and next
implementation priorities.

## Limitations

The TFT writer is not a complete replacement for the official editor yet. The
current independent generation path is deliberately narrow and optimized for
the known 800x480 seed project. Object-name hashing is solved for ASCII names up
to 14 bytes. New picture resources are proven for appended `image`/picture
objects and two-state image buttons, with current PLAY fixtures matching
official TFT outputs byte-for-byte and matching HMI `*.i` / `*.is` resource
payloads. Additional local tests cover JPG source entries, transparent PNG
flattening, non-16-aligned dimensions, and large-image shrink-to-budget behavior.
Multi-page generation, broad widget coverage, event-code authoring, and broader
font fixture coverage are still outside the proven V1 path. Event bytecode
assembly has partial support (`printh`/`page`/`click`/`vis`/`rawhex`), but a live
page-load probe on `COM36` showed that the panel does not yet schedule the
compiled event blocks; the missing piece is likely an additional TJC event
entry/index/flag outside the obvious object-tail byte stream.
