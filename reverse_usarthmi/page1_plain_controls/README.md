# page1_plain_controls

Minimal no-event page1 runtime probe.

Scope:

- page0 stays seed-compatible and has no scene widgets/events.
- page1 contains only ordinary controls: text, button, number, progress, slider, gauge.
- No click events, page-jump button events, timer, waveform, image resource creation, or scheduler probing.

Build:

```powershell
python -m usarthmi scene build examples\page1_plain_controls\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\page1_plain_controls\local_build
```

Live smoke:

```powershell
python tools\live_tft_smoke.py --upload --progress `
  --file reverse_usarthmi\page1_plain_controls\local_build\output.tft `
  --out-dir reverse_usarthmi\page1_plain_controls\live_smoke `
  --expect-json reverse_usarthmi\page1_plain_controls\expected_runtime.json `
  --port COM36 --baud 9600 --download-baud 921600 --chunk-size 4096 `
  --timeout-ms 3000 --prepare-delay-ms 1000 --prepare-wait-ms 800
```
