from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from .agent_preview import generate_agent_preview
from .event_logic import analyze_scene_events
from .hmi_inspect import inspect_hmi
from .page_format import PageBlock, PageFile, parse_page_data
from .scene import validate_scene
from .scene_edit import write_scene_document
from .widgets import (
    CURRENT_TARGET,
    FIXTURE_WIDGET_TEMPLATE_CASES,
    WIDGET_TYPE_REGISTRY,
    WidgetSupport,
    WidgetWriter,
    format_type_code,
)


IMPORT_NOT_CLAIMED = (
    "byte-perfect HMI roundtrip",
    "TFT rebuild equivalence",
    "runtime behavior proof",
    "hardware display proof",
    "complete resource/font reconstruction",
)

_PA_ENTRY_RE = re.compile(r"^(?P<index>\d+)\.pa$", re.IGNORECASE)
_EVENT_PREFIX_TO_NAME = {
    "codesload": "load",
    "codesloadend": "loadend",
    "codesdown": "down",
    "codesup": "up",
    "codesunload": "unload",
    "codestimer": "timer",
    "codesslide": "slide",
}
_BUILTIN_TYPE_CODES = {
    "b": "button",
    "p": "image",
    "6": "number",
    "t": "text",
    "3": "timer",
}
_BASIC_GEOMETRY_FIELDS = {"x", "y", "w", "h"}
_BASIC_VALUE_FIELDS = {"val"}
_TEXT_FIELDS = {"txt", "path"}
_RESOURCE_FIELDS = {"pic", "picc", "pic1", "picc1", "pic2", "picc2", "bpic", "ppic", "vvs0", "vvs1", "vvs2", "path"}
_STYLE_FIELDS = {
    "sta",
    "style",
    "font",
    "bco",
    "bco1",
    "bco2",
    "pco",
    "pco2",
    "xcen",
    "ycen",
    "isbr",
    "spax",
    "spay",
    "maxval",
    "minval",
    "tim",
    "en",
    "dis",
    "dez",
    "format",
    "up",
    "down",
    "left",
    "right",
}


@dataclass(frozen=True, slots=True)
class HmiPageResource:
    entry_name: str
    entry_index: int
    runtime_index: int
    page: PageFile


def import_hmi_project(
    hmi_path: str | Path,
    out_dir: str | Path,
    *,
    target: str = CURRENT_TARGET,
    overwrite: bool = False,
) -> dict[str, Any]:
    source = Path(hmi_path).resolve()
    output_dir = Path(out_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    scene_path = output_dir / "scene.imported.json"
    report_path = output_dir / "import_report.json"
    if not overwrite:
        for path in (scene_path, report_path):
            if path.exists():
                raise FileExistsError(f"Import output already exists: {path}")

    raw = source.read_bytes()
    inspection = inspect_hmi(source)
    pages = _load_page_resources(raw, inspection)
    scene_payload, warnings = _build_imported_scene(source, target, pages)
    scene = validate_scene(scene_payload)
    write_scene_document(scene_path, scene.to_dict())

    event_analysis = analyze_scene_events(scene)
    placeholder_count = sum(
        1
        for page in scene.pages
        for widget in page.widgets
        if widget.bindings.get("hmi_import", {}).get("placeholder")
    )
    report = {
        "source": {
            "path": str(source),
            "sha256": sha256(raw).hexdigest(),
            "target_requested": target,
            "entry_count": inspection.entry_count,
        },
        "outputs": {
            "scene_json": str(scene_path),
            "import_report_json": str(report_path),
        },
        "summary": {
            "pages": len(scene.pages),
            "objects_total": sum(max(0, len(page.page.blocks) - 1) for page in pages),
            "objects_imported": sum(len(page.widgets) for page in scene.pages) - placeholder_count,
            "objects_placeholder": placeholder_count,
            "events_raw_preserved": event_analysis["summary"]["event_slot_count"],
            "events_structured": sum(
                1
                for slot in event_analysis["event_summary"]
                for command in slot["commands"]
                if command.get("structured")
            ),
        },
        "pages": [
            {
                "entry_name": page.entry_name,
                "runtime_index": page.runtime_index,
                "scene_page": scene.pages[index].id,
                "object_count": max(0, len(page.page.blocks) - 1),
            }
            for index, page in enumerate(pages)
        ],
        "warnings": warnings,
        "not_claimed": list(IMPORT_NOT_CLAIMED),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    context = generate_agent_preview(scene_path, output_dir, target=target)
    context_path = Path(context["outputs"]["agent_context_json"])
    context_payload = json.loads(context_path.read_text(encoding="utf-8"))
    reimport_command = f'python -m usarthmi --json hmi import "{source}" --out-dir "{output_dir}" --overwrite'
    roundtrip_command = f'python -m usarthmi --json hmi roundtrip-check "{source}" --out-dir "{output_dir / "roundtrip"}" --overwrite'
    context_payload.setdefault("safe_commands", []).insert(0, reimport_command)
    context_payload.setdefault("safe_commands", []).insert(1, roundtrip_command)
    context_payload.setdefault("agent_interface", {}).setdefault("safe_commands", []).insert(0, reimport_command)
    context_payload.setdefault("agent_interface", {}).setdefault("safe_commands", []).insert(1, roundtrip_command)
    context_payload["import_report"] = {
        "path": str(report_path),
        "summary": report["summary"],
        "warnings": warnings,
        "not_claimed": list(IMPORT_NOT_CLAIMED),
    }
    context_path.write_text(json.dumps(context_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "source_hmi": str(source),
        "scene_path": str(scene_path),
        "import_report": str(report_path),
        "agent_context": str(context_path),
        "preview_png": context["outputs"]["preview_png"],
        "annotated_preview_png": context["outputs"]["annotated_preview_png"],
        "summary": report["summary"],
        "warnings": warnings,
        "not_claimed": list(IMPORT_NOT_CLAIMED),
    }


def _load_page_resources(raw: bytes, inspection) -> list[HmiPageResource]:
    pages: list[HmiPageResource] = []
    for entry in inspection.entries:
        match = _PA_ENTRY_RE.match(entry.name)
        if not match or not entry.in_file:
            continue
        data = raw[entry.data_offset : entry.data_offset + entry.length]
        page = parse_page_data(data)
        pages.append(
            HmiPageResource(
                entry_name=entry.name,
                entry_index=entry.index,
                runtime_index=int(match.group("index")),
                page=page,
            )
        )
    pages.sort(key=lambda item: item.runtime_index)
    if not pages:
        raise ValueError("HMI import requires at least one .pa page entry")
    return pages


def _build_imported_scene(
    source: Path,
    target: str,
    pages: list[HmiPageResource],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    warnings: list[dict[str, Any]] = []
    scene_pages: list[dict[str, Any]] = []
    for page_index, page_resource in enumerate(pages):
        page_block = _first_page_block(page_resource.page)
        page_id = page_block.objname or page_resource.page.page_name or f"page{page_resource.runtime_index}"
        page_doc = {
            "id": page_id,
            "layout": {
                "type": "absolute",
                "hmi_import": {
                    "entry_name": page_resource.entry_name,
                    "runtime_index": page_resource.runtime_index,
                    "source_page_name": page_resource.page.page_name,
                },
            },
            "events": _events_from_block(page_block),
            "widgets": [],
        }
        for block_index, block in enumerate(page_resource.page.blocks):
            if block.type_code == "y":
                continue
            widget, widget_warnings = _widget_from_block(
                block,
                page_id=page_id,
                page_index=page_index,
                block_index=block_index,
            )
            page_doc["widgets"].append(widget)
            warnings.extend(widget_warnings)
        scene_pages.append(page_doc)

    default_page = scene_pages[0]["id"]
    payload = {
        "project": {
            "name": source.stem,
            "default_page": default_page,
            "target": target,
            "hmi_import": {
                "source": str(source),
                "lossy": True,
                "not_claimed": list(IMPORT_NOT_CLAIMED),
            },
        },
        "canvas": {"width": 800, "height": 480, "background_color": _page_background(pages[0].page)},
        "assets": {},
        "pages": scene_pages,
    }
    return payload, warnings


def _first_page_block(page: PageFile) -> PageBlock:
    for block in page.blocks:
        if block.type_code == "y":
            return block
    if not page.blocks:
        raise ValueError("page has no blocks")
    return page.blocks[0]


def _page_background(page: PageFile) -> int:
    page_block = _first_page_block(page)
    value = _field_value(page_block, "bco")
    return int(value) if isinstance(value, int) else 65535


def _widget_from_block(
    block: PageBlock,
    *,
    page_id: str,
    page_index: int,
    block_index: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    type_code = block.type_code or ""
    widget_type = _widget_type_from_type_code(type_code)
    objname = block.objname or f"obj{block_index}"
    fields = _block_fields(block)
    source = {
        "source": "hmi_import",
        "page": page_id,
        "page_index": page_index,
        "block_index": block_index,
        "attr_name": block.attr_name,
        "source_type_code": format_type_code(type_code),
        "source_object_id": fields.get("id"),
    }
    warnings: list[dict[str, Any]] = []
    placeholder = widget_type is None
    if placeholder:
        widget_type = "text"
        warnings.append(
            {
                "severity": "warning",
                "code": "UNKNOWN_WIDGET_TYPE",
                "page": page_id,
                "object": objname,
                "source_type_code": format_type_code(type_code),
                "message": f"Object type {format_type_code(type_code)!r} is preserved as a text placeholder",
            }
        )

    widget: dict[str, Any] = {
        "id": objname,
        "type": widget_type,
        "bindings": {
            "hmi_import": {
                **source,
                "placeholder": placeholder,
                "lossy": True,
            }
        },
        "events": _events_from_block(block),
    }
    for key in _BASIC_GEOMETRY_FIELDS:
        value = fields.get(key)
        if isinstance(value, int):
            widget[key] = value
    if placeholder:
        widget.setdefault("x", int(fields.get("x") or 0))
        widget.setdefault("y", int(fields.get("y") or 0))
        widget.setdefault("w", int(fields.get("w") or 180))
        widget.setdefault("h", int(fields.get("h") or 36))
        widget["text"] = f"{objname} {format_type_code(type_code)}"
    elif "txt" in fields and isinstance(fields["txt"], str):
        widget["text"] = fields["txt"]
    elif widget_type in {"text", "button"} and "path" in fields and isinstance(fields["path"], str):
        widget["text"] = fields["path"]
    if "val" in fields and isinstance(fields["val"], int):
        widget["value"] = fields["val"]
    style = {key: value for key, value in fields.items() if key in _STYLE_FIELDS}
    resources = {key: value for key, value in fields.items() if key in _RESOURCE_FIELDS}
    if style:
        widget["style"] = style
    if resources:
        widget["resources"] = resources
    if fields:
        widget["bindings"]["hmi_import"]["fields"] = fields
    return widget, warnings


def _widget_type_from_type_code(type_code: str) -> str | None:
    if type_code in _BUILTIN_TYPE_CODES:
        return _BUILTIN_TYPE_CODES[type_code]
    for widget_type, (_case_name, candidate) in FIXTURE_WIDGET_TEMPLATE_CASES.items():
        if candidate == type_code:
            return widget_type
    for widget_type, info in WIDGET_TYPE_REGISTRY.items():
        if info.type_code == type_code and info.support in {WidgetSupport.SUPPORTED, WidgetSupport.PENDING}:
            if info.writer in {WidgetWriter.BUILT_IN, WidgetWriter.FIXTURE}:
                return widget_type
    return None


def _events_from_block(block: PageBlock) -> dict[str, list[str]]:
    events: dict[str, list[str]] = {}
    cursor = 0
    tokens = list(block.event_tokens)
    while cursor < len(tokens):
        raw_header = tokens[cursor].strip()
        cursor += 1
        prefix, count = _parse_event_header(raw_header)
        if prefix is None:
            continue
        lines = tokens[cursor : cursor + count]
        cursor += count
        event_name = _EVENT_PREFIX_TO_NAME.get(prefix)
        if event_name and lines:
            events[event_name] = list(lines)
    return events


def _parse_event_header(raw_header: str) -> tuple[str | None, int]:
    match = re.match(r"^(codes[A-Za-z0-9_]+)-(\d+)", raw_header)
    if match is None:
        return None, 0
    return match.group(1), int(match.group(2))


def _block_fields(block: PageBlock) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for field in block.fields:
        fields[field.name] = _field_value(block, field.name)
    return fields


def _field_value(block: PageBlock, name: str) -> Any:
    field = block.get_field(name)
    if field is None:
        return None
    if name in _TEXT_FIELDS:
        return _decode_text(field.value).rstrip("\x00")
    if 0 < len(field.value) <= 4:
        return int.from_bytes(field.value, "little", signed=False)
    if not field.value:
        return 0
    text = _decode_text(field.value).rstrip("\x00")
    if text and all(char.isprintable() or char in "\t\r\n" for char in text):
        return text
    return field.value.hex(" ")


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "gbk", "ascii"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")
