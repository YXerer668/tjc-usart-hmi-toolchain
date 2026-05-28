from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import difflib
import json
from pathlib import Path
import re
from typing import Any, Mapping

import yaml

from .event_logic import analyze_scene_events, build_event_command_line
from .scene import AssetSpec, PageSpec, SceneError, SceneModel, WidgetSpec, load_scene, validate_scene


EVENT_NAMES = ("load", "loadend", "down", "up", "unload", "timer", "slide")
EVENT_BYTECODE_SUPPORT = "partial/guarded"
EVENT_NOT_CLAIMED = (
    "complete official USART HMI event compiler compatibility",
    "runtime behavior without fixture, bytecode, or live proof",
    "physical touch proof from serial click alone",
    "fixture-backed limited-claim widget TFT/live behavior outside documented cases",
)


@dataclass(frozen=True, slots=True)
class EventTarget:
    page_id: str
    event_name: str
    widget_id: str | None = None

    @property
    def path(self) -> str:
        if self.widget_id is None:
            return f"{self.page_id}.{self.event_name}"
        return f"{self.page_id}.{self.widget_id}.{self.event_name}"

    @property
    def kind(self) -> str:
        return "page" if self.widget_id is None else "widget"


def read_scene_document(path: str | Path) -> dict[str, Any]:
    file_path = Path(path).resolve()
    raw_text = file_path.read_text(encoding="utf-8")
    if file_path.suffix.lower() in {".yaml", ".yml"}:
        payload = yaml.safe_load(raw_text)
    else:
        payload = json.loads(raw_text)
    if not isinstance(payload, dict):
        raise SceneError("Scene root must be an object")
    return payload


def write_scene_document(path: str | Path, payload: Mapping[str, Any]) -> Path:
    file_path = Path(path).resolve()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if file_path.suffix.lower() in {".yaml", ".yml"}:
        text = yaml.safe_dump(dict(payload), allow_unicode=True, sort_keys=False)
    else:
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    file_path.write_text(text, encoding="utf-8")
    return file_path


def create_scene_document(
    path: str | Path,
    *,
    project_name: str | None = None,
    width: int = 800,
    height: int = 480,
    default_page: str = "page0",
    background_color: int = 65535,
    overwrite: bool = False,
) -> dict[str, Any]:
    file_path = Path(path).resolve()
    if file_path.exists() and not overwrite:
        raise SceneError(f"Scene already exists: {file_path}")
    if not default_page:
        raise SceneError("default page id must be non-empty")
    payload: dict[str, Any] = {
        "project": {"name": project_name or file_path.stem or "usarthmi-scene", "default_page": default_page},
        "canvas": {"width": int(width), "height": int(height), "background_color": int(background_color)},
        "assets": {},
        "pages": [
            {
                "id": default_page,
                "layout": {"type": "absolute"},
                "events": {},
                "widgets": [],
            }
        ],
    }
    scene = validate_scene(deepcopy(payload))
    write_scene_document(file_path, scene.to_dict())
    return _scene_document_result(file_path, scene)


def save_scene_document_as(
    source_path: str | Path,
    dest_path: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    source = Path(source_path).resolve()
    destination = Path(dest_path).resolve()
    if destination.exists() and not overwrite:
        raise SceneError(f"Scene already exists: {destination}")
    payload = read_scene_document(source)
    scene = validate_scene(deepcopy(payload))
    document = scene.to_dict()
    document["project"] = {
        key: value
        for key, value in document.get("project", {}).items()
        if not str(key).startswith("_")
    }
    write_scene_document(destination, document)
    return {
        "source_path": str(source),
        **_scene_document_result(destination, validate_scene(deepcopy(document))),
    }


def update_scene_project(
    path: str | Path,
    *,
    name: str | None = None,
    default_page: str | None = None,
    width: int | None = None,
    height: int | None = None,
    background_color: int | None = None,
) -> dict[str, Any]:
    payload = read_scene_document(path)
    project = payload.get("project")
    canvas = payload.get("canvas")
    if not isinstance(project, dict):
        raise SceneError("project must be an object")
    if not isinstance(canvas, dict):
        raise SceneError("canvas must be an object")

    changed = False
    if name is not None:
        if not name:
            raise SceneError("project name must be non-empty")
        project["name"] = name
        changed = True
    if default_page is not None:
        if not default_page:
            raise SceneError("default page id must be non-empty")
        _assert_page_exists(payload, default_page)
        project["default_page"] = default_page
        changed = True
    if width is not None:
        canvas["width"] = _positive_int(width, "canvas.width")
        changed = True
    if height is not None:
        canvas["height"] = _positive_int(height, "canvas.height")
        changed = True
    if background_color is not None:
        canvas["background_color"] = int(background_color)
        changed = True
    if not changed:
        raise SceneError("scene project update requires at least one property option")

    scene = validate_scene(deepcopy(payload))
    _assert_project_default_page_exists(scene)
    write_scene_document(path, scene.to_dict())
    return _scene_document_result(Path(path).resolve(), scene)


def update_scene_page(
    path: str | Path,
    *,
    page_id: str,
    new_id: str | None = None,
    layout: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = read_scene_document(path)
    page, page_index = _find_page_with_index(payload, page_id)

    changed = False
    old_page_id = str(page.get("id"))
    warnings: list[dict[str, Any]] = []
    if new_id is not None:
        if not new_id:
            raise SceneError("page id must be non-empty")
        if new_id != old_page_id:
            _assert_unique_page_id(payload, new_id)
            warnings = _collect_page_rename_warnings(payload, old_page_id, new_id)
            page["id"] = new_id
            project = payload.get("project")
            if isinstance(project, dict) and project.get("default_page") == old_page_id:
                project["default_page"] = new_id
            changed = True
    if layout is not None:
        if not isinstance(layout, Mapping):
            raise SceneError("page layout update must be an object")
        page["layout"] = dict(layout)
        changed = True
    if not changed:
        raise SceneError("scene pages update requires --id or --layout-json")

    scene = validate_scene(deepcopy(payload))
    _assert_project_default_page_exists(scene)
    updated_id = new_id if new_id is not None else old_page_id
    updated_page = _find_model_page(scene, str(updated_id))
    write_scene_document(path, scene.to_dict())
    return {
        "scene_path": str(Path(path).resolve()),
        "page": _page_result(updated_page),
        "page_index": page_index,
        "old_page_id": old_page_id if updated_id != old_page_id else None,
        "default_page": scene.project.get("default_page"),
        "warnings": warnings,
    }


def normalize_event_map(events: Mapping[str, str | list[str] | tuple[str, ...] | None]) -> dict[str, list[str]]:
    normalized: dict[str, list[str]] = {}
    for name in EVENT_NAMES:
        value = events.get(name)
        if value is None:
            continue
        lines = normalize_event_lines(name, value)
        if lines:
            normalized[name] = lines
    unknown = sorted(set(events) - set(EVENT_NAMES))
    if unknown:
        raise SceneError(f"Unsupported event name(s): {', '.join(unknown)}")
    return normalized


def normalize_event_lines(
    event_name: str,
    lines: str | list[str] | tuple[str, ...] | None,
) -> list[str]:
    if event_name not in EVENT_NAMES:
        raise SceneError(f"Unsupported event name: {event_name}")
    if lines is None:
        return []
    if isinstance(lines, str):
        return [line.rstrip() for line in lines.splitlines() if line.strip()]
    if isinstance(lines, (list, tuple)) and all(isinstance(item, str) for item in lines):
        return [line.rstrip() for line in lines if line.strip()]
    raise SceneError(f"event '{event_name}' must be a string or list of strings")


def parse_event_path(value: str) -> EventTarget:
    parts = [part.strip() for part in value.split(".") if part.strip()]
    if len(parts) == 2 and parts[1] in EVENT_NAMES:
        return EventTarget(page_id=parts[0], event_name=parts[1])
    if len(parts) == 3 and parts[2] in EVENT_NAMES:
        return EventTarget(page_id=parts[0], widget_id=parts[1], event_name=parts[2])
    expected = "page.event or page.widget.event, for example page0.load or page0.btn0.down"
    raise SceneError(f"Invalid event path '{value}'; expected {expected}")


def list_scene_events(path: str | Path, *, include_empty: bool = True) -> dict[str, Any]:
    scene = load_scene(path)
    return {
        "scene_path": str(Path(path).resolve()),
        "events": collect_scene_event_slots(scene, include_empty=include_empty),
        "event_model": event_model_manifest(),
    }


def collect_scene_event_slots(scene: SceneModel, *, include_empty: bool = True) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    for page in scene.pages:
        slots.extend(_page_event_slots(page, include_empty=include_empty))
        for widget in page.widgets:
            slots.extend(_widget_event_slots(page, widget, include_empty=include_empty))
    return slots


def get_scene_event(path: str | Path, event_path: str) -> dict[str, Any]:
    target = parse_event_path(event_path)
    scene = load_scene(path)
    page = _find_model_page(scene, target.page_id)
    if target.widget_id is None:
        return _event_slot(target, page.events.get(target.event_name, []))
    widget = _find_model_widget(page, target.widget_id)
    return _event_slot(target, widget.events.get(target.event_name, []), widget=widget)


def set_scene_event(
    path: str | Path,
    event_path: str,
    lines: str | list[str] | tuple[str, ...],
    *,
    append: bool = False,
) -> dict[str, Any]:
    target = parse_event_path(event_path)
    payload = read_scene_document(path)
    owner = _find_event_owner(payload, target)
    events = dict(owner.get("events") or {})
    new_lines = normalize_event_lines(target.event_name, lines)
    if append:
        existing = normalize_event_lines(target.event_name, events.get(target.event_name))
        new_lines = [*existing, *new_lines]
    if new_lines:
        events[target.event_name] = new_lines
    else:
        events.pop(target.event_name, None)
    owner["events"] = events
    validate_scene(deepcopy(payload))
    write_scene_document(path, payload)
    return get_scene_event(path, event_path)


def append_scene_event_command(
    path: str | Path,
    event_path: str,
    *,
    command: str,
    target: str | None = None,
    value: str | int | None = None,
    op: str = "=",
    attribute: str = "val",
    hex_bytes: str | list[str] | list[int] | tuple[str | int, ...] | None = None,
    delay_ms: int | None = None,
    raw_line: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    try:
        built = build_event_command_line(
            command,
            target=target,
            value=value,
            op=op,
            attribute=attribute,
            hex_bytes=hex_bytes,
            delay_ms=delay_ms,
            raw_line=raw_line,
        )
    except ValueError as exc:
        raise SceneError(str(exc)) from exc
    if dry_run:
        slot = get_scene_event(path, event_path)
        return {
            "scene_path": str(Path(path).resolve()),
            "event": slot,
            "command": built,
            "dry_run": True,
        }
    slot = set_scene_event(path, event_path, [built["line"]], append=True)
    return {
        "scene_path": str(Path(path).resolve()),
        "event": slot,
        "command": built,
        "dry_run": False,
        "op": {
            "op": "append_event_command",
            "path": event_path,
            "line": built["line"],
        },
    }


def list_scene_event_commands(path: str | Path, event_path: str) -> dict[str, Any]:
    target = parse_event_path(event_path)
    scene = load_scene(path)
    slot = get_scene_event(path, event_path)
    slot_analysis = _event_command_slot_analysis(scene, target)
    analysis = analyze_scene_events(scene)
    return {
        "scene_path": str(Path(path).resolve()),
        "event": slot,
        "commands": slot_analysis["commands"],
        "slot_warnings": slot_analysis.get("warnings", []),
        "diagnostics": [
            item for item in analysis["diagnostics"] if item.get("path") == target.path
        ],
        "event_capabilities": analysis["event_capabilities"],
        "safe_to_flash": False,
    }


def edit_scene_event_command(
    path: str | Path,
    event_path: str,
    *,
    action: str,
    index: int | None = None,
    to_index: int | None = None,
    line: str | None = None,
    command: str | None = None,
    target: str | None = None,
    value: str | int | None = None,
    op: str = "=",
    attribute: str = "val",
    hex_bytes: str | list[str] | list[int] | tuple[str | int, ...] | None = None,
    delay_ms: int | None = None,
    raw_line: str | None = None,
    dry_run: bool = False,
    simulate: bool = False,
    out_dir: str | Path | None = None,
    max_steps: int = 128,
) -> dict[str, Any]:
    """Patch one event command line without replacing the whole event slot."""
    normalized_action = action.strip().lower().replace("_", "-")
    if normalized_action not in {"insert", "replace", "delete", "move"}:
        raise SceneError("event command action must be one of insert, replace, delete, move")
    if max_steps <= 0:
        raise SceneError("max_steps must be a positive integer")

    source_path = Path(path).resolve()
    target_slot = parse_event_path(event_path)
    before_payload = read_scene_document(source_path)
    before_scene = validate_scene(deepcopy(before_payload))
    after_payload = deepcopy(before_payload)
    owner = _find_event_owner(after_payload, target_slot)
    events = dict(owner.get("events") or {})
    before_lines = normalize_event_lines(target_slot.event_name, events.get(target_slot.event_name))
    after_lines = list(before_lines)

    built: dict[str, Any] | None = None
    removed_line: str | None = None
    moved_line: str | None = None
    inserted_line: str | None = None

    if normalized_action in {"insert", "replace"}:
        built = _event_command_patch_line(
            target_slot.event_name,
            line=line,
            command=command,
            target=target,
            value=value,
            op=op,
            attribute=attribute,
            hex_bytes=hex_bytes,
            delay_ms=delay_ms,
            raw_line=raw_line,
        )
        inserted_line = built["line"]

    if normalized_action == "insert":
        insert_at = _validate_event_insert_index(index, len(after_lines))
        after_lines.insert(insert_at, inserted_line or "")
        operation: dict[str, Any] = {"action": normalized_action, "index": insert_at, "line": inserted_line}
    elif normalized_action == "replace":
        replace_at = _validate_event_line_index(index, len(after_lines), "replace")
        removed_line = after_lines[replace_at]
        after_lines[replace_at] = inserted_line or ""
        operation = {
            "action": normalized_action,
            "index": replace_at,
            "old_line": removed_line,
            "line": inserted_line,
        }
    elif normalized_action == "delete":
        delete_at = _validate_event_line_index(index, len(after_lines), "delete")
        removed_line = after_lines.pop(delete_at)
        operation = {"action": normalized_action, "index": delete_at, "old_line": removed_line}
    else:
        from_at = _validate_event_line_index(index, len(after_lines), "move")
        if to_index is None:
            raise SceneError("move event command requires to_index")
        moved_line = after_lines.pop(from_at)
        insert_at = _validate_event_insert_index(to_index, len(after_lines))
        after_lines.insert(insert_at, moved_line)
        operation = {
            "action": normalized_action,
            "from_index": from_at,
            "to_index": insert_at,
            "line": moved_line,
        }

    if after_lines:
        events[target_slot.event_name] = after_lines
    else:
        events.pop(target_slot.event_name, None)
    owner["events"] = events
    after_scene = validate_scene(deepcopy(after_payload))

    if not dry_run:
        write_scene_document(source_path, after_scene.to_dict())

    analysis_after = analyze_scene_events(after_scene)
    diff = _event_line_diff(target_slot.path, before_lines, after_lines)
    result: dict[str, Any] = {
        "scene_path": str(source_path),
        "event_path": target_slot.path,
        "dry_run": bool(dry_run),
        "operation": {
            **operation,
            "command": built,
            "safe_to_flash": False,
        },
        "event_before": _event_slot_from_scene(before_scene, target_slot, before_lines),
        "event_after": _event_slot_from_scene(after_scene, target_slot, after_lines),
        "commands_after": _event_command_slot_analysis(after_scene, target_slot)["commands"],
        "diff": diff,
        "lint_after": {
            "summary": analysis_after["summary"],
            "diagnostics": [
                item for item in analysis_after["diagnostics"] if item.get("path") == target_slot.path
            ],
        },
        "safe_to_flash": False,
        "not_claimed": [
            "event command patching is source-level authoring, not official bytecode proof",
            "offline simulation is not physical panel behavior",
            "hardware upload remains a separate explicit user action",
        ],
    }

    if simulate:
        result["simulation"] = _simulate_event_command_patch(
            before_scene,
            after_scene,
            target_slot.path,
            source_path=source_path,
            out_dir=out_dir,
            max_steps=max_steps,
        )

    if out_dir is not None:
        result["outputs"] = _write_event_command_patch_outputs(result, out_dir)
    return result


def clear_scene_event(path: str | Path, event_path: str) -> dict[str, Any]:
    target = parse_event_path(event_path)
    payload = read_scene_document(path)
    owner = _find_event_owner(payload, target)
    events = dict(owner.get("events") or {})
    events.pop(target.event_name, None)
    owner["events"] = events
    validate_scene(deepcopy(payload))
    write_scene_document(path, payload)
    return get_scene_event(path, event_path)


def list_scene_assets(path: str | Path) -> dict[str, Any]:
    scene = load_scene(path)
    return {
        "scene_path": str(Path(path).resolve()),
        "assets": [_asset_result(key, asset) for key, asset in scene.assets.items()],
    }


def add_scene_asset(path: str | Path, *, asset_id: str, asset: Mapping[str, Any]) -> dict[str, Any]:
    payload = read_scene_document(path)
    assets = _scene_assets(payload)
    if not asset_id:
        raise SceneError("new asset requires a non-empty id")
    if asset_id in assets:
        raise SceneError(f"Asset '{asset_id}' already exists in scene")
    assets[asset_id] = _clean_asset_document(asset, default_id=asset_id)
    scene = validate_scene(deepcopy(payload))
    write_scene_document(path, scene.to_dict())
    return {
        "scene_path": str(Path(path).resolve()),
        "asset": _asset_result(asset_id, _find_model_asset(scene, asset_id)),
    }


def update_scene_asset(path: str | Path, *, asset_id: str, updates: Mapping[str, Any]) -> dict[str, Any]:
    payload = read_scene_document(path)
    assets = _scene_assets(payload)
    if asset_id not in assets:
        raise SceneError(f"Asset '{asset_id}' not found in scene")
    asset_doc = assets[asset_id]
    if not isinstance(asset_doc, dict):
        raise SceneError(f"asset '{asset_id}' must be an object")
    _apply_asset_updates(asset_doc, updates)
    scene = validate_scene(deepcopy(payload))
    write_scene_document(path, scene.to_dict())
    return {
        "scene_path": str(Path(path).resolve()),
        "asset": _asset_result(asset_id, _find_model_asset(scene, asset_id)),
    }


def delete_scene_asset(path: str | Path, *, asset_id: str, force: bool = False) -> dict[str, Any]:
    scene_before = load_scene(path)
    deleted = _find_model_asset(scene_before, asset_id)
    payload = read_scene_document(path)
    assets = _scene_assets(payload)
    if asset_id not in assets:
        raise SceneError(f"Asset '{asset_id}' not found in scene")
    references = _find_asset_references(payload, asset_id)
    if references and not force:
        raise SceneError(f"Asset '{asset_id}' is still referenced; pass force=True or --force to delete it")
    assets.pop(asset_id)
    scene = validate_scene(deepcopy(payload))
    write_scene_document(path, scene.to_dict())
    return {
        "scene_path": str(Path(path).resolve()),
        "deleted_asset": _asset_result(asset_id, deleted),
        "references": references,
        "remaining_assets": len(scene.assets),
    }


def add_scene_widget(path: str | Path, *, page_id: str, widget: Mapping[str, Any]) -> dict[str, Any]:
    payload = read_scene_document(path)
    page = _find_page(payload, page_id)
    widgets = page.setdefault("widgets", [])
    if not isinstance(widgets, list):
        raise SceneError(f"page '{page_id}' widgets must be a list")
    widget_doc = _clean_widget_document(widget)
    widget_id = widget_doc.get("id")
    if not isinstance(widget_id, str) or not widget_id:
        raise SceneError("new widget requires a non-empty id")
    if any(isinstance(item, dict) and item.get("id") == widget_id for item in widgets):
        raise SceneError(f"Widget '{widget_id}' already exists on page '{page_id}'")
    widgets.append(widget_doc)
    scene = validate_scene(deepcopy(payload))
    write_scene_document(path, scene.to_dict())
    created = _find_model_widget(_find_model_page(scene, page_id), widget_id)
    return {
        "scene_path": str(Path(path).resolve()),
        "page": page_id,
        "widget": _widget_result(created),
    }


def update_scene_widget(
    path: str | Path,
    *,
    page_id: str,
    widget_id: str,
    updates: Mapping[str, Any],
    rewrite_event_references: bool = False,
) -> dict[str, Any]:
    payload = read_scene_document(path)
    page = _find_page(payload, page_id)
    widget, index = _find_widget(page, widget_id=widget_id, widget_index=None)
    old_widget_id = str(widget.get("id") or widget_id)
    _apply_widget_updates(widget, updates)
    updated_id = str(widget.get("id") or widget_id)
    _assert_unique_widget_id(page, updated_id, allowed_index=index)
    rewritten_event_references = (
        _rewrite_widget_event_references(payload, page_id, old_widget_id, updated_id)
        if rewrite_event_references and updated_id != old_widget_id
        else []
    )
    warnings = (
        _collect_widget_rename_warnings(payload, page_id, old_widget_id, updated_id)
        if updated_id != old_widget_id
        else []
    )
    scene = validate_scene(deepcopy(payload))
    write_scene_document(path, scene.to_dict())
    updated = _find_model_widget(_find_model_page(scene, page_id), updated_id)
    return {
        "scene_path": str(Path(path).resolve()),
        "page": page_id,
        "old_widget_id": old_widget_id if updated_id != old_widget_id else None,
        "widget": _widget_result(updated),
        "rewritten_event_references": rewritten_event_references,
        "warnings": warnings,
    }


def delete_scene_widget(path: str | Path, *, page_id: str, widget_id: str) -> dict[str, Any]:
    scene_before = load_scene(path)
    deleted = _find_model_widget(_find_model_page(scene_before, page_id), widget_id)
    payload = read_scene_document(path)
    page = _find_page(payload, page_id)
    widgets = _page_widgets(page)
    _widget, index = _find_widget(page, widget_id=widget_id, widget_index=None)
    widgets.pop(index)
    scene = validate_scene(deepcopy(payload))
    write_scene_document(path, scene.to_dict())
    return {
        "scene_path": str(Path(path).resolve()),
        "page": page_id,
        "deleted_widget": _widget_result(deleted),
        "deleted_index": index,
        "remaining_widgets": len(_find_model_page(scene, page_id).widgets),
    }


def duplicate_scene_widget(
    path: str | Path,
    *,
    page_id: str,
    widget_id: str,
    new_id: str | None = None,
    offset_x: int = 16,
    offset_y: int = 16,
) -> dict[str, Any]:
    payload = read_scene_document(path)
    page = _find_page(payload, page_id)
    widgets = _page_widgets(page)
    widget, index = _find_widget(page, widget_id=widget_id, widget_index=None)
    copied = deepcopy(widget)
    copied["id"] = new_id or _next_widget_id(page, str(widget.get("id") or "widget"))
    _assert_unique_widget_id(page, str(copied["id"]), allowed_index=None)
    for key, offset in (("x", offset_x), ("y", offset_y)):
        if copied.get(key) is not None:
            copied[key] = int(copied[key]) + int(offset)
    widgets.insert(index + 1, copied)
    scene = validate_scene(deepcopy(payload))
    write_scene_document(path, scene.to_dict())
    duplicated = _find_model_widget(_find_model_page(scene, page_id), str(copied["id"]))
    return {
        "scene_path": str(Path(path).resolve()),
        "page": page_id,
        "source_widget": widget_id,
        "widget": _widget_result(duplicated),
        "z_index": index + 1,
    }


def copy_scene_widget(path: str | Path, *, page_id: str, widget_id: str) -> dict[str, Any]:
    payload = read_scene_document(path)
    page = _find_page(payload, page_id)
    widget, index = _find_widget(page, widget_id=widget_id, widget_index=None)
    copied = _clean_widget_document(deepcopy(widget))
    return {
        "scene_path": str(Path(path).resolve()),
        "source_page": page_id,
        "source_widget": widget_id,
        "source_z_index": index,
        "clipboard": {
            "kind": "widget",
            "source_page": page_id,
            "source_widget": widget_id,
            "widget": copied,
        },
    }


def cut_scene_widget(path: str | Path, *, page_id: str, widget_id: str) -> dict[str, Any]:
    copied = copy_scene_widget(path, page_id=page_id, widget_id=widget_id)
    deleted = delete_scene_widget(path, page_id=page_id, widget_id=widget_id)
    return {
        "scene_path": str(Path(path).resolve()),
        "source_page": page_id,
        "source_widget": widget_id,
        "clipboard": copied["clipboard"],
        "deleted_widget": deleted["deleted_widget"],
        "deleted_index": deleted["deleted_index"],
        "remaining_widgets": deleted["remaining_widgets"],
        "op": {
            "op": "cut_widget",
            "page": page_id,
            "widget": widget_id,
        },
    }


def paste_scene_widget(
    path: str | Path,
    *,
    page_id: str,
    widget: Mapping[str, Any],
    new_id: str | None = None,
    offset_x: int = 16,
    offset_y: int = 16,
    x: int | None = None,
    y: int | None = None,
) -> dict[str, Any]:
    payload = read_scene_document(path)
    page = _find_page(payload, page_id)
    widgets = _page_widgets(page)
    copied = _clean_widget_document(deepcopy(widget))
    base_id = str(copied.get("id") or "widget")
    if new_id is not None:
        copied["id"] = new_id
        _assert_unique_widget_id(page, str(copied["id"]), allowed_index=None)
    elif any(isinstance(item, dict) and item.get("id") == base_id for item in widgets):
        copied["id"] = _next_widget_id(page, base_id)
    else:
        copied["id"] = base_id
    if x is not None:
        copied["x"] = int(x)
    elif copied.get("x") is not None:
        copied["x"] = int(copied["x"]) + int(offset_x)
    if y is not None:
        copied["y"] = int(y)
    elif copied.get("y") is not None:
        copied["y"] = int(copied["y"]) + int(offset_y)
    widgets.append(copied)
    scene = validate_scene(deepcopy(payload))
    write_scene_document(path, scene.to_dict())
    pasted = _find_model_widget(_find_model_page(scene, page_id), str(copied["id"]))
    return {
        "scene_path": str(Path(path).resolve()),
        "page": page_id,
        "widget": _widget_result(pasted),
        "z_index": len(widgets) - 1,
        "op": {
            "op": "paste_widget",
            "page": page_id,
            "widget": copied["id"],
        },
    }


def copy_scene_widget_to_page(
    path: str | Path,
    *,
    source_page_id: str,
    widget_id: str,
    target_page_id: str,
    new_id: str | None = None,
    offset_x: int = 16,
    offset_y: int = 16,
    x: int | None = None,
    y: int | None = None,
) -> dict[str, Any]:
    copied = copy_scene_widget(path, page_id=source_page_id, widget_id=widget_id)
    pasted = paste_scene_widget(
        path,
        page_id=target_page_id,
        widget=copied["clipboard"]["widget"],
        new_id=new_id,
        offset_x=offset_x,
        offset_y=offset_y,
        x=x,
        y=y,
    )
    return {
        **pasted,
        "source_page": source_page_id,
        "source_widget": widget_id,
        "clipboard": copied["clipboard"],
    }


def move_scene_widget(path: str | Path, *, page_id: str, widget_id: str, direction: str) -> dict[str, Any]:
    payload = read_scene_document(path)
    page = _find_page(payload, page_id)
    widgets = _page_widgets(page)
    _widget, old_index = _find_widget(page, widget_id=widget_id, widget_index=None)
    normalized_direction = direction.strip().lower()
    if normalized_direction == "up":
        new_index = max(0, old_index - 1)
    elif normalized_direction == "down":
        new_index = min(len(widgets) - 1, old_index + 1)
    elif normalized_direction == "front":
        new_index = len(widgets) - 1
    elif normalized_direction == "back":
        new_index = 0
    else:
        raise SceneError("direction must be one of: up, down, front, back")
    if new_index != old_index:
        moved = widgets.pop(old_index)
        widgets.insert(new_index, moved)
    scene = validate_scene(deepcopy(payload))
    write_scene_document(path, scene.to_dict())
    moved_widget = _find_model_widget(_find_model_page(scene, page_id), widget_id)
    return {
        "scene_path": str(Path(path).resolve()),
        "page": page_id,
        "widget": _widget_result(moved_widget),
        "old_z_index": old_index,
        "z_index": new_index,
        "direction": normalized_direction,
        "changed": new_index != old_index,
    }


def add_scene_page(path: str | Path, *, page_id: str, layout: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = read_scene_document(path)
    pages = _scene_pages(payload)
    if not page_id:
        raise SceneError("new page requires a non-empty id")
    _assert_unique_page_id(payload, page_id)
    page_doc = {
        "id": page_id,
        "layout": dict(layout or {"type": "absolute"}),
        "events": {},
        "widgets": [],
    }
    pages.append(page_doc)
    scene = validate_scene(deepcopy(payload))
    write_scene_document(path, scene.to_dict())
    page = _find_model_page(scene, page_id)
    return {
        "scene_path": str(Path(path).resolve()),
        "page": _page_result(page),
        "page_index": len(scene.pages) - 1,
    }


def duplicate_scene_page(path: str | Path, *, page_id: str, new_id: str | None = None) -> dict[str, Any]:
    payload = read_scene_document(path)
    pages = _scene_pages(payload)
    page, index = _find_page_with_index(payload, page_id)
    copied = deepcopy(page)
    copied["id"] = new_id or _next_page_id(payload, page_id)
    _assert_unique_page_id(payload, str(copied["id"]))
    pages.insert(index + 1, copied)
    scene = validate_scene(deepcopy(payload))
    write_scene_document(path, scene.to_dict())
    duplicated = _find_model_page(scene, str(copied["id"]))
    return {
        "scene_path": str(Path(path).resolve()),
        "source_page": page_id,
        "page": _page_result(duplicated),
        "page_index": index + 1,
    }


def delete_scene_page(path: str | Path, *, page_id: str) -> dict[str, Any]:
    scene_before = load_scene(path)
    deleted = _find_model_page(scene_before, page_id)
    payload = read_scene_document(path)
    pages = _scene_pages(payload)
    _page, index = _find_page_with_index(payload, page_id)
    if len(pages) <= 1:
        raise SceneError("Cannot delete the only page in a scene")
    pages.pop(index)
    project = payload.get("project")
    if isinstance(project, dict) and project.get("default_page") == page_id:
        first_page = pages[0]
        if isinstance(first_page, dict):
            project["default_page"] = first_page.get("id")
    scene = validate_scene(deepcopy(payload))
    write_scene_document(path, scene.to_dict())
    return {
        "scene_path": str(Path(path).resolve()),
        "deleted_page": _page_result(deleted),
        "deleted_index": index,
        "remaining_pages": len(scene.pages),
        "default_page": scene.project.get("default_page"),
    }


def event_model_manifest() -> dict[str, Any]:
    return {
        "supported_event_names": list(EVENT_NAMES),
        "source_format": "tjc-script-lines",
        "scene_editing": True,
        "hmi_emit": True,
        "tft_bytecode_support": EVENT_BYTECODE_SUPPORT,
        "live_proven": False,
        "not_claimed": list(EVENT_NOT_CLAIMED),
    }


def set_scene_events(
    path: str | Path,
    *,
    page_id: str,
    events: Mapping[str, str | list[str] | tuple[str, ...] | None],
    widget_id: str | None = None,
    widget_index: int | None = None,
) -> dict[str, Any]:
    """Set page or top-level widget event scripts in a scene file.

    This edits the source scene document, then validates the whole scene. It
    intentionally does not try to compile event bytecode or upload hardware.
    Existing build guardrails remain responsible for rejecting unsupported
    runtime combinations.
    """
    payload = read_scene_document(path)
    target_page = _find_page(payload, page_id)
    normalized_events = normalize_event_map(events)
    if widget_id is None and widget_index is None:
        target_page["events"] = normalized_events
        target = {"kind": "page", "page": page_id}
    else:
        target_widget, resolved_index = _find_widget(target_page, widget_id=widget_id, widget_index=widget_index)
        target_widget["events"] = normalized_events
        target = {
            "kind": "widget",
            "page": page_id,
            "widget": target_widget.get("id"),
            "widget_index": resolved_index,
        }

    validate_scene(deepcopy(payload))
    write_scene_document(path, payload)
    return {
        "scene_path": str(Path(path).resolve()),
        "target": target,
        "events": normalized_events,
    }


def _page_event_slots(page: PageSpec, *, include_empty: bool) -> list[dict[str, Any]]:
    return [
        _event_slot(EventTarget(page_id=page.id, event_name=name), page.events.get(name, []))
        for name in EVENT_NAMES
        if include_empty or page.events.get(name)
    ]


def _widget_event_slots(page: PageSpec, widget: WidgetSpec, *, include_empty: bool) -> list[dict[str, Any]]:
    return [
        _event_slot(
            EventTarget(page_id=page.id, widget_id=widget.id, event_name=name),
            widget.events.get(name, []),
            widget=widget,
        )
        for name in EVENT_NAMES
        if include_empty or widget.events.get(name)
    ]


def _event_slot(target: EventTarget, lines: list[str], *, widget: WidgetSpec | None = None) -> dict[str, Any]:
    warnings = [
        "Event editing is scene-model level; complete official event compiler compatibility is not claimed.",
        "Runtime behavior requires fixture, bytecode, or live hardware proof for the specific event path.",
    ]
    if widget is not None and widget.type in {"text-select", "sliding-text", "data-record", "file-browser", "file-stream"}:
        warnings.append(
            "This widget is supported through a fixture-backed current-target writer, but generic TFT rebuild and live event behavior outside the documented cases are not claimed."
        )
    return {
        "path": target.path,
        "kind": target.kind,
        "page": target.page_id,
        "widget": target.widget_id,
        "event": target.event_name,
        "lines": list(lines),
        "line_count": len(lines),
        "scene_editable": True,
        "hmi_emit": True,
        "tft_bytecode_support": EVENT_BYTECODE_SUPPORT,
        "live_proven": False,
        "warnings": warnings,
    }


def _find_model_page(scene: SceneModel, page_id: str) -> PageSpec:
    for page in scene.pages:
        if page.id == page_id:
            return page
    raise SceneError(f"Page '{page_id}' not found in scene")


def _find_model_asset(scene: SceneModel, asset_id: str) -> AssetSpec:
    asset = scene.assets.get(asset_id)
    if asset is None:
        raise SceneError(f"Asset '{asset_id}' not found in scene")
    return asset


def _find_model_widget(page: PageSpec, widget_id: str) -> WidgetSpec:
    matches = [widget for widget in page.widgets if widget.id == widget_id]
    if not matches:
        raise SceneError(f"Widget '{widget_id}' not found on page '{page.id}'")
    if len(matches) > 1:
        raise SceneError(f"Widget '{widget_id}' is duplicated on page '{page.id}'")
    return matches[0]


def _find_event_owner(payload: Mapping[str, Any], target: EventTarget) -> dict[str, Any]:
    page = _find_page(payload, target.page_id)
    if target.widget_id is None:
        return page
    widget, _index = _find_widget(page, widget_id=target.widget_id, widget_index=None)
    return widget


def _event_command_patch_line(
    event_name: str,
    *,
    line: str | None,
    command: str | None,
    target: str | None,
    value: str | int | None,
    op: str,
    attribute: str,
    hex_bytes: str | list[str] | list[int] | tuple[str | int, ...] | None,
    delay_ms: int | None,
    raw_line: str | None,
) -> dict[str, Any]:
    if line is not None:
        lines = normalize_event_lines(event_name, line)
        if len(lines) != 1:
            raise SceneError("event command line input must contain exactly one non-empty line")
        return {
            "command": "raw-line",
            "line": lines[0],
            "structured": False,
            "safe_to_flash": False,
            "not_claimed": [
                "raw source line is preserved but not necessarily structurally understood",
                "hardware upload remains a separate explicit operation",
            ],
        }
    if command is None:
        raise SceneError("insert/replace event command requires --line, --from-file, or --command")
    try:
        return build_event_command_line(
            command,
            target=target,
            value=value,
            op=op,
            attribute=attribute,
            hex_bytes=hex_bytes,
            delay_ms=delay_ms,
            raw_line=raw_line,
        )
    except ValueError as exc:
        raise SceneError(str(exc)) from exc


def _validate_event_line_index(index: int | None, line_count: int, action: str) -> int:
    if index is None:
        raise SceneError(f"{action} event command requires index")
    resolved = int(index)
    if resolved < 0 or resolved >= line_count:
        raise SceneError(f"{action} event command index {resolved} out of range for {line_count} line(s)")
    return resolved


def _validate_event_insert_index(index: int | None, line_count: int) -> int:
    if index is None:
        return line_count
    resolved = int(index)
    if resolved < 0 or resolved > line_count:
        raise SceneError(f"insert event command index {resolved} out of range for {line_count} line(s)")
    return resolved


def _event_slot_from_scene(scene: SceneModel, target: EventTarget, lines: list[str]) -> dict[str, Any]:
    page = _find_model_page(scene, target.page_id)
    widget = _find_model_widget(page, target.widget_id) if target.widget_id is not None else None
    return _event_slot(target, lines, widget=widget)


def _event_command_slot_analysis(scene: SceneModel, target: EventTarget) -> dict[str, Any]:
    analysis = analyze_scene_events(scene)
    for slot in analysis["event_summary"]:
        if slot.get("path") == target.path:
            return slot
    return {
        "path": target.path,
        "kind": target.kind,
        "page": target.page_id,
        "widget": target.widget_id,
        "event": target.event_name,
        "line_count": 0,
        "lines": [],
        "commands": [],
        "warnings": [],
    }


def _event_line_diff(event_path: str, before_lines: list[str], after_lines: list[str]) -> dict[str, Any]:
    before = [f"{line}\n" for line in before_lines]
    after = [f"{line}\n" for line in after_lines]
    unified = [
        line.rstrip("\n")
        for line in difflib.unified_diff(
            before,
            after,
            fromfile=f"{event_path}:before",
            tofile=f"{event_path}:after",
            lineterm="",
        )
    ]
    return {
        "changed": before_lines != after_lines,
        "before_line_count": len(before_lines),
        "after_line_count": len(after_lines),
        "before_lines": list(before_lines),
        "after_lines": list(after_lines),
        "unified": unified,
    }


def _simulate_event_command_patch(
    before_scene: SceneModel,
    after_scene: SceneModel,
    event_path: str,
    *,
    source_path: Path,
    out_dir: str | Path | None,
    max_steps: int,
) -> dict[str, Any]:
    from .event_simulator import simulate_scene_event_model

    before_out = Path(out_dir).resolve() / "simulation_before" if out_dir is not None else None
    after_out = Path(out_dir).resolve() / "simulation_after" if out_dir is not None else None
    return {
        "before": simulate_scene_event_model(
            before_scene,
            event_path,
            source_path=source_path,
            out_dir=before_out,
            max_steps=max_steps,
        ),
        "after": simulate_scene_event_model(
            after_scene,
            event_path,
            source_path=source_path,
            out_dir=after_out,
            max_steps=max_steps,
        ),
    }


def _write_event_command_patch_outputs(result: Mapping[str, Any], out_dir: str | Path) -> dict[str, str]:
    output_dir = Path(out_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    patch_path = output_dir / "event_patch.json"
    diff_path = output_dir / "event_diff.json"
    patch_payload = {
        key: value
        for key, value in result.items()
        if key not in {"outputs", "simulation"}
    }
    if "simulation" in result:
        patch_payload["simulation_summary"] = {
            "before": result["simulation"]["before"].get("summary"),
            "after": result["simulation"]["after"].get("summary"),
        }
    _write_json_file(patch_path, patch_payload)
    _write_json_file(diff_path, result["diff"])
    return {
        "event_patch_json": str(patch_path),
        "event_diff_json": str(diff_path),
    }


def _write_json_file(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _clean_widget_document(widget: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {"id", "type", "text", "value", "x", "y", "w", "h", "style", "resources", "bindings", "events", "layout", "children"}
    result = {key: deepcopy(value) for key, value in widget.items() if key in allowed and value is not None}
    for key in ("style", "resources", "bindings", "events", "layout"):
        if key in result and not isinstance(result[key], dict):
            raise SceneError(f"widget {key} must be an object")
    if "children" in result and not isinstance(result["children"], list):
        raise SceneError("widget children must be a list")
    return result


def _clean_asset_document(asset: Mapping[str, Any], *, default_id: str) -> dict[str, Any]:
    allowed = {"id", "source", "normal", "pressed", "disabled"}
    result = {
        key: deepcopy(value)
        for key, value in asset.items()
        if key in allowed and value is not None and value != ""
    }
    result.setdefault("id", default_id)
    for key in allowed:
        if key in result and not isinstance(result[key], str):
            result[key] = str(result[key])
    if not result.get("source") and not result.get("normal"):
        raise SceneError("asset requires source or normal")
    return result


def _apply_asset_updates(asset: dict[str, Any], updates: Mapping[str, Any]) -> None:
    for key in ("id", "source", "normal", "pressed", "disabled"):
        if key not in updates:
            continue
        value = updates[key]
        if value is None or value == "":
            asset.pop(key, None)
        else:
            asset[key] = str(value)
    if not asset.get("source") and not asset.get("normal"):
        raise SceneError("asset requires source or normal")


def _apply_widget_updates(widget: dict[str, Any], updates: Mapping[str, Any]) -> None:
    for key in ("id", "type", "text", "value", "x", "y", "w", "h"):
        if key not in updates:
            continue
        value = updates[key]
        if value is None:
            widget.pop(key, None)
        else:
            widget[key] = value
    for key in ("style", "resources", "bindings", "events", "layout"):
        if key not in updates:
            continue
        value = updates[key]
        if value is None:
            widget.pop(key, None)
            continue
        if not isinstance(value, Mapping):
            raise SceneError(f"widget {key} update must be an object")
        widget[key] = dict(value)


def _widget_result(widget: WidgetSpec) -> dict[str, Any]:
    return {
        "id": widget.id,
        "type": widget.type,
        "text": widget.text,
        "value": widget.value,
        "x": widget.x,
        "y": widget.y,
        "w": widget.w,
        "h": widget.h,
        "style": dict(widget.style),
        "resources": dict(widget.resources),
        "bindings": dict(widget.bindings),
        "events": {name: list(lines) for name, lines in widget.events.items()},
    }


def _asset_result(key: str, asset: AssetSpec) -> dict[str, Any]:
    return {
        "key": key,
        "id": asset.id,
        "source": asset.source,
        "normal": asset.normal,
        "pressed": asset.pressed,
        "disabled": asset.disabled,
    }


def _scene_document_result(path: Path, scene: SceneModel) -> dict[str, Any]:
    return {
        "scene_path": str(path.resolve()),
        "project": dict(scene.project),
        "canvas": dict(scene.canvas),
        "page_count": len(scene.pages),
        "asset_count": len(scene.assets),
        "widget_count": sum(len(page.widgets) for page in scene.pages),
    }


def _page_result(page: PageSpec) -> dict[str, Any]:
    return {
        "id": page.id,
        "layout": dict(page.layout),
        "events": {name: list(lines) for name, lines in page.events.items()},
        "widget_count": len(page.widgets),
        "widgets": [_widget_result(widget) for widget in page.widgets],
    }


def _scene_pages(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    pages = payload.get("pages")
    if not isinstance(pages, list):
        raise SceneError("pages must be a list")
    return pages


def _scene_assets(payload: Mapping[str, Any]) -> dict[str, Any]:
    assets = payload.setdefault("assets", {})
    if not isinstance(assets, dict):
        raise SceneError("assets must be an object map")
    return assets


def _find_page(payload: Mapping[str, Any], page_id: str) -> dict[str, Any]:
    page, _index = _find_page_with_index(payload, page_id)
    return page


def _find_page_with_index(payload: Mapping[str, Any], page_id: str) -> tuple[dict[str, Any], int]:
    for index, page in enumerate(_scene_pages(payload)):
        if isinstance(page, dict) and page.get("id") == page_id:
            return page, index
    raise SceneError(f"Page '{page_id}' not found in scene")


def _assert_page_exists(payload: Mapping[str, Any], page_id: str) -> None:
    _find_page_with_index(payload, page_id)


def _assert_project_default_page_exists(scene: SceneModel) -> None:
    default_page = scene.project.get("default_page")
    if default_page is None:
        return
    if not isinstance(default_page, str) or not default_page:
        raise SceneError("project.default_page must be a non-empty string when provided")
    page_ids = {page.id for page in scene.pages}
    if default_page not in page_ids:
        raise SceneError(f"project.default_page '{default_page}' does not match any scene page")


def _positive_int(value: int, label: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise SceneError(f"{label} must be a positive integer")
    return parsed


def _page_widgets(page: Mapping[str, Any]) -> list[dict[str, Any]]:
    widgets = page.get("widgets")
    if not isinstance(widgets, list):
        raise SceneError(f"page '{page.get('id')}' widgets must be a list")
    return widgets


def _find_widget(
    page: Mapping[str, Any],
    *,
    widget_id: str | None,
    widget_index: int | None,
) -> tuple[dict[str, Any], int]:
    widgets = _page_widgets(page)
    if widget_index is not None:
        if widget_index < 0 or widget_index >= len(widgets):
            raise SceneError(f"Widget index {widget_index} is out of range on page '{page.get('id')}'")
        widget = widgets[widget_index]
        if not isinstance(widget, dict):
            raise SceneError(f"Widget index {widget_index} on page '{page.get('id')}' is not an object")
        if widget_id is not None and widget.get("id") != widget_id:
            raise SceneError(
                f"Widget index {widget_index} is {widget.get('id')!r}, not requested widget {widget_id!r}"
            )
        return widget, widget_index
    matches = [(index, widget) for index, widget in enumerate(widgets) if isinstance(widget, dict) and widget.get("id") == widget_id]
    if not matches:
        raise SceneError(f"Widget '{widget_id}' not found on page '{page.get('id')}'")
    if len(matches) > 1:
        raise SceneError(f"Widget '{widget_id}' is duplicated on page '{page.get('id')}'; use widget_index")
    return matches[0][1], matches[0][0]


def _assert_unique_widget_id(page: Mapping[str, Any], widget_id: str, *, allowed_index: int | None) -> None:
    for index, widget in enumerate(_page_widgets(page)):
        if allowed_index is not None and index == allowed_index:
            continue
        if isinstance(widget, dict) and widget.get("id") == widget_id:
            raise SceneError(f"Widget '{widget_id}' already exists on page '{page.get('id')}'")


def _next_widget_id(page: Mapping[str, Any], base_id: str) -> str:
    existing = {str(widget.get("id")) for widget in _page_widgets(page) if isinstance(widget, dict)}
    if f"{base_id}_copy" not in existing:
        return f"{base_id}_copy"
    index = 2
    while f"{base_id}_copy{index}" in existing:
        index += 1
    return f"{base_id}_copy{index}"


def _assert_unique_page_id(payload: Mapping[str, Any], page_id: str) -> None:
    for page in _scene_pages(payload):
        if isinstance(page, dict) and page.get("id") == page_id:
            raise SceneError(f"Page '{page_id}' already exists in scene")


def _next_page_id(payload: Mapping[str, Any], base_id: str) -> str:
    existing = {str(page.get("id")) for page in _scene_pages(payload) if isinstance(page, dict)}
    if f"{base_id}_copy" not in existing:
        return f"{base_id}_copy"
    index = 2
    while f"{base_id}_copy{index}" in existing:
        index += 1
    return f"{base_id}_copy{index}"


def _collect_page_rename_warnings(payload: Mapping[str, Any], old_page_id: str, new_page_id: str) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for page in _scene_pages(payload):
        if not isinstance(page, dict):
            continue
        page_id = str(page.get("id") or "")
        _collect_event_page_references(
            page.get("events") or {},
            old_page_id,
            new_page_id,
            owner=f"{page_id}.<page>",
            warnings=warnings,
        )
        for widget in page.get("widgets") or []:
            if not isinstance(widget, dict):
                continue
            widget_id = str(widget.get("id") or "")
            _collect_event_page_references(
                widget.get("events") or {},
                old_page_id,
                new_page_id,
                owner=f"{page_id}.{widget_id}",
                warnings=warnings,
            )
    return warnings


def _collect_event_page_references(
    events: Any,
    old_page_id: str,
    new_page_id: str,
    *,
    owner: str,
    warnings: list[dict[str, Any]],
) -> None:
    if not isinstance(events, Mapping):
        return
    for event_name, raw_lines in events.items():
        try:
            lines = normalize_event_lines(str(event_name), raw_lines)
        except SceneError:
            continue
        for line_index, line in enumerate(lines):
            if old_page_id not in line:
                continue
            warnings.append(
                {
                    "code": "PAGE_RENAME_EVENT_REFERENCE_NOT_REWRITTEN",
                    "owner": owner,
                    "event": str(event_name),
                    "line_index": line_index,
                    "old_page": old_page_id,
                    "new_page": new_page_id,
                    "line": line,
                    "message": "Page rename does not rewrite event script text references.",
                }
            )


def _collect_widget_rename_warnings(payload: Mapping[str, Any], page_id: str, old_widget_id: str, new_widget_id: str) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    page = _find_page(payload, page_id)
    _collect_event_widget_references(
        page.get("events") or {},
        old_widget_id,
        new_widget_id,
        owner=f"{page_id}.<page>",
        warnings=warnings,
    )
    for widget in page.get("widgets") or []:
        if not isinstance(widget, dict):
            continue
        widget_id = str(widget.get("id") or "")
        _collect_event_widget_references(
            widget.get("events") or {},
            old_widget_id,
            new_widget_id,
            owner=f"{page_id}.{widget_id}",
            warnings=warnings,
        )
    return warnings


def _rewrite_widget_event_references(payload: Mapping[str, Any], page_id: str, old_widget_id: str, new_widget_id: str) -> list[dict[str, Any]]:
    rewritten: list[dict[str, Any]] = []
    page = _find_page(payload, page_id)
    _rewrite_event_widget_references(
        page.get("events") or {},
        old_widget_id,
        new_widget_id,
        owner=f"{page_id}.<page>",
        rewritten=rewritten,
    )
    for widget in page.get("widgets") or []:
        if not isinstance(widget, dict):
            continue
        widget_id = str(widget.get("id") or "")
        _rewrite_event_widget_references(
            widget.get("events") or {},
            old_widget_id,
            new_widget_id,
            owner=f"{page_id}.{widget_id}",
            rewritten=rewritten,
        )
    return rewritten


def _rewrite_event_widget_references(
    events: Any,
    old_widget_id: str,
    new_widget_id: str,
    *,
    owner: str,
    rewritten: list[dict[str, Any]],
) -> None:
    if not isinstance(events, dict):
        return
    for event_name, raw_lines in list(events.items()):
        try:
            lines = normalize_event_lines(str(event_name), raw_lines)
        except SceneError:
            continue
        changed = False
        rewritten_lines: list[str] = []
        for line_index, line in enumerate(lines):
            new_line = _replace_identifier_reference(line, old_widget_id, new_widget_id)
            rewritten_lines.append(new_line)
            if new_line != line:
                changed = True
                rewritten.append(
                    {
                        "owner": owner,
                        "event": str(event_name),
                        "line_index": line_index,
                        "old_widget": old_widget_id,
                        "new_widget": new_widget_id,
                        "old_line": line,
                        "new_line": new_line,
                    }
                )
        if changed:
            events[str(event_name)] = rewritten_lines


def _collect_event_widget_references(
    events: Any,
    old_widget_id: str,
    new_widget_id: str,
    *,
    owner: str,
    warnings: list[dict[str, Any]],
) -> None:
    if not isinstance(events, Mapping):
        return
    for event_name, raw_lines in events.items():
        try:
            lines = normalize_event_lines(str(event_name), raw_lines)
        except SceneError:
            continue
        for line_index, line in enumerate(lines):
            if not _line_has_identifier_reference(line, old_widget_id):
                continue
            warnings.append(
                {
                    "code": "WIDGET_RENAME_EVENT_REFERENCE_NOT_REWRITTEN",
                    "owner": owner,
                    "event": str(event_name),
                    "line_index": line_index,
                    "old_widget": old_widget_id,
                    "new_widget": new_widget_id,
                    "line": line,
                    "message": "Widget rename does not rewrite event script text references.",
                }
            )


def _line_has_identifier_reference(line: str, identifier: str) -> bool:
    return _identifier_reference_pattern(identifier).search(line) is not None


def _replace_identifier_reference(line: str, old_identifier: str, new_identifier: str) -> str:
    return _identifier_reference_pattern(old_identifier).sub(new_identifier, line)


def _identifier_reference_pattern(identifier: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(identifier)}(?![A-Za-z0-9_])")


def _find_asset_references(payload: Mapping[str, Any], asset_id: str) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    for page in _scene_pages(payload):
        if not isinstance(page, dict):
            continue
        _collect_asset_references(page.get("widgets", []), asset_id, str(page.get("id") or ""), references)
    return references


def _collect_asset_references(
    widgets: Any,
    asset_id: str,
    page_id: str,
    references: list[dict[str, Any]],
) -> None:
    if not isinstance(widgets, list):
        return
    for widget in widgets:
        if not isinstance(widget, dict):
            continue
        widget_id = str(widget.get("id") or "")
        resources = widget.get("resources") or {}
        if isinstance(resources, dict):
            for key, value in resources.items():
                if value == asset_id:
                    references.append({"page": page_id, "widget": widget_id, "resource": key})
        _collect_asset_references(widget.get("children", []), asset_id, page_id, references)
