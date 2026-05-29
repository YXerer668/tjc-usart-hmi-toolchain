# usarthmi

[中文说明](README.zh-CN.md) | [Feature Status](FEATURE_STATUS.md)

`usarthmi` is an open, evidence-driven toolchain for TJC / USART HMI serial
screens. It combines a Python CLI, reverse-engineered `.HMI` / `.TFT` readers,
scene authoring tools, preview and collision gates, live serial upload helpers,
and a clickless bridge around the official `USART HMI` editor.

The project started from live work on a `TJC8048X543_011C` 800x480 panel. It is
not a blanket replacement for every official-editor workflow; supported features
are documented with concrete evidence such as fixture byte-comparison, checksum
validation, serial readback, or camera proof from the real panel.

## What You Can Do

- Inspect `.HMI` / `.TFT` files and render page previews.
- Author JSON/YAML scenes, edit widgets and events, and generate agent handoff
  bundles.
- Start from reusable three-page 800x480 electronic-contest templates shaped
  around common contest problem types: power conversion, measurement, signal
  generation, communications, PID control, motor drive, sensor DAQ, robot
  tasks, vision/audio recognition, and field debugging. Each template keeps
  stable MCU-facing object names while giving page1/page2 problem-specific
  setup and diagnostic widgets.
- Build touch-safe cases through the official compiler without manual mouse
  clicks.
- Catch visual overlaps and hidden touch hitbox mismatches before flashing.
- Upload TFTs over the public serial protocol and verify the live panel state.
- Package the headless workflow for another Windows machine with official
  `USART HMI` installed.

## Quick Start

```powershell
python -m pip install -e .
python -m usarthmi --json scene check examples\polished_dashboard_demo\scene.json --out-dir build\scene_check
python -m usarthmi --json scene check examples\econtest_templates\power_converter\scene.json --out-dir build\econtest_check --simulate-events
python tools\package_touchsafe_headless_toolchain.py --out-dir dist --require-host-exe
```

Build through the touch-safe official pipeline:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\touchsafe_headless_bootstrap.ps1
powershell -ExecutionPolicy Bypass -File .\tools\run_touchsafe_pipeline.ps1 `
  -Spec .\examples\polished_dashboard_demo\touchsafe_pipeline.template.json
```

Build-only is the default. Flashing a real panel must be explicit and should
include the correct target identity gate.

## Agent Skills

Reusable Codex skills live under [`skills/`](skills/):

- `usarthmi-headless-toolchain` for portable packaging and official headless
  compile flows.
- `usarthmi-scene-authoring` for offline scene edits, previews, linting, and
  agent handoff.
- `usarthmi-live-panel-validation` for checksum, upload, serial health, and
  camera-backed live validation.

## Why This Exists

The official editor is useful, but it is GUI-first and hard to automate. This
repository explores a more hackable workflow:

1. describe a page as JSON/YAML;
2. render a local preview;
3. build an `.HMI` for inspection or official-editor fallback;
4. when the feature is recovered, build a flashable `.TFT` directly;
5. upload through the public serial protocol and verify with live `get` /
   `sendme` commands.

This is not a complete replacement for `USART HMI` yet. It is a practical,
open research toolchain with strict guardrails around the parts that are known
to work.

## Status At A Glance

Stable enough for local use:

- Serial CLI for normal runtime commands.
- `.HMI` extraction/inspection and page preview.
- Scene JSON/YAML validation, layout solving, and PNG preview.
- HmiSafe mode-3 TFT finalization for pre-HmiSafe intermediates, with a
  true-pre fixture that byte-matches the official final TFT.
- Appended page0 TFT generation for the current 800x480 seed project.
- Text, button, number, image, picture resources, two-state image buttons,
  custom `.zi` fonts, xfloat, combobox, external-picture, and the current-target
  supported widget set covered by fixtures/tests. The all-supported-controls
  offline boundary is audited in
  `examples/all_supported_controls_completion_audit_2026-05-17.json`.

Experimental but useful:

- Multi-page page0/page1 generation with limited plain controls.
- Multi-page seed-page button patching for narrow two-way navigation probes:
  `patch_seed_page0_widgets` can edit an existing page0 button event while
  keeping the seed object layout intact.
- A minimal page0 full-page rebuild path through `drop_seed_objects`.
  `examples/number_demo/full_page_rebuild_scene.json` is live-proven on
  `COM36`: the generated TFT removed seed `t0/b0/p0`, rebuilt
  `page0/title/incbtn/numval`, and kept the `incbtn -> numval.val++` event
  working after a full serial upload.
- Event bytecode assembly/inspection for a small set of commands. Page0
  button `ref obj` is live-proven from scene DSL through TFT upload and
  camera-verified redraw after a red `fill` overlay. Page0 `tsw obj,0/1`
  compiles and dispatches in the narrow tested path, but serial `click` is not
  suppressed by `tsw targetbtn,0`; physical-touch lockout proof is tracked
  separately from the serial-click negative result. Page1
  normal-button events are live-proven for `page 1`, explicit-hex `printh`,
  one-level same-page `click` cascades, and numeric field `++` / `=` / `--`
  operations, plus same-page `vis obj,0/1` show/hide operations. The
  `examples/number_demo` page0 `incbtn` down event is also live-proven: two
  serial `click incbtn,1` steps advanced `numval.val` from `123` to `125` and
  emitted `23 02 4e 31` through `printh`. Page0 timer
  `codestimer-` callbacks are live-proven for `numval.val++` after runtime
  `tm0.en=1`; boot/page-load autorun is still open.
  media/audio assignments and `play` events are fixture-backed, while live
  page-load scheduling is not fully solved.
- Single internal GMOV/animation smoke builds for the current resource layout.

Known unstable / research-only:

- Video and audio independent TFT resource scheduling.
- Official-editor smart/sparse download behavior. The recommended upload path
  is the slower full serial upload, because it is much easier to reason about
  and has been more reliable on the test machine.

For a clearer implemented / experimental / missing matrix, see
[`FEATURE_STATUS.md`](FEATURE_STATUS.md).

## HmiSafe TFT Finalization

`usarthmi.tft_hmisafe` exposes the recovered HmiSafe mode-3 finalizer as a
library and CLI. It reproduces the observed native boundary only: selected
bytes in the 400-byte TFT header are rewritten, two header CRC fields are
refreshed, the mode-3 Appfree10 header XOR is applied, and the final EOF-4
little-endian check value is written. It does not build resources, compress
payloads, bypass licensing, patch the official editor, or replace earlier
compiler stages.

The regression gate is a true x32dbg pre-HmiSafe capture:

```powershell
python -m usarthmi --json tft hmisafe-finalize `
  --input path\to\pre_hmisafe.tft `
  --out path\to\reproduced.tft `
  --final path\to\official_final.tft

python -m usarthmi --json tft hmisafe-verify --file path\to\official_final.tft
```

The fixture in `examples/control_fixture_library_2026-05-21.json` requires
`pre_hmisafe.tft -> reproduced.tft` to be byte-identical to the official final
TFT. Mode `0x64` / `Appfree11Encode` is recognized from native code but is not
verified with a true pre/final pair, so finalize/write paths fail closed for
that mode until a matching sample is captured.

## Python API And Widget Registry

The reusable surface is intentionally small:

- `usarthmi.api` exposes `validate_scene_file`, `validate_scene_document`,
  `build_scene_artifacts`, `import_hmi_file`, `inspect_hmi_file`,
  `inspect_tft_file`, `list_tft_models`, `list_widget_capabilities`,
  `get_widget_capability`, `get_capability_manifest`,
  `get_current_target_completion_audit`, `get_current_target_status_summary`,
  `get_builder_calibration_status`, `get_page1_filebrowser_frontier_report`,
  `get_page1_filebrowser_native_init_compare_targets_report`,
  `get_next_live_probe_bundle`, and `run_next_live_probe`.
- `usarthmi.widgets` owns widget metadata: aliases, current-target support
  status, writer kind, fixture case, TFT type code, and pending/unsupported
  reasons.

Reusable contest templates live in
[`examples/econtest_templates`](examples/econtest_templates/). They are indexed
with page roles and per-page widget lists so agents can verify that page0,
page1, and page2 are problem-specific rather than color-only variants. A small
gallery renderer can preview all three pages for all templates with
`python tools\render_econtest_template_gallery.py --out-dir build\econtest_preview_gallery`.
A small MCU-side C99 serial helper for STM32 or any UART driver lives in
[`firmware/usarthmi_serial`](firmware/usarthmi_serial/).

When adding a new widget, update the registry first and let scene validation,
editor writer guards, docs, and tests consume that same metadata. The matching
CLI entrypoints are:

```powershell
python -m usarthmi --json capabilities --widget filebrowser
python -m usarthmi --json editor capabilities
python -m usarthmi --json target summary
python -m usarthmi --json target audit
python -m usarthmi --json target calibration
python -m usarthmi --json target frontier
python -m usarthmi --json target compare-targets
python -m usarthmi --json target next-probe
python -m usarthmi --json target check-next-probe
python -m usarthmi --json target run-next-probe --result-json reverse_usarthmi\next_probe\run_next_probe_result.json
python -m usarthmi --json widgets list --support supported
python -m usarthmi --json widgets show filebrowser
python -m usarthmi --json widgets manifest --include-aliases
python -m usarthmi --json widgets template qrcode --id qr0 --x 80 --y 96
```

For handoff to another agent, generate a read-only preview bundle:

```powershell
python -m usarthmi --json scene check examples\polished_dashboard_demo\scene.json `
  --out-dir reverse_usarthmi\scene_check `
  --simulate-events `
  --scenario <scenario.yaml>

python -m usarthmi --json scene agent-preview examples\polished_dashboard_demo\scene.json `
  --out-dir reverse_usarthmi\gui_agent_preview
```

`scene check` is the offline compile-diagnostics style gate: it validates the
scene, audits widget capability and direct-TFT blockers, runs event lint plus
navigation analysis, and can bounded-simulate non-empty event slots with
`--simulate-events`. It can also run explicit trigger/assert scenario files with
repeatable `--scenario`. With `--out-dir`, it writes `scene_check_report.json`.
It does not build TFTs, open serial ports, or upload to the panel, and keeps
`safe_to_flash=false`.

It writes `preview.png`, `preview.annotated.png`, `scene.normalized.json`,
`agent_context.json`, `diagnostics.json`, `capability_report.json`,
`event_snippets.json`, and `build_manifest.json`. The context file includes
widget coordinates, capability status, event summaries, navigation graph
edges, diagnostics, safe follow-up commands, and a hardware policy that keeps
upload disabled by default. It does not build TFTs, open serial ports, or upload
to the panel.

Existing official `.HMI` files can also be imported into a lossy editable scene
bundle for agent handoff:

```powershell
python -m usarthmi --json hmi import path\to\project.HMI `
  --out-dir reverse_usarthmi\imported_project `
  --overwrite
```

This writes `scene.imported.json`, `import_report.json`, the same preview bundle,
and an `agent_context.json` with import metadata. The importer preserves recovered
page/object geometry, text/value/style/resource fields, raw HMI fields under
`bindings.hmi_import`, and known event slots. Unknown object types are retained
as visible text placeholders instead of being silently dropped. This is not a
byte-perfect `.HMI` roundtrip, TFT rebuild equivalence, resource/font
reconstruction, or hardware proof.

After importing an official `.HMI`, run a roundtrip diagnostic to make the
remaining loss explicit before handing the file to an agent:

```powershell
python -m usarthmi --json hmi roundtrip-check path\to\project.HMI `
  --out-dir reverse_usarthmi\roundtrip_project `
  --source-tft path\to\official.run `
  --overwrite
```

It writes `source.inspect.json`, `scene.imported.json`,
`regenerated\output.hmi`, `regenerated.inspect.json`, and
`roundtrip_report.json`. The report compares source/regenerated objects,
resources, events, and SHA256 values, sets `summary.byte_perfect=true` only
when the bytes actually match, and keeps `safe_to_flash=false`. When
`--source-tft` is supplied, the same report also writes
`event_index.inspect.json` and includes compiled event-index scheduler blockers.
The desktop EXE exposes the same flow through `Roundtrip HMI` and loads the
imported scene, preview, agent context, and blocker summary back into the
workspace.

## Donor HMI Fixture Factory

For low-level-compatible `.HMI` fixture generation, the current recommended path
is donor/template-based patching, not a from-scratch HMI writer.

Reusable entrypoints:

- CLI: `python -m usarthmi --json hmi donor-patch ...`
- API: `usarthmi.api.patch_hmi_donor_file(...)`
- implementation: `usarthmi.hmi_donor_patch`
- official low-level gate: `tools/official_hmi_lowlevel_probe.py`

This path preserves donor container shape and page-shadow lineage, then checks
the result through official `open-lowlevel` / `compile-lowlevel`.

Current boundary:

- supported goal: stable, reproducible donor-based `add/delete/move/set-int/set-str`
  fixture generation
- not claimed: a generic from-scratch HMI writer
- not claimed: runtime or hardware proof from low-level acceptance alone
- not claimed: license/DRM bypass or patching official EXE/DLLs

The current corpus lives under:

- `reverse_usarthmi/hmi_donor_lowlevel_probe_20260522`

Start with:

- `donor_patch_capability_matrix.md`
- `donor_patch_capability_summary.json`
- `lowlevel_compatible_control_map.json`
- `reopen_safe_control_map.json`
- `fixture_corpus/corpus_manifest.json`

Important current nuance:

- current exact donors `case42/43/44/80/83/85` are accepted by the low-level gate
- a historical exact `case80` sample still exists as a failed low-level record
- `case80_like_from_case83_delete_b1` remains the canonical generated
  case80-like sample for dynamic snapshot handoff

Current silent-compatible generator entry:

- `python tools\generate_lowlevel_compatible_fixture.py <control_type> --out-dir <dir>`
- `python -m usarthmi --json hmi lowlevel-compatible-fixture <control_type> --out-dir <dir>`
- `usarthmi.hmi_donor_patch.generate_lowlevel_compatible_fixture(...)`

This is the current recommended path when you want one modified HMI for a
control type and your primary gate is official `open-lowlevel` /
`compile-lowlevel` without claiming GUI reopen evidence.

Current reopen-safe generator entry:

- `python tools\generate_reopen_safe_fixture.py <control_type> --out-dir <dir>`
- `python -m usarthmi --json hmi reopen-safe-fixture <control_type> --out-dir <dir>`
- `usarthmi.hmi_donor_patch.generate_reopen_safe_fixture(...)`

This is the current recommended path when you want one modified HMI for a
control type and you want that generated HMI to stay within the current
reopen-safe corpus.

For the dynamic snapshot Goal A lane, feed only fixtures whose summary record
has `dynamic_snapshot_goal_a_ready=true`.

For an offline compile-style pass similar to the official editor's Compile
button, use `scene export`:

```powershell
python -m usarthmi --json scene export examples\polished_dashboard_demo\scene.json `
  --out-dir reverse_usarthmi\export_bundle `
  --seed "D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI" `
  --baseline-tft "C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft"
```

It always writes `export_report.json` plus preview/agent artifacts. When a seed
HMI is supplied it also tries to emit `output.hmi`; when a compatible baseline
TFT is supplied and writer guards pass, it tries to emit `output.tft`. A blocked
or skipped TFT build is reported instead of being mistaken for hardware proof.
When `output.tft` exists, the bundle now also writes `smoke.expect.json` and
includes recommended native `scene smoke` commands in the manifest so the next
live-runtime step can reuse scene-derived readbacks and marker checks without a
separate hand-maintained expectation file. The export bundle never opens COM36
or uploads.

For scenes that need more than simple readbacks or `printh` markers, add an
explicit `project.live_smoke` block in the scene itself. The current intended
split is:

- auto-generated smoke: stable readbacks plus simple button/down/up -> `printh`
  markers
- explicit `project.live_smoke`: method calls, post-click state changes,
  waits, file-system prep, and other runtime-specific sequences

`scene validate` / `scene check` now parse and validate this block directly, so
missing `command`, unsupported keys, or invalid attempt counts fail early as
scene-contract errors instead of turning into a later smoke surprise.

For a scene-driven offline-to-live handoff, the native CLI entrypoint is:

```powershell
python -m usarthmi --json scene smoke `
  examples\advanced_direct_tft_demo\data_record_text_select_button_case83_event_scene.json `
  --seed "D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI" `
  --baseline-tft "C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft" `
  --out reverse_usarthmi\caseC4_scene_smoke_cli
```

The older script wrapper still exists when a plain script path is more convenient:

```powershell
python tools\scene_smoke_runner.py `
  --scene examples\advanced_direct_tft_demo\data_record_text_select_button_case83_event_scene.json `
  --seed "D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI" `
  --baseline-tft "C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft" `
  --out reverse_usarthmi\caseC4_scene_smoke_runner
```

Both entrypoints build the scene, resolves the generated sibling
`smoke.expect.json`, and returns an offline readiness summary. Add `--preflight`
for serial-readiness probing, or `--smoke --upload` to continue into live
runtime checks using the same generated smoke bundle.

To reduce parallel truth during migration, `scene smoke` also supports:

- `--check-expect[=<path>]`: compare the scene-generated payload against an
  existing legacy `smoke.expect.json`
- `--write-expect[=<path>]`: rewrite a legacy `smoke.expect.json` from the
  scene-generated payload

When the path is omitted, the command uses the conventional sibling path such
as `*_scene.json -> *_smoke.expect.json`.

For a directory-level convergence snapshot, run:

```powershell
python tools\scene_smoke_migration_audit.py `
  --out examples\advanced_direct_tft_demo\live_smoke_migration_audit_2026-05-20.json
```

This reports how many scenes already declare `project.live_smoke`, how many
legacy sibling `smoke.expect.json` files still exist, how many of those match
the scene-generated payload exactly, and which legacy files are now orphans.

Scene-model event scripts can be listed and edited through the CLI or the Agent
Editor event tab:

```powershell
python -m usarthmi --json scene new examples\new_project\scene.json --name NewProject
python -m usarthmi --json scene save-as examples\new_project\scene.json examples\new_project\scene_copy.json
python -m usarthmi --json scene events list examples\event_demo\scene.json --non-empty
python -m usarthmi --json scene events lint examples\event_demo\scene.json
python -m usarthmi --json scene events graph examples\event_demo\scene.json
python -m usarthmi --json scene events snippets
python -m usarthmi --json scene events set examples\event_demo\scene.json page0.evtbtn.up --line "printh 23 02 55 50"
python -m usarthmi --json scene events append-command examples\event_demo\scene.json page0.evtbtn.up --command vis --target status0 --value 1
python -m usarthmi --json scene events commands list examples\event_demo\scene.json page0.evtbtn.up
python -m usarthmi --json scene events commands replace examples\event_demo\scene.json page0.evtbtn.up --index 0 --command page --target page1 --dry-run --simulate --out-dir reverse_usarthmi\event_patch
python -m usarthmi --json scene events set examples\event_demo\scene.json page0.evtbtn.up --from-file event.txt
python -m usarthmi --json scene simulate examples\event_demo\scene.json page0.evtbtn.up --out-dir reverse_usarthmi\event_sim
python -m usarthmi --json scene scenario run examples\event_demo\scene.json examples\event_demo\scenario_printh.yaml --out-dir reverse_usarthmi\scenario
python -m usarthmi --json tft event-index inspect --hmi path\to\source.HMI --tft path\to\official.run --out reverse_usarthmi\event_index.json
python -m usarthmi --json tft event-index batch path\to\case_root --out reverse_usarthmi\event_index_batch.json
python -m usarthmi --json editor audit
```

This is the authoring/agent handoff layer for known scene slots. Event linting
recognizes a guarded subset (`page/ref/vis/tsw/click/get/set/printh/delay`),
preserves unknown raw lines, and emits page/object reference diagnostics plus a
navigation graph for agent review. It does not claim complete official USART
HMI event compiler compatibility or live behavior for event paths that lack
fixture, bytecode, or hardware proof.
`scene events append-command` is the structured command-builder path for agents:
it appends guarded commands such as `page`, `vis`, `tsw`, `click`, `set`,
`printh`, and `delay` without asking the agent to hand-format the source line.
`scene events commands` is the command-level patch path: agents can
list/insert/replace/delete/move individual event lines, request a dry-run diff,
and optionally run before/after offline simulation without writing the scene or
touching COM36.

`editor audit` is the current parity checklist for the official-editor-like
goal. It reports implemented desktop, page/project, widget, layout, agent
handoff, and import/export surfaces, includes a prompt-to-artifact checklist
for agent review, and keeps event logic marked as a guarded subset until
official compiler/scheduler equivalence is proven.

`scene simulate` runs the same guarded subset as an offline state trace. It
records current page, widget attributes, visibility, touch-enabled state,
simulated delay time, and `printh` output, and can write `runtime_trace.json`,
`runtime_state.json`, and `simulation_report.json` for agent review. It never
opens serial, uploads, or proves official scheduler, bytecode, physical touch,
timing, media, or file-system behavior.
The simulator also handles a small official-script assignment expression subset
for agent review, including bare `sys0=28*5`, object-to-object assignments,
string concatenation, and string/numeric `+=` updates.
`scene scenario run` builds on the simulator for multi-step regression scripts:
YAML/JSON steps can trigger event slots and assert `current_page`,
`elapsed_ms`, `printh_hex`, or widget paths such as `page0.num0.val`. It writes
`scenario_report.json` plus runtime trace/state, and still stays offline.
`tft event-index inspect` is the read-only compiled-TFT evidence path: it
compares HMI source event slots with event tables, callback-slot candidates, and
post-primary page-load chunks found in an official or generated `.tft`/`.run`.
It is specifically for narrowing scheduler/index/flags gaps and always keeps
`safe_to_flash=false`. For multi-page HMI fixtures it now also reports
`all_page_summary` and compact `additional_pages` entries for non-`0.pa`
resources; those extra pages scan non-empty event blocks only, so keyboard and
helper pages expose useful event matches and unsupported-bytecode examples
without turning the report into an empty-table search dump.
`tft event-index batch` scans HMI files or case folders, picks nearby official
compile outputs when present, and summarizes which fixtures still lack an
event-index oracle or complete scheduler evidence for agent follow-up.
The current advanced-control batch evidence for case 38/41/42/43/44 is recorded
in `examples/event_index_batch_3841424344_2026-05-18.json`; it includes both
scheduler classification and remaining bytecode/scheduler blockers. The
case 38 text-select and case 41 sliding-text object events now byte-match their
official TFT event tables as `object_callbacks_only` complete probes. The case
42 data-record source events now compile, and `data0/b0/b1/b2/b3` object-event
tables byte-match the official TFT; its page-load `repo` path still lacks page
callback/scheduler proof. `event-index inspect` now records the official
page-load `repo` command candidate at `0x70B`
(`09 18 08 01 e5 00 00 00`) for the next narrowing pass. The case 43/44 file
startup scripts now compile through the visible
`findfile/newfile/if/page` source flow, but official TFTs still append hidden
unload/runtime callbacks. `page_event_prefix_probe` now records that their
visible page-event prefix byte-matches at `0x2348`, separates the immediate
hidden unload item as a no-arg method call on slot `0xBF`, and exposes a
following complete-item preview with `"当前路径：" + field 0x89`,
`if_field_ne` for `fbrowser0.txt!=""`,
`btnOpenFile/btnRenameFile/btnDelFile` visibility toggles, and
`spstr fbrowser0.txt,t0.txt,".",1` decoded as field slot `0x8E -> 0x207`.
The same `spstr` shape now compiles back to the official payload using the
case43/44 file-storage page slot-width rule; the UTF-8
`fbpath.txt="当前路径："+fbrowser0.dir` expression and
`if(fbrowser0.txt!="")` condition do too. Field+field path concatenation,
`delfile`, `btlen`, no-else `if(field<field)`, `&txt&` / `&id&`
current-object placeholders, the `dp` operand, selected page-qualified
file/keyboard helper slots, and the exact official file-open branch script are
also fixture-proven for the observed shapes. The batch report now exposes all
11 case43/case44 `2.pa`/`main` object-event byte matches with zero main-page
compile errors, plus `27095` all-page compiled event-table matches and `85`
remaining helper-page compile errors. The callback/runtime binding is still
unrecovered.

The case51 minimal scheduler-oracle handoff now lives in
`C:\Users\SinYu\Desktop\case_for_codex\case_51_scheduler_minimal_oracle`.
It adds official source-HMI plus complete `output/source_raw.tft` evidence for
page0 load/loadend, button down/up, timer tick, and page1 load. The saved
`examples\case51_*.json` reports locate page0 load at `0x327`, button table
`0x18B` / first executable `0x197`, timer table `0x1C7` / first executable
`0x1D4`, and page1 load at `0x45A` with `global_slot_offset=149` and
`page1.t0.txt` field slot `0xD2`. Page-load phase descriptors now preserve
64 bytes before and 512 bytes after the matched phase and scan LE32 references
to phase start, first executable, and phase end; neither page0 `0x327` nor page1
`0x45A` has a recovered object-region LE32 dispatch reference. These are
compiler-oracle facts only; runtime dispatch remains unmapped.

The case52 lifecycle-delta oracle now adds six official GUI-saved HMI plus
complete official TFT pairs under
`C:\Users\SinYu\Desktop\case_for_codex\case_52_page_lifecycle_delta_oracle`.
The `examples\case52_*.json` reports show page0 load/loadend phases staying at
`0x2AB`; load+loadend is one merged phase with prefix length `47`, the longer
load body has prefix length `50`, and none of those page0 phases has a direct
LE32 dispatch reference. The same payload in button-up form uses the object
callback table (`0x18B` / first executable `0x1A1` / `slot_0x10`). The page1
candidate now sits at `0x255` and reports one `prefix_end` reference at `0x1AEB`,
but `examples\case52_lifecycle_dispatch_candidates_20260518.json` shows the
referenced value `0x272` is also `event_table_start` for primary
`page0/t0/bar1`. That alias means it is not runtime scheduler proof.
The same report now includes `lifecycle_record_fields`: across case51+case52
page-load oracles, page record callback slots `0x0c/0x10/0x14` stay empty
(`0xFFFFFFFF`), while `event_offset_0x34` points at a page event-table boundary
or, for clean case52-06, the `0x272` phase-end/wrapper boundary. The combined
`examples\case51_case52_lifecycle_dispatch_candidates_20260518.json` keeps this
negative evidence next to the object callback controls, where button/timer slots
do point at first executable bytecode.

Scene widgets can also be adjusted headlessly for agent handoff:

```powershell
python -m usarthmi --json scene assets list examples\event_demo\scene.json
python -m usarthmi --json scene assets add examples\event_demo\scene.json logo --source assets\logo.png
python -m usarthmi --json scene assets update examples\event_demo\scene.json logo --normal assets\logo-normal.png
python -m usarthmi --json scene assets delete examples\event_demo\scene.json logo --force
python -m usarthmi --json scene project update examples\event_demo\scene.json --name EventDemo --default-page page0 --background-color 65535
python -m usarthmi --json scene pages add examples\event_demo\scene.json page1
python -m usarthmi --json scene pages update examples\event_demo\scene.json page1 --id settings --layout-json '{\"type\":\"absolute\"}'
python -m usarthmi --json scene pages duplicate examples\event_demo\scene.json page0 --id page2
python -m usarthmi --json scene pages delete examples\event_demo\scene.json page2
python -m usarthmi --json scene widgets update examples\event_demo\scene.json page0.evtbtn --x 40 --text "Run" --resource asset=logo
python -m usarthmi --json scene widgets copy-to examples\event_demo\scene.json page0.evtbtn page0 --id evtbtn_paste
python -m usarthmi --json scene widgets duplicate examples\event_demo\scene.json page0.evtbtn --id evtbtn_copy
python -m usarthmi --json scene widgets duplicate examples\event_demo\scene.json page0.evtbtn --id evtbtn_copy2
python -m usarthmi --json scene widgets cut examples\event_demo\scene.json page0.evtbtn_paste
python -m usarthmi --json scene widgets move examples\event_demo\scene.json page0.evtbtn_copy --direction up
python -m usarthmi --json scene design align examples\event_demo\scene.json page0.evtbtn page0.evtbtn_copy --edge left --anchor first --out-dir reverse_usarthmi\design_session
python -m usarthmi --json scene design distribute examples\event_demo\scene.json page0.evtbtn page0.evtbtn_copy page0.evtbtn_copy2 --axis horizontal --out-dir reverse_usarthmi\design_session
python -m usarthmi --json scene design match-size examples\event_demo\scene.json page0.evtbtn page0.evtbtn_copy --mode width --anchor first --out-dir reverse_usarthmi\design_session
python -m usarthmi --json scene widgets delete examples\event_demo\scene.json page0.evtbtn_copy
python -m usarthmi --json scene widgets delete examples\event_demo\scene.json page0.evtbtn_copy2
python -m usarthmi --json scene design move examples\event_demo\scene.json page0.evtbtn --x 80 --y 96 --out-dir reverse_usarthmi\design_session
python -m usarthmi --json scene design resize examples\event_demo\scene.json page0.evtbtn --w 140 --h 48 --out-dir reverse_usarthmi\design_session
```

The `scene design` commands are the canvas-style edit path used by the GUI. They
write the scene geometry, can align, distribute, or same-size multiple widgets for agent layout cleanup,
and also emit `design_session.json`, `agent_patch.json`, and
`scene.modified.json` for agent review or replay. They do not build or upload
hardware artifacts.

The desktop `usarthmi-preview.exe` now exposes the same scene-authoring layer in
a GUI: an object tree, canvas preview, Properties form, Toolbox add-widget form,
Project/Page settings form, Events editor with command snippets and `Save+Simulate`
offline event traces, diagnostics, and agent artifact
panel. The top toolbar includes scene-file Undo/Redo for GUI edits. The object tree can add/copy/delete pages, copy/cut/paste/duplicate/delete widgets, and
move them up/down/front/back in page z-order; multi-selecting widgets enables Align Left,
Align Top, H Center, V Center, Dist H, Dist V, Same W, Same H, and Same Size.
Selecting a page and pressing `Preview Page` regenerates the preview bundle for
that page; selecting a widget makes Preview Bundle target that widget's page.
When the object tree or preview canvas has focus, `Delete` deletes the selected
widget, `Ctrl+C`/`Ctrl+X`/`Ctrl+V` copy, cut, and paste it, and `Ctrl+D` duplicates it.
The Project tab can edit project name,
default page, canvas width/height/background, page id, and page layout JSON.
Page rename is scene-only and reports event-script references that still need
manual review; widget rename reports same-page event-script references that
still mention the old object id, or can rewrite them when `--rewrite-event-references`
or the GUI checkbox is explicitly used. The Assets tab can add/update/delete scene image assets and
blocks normal deletion while widgets still reference an asset unless forced.
Properties and Toolbox can edit `id/type/x/y/w/h/text/value` plus JSON-backed
`style/resources/bindings`; Toolbox `Load Template` fills starter dimensions,
text/value, style, and resource JSON for registered widget types. The top bar can create a new blank scene or save
the current scene under a new path. `Import HMI` opens an official `.HMI`,
creates an imported scene/preview/report directory, and then loads that scene for
editing. The preview canvas supports click-to-select, drag-to-move,
bottom-right-handle resize, and arrow-key nudging for the selected object; each
drag/resize/layout edit uses the Snap value in the preview toolbar and writes a
design agent patch in the output directory. Tree-based
alignment/distribution/same-size editing uses the same design patch path. `Check Scene` runs the offline
diagnostics and bounded event-simulation report, while `Export Bundle` runs the
same offline compile-style report path from the GUI. It edits the scene
file and regenerates preview/context artifacts; flashing remains a separate
explicit command.

For a double-clickable workflow, use `dist\usarthmi-preview.exe`. Its window is
an editor-style shell with an object tree, canvas preview, annotated agent
overlay, inspector, diagnostics table, and agent artifact panel. The `Build TFT`
button can emit HMI/TFT artifacts, but it still does not upload.

## Safety Notes

- Keep generated `.TFT`, `.HMI`, `.zi`, screenshots, official binaries, and
  large fixtures out of git. The repository `.gitignore` is set up for that.
- Prefer full `tft upload` over trying to reuse the official editor's
  "skip unchanged blocks" downloader. The latter was observed to leave Windows
  USB/PnP in a ghost-COM state on the development machine.
- Live smoke upload helpers use the same serial-health preflight as the CLI:
  a matching `connect` model is not enough; `sendme` and `get dim` must also
  respond before public `whmi-wri` upload is attempted.
- For burn-and-check loops, add `--verify-after-upload` and one or more
  `--verify-get obj.attr=value` assertions. The verification runs even when
  `--skip-if-current` skips an identical file, and a failed verification keeps
  the upload result from being recorded as the new known-current manifest. Add
  repeatable `--verify-step` commands for runtime actions such as `sendme`,
  `get numval.val => 124`, `click incbtn,1 => hex:23 02 4e 31`, media enable
  toggles, or follow-up reads. Add `--verify-capture` when the visual state also
  matters.
- Do not copy official `work\a-*\output\*.tft` while the official serial
  download is actively transferring. Copy it before starting transfer or after
  the transfer has fully finished.
- For official GUI oracle work, the final HMI must pass a pre-compile
  confirmation gate before running Compile: reopen the exact HMI in the
  official editor, capture `before_official_compile_confirmation.png`, close
  and save through the official GUI, inspect the saved object list/event
  scripts, and write `precompile_confirmation.json`. If that manifest does not
  show the expected object names, type codes, and required event lines, the case
  is invalid and must not be compiled as a positive oracle.
- The repository is MIT licensed. Reverse-engineering notes and code are open,
  but official editor binaries and proprietary payloads still stay out of git.

## Current Capabilities

- Serial command CLI for `connect`, `sendme`, `get`, `set`, `page`, `ref`,
  `vis`, `tsw`, `click`, and `dim`.
- Lightweight `.HMI` inspection and extraction helpers, including structured
  `0.pa` object/event summaries for official TJC sample projects.
- Scene JSON/YAML authoring helpers and PNG preview rendering.
- Direct `.HMI` / extracted `.pa` page preview rendering with object labels and
  embedded picture resource support.
- Preview rendering can use real `.zi` glyph data, including GB2312 Chinese
  fonts, instead of approximating text with Windows fonts.
- Runtime serial preview for simple scene layouts.
- Font subset generation helpers around the local ZiCli tool.
- Full-codepage GB2312 font generation for practical Chinese/English UI
  baselines.
- Experimental in-place TFT font replacement: a generated `.zi` can replace the
  embedded font resource in a TFT while preserving section addresses.
- Scene/TFT builds can take `--font-zi` to patch the same `.zi` into
  `output.hmi` and the safe in-place TFT font slot in one build.
- TFT inspection/checksum helpers using a small vendored copy of TFTTool.
- Experimental same-layout TFT patching for text/coordinate changes.
- Experimental appended-object TFT tail generation for the current seed layout:
  adding one or more `t`, `b`, or `p` objects can be compiled into a flashable
  TFT tail.
- Scene builds can now route through that appended-object TFT generator when a
  compatible baseline TFT is supplied, emitting `output.hmi`, `output.tft`,
  `manifest.json`, `smoke.expect.json`, and previews from one JSON/YAML scene.
- Experimental TFT picture-resource packing for scene `image` widgets: local
  PNG/JPG assets can be compiled into new `pic` resources inside the fixed TFT
  resource area and referenced by appended picture objects.
- Picture resource import handles JPG/JPEG source preservation, EXIF-oriented
  image loading, transparent PNG flattening to the screen's RGB format, 16-pixel
  storage padding, and automatic quality/scale reduction when the fixed TFT
  resource budget is tight.
- Experimental multi-state image-button packing: normal/pressed button assets
  can be packed into TFT picture resources and written into the compiled button
  background slots for live-screen testing.
- Fixture-backed official widgets can be authored from scenes and compiled into
  the current page0 TFT tail, including virtual float / `xfloat` (`type=';'`),
  combo box / `combobox` (`type='='`), touch capture (`type=0x05`), and the
  current-editor external-picture record shape (`type='<'`). External-picture
  is live-proven when compiled against the healthy `case_00_baseline` resource
  layout; `case_46_expicture_current_gui` remains the tail/reference fixture,
  not the recommended live baseline.
- First-pass media widget authoring is available for animation / `gmov`
  (`type=0x02`), video (`type=0x03`), and audio / `wav` (`type=0x04`) in HMI and
  preview outputs. Single internal GMOV builds, a narrow single SD-video object
  smoke, and a narrow single SD-audio object smoke are available for the current
  layout; broad media playback/resource scheduling is still research-only.
- `tools/probe_official_widget_support.py` can clone one object from a
  downloaded official/sample HMI into the current seed and ask the official
  compiler whether the current target actually emits that extra object.

## What Is Not Included

Large or potentially proprietary artifacts are intentionally not committed:

- official `.HMI` / `.TFT` / `.zi` payloads
- extracted USART HMI editor binaries
- generated build directories
- local screenshots and serial upload logs
- third-party example HMI/TFT repositories used as research references

Some local tests are skipped automatically when those optional fixtures are not
present.

## Install

```powershell
python -m pip install -e .
```

Dependencies are declared in `pyproject.toml`.

## Project Layout

- `usarthmi/`: Python package and CLI implementation.
- `examples/`: small scene files that demonstrate recovered controls.
- `tests/`: unit and fixture-backed regression tests. Some tests skip
  automatically when private/local fixtures are absent.
- `tools/`: local helper scripts for live smoke tests, official-editor fixture
  capture, camera capture, and widget probes.
- `SCENE_BUILDER.md`: scene authoring and build examples.

## Test Tiers

Use the tiered entrypoints instead of defaulting to a full raw `pytest` run:

```powershell
python tools\run_smoke.py
python tools\run_acceptance.py
python tools\run_official_probe_tests.py
python tools\run_full_tests.py
```

- `smoke`: default daily loop. Fast offline checks only, intended to stay in the
  30 second to 2 minute range.
- `acceptance`: close-out lane before handoff or commit. Covers the smoke tier
  plus donor-patcher acceptance checks, donor summary JSON, and static/dynamic
  index structure checks.
- `official_probe`: explicit opt-in only. Use this when you are changing
  official-tool probe code or need to validate official GUI/low-level probe
  integrations on a machine that has those local prerequisites.
- `full`: broad repo regression for larger changes. It includes the whole normal
  suite, but tests marked `official_probe` are still gated and stay skipped
  unless you deliberately opt in.

If you need the broad suite plus official-tool probes in one go, run:

```powershell
python tools\run_full_tests.py --include-official-probe
```

Manual marker examples:

```powershell
python -m pytest -m smoke
python -m pytest -m acceptance
python -m pytest -m official_probe --run-official-probe
python -m pytest -m full
```

Agent/default guidance:

- daily edit loop: run `python tools\run_smoke.py`
- before handoff / close-out: run `python tools\run_acceptance.py`
- only when the work actually touches official-tool probe paths: run
  `python tools\run_official_probe_tests.py`
- do not casually run `full` on a machine with expensive local fixtures,
  hardware, or official GUI dependencies unless the change is large enough to
  justify the time

## Serial Examples

```powershell
python -m usarthmi --json connect --port COM36 --baud 9600
python -m usarthmi --json sendme --port COM36 --baud 9600
python -m usarthmi --json get t0.txt --port COM36 --baud 9600
python -m usarthmi --json set t0.txt '"hello"' --port COM36 --baud 9600
python -m usarthmi --json dim 30 --port COM36 --baud 9600
```

## HMI / Scene Examples

```powershell
python -m usarthmi --json inspect-hmi path\to\lcd_test.HMI
python -m usarthmi --json extract-hmi path\to\lcd_test.HMI --out hmi_extract
python -m usarthmi --json hmi import path\to\lcd_test.HMI --out-dir hmi_import --overwrite
python -m usarthmi --json hmi preview --hmi path\to\lcd_test.HMI --out hmi_preview.png
python -m usarthmi --json hmi preview-pa --pa hmi_extract\0.pa --assets-dir hmi_extract --out pa_preview.png
python -m usarthmi --json scene validate examples\menu_demo\scene.json
python -m usarthmi --json scene preview examples\menu_demo\scene.json --out preview.png
python -m usarthmi --json hmi preview-pa `
  --pa reverse_usarthmi\font_baselines\ui_cn_en_32\build_stock\target_0.pa `
  --out reverse_usarthmi\font_baselines\ui_cn_en_32\preview_zi_font.png `
  --font 0=reverse_usarthmi\font_baselines\ui_cn_en_32\UiCNEN32GBFull.zi `
  --no-labels
python -m usarthmi --json tft build `
  --scene reverse_usarthmi\live_scene_build\scene_multi.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\live_scene_build
python -m usarthmi --json scene build examples\external_picture_demo\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\external_picture_demo_build
python tools\external_picture_demo_runner.py
python tools\external_picture_demo_runner.py --skip-build --smoke --capture
python -m usarthmi --json scene build examples\media_widgets_demo\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --out reverse_usarthmi\media_widgets_demo_build
```

`inspect-hmi` reports raw strings plus parsed page/object event scripts such as
`codesload-*`, `codesdown-*`, `codesup-*`, and `codestimer-*` when `0.pa` is a
known layout.

## TFT Patch Examples

Same-layout patch:

```powershell
python -m usarthmi --json tft patch-basic `
  --baseline-tft path\to\baseline.tft `
  --baseline-pa path\to\baseline\0.pa `
  --target-pa path\to\target\0.pa `
  --out patched.tft
```

One or more appended objects, current seed layout only:

```powershell
python -m usarthmi --json tft patch-add-object `
  --baseline-tft path\to\baseline.tft `
  --baseline-pa path\to\baseline\0.pa `
  --target-pa path\to\target_with_one_or_more_added_objects\0.pa `
  --out added_object.tft
```

Upload:

```powershell
python -m usarthmi --json tft health `
  --port COM36 `
  --baud 9600 `
  --timeout-ms 3000 `
  --expected-model TJC8048X543_011C

python -m usarthmi --json tft preflight `
  --file added_object.tft `
  --port COM36 `
  --baud 9600 `
  --expected-model TJC8048X543_011C

python -m usarthmi --json tft readiness `
  --file added_object.tft

python -m usarthmi --json tft upload `
  --file added_object.tft `
  --port COM36 `
  --baud 9600 `
  --download-baud 921600 `
  --expected-model TJC8048X543_011C `
  --skip-if-current `
  --verify-after-upload `
  --verify-get t0.txt=nihao `
  --verify-step '{"command":"sendme","expected_kind":"page_id","expected_value":0}' `
  --verify-capture `
  --progress
```

`tft readiness` is the offline gate: it checks the TFT checksum and, when a
sibling `manifest.json` exists, reports `delivery_status`,
`oracle_alignment`, `hardware_quarantine`, and any active SD-recovery block.
Use it first when you only need to decide whether a build artifact should even
be considered for hardware upload.

`tft upload` runs checksum and serial-health preflight by default. Use
`--no-preflight` only for deliberate recovery or reverse-engineering probes.
After a successful public upload the CLI writes `.usarthmi_last_upload.json`
atomically. A later upload with `--skip-if-current` compares the candidate TFT's
SHA256/size plus the target port, baud, and expected model against that manifest
and skips before runtime preflight/upload when they match. The manifest is only a
record of the last successful upload performed by this tool; it is not proof that
the screen has not been changed by SD-card flashing, the official downloader, or
another machine.
When a build manifest declares `hardware_quarantine.active=true`, upload and live
smoke are blocked by default even if checksum/model preflight would otherwise
pass. Use `--allow-hardware-quarantine` only when there is an explicit
recovery/live plan. The older `--allow-quarantined-touch-capture` flag is still
accepted for backward compatibility, but the generic hardware-quarantine flag is
the intended override path going forward.
Add `--verify-after-upload` plus `--verify-get obj.attr=value` assertions when
the upload must be followed by serial readback. If verification fails, the
command returns non-zero and does not update the known-current manifest.
Add repeatable `--verify-step` entries when the post-upload proof needs runtime
actions, for example `{"command":"sendme","expected_kind":"page_id","expected_value":0}`.
For common readback/click checks, shorthand is usually easier:
`get numval.val => 124` or `click incbtn,1 => hex:23 02 4e 31`. Media
sequences can still use JSON, such as `{"command":"wav0.en=1","expect_response":false}`
followed by `{"command":"get wav0.en","expected_kind":"number","expected_value":1}`.
For visual evidence, add `--verify-capture`; by default it saves a camera frame
under `reverse_usarthmi/upload_verify_captures/` using the local MSMF camera
path that has been reliable on this workstation.

Replace the embedded TFT font with a generated `.zi`:

```powershell
python -m usarthmi --json tft patch-font `
  --baseline-tft output.tft `
  --font custom.zi `
  --out output_custom_font.tft
```

Patch a generated `.zi` during a normal scene/TFT build:

```powershell
python -m usarthmi --json tft build `
  --scene examples\number_demo\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --font-zi reverse_usarthmi\font_baselines\ui_cn_en_32\UiCNEN32GBFull.zi `
  --out reverse_usarthmi\number_demo_font_build
```

Generate the verified Chinese/English 32px baseline font:

```powershell
python -m usarthmi font generate-zi `
  --out reverse_usarthmi\font_baselines\ui_cn_en_32\UiCNEN32GBFull.zi `
  --font-file C:\Windows\Fonts\SourceHanSansCN-Normal.ttf `
  --name UiCNEN32GBFull `
  --height 32 `
  --font-size 34 `
  --codepage gb2312 `
  --full-codepage `
  --no-ascii
```

## Verification Status

The local development session verified:

- same-layout text patch `nihao -> buhao` was flashed and read back from a real
  `TJC8048X543_011C` panel.
- one added text object `t1` was flashed and queried successfully with
  `get t1.txt` and `get t1.x`.
- arbitrary object name `note1` was flashed and queried successfully with
  `get note1.txt`, proving the recovered object-name hash algorithm live.
- three appended objects `note1`, `btn1`, and `pic1` were flashed together and
  queried successfully from the real panel.
- scene-driven build emitted a valid multi-object `output.tft` with
  `note1/btn1/pic1` via the same generator.
- scene-driven image build packed a new JPG resource as `pic=1`, flashed it,
  and read back `photo1.pic == 1` from the real panel.
- an inferred image-button build packed normal/pressed PLAY assets, flashed the
  result, and read back `playbtn.sta == 2`, `playbtn.bco == 1`, and
  `playbtn.bco2 == 2` from the real panel.
- custom `.zi` font replacement is now visually confirmed: an ordered ASCII
  `Impact56Ordered` font was generated, patched into a scene TFT, flashed, and
  photographed on the real panel with correct text and changed glyph shapes.
  Earlier unordered/UTF-8 generated fonts were loaded by the panel but produced
  wrong glyph mapping, which exposed and fixed the ZiCli glyph-order bug.
- Chinese/English 32px baseline font replacement is visually confirmed with
  `UiCNEN32GBFull.zi`: the generated full GB2312 font was patched into a scene
  TFT, flashed to `COM36`, and photographed with correct `主菜单`,
  `开始/设置/系统/返回`, `状态/正常/温度`, and mixed ASCII text. A sparse GB2312
  subset test rendered Chinese as repeated wrong glyphs, so Chinese currently
  uses `--full-codepage`.
- `.zi`-backed preview rendering is now available: `preview-pa`, `hmi preview`,
  and `scene preview` accept `--font 0=path\to\font.zi`; `hmi preview` also
  auto-loads embedded `N.zi` entries from the HMI container.
- the same `FONT TEST 123` object was rebuilt with the stock embedded font,
  flashed, and read back with `fontmsg.txt_maxl == 13`,
  `fontmsg.style == 1`, and `fontmsg.bco == 65504`.
- the picture-resource packer was corrected to preserve the official
  `unknown_objects_address == 0xAE0000` layout; a `PLAY + newtxt` scene was
  flashed, photographed, and read back with `fontmsg.txt == "newtxt"` and
  `playbtn.txt == "PLAY"`.
- official PLAY image resources are now reproduced byte-for-byte in both TFT
  and HMI forms: scene-generated `case13` / `case14` TFT files match the
  official editor outputs, and `output.hmi` contains matching `1.i`, `2.i`,
  `1.is`, and `2.is` entries for the current fixtures.
- a mixed JPG + transparent PNG + image-button stress scene was flashed to the
  real panel; an initial resource-table ordering bug swapped images on-screen,
  then sorting TFT picture records by `pic` id fixed the live display.
- `case_36_xfloat` is reproduced at compiled-tail level against the official
  GUI output, with `val/vvs0/vvs1` primary-record offsets locked by tests. This
  case is now live-flashed on `COM36` in the `xfloat_combobox_demo` smoke scene,
  with `get xval.val` returning `123456`.
- `case_37_combobox` is reproduced at compiled-tail level against the official
  GUI output, including compact primary-string layout and dual `txt/path`
  pointers. This case is now live-flashed in the same smoke scene, with
  `get cbval.val` returning `2` and `get cbval.txt` returning `80V`.
- `case_46_expicture_current_gui` supersedes the older grafted
  `case_40_expicture` sample as the real current-editor "外部图片" tail fixture:
  its object record and `path` string slot are reproduced byte-for-byte against
  official GUI output. Live flashing later proved the control itself works on
  the current X543 panel when compiled from the healthy 11.4 MB
  `case_00_baseline` resource layout: `sendme` returned page `0`,
  `get exp0.path` returned `sd0/1.jpg`, and the SD image was visible on camera.
  The compact `case_46` resource/header baseline still makes the panel return
  the short `66 FF FF FF` `sendme` frame, so it is kept as a reference fixture
  only, not a runtime baseline.
- `case_38_text_select`, `case_41_sltext`, `case_42_datarecord`,
  `case_43_filebrowser`, and `case_44_filestream` have now been rebuilt by
  real official GUI toolbox clicks, not by binary grafting. Each saved
  current-target `.HMI` contains the new control (`D`, `>`, `B`, `A`, `?`),
  and each official compile emits a fifth object in
  `work\a-*\output\lcd_test.tft`. Text-select, sliding-text, data-record,
  file-browser, and file-stream are now supported on the current target through
  fixture-backed current-target writers: the audited donor/edit paths byte-match
  the official outputs where required and have COM36 readback evidence. The
  file/data controls still keep narrower claim boundaries, so arbitrary
  property synthesis, mixed same-page native synthesis outside the documented
  cases, unsupported event paths, and file-system/data side effects remain
  unclaimed. The
  machine-readable index is
  `examples/advanced_widget_case_outputs_2026-05-17.json`; the case-folder
  explanation is
  `C:\Users\SinYu\Desktop\case_for_codex\CASE_38_44_COMPLETION_20260517.md`.
- Experimental official GUI automation now has a declarative spec runner at
  `tools/official_hmi_automation.py`. It merges decompiled `appobjsclass.cs`
  control metadata, decompiled `HMIFORM\main.cs` toolbox ordering, and the
  current GUI calibration layer. `create-widget` now prefers a toolbox
  `message-index` lane driven from `RefGongjuItem()`: it walks the official
  control order with `WM_KEYDOWN/WM_LBUTTONUP` instead of relying only on
  fragile screen-Y clicks. The runner can orchestrate `select-page`,
  `create-widget`, `patch-field`, `patch-rect`, `patch-event`,
  `save-and-close`, `precompile-confirm`, and `compile-capture`. Dump the
  parsed control registry with:

```powershell
python tools\official_hmi_automation.py --dump-decompiled-registry
```

  Or inspect a resolved plan without touching the GUI:

```powershell
python tools\official_hmi_automation.py `
  --spec-json examples\official_gui_automation_specs\case73_page1_textselect_minimal.json `
  --dry-run
```

  If the GUI coordinate band drifts, the runner can also consume existing
  toolbox scan output through `page0_scan_report` / `page1_scan_report` in the
  automation spec. Generate a scan report first with:

```powershell
python tools\official_gui_toolbox_scan.py `
  --out-dir reverse_usarthmi\toolbox_scan_page1_textselect `
  --page-index 1 `
  --y-values 320 334 348 `
  --wheel-values 0
```

  Then point the automation spec at the resulting `scan_report.json`; the
  runner will use `first_added_type` matches to override the default
  `tool_rel_y/toolbox_wheel` calibration for the affected controls.

  Multiple example specs are included:
  `examples\official_gui_automation_specs\case73_page1_textselect_minimal.json`,
  `examples\official_gui_automation_specs\case60_filebrowser_textselect_button_event.json`,
  `examples\official_gui_automation_specs\case60_filebrowser_textselect_button_event_gui_patch.json`,
  `examples\official_gui_automation_specs\page0_datarecord_slidingtext_minimal.json`,
  `examples\official_gui_automation_specs\page0_button_gui_patch_minimal.json`,
  `examples\official_gui_automation_specs\page0_button_gui_event_patch_minimal.json`,
  and `examples\official_gui_automation_specs\page0_existing_button_gui_patch_minimal.json`.
  The current worktree now has several real non-dry-run official GUI closure proofs:
  `case73` passes page1 `text-select` create + precompile-confirm +
  compile-capture; `case60` passes page0 `file-browser + text-select + button`
  create + offline patch + precompile-confirm + compile-capture; the
  `case60 ... gui_patch` variant replaces the button rename/rect/event steps
  with official GUI property-grid + event-editor edits and still passes
  precompile-confirm + compile-capture; `page0_datarecord_slidingtext_minimal`
  passes create + precompile-confirm + compile-capture;
  `page0_button_gui_patch_minimal` proves GUI property-grid editing for
  `objname/txt/x/y/w/h`; `page0_button_gui_event_patch_minimal` proves GUI
  event-editor writes a persisted `codesdown-1 / printh ...` script; and
  `page0_existing_button_gui_patch_minimal` proves the runner can re-select an
  already existing canvas object (`b0`) and then patch it through the official
  property grid before compile.

  The automation layer now also has decompiled-driven batch helpers:

  - `tools\generate_official_gui_automation_specs.py` writes one minimal spec
    per selected control from the decompiled toolbox order and objmark metadata.
  - `tools\run_official_hmi_automation_batch.py` executes a manifest/spec set
    and summarizes pass/fail/report paths.
  - `tools\build_official_gui_automation_control_matrix.py` condenses finished
    runs into a machine-readable control matrix.
  - `tools\probe_official_gui_controls.py` is the end-to-end entrypoint that
    generates specs, runs them, and emits a per-control matrix in one step.

  The current aggregated evidence is in
  `examples\official_gui_automation_control_matrix_2026-05-24.json`. It merges
  real control records from validated official GUI runs, including the curated
  page1/page0 advanced examples, the GUI property/event patch samples, and the
  auto-discovered page0 minimal create/compile lanes.
- local test suite passed with the available fixtures.

See `USART_HMI_STATUS_2026-05-04.md` for the detailed working log.
See `USART_HMI_ROADMAP_2026-05-04.md` for the remaining work plan and next
implementation priorities.

## Limitations

The TFT writer is not a complete replacement for the official editor yet. The
current independent generation path is deliberately narrow and optimized for
the known 800x480 seed project. Object-name hashing is solved for ASCII names up
to 14 bytes. New picture resources are proven for appended `image`/picture
objects and two-state image buttons, with current PLAY fixtures matching
official TFT outputs byte-for-byte and matching HMI `*.i` / `*.is` resource
payloads. Additional local tests cover JPG source entries, transparent PNG
flattening, non-16-aligned dimensions, and large-image shrink-to-budget behavior.
Multi-page generation, every-widget live behavior coverage, event-code
authoring, and broader font fixture coverage are still outside the proven V1
path. The current-target supported widget writer/offline rebuild boundary is
audited in `examples/all_supported_controls_completion_audit_2026-05-17.json`.
A minimal page0 full-page rebuild is live-proven for the number demo only:
`drop_seed_objects` removed seed `t0/b0/p0`, rebuilt
`page0/title/incbtn/numval`, and preserved the button event through full COM36
upload, serial readback, and camera proof. The
accepted visual proof uses `UiCNEN32GBFull.zi` plus `numval.lenth=3`; an earlier
UTF-8 sparse font build was serial-good but rendered wrong glyphs. A follow-up
offline reorder fixture, `examples/number_demo/reorder_broadening_scene.json`,
extends this path to `page0/status/incbtn/title/footer/numval` while keeping the
button before its later `numval` target. `examples/number_demo/event_matrix_scene.json`
adds offline same-page event-preservation coverage for clean rebuilt `ref`,
`vis`, `tsw`, and numeric `++` button events. Event bytecode
assembly has partial support (`printh`/`page`/`click`/`ref`/`vis`/`tsw`/`rawhex`):
object button events are live-proven for `printh`, `click`, `ref`, `vis`, and
numeric updates; `tsw` is compiled and dispatched in the isolated probe below,
but serial click remains a separate path. The `examples/number_demo` hardware
proof records a page0 button event that increments `numval.val` from `123` to
`125` and emits `23 02 4e 31` through `printh`. The isolated
`examples/number_demo/tsw_promotion_scene.json` live burn is recorded in
`examples/number_demo/tsw_promotion_serial_click_hardware_verified_2026-05-16.json`:
it proves the clean-rebuilt page uploads and that `disablebtn`/`enablebtn` reach
their T0/T1 `tsw targetbtn,0/1` event markers, but serial `click targetbtn,1`
still emits TG after `tsw targetbtn,0`. Treat that as a negative
serial-click-path result, not as physical touch-lockout proof; a fast
same-session 0/10/20/50/100/200 ms timing scan still saw T0 followed by TG in
all 18 critical trials, so the serial result is not caused by commands being
sent too slowly. The
`examples/event_combo_probe` smoke test proves a
single page0 button can execute multiple numeric event lines in order
(`val=10`, `++`, `++`, `--`) and be verified by serial readback.
Media event bytecode is now decoded in oracle reports, with official audio
fixtures proving `wav0.vid=0`, `wav0.en=1`, and `play 0,0,0` byte-for-byte.
Page-load runtime dispatch is not recovered yet. A 2026-05-15 single-page
`page0.load` probe and separate page1 callback-slot probes on `COM36` both
showed that the panel does not yet schedule generated page-load blocks; the
2026-05-18 case51 official oracles locate page0/page1 load bytecode phases but
still do not prove runtime callback binding. Event oracle reports now include
`scheduler_path`, `upload_risk`, and `recommended_writer_action` fields:
generated normal-table page-load probes are marked high risk, while official
media-style samples show a separate post-primary page-event chunk that remains
research-only until reproduced byte-for-byte for the target layout.
