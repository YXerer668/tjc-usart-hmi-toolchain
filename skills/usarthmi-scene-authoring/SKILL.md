---
name: usarthmi-scene-authoring
description: Use when creating, importing, editing, linting, previewing, or handing off USART HMI scene JSON/YAML files, including widget layout, event scripts, agent-preview bundles, scene check/export/smoke preparation, and offline gates before official compilation or live flashing.
---

# USART HMI Scene Authoring

Use this skill for work that should stay offline: scene edits, layout, preview,
event linting, import diagnostics, and agent handoff bundles. Do not open serial
ports or flash hardware from this skill.

## Normal Workflow

1. Inspect the scene or import the `.HMI` into a scene bundle.
2. Apply small structured edits through `python -m usarthmi --json scene ...`
   commands when possible.
3. Run preview/check gates and read the JSON reports.
4. Stop at `safe_to_flash=false` until a build or live-validation skill takes over.

## Useful Commands

Create or inspect a scene:

```powershell
python -m usarthmi --json scene new examples\new_project\scene.json --name NewProject
python -m usarthmi --json scene preview examples\new_project\scene.json --out build\preview.png
python -m usarthmi --json scene check examples\new_project\scene.json --out-dir build\scene_check --simulate-events
python -m usarthmi --json scene agent-preview examples\new_project\scene.json --out-dir build\agent_preview
```

Edit scene structure:

```powershell
python -m usarthmi --json scene pages add examples\new_project\scene.json page1
python -m usarthmi --json scene widgets update examples\new_project\scene.json page0.btn0 --x 80 --y 96 --text "Run"
python -m usarthmi --json scene design align examples\new_project\scene.json page0.btn0 page0.txt0 --edge left --out-dir build\design_session
python -m usarthmi --json scene design distribute examples\new_project\scene.json page0.btn0 page0.txt0 --axis horizontal --out-dir build\design_session
```

Edit and check events:

```powershell
python -m usarthmi --json scene events lint examples\new_project\scene.json
python -m usarthmi --json scene events graph examples\new_project\scene.json
python -m usarthmi --json scene events append-command examples\new_project\scene.json page0.btn0.up --command page --target page1 --dry-run --simulate --out-dir build\event_patch
```

Import an official project for lossy editing:

```powershell
python -m usarthmi --json hmi import path\to\project.HMI --out-dir build\imported_project --overwrite
python -m usarthmi --json hmi roundtrip-check path\to\project.HMI --out-dir build\roundtrip_project --overwrite
```

## Evidence Rules

- A preview is not a hardware proof.
- `scene check` and `agent-preview` are offline gates only.
- Treat unsupported widget diagnostics and direct-TFT blockers as real blockers.
- If a layout changes touchable controls, a later touch-safe pipeline must check
  hidden `endx` / `endy`, not just visible rectangles.
- Commit scene specs and small JSON reports when useful; keep generated `.HMI`,
  `.TFT`, screenshots, and build directories out of Git.
