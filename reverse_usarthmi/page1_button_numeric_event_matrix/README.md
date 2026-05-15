# page1_button_numeric_event_matrix

Experimental page1 numeric-event matrix probe.

Scope:

- page0 stays seed-compatible and keeps the original runtime page id `1`.
- page1 is the extra compiled page and uses runtime page id `0`.
- page1 contains number `numval` and three normal buttons.
- `inc0` press event runs `numval.val++`.
- `set7` press event runs `numval.val=7`.
- `dec0` press event runs `numval.val--`.
- This remains behind `experimental_multi_page_events`.

Live evidence:

- `hardware_verified_2026-05-15.json` records a full COM36 upload and serial
  smoke test. Runtime reads verify `numval.val` transitions `3 -> 4 -> 7 -> 6`
  through `inc0`, `set7`, and `dec0`.
- This confirms that several page1 button callbacks can coexist on the same
  generated page when their numeric field references use page-local user slots.

Live smoke:

```powershell
python tools\live_tft_smoke.py --upload `
  --file reverse_usarthmi\page1_button_numeric_event_matrix\local_build\output.tft `
  --out-dir reverse_usarthmi\page1_button_numeric_event_matrix\live_smoke `
  --expect-json reverse_usarthmi\page1_button_numeric_event_matrix\expected_runtime.json `
  --port COM36 --baud 9600 --download-baud 921600 --chunk-size 4096 `
  --timeout-ms 3000 --prepare-delay-ms 1000 --prepare-wait-ms 800
```
