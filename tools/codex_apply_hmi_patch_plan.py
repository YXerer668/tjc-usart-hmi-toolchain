from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from usarthmi.hmi_inspect import inspect_hmi  # noqa: E402
from usarthmi.hmi_pagesafe import inspect_page_safe_status, refresh_page_safe_header  # noqa: E402


ALLOWED_FIELDS = {"x", "y", "w", "h", "endx", "endy", "bco", "pco", "pic", "picc", "font", "sta"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply an HMI patch-plan JSON to existing .pa fields only.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--allow-field", action="append", default=[], help="Extra field name allowed for patching.")
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.source, args.output)

    allowed = set(ALLOWED_FIELDS) | {str(item) for item in args.allow_field}
    plan_payload = json.loads(args.plan.read_text(encoding="utf-8-sig"))
    raw_patches = plan_payload.get("patches")
    if not isinstance(raw_patches, dict):
        raise SystemExit("patch plan must contain an object at key 'patches'")

    raw = bytearray(args.output.read_bytes())
    source_inspection = inspect_hmi(args.source)
    inspection = inspect_hmi(args.output)
    entries_by_name = {entry.name: entry for entry in inspection.entries}
    page_by_name = {page.entry_name: page for page in inspection.pa_pages}

    report: dict[str, Any] = {
        "source": str(args.source.resolve()),
        "plan": str(args.plan.resolve()),
        "output": str(args.output.resolve()),
        "allowed_fields": sorted(allowed),
        "patched_pages": {},
        "missing": [],
        "rejected": [],
        "lengths_unchanged": True,
    }

    patches = expand_geometry_end_fields(inspection, raw_patches)

    for page_name, object_patches_raw in patches.items():
        if not isinstance(object_patches_raw, dict):
            report["rejected"].append({"page": page_name, "reason": "page patch is not an object"})
            continue
        entry = entries_by_name.get(str(page_name))
        page = page_by_name.get(str(page_name))
        if entry is None or not entry.in_file:
            report["missing"].append({"page": page_name, "reason": "missing page resource"})
            continue
        if page is None:
            report["missing"].append({"page": page_name, "reason": "missing page summary"})
            continue

        original = bytes(raw[entry.data_offset : entry.data_offset + entry.length])
        page_report: dict[str, Any] = {"objects": {}, "original_length": len(original)}
        blocks_by_name = {block.objname: block for block in page.blocks if block.objname}

        for objname, fields_raw in object_patches_raw.items():
            if not isinstance(fields_raw, dict):
                report["rejected"].append({"page": page_name, "object": objname, "reason": "object patch is not an object"})
                continue
            block = blocks_by_name.get(str(objname))
            if block is None:
                report["missing"].append({"page": page_name, "object": objname, "reason": "missing object"})
                continue

            before: dict[str, int] = {}
            after: dict[str, int] = {}
            for field_name_raw, value_raw in fields_raw.items():
                field_name = str(field_name_raw)
                if field_name not in allowed:
                    report["rejected"].append(
                        {"page": page_name, "object": objname, "field": field_name, "reason": "field is not allowed"}
                    )
                    continue
                value = int(value_raw)
                value_range = field_value_range(original, block.index, field_name)
                if value_range is None:
                    report["missing"].append(
                        {"page": page_name, "object": objname, "field": field_name, "reason": "missing field"}
                    )
                    continue
                value_start, value_end = value_range
                width = value_end - value_start
                if value < 0 or value >= (1 << (8 * width)):
                    report["rejected"].append(
                        {
                            "page": page_name,
                            "object": objname,
                            "field": field_name,
                            "value": value,
                            "reason": f"value does not fit in {width} byte(s)",
                        }
                    )
                    continue
                before_bytes = raw[entry.data_offset + value_start : entry.data_offset + value_end]
                before[field_name] = int.from_bytes(before_bytes, "little", signed=False) if before_bytes else 0
                raw[entry.data_offset + value_start : entry.data_offset + value_end] = value.to_bytes(width, "little")
                after[field_name] = value

            if before or after:
                page_report["objects"][str(objname)] = {
                    "index": block.index,
                    "type": block.type_code,
                    "before": before,
                    "after": after,
                    "event_scripts": [item.to_dict() for item in block.event_scripts],
                }

        patched_page = bytes(raw[entry.data_offset : entry.data_offset + entry.length])
        page_report["page_safe_before"] = inspect_page_safe_status(original).to_dict()
        patched_page = refresh_page_safe_header(patched_page)
        raw[entry.data_offset : entry.data_offset + entry.length] = patched_page
        page_report["page_safe_after"] = inspect_page_safe_status(patched_page).to_dict()
        page_report["patched_length"] = entry.length
        page_report["length_unchanged"] = len(patched_page) == len(original)
        if not page_report["length_unchanged"]:
            report["lengths_unchanged"] = False
        report["patched_pages"][str(page_name)] = page_report

    if report["missing"] or report["rejected"]:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise SystemExit(json.dumps(report, ensure_ascii=False, indent=2))

    args.output.write_bytes(raw)
    output_inspection = inspect_hmi(args.output)
    report["output_size"] = args.output.stat().st_size
    report["field_verification"] = verify_fields(output_inspection, patches)
    report["event_preservation"] = compare_events(source_inspection, output_inspection)
    report["status"] = (
        "ok"
        if report["lengths_unchanged"]
        and not report["field_verification"]["mismatches"]
        and report["event_preservation"]["changed_event_objects"] == 0
        else "failed"
    )
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "ok" else 2


def field_value_range(page_data: bytes, block_index: int, field_name: str) -> tuple[int, int] | None:
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


def expand_geometry_end_fields(inspection: Any, patches: dict[str, Any]) -> dict[str, Any]:
    pages = {page.entry_name: page for page in inspection.pa_pages}
    expanded: dict[str, Any] = {}
    for page_name, object_patches_raw in patches.items():
        if not isinstance(object_patches_raw, dict):
            expanded[page_name] = object_patches_raw
            continue
        page = pages.get(str(page_name))
        blocks = {block.objname: block for block in page.blocks if block.objname} if page is not None else {}
        expanded_objects: dict[str, Any] = {}
        for objname, fields_raw in object_patches_raw.items():
            if not isinstance(fields_raw, dict):
                expanded_objects[objname] = fields_raw
                continue
            fields = dict(fields_raw)
            if any(name in fields for name in ("x", "y", "w", "h")):
                block = blocks.get(str(objname))
                if block is not None and all(name in block.fields for name in ("x", "y", "w", "h")):
                    x = int(fields.get("x", block.fields["x"]))
                    y = int(fields.get("y", block.fields["y"]))
                    w = int(fields.get("w", block.fields["w"]))
                    h = int(fields.get("h", block.fields["h"]))
                    fields.setdefault("endx", x + w - 1)
                    fields.setdefault("endy", y + h - 1)
            expanded_objects[objname] = fields
        expanded[page_name] = expanded_objects
    return expanded


def verify_fields(inspection: Any, patches: dict[str, Any]) -> dict[str, Any]:
    pages = {page.entry_name: page for page in inspection.pa_pages}
    verified: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    for page_name, object_patches in patches.items():
        page = pages.get(str(page_name))
        if page is None:
            mismatches.append({"page": page_name, "reason": "missing page after patch"})
            continue
        blocks = {block.objname: block for block in page.blocks if block.objname}
        for objname, fields in object_patches.items():
            block = blocks.get(str(objname))
            if block is None:
                mismatches.append({"page": page_name, "object": objname, "reason": "missing object after patch"})
                continue
            for field_name, expected_raw in fields.items():
                if field_name not in ALLOWED_FIELDS:
                    continue
                expected = int(expected_raw)
                actual = block.fields.get(str(field_name))
                item = {"page": page_name, "object": objname, "field": field_name, "expected": expected, "actual": actual}
                if actual != expected:
                    mismatches.append(item)
                else:
                    verified.append(item)
    return {"verified_count": len(verified), "mismatches": mismatches}


def compare_events(source: Any, output: Any) -> dict[str, Any]:
    source_events = event_map(source)
    output_events = event_map(output)
    changed = []
    for key in sorted(set(source_events) | set(output_events)):
        if source_events.get(key) != output_events.get(key):
            changed.append({"key": key, "source": source_events.get(key), "output": output_events.get(key)})
    return {
        "source_event_objects": sum(1 for value in source_events.values() if value),
        "output_event_objects": sum(1 for value in output_events.values() if value),
        "changed_event_objects": len(changed),
        "changes": changed,
    }


def event_map(inspection: Any) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for page in inspection.pa_pages:
        for block in page.blocks:
            name = block.objname or block.attr_name or f"block{block.index}"
            result[f"{page.entry_name}:{name}:{block.index}"] = [item.to_dict() for item in block.event_scripts]
    return result


if __name__ == "__main__":
    raise SystemExit(main())
