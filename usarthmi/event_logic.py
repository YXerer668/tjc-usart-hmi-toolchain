from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .scene import PageSpec, SceneModel, WidgetSpec, load_scene


STRUCTURED_EVENT_COMMANDS = ("page", "ref", "vis", "tsw", "click", "get", "set", "printh", "delay", "file_stream_open")
EVENT_BYTECODE_SUPPORT = "partial/guarded"
_IDENT = r"[A-Za-z_][A-Za-z0-9_]*"
_ASSIGN_RE = re.compile(rf"^(?P<target>{_IDENT}(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\s*(?P<op>\+\+|--|=|\+=|-=)\s*(?P<value>.*)$")
_METHOD_CALL_RE = re.compile(rf"^(?P<object>{_IDENT})\.(?P<method>{_IDENT})\((?P<arg>.*)\)$")
_ATTR_TARGET_RE = re.compile(rf"^(?P<object>{_IDENT})\.(?P<attr>{_IDENT})$")
_SYSTEM_VAR_RE = re.compile(r"^sys\d+$", flags=re.IGNORECASE)
_SET_OPS = {"=", "++", "--", "+=", "-="}


EVENT_COMMAND_SNIPPETS: list[dict[str, Any]] = [
    {
        "id": "page",
        "label": "Switch Page",
        "template": "page <page_id>",
        "description": "Switch to another scene page by id/name.",
    },
    {
        "id": "ref",
        "label": "Refresh Object",
        "template": "ref <object_id>",
        "description": "Refresh one object on the current page.",
    },
    {
        "id": "vis_show",
        "label": "Show Object",
        "template": "vis <object_id>,1",
        "description": "Show an object.",
    },
    {
        "id": "vis_hide",
        "label": "Hide Object",
        "template": "vis <object_id>,0",
        "description": "Hide an object.",
    },
    {
        "id": "tsw_enable",
        "label": "Enable Touch",
        "template": "tsw <object_id>,1",
        "description": "Enable touch for an object.",
    },
    {
        "id": "tsw_disable",
        "label": "Disable Touch",
        "template": "tsw <object_id>,0",
        "description": "Disable touch for an object.",
    },
    {
        "id": "click_up",
        "label": "Trigger Click Up",
        "template": "click <object_id>,0",
        "description": "Trigger an object's release event.",
    },
    {
        "id": "set_value",
        "label": "Set Attribute",
        "template": "<object_id>.val=0",
        "description": "Assign an object attribute.",
    },
    {
        "id": "increment",
        "label": "Increment Value",
        "template": "<object_id>.val++",
        "description": "Increment an object attribute.",
    },
    {
        "id": "printh",
        "label": "Print Hex",
        "template": "printh 23 02 00",
        "description": "Emit hex bytes over serial.",
    },
    {
        "id": "delay",
        "label": "Delay",
        "template": "delay=100",
        "description": "Delay event execution in milliseconds.",
    },
    {
        "id": "file_stream_open",
        "label": "Open File Stream",
        "template": "fs0.open(t1.txt)",
        "description": "Open a file-stream from a text widget path using the case72-proven method-call shape.",
    },
]


def event_capability_manifest() -> dict[str, Any]:
    return {
        "structured_supported": list(STRUCTURED_EVENT_COMMANDS),
        "raw_preserved": True,
        "scene_lint": True,
        "navigation_graph": True,
        "structured_command_builder": True,
        "hmi_emit": True,
        "tft_bytecode_support": EVENT_BYTECODE_SUPPORT,
        "bytecode_complete": False,
        "live_proven": False,
        "not_claimed": [
            "complete official USART HMI event compiler compatibility",
            "runtime behavior without fixture, bytecode, or live proof",
            "automatic rewrite of every raw script reference",
        ],
    }


def list_event_command_snippets() -> dict[str, Any]:
    return {
        "event_capabilities": event_capability_manifest(),
        "snippets": [dict(item) for item in EVENT_COMMAND_SNIPPETS],
    }


def build_event_command_line(
    command: str,
    *,
    target: str | None = None,
    value: str | int | None = None,
    op: str = "=",
    attribute: str = "val",
    hex_bytes: str | list[str] | list[int] | tuple[str | int, ...] | None = None,
    delay_ms: int | None = None,
    raw_line: str | None = None,
) -> dict[str, Any]:
    """Build one guarded scene-event source line from structured parameters."""
    cmd = command.strip().lower()
    if cmd == "raw":
        if not raw_line or not raw_line.strip():
            raise ValueError("raw event command requires raw_line")
        return _built_line(cmd, raw_line.strip())
    if cmd == "page":
        return _built_line(cmd, f"page {_require_target(cmd, target)}")
    if cmd == "ref":
        return _built_line(cmd, f"ref {_require_target(cmd, target)}")
    if cmd in {"vis", "tsw", "click"}:
        if value is None:
            raise ValueError(f"{cmd} event command requires value")
        return _built_line(cmd, f"{cmd} {_require_target(cmd, target)},{_format_scalar(value)}")
    if cmd == "get":
        return _built_line(cmd, f"get {_attribute_target(_require_target(cmd, target), attribute)}")
    if cmd == "set":
        if op not in _SET_OPS:
            raise ValueError(f"set event command op must be one of {', '.join(sorted(_SET_OPS))}")
        attr_target = _attribute_target(_require_target(cmd, target), attribute)
        if op in {"++", "--"}:
            return _built_line(cmd, f"{attr_target}{op}")
        if value is None:
            raise ValueError(f"set event command op {op} requires value")
        return _built_line(cmd, f"{attr_target}{op}{_format_scalar(value)}")
    if cmd == "printh":
        return _built_line(cmd, f"printh {_format_hex_bytes(hex_bytes)}")
    if cmd == "delay":
        if delay_ms is None:
            raise ValueError("delay event command requires delay_ms")
        if delay_ms < 0:
            raise ValueError("delay_ms must be non-negative")
        return _built_line(cmd, f"delay={int(delay_ms)}")
    if cmd == "file_stream_open":
        source = _require_value(cmd, value)
        if "." not in source:
            source = _attribute_target(source, "txt")
        return _built_line(cmd, f"{_require_target(cmd, target)}.open({source})")
    raise ValueError(f"Unsupported structured event command: {command}")


def lint_scene_events(path: str | Path) -> dict[str, Any]:
    scene = load_scene(path)
    analysis = analyze_scene_events(scene)
    return {
        "scene_path": str(Path(path).resolve()),
        **analysis,
    }


def graph_scene_events(path: str | Path) -> dict[str, Any]:
    scene = load_scene(path)
    analysis = analyze_scene_events(scene)
    return {
        "scene_path": str(Path(path).resolve()),
        "nodes": [
            {
                "id": page.id,
                "index": index,
                "widget_count": len(page.widgets),
            }
            for index, page in enumerate(scene.pages)
        ],
        "edges": analysis["navigation_graph"],
        "diagnostics": [
            item
            for item in analysis["diagnostics"]
            if item.get("code") in {"MISSING_PAGE_REFERENCE", "UNRESOLVED_PAGE_INDEX"}
        ],
        "event_capabilities": analysis["event_capabilities"],
    }


def analyze_scene_events(scene: SceneModel) -> dict[str, Any]:
    page_ids = {page.id for page in scene.pages}
    widgets_by_page = {page.id: {widget.id: widget for widget in page.widgets} for page in scene.pages}
    event_summary: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    navigation_graph: list[dict[str, Any]] = []

    for page in scene.pages:
        _collect_event_owner_analysis(
            event_summary,
            diagnostics,
            navigation_graph,
            scene,
            page,
            page.events,
            widget=None,
            page_ids=page_ids,
            widgets_by_page=widgets_by_page,
        )
        for widget in page.widgets:
            _collect_event_owner_analysis(
                event_summary,
                diagnostics,
                navigation_graph,
                scene,
                page,
                widget.events,
                widget=widget,
                page_ids=page_ids,
                widgets_by_page=widgets_by_page,
            )

    error_count = sum(1 for item in diagnostics if item.get("severity") == "error")
    warning_count = sum(1 for item in diagnostics if item.get("severity") == "warning")
    return {
        "event_capabilities": event_capability_manifest(),
        "event_summary": event_summary,
        "navigation_graph": navigation_graph,
        "diagnostics": diagnostics,
        "summary": {
            "event_slot_count": len(event_summary),
            "command_count": sum(len(item["commands"]) for item in event_summary),
            "navigation_edge_count": len(navigation_graph),
            "error_count": error_count,
            "warning_count": warning_count,
            "ok": error_count == 0,
        },
    }


def _collect_event_owner_analysis(
    event_summary: list[dict[str, Any]],
    diagnostics: list[dict[str, Any]],
    navigation_graph: list[dict[str, Any]],
    scene: SceneModel,
    page: PageSpec,
    events: dict[str, list[str]],
    *,
    widget: WidgetSpec | None,
    page_ids: set[str],
    widgets_by_page: dict[str, dict[str, WidgetSpec]],
) -> None:
    for event_name, lines in events.items():
        if not lines:
            continue
        owner_path = page.id if widget is None else f"{page.id}.{widget.id}"
        slot_path = f"{owner_path}.{event_name}"
        commands = [
            parse_event_line(
                line,
                scene=scene,
                current_page=page,
                page_ids=page_ids,
                widgets_by_page=widgets_by_page,
                line_index=line_index,
            )
            for line_index, line in enumerate(lines)
        ]
        slot_warnings = [warning for command in commands for warning in command.get("warnings", [])]
        for warning in slot_warnings:
            diagnostics.append({**warning, "path": slot_path, "page": page.id, "widget": widget.id if widget else None, "event": event_name})
        for command in commands:
            if command.get("cmd") == "page":
                navigation_graph.append(
                    {
                        "from_page": page.id,
                        "from_object": widget.id if widget else None,
                        "event": event_name,
                        "to_page": command.get("target"),
                        "resolved_page": command.get("resolved_page"),
                        "resolved": bool(command.get("resolved")),
                        "line_index": command.get("line_index"),
                    }
                )
        event_summary.append(
            {
                "path": slot_path,
                "kind": "page" if widget is None else "widget",
                "page": page.id,
                "widget": widget.id if widget else None,
                "event": event_name,
                "line_count": len(lines),
                "lines": list(lines),
                "commands": commands,
                "warnings": slot_warnings,
            }
        )


def parse_event_line(
    line: str,
    *,
    scene: SceneModel,
    current_page: PageSpec,
    page_ids: set[str],
    widgets_by_page: dict[str, dict[str, WidgetSpec]],
    line_index: int,
) -> dict[str, Any]:
    stripped = line.strip().lstrip("\ufeff").strip()
    lower = stripped.lower()
    if not stripped:
        return _command("blank", line, line_index, structured=False)
    if lower.startswith("page "):
        target = stripped.split(None, 1)[1].strip()
        resolved, resolved_page, warnings = _resolve_page_target(scene, target, page_ids)
        return _command("page", line, line_index, target=target, resolved=resolved, resolved_page=resolved_page, warnings=warnings)
    if lower.startswith("ref "):
        target = stripped.split(None, 1)[1].strip()
        warnings = _object_reference_warnings(target, current_page, widgets_by_page)
        return _command("ref", line, line_index, target=target, resolved=not warnings, warnings=warnings)
    if lower.startswith(("vis ", "tsw ", "click ")):
        cmd, rest = stripped.split(None, 1)
        target, value = _split_target_value(rest)
        warnings = _object_reference_warnings(target, current_page, widgets_by_page)
        return _command(cmd.lower(), line, line_index, target=target, value=value, resolved=not warnings, warnings=warnings)
    if lower.startswith("get "):
        target = stripped.split(None, 1)[1].strip()
        warnings = _attribute_reference_warnings(target, current_page, widgets_by_page)
        return _command("get", line, line_index, target=target, resolved=not warnings, warnings=warnings)
    if lower.startswith("printh "):
        raw_bytes = stripped.split(None, 1)[1].strip()
        parsed_bytes, warnings = _parse_printh_bytes(raw_bytes)
        return _command("printh", line, line_index, bytes=parsed_bytes, resolved=not warnings, warnings=warnings)
    if lower.startswith("delay=") or lower.startswith("delay "):
        raw_value = stripped.split("=", 1)[1] if "=" in stripped else stripped.split(None, 1)[1]
        warnings: list[dict[str, Any]] = []
        try:
            delay_ms = int(raw_value.strip(), 0)
            if delay_ms < 0:
                raise ValueError
        except ValueError:
            delay_ms = None
            warnings.append(_warning("INVALID_DELAY", "delay value must be a non-negative integer", severity="error"))
        return _command("delay", line, line_index, value=delay_ms, resolved=not warnings, warnings=warnings)
    method_call = _parse_file_stream_open_method_call(stripped, current_page, widgets_by_page)
    if method_call is not None:
        return _command("file_stream_open", line, line_index, **method_call)
    assignment = _ASSIGN_RE.match(stripped)
    if assignment:
        target = assignment.group("target")
        warnings = _attribute_reference_warnings(target, current_page, widgets_by_page)
        return _command(
            "set",
            line,
            line_index,
            target=target,
            op=assignment.group("op"),
            value=assignment.group("value").strip() or None,
            resolved=not warnings,
            warnings=warnings,
        )
    return _command(
        "raw",
        line,
        line_index,
        structured=False,
        resolved=False,
        warnings=[_warning("UNKNOWN_EVENT_COMMAND", "event line is preserved as raw text but is not structurally understood")],
    )


def _built_line(command: str, line: str) -> dict[str, Any]:
    return {
        "command": command,
        "line": line,
        "structured": command in STRUCTURED_EVENT_COMMANDS,
        "safe_to_flash": False,
        "not_claimed": [
            "structured event builder does not prove official bytecode or runtime scheduling",
            "hardware upload remains a separate explicit operation",
        ],
    }


def _require_target(command: str, target: str | None) -> str:
    if target is None or not str(target).strip():
        raise ValueError(f"{command} event command requires target")
    return str(target).strip()


def _require_value(command: str, value: str | int | None) -> str:
    if value is None or not str(value).strip():
        raise ValueError(f"{command} event command requires value")
    return str(value).strip()


def _attribute_target(target: str, attribute: str) -> str:
    cleaned = target.strip()
    if "." in cleaned:
        return cleaned
    attr = attribute.strip() if attribute else "val"
    if not attr:
        raise ValueError("attribute must be non-empty")
    return f"{cleaned}.{attr}"


def _format_scalar(value: str | int) -> str:
    if isinstance(value, int):
        return str(value)
    return str(value).strip()


def _format_hex_bytes(hex_bytes: str | list[str] | list[int] | tuple[str | int, ...] | None) -> str:
    if hex_bytes is None:
        raise ValueError("printh event command requires hex_bytes")
    if isinstance(hex_bytes, str):
        tokens = hex_bytes.replace(",", " ").split()
    else:
        tokens = [f"{item:02X}" if isinstance(item, int) else str(item) for item in hex_bytes]
    if not tokens:
        raise ValueError("printh event command requires at least one byte")
    normalized: list[str] = []
    for token in tokens:
        try:
            value = int(str(token), 16)
        except ValueError as exc:
            raise ValueError(f"invalid printh byte: {token}") from exc
        if value < 0 or value > 255:
            raise ValueError(f"printh byte out of range: {token}")
        normalized.append(f"{value:02X}")
    return " ".join(normalized)


def _command(cmd: str, line: str, line_index: int, **extra: Any) -> dict[str, Any]:
    warnings = extra.pop("warnings", [])
    return {
        "cmd": cmd,
        "line": line,
        "line_index": line_index,
        "structured": bool(extra.pop("structured", cmd in STRUCTURED_EVENT_COMMANDS)),
        "warnings": warnings,
        **extra,
    }


def _resolve_page_target(scene: SceneModel, target: str, page_ids: set[str]) -> tuple[bool, str | None, list[dict[str, Any]]]:
    if target in page_ids:
        return True, target, []
    try:
        page_index = int(target, 0)
    except ValueError:
        page_index = -1
    if 0 <= page_index < len(scene.pages):
        return True, scene.pages[page_index].id, []
    code = "UNRESOLVED_PAGE_INDEX" if target.isdigit() else "MISSING_PAGE_REFERENCE"
    return False, None, [_warning(code, f"page target {target!r} does not resolve to a scene page", severity="error")]


def _split_target_value(rest: str) -> tuple[str, str | None]:
    if "," not in rest:
        return rest.strip(), None
    target, value = rest.split(",", 1)
    return target.strip(), value.strip()


def _attribute_reference_warnings(
    target: str,
    current_page: PageSpec,
    widgets_by_page: dict[str, dict[str, WidgetSpec]],
) -> list[dict[str, Any]]:
    if _SYSTEM_VAR_RE.match(target.strip()):
        return []
    object_id = target.split(".", 1)[0].strip()
    return _object_reference_warnings(object_id, current_page, widgets_by_page)


def _object_reference_warnings(
    object_id: str,
    current_page: PageSpec,
    widgets_by_page: dict[str, dict[str, WidgetSpec]],
) -> list[dict[str, Any]]:
    if object_id in {"", "sys", "dp"}:
        return []
    if object_id in widgets_by_page.get(current_page.id, {}):
        return []
    pages = [page_id for page_id, widgets in widgets_by_page.items() if object_id in widgets]
    if pages:
        return [_warning("CROSS_PAGE_OBJECT_REFERENCE", f"object {object_id!r} exists on page(s) {pages}, not current page {current_page.id!r}")]
    return [_warning("MISSING_OBJECT_REFERENCE", f"object {object_id!r} does not exist on current page {current_page.id!r}", severity="error")]


def _parse_file_stream_open_method_call(
    stripped: str,
    current_page: PageSpec,
    widgets_by_page: dict[str, dict[str, WidgetSpec]],
) -> dict[str, Any] | None:
    method_call = _METHOD_CALL_RE.match(stripped)
    if method_call is None:
        return None
    method = method_call.group("method")
    if method.lower() != "open":
        return None

    object_id = method_call.group("object")
    arg = method_call.group("arg").strip()
    widgets = widgets_by_page.get(current_page.id, {})
    target_widget = widgets.get(object_id)
    if target_widget is None or _normalized_widget_type(target_widget) != "file-stream":
        return None

    warnings: list[dict[str, Any]] = []
    argument_match = _ATTR_TARGET_RE.match(arg)
    if argument_match is None:
        warnings.append(
            _warning(
                "UNSUPPORTED_FILE_STREAM_OPEN_ARGUMENT",
                "file-stream open currently supports only a text widget .txt argument",
                severity="error",
            )
        )
        return {
            "target": object_id,
            "method": method,
            "argument": arg,
            "resolved": False,
            "warnings": warnings,
            "hardware_proof": "case72-button-down-fs0-open-text-txt",
        }

    argument_object = argument_match.group("object")
    argument_attr = argument_match.group("attr")
    if argument_attr != "txt":
        warnings.append(
            _warning(
                "UNSUPPORTED_FILE_STREAM_OPEN_ARGUMENT",
                "file-stream open argument must use the .txt attribute",
                severity="error",
            )
        )
    argument_widget = widgets.get(argument_object)
    if argument_widget is None:
        warnings.extend(_object_reference_warnings(argument_object, current_page, widgets_by_page))
    elif _normalized_widget_type(argument_widget) != "text":
        warnings.append(
            _warning(
                "UNSUPPORTED_FILE_STREAM_OPEN_ARGUMENT",
                "file-stream open argument must reference a text widget",
                severity="error",
            )
        )

    return {
        "target": object_id,
        "method": method,
        "argument": arg,
        "argument_target": argument_object,
        "argument_attr": argument_attr,
        "resolved": not warnings,
        "warnings": warnings,
        "hardware_proof": "case72-button-down-fs0-open-text-txt",
    }


def _normalized_widget_type(widget: WidgetSpec) -> str:
    value = widget.type.replace("_", "-").replace(" ", "-").lower()
    aliases = {
        "filestream": "file-stream",
        "file-stream": "file-stream",
        "text": "text",
    }
    return aliases.get(value, value)


def _parse_printh_bytes(raw_bytes: str) -> tuple[list[int], list[dict[str, Any]]]:
    parsed: list[int] = []
    warnings: list[dict[str, Any]] = []
    for token in raw_bytes.split():
        try:
            value = int(token, 16)
        except ValueError:
            warnings.append(_warning("INVALID_PRINTH_BYTE", f"printh byte {token!r} is not hex", severity="error"))
            continue
        if value < 0 or value > 255:
            warnings.append(_warning("INVALID_PRINTH_BYTE", f"printh byte {token!r} is outside 00..FF", severity="error"))
            continue
        parsed.append(value)
    if not parsed:
        warnings.append(_warning("EMPTY_PRINTH", "printh requires at least one byte", severity="error"))
    return parsed, warnings


def _warning(code: str, message: str, *, severity: str = "warning") -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
    }
