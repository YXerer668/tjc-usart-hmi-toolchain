# Touch-Safe Official Pipeline

`tools/codex_touchsafe_official_pipeline.py` is the reusable build path for
HMI cases that should go through the official USART HMI compiler without manual
mouse clicks.

The pipeline is intentionally conservative:

1. copy or patch an input `.HMI`
2. audit touch geometry, including hidden `endx` / `endy`
3. render a headless PNG/HTML preview and fail on layout collisions
4. save and compile through the official headless GUI bridge
5. verify the TFT checksum
6. only when `--flash` is passed: check COM36 ownership, validate target model
   fields, upload, run health checks, run optional serial smoke commands, and
   optionally capture `USB Cam`

Build-only example:

```powershell
python tools\codex_touchsafe_official_pipeline.py `
  --source-hmi build\my_source_case\lcd_test.HMI `
  --out-dir build\my_touchsafe_case `
  --name my_touchsafe_case
```

The official `USART HMI` install is auto-discovered from
`USARTHMI_OFFICIAL_DIR`, `C:\Program Files (x86)\USART HMI`, or
`C:\Program Files\USART HMI`. Pass `--install-dir` only when auto-discovery
cannot find the correct install/runtime directory.

Patch-plan example:

```powershell
python tools\codex_touchsafe_official_pipeline.py `
  --source-hmi build\my_source_case\lcd_test.HMI `
  --patch-plan build\my_preview\beauty_patch_plan.json `
  --out-dir build\my_touchsafe_case `
  --name my_touchsafe_case
```

Spec-driven example:

```powershell
python tools\codex_touchsafe_official_pipeline.py `
  --spec examples\polished_dashboard_demo\touchsafe_pipeline.template.json
```

Flash must be explicit:

```powershell
python tools\codex_touchsafe_official_pipeline.py `
  --spec examples\polished_dashboard_demo\touchsafe_pipeline.template.json `
  --flash --serial-smoke --camera
```

The normal output is `pipeline_manifest.json` under the selected `out_dir`.
Generated `.HMI`, `.TFT`, screenshots, command stdout/stderr, and preview files
belong under `build/`, which is ignored by Git. Commit the script, spec, and
small evidence notes; do not commit generated binary payloads unless the repo
explicitly moves them into a fixture or LFS policy.

For another Windows machine, build a portable source package with:

```powershell
python tools\package_touchsafe_headless_toolchain.py --out-dir dist --require-host-exe
```

See `touchsafe_headless_package.md` for bootstrap, wrapper, and Codex skill
installation details.

## Geometry Gate

For objects with geometry fields, the pipeline checks:

```text
endx == x + w - 1
endy == y + h - 1
```

This is required because visual preview alone cannot prove physical touch
hitboxes. A stale `endx` / `endy` can render correctly while keeping the old
touch area.
