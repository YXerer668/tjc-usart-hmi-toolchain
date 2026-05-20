from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a compact lifecycle scheduler equivalence matrix from existing oracle and live-proof JSON files."
    )
    parser.add_argument("--case51-case52", type=Path, required=True, help="Combined lifecycle dispatch candidate report JSON")
    parser.add_argument("--case52", type=Path, required=True, help="Case52 lifecycle dispatch candidate report JSON")
    parser.add_argument("--page1-slot-probe", type=Path, required=True, help="Page1 callback-slot hardware probe JSON")
    parser.add_argument("--local-page0-positive", type=Path, required=True, help="Local generated page0 load positive proof JSON")
    parser.add_argument("--out", type=Path, required=True, help="Output JSON path")
    args = parser.parse_args()

    report = build_report(
        case51_case52=_load_json(args.case51_case52),
        case52=_load_json(args.case52),
        page1_slot_probe=_load_json(args.page1_slot_probe),
        local_page0_positive=_load_json(args.local_page0_positive),
    )
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


def build_report(
    *,
    case51_case52: dict[str, Any],
    case52: dict[str, Any],
    page1_slot_probe: dict[str, Any],
    local_page0_positive: dict[str, Any],
) -> dict[str, Any]:
    case51_page0 = _find_item(case51_case52, "case51_01_page_load_source_events_official_event_index.json")
    case51_page1 = _find_item(case51_case52, "case51_04_second_page_load_source_events_official_event_index.json")
    case52_page0 = _find_item(case52, "case52_01_page0_load_printh_only_official_event_index.json")
    case52_page1 = _find_item(case52, "case52_06_page1_load_printh_only_official_event_index.json")

    rows = [
        _row_from_local_positive(local_page0_positive),
        _row_from_dispatch_item("official_case51_page0_load", case51_page0),
        _row_from_dispatch_item("official_case51_page1_load", case51_page1),
        _row_from_dispatch_item("official_case52_page0_load", case52_page0),
        _row_from_dispatch_item("official_case52_page1_load", case52_page1),
        _row_from_page1_slot_probe(page1_slot_probe),
    ]

    return {
        "schema_version": 1,
        "mode": "lifecycle_runtime_equivalence_report",
        "rows": rows,
        "interpretation": {
            "official_page_load_uses_callback_slots": False,
            "local_page0_positive_is_general_scheduler_equivalence": False,
            "page1_lifecycle_recovered": False,
            "narrowing": [
                "Official lifecycle oracles keep scheduler_path at page_event_boundary_without_page_callback and leave callback slots 0x0c/0x10/0x14 empty.",
                "The local generated page0 positive proof is real, but it is a narrow post_primary_page_event path and does not prove general lifecycle equivalence.",
                "Blindly writing page mirror callback slots 0x0c/0x10/0x14 to the page1 event table start fails cleanly and does not recover page1 lifecycle dispatch."
            ],
            "recommended_next_step": "Treat lifecycle scheduler recovery as research-only until a new official oracle or descriptor-level explanation narrows the runtime binding path further.",
        },
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_item(report: dict[str, Any], suffix: str) -> dict[str, Any]:
    return next(item for item in report["items"] if str(item["file"]).endswith(suffix))


def _first_lifecycle_record(item: dict[str, Any]) -> dict[str, Any]:
    return item.get("lifecycle_record_fields", [])[0]


def _row_from_dispatch_item(label: str, item: dict[str, Any]) -> dict[str, Any]:
    phase = item.get("phase_matches", [None])[0] or {}
    record = _first_lifecycle_record(item)
    first_record = record.get("records", [None])[0] or {}
    slot_0c = first_record.get("slot_0x0c", {})
    slot_10 = first_record.get("slot_0x10", {})
    slot_14 = first_record.get("slot_0x14", {})
    event_34 = first_record.get("event_offset_0x34", {})
    return {
        "label": label,
        "scheduler_path": item.get("scheduler_path"),
        "safe_to_flash": item.get("summary", {}).get("safe_to_flash"),
        "phase_start_hex": phase.get("offset_hex"),
        "first_executable_hex": phase.get("first_executable_absolute_hex"),
        "phase_end_hex": phase.get("end_hex"),
        "slot_0x0c_hex": slot_0c.get("value_hex"),
        "slot_0x10_hex": slot_10.get("value_hex"),
        "slot_0x14_hex": slot_14.get("value_hex"),
        "event_offset_0x34_hex": event_34.get("value_hex"),
        "runtime_result": "compiler_oracle_only",
    }


def _row_from_page1_slot_probe(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": "page1_slot_write_negative",
        "scheduler_path": "blind_slot_write_negative",
        "safe_to_flash": False,
        "phase_start_hex": report.get("basis", {}).get("page_event_table_relative_offset_hex"),
        "first_executable_hex": None,
        "phase_end_hex": None,
        "slot_0x0c_hex": "0x14B",
        "slot_0x10_hex": "0x14B",
        "slot_0x14_hex": "0x14B",
        "event_offset_0x34_hex": report.get("basis", {}).get("page_mirror_record_relative_offset_hex"),
        "runtime_result": "no_printh_seen_after_slot_write",
    }


def _row_from_local_positive(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("event_index_summary", {})
    result = report.get("result", {})
    return {
        "label": "local_generated_page0_load_positive",
        "scheduler_path": summary.get("scheduler_path"),
        "safe_to_flash": True,
        "phase_start_hex": summary.get("page_load_phase_offset_hex"),
        "first_executable_hex": summary.get("page_load_phase_offset_hex"),
        "phase_end_hex": None,
        "slot_0x0c_hex": None,
        "slot_0x10_hex": None,
        "slot_0x14_hex": None,
        "event_offset_0x34_hex": None,
        "runtime_result": f"observed {result.get('observed_hex')} after {result.get('trigger')}",
    }


if __name__ == "__main__":
    raise SystemExit(main())
