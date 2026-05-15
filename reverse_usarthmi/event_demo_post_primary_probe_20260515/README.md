# event_demo post-primary page-load probe 2026-05-15

This is a negative live experiment for the page-load scheduler.

## Hypothesis

The previous `event_demo` generated a normal page event table containing
`codesload-1 printh 23 02 50 01`, and mirror `event_offset_0x34` pointed to it,
but the real panel did not emit `23 02 50 01` on `page 0` or `rest`.

Official `case_49_audio` showed a media project can place page-load bytecode in
a post-primary page event chunk. This probe asked whether forcing the same
post-primary layout on a non-media single-page build would make page-load run.

## Result

Failed. The generated TFT had a valid checksum and the post-primary chunk was
detectable by `tools/page_event_oracle_probe.py --force-post-primary-page-load`,
but after serial upload the panel only responded to `connect`. It did not answer:

- `sendme`
- `get evtbtn.txt`
- `click evtbtn,0`
- `page 0`
- `bkcmd=3`
- `get dim`
- `rest`
- `whmi-wri ...`

This means "blindly move non-media page-load to post-primary" is not a safe fix.

## Recovery note

An attempted serial restore to the prior known-good `event_demo` TFT failed at
the initial `whmi-wri` ACK while the bad probe was running. The panel still
reported `connect` as `TJC8048X543_011C`, but did not accept public serial
download commands in this state.

Next recovery should use one of:

- physical reset/power-cycle, then retry serial upload immediately;
- official USART HMI downloader if it can enter a deeper recovery path;
- SD-card restore with a known-good TFT if serial runtime remains wedged.

Do not expose this forced post-primary generation path as a normal scene option
until a safe scheduler descriptor is recovered.

## Added guardrail

`tools/tjc_serial_health.py` was added after this failure. It sends only safe
runtime commands:

```powershell
python tools\tjc_serial_health.py --port COM36 --baud 9600 --timeout-ms 3000 --expected-model TJC8048X543_011C --out reverse_usarthmi\event_demo_post_primary_probe_20260515\serial_health_after_failure_2026-05-15.json
python -m usarthmi --json tft health --port COM36 --baud 9600 --timeout-ms 3000 --expected-model TJC8048X543_011C
```

Current bad-state result:

- `connect_ok=true`
- `model=TJC8048X543_011C`
- `runtime_ok=false`
- `public_upload_ready=false`

Use this before future automated uploads. If it reports `connect_ok=true` but
`runtime_ok=false`, do not keep retrying public `whmi-wri`; recover the panel
first.

Formal CLI uploads should use the same guardrail:

```powershell
python -m usarthmi --json tft preflight --file known_good.tft --port COM36 --baud 9600 --expected-model TJC8048X543_011C
python -m usarthmi --json tft upload --file known_good.tft --port COM36 --baud 9600 --download-baud 921600 --require-valid-checksum --require-runtime-healthy --expected-model TJC8048X543_011C
```
