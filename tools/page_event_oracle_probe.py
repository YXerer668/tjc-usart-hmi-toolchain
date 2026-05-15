from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from usarthmi.hmi_inspect import _parse_entries
from usarthmi.event_bytecode import decode_event_table
from usarthmi.page_format import PageBlock, parse_page_data
from usarthmi.tft_patch import (
    _build_event_compile_context,
    _build_object_event_table,
    _build_page_event_table,
    _build_post_primary_page_event,
    _header,
    _header_int,
)
from usarthmi.tft_toolchain import inspect_tft


CALLBACK_SLOT_OFFSETS = {
    "slot_0x0c": 0x0C,
    "slot_0x10": 0x10,
    "slot_0x14": 0x14,
    "event_offset_0x34": 0x34,
}


def probe_hmi_tft(
    hmi_path: Path,
    tft_path: Path,
    *,
    force_post_primary_page_load: bool = False,
) -> dict[str, Any]:
    try:
        page = parse_page_data(_hmi_resource(hmi_path, "0.pa"))
    except ValueError as exc:
        raise SystemExit(f"Unable to parse 0.pa from {hmi_path}: {exc}") from exc
    context = _build_event_compile_context(page.blocks)
    tft_raw = tft_path.read_bytes()
    tft = inspect_tft(tft_path)
    header2 = _header(tft, "Header2")
    object_start = _header_int(header2, "unknown_objects_address")
    if object_start is None:
        raise SystemExit("TFT Header2 does not expose unknown_objects_address")
    object_region = tft_raw[object_start:]
    post_primary_page_event = _build_post_primary_page_event(
        page.blocks,
        context=context,
        force=force_post_primary_page_load,
    )
    post_primary_matches = _all_matches(object_region, post_primary_page_event)

    block_reports = []
    for index, block in enumerate(page.blocks):
        event_table = (
            _build_page_event_table(block, context=context)
            if index == 0
            else _build_object_event_table(block, context=context)
        )
        event_matches = _all_matches(object_region, event_table)
        first_executable = _first_executable_offset(event_table)
        reference_targets = _reference_targets(event_matches, len(event_table), first_executable)
        record_candidates = _record_candidates(object_region, block, reference_targets)
        block_reports.append(
            {
                "index": index,
                "objname": block.objname,
                "type_code": _display_type_code(block.type_code),
                "id": _block_id(block),
                "event_tokens": block.event_tokens,
                "event_table_length": len(event_table),
                "event_table_hex_prefix": event_table[:64].hex(" "),
                "event_table_items": decode_event_table(event_table),
                "event_table_matches": [_offset_item(value) for value in event_matches],
                "first_non_empty_item_offset_in_table": first_executable,
                "first_non_empty_item_offset_in_table_hex": f"0x{first_executable:X}" if first_executable is not None else None,
                "reference_targets": [
                    {
                        "name": item["name"],
                        "value": item["value"],
                        "value_hex": f"0x{item['value']:X}",
                        "references": [_offset_item(value) for value in _all_u32_references(object_region, item["value"])],
                    }
                    for item in reference_targets
                ],
                "record_candidates": record_candidates,
            }
        )

    return {
        "hmi": str(hmi_path.resolve()),
        "tft": str(tft_path.resolve()),
        "editor_version": tft["editor_version"],
        "model": tft["model"],
        "object_start": object_start,
        "object_start_hex": f"0x{object_start:X}",
        "object_region_length": len(object_region),
        "object_region_length_hex": f"0x{len(object_region):X}",
        "page_name": page.page_name,
        "object_count": len(page.blocks),
        "post_primary_page_event": {
            "force_post_primary_page_load": force_post_primary_page_load,
            "length": len(post_primary_page_event),
            "hex_prefix": post_primary_page_event[:64].hex(" "),
            "items": decode_event_table(post_primary_page_event),
            "matches": [_offset_item(value) for value in post_primary_matches],
            "reference_targets": [
                {
                    "name": "post_primary_page_event_start",
                    "value": value,
                    "value_hex": f"0x{value:X}",
                    "references": [_offset_item(ref) for ref in _all_u32_references(object_region, value)],
                }
                for value in post_primary_matches
            ],
        },
        "blocks": block_reports,
        "diagnosis": _diagnose(block_reports, post_primary_matches=post_primary_matches),
    }


def _hmi_resource(path: Path, name: str) -> bytes:
    raw = path.read_bytes()
    if len(raw) < 4:
        raise SystemExit(f"HMI too small: {path}")
    entry_count = int.from_bytes(raw[:4], "little")
    for entry in _parse_entries(raw, entry_count):
        if entry.name == name and entry.in_file:
            return raw[entry.data_offset : entry.data_offset + entry.length]
    raise SystemExit(f"HMI resource {name!r} not found in {path}")


def _record_candidates(region: bytes, block: PageBlock, targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    block_id = _block_id(block)
    if block.type_code is None or block_id is None:
        return []
    header = block.type_code.encode("latin1") + int(block_id).to_bytes(1, "little") + b"\x00\x37"
    offsets = _all_matches(region, header)
    target_values = {item["value"] for item in targets}
    candidates = []
    for offset in offsets:
        record = region[offset : offset + 0x60]
        slots = {}
        for name, slot_offset in CALLBACK_SLOT_OFFSETS.items():
            if len(record) < slot_offset + 4:
                continue
            value = int.from_bytes(record[slot_offset : slot_offset + 4], "little")
            slots[name] = {
                "offset": slot_offset,
                "offset_hex": f"0x{slot_offset:X}",
                "value": value,
                "value_hex": f"0x{value:X}",
                "raw_hex": record[slot_offset : slot_offset + 4].hex(" "),
                "points_to_event_target": value in target_values,
            }
        candidates.append(
            {
                "relative_offset": offset,
                "relative_offset_hex": f"0x{offset:X}",
                "header_hex": header.hex(" "),
                "slots": slots,
            }
        )
    return candidates


def _reference_targets(
    matches: list[int],
    event_table_length: int,
    first_executable: int | None,
) -> list[dict[str, Any]]:
    targets = []
    for match in matches:
        targets.append({"name": "event_table_start", "value": match})
        if first_executable is not None and first_executable < event_table_length:
            targets.append({"name": "first_executable", "value": match + first_executable})
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for item in targets:
        key = (item["name"], item["value"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def _first_executable_offset(event_table: bytes) -> int | None:
    cursor = 0
    while cursor + 4 <= len(event_table):
        length = int.from_bytes(event_table[cursor : cursor + 4], "little")
        payload_start = cursor + 4
        payload_end = payload_start + length
        if payload_end > len(event_table):
            return None
        payload = event_table[payload_start:payload_end]
        if payload.startswith(b"\x09") or payload.startswith(b"\x01") or payload.startswith(b"\x04"):
            return cursor
        cursor = payload_end
    return None


def _all_matches(data: bytes, needle: bytes) -> list[int]:
    if not needle:
        return []
    offsets = []
    start = 0
    while True:
        found = data.find(needle, start)
        if found < 0:
            return offsets
        offsets.append(found)
        start = found + 1


def _all_u32_references(data: bytes, value: int) -> list[int]:
    if value < 0 or value > 0xFFFFFFFF:
        return []
    return _all_matches(data, value.to_bytes(4, "little"))


def _offset_item(value: int) -> dict[str, Any]:
    return {"value": value, "hex": f"0x{value:X}"}


def _display_type_code(type_code: str | None) -> str | None:
    if type_code is None:
        return None
    return type_code if type_code.isprintable() else f"0x{ord(type_code):02X}"


def _block_id(block: PageBlock) -> int | None:
    field = block.get_field("id")
    if field is None or not field.value:
        return None
    return int.from_bytes(field.value, "little")


def _is_callback_slot(name: str) -> bool:
    return name.startswith("slot_")


def _diagnose(block_reports: list[dict[str, Any]], *, post_primary_matches: list[int]) -> dict[str, Any]:
    page = block_reports[0] if block_reports else None
    page_load_non_empty = False
    if page:
        page_load_non_empty = any(
            token.startswith("codesload-") and not token.endswith("-0")
            for token in page["event_tokens"]
        )
    page_callbacks = _slot_refs(block_reports[:1], callback_slots_only=True)
    object_callbacks = _slot_refs(block_reports[1:], callback_slots_only=True)
    page_event_offsets = _slot_refs(block_reports[:1], names={"event_offset_0x34"})
    object_event_offsets = _slot_refs(block_reports[1:], names={"event_offset_0x34"})
    scheduler_path = _scheduler_path(
        page_load_non_empty=page_load_non_empty,
        page_event_table_found=bool(page and page["event_table_matches"]),
        post_primary_page_event_found=bool(post_primary_matches),
        page_callbacks=page_callbacks,
        object_callbacks=object_callbacks,
        page_event_offsets=page_event_offsets,
    )
    return {
        "page_load_non_empty": page_load_non_empty,
        "page_event_table_found": bool(page and page["event_table_matches"]),
        "post_primary_page_event_found": bool(post_primary_matches),
        "page_callback_like_slots": page_callbacks,
        "object_callback_like_slots": object_callbacks,
        "page_event_offset_0x34_refs": page_event_offsets,
        "object_event_offset_0x34_refs": object_event_offsets,
        "scheduler_path": scheduler_path,
        "upload_risk": _upload_risk(scheduler_path),
        "recommended_writer_action": _recommended_writer_action(scheduler_path),
        "interpretation": _interpretation(
            page_load_non_empty=page_load_non_empty,
            page_event_table_found=bool(page and page["event_table_matches"]),
            post_primary_page_event_found=bool(post_primary_matches),
            page_callbacks=page_callbacks,
            object_callbacks=object_callbacks,
            page_event_offsets=page_event_offsets,
        ),
    }


def _slot_refs(
    block_reports: list[dict[str, Any]],
    *,
    names: set[str] | None = None,
    callback_slots_only: bool = False,
) -> list[dict[str, Any]]:
    refs = []
    for block in block_reports:
        for candidate in block["record_candidates"]:
            slots = [
                name
                for name, slot in candidate["slots"].items()
                if slot.get("points_to_event_target")
                and (names is None or name in names)
                and (not callback_slots_only or _is_callback_slot(name))
            ]
            if slots:
                item = {
                    "record_offset_hex": candidate["relative_offset_hex"],
                    "slots": slots,
                }
                if block.get("objname") is not None:
                    item["objname"] = block["objname"]
                refs.append(item)
    return refs


def _scheduler_path(
    *,
    page_load_non_empty: bool,
    page_event_table_found: bool,
    post_primary_page_event_found: bool,
    page_callbacks: list[dict[str, Any]],
    object_callbacks: list[dict[str, Any]],
    page_event_offsets: list[dict[str, Any]],
) -> str:
    if page_load_non_empty and post_primary_page_event_found:
        return "post_primary_page_event"
    if page_load_non_empty and page_event_table_found and page_event_offsets and not page_callbacks:
        return "normal_page_table_without_page_callback"
    if page_load_non_empty and page_callbacks:
        return "normal_page_table_with_page_callback"
    if object_callbacks:
        return "object_callbacks_only"
    return "unbound_or_empty"


def _upload_risk(scheduler_path: str) -> str:
    return {
        "post_primary_page_event": "research_only",
        "normal_page_table_without_page_callback": "high",
        "normal_page_table_with_page_callback": "medium",
        "object_callbacks_only": "low_for_object_events_only",
        "unbound_or_empty": "unknown",
    }.get(scheduler_path, "unknown")


def _recommended_writer_action(scheduler_path: str) -> str:
    if scheduler_path == "post_primary_page_event":
        return (
            "Keep page-load generation fixture-gated: official media-style TFTs relocate page-load bytecode "
            "into a post-primary chunk, so do not burn an ad-hoc page-load build until this chunk is reproduced "
            "byte-for-byte for the target layout."
        )
    if scheduler_path == "normal_page_table_without_page_callback":
        return (
            "Do not burn callback-slot guesses. The normal page event table exists, but no recovered page-level "
            "callback cache points at executable code; compare against an official page-load oracle first."
        )
    if scheduler_path == "normal_page_table_with_page_callback":
        return "Inspect the referenced descriptor and then validate on hardware with a minimal recovery TFT ready."
    if scheduler_path == "object_callbacks_only":
        return "Continue object-event bytecode work; this fixture does not prove page-load scheduling."
    return "Collect a smaller official oracle before adding writer behavior."


def _interpretation(
    *,
    page_load_non_empty: bool,
    page_event_table_found: bool,
    post_primary_page_event_found: bool,
    page_callbacks: list[dict[str, Any]],
    object_callbacks: list[dict[str, Any]],
    page_event_offsets: list[dict[str, Any]],
) -> str:
    if page_load_non_empty and post_primary_page_event_found:
        return (
            "Official-style media page-load bytecode is present after the primary records. "
            "Do not expect the normal page event table search alone to find codesload."
        )
    if page_load_non_empty and page_event_table_found and page_event_offsets and not page_callbacks:
        return (
            "Page-load bytecode is present and the mirror event_offset_0x34 points to the page event table, "
            "but no recovered callback-cache slot points to the executable item. The page-load scheduler path "
            "is still separate from object click/timer callback caches."
        )
    if page_load_non_empty and not page_callbacks and object_callbacks:
        return (
            "Page-load bytecode is present and object callbacks are visible, "
            "but no page callback-like slot points to the page event table. "
            "Compare against an official page-load oracle."
        )
    if page_load_non_empty and page_callbacks:
        return "A page callback-like reference exists; inspect the referenced descriptor and live behavior."
    if object_callbacks:
        return "Object event callback-like references are visible; page load is empty or not the target of this fixture."
    return "No callback-like references were found by this narrow probe."


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe page/object event table references in an HMI/TFT oracle pair."
    )
    parser.add_argument("--hmi", required=True, type=Path)
    parser.add_argument("--tft", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--force-post-primary-page-load",
        action="store_true",
        help="Also search the experimental post-primary page-load chunk for non-media pages.",
    )
    args = parser.parse_args()

    report = probe_hmi_tft(
        args.hmi.resolve(),
        args.tft.resolve(),
        force_post_primary_page_load=args.force_post_primary_page_load,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
