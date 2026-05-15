# page1_event_matrix_smoke

Page1 event matrix smoke for the experimental multi-page path.

This is a higher-coverage live sample than the single-purpose probes. It keeps
each button to one event line, but combines the currently recovered page1 normal
button event forms:

- `numval.val++`
- `numval.val=7`
- `numval.val--`
- `vis label0,0`
- `vis label0,1`
- `ref label0`
- `tsw label0,0`
- `tsw 255,1`

Build:

```powershell
.\usarthmi.cmd scene build .\examples\page1_event_matrix_smoke\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\page1_event_matrix_smoke\local_build
```

Live smoke:

```powershell
python tools\live_tft_smoke.py `
  --file reverse_usarthmi\page1_event_matrix_smoke\local_build\output.tft `
  --out-dir reverse_usarthmi\page1_event_matrix_smoke\smoke `
  --expect-json examples\page1_event_matrix_smoke\smoke.expect.json `
  --upload --progress
```

Live validation:

- Date: 2026-05-16.
- Panel: `COM36`, `TJC8048X543_011C`.
- TFT: `reverse_usarthmi/page1_event_matrix_smoke/local_build/output.tft`.
- Checksum: `0xA1851E9E`, valid, file size `11423332`.
- Upload: `11423332` bytes, `2789` chunks, `4096` byte chunks, `209.406s`.
- Serial readback: `sendme=0`, `title0.txt=PAGE1 EVENT MATRIX`,
  `label0.txt=VISIBLE LABEL`, `numval.val` changes `0 -> 1 -> 7 -> 6`.
- Camera proof:
  `reverse_usarthmi/page1_event_matrix_smoke/smoke/camera_after_smoke.jpg`.
- Machine-readable record:
  `examples/page1_event_matrix_smoke/hardware_verified_2026-05-16.json`.

The smoke can prove numeric assignment/inc/dec through `get numval.val`, object
readback through `get *.txt`, and serial click dispatch for `vis/ref/tsw`.
Physical finger lockout from `tsw` still needs a touch-based validation path.
