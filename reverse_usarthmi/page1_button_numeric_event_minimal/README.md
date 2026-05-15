# page1_button_numeric_event_minimal

Minimal experimental page1 numeric-event probe.

Scope:

- page0 stays seed-compatible and keeps the original runtime page id `1`.
- page1 is the extra compiled page and uses runtime page id `0`.
- page1 contains number `numval` and normal button `inc0`.
- `inc0` has a single press event: `numval.val++`.
- This remains behind `experimental_multi_page_events`.

Live evidence:

- `hardware_verified_2026-05-15.json` records a full COM36 upload and serial
  smoke test. `numval.val` starts at `3`, then `click inc0,1` increments it to
  `4`, and a second press increments it to `5`.
- The event-field reference must be compiled with the page-local user-slot
  context. A cross-page/global slot build produced `0x1C` on `click inc0,1` and
  did not change `numval.val`.

Live smoke:

```powershell
python tools\live_tft_smoke.py --upload `
  --file reverse_usarthmi\page1_button_numeric_event_minimal\local_build\output.tft `
  --out-dir reverse_usarthmi\page1_button_numeric_event_minimal\live_smoke `
  --expect-json reverse_usarthmi\page1_button_numeric_event_minimal\expected_runtime.json `
  --port COM36 --baud 9600 --download-baud 921600 --chunk-size 4096 `
  --timeout-ms 3000 --prepare-delay-ms 1000 --prepare-wait-ms 800
```
