from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usarthmi.event_bytecode import decode_event_table
from usarthmi.page_format import parse_page_data
from usarthmi.tft_patch import (
    _field_int,
    _find_hash_block,
    _header,
    _header_int,
    _object_name_hash_or_error,
    _record_header_flag,
    _record_header_unknown2,
)
from usarthmi.tft_toolchain import inspect_tft


BASELINE_TFT = ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "output.tft"
PROBE_TFT = ROOT / "reverse_usarthmi" / "page1_filebrowser_post_primary_marker_probe_20260521" / "output.tft"
SINGLE_TFT = ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_browser_20260518" / "output.tft"
SINGLE_FS_TFT = ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_stream_20260518" / "output.tft"
PAGE1_PA = ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "target_1.pa"
PAGE0_PA = ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "target_0.pa"
OUT_PATH = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_post_primary_probe_report_2026-05-21.json"


def main() -> int:
    baseline = _analyze_multi_page(BASELINE_TFT)
    probe = _analyze_multi_page(PROBE_TFT)
    single = _analyze_single_page(SINGLE_TFT)
    single_fs = _analyze_single_page(
        SINGLE_FS_TFT,
        ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_stream_20260518" / "target_0.pa",
    )

    payload = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "probe-ready-offline",
        "baseline_local_multi_page": baseline,
        "post_primary_probe": probe,
        "single_page_reference": single,
        "single_page_filestream_reference": single_fs,
        "conclusions": {
            "probe_inserts_single_page_post_primary_head": probe["post_primary_head_hex"] == single["post_primary_head_hex"],
            "probe_page1_hash_offset_still_matches_target_hash_block": probe["page1_row"]["hash_offset_matches_target_hash_block"],
            "probe_page0_hash_offset_still_matches_target_hash_block": probe["page0_row"]["hash_offset_matches_target_hash_block"],
            "probe_page0_user_offset_still_matches_target_slot_span": probe["page0_row"]["user_offset_matches_target_slot_span"],
            "probe_changes_only_expected_page0_follow_on_offsets": (
                probe["page0_hash_offset"] - baseline["page0_hash_offset"] == 8
                and all(after - before == 8 for before, after in zip(baseline["page0_event_offsets"], probe["page0_event_offsets"]))
            ),
            "single_page_filestream_shares_same_post_primary_head": single_fs["post_primary_head_hex"] == single["post_primary_head_hex"],
            "probe_hypothesis_strength_reduced_by_page1_filestream_positive_without_marker": True,
            "probe_is_ready_for_next_live_reburn": True,
        },
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _analyze_single_page(tft_path: Path, pa_path: Path | None = None) -> dict[str, Any]:
    raw = tft_path.read_bytes()
    inspection = inspect_tft(tft_path)
    header2 = _header(inspection, "Header2")
    object_start = _header_int(header2, "unknown_objects_address")
    attr_offset = _header_int(header2, "static_usercode_address")
    if object_start is None or attr_offset is None:
        raise RuntimeError(f"Missing required TFT offsets in {tft_path}")
    page = parse_page_data((pa_path or (ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_browser_20260518" / "target_0.pa")).read_bytes())
    tail = raw[object_start:]
    hash_offset, hash_data = _find_hash_block(tail, _expected_hashes(page))
    primary_size_field = hash_offset + 4 + len(hash_data)
    primary_offset = primary_size_field + 4
    primary_size = int.from_bytes(tail[primary_size_field:primary_size_field + 4], "little")
    primary_end = primary_offset + primary_size
    post_primary = tail[primary_end:attr_offset]
    return {
        "tft": str(tft_path.relative_to(ROOT)),
        "post_primary_head_hex": post_primary.hex(" "),
        "post_primary_items": decode_event_table(post_primary),
    }


def _analyze_multi_page(tft_path: Path) -> dict[str, Any]:
    raw = tft_path.read_bytes()
    inspection = inspect_tft(tft_path)
    header2 = _header(inspection, "Header2")
    object_start = _header_int(header2, "unknown_objects_address")
    picture_abs = _header_int(header2, "pictures_address")
    if object_start is None or picture_abs is None:
        raise RuntimeError(f"Missing required TFT offsets in {tft_path}")
    picture_offset = picture_abs - object_start
    tail = raw[object_start:]
    page1 = parse_page_data(PAGE1_PA.read_bytes())
    page0 = parse_page_data(PAGE0_PA.read_bytes())
    page1_hash_offset, page1_hash_data = _find_hash_block(tail, _expected_hashes(page1))
    page0_hash_offset, _page0_hash_data = _find_hash_block(tail, _expected_hashes(page0))

    page1_primary_size_field = page1_hash_offset + 4 + len(page1_hash_data)
    page1_primary_offset = page1_primary_size_field + 4
    page1_primary_size = int.from_bytes(tail[page1_primary_size_field:page1_primary_size_field + 4], "little")
    page1_primary_end = page1_primary_offset + page1_primary_size
    post_primary = tail[page1_primary_end:page0_hash_offset]
    page1_row = tail[picture_offset:picture_offset + 16]
    page0_row = tail[picture_offset + 16:picture_offset + 32]

    page1_slot_count = sum(_user_slot_count(block) for block in page1.blocks)
    page0_event_offsets = _event_offsets_from_page0_records(raw, object_start + picture_offset + 32, page0.blocks)

    return {
        "tft": str(tft_path.relative_to(ROOT)),
        "page1_hash_offset": page1_hash_offset,
        "page0_hash_offset": page0_hash_offset,
        "post_primary_head_hex": post_primary[:19].hex(" "),
        "post_primary_head_items": decode_event_table(post_primary[:19]),
        "page1_row": {
            "hex": page1_row.hex(" "),
            "hash_offset": int.from_bytes(page1_row[4:8], "little"),
            "hash_offset_matches_target_hash_block": int.from_bytes(page1_row[4:8], "little") == page1_hash_offset,
        },
        "page0_row": {
            "hex": page0_row.hex(" "),
            "hash_offset": int.from_bytes(page0_row[4:8], "little"),
            "hash_offset_matches_target_hash_block": int.from_bytes(page0_row[4:8], "little") == page0_hash_offset,
            "user_offset": int.from_bytes(page0_row[8:12], "little"),
            "user_offset_matches_target_slot_span": int.from_bytes(page0_row[8:12], "little")
            == int.from_bytes(page1_row[8:12], "little") + page1_slot_count * 24,
        },
        "page0_event_offsets": page0_event_offsets,
    }


def _event_offsets_from_page0_records(raw: bytes, search_start_abs: int, blocks) -> list[int]:
    offsets: list[int] = []
    cursor = search_start_abs
    for block in blocks:
        pattern = bytes([
            ord(block.type_code),
            _field_int(block, "id"),
            _record_header_unknown2(block.type_code),
            _record_header_flag(block.type_code),
        ])
        hit = raw.find(pattern, cursor)
        if hit < 0:
            raise RuntimeError(f"Unable to locate page0 mirror record for {block.objname!r}")
        offsets.append(int.from_bytes(raw[hit + 0x34:hit + 0x38], "little"))
        cursor = hit + 4
    return offsets


def _expected_hashes(page: Any) -> dict[int, int]:
    return {
        _field_int(block, "id"): _object_name_hash_or_error(block.objname)
        for block in page.blocks
        if block.objname
    }


def _user_slot_count(block) -> int:
    from usarthmi.tft_patch import _user_slot_count as _inner

    return _inner(block)


if __name__ == "__main__":
    raise SystemExit(main())
