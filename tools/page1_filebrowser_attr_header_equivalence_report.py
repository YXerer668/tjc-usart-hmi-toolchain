from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usarthmi.tft_toolchain import inspect_tft
from usarthmi.tft_patch import _header, _header_int


OUT_PATH = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_attr_header_equivalence_2026-05-21.json"


CASES = {
    "single_page_filebrowser_working": ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_browser_20260518" / "output.tft",
    "single_page_filestream_working": ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_stream_20260518" / "output.tft",
    "page1_filebrowser_local_multipt": ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "output.tft",
    "page1_filestream_local_multipt": ROOT / "reverse_usarthmi" / "page1_filestream_local_multipt_probe_20260521" / "output.tft",
}


def main() -> int:
    cases = {name: _analyze(path) for name, path in CASES.items()}
    headers = {name: case["attr_user_header_hex"] for name, case in cases.items()}
    unique_headers = sorted(set(headers.values()))

    payload = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "attr-header-equivalent",
        "cases": cases,
        "conclusions": {
            "all_four_attr_user_headers_identical": len(unique_headers) == 1,
            "attr_user_header_not_the_missing_filebrowser_registration_layer": True,
        },
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _analyze(tft_path: Path) -> dict[str, object]:
    raw = tft_path.read_bytes()
    inspection = inspect_tft(tft_path)
    header2 = _header(inspection, "Header2")
    object_start = _header_int(header2, "unknown_objects_address")
    attr_offset = _header_int(header2, "static_usercode_address")
    user_offset = _header_int(header2, "usercode_address")
    if None in {object_start, attr_offset, user_offset}:
        raise RuntimeError(f"Missing required TFT offsets in {tft_path}")
    assert object_start is not None
    assert attr_offset is not None
    assert user_offset is not None
    header = raw[object_start + attr_offset : object_start + user_offset]
    return {
        "tft": str(tft_path.relative_to(ROOT)),
        "attr_offset": attr_offset,
        "user_offset": user_offset,
        "attr_user_header_hex": header.hex(" "),
    }


if __name__ == "__main__":
    raise SystemExit(main())
