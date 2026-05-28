from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import re
from typing import Any

from .event_logic import analyze_scene_events, parse_event_line
from .scene import PageSpec, SceneError, SceneModel, WidgetSpec, load_scene
from .scene_edit import EventTarget, parse_event_path


EVENT_SIMULATOR_SCHEMA_VERSION = 1
DEFAULT_MAX_STEPS = 128
_ATTR_REF_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")
_SYSTEM_VAR_RE = re.compile(r"^sys\d+$", flags=re.IGNORECASE)
EVENT_SIMULATOR_NOT_CLAIMED = [
    "official USART HMI runtime scheduler equivalence",
    "official event bytecode proof",
    "hardware, serial, or COM36 behavior",
    "physical touch semantics or tsw touch-lockout proof",
    "real firmware timing for delay commands",
    "complete USART HMI event language coverage",
    "media, file-system, or widget-specific hidden side effects",
]


def simulate_scene_event(
    scene_path: str | Path,
    event_path: str,
    *,
    out_dir: str | Path | None = None,
    initial_page: str | None = None,
    max_steps: int = DEFAULT_MAX_STEPS,
) -> dict[str, Any]:
    """Run a guarded offline simulation of one scene event slot.

    This is a deterministic scene-state helper for agents and tests. It does
    not upload, read serial, emulate the firmware scheduler, or prove runtime
    behavior on the physical panel.
    """
    source_path = Path(scene_path).resolve()
    scene = load_scene(source_path)
    return simulate_scene_event_model(
        scene,
        event_path,
        source_path=source_path,
        out_dir=out_dir,
        initial_page=initial_page,
        max_steps=max_steps,
    )


def simulate_scene_event_model(
    scene: SceneModel,
    event_path: str,
    *,
    source_path: str | Path | None = None,
    out_dir: str | Path | None = None,
    initial_page: str | None = None,
    max_steps: int = DEFAULT_MAX_STEPS,
) -> dict[str, Any]:
    if max_steps <= 0:
        raise SceneError("max_steps must be a positive integer")
    target = parse_event_path(event_path)
    page_map = _page_map(scene)
    if target.page_id not in page_map:
        raise SceneError(f"Page '{target.page_id}' not found in scene")
    if target.widget_id is not None and target.widget_id not in _widget_map(page_map[target.page_id]):
        raise SceneError(f"Widget '{target.widget_id}' not found on page '{target.page_id}'")

    resolved_initial_page = _resolve_initial_page(scene, target, initial_page)
    runtime = _initial_runtime(scene, resolved_initial_page)
    indexes = _scene_indexes(scene)
    diagnostics: list[dict[str, Any]] = []
    trace: list[dict[str, Any]] = []
    executed_steps, truncated = _execute_event_queue(
        scene,
        page_map=page_map,
        indexes=indexes,
        runtime=runtime,
        queue=[target],
        max_steps=max_steps,
        executed_steps=0,
        trace=trace,
        diagnostics=diagnostics,
    )

    final_state = _public_runtime_state(runtime)
    event_analysis = analyze_scene_events(scene)
    result: dict[str, Any] = {
        "schema_version": EVENT_SIMULATOR_SCHEMA_VERSION,
        "scene_path": str(Path(source_path).resolve()) if source_path is not None else None,
        "trigger": event_path,
        "initial_page": resolved_initial_page,
        "max_steps": max_steps,
        "offline_simulated": True,
        "safe_to_flash": False,
        "trace": trace,
        "final_state": final_state,
        "diagnostics": diagnostics,
        "event_capabilities": event_analysis["event_capabilities"],
        "not_claimed": list(EVENT_SIMULATOR_NOT_CLAIMED),
        "summary": _simulation_summary(trace, diagnostics, final_state, executed_steps, truncated),
    }

    if out_dir is not None:
        outputs = _write_simulation_outputs(result, out_dir)
        result["outputs"] = outputs
        _write_json(Path(outputs["simulation_report_json"]), result)
    return result


def _scene_indexes(scene: SceneModel) -> dict[str, Any]:
    page_ids = {page.id for page in scene.pages}
    widgets_by_page = {page.id: _widget_map(page) for page in scene.pages}
    return {
        "page_ids": page_ids,
        "widgets_by_page": widgets_by_page,
    }


def _page_map(scene: SceneModel) -> dict[str, PageSpec]:
    return {page.id: page for page in scene.pages}


def _widget_map(page: PageSpec) -> dict[str, WidgetSpec]:
    widgets: dict[str, WidgetSpec] = {}

    def add_widget(widget: WidgetSpec) -> None:
        widgets[widget.id] = widget
        for child in widget.children:
            add_widget(child)

    for widget in page.widgets:
        add_widget(widget)
    return widgets


def _resolve_initial_page(scene: SceneModel, target: EventTarget, initial_page: str | None) -> str:
    page_ids = {page.id for page in scene.pages}
    if initial_page is not None:
        if initial_page not in page_ids:
            raise SceneError(f"Initial page '{initial_page}' not found in scene")
        return initial_page
    if target.page_id in page_ids:
        return target.page_id
    default_page = scene.project.get("default_page")
    if isinstance(default_page, str) and default_page in page_ids:
        return default_page
    return scene.pages[0].id


def _initial_runtime(scene: SceneModel, initial_page: str) -> dict[str, Any]:
    pages: dict[str, Any] = {}
    for page in scene.pages:
        widgets: dict[str, Any] = {}
        for widget_id, widget in _widget_map(page).items():
            widgets[widget_id] = {
                "type": widget.type,
                "visible": True,
                "touch_enabled": True,
                "attrs": _initial_widget_attrs(widget),
            }
        pages[page.id] = {"widgets": widgets}
    return {
        "current_page": initial_page,
        "elapsed_ms": 0,
        "pages": pages,
        "system": {"sys": {}, "dp": {}},
        "printh": [],
    }


def _initial_widget_attrs(widget: WidgetSpec) -> dict[str, Any]:
    attrs: dict[str, Any] = {}
    if widget.value is not None:
        attrs["val"] = widget.value
    if widget.text is not None:
        attrs["txt"] = widget.text
    for key in ("x", "y", "w", "h"):
        value = getattr(widget, key)
        if value is not None:
            attrs[key] = value
    for key, value in widget.style.items():
        if key not in attrs:
            attrs[key] = deepcopy(value)
    return attrs


def _execute_event_queue(
    scene: SceneModel,
    *,
    page_map: dict[str, PageSpec],
    indexes: dict[str, Any],
    runtime: dict[str, Any],
    queue: list[EventTarget],
    max_steps: int,
    executed_steps: int,
    trace: list[dict[str, Any]],
    diagnostics: list[dict[str, Any]],
) -> tuple[int, bool]:
    truncated = False
    while queue:
        queued_target = queue.pop(0)
        if queued_target.page_id not in page_map:
            diagnostics.append(_diagnostic("error", "MISSING_PAGE_REFERENCE", f"page {queued_target.page_id!r} does not exist", queued_target.path))
            continue
        if queued_target.widget_id is not None and queued_target.widget_id not in indexes["widgets_by_page"].get(queued_target.page_id, {}):
            diagnostics.append(_diagnostic("error", "MISSING_OBJECT_REFERENCE", f"widget {queued_target.widget_id!r} does not exist on page {queued_target.page_id!r}", queued_target.path))
            continue

        if runtime["current_page"] != queued_target.page_id:
            runtime["current_page"] = queued_target.page_id
        owner = _event_owner(page_map[queued_target.page_id], queued_target)
        lines = list(owner.events.get(queued_target.event_name, []))
        trace.append(
            {
                "step": len(trace),
                "kind": "trigger",
                "event_path": queued_target.path,
                "line_count": len(lines),
                "current_page": runtime["current_page"],
            }
        )
        if not lines:
            diagnostics.append(_diagnostic("warning", "EMPTY_EVENT_SLOT", "event slot has no script lines", queued_target.path))
            continue

        for line_index, line in enumerate(lines):
            if executed_steps >= max_steps:
                diagnostics.append(
                    _diagnostic(
                        "error",
                        "MAX_STEPS_EXCEEDED",
                        f"simulation stopped after {max_steps} executed command line(s)",
                        queued_target.path,
                        line_index=line_index,
                    )
                )
                truncated = True
                queue.clear()
                break
            current_page = page_map[runtime["current_page"]]
            command = parse_event_line(
                line,
                scene=scene,
                current_page=current_page,
                page_ids=indexes["page_ids"],
                widgets_by_page=indexes["widgets_by_page"],
                line_index=line_index,
            )
            for warning in command.get("warnings", []):
                diagnostics.append({**warning, "path": queued_target.path, "line_index": line_index, "line": line})
            line_trace = _execute_command(
                command,
                runtime=runtime,
                scene=scene,
                page_map=page_map,
                indexes=indexes,
                queue=queue,
                event_path=queued_target.path,
                diagnostics=diagnostics,
            )
            trace.append(
                {
                    "step": len(trace),
                    "kind": "line",
                    "event_path": queued_target.path,
                    "line_index": line_index,
                    "line": line,
                    **line_trace,
                }
            )
            executed_steps += 1
        if truncated:
            break
    return executed_steps, truncated


def _event_owner(page: PageSpec, target: EventTarget) -> PageSpec | WidgetSpec:
    if target.widget_id is None:
        return page
    widgets = _widget_map(page)
    try:
        return widgets[target.widget_id]
    except KeyError as exc:
        raise SceneError(f"Widget '{target.widget_id}' not found on page '{page.id}'") from exc


def _execute_command(
    command: dict[str, Any],
    *,
    runtime: dict[str, Any],
    scene: SceneModel,
    page_map: dict[str, PageSpec],
    indexes: dict[str, Any],
    queue: list[EventTarget],
    event_path: str,
    diagnostics: list[dict[str, Any]],
) -> dict[str, Any]:
    cmd = command.get("cmd")
    if cmd in {"blank"}:
        return {"command": cmd, "status": "skipped"}
    if not command.get("structured", True) or cmd == "raw":
        diagnostics.append(_diagnostic("warning", "UNSUPPORTED_EVENT_COMMAND", "event line is preserved but not executed", event_path, line_index=command.get("line_index")))
        return {"command": cmd, "status": "unsupported", "reason": "raw or unsupported event command"}
    if cmd == "page":
        target = command.get("resolved_page")
        if not target or target not in page_map:
            return {"command": cmd, "status": "error", "reason": "unresolved page target", "target": command.get("target")}
        before = runtime["current_page"]
        runtime["current_page"] = target
        return {"command": cmd, "status": "executed", "page_before": before, "page_after": target}
    if cmd == "ref":
        target = command.get("target")
        resolved = _resolve_object(runtime, str(target or ""), indexes)
        if resolved is None:
            return {"command": cmd, "status": "error", "target": target, "reason": "unresolved object"}
        return {"command": cmd, "status": "trace-only", "target": _object_path(resolved), "reason": "refresh has no offline visual side effect"}
    if cmd in {"vis", "tsw"}:
        target = command.get("target")
        resolved = _resolve_object(runtime, str(target or ""), indexes)
        if resolved is None:
            return {"command": cmd, "status": "error", "target": target, "reason": "unresolved object"}
        state = _parse_binary_state(command.get("value"))
        if state is None:
            diagnostics.append(_diagnostic("error", "INVALID_BINARY_STATE", f"{cmd} requires 0/1 state", event_path, line_index=command.get("line_index")))
            return {"command": cmd, "status": "error", "target": target, "reason": "invalid state"}
        widget_state = _widget_runtime(runtime, resolved["page_id"], resolved["widget_id"])
        field = "visible" if cmd == "vis" else "touch_enabled"
        before = bool(widget_state[field])
        widget_state[field] = bool(state)
        return {
            "command": cmd,
            "status": "executed",
            "target": _object_path(resolved),
            "field": field,
            "before": before,
            "after": bool(state),
        }
    if cmd == "click":
        target = command.get("target")
        resolved = _resolve_object(runtime, str(target or ""), indexes)
        if resolved is None:
            return {"command": cmd, "status": "error", "target": target, "reason": "unresolved object"}
        click_event = _click_event_name(command.get("value"))
        if click_event is None:
            diagnostics.append(_diagnostic("error", "INVALID_CLICK_EVENT", "click requires 1/down or 0/up", event_path, line_index=command.get("line_index")))
            return {"command": cmd, "status": "error", "target": target, "reason": "invalid click event"}
        queued = EventTarget(page_id=resolved["page_id"], widget_id=resolved["widget_id"], event_name=click_event)
        queue.append(queued)
        widget_state = _widget_runtime(runtime, resolved["page_id"], resolved["widget_id"])
        return {
            "command": cmd,
            "status": "queued",
            "target": _object_path(resolved),
            "queued_event": queued.path,
            "target_touch_enabled": bool(widget_state["touch_enabled"]),
            "touch_note": "script/serial click is not treated as physical touch proof",
        }
    if cmd == "get":
        value = _get_runtime_attr(runtime, str(command.get("target") or ""), indexes)
        return {"command": cmd, "status": "executed", "target": command.get("target"), "value": value}
    if cmd == "set":
        return _execute_assignment(command, runtime=runtime, indexes=indexes, event_path=event_path, diagnostics=diagnostics)
    if cmd == "printh":
        bytes_out = list(command.get("bytes") or [])
        runtime["printh"].append({"bytes": bytes_out, "hex": " ".join(f"{item:02X}" for item in bytes_out)})
        return {"command": cmd, "status": "executed", "bytes": bytes_out, "hex": " ".join(f"{item:02X}" for item in bytes_out)}
    if cmd == "delay":
        delay_ms = command.get("value")
        if not isinstance(delay_ms, int):
            return {"command": cmd, "status": "error", "reason": "invalid delay"}
        before = runtime["elapsed_ms"]
        runtime["elapsed_ms"] = before + delay_ms
        return {"command": cmd, "status": "trace-only", "elapsed_before_ms": before, "elapsed_after_ms": runtime["elapsed_ms"]}
    if cmd == "file_stream_open":
        return _execute_file_stream_open(command, runtime=runtime, indexes=indexes)
    diagnostics.append(_diagnostic("warning", "UNSUPPORTED_EVENT_COMMAND", f"simulator does not execute command {cmd!r}", event_path, line_index=command.get("line_index")))
    return {"command": cmd, "status": "unsupported"}


def _execute_file_stream_open(command: dict[str, Any], *, runtime: dict[str, Any], indexes: dict[str, Any]) -> dict[str, Any]:
    target = str(command.get("target") or "")
    resolved = _resolve_object(runtime, target, indexes)
    if resolved is None:
        return {"command": "file_stream_open", "status": "error", "target": target, "reason": "unresolved file-stream object"}
    widget_state = _widget_runtime(runtime, resolved["page_id"], resolved["widget_id"])
    if _normalized_widget_type(widget_state.get("type")) != "file-stream":
        return {"command": "file_stream_open", "status": "error", "target": _object_path(resolved), "reason": "target is not a file-stream widget"}

    argument = str(command.get("argument") or "")
    open_path = _get_runtime_attr(runtime, argument, indexes)
    widget_state["attrs"]["last_open_path"] = "" if open_path is None else str(open_path)
    return {
        "command": "file_stream_open",
        "status": "trace-only",
        "target": _object_path(resolved),
        "argument": argument,
        "path": widget_state["attrs"]["last_open_path"],
        "hardware_proof": command.get("hardware_proof"),
        "reason": "offline simulator records the intended open path; real file-system side effects require serial hardware smoke",
    }


def _execute_assignment(
    command: dict[str, Any],
    *,
    runtime: dict[str, Any],
    indexes: dict[str, Any],
    event_path: str,
    diagnostics: list[dict[str, Any]],
) -> dict[str, Any]:
    target = str(command.get("target") or "")
    reference = _resolve_attribute(runtime, target, indexes)
    if reference is None:
        return {"command": "set", "status": "error", "target": target, "reason": "unresolved attribute owner"}
    op = command.get("op")
    before = _read_attr_ref(runtime, reference)
    try:
        if op == "=":
            after = _eval_event_value(command.get("value"), runtime=runtime, indexes=indexes)
        elif op in {"++", "--"}:
            base = _numeric_value(before)
            after = base + (1 if op == "++" else -1)
        elif op in {"+=", "-="}:
            delta = _eval_event_value(command.get("value"), runtime=runtime, indexes=indexes)
            if op == "+=" and (isinstance(before, str) or isinstance(delta, str)):
                after = _string_value(before) + _string_value(delta)
            else:
                base = _numeric_value(before)
                numeric_delta = _numeric_value(delta)
                after = base + (numeric_delta if op == "+=" else -numeric_delta)
        else:
            diagnostics.append(_diagnostic("warning", "UNSUPPORTED_ASSIGNMENT_OP", f"assignment operator {op!r} is not executed", event_path, line_index=command.get("line_index")))
            return {"command": "set", "status": "unsupported", "target": target, "op": op}
    except (TypeError, ValueError) as exc:
        diagnostics.append(_diagnostic("error", "INVALID_ASSIGNMENT_VALUE", str(exc), event_path, line_index=command.get("line_index")))
        return {"command": "set", "status": "error", "target": target, "op": op, "before": before}
    _write_attr_ref(runtime, reference, after)
    return {"command": "set", "status": "executed", "target": target, "op": op, "before": before, "after": after}


def _resolve_object(runtime: dict[str, Any], target: str, indexes: dict[str, Any]) -> dict[str, str] | None:
    value = target.strip()
    if not value:
        return None
    parts = value.split(".")
    pages = runtime["pages"]
    if len(parts) >= 2 and parts[0] in pages and parts[1] in pages[parts[0]]["widgets"]:
        return {"page_id": parts[0], "widget_id": parts[1]}
    current_page = runtime["current_page"]
    if value in pages[current_page]["widgets"]:
        return {"page_id": current_page, "widget_id": value}
    return None


def _resolve_attribute(runtime: dict[str, Any], target: str, indexes: dict[str, Any]) -> dict[str, Any] | None:
    parts = [part for part in target.split(".") if part]
    if len(parts) == 1 and _SYSTEM_VAR_RE.match(parts[0]):
        return {"kind": "system", "namespace": "sys", "attr": parts[0].lower()}
    if len(parts) < 2:
        return None
    if parts[0] in {"sys", "dp"}:
        return {"kind": "system", "namespace": parts[0], "attr": ".".join(parts[1:])}
    pages = runtime["pages"]
    if len(parts) >= 3 and parts[0] in pages and parts[1] in pages[parts[0]]["widgets"]:
        return {"kind": "widget", "page_id": parts[0], "widget_id": parts[1], "attr": ".".join(parts[2:])}
    resolved = _resolve_object(runtime, parts[0], indexes)
    if resolved is None:
        return None
    return {"kind": "widget", **resolved, "attr": ".".join(parts[1:])}


def _get_runtime_attr(runtime: dict[str, Any], target: str, indexes: dict[str, Any]) -> Any:
    reference = _resolve_attribute(runtime, target, indexes)
    if reference is None:
        return None
    return _read_attr_ref(runtime, reference)


def _read_attr_ref(runtime: dict[str, Any], reference: dict[str, Any]) -> Any:
    if reference["kind"] == "system":
        return runtime["system"].setdefault(reference["namespace"], {}).get(reference["attr"])
    widget_state = _widget_runtime(runtime, reference["page_id"], reference["widget_id"])
    return widget_state["attrs"].get(reference["attr"])


def _write_attr_ref(runtime: dict[str, Any], reference: dict[str, Any], value: Any) -> None:
    if reference["kind"] == "system":
        runtime["system"].setdefault(reference["namespace"], {})[reference["attr"]] = value
        return
    widget_state = _widget_runtime(runtime, reference["page_id"], reference["widget_id"])
    widget_state["attrs"][reference["attr"]] = value


def _widget_runtime(runtime: dict[str, Any], page_id: str, widget_id: str) -> dict[str, Any]:
    return runtime["pages"][page_id]["widgets"][widget_id]


def _object_path(resolved: dict[str, str]) -> str:
    return f"{resolved['page_id']}.{resolved['widget_id']}"


def _normalized_widget_type(value: Any) -> str:
    normalized = str(value or "").replace("_", "-").replace(" ", "-").lower()
    aliases = {
        "filestream": "file-stream",
        "file-stream": "file-stream",
    }
    return aliases.get(normalized, normalized)


def _parse_binary_state(value: Any) -> bool | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "on", "enable", "enabled"}:
        return True
    if normalized in {"0", "false", "off", "disable", "disabled"}:
        return False
    return None


def _click_event_name(value: Any) -> str | None:
    normalized = str(value).strip().lower() if value is not None else ""
    if normalized in {"1", "down", "press", "pressed"}:
        return "down"
    if normalized in {"0", "up", "release", "released"}:
        return "up"
    return None


def _parse_literal(value: Any) -> Any:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return _decode_event_string_literal(text[1:-1])
    try:
        return int(text, 0)
    except ValueError:
        return text


def _eval_event_value(value: Any, *, runtime: dict[str, Any], indexes: dict[str, Any]) -> Any:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return _decode_event_string_literal(text[1:-1])
    plus_parts = _split_expression(text, "+")
    if len(plus_parts) > 1:
        values = [_eval_event_value(part, runtime=runtime, indexes=indexes) for part in plus_parts]
        if all(_numeric_or_none(item) is not None for item in values):
            return sum(int(_numeric_or_none(item)) for item in values)
        return "".join(_string_value(item) for item in values)
    multiply_parts = _split_expression(text, "*")
    if len(multiply_parts) > 1:
        values = [_eval_event_value(part, runtime=runtime, indexes=indexes) for part in multiply_parts]
        product = 1
        for item in values:
            numeric = _numeric_or_none(item)
            if numeric is None:
                return text
            product *= numeric
        return product
    if _ATTR_REF_RE.match(text) or _SYSTEM_VAR_RE.match(text):
        reference = _resolve_attribute(runtime, text, indexes)
        if reference is not None:
            value = _read_attr_ref(runtime, reference)
            return "" if value is None else value
    return _parse_literal(text)


def _decode_event_string_literal(value: str) -> str:
    return (
        value.replace(r"\r", "\r")
        .replace(r"\n", "\n")
        .replace(r"\t", "\t")
        .replace(r"\"", '"')
        .replace(r"\'", "'")
        .replace(r"\\", "\\")
    )


def _split_expression(text: str, operator: str) -> list[str]:
    parts: list[str] = []
    quote: str | None = None
    start = 0
    for index, char in enumerate(text):
        if char in {"'", '"'}:
            if quote == char:
                quote = None
            elif quote is None:
                quote = char
            continue
        if char == operator and quote is None:
            parts.append(text[start:index].strip())
            start = index + 1
    if not parts:
        return [text.strip()]
    parts.append(text[start:].strip())
    return parts


def _numeric_or_none(value: Any) -> int | None:
    try:
        return _numeric_value(value)
    except (TypeError, ValueError):
        return None


def _string_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _numeric_value(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if value is None:
        return 0
    if isinstance(value, str):
        return int(value.strip(), 0)
    raise TypeError(f"value {value!r} is not numeric")


def _public_runtime_state(runtime: dict[str, Any]) -> dict[str, Any]:
    return {
        "current_page": runtime["current_page"],
        "elapsed_ms": runtime["elapsed_ms"],
        "pages": deepcopy(runtime["pages"]),
        "system": deepcopy(runtime["system"]),
        "printh": deepcopy(runtime["printh"]),
    }


def _simulation_summary(
    trace: list[dict[str, Any]],
    diagnostics: list[dict[str, Any]],
    final_state: dict[str, Any],
    executed_steps: int,
    truncated: bool,
) -> dict[str, Any]:
    error_count = sum(1 for item in diagnostics if item.get("severity") == "error")
    warning_count = sum(1 for item in diagnostics if item.get("severity") == "warning")
    return {
        "ok": error_count == 0,
        "executed_line_count": executed_steps,
        "trace_step_count": len(trace),
        "error_count": error_count,
        "warning_count": warning_count,
        "truncated": truncated,
        "final_page": final_state["current_page"],
        "offline_simulated": True,
        "safe_to_flash": False,
    }


def _write_simulation_outputs(result: dict[str, Any], out_dir: str | Path) -> dict[str, str]:
    output_dir = Path(out_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = output_dir / "runtime_trace.json"
    state_path = output_dir / "runtime_state.json"
    report_path = output_dir / "simulation_report.json"
    _write_json(trace_path, result["trace"])
    _write_json(state_path, result["final_state"])
    return {
        "runtime_trace_json": str(trace_path),
        "runtime_state_json": str(state_path),
        "simulation_report_json": str(report_path),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _diagnostic(
    severity: str,
    code: str,
    message: str,
    path: str,
    *,
    line_index: int | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
        "path": path,
    }
    if line_index is not None:
        item["line_index"] = line_index
    return item
