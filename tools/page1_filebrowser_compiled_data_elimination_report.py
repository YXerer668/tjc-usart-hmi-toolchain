from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_compiled_data_elimination_2026-05-21.json"

INPUTS = {
    "clone_vs_local": ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_clone_vs_local_report_2026-05-21.json",
    "pointer_closure": ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_pointer_closure_report_2026-05-21.json",
    "object_local_equivalence": ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_object_local_equivalence_2026-05-21.json",
    "full_page_local_equivalence": ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_full_page_local_equivalence_2026-05-21.json",
    "primary_record_equivalence": ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_primary_record_equivalence_2026-05-21.json",
    "prefix_head_equivalence": ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_prefix_head_equivalence_2026-05-21.json",
    "no_post_mirror_tail": ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_no_post_mirror_service_tail_2026-05-21.json",
}


def main() -> int:
    reports = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in INPUTS.items()}

    payload = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "compiled-data-eliminated",
        "evidence": {
            "authoring_gap_separated": reports["clone_vs_local"]["conclusions"]["official_clone_is_authoring_gap_not_runtime_a_type_enumeration_gap"],
            "pointer_closure_valid": reports["pointer_closure"]["conclusions"]["all_target_rows_keep_basic_pointer_closure"],
            "object_local_user_and_mirror_identical": (
                reports["object_local_equivalence"]["conclusions"]["all_60_actual_user_records_identical"]
                and reports["object_local_equivalence"]["conclusions"]["all_60_actual_mirror_abs_slot_values_identical"]
            ),
            "full_page_local_user_identical": reports["full_page_local_equivalence"]["conclusions"]["all_204_page_local_user_records_identical"],
            "primary_records_identical": reports["primary_record_equivalence"]["conclusions"]["all_five_primary_records_identical"],
            "prefix_head_equivalent_after_generic_multipt_normalization": reports["prefix_head_equivalence"]["conclusions"]["prefix_head_collapses_to_single_page_after_generic_multipt_normalization"],
            "page_event_table_byte_identical": reports["prefix_head_equivalence"]["conclusions"]["page_event_table_is_byte_identical"],
            "no_post_mirror_service_tail": reports["no_post_mirror_tail"]["conclusions"]["no_room_for_meaningful_post_mirror_global_service_table"],
        },
        "conclusions": {
            "compiled_data_envelope_exhausted": all(
                [
                    reports["clone_vs_local"]["conclusions"]["official_clone_is_authoring_gap_not_runtime_a_type_enumeration_gap"],
                    reports["pointer_closure"]["conclusions"]["all_target_rows_keep_basic_pointer_closure"],
                    reports["object_local_equivalence"]["conclusions"]["all_60_actual_user_records_identical"],
                    reports["object_local_equivalence"]["conclusions"]["all_60_actual_mirror_abs_slot_values_identical"],
                    reports["full_page_local_equivalence"]["conclusions"]["all_204_page_local_user_records_identical"],
                    reports["primary_record_equivalence"]["conclusions"]["all_five_primary_records_identical"],
                    reports["prefix_head_equivalence"]["conclusions"]["prefix_head_collapses_to_single_page_after_generic_multipt_normalization"],
                    reports["prefix_head_equivalence"]["conclusions"]["page_event_table_is_byte_identical"],
                    reports["no_post_mirror_tail"]["conclusions"]["no_room_for_meaningful_post_mirror_global_service_table"],
                ]
            ),
            "remaining_gap_is_not_locatable_in_current_object_tail_compiled_data": True,
            "best_current_hypotheses": [
                "page-global runtime registration outside the currently recovered object-tail model",
                "target runtime limitation for page1 A-type enumeration/display despite compiled data parity",
            ],
            "next_priority": "prefer stronger runtime-limitation evidence or a targeted live falsification probe over more page-local byte patching",
        },
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
