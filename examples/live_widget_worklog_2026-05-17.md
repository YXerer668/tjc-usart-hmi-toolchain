# Live Widget Worklog - 2026-05-17

Objective: keep converging the TJC/USART HMI reverse-engineering workspace
toward committed build and live evidence for every current-target supported
control.

## Completed Main Lane

- Active item: external-picture live proof.
- Result: COM36 full upload and smoke passed on `TJC8048X543_011C`.
- Evidence being committed:
  - `examples/external_picture_demo/hardware_verified_2026-05-17.json`
  - `examples/live_widget_proof_matrix_2026-05-17.json`
  - `tests/test_live_tft_smoke.py`
- Verified command:
  - `python -m pytest -q tests/test_live_tft_smoke.py::LiveTftSmokeTests::test_external_picture_demo_smoke_expect_loads_readbacks tests/test_live_tft_smoke.py::LiveTftSmokeTests::test_external_picture_demo_hardware_evidence_matches_smoke_expect tests/test_editor_tft_build.py::EditorTftBuildTests::test_live_widget_proof_matrix_tracks_supported_control_runtime_gap tests/test_editor_tft_build.py::EditorTftBuildTests::test_external_picture_demo_full_page_rebuild_preserves_sd_path_object`
- Verified result: `4 passed, 26 subtests passed in 3.77s`.
- Boundary: no pixel-level assertion for SD-card image content beyond serial
  path readback and camera capture.

## Completed Main Lane

- Active item: normal image widget with newly packed picture resource.
- Result: COM36 full upload and smoke passed on `TJC8048X543_011C`.
- Evidence:
  - `examples/image_resource_demo/scene.json`
  - `examples/image_resource_demo/smoke.expect.json`
  - `examples/image_resource_demo/hardware_verified_2026-05-17.json`
- Runtime fields verified: `photo1.pic`, `photo1.id`, `photo1.x`, `photo1.y`,
  `photo1.w`, and `photo1.h`.
- Boundary: camera capture is useful visual evidence, but pixel-level
  image-content matching remains separate.

## Current Main Lane

- Status: planning.
- Active item: choose next live-proof target from `audio`, `crop-image`, or
  `waveform` after committing image evidence.

## Parallel Lanes

- Non-media controls explorer:
  - Agent: `019e3550-3deb-7381-a0bb-42825910fb29`.
  - Status: completed.
  - Scope: hotspot, touch-capture, waveform, crop-image, image.
  - Rule: read-only; no hardware or file edits.
  - Conclusion: lowest-risk next artifact is `image`, because historical live
    evidence already exists and the matrix only lacks a dedicated committed
    evidence JSON. `crop-image` is second; `hotspot`, `touch-capture`, and
    `waveform` need stronger physical-touch or visual behavior closure.
- Media controls explorer:
  - Agent: `019e3550-6012-78b0-b0f6-7da1004a54cc`.
  - Status: completed.
  - Conclusion: fastest committed media artifact is likely
    `examples/media_single_audio_sd_smoke`, because smoke and play expect files
    already exist. GMOV needs resource-backed scene work first; video readback
    does not prove playback quality.
- Audio proof planner:
  - Agent: `019e3557-0d14-7ec1-8995-d340d6f3c736`.
  - Status: completed.
  - Scope: exact build/smoke/play commands and evidence schema for
    `examples/media_single_audio_sd_smoke`.
  - Rule: read-only; no hardware or file edits.
  - Conclusion: build `examples/media_single_audio_sd_smoke`, then run one
    upload smoke with `smoke.expect.json` plus one no-upload play smoke with
    `play.expect.json`; this only proves object fields and `wav0.en`
    start/stop control, not speaker output or WAV compatibility.

## Remaining Known Gaps

- `crop-image`: needs camera/visual proof beyond current readback set.
- `hotspot`: needs real touch or proven-equivalent event proof.
- `touch-capture`: needs real touch input and serial/camera evidence.
- `waveform`: needs sample write plus visible drawing or readback proof.
- `animation`, `video`, `audio`: media live artifacts still pending; keep
  playback-quality claims separate from serial field readbacks.
