from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usarthmi.page_format import parse_page_data


FB_PROBE_DIR = ROOT / "reverse_usarthmi" / "page0_filebrowser_multipt_blank_page1_probe_20260521"
FS_PROBE_DIR = ROOT / "reverse_usarthmi" / "page0_filestream_multipt_blank_page1_probe_20260521"
TS_PROBE_DIR = ROOT / "reverse_usarthmi" / "page0_textselect_multipt_blank_page1_probe_20260521"
FB_EXPECT = ROOT / "examples" / "lifecycle_runtime_smoke" / "page0_filebrowser_multipt_blank_page1_smoke_2026-05-21.json"
FS_EXPECT = ROOT / "examples" / "lifecycle_runtime_smoke" / "page0_filestream_multipt_blank_page1_smoke_2026-05-21.json"
TS_EXPECT = ROOT / "examples" / "lifecycle_runtime_smoke" / "page0_textselect_multipt_blank_page1_smoke_2026-05-21.json"
OUT_PATH = ROOT / "examples" / "lifecycle_runtime_smoke" / "seed_side_multipt_runtime_limit_probes_2026-05-21.json"
FIDELITY = ROOT / "examples" / "lifecycle_runtime_smoke" / "seed_side_multipt_probe_fidelity_2026-05-21.json"


def main() -> int:
    fidelity = json.loads(FIDELITY.read_text(encoding="utf-8")) if FIDELITY.exists() else {}
    payload = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "seed-side-probes-prepared",
        "probes": {
            "page0_filebrowser_blank_page1": _probe_entry(FB_PROBE_DIR, "fbrowser0"),
            "page0_filestream_blank_page1": _probe_entry(FS_PROBE_DIR, "fs0"),
            "page0_textselect_blank_page1": _probe_entry(TS_PROBE_DIR, "select0"),
        },
        "live_plan": {
            "expected_runtime_mapping": {
                "page 0": "blank extra page1",
                "page 1": "seed-side page0 carrying the advanced control",
            },
            "recommended_order": [
                "optionally upload page0_textselect_blank_page1 as a D-type seed-side control",
                "verify sendme -> page 1 and get select0.val",
                "upload page0_filestream_blank_page1 control probe second",
                "verify sendme -> page 1 and get fs0.en/fs0.val",
                "upload page0_filebrowser_blank_page1 falsification probe last",
                "verify sendme -> page 1 and get fbrowser0.dir/filter/qty/txt",
            ],
            "interpretation": {
                "filestream_positive_and_filebrowser_negative": "strong evidence for A-type-specific multi-page runtime limitation",
                "textselect_positive_filestream_positive_filebrowser_negative": "very strong evidence for A-type-specific multi-page runtime limitation rather than a generic seed-side/runtime1 problem",
                "both_positive": "extra-page/page1 placement is the primary limiter, not multi-page in general",
                "both_negative": "seed-side runtime page 1 itself may still be the limiter, or multi-page advanced runtime is more broadly constrained",
            },
            "fidelity_notes": fidelity.get("conclusions", {}),
        },
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _probe_entry(probe_dir: Path, advanced_name: str) -> dict[str, object]:
    build = json.loads((probe_dir / "build_report.json").read_text(encoding="utf-8"))
    page0 = parse_page_data(Path(build["target_pages"][0]).read_bytes())
    page1 = parse_page_data(Path(build["target_pages"][1]).read_bytes())
    return {
        "probe_dir": str(probe_dir.relative_to(ROOT)),
        "output_tft": str((probe_dir / "output.tft").relative_to(ROOT)),
        "expect_json": str(_expect_for_name(advanced_name).relative_to(ROOT)),
        "page0_blocks": [[block.objname, block.type_code] for block in page0.blocks],
        "page1_blocks": [[block.objname, block.type_code] for block in page1.blocks],
        "advanced_name": advanced_name,
        "build_summary": {
            "file_size": build["file_size"],
            "object_count": build["object_count"],
            "section_offsets": build["section_offsets"],
        },
    }


def _expect_for_name(advanced_name: str) -> Path:
    if advanced_name == "fbrowser0":
        return FB_EXPECT
    if advanced_name == "fs0":
        return FS_EXPECT
    if advanced_name == "select0":
        return TS_EXPECT
    raise KeyError(advanced_name)


if __name__ == "__main__":
    raise SystemExit(main())
