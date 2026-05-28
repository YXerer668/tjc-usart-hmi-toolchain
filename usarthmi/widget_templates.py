from __future__ import annotations

from copy import deepcopy
from typing import Any

from .widgets import get_widget_type_info, normalize_widget_type


DEFAULT_WIDGET_TEMPLATE_VERSION = 1


_TEMPLATE_DEFAULTS: dict[str, dict[str, Any]] = {
    "animation": {"w": 162, "h": 102, "resources": {"path": "sd0/anim/0.gmov"}, "style": {"en": 1, "loop": 1}},
    "audio": {"w": 1, "h": 1, "resources": {"path": "sd0/music/0.wav"}, "style": {"en": 0}},
    "button": {"w": 160, "h": 56, "text": "Button", "style": {"background_color": 21130, "foreground_color": 65535, "border_color": 0}},
    "checkbox": {"w": 160, "h": 40, "text": "Check", "value": 0},
    "combobox": {"w": 180, "h": 44, "text": "Item 1", "value": 0, "style": {"qty": 3}},
    "crop-image": {"w": 160, "h": 120, "resources": {"asset": ""}},
    "data-record": {"w": 300, "h": 160, "style": {"rows": 4}},
    "dual-button": {"w": 160, "h": 56, "text": "Dual", "value": 0},
    "dualstate-button": {"w": 160, "h": 56, "text": "Dual", "value": 0},
    "external-picture": {"w": 180, "h": 120, "resources": {"path": "sd0/1.jpg"}, "style": {"path_m": 24}},
    "file-browser": {"w": 300, "h": 220, "resources": {"path": "sd0/"}, "style": {"show_dirs": 1}},
    "file-stream": {"w": 1, "h": 1, "resources": {"path": "sd0/data.bin"}},
    "gauge": {"w": 120, "h": 120, "value": 45},
    "hotspot": {"w": 180, "h": 120, "style": {"transparent": 1}},
    "image": {"w": 160, "h": 120, "resources": {"asset": ""}},
    "number": {"w": 120, "h": 44, "value": 0, "style": {"background_color": 65535, "foreground_color": 0}},
    "progress": {"w": 220, "h": 30, "value": 50, "style": {"background_color": 50712, "foreground_color": 2016}},
    "qrcode": {"w": 160, "h": 160, "text": "https://example.com"},
    "radio": {"w": 160, "h": 40, "text": "Option", "value": 0},
    "scrolling-text": {"w": 260, "h": 40, "text": "Scrolling text", "style": {"sta": 1}},
    "slider": {"w": 220, "h": 36, "value": 50},
    "sliding-text": {"w": 260, "h": 48, "text": "Sliding text"},
    "state-button": {"w": 160, "h": 56, "text": "Switch", "value": 0},
    "text": {"w": 220, "h": 40, "text": "Text", "style": {"background_color": 65535, "foreground_color": 0}},
    "text-select": {"w": 220, "h": 48, "text": "Select", "value": 0},
    "timer": {"w": 1, "h": 1, "style": {"en": 0, "tim": 1000}},
    "touch-capture": {"w": 220, "h": 160, "style": {"capture": 1}},
    "variable": {"w": 1, "h": 1, "value": 0},
    "video": {"w": 220, "h": 140, "resources": {"path": "sd0/video/0.video"}, "style": {"en": 0}},
    "waveform": {"w": 300, "h": 140, "style": {"grid": 1}},
    "xfloat": {"w": 140, "h": 44, "value": 0, "style": {"vvs0": 2, "vvs1": 2}},
}


def get_widget_template(
    widget_type: str,
    *,
    widget_id: str | None = None,
    x: int = 40,
    y: int = 40,
) -> dict[str, Any]:
    normalized = normalize_widget_type(widget_type)
    info = get_widget_type_info(normalized)
    defaults = deepcopy(_TEMPLATE_DEFAULTS.get(normalized, {"w": 160, "h": 48, "text": normalized}))
    template: dict[str, Any] = {
        "id": widget_id or _default_widget_id(normalized),
        "type": normalized,
        "x": int(x),
        "y": int(y),
        "w": int(defaults.pop("w", 160)),
        "h": int(defaults.pop("h", 48)),
        "text": defaults.pop("text", None),
        "value": defaults.pop("value", None),
        "style": defaults.pop("style", {}),
        "resources": defaults.pop("resources", {}),
        "bindings": defaults.pop("bindings", {}),
        "events": defaults.pop("events", {}),
        "children": [],
        "layout": {},
    }
    template.update(defaults)
    return {
        "schema_version": DEFAULT_WIDGET_TEMPLATE_VERSION,
        "widget": template,
        "capability": info.to_dict(include_aliases=True) if info is not None else {"type": normalized, "support": "unknown", "writer": "none"},
        "not_claimed": [
            "template defaults are authoring hints, not official property equivalence",
            "resource paths may need editing before build or live use",
            "pending widgets remain HMI-only unless their capability says otherwise",
        ],
    }


def list_widget_templates() -> dict[str, Any]:
    return {
        "schema_version": DEFAULT_WIDGET_TEMPLATE_VERSION,
        "templates": [
            get_widget_template(widget_type)["widget"]
            for widget_type in sorted(_TEMPLATE_DEFAULTS)
        ],
    }


def _default_widget_id(widget_type: str) -> str:
    compact = "".join(ch for ch in widget_type if ch.isalnum())
    if not compact:
        compact = "widget"
    return f"{compact}0"
