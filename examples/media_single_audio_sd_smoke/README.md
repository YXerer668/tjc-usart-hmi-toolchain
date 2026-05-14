# Single Audio SD Smoke

This is a narrow live-panel smoke for one `audio` / `wav` object that points at
an SD-card file path. It verifies the generated object tail and runtime fields;
it does not claim that every WAV encoding, speaker path, or volume setup is
solved.

Expected SD-card file:

```text
sd0/music/official_0.wav
```

Build:

```powershell
python -m usarthmi --json scene build examples\media_single_audio_sd_smoke\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\media_single_audio_sd_smoke_build
```

Live smoke after upload:

```powershell
python tools\live_tft_smoke.py `
  --file reverse_usarthmi\media_single_audio_sd_smoke_build\output.tft `
  --out-dir reverse_usarthmi\media_single_audio_sd_smoke_build\smoke `
  --expect-json examples\media_single_audio_sd_smoke\smoke.expect.json `
  --upload --progress
```

Optional runtime start/stop smoke, after this TFT is already on the panel:

```powershell
python tools\live_tft_smoke.py `
  --file reverse_usarthmi\media_single_audio_sd_smoke_build\output.tft `
  --out-dir reverse_usarthmi\media_single_audio_sd_smoke_build\play_smoke `
  --expect-json examples\media_single_audio_sd_smoke\play.expect.json
```

Notes:

- The sample keeps `wav0.en=0` so flashing it does not immediately try to play
  audio.
- `play.expect.json` deliberately toggles `wav0.en=1` and then restores
  `wav0.en=0`. It proves runtime start/stop control and readback, but it still
  does not prove the physical speaker path.
- Runtime reads are limited to fields such as `wav0.en`, `wav0.vid`,
  `wav0.loop`, `wav0.fps`, `wav0.dis`, and `wav0.tim`.
- `get wav0.path` returns `0x1A` on the current panel, so the smoke explicitly
  checks that it is not runtime-readable instead of treating that as object
  creation failure.
- Do not mix this with GMOV/video in one TFT until media scheduling is proven.
