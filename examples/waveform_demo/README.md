# Waveform Demo

`scene.json` is the isolated waveform clean-rebuild fixture. It keeps the live
case-27 shape small: `s0` is the target waveform object and `b1` is a readable
button used to prove ordinary object read/write behavior still works.

The historical successful COM36 runs inserted hidden runtime pads before the
waveform target. This scene keeps them explicit so the JSON scene path has the
same runtime object ordering:

- `_wfpad1`: text, id `1`, at `799,479`, size `1x1`
- `_wfpad2`: button, id `2`, at `799,479`, size `1x1`
- `_wfpad3`: picture, id `3`, at `799,479`, size `1x1`

With those pads present, `s0` becomes runtime id `4`, matching the previously
successful `add s0.id,0,50` command. `smoke.expect.json` records that command as
a pending live runtime step and does not claim hardware verification.

Offline build:

```powershell
.\usarthmi.cmd --json scene build .\examples\waveform_demo\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\waveform_demo\local_build
```

Checksum only:

```powershell
.\usarthmi.cmd --json tft checksum --file reverse_usarthmi\waveform_demo\local_build\output.tft
```

Pending COM36 smoke for the main line after hardware is available:

```powershell
python tools\live_tft_smoke.py `
  --file reverse_usarthmi\waveform_demo\local_build\output.tft `
  --out-dir reverse_usarthmi\waveform_demo\smoke `
  --expect-json examples\waveform_demo\smoke.expect.json `
  --upload --require-model TJC8048X543_011C --port COM36 --baud 9600 `
  --download-baud 921600 --chunk-size 4096 --timeout-ms 8000 `
  --post-upload-wait-s 2.5 --progress --capture
```

Do not add a `hardware_verified_*.json` file until that live command has passed
with checksum, serial runtime checks, and camera evidence.
