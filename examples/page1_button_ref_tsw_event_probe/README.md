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
