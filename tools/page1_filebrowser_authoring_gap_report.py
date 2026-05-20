from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usarthmi.hmi_inspect import inspect_hmi
from usarthmi.page_format import parse_page_data


SCAN_DIRS = [
    ROOT / "reverse_usarthmi" / "page1_filebrowser_drag_scan_20260519",
    ROOT / "reverse_usarthmi" / "page1_filebrowser_dragdepth_scan_20260519",
    ROOT / "reverse_usarthmi" / "page1_filebrowser_midband_scan_20260519",
    ROOT / "reverse_usarthmi" / "page1_filebrowser_midband_scan2_20260519",
    ROOT / "reverse_usarthmi" / "page1_filebrowser_narrow_scan_20260519",
    ROOT / "reverse_usarthmi" / "page1_filebrowser_tight_scan_20260519",
]
OFFICIAL_MINIMAL_HMI = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_76_page1_filebrowser_minimal_official_oracle\lcd_test.HMI")
OFFICIAL_MINIMAL_CONFIRMATION = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_76_page1_filebrowser_minimal_official_oracle\gui_verify_after_gui_create_20260519\precompile_confirmation.json")
CLONE_HMI = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_B4_page1_filebrowser_hmi_clone_oracle\lcd_test.HMI")
CLONE_COMPILE_JSON = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_B4_page1_filebrowser_hmi_clone_oracle\official_compile_probe_20260520\lcd_test.official_compile.json")
DEFAULT_OUT = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_authoring_gap_2026-05-20.json"


def _page1_blocks(hmi_path: Path) -> list[tuple[str, str]]:
    raw = hmi_path.read_bytes()
    inspection = inspect_hmi(hmi_path)
    entry = next((item for item in inspection.entries if item.name == "1.pa"), None)
    if entry is None or not entry.in_file:
        return []
    page = parse_page_data(raw[entry.data_offset : entry.data_offset + entry.length])
    return [(block.objname, block.type_code) for block in page.blocks]


def build_report() -> dict[str, Any]:
    scan_rows: list[dict[str, Any]] = []
    secondary_type_counter: Counter[str] = Counter()
    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue
        for hmi_path in sorted(scan_dir.rglob("lcd_test.HMI")):
            blocks = _page1_blocks(hmi_path)
            secondary = blocks[1:] if len(blocks) > 1 else []
            for _name, type_code in secondary:
                secondary_type_counter[type_code] += 1
            scan_rows.append(
                {
                    "hmi": str(hmi_path),
                    "page1_blocks": blocks,
                    "has_page1_filebrowser": any(type_code == "A" for _name, type_code in blocks),
                }
            )

    clone_blocks = _page1_blocks(CLONE_HMI) if CLONE_HMI.exists() else []
    clone_compile = json.loads(CLONE_COMPILE_JSON.read_text(encoding="utf-8")) if CLONE_COMPILE_JSON.exists() else {}
    official_minimal_blocks = _page1_blocks(OFFICIAL_MINIMAL_HMI) if OFFICIAL_MINIMAL_HMI.exists() else []
    official_minimal_confirmation = (
        json.loads(OFFICIAL_MINIMAL_CONFIRMATION.read_text(encoding="utf-8"))
        if OFFICIAL_MINIMAL_CONFIRMATION.exists()
        else {}
    )

    return {
        "schema_version": 1,
        "date": "2026-05-20",
        "target": "TJC8048X543_011C",
        "status": "page1-filebrowser-authoring-gap",
        "summary": {
            "scan_hmi_count": len(scan_rows),
            "scan_saved_page1_filebrowser_count": sum(1 for row in scan_rows if row["has_page1_filebrowser"]),
            "clone_saved_page1_filebrowser": any(type_code == "A" for _name, type_code in clone_blocks),
            "secondary_type_counts": dict(sorted(secondary_type_counter.items())),
        },
        "scan_rows": scan_rows,
        "clone_case": {
            "hmi": str(CLONE_HMI),
            "page1_blocks": clone_blocks,
            "official_compile_json": str(CLONE_COMPILE_JSON),
            "official_compile": {
                "compiled_output_size": clone_compile.get("compiled_output_size"),
                "page_lines": clone_compile.get("output_after", "").splitlines(),
            },
        },
        "official_minimal_case": {
            "hmi": str(OFFICIAL_MINIMAL_HMI),
            "page1_blocks": official_minimal_blocks,
            "precompile_confirmation": str(OFFICIAL_MINIMAL_CONFIRMATION),
            "confirmation_status": official_minimal_confirmation.get("status"),
            "confirmation_failures": official_minimal_confirmation.get("failures", []),
        },
        "conclusions": {
            "page1_filebrowser_saved_by_official_or_clone_hmi": False,
            "page1_filebrowser_runtime_negative_proof_exists": False,
            "narrowing": "current evidence does not show a real page1 file-browser object surviving into 1.pa for official compile/runtime. the official page1 minimal case mis-saves as v0(type 0x03), drag scans save other controls or nothing, and the clone case saves only page1. this is an authoring/save gap before it is a runtime-binding gap."
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize the page1 file-browser authoring/save gap from current scan and clone evidence.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    report = build_report()
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
