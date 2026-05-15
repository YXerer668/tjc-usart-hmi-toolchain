# HMI event fixture scan 2026-05-15

This folder records a recursive event scan over:

`C:\Users\SinYu\Desktop\case_for_codex`

Generated with:

```powershell
python tools\find_hmi_event_fixtures.py C:\Users\SinYu\Desktop\case_for_codex --out reverse_usarthmi\fixture_event_scan_20260515\case_for_codex_event_scan_2026-05-15.json --compact
```

## Key findings

- 107 `.HMI` paths were scanned.
- 77 parsed as normal USART HMI containers.
- 12 files are event-interesting after ignoring empty `codes*-0` placeholders.
- 4 official wiki projects contain non-empty page-level event scripts.
- 9 official wiki projects contain non-empty object-level event scripts.
- Event names observed: `codesload`, `codesdown`, `codesup`, `codestimer`.

## Page-event oracle candidates

- `case_42_datarecord\official_wiki\source_raw.HMI`
  - Page block `demo`, event `codesload-1`.
  - Script: `repo primaryKey.val,0`.
  - Good candidate for minimal page-load storage/event-table recovery because the page event is only one line.
- `case_43_filebrowser\official_wiki\source_raw.HMI`
  - Page block `start`, event `codesload-21`.
  - Script checks `sd0/sd.cfg` and branches.
  - Good for file/SD logic, but large as a first page-event oracle.
- `case_44_filestream\official_wiki\source_raw.HMI`
  - Same page-load pattern as filebrowser.
- `case_49_audio\official_wiki\source_raw.HMI`
  - Page block `page0`, event `codesload-1`.
  - Script: `volume=100  //音量调到最大`.
  - Good candidate if an official compiled TFT oracle is available.

## Next bit-to-bit target

Use `case_42_datarecord` or `case_49_audio` as the next page-load oracle, depending on
which one has the cleanest official compiled TFT pair. The previous generated
`event_demo` proved object up-event scheduling works, while page-load remains missing.
These official samples should let us compare HMI event scripts against official object
records instead of continuing to guess callback slots.
