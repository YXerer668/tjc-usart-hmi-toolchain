# External Picture Demo

This scene is the default live-safe example for the `external-picture` /
`expicture` widget.

It intentionally builds against the known-good resource baseline:

```powershell
python -m usarthmi --json scene build examples\external_picture_demo\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\external_picture_demo_build
```

The easiest repeatable path is the demo runner. By default it builds and
checksums without touching the serial port:

```powershell
python tools\external_picture_demo_runner.py
```

Add `--smoke --capture` to reuse the current TFT on the panel and collect
serial plus camera evidence. Add `--upload --progress` only when you want to
burn the generated TFT first.

Live smoke checklist:

- `sendme` returns page `0`.
- `get exp0.path` returns `sd0/1.jpg`.
- `get guard.txt` returns `guard.txt ok`.
- The SD picture is visible in the large left frame.

The same serial checks can be replayed without re-uploading:

```powershell
python tools\live_tft_smoke.py `
  --file reverse_usarthmi\external_picture_demo_build\output.tft `
  --out-dir reverse_usarthmi\external_picture_demo_build\smoke `
  --expect-json examples\external_picture_demo\smoke.expect.json
```

Add `--capture` to include the known-good DirectShow `USB Cam` screenshot in
the same smoke result:

```powershell
python tools\live_tft_smoke.py `
  --file reverse_usarthmi\external_picture_demo_build\output.tft `
  --out-dir reverse_usarthmi\external_picture_demo_build\smoke_capture `
  --expect-json examples\external_picture_demo\smoke.expect.json `
  --capture
```

If you do want to rebuild, upload, then check in one pass, add `--upload
--progress`. Keep the normal public uploader chunk size at 4096 bytes.

Do not use `case_46_expicture_current_gui` as the live baseline for this demo.
That case remains useful as the official object-tail fixture, but its compact
resource/header layout made the current X543 panel return page `255` after
upload.
