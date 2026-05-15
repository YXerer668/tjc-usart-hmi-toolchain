# page1_load_printh_event_probe

Minimal page1 page-load event probe for the experimental multi-page event path.

- `page1.events.load = ["printh 23 02 50 4C"]`.
- `23 02 50 4C` is the ASCII-safe probe payload `#\x02PL`.
- This stays behind `project.experimental_multi_page_events = true`.
- V1 intentionally allows only one fixed 4-byte explicit-hex `printh` line on page1 load; arbitrary page-level logic remains blocked.
- On the live `TJC8048X543_011C`, generated `page1` maps to runtime `page 0`, so serial verification should issue `page 0` and try to read the probe bytes.
- 2026-05-15 live result: this compiles, checksums, uploads, and page switching remains healthy, but the `23 02 50 4C` load probe was not observed. Keep this as a scheduler-recovery fixture, not as a proven feature.
- Current builds expose this explicitly in `manifest.json`:
  `tft_patch.experimental_event_summary.page1_page_events[].runtime_status`
  is `compile_only_scheduler_unrecovered`.

Build from the repo root:

```powershell
.\usarthmi.cmd scene build .\examples\page1_load_printh_event_probe\scene.json --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft --out reverse_usarthmi\page1_load_printh_event_probe\local_build
```
