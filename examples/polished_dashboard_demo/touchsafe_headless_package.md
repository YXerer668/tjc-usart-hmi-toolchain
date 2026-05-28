# Portable Headless USART HMI Package

This package turns the current touch-safe official build flow into a reusable
Windows bundle. A target machine must have the official `USART HMI` application
installed. The source package also requires Python 3.10+; use a separate
standalone build if the target must not install Python.

## Build The Package

From the repository root:

```powershell
python tools\package_touchsafe_headless_toolchain.py --out-dir dist --require-host-exe
```

The generated zip includes:

- `usarthmi` Python package
- touch-safe build pipeline
- official headless GUI bridge
- `OfficialGuiHostSelect.cs`
- prebuilt `tools\UsartHmiHostAutomation.exe` when the local C# compiler is available
- bootstrap and run wrappers
- reusable Codex skill: `skills\usarthmi-headless-toolchain`

Generated `.HMI`, `.TFT`, screenshots, local `build\`, reverse dumps, and
private machine paths are excluded.

## Use On Another Machine

1. Install official `USART HMI`.
2. Extract the zip.
3. Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\touchsafe_headless_bootstrap.ps1
```

If auto-discovery fails:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\touchsafe_headless_bootstrap.ps1 `
  -OfficialDir "C:\Program Files (x86)\USART HMI"
```

Then build:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_touchsafe_pipeline.ps1 `
  -Spec .\examples\polished_dashboard_demo\touchsafe_pipeline.template.json
```

The main evidence file is `<out-dir>\pipeline_manifest.json`.

## Flashing

Build-only is the default. Flashing requires explicit intent:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_touchsafe_pipeline.ps1 `
  -Spec .\examples\polished_dashboard_demo\touchsafe_pipeline.template.json `
  -Flash -SerialSmoke -Camera
```

For the live `TJC8048X543_011C` lane, keep the exact connect gate in the spec
and do not run another serial stress/probe process against the same COM port.

## Codex Skill

The package includes `skills\usarthmi-headless-toolchain`. To install it into a
Codex environment on the target machine:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\touchsafe_headless_bootstrap.ps1 -InstallSkill
```

After that, Codex can trigger the skill when asked to package, bootstrap, or run
the USART HMI headless toolchain.
