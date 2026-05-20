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
            "why_unfinished": [
                "fresh live evidence now proves the official case52 page1 load oracle plus rebuilt local page1 load/loadend probes dispatch on corrected runtime page 0 for the minimal fixed 4-byte printh family, including the minimal combined load+loadend case",
                "the new parity report shows why that recovery was needed: the official oracle uses an inline page-load phase wrapper while the older local build emitted a normal page event table",
                "broader general lifecycle equivalence is still unfinished: richer load bodies, load/loadend combinations beyond the fixed 4-byte printh family, timers, and non-probe page-level logic are not yet established as a general recovered family"
            ],
            "blocks": [
                "broader page-level lifecycle generalization",
                "multi-page lifecycle wrapper expansion beyond the fixed 4-byte load-printh family",
                "confident expansion beyond narrow object-callback proofs",
            ],
            "evidence": [
                "examples/lifecycle_runtime_smoke/lifecycle_runtime_equivalence_report_2026-05-19.json",
                "examples/lifecycle_runtime_smoke/page1_load_official_oracle_live_positive_2026-05-20.json",
                "examples/lifecycle_runtime_smoke/page1_load_local_generated_live_verified_2026-05-20.json",
                "examples/lifecycle_runtime_smoke/page1_loadend_local_generated_live_verified_2026-05-20.json",
                "examples/lifecycle_runtime_smoke/page1_load_and_loadend_local_generated_live_verified_2026-05-20.json",
                "examples/lifecycle_runtime_smoke/page1_load_dispatch_parity_report_2026-05-20.json",
            ],
        },
        {
            "id": "page1_advanced_runtime_binding",
            "status": "unfinished",
            "scope": "page1 file-browser direct-runtime enumeration/display gap, official authoring/save gap, plus remaining page1 advanced-event expansion",
            "why_unfinished": [
                "fresh live re-verification proves the recovered case31-style two-page scaffold binds generated or official page1 content on runtime page 0, so earlier runtime page 1 invalid_reference probes were contaminated by a wrong-page assumption",
                "the local direct-TFT page1 file-browser probe now reads back dir/filter/txt on runtime page 0, but a new refresh probe shows qty stays 0 and the camera remains a white surface even after ref fbrowser0 and a page1->page0 cycle",
                "the official GUI page1 file-browser path still fails even earlier and does not preserve an A-type object into 1.pa, so the authoring/save lane is still blocked independently of the local direct-TFT lane",
                "two stricter direct-TFT narrowing probes also stayed negative: renaming the page1 companion objects away from page0 names did not change qty=0 white-surface behavior, and transplanting the exact known-good page0 file-browser cluster onto page1 still stayed qty=0 white-surface. this rules out cross-page companion naming and gross page0-vs-page1 geometry/style mismatch as the primary cause",
                "a fourth probe adds the already recovered fixed 4-byte page1 load wrapper to that exact page0 file-browser cluster and still stays at qty=0 with a white camera surface, so the mere absence of the recovered narrow page1 load wrapper is not the primary cause either",
                "a fifth and sixth probe also stayed negative: page0 control evidence now proves qty is a meaningful enumeration signal because the visible working page0 file-browser returns qty=14, while changing only the page1 fbrowser0 user-record runtime-index bytes and then changing only the actual on-disk second page1 fbrowser0 record event_offset from 0x1E5 to the working single-page on-disk value 0x207 still both leave qty=0 and a white camera surface",
                "a seventh probe still stayed negative even after patching the actual on-disk page1 mirror-page-header tuple itself to the single-page working header values, so the remaining gap is deeper than a one-tuple page-header mismatch",
                "a new tail-prefix decode artifact now shows the deeper multi-page prefix/page-table layer diverges sharply between the working page1 load family and the failing page1 file-browser family, so the next target moves above single-object and one-tuple page-header patches",
                "an eighth probe shows the three +6 prefix-offset fields are necessary for even object binding: reverting just those fields turns page1 fbrowser0.dir/filter/qty/txt into invalid_reference, so the remaining suspect narrows further to the inserted 6-byte page row and deeper page-table semantics rather than the offset trio itself",
                "a ninth probe changes only the inserted page-row count field from 1 to 0 while keeping the offset trio and inserted 6-byte row intact; field binding stays alive but qty remains 0 and the white camera surface remains, so the count field itself is not sufficient either",
                "a tenth and eleventh probe then change the inserted 6-byte row's last two bytes and middle four bytes independently; in both cases page1->sendme still reaches 1 while qty remains 0 and the white camera surface remains, so neither rowindex nor rowhash is sufficient on its own",
            ],
            "blocks": [
                "page1 file-browser direct enumeration/display recovery",
                "page1 file-browser authoring/save recovery",
                "page1 advanced event dispatch after corrected-page proof",
            ],
            "evidence": [
                "examples/lifecycle_runtime_smoke/page1_runtime_mapping_reverified_2026-05-20.json",
                "examples/lifecycle_runtime_smoke/page1_filebrowser_direct_tft_live_verified_2026-05-20.json",
                "examples/lifecycle_runtime_smoke/page1_filebrowser_refresh_probe_2026-05-20.json",
                "examples/lifecycle_runtime_smoke/page0_filebrowser_qty_semantics_probe_2026-05-20.json",
                "examples/lifecycle_runtime_smoke/page1_filebrowser_fbrowser_runtime_index_live_probe_2026-05-20.json",
                "examples/lifecycle_runtime_smoke/page1_filebrowser_mirror_event_offset_live_probe_2026-05-20.json",
                "examples/lifecycle_runtime_smoke/page1_filebrowser_record_diff_2026-05-20.json",
                "examples/lifecycle_runtime_smoke/page1_filebrowser_page_header_diff_2026-05-20.json",
                "examples/lifecycle_runtime_smoke/page1_filebrowser_page_header_live_probe_2026-05-21.json",
                "examples/lifecycle_runtime_smoke/page1_filebrowser_tail_prefix_decode_2026-05-21.json",
                "examples/lifecycle_runtime_smoke/page1_filebrowser_prefix_offset_live_probe_2026-05-21.json",
                "examples/lifecycle_runtime_smoke/page1_filebrowser_prefix_rowcount_live_probe_2026-05-21.json",
                "examples/lifecycle_runtime_smoke/page1_filebrowser_prefix_rowindex_live_probe_2026-05-21.json",
                "examples/lifecycle_runtime_smoke/page1_filebrowser_prefix_rowhash_live_probe_2026-05-21.json",
                "examples/lifecycle_runtime_smoke/page1_filebrowser_narrowing_experiments_2026-05-20.json",
                "examples/lifecycle_runtime_smoke/page1_filebrowser_load_wrapper_live_probe_2026-05-20.json",
                "examples/lifecycle_runtime_smoke/page1_filebrowser_authoring_gap_2026-05-20.json",
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
            "reason": "page1 runtime-page mapping is now corrected and the minimal local page1 load wrapper family is live-proven, but broader general lifecycle equivalence across richer page-level logic is still unresolved; that remains the highest-leverage blocker for trustworthy multi-page logic recovery",
            "supporting_matrix": "examples/lifecycle_runtime_smoke/runtime_binding_matrix_2026-05-20.json",
            "binding_matrix_summary": binding_matrix["summary"],
        },
        "unfinished": unfinished,
        "evidence_roots": {
            "feature_status": feature_status,
            "current_target_limitations": limitations,
            "lifecycle_runtime_equivalence": "examples/lifecycle_runtime_smoke/lifecycle_runtime_equivalence_report_2026-05-19.json",
            "page1_runtime_mapping_reverified": "examples/lifecycle_runtime_smoke/page1_runtime_mapping_reverified_2026-05-20.json",
            "page1_load_official_oracle_live_positive": "examples/lifecycle_runtime_smoke/page1_load_official_oracle_live_positive_2026-05-20.json",
            "page1_load_local_generated_live_verified": "examples/lifecycle_runtime_smoke/page1_load_local_generated_live_verified_2026-05-20.json",
            "page1_loadend_local_generated_live_verified": "examples/lifecycle_runtime_smoke/page1_loadend_local_generated_live_verified_2026-05-20.json",
            "page1_load_and_loadend_local_generated_live_verified": "examples/lifecycle_runtime_smoke/page1_load_and_loadend_local_generated_live_verified_2026-05-20.json",
            "page1_load_dispatch_parity_report": "examples/lifecycle_runtime_smoke/page1_load_dispatch_parity_report_2026-05-20.json",
            "runtime_binding_matrix": "examples/lifecycle_runtime_smoke/runtime_binding_matrix_2026-05-20.json",
        },
    }


def _load_json(relative_path: str) -> dict[str, Any]:
    path = WORKSPACE_ROOT / relative_path
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
