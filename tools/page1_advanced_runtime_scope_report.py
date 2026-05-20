from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from usarthmi.hmi_inspect import inspect_hmi
from usarthmi.page_format import parse_page_data


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = {
    "text-select": ROOT / "examples" / "advanced_direct_tft_demo" / "page1_textselect_official_gui_live_negative_2026-05-19.json",
    "sliding-text": ROOT / "examples" / "advanced_direct_tft_demo" / "page1_sltext_official_gui_live_negative_2026-05-19.json",
    "data-record": ROOT / "examples" / "advanced_direct_tft_demo" / "page1_datarecord_official_gui_live_negative_2026-05-19.json",
    "file-stream": ROOT / "examples" / "advanced_direct_tft_demo" / "page1_filestream_official_gui_live_negative_2026-05-19.json",
    "file-browser": ROOT / "examples" / "advanced_direct_tft_demo" / "page1_filebrowser_official_clone_live_negative_2026-05-20.json",
}
SCAN_ROOTS = [
    ROOT / "reverse_usarthmi" / "page1_filebrowser_drag_scan_20260519",
    ROOT / "reverse_usarthmi" / "page1_filebrowser_dragdepth_scan_20260519",
    ROOT / "reverse_usarthmi" / "page1_filebrowser_midband_scan2_20260519",
    ROOT / "reverse_usarthmi" / "page1_filebrowser_tight_scan_20260519",
    ROOT / "reverse_usarthmi" / "page1_toolbox_upper_scan_20260519",
    ROOT / "reverse_usarthmi" / "page1_toolbox_top_scan_20260519",
    ROOT / "reverse_usarthmi" / "page1_toolbox_edge_scan_20260519",
    ROOT / "reverse_usarthmi" / "page1_toolbox_end520_topscan_20260519",
]
OUT = ROOT / "examples" / "advanced_direct_tft_demo" / "page1_advanced_runtime_scope_report_2026-05-19.json"


def _scan_filebrowser_mapping() -> dict[str, Any]:
    tested_variants = 0
    found_candidates: list[dict[str, Any]] = []
    for scan_root in SCAN_ROOTS:
        if not scan_root.exists():
            continue
        for hmi in scan_root.rglob("lcd_test.HMI"):
            tested_variants += 1
            try:
                inspection = inspect_hmi(hmi)
                raw = hmi.read_bytes()
                entry = next((item for item in inspection.entries if item.name == "1.pa" and item.in_file), None)
                if entry is None:
                    continue
                page = parse_page_data(raw[entry.data_offset : entry.data_offset + entry.length])
            except Exception:
                continue
            for block in page.blocks:
                if block.type_code == "A":
                    found_candidates.append(
                        {
                            "hmi": str(hmi.relative_to(ROOT).as_posix()),
                            "objname": block.objname,
                            "type_code": block.type_code,
                            "id": _field_int(block, "id"),
                        }
                    )
    return {
        "tested_variants": tested_variants,
        "found_candidates": found_candidates,
        "resolved": bool(found_candidates),
    }


def _field_int(block, name: str) -> int | None:
    field = next((item for item in block.fields if item.name == name), None)
    if field is None or field.value is None:
        return None
    raw = field.value
    if isinstance(raw, bytes):
        return int.from_bytes(raw, "little")
    if isinstance(raw, int):
        return raw
    return None


def main() -> int:
    report: dict[str, Any] = {
        "schema_version": 1,
        "date": "2026-05-20",
        "target": "TJC8048X543_011C",
        "status": "page1-advanced-runtime-scoped-out",
        "summary": {
            "compile_positive_runtime_negative_controls": [],
            "count": 0,
            "filebrowser_mapping_resolved": False,
        },
        "controls": {},
        "filebrowser_mapping": _scan_filebrowser_mapping(),
        "decision": {
            "builder_policy": "fail-closed",
            "scope_out_reason": "page1 advanced runtime is still not closed on the current target; four official GUI-created controls compile to non-empty TFTs yet remain invalid_reference at runtime, and a separately cloned page1 file-browser HMI also compiles positive but remains invalid_reference on the live panel",
            "next_requirement": "either recover target-runtime binding for page1 advanced controls or keep page1 advanced explicitly out of the independent workflow contract",
        },
    }
    for control_name, artifact_path in ARTIFACTS.items():
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        compiled = payload["official_compile"]
        runtime = payload["live_smoke"]
        report["controls"][control_name] = {
            "artifact": str(artifact_path.relative_to(ROOT).as_posix()),
            "compiled_success": compiled["compiled_success"],
            "compiled_output_size": compiled["compiled_output_size"],
            "object_region_length": compiled.get("object_region_length"),
            "page_lines": compiled.get("page_lines"),
            "page_switch_ok": runtime["page_switch"]["ok"],
            "sendme_ok": runtime["sendme"]["ok"],
            "runtime_status": "invalid_reference",
        }
        report["summary"]["compile_positive_runtime_negative_controls"].append(control_name)
    report["summary"]["count"] = len(report["summary"]["compile_positive_runtime_negative_controls"])
    report["summary"]["filebrowser_mapping_resolved"] = report["filebrowser_mapping"]["resolved"]
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
