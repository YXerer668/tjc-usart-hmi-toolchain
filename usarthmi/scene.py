from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

import yaml

from .widgets import (
    HMI_ONLY_FIXTURE_WIDGET_TYPES,
    SUPPORTED_WIDGET_TYPES,
    UNSUPPORTED_CURRENT_TARGET_WIDGET_TYPES,
    WIDGET_TYPE_ALIASES,
    normalize_widget_type as _normalize_widget_type,
)


class SceneError(ValueError):
    """Raised when a scene file is invalid."""


SUPPORTED_WIDGET_TYPE_ALIASES = dict(WIDGET_TYPE_ALIASES)
LIVE_SMOKE_SCHEMA_VERSION = 1
LIVE_SMOKE_ALLOWED_KEYS = {
    "version",
    "auto",
    "auto_expectations",
    "auto_steps",
    "page_id",
    "select_page",
    "restore_page",
    "expectations",
    "set_expectations",
    "steps",
    "generation_warnings",
}
LIVE_SMOKE_EXPECTATION_ALLOWED_KEYS = {"target", "name", "expected", "expected_kind", "attempts"}
LIVE_SMOKE_STEP_ALLOWED_KEYS = {
    "label",
    "command",
    "expected_kind",
    "expected",
    "expected_value",
    "expected_min",
    "expected_max",
    "expected_hex",
    "expected_ascii_preview",
    "delay_ms",
    "attempts",
}


def normalize_widget_type(widget_type: Any) -> str:
    try:
        return _normalize_widget_type(widget_type)
    except ValueError as exc:
        raise SceneError(str(exc)) from exc


@dataclass(slots=True)
class AssetSpec:
    id: str
    source: str | None = None
    normal: str | None = None
    pressed: str | None = None
    disabled: str | None = None


@dataclass(slots=True)
class WidgetSpec:
    id: str
    type: str
    text: str | None = None
    value: int | None = None
    x: int | None = None
    y: int | None = None
    w: int | None = None
    h: int | None = None
    style: dict[str, Any] = field(default_factory=dict)
    resources: dict[str, Any] = field(default_factory=dict)
    bindings: dict[str, Any] = field(default_factory=dict)
    events: dict[str, list[str]] = field(default_factory=dict)
    children: list["WidgetSpec"] = field(default_factory=list)
    layout: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PageSpec:
    id: str
    layout: dict[str, Any]
    widgets: list[WidgetSpec]
    events: dict[str, list[str]] = field(default_factory=dict)


@dataclass(slots=True)
class SceneModel:
    project: dict[str, Any]
    canvas: dict[str, Any]
    assets: dict[str, AssetSpec]
    pages: list[PageSpec]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "canvas": self.canvas,
            "assets": {
                key: {
                    "id": asset.id,
                    "source": asset.source,
                    "normal": asset.normal,
                    "pressed": asset.pressed,
                    "disabled": asset.disabled,
                }
                for key, asset in self.assets.items()
            },
            "pages": [page_to_dict(page) for page in self.pages],
        }


def page_to_dict(page: PageSpec) -> dict[str, Any]:
    return {
        "id": page.id,
        "layout": page.layout,
        "events": page.events,
        "widgets": [widget_to_dict(widget) for widget in page.widgets],
    }


def widget_to_dict(widget: WidgetSpec) -> dict[str, Any]:
    return {
        "id": widget.id,
        "type": widget.type,
        "text": widget.text,
        "value": widget.value,
        "x": widget.x,
        "y": widget.y,
        "w": widget.w,
        "h": widget.h,
        "style": widget.style,
        "resources": widget.resources,
        "bindings": widget.bindings,
        "events": widget.events,
        "layout": widget.layout,
        "children": [widget_to_dict(child) for child in widget.children],
    }


def load_scene(path: str | Path) -> SceneModel:
    file_path = Path(path).resolve()
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    suffix = file_path.suffix.lower()
    raw_text = file_path.read_text(encoding="utf-8")
    if suffix in {".yaml", ".yml"}:
        payload = yaml.safe_load(raw_text)
    else:
        payload = json.loads(raw_text)

    scene = validate_scene(payload)
    scene.project.setdefault("_source_dir", str(file_path.parent))
    for asset in scene.assets.values():
        for attr_name in ("source", "normal", "pressed", "disabled"):
            value = getattr(asset, attr_name)
            if not value:
                continue
            asset_path = Path(value)
            if not asset_path.is_absolute():
                setattr(asset, attr_name, str((file_path.parent / asset_path).resolve()))
    return scene


def save_scene_json(scene: SceneModel, path: str | Path) -> Path:
    file_path = Path(path).resolve()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(scene.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return file_path


def validate_scene(payload: dict[str, Any]) -> SceneModel:
    if not isinstance(payload, dict):
        raise SceneError("Scene root must be an object")

    project = payload.get("project")
    canvas = payload.get("canvas")
    pages = payload.get("pages")
    assets = payload.get("assets", {})

    if not isinstance(project, dict):
        raise SceneError("project must be an object")
    if not isinstance(canvas, dict):
        raise SceneError("canvas must be an object")
    if not isinstance(pages, list) or not pages:
        raise SceneError("pages must be a non-empty list")
    if not isinstance(assets, dict):
        raise SceneError("assets must be an object map")

    project = _validate_project(project)

    width = int(canvas.get("width", 0))
    height = int(canvas.get("height", 0))
    if width <= 0 or height <= 0:
        raise SceneError("canvas.width and canvas.height must be positive integers")

    asset_specs: dict[str, AssetSpec] = {}
    for key, asset in assets.items():
        if not isinstance(asset, dict):
            raise SceneError(f"asset '{key}' must be an object")
        source = asset.get("source")
        normal = asset.get("normal")
        pressed = asset.get("pressed")
        disabled = asset.get("disabled")
        if source is not None and (not isinstance(source, str) or not source):
            raise SceneError(f"asset '{key}' source must be a non-empty string when provided")
        for attr_name, value in (("normal", normal), ("pressed", pressed), ("disabled", disabled)):
            if value is not None and (not isinstance(value, str) or not value):
                raise SceneError(f"asset '{key}' {attr_name} must be a non-empty string when provided")
        if not source and not normal:
            raise SceneError(f"asset '{key}' requires source or normal")
        asset_specs[key] = AssetSpec(
            id=str(asset.get("id") or key),
            source=source,
            normal=normal,
            pressed=pressed,
            disabled=disabled,
        )

    page_specs = [_validate_page(page) for page in pages]

    return SceneModel(
        project=project,
        canvas={**canvas, "width": width, "height": height},
        assets=asset_specs,
        pages=page_specs,
    )


def _validate_project(project: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(project)
    normalized["live_smoke"] = _validate_live_smoke(project.get("live_smoke"))
    if normalized["live_smoke"] is None:
        normalized.pop("live_smoke", None)
    return normalized


def _validate_live_smoke(payload: Any) -> dict[str, Any] | None:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise SceneError("project.live_smoke must be an object")
    unknown_keys = sorted(set(payload) - LIVE_SMOKE_ALLOWED_KEYS)
    if unknown_keys:
        raise SceneError(f"project.live_smoke has unsupported keys: {', '.join(unknown_keys)}")
    normalized: dict[str, Any] = {}
    version = payload.get("version", LIVE_SMOKE_SCHEMA_VERSION)
    if not isinstance(version, int) or version != LIVE_SMOKE_SCHEMA_VERSION:
        raise SceneError(f"project.live_smoke.version must be {LIVE_SMOKE_SCHEMA_VERSION}")
    normalized["version"] = version
    for key in ("auto", "auto_expectations", "auto_steps"):
        if key in payload:
            value = payload[key]
            if not isinstance(value, bool):
                raise SceneError(f"project.live_smoke.{key} must be a boolean")
            normalized[key] = value
    if "page_id" in payload:
        normalized["page_id"] = _validate_live_smoke_int(payload["page_id"], "project.live_smoke.page_id", minimum=0)
    for key in ("select_page", "restore_page"):
        if key in payload:
            normalized[key] = _validate_live_smoke_page_selector(payload[key], f"project.live_smoke.{key}")
    if "expectations" in payload:
        normalized["expectations"] = _validate_live_smoke_expectations(payload["expectations"], "project.live_smoke.expectations")
    if "set_expectations" in payload:
        normalized["set_expectations"] = _validate_live_smoke_expectations(
            payload["set_expectations"],
            "project.live_smoke.set_expectations",
        )
    if "steps" in payload:
        normalized["steps"] = _validate_live_smoke_steps(payload["steps"], "project.live_smoke.steps")
    if "generation_warnings" in payload:
        normalized["generation_warnings"] = _validate_live_smoke_string_list(
            payload["generation_warnings"],
            "project.live_smoke.generation_warnings",
        )
    return normalized


def _validate_live_smoke_page_selector(value: Any, context: str) -> str | int:
    if isinstance(value, bool):
        raise SceneError(f"{context} must be an integer or non-empty string")
    if isinstance(value, int):
        if value < 0:
            raise SceneError(f"{context} must be >= 0")
        return value
    if isinstance(value, str) and value.strip():
        return value
    raise SceneError(f"{context} must be an integer or non-empty string")


def _validate_live_smoke_expectations(payload: Any, context: str) -> dict[str, Any] | list[dict[str, Any]]:
    if isinstance(payload, dict):
        normalized: dict[str, Any] = {}
        for key, value in payload.items():
            if not isinstance(key, str) or not key.strip():
                raise SceneError(f"{context} keys must be non-empty strings")
            normalized[key] = value
        return normalized
    if not isinstance(payload, list):
        raise SceneError(f"{context} must be an object map or list")
    normalized_list: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise SceneError(f"{context}[{index}] must be an object")
        unknown_keys = sorted(set(item) - LIVE_SMOKE_EXPECTATION_ALLOWED_KEYS)
        if unknown_keys:
            raise SceneError(f"{context}[{index}] has unsupported keys: {', '.join(unknown_keys)}")
        target = item.get("target", item.get("name"))
        if not isinstance(target, str) or not target.strip():
            raise SceneError(f"{context}[{index}] requires non-empty target")
        normalized = dict(item)
        normalized["target"] = target
        attempts = item.get("attempts", 3)
        normalized["attempts"] = _validate_live_smoke_int(attempts, f"{context}[{index}].attempts", minimum=1)
        expected_kind = item.get("expected_kind")
        if expected_kind is not None and (not isinstance(expected_kind, str) or not expected_kind.strip()):
            raise SceneError(f"{context}[{index}].expected_kind must be a non-empty string when provided")
        normalized_list.append(normalized)
    return normalized_list


def _validate_live_smoke_steps(payload: Any, context: str) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise SceneError(f"{context} must be a list")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise SceneError(f"{context}[{index}] must be an object")
        unknown_keys = sorted(set(item) - LIVE_SMOKE_STEP_ALLOWED_KEYS)
        if unknown_keys:
            raise SceneError(f"{context}[{index}] has unsupported keys: {', '.join(unknown_keys)}")
        command = item.get("command")
        if not isinstance(command, str) or not command.strip():
            raise SceneError(f"{context}[{index}].command must be a non-empty string")
        label = item.get("label")
        if label is not None and (not isinstance(label, str) or not label.strip()):
            raise SceneError(f"{context}[{index}].label must be a non-empty string when provided")
        expected_kind = item.get("expected_kind")
        if expected_kind is not None and (not isinstance(expected_kind, str) or not expected_kind.strip()):
            raise SceneError(f"{context}[{index}].expected_kind must be a non-empty string when provided")
        normalized_item = dict(item)
        normalized_item["attempts"] = _validate_live_smoke_int(
            item.get("attempts", 3),
            f"{context}[{index}].attempts",
            minimum=1,
        )
        if "delay_ms" in item:
            normalized_item["delay_ms"] = _validate_live_smoke_int(
                item["delay_ms"],
                f"{context}[{index}].delay_ms",
                minimum=0,
            )
        normalized.append(normalized_item)
    return normalized


def _validate_live_smoke_string_list(payload: Any, context: str) -> list[str]:
    if not isinstance(payload, list):
        raise SceneError(f"{context} must be a list of strings")
    normalized: list[str] = []
    for index, item in enumerate(payload):
        if not isinstance(item, str) or not item.strip():
            raise SceneError(f"{context}[{index}] must be a non-empty string")
        normalized.append(item)
    return normalized


def _validate_live_smoke_int(value: Any, context: str, *, minimum: int) -> int:
    if isinstance(value, bool):
        raise SceneError(f"{context} must be an integer >= {minimum}")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise SceneError(f"{context} must be an integer >= {minimum}") from exc
    if parsed < minimum:
        raise SceneError(f"{context} must be >= {minimum}")
    return parsed


def _validate_page(payload: dict[str, Any]) -> PageSpec:
    if not isinstance(payload, dict):
        raise SceneError("Each page must be an object")
    page_id = payload.get("id")
    if not isinstance(page_id, str) or not page_id:
        raise SceneError("page.id must be a non-empty string")
    layout = payload.get("layout") or {"type": "absolute"}
    widgets = payload.get("widgets", [])
    events = _validate_events(payload.get("events") or {}, f"page '{page_id}'")
    if not isinstance(layout, dict):
        raise SceneError(f"page '{page_id}' layout must be an object")
    if not isinstance(widgets, list):
        raise SceneError(f"page '{page_id}' widgets must be a list")
    return PageSpec(
        id=page_id,
        layout=layout,
        widgets=[_validate_widget(item) for item in widgets],
        events=events,
    )


def _validate_widget(payload: dict[str, Any]) -> WidgetSpec:
    if not isinstance(payload, dict):
        raise SceneError("widget must be an object")

    widget_id = payload.get("id")
    widget_type = normalize_widget_type(payload.get("type"))
    if not isinstance(widget_id, str) or not widget_id:
        raise SceneError("widget.id must be a non-empty string")
    if widget_type in UNSUPPORTED_CURRENT_TARGET_WIDGET_TYPES:
        reason = UNSUPPORTED_CURRENT_TARGET_WIDGET_TYPES[widget_type]
        raise SceneError(f"widget '{widget_id}' has unsupported type '{widget_type}' for the current target: {reason}")
    if widget_type not in SUPPORTED_WIDGET_TYPES and widget_type not in HMI_ONLY_FIXTURE_WIDGET_TYPES:
        raise SceneError(f"widget '{widget_id}' has unsupported type '{widget_type}'")

    for key in ("x", "y", "w", "h"):
        if key in payload and payload[key] is not None:
            payload[key] = int(payload[key])

    children = payload.get("children", [])
    if not isinstance(children, list):
        raise SceneError(f"widget '{widget_id}' children must be a list")

    style = payload.get("style") or {}
    resources = payload.get("resources") or {}
    bindings = payload.get("bindings") or {}
    events = _validate_events(payload.get("events") or {}, f"widget '{widget_id}'")
    layout = payload.get("layout") or {}
    if not isinstance(style, dict):
        raise SceneError(f"widget '{widget_id}' style must be an object")
    if not isinstance(resources, dict):
        raise SceneError(f"widget '{widget_id}' resources must be an object")
    if not isinstance(bindings, dict):
        raise SceneError(f"widget '{widget_id}' bindings must be an object")
    if not isinstance(layout, dict):
        raise SceneError(f"widget '{widget_id}' layout must be an object")

    return WidgetSpec(
        id=widget_id,
        type=widget_type,
        text=payload.get("text"),
        value=int(payload["value"]) if payload.get("value") is not None else None,
        x=payload.get("x"),
        y=payload.get("y"),
        w=payload.get("w"),
        h=payload.get("h"),
        style=style,
        resources=resources,
        bindings=bindings,
        events=events,
        layout=layout,
        children=[_validate_widget(item) for item in children],
    )


def _validate_events(payload: Any, owner: str) -> dict[str, list[str]]:
    if not isinstance(payload, dict):
        raise SceneError(f"{owner} events must be an object")
    normalized: dict[str, list[str]] = {}
    for event_name, lines in payload.items():
        if event_name not in {"load", "loadend", "down", "up", "unload", "timer", "slide"}:
            raise SceneError(
                f"{owner} event '{event_name}' is unsupported; use load/loadend/down/up/unload/timer/slide"
            )
        if isinstance(lines, str):
            normalized[str(event_name)] = [lines]
            continue
        if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines):
            raise SceneError(f"{owner} event '{event_name}' must be a string or list of strings")
        normalized[str(event_name)] = list(lines)
    return normalized
