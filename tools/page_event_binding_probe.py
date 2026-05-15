from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from usarthmi.page_format import load_page_file
from usarthmi.tft_patch import (
    _build_event_compile_context,
    _build_object_event_table,
    _build_page_event_table,
    _header,
    _header_int,
    _load_tail_seed,
)
from usarthmi.tft_toolchain import inspect_tft


CALLBACK_SLOT_OFFSETS = {
    "maybe_load_or_down_0x0c": 0x0C,
    "maybe_load_or_up_0x10": 0x10,
    "maybe_timer_0x14": 0x14,
}


def probe_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target_pages = [Path(path) for path in manifest["target_pages"]]
    if len(target_pages) != 2:
        raise SystemExit("This probe currently expects the recovered two-page layout")

    baseline_tft = Path(manifest["baseline_tft"])
    baseline_pa = Path(manifest["baseline_pa"])
    output_tft = Path(manifest["output_tft"])
    page1_pa = target_pages[1]

    seed = _load_tail_seed(baseline_tft, baseline_pa, load_page_file(baseline_pa))
    mirror_value_count = len(seed.mirror_descriptor_sequences[""])
    mirror_record_len = 0x38 + mirror_value_count * 2

    raw = output_tft.read_bytes()
    inspection = inspect_tft(output_tft)
    header2 = _header(inspection, "Header2")
    object_start = _header_int(header2, "unknown_objects_address")
    if object_start is None:
        raise SystemExit("TFT header does not expose unknown_objects_address")
    tail = raw[object_start:]

    section_offsets = {
        key: int(value["value"])
        for key, value in manifest["tft_patch"]["section_offsets"].items()
        if isinstance(value, dict) and "value" in value
    }
    mirror_start = section_offsets["pic"]
    page_count = len(target_pages)
    page1_records_start = mirror_start + 16 * page_count
    page1 = load_page_file(page1_pa)
    context = _build_event_compile_context(page1.blocks)

    blocks: list[dict[str, Any]] = []
    for index, block in enumerate(page1.blocks):
        record_start = page1_records_start + index * mirror_record_len
        record = tail[record_start : record_start + mirror_record_len]
        event_table = (
            _build_page_event_table(block, context=context)
            if index == 0
            else _build_object_event_table(block, context=context)
        )
        event_matches = _all_matches(tail, event_table)
        mirror_event_offset = int.from_bytes(record[0x34:0x38], "little") if len(record) >= 0x38 else None
        callback_slots = {
            name: _slot_value(record, offset)
            for name, offset in CALLBACK_SLOT_OFFSETS.items()
        }
        blocks.append(
            {
                "index": index,
                "objname": block.objname,
                "type_code": _display_type_code(block.type_code),
                "event_tokens": block.event_tokens,
                "event_table_length": len(event_table),
                "event_table_matches": [_offset_item(offset) for offset in event_matches],
                "mirror_record_relative_offset": record_start,
                "mirror_record_relative_offset_hex": f"0x{record_start:X}",
                "mirror_record_header_hex": record[:4].hex(" "),
                "mirror_event_offset_field": _offset_item(mirror_event_offset)
                if mirror_event_offset is not None
                else None,
                "callback_slots": callback_slots,
                "callback_slots_pointing_at_event_table": [
                    name
                    for name, value in callback_slots.items()
                    if isinstance(value.get("value"), int)
                    and _value_points_inside_any_match(value["value"], event_matches, len(event_table))
                ],
            }
        )

    page_block = blocks[0]
    non_empty_page_load = any(
        token.startswith("codesload-") and not token.endswith("-0")
        for token in page_block["event_tokens"]
    )
    page_load_has_callback = bool(page_block["callback_slots_pointing_at_event_table"])
    object_blocks_with_callbacks = [
        block
        for block in blocks[1:]
        if block["callback_slots_pointing_at_event_table"]
    ]

    return {
        "manifest": str(manifest_path),
        "output_tft": str(output_tft),
        "object_start": object_start,
        "object_start_hex": f"0x{object_start:X}",
        "mirror_value_count": mirror_value_count,
        "mirror_record_len": mirror_record_len,
        "mirror_record_len_hex": f"0x{mirror_record_len:X}",
        "section_offsets": {
            name: _offset_item(value)
            for name, value in section_offsets.items()
        },
        "page1": {
            "pa": str(page1_pa),
            "object_count": len(page1.blocks),
            "mirror_records_start": _offset_item(page1_records_start),
            "blocks": blocks,
        },
        "diagnosis": {
            "non_empty_page_load_event": non_empty_page_load,
            "page_event_table_found": bool(page_block["event_table_matches"]),
            "page_mirror_event_offset_points_to_table": any(
                page_block["mirror_event_offset_field"]["value"] == match["value"]
                for match in page_block["event_table_matches"]
            )
            if page_block["mirror_event_offset_field"]
            else False,
            "page_load_callback_slot_points_to_table": page_load_has_callback,
            "object_event_callbacks_found": [
                {
                    "objname": block["objname"],
                    "slots": block["callback_slots_pointing_at_event_table"],
                }
                for block in object_blocks_with_callbacks
            ],
            "interpretation": _interpretation(non_empty_page_load, page_load_has_callback, object_blocks_with_callbacks),
        },
    }


def _interpretation(
    non_empty_page_load: bool,
    page_load_has_callback: bool,
    object_blocks_with_callbacks: list[dict[str, Any]],
) -> str:
    if non_empty_page_load and not page_load_has_callback:
        if object_blocks_with_callbacks:
            return (
                "Page-load bytecode exists and object callbacks are bound, but the page block has no callback slot "
                "pointing at the page event table. This supports the missing page-level scheduler binding hypothesis."
            )
        return (
            "Page-load bytecode exists, but no callback slots point at it. Compare against an official page-load TFT "
            "before guessing a field offset."
        )
    if non_empty_page_load and page_load_has_callback:
        return "The page load table has a callback-like mirror binding; investigate event table placement next."
    return "No non-empty page load script is present in this page."


def _slot_value(record: bytes, offset: int) -> dict[str, Any]:
    if len(record) < offset + 4:
        return {"offset": offset, "offset_hex": f"0x{offset:X}", "value": None}
    value = int.from_bytes(record[offset : offset + 4], "little")
    return {
        "offset": offset,
        "offset_hex": f"0x{offset:X}",
        "value": value,
        "value_hex": f"0x{value:X}",
        "raw_hex": record[offset : offset + 4].hex(" "),
    }


def _offset_item(value: int) -> dict[str, Any]:
    return {"value": value, "hex": f"0x{value:X}"}


def _all_matches(data: bytes, needle: bytes) -> list[int]:
    if not needle:
        return []
    offsets: list[int] = []
    start = 0
    while True:
        found = data.find(needle, start)
        if found < 0:
            return offsets
        offsets.append(found)
        start = found + 1


def _value_points_inside_any_match(value: int, matches: list[int], length: int) -> bool:
    return any(start <= value < start + length for start in matches)


def _display_type_code(type_code: str) -> str:
    return type_code if type_code.isprintable() else f"0x{ord(type_code):02X}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe page1 page/event mirror callback bindings from a scene-build manifest."
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = probe_manifest(args.manifest.resolve())
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
