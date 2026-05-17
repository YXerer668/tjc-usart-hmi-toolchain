# Crop Image Demo

This is the focused `crop-image` / `q` control smoke fixture. It is separated
from `examples/new_controls_demo` so the crop-image loop no longer depends on a
mixed page where `q0.picc` previously failed readback.

Evidence boundary:

- Source fixture: `reverse_usarthmi/minimal_control_live/case_30_crop_image/smoke_result.json`.
- Historical live evidence there showed page `0`, readable `q0.x == 0`, and
  readable `q0.picc == 65535` on the focused crop-image page.
- `hardware_verified_2026-05-17.json` records the fresh COM36 upload, serial
  readback, and `USB Cam` capture for the current `TJC8048X543_011C` panel.
- The expect file intentionally stays narrow. It does not claim visual crop
  correctness, arbitrary image-resource behavior, or mixed-page crop-image
  behavior.

Offline build:

```powershell
python -m usarthmi --json scene build examples\crop_image_demo\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\crop_image_demo_build
```

Live smoke command used for the committed hardware proof:

```powershell
python tools\live_tft_smoke.py `
  --file reverse_usarthmi\crop_image_demo_build\output.tft `
  --out-dir reverse_usarthmi\crop_image_demo_build\smoke `
  --expect-json examples\crop_image_demo\smoke.expect.json `
  --upload --require-model TJC8048X543_011C `
  --port COM36 --baud 9600 --download-baud 921600 `
  --chunk-size 4096 --timeout-ms 8000 --post-upload-wait-s 2.5 `
  --progress --capture
```

Boundary: this is a serial-readback smoke plus camera capture. It proves the
focused object exists and its historically successful `picc` field reads back;
pixel-level crop visual correctness still needs a separate image assertion.
