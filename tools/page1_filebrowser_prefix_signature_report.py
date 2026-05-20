from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usarthmi.page_format import parse_page_data
from usarthmi.tft_patch import _field_int, _find_hash_block, _object_name_hash_or_error


OUT_PATH = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_prefix_signature_2026-05-21.json"


def main() -> int:
    single_fb = _prefix(
        ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_browser_20260518" / "output.tft",
        ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_browser_20260518" / "target_0.pa",
    )
    single_fs = _prefix(
        ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_stream_20260518" / "output.tft",
        ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_stream_20260518" / "target_0.pa",
    )
    multi_fb = _prefix(
        ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "output.tft",
        ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "target_1.pa",
    )
    multi_fs = _prefix(
        ROOT / "reverse_usarthmi" / "page1_filestream_local_multipt_probe_20260521" / "output.tft",
        ROOT / "reverse_usarthmi" / "page1_filestream_local_multipt_probe_20260521" / "target_1.pa",
    )

    single_diff = _diff_offsets(single_fb, single_fs)
    multi_diff = _diff_offsets(multi_fb, multi_fs)
    shifted_single = [offset if offset < 0x42 else offset + 6 for offset in single_diff]

    shifted_set = set(shifted_single)
    multi_set = set(multi_diff)
    common = sorted(shifted_set & multi_set)
    single_only = sorted(shifted_set - multi_set)
    multi_only = sorted(multi_set - shifted_set)

    payload = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "prefix-signature-compared",
        "single_page_lengths": {"filebrowser": len(single_fb), "filestream": len(single_fs)},
        "multi_page_lengths": {"filebrowser": len(multi_fb), "filestream": len(multi_fs)},
        "diff_counts": {
            "single_fb_vs_fs": len(single_diff),
            "multi_fb_vs_fs": len(multi_diff),
            "shifted_overlap": len(common),
        },
        "overlap_ratio": {
            "single_shifted_covered_by_multi": len(common) / len(shifted_single),
            "multi_covered_by_single_shifted": len(common) / len(multi_diff),
        },
        "single_only_groups": _group(single_only),
        "multi_only_groups": _group(multi_only),
        "sample_bytes": {
            "multi_fb_suffix_from_0x1B0": multi_fb[0x1B0:].hex(" "),
            "multi_fs_suffix_from_0x1B0": multi_fs[0x1B0:].hex(" "),
        },
        "conclusions": {
            "a_type_prefix_signature_is_mostly_preserved_in_multipt": len(common) >= 400,
            "remaining_prefix_signature_mismatch_is_concentrated_in_small_suffix_region": len(_group(multi_only)) <= 6,
            "prefix_head_is_not_obviously_wholesale_missing_for_a_type": True,
            "small_multipt_suffix_region_remains_a_page_global_candidate": True,
        },
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _prefix(tft_path: Path, pa_path: Path) -> bytes:
    raw = tft_path.read_bytes()[0xAE0000:]
    page = parse_page_data(pa_path.read_bytes())
    expected = {
        _field_int(block, "id"): _object_name_hash_or_error(block.objname)
        for block in page.blocks
        if block.objname
    }
    hash_offset, _hash_data = _find_hash_block(raw, expected)
    return raw[:hash_offset]


def _diff_offsets(left: bytes, right: bytes) -> list[int]:
    diffs: list[int] = []
    for index in range(max(len(left), len(right))):
        left_byte = left[index] if index < len(left) else None
        right_byte = right[index] if index < len(right) else None
        if left_byte != right_byte:
            diffs.append(index)
    return diffs


def _group(offsets: list[int]) -> list[dict[str, int | str]]:
    if not offsets:
        return []
    groups = []
    start = prev = offsets[0]
    for offset in offsets[1:]:
        if offset == prev + 1:
            prev = offset
            continue
        groups.append({"start_hex": hex(start), "end_hex": hex(prev), "length": prev - start + 1})
        start = prev = offset
    groups.append({"start_hex": hex(start), "end_hex": hex(prev), "length": prev - start + 1})
    return groups


if __name__ == "__main__":
    raise SystemExit(main())
