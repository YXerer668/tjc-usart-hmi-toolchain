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

## Follow-up oracle probe

`tools/page_event_oracle_probe.py` now reports two separate page-event locations:

- The normal per-record event table referenced by mirror `event_offset_0x34`.
- The post-primary page event chunk used by media projects.
- It also classifies each report with `scheduler_path`, `upload_risk`, and
  `recommended_writer_action` so generated page-load candidates are not treated
  as safe just because their bytecode exists somewhere in the TFT.

Evidence:

- `case42_lcd_test_page_event_probe_2026-05-15.json`
  - Current-model compiled seed has empty page events.
  - Page mirror `event_offset_0x34` still points to the normal page event table.
- `case49_audio_page_event_probe_2026-05-15.json`
  - Official audio sample has non-empty `codesload-1`.
  - The normal page event table does not contain the page-load payload.
  - A 32-byte post-primary page event chunk matches the official TFT at relative object-region offset `0x8DA`.
  - Current descriptor fingerprint:
    `offset=0x8DA`, `end=0x8FA`, `len=32`,
    `sha256=351515b69f4905ccc4f36d371113f8a7093031530c7ed0a25e485bbcdbb45cbc`.
  - Classified as `scheduler_path=post_primary_page_event`, `upload_risk=research_only`.
- `event_demo_live_probe_20260515\page_event_oracle_probe_2026-05-15.json`
  - Generated page-load bytecode is present in the normal page table.
  - No recovered page-level callback cache points at executable code.
  - Classified as `scheduler_path=normal_page_table_without_page_callback`, `upload_risk=high`.

This is important because the failed generated `event_demo` already had a page event table
and `event_offset_0x34`, but page-load still did not run live. For media-style official
projects, page-load can be relocated into the post-primary chunk, so the next fix should
separate "event bytes exist" from "runtime scheduler has a launch path."

## Scheduler decision matrix

Before burning more page-load candidates, run:

```powershell
python tools\page_event_scheduler_matrix.py
```

The matrix combines the batch official-oracle scan with the live page1 callback-slot
negative probe. It records the complete `case_49_audio` `post_primary_page_event`
oracle, the partial/unsupported `case_42`/`case_43`/`case_44` oracles, and the
live-failed page1 slots `0x0C`, `0x10`, and `0x14`.

The 2026-05-16 matrix also imports the official object-event oracle from
`timer_autorun_live_probe/official_timer_control_oracle_probe_2026-05-16.json`.
That oracle proves object-level callback binding for `codesdown` and
`codestimer`, including the timer `tm0.codestimer-1 -> n0.val++` event. It is
kept in the matrix as a boundary, not as page-lifecycle evidence: object
callbacks are real, but they must not be extrapolated to `codesload` scheduling.

Treat its `decision.forbidden_actions` as guardrails for automation: do not repeat
blind page mirror slot writes, do not extrapolate object callback slots to page
lifecycle scheduling, and do not treat partial oracles as scheduler truth. The next
useful path is either a complete official two-page/page-load oracle or a byte-for-byte
post-primary scheduler descriptor diff.

To compare the current official post-primary oracle against the known unsafe
generated force-post-primary probe, run:

```powershell
python tools\page_event_post_primary_diff.py
```

Current high-signal diff:

- Official `case49_audio`: `offset=0x8DA`, `len=32`, payload hash
  `351515b69f4905ccc4f36d371113f8a7093031530c7ed0a25e485bbcdbb45cbc`.
- Generated force-post-primary probe: `offset=0x3C5`, `len=37`, payload hash
  `4f9ca1251f6da411b4b0d93e00f2dd86613ae0a4fc260bb2b391b8e317cc55fc`.
- Both sides have zero direct u32 references to table start / first executable,
  so the scheduler is not a simple recovered pointer slot.
- Both descriptors currently share the same 32-byte descriptor-adjacent tail after
  the payload. Decoded as little-endian u32 words:
  `0xD073BAFB, 0x00000008, 0x00000009, 0xD9F18195,
  0x00000000, 0x00000009, 0xDD309C22, 0x00000004`.
  Treat this as a scheduler-record candidate until another official oracle proves
  whether these are hashes, IDs, counts, or flags.
- The generated force-post-primary probe has live negative evidence: valid
  checksum and upload, but the runtime command parser became unresponsive
  except for `connect`.
