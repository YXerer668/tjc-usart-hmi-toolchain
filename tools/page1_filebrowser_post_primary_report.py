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
from usarthmi.tft_patch import _field_int, _find_hash_block, _object_name_hash_or_error, _header, _header_int
from usarthmi.tft_toolchain import inspect_tft


OUT_PATH = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_post_primary_report_2026-05-21.json"

CASES = {
    "single_page_filebrowser_working": (
        ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_browser_20260518" / "output.tft",
        ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_browser_20260518" / "target_0.pa",
        None,
    ),
    "page1_filebrowser_local_multipt": (
        ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "output.tft",
        ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "target_1.pa",
        ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "target_0.pa",
    ),
    "page1_filestream_local_multipt": (
        ROOT / "reverse_usarthmi" / "page1_filestream_local_multipt_probe_20260521" / "output.tft",
        ROOT / "reverse_usarthmi" / "page1_filestream_local_multipt_probe_20260521" / "target_1.pa",
        ROOT / "reverse_usarthmi" / "page1_filestream_local_multipt_probe_20260521" / "target_0.pa",
    ),
}


def main() -> int:
    cases = {name: _analyze_case(*spec) for name, spec in CASES.items()}
    payload = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "post-primary-compared",
        "cases": cases,
        "conclusions": {
            "single_page_filebrowser_has_post_primary_page_load_marker": (
                cases["single_page_filebrowser_working"]["post_primary_items"][0]["command"] == "post_primary_page_load"
            ),
            "current_local_page1_filebrowser_lacks_single_page_post_primary_marker": not any(
                item.get("command") == "post_primary_page_load"
                for item in cases["page1_filebrowser_local_multipt"]["post_primary_head_items"]
            ),
            "current_local_page1_filestream_also_lacks_single_page_post_primary_marker": not any(
                item.get("command") == "post_primary_page_load"
                for item in cases["page1_filestream_local_multipt"]["post_primary_head_items"]
            ),
            "post_primary_marker_absence_is_not_a_general_advanced_page_failure_explanation": (
                cases["page1_filestream_local_multipt"]["post_primary_head_items"][0]["command"] == "loadend"
            ),
            "post_primary_marker_remains_a_specific_a_type_probe_candidate": True,
        },
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _analyze_case(tft_path: Path, target_page_path: Path, page0_path: Path | None) -> dict[str, Any]:
    raw = tft_path.read_bytes()
    inspection = inspect_tft(tft_path)
    header2 = _header(inspection, "Header2")
    object_start = _header_int(header2, "unknown_objects_address")
    attr_offset = _header_int(header2, "static_usercode_address")
    if object_start is None or attr_offset is None:
        raise RuntimeError(f"Missing required TFT offsets in {tft_path}")
    target_page = parse_page_data(target_page_path.read_bytes())
    tail = raw[object_start:]
    target_hash_offset, target_hash_data = _find_hash_block(tail, _expected_hashes(target_page))
    primary_size_field = target_hash_offset + 4 + len(target_hash_data)
    primary_offset = primary_size_field + 4
    primary_size = int.from_bytes(tail[primary_size_field:primary_size_field + 4], "little")
    primary_end = primary_offset + primary_size

    if page0_path is None:
        post_primary_end = attr_offset
    else:
        page0 = parse_page_data(page0_path.read_bytes())
        page0_hash_offset, _page0_hash_data = _find_hash_block(tail, _expected_hashes(page0))
        post_primary_end = page0_hash_offset

    post_primary = tail[primary_end:post_primary_end]
    head_length = min(len(post_primary), 11 if page0_path is not None else len(post_primary))
    post_primary_head = post_primary[:head_length]

    return {
        "tft": str(tft_path.relative_to(ROOT)),
        "target_page": str(target_page_path.relative_to(ROOT)),
        "primary_offset": primary_offset,
        "primary_size": primary_size,
        "primary_end": primary_end,
        "post_primary_length": len(post_primary),
        "post_primary_hex": post_primary.hex(" "),
        "post_primary_items": decode_event_table(post_primary),
        "post_primary_head_hex": post_primary_head.hex(" "),
        "post_primary_head_items": decode_event_table(post_primary_head),
        "page0_hash_offset": post_primary_end if page0_path is not None else None,
    }


def _expected_hashes(page: Any) -> dict[int, int]:
    return {
        _field_int(block, "id"): _object_name_hash_or_error(block.objname)
        for block in page.blocks
        if block.objname
    }


if __name__ == "__main__":
    raise SystemExit(main())
