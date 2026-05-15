# page1_button_printh_event_probe

Minimal page1 normal-button event probe for the experimental multi-page event path.

- `ping0.events.up = ["printh 23 02 50 31"]`.
- `23 02 50 31` is an ASCII-safe hex-byte probe payload.
- This stays behind `project.experimental_multi_page_events = true`.
- V1 intentionally allows only `printh` payloads that are explicit hex-byte lists; arbitrary `rawhex` remains blocked at the page1 event allow-list.

Build from the repo root:

```powershell
.\usarthmi.cmd scene build .\examples\page1_button_printh_event_probe\scene.json --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft --out reverse_usarthmi\page1_button_printh_event_probe\local_build
```
