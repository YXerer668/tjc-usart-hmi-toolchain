from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usarthmi.page_format import parse_page_data
from usarthmi.tft_toolchain import inspect_tft
from usarthmi.tft_patch import (
    _field_int,
    _header,
    _header_int,
    _record_header_flag,
    _record_header_unknown2,
    _user_slot_count,
)


OUT_PATH = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_object_local_equivalence_2026-05-21.json"


def main() -> int:
    single = _collect_case(
        ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_browser_20260518" / "output.tft",
        ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_browser_20260518" / "target_0.pa",
        page_row_offset=0x1A1E,
        record_search_offset=0x1A1E + 16,
    )
    multi = _collect_case(
        ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "output.tft",
        ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "target_1.pa",
        page_row_offset=0x2991,
        record_search_offset=0x2991 + 32,
    )

    user_equal_indices = [index for index, (left, right) in enumerate(zip(single["user_records_hex"], multi["user_records_hex"])) if left == right]
    mirror_equal_indices = [index for index, (left, right) in enumerate(zip(single["mirror_abs_values"], multi["mirror_abs_values"])) if left == right]

    payload = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "object-local-equivalent",
        "single_page_working": single,
        "current_local_multi_page": multi,
        "comparison": {
            "user_record_equal_count": len(user_equal_indices),
            "user_record_equal_indices": user_equal_indices,
            "mirror_abs_value_equal_count": len(mirror_equal_indices),
            "mirror_abs_value_equal_indices": mirror_equal_indices,
            "mirror_record_event_offset_delta": multi["mirror_record_event_offset"] - single["mirror_record_event_offset"],
            "mirror_record_offset_delta": multi["mirror_record_offset"] - single["mirror_record_offset"],
        },
        "conclusions": {
            "all_60_actual_user_records_identical": len(user_equal_indices) == 60,
            "all_60_actual_mirror_abs_slot_values_identical": len(mirror_equal_indices) == 60,
            "only_object_local_delta_is_page_level_event_offset_shift": (
                multi["mirror_record_event_offset"] - single["mirror_record_event_offset"] == 6
            ),
            "remaining_gap_is_outside_object_local_a_type_wiring": True,
        },
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _collect_case(tft_path: Path, pa_path: Path, *, page_row_offset: int, record_search_offset: int) -> dict[str, object]:
    raw = tft_path.read_bytes()
    page = parse_page_data(pa_path.read_bytes())
    inspection = inspect_tft(tft_path)
    header2 = _header(inspection, "Header2")
    object_start = _header_int(header2, "unknown_objects_address")
    if object_start is None:
        raise RuntimeError(f"Missing object_start in {tft_path}")

    row = raw[object_start + page_row_offset : object_start + page_row_offset + 16]
    user_offset = int.from_bytes(row[8:12], "little")
    slot_start = 0
    for block in page.blocks:
        if block.objname == "fbrowser0":
            break
        slot_start += _user_slot_count(block)

    user_records = [
        raw[object_start + user_offset + (slot_start + index) * 24 : object_start + user_offset + (slot_start + index + 1) * 24]
        for index in range(60)
    ]

    block = next(block for block in page.blocks if block.objname == "fbrowser0")
    pattern = bytes([
        ord(block.type_code),
        _field_int(block, "id"),
        _record_header_unknown2(block.type_code),
        _record_header_flag(block.type_code),
    ])
    record_offset_abs = raw.find(pattern, object_start + record_search_offset)
    if record_offset_abs < 0:
        raise RuntimeError(f"Unable to locate fbrowser0 mirror record in {tft_path}")
    record = raw[record_offset_abs : record_offset_abs + 0x38 + 60 * 2]
    mirror_abs_values = [int.from_bytes(record[offset : offset + 2], "little") for offset in range(0x38, len(record), 2)]

    return {
        "tft": str(tft_path.relative_to(ROOT)),
        "page": str(pa_path.relative_to(ROOT)),
        "user_offset": user_offset,
        "slot_start": slot_start,
        "user_records_hex": [record.hex(" ") for record in user_records],
        "mirror_record_offset": record_offset_abs - object_start,
        "mirror_record_event_offset": int.from_bytes(record[0x34:0x38], "little"),
        "mirror_abs_values": mirror_abs_values,
    }


if __name__ == "__main__":
    raise SystemExit(main())
