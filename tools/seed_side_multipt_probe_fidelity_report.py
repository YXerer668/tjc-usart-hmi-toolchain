from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usarthmi.page_format import parse_page_data
from usarthmi.tft_toolchain import inspect_tft
from usarthmi.tft_patch import (
    _field_int,
    _find_hash_block,
    _object_name_hash_or_error,
    _primary_value_offsets,
    _record_header_flag,
    _record_header_unknown2,
    _user_slot_count,
    PREFIX_SYSTEM_EVENT_LAYOUT_SIZE,
)


OUT_PATH = ROOT / "examples" / "lifecycle_runtime_smoke" / "seed_side_multipt_probe_fidelity_2026-05-21.json"

SPECS = [
    {
        "name": "filebrowser",
        "baseline_tft": ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_browser_20260518" / "output.tft",
        "baseline_pa": ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_browser_20260518" / "target_0.pa",
        "probe_tft": ROOT / "reverse_usarthmi" / "page0_filebrowser_multipt_blank_page1_probe_20260521" / "output.tft",
        "probe_page0": ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_browser_20260518" / "target_0.pa",
    },
    {
        "name": "filestream",
        "baseline_tft": ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_stream_20260518" / "output.tft",
        "baseline_pa": ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_stream_20260518" / "target_0.pa",
        "probe_tft": ROOT / "reverse_usarthmi" / "page0_filestream_multipt_blank_page1_probe_20260521" / "output.tft",
        "probe_page0": ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_stream_20260518" / "target_0.pa",
    },
    {
        "name": "textselect",
        "baseline_tft": ROOT / "reverse_usarthmi" / "advanced_direct_tft_text_select_20260518" / "output.tft",
        "baseline_pa": ROOT / "reverse_usarthmi" / "advanced_direct_tft_text_select_20260518" / "target_0.pa",
        "probe_tft": ROOT / "reverse_usarthmi" / "page0_textselect_multipt_blank_page1_probe_20260521" / "output.tft",
        "probe_page0": ROOT / "reverse_usarthmi" / "advanced_direct_tft_text_select_20260518" / "target_0.pa",
    },
]


def main() -> int:
    cases = {spec["name"]: _compare_case(**spec) for spec in SPECS}
    payload = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "seed-side-fidelity-compared",
        "cases": cases,
        "conclusions": {
            "filebrowser_seed_side_probe_is_compiled_faithful_modulo_runtime_index_and_event_shift": cases["filebrowser"]["compiled_fidelity_ok"],
            "textselect_seed_side_probe_is_compiled_faithful_modulo_runtime_index_and_event_shift": cases["textselect"]["compiled_fidelity_ok"],
            "filestream_seed_side_probe_has_a_small_page_event_delta": not cases["filestream"]["page_event_table_identical"],
            "seed_side_runtime_limiter_runner_should_treat_textselect_as_the_strongest_control": True,
        },
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _compare_case(*, name: str, baseline_tft: Path, baseline_pa: Path, probe_tft: Path, probe_page0: Path) -> dict[str, Any]:
    base = _single_page_snapshot(baseline_tft, baseline_pa)
    probe = _seed_side_page0_snapshot(probe_tft, probe_page0)
    return {
        "baseline_tft": str(baseline_tft.relative_to(ROOT)),
        "probe_tft": str(probe_tft.relative_to(ROOT)),
        "user_records_match_after_runtime_index_normalization": base["user_records_norm"] == probe["user_records_norm"],
        "primary_records_identical": base["primary_records_hex"] == probe["primary_records_hex"],
        "page_event_table_identical": base["page_event_table_hex"] == probe["page_event_table_hex"],
        "mirror_event_offset_deltas": [
            after - before for before, after in zip(base["mirror_event_offsets"], probe["mirror_event_offsets"])
        ],
        "compiled_fidelity_ok": (
            base["user_records_norm"] == probe["user_records_norm"]
            and base["primary_records_hex"] == probe["primary_records_hex"]
            and all(after - before >= 0 for before, after in zip(base["mirror_event_offsets"], probe["mirror_event_offsets"]))
        ),
    }


def _single_page_snapshot(tft_path: Path, pa_path: Path) -> dict[str, Any]:
    raw = tft_path.read_bytes()[0xAE0000:]
    page = parse_page_data(pa_path.read_bytes())
    hash_offset, _hash_data = _find_hash_block(raw, _expected_hashes(page))
    prefix = raw[:hash_offset]
    sentinel = int.from_bytes(prefix[:4], "little")
    event_start = sentinel + 4 + PREFIX_SYSTEM_EVENT_LAYOUT_SIZE
    event_table = prefix[event_start:hash_offset]
    picture_row_offset = _picture_row_offset(tft_path)
    primary_records, user_records, mirror_event_offsets = _page_records(
        raw,
        page,
        picture_row_offset=picture_row_offset,
        record_search_offset=picture_row_offset + 16,
    )
    return {
        "page_event_table_hex": event_table.hex(" "),
        "primary_records_hex": primary_records,
        "user_records_norm": [_normalize_runtime_index(record) for record in user_records],
        "mirror_event_offsets": mirror_event_offsets,
    }


def _seed_side_page0_snapshot(tft_path: Path, pa_path: Path) -> dict[str, Any]:
    raw = tft_path.read_bytes()[0xAE0000:]
    page = parse_page_data(pa_path.read_bytes())
    info = inspect_tft(tft_path)["parsed"]["Header2"]
    picture_row_offset = int(info["pictures_address"], 16) - int(info["unknown_objects_address"], 16) + 16
    page0_hash = int.from_bytes(raw[picture_row_offset + 4:picture_row_offset + 8], "little")
    page0_event_start = _find_page0_first_event_offset(raw, picture_row_offset + 32)
    event_table = raw[page0_event_start:page0_hash]
    primary_records, user_records, mirror_event_offsets = _page_records(
        raw,
        page,
        picture_row_offset=picture_row_offset,
        record_search_offset=picture_row_offset + 32,
    )
    return {
        "page_event_table_hex": event_table.hex(" "),
        "primary_records_hex": primary_records,
        "user_records_norm": [_normalize_runtime_index(record) for record in user_records],
        "mirror_event_offsets": mirror_event_offsets,
    }


def _page_records(raw: bytes, page, *, picture_row_offset: int, record_search_offset: int) -> tuple[list[str], list[bytes], list[int]]:
    page_header = raw[picture_row_offset:picture_row_offset + 16]
    hash_offset = int.from_bytes(page_header[4:8], "little")
    user_offset = int.from_bytes(page_header[8:12], "little")
    hash_size = int.from_bytes(raw[hash_offset:hash_offset + 4], "little")
    primary_size_offset = hash_offset + 4 + hash_size
    primary_size = int.from_bytes(raw[primary_size_offset:primary_size_offset + 4], "little")
    primary = raw[primary_size_offset + 4:primary_size_offset + 4 + primary_size]
    value_offsets = _primary_value_offsets(primary, len(page.blocks))

    primary_records = []
    for index, block in enumerate(page.blocks):
        start = value_offsets[index] - 0x10
        later_starts = [offset - 0x10 for offset in value_offsets[index + 1:] if offset > value_offsets[index] - 0x10]
        end = min(later_starts) if later_starts else len(primary) - 4
        primary_records.append(primary[start:end].hex(" "))

    user_records = []
    slot_cursor = 0
    for block in page.blocks:
        count = _user_slot_count(block)
        for index in range(count):
            record = raw[user_offset + (slot_cursor + index) * 24 : user_offset + (slot_cursor + index + 1) * 24]
            user_records.append(record)
        slot_cursor += count

    mirror_event_offsets = []
    cursor = record_search_offset
    for block in page.blocks:
        pattern = bytes([
            ord(block.type_code),
            _field_int(block, "id"),
            _record_header_unknown2(block.type_code),
            _record_header_flag(block.type_code),
        ])
        hit = raw.find(pattern, cursor)
        if hit < 0:
            raise RuntimeError(f"Unable to locate mirror record for {block.objname!r}")
        mirror_event_offsets.append(int.from_bytes(raw[hit + 0x34:hit + 0x38], "little"))
        cursor = hit + 4

    return primary_records, user_records, mirror_event_offsets


def _normalize_runtime_index(record: bytes) -> str:
    data = bytearray(record)
    if len(data) >= 17:
        data[16] = 0
    return bytes(data).hex(" ")


def _picture_row_offset(tft_path: Path) -> int:
    info = inspect_tft(tft_path)["parsed"]["Header2"]
    return int(info["pictures_address"], 16) - int(info["unknown_objects_address"], 16)


def _find_page0_first_event_offset(raw: bytes, cursor: int) -> int:
    pattern = bytes([ord("y"), 0, _record_header_unknown2("y"), _record_header_flag("y")])
    hit = raw.find(pattern, cursor)
    if hit < 0:
        raise RuntimeError("Unable to locate page0 mirror page record")
    return int.from_bytes(raw[hit + 0x34:hit + 0x38], "little")


def _expected_hashes(page) -> dict[int, int]:
    return {
        _field_int(block, "id"): _object_name_hash_or_error(block.objname)
        for block in page.blocks
        if block.objname
    }


if __name__ == "__main__":
    raise SystemExit(main())
