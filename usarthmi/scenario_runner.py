from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import yaml

from .event_logic import analyze_scene_events
from .event_simulator import (
    DEFAULT_MAX_STEPS,
    EVENT_SIMULATOR_NOT_CLAIMED,
    _execute_event_queue,
    _initial_runtime,
    _page_map,
    _public_runtime_state,
    _resolve_initial_page,
    _scene_indexes,
    _simulation_summary,
)
from .scene import SceneError, SceneModel, load_scene
from .scene_edit import EventTarget, parse_event_path


SCENARIO_RUNNER_SCHEMA_VERSION = 1
SCENARIO_NOT_CLAIMED = [
    *EVENT_SIMULATOR_NOT_CLAIMED,
    "official USART HMI scenario-test format compatibility",
    "real user physical input timing",
]


def run_scene_scenario(
    scene_path: str | Path,
    scenario_path: str | Path,
    *,
    out_dir: str | Path | None = None,
    initial_page: str | None = None,
    max_steps: int | None = None,
) -> dict[str, Any]:
    source_path = Path(scene_path).resolve()
    scenario_file = Path(scenario_path).resolve()
    scene = load_scene(source_path)
    scenario = read_scenario_document(scenario_file)
    return run_scene_scenario_model(
        scene,
        scenario,
        source_path=source_path,
        scenario_path=scenario_file,
        out_dir=out_dir,
        initial_page=initial_page,
        max_steps=max_steps,
    )


def read_scenario_document(path: str | Path) -> dict[str, Any]:
    scenario_path = Path(path).resolve()
    text = scenario_path.read_text(encoding="utf-8")
    if scenario_path.suffix.lower() in {".yaml", ".yml"}:
        payload = yaml.safe_load(text)
    else:
        payload = json.loads(text)
    if not isinstance(payload, dict):
        raise SceneError("Scenario root must be an object")
    return payload


def run_scene_scenario_model(
    scene: SceneModel,
    scenario: Mapping[str, Any],
    *,
    source_path: str | Path | None = None,
    scenario_path: str | Path | None = None,
    out_dir: str | Path | None = None,
    initial_page: str | None = None,
    max_steps: int | None = None,
) -> dict[str, Any]:
    steps = scenario.get("steps")
    if not isinstance(steps, list) or not steps:
        raise SceneError("Scenario requires a non-empty steps list")
    resolved_max_steps = _resolve_max_steps(scenario, max_steps)
    page_map = _page_map(scene)
    indexes = _scene_indexes(scene)
    first_target = _first_trigger_target(steps)
    resolved_initial_page = initial_page or _string_or_none(scenario.get("initial_page"))
    if resolved_initial_page is None:
        resolved_initial_page = _resolve_initial_page(scene, first_target, None)
    elif resolved_initial_page not in page_map:
        raise SceneError(f"Initial page '{resolved_initial_page}' not found in scene")

    runtime = _initial_runtime(scene, resolved_initial_page)
    trace: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    step_results: list[dict[str, Any]] = []
    executed_steps = 0
    truncated = False
    assertion_count = 0
    failed_assertion_count = 0

    for step_index, raw_step in enumerate(steps):
        step = _scenario_step(raw_step, step_index)
        result: dict[str, Any] = {"index": step_index}
        trigger_path = _string_or_none(step.get("trigger"))
        if trigger_path is not None:
            target = parse_event_path(trigger_path)
            _assert_trigger_exists(page_map, indexes, target)
            before_trace_count = len(trace)
            executed_steps, step_truncated = _execute_event_queue(
                scene,
                page_map=page_map,
                indexes=indexes,
                runtime=runtime,
                queue=[target],
                max_steps=resolved_max_steps,
                executed_steps=executed_steps,
                trace=trace,
                diagnostics=diagnostics,
            )
            truncated = truncated or step_truncated
            result.update(
                {
                    "kind": "trigger",
                    "trigger": target.path,
                    "trace_start": before_trace_count,
                    "trace_end": len(trace),
                    "truncated": step_truncated,
                }
            )
        assertions = step.get("assert")
        if assertions is not None:
            assertion_result = _evaluate_assertions(_public_runtime_state(runtime), assertions, step_index)
            assertion_count += assertion_result["assertion_count"]
            failed_assertion_count += assertion_result["failed_count"]
            if assertion_result["failed_count"]:
                diagnostics.extend(assertion_result["diagnostics"])
            result["assertions"] = assertion_result["assertions"]
            result["kind"] = "assert" if "kind" not in result else "trigger_assert"
        if "kind" not in result:
            raise SceneError(f"Scenario step {step_index} must contain trigger and/or assert")
        step_results.append(result)
        if truncated:
            break

    final_state = _public_runtime_state(runtime)
    event_analysis = analyze_scene_events(scene)
    summary = _simulation_summary(trace, diagnostics, final_state, executed_steps, truncated)
    summary.update(
        {
            "scenario_ok": failed_assertion_count == 0 and summary["ok"],
            "step_count": len(step_results),
            "configured_step_count": len(steps),
            "assertion_count": assertion_count,
            "failed_assertion_count": failed_assertion_count,
        }
    )
    result = {
        "schema_version": SCENARIO_RUNNER_SCHEMA_VERSION,
        "scene_path": str(Path(source_path).resolve()) if source_path is not None else None,
        "scenario_path": str(Path(scenario_path).resolve()) if scenario_path is not None else None,
        "name": str(scenario.get("name") or Path(str(scenario_path)).stem if scenario_path is not None else scenario.get("name") or "scenario"),
        "initial_page": resolved_initial_page,
        "max_steps": resolved_max_steps,
        "offline_simulated": True,
        "safe_to_flash": False,
        "steps": step_results,
        "trace": trace,
        "final_state": final_state,
        "diagnostics": diagnostics,
        "event_capabilities": event_analysis["event_capabilities"],
        "not_claimed": list(SCENARIO_NOT_CLAIMED),
        "summary": summary,
    }
    if out_dir is not None:
        result["outputs"] = _write_scenario_outputs(result, out_dir)
    return result


def _resolve_max_steps(scenario: Mapping[str, Any], override: int | None) -> int:
    raw = override if override is not None else scenario.get("max_steps", DEFAULT_MAX_STEPS)
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise SceneError("Scenario max_steps must be a positive integer") from exc
    if value <= 0:
        raise SceneError("Scenario max_steps must be a positive integer")
    return value


def _first_trigger_target(steps: list[Any]) -> EventTarget:
    for index, raw_step in enumerate(steps):
        step = _scenario_step(raw_step, index)
        trigger = _string_or_none(step.get("trigger"))
        if trigger is not None:
            return parse_event_path(trigger)
    raise SceneError("Scenario requires at least one trigger step when initial_page is not explicit")


def _scenario_step(raw_step: Any, step_index: int) -> Mapping[str, Any]:
    if not isinstance(raw_step, Mapping):
        raise SceneError(f"Scenario step {step_index} must be an object")
    return raw_step


def _assert_trigger_exists(
    page_map: dict[str, Any],
    indexes: dict[str, Any],
    target: EventTarget,
) -> None:
    if target.page_id not in page_map:
        raise SceneError(f"Page '{target.page_id}' not found in scene")
    if target.widget_id is not None and target.widget_id not in indexes["widgets_by_page"].get(target.page_id, {}):
        raise SceneError(f"Widget '{target.widget_id}' not found on page '{target.page_id}'")


def _evaluate_assertions(state: Mapping[str, Any], assertions: Any, step_index: int) -> dict[str, Any]:
    if not isinstance(assertions, Mapping):
        raise SceneError(f"Scenario step {step_index} assert must be an object")
    checks: list[tuple[str, Any]] = []
    for key, expected in assertions.items():
        if key in {"widgets", "widget"}:
            if not isinstance(expected, Mapping):
                raise SceneError(f"Scenario step {step_index} {key} assertion must be an object")
            checks.extend((str(path), value) for path, value in expected.items())
        else:
            checks.append((str(key), expected))

    results: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for path, expected in checks:
        actual = _resolve_assertion_path(state, path)
        passed = actual == expected
        item = {
            "path": path,
            "expected": expected,
            "actual": actual,
            "passed": passed,
        }
        results.append(item)
        if not passed:
            diagnostics.append(
                {
                    "severity": "error",
                    "code": "SCENARIO_ASSERTION_FAILED",
                    "message": f"scenario step {step_index} assertion failed for {path}",
                    "step_index": step_index,
                    **item,
                }
            )
    failed_count = sum(1 for item in results if not item["passed"])
    return {
        "assertion_count": len(results),
        "failed_count": failed_count,
        "assertions": results,
        "diagnostics": diagnostics,
    }


def _resolve_assertion_path(state: Mapping[str, Any], path: str) -> Any:
    if path == "current_page":
        return state.get("current_page")
    if path == "elapsed_ms":
        return state.get("elapsed_ms")
    if path in {"printh_hex", "serial_hex"}:
        return [item.get("hex") for item in state.get("printh", []) if isinstance(item, Mapping)]

    parts = [part for part in path.split(".") if part]
    if not parts:
        raise SceneError("Scenario assertion path cannot be empty")
    if parts[0] == "pages":
        return _traverse(state, parts)
    if len(parts) >= 3:
        page_id, widget_id, *field_parts = parts
        pages = state.get("pages")
        if not isinstance(pages, Mapping) or page_id not in pages:
            raise SceneError(f"Scenario assertion page '{page_id}' not found")
        page = pages[page_id]
        widgets = page.get("widgets") if isinstance(page, Mapping) else None
        if not isinstance(widgets, Mapping) or widget_id not in widgets:
            raise SceneError(f"Scenario assertion widget '{widget_id}' not found on page '{page_id}'")
        widget = widgets[widget_id]
        first_field = field_parts[0]
        if first_field in {"visible", "touch_enabled", "type"}:
            return _traverse(widget, field_parts)
        if first_field == "attrs":
            return _traverse(widget, field_parts)
        attrs = widget.get("attrs") if isinstance(widget, Mapping) else None
        if isinstance(attrs, Mapping):
            return _traverse(attrs, field_parts)
    return _traverse(state, parts)


def _traverse(value: Any, parts: list[str]) -> Any:
    current = value
    for part in parts:
        if isinstance(current, Mapping):
            if part not in current:
                raise SceneError(f"Scenario assertion path segment '{part}' not found")
            current = current[part]
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError) as exc:
                raise SceneError(f"Scenario assertion list index '{part}' not found") from exc
        else:
            raise SceneError(f"Scenario assertion path segment '{part}' cannot be resolved")
    return current


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _write_scenario_outputs(result: Mapping[str, Any], out_dir: str | Path) -> dict[str, str]:
    output_dir = Path(out_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = output_dir / "runtime_trace.json"
    state_path = output_dir / "runtime_state.json"
    report_path = output_dir / "scenario_report.json"
    _write_json(trace_path, result["trace"])
    _write_json(state_path, result["final_state"])
    _write_json(report_path, {key: value for key, value in result.items() if key != "outputs"})
    return {
        "runtime_trace_json": str(trace_path),
        "runtime_state_json": str(state_path),
        "scenario_report_json": str(report_path),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
