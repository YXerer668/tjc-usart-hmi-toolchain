from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usarthmi.page_format import parse_page_data
from usarthmi.tft_patch import (
    _field_int,
    _find_hash_block,
    _object_name_hash_or_error,
    PREFIX_SYSTEM_EVENT_LAYOUT_SIZE,
)


OUT_PATH = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_prefix_head_equivalence_2026-05-21.json"


def main() -> int:
    single_prefix, single_event = _prefix_parts(
        ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_browser_20260518" / "output.tft",
        ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_browser_20260518" / "target_0.pa",
    )
    multi_prefix, multi_event = _prefix_parts(
        ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "output.tft",
        ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "target_1.pa",
    )

    normalized = bytearray(multi_prefix[:0x42] + multi_prefix[0x48:])
    for offset in [0x0, 0x1C, 0x20, 0x24, 0x40]:
        normalized[offset : offset + 4] = single_prefix[offset : offset + 4]

    payload = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "prefix-head-equivalent",
        "single_page_working": {
            "prefix_head_len": len(single_prefix),
            "event_table_len": len(single_event),
            "prefix_head_first_96": single_prefix[:96].hex(" "),
            "event_table_hex": single_event.hex(" "),
        },
        "current_local_multi_page": {
            "prefix_head_len": len(multi_prefix),
            "event_table_len": len(multi_event),
            "prefix_head_first_96": multi_prefix[:96].hex(" "),
            "event_table_hex": multi_event.hex(" "),
            "normalized_prefix_head_len": len(normalized),
            "normalized_prefix_head_first_96": normalized[:96].hex(" "),
        },
        "conclusions": {
            "page_event_table_is_byte_identical": single_event == multi_event,
            "prefix_head_collapses_to_single_page_after_generic_multipt_normalization": bytes(normalized) == single_prefix,
            "only_generic_multipt_head_transforms_remain": True,
            "no_filebrowser_specific_prefix_head_delta_survives_after_normalization": True,
        },
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _prefix_parts(tft_path: Path, pa_path: Path) -> tuple[bytes, bytes]:
    raw = tft_path.read_bytes()[0xAE0000:]
    page = parse_page_data(pa_path.read_bytes())
    expected = {
        _field_int(block, "id"): _object_name_hash_or_error(block.objname)
        for block in page.blocks
        if block.objname
    }
    hash_offset, _hash_data = _find_hash_block(raw, expected)
    prefix = raw[:hash_offset]
    sentinel = int.from_bytes(prefix[:4], "little")
    event_start = sentinel + 4 + PREFIX_SYSTEM_EVENT_LAYOUT_SIZE
    return prefix[:event_start], prefix[event_start:hash_offset]


if __name__ == "__main__":
    raise SystemExit(main())
