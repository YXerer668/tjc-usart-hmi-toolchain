# usarthmi

[中文说明](README.zh-CN.md) | [Feature Status](FEATURE_STATUS.md)

`usarthmi` is an experimental, scriptable toolchain for TJC / USART HMI serial
screens. It started from live reverse engineering of a `TJC8048X543_011C`
800x480 panel and the official `USART HMI` editor, then grew into a Python CLI
for serial control, `.HMI` inspection, scene authoring, preview rendering, and
narrow-but-real independent `.TFT` generation.

The project is intentionally evidence-driven. Features are marked as
flashable only after they have at least one concrete proof point: fixture
byte-comparison, checksum validation, serial readback, or a photo/camera check
on the real panel.

## Why This Exists

The official editor is useful, but it is GUI-first and hard to automate. This
repository explores a more hackable workflow:

1. describe a page as JSON/YAML;
2. render a local preview;
3. build an `.HMI` for inspection or official-editor fallback;
4. when the feature is recovered, build a flashable `.TFT` directly;
5. upload through the public serial protocol and verify with live `get` /
   `sendme` commands.

This is not a complete replacement for `USART HMI` yet. It is a practical,
open research toolchain with strict guardrails around the parts that are known
to work.

## Status At A Glance

Stable enough for local use:

- Serial CLI for normal runtime commands.
- `.HMI` extraction/inspection and page preview.
- Scene JSON/YAML validation, layout solving, and PNG preview.
- Appended page0 TFT generation for the current 800x480 seed project.
- Text, button, number, image, picture resources, two-state image buttons,
  custom `.zi` fonts, xfloat, combobox, external-picture, and several basic
  controls covered by fixtures/tests.

Experimental but useful:

- Multi-page page0/page1 generation with limited plain controls.
- Event bytecode assembly/inspection for a small set of commands. Page0
  button `ref obj` is live-proven from scene DSL through TFT upload and
  camera-verified redraw after a red `fill` overlay. Page0 `tsw obj,0`
  is live-proven with a raw opcode matrix: only opcode `09` accepted the
  `target0,0` payload, and a physical tap on the disabled target left
  `numval.val` at `0`. Page1
  normal-button events are live-proven for `page 1`, explicit-hex `printh`,
  one-level same-page `click` cascades, and numeric field `++` / `=` / `--`
  operations, plus same-page `vis obj,0/1` show/hide operations;
  media/audio assignments and `play` events are fixture-backed, while live
  page-load scheduling is not fully solved.
- Single internal GMOV/animation smoke builds for the current resource layout.

Known unstable / research-only:

- Video and audio independent TFT resource scheduling.
- Official-editor smart/sparse download behavior. The recommended upload path
  is the slower full serial upload, because it is much easier to reason about
  and has been more reliable on the test machine.

For a clearer implemented / experimental / missing matrix, see
[`FEATURE_STATUS.md`](FEATURE_STATUS.md).

## Safety Notes

- Keep generated `.TFT`, `.HMI`, `.zi`, screenshots, official binaries, and
  large fixtures out of git. The repository `.gitignore` is set up for that.
- Prefer full `tft upload` over trying to reuse the official editor's
  "skip unchanged blocks" downloader. The latter was observed to leave Windows
  USB/PnP in a ghost-COM state on the development machine.
- Live smoke upload helpers use the same serial-health preflight as the CLI:
  a matching `connect` model is not enough; `sendme` and `get dim` must also
  respond before public `whmi-wri` upload is attempted.
- Do not copy official `work\a-*\output\*.tft` while the official serial
  download is actively transferring. Copy it before starting transfer or after
  the transfer has fully finished.
- The repository is MIT licensed. Reverse-engineering notes and code are open,
  but official editor binaries and proprietary payloads still stay out of git.

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
- Fixture-backed official widgets can be authored from scenes and compiled into
  the current page0 TFT tail, including virtual float / `xfloat` (`type=';'`),
  combo box / `combobox` (`type='='`), touch capture (`type=0x05`), and the
  current-editor external-picture record shape (`type='<'`). External-picture
  is live-proven when compiled against the healthy `case_00_baseline` resource
  layout; `case_46_expicture_current_gui` remains the tail/reference fixture,
  not the recommended live baseline.
- First-pass media widget authoring is available for animation / `gmov`
  (`type=0x02`), video (`type=0x03`), and audio / `wav` (`type=0x04`) in HMI and
  preview outputs. Single internal GMOV builds, a narrow single SD-video object
  smoke, and a narrow single SD-audio object smoke are available for the current
  layout; broad media playback/resource scheduling is still research-only.
- `tools/probe_official_widget_support.py` can clone one object from a
  downloaded official/sample HMI into the current seed and ask the official
  compiler whether the current target actually emits that extra object.

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

## Project Layout

- `usarthmi/`: Python package and CLI implementation.
- `examples/`: small scene files that demonstrate recovered controls.
- `tests/`: unit and fixture-backed regression tests. Some tests skip
  automatically when private/local fixtures are absent.
- `tools/`: local helper scripts for live smoke tests, official-editor fixture
  capture, camera capture, and widget probes.
- `SCENE_BUILDER.md`: scene authoring and build examples.

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
python -m usarthmi --json scene build examples\external_picture_demo\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\external_picture_demo_build
python tools\external_picture_demo_runner.py
python tools\external_picture_demo_runner.py --skip-build --smoke --capture
python -m usarthmi --json scene build examples\media_widgets_demo\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --out reverse_usarthmi\media_widgets_demo_build
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
python -m usarthmi --json tft health `
  --port COM36 `
  --baud 9600 `
  --timeout-ms 3000 `
  --expected-model TJC8048X543_011C

python -m usarthmi --json tft preflight `
  --file added_object.tft `
  --port COM36 `
  --baud 9600 `
  --expected-model TJC8048X543_011C

python -m usarthmi --json tft upload `
  --file added_object.tft `
  --port COM36 `
  --baud 9600 `
  --download-baud 921600 `
  --expected-model TJC8048X543_011C `
  --progress
```

`tft upload` runs checksum and serial-health preflight by default. Use
`--no-preflight` only for deliberate recovery or reverse-engineering probes.

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
- `case_36_xfloat` is reproduced at compiled-tail level against the official
  GUI output, with `val/vvs0/vvs1` primary-record offsets locked by tests. This
  case is now live-flashed on `COM36` in the `xfloat_combobox_demo` smoke scene,
  with `get xval.val` returning `123456`.
- `case_37_combobox` is reproduced at compiled-tail level against the official
  GUI output, including compact primary-string layout and dual `txt/path`
  pointers. This case is now live-flashed in the same smoke scene, with
  `get cbval.val` returning `2` and `get cbval.txt` returning `80V`.
- `case_46_expicture_current_gui` supersedes the older grafted
  `case_40_expicture` sample as the real current-editor "外部图片" tail fixture:
  its object record and `path` string slot are reproduced byte-for-byte against
  official GUI output. Live flashing later proved the control itself works on
  the current X543 panel when compiled from the healthy 11.4 MB
  `case_00_baseline` resource layout: `sendme` returned page `0`,
  `get exp0.path` returned `sd0/1.jpg`, and the SD image was visible on camera.
  The compact `case_46` resource/header baseline still makes the panel return
  the short `66 FF FF FF` `sendme` frame, so it is kept as a reference fixture
  only, not a runtime baseline.
- `case_38_text_select`, `case_39_touchcap`, `case_40_expicture`,
  `case_41_sltext`, `case_42_datarecord`, `case_43_filebrowser`, and
  `case_44_filestream` were grafted into the current X543 seed `.HMI` and
  compiled with the official GUI. The compiler emitted only the original four
  seed objects in the generated TFT, so these controls are recorded as
  current-target unsupported/dropped rather than pending TFT-writer work.
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
assembly has partial support (`printh`/`page`/`click`/`ref`/`vis`/`tsw`/`rawhex`):
object button events are live-proven, including `printh`, `click`, `ref`, `tsw`,
and numeric updates.
Media event bytecode is now decoded in oracle reports, with official audio
fixtures proving `wav0.vid=0`, `wav0.en=1`, and `play 0,0,0` byte-for-byte.
Page-load events are not recovered yet. A 2026-05-15 single-page `page0.load`
probe and separate page1 callback-slot probes on `COM36` both showed that the
panel does not yet schedule compiled page-load blocks. Event oracle reports now
include `scheduler_path`, `upload_risk`, and `recommended_writer_action` fields:
generated normal-table page-load probes are marked high risk, while official
media-style samples show a separate post-primary page-event chunk that remains
research-only until reproduced byte-for-byte for the target layout.
