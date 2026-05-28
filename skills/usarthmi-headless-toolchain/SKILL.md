---
name: usarthmi-headless-toolchain
description: Use when packaging, bootstrapping, or running the reusable touch-safe headless USART HMI toolchain on Windows, especially for .HMI to .TFT builds through the official USART HMI compiler without manual GUI clicks, portable package creation, official install discovery, geometry overlap gates, or explicit COM flashing.
---

# USART HMI Headless Toolchain

Use the repository/package entrypoints instead of ad-hoc GUI clicks. The normal path is:

1. Bootstrap the package on the target Windows machine.
2. Run the touch-safe pipeline in build-only mode.
3. Inspect `pipeline_manifest.json`, preview output, and checksum.
4. Flash only when the user explicitly asks and the serial target gate passes.

## Entry Points

From the toolchain root:

```powershell
.\tools\touchsafe_headless_bootstrap.ps1
.\tools\run_touchsafe_pipeline.ps1 -Spec .\examples\polished_dashboard_demo\touchsafe_pipeline.template.json
```

Direct Python remains supported:

```powershell
python .\tools\codex_touchsafe_official_pipeline.py --spec <spec.json>
```

Create a reusable zip:

```powershell
python .\tools\package_touchsafe_headless_toolchain.py --out-dir .\dist
```

## Required Checks

- Confirm the official runtime is discoverable or pass `--install-dir` / `-OfficialDir`.
- Do not rely on visual preview alone for touch correctness. The pipeline must pass the hidden `endx=x+w-1` and `endy=y+h-1` geometry audit.
- Treat preview collision failures as blocking unless the user explicitly accepts the overlap.
- Build-only is the default. Use `--flash` or `-Flash` only for intentional hardware programming.
- Before flashing, check that no stress/probe process owns the COM port. The pipeline has a COM36 guard, but still avoid parallel serial tools.
- For the live TJC8048X543_011C lane, keep the connect gate exact: model, firmware, MCU code, flash descriptor, and feature descriptor must match the configured expected fields.

## Portable Package Rules

- The package should include the Python source, `usarthmi` package, official headless bridge scripts, `OfficialGuiHostSelect.cs`, wrappers, docs, and this skill.
- Include a prebuilt `tools\UsartHmiHostAutomation.exe` in generated zips when possible so target machines do not need the C# compiler.
- Do not include generated `.HMI`, `.TFT`, screenshots, build directories, reverse-engineering dumps, or private local paths in release zips.
- The source package still needs Python 3.10+ on the target machine. If the user requires zero Python installation, make a separate PyInstaller or embedded-Python deliverable and verify the subprocess entrypoints under that runtime.

## Output Evidence

The success artifact is `pipeline_manifest.json` under the chosen output directory. For a build-only run, cite:

- `touchsafe_geometry_audit` status
- `preview_collision_gate` status
- `official_compile` status and TFT size
- `checksum` validity

For flash runs, additionally cite COM ownership, connect gate, upload, health, optional serial smoke, and camera capture.
