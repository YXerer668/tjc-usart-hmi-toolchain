# page1_button_click_event_probe

Minimal page1 normal-button click-cascade probe for the experimental multi-page event path.

- `fire0.events.up = ["click sink0,0"]`.
- `sink0.events.up = ["printh 23 02 43 4B"]`.
- This verifies whether a page1 button event can dispatch another page1 button release event.
- V1 intentionally allows only one-level same-page button-to-button click cascades whose target emits an explicit hex `printh` probe.

Build from the repo root:

```powershell
.\usarthmi.cmd scene build .\examples\page1_button_click_event_probe\scene.json --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft --out reverse_usarthmi\page1_button_click_event_probe\local_build
```
