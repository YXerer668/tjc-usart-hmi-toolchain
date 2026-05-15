# page1_button_numeric_event_matrix

This is the current minimal live-proven page1 numeric-event matrix.

- `numval` starts at `3`.
- `inc0.events.down = ["numval.val++"]`.
- `set7.events.down = ["numval.val=7"]`.
- `dec0.events.down = ["numval.val--"]`.
- Release events are intentionally empty and should not change `numval.val`.

Live verification on `TJC8048X543_011C` / `COM36`:

- `get numval.val` initially returned `3`.
- `click inc0,1` changed it to `4`; `click inc0,0` kept it at `4`.
- `click set7,1` changed it to `7`; `click set7,0` kept it at `7`.
- `click dec0,1` changed it to `6`; `click dec0,0` kept it at `6`.

Build example:

```powershell
.\usarthmi.cmd scene build .\examples\page1_button_numeric_event_matrix\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\page1_button_numeric_event_matrix\local_build
```
