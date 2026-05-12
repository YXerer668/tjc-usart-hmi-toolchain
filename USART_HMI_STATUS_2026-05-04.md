# USART HMI Status 2026-05-04

## Scope

This note records the current state of the local `usarthmi` toolchain, verified artifacts, and the exact gap that still blocks a true `scene -> TFT -> flash` workflow for the `TJC8048X543_011C` screen on `COM36`.

## Verified Working Pieces

### Serial runtime control

- `COM36 @ 9600` is the active screen link.
- Runtime drawing works on the real screen.
- The following have been visually verified on hardware:
  - page background color changes
  - temporary runtime button previews
  - scene-driven runtime preview push

### Scene authoring and preview

- Scene validation works for both JSON and YAML.
- Scene layout resolution works for:
  - `absolute`
  - `row`
  - `column`
  - `grid`
  - `stack`
  - `anchor`
- Local PNG preview rendering works.
- Current preview entrypoint:

```powershell
python -m usarthmi scene preview examples\menu_demo\scene.json --out .\preview_menu_demo.png
```

### HMI page rewriting

- The seed HMI container can be parsed safely.
- `0.pa` round-trips exactly for the current seed page.
- Rebuilt `.HMI` files preserve the original seed container addressing style.
- Scene build emits:
  - `output.hmi`
  - `preview.png`
  - `scene.normalized.json`
  - `manifest.json`

### Font toolchain

- The local `ZiLib` library is built successfully against `.NET Framework 4.8`.
- The local helper [ZiCli.exe](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/tools/ZiCli/bin/Release/ZiCli.exe>) is built and runnable.
- Existing seed font [0.zi](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/hmi_extract_v1/0.zi>) can be inspected.
- New `.zi` subset fonts can be generated from:
  - explicit text files
  - scene text
- `0.zi` replacement inside `.HMI` works.
- Multiple `.zi` files can now be packed into a TFT-style embedded font run.

## Important Artifacts

### Scene / HMI

- Seed HMI: [lcd_test.HMI](</D:/MySTM32/H723ZGT6/Program/ISP_Test/lcd_test.HMI>)
- Example scene preview: [preview_menu_demo.png](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/preview_menu_demo.png>)
- Current built scene HMI: [output.hmi](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/build_menu_demo_v3/output.hmi>)
- Current built scene HMI with replaced font: [output_font.hmi](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/build_menu_demo_v3/output_font.hmi>)
- Build manifest: [manifest.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/build_menu_demo_v3/manifest.json>)

### Fonts

- Extracted seed font: [0.zi](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/hmi_extract_v1/0.zi>)
- Demo generated subset font: [build_font_demo.zi](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/build_font_demo.zi>)
- Scene-derived subset font: [build_font_scene.zi](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/build_font_scene.zi>)
- Packed TFT-style font run: [build_tft_font_run.bin](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/build_tft_font_run.bin>)
- Demo text source for font generation: [zi_chars_demo.txt](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/tools/zi_chars_demo.txt>)

### Local tooling

- Font helper executable: [ZiCli.exe](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/tools/ZiCli/bin/Release/ZiCli.exe>)
- Font helper source: [Program.cs](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/tools/ZiCli/Program.cs>)
- Python font integration: [font_toolchain.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/font_toolchain.py>)
- Python TFT uploader: [tft_download.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/tft_download.py>)
- Python TFT inspector: [tft_toolchain.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/tft_toolchain.py>)
- Python TFT font packer: [tft_font_pack.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/tft_font_pack.py>)
- Reference parsed TFT sample: [tft_reference_nextion43_18may.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/tft_reference_nextion43_18may.json>)
- Experimental forced-conversion TFT, not flashed: [build_experimental_hsv_to_tjc8048x543.tft](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/build_experimental_hsv_to_tjc8048x543.tft>)
- Official compiled target TFT, flashed and verified: [official_lcd_test_TJC8048X543_011_20260504.tft](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/official_lcd_test_TJC8048X543_011_20260504.tft>)
- Official target TFT inspection: [official_lcd_test_TJC8048X543_011_20260504.inspect.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/official_lcd_test_TJC8048X543_011_20260504.inspect.json>)
- Extracted `USART HMI.exe` embedded PE files: [embedded_pe](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/embedded_pe>)
- XOR-decoded `ACTR.dll` container: [ACTR_xor09.bin](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/ACTR_xor09.bin>)
- Extracted `ACTR.dll` entries: [actr_entries](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/actr_entries>)

## Commands That Work Now

### Build local font helper

```powershell
python -m usarthmi font build-zicli
```

### Generate `.zi` from scene text

```powershell
python -m usarthmi font from-scene `
  --scene examples\menu_demo\scene.json `
  --out .\build_font_scene.zi `
  --font-file C:\Windows\Fonts\simsun.ttc `
  --name SimSun32scene `
  --height 32 `
  --font-size 32
```

### Replace `0.zi` in an HMI file

```powershell
python -m usarthmi font replace-hmi `
  --hmi .\build_menu_demo_v3\output.hmi `
  --zi .\build_font_scene.zi `
  --out .\build_menu_demo_v3\output_font.hmi
```

### Push a runtime scene preview to the real screen

```powershell
python -m usarthmi scene push-preview examples\menu_demo\scene.json --port COM36 --baud 9600 --page page0
```

### Inspect an existing TFT file

```powershell
python -m usarthmi --json tft inspect --file .\github_refs\Gaggiuino_35\Nextion_43\Nextion_43_18MAY2024_0_Deg.tft
```

### Upload the official compiled target TFT

```powershell
python -m usarthmi --json tft upload `
  --file .\official_lcd_test_TJC8048X543_011_20260504.tft `
  --port COM36 `
  --baud 9600 `
  --download-baud 921600 `
  --timeout-ms 8000
```

The uploader now mirrors the official open-source `TFTFileDownload` preparation sequence by default:

- sends `delay=2500`
- waits `1500ms`
- sends an empty command
- sends `whmi-wri filesize,baud,0`
- streams 4096-byte chunks and waits for `0x05` after each chunk

Use `--progress` to print progress to stderr. Use `--prepare-delay-ms 0` to disable the `delay=2500` preparation step.

### Analyze TFT upload chunks

```powershell
python -m usarthmi --json tft plan-upload `
  --file .\official_lcd_test_TJC8048X543_011_20260504.tft `
  --baseline .\official_lcd_test_TJC8048X543_011_20260504.tft `
  --download-baud 921600
```

For the known-good official TFT:

- file size: `11408156`
- upload chunks: `2786`
- theoretical serial-only minimum at `921600 8N1`: about `123.786s`
- all-`FF` chunks: `31`
- all-zero chunks: `16`
- comparing the file against itself reports `2786/2786` identical chunks

### Pack `.zi` files into a TFT-style font run

```powershell
python -m usarthmi --json tft pack-fonts `
  --font .\build_font_demo.zi `
  --font .\build_font_scene.zi `
  --out .\build_tft_font_run.bin
```

## What Is Not Finished Yet

- There is still no real `.tft` compiler in `usarthmi`.
- The serial upload command has now been exercised successfully with a known-good official `.tft` for this exact screen.
- The generated `.HMI` files are not yet equivalent to a fully official `USART HMI` build product.
- Static image resource packing into final `.HMI/.TFT` is still incomplete.
- The official `.tft` generated by `USART HMI` has been flashed and should persist after power cycle; what is still missing is a self-generated `.tft` from the `usarthmi` toolchain.
- The local `TFTTool` model database contains `TJC8048X543_011`, but the real screen handshake reports `TJC8048X543_011C`, so the suffix difference still needs to be explained or normalized before a fully confident generator/patcher path exists.
- Current `TFT` progress is strongest on the font segment; page/object/picture/resource sections are still not emitted by our own builder.
- A forced-converted same-resolution sample TFT was generated from `HSV Test.tft` to target `TJC8048X543_011`, but it was not flashed because the source content still reports `model_series=0` (T0), while `TJC8048X543` is X5 (`model_series=3`). It is useful as a header/checksum experiment, not as a safe screen payload.

## New Reverse Engineering Notes

- `ACTR.dll` is not a normal PE file. XORing the whole file with `0x09` reveals a 64-byte-record container.
- The decoded container includes these core entries:
  - `HMIFORM.dll`
  - `TFTEDIT.dll`
  - `TFTRUN.dll`
  - `Tcode.dll`
  - `hmitype.dll`
- The bundled `AppDllPass.dll` was extracted from `USART HMI.exe` and exports:
  - `AppDllPass_Decode`
  - `AppDllPass_Encode`
- Applying `AppDllPass_Decode` directly to the extracted entries does not yet produce normal PE headers, so there is at least one more loader/decode step.
- The real panel reports `mcu_code=10501` in `connect`.
- Official install file `3.cc` starts with little-endian code `10501`, and its payload size field matches `len(file)-8`. This strongly indicates `3.cc` is the matching static MCU/code block for the current panel family.
- The official wiki now provides `TFTFileDownload` binaries and C# source. Downloaded copies are kept locally:
  - [TFTFileDownload_0.zip](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/external/TFTFileDownload_0.zip>)
  - [TFTFileDownload_1.zip](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/external/TFTFileDownload_1.zip>)
  - [MainFrame.cs](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/external/TFTFileDownload_source/TFTFileDownLoad/TFTFileDownload/MainFrame.cs>)
- The open-source `TFTFileDownload` implementation does not contain a sparse/incremental protocol. It uses the same public protocol:
  - optional scan/connect
  - `delay=2500`
  - empty command
  - `whmi-wri filesize,baud,0`
  - 4096-byte chunks
  - wait for single-byte `0x05` after command and each chunk
- The public wiki page [HMI download protocol](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/hmi_download_protocol.html>) also documents only full-stream `whmi-wri`.
- Therefore the official editor's "same part not downloaded/written" behavior is not exposed by the public TFT downloader source. It is likely either:
  - inside the closed `USART HMI` editor download path, or
  - inside the screen bootloader/flash layer as "receive full stream but skip flash erase/write for unchanged blocks".

## Flash Verification 2026-05-04

- Official output path supplied by user:
  - `C:\Users\SinYu\AppData\Roaming\USART HMI\work\a-20265415630280\output\lcd_test.tft`
- The official TFT inspected as:
  - `model=TJC8048X543_011`
  - `model_series=3`
  - `lcd_resolution_x=800`
  - `lcd_resolution_y=480`
  - `editor_version=tjc-1.67.6`
  - `file_size=11408156`
- The file was uploaded successfully over `COM36`:
  - initial baud: `9600`
  - download baud: `921600`
  - chunks sent: `2786`
- Post-flash serial verification passed:
  - `connect` returned `TJC8048X543_011C`
  - `sendme` returned page `0`
  - `get dim` returned `100`
  - `get t0.txt` returned `nihao`
  - `get b0.txt` returned `ceshi`
  - `get p0.pic` returned `0`

## Chinese / English Font Baseline 2026-05-05

- Added a practical 800x480 `page0` font baseline under:
  - [ui_cn_en_32](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/font_baselines/ui_cn_en_32>)
- The verified scene contains:
  - `主菜单  UI FONT 32`
  - `开始  设置  系统  返回`
  - `状态: 正常  温度: 36.5C`
  - `确认 / 取消 / 保存 / 运行`
  - `中文英文混排 OK 123 ABC xyz`
- `ZiCli` now has `--full-codepage`, exposed through:
  - `python -m usarthmi font generate-zi --full-codepage`
- A sparse GB2312 subset font was tested first:
  - [UiCNEN32GB.zi](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/font_baselines/ui_cn_en_32/UiCNEN32GB.zi>)
  - size about `29.6KB`
  - result: loaded by the panel, but Chinese rendered as repeated wrong glyphs
  - conclusion: GB2312 subset mode is not a safe baseline on this panel yet
- The working baseline is full GB2312:
  - [UiCNEN32GBFull.zi](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/font_baselines/ui_cn_en_32/UiCNEN32GBFull.zi>)
  - `8273` characters
  - `.zi` payload about `2.1MB`
  - font height `32`
  - codepage `gb2312`
- The flashed TFT is:
  - [output_gb2312_full.tft](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/font_baselines/ui_cn_en_32/build_gb2312_full/output_gb2312_full.tft>)
- Upload verification:
  - `COM36`
  - initial baud `9600`
  - download baud `921600`
  - bytes sent `11414492`
  - chunks sent `2787`
  - elapsed about `209s`
- Serial verification after flashing:
  - `sendme` returned page `0`
  - `get title.font` returned `0`
  - `get title.txt` raw bytes were `D6 F7 B2 CB B5 A5 20 20 55 49 20 46 4F 4E 54 20 33 32`
  - protocol parser now decodes `0x70` string returns as `gbk`, so JSON `value` shows `主菜单  UI FONT 32`
- Visual verification:
  - [ui_cn_en_32_gb2312_full_cam1.jpg](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/font_baselines/ui_cn_en_32/captures/ui_cn_en_32_gb2312_full_cam1.jpg>)
- Added `.zi`-backed preview rendering:
  - new parser/renderer: [zi_font.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/zi_font.py>)
  - `hmi preview-pa`, `hmi preview`, and `scene preview` accept `--font 0=path\to\font.zi`
  - `hmi preview` also auto-loads embedded `N.zi` entries from the HMI container
  - generated local preview: [preview_zi_font.png](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/font_baselines/ui_cn_en_32/preview_zi_font.png>)
  - generated scene preview: [scene_preview_zi_font.png](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/font_baselines/ui_cn_en_32/scene_preview_zi_font.png>)

## TFT Object Tail Reverse Probe 2026-05-04

- Added a repeatable CLI probe:
  - `python -m usarthmi --json tft reverse-tail --file official_lcd_test_TJC8048X543_011_20260504.tft --hmi-pa hmi_extract_current\0.pa --context-bytes 32`
- The current evidence JSON is saved at:
  - [official_lcd_test_tft_tail_reverse.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/official_lcd_test_tft_tail_reverse.json>)
- The official TFT object region is:
  - start `0xAE0000`
  - end `0xAE10DE`
  - size `0x10DE`
- The parsed `.HMI` `0.pa` objects align uniquely with the compiled TFT object records:
  - `page0`: header `0xAE01EB`, body `0xAE0207`, coords `0xAE0213`, value offset `0x20`, record length `0x40`
  - `t0`: header `0xAE022B`, body `0xAE0247`, coords `0xAE0253`, value offset `0x60`, record length `0x54`, text `nihao` at `0xAE0313`
  - `b0`: header `0xAE027F`, body `0xAE029B`, coords `0xAE02A7`, value offset `0xB4`, record length `0x54`, text `ceshi` at `0xAE031F`
  - `p0`: header `0xAE02D3`, body `0xAE02EF`, coords `0xAE02FB`, value offset `0x108`, record length `0x40`
- In each object record:
  - `coord_offset - 0x0C` is the body start.
  - `body_start - 0x1C` is the object header.
  - header byte 0 matches the HMI object type (`y/t/b/p`).
  - header byte 1 matches the HMI object id.
  - body dword 0 matches the compiled object value offset.
- A u32 value-offset table matching all four body dword-0 values exists at `0xAE01DB`:
  - `0x20, 0x60, 0xB4, 0x108`
- Text objects currently share a compiled text-pointer bias:
  - bias `0x1CB`
  - `t0` body `+0x2C` stores pointer `0x148`; `0x148 + 0x1CB = 0x313`, which is `nihao`
  - `b0` body `+0x30` stores pointer `0x154`; `0x154 + 0x1CB = 0x31F`, which is `ceshi`
- Resource matching from the extracted `.HMI` directory shows:
  - `0.i` is embedded byte-for-byte in the official TFT at `0x80F14`
  - `0.zi` is embedded byte-for-byte in the official TFT at `0x81BD6`
  - `Program.s`, `0.pa`, and `0.is` are not embedded as raw files
- Static resource matching from the installed `USART HMI` directory shows:
  - `input.bin` is embedded byte-for-byte at `0x20090`
  - `3.cc` is embedded byte-for-byte at `0x24532`
  - `cdx.dll` is embedded byte-for-byte at `0x7F4DA`
- These sections are contiguous:
  - `0x20000..0x20090`: 0x90-byte resource directory/header
  - `0x20090..0x24532`: `input.bin`
  - `0x24532..0x7F4DA`: `3.cc`
  - `0x7F4DA..0x80F14`: `cdx.dll`
  - `0x80F14..0x81BD6`: HMI `0.i`
  - `0x81BD6..0xACF82A`: HMI `0.zi`
  - `0xACF82A..0xAE0000`: zero padding/alignment before the object tail
- The 0x90-byte resource directory stores relative offsets from `0x20000`:
  - word 0/1: `input.bin` offset `0x90`, size `0x44A2`
  - word 3/4: `3.cc` offset `0x4532`, size `0x5AFA8`
  - word 6/7: `cdx.dll` offset `0x5F4DA`, size `0x1A3A`
  - word 21/22: `0.i` offset `0x60F14`, size `0xCC2`
  - word 24/25: `0.zi` offset `0x61BD6`, size `0xA4DC54`
- This means first-pass picture and font transfer can likely reuse the HMI resource blobs directly, while page/object data must be compiled into the object tail format.
- This is now the strongest known path toward a TFT writer/patcher: generate or patch the object tail from `.pa` semantics, then handle picture/font/resource tables separately.

## Case Diff Reverse Probe 2026-05-04

- User-provided one-variable official compiler samples are stored under:
  - `C:\Users\SinYu\Desktop\case_for_codex`
- Added a repeatable comparison CLI:
  - `python -m usarthmi --json tft compare-cases --case-root "C:\Users\SinYu\Desktop\case_for_codex" --out reverse_usarthmi\case_compare --install-dir "C:\Program Files (x86)\USART HMI"`
- The summary is saved at:
  - [summary.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/case_compare/summary.json>)
- `case_01_t0_text_hello`:
  - same file size as baseline
  - changes only `0xAE0313..` string pool text plus the final 4-byte word
- `case_02_t0_x_plus10`:
  - same file size as baseline
  - changes `t0` primary coordinates at relative `0x253`
  - also changes mirrored/render coordinates at relative `0x11A0`
  - changes the final 4-byte word
- `case_03_b0_text_test`:
  - same file size as baseline
  - changes `b0` string pool text plus the final 4-byte word
- The compiled tail must be considered `unknown_objects_address..EOF`, not only `unknown_objects_address..pictures_address` from TFTTool:
  - baseline tail size `0x131C`, while TFTTool `pictures_address` cuts at `0x10DE`
  - the post-`pictures_address` section contains mirrored coordinates/render metadata and the final 4-byte word
- Coordinate matches are now two-per-object:
  - baseline `page0`: `0x213`, `0x1116`
  - baseline `t0`: `0x253`, `0x11A0`
  - baseline `b0`: `0x2A7`, `0x122A`
  - baseline `p0`: `0x2FB`, `0x12B4`
- Adding one object changes the value-offset table:
  - 4-object baseline: `0x20, 0x60, 0xB4, 0x108`
  - 5-object cases: `0x24, 0x64, 0xB8, 0x10C, 0x148`
- Adding duplicate text does not deduplicate the string pool:
  - `case_04_add_text` stores `nihao`, `ceshi`, `nihao`
  - `case_05_add_button` stores `nihao`, `ceshi`, `ceshi`
- Text pointer bias remains stable in 5-object cases:
  - bias `0x1EB`
  - `t0` pointer body `+0x2C`
  - `b0/b1` pointer body `+0x30`
- Final 4-byte checksum is now decoded:
  - implemented in [tft_checksum.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/tft_checksum.py>)
  - X5 / model series 3 uses the TFTTool word-based CRC variant
  - the checksum is then XORed with bytes `0x03`, `0x2E`, and `0x3C` from the TFT header/body
  - verified against all 7 user-provided official TFT samples

## Experimental TFT Writer V0 2026-05-04

- Added a conservative same-layout TFT patcher:
  - [tft_patch.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/tft_patch.py>)
  - CLI: `python -m usarthmi --json tft patch-basic --baseline-tft <official-baseline.tft> --baseline-pa <baseline-0.pa> --target-pa <target-0.pa> --out <candidate.tft>`
- Current V0 scope:
  - object count/type/order must be unchanged
  - patches all matching coordinate sequences in the compiled tail
  - patches fixed-size text slots using `txt_maxl + 2` bytes
  - recomputes the final 4-byte TFT checksum by default
- Validation against user-provided official cases:
  - `case_01_t0_text_hello`: generated TFT equals official target byte-for-byte
  - `case_02_t0_x_plus10`: generated TFT equals official target byte-for-byte
  - `case_03_b0_text_test`: generated TFT equals official target byte-for-byte
- Added regression test:
  - [test_tft_patch.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/tests/test_tft_patch.py>)
- This proves the currently reversed fields are sufficient to generate real same-layout TFT content. The next blocker is no longer checksum; it is generating new-object tails rather than only patching same-layout files.

## Live Flash Verification: nihao -> buhao 2026-05-04

- Built a same-layout patched target:
  - target `.pa`: [0_buhao.pa](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_buhao_patch/0_buhao.pa>)
  - generated `.tft`: [lcd_test_buhao.tft](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_buhao_patch/lcd_test_buhao.tft>)
- Patch summary:
  - file size `11408156`
  - changed `t0.txt` from `nihao` to `buhao`
  - checksum recomputed to `0x7F034D2F`
  - compared with baseline: only string bytes and final checksum differ
- Uploaded to the real screen:
  - port `COM36`
  - initial baud `9600`
  - download baud `921600`
  - bytes sent `11408156`
  - chunks sent `2786`
  - elapsed `207.359s`
- Post-flash serial verification:
  - `connect` returned `TJC8048X543_011C`
  - `sendme` returned page `0`
  - `get t0.txt` returned `buhao`
  - `get dim` returned `100`
- This is the first confirmed live-screen proof that a non-official `usarthmi` generated TFT patch can be flashed and run.

## Milestone: First Non-Official TFT Patch Accepted By Screen

- Status: achieved.
- Scope proven:
  - parse official baseline HMI/TFT
  - modify page text through a generated target `0.pa`
  - patch compiled TFT text slots
  - recompute final TFT checksum
  - upload through public `whmi-wri`
  - verify runtime state over serial
- Practical meaning:
  - `usarthmi` can now generate a valid same-layout TFT patch without calling the official GUI compiler.
  - Same-layout edits such as text and coordinates are no longer only theoretical reverse-engineering results; they have been accepted by the real `TJC8048X543_011C` panel.

## Next Target: Full New-Object Object Tail Generation

- New blocker:
  - Generate the complete compiled object tail for added widgets instead of only patching existing same-layout objects.
- Immediate fixtures:
  - `case_04_add_text`
  - `case_05_add_button`
  - `case_06_add_picture`
- Required object-tail pieces to synthesize:
  - event token area growth for the extra object
  - object count and offset table changes
  - primary object records for `t1/b1/p1`
  - string pool growth with duplicate text preserved
  - value-offset table update
  - mirrored/render metadata section after TFTTool `pictures_address`
  - final TFT checksum recomputation
- Target acceptance for the next phase:
  - Generate `case_04_add_text`, `case_05_add_button`, and `case_06_add_picture` from baseline plus target `.pa`.
  - Match the official TFT outputs byte-for-byte.
  - Then flash one added-object TFT to the real screen and verify over serial.

## Current Gap

The remaining blocker is not runtime serial drawing, not font generation, and not `0.zi` replacement.

The blocker is:

`scene/HMI/font state` can be created locally, but it still cannot be compiled into a final `TFT` payload that is known-good for `TJC8048X543_011C`, then flashed and verified on the real panel.

## Recommended Next Step

Continue reverse engineering toward one of these:

1. Build a real `TFT` emitter inside `usarthmi`.
2. Or derive a reusable bridge from a known-good official `.tft` layout and patch it safely.

Until that step is complete, all screen changes remain either:
- runtime-only, or
- local `.HMI` source artifacts not yet proven as flashable screen firmware.

## Milestone: One-Object Add TFT Tail Generation 2026-05-04

- Status: achieved for the current seed and one added `t/b/p` object.
- Implemented:
  - [tft_patch.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/tft_patch.py>)
  - [cli.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/cli.py>)
  - [test_tft_patch.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/tests/test_tft_patch.py>)
- New CLI:
  - `python -m usarthmi --json tft patch-add-object --baseline-tft <baseline.tft> --baseline-pa <baseline 0.pa> --target-pa <target 0.pa> --out <out.tft>`
- Proven byte-for-byte against official fixtures:
  - `case_04_add_text`
  - `case_05_add_button`
  - `case_06_add_picture`
- Reverse facts now encoded:
  - event token area grows by one extra down/up event block sequence
  - object hash/index list is regenerated and sorted by recovered object hash
  - primary object block is rebuilt with value-offset table, records, text pointers, and duplicate text slots
  - `attr/usercode` section is rebuilt as `0x24` header plus per-object 24-byte property records
  - mirror section is rebuilt as 16-byte header plus fixed `0x8A` per-object records
  - encrypted Header2 fields, Header1/Header2 CRCs, and final TFT checksum are recomputed
- Command-line verification:
  - generated [case_04_add_text.tft](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/patch_add_object/case_04_add_text.tft>)
  - SHA256 matched the official `case_04_add_text/lcd_test.tft`
  - checksum verified as valid: `0xEA1A9568`
- Current limitation:
  - This is still a current-seed V1 path.
  - It supports adding exactly one object whose type is `t`, `b`, or `p`.
  - Object-name hashes were the next blocker at this point; the algorithm was solved in the later section below.

## Live Flash Verification: Added `t1` Object 2026-05-04

- Flashed generated file:
  - [case_04_add_text.tft](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/patch_add_object/case_04_add_text.tft>)
- Upload result:
  - port `COM36`
  - initial baud `9600`
  - download baud `921600`
  - bytes sent `11409408`
  - chunks sent `2786`
  - elapsed `208.079s`
  - log: [case_04_upload_result.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/patch_add_object/case_04_upload_result.json>)
- Post-flash serial verification:
  - `connect` returned `TJC8048X543_011C`
  - `sendme` returned page `0`
  - `get t1.txt` returned `nihao`
  - `get t1.x` returned `355`
- Meaning:
  - Added-object tail generation is accepted by the real screen.
  - The new object is not only visible in the binary; it is present in the runtime object table and queryable over serial.

## Reverse Fact: Object Name Hash Algorithm 2026-05-04

- Status: solved and encoded.
- Implemented:
  - [object_hash.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/object_hash.py>)
  - [tft_patch.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/tft_patch.py>)
  - [test_object_hash.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/tests/test_object_hash.py>)
- Algorithm:
  - encode the page/object name as ASCII
  - right-pad with `00` to 14 bytes
  - run the same non-reflected Nextion/TJC CRC32 variant used by TFTTool `NextionChecksum`
- Known values now generated by formula, no hardcoded fixture map:
  - `page0 -> 0xAC967926`
  - `t0 -> 0xC02992D9`
  - `b0 -> 0xCE1A7436`
  - `p0 -> 0x56156502`
  - `t1 -> 0xB64689A1`
  - `b1 -> 0xB8756F4E`
  - `p1 -> 0x207A7E7A`
- Evidence:
  - The earlier clue `t0^t1 == b0^b1 == p0^p1 == 0x766F1B78` matches the CRC contribution after padding to 14 bytes.
  - Local TJC `case_04_add_text` hash/index block is reconstructed and found in the official TFT.
  - Public `Gaggiuino_35/Nextion_43` HMI/TFT pair reconstructs all 20 page hash/index blocks from `.pa` object names and IDs.
- New CLI:
  - `python -m usarthmi --json tft hash-name t1`
- Test result:
  - `python -m pytest tests\test_object_hash.py -q` -> 4 passed
  - `python -m pytest tests\test_tft_patch.py -q` -> 4 passed
  - `python -m pytest -q` -> 32 passed
- Practical impact:
  - Added-object TFT generation is no longer limited to recovered names `t1/b1/p1`.
  - Arbitrary ASCII object names up to 14 bytes can now be placed into the compiled object hash/index list.
  - A regression test renames the added object to `note1` and verifies the generated TFT checksum remains valid.

## Live Flash Verification: Arbitrary Object Name `note1` 2026-05-04

- Status: achieved on the real `COM36` panel.
- Generated artifacts:
  - target page: [0_note1.pa](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_note1_patch/0_note1.pa>)
  - generated TFT: [lcd_test_note1.tft](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_note1_patch/lcd_test_note1.tft>)
  - patch/checksum record: [patch_result.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_note1_patch/patch_result.json>)
  - upload record: [upload_result.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_note1_patch/upload_result.json>)
  - runtime verification: [verify_after_upload.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_note1_patch/verify_after_upload.json>)
- Build facts:
  - added object name: `note1`
  - type: `t`
  - object id: `4`
  - generated hash: `0x2611D5E4`
  - TFT checksum valid: `0xDAEFBDE3`
- Upload facts:
  - port `COM36`
  - initial baud `9600`
  - download baud `921600`
  - bytes sent `11409408`
  - chunks sent `2786`
  - elapsed `207.656s`
- Post-flash serial verification:
  - `connect` returned `TJC8048X543_011C`
  - `sendme` returned page `0`
  - `get note1.txt` returned `note1`
  - `get note1.x` returned `355`
  - `get note1.id` returned `4`
  - `get t1.txt` returned `0x1A invalid_reference`
- Meaning:
  - The recovered object-name hash algorithm is not only byte-matching fixtures; it is accepted by the real screen runtime.
  - The compiled object lookup table now works for a new arbitrary object name, not just fixture-derived names.

## Preview Milestone: HMI/PA Page Preview 2026-05-04

- Status: implemented.
- Implemented:
  - [preview.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/preview.py>)
  - [cli.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/cli.py>)
  - [test_scene_layout.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/tests/test_scene_layout.py>)
- New CLI:
  - `python -m usarthmi --json hmi preview --hmi <file.HMI> --out preview.png`
  - `python -m usarthmi --json hmi preview-pa --pa <0.pa> --assets-dir <extract_dir> --out preview.png`
- Rendered preview artifacts:
  - [preview_note1_with_assets.png](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_note1_patch/preview_note1_with_assets.png>)
  - [preview_seed_hmi_with_assets.png](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_note1_patch/preview_seed_hmi_with_assets.png>)
- Supported in this first preview pass:
  - page background from `bco`
  - absolute coordinates from `.pa`
  - text objects
  - button objects
  - picture objects
  - number-like objects
  - yellow object-name labels similar to the official editor
  - embedded `*.i` / `*.is` JPEG/PNG picture resources from HMI/extract directories
- Current limitation:
  - This is a practical visual preview, not a pixel-perfect official renderer.
  - Font metrics and some advanced widget styles are approximate.

## Milestone: Multiple Appended Objects In One TFT 2026-05-04

- Status: achieved and live-flashed.
- Implemented:
  - [tft_patch.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/tft_patch.py>)
  - [cli.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/cli.py>)
  - [test_tft_patch.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/tests/test_tft_patch.py>)
- New behavior:
  - `patch-add-object` now accepts one or more appended `t/b/p` objects.
  - Existing baseline objects must still remain unchanged and first in the target page.
  - Target object names and IDs are validated as unique.
  - Object IDs are validated to fit the one-byte compiled record field.
- Generated artifacts:
  - target page: [0_multi.pa](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_multi_patch/0_multi.pa>)
  - preview: [preview_multi.png](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_multi_patch/preview_multi.png>)
  - generated TFT: [lcd_test_multi.tft](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_multi_patch/lcd_test_multi.tft>)
  - patch/checksum record: [patch_result.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_multi_patch/patch_result.json>)
  - upload record: [upload_result.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_multi_patch/upload_result.json>)
  - runtime verification: [verify_after_upload.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_multi_patch/verify_after_upload.json>)
- Build facts:
  - object count: `7`
  - added objects: `note1` (`t`, id `4`), `btn1` (`b`, id `5`), `pic1` (`p`, id `6`)
  - file size: `11411592`
  - TFT checksum valid: `0x62C3E6A1`
- Upload facts:
  - port `COM36`
  - initial baud `9600`
  - download baud `921600`
  - bytes sent `11411592`
  - chunks sent `2787`
  - elapsed `208.468s`
- Post-flash serial verification:
  - `connect` returned `TJC8048X543_011C`
  - `sendme` returned page `0`
  - `get note1.txt` returned `note1`
  - `get note1.id` returned `4`
  - `get note1.x` returned `355`
  - `get btn1.txt` returned `BTN1`
  - `get btn1.id` returned `5`
  - `get btn1.x` returned `192`
  - `get pic1.pic` returned `0`
  - `get pic1.id` returned `6`
  - `get pic1.x` returned `579`
- Meaning:
  - The object-tail generator now handles multiple appended compiled records, user/attribute records, mirror records, and hash entries in one build.
  - This enables the next step: generating richer menu pages from scene/HMI authoring instead of one-off object fixtures.

## Milestone: Scene Builder Routed To Multi-Object TFT Generator 2026-05-04

- Status: implemented and live-flashed.
- Implemented:
  - [editor.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/editor.py>)
  - [cli.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/cli.py>)
  - [tft_patch.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/tft_patch.py>)
  - [test_editor_tft_build.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/tests/test_editor_tft_build.py>)
- New CLI path:
  - `python -m usarthmi --json tft build --scene reverse_usarthmi\live_scene_build\scene_multi.json --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft --out reverse_usarthmi\live_scene_build`
- Generated artifacts:
  - scene: [scene_multi.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_scene_build/scene_multi.json>)
  - normalized scene: [scene.normalized.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_scene_build/scene.normalized.json>)
  - target page: [target_0.pa](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_scene_build/target_0.pa>)
  - preview: [preview_target_pa.png](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_scene_build/preview_target_pa.png>)
  - generated HMI: [output.hmi](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_scene_build/output.hmi>)
  - generated TFT: [output.tft](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_scene_build/output.tft>)
  - manifest: [manifest.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_scene_build/manifest.json>)
  - upload record: [upload_result.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_scene_build/upload_result.json>)
  - runtime verification: [verify_after_upload.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_scene_build/verify_after_upload.json>)
- Build facts:
  - object count: `7`
  - added objects: `note1` (`t`, id `4`), `btn1` (`b`, id `5`), `pic1` (`p`, id `6`)
  - file size: `11411584`
  - TFT checksum valid: `0x7734E28E`
  - object-tail padding is inserted before the final TFT checksum when the scene-generated tail is not naturally 4-byte aligned.
- Validation facts:
  - `python -m pytest tests\test_editor_tft_build.py -q` -> 2 passed
  - `python -m pytest tests\test_tft_patch.py -q` -> 5 passed, 13 subtests passed
  - `python -m pytest -q` -> 36 passed, 20 subtests passed
- Upload facts:
  - port `COM36`
  - initial baud `9600`
  - download baud `921600`
  - bytes sent `11411584`
  - chunks sent `2787`
  - elapsed `207.422s`
- Post-flash serial verification:
  - `connect` returned `TJC8048X543_011C`
  - `sendme` returned page `0`
  - `get note1.txt` returned `note1`
  - `get note1.id` returned `4`
  - `get btn1.txt` returned `BTN1`
  - `get btn1.id` returned `5`
  - `get pic1.pic` returned `0`
  - `get pic1.id` returned `6`
- Current boundary:
  - Scene-to-TFT supports appended `text/button/image` objects for the current seed layout.
  - Image widgets may reference picture IDs already present in the seed, such as `pic=0`.
  - Packing brand-new image resources into TFT is still rejected explicitly instead of producing a fake or broken file.

## Reverse Sample: Imported JPG Resource 2026-05-04

- Status: sample captured and initial layout recovered.
- User-provided case folders:
  - source JPG: [case_07_image_source_png_jpg](</C:/Users/SinYu/Desktop/case_for_codex/case_07_image_source_png_jpg>)
  - official HMI: [case_08_hmi_with_imported_image](</C:/Users/SinYu/Desktop/case_for_codex/case_08_hmi_with_imported_image>)
  - official TFT: [case_09_tft_with_imported_image](</C:/Users/SinYu/Desktop/case_for_codex/case_09_tft_with_imported_image>)
  - compare workspace: [case_11_image_resource_compare_work](</C:/Users/SinYu/Desktop/case_for_codex/case_11_image_resource_compare_work>)
- Generated compare artifacts:
  - HMI extract: [hmi_extract](</C:/Users/SinYu/Desktop/case_for_codex/case_11_image_resource_compare_work/hmi_extract>)
  - preview: [preview_hmi_with_imported_image.png](</C:/Users/SinYu/Desktop/case_for_codex/case_11_image_resource_compare_work/preview_hmi_with_imported_image.png>)
  - notes: [README_image_resource_findings.md](</C:/Users/SinYu/Desktop/case_for_codex/case_11_image_resource_compare_work/README_image_resource_findings.md>)
  - probes: [image_resource_probe.json](</C:/Users/SinYu/Desktop/case_for_codex/case_11_image_resource_compare_work/image_resource_probe.json>), [embedded_jpeg_probe.json](</C:/Users/SinYu/Desktop/case_for_codex/case_11_image_resource_compare_work/embedded_jpeg_probe.json>)
- HMI facts:
  - new entries: `1.is` (`73406` bytes) and `1.i` (`106378` bytes)
  - `1.is` is a 27-byte resource header followed by the original JPG exactly
  - `1.i` is a 44-byte compiled-resource header followed by a recompressed/padded JPG
  - `0.pa` adds object `p1`, `pic=1`, box `162,87,489,342`
- TFT facts:
  - official image TFT size: `11540132`
  - baseline TFT size: `11408156`
  - delta: `131976`
  - `pic=1` JPEG payload is at TFT offset `0x81C02`, size `106334`, dimensions `496x352`
  - the TFT payload exactly matches `1.i` after its 44-byte header, not the original JPG from `1.is`
- Layout hypothesis:
  - TFT picture resource section begins with one 24-byte index record per picture
  - each picture then has a 20-byte image block header followed by the JPEG payload
  - compiled width/height are padded to multiples of 16

## Milestone: Independent TFT Picture Resource Packer 2026-05-04

- Status: implemented and live-flashed.
- Implemented:
  - [tft_images.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/tft_images.py>)
  - [editor.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/editor.py>)
  - [test_editor_tft_build.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/tests/test_editor_tft_build.py>)
- New behavior:
  - Scene `image` widgets with `resources.asset` are assigned new sequential TFT `pic` ids after seed resources.
  - PNG/JPG inputs are padded to 16-pixel boundaries and JPEG-encoded into the TFT picture resource section.
  - Historical note: this first implementation expanded the resource area and moved the object section.
  - This was later proven different from official USART HMI output; see the 2026-05-05 fixed-region picture packer milestone below.
  - Header1 file size/resource size/resource CRC/header CRC, Header2 shifted addresses/header CRC, and final TFT checksum were recomputed.
  - The resulting resource-expanded TFT was used as the seed for the existing appended-object tail generator.
- Generated artifacts:
  - scene: [scene_image.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_pack/scene_image.json>)
  - resource seed TFT: [resource_seed.tft](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_pack/resource_seed.tft>)
  - output TFT: [output.tft](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_pack/output.tft>)
  - manifest: [manifest.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_pack/manifest.json>)
  - preview: [preview_target_pa.png](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_pack/preview_target_pa.png>)
  - upload record: [upload_result.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_pack/upload_result.json>)
  - runtime verification: [verify_after_upload.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_pack/verify_after_upload.json>)
- Build facts:
  - source image: `489x342`
  - compiled image: `496x352`
  - assigned picture id: `1`
  - added object: `photo1` (`p`, id `4`, `pic=1`, box `162,87,489,342`)
  - output TFT size: `11540132`
  - object start shifted from `0xAE0000` to `0xB00000`; this is now a superseded behavior, not the official-compatible path.
  - new JPEG payload offset: `0x81C02`
  - TFT checksum valid: `0x464E199A`
- Validation facts:
  - `python -m pytest tests\test_editor_tft_build.py -q` -> 3 passed
  - `python -m pytest tests\test_tft_patch.py -q` -> 5 passed, 13 subtests passed
  - `python -m pytest -q` -> 37 passed, 20 subtests passed
- Upload facts:
  - port `COM36`
  - initial baud `9600`
  - download baud `921600`
  - bytes sent `11540132`
  - chunks sent `2818`
  - elapsed `209.016s`
- Post-flash serial verification:
  - `connect` returned `TJC8048X543_011C`
  - `sendme` returned page `0`
  - `get photo1.pic` returned `1`
  - `get photo1.id` returned `4`
  - `get photo1.x` returned `162`
  - `get photo1.w` returned `489`
  - `get photo1.h` returned `342`
- Current boundary:
  - New image resources are proven for appended picture/image objects.
  - Generated `output.hmi` does not yet contain the added `*.i/*.is` HMI resource entries.
  - New image-button support was added in the next milestone below; it still needs official fixture comparison.

## Milestone: Inferred Multi-State Image Button TFT Path 2026-05-04

- Status: implemented and live-flashed as an inferred path.
- Implemented:
  - [editor.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/editor.py>)
  - [tft_patch.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/tft_patch.py>)
  - [tft_images.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/tft_images.py>)
  - [test_editor_tft_build.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/tests/test_editor_tft_build.py>)
- Inference:
  - Button `sta=1` exposes the two compiled background slots as `bco/bco2`.
  - Button image mode likely uses the same two compiled slots with `sta=2`.
  - The authoring layer maps `normal -> pic`, `pressed -> pic2`, but the live runtime currently reads those two compiled slots back as `bco/bco2`.
- Generated artifacts:
  - scene: [scene_image_button.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_button_pack/scene_image_button.json>)
  - resource seed TFT: [resource_seed.tft](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_button_pack/resource_seed.tft>)
  - output TFT: [output.tft](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_button_pack/output.tft>)
  - preview: [preview.png](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_button_pack/preview.png>)
  - upload record: [upload_result.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_button_pack/upload_result.json>)
  - runtime verification: [verify_after_upload.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_button_pack/verify_after_upload.json>)
  - attribute sweep: [verify_attrs_after_upload.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_button_pack/verify_attrs_after_upload.json>)
- Build facts:
  - added object: `playbtn` (`b`, id `4`, box `320,330,160,96`)
  - packed normal image: picture id `1`, source `play.png`
  - packed pressed image: picture id `2`, source `play_pressed.png`
  - output TFT size: `11540500`
  - TFT checksum valid: `0xF9CDB181`
- Validation facts:
  - `python -m pytest tests\test_editor_tft_build.py -q` -> 4 passed
  - `python -m pytest tests\test_tft_patch.py -q` -> 5 passed, 13 subtests passed
  - `python -m pytest -q` -> 39 passed, 20 subtests passed
- Upload facts:
  - port `COM36`
  - initial baud `9600`
  - download baud `921600`
  - bytes sent `11540500`
  - chunks sent `2818`
  - elapsed `213.579s`
- Post-flash serial verification:
  - `connect` returned `TJC8048X543_011C`
  - `sendme` returned page `0`
  - `get playbtn.id` returned `4`
  - `get playbtn.sta` returned `2`
  - `get playbtn.x` returned `320`
  - `get playbtn.w` returned `160`
  - `get playbtn.h` returned `96`
  - `get playbtn.txt` returned `PLAY`
  - `get playbtn.bco` returned `1`
  - `get playbtn.bco2` returned `2`
  - `get playbtn.pic`, `get playbtn.pic2`, `get playbtn.picc`, and `get playbtn.picc2` returned `0x1A`
  - `click playbtn down/up` sent successfully with no error response
- Current boundary:
  - The screen runtime accepts the generated object and two packed image IDs.
  - Manual visual confirmation is still needed to decide whether this is fully correct for the pressed-state image.
  - An official image-button fixture should still be captured later to verify the exact HMI/TFT byte layout.

## Milestone: Clean Seed Objects Mode 2026-05-04

- Status: implemented and live-flashed.
- Purpose:
  - The current TFT writer still keeps the seed page's original `t0/b0/p0` records for compatibility.
  - `project.clean_seed_objects=true` moves those seed objects offscreen instead of deleting them, so the generated scene is visually clean while the current seed-based tail compiler remains safe.
- Implemented:
  - [editor.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/editor.py>)
  - [test_editor_tft_build.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/tests/test_editor_tft_build.py>)
  - [scene_image_button.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_button_pack/scene_image_button.json>)
- Generated artifacts:
  - clean build directory: [live_image_button_pack_clean](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_button_pack_clean>)
  - output TFT: [output.tft](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_button_pack_clean/output.tft>)
  - upload record: [upload_result.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_button_pack_clean/upload_result.json>)
  - runtime verification: [verify_after_upload.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_button_pack_clean/verify_after_upload.json>)
- Build facts:
  - output TFT size: `11540500`
  - TFT checksum valid: `0x366E46B0`
  - old seed objects are retained but moved to `x=832,y=512,w=1,h=1`
  - `playbtn` remains at `x=320,y=330,w=160,h=96`
- Upload facts:
  - port `COM36`
  - initial baud `9600`
  - download baud `921600`
  - bytes sent `11540500`
  - chunks sent `2818`
  - elapsed `213.672s`
- Post-flash serial verification:
  - `sendme` returned page `0`
  - `get t0.x/y/w/h` returned `832/512/1/1`
  - `get b0.x/y/w/h` returned `832/512/1/1`
  - `get p0.x/y/w/h` returned `832/512/1/1`
  - `get playbtn.x/y/w/h` returned `320/330/160/96`
  - `get playbtn.sta` returned `2`
  - `get playbtn.bco` returned `1`
  - `get playbtn.bco2` returned `2`
- Current boundary:
  - This is a safe visual clean mode, not true object deletion.
  - A later full-page compiler should support deleting seed objects entirely.

## Milestone: Custom TFT Font Replacement 2026-05-04

- Status: implemented and live-flashed.
- Implemented:
  - [tft_fonts.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/tft_fonts.py>)
  - [cli.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/cli.py>)
  - [test_tft_fonts.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/tests/test_tft_fonts.py>)
- New CLI:
  - `python -m usarthmi --json tft patch-font --baseline-tft <input.tft> --font <custom.zi> --out <output.tft>`
- Safe strategy:
  - Locate the first embedded `.zi` magic inside the TFT resource area.
  - Replace it in place with a same-or-smaller generated `.zi`.
  - Zero-fill the remaining old font span.
  - Preserve TFT file size and all Header2 section addresses.
  - Recompute resource CRC, Header1 CRC, and final TFT checksum.
- Generated artifacts:
  - scene: [scene_custom_font.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_custom_font/scene_custom_font.json>)
  - generated font: [Hupo48ASCII.zi](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_custom_font/Hupo48ASCII.zi>)
  - base build: [build_base](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_custom_font/build_base>)
  - final TFT: [output_custom_font.tft](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_custom_font/output_custom_font.tft>)
  - upload record: [upload_result.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_custom_font/upload_result.json>)
  - runtime verification: [verify_after_upload.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_custom_font/verify_after_upload.json>)
- Font facts:
  - source font file: `C:\Windows\Fonts\STHUPO.TTF`
  - generated `.zi` name: `Hupo48ASCII`
  - codepage: `utf-8`
  - char height: `48`
  - char count: `95`
  - generated `.zi` size: `14681`
  - replaced TFT font span: `0x84429..0xAD207D`, old span `10804308`
- Build facts:
  - visible text object: `fontmsg`, text `FONT TEST 123`, font `0`
  - image button remains `playbtn`
  - clean seed objects remain offscreen
  - final TFT size: `11541756`
  - final TFT checksum valid: `0x9AFAC92B`
- Upload facts:
  - port `COM36`
  - initial baud `9600`
  - download baud `921600`
  - bytes sent `11541756`
  - chunks sent `2818`
  - elapsed `214.343s`
- Post-flash serial verification:
  - `sendme` returned page `0`
  - `get fontmsg.id` returned `4`
  - `get fontmsg.txt` returned `FONT TEST 123`
  - `get fontmsg.x/y/w/h` returned `120/96/560/88`
  - `get fontmsg.font` returned `0`
  - `get playbtn.id` returned `5`
  - `get playbtn.sta` returned `2`
  - `get playbtn.bco/bco2` returned `1/2`
  - `get t0.x`, `get b0.x`, and `get p0.x` returned `832`, confirming clean mode remains active.
- Current boundary:
  - Serial object lookup validated the custom-font TFT structure, but the photographed panel did not visibly show `FONT TEST 123`; only the `PLAY` button and a small black artifact were visible.
  - The custom `.zi` replacement path is therefore not visually proven yet.
  - Follow-up diagnosis should separate text-object compilation from `.zi` resource compatibility.
  - Larger font resources still need the resource-shifting path.
  - The current TFT text compiler still emits ASCII text bytes; Chinese text in TFT string pools remains a separate follow-up.

## Milestone: Original-Font Text Object Diagnostic 2026-05-04

- Status: implemented and live-flashed.
- Purpose:
  - Verify the generated text object itself using the stock embedded font, before changing the `.zi` resource.
  - Avoid confusing text object record bugs with custom font rendering bugs.
- Implemented:
  - [tft_patch.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/tft_patch.py>) now patches text-object primary record metadata for `t` objects.
  - [test_editor_tft_build.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/tests/test_editor_tft_build.py>) now verifies generated text records keep `style=1` and `txt_maxl=13` for `FONT TEST 123`.
- Text record fields now patched for `t` objects:
  - `sta`
  - `style`
  - `borderc`
  - `font`
  - solid/image background slot
  - `pco`
  - `xcen`
  - `ycen`
  - `pw`
  - `txt_maxl`
- Important note:
  - The byte that looked like `borderw` is intentionally left as the official template value; exact official TFT reproduction showed that USART HMI 1.67.6 leaves it zero in the primary record.
- Generated artifacts:
  - scene: [scene_original_font_text.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_original_font_text/scene_original_font_text.json>)
  - build directory: [live_original_font_text/build](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_original_font_text/build>)
  - preview: [preview.png](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_original_font_text/build/preview.png>)
  - output TFT: [output.tft](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_original_font_text/build/output.tft>)
  - upload record: [upload_result.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_original_font_text/build/upload_result.json>)
  - runtime verification: [verify_after_upload.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_original_font_text/build/verify_after_upload.json>)
- Build facts:
  - `fontmsg` uses stock font id `0`.
  - `fontmsg` is at `x=80,y=70,w=640,h=120`.
  - `fontmsg.txt` is `FONT TEST 123`.
  - `fontmsg.bco` is `65504`, a yellow diagnostic background.
  - output TFT size: `11541756`
  - TFT checksum valid: `0x11B0BBBB`
- Upload facts:
  - port `COM36`
  - initial baud `9600`
  - download baud `921600`
  - bytes sent `11541756`
  - chunks sent `2818`
  - elapsed `212.922s`
- Post-flash serial verification:
  - `sendme` returned page `0`
  - `get fontmsg.txt` returned `FONT TEST 123`
  - `get fontmsg.txt_maxl` returned `13`
  - `get fontmsg.bco` returned `65504`
  - `get fontmsg.pco` returned `0`
  - `get fontmsg.style` returned `1`
  - `get fontmsg.font` returned `0`
  - `get fontmsg.x/y` returned `80/70`
  - `get playbtn.bco/bco2` returned `1/2`

## Milestone: Official Cases 12-15 Text/Image References 2026-05-05

- Status: captured and analyzed.
- User supplied official USART HMI GUI outputs under:
  - [case_12_text_yellow_font0](</C:/Users/SinYu/Desktop/case_for_codex/case_12_text_yellow_font0>)
  - [case_13_image_button_only](</C:/Users/SinYu/Desktop/case_for_codex/case_13_image_button_only>)
  - [case_14_text_plus_image_button](</C:/Users/SinYu/Desktop/case_for_codex/case_14_text_plus_image_button>)
  - [case_15_text_after_import_images](</C:/Users/SinYu/Desktop/case_for_codex/case_15_text_after_import_images>)
- Visual facts from official screenshots:
  - `case_12` displays yellow `fontmsg` text with `newtxt`.
  - `case_13` displays the two-state `playbtn`.
  - `case_14` displays both `fontmsg` and `playbtn` together.
- Parsed `.pa` facts:
  - Official `fontmsg` uses `style=0`, not `style=1`.
  - Official `fontmsg` keeps `txt_maxl=10`.
  - Official `fontmsg.txt` is `newtxt`.
  - Official `fontmsg.bco=65504`, `pco=0`, `font=0`.
  - Official `playbtn` uses `sta=2`, `style=4`, `pic=1`, `pic2=2`.
- Compiler fix:
  - [editor.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/editor.py>) now prefers the current seed page's own `t0`/`b0` as text/button prototypes instead of keyboard template widgets.
  - Short text now preserves the seed/default `txt_maxl=10` instead of shrinking it to the exact text length.
- Verification:
  - A scene containing only `fontmsg` with `newtxt` now builds an `output.tft` that is byte-for-byte identical to official `case_12` `lcd_test.tft`.
  - Test added in [test_editor_tft_build.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/tests/test_editor_tft_build.py>).
  - Validation command passed: `7 passed, 13 subtests passed`.
- New resource-pack insight:
  - Official image cases keep `unknown_objects_address=0xAE0000`.
  - Official image cases keep Header1 `ressource_files_size=11272192`.
  - Official image import shifts `fonts_address` from `0xACF82A` to `0xAD164B`.
  - Our earlier image packer moved the object section to `0xB00000`; this is now known to be the wrong direction for matching official output.

## Milestone: Fixed-Region Picture Packer + Live PLAY/newtxt Flash 2026-05-05

- Status: implemented, tested, and live-flashed.
- Core correction:
  - [tft_images.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/tft_images.py>) no longer expands the TFT resource section for new pictures.
  - Header1 `ressource_files_size` remains fixed at `0xAC0000`.
  - Header2 `unknown_objects_address` remains fixed at `0xAE0000`.
  - New picture bytes are inserted inside the fixed resource area and consume trailing `00/FF` padding before the object section.
  - If a picture would overwrite non-padding resource bytes, the packer errors instead of silently corrupting fonts or code.
- Image-size behavior:
  - Default JPEG quality is now `85`, close to the official PLAY image block sizes and smaller than the earlier `95` default.
  - If fixed resource padding is insufficient, the packer lowers JPEG quality and then downscales proportionally as a safety fallback.
  - The large cat/photo test image now fits the fixed resource budget without moving the object section.
- Regression tests:
  - `test_scene_build_packs_new_picture_resource` now asserts `new_object_start == old_object_start`.
  - `test_scene_build_packs_image_button_states` now asserts `new_object_start == old_object_start`.
  - Full relevant command passed: `python -m pytest tests\test_editor_tft_build.py tests\test_tft_patch.py tests\test_tft_fonts.py tests\test_tft_download.py -q`
  - Result: `16 passed, 13 subtests passed`.
- Generated live sample:
  - scene: [scene.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_fixed_image_text/scene.json>)
  - output TFT: [output.tft](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_fixed_image_text/build/output.tft>)
  - preview: [preview.png](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_fixed_image_text/preview.png>)
  - camera capture after flash: [after_upload.jpg](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_fixed_image_text/camera/after_upload.jpg>)
- Build facts:
  - `playbtn` is an image-style button at `x=320,y=300,w=160,h=96`.
  - `playbtn.txt` is `PLAY`.
  - `fontmsg` is a yellow stock-font text object at `x=80,y=70,w=640,h=120`.
  - `fontmsg.txt` is `newtxt`.
  - packed picture ids: normal `1`, pressed `2`.
  - `inserted_bytes=7433`, `trimmed_resource_tail_bytes=7433`.
  - final TFT checksum valid: `0x65A47AE0`.
- Upload facts:
  - port `COM36`
  - initial baud `9600`
  - download baud `921600`
  - bytes sent `11410688`
  - chunks sent `2786`
  - elapsed `210.156s`
- Post-flash verification:
  - camera showed the expected yellow text area and blue PLAY button area.
  - `sendme` returned page `0`.
  - `get fontmsg.txt` returned `newtxt`.
  - `get playbtn.txt` returned `PLAY`.
  - `click playbtn,1` sent successfully with no error response.
  - `get playbtn.pic` returned `1A`; this looks like a screen-side unreadable/invalid runtime property for the image slot, not an object lookup failure.
- Current boundary:
  - Text and image-button objects are live and queryable by name.
  - Picture resources now follow the official fixed-object-start layout.
  - Exact byte-for-byte reproduction of official `case_14` is not claimed yet; our JPEG encoder output differs slightly from the official editor's image blocks.

## Milestone: Official Image-Button Object Tail Layout Matched 2026-05-05

- Status: implemented and regression-tested.
- Official fixtures used:
  - [case_13_image_button_only](</C:/Users/SinYu/Desktop/case_for_codex/case_13_image_button_only>)
  - [case_14_text_plus_image_button](</C:/Users/SinYu/Desktop/case_for_codex/case_14_text_plus_image_button>)
- Recovered image-button layout rules:
  - Full-image buttons use `sta=2`, with `pic` as normal state and `pic2` as pressed state.
  - When any full-image button exists, the object-tail prefix switches to an image-button variant.
  - The image-button prefix inserts fixed bytes `92 48 C9 76` at offset `0x86` and adjusts two internal length/offset fields by `+4`.
  - Page event layout gains one extra empty event block before the normal event sequence.
  - Mirror records expand from `0x8A` to `0x8C` bytes.
  - Mirror/user records use the official full-image-button slot layout, including the recovered `pic/pic2` user-record metadata.
  - Image-button tail padding before the final checksum word is `FF FF`, not `00 00`.
- Implemented in:
  - [tft_patch.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/tft_patch.py>)
  - [test_editor_tft_build.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/tests/test_editor_tft_build.py>)
- Verification:
  - Generated `case13`-equivalent TFT now has official size `11409424`, object region `0x153E`, compiled tail `0x1810`.
  - Generated `case14`-equivalent TFT now has official size `11410680`, object region `0x199A`, compiled tail `0x1CF8`.
  - From `unknown_objects_address` to the final 4-byte TFT checksum word, generated `case13/case14` tails are byte-for-byte identical to official outputs.
  - Full test suite passed: `44 passed, 22 subtests passed`.

## Milestone: Official PLAY Picture Encoder Matched 2026-05-05

- Status: implemented and regression-tested.
- Recovered picture encoder parameters:
  - JPEG `quality=96`
  - JPEG `subsampling=2` / 4:2:0
  - JFIF density/DPI `96x96`
  - `optimize=False`
  - `progressive=False`
  - 16-pixel aligned black padding remains correct.
- Header/resource correction:
  - Header2 field at offset `0x30`, labeled `pages_count` by TFTTool, is updated to `(picture_region_end & 0xFFFF)` after packing picture resources.
  - Header2 field at offset `0x34`, labeled `pictures_count` by TFTTool, increases by `+4` for the recovered full-image-button object-tail layout.
- Implemented in:
  - [tft_images.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/tft_images.py>)
  - [tft_patch.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/tft_patch.py>)
  - [test_editor_tft_build.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/tests/test_editor_tft_build.py>)
- Verification:
  - Compiled `1.i` / `2.i` JPEG payloads for the PLAY normal/pressed images now match official case image payloads byte-for-byte.
  - Scene-generated `case13` TFT now matches official [case_13_image_button_only/lcd_test.tft](</C:/Users/SinYu/Desktop/case_for_codex/case_13_image_button_only/lcd_test.tft>) byte-for-byte.
  - Scene-generated `case14` TFT now matches official [case_14_text_plus_image_button/lcd_test.tft](</C:/Users/SinYu/Desktop/case_for_codex/case_14_text_plus_image_button/lcd_test.tft>) byte-for-byte.
  - Full test suite passed again: `44 passed, 22 subtests passed`.

## Milestone: HMI Picture Resource Writeback 2026-05-05

- Status: implemented and regression-tested.
- Core behavior:
  - `build_scene` now assigns picture IDs before HMI writing, even when only `output.hmi` is requested.
  - The HMI writer rebuilds the container directory instead of patching only one entry in-place.
  - Existing seed resources are preserved.
  - `0.pa` is rewritten with the generated page/object table.
  - Referenced image assets are added as resource pairs:
    - `N.i`: official-style JPEG screen resource entry.
    - `N.is`: official-style source image entry containing the original `png` / `jpg` bytes.
- Implemented in:
  - [editor.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/editor.py>)
  - [tft_images.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/tft_images.py>)
  - [test_editor_tft_build.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/tests/test_editor_tft_build.py>)
- Verification:
  - Scene-generated `output.hmi` for the PLAY image-button fixture contains `1.is`, `2.is`, `1.i`, and `2.i`.
  - Generated `1.is`, `2.is`, `1.i`, and `2.i` match the official [case_14_text_plus_image_button](</C:/Users/SinYu/Desktop/case_for_codex/case_14_text_plus_image_button>) extracted resources byte-for-byte.
  - Full test suite passed: `45 passed, 22 subtests passed`.
- Remaining boundary:
  - This proves HMI resource payload writeback for the current single-page PLAY image-button fixtures.
  - The generated HMI container is structurally valid and inspectable, but broad official-editor round-trip editing still needs more fixtures and manual open/save checks.

## Milestone: Picture Source Edge Cases Hardened 2026-05-05

- Status: implemented and regression-tested.
- Core behavior:
  - PNG/JPG picture loading now applies EXIF orientation before compiling.
  - Transparent PNGs are flattened onto a black RGB background before TFT JPEG encoding, matching the current no-alpha screen resource path.
  - JPG/JPEG source resources in HMI `.is` entries keep the original source payload and use the normalized `jpg` tag.
  - Non-16-aligned images are still stored as 16-pixel padded JPEG dimensions while keeping logical width/height in the resource records.
  - Large/high-entropy images can reduce JPEG quality and then scale down until they fit a caller-provided fixed resource budget.
  - The legacy Pillow `getdata()` warning in RGB565 asset normalization was removed by switching to byte iteration.
- Implemented in:
  - [tft_images.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/tft_images.py>)
  - [editor.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/usarthmi/editor.py>)
  - [test_tft_images.py](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/tests/test_tft_images.py>)
- Verification:
  - Added source-independent tests for transparent PNG flattening, JPG `.is` source payload/tag preservation, 16-pixel padding, and shrink-to-budget behavior.
  - Full test suite passed: `48 passed, 22 subtests passed`.
- Remaining boundary:
  - These are local synthetic edge cases; more official-editor fixtures are still useful for unusual PNG compression modes, palette/transparency combinations, and real-world large photos.

## Milestone: Mixed JPG/PNG/Image-Button Live Stress Scene 2026-05-05

- Status: implemented, flashed, and visually checked.
- Scene/artifacts:
  - [scene.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_stress/scene.json>)
  - [output.hmi](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_stress/build/output.hmi>)
  - [output.tft](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_stress/build/output.tft>)
  - [after_upload_sorted_resources_cam1.jpg](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_image_stress/captures/after_upload_sorted_resources_cam1.jpg>)
- What this scene covers:
  - generated JPG picture resource (`photo1.pic=2`)
  - generated transparent PNG picture resource (`badge1.pic=1`)
  - two-state image button (`playbtn.sta=2`, normal/pressed resources `3/4`)
  - generated text objects (`title`, `valtxt`, `subtxt`)
  - cleaned seed objects moved offscreen
- Bug found:
  - The first flashed build displayed the transparent PNG in `photo1` and the JPG in `badge1`, even though serial reads returned `photo1.pic=2` and `badge1.pic=1`.
  - Root cause: TFT picture records were emitted in asset insertion order. The live panel appears to resolve picture resources by resource table order, not only by the record's embedded `picture_id` field.
- Fix:
  - `pack_picture_resources_into_tft` now sorts new picture resources by `picture_id` before writing the TFT picture table.
  - Added a regression test that declares assets out of order and verifies the TFT picture table is ordered as `0,1,2`.
- Verification:
  - Full suite passed after the fix: `49 passed, 22 subtests passed`.
  - Rebuilt and re-uploaded the fixed TFT to `COM36`.
  - Serial readback after upload:
    - `sendme -> 0`
    - `get photo1.pic -> 2`
    - `get badge1.pic -> 1`
    - `get playbtn.sta -> 2`
    - `get title.txt -> IMG STRESS OK`
    - `get subtxt.txt -> jpg + transparent png + image button`
  - Camera capture confirmed the visual order: JPG card on the left, transparent PNG badge in the middle, PLAY button on the right.
- Remaining boundary:
  - `number` widgets are still not supported by the TFT tail compiler; attempting to include `n0` correctly failed with `type '4'`, so the live stress scene used a text-based value display (`valtxt`) instead.

## Milestone: Custom Font Recognition Confirmed 2026-05-05

- Status: implemented, flashed, and visually confirmed.
- Scene/artifacts:
  - [scene.json](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_font_recognition/scene.json>)
  - [Impact56ASCII_ordered.zi](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_font_recognition/Impact56ASCII_ordered.zi>)
  - [output_impact_ordered.tft](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_font_recognition/build_impact_ordered/output_impact_ordered.tft>)
  - [font_stock_cam1.jpg](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_font_recognition/captures/font_stock_cam1.jpg>)
  - [font_impact_ordered_cam1.jpg](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_font_recognition/captures/font_impact_ordered_cam1.jpg>)
- What was tested:
  - Stock font test scene with three large text objects was flashed first for a visual baseline.
  - `Impact56ASCII.zi` using UTF-8/codepage `0x18` was generated and patched into the TFT; the panel loaded the new glyph shapes, but text rendered mostly as repeated `F`.
  - `Impact56ASCII_codepage_ascii.zi` using ASCII/codepage `0x01` was generated and patched; the panel loaded the glyph shapes, but characters were still scrambled.
  - Root cause was found in `tools/ZiCli/Program.cs`: glyphs were collected in a `HashSet`, so the generated `.zi` glyph order was not codepage order.
- Fix:
  - `ZiCli` now stores requested codepoints as integers and emits glyphs ordered by `CodePage.CodePoints`, with any extra codepoints appended sorted numerically.
  - This makes ASCII `.zi` glyph order match the panel's codepage-index lookup.
- Verification:
  - Rebuilt `ZiCli`.
  - Generated `Impact56ASCII_ordered.zi`: codepage `ascii`, version `5`, height `56`, 95 characters, size `18464` bytes.
  - Patched it into [build_stock/output.tft](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_font_recognition/build_stock/output.tft>) with `tft patch-font`.
  - Uploaded [output_impact_ordered.tft](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/live_font_recognition/build_impact_ordered/output_impact_ordered.tft>) to `COM36`.
  - Serial readback after upload:
    - `sendme -> 0`
    - `get fonta.txt -> FONT TEST 123`
    - `get fonta.font -> 0`
    - `get fontb.txt -> WIDE III 888`
    - `get fontc.txt -> IMPACT FONT CHECK`
  - Camera capture confirmed correct text and visually different Impact-style glyphs on the real panel.
  - Full Python test suite passed: `49 passed, 22 subtests passed`.
- Current conclusion:
  - The panel recognizes our custom font resource when the `.zi` is codepage-ordered.
  - Ordered ASCII small fonts are now a working baseline path.
- Remaining boundary:
  - Small GB2312/Chinese baseline fonts still need the same live verification.
  - The current safe TFT font patch still replaces only the first embedded `.zi` in-place and requires the replacement to fit inside the original font span.

## Probe: Event/Logic Bytecode Still Not Scheduled 2026-05-05

- Status: partially implemented, live-probed, not solved yet.
- Implemented pieces:
  - Page `codesloadend-` is now preserved in parsed `.pa` files and accepted by scene validation.
  - The minimal event compiler now emits `vis obj,state` as `09 05 04 + ASCII payload`.
  - Page event blocks can include the official `09 30 08` load/loadend separator observed in external Nextion TFT samples.
  - Regression tests cover `loadend`, `vis`, `printh`, `click`, and `rawhex` event block construction.
- Live probe:
  - Built [output.tft](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/event_logic_probe/build_load_probe_current/output.tft>) with page `load` code:
    - `printh 23 02 50 02`
    - `vis evtbtn,0`
  - Uploaded it to `COM36`; upload completed successfully:
    - size `11409472`
    - sent `11409472`
    - elapsed `210.391s`
  - Serial read immediately after boot and after `page 0` returned no `23 02 50 02` signature.
  - Runtime sanity check still worked: `get evtbtn.x -> 300`.
  - Camera capture [build_load_probe_current_cam.jpg](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/event_logic_probe/build_load_probe_current_cam.jpg>) showed `EVENT TEST` was still visible, so the compiled `vis evtbtn,0` did not execute.
- Current conclusion:
  - The command opcode itself is not the problem; runtime `vis evtbtn,0` hides the object correctly.
  - The object exists and is addressable; serial `get evtbtn.x` works.
  - The compiled event byte blocks are present in the TFT object tail, but the panel does not schedule them.
  - The missing piece is likely an additional event entry/index/flag outside the obvious event byte stream, or a TJC-specific event directory not yet regenerated.
- Official loader probe:
  - Added [RunOfficialInit.cs](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/tools/RunOfficialInit.cs>) to try listing official dynamically loaded assemblies; direct invocation currently hits `StackOverflowException`.
  - Updated [DecodeAppDllPass.cs](</C:/Users/SinYu/Documents/Codex/2026-05-03/files-mentioned-by-the-user-delay/reverse_usarthmi/tools/DecodeAppDllPass.cs>) so `AppDllPass_Decode` receives a fourth key-buffer pointer instead of null.
  - Simple key modes (`zero`, `ff`, `magic`) still did not decode `ACTR.dll` into a valid PE, so the official compiler internals are not opened yet.
- Verification:
  - Focused tests passed after the event compiler changes: `20 passed, 16 subtests passed`.
- Next best evidence needed:
  - A true official TJC 1.67.6 TFT compiled from the same seed with one simple event such as page-load `printh 23 02 50 02` or button-down `vis evtbtn,0`.
  - With that fixture, the remaining event scheduling fields should be diffable instead of guessed.

## Finding: Offline TJC Wiki Integrated As Fixture Source 2026-05-07

- Source received from the user:
  - `C:\Users\SinYu\Desktop\tjcwiki`
- High-value pages found:
  - `advanced\hmi_download_protocol.html`
  - `advanced\download_protocol\python_code.html`
  - `start\ide_introduce\ide_introduce8.html`
  - `widgets\Page.html`
- Download protocol conclusion:
  - The public protocol is still full-stream only:
    - optional active-parse exit + `connect`
    - `whmi-wri filesize,baud,0`
    - switch to forced download baud
    - wait for single-byte `0x05`
    - stream every TFT byte in 4096-byte chunks
    - wait for single-byte `0x05` after each chunk
  - The official public Python downloader source was saved locally under:
    - `external\tjcwiki_download_protocol\official_tftdownloader.py`
  - That source also contains no sparse/differential write command. The editor's "same part not downloaded/written" behavior is not exposed in the public downloader.
- Official HMI samples downloaded as ignored local fixtures:
  - `external\tjcwiki_samples\command_printh.HMI`
  - `external\tjcwiki_samples\command_vis.HMI`
  - `external\tjcwiki_samples\command_click.HMI`
  - `external\tjcwiki_samples\command_page.HMI`
  - `external\tjcwiki_samples\command_sendme.HMI`
- Tooling improvement:
  - `inspect-hmi` now reports structured `0.pa` block summaries in addition to raw string runs:
    - object/page `objname`
    - `type_code`
    - useful numeric fields such as `id/x/y/w/h/pic/font/bco/pco`
    - grouped event scripts parsed from `codesload-*`, `codesloadend-*`, `codesdown-*`, `codesup-*`, `codesunload-*`, and `codestimer-*`
  - `page_format` now decodes event tokens with ASCII/UTF-8/GBK fallback and serializes non-ASCII event comments with GBK when needed.
- Official sample evidence extracted:
  - `command_vis.HMI`:
    - `b0.codesdown-1 -> vis t0,0`
    - `b1.codesdown-1 -> vis t0,1`
  - `command_printh.HMI`:
    - `b0.codesdown-3 -> //printh ... printh ff ff ff`
    - `b1.codesdown-3 -> //printh ... printh 0d 0a`
  - `command_click.HMI`:
    - `page0.codesload-2 -> //用click去触发触摸热区,类似于调用函数 | click getTime,1`
    - `tm0.codestimer-2 -> //用click去触发触摸热区,类似于调用函数 | click getTime,1`
    - `getTime.codesdown-29 -> RTC copy and weekday if/else script`
- Updated conclusion:
  - The HMI event field names and event text structure match our authoring layer.
  - The live failure is therefore more likely in the TFT-side event registration/scheduling table, not in HMI event text naming.
  - The next best fixture is still an official TJC 1.67.6 TFT compiled from a tiny event-bearing HMI for the same model/seed; the wiki samples help parse source-side events, but they do not provide compiled TFT output.
- Verification:
  - Full Python test suite passed after the parser changes: `59 passed, 25 subtests passed`.

## Finding: Official Cases 17-21 Added 2026-05-11

- Source received from the user:
  - `C:\Users\SinYu\Desktop\case_for_codex\case_17_slider`
  - `C:\Users\SinYu\Desktop\case_for_codex\case_18_gauge`
  - `C:\Users\SinYu\Desktop\case_for_codex\case_19_timer`
  - `C:\Users\SinYu\Desktop\case_for_codex\case_20_progress`
  - `C:\Users\SinYu\Desktop\case_for_codex\case_21_qrcode`
- Each case contains:
  - `lcd_test.HMI`
  - `lcd_test.tft`
  - `screenshot.png`
- Visual contact sheet generated at:
  - `reverse_usarthmi\case17_21_contact.png`
- Structured compare output generated at:
  - `reverse_usarthmi\case17_21_compare_cleanbaseline\summary.json`
  - `reverse_usarthmi\case17_21_compare_cleanbaseline\case_*\reverse_tail.json`
  - Note: `C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.HMI` was later found to be dirty/mismatched against its TFT, so the clean compare uses `D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI` plus `official_lcd_test_TJC8048X543_011_20260504.tft` as the baseline.
- New HMI object facts:
  - `case_17_slider`: `slider1`, type code `0x01`, fields include `mode/psta/wid/hig/dis/pic/picc/bco/pic1/picc1/bco1/pic2/pco/val/maxval/minval/ch`, events include `codesslide-0`.
  - `case_18_gauge`: `gauge1`, type code `z`, fields include `sta/pic/picc/bco/pco/pco2/val/format/up/down/left/hig/wid/vvs0/vvs1/vvs2`.
  - `case_19_timer`: `tm0`, type code `3`, fields include `tim/en`, event `codestimer-0`.
  - `case_20_progress`: `bar1`, type code `j`, fields include `sta/dez/val/dis/bco/bpic/pco/ppic`.
  - `case_21_qrcode`: `qr1`, type code `:`, fields include `sta/dis/bco/pco/pic/txt/txt_maxl`.
- TFT reverse summary:
  - Existing reverse logic can locate compiled object records for slider, gauge, progress, and QR code.
  - Timer has no normal coordinate/object body match because it is a non-visual object; it needs separate handling in any future compiled-object model.
  - QR code text pointer follows the same pointer+bias pattern as text-like objects (`body+0x28`, bias `0x1EF` in this fixture).
- Tooling updates from these cases:
  - `page_format.EVENT_PREFIXES` now includes `codesslide-`.
  - Scene event validation and HMI event writing now accept `slide` and `timer`.
  - `inspect-hmi` summaries now expose additional fields used by slider/gauge/timer/progress/QR objects.
- Verification:
  - Focused tests passed: `13 passed`.
  - Full Python test suite passed after these updates: `60 passed, 25 subtests passed`.

## Finding: Experimental Extra Visual Controls TFT 2026-05-11

- Goal:
  - Try the remaining official visual controls from `case_17` through `case_21` in one independently generated TFT, without using the official GUI compiler.
- Implemented generator changes:
  - Added compiled record support for:
    - slider: type `0x01`, primary record length `0x58`, user slots `40`.
    - gauge: type `z`, primary record length `0x54`, user slots `40`.
    - progress bar: type `j`, primary record length `0x44`, user slots `33`.
    - QR code: type `:`, primary record length `0x4C`, user slots `33`, text pointer at primary record offset `0x44`.
  - Added a dynamic object-hash block scanner because slider adds a `slide` event block, so fixed hash-block offsets are no longer safe.
  - Added optional local template loading from `C:\Users\SinYu\Desktop\case_for_codex\case_17_slider`, `case_18_gauge`, `case_20_progress`, and `case_21_qrcode`.
- Generated artifacts:
  - `reverse_usarthmi\extra_controls_demo\target_0.pa`
  - `reverse_usarthmi\extra_controls_demo\output.tft`
  - `reverse_usarthmi\extra_controls_demo\preview.png`
  - `reverse_usarthmi\extra_controls_demo\after_upload.jpg`
  - `reverse_usarthmi\extra_controls_demo\after_runtime_set.jpg`
- Flash result:
  - Uploaded `reverse_usarthmi\extra_controls_demo\output.tft` to `COM36`.
  - File size: `11,415,284` bytes.
  - Upload chunks: `2787`.
  - Elapsed upload time: `209.469s`.
- Live-screen visual result:
  - The panel visibly rendered:
    - title text `EXTRA CONTROLS`
    - slider
    - progress bar
    - gauge needle
    - QR code
    - status text `slider / progress / gauge / qrcode`
- Live runtime query result:
  - `connect` returned `TJC8048X543_011C`.
  - `sendme` returned page `0`.
  - `get title.txt` returned `EXTRA CONTROLS`.
  - `sld1.val=80` succeeded and `get sld1.val` returned `80`.
  - `bar1.val=85` returned code `0x1C`; `get bar1.val` still returned `0`.
  - `get gauge1.val` returned invalid reference `0x1A`.
  - `get qr1.txt` returned invalid reference `0x1A`.
- Current interpretation:
  - Slider is now promoted to "display + runtime value works" for this seed path.
  - Progress/gauge/QR are "display works, runtime property table/user-record mapping still incomplete".
  - Timer remains excluded from the combined TFT because it is non-visual and does not follow the normal coordinate object body.

## Finding: Extra Visual Controls Runtime Tail Fix 2026-05-11

- 中文结论：
  - `slider / gauge / progress / qrcode` 单类型新增对象链路已经打通。
  - 这几个控件不能只补 primary record；还必须同步补：
    - extra 控件真实 primary record 长度。
    - 官方 prefix 插入片段。
    - Header2 中随 prefix 插入增长的加密字段。
    - 对应布局的完整 mirror record 宽度与中间插槽位置。
- 已修正的记录长度：
  - slider `0x01`: primary `0x54`, user slots `40`.
  - gauge `z`: primary `0x50`, user slots `40`.
  - progress `j`: primary `0x40`, user slots `33`.
  - qrcode `:`: primary `0x48`, user slots `33`.
- 官方复刻结果：
  - `case_18_gauge` 生成 TFT 与官方 TFT byte-for-byte 一致。
  - `case_20_progress` 生成 TFT 与官方 TFT byte-for-byte 一致。
  - `case_21_qrcode` 生成 TFT 只剩尾部极小差异，但真机运行时验证通过。
  - `case_17_slider` 还有尾部后段差异，但真机运行时验证通过。
- 真机验证：
  - Generated progress TFT:
    - `sendme` returned page `0`.
    - `get bar1.val` returned `60`.
    - `bar1.val=85` succeeded.
    - `get bar1.val` returned `85`.
    - `get bar1.x` returned `80`.
  - Generated gauge TFT:
    - `get gauge1.val` returned `75`.
    - `gauge1.val=35` succeeded.
    - `get gauge1.val` returned `35`.
    - `get gauge1.x` returned `200`.
  - Generated qrcode TFT:
    - `get qr1.txt` returned `Hello USART HMI`.
    - `qr1.txt="HELLO"` succeeded.
    - `get qr1.txt` returned `HELLO`.
    - `get qr1.x` returned `350`.
  - Generated slider TFT:
    - `get slider1.val` returned `50`.
    - `slider1.val=80` succeeded.
    - `get slider1.val` returned `80`.
    - `get slider1.x` returned `80`.
- 重要限制：
  - 多个 advanced extra 控件类型混在同一个 TFT 的官方组合布局还没有样本，不能靠简单合并单控件 prefix/mirror 模板。
  - 工具现在应拒绝混合 `slider/gauge/progress/qrcode` 多种 advanced layout，直到拿到官方 mixed fixture 后再学习组合规则。
  - 普通多对象新增仍然可用；安全边界是“普通控件 + 一个 advanced extra 类型”。
- Evidence files:
  - `reverse_usarthmi\extra_controls_demo\verify_generated_case20_progress_exact.json`
  - `reverse_usarthmi\extra_controls_demo\verify_generated_case18_gauge_exact.json`
  - `reverse_usarthmi\extra_controls_demo\verify_generated_case21_qrcode.json`
  - `reverse_usarthmi\extra_controls_demo\verify_generated_case17_slider.json`

## Finding: Mixed Extra Visual Controls 2026-05-11

- Status: mixed slider + progress + gauge + QR code on one page is now runtime-usable on the real `COM36` panel.
- Root cause:
  - The extra-control prefix table is a descriptor sequence from offset `0x3E`.
  - Mixed layouts need mirror records sized from the combined descriptor sequence, not the maximum single-control mirror width.
  - Equivalent prefix insertions must be canonicalized before dedupe; otherwise repeated-byte descriptors can be inserted twice in mixed layouts.
- Additional QR fix:
  - QR code text uses a `0x1F3F` user-record text pointer slot.
  - Treating it as `value_base + delta` worked by coincidence in a single-QR fixture, but made `qr1.txt` share the preceding title text buffer when extra text objects existed.
- Live validation after flashing `reverse_usarthmi\extra_controls_demo\output_mixed_extra_descriptor_merge_qrfix.tft` to `COM36`:
  - `sendme -> 0`
  - `sld1.val` read `50`, set to `80`, read back `80`; `sld1.x -> 56`
  - `bar1.val` read `60`, set to `85`, read back `85`; `bar1.x -> 56`
  - `gauge1.val` read `75`, set to `35`, read back `35`; `gauge1.x -> 455`
  - `qr1.txt` read `Hello USART HMI`, set to `HELLO`, read back `HELLO`; `qr1.x -> 560`
  - `title.txt` stayed `EXTRA CONTROLS` after `qr1.txt` was changed, confirming the QR text buffer is no longer aliased.
- Evidence:
  - Build report: `reverse_usarthmi\extra_controls_demo\output_mixed_extra_descriptor_merge_qrfix.json`
  - Upload log: `reverse_usarthmi\extra_controls_demo\upload_mixed_extra_descriptor_merge_qrfix.json`
  - Runtime log: `reverse_usarthmi\extra_controls_demo\verify_mixed_extra_descriptor_merge_qrfix.json`
  - Reduced same-type control: `reverse_usarthmi\extra_controls_demo\two_sliders\verify_result.json`
  - Reduced cross-type control: `reverse_usarthmi\extra_controls_demo\slider_progress\verify_descriptor_merge.json`
- Regression tests:
  - `python -m pytest tests\test_tft_patch.py tests\test_editor_tft_build.py tests\test_page_format.py tests\test_scene_layout.py -q`
  - Result: `36 passed, 22 subtests passed`

## Finding: Timer Non-Visual Control 2026-05-11

- Status:
  - `timer` / `tm0` is now supported as a non-visual scene widget and appended TFT object.
  - It is intentionally not treated as a visible widget; the preview and layout layers give it a safe `1x1` authoring placeholder, but it does not consume row/grid/stack layout space.
- Recovered compiled details:
  - HMI type code: `3`.
  - Primary record length: `0x24`.
  - User slot count: `11`.
  - Primary and mirror record header flag byte: `0x27`.
  - Mirror pseudo geometry payload: `00 00 00 00 01 00 01 00 00 00 00 00`.
  - Timer tail layout omits the normal pre-string sentinel and uses string pointer bias `0x10`.
  - The timer extra code block is `09 1f 04 34`.
  - Timer object fields verified in HMI/source model: `tim`, `en`, event token `codestimer-0`.
- Tooling changes:
  - `scene` validation accepts widget type `timer`.
  - `editor.build_scene` can clone the official local `case_19_timer` template when the seed does not already contain a timer.
  - `tft_patch.patch_added_object_tft` can emit appended timer objects.
  - CLI authoring includes `usarthmi hmi add-timer`; timer no longer requires visual `x/y/w/h`.
  - Example scene added: `examples\timer_demo\scene.json`.
  - Event probe scene added: `examples\timer_demo\scene_printh.json`.
- Generated artifacts:
  - `reverse_usarthmi\extra_controls_demo\timer_scene_build\output.hmi`
  - `reverse_usarthmi\extra_controls_demo\timer_scene_build\output.tft`
  - `reverse_usarthmi\extra_controls_demo\timer_scene_build\manifest.json`
  - `reverse_usarthmi\extra_controls_demo\timer_scene_build\upload_timer.json`
- Build verification:
  - CLI build command produced a valid TFT checksum: `0x97734E5A`.
  - Added object summary: `tm0`, type `3`, id `4`, `tim=400`, `en=1`.
  - Earlier direct patch reproduction of `case_19_timer` is byte-for-byte equal to the official fixture when using the extracted official target `0.pa`.
- Live validation on `COM36`:
  - Uploaded `reverse_usarthmi\extra_controls_demo\timer_scene_build\output.tft`.
  - File size: `11,408,652` bytes.
  - Upload chunks: `2786`.
  - Elapsed upload time: `210.344s`.
  - Runtime reads:
    - `sendme -> 0`
    - `get tm0.tim -> 400`
    - `get tm0.en -> 1`
  - Runtime writes:
    - `tm0.en=0`, then `get tm0.en -> 0`
    - `tm0.tim=250`, then `get tm0.tim -> 250`
  - Restored `tm0.en=1` and `tm0.tim=400`.
- Timer event probe:
  - Built and uploaded `reverse_usarthmi\extra_controls_demo\timer_printh_build\output.tft`.
  - Event source was `codestimer-1` with `printh 23 02 54 4d`.
  - Serial passive listen before and after `tm0.en=1` received no `23 02 54 4d` frames.
  - This means `timer` object/property compilation works, but timer event scheduling is still not proven and likely needs another compiled scheduler/index table.
  - Evidence:
    - `reverse_usarthmi\extra_controls_demo\timer_printh_build\verify_timer_printh.json`
    - `reverse_usarthmi\extra_controls_demo\timer_printh_build\verify_timer_printh_after_enable.json`
- Current limit:
  - Timer event scheduling remains unsolved. The next useful fixture is an official `timer + text/number/printh witness` compiled TFT, so the runtime scheduler/index delta can be diffed directly.
- Regression tests:
  - `python -m pytest tests\test_tft_patch.py tests\test_scene_layout.py tests\test_editor_tft_build.py -q`
  - Result after CLI timer fix: `40 passed, 22 subtests passed`

## Finding: Event Callback Runtime Pointers And Number Control 2026-05-11

- Event callback fix:
  - Object event bytecode alone is not enough; official TFTs cache executable callback entry offsets in both primary and mirror object records.
  - Recovered fields:
    - `codesdown-` callback pointer at record offset `0x0C`.
    - `codesup-` callback pointer at record offset `0x10`.
    - `codestimer-` callback pointer at record offset `0x14`.
  - After writing these pointers in both record copies, real screen event dispatch works.
- Live event validation on `COM36`:
  - `case19_printh_patch`: `click b0 down` returned raw `23 02 42 44`, proving button down event dispatch.
  - `assign_opcode_probe`: `click startbtn down` returned `23 02 41 31 23 02 41 32 23 02 41 33 ...`, changed `t0.x` from `832` to `120`, changed `tm0.en` from `0` to `1`, and started timer prints `23 02 54 30`.
  - Earlier apparent `tm0.en=1` failure was caused by the timer event immediately running `tm0.en=0`, not by a broken assignment opcode.
- Number control support:
  - Official ordinary number control uses HMI/TFT type code `6`.
  - Primary record length: `0x54`.
  - User slot count: `41`.
  - Mirror layout for the number fixture uses the combined descriptor width `43`.
  - Type `6` shares the compact primary tail/string layout previously seen on timer; it omits the normal 4-byte pre-string sentinel and uses string pointer bias `0x10`.
  - `editor.build_scene` now uses the local official `case_16_number_basic` prototype for scene `number` widgets instead of the keyboard page's incompatible `type 4` object.
- Live number validation on `COM36`:
  - Built and uploaded `reverse_usarthmi\live_number_demo\output.tft`.
  - Initial `get numval.val -> 123`.
  - `click incbtn down` returned raw `23 02 4e 31`.
  - After the click, `get numval.val -> 124`, proving `numval.val++` event compilation and runtime mutation.
- Artifacts:
  - `examples\number_demo\scene.json`
  - `reverse_usarthmi\live_number_demo\output.hmi`
  - `reverse_usarthmi\live_number_demo\output.tft`
  - `reverse_usarthmi\live_number_demo\manifest.json`
  - `reverse_usarthmi\event_logic_probe\assign_opcode_probe\scene.json`
  - `reverse_usarthmi\event_logic_probe\assign_low_slot\scene.json`
- Regression tests:
  - `python -m pytest tests\test_tft_patch.py tests\test_editor_tft_build.py -q`
  - Result: `28 passed, 23 subtests passed`

## Milestone: Official GUI Compile Capture Automation 2026-05-11

- Added an official comparison generator:
  - `tools\official_hmi_compile_capture.py`
  - It launches `USART HMI.exe`, opens a target `.HMI`, clicks the official `编译` toolbar button, waits for `%APPDATA%\USART HMI\work\a-*\run.run`, and copies the newest official output into a chosen fixture directory.
- Smoke verification:
  - Input: `reverse_usarthmi\official_timer_samples\timer_control.HMI`.
  - Captured output: `reverse_usarthmi\official_timer_samples\official_compile_capture\timer_control.run`.
  - The captured file is byte-for-byte identical to `reverse_usarthmi\official_timer_samples\official_compile_output\timer_control.run`.
  - Official log included `编译成功! 0个错误, 0个警告`.
- Batch official captures generated:
  - `reverse_usarthmi\official_case_runs\case_17_slider\lcd_test.run`, size `11,016,304`.
  - `reverse_usarthmi\official_case_runs\case_18_gauge\lcd_test.run`, size `11,016,236`.
  - `reverse_usarthmi\official_case_runs\case_19_timer\lcd_test.run`, size `11,015,436`.
  - `reverse_usarthmi\official_case_runs\case_20_progress\lcd_test.run`, size `11,015,996`.
  - `reverse_usarthmi\official_case_runs\case_21_qrcode\lcd_test.run`, size `11,016,024`.
- Why this matters:
  - We now have a reproducible path to create official byte-level fixtures from the user's desktop case folders without manual mouse/screenshot work.
  - This unblocks faster reverse loops for slider, gauge, timer, progress, QR code, and future official comparison cases.

## Finding: New Control Fixtures 22-34 And TFT Type Table 2026-05-11

- User-provided official samples were added under `C:\Users\SinYu\Desktop\case_for_codex`:
  - `case_22_scrolling_text`
  - `case_23_dual_state_button`
  - `case_24_state_button`
  - `case_25_hotspot_touch_area`
  - `case_26_variable_numeric_string`
  - `case_27_waveform_basic`
  - `case_28_checkbox`
  - `case_29_radio`
  - `case_30_crop_image`
  - `case_31_multi_page_navigation`
  - `case_32_timer_autorun_witness`
  - `case_33_all_controls_mixed_stress`
  - `case_34_complex_event_logic`
- Extracted single-page samples were written into `reverse_usarthmi\case_compare\case_22_*` through `case_34_*`.
- New recovered TFT object type table entries:
  - waveform: type `0x00`, primary record `0x5C`, user slots `41`.
  - variable: type `4`, primary record `0x10`, user slots `11`, non-visual, header flag `0x07`.
  - dual-state button: type `5`, primary record `0x58`, user slots `42`.
  - scrolling text: type `7`, primary record `0x60`, user slots `48`.
  - checkbox: type `8`, primary record `0x48`, user slots `31`.
  - radio: type `9`, primary record `0x40`, user slots `30`.
  - state button: type `C`, primary record `0x50`, user slots `38`.
  - hotspot/touch area: type `m`, primary record `0x3C`, user slots `27`.
  - crop image: type `q`, primary record `0x44`, user slots `30`.
- Tooling changes:
  - `tft_patch.TYPE_RECORD_LENGTHS`, `TYPE_USER_SLOT_COUNTS`, and `KNOWN_EXTRA_TYPE_CASES` now include the new types above.
  - Variable objects are treated as non-visual records and do not require normal `x/y/w/h/endx/endy` coordinates.
  - `5/7/C` text-bearing controls use the compact string layout seen in official fixtures, without the normal pre-string sentinel.
- Verification:
  - `case_23_dual_state_button` now reproduces the official TFT byte-for-byte from the baseline TFT plus target `0.pa`.
  - `case_22` through `case_30` all compile through `patch_added_object_tft` into checksum-valid TFTs.
  - `case_32_timer_autorun_witness` and `case_34_complex_event_logic` also compile into checksum-valid TFTs during manual verification.
- Current limits:
  - Most new controls are at "valid generated TFT" level, not yet "byte-perfect and live-smoked" level.
  - `case_22`, `case_24` through `case_30`, `case_32`, and `case_34` still have byte differences from official output.
  - `case_31_multi_page_navigation` is not implemented in the independent writer yet; current writer remains page0-oriented.
  - The all-controls stress sample `case_33` is evidence for future mixed-layout work, but not yet promoted as a full supported build path.
- Regression tests:
  - `python -m pytest tests\test_tft_patch.py -q`
  - Result: `18 passed, 30 subtests passed`
  - `python -m pytest tests\test_editor_tft_build.py tests\test_page_format.py tests\test_scene_layout.py -q`
  - Result: `27 passed, 2 subtests passed`

## Live Flash Verification: Dual-State Button Case 23 2026-05-11

- Built fixed artifact:
  - `reverse_usarthmi\live_case23_dual_state\output.tft`
  - Size: `11,409,432` bytes.
  - Final TFT checksum valid: `0x5FE98864`.
  - Byte-for-byte identical to official `C:\Users\SinYu\Desktop\case_for_codex\case_23_dual_state_button\lcd_test.tft`.
- Uploaded to the real screen:
  - Port: `COM36`.
  - Initial baud: `9600`.
  - Download baud: `921600`.
  - File size: `11,409,432`.
  - Chunks sent: `2786`.
  - Bytes sent: `11,409,432`.
  - Elapsed: `206.766s`.
  - Upload log: `reverse_usarthmi\live_case23_dual_state\upload_case23.json`.
- Runtime verification:
  - `sendme -> 0`.
  - Initial `get bt0.val -> 0`.
  - `get bt0.x -> 0`.
  - `click bt0 down`, then `get bt0.val -> 1`.
  - Second `click bt0 down`, then `get bt0.val -> 0`.
  - `click bt0 up` leaves the current toggle state unchanged.
- Conclusion:
  - Type `5` dual-state button is now promoted from offline exact reproduction to live-flashed runtime verified.
  - Evidence files are under `reverse_usarthmi\live_case23_dual_state`.

## Milestone: Clean Page Rebuild And Live Verification 2026-05-11

- Problem found by camera:
  - The earlier `case23` byte-perfect upload still displayed old baseline objects (`t0/b0/p0`) because the official target case itself was an appended-object page.
  - Serial confirmed the same issue: old `b0.txt` and `t0.txt` were still readable.
- New tooling:
  - Added `patch_rebuild_page_tft()` in `usarthmi\tft_patch.py`.
  - Added CLI command:
    - `python -m usarthmi tft rebuild-page --baseline-tft <seed.tft> --seed-pa <seed 0.pa> --target-pa <target 0.pa> --out <out.tft>`
  - This mode uses the baseline TFT only as binary shell/template source, then rebuilds the compiled page object/hash/user/mirror tail from the target `0.pa`.
- Clean test artifact:
  - Target PA: `reverse_usarthmi\live_clean_case23\clean_bt0.pa`.
  - Output TFT: `reverse_usarthmi\live_clean_case23\clean_bt0.tft`.
  - Object list: `page0`, `bt0`.
  - Removed seed objects: `t0`, `b0`, `p0`.
  - File size: `11,405,996` bytes.
  - Final TFT checksum valid: `0x4552544E`.
- Live upload:
  - Port: `COM36`.
  - Initial baud: `9600`.
  - Download baud: `921600`.
  - Chunks sent: `2785`.
  - Bytes sent: `11,405,996`.
  - Elapsed: `206.469s`.
  - Upload log: `reverse_usarthmi\live_clean_case23\upload_clean_bt0.json`.
- Runtime verification:
  - `sendme -> 0`.
  - Initial `get bt0.val -> 0`.
  - `get b0.txt -> 1A invalid_reference`.
  - `get t0.txt -> 1A invalid_reference`.
  - `get p0.pic -> 1A invalid_reference`.
  - `click bt0 down`, then `get bt0.val -> 1`.
- Camera verification:
  - Screenshot: `reverse_usarthmi\live_clean_case23\camera_clean_bt0_idx0.jpg`.
  - Visual result: only the clean dual-state button remains visible; old `ceshi/nihao/C/newt` baseline objects are gone.
- Regression:
  - `python -m pytest tests\test_tft_patch.py -q`
  - Result: `19 passed, 30 subtests passed`.

## Milestone: Case22-30 Clean Smoke And Extra Tail Rules 2026-05-11

- New automation:
  - Added `tools\live_case_smoke.py`.
  - It builds a clean page from a local official case, removes baseline `t0/b0/p0`, rebuilds `0.pa` and TFT, optionally uploads to `COM36`, runs serial probes, and captures a camera frame.
  - It records evidence under `reverse_usarthmi\live_case_smoke\<case_name>\`.
- Byte-perfect append reproduction promoted:
  - `case_22_scrolling_text`: fixed type `7` extra runtime code block `09 1f 04 34`.
  - `case_24_state_button`: fixed type `C` text slot length and `FF` padding.
  - `case_25_hotspot_touch_area`: fixed type `m` compact string layout and absolute user-record slot handling.
  - `case_27_waveform_basic`: fixed waveform extra runtime code block, `FF` padding, and primary final waveform anchor.
  - `case_28_checkbox`: fixed type `8` compact string layout.
  - `case_29_radio`: fixed type `9` `FF` padding.
  - `case_30_crop_image`: fixed type `q` compact string layout and `FF` padding.
  - Existing `case_23_dual_state_button` remains byte-perfect.
- Live clean-page verification:
  - `case_22_scrolling_text`: uploaded clean TFT, `sendme -> 0`, old objects invalid, `get g0.txt -> newtxt`, camera captured.
  - `case_24_state_button`: uploaded clean TFT, `get sw0.txt -> ""`, `get sw0.val -> 0`, click changed `sw0.val -> 1`, camera captured.
  - `case_25_hotspot_touch_area`: uploaded clean TFT, `get m0.x -> 0`, old objects invalid, camera captured.
  - `case_26_variable_numeric_string`: clean TFT checksum valid, upload skipped on repeat, `get va0.val -> 123`, `get va1.val -> 0`, `va0.val=123` read back correctly.
  - `case_28_checkbox`: uploaded clean TFT, `get c0.val -> 1`, click changed `c0.val -> 0`, old objects invalid, camera captured.
  - `case_29_radio`: uploaded clean TFT, `get r0.val -> 1`, `get r1.val -> 1`, click changed `r0.val -> 0`, old objects invalid, camera captured.
  - `case_30_crop_image`: uploaded clean TFT, `get q0.x -> 0`, old objects invalid, camera captured.
- Waveform-specific finding:
  - Official `case_27_waveform_basic` TFT was uploaded and verified separately.
  - Official append TFT accepts `add s0.id,0,50`, `add 4,0,50`, and `cle s0.id,255`.
  - Clean rebuild can read `s0.id/ch/x/w/h/gdc/gdw` and `b1.txt`, and button click works, but `add s0.id,0,50` still returns `12 FF FF FF`.
  - `12 FF FF FF` is now parsed as `invalid_waveform`, meaning "invalid waveform object id or channel".
  - Current conclusion: waveform ordinary object/property tables are correct, but clean-page waveform runtime registration still has one unresolved hidden dependency.
- Evidence files:
  - `reverse_usarthmi\live_case_smoke_case22_upload_fixed.json`
  - `reverse_usarthmi\live_case_smoke_case24_upload.json`
  - `reverse_usarthmi\live_case_smoke_case25_upload.json`
  - `reverse_usarthmi\live_case_smoke_case26_rerun_skip.json`
  - `reverse_usarthmi\live_case_smoke_case27_official_upload_probe.json`
  - `reverse_usarthmi\live_case_smoke_case27_upload_marker.json`
  - `reverse_usarthmi\live_case_smoke_case27_no_renumber_upload.json`
  - `reverse_usarthmi\live_case_smoke_case28_upload.json`
  - `reverse_usarthmi\live_case_smoke_case29_upload.json`
  - `reverse_usarthmi\live_case_smoke_case30_upload.json`
- Regression:
  - `python -m pytest tests\test_tft_patch.py tests\test_protocol.py -q`
  - Result: `32 passed, 33 subtests passed`.

## Milestone: Case33 Mixed Object Exact Rebuild And Live Flash 2026-05-11

- Scope:
  - Target fixture: `case_33_all_controls_mixed_stress`.
  - Object mix: baseline `page0/t0/b0/p0` plus `g0/q0/m0/s0/va0/bt0/c0/r0/sw0`.
  - This is the first all-new-control mixed append page promoted to byte-perfect generation.
- Recovered mixed-layout rules:
  - Mixed descriptor order is not a plain union of single-control prefix insertions.
  - The writer now learns the canonical mixed descriptor order and mirror sparsity from official `case_33_all_controls_mixed_stress`.
  - Multi-control prefix insertions are rebuilt from descriptor sequence order, so duplicate/subset descriptors are merged instead of double-inserted.
  - Mixed primary records use compact lengths for `5/7/8/m/q` when multiple prefix-extended controls share one page.
  - Mixed waveform primary anchor uses `primary_size + 0x0C`, while the final waveform marker stays `0x114`.
  - Variable type `4` user records keep the official `FF FF FF` object marker instead of injecting the object id.
  - State button type `C` user records now treat `0x193F` as a text-pointer record.
- Offline verification:
  - Generated TFT: `reverse_usarthmi\live_case33_mixed\generated_case33_mixed.tft`.
  - Official reference: `C:\Users\SinYu\Desktop\case_for_codex\case_33_all_controls_mixed_stress\lcd_test.tft`.
  - Result: byte-for-byte identical.
  - Size: `11,418,160` bytes.
  - SHA-256: `894e1df61f985f6fe1fd6985f550b4fc3f08f65a93a99668ccfda5256a018988`.
  - Final TFT checksum valid: `0xFF12E268`.
- Live flash:
  - Port: `COM36`.
  - Initial baud: `9600`.
  - Download baud: `921600`.
  - Bytes sent: `11,418,160`.
  - Chunks sent: `2788`.
  - Elapsed: `205.828s`.
  - Result log: `reverse_usarthmi\live_case33_mixed\live_result.json`.
  - Camera capture: `reverse_usarthmi\live_case33_mixed\camera_after_upload.jpg`.
- Runtime verification:
  - `get t0.txt -> nihao`.
  - `get b0.txt -> ceshi`.
  - `get g0.txt -> newtxt`.
  - `get q0.x -> 0`.
  - `get m0.x -> 0`.
  - `get s0.id -> 7`.
  - `get s0.ch -> 1`.
  - `get va0.val -> 0`.
  - `get bt0.txt -> newtxt`.
  - `get bt0.val -> 0`.
  - `get c0.val -> 1`, then `click c0 down`, then `get c0.val -> 0`.
  - `get r0.val -> 1`.
  - `get sw0.val -> 0`, then `click sw0 down`, then `get sw0.val -> 1`.
  - `add s0.id,0,50` returned no error, so the mixed append waveform runtime registration is valid.
- Regression:
  - `python -m py_compile usarthmi\tft_patch.py tests\test_tft_patch.py`
  - `python -m pytest tests\test_tft_patch.py tests\test_protocol.py -q`
  - Result: `33 passed, 33 subtests passed`.

## Milestone: Case27 Clean Waveform Runtime Pad Fix 2026-05-11

- Scope:
  - Target fixture: `case_27_waveform_basic`.
  - Problem reproduced on hardware: a clean rebuild containing only `page0/s0/b1` could read `s0.id/ch/x` and `b1.txt`, but `add s0.id,0,50`, `add 1,0,50`, and `cle s0.id,255` returned `12 FF FF FF`.
  - This proved the name hash and ordinary property tables were valid, while waveform runtime registration was missing.
- Recovered rule:
  - Clean waveform pages now keep three tiny renamed runtime pad objects before the waveform: `_wfpad1` type `t`, `_wfpad2` type `b`, `_wfpad3` type `p`.
  - The pads are `1x1` at `(799,479)`, so the public old seed names `t0/b0/p0` stay invalid while `s0` is placed at internal id `4`, matching the proven official append topology.
  - `tools\live_case_smoke.py` now inserts these pads only for waveform clean-page smoke builds; ordinary append and byte-perfect official fixture reproduction are unchanged.
- Live flash:
  - Generated TFT: `reverse_usarthmi\live_case27_fixed_tool\case_27_waveform_basic\clean.tft`.
  - Probe TFT uploaded to `COM36` at `921600`.
  - Bytes sent: `11,410,884`.
  - Chunks sent: `2786`.
  - Elapsed: `206.015s`.
  - The fixed tool output is byte-identical to the uploaded probe TFT, so the final tool smoke used safe identical-file skip.
- Runtime verification:
  - `sendme -> 0`.
  - Old seed names are invalid: `get t0.txt`, `get b0.txt`, `get p0.pic` all returned `1A FF FF FF`.
  - `get s0.id -> 4`.
  - `get s0.ch -> 1`.
  - `get s0.x -> 0`.
  - `add s0.id,0,50` returned no error.
  - `add 4,0,50` returned no error.
  - `cle s0.id,255` returned no error.
  - `get b1.txt -> newtxt`; `click b1,1` is accepted.
- Evidence:
  - Tool result: `reverse_usarthmi\live_case27_fixed_tool_upload_skip.json`.
  - Full upload result: `reverse_usarthmi\live_case27_runtime_pad_probe_upload2_result.json`.
  - Camera capture: `reverse_usarthmi\live_case27_fixed_tool\case_27_waveform_basic\camera_after_upload.jpg`.
- Regression:
  - `python -m py_compile tools\live_case_smoke.py tests\test_tft_patch.py usarthmi\tft_patch.py`
  - `python -m pytest tests\test_tft_patch.py tests\test_protocol.py -q`
  - Result: `34 passed, 33 subtests passed`.

## Milestone: Minimal Control Live Matrix Case16-30 2026-05-11

- Scope:
  - Goal: prove each minimal single-control page is not only checksum-valid, but also live on the real `COM36` screen.
  - Method: build clean TFT, upload or skip when identical, run `sendme`, confirm old seed objects `t0/b0/p0` are invalid, then run the smallest meaningful property/action check for the target object.
  - Camera captures were stored under `reverse_usarthmi\minimal_control_live\<case>\camera_after_upload.jpg`.
- Smoke tool hardening:
  - Text-like controls now write `txt="OK"` and read it back for `t/b/5/7/C/:`.
  - Numeric visual controls now write `val=37` and read it back for slider, number, progress bar, and gauge.
  - Timer checks now read `tim/en`, set `en=1`, and read it back.
  - Variable checks now write `val=123` and read it back.
  - Hotspot checks now issue `click m0,1` and require no invalid-object response.
  - Picture/crop-image checks now read and rewrite `pic` or `picc`; crop image `q0.picc=65535` was confirmed live.
- Live verified controls:
  - `case_16_number_basic`: `numval.val=37` read back as `37`; camera shows `00037`.
  - `case_17_slider`: `slider1.val=37` read back as `37`.
  - `case_18_gauge`: `gauge1.val=37` read back as `37`.
  - `case_19_timer`: `tm0.tim -> 400`, `tm0.en=1` read back as `1`.
  - `case_20_progress`: `bar1.val=37` read back as `37`.
  - `case_21_qrcode`: `qr1.txt="OK"` read back as `OK`.
  - `case_22_scrolling_text`: `g0.txt="OK"` read back as `OK`.
  - `case_23_dual_state_button`: `bt0.txt="OK"` read back as `OK`; click changed `bt0.val` to `1`.
  - `case_24_state_button`: `sw0.txt="OK"` read back as `OK`; click changed `sw0.val` to `1`.
  - `case_25_hotspot_touch_area`: `m0.x -> 0`; `click m0,1` accepted.
  - `case_26_variable_numeric_string`: `va0.val=123` read back as `123`; `va1` is also reachable.
  - `case_27_waveform_basic`: `b1.txt="OK"` read back as `OK`; click changed `b1.val` to `1`; `add s0.id,0,50` accepted.
  - `case_28_checkbox`: click changed `c0.val` from `1` to `0`.
  - `case_29_radio`: `r0/r1` reachable; click changed `r0.val` from `1` to `0`.
  - `case_30_crop_image`: `q0.x -> 0`; `q0.picc -> 65535`; `q0.picc=65535` read back as `65535`.
- Evidence files:
  - `reverse_usarthmi\minimal_control_live_case16.json`
  - `reverse_usarthmi\minimal_control_live_case17.json`
  - `reverse_usarthmi\minimal_control_live_case18.json`
  - `reverse_usarthmi\minimal_control_live_case19.json`
  - `reverse_usarthmi\minimal_control_live_case20.json`
  - `reverse_usarthmi\minimal_control_live_case21.json`
  - `reverse_usarthmi\minimal_control_live_case22.json`
  - `reverse_usarthmi\minimal_control_live_case23.json`
  - `reverse_usarthmi\minimal_control_live_case24.json`
  - `reverse_usarthmi\minimal_control_live_case25.json`
  - `reverse_usarthmi\minimal_control_live_case26.json`
  - `reverse_usarthmi\minimal_control_live_case27.json`
  - `reverse_usarthmi\minimal_control_live_case28.json`
  - `reverse_usarthmi\minimal_control_live_case29.json`
  - `reverse_usarthmi\minimal_control_live_case30_rerun.json`
- Boundary note:
  - This milestone proves minimal object/property/action survival on `page0`.
  - `case_31+` should be treated separately because page lifecycle, page table, real event side effects, timer scheduling, and cold boot persistence can still produce false positives if only "command did not error" is checked.
- Regression:
  - `python -m py_compile tools\live_case_smoke.py`
  - `python -m pytest tests\test_tft_patch.py tests\test_protocol.py -q`
  - Result: `34 passed, 33 subtests passed`.
