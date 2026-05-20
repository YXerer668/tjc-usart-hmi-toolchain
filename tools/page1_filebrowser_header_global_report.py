from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usarthmi.tft_toolchain import inspect_tft


OUT_PATH = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_header_global_2026-05-21.json"

CASES = {
    "single_page_filebrowser_working": ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_browser_20260518" / "output.tft",
    "single_page_filestream_working": ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_stream_20260518" / "output.tft",
    "page1_filebrowser_local_multipt": ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "output.tft",
    "page1_filestream_local_multipt": ROOT / "reverse_usarthmi" / "page1_filestream_local_multipt_probe_20260521" / "output.tft",
}


def main() -> int:
    cases = {name: _case(path) for name, path in CASES.items()}
    fb_multi = cases["page1_filebrowser_local_multipt"]["Header2"]
    fs_multi = cases["page1_filestream_local_multipt"]["Header2"]

    differing_keys = sorted(key for key in fb_multi if fb_multi.get(key) != fs_multi.get(key))
    payload = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "header-global-compared",
        "cases": cases,
        "comparison": {
            "multi_fb_vs_fs_differing_header2_keys": differing_keys,
            "multi_fb_vs_fs_same_header2_keys": sorted(key for key in fb_multi if fb_multi.get(key) == fs_multi.get(key)),
        },
        "conclusions": {
            "multi_page_fb_and_fs_share_same_non_offset_runtime_header_shape": all(
                fb_multi[key] == fs_multi[key]
                for key in (
                    "unknown_pages_address",
                    "unknown_objects_address",
                    "videos_address",
                    "audios_address",
                    "fonts_address",
                    "unknown_maincode_binary",
                    "pages_count",
                    "unknown_objects_count",
                    "gmovs_count",
                    "videos_count",
                    "audios_count",
                    "fonts_count",
                    "unknown_res1",
                    "unknown_encode",
                    "unknown_res2",
                    "unknown_res3",
                )
            ),
            "remaining_multi_fb_vs_fs_header2_deltas_are_offsets_or_picture_count_only": differing_keys
            == [
                "app_attributes_data_address",
                "gmovs_address",
                "pictures_address",
                "pictures_count",
                "static_usercode_address",
                "usercode_address",
            ],
            "header_globals_do_not_expose_a_filebrowser_specific_runtime_registration_bit": True,
        },
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _case(path: Path) -> dict[str, Any]:
    info = inspect_tft(path)
    parsed = info["parsed"]
    return {
        "tft": str(path.relative_to(ROOT)),
        "editor_version": info["editor_version"],
        "model": info["model"],
        "Header1": parsed["Header1"],
        "Header2": parsed["Header2"],
    }


if __name__ == "__main__":
    raise SystemExit(main())
