# page1_button_event_minimal

Minimal experimental page1 button-event probe.

Scope:

- page0 stays seed-compatible and keeps the original runtime page id `1`.
- page1 is the extra compiled page and uses runtime page id `0`.
- page1 contains a title text and one normal button `back0`.
- `back0` has a single release event: `page 1`, which should jump back to page0.
- This remains behind `experimental_multi_page_events`.

Live evidence:

- `hardware_verified_2026-05-14.json` records a full COM36 upload and serial
  smoke test.
- Runtime page ids are inverted in this recovered layout: `page 0` selects the
  generated page1, and `page 1` selects the seed page0.

Build:

```powershell
python -m usarthmi scene build examples\page1_button_event_minimal\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\page1_button_event_minimal\local_build
```

Live smoke:

```powershell
python tools\live_tft_smoke.py --upload --progress `
  --file reverse_usarthmi\page1_button_event_minimal\local_build\output.tft `
  --out-dir reverse_usarthmi\page1_button_event_minimal\live_smoke `
  --expect-json reverse_usarthmi\page1_button_event_minimal\expected_runtime.json `
  --port COM36 --baud 9600 --download-baud 921600 --chunk-size 4096 `
  --timeout-ms 3000 --prepare-delay-ms 1000 --prepare-wait-ms 800
```
