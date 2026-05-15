# event_combo_probe

`event_combo_probe` is the live-panel smoke scene for multi-line button event
scripts on `page0`.

The `combo0` down event is intentionally simple and serial-verifiable:

```text
numval.val=10
numval.val++
numval.val++
numval.val--
```

Expected runtime result after `click combo0 down` is `numval.val == 11`.

Build from the repository root:

```powershell
python -m usarthmi --json scene build examples\event_combo_probe\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\event_combo_probe\local_build
```

2026-05-15 live proof on `COM36` / `TJC8048X543_011C`:

- TFT checksum: valid, `0xD4DD1200`.
- Upload: `11,414,588` bytes, `2787` chunks, public `whmi-wri` at `921600`.
- Before click: `get numval.val` returned `0`.
- After `click combo0 down`: `get numval.val` returned `11`.
- After `click reset0 down`: `get numval.val` returned `0`.
- Camera proof: `reverse_usarthmi\event_combo_probe\live_event_combo_after_click_2026-05-15.jpg`.

