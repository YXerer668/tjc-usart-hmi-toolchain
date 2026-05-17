# New Controls Demo

`scene.json` is the clean-rebuild fixture for fixture-backed non-media controls.
`smoke.expect.json` checks page `0` plus simple initial readback fields for the
value/text-like controls. `hardware_verified_2026-05-17.json` records the COM36
smoke that passed after the type-5 dual-state value writer was fixed.

This folder still does not claim live behavior for every object. Hotspot,
crop-image runtime attributes, waveform drawing, touch behavior, and
camera-only visual claims need separate focused live evidence before they can be
marked closed.
