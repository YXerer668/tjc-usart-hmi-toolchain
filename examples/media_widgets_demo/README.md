# Media Widgets Demo

This is the first-pass authoring demo for the current-editor media widgets:

- `animation` / `gmov`, HMI type `0x02`
- `video`, HMI type `0x03`
- `audio` / `wav`, HMI type `0x04`

Current status: this mixed-media demo is HMI and preview support only. The
independent TFT writer now knows the official primary record sizes and
user-slot counts for these media types. Use `media_single_gmov_smoke` for the
proven single-animation path, and `media_single_video_sd_smoke` for the narrow
single SD-video object smoke. Mixed GMOV/video/audio resource scheduling is not
closed yet, so do not pass `--baseline-tft` for this demo.

Build and preview:

```powershell
python -m usarthmi --json scene build examples\media_widgets_demo\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --out reverse_usarthmi\media_widgets_demo_build

python -m usarthmi --json scene preview examples\media_widgets_demo\scene.json `
  --out reverse_usarthmi\media_widgets_demo_build\preview_scene.png
```

Append media widgets to your own scene from the CLI:

```powershell
python -m usarthmi --json hmi add-animation --scene my_scene.json `
  --id gm0 --x 40 --y 80 --w 300 --h 170 `
  --path sd0/anim/official_0.gmov --enabled --loop 1

python -m usarthmi --json hmi add-video --scene my_scene.json `
  --id v0 --x 420 --y 80 --w 300 --h 170 `
  --path sd0/video/official_0.video --enabled

python -m usarthmi --json hmi add-audio --scene my_scene.json `
  --id wav0 --path sd0/music/official_0.wav --disabled
```

The same CLI also has a generic escape hatch for newly recovered controls:

```powershell
python -m usarthmi --json hmi add-widget --scene my_scene.json `
  --id gm0 --type gmov --x 40 --y 80 --w 300 --h 170 `
  --resource path=sd0/anim/official_0.gmov --style en=1 --style loop=1
```

The sample paths target the SD-card resource folders prepared during the case
47/48/49 fixture pass:

- `sd0/anim/official_0.gmov`
- `sd0/video/official_0.video`
- `sd0/music/official_0.wav`
