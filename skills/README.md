# Agent Skills

This repository ships Codex-style skills for agents working on the USART HMI
toolchain. Copy a skill folder into `~/.codex/skills` or use the package
bootstrap command when available.

Available skills:

- `usarthmi-headless-toolchain`: package, bootstrap, and run the touch-safe
  headless official USART HMI compiler flow.
- `usarthmi-scene-authoring`: create, edit, preview, import, lint, and hand off
  scene JSON/YAML files without touching hardware.
- `usarthmi-live-panel-validation`: safely checksum, upload, and verify TFTs on
  a real serial panel with explicit COM and target gates.

Install the packaged skills on a target machine:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\touchsafe_headless_bootstrap.ps1 -InstallSkill
```

Skill folders contain only agent-facing instructions and minimal UI metadata.
Generated `.HMI`, `.TFT`, screenshots, and local build outputs should stay out
of Git and out of skill folders.
