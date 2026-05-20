from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))


DEFAULT_OUT = WORKSPACE_ROOT / "examples" / "current_target_full_completion_audit_2026-05-20.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize what is still unfinished for full current-target screen recovery.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON path")
    args = parser.parse_args()

    report = build_report()
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def build_report() -> dict[str, Any]:
    migration = _load_json("examples/advanced_direct_tft_demo/live_smoke_migration_audit_2026-05-20.json")
    lifecycle = _load_json("examples/lifecycle_runtime_smoke/lifecycle_runtime_equivalence_report_2026-05-19.json")
    page1_mapping = _load_json("examples/lifecycle_runtime_smoke/page1_runtime_mapping_reverified_2026-05-20.json")
    binding_matrix = _load_json("examples/lifecycle_runtime_smoke/runtime_binding_matrix_2026-05-20.json")
    case80 = _load_json("examples/advanced_direct_tft_demo/datarecord_textselect_case80_oracle_aligned_live_verified_2026-05-19.json")
    case85 = _load_json("examples/advanced_direct_tft_demo/datarecord_sltext_case85_oracle_aligned_live_verified_2026-05-19.json")
    case83 = _load_json("examples/advanced_direct_tft_demo/datarecord_textselect_button_case83_oracle_aligned_live_verified_2026-05-19.json")
    case83_event = _load_json("examples/advanced_direct_tft_demo/datarecord_textselect_button_case83_event_live_verified_2026-05-20.json")
    feature_status = str((WORKSPACE_ROOT / "FEATURE_STATUS.md").resolve())
    limitations = str((WORKSPACE_ROOT / "CURRENT_TARGET_LIMITATIONS.md").resolve())

    unfinished = [
        {
            "id": "scheduler_lifecycle_general_equivalence",
            "status": "unfinished",
            "scope": "general page load/unload, timer, lifecycle callback binding, and scheduler equivalence",
            "why_unfinished": lifecycle["interpretation"]["narrowing"],
            "blocks": [
                "general page-level logic recovery",
                "multi-page runtime registration recovery",
                "confident expansion beyond narrow object-callback proofs",
            ],
            "evidence": [
                "examples/lifecycle_runtime_smoke/lifecycle_runtime_equivalence_report_2026-05-19.json",
            ],
        },
        {
            "id": "page1_advanced_runtime_binding",
            "status": "unfinished",
            "scope": "page1 page-load scheduling plus corrected-page revalidation of the remaining advanced controls",
            "why_unfinished": [
                "fresh live re-verification proves the recovered case31-style two-page scaffold binds generated or official page1 content on runtime page 0, so earlier runtime page 1 invalid_reference probes were contaminated by a wrong-page assumption",
                "official GUI page1 text-select, official GUI page1 data-record, and official GUI page1 file-stream now all read back correctly on runtime page 0, but sliding-text and file-browser still need corrected-page live revalidation",
                "the local generated page1 load probe now reads p1title.txt correctly on runtime page 0, but the page-level load marker is still not observed when switching back to that runtime page",
            ],
            "blocks": [
                "corrected-page live revalidation for page1 sliding-text",
                "corrected-page live revalidation for page1 file-browser",
                "page1 advanced event dispatch after corrected-page proof",
                "page1 page-load scheduler recovery",
            ],
            "evidence": [
                "examples/lifecycle_runtime_smoke/page1_runtime_mapping_reverified_2026-05-20.json",
                "examples/advanced_direct_tft_demo/page1_sltext_official_gui_live_negative_2026-05-19.json",
                "examples/advanced_direct_tft_demo/page1_filebrowser_official_clone_live_negative_2026-05-20.json",
            ],
        },
        {
            "id": "advanced_control_general_synthesis",
            "status": "unfinished",
            "scope": "arbitrary property synthesis and wider advanced-control mixing beyond the narrow proven shapes",
            "why_unfinished": [
                "current support is still narrow and shape-specific for exact case80/case85/case83 families and selected local runtime-first mixes",
                "broader advanced-control mixing and arbitrary field synthesis remain not claimed in the current target limitations",
            ],
            "blocks": [
                "generic advanced-control layout synthesis",
                "wider same-page advanced mixes",
                "non-shape-specific property authoring",
            ],
            "evidence": [
                "CURRENT_TARGET_LIMITATIONS.md",
                "FEATURE_STATUS.md",
            ],
        },
        {
            "id": "data_record_owned_events_and_broader_datarecord_logic",
            "status": "unfinished",
            "scope": "data-record self-owned events and broader data-record logic combinations",
            "why_unfinished": [
                "only narrow ordinary-button event paths and exact no-event shapes are proven",
                "data-record-owned event behavior remains fail-closed",
            ],
            "blocks": [
                "data-record self events",
                "generic data-record advanced event synthesis",
            ],
            "evidence": [
                "CURRENT_TARGET_LIMITATIONS.md",
                "FEATURE_STATUS.md",
            ],
        },
        {
            "id": "file_stream_self_events_and_general_file_system_logic",
            "status": "unfinished",
            "scope": "file-stream self events, page events, literal open args, and generalized file-system workflows",
            "why_unfinished": [
                "narrow button-wrapper paths are proven, but file-stream self-event and broader file workflows remain fail-closed/not claimed",
                "negative evidence shows fs0.down self paths still do not dispatch correctly",
            ],
            "blocks": [
                "file-stream self events",
                "general file-stream methods",
                "generalized file-system side effects",
            ],
            "evidence": [
                "CURRENT_TARGET_LIMITATIONS.md",
                "FEATURE_STATUS.md",
            ],
        },
        {
            "id": "full_hmi_replacement",
            "status": "unfinished",
            "scope": "full official USART HMI project decompiler/editor replacement",
            "why_unfinished": [
                "the current toolchain edits through a recovered scene model and seed project rather than replacing every official editor feature",
            ],
            "blocks": [
                "full project-level official equivalence",
                "complete .HMI decompile/rebuild",
            ],
            "evidence": [
                feature_status,
            ],
        },
        {
            "id": "cross_model_compiler",
            "status": "unfinished",
            "scope": "generic all-model TFT compiler",
            "why_unfinished": [
                "the current writer remains current-target specific to TJC8048X543_011C / 800x480",
            ],
            "blocks": [
                "cross-model compilation",
                "model-agnostic runtime layout recovery",
            ],
            "evidence": [
                feature_status,
            ],
        },
    ]

    return {
        "schema_version": 1,
        "date": "2026-05-20",
        "target": "TJC8048X543_011C",
        "goal": "recover all controls, page transitions, and logic behavior on the current target screen",
        "current_state": {
            "independent_scene_tft_live_workflow_exists": True,
            "native_scene_smoke_live_proven": True,
            "migration_convergence": migration["summary"],
        },
        "proven_foundations": [
            {
                "id": "exact_case80_no_event",
                "summary": case80["claim"],
                "evidence": "examples/advanced_direct_tft_demo/datarecord_textselect_case80_oracle_aligned_live_verified_2026-05-19.json",
            },
            {
                "id": "exact_case85_no_event",
                "summary": case85["claim"],
                "evidence": "examples/advanced_direct_tft_demo/datarecord_sltext_case85_oracle_aligned_live_verified_2026-05-19.json",
            },
            {
                "id": "exact_case83_no_event",
                "summary": case83["claim"],
                "evidence": "examples/advanced_direct_tft_demo/datarecord_textselect_button_case83_oracle_aligned_live_verified_2026-05-19.json",
            },
            {
                "id": "exact_case83_event",
                "summary": case83_event["claim"],
                "evidence": "examples/advanced_direct_tft_demo/datarecord_textselect_button_case83_event_live_verified_2026-05-20.json",
            },
        ],
        "highest_leverage_unsolved_subsystem": {
            "id": "scheduler_lifecycle_general_equivalence",
            "reason": "page1 runtime-page mapping is now corrected, but page-level lifecycle scheduling is still the common unresolved layer behind load events, timers, and trustworthy multi-page logic recovery",
            "supporting_matrix": "examples/lifecycle_runtime_smoke/runtime_binding_matrix_2026-05-20.json",
            "binding_matrix_summary": binding_matrix["summary"],
        },
        "unfinished": unfinished,
        "evidence_roots": {
            "feature_status": feature_status,
            "current_target_limitations": limitations,
            "lifecycle_runtime_equivalence": "examples/lifecycle_runtime_smoke/lifecycle_runtime_equivalence_report_2026-05-19.json",
            "page1_runtime_mapping_reverified": "examples/lifecycle_runtime_smoke/page1_runtime_mapping_reverified_2026-05-20.json",
            "runtime_binding_matrix": "examples/lifecycle_runtime_smoke/runtime_binding_matrix_2026-05-20.json",
        },
    }


def _load_json(relative_path: str) -> dict[str, Any]:
    path = WORKSPACE_ROOT / relative_path
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
