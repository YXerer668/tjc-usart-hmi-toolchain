from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usarthmi.page_format import parse_page_data
from usarthmi.tft_patch import (
    _field_int,
    _find_hash_block,
    _header,
    _header_int,
    _object_name_hash_or_error,
    _record_header_flag,
    _record_header_unknown2,
    _user_slot_count,
)
from usarthmi.tft_toolchain import inspect_tft


OUT_PATH = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_pointer_closure_report_2026-05-21.json"


@dataclass(frozen=True)
class CaseSpec:
    name: str
    kind: str
    tft: Path
    target_page: Path
    page0_page: Path | None = None


CASES = [
    CaseSpec(
        name="single_page_filebrowser_working",
        kind="single-page-working",
        tft=ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_browser_20260518" / "output.tft",
        target_page=ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_browser_20260518" / "target_0.pa",
    ),
    CaseSpec(
        name="page1_filebrowser_local_multipt",
        kind="multi-page-failing",
        tft=ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "output.tft",
        target_page=ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "target_1.pa",
        page0_page=ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "target_0.pa",
    ),
    CaseSpec(
        name="page1_filestream_local_multipt",
        kind="multi-page-working",
        tft=ROOT / "reverse_usarthmi" / "page1_filestream_local_multipt_probe_20260521" / "output.tft",
        target_page=ROOT / "reverse_usarthmi" / "page1_filestream_local_multipt_probe_20260521" / "target_1.pa",
        page0_page=ROOT / "reverse_usarthmi" / "page1_filestream_local_multipt_probe_20260521" / "target_0.pa",
    ),
    CaseSpec(
        name="page1_textselect_local_multipt",
        kind="multi-page-working",
        tft=ROOT / "reverse_usarthmi" / "page1_textselect_local_multipt_probe_20260521" / "output.tft",
        target_page=ROOT / "reverse_usarthmi" / "page1_textselect_local_multipt_probe_20260521" / "target_1.pa",
        page0_page=ROOT / "reverse_usarthmi" / "page1_textselect_local_multipt_probe_20260521" / "target_0.pa",
    ),
]


def main() -> int:
    payload = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "page-pointer-closure-compared",
        "cases": {spec.name: _analyze_case(spec) for spec in CASES},
    }
    payload["comparisons"] = _build_comparisons(payload["cases"])
    payload["conclusions"] = _build_conclusions(payload["cases"], payload["comparisons"])
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _analyze_case(spec: CaseSpec) -> dict[str, Any]:
    raw = spec.tft.read_bytes()
    inspection = inspect_tft(spec.tft)
    header2 = _header(inspection, "Header2")
    object_start = _header_int(header2, "unknown_objects_address")
    picture_abs = _header_int(header2, "pictures_address")
    attr_rel = _header_int(header2, "static_usercode_address")
    user_rel = _header_int(header2, "usercode_address")
    if None in {object_start, picture_abs, attr_rel, user_rel}:
        raise RuntimeError(f"Unable to inspect required TFT offsets for {spec.tft}")
    assert object_start is not None
    assert picture_abs is not None
    assert attr_rel is not None
    assert user_rel is not None
    tail = raw[object_start:]
    picture_rel = picture_abs - object_start

    target_page = parse_page_data(spec.target_page.read_bytes())
    target_hash_offset, target_hash_data = _find_hash_block(tail, _expected_hashes(target_page))
    target_primary_size_field = target_hash_offset + 4 + len(target_hash_data)
    target_primary_offset = target_primary_size_field + 4
    target_primary_size = int.from_bytes(tail[target_primary_size_field:target_primary_size_field + 4], "little")

    page_header_rows = _decode_page_header_rows(tail, picture_rel, single_page=(spec.page0_page is None))
    target_row = page_header_rows[0]
    target_slot_count = sum(_user_slot_count(block) for block in target_page.blocks)
    target_record_offsets = _mirror_record_offsets(
        raw,
        search_start_abs=object_start + picture_rel + (16 if spec.page0_page is None else 32),
        blocks=target_page.blocks,
    )
    target_event_offsets = [int.from_bytes(raw[offset + 0x34:offset + 0x38], "little") for offset in target_record_offsets]
    target_user_record_first24 = tail[target_row["user_offset"]:target_row["user_offset"] + 24]

    result: dict[str, Any] = {
        "kind": spec.kind,
        "tft": _rel(spec.tft),
        "target_page": _rel(spec.target_page),
        "page_blocks": [[block.objname, block.type_code] for block in target_page.blocks],
        "object_start_hex": hex(object_start),
        "section_layout": {
            "picture_offset": picture_rel,
            "attr_header_offset": attr_rel,
            "user_header_offset": user_rel,
            "target_hash_offset": target_hash_offset,
            "target_hash_size": len(target_hash_data),
            "target_primary_size_field_offset": target_primary_size_field,
            "target_primary_offset": target_primary_offset,
            "target_primary_size": target_primary_size,
            "target_event_region_start": target_event_offsets[0],
            "target_event_region_end": target_hash_offset,
        },
        "mirror_page_header_rows": page_header_rows,
        "target_page_row": {
            **target_row,
            "block_count_matches_target_page": target_row["block_count"] == len(target_page.blocks),
            "hash_offset_matches_target_hash_block": target_row["hash_offset"] == target_hash_offset,
            "user_offset_points_to_nonzero_user_record": target_user_record_first24 != b"\x00" * 24,
            "primary_pre_string_len_within_primary_size": target_row["primary_pre_string_len"] <= target_primary_size,
            "slot_count": target_slot_count,
            "first_user_record_first_24_hex": target_user_record_first24.hex(" "),
        },
        "target_mirror_records": [
            {
                "objname": block.objname,
                "type_code": block.type_code,
                "record_offset_hex": hex(offset),
                "event_offset": event_offset,
                "event_offset_hex": hex(event_offset),
                "event_offset_before_hash_block": event_offset < target_hash_offset,
            }
            for block, offset, event_offset in zip(target_page.blocks, target_record_offsets, target_event_offsets)
        ],
        "target_event_offsets": target_event_offsets,
        "target_event_offset_deltas": [
            target_event_offsets[index + 1] - target_event_offsets[index]
            for index in range(len(target_event_offsets) - 1)
        ],
        "target_object_event_offset": target_event_offsets[-1],
        "target_object_event_offset_matches_last_event_start": target_event_offsets[-1] == max(target_event_offsets),
    }

    if spec.page0_page is not None:
        page0_page = parse_page_data(spec.page0_page.read_bytes())
        page0_hash_offset, page0_hash_data = _find_hash_block(tail, _expected_hashes(page0_page))
        page0_row = page_header_rows[1]
        expected_page0_user_offset = target_row["user_offset"] + target_slot_count * 24
        result["page0_page"] = _rel(spec.page0_page)
        result["page0_row"] = {
            **page0_row,
            "hash_offset_matches_page0_hash_block": page0_row["hash_offset"] == page0_hash_offset,
            "page0_user_offset_matches_target_slot_span": page0_row["user_offset"] == expected_page0_user_offset,
            "page0_hash_size": len(page0_hash_data),
        }

    return result


def _build_comparisons(cases: dict[str, Any]) -> dict[str, Any]:
    single = cases["single_page_filebrowser_working"]
    page1_fb = cases["page1_filebrowser_local_multipt"]
    page1_fs = cases["page1_filestream_local_multipt"]
    page1_ts = cases["page1_textselect_local_multipt"]

    single_row = single["target_page_row"]
    page1_fb_row = page1_fb["target_page_row"]
    page1_fs_row = page1_fs["target_page_row"]
    page1_ts_row = page1_ts["target_page_row"]

    return {
        "single_page_filebrowser_vs_page1_filebrowser": {
            "block_count_equal": single_row["block_count"] == page1_fb_row["block_count"],
            "primary_pre_string_len_equal": single_row["primary_pre_string_len"] == page1_fb_row["primary_pre_string_len"],
            "slot_count_equal": single_row["slot_count"] == page1_fb_row["slot_count"],
            "hash_offset_delta": page1_fb_row["hash_offset"] - single_row["hash_offset"],
            "target_event_offset_deltas": [
                multi - base
                for base, multi in zip(single["target_event_offsets"], page1_fb["target_event_offsets"])
            ],
        },
        "page1_filebrowser_vs_page1_filestream": {
            "target_rows_both_hash_valid": (
                page1_fb_row["hash_offset_matches_target_hash_block"]
                and page1_fs_row["hash_offset_matches_target_hash_block"]
            ),
            "target_rows_both_user_valid": (
                page1_fb_row["user_offset_points_to_nonzero_user_record"]
                and page1_fs_row["user_offset_points_to_nonzero_user_record"]
            ),
            "target_object_event_offsets_both_valid": (
                page1_fb["target_object_event_offset_matches_last_event_start"]
                and page1_fs["target_object_event_offset_matches_last_event_start"]
            ),
            "page0_rows_both_hash_valid": (
                page1_fb["page0_row"]["hash_offset_matches_page0_hash_block"]
                and page1_fs["page0_row"]["hash_offset_matches_page0_hash_block"]
            ),
            "page0_rows_both_user_span_valid": (
                page1_fb["page0_row"]["page0_user_offset_matches_target_slot_span"]
                and page1_fs["page0_row"]["page0_user_offset_matches_target_slot_span"]
            ),
        },
        "page1_filebrowser_vs_page1_textselect": {
            "target_rows_both_hash_valid": (
                page1_fb_row["hash_offset_matches_target_hash_block"]
                and page1_ts_row["hash_offset_matches_target_hash_block"]
            ),
            "target_rows_both_user_valid": (
                page1_fb_row["user_offset_points_to_nonzero_user_record"]
                and page1_ts_row["user_offset_points_to_nonzero_user_record"]
            ),
            "target_object_event_offsets_both_valid": (
                page1_fb["target_object_event_offset_matches_last_event_start"]
                and page1_ts["target_object_event_offset_matches_last_event_start"]
            ),
            "page0_rows_both_hash_valid": (
                page1_fb["page0_row"]["hash_offset_matches_page0_hash_block"]
                and page1_ts["page0_row"]["hash_offset_matches_page0_hash_block"]
            ),
            "page0_rows_both_user_span_valid": (
                page1_fb["page0_row"]["page0_user_offset_matches_target_slot_span"]
                and page1_ts["page0_row"]["page0_user_offset_matches_target_slot_span"]
            ),
        },
    }


def _build_conclusions(cases: dict[str, Any], comparisons: dict[str, Any]) -> dict[str, Any]:
    page1_fb = cases["page1_filebrowser_local_multipt"]
    all_cases = list(cases.values())
    return {
        "page1_filebrowser_target_row_hash_offset_valid": page1_fb["target_page_row"]["hash_offset_matches_target_hash_block"],
        "page1_filebrowser_target_row_user_offset_valid": page1_fb["target_page_row"]["user_offset_points_to_nonzero_user_record"],
        "page1_filebrowser_target_object_event_offset_valid": page1_fb["target_object_event_offset_matches_last_event_start"],
        "multi_page_page0_rows_remain_structurally_valid_even_in_filebrowser_case": (
            page1_fb["page0_row"]["hash_offset_matches_page0_hash_block"]
            and page1_fb["page0_row"]["page0_user_offset_matches_target_slot_span"]
        ),
        "single_page_filebrowser_and_page1_filebrowser_share_same_page_level_shape_except_expected_shift": (
            comparisons["single_page_filebrowser_vs_page1_filebrowser"]["block_count_equal"]
            and comparisons["single_page_filebrowser_vs_page1_filebrowser"]["primary_pre_string_len_equal"]
            and comparisons["single_page_filebrowser_vs_page1_filebrowser"]["slot_count_equal"]
            and comparisons["single_page_filebrowser_vs_page1_filebrowser"]["hash_offset_delta"] == 6
            and all(delta == 6 for delta in comparisons["single_page_filebrowser_vs_page1_filebrowser"]["target_event_offset_deltas"])
        ),
        "all_target_rows_keep_basic_pointer_closure": all(
            case["target_page_row"]["hash_offset_matches_target_hash_block"]
            and case["target_page_row"]["user_offset_points_to_nonzero_user_record"]
            and case["target_page_row"]["primary_pre_string_len_within_primary_size"]
            and case["target_object_event_offset_matches_last_event_start"]
            for case in all_cases
        ),
        "remaining_gap_more_likely_a_type_runtime_registration_or_descriptor_semantics": True,
        "page0_row_deltas_alone_are_not_a_sufficient_explanation_for_page1_filebrowser_failure": (
            comparisons["page1_filebrowser_vs_page1_filestream"]["page0_rows_both_hash_valid"]
            and comparisons["page1_filebrowser_vs_page1_filestream"]["page0_rows_both_user_span_valid"]
            and comparisons["page1_filebrowser_vs_page1_textselect"]["page0_rows_both_hash_valid"]
            and comparisons["page1_filebrowser_vs_page1_textselect"]["page0_rows_both_user_span_valid"]
        ),
    }


def _expected_hashes(page: Any) -> dict[int, int]:
    return {
        _field_int(block, "id"): _object_name_hash_or_error(block.objname)
        for block in page.blocks
        if block.objname
    }


def _decode_page_header_rows(tail: bytes, picture_rel: int, *, single_page: bool) -> list[dict[str, int | str]]:
    count = 1 if single_page else 2
    rows: list[dict[str, int | str]] = []
    for index in range(count):
        base = picture_rel + index * 16
        row = tail[base:base + 16]
        count_field = int.from_bytes(row[:4], "little")
        rows.append(
            {
                "record_offset": base,
                "record_offset_hex": hex(base),
                "count_field": count_field,
                "count_field_hex": hex(count_field),
                "block_count": count_field >> 16,
                "runtime_index": count_field & 0xFFFF,
                "hash_offset": int.from_bytes(row[4:8], "little"),
                "hash_offset_hex": hex(int.from_bytes(row[4:8], "little")),
                "user_offset": int.from_bytes(row[8:12], "little"),
                "user_offset_hex": hex(int.from_bytes(row[8:12], "little")),
                "primary_pre_string_len": int.from_bytes(row[12:16], "little"),
                "primary_pre_string_len_hex": hex(int.from_bytes(row[12:16], "little")),
            }
        )
    return rows


def _mirror_record_offsets(raw: bytes, *, search_start_abs: int, blocks: list[Any]) -> list[int]:
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
            raise RuntimeError(f"Unable to find mirror record header for {block.objname!r}")
        offsets.append(hit)
        cursor = hit + 4
    return offsets


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
