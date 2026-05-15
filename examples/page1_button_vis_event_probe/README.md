# page1_button_vis_event_probe

Minimal page1 normal-button visibility-event probe.

- `label0` starts visible with text `VISIBLE LABEL`.
- `hide0.events.down = ["vis label0,0"]`.
- `show0.events.down = ["vis label0,1"]`.
- The target object must be present on the same generated page1.

This intentionally keeps `vis` narrow: only `vis obj,0` and `vis obj,1` are
accepted in page1 button events, and only when `obj` is a known same-page object.

Live validation on 2026-05-15:

- Built against `case_00_baseline/lcd_test.tft`.
- Uploaded to the `TJC8048X543_011C` on `COM36` through public `whmi-wri`.
- Runtime `page 0` maps to the generated `page1`; `sendme` returns `0`.
- `get label0.txt`, `get hide0.txt`, and `get show0.txt` read back the expected strings.
- `click hide0,1` hides `label0`; `click show0,1` shows it again, verified by camera capture.

Build example:

```powershell
.\usarthmi.cmd scene build .\examples\page1_button_vis_event_probe\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\page1_button_vis_event_probe\local_build
```
