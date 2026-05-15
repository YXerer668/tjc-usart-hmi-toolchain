# page1_button_ref_tsw_event_probe

Minimal page1 normal-button `ref` / `tsw` event probe for the experimental
multi-page event path.

- `ref0.events.down = ["ref label0"]`.
- `disable0.events.down = ["tsw label0,0"]`.
- `enable0.events.down = ["tsw 255,1"]`.
- The target object must be present on the same generated page1, except
  `tsw 255,1`, which intentionally targets all touch controls.

This sample exists because the scene/editor allow-list and the lower-level TFT
patcher must stay in lockstep. `ref` and `tsw` compile into length-prefixed
event bytecode, but `tsw` changes physical touch behavior, so serial-only smoke
tests can confirm object/readback health but cannot fully prove touch lockout
without a physical touch or camera-assisted manual check.

Build example:

```powershell
.\usarthmi.cmd scene build .\examples\page1_button_ref_tsw_event_probe\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\page1_button_ref_tsw_event_probe\local_build
```

Expected compile-time evidence:

- `manifest.json` contains a valid `output_tft`.
- `tft_checksum.valid` is `true`.
- `tft_patch.experimental_events` is `true`.
- The generated page1 object event tables contain `ref label0`,
  `tsw label0,0`, and `tsw 255,1`.

Optional live smoke after building or uploading:

```powershell
python tools\live_tft_smoke.py `
  --file reverse_usarthmi\page1_button_ref_tsw_event_probe\local_build\output.tft `
  --out-dir reverse_usarthmi\page1_button_ref_tsw_event_probe\smoke `
  --expect-json examples\page1_button_ref_tsw_event_probe\smoke.expect.json
```

Add `--upload --progress --capture` when the screen should be reflashed first.
The smoke checks object readback and serial `click` dispatch. It does not claim
to prove the physical touch-lockout behavior of `tsw label0,0`; that still needs
a manual or camera-assisted touch check.

Live validation on 2026-05-16:

- Built against `case_00_baseline/lcd_test.tft`.
- Checksum valid: `0xAA7BA568`.
- Uploaded to `COM36` / `TJC8048X543_011C`: `11,415,644` bytes, `2788` chunks,
  about `208.625 s`.
- Runtime `sendme` returned page `0`.
- `get title0.txt`, `get label0.txt`, `get ref0.txt`, `get disable0.txt`, and
  `get enable0.txt` all matched the expected strings.
- Serial `click ref0,1`, `click disable0,1`, and `click enable0,1` all returned
  the expected silent success shape.
- Camera proof captured the page layout with the title, yellow target label, and
  three buttons visible.

This proves the generated page, object readback, serial click dispatch, and
visible layout. It still does not prove physical touch lockout because serial
`click` is not the same input path as a finger touching the panel.
