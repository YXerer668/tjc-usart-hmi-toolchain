# Single Video SD Smoke

This is a narrow live-panel smoke for one `video` object that points at an SD
card file path. It is meant to verify the object tail and runtime fields, not to
claim that every video encoding or SD-card playback mode is solved.

Expected SD-card file:

```text
sd0/video/official_0.video
```

Build:

```powershell
python -m usarthmi --json scene build examples\media_single_video_sd_smoke\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\media_single_video_sd_smoke_build
```

Live smoke after upload:

```powershell
python tools\live_tft_smoke.py `
  --file reverse_usarthmi\media_single_video_sd_smoke_build\output.tft `
  --out-dir reverse_usarthmi\media_single_video_sd_smoke_build\smoke `
  --expect-json examples\media_single_video_sd_smoke\smoke.expect.json `
  --upload --progress
```

Notes:

- Runtime reads are limited to fields such as `v0.en`, `v0.vid`, `v0.loop`,
  `v0.fps`, `v0.dis`, and `v0.tim`.
- `get v0.path` returns `0x1A` on the current panel, so the smoke explicitly
  checks that it is not runtime-readable instead of treating that as object
  creation failure.
- Do not mix this with GMOV/audio in one TFT until media scheduling is proven.
