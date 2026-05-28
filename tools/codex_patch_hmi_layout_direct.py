from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from usarthmi.hmi_inspect import inspect_hmi
from usarthmi.hmi_pagesafe import inspect_page_safe_status, refresh_page_safe_header


PATCHES: dict[str, dict[str, dict[str, int]]] = {
    "0.pa": {
        "t0": {"y": 500},
        "b0": {"y": 500},
        "p0": {"y": 500},
        "alarmtx": {"x": 24, "y": 322, "w": 420, "h": 38},
        "p3btn": {"x": 340, "y": 386, "w": 116, "h": 52},
        "p2btn": {"x": 492, "y": 386, "w": 116, "h": 52},
        "homebtn": {"x": 656, "y": 386, "w": 116, "h": 52},
    },
    "1.pa": {
        "ticker": {"x": 24, "y": 322, "w": 500, "h": 38},
        "trendbtn": {"x": 300, "y": 386, "w": 96, "h": 52},
        "logbtn": {"x": 416, "y": 386, "w": 104, "h": 52},
        "detailbtn": {"x": 544, "y": 386, "w": 104, "h": 52},
        "alarmbtn": {"x": 668, "y": 386, "w": 104, "h": 52},
    },
    "3.pa": {
        "p3bump": {"x": 292, "y": 386, "w": 130, "h": 54},
        "p3alarm": {"x": 448, "y": 386, "w": 136, "h": 54},
        "p3home": {"x": 604, "y": 386, "w": 136, "h": 54},
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch only existing x/y/w/h fields in USART HMI .pa resources.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--macro-spec", type=Path, help="Optional official hook macro JSON; select-page/select-object/patch-field actions are applied directly before layout fixes.")
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.source, args.output)

    raw = bytearray(args.output.read_bytes())
    inspection = inspect_hmi(args.output)
    entries_by_name = {entry.name: entry for entry in inspection.entries}
    patches = _macro_patches(args.macro_spec) if args.macro_spec else {}
    patches = _merge_patches(patches, PATCHES)
    patches = _expand_geometry_end_fields(inspection, patches)
    report: dict[str, Any] = {
        "source": str(args.source.resolve()),
        "output": str(args.output.resolve()),
        "macro_spec": str(args.macro_spec.resolve()) if args.macro_spec else None,
        "patched_pages": {},
        "missing": [],
        "lengths_unchanged": True,
    }

    for page_name, object_patches in patches.items():
        entry = entries_by_name.get(page_name)
        if entry is None or not entry.in_file:
            report["missing"].append({"page": page_name, "reason": "missing page resource"})
            continue

        original = bytes(raw[entry.data_offset : entry.data_offset + entry.length])
        page = next((item for item in inspection.pa_pages if item.entry_name == page_name), None)
        if page is None:
            report["missing"].append({"page": page_name, "reason": "missing page summary"})
            continue
        blocks_by_name = {block.objname: block for block in page.blocks if block.objname}
        page_report: dict[str, Any] = {"objects": {}, "original_length": len(original)}

        for objname, fields in object_patches.items():
            block = blocks_by_name.get(objname)
            if block is None:
                report["missing"].append({"page": page_name, "object": objname, "reason": "missing object"})
                continue

            before: dict[str, int | None] = {}
            after: dict[str, int] = {}
            for field_name, value in fields.items():
                value_range = _field_value_range(original, block.index, field_name)
                if value_range is None:
                    report["missing"].append(
                        {"page": page_name, "object": objname, "field": field_name, "reason": "missing field"}
                    )
                    continue
                value_start, value_end = value_range
                width = value_end - value_start
                if value < 0 or value >= (1 << (8 * width)):
                    raise SystemExit(f"{page_name}.{objname}.{field_name}={value} does not fit in {width} byte(s)")
                before_bytes = raw[entry.data_offset + value_start : entry.data_offset + value_end]
                before[field_name] = int.from_bytes(before_bytes, "little", signed=False) if before_bytes else 0
                raw[entry.data_offset + value_start : entry.data_offset + value_end] = value.to_bytes(width, "little")
                after[field_name] = value

            page_report["objects"][objname] = {
                "before": before,
                "after": after,
                "events": [item.to_dict() for item in block.event_scripts],
            }

        patched_page = bytes(raw[entry.data_offset : entry.data_offset + entry.length])
        before_safe = inspect_page_safe_status(original).to_dict()
        patched_page = refresh_page_safe_header(patched_page)
        raw[entry.data_offset : entry.data_offset + entry.length] = patched_page
        after_safe = inspect_page_safe_status(patched_page).to_dict()

        page_report["patched_length"] = entry.length
        page_report["length_unchanged"] = True
        page_report["page_safe_before"] = before_safe
        page_report["page_safe_after"] = after_safe
        report["patched_pages"][page_name] = page_report

    if report["missing"]:
        raise SystemExit(json.dumps(report, ensure_ascii=False, indent=2))

    args.output.write_bytes(raw)
    report["output_size"] = args.output.stat().st_size
    report["post_inspect"] = _post_inspect(args.output)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def _event_lines(tokens: list[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    cursor = 0
    while cursor < len(tokens):
        header = tokens[cursor]
        cursor += 1
        try:
            count = int(header.rsplit("-", 1)[1])
        except (IndexError, ValueError):
            count = 0
        result[header] = tokens[cursor : cursor + count]
        cursor += count
    return result


def _field_value_range(page_data: bytes, block_index: int, field_name: str) -> tuple[int, int] | None:
    table_offset = 0x38 + block_index * 12
    if table_offset + 8 > len(page_data):
        return None
    rel_offset = int.from_bytes(page_data[table_offset : table_offset + 4], "little")
    block_length = int.from_bytes(page_data[table_offset + 4 : table_offset + 8], "little")
    cursor = 0x38 + rel_offset
    block_end = cursor + block_length
    if cursor + 4 > len(page_data) or block_end > len(page_data):
        return None

    attr_len = int.from_bytes(page_data[cursor : cursor + 4], "little")
    cursor += 4 + attr_len
    while cursor + 4 <= block_end:
        chunk_len = int.from_bytes(page_data[cursor : cursor + 4], "little")
        cursor += 4
        if chunk_len == 0:
            return None
        chunk_start = cursor
        chunk_end = cursor + chunk_len
        if chunk_end > block_end:
            return None
        if chunk_len >= 16:
            raw_name = page_data[chunk_start : chunk_start + 16]
            name = raw_name.split(b"\x00", 1)[0].decode("ascii", errors="ignore")
            if name == field_name:
                return chunk_start + 16, chunk_end
        cursor = chunk_end
    return None


def _macro_patches(path: Path) -> dict[str, dict[str, dict[str, int]]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    result: dict[str, dict[str, dict[str, int]]] = {}
    current_page: str | None = None
    current_object: str | None = None
    for action in data.get("actions", []):
        kind = action.get("kind")
        if kind == "select-page":
            current_page = str(action.get("page_resource") or "")
            current_object = None
        elif kind == "select-object":
            current_object = str(action.get("object") or "")
        elif kind == "patch-field":
            if not current_page or not current_object:
                raise ValueError(f"patch-field without selected page/object in {path}")
            field = str(action["field"])
            value = int(str(action["value"]), 0)
            result.setdefault(current_page, {}).setdefault(current_object, {})[field] = value
    return result


def _merge_patches(
    base: dict[str, dict[str, dict[str, int]]],
    overlay: dict[str, dict[str, dict[str, int]]],
) -> dict[str, dict[str, dict[str, int]]]:
    result = {
        page: {obj: dict(fields) for obj, fields in objects.items()}
        for page, objects in base.items()
    }
    for page, objects in overlay.items():
        for obj, fields in objects.items():
            result.setdefault(page, {}).setdefault(obj, {}).update(fields)
    return result


def _expand_geometry_end_fields(
    inspection: Any,
    patches: dict[str, dict[str, dict[str, int]]],
) -> dict[str, dict[str, dict[str, int]]]:
    pages = {page.entry_name: page for page in inspection.pa_pages}
    result = {
        page: {obj: dict(fields) for obj, fields in objects.items()}
        for page, objects in patches.items()
    }
    for page_name, objects in result.items():
        page = pages.get(page_name)
        if page is None:
            continue
        blocks = {block.objname: block for block in page.blocks if block.objname}
        for objname, fields in objects.items():
            if not any(name in fields for name in ("x", "y", "w", "h")):
                continue
            block = blocks.get(objname)
            if block is None or not all(name in block.fields for name in ("x", "y", "w", "h")):
                continue
            x = int(fields.get("x", block.fields["x"]))
            y = int(fields.get("y", block.fields["y"]))
            w = int(fields.get("w", block.fields["w"]))
            h = int(fields.get("h", block.fields["h"]))
            fields.setdefault("endx", x + w - 1)
            fields.setdefault("endy", y + h - 1)
    return result


def _post_inspect(path: Path) -> dict[str, Any]:
    need = {name for page in PATCHES.values() for name in page}
    inspection = inspect_hmi(path)
    out: dict[str, Any] = {}
    for page in inspection.pa_pages:
        items = []
        for block in page.blocks:
            if block.objname not in need:
                continue
            fields = {
                name: value
                for name, value in block.fields.items()
                if name in {"id", "x", "y", "w", "h", "endx", "endy", "txt"}
            }
            items.append(
                {
                    "index": block.index,
                    "name": block.objname,
                    "type": block.type_code,
                    "fields": fields,
                    "events": [item.to_dict() for item in block.event_scripts],
                }
            )
        if items:
            out[page.entry_name] = items
    return out


if __name__ == "__main__":
    raise SystemExit(main())
