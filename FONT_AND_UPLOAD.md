# Font Import And Upload

## Current Working Pieces

Build the local `.zi` helper:

```powershell
python -m usarthmi font build-zicli
```

Generate a `.zi` font subset directly from a scene:

```powershell
python -m usarthmi font from-scene `
  --scene examples\menu_demo\scene.json `
  --out .\build_font_scene.zi `
  --font-file C:\Windows\Fonts\simsun.ttc `
  --name SimSun32scene `
  --height 32 `
  --font-size 32
```

Generate a `.zi` font from explicit text files:

```powershell
python -m usarthmi font generate-zi `
  --out .\reverse_usarthmi\live_font_recognition\Impact56ASCII_ordered.zi `
  --font-file C:\Windows\Fonts\impact.ttf `
  --name Impact56Ordered `
  --height 56 `
  --font-size 64 `
  --codepage ascii `
  --text "FONT TEST 123 WIDE III 888 IMPACT CHECK"
```

For ASCII-only screen text, use `--codepage ascii` and keep all needed printable
ASCII glyphs in codepage order. `ZiCli` now emits glyphs in codepage order; this
is required because the panel resolves glyphs by the codepage index. Older
unordered subset output was accepted by the panel but rendered the wrong
characters.

Generate the currently verified Chinese/English 32px baseline font:

```powershell
python -m usarthmi font generate-zi `
  --out .\reverse_usarthmi\font_baselines\ui_cn_en_32\UiCNEN32GBFull.zi `
  --font-file C:\Windows\Fonts\SourceHanSansCN-Normal.ttf `
  --name UiCNEN32GBFull `
  --height 32 `
  --font-size 34 `
  --codepage gb2312 `
  --full-codepage `
  --no-ascii
```

Important: sparse GB2312 subset fonts currently load but render Chinese through
the wrong glyph index on this panel. The working Chinese baseline is full
GB2312 mode (`8273` characters, about `2.1MB`), which is still much smaller than
the original embedded font span used by the seed TFT.

Render a preview with the real `.zi` glyphs:

```powershell
python -m usarthmi --json hmi preview-pa `
  --pa .\reverse_usarthmi\font_baselines\ui_cn_en_32\build_stock\target_0.pa `
  --out .\reverse_usarthmi\font_baselines\ui_cn_en_32\preview_zi_font.png `
  --font 0=.\reverse_usarthmi\font_baselines\ui_cn_en_32\UiCNEN32GBFull.zi `
  --no-labels
```

`hmi preview` auto-loads embedded `N.zi` entries when they exist. `scene preview`
and `hmi preview-pa` accept explicit `--font FONT_ID=path` mappings.

Replace the `0.zi` entry inside an `.HMI` source file:

```powershell
python -m usarthmi font replace-hmi `
  --hmi .\build_menu_demo_v3\output.hmi `
  --zi .\build_font_scene.zi `
  --out .\build_menu_demo_v3\output_font.hmi
```

Upload a `.tft` file over serial:

```powershell
python -m usarthmi tft upload `
  --file your_file.tft `
  --port COM36 `
  --baud 9600 `
  --download-baud 115200
```

## Current Limit

- `.zi` generation works for visually confirmed ordered ASCII fonts.
- Full GB2312 Chinese/English font generation works and has been flashed on the
  real `TJC8048X543_011C` panel.
- `.zi` glyph decoding is integrated into local PNG previews for more faithful
  Chinese/English text layout.
- `.HMI` font replacement works.
- `.tft` serial upload command is implemented from the official download protocol.
- `tft patch-font` can replace the first embedded font in-place when the new
  `.zi` is no larger than the original font span.
- Sparse GB2312 subset fonts are not a safe baseline yet; use `--full-codepage`
  for Chinese.
