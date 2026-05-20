from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usarthmi.page_format import parse_page_data
from usarthmi.tft_patch import _field_int, _record_header_flag, _record_header_unknown2


OUT_PATH = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_no_post_mirror_service_tail_2026-05-21.json"


def main() -> int:
    multi_fb = _analyze_multipt(
        ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "output.tft",
        ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "target_1.pa",
        ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "target_0.pa",
        record_search_offset=0x2991 + 32,
    )
    multi_fs = _analyze_multipt(
        ROOT / "reverse_usarthmi" / "page1_filestream_local_multipt_probe_20260521" / "output.tft",
        ROOT / "reverse_usarthmi" / "page1_filestream_local_multipt_probe_20260521" / "target_1.pa",
        ROOT / "reverse_usarthmi" / "page1_filestream_local_multipt_probe_20260521" / "target_0.pa",
        record_search_offset=0x227F + 32,
    )
    single_fb = _analyze_single(
        ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_browser_20260518" / "output.tft",
        ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_browser_20260518" / "target_0.pa",
        record_search_offset=0x1A1E + 16,
    )
    single_fs = _analyze_single(
        ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_stream_20260518" / "output.tft",
        ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_stream_20260518" / "target_0.pa",
        record_search_offset=0x1317 + 16,
    )

    payload = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "no-post-mirror-service-tail",
        "cases": {
            "single_page_filebrowser_working": single_fb,
            "single_page_filestream_working": single_fs,
            "page1_filebrowser_local_multipt": multi_fb,
            "page1_filestream_local_multipt": multi_fs,
        },
        "conclusions": {
            "page1_to_page0_mirror_sets_are_adjacent_in_multipt_filebrowser": multi_fb["gap_between_page1_last_and_page0_first"] == 0,
            "page1_to_page0_mirror_sets_are_adjacent_in_multipt_filestream": multi_fs["gap_between_page1_last_and_page0_first"] == 0,
            "final_mirror_record_to_file_end_is_tiny_across_cases": all(
                case["trailing_bytes_after_last_record"] <= 7
                for case in [single_fb, single_fs, multi_fb, multi_fs]
            ),
            "no_room_for_meaningful_post_mirror_global_service_table": True,
        },
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _analyze_multipt(tft_path: Path, page1_path: Path, page0_path: Path, *, record_search_offset: int) -> dict[str, object]:
    raw = tft_path.read_bytes()
    object_start = 0xAE0000
    page1 = parse_page_data(page1_path.read_bytes())
    page0 = parse_page_data(page0_path.read_bytes())

    page1_records, cursor = _record_starts(raw, object_start + record_search_offset, page1)
    page0_records, cursor = _record_starts(raw, cursor, page0)
    mirror_record_length = page1_records[1]["record_offset"] - page1_records[0]["record_offset"]
    page1_last_end = page1_records[-1]["record_offset"] + mirror_record_length
    page0_first_start = page0_records[0]["record_offset"]
    page0_last_end = page0_records[-1]["record_offset"] + mirror_record_length
    trailing = len(raw) - (object_start + page0_last_end)

    return {
        "tft": str(tft_path.relative_to(ROOT)),
        "mirror_record_length": mirror_record_length,
        "page1_records": page1_records,
        "page0_records": page0_records,
        "gap_between_page1_last_and_page0_first": page0_first_start - page1_last_end,
        "page0_last_record_end": page0_last_end,
        "trailing_bytes_after_last_record": trailing,
        "trailing_hex": raw[object_start + page0_last_end : object_start + page0_last_end + 16].hex(" "),
    }


def _analyze_single(tft_path: Path, page_path: Path, *, record_search_offset: int) -> dict[str, object]:
    raw = tft_path.read_bytes()
    object_start = 0xAE0000
    page = parse_page_data(page_path.read_bytes())
    records, _cursor = _record_starts(raw, object_start + record_search_offset, page)
    mirror_record_length = records[1]["record_offset"] - records[0]["record_offset"]
    last_end = records[-1]["record_offset"] + mirror_record_length
    trailing = len(raw) - (object_start + last_end)
    return {
        "tft": str(tft_path.relative_to(ROOT)),
        "mirror_record_length": mirror_record_length,
        "records": records,
        "last_record_end": last_end,
        "trailing_bytes_after_last_record": trailing,
        "trailing_hex": raw[object_start + last_end : object_start + last_end + 16].hex(" "),
    }


def _record_starts(raw: bytes, cursor_abs: int, page) -> tuple[list[dict[str, int | str]], int]:
    object_start = 0xAE0000
    records = []
    cursor = cursor_abs
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
        records.append(
            {
                "objname": block.objname,
                "type_code": block.type_code,
                "record_offset": hit - object_start,
                "record_offset_hex": hex(hit - object_start),
            }
        )
        cursor = hit + 4
    return records, cursor


if __name__ == "__main__":
    raise SystemExit(main())
