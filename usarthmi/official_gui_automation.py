from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any


AUTOMATION_SCHEMA_VERSION = 1
DEFAULT_OFFICIAL_EXE = Path(r"C:\Program Files (x86)\USART HMI\USART HMI.exe")
DEFAULT_DECOMPILED_APPOBJSCLASS = Path(
    r"D:\reverse\USART HMI_decompile\decompiled\ACTR\hmitype\hmitype\appobjsclass.cs"
)
DEFAULT_DECOMPILED_HMITYPE_DIR = DEFAULT_DECOMPILED_APPOBJSCLASS.parent
DEFAULT_DECOMPILED_MAINCS = Path(
    r"D:\reverse\USART HMI_decompile\decompiled\ACTR\HMIFORM\HMIFORM\main.cs"
)
DEFAULT_PAGE_LIST_X = 3600
DEFAULT_PAGE_ROW_Y = {0: 285, 1: 247}
DEFAULT_TOOLBOX_X = 87
DEFAULT_CANVAS_X = 712
DEFAULT_CANVAS_Y = 432
DEFAULT_PAGE1_PANEL_SPLITTER_X = 170
DEFAULT_PAGE1_PANEL_SPLITTER_START_Y = 315
DEFAULT_PAGE1_PANEL_SPLITTER_END_Y = 520
DEFAULT_PAGE1_DRAG_SCROLL_START_Y = 238
DEFAULT_PAGE1_DRAG_SCROLL_END_Y = 640


@dataclass(frozen=True, slots=True)
class DecompiledObjmark:
    var_name: str
    display_name: str | None
    label: str | None
    object_id: int | None
    intname: str | None
    default_width: int | None
    default_height: int | None
    event_slots: int | None
    obj_get_atts_class: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "var_name": self.var_name,
            "display_name": self.display_name,
            "label": self.label,
            "object_id": self.object_id,
            "intname": self.intname,
            "default_width": self.default_width,
            "default_height": self.default_height,
            "event_slots": self.event_slots,
            "obj_get_atts_class": self.obj_get_atts_class,
        }


@dataclass(frozen=True, slots=True)
class GuiFieldCatalog:
    class_name: str
    source_path: str | None
    visible_fields: tuple[str, ...]
    all_fields: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "class_name": self.class_name,
            "source_path": self.source_path,
            "visible_fields": list(self.visible_fields),
            "all_fields": list(self.all_fields),
        }


@dataclass(frozen=True, slots=True)
class GuiCalibration:
    page0_tool_rel_y: int | None = None
    page1_tool_rel_y: int | None = None
    page1_toolbox_wheel: int = 0
    page1_panel_splitter_x: int | None = DEFAULT_PAGE1_PANEL_SPLITTER_X
    page1_panel_splitter_start_y: int | None = DEFAULT_PAGE1_PANEL_SPLITTER_START_Y
    page1_panel_splitter_end_y: int | None = DEFAULT_PAGE1_PANEL_SPLITTER_END_Y
    page1_drag_scroll_start_y: int | None = DEFAULT_PAGE1_DRAG_SCROLL_START_Y
    page1_drag_scroll_end_y: int | None = DEFAULT_PAGE1_DRAG_SCROLL_END_Y
    canvas_x: int = DEFAULT_CANVAS_X
    canvas_y: int = DEFAULT_CANVAS_Y

    def tool_rel_y_for_page(self, page_index: int) -> int | None:
        return self.page1_tool_rel_y if page_index == 1 else self.page0_tool_rel_y


@dataclass(frozen=True, slots=True)
class OfficialGuiControlSpec:
    key: str
    aliases: tuple[str, ...]
    decompiled_var_name: str
    expected_type_code: str | None
    calibration: GuiCalibration
    toolbox_index: int | None = None
    decompiled: DecompiledObjmark | None = None
    field_catalog: GuiFieldCatalog | None = None

    @property
    def canonical_names(self) -> tuple[str, ...]:
        names = [self.key, *self.aliases]
        if self.decompiled is not None:
            if self.decompiled.label:
                names.append(self.decompiled.label)
            if self.decompiled.intname:
                names.append(self.decompiled.intname)
            if self.decompiled.var_name:
                names.append(self.decompiled.var_name)
            if self.decompiled.display_name:
                names.append(self.decompiled.display_name)
        lowered: list[str] = []
        for item in names:
            text = str(item).strip().lower()
            if text and text not in lowered:
                lowered.append(text)
        return tuple(lowered)

    def default_expected_objname(self) -> str | None:
        if self.decompiled is None or not self.decompiled.intname:
            return None
        return f"{self.decompiled.intname}0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "aliases": list(self.aliases),
            "decompiled_var_name": self.decompiled_var_name,
            "expected_type_code": self.expected_type_code,
            "toolbox_index": self.toolbox_index,
            "calibration": {
                "page0_tool_rel_y": self.calibration.page0_tool_rel_y,
                "page1_tool_rel_y": self.calibration.page1_tool_rel_y,
                "page1_toolbox_wheel": self.calibration.page1_toolbox_wheel,
                "page1_panel_splitter_x": self.calibration.page1_panel_splitter_x,
                "page1_panel_splitter_start_y": self.calibration.page1_panel_splitter_start_y,
                "page1_panel_splitter_end_y": self.calibration.page1_panel_splitter_end_y,
                "page1_drag_scroll_start_y": self.calibration.page1_drag_scroll_start_y,
                "page1_drag_scroll_end_y": self.calibration.page1_drag_scroll_end_y,
                "canvas_x": self.calibration.canvas_x,
                "canvas_y": self.calibration.canvas_y,
            },
            "decompiled": None if self.decompiled is None else self.decompiled.to_dict(),
            "field_catalog": None if self.field_catalog is None else self.field_catalog.to_dict(),
        }


CONTROL_HINTS: dict[str, dict[str, Any]] = {
    "text": {
        "aliases": ("text",),
        "decompiled_var_name": "text",
        "expected_type_code": "t",
        "calibration": GuiCalibration(page0_tool_rel_y=225),
    },
    "button": {
        "aliases": ("button",),
        "decompiled_var_name": "button",
        "expected_type_code": "b",
        "calibration": GuiCalibration(page0_tool_rel_y=345),
    },
    "text-select": {
        "aliases": ("textselect", "select-text", "select text", "text select"),
        "decompiled_var_name": "textselect",
        "expected_type_code": "D",
        "calibration": GuiCalibration(page0_tool_rel_y=982, page1_tool_rel_y=806),
    },
    "sliding-text": {
        "aliases": ("sltext", "sliding text"),
        "decompiled_var_name": "sltext",
        "expected_type_code": ">",
        "calibration": GuiCalibration(page0_tool_rel_y=1019, page1_tool_rel_y=842),
    },
    "data-record": {
        "aliases": ("datarecord", "data record"),
        "decompiled_var_name": "datarecord",
        "expected_type_code": "B",
        "calibration": GuiCalibration(page0_tool_rel_y=1056, page1_tool_rel_y=878),
    },
    "file-browser": {
        "aliases": ("filebrowser", "file browser"),
        "decompiled_var_name": "filebrowser",
        "expected_type_code": "A",
        "calibration": GuiCalibration(page0_tool_rel_y=1094, page1_tool_rel_y=914),
    },
    "file-stream": {
        "aliases": ("filestream", "file stream"),
        "decompiled_var_name": "filestream",
        "expected_type_code": "?",
        "calibration": GuiCalibration(page0_tool_rel_y=1131, page1_tool_rel_y=950),
    },
}

AUTO_DISCOVERED_CONTROL_OVERRIDES: dict[str, dict[str, Any]] = {
    "gtext": {"key": "scrolling-text", "aliases": ("gtext", "scrolling text")},
    "button_t": {"key": "dual-state-button", "aliases": ("button_t", "dual state button", "button-t")},
    "expic": {"key": "external-picture", "aliases": ("expic", "external picture")},
    "OBJECT_TYPE_CURVE": {"key": "curve", "aliases": ("object_type_curve", "waveform")},
    "OBJECT_TYPE_SLIDER": {"key": "slider", "aliases": ("object_type_slider",)},
    "switchbutton": {"key": "switch-button", "aliases": ("switchbutton", "switch button")},
    "prog": {"key": "progress", "aliases": ("prog", "progress bar")},
    "pic": {"key": "image", "aliases": ("pic", "picture")},
    "picc": {"key": "crop-image", "aliases": ("picc", "crop picture", "cut image")},
    "touch": {"key": "hotspot", "aliases": ("touch", "touch hotspot")},
    "touchcap": {"key": "touch-capture", "aliases": ("touchcap", "touch capture")},
    "zhizhen": {"key": "gauge", "aliases": ("zhizhen", "pointer")},
}

AUTO_DISCOVERED_TYPE_CODE_OVERRIDES: dict[str, str] = {
    "combobox": "=",
    "switchbutton": "C",
    "prog": "j",
    "xfloat": ";",
    "number": "6",
    "gtext": "7",
    "touch": "m",
    "touchcap": "\x05",
    "zhizhen": "z",
    "button_t": "5",
    "qrcode": ":",
    "pic": "p",
    "picc": "q",
    "OBJECT_TYPE_SLIDER": "\x01",
    "OBJECT_TYPE_CURVE": "\x00",
    "checkbox": "8",
    "radiobutton": "9",
    "timer": "3",
    "variable": "4",
    "gmov": "\x02",
    "video": "\x03",
    "audio": "\x04",
    "expic": "<",
}


def _extract_objmark_bodies(text: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    index = 0
    while True:
        match = re.search(r"(?P<var>\w+)\s*=\s*new objmark_\s*\{", text[index:])
        if match is None:
            return blocks
        var_name = match.group("var")
        absolute_start = index + match.start()
        body_start = text.find("{", absolute_start) + 1
        cursor = body_start
        depth = 1
        while cursor < len(text) and depth > 0:
            char = text[cursor]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            cursor += 1
        if depth != 0:
            raise ValueError(f"Unterminated objmark block for {var_name}")
        body = text[body_start : cursor - 1]
        blocks[var_name] = body
        index = cursor


def parse_decompiled_objmarks(source_text: str) -> dict[str, DecompiledObjmark]:
    result: dict[str, DecompiledObjmark] = {}
    for var_name, body in _extract_objmark_bodies(source_text).items():
        display_name = _optional_match(body, r'name\s*=\s*"([^"]*)"(?:\.Language\(\))?')
        label = _optional_match(body, r'label\s*=\s*"([^"]*)"')
        object_id = _optional_int(body, r"id\s*=\s*(\d+)")
        intname = _optional_match(body, r'intname\s*=\s*"([^"]*)"')
        event_slots = _optional_int(body, r"events\s*=\s*new _eventtype\[(\d+)\]")
        obj_get_atts_class = _optional_match(body, r"ObjGetAllAtts\s*=\s*(\w+)\.GetAtts_WithNoHead")
        rect_match = re.search(
            r"defaultRectangle\s*=\s*new Rectangle\(\s*0\s*,\s*0\s*,\s*(\d+)\s*,\s*(\d+)\s*\)",
            body,
        )
        width = int(rect_match.group(1)) if rect_match else None
        height = int(rect_match.group(2)) if rect_match else None
        result[var_name] = DecompiledObjmark(
            var_name=var_name,
            display_name=display_name,
            label=label,
            object_id=object_id,
            intname=intname,
            default_width=width,
            default_height=height,
            event_slots=event_slots,
            obj_get_atts_class=obj_get_atts_class,
        )
    return result


def parse_decompiled_gui_obj_field_catalog(
    source_text: str,
    *,
    class_name: str,
    source_path: str | None = None,
) -> GuiFieldCatalog:
    pattern = re.compile(
        r'atts\.addatt\("(?P<name>[^"]+)"\s*,.*?attshuvis\.(?P<vis>yes|no)\b',
        re.IGNORECASE,
    )
    visible_fields: list[str] = []
    all_fields: list[str] = []
    for match in pattern.finditer(source_text):
        field_name = str(match.group("name")).strip()
        if not field_name:
            continue
        if field_name not in all_fields:
            all_fields.append(field_name)
        if match.group("vis").lower() == "yes" and field_name not in visible_fields:
            visible_fields.append(field_name)
    return GuiFieldCatalog(
        class_name=class_name,
        source_path=source_path,
        visible_fields=tuple(visible_fields),
        all_fields=tuple(all_fields),
    )


def load_decompiled_gui_obj_field_catalog(
    class_name: str,
    *,
    hmitype_dir: str | Path = DEFAULT_DECOMPILED_HMITYPE_DIR,
) -> GuiFieldCatalog | None:
    source_path = Path(hmitype_dir).resolve() / f"{class_name}.cs"
    if not source_path.exists():
        return None
    text = source_path.read_text(encoding="utf-8")
    return parse_decompiled_gui_obj_field_catalog(
        text,
        class_name=class_name,
        source_path=str(source_path),
    )


def load_decompiled_objmarks(path: str | Path = DEFAULT_DECOMPILED_APPOBJSCLASS) -> dict[str, DecompiledObjmark]:
    source_path = Path(path).resolve()
    text = source_path.read_text(encoding="utf-8")
    return parse_decompiled_objmarks(text)


def parse_decompiled_toolbox_order(source_text: str) -> list[str]:
    body_match = re.search(
        r"private void RefGongjuItem\(\)\s*\{(?P<body>.*?)\}\s*private void Form1_Load",
        source_text,
        re.DOTALL,
    )
    if body_match is None:
        raise ValueError("Unable to locate RefGongjuItem() in decompiled HMIFORM main.cs")
    body = body_match.group("body")
    pattern = re.compile(
        r"colListBox1\.Items_Add\(new ColListBoxItem\s*\{\s*"
        r"Text = AppData\.appobjs\.(?P<text_var>\w+)\.name,\s*"
        r"img = .*?,\s*"
        r"obj = AppData\.appobjs\.(?P<obj_var>\w+)\s*"
        r"\}\);",
        re.DOTALL,
    )
    order: list[str] = []
    for match in pattern.finditer(body):
        text_var = match.group("text_var")
        obj_var = match.group("obj_var")
        if text_var != obj_var:
            continue
        order.append(obj_var)
    if not order:
        raise ValueError("No toolbox entries found in RefGongjuItem()")
    return order


def load_decompiled_toolbox_order(path: str | Path = DEFAULT_DECOMPILED_MAINCS) -> list[str]:
    source_path = Path(path).resolve()
    text = source_path.read_text(encoding="utf-8")
    return parse_decompiled_toolbox_order(text)


def _auto_key_for_decompiled_var(var_name: str) -> str:
    override = AUTO_DISCOVERED_CONTROL_OVERRIDES.get(var_name)
    if override is not None:
        return str(override["key"])
    return var_name.strip().lower().replace("_", "-")


def _auto_aliases_for_decompiled_var(var_name: str) -> tuple[str, ...]:
    override = AUTO_DISCOVERED_CONTROL_OVERRIDES.get(var_name)
    if override is not None:
        return tuple(str(item) for item in override.get("aliases", ()))
    return (var_name.strip().lower(),)


def build_official_gui_control_registry(
    *,
    appobjsclass_path: str | Path = DEFAULT_DECOMPILED_APPOBJSCLASS,
    maincs_path: str | Path = DEFAULT_DECOMPILED_MAINCS,
    decompiled_objmarks: dict[str, DecompiledObjmark] | None = None,
    toolbox_order: list[str] | None = None,
    page0_scan_report: str | Path | None = None,
    page1_scan_report: str | Path | None = None,
) -> dict[str, OfficialGuiControlSpec]:
    objmarks = decompiled_objmarks if decompiled_objmarks is not None else load_decompiled_objmarks(appobjsclass_path)
    if toolbox_order is not None:
        decompiled_toolbox_order = toolbox_order
    else:
        try:
            decompiled_toolbox_order = load_decompiled_toolbox_order(maincs_path)
        except FileNotFoundError:
            decompiled_toolbox_order = []
    toolbox_indices = {var_name: index for index, var_name in enumerate(decompiled_toolbox_order)}
    registry: dict[str, OfficialGuiControlSpec] = {}
    registered_var_names: set[str] = set()
    for key, hint in CONTROL_HINTS.items():
        decompiled = objmarks.get(hint["decompiled_var_name"])
        field_catalog = None
        if decompiled is not None and decompiled.obj_get_atts_class:
            field_catalog = load_decompiled_gui_obj_field_catalog(decompiled.obj_get_atts_class)
        spec = OfficialGuiControlSpec(
            key=key,
            aliases=tuple(hint["aliases"]),
            decompiled_var_name=hint["decompiled_var_name"],
            expected_type_code=hint["expected_type_code"],
            calibration=hint["calibration"],
            toolbox_index=toolbox_indices.get(hint["decompiled_var_name"]),
            decompiled=decompiled,
            field_catalog=field_catalog,
        )
        registry[key] = spec
        registered_var_names.add(hint["decompiled_var_name"])
    for var_name in decompiled_toolbox_order:
        if var_name in registered_var_names:
            continue
        decompiled = objmarks.get(var_name)
        if decompiled is None:
            continue
        field_catalog = None
        if decompiled.obj_get_atts_class:
            field_catalog = load_decompiled_gui_obj_field_catalog(decompiled.obj_get_atts_class)
        key = _auto_key_for_decompiled_var(var_name)
        if key in registry:
            continue
        registry[key] = OfficialGuiControlSpec(
            key=key,
            aliases=_auto_aliases_for_decompiled_var(var_name),
            decompiled_var_name=var_name,
            expected_type_code=AUTO_DISCOVERED_TYPE_CODE_OVERRIDES.get(var_name),
            calibration=GuiCalibration(),
            toolbox_index=toolbox_indices.get(var_name),
            decompiled=decompiled,
            field_catalog=field_catalog,
        )
    if page0_scan_report is not None:
        registry = _apply_scan_report_overrides(registry, scan_report_path=page0_scan_report, page_index=0)
    if page1_scan_report is not None:
        registry = _apply_scan_report_overrides(registry, scan_report_path=page1_scan_report, page_index=1)
    return registry


def normalize_official_gui_control_name(
    raw_name: str,
    *,
    registry: dict[str, OfficialGuiControlSpec] | None = None,
) -> str:
    if not isinstance(raw_name, str) or not raw_name.strip():
        raise ValueError("control name must be a non-empty string")
    lookup = registry or build_official_gui_control_registry()
    lowered = raw_name.strip().lower()
    for key, spec in lookup.items():
        if lowered in spec.canonical_names:
            return key
    raise KeyError(f"Unknown official GUI control {raw_name!r}")


def resolve_official_gui_control(
    raw_name: str,
    *,
    registry: dict[str, OfficialGuiControlSpec] | None = None,
) -> OfficialGuiControlSpec:
    lookup = registry or build_official_gui_control_registry()
    key = normalize_official_gui_control_name(raw_name, registry=lookup)
    return lookup[key]


def normalize_official_hmi_automation_spec(
    spec: dict[str, Any],
    *,
    registry: dict[str, OfficialGuiControlSpec] | None = None,
) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise ValueError("automation spec must be a JSON object")
    if int(spec.get("schema_version", 0) or 0) != AUTOMATION_SCHEMA_VERSION:
        raise ValueError(f"automation spec schema_version must be {AUTOMATION_SCHEMA_VERSION}")
    actions = spec.get("actions")
    if not isinstance(actions, list) or not actions:
        raise ValueError("automation spec must contain a non-empty actions list")

    lookup = registry or build_official_gui_control_registry(
        page0_scan_report=spec.get("page0_scan_report"),
        page1_scan_report=spec.get("page1_scan_report"),
    )
    out_dir = Path(spec.get("out_dir") or ".").resolve()
    normalized_actions: list[dict[str, Any]] = []
    created_controls: list[dict[str, Any]] = []
    current_page_index = int(spec.get("default_page_index", 0) or 0)

    for index, raw_action in enumerate(actions):
        if not isinstance(raw_action, dict):
            raise ValueError(f"action #{index} must be a JSON object")
        kind = str(raw_action.get("kind") or "").strip()
        if kind == "select-page":
            page_index = int(raw_action.get("page_index", 0))
            normalized = {
                "kind": kind,
                "page_index": page_index,
                "page_resource": raw_action.get("page_resource") or f"{page_index}.pa",
                "page_list_x": int(raw_action.get("page_list_x", DEFAULT_PAGE_LIST_X)),
                "page_row_y": int(raw_action.get("page_row_y", DEFAULT_PAGE_ROW_Y.get(page_index, DEFAULT_PAGE_ROW_Y[1]))),
            }
            normalized_actions.append(normalized)
            current_page_index = page_index
            continue
        if kind == "create-widget":
            control = resolve_official_gui_control(str(raw_action.get("control") or raw_action.get("widget") or ""), registry=lookup)
            page_index = int(raw_action.get("page_index", current_page_index))
            selection_mode = str(
                raw_action.get("selection_mode")
                or ("message-index" if control.toolbox_index is not None else "screen-click")
            )
            tool_rel_y = raw_action.get("tool_rel_y")
            if tool_rel_y is None:
                tool_rel_y = control.calibration.tool_rel_y_for_page(page_index)
            if tool_rel_y is None and selection_mode != "message-index":
                raise ValueError(f"action #{index} missing tool_rel_y for control {control.key!r} on page {page_index}")
            expected_objname = raw_action.get("expected_objname") or control.default_expected_objname()
            raw_expected_type_code = raw_action.get("expected_type_code", control.expected_type_code)
            expected_type_code = None
            if raw_expected_type_code is not None and str(raw_expected_type_code).strip():
                expected_type_code = str(raw_expected_type_code)
            normalized = {
                "kind": kind,
                "control": control.key,
                "control_spec": control.to_dict(),
                "page_index": page_index,
                "page_resource": raw_action.get("page_resource") or f"{page_index}.pa",
                "toolbox_x": int(raw_action.get("toolbox_x", DEFAULT_TOOLBOX_X)),
                "toolbox_index": (
                    None if raw_action.get("toolbox_index") is None else int(raw_action.get("toolbox_index"))
                ) if raw_action.get("toolbox_index") is not None else control.toolbox_index,
                "selection_mode": selection_mode,
                "tool_rel_y": 0 if tool_rel_y is None else int(tool_rel_y),
                "toolbox_wheel": int(raw_action.get("toolbox_wheel", control.calibration.page1_toolbox_wheel if page_index == 1 else 0)),
                "panel_splitter_x": raw_action.get(
                    "panel_splitter_x",
                    control.calibration.page1_panel_splitter_x if page_index == 1 else None,
                ),
                "panel_splitter_start_y": raw_action.get(
                    "panel_splitter_start_y",
                    control.calibration.page1_panel_splitter_start_y if page_index == 1 else None,
                ),
                "panel_splitter_end_y": raw_action.get(
                    "panel_splitter_end_y",
                    control.calibration.page1_panel_splitter_end_y if page_index == 1 else None,
                ),
                "drag_scroll_start_y": raw_action.get(
                    "drag_scroll_start_y",
                    control.calibration.page1_drag_scroll_start_y if page_index == 1 else None,
                ),
                "drag_scroll_end_y": raw_action.get(
                    "drag_scroll_end_y",
                    control.calibration.page1_drag_scroll_end_y if page_index == 1 else None,
                ),
                "canvas_x": int(raw_action.get("canvas_x", control.calibration.canvas_x)),
                "canvas_y": int(raw_action.get("canvas_y", control.calibration.canvas_y)),
                "expected_objname": expected_objname,
                "expected_type_code": expected_type_code,
                "post_delay_s": float(raw_action.get("post_delay_s", 1.5)),
            }
            normalized_actions.append(normalized)
            if expected_objname:
                created = {
                    "page": normalized["page_resource"],
                    "objname": expected_objname,
                }
                if expected_type_code is not None:
                    created["type_code"] = expected_type_code
                created_controls.append(created)
            current_page_index = page_index
            continue
        if kind == "create-widget-host":
            control = resolve_official_gui_control(str(raw_action.get("control") or raw_action.get("widget") or ""), registry=lookup)
            page_index = int(raw_action.get("page_index", current_page_index))
            expected_objname = raw_action.get("expected_objname") or control.default_expected_objname()
            raw_expected_type_code = raw_action.get("expected_type_code", control.expected_type_code)
            expected_type_code = None
            if raw_expected_type_code is not None and str(raw_expected_type_code).strip():
                expected_type_code = str(raw_expected_type_code)
            normalized = {
                "kind": kind,
                "control": control.key,
                "control_spec": control.to_dict(),
                "create_control_var_name": control.decompiled_var_name,
                "page_index": page_index,
                "page_resource": raw_action.get("page_resource") or f"{page_index}.pa",
                "expected_objname": expected_objname,
                "expected_type_code": expected_type_code,
            }
            normalized_actions.append(normalized)
            if expected_objname:
                created = {
                    "page": normalized["page_resource"],
                    "objname": expected_objname,
                }
                if expected_type_code is not None:
                    created["type_code"] = expected_type_code
                created_controls.append(created)
            current_page_index = page_index
            continue
        if kind == "select-object-gui":
            target = _normalize_patch_target(raw_action, index=index, registry=lookup)
            normalized_actions.append(
                {
                    "kind": kind,
                    "page_index": int(raw_action.get("page_index", current_page_index)),
                    "page_resource": str(raw_action.get("page_resource") or f"{current_page_index}.pa"),
                    "force_direct_gui": bool(raw_action.get("force_direct_gui", False)),
                    "prefer_managed_select": bool(raw_action.get("prefer_managed_select", False)),
                    **target,
                }
            )
            continue
        if kind == "save-and-close":
            normalized_actions.append({"kind": kind, "timeout_s": float(raw_action.get("timeout_s", 12.0))})
            continue
        if kind == "normalize-page-entry-length":
            normalized_actions.append(
                {
                    "kind": kind,
                    "page_resource": str(raw_action.get("page_resource") or f"{current_page_index}.pa"),
                }
            )
            continue
        if kind == "patch-field":
            field_name = str(raw_action.get("field") or "").strip()
            target = _normalize_patch_target(raw_action, index=index, registry=lookup)
            if not field_name or "value" not in raw_action:
                raise ValueError(f"action #{index} patch-field requires field/value")
            value = raw_action["value"]
            value_kind = "int" if isinstance(value, int) else str(raw_action.get("value_kind") or "string")
            normalized_actions.append(
                {
                    "kind": kind,
                    "page_resource": str(raw_action.get("page_resource") or f"{current_page_index}.pa"),
                    **target,
                    "field": field_name,
                    "value": value,
                    "value_kind": value_kind,
                }
            )
            continue
        if kind == "patch-rect":
            target = _normalize_patch_target(raw_action, index=index, registry=lookup)
            normalized_actions.append(
                {
                    "kind": kind,
                    "page_resource": str(raw_action.get("page_resource") or f"{current_page_index}.pa"),
                    **target,
                    "x": int(raw_action["x"]),
                    "y": int(raw_action["y"]),
                    "w": int(raw_action["w"]),
                    "h": int(raw_action["h"]),
                }
            )
            continue
        if kind == "patch-field-gui":
            field_name = str(raw_action.get("field") or "").strip()
            if not field_name or "value" not in raw_action:
                raise ValueError(f"action #{index} patch-field-gui requires field/value")
            value = raw_action["value"]
            value_kind = "int" if isinstance(value, int) else str(raw_action.get("value_kind") or "string")
            normalized_actions.append(
                {
                    "kind": kind,
                    "field": field_name,
                    "value": value,
                    "value_kind": value_kind,
                }
            )
            continue
        if kind == "patch-rect-gui":
            normalized_actions.append(
                {
                    "kind": kind,
                    "x": int(raw_action["x"]),
                    "y": int(raw_action["y"]),
                    "w": int(raw_action["w"]),
                    "h": int(raw_action["h"]),
                }
            )
            continue
        if kind == "patch-event-gui":
            lines = raw_action.get("lines")
            if not isinstance(lines, list):
                raise ValueError(f"action #{index} patch-event-gui requires lines list")
            event_name = str(raw_action.get("event") or raw_action.get("event_name") or "").strip().lower()
            event_prefix = str(raw_action.get("event_prefix") or _event_prefix_for_name(event_name) or "").strip()
            if not event_prefix:
                raise ValueError(f"action #{index} patch-event-gui requires event/event_prefix")
            normalized_actions.append(
                {
                    "kind": kind,
                    "event_prefix": event_prefix,
                    "event_name": event_name or None,
                    "lines": [str(line) for line in lines],
                }
            )
            continue
        if kind == "patch-event":
            target = _normalize_patch_target(raw_action, index=index, registry=lookup)
            lines = raw_action.get("lines")
            if not isinstance(lines, list):
                raise ValueError(f"action #{index} patch-event requires lines list")
            event_name = str(raw_action.get("event") or raw_action.get("event_name") or "").strip().lower()
            event_prefix = str(raw_action.get("event_prefix") or _event_prefix_for_name(event_name) or "").strip()
            if not event_prefix:
                raise ValueError(f"action #{index} patch-event requires event/event_prefix")
            normalized_actions.append(
                {
                    "kind": kind,
                    "page_resource": str(raw_action.get("page_resource") or f"{current_page_index}.pa"),
                    **target,
                    "event_prefix": event_prefix,
                    "event_name": event_name or None,
                    "lines": [str(line) for line in lines],
                }
            )
            continue
        if kind == "precompile-confirm":
            expect_controls = raw_action.get("expect_controls")
            if expect_controls is None:
                expect_controls = list(created_controls)
            normalized_actions.append(
                {
                    "kind": kind,
                    "out_dir": str(Path(raw_action.get("out_dir") or (out_dir / "precompile_confirmation")).resolve()),
                    "timeout_s": float(raw_action.get("timeout_s", 45.0)),
                    "allow_failure": bool(raw_action.get("allow_failure", False)),
                    "expect_controls": [_normalize_expected_control(item) for item in expect_controls],
                    "expect_orders": [_normalize_expected_order(item) for item in raw_action.get("expect_orders", [])],
                    "pages": list(raw_action.get("pages") or sorted({item["page"] for item in expect_controls if item.get("page")})),
                }
            )
            continue
        if kind == "compile-capture":
            normalized_actions.append(
                {
                    "kind": kind,
                    "out_dir": str(Path(raw_action.get("out_dir") or (out_dir / "official_compile")).resolve()),
                    "timeout_s": float(raw_action.get("timeout_s", 90.0)),
                    "open_download_output": bool(raw_action.get("open_download_output", True)),
                    "close": bool(raw_action.get("close", False)),
                    "allow_failure": bool(raw_action.get("allow_failure", False)),
                }
            )
            continue
        if kind == "event-index-inspect":
            normalized_actions.append(
                {
                    "kind": kind,
                    "tft_path": None if raw_action.get("tft_path") is None else str(Path(raw_action["tft_path"]).resolve()),
                    "out_path": str(Path(raw_action.get("out_path") or (out_dir / "compile_event_index.json")).resolve()),
                }
            )
            continue
        raise ValueError(f"Unsupported automation action kind: {kind!r}")

    return {
        "schema_version": AUTOMATION_SCHEMA_VERSION,
        "name": str(spec.get("name") or "official_hmi_automation"),
        "hmi_path": str(Path(spec["hmi_path"]).resolve()) if spec.get("hmi_path") else None,
        "seed_hmi": str(Path(spec["seed_hmi"]).resolve()) if spec.get("seed_hmi") else None,
        "out_dir": str(out_dir),
        "exe_path": str(Path(spec.get("exe_path") or DEFAULT_OFFICIAL_EXE).resolve()),
        "default_page_index": int(spec.get("default_page_index", 0) or 0),
        "page0_scan_report": (
            None if spec.get("page0_scan_report") is None else str(Path(spec["page0_scan_report"]).resolve())
        ),
        "page1_scan_report": (
            None if spec.get("page1_scan_report") is None else str(Path(spec["page1_scan_report"]).resolve())
        ),
        "actions": normalized_actions,
    }


def _normalize_expected_control(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError(f"expect_controls items must be objects, got {item!r}")
    page = str(item.get("page") or "").strip()
    objname = str(item.get("objname") or "").strip()
    if not page or not objname:
        raise ValueError(f"expect_controls item missing page/objname: {item!r}")
    payload = {"page": page, "objname": objname}
    if item.get("type_code") is not None:
        payload["type_code"] = str(item["type_code"])
    if item.get("object_id") is not None:
        payload["object_id"] = int(item["object_id"])
    if item.get("event_tokens_contains") is not None:
        tokens = item["event_tokens_contains"]
        if not isinstance(tokens, list):
            raise ValueError(f"expect_controls.event_tokens_contains must be a list: {item!r}")
        payload["event_tokens_contains"] = [str(token) for token in tokens]
    if item.get("field_equals") is not None:
        field_equals = item["field_equals"]
        if not isinstance(field_equals, dict):
            raise ValueError(f"expect_controls.field_equals must be an object: {item!r}")
        payload["field_equals"] = {
            str(name): value
            for name, value in field_equals.items()
        }
    return payload


def _normalize_expected_order(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError(f"expect_orders items must be objects, got {item!r}")
    page = str(item.get("page") or "").strip()
    names = item.get("names")
    if not page or not isinstance(names, list) or not names:
        raise ValueError(f"expect_orders item missing page/names: {item!r}")
    return {"page": page, "names": [str(name) for name in names]}


def _event_prefix_for_name(name: str) -> str | None:
    mapping = {
        "ref": "codesref-",
        "vis": "codesvis-",
        "down": "codesdown-",
        "up": "codesup-",
        "load": "codesload-",
        "loadend": "codesloadend-",
        "unload": "codesunload-",
        "playend": "codesplayend-",
        "touchs": "codestouchs-",
        "timer": "codestimer-",
        "slide": "codesslide-",
    }
    return mapping.get(name)


def _normalize_patch_target(
    raw_action: dict[str, Any],
    *,
    index: int,
    registry: dict[str, OfficialGuiControlSpec],
) -> dict[str, Any]:
    objname = str(raw_action.get("object") or "").strip()
    if objname:
        return {"object": objname}
    type_code = raw_action.get("type_code")
    control_name = raw_action.get("control")
    if type_code is None and control_name is not None:
        type_code = resolve_official_gui_control(str(control_name), registry=registry).expected_type_code
    if type_code is None:
        raise ValueError(f"action #{index} patch action requires object, type_code, or control")
    exclude_names = raw_action.get("exclude_names") or []
    if not isinstance(exclude_names, list):
        raise ValueError(f"action #{index} exclude_names must be a list")
    return {
        "object": None,
        "type_code": str(type_code),
        "exclude_names": [str(name) for name in exclude_names],
        "newest": bool(raw_action.get("newest", False)),
    }


def _optional_match(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text)
    return match.group(1) if match else None


def _optional_int(text: str, pattern: str) -> int | None:
    match = re.search(pattern, text)
    return int(match.group(1)) if match else None


def _apply_scan_report_overrides(
    registry: dict[str, OfficialGuiControlSpec],
    *,
    scan_report_path: str | Path,
    page_index: int,
) -> dict[str, OfficialGuiControlSpec]:
    report = json.loads(Path(scan_report_path).resolve().read_text(encoding="utf-8"))
    matches_by_type: dict[str, dict[str, Any]] = {}
    for item in report.get("items", []):
        if not isinstance(item, dict):
            continue
        type_code = item.get("first_added_type")
        if not type_code:
            continue
        matches_by_type[str(type_code)] = item

    updated: dict[str, OfficialGuiControlSpec] = {}
    for key, spec in registry.items():
        if spec.expected_type_code is None:
            updated[key] = spec
            continue
        item = matches_by_type.get(spec.expected_type_code)
        if item is None:
            updated[key] = spec
            continue
        calibration = spec.calibration
        if page_index == 1:
            calibration = GuiCalibration(
                page0_tool_rel_y=calibration.page0_tool_rel_y,
                page1_tool_rel_y=int(item["tool_rel_y"]),
                page1_toolbox_wheel=int(item.get("toolbox_wheel", calibration.page1_toolbox_wheel)),
                page1_panel_splitter_x=calibration.page1_panel_splitter_x,
                page1_panel_splitter_start_y=calibration.page1_panel_splitter_start_y,
                page1_panel_splitter_end_y=calibration.page1_panel_splitter_end_y,
                page1_drag_scroll_start_y=calibration.page1_drag_scroll_start_y,
                page1_drag_scroll_end_y=calibration.page1_drag_scroll_end_y,
                canvas_x=calibration.canvas_x,
                canvas_y=calibration.canvas_y,
            )
        else:
            calibration = GuiCalibration(
                page0_tool_rel_y=int(item["tool_rel_y"]),
                page1_tool_rel_y=calibration.page1_tool_rel_y,
                page1_toolbox_wheel=calibration.page1_toolbox_wheel,
                page1_panel_splitter_x=calibration.page1_panel_splitter_x,
                page1_panel_splitter_start_y=calibration.page1_panel_splitter_start_y,
                page1_panel_splitter_end_y=calibration.page1_panel_splitter_end_y,
                page1_drag_scroll_start_y=calibration.page1_drag_scroll_start_y,
                page1_drag_scroll_end_y=calibration.page1_drag_scroll_end_y,
                canvas_x=calibration.canvas_x,
                canvas_y=calibration.canvas_y,
            )
        updated[key] = OfficialGuiControlSpec(
            key=spec.key,
            aliases=spec.aliases,
            decompiled_var_name=spec.decompiled_var_name,
            expected_type_code=spec.expected_type_code,
            calibration=calibration,
            toolbox_index=spec.toolbox_index,
            decompiled=spec.decompiled,
        )
    return updated


def build_minimal_official_hmi_automation_spec(
    *,
    control_name: str,
    seed_hmi: str | Path,
    out_dir: str | Path,
    page_index: int = 0,
    hmi_path: str | Path | None = None,
    name: str | None = None,
    include_compile_capture: bool = True,
    registry: dict[str, OfficialGuiControlSpec] | None = None,
) -> dict[str, Any]:
    lookup = registry or build_official_gui_control_registry()
    control = resolve_official_gui_control(control_name, registry=lookup)
    seed_path = Path(seed_hmi).resolve()
    out_path = Path(out_dir).resolve()
    spec_name = name or f"{control.key.replace('-', '_')}_page{page_index}_minimal_official_gui_oracle"
    expected_objname = control.default_expected_objname()
    if not expected_objname:
        raise ValueError(f"Control {control.key!r} has no decompiled intname/default object name")

    create_action: dict[str, Any] = {
        "kind": "create-widget",
        "control": control.key,
        "page_index": int(page_index),
        "expected_objname": expected_objname,
    }
    if control.expected_type_code is not None:
        create_action["expected_type_code"] = control.expected_type_code

    expect_control: dict[str, Any] = {
        "page": f"{int(page_index)}.pa",
        "objname": expected_objname,
    }
    if control.expected_type_code is not None:
        expect_control["type_code"] = control.expected_type_code

    actions: list[dict[str, Any]] = []
    if int(page_index) != 0:
        actions.append({"kind": "select-page", "page_index": int(page_index)})
    actions.append(create_action)
    actions.append({"kind": "save-and-close"})
    actions.append(
        {
            "kind": "precompile-confirm",
            "expect_controls": [expect_control],
            "pages": [f"{int(page_index)}.pa"],
        }
    )
    if include_compile_capture:
        actions.append({"kind": "compile-capture", "open_download_output": True, "close": True})

    payload: dict[str, Any] = {
        "schema_version": AUTOMATION_SCHEMA_VERSION,
        "name": spec_name,
        "seed_hmi": str(seed_path),
        "out_dir": str(out_path),
        "actions": actions,
    }
    if hmi_path is not None:
        payload["hmi_path"] = str(Path(hmi_path).resolve())
    return payload


def dump_control_registry(
    *,
    appobjsclass_path: str | Path = DEFAULT_DECOMPILED_APPOBJSCLASS,
) -> dict[str, Any]:
    registry = build_official_gui_control_registry(appobjsclass_path=appobjsclass_path)
    return {
        "appobjsclass": str(Path(appobjsclass_path).resolve()),
        "controls": {
            key: spec.to_dict()
            for key, spec in sorted(registry.items())
        },
    }


def dump_normalized_automation_spec(spec: dict[str, Any]) -> str:
    return json.dumps(normalize_official_hmi_automation_spec(spec), ensure_ascii=False, indent=2)
