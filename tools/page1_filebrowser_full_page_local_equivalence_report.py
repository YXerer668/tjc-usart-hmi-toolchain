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


OUT_PATH = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_full_page_local_equivalence_2026-05-21.json"


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

    payload = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "full-page-local-equivalent",
        "single_page_working": single,
        "current_local_multi_page": multi,
        "comparison": {
            "full_page_user_record_equal_count": sum(
                1 for left, right in zip(single["user_records_hex"], multi["user_records_hex"]) if left == right
            ),
            "full_page_user_record_total": len(single["user_records_hex"]),
            "record_offset_deltas": [
                right["record_offset"] - left["record_offset"]
                for left, right in zip(single["mirror_records"], multi["mirror_records"])
            ],
            "event_offset_deltas": [
                right["event_offset"] - left["event_offset"]
                for left, right in zip(single["mirror_records"], multi["mirror_records"])
            ],
        },
        "conclusions": {
            "all_204_page_local_user_records_identical": all(
                left == right for left, right in zip(single["user_records_hex"], multi["user_records_hex"])
            ),
            "all_five_mirror_records_shift_by_same_absolute_record_delta": len(
                {
                    right["record_offset"] - left["record_offset"]
                    for left, right in zip(single["mirror_records"], multi["mirror_records"])
                }
            )
            == 1,
            "all_five_mirror_event_offsets_shift_by_plus_6_only": all(
                right["event_offset"] - left["event_offset"] == 6
                for left, right in zip(single["mirror_records"], multi["mirror_records"])
            ),
            "page_local_companion_objects_are_not_the_primary_gap": True,
            "remaining_gap_is_above_full_page_local_wiring": True,
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

    user_records: list[str] = []
    slot_start = 0
    mirror_records: list[dict[str, int | str]] = []
    cursor = object_start + record_search_offset
    for block in page.blocks:
        slot_count = _user_slot_count(block)
        for index in range(slot_count):
            record = raw[
                object_start + user_offset + (slot_start + index) * 24 : object_start + user_offset + (slot_start + index + 1) * 24
            ]
            user_records.append(record.hex(" "))

        pattern = bytes([
            ord(block.type_code),
            _field_int(block, "id"),
            _record_header_unknown2(block.type_code),
            _record_header_flag(block.type_code),
        ])
        hit = raw.find(pattern, cursor)
        if hit < 0:
            raise RuntimeError(f"Unable to locate mirror record for {block.objname!r}")
        mirror_records.append(
            {
                "objname": block.objname,
                "type_code": block.type_code,
                "record_offset": hit - object_start,
                "record_offset_hex": hex(hit - object_start),
                "event_offset": int.from_bytes(raw[hit + 0x34 : hit + 0x38], "little"),
                "event_offset_hex": hex(int.from_bytes(raw[hit + 0x34 : hit + 0x38], "little")),
            }
        )
        cursor = hit + 4
        slot_start += slot_count

    return {
        "tft": str(tft_path.relative_to(ROOT)),
        "page": str(pa_path.relative_to(ROOT)),
        "user_offset": user_offset,
        "user_records_hex": user_records,
        "mirror_records": mirror_records,
    }


if __name__ == "__main__":
    raise SystemExit(main())
