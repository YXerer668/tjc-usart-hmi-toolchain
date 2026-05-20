from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usarthmi.page_format import parse_page_data


PROBE_DIR = ROOT / "reverse_usarthmi" / "page0_filebrowser_multipt_blank_page1_probe_20260521"
BUILD_REPORT = PROBE_DIR / "build_report.json"
TARGET0 = ROOT / "reverse_usarthmi" / "advanced_direct_tft_file_browser_20260518" / "target_0.pa"
TARGET1 = PROBE_DIR / "target_1.pa"
OUT_PATH = ROOT / "examples" / "lifecycle_runtime_smoke" / "page0_filebrowser_multipt_blank_page1_probe_2026-05-21.json"


def main() -> int:
    build = json.loads(BUILD_REPORT.read_text(encoding="utf-8"))
    page0 = parse_page_data(TARGET0.read_bytes())
    page1 = parse_page_data(TARGET1.read_bytes())

    payload = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "probe-prepared",
        "probe_dir": str(PROBE_DIR.relative_to(ROOT)),
        "build_report": str(BUILD_REPORT.relative_to(ROOT)),
        "output_tft": str((PROBE_DIR / "output.tft").relative_to(ROOT)),
        "page0_blocks": [[block.objname, block.type_code] for block in page0.blocks],
        "page1_blocks": [[block.objname, block.type_code] for block in page1.blocks],
        "build_summary": {
            "file_size": build["file_size"],
            "object_count": build["object_count"],
            "section_offsets": build["section_offsets"],
            "warnings": build["warnings"],
        },
        "live_hypothesis": {
            "runtime_mapping": {
                "page 0": "extra page (blank page1)",
                "page 1": "seed-side page0 carrying fbrowser0",
            },
            "commands": [
                "sendme",
                "page 1",
                "sendme",
                "get fbrowser0.dir",
                "get fbrowser0.filter",
                "get fbrowser0.qty",
                "get fbrowser0.txt",
            ],
            "interpretation": {
                "if_page1_reads_fbrowser_fields": "extra-page/page1-specific runtime limitation is weakened",
                "if_page1_still_fails_like_page1_filebrowser": "current target likely rejects multi-page A-type more generally, not only the extra-page placement",
            },
        },
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
