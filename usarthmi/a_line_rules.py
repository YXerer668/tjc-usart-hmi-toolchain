from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from usarthmi.hmi_inspect import inspect_hmi
from usarthmi.official_gui_automation import AUTOMATION_SCHEMA_VERSION
from usarthmi.page_format import parse_page_data


@dataclass(frozen=True, slots=True)
class ALinePage:
    runtime_index: int
    page_resource: str
    page_name: str
    block_count: int


ALINE_SHARED_WRAPPER_PAGES: tuple[ALinePage, ...] = (
    ALinePage(0, "0.pa", "start", 1),
    ALinePage(1, "1.pa", "keybdAP", 83),
    ALinePage(2, "2.pa", "main", 20),
    ALinePage(3, "3.pa", "myNewDir", 8),
    ALinePage(4, "4.pa", "myNewFile", 15),
    ALinePage(5, "5.pa", "myDelDir", 8),
    ALinePage(6, "6.pa", "jpegViewer", 6),
    ALinePage(7, "7.pa", "videoViewer", 9),
    ALinePage(8, "8.pa", "textViewer", 4),
    ALinePage(9, "9.pa", "renameFile", 15),
    ALinePage(10, "10.pa", "wavViewer", 11),
    ALinePage(11, "11.pa", "noSDcardError", 2),
    ALinePage(12, "12.pa", "dataViewer", 16),
    ALinePage(13, "13.pa", "csvViewer", 16),
    ALinePage(14, "14.pa", "keybdB", 28),
    ALinePage(15, "15.pa", "mycsvFile", 14),
    ALinePage(16, "16.pa", "csvAdd", 23),
)

ALINE_MAIN_PAGE_ANCHORS: dict[str, str] = {
    "btnOpenFile": "0x2608",
    "btnRenameFile": "0x29AF",
    "btnDelFile": "0x2A3D",
    "msg": "0x2AF9",
}

ALINE_PAGE_BY_RESOURCE = {page.page_resource: page for page in ALINE_SHARED_WRAPPER_PAGES}
ALINE_PAGE_BY_NAME = {page.page_name.lower(): page for page in ALINE_SHARED_WRAPPER_PAGES}
ALINE_PAGE_BY_RUNTIME_INDEX = {page.runtime_index: page for page in ALINE_SHARED_WRAPPER_PAGES}


def inspect_a_line_pages(hmi_path: Path) -> list[ALinePage]:
    raw = hmi_path.read_bytes()
    inspection = inspect_hmi(hmi_path)
    pages: list[ALinePage] = []
    for entry in inspection.entries:
        if not (entry.in_file and entry.name.lower().endswith(".pa")):
            continue
        page = parse_page_data(raw[entry.data_offset : entry.data_offset + entry.length])
        runtime_index = int(entry.name.split(".", 1)[0])
        pages.append(
            ALinePage(
                runtime_index=runtime_index,
                page_resource=entry.name,
                page_name=str(page.page_name or ""),
                block_count=len(page.blocks),
            )
        )
    pages.sort(key=lambda item: item.runtime_index)
    return pages


def detect_a_line_wrapper_family(hmi_path: Path) -> dict[str, Any]:
    observed = inspect_a_line_pages(hmi_path)
    observed_simple = [(page.runtime_index, page.page_resource, page.page_name) for page in observed]
    expected_simple = [(page.runtime_index, page.page_resource, page.page_name) for page in ALINE_SHARED_WRAPPER_PAGES]
    return {
        "hmi_path": str(hmi_path),
        "matched": observed_simple == expected_simple,
        "observed_pages": [asdict(page) for page in observed],
        "expected_pages": [asdict(page) for page in ALINE_SHARED_WRAPPER_PAGES],
        "main_page_anchors": dict(ALINE_MAIN_PAGE_ANCHORS),
    }


def resolve_a_line_page(page: str | int) -> ALinePage:
    if isinstance(page, int):
        if page not in ALINE_PAGE_BY_RUNTIME_INDEX:
            raise KeyError(page)
        return ALINE_PAGE_BY_RUNTIME_INDEX[page]
    text = str(page).strip()
    if text.lower() in ALINE_PAGE_BY_NAME:
        return ALINE_PAGE_BY_NAME[text.lower()]
    if text in ALINE_PAGE_BY_RESOURCE:
        return ALINE_PAGE_BY_RESOURCE[text]
    if text.isdigit():
        value = int(text)
        if value in ALINE_PAGE_BY_RUNTIME_INDEX:
            return ALINE_PAGE_BY_RUNTIME_INDEX[value]
    raise KeyError(page)


def build_a_line_existing_object_patch_spec(
    *,
    seed_hmi: Path,
    out_dir: Path,
    page: str | int,
    object_name: str,
    field_name: str,
    value: Any,
    force_direct_gui: bool = False,
    prefer_managed_select: bool = False,
) -> dict[str, Any]:
    page_info = resolve_a_line_page(page)
    return {
        "schema_version": AUTOMATION_SCHEMA_VERSION,
        "name": f"a_line_{page_info.page_name}_{object_name}_{field_name}_official_gui_oracle",
        "seed_hmi": str(seed_hmi.resolve()),
        "hmi_path": str((out_dir / "lcd_test.HMI").resolve()),
        "out_dir": str(out_dir.resolve()),
        "actions": [
            {
                "kind": "select-object-gui",
                "page_index": int(page_info.runtime_index),
                "page_resource": page_info.page_resource,
                "object": object_name,
                "force_direct_gui": bool(force_direct_gui),
                "prefer_managed_select": bool(prefer_managed_select),
            },
            {
                "kind": "patch-field-gui",
                "field": field_name,
                "value": value,
            },
            {
                "kind": "save-and-close",
            },
            {
                "kind": "precompile-confirm",
                "pages": [page_info.page_resource],
                "expect_controls": [
                    {
                        "page": page_info.page_resource,
                        "objname": object_name,
                        "field_equals": {field_name: value},
                    }
                ],
            },
            {
                "kind": "compile-capture",
                "open_download_output": True,
                "close": True,
            },
        ],
    }


def build_a_line_existing_object_event_spec(
    *,
    seed_hmi: Path,
    out_dir: Path,
    page: str | int,
    object_name: str,
    event_name: str,
    lines: list[str],
    force_direct_gui: bool = False,
    prefer_managed_select: bool = False,
) -> dict[str, Any]:
    page_info = resolve_a_line_page(page)
    return {
        "schema_version": AUTOMATION_SCHEMA_VERSION,
        "name": f"a_line_{page_info.page_name}_{object_name}_{event_name}_official_gui_oracle",
        "seed_hmi": str(seed_hmi.resolve()),
        "hmi_path": str((out_dir / "lcd_test.HMI").resolve()),
        "out_dir": str(out_dir.resolve()),
        "actions": [
            {
                "kind": "select-object-gui",
                "page_index": int(page_info.runtime_index),
                "page_resource": page_info.page_resource,
                "object": object_name,
                "force_direct_gui": bool(force_direct_gui),
                "prefer_managed_select": bool(prefer_managed_select),
            },
            {
                "kind": "patch-event-gui",
                "event": event_name,
                "lines": list(lines),
            },
            {
                "kind": "save-and-close",
            },
            {
                "kind": "precompile-confirm",
                "pages": [page_info.page_resource],
                "expect_controls": [
                    {
                        "page": page_info.page_resource,
                        "objname": object_name,
                        "event_tokens_contains": list(lines),
                    }
                ],
            },
            {
                "kind": "compile-capture",
                "open_download_output": True,
                "close": True,
            },
        ],
    }
