# Feature Status

This project is evidence-driven. A feature is marked "implemented" only when it
has code plus at least one useful proof point such as a parser regression test,
fixture byte comparison, checksum validation, serial readback, or live-panel
camera verification.

Legend:

- **Stable**: intended for normal use in this repository's current workflow.
- **Experimental**: implemented, but narrow, fixture-shaped, or current-panel
  specific.
- **Authoring only**: scene/HMI/preview support exists, but independent TFT
  output is not considered flashable.
- **Research only**: useful reverse-engineering code or notes exist, but this is
  not a supported workflow.
- **Not implemented**: intentionally not available yet.

## Core Toolchain

| Area | Status | Notes |
| --- | --- | --- |
| Serial runtime CLI | Stable | `connect`, `sendme`, `get`, `set`, `page`, `ref`, `vis`, `tsw`, `click`, and `dim` use the public string protocol. |
| `.HMI` inspect/extract | Stable | Reads the recovered container layout and parses useful `0.pa` page/object/event metadata. |
| Scene JSON/YAML model | Stable | Supports validation, normalization, layout solving, and JSON/YAML round-trips. |
| Preview renderer | Stable | Renders scenes, extracted `.pa` pages, and `.HMI` files; can use real `.zi` glyphs. |
| Layout engine | Stable | `absolute`, `row`, `column`, `grid`, `stack`, and `anchor` resolve to fixed 800x480 coordinates. |
| Full serial upload | Stable | Uses the public upload protocol; slower than official smart download, but much safer to reproduce. |
| TFT checksum / inspection | Stable | Uses the recovered checksum path and a small vendored TFTTool helper. |
| Same-layout TFT patch | Stable | Live-proven for text/coordinate style changes on the current panel. |
| Page0 appended-object TFT build | Experimental | Can rebuild the current seed page tail and append known object records. |
| Picture-resource packing | Experimental | Packs local PNG/JPG assets into TFT picture resources; live-proven for image widgets and two-state image buttons. |
| Custom `.zi` font generation/patching | Experimental | Full GB2312 Chinese/English baseline is live-proven; sparse Chinese subsets are not reliable yet. |
| Multi-page TFT build | Experimental | Limited to the recovered two-page layout and plain page1 controls, including image widgets that reference an existing picture ID plus checkbox/radio values. |
| Event bytecode compiler | Research only | Can emit some `page`/`printh`/`click`/`vis`/`play`/assignment bytecode. The narrow `page1` normal-button jump-page path is fixture-tested behind `experimental_multi_page_events`, but live scheduling is not fully solved. |
| Official smart/sparse download | Research only | Captured and partially understood, but not recommended after USB/PnP instability on the test machine. |
| Full `.HMI` decompiler/editor replacement | Not implemented | The tool edits through a recovered scene model and seed project; it does not reconstruct every official editor feature. |
| Generic all-model TFT compiler | Not implemented | Current writer targets the recovered 800x480 `TJC8048X543_011C` seed layout. |

## Widget Status

| Widget / feature | Scene/HMI | Independent TFT | Evidence level |
| --- | --- | --- | --- |
| Page object | Implemented | Experimental | Required by all page builds. |
| Text | Implemented | Stable for current seed | Live serial readback and font tests. |
| Button | Implemented | Stable for current seed | Live multi-object tests. |
| Number | Implemented | Experimental | Fixture-backed and included in page1 plain-control path. |
| Image / picture | Implemented | Experimental | Live-proven with packed JPG resources. |
| Two-state image button | Implemented | Experimental | Live-proven with normal/pressed PLAY assets. |
| External picture / SD image | Implemented | Experimental | Live-proven against healthy `case_00_baseline`; `case_46` is fixture/reference only. |
| Custom font display | Implemented | Experimental | ASCII and full GB2312 baseline fonts visually verified. |
| Virtual float / xfloat | Implemented | Experimental | Byte-aligned fixture tests and live `get xval.val`. |
| Combo box | Implemented | Experimental | Byte-aligned fixture tests and live `get cbval.*`. |
| Slider | Implemented | Experimental | Fixture-backed record generation; allowed in page1 plain controls. |
| Gauge | Implemented | Experimental | Fixture-backed record generation; allowed in page1 plain controls. |
| Progress bar | Implemented | Experimental | Fixture-backed record generation; allowed in page1 plain controls. |
| QR code | Implemented | Experimental | Fixture-backed record generation. |
| Timer | Implemented | Experimental | Fixture-backed; event/runtime scheduling still limited. |
| Variable | Implemented | Experimental | Fixture-backed record generation. |
| Dual-state button | Implemented | Experimental | Fixture-backed record generation. |
| State button / switch | Implemented | Experimental | Fixture-backed record generation. |
| Hotspot / touch area | Implemented | Experimental | Fixture-backed record generation. |
| Waveform | Implemented | Experimental | Fixture-backed record generation; broad runtime drawing helpers are not complete. |
| Checkbox | Implemented | Experimental | Fixture-backed record generation. |
| Radio | Implemented | Experimental | Fixture-backed record generation. |
| Crop image | Implemented | Experimental | Fixture-backed record generation. |
| Scrolling text (`case_22`) | Implemented | Experimental | Fixture-backed record generation. |
| Touch capture (`case_45`) | Implemented | Experimental | Current-editor fixture-backed record generation. |
| GMOV animation | Implemented | Experimental | Single internal GMOV smoke path is the recommended media test. |
| Video | Implemented | Authoring only | HMI/preview and record-shape work exist; resource scheduling is not closed. |
| Audio / WAV | Implemented | Authoring only | HMI/preview and record-shape work exist; resource scheduling is not closed. |
| Text select (`case_38`) | Authoring probe only | Not implemented | Current target/editor compile dropped the grafted object. |
| Sliding text / `sltext` (`case_41`) | Authoring probe only | Not implemented | Current target/editor compile dropped the grafted object. |
| Data record | Authoring probe only | Not implemented | Current target/editor compile dropped the grafted object. |
| File browser | Authoring probe only | Not implemented | Current target/editor compile dropped the grafted object. |
| File stream | Authoring probe only | Not implemented | Current target/editor compile dropped the grafted object. |

## Practical Recommendations

- Use `examples/menu_demo` or `examples/external_picture_demo` to understand
  the stable scene flow.
- Use `examples/media_single_gmov_smoke` for animation work; do not mix GMOV,
  video, and audio in one flashable TFT until the scheduler is recovered.
- Use full `tft upload` for live-panel testing. Treat official smart download
  as reverse-engineering material, not the default deployment path.
- Keep private official fixtures and generated binaries outside git. If you add
  a new widget, add the smallest testable fixture notes and avoid committing
  large/proprietary payloads.
