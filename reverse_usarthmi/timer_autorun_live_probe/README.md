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

Treat this as: timer event callback generation is live-proven, but the initial
timer scheduler/autorun path still needs reverse engineering.
