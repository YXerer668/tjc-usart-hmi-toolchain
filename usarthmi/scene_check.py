from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
from typing import Any

from .event_logic import analyze_scene_events
from .event_simulator import simulate_scene_event_model
from .scene import PageSpec, SceneModel, WidgetSpec, load_scene
from .scenario_runner import read_scenario_document, run_scene_scenario_model
from .scene_edit import collect_scene_event_slots
from .target_status import target_status_summary
from .widgets import CURRENT_TARGET, get_widget_type_info


SCENE_CHECK_SCHEMA_VERSION = 1
SCENE_CHECK_NOT_CLAIMED = [
    "official USART HMI compiler equivalence",
    "byte-perfect HMI or TFT output",
    "hardware, serial, or COM36 behavior",
    "physical touch behavior",
    "media/file-system side effects",
    "safe-to-flash proof",
]


def check_scene_project(
    scene_path: str | Path,
    *,
    out_dir: str | Path | None = None,
    target: str = CURRENT_TARGET,
    simulate_events: bool = False,
    max_event_slots: int = 50,
    max_steps: int = 128,
    scenario_paths: list[str | Path] | tuple[str | Path, ...] | None = None,
) -> dict[str, Any]:
    """Build an offline editor-style check report for a scene file."""
    source_path = Path(scene_path).resolve()
    scene = load_scene(source_path)
    result = check_scene_model(
        scene,
        source_path=source_path,
        out_dir=out_dir,
        target=target,
        simulate_events=simulate_events,
        max_event_slots=max_event_slots,
        max_steps=max_steps,
        scenario_paths=scenario_paths,
    )
    return result


def check_scene_model(
    scene: SceneModel,
    *,
    source_path: str | Path | None = None,
    out_dir: str | Path | None = None,
    target: str = CURRENT_TARGET,
    simulate_events: bool = False,
    max_event_slots: int = 50,
    max_steps: int = 128,
    scenario_paths: list[str | Path] | tuple[str | Path, ...] | None = None,
) -> dict[str, Any]:
    if max_event_slots < 0:
        raise ValueError("max_event_slots must be a non-negative integer")
    if max_steps <= 0:
        raise ValueError("max_steps must be a positive integer")

    widgets = _collect_widgets(scene)
    widget_report = _widget_report(scene, widgets)
    live_smoke = _live_smoke_summary(scene)
    event_analysis = analyze_scene_events(scene)
    target_status = target_status_summary()
    event_slots = collect_scene_event_slots(scene, include_empty=False)
    simulations = _simulate_event_slots(
        scene,
        event_slots,
        enabled=simulate_events,
        max_event_slots=max_event_slots,
        max_steps=max_steps,
    )
    scenarios = _run_scenarios(
        scene,
        scenario_paths or [],
        source_path=source_path,
        out_dir=out_dir,
        max_steps=max_steps,
    )
    diagnostics = [
        *_scene_diagnostics(scene),
        *widget_report["diagnostics"],
        *_event_diagnostics(event_analysis),
        *_simulation_diagnostics(simulations),
        *_scenario_diagnostics(scenarios),
    ]
    summary = _summary(scene, widget_report, event_slots, event_analysis, simulations, scenarios, diagnostics)
    result: dict[str, Any] = {
        "schema_version": SCENE_CHECK_SCHEMA_VERSION,
        "scene_path": str(Path(source_path).resolve()) if source_path is not None else None,
        "target": target,
        "offline_only": True,
        "safe_to_flash": False,
        "summary": summary,
        "project": {
            "name": scene.project.get("name"),
            "default_page": scene.project.get("default_page"),
        },
        "target_status": target_status,
        "live_smoke": live_smoke,
        "canvas": dict(scene.canvas),
        "pages": [
            {
                "id": page.id,
                "widget_count": len(page.widgets),
                "event_count": sum(1 for lines in page.events.values() if lines),
                "layout": dict(page.layout),
            }
            for page in scene.pages
        ],
        "widgets": widget_report["widgets"],
        "widget_capability_summary": widget_report["summary"],
        "events": {
            "summary": event_analysis["summary"],
            "navigation_graph": event_analysis["navigation_graph"],
            "event_summary": event_analysis["event_summary"],
            "diagnostics": event_analysis["diagnostics"],
        },
        "event_simulations": simulations,
        "scenarios": scenarios,
        "diagnostics": diagnostics,
        "not_claimed": list(SCENE_CHECK_NOT_CLAIMED),
    }
    if out_dir is not None:
        output_dir = Path(out_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / "scene_check_report.json"
        report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        result["outputs"] = {"scene_check_report_json": str(report_path)}
        report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _collect_widgets(scene: SceneModel) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    for page in scene.pages:
        for index, widget in enumerate(page.widgets):
            _collect_widget(page, widget, index=index, parent=None, collected=collected)
    return collected


def _collect_widget(
    page: PageSpec,
    widget: WidgetSpec,
    *,
    index: int,
    parent: str | None,
    collected: list[dict[str, Any]],
) -> None:
    collected.append(
        {
            "page": page.id,
            "id": widget.id,
            "path": f"{page.id}.{widget.id}",
            "type": widget.type,
            "parent": parent,
            "index": index,
            "bbox": [widget.x, widget.y, widget.w, widget.h],
            "event_count": sum(1 for lines in widget.events.values() if lines),
            "child_count": len(widget.children),
        }
    )
    for child_index, child in enumerate(widget.children):
        _collect_widget(page, child, index=child_index, parent=widget.id, collected=collected)


def _widget_report(scene: SceneModel, widgets: list[dict[str, Any]]) -> dict[str, Any]:
    diagnostics: list[dict[str, Any]] = []
    support_counts: Counter[str] = Counter()
    writer_counts: Counter[str] = Counter()
    enriched: list[dict[str, Any]] = []
    direct_tft_blockers: list[dict[str, Any]] = []
    canvas_width = int(scene.canvas.get("width", 0))
    canvas_height = int(scene.canvas.get("height", 0))

    for page in scene.pages:
        names = [widget.id for widget in page.widgets]
        for widget_id, count in Counter(names).items():
            if count > 1:
                diagnostics.append(
                    _diagnostic(
                        "error",
                        "DUPLICATE_WIDGET_ID",
                        f"page {page.id!r} has duplicate widget id {widget_id!r}",
                        f"{page.id}.{widget_id}",
                    )
                )

    for widget in widgets:
        info = get_widget_type_info(widget["type"])
        capability = info.to_dict(include_aliases=True) if info is not None else {"type": widget["type"], "support": "unknown", "writer": "none"}
        support = str(capability.get("support", "unknown"))
        writer = str(capability.get("writer", "none"))
        support_counts[support] += 1
        writer_counts[writer] += 1
        can_build_tft = _can_build_tft(capability)
        if not can_build_tft:
            blocker = {
                "path": widget["path"],
                "type": widget["type"],
                "support": support,
                "writer": writer,
                "reason": capability.get("reason") or "direct TFT writer is not available",
            }
            direct_tft_blockers.append(blocker)
            diagnostics.append(
                _diagnostic(
                    "warning",
                    "NO_DIRECT_TFT_WRITER",
                    f"{widget['path']} is authoring-only for direct TFT output",
                    widget["path"],
                    widget_type=widget["type"],
                )
            )
        if support == "pending":
            diagnostics.append(
                _diagnostic(
                    "warning",
                    "HMI_ONLY_WIDGET",
                    f"{widget['path']} is fixture-backed HMI-only on the current target",
                    widget["path"],
                    widget_type=widget["type"],
                )
            )
        _geometry_diagnostics(widget, canvas_width, canvas_height, diagnostics)
        enriched.append({**widget, "capability": capability, "can_build_tft": can_build_tft})

    return {
        "widgets": enriched,
        "diagnostics": diagnostics,
        "summary": {
            "widget_count": len(enriched),
            "by_support": dict(sorted(support_counts.items())),
            "by_writer": dict(sorted(writer_counts.items())),
            "direct_tft_ready": not direct_tft_blockers,
            "direct_tft_blocker_count": len(direct_tft_blockers),
            "direct_tft_blockers": direct_tft_blockers,
        },
    }


def _can_build_tft(capability: dict[str, Any]) -> bool:
    if capability.get("can_build_tft") is False:
        return False
    support = capability.get("support")
    writer = capability.get("writer")
    return support == "supported" and writer in {"built-in", "fixture"}


def _geometry_diagnostics(
    widget: dict[str, Any],
    canvas_width: int,
    canvas_height: int,
    diagnostics: list[dict[str, Any]],
) -> None:
    bbox = widget.get("bbox") or []
    if len(bbox) != 4 or any(value is None for value in bbox):
        diagnostics.append(
            _diagnostic(
                "warning",
                "MISSING_GEOMETRY",
                f"{widget['path']} has incomplete x/y/w/h geometry",
                widget["path"],
                widget_type=widget["type"],
            )
        )
        return
    x, y, width, height = [int(value) for value in bbox]
    if width <= 0 or height <= 0:
        diagnostics.append(
            _diagnostic(
                "error",
                "INVALID_GEOMETRY",
                f"{widget['path']} has non-positive width/height",
                widget["path"],
                widget_type=widget["type"],
            )
        )
        return
    if x < 0 or y < 0 or x + width > canvas_width or y + height > canvas_height:
        diagnostics.append(
            _diagnostic(
                "warning",
                "OFF_CANVAS",
                f"{widget['path']} extends outside the canvas",
                widget["path"],
                widget_type=widget["type"],
            )
        )


def _scene_diagnostics(scene: SceneModel) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    page_ids = {page.id for page in scene.pages}
    default_page = scene.project.get("default_page")
    if default_page not in page_ids:
        diagnostics.append(
            _diagnostic(
                "error",
                "MISSING_DEFAULT_PAGE",
                f"default_page {default_page!r} does not name a scene page",
                "project.default_page",
            )
        )
    return diagnostics


def _event_diagnostics(event_analysis: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            **item,
            "source": "event-lint",
        }
        for item in event_analysis.get("diagnostics", [])
    ]


def _simulate_event_slots(
    scene: SceneModel,
    event_slots: list[dict[str, Any]],
    *,
    enabled: bool,
    max_event_slots: int,
    max_steps: int,
) -> dict[str, Any]:
    non_empty = [slot for slot in event_slots if slot.get("line_count", 0) > 0]
    selected = non_empty[:max_event_slots] if enabled else []
    skipped = max(0, len(non_empty) - len(selected)) if enabled else len(non_empty)
    results: list[dict[str, Any]] = []
    for slot in selected:
        result = simulate_scene_event_model(
            scene,
            str(slot["path"]),
            max_steps=max_steps,
        )
        results.append(
            {
                "event_path": slot["path"],
                "summary": result["summary"],
                "diagnostics": result["diagnostics"],
                "trace": result["trace"],
                "final_state": result["final_state"],
                "not_claimed": result["not_claimed"],
            }
        )
    return {
        "enabled": enabled,
        "available_event_slot_count": len(non_empty),
        "simulated_event_slot_count": len(results),
        "skipped_event_slot_count": skipped,
        "max_event_slots": max_event_slots,
        "max_steps": max_steps,
        "results": results,
        "not_claimed": [
            "offline simulation is not official runtime scheduler proof",
            "serial click and physical touch behavior are not proven by simulation",
        ],
    }


def _simulation_diagnostics(simulations: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    if simulations.get("enabled") and simulations.get("skipped_event_slot_count", 0):
        diagnostics.append(
            _diagnostic(
                "warning",
                "EVENT_SIMULATION_LIMIT",
                f"{simulations['skipped_event_slot_count']} non-empty event slot(s) were not simulated due to max_event_slots",
                "events",
            )
        )
    for result in simulations.get("results", []):
        event_path = str(result.get("event_path"))
        for item in result.get("diagnostics", []):
            diagnostics.append({**item, "source": "event-simulation", "path": item.get("path") or event_path})
    return diagnostics


def _run_scenarios(
    scene: SceneModel,
    scenario_paths: list[str | Path] | tuple[str | Path, ...],
    *,
    source_path: str | Path | None,
    out_dir: str | Path | None,
    max_steps: int,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    output_root = Path(out_dir).resolve() / "scenarios" if out_dir is not None else None
    for index, raw_path in enumerate(scenario_paths):
        scenario_path = Path(raw_path).resolve()
        scenario = read_scenario_document(scenario_path)
        scenario_out = None
        if output_root is not None:
            scenario_out = output_root / f"{index:02d}_{scenario_path.stem}"
        result = run_scene_scenario_model(
            scene,
            scenario,
            source_path=source_path,
            scenario_path=scenario_path,
            out_dir=scenario_out,
            max_steps=max_steps,
        )
        results.append(
            {
                "scenario_path": str(scenario_path),
                "name": result.get("name"),
                "summary": result["summary"],
                "diagnostics": result["diagnostics"],
                "outputs": result.get("outputs", {}),
                "safe_to_flash": result.get("safe_to_flash"),
                "not_claimed": result.get("not_claimed"),
            }
        )
    failed = [
        item
        for item in results
        if not bool(item.get("summary", {}).get("scenario_ok"))
    ]
    return {
        "enabled": bool(scenario_paths),
        "scenario_count": len(results),
        "failed_scenario_count": len(failed),
        "results": results,
        "not_claimed": [
            "offline scenarios are not official runtime scheduler proof",
            "scenario assertions do not prove hardware, serial, or physical touch behavior",
        ],
    }


def _scenario_diagnostics(scenarios: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for result in scenarios.get("results", []):
        scenario_path = str(result.get("scenario_path"))
        for item in result.get("diagnostics", []):
            diagnostics.append({**item, "source": "scenario", "scenario_path": scenario_path})
    return diagnostics


def _summary(
    scene: SceneModel,
    widget_report: dict[str, Any],
    event_slots: list[dict[str, Any]],
    event_analysis: dict[str, Any],
    simulations: dict[str, Any],
    scenarios: dict[str, Any],
    diagnostics: list[dict[str, Any]],
) -> dict[str, Any]:
    error_count = sum(1 for item in diagnostics if item.get("severity") == "error")
    warning_count = sum(1 for item in diagnostics if item.get("severity") == "warning")
    event_errors = int(event_analysis.get("summary", {}).get("error_count", 0))
    simulation_errors = sum(
        int(result.get("summary", {}).get("error_count", 0))
        for result in simulations.get("results", [])
    )
    live_smoke = _live_smoke_summary(scene)
    return {
        "ok": error_count == 0,
        "authoring_ok": error_count == 0,
        "direct_tft_ready": bool(widget_report["summary"]["direct_tft_ready"]) and event_errors == 0,
        "safe_to_flash": False,
        "page_count": len(scene.pages),
        "widget_count": widget_report["summary"]["widget_count"],
        "asset_count": len(scene.assets),
        "event_slot_count": len(event_slots),
        "event_command_count": int(event_analysis.get("summary", {}).get("command_count", 0)),
        "event_simulation_enabled": bool(simulations.get("enabled")),
        "event_simulation_count": int(simulations.get("simulated_event_slot_count", 0)),
        "scenario_enabled": bool(scenarios.get("enabled")),
        "scenario_count": int(scenarios.get("scenario_count", 0)),
        "failed_scenario_count": int(scenarios.get("failed_scenario_count", 0)),
        "live_smoke_declared": bool(live_smoke["declared"]),
        "live_smoke_expectation_count": int(live_smoke["expectation_count"]),
        "live_smoke_set_expectation_count": int(live_smoke["set_expectation_count"]),
        "live_smoke_step_count": int(live_smoke["step_count"]),
        "error_count": error_count,
        "warning_count": warning_count,
        "event_error_count": event_errors,
        "simulation_error_count": simulation_errors,
        "offline_only": True,
    }


def _live_smoke_summary(scene: SceneModel) -> dict[str, Any]:
    payload = scene.project.get("live_smoke")
    if not isinstance(payload, dict):
        return {
            "declared": False,
            "version": None,
            "auto": None,
            "auto_expectations": None,
            "auto_steps": None,
            "expectation_count": 0,
            "set_expectation_count": 0,
            "step_count": 0,
        }
    return {
        "declared": True,
        "version": payload.get("version"),
        "auto": payload.get("auto"),
        "auto_expectations": payload.get("auto_expectations"),
        "auto_steps": payload.get("auto_steps"),
        "expectation_count": _count_live_smoke_items(payload.get("expectations")),
        "set_expectation_count": _count_live_smoke_items(payload.get("set_expectations")),
        "step_count": len(payload.get("steps") or []),
    }


def _count_live_smoke_items(payload: Any) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        return len(payload)
    return 0


def _diagnostic(
    severity: str,
    code: str,
    message: str,
    path: str,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "path": path,
        **extra,
    }
