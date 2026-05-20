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
    page1_local_load_negative = _load_json("examples/lifecycle_runtime_smoke/page1_load_local_generated_live_negative_2026-05-20.json")
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
            "id": "page1_local_load_negative",
            "page": 1,
            "class": "ordinary_lifecycle_negative",
            "source": "examples/lifecycle_runtime_smoke/page1_load_local_generated_live_negative_2026-05-20.json",
            "compiled_positive": True,
            "runtime_positive": False,
            "runtime_signal": "missing_load_marker_and_invalid_reference",
            "page_switch_ok": True,
            "sendme_ok": True,
            "meaning": page1_local_load_negative["meaning"]["narrowing"],
        },
    ]

    for control_name, item in page1_scope["controls"].items():
        rows.append(
            {
                "id": f"page1_{control_name.replace('-', '_')}",
                "page": 1,
                "class": "advanced_runtime_negative",
                "source": item["artifact"],
                "compiled_positive": bool(item["compiled_success"]),
                "runtime_positive": False,
                "runtime_signal": item["runtime_status"],
                "page_switch_ok": bool(item["page_switch_ok"]),
                "sendme_ok": bool(item["sendme_ok"]),
                "meaning": f"page1 {control_name} compiles and page-switches, but runtime object binding remains {item['runtime_status']}",
            }
        )

    return {
        "schema_version": 1,
        "date": "2026-05-20",
        "target": "TJC8048X543_011C",
        "summary": {
            "page0_advanced_positive_count": sum(1 for item in rows if item["page"] == 0 and item["runtime_positive"]),
            "page1_advanced_compile_positive_runtime_negative_count": sum(
                1 for item in rows if item["class"] == "advanced_runtime_negative" and item["compiled_positive"] and not item["runtime_positive"]
            ),
            "page1_ordinary_lifecycle_negative_count": sum(
                1 for item in rows if item["class"] == "ordinary_lifecycle_negative" and not item["runtime_positive"]
            ),
            "page_navigation_layer_proven": True,
            "page_local_advanced_registration_recovered": False,
            "highest_leverage_gap": "general scheduler/lifecycle and page-local advanced runtime registration",
        },
        "rows": rows,
        "interpretation": {
            "page0_positive_does_not_imply_page1_binding": True,
            "page1_failure_is_no_longer_advanced_only": True,
            "likely_shared_breakpoint": [
                "page1 advanced controls compile into non-empty TFT object regions and page switching works, so the remaining failure is deeper than GUI authoring or page navigation",
                "the lifecycle equivalence report still does not explain a general page callback binding path, which lines up with both page1 advanced objects and a minimal page1 ordinary load/text probe failing after page switch",
            ],
            "recommended_next_step": "continue recovering general scheduler/lifecycle/page-event binding, and use page1 advanced invalid_reference as the strongest runtime registration acceptance test",
        },
    }


def _load_json(relative_path: str) -> dict[str, Any]:
    path = WORKSPACE_ROOT / relative_path
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
