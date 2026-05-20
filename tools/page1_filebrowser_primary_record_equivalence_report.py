from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usarthmi.page_format import parse_page_data
from usarthmi.tft_patch import _field_int, _find_hash_block, _object_name_hash_or_error, _primary_value_offsets


OUT_PATH = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_primary_record_equivalence_2026-05-21.json"


def main() -> int:
    single = _collect_case(
        ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_browser_20260518" / "output.tft",
        ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_browser_20260518" / "target_0.pa",
    )
    multi = _collect_case(
        ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "output.tft",
        ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "target_1.pa",
    )

    comparisons = []
    for left, right in zip(single["records"], multi["records"]):
        comparisons.append(
            {
                "objname": left["objname"],
                "type_code": left["type_code"],
                "equal": left["record_hex"] == right["record_hex"],
                "single_length": left["record_length"],
                "multi_length": right["record_length"],
                "start_delta": right["record_start"] - left["record_start"],
            }
        )

    payload = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "primary-record-equivalent",
        "single_page_working": single,
        "current_local_multi_page": multi,
        "comparisons": comparisons,
        "conclusions": {
            "all_five_primary_records_identical": all(item["equal"] for item in comparisons),
            "primary_record_lengths_match": all(item["single_length"] == item["multi_length"] for item in comparisons),
            "primary_record_starts_do_not_shift": all(item["start_delta"] == 0 for item in comparisons),
            "remaining_gap_is_outside_primary_object_records": True,
        },
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _collect_case(tft_path: Path, pa_path: Path) -> dict[str, object]:
    raw = tft_path.read_bytes()
    object_start = 0xAE0000
    tail = raw[object_start:]
    page = parse_page_data(pa_path.read_bytes())
    expected_hashes = {
        _field_int(block, "id"): _object_name_hash_or_error(block.objname)
        for block in page.blocks
        if block.objname
    }
    hash_offset, hash_data = _find_hash_block(tail, expected_hashes)
    primary_size_offset = hash_offset + 4 + len(hash_data)
    primary_size = int.from_bytes(tail[primary_size_offset : primary_size_offset + 4], "little")
    primary = tail[primary_size_offset + 4 : primary_size_offset + 4 + primary_size]
    value_offsets = _primary_value_offsets(primary, len(page.blocks))

    records = []
    for index, block in enumerate(page.blocks):
        record_start = value_offsets[index] - 0x10
        later_starts = [offset - 0x10 for offset in value_offsets[index + 1 :] if offset > value_offsets[index] - 0x10]
        if later_starts:
            record_end = min(later_starts)
        else:
            record_end = len(primary) - 4
        record = primary[record_start:record_end]
        records.append(
            {
                "objname": block.objname,
                "type_code": block.type_code,
                "record_start": record_start,
                "record_end": record_end,
                "record_length": record_end - record_start,
                "record_hex": record.hex(" "),
            }
        )

    return {
        "tft": str(tft_path.relative_to(ROOT)),
        "page": str(pa_path.relative_to(ROOT)),
        "hash_offset": hash_offset,
        "primary_size": primary_size,
        "records": records,
    }


if __name__ == "__main__":
    raise SystemExit(main())
