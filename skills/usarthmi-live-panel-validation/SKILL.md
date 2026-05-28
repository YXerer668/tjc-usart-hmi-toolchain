---
name: usarthmi-live-panel-validation
description: Use when safely validating or flashing USART HMI TFT files on a real serial panel, including checksum checks, COM ownership checks, connect gates, public serial upload, post-upload health probes, sendme/get readback, smoke commands, and camera evidence.
---

# USART HMI Live Panel Validation

Use this skill only when a task explicitly involves a real panel, serial port,
upload, smoke test, camera proof, or post-flash diagnosis. Keep build-only work
in the headless or scene-authoring skills.

## Safety Gate

Before opening the serial port:

1. Confirm no background stress/probe process owns the COM port.
2. Run a checksum or readiness check on the candidate TFT.
3. Run `connect` and compare the target identity with the expected gate.
4. Upload only after the user explicitly asked to flash or validate on hardware.

For the known `TJC8048X543_011C` lab lane, the expected fields are:

```text
mode=2
flash_descriptor=1089-0
model=TJC8048X543_011C
firmware=277
mcu_code=10501
feature_descriptor=128974848-0
```

Do not reuse that gate for another model without changing the expected fields.

## Useful Commands

Offline TFT check:

```powershell
python -m usarthmi --json tft checksum --file build\case\output.tft
python -m usarthmi --json tft readiness --file build\case\output.tft
```

Serial identity and health:

```powershell
.\usarthmi.cmd --json connect --port COM36 --baud 9600 --timeout-ms 3000
.\usarthmi.cmd --json sendme --port COM36 --baud 9600 --timeout-ms 3000
.\usarthmi.cmd --json tft health --port COM36 --baud 9600 --timeout-ms 3000
```

Upload through the public serial protocol:

```powershell
.\usarthmi.cmd --json tft upload `
  --file build\case\output.tft `
  --port COM36 `
  --baud 9600 `
  --download-baud 921600 `
  --chunk-size 4096 `
  --timeout-ms 8000 `
  --progress `
  --verify-after-upload
```

Use the touch-safe wrapper for integrated build + flash:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_touchsafe_pipeline.ps1 `
  -Spec .\case.spec.json `
  -Flash -SerialSmoke -Camera
```

## Evidence Rules

- A successful upload is not the same as a healthy runtime.
- A healthy runtime is not proof that every UI path works.
- Collect post-upload `tft health`, `sendme`, relevant `get obj.attr` probes,
  and camera evidence for visual claims.
- If a process is already running a stress or probe script, read only its
  process/checkpoint files until it exits; do not issue competing serial
  commands.
- Never copy official `work\a-*\output\*.tft` during an active official serial
  transfer. Copy before transfer starts or after it completes.
