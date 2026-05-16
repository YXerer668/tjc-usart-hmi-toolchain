# Timer Autorun Live Probe

This probe captures the current state of timer event compilation on the
`TJC8048X543_011C` panel.

## Scene

- `n0`: number display, initial value `0`.
- `tm0`: timer, `tim=400`, `en=1`.
- `tm0.timer`: `n0.val++`.
- `page0.load`: `tm0.en=0`, then `tm0.en=1`.

## Live Findings

- The generated TFT uploads and boots with a valid checksum.
- `tm0.en` and `tm0.tim` read back correctly.
- Timer callback bytecode works after runtime serial arming:
  `tm0.en=0`, `n0.val=0`, `tm0.en=1`.
- Timer auto-start is not recovered yet. Even with `en=1` and a page-load
  restart script, `n0.val` stayed at `0` after upload/page load.

## Evidence

- Failed autorun upload smoke:
  `live_20260516_1116_timer_load_restart/smoke_result.json`
- Manual-arm passing smoke:
  `live_20260516_1125_timer_manual_arm/smoke_result.json`
- Compact hardware summary:
  `hardware_probe_2026-05-16.json`
- Timer oracle scan:
  `timer_oracle_matrix_2026-05-16.json`
- Official timer sample scan:
  `official_timer_samples_matrix_2026-05-16.json`
- Official timer object-event probe:
  `official_timer_control_oracle_probe_2026-05-16.json`

## Timer Oracle Matrix

`tools/timer_oracle_matrix.py` scanned `C:\Users\SinYu\Desktop\case_for_codex`
on 2026-05-16 and found:

- `case_19_timer`: timer object exists, but only `codestimer-0`.
- `case_32_timer_autorun_witness`: timer object exists, but only
  `codestimer-0`; despite the folder README, it is not a non-empty timer event
  oracle.
- `case_41_sltext\official_wiki\source_raw.HMI`: one real `codestimer-2`
  timer event, but no sibling compiled TFT oracle is currently present.

The scan deliberately does not treat unrelated `lcd_test.run` files as compiled
oracles for `official_wiki/source_raw.HMI`; that would create false-positive
object-event evidence.

## Official Timer Control Oracle

`reverse_usarthmi/official_timer_samples/timer_control.HMI` is the current
compiled official non-empty timer oracle:

- HMI: `reverse_usarthmi/official_timer_samples/timer_control.HMI`
- TFT/run: `reverse_usarthmi/official_timer_samples/official_compile_output/timer_control.run`
- Model: `TJC8048X550_011`
- Size: `1,185,424` bytes
- Checksum: `0xDBD4FC41`
- Timer: `tm0`, `codestimer-1`, line `n0.val++`

`official_timer_control_oracle_probe_2026-05-16.json` shows:

- `tm0` event table relative offset: `0x18F`
- First executable timer payload offset: `0x19C`
- Event table start referenced at `0x1516`
- First executable referenced at `0x2D3` and `0x14F6`
- Property event payload: `01 3c 00 00 00 2b 2b`
- Property slot: `0x3C`
- Operation: `++`

This fixture proves official object timer callback binding for a non-empty
`codestimer` event. It still does not prove page-load or timer autorun scheduler
binding.

Treat this as: timer event callback generation is live-proven, but the initial
timer scheduler/autorun path still needs reverse engineering.
