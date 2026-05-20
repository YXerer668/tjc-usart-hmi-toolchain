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
    page1_load_oracle = _load_json("examples/lifecycle_runtime_smoke/page1_load_official_oracle_live_positive_2026-05-20.json")
    page1_load_local = _load_json("examples/lifecycle_runtime_smoke/page1_load_local_generated_live_verified_2026-05-20.json")
    page1_loadend_local = _load_json("examples/lifecycle_runtime_smoke/page1_loadend_local_generated_live_verified_2026-05-20.json")
    page1_load_and_loadend_local = _load_json(
        "examples/lifecycle_runtime_smoke/page1_load_and_loadend_local_generated_live_verified_2026-05-20.json"
    )
    page1_filebrowser_direct = _load_json("examples/lifecycle_runtime_smoke/page1_filebrowser_direct_tft_live_verified_2026-05-20.json")
    page1_filebrowser_refresh = _load_json("examples/lifecycle_runtime_smoke/page1_filebrowser_refresh_probe_2026-05-20.json")
    page1_filebrowser_gap = _load_json("examples/lifecycle_runtime_smoke/page1_filebrowser_authoring_gap_2026-05-20.json")
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
            "id": "page1_local_load_dispatch_positive",
            "page": 1,
            "class": "lifecycle_runtime_positive",
            "source": "examples/lifecycle_runtime_smoke/page1_load_local_generated_live_verified_2026-05-20.json",
            "compiled_positive": True,
            "runtime_positive": True,
            "runtime_page": 0,
            "runtime_signal": page1_load_local["live_sequence"][1]["hex"],
            "meaning": "the rebuilt local page1 load probe now emits its marker when switching back to runtime page 0, proving the minimal fixed 4-byte page1 load-printh family is reproduced locally",
        },
        {
            "id": "page1_official_load_dispatch_positive",
            "page": 1,
            "class": "lifecycle_runtime_positive",
            "source": "examples/lifecycle_runtime_smoke/page1_load_official_oracle_live_positive_2026-05-20.json",
            "compiled_positive": True,
            "runtime_positive": True,
            "runtime_page": 0,
            "runtime_signal": page1_load_oracle["official_oracle"]["runtime_sequence"][3]["hex"],
            "meaning": "the official case52 page1 load oracle emits its marker when switching to runtime page 0, proving that the panel runtime does support page1 load dispatch",
        },
        {
            "id": "page1_local_loadend_dispatch_positive",
            "page": 1,
            "class": "lifecycle_runtime_positive",
            "source": "examples/lifecycle_runtime_smoke/page1_loadend_local_generated_live_verified_2026-05-20.json",
            "compiled_positive": True,
            "runtime_positive": True,
            "runtime_page": 0,
            "runtime_signal": page1_loadend_local["live_sequence"][0]["hex"],
            "meaning": "the rebuilt local page1 loadend probe now emits its marker when switching to runtime page 0, extending the recovered narrow page1 phase-printh family beyond plain load",
        },
        {
            "id": "page1_local_load_and_loadend_dispatch_positive",
            "page": 1,
            "class": "lifecycle_runtime_positive",
            "source": "examples/lifecycle_runtime_smoke/page1_load_and_loadend_local_generated_live_verified_2026-05-20.json",
            "compiled_positive": True,
            "runtime_positive": True,
            "runtime_page": 0,
            "runtime_signal": page1_load_and_loadend_local["live_sequence"][0]["hex"],
            "meaning": "the rebuilt local page1 load+loadend probe now emits both markers when switching to runtime page 0, proving the fixed 4-byte family extends to the minimal combined case as well",
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
            "id": "page1_sliding_text_positive_mapping_corrected",
            "page": 1,
            "class": "advanced_readback_positive",
            "source": "examples/lifecycle_runtime_smoke/page1_runtime_mapping_reverified_2026-05-20.json",
            "compiled_positive": True,
            "runtime_positive": True,
            "runtime_page": 0,
            "runtime_readback": {
                "slt0.txt": page1_mapping["fresh_reverification"]["official_gui_page1_sliding_text"]["runtime_page_0"][
                    "get_slt0_txt"
                ]["value"]
            },
            "meaning": "the official GUI page1 sliding-text minimal case is readable on runtime page 0; the earlier runtime page 1 invalid_reference result was a wrong-page probe",
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
        {
            "id": "page1_file_browser_direct_binding_positive",
            "page": 1,
            "class": "advanced_readback_positive",
            "source": "examples/lifecycle_runtime_smoke/page1_filebrowser_direct_tft_live_verified_2026-05-20.json",
            "compiled_positive": True,
            "runtime_positive": True,
            "runtime_page": 0,
            "runtime_readback": {
                "fbrowser0.dir": page1_filebrowser_direct["live_readback"]["fbrowser0.dir"]["value"],
                "fbrowser0.filter": page1_filebrowser_direct["live_readback"]["fbrowser0.filter"]["value"],
                "fbrowser0.txt": page1_filebrowser_direct["live_readback"]["fbrowser0.txt"]["value"],
            },
            "meaning": "the local direct-TFT page1 file-browser probe now reads back dir/filter/txt on runtime page 0, proving field binding for page1 file-browser on the local path",
        },
        {
            "id": "page1_file_browser_direct_enumeration_negative",
            "page": 1,
            "class": "advanced_runtime_negative",
            "source": "examples/lifecycle_runtime_smoke/page1_filebrowser_refresh_probe_2026-05-20.json",
            "compiled_positive": True,
            "runtime_positive": False,
            "runtime_page": 0,
            "runtime_signal": {
                "qty": page1_filebrowser_refresh["steps"]["after_page_cycle"]["qty"]["response"]["value"],
                "txt": page1_filebrowser_refresh["steps"]["after_page_cycle"]["txt"]["response"]["value"],
            },
            "meaning": "after ref fbrowser0 and a page1->page0 cycle, page1 direct-TFT file-browser still keeps qty=0 and the camera stays white, so enumeration/display is not yet recovered even though field binding is alive",
        },
        {
            "id": "page1_file_browser_authoring_gap",
            "page": 1,
            "class": "advanced_authoring_gap",
            "source": "examples/lifecycle_runtime_smoke/page1_filebrowser_authoring_gap_2026-05-20.json",
            "compiled_positive": False,
            "runtime_positive": None,
            "runtime_signal": "no_saved_page1_filebrowser_object",
            "meaning": page1_filebrowser_gap["conclusions"]["narrowing"],
        },
    ]

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
            "page1_advanced_binding_negative_count": sum(
                1 for item in rows if item["page"] == 1 and item["class"] == "advanced_runtime_negative" and not item["runtime_positive"]
            ),
            "page1_advanced_authoring_gap_count": sum(
                1 for item in rows if item["page"] == 1 and item["class"] == "advanced_authoring_gap"
            ),
            "page1_official_load_dispatch_positive_count": sum(
                1
                for item in rows
                if item["page"] == 1
                and item["id"] == "page1_official_load_dispatch_positive"
                and item["runtime_positive"]
            ),
            "page1_local_load_dispatch_positive_count": sum(
                1
                for item in rows
                if item["page"] == 1
                and item["id"] in {
                    "page1_local_load_dispatch_positive",
                    "page1_local_loadend_dispatch_positive",
                    "page1_local_load_and_loadend_dispatch_positive",
                }
                and item["runtime_positive"]
            ),
            "page1_load_marker_recovered": True,
            "page1_remaining_controls_requiring_correct_page_recheck_count": 0,
            "highest_leverage_gap": "broader page-level lifecycle generalization and page1 file-browser authoring/save recovery",
        },
        "rows": rows,
        "interpretation": {
            "page0_positive_does_not_imply_page1_scheduler_equivalence": True,
            "runtime_page_0_maps_to_generated_page1": True,
            "likely_shared_breakpoint": [
                "fresh live re-verification now proves the recovered case31-style two-page scaffold binds generated or official page1 content on runtime page 0, not runtime page 1",
                "the local ordinary page1 text probe and official GUI page1 text-select/sliding-text/data-record/file-stream probes all become positive on runtime page 0, so the older runtime page 1 invalid_reference results were wrong-page negatives",
                "the official case52 page1 load oracle and the rebuilt local page1 load/loadend probes now dispatch on corrected runtime page 0 for the minimal fixed 4-byte page-level printh family, including the minimal combined load+loadend case",
                "the remaining unrecovered gaps are narrower: page1 object binding is now alive for five tested advanced controls on the local runtime path, but page1 file-browser still has two separate gaps: direct-TFT enumeration/display stays negative with qty=0 plus a white camera surface, and the official authoring/save layer still fails to preserve an A-type object into 1.pa",
            ],
            "recommended_next_step": "generalize the recovered page1 load wrapper path beyond the fixed 4-byte load/loadend printh family, and in parallel split page1 file-browser into two recovery lanes: fix local direct-TFT enumeration/display beyond qty=0 white-surface behavior, and separately recover a page1 file-browser HMI that actually preserves an A-type object into 1.pa",
        },
    }


def _load_json(relative_path: str) -> dict[str, Any]:
    path = WORKSPACE_ROOT / relative_path
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
