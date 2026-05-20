from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))


DEFAULT_OUT = WORKSPACE_ROOT / "examples" / "lifecycle_runtime_smoke" / "runtime_binding_matrix_2026-05-20.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a compact page/runtime binding matrix from existing live and oracle artifacts.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON path")
    args = parser.parse_args()

    report = build_report()
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def build_report() -> dict[str, Any]:
    lifecycle = _load_json("examples/lifecycle_runtime_smoke/lifecycle_runtime_equivalence_report_2026-05-19.json")
    page1_mapping = _load_json("examples/lifecycle_runtime_smoke/page1_runtime_mapping_reverified_2026-05-20.json")
    page1_scope = _load_json("examples/advanced_direct_tft_demo/page1_advanced_runtime_scope_report_2026-05-19.json")
    case80 = _load_json("examples/advanced_direct_tft_demo/datarecord_textselect_case80_oracle_aligned_live_verified_2026-05-19.json")
    case85 = _load_json("examples/advanced_direct_tft_demo/datarecord_sltext_case85_oracle_aligned_live_verified_2026-05-19.json")
    case83 = _load_json("examples/advanced_direct_tft_demo/datarecord_textselect_button_case83_oracle_aligned_live_verified_2026-05-19.json")
    case83_event = _load_json("examples/advanced_direct_tft_demo/datarecord_textselect_button_case83_event_live_verified_2026-05-20.json")

    rows = [
        {
            "id": "page0_load_local_positive",
            "page": 0,
            "class": "lifecycle_page_event",
            "source": "examples/lifecycle_runtime_smoke/lifecycle_runtime_equivalence_report_2026-05-19.json",
            "compiled_positive": True,
            "runtime_positive": True,
            "runtime_signal": lifecycle["rows"][0]["runtime_result"],
            "scheduler_path": lifecycle["rows"][0]["scheduler_path"],
            "meaning": "local generated page0 load can dispatch through the narrow post_primary_page_event path",
        },
        {
            "id": "page0_case80_exact",
            "page": 0,
            "class": "advanced_readback_positive",
            "source": "examples/advanced_direct_tft_demo/datarecord_textselect_case80_oracle_aligned_live_verified_2026-05-19.json",
            "compiled_positive": True,
            "runtime_positive": True,
            "runtime_readback": case80["live_smoke"]["readback"],
            "meaning": "page0 exact data-record plus text-select shape is alive at runtime",
        },
        {
            "id": "page0_case85_exact",
            "page": 0,
            "class": "advanced_readback_positive",
            "source": "examples/advanced_direct_tft_demo/datarecord_sltext_case85_oracle_aligned_live_verified_2026-05-19.json",
            "compiled_positive": True,
            "runtime_positive": True,
            "runtime_readback": case85["live_smoke"]["readback"],
            "meaning": "page0 exact data-record plus sliding-text shape is alive at runtime",
        },
        {
            "id": "page0_case83_exact",
            "page": 0,
            "class": "advanced_readback_positive",
            "source": "examples/advanced_direct_tft_demo/datarecord_textselect_button_case83_oracle_aligned_live_verified_2026-05-19.json",
            "compiled_positive": True,
            "runtime_positive": True,
            "runtime_readback": case83["live_smoke"]["readback"],
            "meaning": "page0 exact data-record plus text-select plus ordinary button shape is alive at runtime",
        },
        {
            "id": "page0_case83_exact_event",
            "page": 0,
            "class": "advanced_event_positive",
            "source": "examples/advanced_direct_tft_demo/datarecord_textselect_button_case83_event_live_verified_2026-05-20.json",
            "compiled_positive": True,
            "runtime_positive": True,
            "runtime_observation": case83_event["live_smoke"]["runtime_observation"],
            "meaning": "page0 exact case83 event shape proves ordinary b1.down marker dispatch on top of the complex page",
        },
        {
            "id": "page1_local_text_positive_mapping_corrected",
            "page": 1,
            "class": "ordinary_readback_positive",
            "source": "examples/lifecycle_runtime_smoke/page1_runtime_mapping_reverified_2026-05-20.json",
            "compiled_positive": True,
            "runtime_positive": True,
            "runtime_page": 0,
            "runtime_readback": {
                "p1title.txt": page1_mapping["fresh_reverification"]["local_generated_page1_load_probe"]["runtime_page_0"][
                    "get_p1title_txt"
                ]["value"]
            },
            "meaning": "the local generated ordinary page1 text object is readable on runtime page 0; the earlier runtime page 1 invalid_reference result was a wrong-page probe",
        },
        {
            "id": "page1_load_marker_unrecovered",
            "page": 1,
            "class": "lifecycle_runtime_negative",
            "source": "examples/lifecycle_runtime_smoke/page1_runtime_mapping_reverified_2026-05-20.json",
            "compiled_positive": True,
            "runtime_positive": False,
            "runtime_page": 0,
            "runtime_signal": page1_mapping["fresh_reverification"]["local_generated_page1_load_probe"][
                "page_load_marker_after_runtime_page_1_to_0_switch"
            ]["kind"],
            "meaning": "the runtime page mapping is now corrected, but the local generated page1 load marker is still not observed when switching back to runtime page 0",
        },
        {
            "id": "page1_text_select_positive_mapping_corrected",
            "page": 1,
            "class": "advanced_readback_positive",
            "source": "examples/lifecycle_runtime_smoke/page1_runtime_mapping_reverified_2026-05-20.json",
            "compiled_positive": True,
            "runtime_positive": True,
            "runtime_page": 0,
            "runtime_readback": {
                "select0.val": page1_mapping["fresh_reverification"]["official_gui_page1_text_select"]["runtime_page_0"][
                    "get_select0_val"
                ]["value"]
            },
            "meaning": "the official GUI page1 text-select minimal case is readable on runtime page 0; the earlier runtime page 1 invalid_reference result was a wrong-page probe",
        },
        {
            "id": "page1_data_record_positive_mapping_corrected",
            "page": 1,
            "class": "advanced_readback_positive",
            "source": "examples/lifecycle_runtime_smoke/page1_runtime_mapping_reverified_2026-05-20.json",
            "compiled_positive": True,
            "runtime_positive": True,
            "runtime_page": 0,
            "runtime_readback": {
                "data0.maxval": page1_mapping["fresh_reverification"]["official_gui_page1_data_record"]["runtime_page_0"][
                    "get_data0_maxval"
                ]["value"],
                "data0.path": page1_mapping["fresh_reverification"]["official_gui_page1_data_record"]["runtime_page_0"][
                    "get_data0_path"
                ]["value"],
            },
            "meaning": "the official GUI page1 data-record minimal case is readable on runtime page 0; the earlier runtime page 1 invalid_reference result was a wrong-page probe",
        },
        {
            "id": "page1_file_stream_positive_mapping_corrected",
            "page": 1,
            "class": "advanced_readback_positive",
            "source": "examples/lifecycle_runtime_smoke/page1_runtime_mapping_reverified_2026-05-20.json",
            "compiled_positive": True,
            "runtime_positive": True,
            "runtime_page": 0,
            "runtime_readback": {
                "fs0.en": page1_mapping["fresh_reverification"]["official_gui_page1_file_stream"]["runtime_page_0"][
                    "get_fs0_en"
                ]["value"],
                "fs0.val": page1_mapping["fresh_reverification"]["official_gui_page1_file_stream"]["runtime_page_0"][
                    "get_fs0_val"
                ]["value"],
            },
            "meaning": "the official GUI page1 file-stream minimal case is readable on runtime page 0; the earlier runtime page 1 invalid_reference result was a wrong-page probe",
        },
    ]

    for control_name, item in page1_scope["controls"].items():
        if control_name in {"text-select", "data-record", "file-stream"}:
            continue
        rows.append(
            {
                "id": f"page1_{control_name.replace('-', '_')}",
                "page": 1,
                "class": "advanced_runtime_recheck_pending",
                "source": item["artifact"],
                "compiled_positive": bool(item["compiled_success"]),
                "runtime_positive": None,
                "runtime_signal": "stale_wrong_runtime_page_probe",
                "page_switch_ok": bool(item["page_switch_ok"]),
                "sendme_ok": bool(item["sendme_ok"]),
                "meaning": f"the historical page1 {control_name} probe switched to runtime page 1 before reading back; correct runtime page 0 revalidation is still pending",
            }
        )

    return {
        "schema_version": 1,
        "date": "2026-05-20",
        "target": "TJC8048X543_011C",
        "summary": {
            "page0_advanced_positive_count": sum(1 for item in rows if item["page"] == 0 and item["runtime_positive"]),
            "page1_runtime_page_mapping_confirmed": True,
            "page1_ordinary_binding_positive_count": sum(
                1 for item in rows if item["page"] == 1 and item["class"] == "ordinary_readback_positive" and item["runtime_positive"]
            ),
            "page1_advanced_binding_positive_count": sum(
                1 for item in rows if item["page"] == 1 and item["class"] == "advanced_readback_positive" and item["runtime_positive"]
            ),
            "page1_load_marker_recovered": False,
            "page1_remaining_controls_requiring_correct_page_recheck_count": sum(
                1 for item in rows if item["class"] == "advanced_runtime_recheck_pending"
            ),
            "highest_leverage_gap": "page-load scheduler recovery and corrected-page revalidation of remaining page1 advanced controls",
        },
        "rows": rows,
        "interpretation": {
            "page0_positive_does_not_imply_page1_scheduler_equivalence": True,
            "runtime_page_0_maps_to_generated_page1": True,
            "likely_shared_breakpoint": [
                "fresh live re-verification now proves the recovered case31-style two-page scaffold binds generated or official page1 content on runtime page 0, not runtime page 1",
                "the local ordinary page1 text probe and official GUI page1 text-select/data-record/file-stream probes all become positive on runtime page 0, so the older runtime page 1 invalid_reference results were wrong-page negatives",
                "the remaining unrecovered gap is narrower: page1 object binding is not generally absent, but page-level load scheduling is still missing and the remaining advanced controls need corrected-page revalidation",
            ],
            "recommended_next_step": "keep lifecycle recovery focused on page-load scheduling, and re-run the remaining page1 advanced controls on runtime page 0 before treating any of them as real negatives",
        },
    }


def _load_json(relative_path: str) -> dict[str, Any]:
    path = WORKSPACE_ROOT / relative_path
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
