from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from hashlib import sha256


ROOT = Path(__file__).resolve().parents[1]
CURRENT_TARGET_COMPLETION_AUDIT = ROOT / "examples" / "current_target_full_completion_audit_2026-05-20.json"
BUILDER_CALIBRATION_STATUS = ROOT / "examples" / "builder_calibration_status_2026-05-22.json"
NEXT_LIVE_PROBE_BUNDLE = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_next_live_probe_bundle_2026-05-22.json"
LATEST_NEXT_PROBE_RUN_RESULT = ROOT / "reverse_usarthmi" / "next_probe" / "run_next_probe_result_20260522.json"
PAGE1_FILEBROWSER_FRONTIER = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_frontier_2026-05-23.json"
PAGE1_FILEBROWSER_FAMILY_RANKING = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_family_ranking_2026-05-23.json"
PAGE1_FILEBROWSER_NATIVE_INIT_COMPARE_TARGETS = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_native_init_compare_targets_2026-05-23.json"
PAGE1_FILEBROWSER_A_ONLY_COMMON_FIELD_EXHAUSTION = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_a_only_common_field_exhaustion_2026-05-23.json"
PAGE1_FILEBROWSER_HASH_FANOUT_INTERPRETATION = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_hash_fanout_interpretation_2026-05-23.json"
PAGE1_FILEBROWSER_COMMON_FIELD_SHORTLIST = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_common_field_shortlist_2026-05-23.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_SEARCH_FRAME = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_search_frame_2026-05-23.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_HMI_SCRIPT_SURFACE = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_hmi_script_surface_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_COMPILE_PARITY = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_compile_parity_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_CATALOG_DELTA = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_catalog_delta_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_PAGE_GRAPH_TARGETS = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_page_graph_targets_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_PAGE_RESOURCE_MAPPING = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_page_resource_mapping_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_PAGE_COMMAND_OFFSETS = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_page_command_offsets_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_PAGE_BOUNDARY_CANDIDATES = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_page_boundary_candidates_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_CLUSTER_DIFF = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_cluster_diff_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_FIELD_TARGETS = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_field_targets_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_FIELD_REFERENCE_CLUSTERS = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_field_reference_clusters_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_FIELD_0X242E_ANCHOR_RECORDS = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_field_0x242e_anchor_records_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_FIELD_0X242E_TAIL_DIVERGENCE = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_field_0x242e_tail_divergence_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_UNLOAD_BRIDGE_FOLLOWER_CLASSES = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_unload_bridge_follower_classes_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_SINGLETON_METHODCALL_SLOT_REUSE = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_singleton_methodcall_slot_reuse_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_REUSED_METHODCALL_PRELUDE_PAIRS = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_reused_methodcall_prelude_pairs_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_HIDDEN_TAIL_PREANCHOR_CORRIDOR = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_hidden_tail_preanchor_corridor_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_MAIN_PAGE_AUXILIARY_FLOW = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_main_page_auxiliary_flow_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_MAIN_PAGE_AUXILIARY_COMPILED_FLOW = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_main_page_auxiliary_compiled_flow_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_RENAMEFILE_PAGE_SURFACE_AND_ANCHOR = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_renamefile_page_surface_and_anchor_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_RENAMEFILE_EVENT_ANCHORABILITY = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_renamefile_event_anchorability_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_RENAMEFILE_UNIQUE_ANCHORED_SUPPORT_FIELDS = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_renamefile_unique_anchored_support_fields_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_RENAMEFILE_KEYBDAP_CALLSITE_LADDER = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_renamefile_keybdap_callsite_ladder_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_RENAMEFILE_LOCAL_COMPILED_SUPPORT_CORRIDOR = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_renamefile_local_compiled_support_corridor_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_RENAMEFILE_B0_SEMANTIC_FRONTIER = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_renamefile_b0_semantic_frontier_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_RENAMEFILE_COMPILED_FRAGMENT_ABSENCE = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_renamefile_compiled_fragment_absence_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_PREANCHOR_LAUNCH_PAGES_SURFACE_AND_ANCHOR = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_preanchor_launch_pages_surface_and_anchor_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_PREANCHOR_LAUNCH_EVENT_ANCHORABILITY = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_preanchor_launch_event_anchorability_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_PREANCHOR_LAUNCH_COMPILED_NO_ANCHOR_FAMILIES = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_preanchor_launch_compiled_no_anchor_families_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_PREANCHOR_LAUNCH_COMPILED_NO_ANCHOR_FRAGMENT_ABSENCE = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_preanchor_launch_compiled_no_anchor_fragment_absence_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_MYCSVFILE_PAGE_SURFACE_AND_ANCHOR = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_mycsvfile_page_surface_and_anchor_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_MYCSVFILE_EVENT_ANCHORABILITY = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_mycsvfile_event_anchorability_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_MYCSVFILE_COMPILED_NO_ANCHOR_FAMILIES = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_mycsvfile_compiled_no_anchor_families_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_MYCSVFILE_COMPILED_NO_ANCHOR_FRAGMENT_ABSENCE = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_mycsvfile_compiled_no_anchor_fragment_absence_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_CSVADD_PAGE_SURFACE_AND_ANCHOR = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_csvadd_page_surface_and_anchor_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_CSVADD_UNIQUE_ANCHORED_SUBCONTROLS = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_csvadd_unique_anchored_subcontrols_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_CSVADD_EVENT_ANCHORABILITY = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_csvadd_event_anchorability_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_CSVADD_AUTO_FRAGMENT_ABSENCE = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_csvadd_auto_fragment_absence_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_CSVADD_LOCAL_COMPILED_CORRIDOR = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_csvadd_local_compiled_corridor_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_KEYBOARD_HELPER_PAGES_SURFACE_AND_ANCHOR = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_keyboard_helper_pages_surface_and_anchor_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_KEYBOARD_HELPER_EVENT_ANCHORABILITY = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_keyboard_helper_event_anchorability_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_KEYBOARD_HELPER_COMPILED_NO_ANCHOR_FAMILIES = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_keyboard_helper_compiled_no_anchor_families_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_KEYBOARD_HELPER_COMPILED_NO_ANCHOR_FRAGMENT_ABSENCE = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_keyboard_helper_compiled_no_anchor_fragment_absence_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_KEYBOARD_HELPER_CALLSITE_FAMILIES = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_keyboard_helper_callsite_families_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_MAIN_PAGE_ANCHOR = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_main_page_anchor_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_MAIN_PAGE_SLOT_MAPPING = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_main_page_slot_mapping_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_BTNOPENFILE_BRANCH_TARGET_PAGES = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_btnopenfile_branch_target_pages_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_BTNOPENFILE_DEFAULT_TEXTVIEWER_BRANCH = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_btnopenfile_default_textviewer_branch_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_ORACLE_SOURCES = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_oracle_sources_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_LIFECYCLE_SCHEDULER_ORACLE_FRONTIER = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_lifecycle_scheduler_oracle_frontier_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_POST_PRIMARY_SCHEDULER_PAGE_INDEX_BINDING_MATRIX = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_post_primary_scheduler_page_index_binding_matrix_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_POST_PRIMARY_SCHEDULER_NEIGHBORHOOD_SPECIFICITY = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_post_primary_scheduler_neighborhood_specificity_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_SCHEDULER_CANDIDATE_TO_PAGE_GRAPH_CONTAINER_CORRELATION = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_scheduler_candidate_to_page_graph_container_correlation_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_POST_PRIMARY_SCHEDULER_CANDIDATE_ENVELOPE_FIELD_BOUNDARY = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_post_primary_scheduler_candidate_envelope_field_boundary_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_POST_PRIMARY_SCHEDULER_CORE_TO_DUAL_RECORD_OWNER_FAMILY_CORRELATION = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_post_primary_scheduler_core_to_dual_record_owner_family_correlation_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_STRIDE_NEIGHBORHOOD_DUAL_SUBFAMILY = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_stride_neighborhood_dual_subfamily_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_DUAL_SUBFAMILY_TO_STRIDE_BOUNDARY_OWNER_EXTENT = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_dual_subfamily_to_stride_boundary_owner_extent_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SHARED_STRIDE_RUN_SCHEMA_PARTITION = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_shared_stride_run_schema_partition_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_PROGRESSIVE_MARKER_SERIES_MAIN_PAGE_EVENT_TABLE_CORRELATION = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_progressive_marker_series_main_page_event_table_correlation_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_MAIN_PAGE_BUTTON_EVENT_DESCRIPTOR_LADDER = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_main_page_button_event_descriptor_ladder_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_BUTTON_EVENT_LADDER_0X1C_SECONDARY_DESCRIPTOR_CHAIN = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_button_event_ladder_0x1c_secondary_descriptor_chain_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_CHAIN_SCHEMA_PARTITION = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_secondary_descriptor_chain_schema_partition_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_CHAIN_BUTTON_ORDER_CORRELATION = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_secondary_descriptor_chain_button_order_correlation_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_CLASS_TO_LOCAL_STRUCTURE_CORRELATION = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_secondary_descriptor_class_to_local_structure_correlation_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_REFERENCE_LIKE_PAYLOAD_SCOPE = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_secondary_descriptor_reference_like_payload_scope_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_COMPACT_LOCAL_OFFSET_SCOPE = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_secondary_descriptor_compact_local_offset_scope_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_COMPACT_LOCAL_OFFSET_MAIN_PAGE_SLOT_ANCHOR_CORRELATION = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_secondary_descriptor_compact_local_offset_main_page_slot_anchor_corr_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_COMPACT_OFFSET_UNRESOLVED_PAIR_BTNY_NEIGHBORHOOD = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_corr_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_BTNNEWFILE_LOCAL_SLICE = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_secondary_descriptor_btnnewfile_slice_corr_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_BUTTON_LOCAL_SLICE_LADDER = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_btn_local_slice_ladder_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_BTNNEWFILE_LOCAL_SLICE_NEIGHBOR_OVERLAP = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_btnnewfile_local_slice_neighbor_overlap_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_SUBFAMILY = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_mid_triplet_subfamily_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_COMMON_CORE_PARTITION = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_mid_triplet_common_core_partition_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_DIFFERENTIAL_OWNERSHIP = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_mid_triplet_differential_ownership_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_MIXED_PAIR_PARTITION = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_BTNNEWFILE_RENAMEFILE_SUBRUN_PARTITION = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_subrun_partition_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_BTNNEWFILE_RENAMEFILE_ADJACENT_SUBRUN_VALUE_SPLIT = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_adjacent_subrun_value_split_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_BTNNEWFILE_RENAMEFILE_ISOLATED_INDEX4_OUTLIER = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_isolated_index4_outlier_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_BTNDELDIR_RENAMEFILE_SINGLETON_INDEX11 = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_mid_triplet_btndeldir_renamefile_singleton_index11_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_SINGLETON_ENDPOINT_CONTRAST = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_mid_triplet_singleton_endpoint_contrast_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_BTNNEWFILE_RENAMEFILE_INDEX4_NONZERO_PAIR = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_nonzero_pair_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_BTNNEWFILE_RENAMEFILE_INDEX4_BITMASK_RELATION = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_bitmask_relation_2026-05-24.json"
PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_SEARCH_WINDOW = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_membership_registration_search_window_2026-05-24.json"
PAGE1_FILEBROWSER_NO_UPLOAD_RUNTIME = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_no_upload_runtime_2026-05-22.json"
RUNTIME_SOFT_RESET_RECOVERY = ROOT / "examples" / "lifecycle_runtime_smoke" / "runtime_soft_reset_recovery_2026-05-22.json"
HMISAFE_SAMPLE_CHAIN_REPORT = ROOT / "examples" / "hmisafe_sample_chain_2026-05-22.json"
BUILDER_FIELD_MAP = ROOT / "examples" / "builder_field_map_2026-05-22.json"


def _load_json_artifact(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing target status artifact: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"target status artifact is not a JSON object: {path}")
    return payload


def _load_optional_json_artifact(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _load_json_artifact(path)


def current_target_completion_audit() -> dict[str, Any]:
    """Return the checked-in current-target completion audit artifact."""
    return _load_json_artifact(CURRENT_TARGET_COMPLETION_AUDIT)


def builder_calibration_status() -> dict[str, Any]:
    """Return the checked-in builder calibration status artifact."""
    return _load_json_artifact(BUILDER_CALIBRATION_STATUS)


def page1_filebrowser_frontier() -> dict[str, Any]:
    """Return the checked-in page1 file-browser frontier report."""
    return _load_json_artifact(PAGE1_FILEBROWSER_FRONTIER)


def page1_filebrowser_native_init_compare_targets() -> dict[str, Any]:
    """Return the checked-in page1 file-browser native-init compare-targets report."""
    return _load_json_artifact(PAGE1_FILEBROWSER_NATIVE_INIT_COMPARE_TARGETS)


def next_live_probe_bundle() -> dict[str, Any]:
    """Return the checked-in next live-probe bundle for the current target."""
    return _load_json_artifact(NEXT_LIVE_PROBE_BUNDLE)


def target_status_summary() -> dict[str, Any]:
    """Return a compact current-target status summary for handoff artifacts."""
    audit = current_target_completion_audit()
    calibration = builder_calibration_status()
    next_live_probe = next_live_probe_bundle()
    frontier = _load_optional_json_artifact(PAGE1_FILEBROWSER_FRONTIER)
    family_ranking = _load_optional_json_artifact(PAGE1_FILEBROWSER_FAMILY_RANKING)
    compare_targets = _load_optional_json_artifact(PAGE1_FILEBROWSER_NATIVE_INIT_COMPARE_TARGETS)
    common_field_shortlist = _load_optional_json_artifact(PAGE1_FILEBROWSER_COMMON_FIELD_SHORTLIST)
    membership_search_frame = _load_optional_json_artifact(PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_SEARCH_FRAME)
    membership_hmi_script_surface = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_HMI_SCRIPT_SURFACE
    )
    membership_wrapper_compile_parity = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_COMPILE_PARITY
    )
    membership_wrapper_catalog_delta = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_CATALOG_DELTA
    )
    membership_wrapper_page_graph_targets = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_PAGE_GRAPH_TARGETS
    )
    membership_wrapper_page_resource_mapping = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_PAGE_RESOURCE_MAPPING
    )
    membership_wrapper_start_page_command_offsets = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_PAGE_COMMAND_OFFSETS
    )
    membership_wrapper_start_page_boundary_candidates = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_PAGE_BOUNDARY_CANDIDATES
    )
    membership_wrapper_start_record_cluster_diff = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_CLUSTER_DIFF
    )
    membership_wrapper_start_record_field_targets = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_FIELD_TARGETS
    )
    membership_wrapper_start_record_field_reference_clusters = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_FIELD_REFERENCE_CLUSTERS
    )
    membership_wrapper_start_record_field_0x242e_anchor_records = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_FIELD_0X242E_ANCHOR_RECORDS
    )
    membership_wrapper_start_record_field_0x242e_tail_divergence = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_FIELD_0X242E_TAIL_DIVERGENCE
    )
    membership_wrapper_unload_bridge_follower_classes = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_UNLOAD_BRIDGE_FOLLOWER_CLASSES
    )
    membership_wrapper_singleton_methodcall_slot_reuse = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_SINGLETON_METHODCALL_SLOT_REUSE
    )
    membership_wrapper_reused_methodcall_prelude_pairs = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_REUSED_METHODCALL_PRELUDE_PAIRS
    )
    membership_wrapper_hidden_tail_preanchor_corridor = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_HIDDEN_TAIL_PREANCHOR_CORRIDOR
    )
    membership_main_page_auxiliary_flow = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_MAIN_PAGE_AUXILIARY_FLOW
    )
    membership_main_page_auxiliary_compiled_flow = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_MAIN_PAGE_AUXILIARY_COMPILED_FLOW
    )
    membership_renamefile_page_surface_and_anchor = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_RENAMEFILE_PAGE_SURFACE_AND_ANCHOR
    )
    membership_renamefile_event_anchorability = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_RENAMEFILE_EVENT_ANCHORABILITY
    )
    membership_renamefile_unique_anchored_support_fields = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_RENAMEFILE_UNIQUE_ANCHORED_SUPPORT_FIELDS
    )
    membership_renamefile_keybdap_callsite_ladder = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_RENAMEFILE_KEYBDAP_CALLSITE_LADDER
    )
    membership_renamefile_local_compiled_support_corridor = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_RENAMEFILE_LOCAL_COMPILED_SUPPORT_CORRIDOR
    )
    membership_renamefile_b0_semantic_frontier = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_RENAMEFILE_B0_SEMANTIC_FRONTIER
    )
    membership_renamefile_compiled_fragment_absence = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_RENAMEFILE_COMPILED_FRAGMENT_ABSENCE
    )
    membership_preanchor_launch_pages_surface_and_anchor = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_PREANCHOR_LAUNCH_PAGES_SURFACE_AND_ANCHOR
    )
    membership_preanchor_launch_event_anchorability = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_PREANCHOR_LAUNCH_EVENT_ANCHORABILITY
    )
    membership_preanchor_launch_compiled_no_anchor_families = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_PREANCHOR_LAUNCH_COMPILED_NO_ANCHOR_FAMILIES
    )
    membership_preanchor_launch_compiled_no_anchor_fragment_absence = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_PREANCHOR_LAUNCH_COMPILED_NO_ANCHOR_FRAGMENT_ABSENCE
    )
    membership_mycsvfile_page_surface_and_anchor = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_MYCSVFILE_PAGE_SURFACE_AND_ANCHOR
    )
    membership_mycsvfile_event_anchorability = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_MYCSVFILE_EVENT_ANCHORABILITY
    )
    membership_mycsvfile_compiled_no_anchor_families = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_MYCSVFILE_COMPILED_NO_ANCHOR_FAMILIES
    )
    membership_mycsvfile_compiled_no_anchor_fragment_absence = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_MYCSVFILE_COMPILED_NO_ANCHOR_FRAGMENT_ABSENCE
    )
    membership_csvadd_page_surface_and_anchor = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_CSVADD_PAGE_SURFACE_AND_ANCHOR
    )
    membership_csvadd_unique_anchored_subcontrols = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_CSVADD_UNIQUE_ANCHORED_SUBCONTROLS
    )
    membership_csvadd_event_anchorability = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_CSVADD_EVENT_ANCHORABILITY
    )
    membership_csvadd_auto_fragment_absence = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_CSVADD_AUTO_FRAGMENT_ABSENCE
    )
    membership_csvadd_local_compiled_corridor = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_CSVADD_LOCAL_COMPILED_CORRIDOR
    )
    membership_keyboard_helper_pages_surface_and_anchor = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_KEYBOARD_HELPER_PAGES_SURFACE_AND_ANCHOR
    )
    membership_keyboard_helper_event_anchorability = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_KEYBOARD_HELPER_EVENT_ANCHORABILITY
    )
    membership_keyboard_helper_compiled_no_anchor_families = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_KEYBOARD_HELPER_COMPILED_NO_ANCHOR_FAMILIES
    )
    membership_keyboard_helper_compiled_no_anchor_fragment_absence = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_KEYBOARD_HELPER_COMPILED_NO_ANCHOR_FRAGMENT_ABSENCE
    )
    membership_keyboard_helper_callsite_families = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_KEYBOARD_HELPER_CALLSITE_FAMILIES
    )
    membership_wrapper_main_page_anchor = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_MAIN_PAGE_ANCHOR
    )
    membership_wrapper_main_page_slot_mapping = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_MAIN_PAGE_SLOT_MAPPING
    )
    membership_btnopenfile_branch_target_pages = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_BTNOPENFILE_BRANCH_TARGET_PAGES
    )
    membership_btnopenfile_default_textviewer_branch = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_BTNOPENFILE_DEFAULT_TEXTVIEWER_BRANCH
    )
    membership_oracle_sources = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_ORACLE_SOURCES
    )
    membership_lifecycle_scheduler_oracle_frontier = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_LIFECYCLE_SCHEDULER_ORACLE_FRONTIER
    )
    membership_post_primary_scheduler_page_index_binding_matrix = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_POST_PRIMARY_SCHEDULER_PAGE_INDEX_BINDING_MATRIX
    )
    membership_post_primary_scheduler_neighborhood_specificity = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_POST_PRIMARY_SCHEDULER_NEIGHBORHOOD_SPECIFICITY
    )
    membership_scheduler_candidate_to_page_graph_container_correlation = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_SCHEDULER_CANDIDATE_TO_PAGE_GRAPH_CONTAINER_CORRELATION
    )
    membership_post_primary_scheduler_candidate_envelope_field_boundary = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_POST_PRIMARY_SCHEDULER_CANDIDATE_ENVELOPE_FIELD_BOUNDARY
    )
    membership_post_primary_scheduler_core_to_dual_record_owner_family_correlation = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_POST_PRIMARY_SCHEDULER_CORE_TO_DUAL_RECORD_OWNER_FAMILY_CORRELATION
    )
    membership_wrapper_start_record_stride_neighborhood_dual_subfamily = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_STRIDE_NEIGHBORHOOD_DUAL_SUBFAMILY
    )
    membership_wrapper_start_record_dual_subfamily_to_stride_boundary_owner_extent = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_DUAL_SUBFAMILY_TO_STRIDE_BOUNDARY_OWNER_EXTENT
    )
    membership_wrapper_start_record_shared_stride_run_schema_partition = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SHARED_STRIDE_RUN_SCHEMA_PARTITION
    )
    membership_wrapper_start_record_progressive_marker_series_main_page_event_table_correlation = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_PROGRESSIVE_MARKER_SERIES_MAIN_PAGE_EVENT_TABLE_CORRELATION
    )
    membership_wrapper_start_record_main_page_button_event_descriptor_ladder = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_MAIN_PAGE_BUTTON_EVENT_DESCRIPTOR_LADDER
    )
    membership_wrapper_start_record_button_event_ladder_0x1c_secondary_descriptor_chain = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_BUTTON_EVENT_LADDER_0X1C_SECONDARY_DESCRIPTOR_CHAIN
    )
    membership_wrapper_start_record_secondary_descriptor_chain_schema_partition = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_CHAIN_SCHEMA_PARTITION
    )
    membership_wrapper_start_record_secondary_descriptor_chain_button_order_correlation = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_CHAIN_BUTTON_ORDER_CORRELATION
    )
    membership_wrapper_start_record_secondary_descriptor_class_to_local_structure_correlation = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_CLASS_TO_LOCAL_STRUCTURE_CORRELATION
    )
    membership_wrapper_start_record_secondary_descriptor_reference_like_payload_scope = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_REFERENCE_LIKE_PAYLOAD_SCOPE
    )
    membership_wrapper_start_record_secondary_descriptor_compact_local_offset_scope = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_COMPACT_LOCAL_OFFSET_SCOPE
    )
    membership_wrapper_start_record_secondary_descriptor_compact_local_offset_main_page_slot_anchor_correlation = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_COMPACT_LOCAL_OFFSET_MAIN_PAGE_SLOT_ANCHOR_CORRELATION
    )
    membership_wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_COMPACT_OFFSET_UNRESOLVED_PAIR_BTNY_NEIGHBORHOOD
    )
    membership_wrapper_start_record_secondary_descriptor_btnnewfile_local_slice = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_BTNNEWFILE_LOCAL_SLICE
    )
    membership_wrapper_start_record_sidebar_button_local_slice_ladder = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_BUTTON_LOCAL_SLICE_LADDER
    )
    membership_wrapper_start_record_btnnewfile_local_slice_neighbor_overlap = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_BTNNEWFILE_LOCAL_SLICE_NEIGHBOR_OVERLAP
    )
    membership_wrapper_start_record_sidebar_mid_triplet_subfamily = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_SUBFAMILY
    )
    membership_wrapper_start_record_sidebar_mid_triplet_common_core_partition = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_COMMON_CORE_PARTITION
    )
    membership_wrapper_start_record_sidebar_mid_triplet_differential_ownership = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_DIFFERENTIAL_OWNERSHIP
    )
    membership_wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_MIXED_PAIR_PARTITION
    )
    membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_subrun_partition = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_BTNNEWFILE_RENAMEFILE_SUBRUN_PARTITION
    )
    membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_adjacent_subrun_value_split = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_BTNNEWFILE_RENAMEFILE_ADJACENT_SUBRUN_VALUE_SPLIT
    )
    membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_isolated_index4_outlier = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_BTNNEWFILE_RENAMEFILE_ISOLATED_INDEX4_OUTLIER
    )
    membership_wrapper_start_record_sidebar_mid_triplet_btndeldir_renamefile_singleton_index11 = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_BTNDELDIR_RENAMEFILE_SINGLETON_INDEX11
    )
    membership_wrapper_start_record_sidebar_mid_triplet_singleton_endpoint_contrast = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_SINGLETON_ENDPOINT_CONTRAST
    )
    membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_nonzero_pair = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_BTNNEWFILE_RENAMEFILE_INDEX4_NONZERO_PAIR
    )
    membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_bitmask_relation = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_BTNNEWFILE_RENAMEFILE_INDEX4_BITMASK_RELATION
    )
    membership_search_window = _load_optional_json_artifact(
        PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_SEARCH_WINDOW
    )
    latest_next_probe_run = _load_optional_json_artifact(LATEST_NEXT_PROBE_RUN_RESULT)
    page1_no_upload_runtime = _load_optional_json_artifact(PAGE1_FILEBROWSER_NO_UPLOAD_RUNTIME)
    runtime_soft_reset = _load_optional_json_artifact(RUNTIME_SOFT_RESET_RECOVERY)
    hmisafe_sample_chain = _load_optional_json_artifact(HMISAFE_SAMPLE_CHAIN_REPORT)
    builder_field_map = _load_optional_json_artifact(BUILDER_FIELD_MAP)
    domains = calibration.get("domains", {})
    hmisafe = domains.get("hmisafe_finalizer", {})
    fixture_library = domains.get("fixture_library", {})
    page_row = domains.get("page_row_and_runtime_index", {})
    mirror_event_offset = domains.get("mirror_event_offset", {})
    count_candidate = domains.get("filebrowser_count_buffer_candidate", {})

    return {
        "schema_version": 1,
        "target": audit.get("target"),
        "last_updated": audit.get("last_updated"),
        "status": calibration.get("status"),
        "highest_leverage_open_boundary": calibration.get("highest_leverage_open_boundary"),
        "artifacts": {
            "completion_audit": _artifact_ref(CURRENT_TARGET_COMPLETION_AUDIT),
            "builder_calibration": _artifact_ref(BUILDER_CALIBRATION_STATUS),
            "next_live_probe_bundle": _artifact_ref(NEXT_LIVE_PROBE_BUNDLE),
            "latest_next_probe_run_result": _artifact_ref(LATEST_NEXT_PROBE_RUN_RESULT),
            "page1_filebrowser_frontier": _artifact_ref(PAGE1_FILEBROWSER_FRONTIER),
            "page1_filebrowser_family_ranking": _artifact_ref(PAGE1_FILEBROWSER_FAMILY_RANKING),
            "page1_filebrowser_native_init_compare_targets": _artifact_ref(
                PAGE1_FILEBROWSER_NATIVE_INIT_COMPARE_TARGETS
            ),
            "page1_filebrowser_a_only_common_field_exhaustion": _artifact_ref(
                PAGE1_FILEBROWSER_A_ONLY_COMMON_FIELD_EXHAUSTION
            ),
            "page1_filebrowser_hash_fanout_interpretation": _artifact_ref(
                PAGE1_FILEBROWSER_HASH_FANOUT_INTERPRETATION
            ),
            "page1_filebrowser_common_field_shortlist": _artifact_ref(
                PAGE1_FILEBROWSER_COMMON_FIELD_SHORTLIST
            ),
            "page1_filebrowser_membership_registration_search_frame": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_SEARCH_FRAME
            ),
            "page1_filebrowser_membership_registration_hmi_script_surface": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_HMI_SCRIPT_SURFACE
            ),
            "page1_filebrowser_membership_registration_wrapper_compile_parity": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_COMPILE_PARITY
            ),
            "page1_filebrowser_membership_registration_wrapper_catalog_delta": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_CATALOG_DELTA
            ),
            "page1_filebrowser_membership_registration_wrapper_page_graph_targets": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_PAGE_GRAPH_TARGETS
            ),
            "page1_filebrowser_membership_registration_wrapper_page_resource_mapping": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_PAGE_RESOURCE_MAPPING
            ),
            "page1_filebrowser_membership_registration_wrapper_start_page_command_offsets": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_PAGE_COMMAND_OFFSETS
            ),
            "page1_filebrowser_membership_registration_wrapper_start_page_boundary_candidates": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_PAGE_BOUNDARY_CANDIDATES
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_cluster_diff": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_CLUSTER_DIFF
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_field_targets": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_FIELD_TARGETS
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_field_reference_clusters": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_FIELD_REFERENCE_CLUSTERS
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_field_0x242e_anchor_records": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_FIELD_0X242E_ANCHOR_RECORDS
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_field_0x242e_tail_divergence": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_FIELD_0X242E_TAIL_DIVERGENCE
            ),
            "page1_filebrowser_membership_registration_wrapper_unload_bridge_follower_classes": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_UNLOAD_BRIDGE_FOLLOWER_CLASSES
            ),
            "page1_filebrowser_membership_registration_wrapper_singleton_methodcall_slot_reuse": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_SINGLETON_METHODCALL_SLOT_REUSE
            ),
            "page1_filebrowser_membership_registration_wrapper_reused_methodcall_prelude_pairs": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_REUSED_METHODCALL_PRELUDE_PAIRS
            ),
            "page1_filebrowser_membership_registration_wrapper_hidden_tail_preanchor_corridor": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_HIDDEN_TAIL_PREANCHOR_CORRIDOR
            ),
            "page1_filebrowser_membership_registration_main_page_auxiliary_flow": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_MAIN_PAGE_AUXILIARY_FLOW
            ),
            "page1_filebrowser_membership_registration_main_page_auxiliary_compiled_flow": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_MAIN_PAGE_AUXILIARY_COMPILED_FLOW
            ),
            "page1_filebrowser_membership_registration_renamefile_page_surface_and_anchor": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_RENAMEFILE_PAGE_SURFACE_AND_ANCHOR
            ),
            "page1_filebrowser_membership_registration_renamefile_event_anchorability": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_RENAMEFILE_EVENT_ANCHORABILITY
            ),
            "page1_filebrowser_membership_registration_renamefile_unique_anchored_support_fields": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_RENAMEFILE_UNIQUE_ANCHORED_SUPPORT_FIELDS
            ),
            "page1_filebrowser_membership_registration_renamefile_keybdap_callsite_ladder": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_RENAMEFILE_KEYBDAP_CALLSITE_LADDER
            ),
            "page1_filebrowser_membership_registration_renamefile_local_compiled_support_corridor": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_RENAMEFILE_LOCAL_COMPILED_SUPPORT_CORRIDOR
            ),
            "page1_filebrowser_membership_registration_renamefile_b0_semantic_frontier": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_RENAMEFILE_B0_SEMANTIC_FRONTIER
            ),
            "page1_filebrowser_membership_registration_renamefile_compiled_fragment_absence": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_RENAMEFILE_COMPILED_FRAGMENT_ABSENCE
            ),
            "page1_filebrowser_membership_registration_preanchor_launch_pages_surface_and_anchor": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_PREANCHOR_LAUNCH_PAGES_SURFACE_AND_ANCHOR
            ),
            "page1_filebrowser_membership_registration_preanchor_launch_event_anchorability": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_PREANCHOR_LAUNCH_EVENT_ANCHORABILITY
            ),
            "page1_filebrowser_membership_registration_preanchor_launch_compiled_no_anchor_families": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_PREANCHOR_LAUNCH_COMPILED_NO_ANCHOR_FAMILIES
            ),
            "page1_filebrowser_membership_registration_preanchor_launch_compiled_no_anchor_fragment_absence": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_PREANCHOR_LAUNCH_COMPILED_NO_ANCHOR_FRAGMENT_ABSENCE
            ),
            "page1_filebrowser_membership_registration_mycsvfile_page_surface_and_anchor": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_MYCSVFILE_PAGE_SURFACE_AND_ANCHOR
            ),
            "page1_filebrowser_membership_registration_mycsvfile_event_anchorability": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_MYCSVFILE_EVENT_ANCHORABILITY
            ),
            "page1_filebrowser_membership_registration_mycsvfile_compiled_no_anchor_families": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_MYCSVFILE_COMPILED_NO_ANCHOR_FAMILIES
            ),
            "page1_filebrowser_membership_registration_mycsvfile_compiled_no_anchor_fragment_absence": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_MYCSVFILE_COMPILED_NO_ANCHOR_FRAGMENT_ABSENCE
            ),
            "page1_filebrowser_membership_registration_csvadd_page_surface_and_anchor": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_CSVADD_PAGE_SURFACE_AND_ANCHOR
            ),
            "page1_filebrowser_membership_registration_csvadd_unique_anchored_subcontrols": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_CSVADD_UNIQUE_ANCHORED_SUBCONTROLS
            ),
            "page1_filebrowser_membership_registration_csvadd_event_anchorability": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_CSVADD_EVENT_ANCHORABILITY
            ),
            "page1_filebrowser_membership_registration_csvadd_auto_fragment_absence": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_CSVADD_AUTO_FRAGMENT_ABSENCE
            ),
            "page1_filebrowser_membership_registration_csvadd_local_compiled_corridor": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_CSVADD_LOCAL_COMPILED_CORRIDOR
            ),
            "page1_filebrowser_membership_registration_keyboard_helper_pages_surface_and_anchor": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_KEYBOARD_HELPER_PAGES_SURFACE_AND_ANCHOR
            ),
            "page1_filebrowser_membership_registration_keyboard_helper_event_anchorability": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_KEYBOARD_HELPER_EVENT_ANCHORABILITY
            ),
            "page1_filebrowser_membership_registration_keyboard_helper_compiled_no_anchor_families": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_KEYBOARD_HELPER_COMPILED_NO_ANCHOR_FAMILIES
            ),
            "page1_filebrowser_membership_registration_keyboard_helper_compiled_no_anchor_fragment_absence": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_KEYBOARD_HELPER_COMPILED_NO_ANCHOR_FRAGMENT_ABSENCE
            ),
            "page1_filebrowser_membership_registration_keyboard_helper_callsite_families": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_KEYBOARD_HELPER_CALLSITE_FAMILIES
            ),
            "page1_filebrowser_membership_registration_wrapper_main_page_anchor": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_MAIN_PAGE_ANCHOR
            ),
            "page1_filebrowser_membership_registration_wrapper_main_page_slot_mapping": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_MAIN_PAGE_SLOT_MAPPING
            ),
            "page1_filebrowser_membership_registration_btnopenfile_branch_target_pages": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_BTNOPENFILE_BRANCH_TARGET_PAGES
            ),
            "page1_filebrowser_membership_registration_btnopenfile_default_textviewer_branch": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_BTNOPENFILE_DEFAULT_TEXTVIEWER_BRANCH
            ),
            "page1_filebrowser_membership_registration_oracle_sources": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_ORACLE_SOURCES
            ),
            "page1_filebrowser_membership_registration_lifecycle_scheduler_oracle_frontier": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_LIFECYCLE_SCHEDULER_ORACLE_FRONTIER
            ),
            "page1_filebrowser_membership_registration_post_primary_scheduler_page_index_binding_matrix": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_POST_PRIMARY_SCHEDULER_PAGE_INDEX_BINDING_MATRIX
            ),
            "page1_filebrowser_membership_registration_post_primary_scheduler_neighborhood_specificity": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_POST_PRIMARY_SCHEDULER_NEIGHBORHOOD_SPECIFICITY
            ),
            "page1_filebrowser_membership_registration_scheduler_candidate_to_page_graph_container_correlation": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_SCHEDULER_CANDIDATE_TO_PAGE_GRAPH_CONTAINER_CORRELATION
            ),
            "page1_filebrowser_membership_registration_post_primary_scheduler_candidate_envelope_field_boundary": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_POST_PRIMARY_SCHEDULER_CANDIDATE_ENVELOPE_FIELD_BOUNDARY
            ),
            "page1_filebrowser_membership_registration_post_primary_scheduler_core_to_dual_record_owner_family_correlation": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_POST_PRIMARY_SCHEDULER_CORE_TO_DUAL_RECORD_OWNER_FAMILY_CORRELATION
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_stride_neighborhood_dual_subfamily": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_STRIDE_NEIGHBORHOOD_DUAL_SUBFAMILY
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_dual_subfamily_to_stride_boundary_owner_extent": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_DUAL_SUBFAMILY_TO_STRIDE_BOUNDARY_OWNER_EXTENT
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_shared_stride_run_schema_partition": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SHARED_STRIDE_RUN_SCHEMA_PARTITION
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_progressive_marker_series_main_page_event_table_correlation": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_PROGRESSIVE_MARKER_SERIES_MAIN_PAGE_EVENT_TABLE_CORRELATION
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_main_page_button_event_descriptor_ladder": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_MAIN_PAGE_BUTTON_EVENT_DESCRIPTOR_LADDER
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_button_event_ladder_0x1c_secondary_descriptor_chain": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_BUTTON_EVENT_LADDER_0X1C_SECONDARY_DESCRIPTOR_CHAIN
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_secondary_descriptor_chain_schema_partition": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_CHAIN_SCHEMA_PARTITION
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_secondary_descriptor_chain_button_order_correlation": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_CHAIN_BUTTON_ORDER_CORRELATION
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_secondary_descriptor_class_to_local_structure_correlation": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_CLASS_TO_LOCAL_STRUCTURE_CORRELATION
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_secondary_descriptor_reference_like_payload_scope": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_REFERENCE_LIKE_PAYLOAD_SCOPE
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_secondary_descriptor_compact_local_offset_scope": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_COMPACT_LOCAL_OFFSET_SCOPE
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_secondary_descriptor_compact_local_offset_main_page_slot_anchor_correlation": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_COMPACT_LOCAL_OFFSET_MAIN_PAGE_SLOT_ANCHOR_CORRELATION
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_COMPACT_OFFSET_UNRESOLVED_PAIR_BTNY_NEIGHBORHOOD
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_secondary_descriptor_btnnewfile_local_slice": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SECONDARY_DESCRIPTOR_BTNNEWFILE_LOCAL_SLICE
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_button_local_slice_ladder": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_BUTTON_LOCAL_SLICE_LADDER
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_btnnewfile_local_slice_neighbor_overlap": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_BTNNEWFILE_LOCAL_SLICE_NEIGHBOR_OVERLAP
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_mid_triplet_subfamily": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_SUBFAMILY
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_mid_triplet_common_core_partition": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_COMMON_CORE_PARTITION
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_mid_triplet_differential_ownership": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_DIFFERENTIAL_OWNERSHIP
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_MIXED_PAIR_PARTITION
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_subrun_partition": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_BTNNEWFILE_RENAMEFILE_SUBRUN_PARTITION
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_adjacent_subrun_value_split": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_BTNNEWFILE_RENAMEFILE_ADJACENT_SUBRUN_VALUE_SPLIT
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_isolated_index4_outlier": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_BTNNEWFILE_RENAMEFILE_ISOLATED_INDEX4_OUTLIER
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_mid_triplet_btndeldir_renamefile_singleton_index11": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_BTNDELDIR_RENAMEFILE_SINGLETON_INDEX11
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_mid_triplet_singleton_endpoint_contrast": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_SINGLETON_ENDPOINT_CONTRAST
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_nonzero_pair": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_BTNNEWFILE_RENAMEFILE_INDEX4_NONZERO_PAIR
            ),
            "page1_filebrowser_membership_registration_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_bitmask_relation": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_WRAPPER_START_RECORD_SIDEBAR_MID_TRIPLET_BTNNEWFILE_RENAMEFILE_INDEX4_BITMASK_RELATION
            ),
            "page1_filebrowser_membership_registration_search_window": _artifact_ref(
                PAGE1_FILEBROWSER_MEMBERSHIP_REGISTRATION_SEARCH_WINDOW
            ),
            "page1_filebrowser_no_upload_runtime": _artifact_ref(PAGE1_FILEBROWSER_NO_UPLOAD_RUNTIME),
            "runtime_soft_reset_recovery": _artifact_ref(RUNTIME_SOFT_RESET_RECOVERY),
            "hmisafe_sample_chain": _artifact_ref(HMISAFE_SAMPLE_CHAIN_REPORT),
            "builder_field_map": _artifact_ref(BUILDER_FIELD_MAP),
            "hmisafe_finalizer_report": hmisafe.get("finalizer_report"),
        },
        "verification_methods": {
            "hmisafe_finalizer": [
                "x32dbg true-pre capture",
                "byte-level diff against official final TFT",
                "pytest regression tests",
            ],
            "builder_calibration": [
                "official/reference fixture manifest",
                "live COM36 negative/positive probe artifacts where available",
                "HmiSafe checksum validation after candidate byte patches",
            ],
        },
        "current_state": {
            "independent_scene_tft_live_workflow_exists": audit.get("current_state", {}).get(
                "independent_scene_tft_live_workflow_exists"
            ),
            "native_scene_smoke_live_proven": audit.get("current_state", {}).get(
                "native_scene_smoke_live_proven"
            ),
            "builder_calibration_status": calibration.get("status"),
        },
        "fixture_library": {
            "coverage_ok": fixture_library.get("coverage_ok"),
            "case_count": fixture_library.get("case_count"),
        },
        "hmisafe_finalizer": {
            "status": hmisafe.get("status"),
            "pre_to_final_byte_identical": hmisafe.get("pre_to_final_byte_identical"),
            "true_pre_body_unchanged": hmisafe.get("finalizer_report_conclusion", {}).get(
                "true_pre_body_unchanged"
            ),
            "hmisafe_is_resource_packer_on_observed_boundary": hmisafe.get(
                "finalizer_report_conclusion", {}
            ).get("hmisafe_is_resource_packer_on_observed_boundary"),
            "native_values": {
                key: hmisafe.get("native_values", {}).get(key)
                for key in (
                    "input",
                    "output",
                    "size",
                    "mode",
                    "final_crc_type",
                    "model_crc",
                    "header_crc",
                    "header_tail_crc",
                    "file_crc",
                    "footer",
                )
            },
            "mutated_ranges": [
                {"name": "tft_header", "start": 0, "end_exclusive": 400},
                {"name": "eof4_footer", "start_expression": "file_size - 4", "end_expression": "file_size"},
            ],
        },
        "hmisafe_sample_chain": _hmisafe_sample_chain_summary(hmisafe_sample_chain),
        "page_row_and_runtime_index": {
            "status": page_row.get("status"),
            "runtime_index_to_rows": page_row.get("runtime_index_to_rows"),
            "filebrowser_owner_rows": page_row.get("filebrowser_owner_rows"),
            "row_runtime_index_patch_rejected": page_row.get("row_runtime_index_patch_rejected"),
            "row0_object_count_patch_rejected": page_row.get("row0_object_count_patch_rejected"),
        },
        "builder_field_map": _builder_field_map_summary(builder_field_map),
        "mirror_event_offset": {
            "working": mirror_event_offset.get("working"),
            "failing": mirror_event_offset.get("failing"),
            "patched_absolute_offset": mirror_event_offset.get("patched_absolute_offset"),
            "event_offset_patch_rejected": mirror_event_offset.get("event_offset_patch_rejected"),
            "with_pictures_count_patch_rejected": mirror_event_offset.get(
                "with_pictures_count_patch_rejected"
            ),
        },
        "filebrowser_count_buffer_candidate": {
            "status": count_candidate.get("status"),
            "field": count_candidate.get("field"),
            "field_absolute": count_candidate.get("field_absolute"),
            "field_absolute_hex": count_candidate.get("field_absolute_hex"),
            "before": count_candidate.get("before"),
            "after": count_candidate.get("after"),
            "bytes_before": count_candidate.get("bytes_before"),
            "bytes_after": count_candidate.get("bytes_after"),
            "semantic_diff_offsets_excluding_eof4": count_candidate.get(
                "semantic_diff_offsets_excluding_eof4"
            ),
            "hmisafe_header_tail_crc_ok": count_candidate.get("hmisafe_header_tail_crc_ok"),
            "hmisafe_footer_ok": count_candidate.get("hmisafe_footer_ok"),
            "checksum_valid": count_candidate.get("checksum_valid"),
            "live_probe_blocked_until_recovery": count_candidate.get(
                "live_probe_blocked_until_recovery"
            ),
            "live_probe_executed": count_candidate.get("live_probe_executed"),
            "live_probe_outcome": count_candidate.get("live_probe_outcome"),
            "live_probe_observations": count_candidate.get("live_probe_observations"),
            "next_required_frontier": count_candidate.get("next_required_frontier"),
        },
        "page1_filebrowser_narrowing": _page1_filebrowser_narrowing_summary(
            frontier,
            family_ranking,
            compare_targets,
            common_field_shortlist,
            membership_search_frame,
            membership_hmi_script_surface,
            membership_wrapper_compile_parity,
            membership_wrapper_catalog_delta,
            membership_wrapper_page_graph_targets,
            membership_wrapper_page_resource_mapping,
            membership_wrapper_start_page_command_offsets,
            membership_wrapper_start_page_boundary_candidates,
            membership_wrapper_start_record_cluster_diff,
            membership_wrapper_start_record_field_targets,
            membership_wrapper_start_record_field_reference_clusters,
            membership_wrapper_start_record_field_0x242e_anchor_records,
            membership_wrapper_start_record_field_0x242e_tail_divergence,
            membership_wrapper_unload_bridge_follower_classes,
            membership_wrapper_singleton_methodcall_slot_reuse,
            membership_wrapper_reused_methodcall_prelude_pairs,
            membership_wrapper_hidden_tail_preanchor_corridor,
            membership_main_page_auxiliary_flow,
            membership_main_page_auxiliary_compiled_flow,
            membership_renamefile_page_surface_and_anchor,
            membership_renamefile_event_anchorability,
            membership_renamefile_unique_anchored_support_fields,
            membership_renamefile_keybdap_callsite_ladder,
            membership_renamefile_local_compiled_support_corridor,
            membership_renamefile_b0_semantic_frontier,
            membership_renamefile_compiled_fragment_absence,
            membership_preanchor_launch_pages_surface_and_anchor,
            membership_preanchor_launch_event_anchorability,
            membership_preanchor_launch_compiled_no_anchor_families,
            membership_preanchor_launch_compiled_no_anchor_fragment_absence,
            membership_mycsvfile_page_surface_and_anchor,
            membership_mycsvfile_event_anchorability,
            membership_mycsvfile_compiled_no_anchor_families,
            membership_mycsvfile_compiled_no_anchor_fragment_absence,
            membership_csvadd_page_surface_and_anchor,
            membership_csvadd_unique_anchored_subcontrols,
            membership_csvadd_event_anchorability,
            membership_csvadd_auto_fragment_absence,
            membership_csvadd_local_compiled_corridor,
            membership_keyboard_helper_pages_surface_and_anchor,
            membership_keyboard_helper_event_anchorability,
            membership_keyboard_helper_compiled_no_anchor_families,
            membership_keyboard_helper_compiled_no_anchor_fragment_absence,
            membership_keyboard_helper_callsite_families,
            membership_wrapper_main_page_anchor,
            membership_wrapper_main_page_slot_mapping,
            membership_btnopenfile_branch_target_pages,
            membership_btnopenfile_default_textviewer_branch,
            membership_oracle_sources,
            membership_lifecycle_scheduler_oracle_frontier,
            membership_post_primary_scheduler_page_index_binding_matrix,
            membership_post_primary_scheduler_neighborhood_specificity,
            membership_scheduler_candidate_to_page_graph_container_correlation,
            membership_post_primary_scheduler_candidate_envelope_field_boundary,
            membership_post_primary_scheduler_core_to_dual_record_owner_family_correlation,
            membership_wrapper_start_record_stride_neighborhood_dual_subfamily,
            membership_wrapper_start_record_dual_subfamily_to_stride_boundary_owner_extent,
            membership_wrapper_start_record_shared_stride_run_schema_partition,
            membership_wrapper_start_record_progressive_marker_series_main_page_event_table_correlation,
            membership_wrapper_start_record_main_page_button_event_descriptor_ladder,
            membership_wrapper_start_record_button_event_ladder_0x1c_secondary_descriptor_chain,
            membership_wrapper_start_record_secondary_descriptor_chain_schema_partition,
            membership_wrapper_start_record_secondary_descriptor_chain_button_order_correlation,
            membership_wrapper_start_record_secondary_descriptor_class_to_local_structure_correlation,
            membership_wrapper_start_record_secondary_descriptor_reference_like_payload_scope,
            membership_wrapper_start_record_secondary_descriptor_compact_local_offset_scope,
            membership_wrapper_start_record_secondary_descriptor_compact_local_offset_main_page_slot_anchor_correlation,
            membership_wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood,
            membership_wrapper_start_record_secondary_descriptor_btnnewfile_local_slice,
            membership_wrapper_start_record_sidebar_button_local_slice_ladder,
            membership_wrapper_start_record_btnnewfile_local_slice_neighbor_overlap,
            membership_wrapper_start_record_sidebar_mid_triplet_subfamily,
            membership_wrapper_start_record_sidebar_mid_triplet_common_core_partition,
            membership_wrapper_start_record_sidebar_mid_triplet_differential_ownership,
            membership_wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition,
            membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_subrun_partition,
            membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_adjacent_subrun_value_split,
            membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_isolated_index4_outlier,
            membership_wrapper_start_record_sidebar_mid_triplet_btndeldir_renamefile_singleton_index11,
            membership_wrapper_start_record_sidebar_mid_triplet_singleton_endpoint_contrast,
            membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_nonzero_pair,
            membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_bitmask_relation,
            membership_search_window,
        ),
        "next_live_probe_bundle": {
            "status": next_live_probe.get("status"),
            "candidate_tft": {
                "path": next_live_probe.get("candidate_tft", {}).get("path"),
                "sha256": next_live_probe.get("candidate_tft", {}).get("sha256"),
                "checksum_valid": next_live_probe.get("candidate_tft", {}).get("checksum", {}).get("valid"),
                "hmisafe_all_ok": next_live_probe.get("candidate_tft", {}).get("hmisafe", {}).get("all_ok"),
            },
            "manifest_hardware_quarantine_active": next_live_probe.get("safety_gates", {}).get(
                "manifest_hardware_quarantine_active"
            ),
            "safe_to_flash": next_live_probe.get("safety_gates", {}).get("safe_to_flash"),
            "upload_requires_allow_hardware_quarantine": next_live_probe.get("safety_gates", {}).get(
                "upload_requires_allow_hardware_quarantine"
            ),
            "live_probe_allowed_now": next_live_probe.get("safety_gates", {}).get("live_probe_allowed_now"),
            "ready_for_one_controlled_live_probe_after_panel_recovery": next_live_probe.get(
                "conclusions", {}
            ).get("ready_for_one_controlled_live_probe_after_panel_recovery"),
            "historical_live_probe_was_negative": next_live_probe.get("conclusions", {}).get(
                "historical_live_probe_was_negative"
            ),
            "current_frontier": next_live_probe.get("current_frontier"),
            "smoke_expect_json": next_live_probe.get("probe_files", {}).get("smoke_expect_json", {}).get(
                "path"
            ),
            "single_recovery_upload_smoke_command": next_live_probe.get("commands", {}).get(
                "single_recovery_upload_smoke"
            ),
        },
        "next_live_probe_runner": _next_probe_run_summary(latest_next_probe_run),
        "page1_filebrowser_no_upload_runtime": _no_upload_runtime_summary(page1_no_upload_runtime),
        "runtime_soft_reset_recovery": _runtime_recovery_summary(runtime_soft_reset),
        "rejected_patch_matrix": calibration.get("rejected_patch_matrix"),
        "next_actions": calibration.get("next_actions"),
        "not_claimed": [
            "target_status_summary is a handoff summary, not proof that the full long-term goal is complete",
            "live probes remain required for any candidate patch marked blocked_until_panel_recovery",
        ],
    }


def _builder_field_map_summary(result: dict[str, Any] | None) -> dict[str, Any]:
    if result is None:
        return {
            "status": "missing",
            "page_row_runtime_binding": None,
            "filebrowser_membership": None,
            "known_fields": None,
            "negative_patch_boundaries": None,
            "next_probe": None,
        }

    object_membership = result.get("object_membership", {})
    known_fields = result.get("known_fields", {})
    next_probe = result.get("next_probe", {})
    return {
        "status": result.get("status"),
        "page_row_runtime_binding": result.get("page_row_runtime_binding"),
        "filebrowser_membership": object_membership.get("filebrowser"),
        "binding_proxy_checks": object_membership.get("binding_proxy_checks"),
        "known_fields": {
            "filebrowser_mirror_event_offset": known_fields.get("filebrowser_mirror_event_offset"),
            "filebrowser_primary_buff_marker_count_buffer_candidate": known_fields.get(
                "filebrowser_primary_buff_marker_count_buffer_candidate"
            ),
        },
        "negative_patch_boundaries": result.get("negative_patch_boundaries"),
        "next_probe": {
            "status": next_probe.get("status"),
            "candidate_tft_sha256": next_probe.get("candidate_tft", {}).get("sha256"),
            "safe_to_flash": next_probe.get("safe_to_flash"),
            "upload_requires_allow_hardware_quarantine": next_probe.get(
                "upload_requires_allow_hardware_quarantine"
            ),
            "live_probe_allowed_now": next_probe.get("live_probe_allowed_now"),
            "current_frontier": next_probe.get("current_frontier"),
            "historical_live_probe_was_negative": next_probe.get("historical_live_probe_was_negative"),
        },
        "builder_contract": result.get("builder_contract"),
    }


def _page1_filebrowser_narrowing_summary(
    frontier: dict[str, Any] | None,
    family_ranking: dict[str, Any] | None,
    compare_targets: dict[str, Any] | None,
    common_field_shortlist: dict[str, Any] | None,
    membership_search_frame: dict[str, Any] | None,
    membership_hmi_script_surface: dict[str, Any] | None,
    membership_wrapper_compile_parity: dict[str, Any] | None,
    membership_wrapper_catalog_delta: dict[str, Any] | None,
    membership_wrapper_page_graph_targets: dict[str, Any] | None,
    membership_wrapper_page_resource_mapping: dict[str, Any] | None,
    membership_wrapper_start_page_command_offsets: dict[str, Any] | None,
    membership_wrapper_start_page_boundary_candidates: dict[str, Any] | None,
    membership_wrapper_start_record_cluster_diff: dict[str, Any] | None,
    membership_wrapper_start_record_field_targets: dict[str, Any] | None,
    membership_wrapper_start_record_field_reference_clusters: dict[str, Any] | None,
    membership_wrapper_start_record_field_0x242e_anchor_records: dict[str, Any] | None,
    membership_wrapper_start_record_field_0x242e_tail_divergence: dict[str, Any] | None,
    membership_wrapper_unload_bridge_follower_classes: dict[str, Any] | None,
    membership_wrapper_singleton_methodcall_slot_reuse: dict[str, Any] | None,
    membership_wrapper_reused_methodcall_prelude_pairs: dict[str, Any] | None,
    membership_wrapper_hidden_tail_preanchor_corridor: dict[str, Any] | None,
    membership_main_page_auxiliary_flow: dict[str, Any] | None,
    membership_main_page_auxiliary_compiled_flow: dict[str, Any] | None,
    membership_renamefile_page_surface_and_anchor: dict[str, Any] | None,
    membership_renamefile_event_anchorability: dict[str, Any] | None,
    membership_renamefile_unique_anchored_support_fields: dict[str, Any] | None,
    membership_renamefile_keybdap_callsite_ladder: dict[str, Any] | None,
    membership_renamefile_local_compiled_support_corridor: dict[str, Any] | None,
    membership_renamefile_b0_semantic_frontier: dict[str, Any] | None,
    membership_renamefile_compiled_fragment_absence: dict[str, Any] | None,
    membership_preanchor_launch_pages_surface_and_anchor: dict[str, Any] | None,
    membership_preanchor_launch_event_anchorability: dict[str, Any] | None,
    membership_preanchor_launch_compiled_no_anchor_families: dict[str, Any] | None,
    membership_preanchor_launch_compiled_no_anchor_fragment_absence: dict[str, Any] | None,
    membership_mycsvfile_page_surface_and_anchor: dict[str, Any] | None,
    membership_mycsvfile_event_anchorability: dict[str, Any] | None,
    membership_mycsvfile_compiled_no_anchor_families: dict[str, Any] | None,
    membership_mycsvfile_compiled_no_anchor_fragment_absence: dict[str, Any] | None,
    membership_csvadd_page_surface_and_anchor: dict[str, Any] | None,
    membership_csvadd_unique_anchored_subcontrols: dict[str, Any] | None,
    membership_csvadd_event_anchorability: dict[str, Any] | None,
    membership_csvadd_auto_fragment_absence: dict[str, Any] | None,
    membership_csvadd_local_compiled_corridor: dict[str, Any] | None,
    membership_keyboard_helper_pages_surface_and_anchor: dict[str, Any] | None,
    membership_keyboard_helper_event_anchorability: dict[str, Any] | None,
    membership_keyboard_helper_compiled_no_anchor_families: dict[str, Any] | None,
    membership_keyboard_helper_compiled_no_anchor_fragment_absence: dict[str, Any] | None,
    membership_keyboard_helper_callsite_families: dict[str, Any] | None,
    membership_wrapper_main_page_anchor: dict[str, Any] | None,
    membership_wrapper_main_page_slot_mapping: dict[str, Any] | None,
    membership_btnopenfile_branch_target_pages: dict[str, Any] | None,
    membership_btnopenfile_default_textviewer_branch: dict[str, Any] | None,
    membership_oracle_sources: dict[str, Any] | None,
    membership_lifecycle_scheduler_oracle_frontier: dict[str, Any] | None,
    membership_post_primary_scheduler_page_index_binding_matrix: dict[str, Any] | None,
    membership_post_primary_scheduler_neighborhood_specificity: dict[str, Any] | None,
    membership_scheduler_candidate_to_page_graph_container_correlation: dict[str, Any] | None,
    membership_post_primary_scheduler_candidate_envelope_field_boundary: dict[str, Any] | None,
    membership_post_primary_scheduler_core_to_dual_record_owner_family_correlation: dict[str, Any] | None,
    membership_wrapper_start_record_stride_neighborhood_dual_subfamily: dict[str, Any] | None,
    membership_wrapper_start_record_dual_subfamily_to_stride_boundary_owner_extent: dict[str, Any] | None,
    membership_wrapper_start_record_shared_stride_run_schema_partition: dict[str, Any] | None,
    membership_wrapper_start_record_progressive_marker_series_main_page_event_table_correlation: dict[str, Any] | None,
    membership_wrapper_start_record_main_page_button_event_descriptor_ladder: dict[str, Any] | None,
    membership_wrapper_start_record_button_event_ladder_0x1c_secondary_descriptor_chain: dict[str, Any] | None,
    membership_wrapper_start_record_secondary_descriptor_chain_schema_partition: dict[str, Any] | None,
    membership_wrapper_start_record_secondary_descriptor_chain_button_order_correlation: dict[str, Any] | None,
    membership_wrapper_start_record_secondary_descriptor_class_to_local_structure_correlation: dict[str, Any] | None,
    membership_wrapper_start_record_secondary_descriptor_reference_like_payload_scope: dict[str, Any] | None,
    membership_wrapper_start_record_secondary_descriptor_compact_local_offset_scope: dict[str, Any] | None,
    membership_wrapper_start_record_secondary_descriptor_compact_local_offset_main_page_slot_anchor_correlation: dict[str, Any] | None,
    membership_wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood: dict[str, Any] | None,
    membership_wrapper_start_record_secondary_descriptor_btnnewfile_local_slice: dict[str, Any] | None,
    membership_wrapper_start_record_sidebar_button_local_slice_ladder: dict[str, Any] | None,
    membership_wrapper_start_record_btnnewfile_local_slice_neighbor_overlap: dict[str, Any] | None,
    membership_wrapper_start_record_sidebar_mid_triplet_subfamily: dict[str, Any] | None,
    membership_wrapper_start_record_sidebar_mid_triplet_common_core_partition: dict[str, Any] | None,
    membership_wrapper_start_record_sidebar_mid_triplet_differential_ownership: dict[str, Any] | None,
    membership_wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition: dict[str, Any] | None,
    membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_subrun_partition: dict[str, Any] | None,
    membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_adjacent_subrun_value_split: dict[str, Any] | None,
    membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_isolated_index4_outlier: dict[str, Any] | None,
    membership_wrapper_start_record_sidebar_mid_triplet_btndeldir_renamefile_singleton_index11: dict[str, Any] | None,
    membership_wrapper_start_record_sidebar_mid_triplet_singleton_endpoint_contrast: dict[str, Any] | None,
    membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_nonzero_pair: dict[str, Any] | None,
    membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_bitmask_relation: dict[str, Any] | None,
    membership_search_window: dict[str, Any] | None,
) -> dict[str, Any]:
    if (
        frontier is None
        and family_ranking is None
        and compare_targets is None
        and common_field_shortlist is None
        and membership_search_frame is None
        and membership_hmi_script_surface is None
        and membership_wrapper_compile_parity is None
        and membership_wrapper_catalog_delta is None
        and membership_wrapper_page_graph_targets is None
        and membership_wrapper_page_resource_mapping is None
        and membership_wrapper_start_page_command_offsets is None
        and membership_wrapper_start_page_boundary_candidates is None
        and membership_wrapper_start_record_cluster_diff is None
        and membership_wrapper_start_record_field_targets is None
        and membership_wrapper_start_record_field_reference_clusters is None
        and membership_wrapper_start_record_field_0x242e_anchor_records is None
        and membership_wrapper_start_record_field_0x242e_tail_divergence is None
        and membership_wrapper_unload_bridge_follower_classes is None
        and membership_wrapper_singleton_methodcall_slot_reuse is None
        and membership_wrapper_reused_methodcall_prelude_pairs is None
        and membership_wrapper_hidden_tail_preanchor_corridor is None
        and membership_main_page_auxiliary_flow is None
        and membership_main_page_auxiliary_compiled_flow is None
        and membership_renamefile_page_surface_and_anchor is None
        and membership_renamefile_event_anchorability is None
        and membership_renamefile_unique_anchored_support_fields is None
        and membership_renamefile_keybdap_callsite_ladder is None
        and membership_renamefile_local_compiled_support_corridor is None
        and membership_renamefile_b0_semantic_frontier is None
        and membership_renamefile_compiled_fragment_absence is None
        and membership_preanchor_launch_pages_surface_and_anchor is None
        and membership_preanchor_launch_event_anchorability is None
        and membership_preanchor_launch_compiled_no_anchor_families is None
        and membership_preanchor_launch_compiled_no_anchor_fragment_absence is None
        and membership_mycsvfile_page_surface_and_anchor is None
        and membership_mycsvfile_event_anchorability is None
        and membership_mycsvfile_compiled_no_anchor_families is None
        and membership_mycsvfile_compiled_no_anchor_fragment_absence is None
        and membership_csvadd_page_surface_and_anchor is None
        and membership_csvadd_unique_anchored_subcontrols is None
        and membership_csvadd_event_anchorability is None
        and membership_csvadd_auto_fragment_absence is None
        and membership_csvadd_local_compiled_corridor is None
        and membership_keyboard_helper_pages_surface_and_anchor is None
        and membership_keyboard_helper_event_anchorability is None
        and membership_keyboard_helper_compiled_no_anchor_families is None
        and membership_keyboard_helper_compiled_no_anchor_fragment_absence is None
        and membership_keyboard_helper_callsite_families is None
        and membership_wrapper_main_page_anchor is None
        and membership_wrapper_main_page_slot_mapping is None
        and membership_btnopenfile_branch_target_pages is None
        and membership_btnopenfile_default_textviewer_branch is None
        and membership_oracle_sources is None
        and membership_lifecycle_scheduler_oracle_frontier is None
        and membership_post_primary_scheduler_page_index_binding_matrix is None
        and membership_post_primary_scheduler_neighborhood_specificity is None
        and membership_scheduler_candidate_to_page_graph_container_correlation is None
        and membership_post_primary_scheduler_candidate_envelope_field_boundary is None
        and membership_post_primary_scheduler_core_to_dual_record_owner_family_correlation is None
        and membership_wrapper_start_record_stride_neighborhood_dual_subfamily is None
        and membership_wrapper_start_record_dual_subfamily_to_stride_boundary_owner_extent is None
        and membership_wrapper_start_record_shared_stride_run_schema_partition is None
        and membership_wrapper_start_record_progressive_marker_series_main_page_event_table_correlation is None
        and membership_wrapper_start_record_main_page_button_event_descriptor_ladder is None
        and membership_wrapper_start_record_button_event_ladder_0x1c_secondary_descriptor_chain is None
        and membership_wrapper_start_record_secondary_descriptor_chain_schema_partition is None
        and membership_wrapper_start_record_secondary_descriptor_chain_button_order_correlation is None
        and membership_wrapper_start_record_secondary_descriptor_class_to_local_structure_correlation is None
        and membership_wrapper_start_record_secondary_descriptor_reference_like_payload_scope is None
        and membership_wrapper_start_record_secondary_descriptor_compact_local_offset_scope is None
        and membership_wrapper_start_record_secondary_descriptor_compact_local_offset_main_page_slot_anchor_correlation is None
        and membership_wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood is None
        and membership_wrapper_start_record_secondary_descriptor_btnnewfile_local_slice is None
        and membership_wrapper_start_record_sidebar_button_local_slice_ladder is None
        and membership_wrapper_start_record_btnnewfile_local_slice_neighbor_overlap is None
        and membership_wrapper_start_record_sidebar_mid_triplet_subfamily is None
        and membership_wrapper_start_record_sidebar_mid_triplet_common_core_partition is None
        and membership_wrapper_start_record_sidebar_mid_triplet_differential_ownership is None
        and membership_wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition is None
        and membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_subrun_partition is None
        and membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_adjacent_subrun_value_split is None
        and membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_isolated_index4_outlier is None
        and membership_wrapper_start_record_sidebar_mid_triplet_btndeldir_renamefile_singleton_index11 is None
        and membership_wrapper_start_record_sidebar_mid_triplet_singleton_endpoint_contrast is None
        and membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_nonzero_pair is None
        and membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_bitmask_relation is None
        and membership_search_window is None
    ):
        return {
            "status": "missing",
            "frontier": None,
            "top_ranked_family": None,
            "compare_targets_status": None,
            "common_field_shortlist_status": None,
            "membership_search_frame_status": None,
            "membership_hmi_script_surface_status": None,
            "membership_wrapper_compile_parity_status": None,
            "membership_wrapper_catalog_delta_status": None,
            "membership_wrapper_page_graph_targets_status": None,
            "membership_wrapper_page_resource_mapping_status": None,
            "membership_wrapper_start_page_command_offsets_status": None,
            "membership_wrapper_start_page_boundary_candidates_status": None,
            "membership_wrapper_start_record_cluster_diff_status": None,
            "membership_wrapper_start_record_field_targets_status": None,
            "membership_wrapper_start_record_field_reference_clusters_status": None,
            "membership_wrapper_start_record_field_0x242e_anchor_records_status": None,
            "membership_wrapper_start_record_field_0x242e_tail_divergence_status": None,
            "membership_wrapper_unload_bridge_follower_classes_status": None,
            "membership_wrapper_singleton_methodcall_slot_reuse_status": None,
            "membership_wrapper_reused_methodcall_prelude_pairs_status": None,
            "membership_wrapper_hidden_tail_preanchor_corridor_status": None,
            "membership_main_page_auxiliary_flow_status": None,
            "membership_main_page_auxiliary_compiled_flow_status": None,
            "membership_registration_renamefile_page_surface_and_anchor_status": None,
            "membership_registration_renamefile_event_anchorability_status": None,
            "membership_registration_renamefile_unique_anchored_support_fields_status": None,
            "membership_registration_renamefile_compiled_fragment_absence_status": None,
            "membership_registration_preanchor_launch_pages_surface_and_anchor_status": None,
            "membership_registration_preanchor_launch_event_anchorability_status": None,
            "membership_registration_preanchor_launch_compiled_no_anchor_families_status": None,
            "membership_registration_preanchor_launch_compiled_no_anchor_fragment_absence_status": None,
            "membership_registration_mycsvfile_page_surface_and_anchor_status": None,
            "membership_registration_mycsvfile_event_anchorability_status": None,
            "membership_registration_mycsvfile_compiled_no_anchor_families_status": None,
            "membership_registration_mycsvfile_compiled_no_anchor_fragment_absence_status": None,
            "membership_registration_csvadd_page_surface_and_anchor_status": None,
            "membership_registration_csvadd_unique_anchored_subcontrols_status": None,
            "membership_registration_csvadd_event_anchorability_status": None,
            "membership_registration_csvadd_auto_fragment_absence_status": None,
            "membership_registration_csvadd_local_compiled_corridor_status": None,
            "membership_registration_keyboard_helper_pages_surface_and_anchor_status": None,
            "membership_registration_keyboard_helper_event_anchorability_status": None,
            "membership_registration_keyboard_helper_compiled_no_anchor_families_status": None,
            "membership_registration_keyboard_helper_compiled_no_anchor_fragment_absence_status": None,
            "membership_registration_keyboard_helper_callsite_families_status": None,
            "membership_wrapper_main_page_anchor_status": None,
            "membership_wrapper_main_page_slot_mapping_status": None,
            "membership_btnopenfile_branch_target_pages_status": None,
            "membership_btnopenfile_default_textviewer_branch_status": None,
            "membership_oracle_sources_status": None,
            "membership_post_primary_scheduler_candidate_envelope_field_boundary_status": None,
            "membership_post_primary_scheduler_core_to_dual_record_owner_family_correlation_status": None,
            "membership_registration_wrapper_start_record_stride_neighborhood_dual_subfamily_status": None,
            "membership_registration_wrapper_start_record_dual_subfamily_to_stride_boundary_owner_extent_status": None,
            "membership_registration_wrapper_start_record_shared_stride_run_schema_partition_status": None,
            "membership_registration_wrapper_start_record_progressive_marker_series_main_page_event_table_correlation_status": None,
            "membership_registration_wrapper_start_record_main_page_button_event_descriptor_ladder_status": None,
            "membership_registration_wrapper_start_record_button_event_ladder_0x1c_secondary_descriptor_chain_status": None,
            "membership_registration_wrapper_start_record_secondary_descriptor_chain_schema_partition_status": None,
            "membership_registration_wrapper_start_record_secondary_descriptor_chain_button_order_correlation_status": None,
            "membership_registration_wrapper_start_record_secondary_descriptor_class_to_local_structure_correlation_status": None,
            "membership_registration_wrapper_start_record_secondary_descriptor_reference_like_payload_scope_status": None,
            "membership_registration_wrapper_start_record_secondary_descriptor_compact_local_offset_scope_status": None,
            "membership_registration_wrapper_start_record_secondary_descriptor_compact_local_offset_main_page_slot_anchor_correlation_status": None,
            "membership_registration_wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood_status": None,
            "membership_registration_wrapper_start_record_secondary_descriptor_btnnewfile_local_slice_status": None,
            "membership_registration_wrapper_start_record_sidebar_button_local_slice_ladder_status": None,
            "membership_registration_wrapper_start_record_btnnewfile_local_slice_neighbor_overlap_status": None,
            "membership_registration_wrapper_start_record_sidebar_mid_triplet_subfamily_status": None,
            "membership_registration_wrapper_start_record_sidebar_mid_triplet_common_core_partition_status": None,
            "membership_registration_wrapper_start_record_sidebar_mid_triplet_differential_ownership_status": None,
            "membership_registration_wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition_status": None,
            "membership_registration_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_subrun_partition_status": None,
            "membership_registration_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_adjacent_subrun_value_split_status": None,
            "membership_registration_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_isolated_index4_outlier_status": None,
            "membership_registration_wrapper_start_record_sidebar_mid_triplet_btndeldir_renamefile_singleton_index11_status": None,
            "membership_registration_wrapper_start_record_sidebar_mid_triplet_singleton_endpoint_contrast_status": None,
            "membership_registration_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_nonzero_pair_status": None,
            "membership_registration_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_bitmask_relation_status": None,
            "membership_search_window_status": None,
            "open_common_families": None,
            "explicit_non_candidates": None,
        }

    shortlist = common_field_shortlist or {}
    ranked_open = shortlist.get("ranked_open_shortlist") or []
    deprioritized = shortlist.get("deprioritized_secondary_families") or []
    return {
        "status": "available",
        "frontier": {
            "id": None if frontier is None else frontier.get("frontier_id"),
            "verdict": None if frontier is None else frontier.get("frontier_verdict"),
        },
        "top_ranked_family": None if family_ranking is None else family_ranking.get("top_ranked_family"),
        "compare_targets_status": None if compare_targets is None else compare_targets.get("status"),
        "common_field_shortlist_status": shortlist.get("status"),
        "membership_search_frame_status": None if membership_search_frame is None else membership_search_frame.get("status"),
        "membership_hmi_script_surface_status": None
        if membership_hmi_script_surface is None
        else membership_hmi_script_surface.get("status"),
        "membership_wrapper_compile_parity_status": None
        if membership_wrapper_compile_parity is None
        else membership_wrapper_compile_parity.get("status"),
        "membership_wrapper_catalog_delta_status": None
        if membership_wrapper_catalog_delta is None
        else membership_wrapper_catalog_delta.get("status"),
        "membership_wrapper_page_graph_targets_status": None
        if membership_wrapper_page_graph_targets is None
        else membership_wrapper_page_graph_targets.get("status"),
        "membership_wrapper_page_resource_mapping_status": None
        if membership_wrapper_page_resource_mapping is None
        else membership_wrapper_page_resource_mapping.get("status"),
        "membership_wrapper_start_page_command_offsets_status": None
        if membership_wrapper_start_page_command_offsets is None
        else membership_wrapper_start_page_command_offsets.get("status"),
        "membership_wrapper_start_page_boundary_candidates_status": None
        if membership_wrapper_start_page_boundary_candidates is None
        else membership_wrapper_start_page_boundary_candidates.get("status"),
        "membership_wrapper_start_record_cluster_diff_status": None
        if membership_wrapper_start_record_cluster_diff is None
        else membership_wrapper_start_record_cluster_diff.get("status"),
        "membership_wrapper_start_record_field_targets_status": None
        if membership_wrapper_start_record_field_targets is None
        else membership_wrapper_start_record_field_targets.get("status"),
        "membership_wrapper_start_record_field_reference_clusters_status": None
        if membership_wrapper_start_record_field_reference_clusters is None
        else membership_wrapper_start_record_field_reference_clusters.get("status"),
        "membership_wrapper_start_record_field_0x242e_anchor_records_status": None
        if membership_wrapper_start_record_field_0x242e_anchor_records is None
        else membership_wrapper_start_record_field_0x242e_anchor_records.get("status"),
        "membership_wrapper_start_record_field_0x242e_tail_divergence_status": None
        if membership_wrapper_start_record_field_0x242e_tail_divergence is None
        else membership_wrapper_start_record_field_0x242e_tail_divergence.get("status"),
        "membership_wrapper_unload_bridge_follower_classes_status": None
        if membership_wrapper_unload_bridge_follower_classes is None
        else membership_wrapper_unload_bridge_follower_classes.get("status"),
        "membership_wrapper_singleton_methodcall_slot_reuse_status": None
        if membership_wrapper_singleton_methodcall_slot_reuse is None
        else membership_wrapper_singleton_methodcall_slot_reuse.get("status"),
        "membership_wrapper_reused_methodcall_prelude_pairs_status": None
        if membership_wrapper_reused_methodcall_prelude_pairs is None
        else membership_wrapper_reused_methodcall_prelude_pairs.get("status"),
        "membership_wrapper_hidden_tail_preanchor_corridor_status": None
        if membership_wrapper_hidden_tail_preanchor_corridor is None
        else membership_wrapper_hidden_tail_preanchor_corridor.get("status"),
        "membership_main_page_auxiliary_flow_status": None
        if membership_main_page_auxiliary_flow is None
        else membership_main_page_auxiliary_flow.get("status"),
        "membership_main_page_auxiliary_compiled_flow_status": None
        if membership_main_page_auxiliary_compiled_flow is None
        else membership_main_page_auxiliary_compiled_flow.get("status"),
        "membership_registration_renamefile_page_surface_and_anchor_status": None
        if membership_renamefile_page_surface_and_anchor is None
        else membership_renamefile_page_surface_and_anchor.get("status"),
        "membership_registration_renamefile_event_anchorability_status": None
        if membership_renamefile_event_anchorability is None
        else membership_renamefile_event_anchorability.get("status"),
        "membership_registration_renamefile_unique_anchored_support_fields_status": None
        if membership_renamefile_unique_anchored_support_fields is None
        else membership_renamefile_unique_anchored_support_fields.get("status"),
        "membership_registration_renamefile_keybdap_callsite_ladder_status": None
        if membership_renamefile_keybdap_callsite_ladder is None
        else membership_renamefile_keybdap_callsite_ladder.get("status"),
        "membership_registration_renamefile_local_compiled_support_corridor_status": None
        if membership_renamefile_local_compiled_support_corridor is None
        else membership_renamefile_local_compiled_support_corridor.get("status"),
        "membership_registration_renamefile_b0_semantic_frontier_status": None
        if membership_renamefile_b0_semantic_frontier is None
        else membership_renamefile_b0_semantic_frontier.get("status"),
        "membership_registration_renamefile_compiled_fragment_absence_status": None
        if membership_renamefile_compiled_fragment_absence is None
        else membership_renamefile_compiled_fragment_absence.get("status"),
        "membership_registration_preanchor_launch_pages_surface_and_anchor_status": None
        if membership_preanchor_launch_pages_surface_and_anchor is None
        else membership_preanchor_launch_pages_surface_and_anchor.get("status"),
        "membership_registration_preanchor_launch_event_anchorability_status": None
        if membership_preanchor_launch_event_anchorability is None
        else membership_preanchor_launch_event_anchorability.get("status"),
        "membership_registration_preanchor_launch_compiled_no_anchor_families_status": None
        if membership_preanchor_launch_compiled_no_anchor_families is None
        else membership_preanchor_launch_compiled_no_anchor_families.get("status"),
        "membership_registration_preanchor_launch_compiled_no_anchor_fragment_absence_status": None
        if membership_preanchor_launch_compiled_no_anchor_fragment_absence is None
        else membership_preanchor_launch_compiled_no_anchor_fragment_absence.get("status"),
        "membership_registration_mycsvfile_page_surface_and_anchor_status": None
        if membership_mycsvfile_page_surface_and_anchor is None
        else membership_mycsvfile_page_surface_and_anchor.get("status"),
        "membership_registration_mycsvfile_event_anchorability_status": None
        if membership_mycsvfile_event_anchorability is None
        else membership_mycsvfile_event_anchorability.get("status"),
        "membership_registration_mycsvfile_compiled_no_anchor_families_status": None
        if membership_mycsvfile_compiled_no_anchor_families is None
        else membership_mycsvfile_compiled_no_anchor_families.get("status"),
        "membership_registration_csvadd_page_surface_and_anchor_status": None
        if membership_csvadd_page_surface_and_anchor is None
        else membership_csvadd_page_surface_and_anchor.get("status"),
        "membership_registration_csvadd_unique_anchored_subcontrols_status": None
        if membership_csvadd_unique_anchored_subcontrols is None
        else membership_csvadd_unique_anchored_subcontrols.get("status"),
        "membership_registration_csvadd_event_anchorability_status": None
        if membership_csvadd_event_anchorability is None
        else membership_csvadd_event_anchorability.get("status"),
        "membership_registration_csvadd_auto_fragment_absence_status": None
        if membership_csvadd_auto_fragment_absence is None
        else membership_csvadd_auto_fragment_absence.get("status"),
        "membership_registration_csvadd_local_compiled_corridor_status": None
        if membership_csvadd_local_compiled_corridor is None
        else membership_csvadd_local_compiled_corridor.get("status"),
        "membership_registration_keyboard_helper_pages_surface_and_anchor_status": None
        if membership_keyboard_helper_pages_surface_and_anchor is None
        else membership_keyboard_helper_pages_surface_and_anchor.get("status"),
        "membership_registration_keyboard_helper_event_anchorability_status": None
        if membership_keyboard_helper_event_anchorability is None
        else membership_keyboard_helper_event_anchorability.get("status"),
        "membership_registration_keyboard_helper_compiled_no_anchor_families_status": None
        if membership_keyboard_helper_compiled_no_anchor_families is None
        else membership_keyboard_helper_compiled_no_anchor_families.get("status"),
        "membership_registration_keyboard_helper_compiled_no_anchor_fragment_absence_status": None
        if membership_keyboard_helper_compiled_no_anchor_fragment_absence is None
        else membership_keyboard_helper_compiled_no_anchor_fragment_absence.get("status"),
        "membership_registration_keyboard_helper_callsite_families_status": None
        if membership_keyboard_helper_callsite_families is None
        else membership_keyboard_helper_callsite_families.get("status"),
        "membership_wrapper_main_page_anchor_status": None
        if membership_wrapper_main_page_anchor is None
        else membership_wrapper_main_page_anchor.get("status"),
        "membership_wrapper_main_page_slot_mapping_status": None
        if membership_wrapper_main_page_slot_mapping is None
        else membership_wrapper_main_page_slot_mapping.get("status"),
        "membership_btnopenfile_branch_target_pages_status": None
        if membership_btnopenfile_branch_target_pages is None
        else membership_btnopenfile_branch_target_pages.get("status"),
        "membership_btnopenfile_default_textviewer_branch_status": None
        if membership_btnopenfile_default_textviewer_branch is None
        else membership_btnopenfile_default_textviewer_branch.get("status"),
        "membership_oracle_sources_status": None if membership_oracle_sources is None else membership_oracle_sources.get("status"),
        "membership_lifecycle_scheduler_oracle_frontier_status": None
        if membership_lifecycle_scheduler_oracle_frontier is None
        else membership_lifecycle_scheduler_oracle_frontier.get("status"),
        "membership_post_primary_scheduler_page_index_binding_matrix_status": None
        if membership_post_primary_scheduler_page_index_binding_matrix is None
        else membership_post_primary_scheduler_page_index_binding_matrix.get("status"),
        "membership_post_primary_scheduler_neighborhood_specificity_status": None
        if membership_post_primary_scheduler_neighborhood_specificity is None
        else membership_post_primary_scheduler_neighborhood_specificity.get("status"),
        "membership_scheduler_candidate_to_page_graph_container_correlation_status": None
        if membership_scheduler_candidate_to_page_graph_container_correlation is None
        else membership_scheduler_candidate_to_page_graph_container_correlation.get("status"),
        "membership_post_primary_scheduler_candidate_envelope_field_boundary_status": None
        if membership_post_primary_scheduler_candidate_envelope_field_boundary is None
        else membership_post_primary_scheduler_candidate_envelope_field_boundary.get("status"),
        "membership_post_primary_scheduler_core_to_dual_record_owner_family_correlation_status": None
        if membership_post_primary_scheduler_core_to_dual_record_owner_family_correlation is None
        else membership_post_primary_scheduler_core_to_dual_record_owner_family_correlation.get("status"),
        "membership_registration_wrapper_start_record_stride_neighborhood_dual_subfamily_status": None
        if membership_wrapper_start_record_stride_neighborhood_dual_subfamily is None
        else membership_wrapper_start_record_stride_neighborhood_dual_subfamily.get("status"),
        "membership_registration_wrapper_start_record_dual_subfamily_to_stride_boundary_owner_extent_status": None
        if membership_wrapper_start_record_dual_subfamily_to_stride_boundary_owner_extent is None
        else membership_wrapper_start_record_dual_subfamily_to_stride_boundary_owner_extent.get("status"),
        "membership_registration_wrapper_start_record_shared_stride_run_schema_partition_status": None
        if membership_wrapper_start_record_shared_stride_run_schema_partition is None
        else membership_wrapper_start_record_shared_stride_run_schema_partition.get("status"),
        "membership_registration_wrapper_start_record_progressive_marker_series_main_page_event_table_correlation_status": None
        if membership_wrapper_start_record_progressive_marker_series_main_page_event_table_correlation is None
        else membership_wrapper_start_record_progressive_marker_series_main_page_event_table_correlation.get("status"),
        "membership_registration_wrapper_start_record_main_page_button_event_descriptor_ladder_status": None
        if membership_wrapper_start_record_main_page_button_event_descriptor_ladder is None
        else membership_wrapper_start_record_main_page_button_event_descriptor_ladder.get("status"),
        "membership_registration_wrapper_start_record_button_event_ladder_0x1c_secondary_descriptor_chain_status": None
        if membership_wrapper_start_record_button_event_ladder_0x1c_secondary_descriptor_chain is None
        else membership_wrapper_start_record_button_event_ladder_0x1c_secondary_descriptor_chain.get("status"),
        "membership_registration_wrapper_start_record_secondary_descriptor_chain_schema_partition_status": None
        if membership_wrapper_start_record_secondary_descriptor_chain_schema_partition is None
        else membership_wrapper_start_record_secondary_descriptor_chain_schema_partition.get("status"),
        "membership_registration_wrapper_start_record_secondary_descriptor_chain_button_order_correlation_status": None
        if membership_wrapper_start_record_secondary_descriptor_chain_button_order_correlation is None
        else membership_wrapper_start_record_secondary_descriptor_chain_button_order_correlation.get("status"),
        "membership_registration_wrapper_start_record_secondary_descriptor_class_to_local_structure_correlation_status": None
        if membership_wrapper_start_record_secondary_descriptor_class_to_local_structure_correlation is None
        else membership_wrapper_start_record_secondary_descriptor_class_to_local_structure_correlation.get("status"),
        "membership_registration_wrapper_start_record_secondary_descriptor_reference_like_payload_scope_status": None
        if membership_wrapper_start_record_secondary_descriptor_reference_like_payload_scope is None
        else membership_wrapper_start_record_secondary_descriptor_reference_like_payload_scope.get("status"),
        "membership_registration_wrapper_start_record_secondary_descriptor_compact_local_offset_scope_status": None
        if membership_wrapper_start_record_secondary_descriptor_compact_local_offset_scope is None
        else membership_wrapper_start_record_secondary_descriptor_compact_local_offset_scope.get("status"),
        "membership_registration_wrapper_start_record_secondary_descriptor_compact_local_offset_main_page_slot_anchor_correlation_status": None
        if membership_wrapper_start_record_secondary_descriptor_compact_local_offset_main_page_slot_anchor_correlation is None
        else membership_wrapper_start_record_secondary_descriptor_compact_local_offset_main_page_slot_anchor_correlation.get("status"),
        "membership_registration_wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood_status": None
        if membership_wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood is None
        else membership_wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood.get("status"),
        "membership_registration_wrapper_start_record_secondary_descriptor_btnnewfile_local_slice_status": None
        if membership_wrapper_start_record_secondary_descriptor_btnnewfile_local_slice is None
        else membership_wrapper_start_record_secondary_descriptor_btnnewfile_local_slice.get("status"),
        "membership_registration_wrapper_start_record_sidebar_button_local_slice_ladder_status": None
        if membership_wrapper_start_record_sidebar_button_local_slice_ladder is None
        else membership_wrapper_start_record_sidebar_button_local_slice_ladder.get("status"),
        "membership_registration_wrapper_start_record_btnnewfile_local_slice_neighbor_overlap_status": None
        if membership_wrapper_start_record_btnnewfile_local_slice_neighbor_overlap is None
        else membership_wrapper_start_record_btnnewfile_local_slice_neighbor_overlap.get("status"),
        "membership_registration_wrapper_start_record_sidebar_mid_triplet_subfamily_status": None
        if membership_wrapper_start_record_sidebar_mid_triplet_subfamily is None
        else membership_wrapper_start_record_sidebar_mid_triplet_subfamily.get("status"),
        "membership_registration_wrapper_start_record_sidebar_mid_triplet_common_core_partition_status": None
        if membership_wrapper_start_record_sidebar_mid_triplet_common_core_partition is None
        else membership_wrapper_start_record_sidebar_mid_triplet_common_core_partition.get("status"),
        "membership_registration_wrapper_start_record_sidebar_mid_triplet_differential_ownership_status": None
        if membership_wrapper_start_record_sidebar_mid_triplet_differential_ownership is None
        else membership_wrapper_start_record_sidebar_mid_triplet_differential_ownership.get("status"),
        "membership_registration_wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition_status": None
        if membership_wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition is None
        else membership_wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition.get("status"),
        "membership_registration_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_subrun_partition_status": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_subrun_partition is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_subrun_partition.get("status"),
        "membership_registration_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_adjacent_subrun_value_split_status": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_adjacent_subrun_value_split is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_adjacent_subrun_value_split.get("status"),
        "membership_registration_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_isolated_index4_outlier_status": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_isolated_index4_outlier is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_isolated_index4_outlier.get("status"),
        "membership_registration_wrapper_start_record_sidebar_mid_triplet_btndeldir_renamefile_singleton_index11_status": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btndeldir_renamefile_singleton_index11 is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btndeldir_renamefile_singleton_index11.get("status"),
        "membership_registration_wrapper_start_record_sidebar_mid_triplet_singleton_endpoint_contrast_status": None
        if membership_wrapper_start_record_sidebar_mid_triplet_singleton_endpoint_contrast is None
        else membership_wrapper_start_record_sidebar_mid_triplet_singleton_endpoint_contrast.get("status"),
        "membership_registration_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_nonzero_pair_status": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_nonzero_pair is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_nonzero_pair.get("status"),
        "membership_registration_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_bitmask_relation_status": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_bitmask_relation is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_bitmask_relation.get("status"),
        "membership_search_window_status": None if membership_search_window is None else membership_search_window.get("status"),
        "direct_relevant_hmi_page_scripts_identical": None
        if membership_hmi_script_surface is None
        else membership_hmi_script_surface.get("conclusions", {}).get(
            "direct_relevant_incomplete_hmi_page_scripts_are_identical"
        ),
        "direct_relevant_wrapper_compile_class_identical": None
        if membership_wrapper_compile_parity is None
        else membership_wrapper_compile_parity.get("conclusions", {}).get(
            "direct_relevant_wrapper_compile_class_identical"
        ),
        "remaining_gap_not_distinguished_by_hmi_page_script_text": None
        if membership_hmi_script_surface is None
        else membership_hmi_script_surface.get("conclusions", {}).get(
            "remaining_gap_not_distinguished_by_official_hmi_page_script_text"
        ),
        "remaining_gap_not_distinguished_by_wrapper_compile_parity": None
        if membership_wrapper_compile_parity is None
        else membership_wrapper_compile_parity.get("conclusions", {}).get(
            "remaining_gap_not_distinguished_by_wrapper_compile_parity"
        ),
        "shared_wrapper_entry_catalog_identical": None
        if membership_wrapper_catalog_delta is None
        else membership_wrapper_catalog_delta.get("conclusions", {}).get(
            "shared_wrapper_entry_catalog_identical"
        ),
        "remaining_search_should_focus_on_shared_wrapper_only_pages_or_entry_clusters": None
        if membership_wrapper_catalog_delta is None
        else membership_wrapper_catalog_delta.get("conclusions", {}).get(
            "remaining_search_should_focus_on_shared_wrapper_only_pages_or_entry_clusters"
        ),
        "wrapper_page_graph_primary_targets": None
        if membership_wrapper_page_graph_targets is None
        else membership_wrapper_page_graph_targets.get("wrapper_page_graph_targets", {}).get(
            "primary_targets"
        ),
        "search_should_start_from_main_and_noSDcardError": None
        if membership_wrapper_page_graph_targets is None
        else membership_wrapper_page_graph_targets.get("conclusions", {}).get(
            "search_should_start_from_main_and_noSDcardError"
        ),
        "wrapper_page_resource_target_entries": None
        if membership_wrapper_page_resource_mapping is None
        else [item.get("entry_name") for item in membership_wrapper_page_resource_mapping.get("direct_page_graph_target_resources", {}).get("rows", [])],
        "wrapper_start_page_branch_prefix_offset_hex": None
        if membership_wrapper_start_page_command_offsets is None
        else membership_wrapper_start_page_command_offsets.get("shared_wrapper_start_page_branch", {}).get(
            "prefix_offset_hex"
        ),
        "wrapper_start_page_core_branch_offsets_hex": None
        if membership_wrapper_start_page_command_offsets is None
        else [
            membership_wrapper_start_page_command_offsets.get("conclusions", {}).get(
                "findfile_sd_cfg_absolute_offset_hex"
            ),
            membership_wrapper_start_page_command_offsets.get("conclusions", {}).get(
                "first_page_main_absolute_offset_hex"
            ),
            membership_wrapper_start_page_command_offsets.get("conclusions", {}).get(
                "newfile_sd_cfg_absolute_offset_hex"
            ),
            membership_wrapper_start_page_command_offsets.get("conclusions", {}).get(
                "second_findfile_sd_cfg_absolute_offset_hex"
            ),
            membership_wrapper_start_page_command_offsets.get("conclusions", {}).get(
                "second_page_main_absolute_offset_hex"
            ),
            membership_wrapper_start_page_command_offsets.get("conclusions", {}).get(
                "page_noSDcardError_absolute_offset_hex"
            ),
        ],
        "branch_boundary_search_window_hex": None
        if membership_wrapper_start_page_boundary_candidates is None
        else [
            membership_wrapper_start_page_boundary_candidates.get("conclusions", {}).get(
                "branch_boundary_search_window_start_hex"
            ),
            membership_wrapper_start_page_boundary_candidates.get("conclusions", {}).get(
                "branch_boundary_search_window_end_hex"
            ),
        ],
        "prefix_end_reference_hex": None
        if membership_wrapper_start_page_boundary_candidates is None
        else membership_wrapper_start_page_boundary_candidates.get("conclusions", {}).get(
            "prefix_end_reference_hex"
        ),
        "start_record_cluster_offsets_hex": None
        if membership_wrapper_start_record_cluster_diff is None
        else [
            membership_wrapper_start_record_cluster_diff.get("conclusions", {}).get(
                "left_record_offset_hex"
            ),
            membership_wrapper_start_record_cluster_diff.get("conclusions", {}).get(
                "right_record_offset_hex"
            ),
        ],
        "start_record_cluster_diff_byte_count": None
        if membership_wrapper_start_record_cluster_diff is None
        else membership_wrapper_start_record_cluster_diff.get("conclusions", {}).get("diff_byte_count"),
        "start_record_field_target_windows_hex": None
        if membership_wrapper_start_record_field_targets is None
        else ["0x242E", "0x291CC", "0x29218"],
        "field_reference_cluster_priority_target_hex": None
        if membership_wrapper_start_record_field_reference_clusters is None
        else membership_wrapper_start_record_field_reference_clusters.get("conclusions", {}).get(
            "narrowest_ref_surface_target_hex"
        ),
        "field_0x18_right_record_pair_offsets_hex": None
        if membership_wrapper_start_record_field_0x242e_anchor_records is None
        else membership_wrapper_start_record_field_0x242e_anchor_records.get("conclusions", {}).get(
            "field_0x18_right_record_pair_offsets_hex"
        ),
        "field_0x18_right_pair_companion_target_hex": None
        if membership_wrapper_start_record_field_0x242e_anchor_records is None
        else membership_wrapper_start_record_field_0x242e_anchor_records.get("conclusions", {}).get(
            "field_0x18_right_pair_companion_target_hex"
        ),
        "field_0x18_right_shared_prefix_length_hex": None
        if membership_wrapper_start_record_field_0x242e_anchor_records is None
        else membership_wrapper_start_record_field_0x242e_anchor_records.get("conclusions", {}).get(
            "field_0x18_right_shared_prefix_length_hex"
        ),
        "field_0x18_right_tail_plus_0x34_hex": None
        if membership_wrapper_start_record_field_0x242e_tail_divergence is None
        else membership_wrapper_start_record_field_0x242e_tail_divergence.get("correlations", {}).get(
            "start_record_right_tail_plus_0x34_hex"
        ),
        "field_0x18_right_tail_plus_0x34_matches_branch_boundary_end": None
        if membership_wrapper_start_record_field_0x242e_tail_divergence is None
        else membership_wrapper_start_record_field_0x242e_tail_divergence.get("conclusions", {}).get(
            "start_record_right_tail_plus_0x34_matches_branch_boundary_end"
        ),
        "field_0x18_right_tail_plus_0x34_is_unique_in_object_region": None
        if membership_wrapper_start_record_field_0x242e_tail_divergence is None
        else membership_wrapper_start_record_field_0x242e_tail_divergence.get("conclusions", {}).get(
            "start_record_right_tail_plus_0x34_is_unique_in_object_region"
        ),
        "field_0x18_right_tail_plus_0x38_is_not_unique_in_object_region": None
        if membership_wrapper_start_record_field_0x242e_tail_divergence is None
        else membership_wrapper_start_record_field_0x242e_tail_divergence.get("conclusions", {}).get(
            "tail_plus_0x38_is_not_unique_in_object_region"
        ),
        "field_0x18_right_tail_plus_0x3C_is_not_unique_in_object_region": None
        if membership_wrapper_start_record_field_0x242e_tail_divergence is None
        else membership_wrapper_start_record_field_0x242e_tail_divergence.get("conclusions", {}).get(
            "tail_plus_0x3C_is_not_unique_in_object_region"
        ),
        "unload_bridge_follower_class_count": None
        if membership_wrapper_unload_bridge_follower_classes is None
        else membership_wrapper_unload_bridge_follower_classes.get("conclusions", {}).get(
            "follower_class_count"
        ),
        "unload_bridge_0x240A_follower_class_id": None
        if membership_wrapper_unload_bridge_follower_classes is None
        else membership_wrapper_unload_bridge_follower_classes.get("conclusions", {}).get(
            "bridge_0x240A_follower_class_id"
        ),
        "unload_bridge_0x240A_follower_is_singleton": None
        if membership_wrapper_unload_bridge_follower_classes is None
        else membership_wrapper_unload_bridge_follower_classes.get("conclusions", {}).get(
            "bridge_0x240A_follower_is_singleton"
        ),
        "unload_bridge_largest_repeated_follower_class_id": None
        if membership_wrapper_unload_bridge_follower_classes is None
        else membership_wrapper_unload_bridge_follower_classes.get("conclusions", {}).get(
            "largest_repeated_follower_class_id"
        ),
        "unload_bridge_largest_repeated_follower_class_count": None
        if membership_wrapper_unload_bridge_follower_classes is None
        else membership_wrapper_unload_bridge_follower_classes.get("conclusions", {}).get(
            "largest_repeated_follower_class_count"
        ),
        "singleton_methodcall_slot_count": None
        if membership_wrapper_singleton_methodcall_slot_reuse is None
        else membership_wrapper_singleton_methodcall_slot_reuse.get("conclusions", {}).get(
            "bridge_singleton_methodcall_slot_count"
        ),
        "singleton_methodcall_non_unique_slots_hex": None
        if membership_wrapper_singleton_methodcall_slot_reuse is None
        else membership_wrapper_singleton_methodcall_slot_reuse.get("conclusions", {}).get(
            "slot_level_non_unique_bridge_followers_hex"
        ),
        "singleton_methodcall_hidden_tail_slot_is_not_unique": None
        if membership_wrapper_singleton_methodcall_slot_reuse is None
        else membership_wrapper_singleton_methodcall_slot_reuse.get("conclusions", {}).get(
            "hidden_tail_slot_0xBF_is_not_unique_at_slot_level"
        ),
        "reused_methodcall_pair_count": None
        if membership_wrapper_reused_methodcall_prelude_pairs is None
        else membership_wrapper_reused_methodcall_prelude_pairs.get("conclusions", {}).get(
            "reused_slot_pair_count"
        ),
        "reused_methodcall_pairs_diverge_immediately_after_common_method_call": None
        if membership_wrapper_reused_methodcall_prelude_pairs is None
        else membership_wrapper_reused_methodcall_prelude_pairs.get("conclusions", {}).get(
            "all_reused_pairs_diverge_immediately_after_common_method_call"
        ),
        "reused_methodcall_hidden_tail_rich_page_args": None
        if membership_wrapper_reused_methodcall_prelude_pairs is None
        else next(
            (
                row.get("rich_page_args")
                for row in membership_wrapper_reused_methodcall_prelude_pairs.get("reused_slot_pairs", [])
                if row.get("slot_hex") == "0xBF"
            ),
            None,
        ),
        "hidden_tail_preanchor_corridor_length_hex": None
        if membership_wrapper_hidden_tail_preanchor_corridor is None
        else membership_wrapper_hidden_tail_preanchor_corridor.get("corridor_window", {}).get("length_hex"),
        "hidden_tail_preanchor_page_launch_targets": None
        if membership_wrapper_hidden_tail_preanchor_corridor is None
        else membership_wrapper_hidden_tail_preanchor_corridor.get("conclusions", {}).get(
            "page_launch_targets_before_main_anchor"
        ),
        "hidden_tail_preanchor_visibility_gate_depends_on_field_0x8E_non_empty": None
        if membership_wrapper_hidden_tail_preanchor_corridor is None
        else membership_wrapper_hidden_tail_preanchor_corridor.get("conclusions", {}).get(
            "visibility_gate_depends_on_field_0x8E_non_empty"
        ),
        "main_page_auxiliary_preanchor_launch_resources": None
        if membership_main_page_auxiliary_flow is None
        else membership_main_page_auxiliary_flow.get("conclusions", {}).get(
            "preanchor_page_launch_targets_resources"
        ),
        "main_page_auxiliary_rename_target_resource": None
        if membership_main_page_auxiliary_flow is None
        else membership_main_page_auxiliary_flow.get("conclusions", {}).get("rename_target_resource"),
        "main_page_auxiliary_delete_flow_is_overlay_on_main_not_page_jump": None
        if membership_main_page_auxiliary_flow is None
        else membership_main_page_auxiliary_flow.get("conclusions", {}).get(
            "delete_flow_is_overlay_on_main_not_page_jump"
        ),
        "main_page_auxiliary_compiled_delete_overlay_cluster_window_hex": None
        if membership_main_page_auxiliary_compiled_flow is None
        else membership_main_page_auxiliary_compiled_flow.get("conclusions", {}).get(
            "compiled_delete_overlay_cluster_window_hex"
        ),
        "main_page_auxiliary_compiled_rename_target_absolute_hex": None
        if membership_main_page_auxiliary_compiled_flow is None
        else membership_main_page_auxiliary_compiled_flow.get("conclusions", {}).get(
            "btnRenameFile_page_renameFile_absolute_hex"
        ),
        "main_page_auxiliary_compiled_btnOK_page_main_absolute_hex": None
        if membership_main_page_auxiliary_compiled_flow is None
        else membership_main_page_auxiliary_compiled_flow.get("conclusions", {}).get(
            "btnOK_page_main_absolute_hex"
        ),
        "renamefile_page_resource_entry_name": None
        if membership_renamefile_page_surface_and_anchor is None
        else membership_renamefile_page_surface_and_anchor.get("conclusions", {}).get(
            "renameFile_resource_entry_name"
        ),
        "renamefile_keybdAP_resource_entry_name": None
        if membership_renamefile_page_surface_and_anchor is None
        else membership_renamefile_page_surface_and_anchor.get("conclusions", {}).get(
            "keybdAP_resource_entry_name"
        ),
        "renamefile_b0_primary_confirm_logic_has_no_official_anchor_match": None
        if membership_renamefile_page_surface_and_anchor is None
        else membership_renamefile_page_surface_and_anchor.get("conclusions", {}).get(
            "b0_primary_rename_confirm_logic_has_no_official_anchor_match_today"
        ),
        "renamefile_filename1_compiled_anchor_is_reused_not_unique": None
        if membership_renamefile_page_surface_and_anchor is None
        else membership_renamefile_page_surface_and_anchor.get("conclusions", {}).get(
            "filename1_compiled_anchor_is_reused_not_unique"
        ),
        "renamefile_b1_page_main_cancel_back_is_reused_not_unique": None
        if membership_renamefile_page_surface_and_anchor is None
        else membership_renamefile_page_surface_and_anchor.get("conclusions", {}).get(
            "b1_page_main_cancel_back_is_reused_not_unique"
        ),
        "renamefile_event_anchorability_unique_anchor_surfaces": None
        if membership_renamefile_event_anchorability is None
        else membership_renamefile_event_anchorability.get("conclusions", {}).get(
            "unique_anchor_surfaces"
        ),
        "renamefile_event_anchorability_reused_non_unique_anchor_surfaces": None
        if membership_renamefile_event_anchorability is None
        else membership_renamefile_event_anchorability.get("conclusions", {}).get(
            "reused_non_unique_anchor_surfaces"
        ),
        "renamefile_event_anchorability_compiler_blocked_no_anchor_surfaces": None
        if membership_renamefile_event_anchorability is None
        else membership_renamefile_event_anchorability.get("conclusions", {}).get(
            "compiler_blocked_no_anchor_surfaces"
        ),
        "renamefile_event_anchorability_compiled_no_anchor_match_surfaces": None
        if membership_renamefile_event_anchorability is None
        else membership_renamefile_event_anchorability.get("conclusions", {}).get(
            "compiled_no_anchor_match_surfaces"
        ),
        "renamefile_event_anchorability_b0_rename_confirm_logic_is_the_only_current_compiler_blocked_surface_inside_renameFile": None
        if membership_renamefile_event_anchorability is None
        else membership_renamefile_event_anchorability.get("conclusions", {}).get(
            "b0_rename_confirm_logic_is_the_only_current_compiler_blocked_surface_inside_renameFile"
        ),
        "renamefile_event_anchorability_msg_is_the_only_current_compiled_no_anchor_surface_inside_renameFile": None
        if membership_renamefile_event_anchorability is None
        else membership_renamefile_event_anchorability.get("conclusions", {}).get(
            "msg_is_the_only_current_compiled_no_anchor_surface_inside_renameFile"
        ),
        "renamefile_unique_support_fields_unique_anchor_count": None
        if membership_renamefile_unique_anchored_support_fields is None
        else membership_renamefile_unique_anchored_support_fields.get("conclusions", {}).get(
            "unique_anchor_count"
        ),
        "renamefile_unique_support_fields_unique_anchor_hexes": None
        if membership_renamefile_unique_anchored_support_fields is None
        else membership_renamefile_unique_anchored_support_fields.get("conclusions", {}).get(
            "unique_anchor_hexes"
        ),
        "renamefile_unique_support_fields_unique_anchor_window_hex": None
        if membership_renamefile_unique_anchored_support_fields is None
        else membership_renamefile_unique_anchored_support_fields.get("conclusions", {}).get(
            "unique_anchor_window_hex"
        ),
        "renamefile_unique_support_fields_loadcmpid_values": None
        if membership_renamefile_unique_anchored_support_fields is None
        else membership_renamefile_unique_anchored_support_fields.get("conclusions", {}).get(
            "loadcmpid_values"
        ),
        "renamefile_unique_support_fields_first_three_support_fields_form_a_0x34_stride_cluster": None
        if membership_renamefile_unique_anchored_support_fields is None
        else membership_renamefile_unique_anchored_support_fields.get("conclusions", {}).get(
            "first_three_support_fields_form_a_0x34_stride_cluster"
        ),
        "renamefile_unique_support_fields_all_unique_support_field_full_payloads_have_zero_direct_hits_in_shared_official_tfts": None
        if membership_renamefile_unique_anchored_support_fields is None
        else membership_renamefile_unique_anchored_support_fields.get("conclusions", {}).get(
            "all_unique_support_field_full_payloads_have_zero_direct_hits_in_shared_official_tfts"
        ),
        "renamefile_unique_support_fields_are_the_best_current_compiled_footholds_inside_page9": None
        if membership_renamefile_unique_anchored_support_fields is None
        else membership_renamefile_unique_anchored_support_fields.get("conclusions", {}).get(
            "renameFile_unique_support_fields_are_the_best_current_compiled_footholds_inside_page9"
        ),
        "renamefile_keybdap_callsite_ladder_page_jump_shell_objects": None
        if membership_renamefile_keybdap_callsite_ladder is None
        else membership_renamefile_keybdap_callsite_ladder.get("conclusions", {}).get(
            "page_jump_shell_objects"
        ),
        "renamefile_keybdap_callsite_ladder_routing_only_support_field_objects": None
        if membership_renamefile_keybdap_callsite_ladder is None
        else membership_renamefile_keybdap_callsite_ladder.get("conclusions", {}).get(
            "routing_only_support_field_objects"
        ),
        "renamefile_keybdap_callsite_ladder_page_jump_shell_loadcmpid_values": None
        if membership_renamefile_keybdap_callsite_ladder is None
        else membership_renamefile_keybdap_callsite_ladder.get("conclusions", {}).get(
            "page_jump_shell_loadcmpid_values"
        ),
        "renamefile_keybdap_callsite_ladder_routing_only_support_field_loadcmpid_values": None
        if membership_renamefile_keybdap_callsite_ladder is None
        else membership_renamefile_keybdap_callsite_ladder.get("conclusions", {}).get(
            "routing_only_support_field_loadcmpid_values"
        ),
        "renamefile_keybdap_callsite_ladder_filename_shells_are_the_only_current_page9_keybdap_callsites_that_still_execute_page_keybdAP": None
        if membership_renamefile_keybdap_callsite_ladder is None
        else membership_renamefile_keybdap_callsite_ladder.get("conclusions", {}).get(
            "filename_shells_are_the_only_current_page9_keybdap_callsites_that_still_execute_page_keybdAP"
        ),
        "renamefile_keybdap_callsite_ladder_routing_only_support_field_ladder_matches_the_unique_support_window_inside_the_local_page9_corridor": None
        if membership_renamefile_keybdap_callsite_ladder is None
        else membership_renamefile_keybdap_callsite_ladder.get("conclusions", {}).get(
            "routing_only_support_field_ladder_matches_the_unique_support_window_inside_the_local_page9_corridor"
        ),
        "renamefile_local_support_corridor_start_hex": None
        if membership_renamefile_local_compiled_support_corridor is None
        else membership_renamefile_local_compiled_support_corridor.get("conclusions", {}).get(
            "local_corridor_start_hex"
        ),
        "renamefile_local_support_corridor_end_hex": None
        if membership_renamefile_local_compiled_support_corridor is None
        else membership_renamefile_local_compiled_support_corridor.get("conclusions", {}).get(
            "local_corridor_end_hex"
        ),
        "renamefile_local_support_corridor_left_guard_object": None
        if membership_renamefile_local_compiled_support_corridor is None
        else membership_renamefile_local_compiled_support_corridor.get("conclusions", {}).get(
            "left_guard_object"
        ),
        "renamefile_local_support_corridor_right_guard_object": None
        if membership_renamefile_local_compiled_support_corridor is None
        else membership_renamefile_local_compiled_support_corridor.get("conclusions", {}).get(
            "right_guard_object"
        ),
        "renamefile_local_support_corridor_is_tightest_current_compiled_page9_support_band": None
        if membership_renamefile_local_compiled_support_corridor is None
        else membership_renamefile_local_compiled_support_corridor.get("conclusions", {}).get(
            "corridor_is_the_tightest_current_compiled_page9_support_band"
        ),
        "renamefile_b0_semantic_frontier_standalone_supported_source_statement_ids": None
        if membership_renamefile_b0_semantic_frontier is None
        else membership_renamefile_b0_semantic_frontier.get("conclusions", {}).get(
            "standalone_supported_source_statement_ids"
        ),
        "renamefile_b0_semantic_frontier_standalone_unsupported_source_statement_ids": None
        if membership_renamefile_b0_semantic_frontier is None
        else membership_renamefile_b0_semantic_frontier.get("conclusions", {}).get(
            "standalone_unsupported_source_statement_ids"
        ),
        "renamefile_b0_semantic_frontier_single_field_empty_guard_is_supported_but_dual_field_or_empty_guard_is_not": None
        if membership_renamefile_b0_semantic_frontier is None
        else membership_renamefile_b0_semantic_frontier.get("conclusions", {}).get(
            "single_field_empty_guard_is_supported_but_dual_field_or_empty_guard_is_not"
        ),
        "renamefile_b0_semantic_frontier_sys_integer_guard_is_supported_but_field_integer_zero_guard_is_not": None
        if membership_renamefile_b0_semantic_frontier is None
        else membership_renamefile_b0_semantic_frontier.get("conclusions", {}).get(
            "sys_integer_guard_is_supported_but_field_integer_zero_guard_is_not"
        ),
        "renamefile_b0_semantic_frontier_two_segment_concat_variants_are_supported_but_three_segment_or_more_destination_path_build_is_not": None
        if membership_renamefile_b0_semantic_frontier is None
        else membership_renamefile_b0_semantic_frontier.get("conclusions", {}).get(
            "two_segment_concat_variants_are_supported_but_three_segment_or_more_destination_path_build_is_not"
        ),
        "renamefile_b0_semantic_frontier_literal_findfile_to_sys0_is_supported_but_dynamic_field_path_findfile_is_not": None
        if membership_renamefile_b0_semantic_frontier is None
        else membership_renamefile_b0_semantic_frontier.get("conclusions", {}).get(
            "literal_findfile_to_sys0_is_supported_but_dynamic_field_path_findfile_is_not"
        ),
        "renamefile_b0_semantic_frontier_current_minimal_compiler_has_no_rename_command_lowering_for_refile": None
        if membership_renamefile_b0_semantic_frontier is None
        else membership_renamefile_b0_semantic_frontier.get("conclusions", {}).get(
            "current_minimal_compiler_has_no_rename_command_lowering_for_refile"
        ),
        "renamefile_b0_semantic_frontier_supported_residual_source_statements_only_recover_message_ui_and_generic_page_main_not_rename_runtime_semantics": None
        if membership_renamefile_b0_semantic_frontier is None
        else membership_renamefile_b0_semantic_frontier.get("conclusions", {}).get(
            "supported_residual_source_statements_only_recover_message_ui_and_generic_page_main_not_rename_runtime_semantics"
        ),
        "renamefile_compiled_fragment_absence_zero_hit_fragments": None
        if membership_renamefile_compiled_fragment_absence is None
        else membership_renamefile_compiled_fragment_absence.get("conclusions", {}).get(
            "zero_hit_fragments"
        ),
        "renamefile_compiled_fragment_absence_all_current_compiled_renamefile_support_fields_and_msg_have_zero_hits": None
        if membership_renamefile_compiled_fragment_absence is None
        else membership_renamefile_compiled_fragment_absence.get("conclusions", {}).get(
            "all_current_compiled_renamefile_support_fields_and_msg_have_zero_hits"
        ),
        "preanchor_launch_page_resources": None
        if membership_preanchor_launch_pages_surface_and_anchor is None
        else membership_preanchor_launch_pages_surface_and_anchor.get("conclusions", {}).get(
            "page_resources"
        ),
        "preanchor_launch_keyboard_entry_shells_are_reused": None
        if membership_preanchor_launch_pages_surface_and_anchor is None
        else membership_preanchor_launch_pages_surface_and_anchor.get("conclusions", {}).get(
            "keyboard_entry_shells_are_reused_across_launch_pages"
        ),
        "preanchor_launch_b0_primary_create_delete_logic_has_no_official_anchor_match": None
        if membership_preanchor_launch_pages_surface_and_anchor is None
        else membership_preanchor_launch_pages_surface_and_anchor.get("conclusions", {}).get(
            "b0_primary_create_delete_logic_has_no_official_anchor_match_today"
        ),
        "preanchor_launch_myNewFile_b2_to_mycsvFile_is_unique": None
        if membership_preanchor_launch_pages_surface_and_anchor is None
        else membership_preanchor_launch_pages_surface_and_anchor.get("conclusions", {}).get(
            "myNewFile_b2_to_mycsvFile_is_the_only_unique_official_anchor_among_the_primary_launch_page_actions"
        ),
        "preanchor_launch_event_anchorability_unique_anchor_surfaces": None
        if membership_preanchor_launch_event_anchorability is None
        else membership_preanchor_launch_event_anchorability.get("conclusions", {}).get(
            "unique_anchor_surfaces"
        ),
        "preanchor_launch_event_anchorability_reused_non_unique_anchor_surfaces": None
        if membership_preanchor_launch_event_anchorability is None
        else membership_preanchor_launch_event_anchorability.get("conclusions", {}).get(
            "reused_non_unique_anchor_surfaces"
        ),
        "preanchor_launch_event_anchorability_compiler_blocked_no_anchor_surfaces": None
        if membership_preanchor_launch_event_anchorability is None
        else membership_preanchor_launch_event_anchorability.get("conclusions", {}).get(
            "compiler_blocked_no_anchor_surfaces"
        ),
        "preanchor_launch_event_anchorability_compiled_no_anchor_match_surfaces": None
        if membership_preanchor_launch_event_anchorability is None
        else membership_preanchor_launch_event_anchorability.get("conclusions", {}).get(
            "compiled_no_anchor_match_surfaces"
        ),
        "preanchor_launch_event_anchorability_myNewFile_b2_is_the_only_current_unique_preanchor_launch_surface": None
        if membership_preanchor_launch_event_anchorability is None
        else membership_preanchor_launch_event_anchorability.get("conclusions", {}).get(
            "myNewFile_b2_is_the_only_current_unique_preanchor_launch_surface"
        ),
        "preanchor_launch_event_anchorability_b0_create_delete_logic_remains_blocked_across_all_preanchor_pages": None
        if membership_preanchor_launch_event_anchorability is None
        else membership_preanchor_launch_event_anchorability.get("conclusions", {}).get(
            "b0_create_delete_logic_remains_blocked_across_all_preanchor_pages"
        ),
        "preanchor_launch_compiled_no_anchor_families_shared_page_object_family_exists": None
        if membership_preanchor_launch_compiled_no_anchor_families is None
        else membership_preanchor_launch_compiled_no_anchor_families.get("conclusions", {}).get(
            "shared_page_object_family_exists"
        ),
        "preanchor_launch_compiled_no_anchor_families_shared_temp_helper_family_exists": None
        if membership_preanchor_launch_compiled_no_anchor_families is None
        else membership_preanchor_launch_compiled_no_anchor_families.get("conclusions", {}).get(
            "shared_temp_helper_family_exists"
        ),
        "preanchor_launch_compiled_no_anchor_families_msg_surfaces_are_length_aligned_but_page_specific_compiled_no_anchor": None
        if membership_preanchor_launch_compiled_no_anchor_families is None
        else membership_preanchor_launch_compiled_no_anchor_families.get("conclusions", {}).get(
            "msg_surfaces_are_length_aligned_but_page_specific_compiled_no_anchor"
        ),
        "preanchor_launch_compiled_no_anchor_fragment_absence_zero_hit_fragments": None
        if membership_preanchor_launch_compiled_no_anchor_fragment_absence is None
        else membership_preanchor_launch_compiled_no_anchor_fragment_absence.get("conclusions", {}).get(
            "zero_hit_fragments"
        ),
        "preanchor_launch_compiled_no_anchor_fragment_absence_shared_page_temp_and_msg_family_payloads_all_have_zero_hits": None
        if membership_preanchor_launch_compiled_no_anchor_fragment_absence is None
        else membership_preanchor_launch_compiled_no_anchor_fragment_absence.get("conclusions", {}).get(
            "shared_page_temp_and_msg_family_payloads_all_have_zero_hits"
        ),
        "mycsvfile_page_resource_entry_name": None
        if membership_mycsvfile_page_surface_and_anchor is None
        else membership_mycsvfile_page_surface_and_anchor.get("conclusions", {}).get(
            "mycsvFile_resource_entry_name"
        ),
        "mycsvfile_csvAdd_resource_entry_name": None
        if membership_mycsvfile_page_surface_and_anchor is None
        else membership_mycsvfile_page_surface_and_anchor.get("conclusions", {}).get(
            "csvAdd_resource_entry_name"
        ),
        "mycsvfile_b0_primary_csv_seed_logic_has_no_official_anchor_match": None
        if membership_mycsvfile_page_surface_and_anchor is None
        else membership_mycsvfile_page_surface_and_anchor.get("conclusions", {}).get(
            "b0_primary_csv_seed_logic_has_no_official_anchor_match_today"
        ),
        "mycsvfile_newFileName_keyboard_entry_shell_is_reused_not_unique": None
        if membership_mycsvfile_page_surface_and_anchor is None
        else membership_mycsvfile_page_surface_and_anchor.get("conclusions", {}).get(
            "newFileName_keyboard_entry_shell_is_reused_not_unique"
        ),
        "mycsvfile_event_anchorability_reused_non_unique_anchor_surfaces": None
        if membership_mycsvfile_event_anchorability is None
        else membership_mycsvfile_event_anchorability.get("conclusions", {}).get(
            "reused_non_unique_anchor_surfaces"
        ),
        "mycsvfile_event_anchorability_compiler_blocked_no_anchor_surfaces": None
        if membership_mycsvfile_event_anchorability is None
        else membership_mycsvfile_event_anchorability.get("conclusions", {}).get(
            "compiler_blocked_no_anchor_surfaces"
        ),
        "mycsvfile_event_anchorability_compiled_no_anchor_match_surfaces": None
        if membership_mycsvfile_event_anchorability is None
        else membership_mycsvfile_event_anchorability.get("conclusions", {}).get(
            "compiled_no_anchor_match_surfaces"
        ),
        "mycsvfile_event_anchorability_mycsvFile_page_load_and_b0_csv_seed_logic_are_the_current_compiler_blocked_surfaces": None
        if membership_mycsvfile_event_anchorability is None
        else membership_mycsvfile_event_anchorability.get("conclusions", {}).get(
            "mycsvFile_page_load_and_b0_csv_seed_logic_are_the_current_compiler_blocked_surfaces"
        ),
        "mycsvfile_event_anchorability_newFileName2_and_msg_are_the_current_compiled_no_anchor_surfaces": None
        if membership_mycsvfile_event_anchorability is None
        else membership_mycsvfile_event_anchorability.get("conclusions", {}).get(
            "newFileName2_and_msg_are_the_current_compiled_no_anchor_surfaces"
        ),
        "mycsvfile_compiled_no_anchor_families_newFileName2_extends_the_shared_temp_helper_family": None
        if membership_mycsvfile_compiled_no_anchor_families is None
        else membership_mycsvfile_compiled_no_anchor_families.get("conclusions", {}).get(
            "mycsvfile_newFileName2_extends_the_shared_temp_helper_family"
        ),
        "mycsvfile_compiled_no_anchor_families_msg_remains_a_page_specific_compiled_no_anchor_surface": None
        if membership_mycsvfile_compiled_no_anchor_families is None
        else membership_mycsvfile_compiled_no_anchor_families.get("conclusions", {}).get(
            "mycsvfile_msg_remains_a_page_specific_compiled_no_anchor_surface"
        ),
        "mycsvfile_compiled_no_anchor_fragment_absence_zero_hit_fragments": None
        if membership_mycsvfile_compiled_no_anchor_fragment_absence is None
        else membership_mycsvfile_compiled_no_anchor_fragment_absence.get("conclusions", {}).get(
            "zero_hit_fragments"
        ),
        "mycsvfile_compiled_no_anchor_fragment_absence_newFileName2_and_msg_payloads_both_have_zero_hits": None
        if membership_mycsvfile_compiled_no_anchor_fragment_absence is None
        else membership_mycsvfile_compiled_no_anchor_fragment_absence.get("conclusions", {}).get(
            "newFileName2_and_msg_payloads_both_have_zero_hits"
        ),
        "csvadd_page_resource_entry_name": None
        if membership_csvadd_page_surface_and_anchor is None
        else membership_csvadd_page_surface_and_anchor.get("conclusions", {}).get(
            "csvAdd_resource_entry_name"
        ),
        "csvadd_csvAdd_codesload_open_logic_has_no_official_anchor_match": None
        if membership_csvadd_page_surface_and_anchor is None
        else membership_csvadd_page_surface_and_anchor.get("conclusions", {}).get(
            "csvAdd_codesload_open_logic_has_no_official_anchor_match_today"
        ),
        "csvadd_b0_primary_append_row_logic_has_no_official_anchor_match": None
        if membership_csvadd_page_surface_and_anchor is None
        else membership_csvadd_page_surface_and_anchor.get("conclusions", {}).get(
            "b0_primary_append_row_logic_has_no_official_anchor_match_today"
        ),
        "csvadd_keyboard_field_entry_anchors_are_unique_for_tIndex_tName_tAge": None
        if membership_csvadd_page_surface_and_anchor is None
        else membership_csvadd_page_surface_and_anchor.get("conclusions", {}).get(
            "keyboard_field_entry_anchors_are_unique_for_tIndex_tName_tAge"
        ),
        "csvadd_tm0_auto_append_timer_anchor_is_unique": None
        if membership_csvadd_page_surface_and_anchor is None
        else membership_csvadd_page_surface_and_anchor.get("conclusions", {}).get(
            "tm0_auto_append_timer_anchor_is_unique"
        ),
        "csvadd_unique_anchor_count": None
        if membership_csvadd_unique_anchored_subcontrols is None
        else membership_csvadd_unique_anchored_subcontrols.get("conclusions", {}).get(
            "unique_anchor_count"
        ),
        "csvadd_unique_anchor_window_hex": None
        if membership_csvadd_unique_anchored_subcontrols is None
        else membership_csvadd_unique_anchored_subcontrols.get("conclusions", {}).get(
            "anchor_window_hex"
        ),
        "csvadd_unique_anchor_hexes": None
        if membership_csvadd_unique_anchored_subcontrols is None
        else [
            membership_csvadd_unique_anchored_subcontrols.get("subcontrols", {}).get("tIndex", {}).get(
                "anchor_hex"
            ),
            membership_csvadd_unique_anchored_subcontrols.get("subcontrols", {}).get("tName", {}).get(
                "anchor_hex"
            ),
            membership_csvadd_unique_anchored_subcontrols.get("subcontrols", {}).get("tAge", {}).get(
                "anchor_hex"
            ),
            membership_csvadd_unique_anchored_subcontrols.get("subcontrols", {}).get("tm0", {}).get(
                "anchor_hex"
            ),
        ],
        "csvadd_unique_tName_is_the_only_current_unique_keybdAP_callsite_inside_csvAdd": None
        if membership_csvadd_unique_anchored_subcontrols is None
        else membership_csvadd_unique_anchored_subcontrols.get("conclusions", {}).get(
            "tName_is_the_only_current_unique_keybdAP_callsite_inside_csvAdd"
        ),
        "csvadd_unique_tm0_is_the_only_current_unique_timer_anchor_inside_csvAdd": None
        if membership_csvadd_unique_anchored_subcontrols is None
        else membership_csvadd_unique_anchored_subcontrols.get("conclusions", {}).get(
            "tm0_is_the_only_current_unique_timer_anchor_inside_csvAdd"
        ),
        "csvadd_unique_anchored_subcontrols_are_the_best_current_compiled_footholds_inside_page16": None
        if membership_csvadd_unique_anchored_subcontrols is None
        else membership_csvadd_unique_anchored_subcontrols.get("conclusions", {}).get(
            "csvAdd_unique_anchored_subcontrols_are_the_best_current_compiled_footholds_inside_page16"
        ),
        "csvadd_event_anchorability_unique_anchor_objects": None
        if membership_csvadd_event_anchorability is None
        else membership_csvadd_event_anchorability.get("conclusions", {}).get("unique_anchor_objects"),
        "csvadd_event_anchorability_reused_non_unique_anchor_objects": None
        if membership_csvadd_event_anchorability is None
        else membership_csvadd_event_anchorability.get("conclusions", {}).get(
            "reused_non_unique_anchor_objects"
        ),
        "csvadd_event_anchorability_compiler_blocked_no_anchor_objects": None
        if membership_csvadd_event_anchorability is None
        else membership_csvadd_event_anchorability.get("conclusions", {}).get(
            "compiler_blocked_no_anchor_objects"
        ),
        "csvadd_event_anchorability_compiled_no_anchor_match_objects": None
        if membership_csvadd_event_anchorability is None
        else membership_csvadd_event_anchorability.get("conclusions", {}).get(
            "compiled_no_anchor_match_objects"
        ),
        "csvadd_event_anchorability_auto_is_the_only_current_compiled_no_anchor_match_surface_inside_csvAdd": None
        if membership_csvadd_event_anchorability is None
        else membership_csvadd_event_anchorability.get("conclusions", {}).get(
            "auto_is_the_only_current_compiled_no_anchor_match_surface_inside_csvAdd"
        ),
        "csvadd_event_anchorability_auto_is_the_next_best_page16_compiled_narrowing_surface_after_the_unique_anchor_set": None
        if membership_csvadd_event_anchorability is None
        else membership_csvadd_event_anchorability.get("conclusions", {}).get(
            "auto_is_the_next_best_page16_compiled_narrowing_surface_after_the_unique_anchor_set"
        ),
        "csvadd_auto_fragment_absence_meaningful_zero_hit_fragments": None
        if membership_csvadd_auto_fragment_absence is None
        else membership_csvadd_auto_fragment_absence.get("conclusions", {}).get(
            "meaningful_zero_hit_fragments"
        ),
        "csvadd_auto_fragment_absence_else_jump_match_count": None
        if membership_csvadd_auto_fragment_absence is None
        else membership_csvadd_auto_fragment_absence.get("fragment_searches", {})
        .get("case_43_filebrowser", {})
        .get("else_jump", {})
        .get("match_count"),
        "csvadd_auto_fragment_absence_generic_else_jump_fragment_is_repeated_noise": None
        if membership_csvadd_auto_fragment_absence is None
        else membership_csvadd_auto_fragment_absence.get("conclusions", {}).get(
            "generic_else_jump_fragment_is_repeated_noise"
        ),
        "csvadd_auto_fragment_absence_auto_still_lacks_even_partial_semantic_byte_foothold_in_shared_official_tft": None
        if membership_csvadd_auto_fragment_absence is None
        else membership_csvadd_auto_fragment_absence.get("conclusions", {}).get(
            "auto_still_lacks_even_partial_semantic_byte_foothold_in_shared_official_tft"
        ),
        "csvadd_local_compiled_corridor_start_hex": None
        if membership_csvadd_local_compiled_corridor is None
        else membership_csvadd_local_compiled_corridor.get("conclusions", {}).get(
            "local_corridor_start_hex"
        ),
        "csvadd_local_compiled_corridor_end_hex": None
        if membership_csvadd_local_compiled_corridor is None
        else membership_csvadd_local_compiled_corridor.get("conclusions", {}).get(
            "local_corridor_end_hex"
        ),
        "csvadd_local_compiled_corridor_length_hex": None
        if membership_csvadd_local_compiled_corridor is None
        else membership_csvadd_local_compiled_corridor.get("conclusions", {}).get(
            "local_corridor_length_hex"
        ),
        "csvadd_local_compiled_corridor_left_guard_object": None
        if membership_csvadd_local_compiled_corridor is None
        else membership_csvadd_local_compiled_corridor.get("conclusions", {}).get(
            "left_guard_object"
        ),
        "csvadd_local_compiled_corridor_inner_unique_anchor_objects": None
        if membership_csvadd_local_compiled_corridor is None
        else membership_csvadd_local_compiled_corridor.get("conclusions", {}).get(
            "inner_unique_anchor_objects"
        ),
        "csvadd_local_compiled_corridor_is_tightest_current_compiled_page16_anchor_band": None
        if membership_csvadd_local_compiled_corridor is None
        else membership_csvadd_local_compiled_corridor.get("conclusions", {}).get(
            "corridor_is_the_tightest_current_compiled_page16_anchor_band"
        ),
        "keyboard_helper_keybdAP_resource_entry_name": None
        if membership_keyboard_helper_pages_surface_and_anchor is None
        else membership_keyboard_helper_pages_surface_and_anchor.get("conclusions", {}).get(
            "keybdAP_resource_entry_name"
        ),
        "keyboard_helper_keybdB_resource_entry_name": None
        if membership_keyboard_helper_pages_surface_and_anchor is None
        else membership_keyboard_helper_pages_surface_and_anchor.get("conclusions", {}).get(
            "keybdB_resource_entry_name"
        ),
        "keyboard_helper_keybdAP_has_rich_source_contract_but_zero_official_anchor_matches_today": None
        if membership_keyboard_helper_pages_surface_and_anchor is None
        else membership_keyboard_helper_pages_surface_and_anchor.get("conclusions", {}).get(
            "keybdAP_has_rich_source_contract_but_zero_official_anchor_matches_today"
        ),
        "keyboard_helper_keybdB_has_rich_source_contract_but_zero_official_anchor_matches_today": None
        if membership_keyboard_helper_pages_surface_and_anchor is None
        else membership_keyboard_helper_pages_surface_and_anchor.get("conclusions", {}).get(
            "keybdB_has_rich_source_contract_but_zero_official_anchor_matches_today"
        ),
        "keyboard_helper_event_anchorability_blocked_surface_count": None
        if membership_keyboard_helper_event_anchorability is None
        else membership_keyboard_helper_event_anchorability.get("conclusions", {}).get(
            "blocked_surface_count"
        ),
        "keyboard_helper_event_anchorability_compiled_no_anchor_surface_count": None
        if membership_keyboard_helper_event_anchorability is None
        else membership_keyboard_helper_event_anchorability.get("conclusions", {}).get(
            "compiled_no_anchor_surface_count"
        ),
        "keyboard_helper_event_anchorability_compiler_blocked_surfaces": None
        if membership_keyboard_helper_event_anchorability is None
        else membership_keyboard_helper_event_anchorability.get("conclusions", {}).get(
            "compiler_blocked_surfaces"
        ),
        "keyboard_helper_event_anchorability_compiled_no_anchor_surfaces": None
        if membership_keyboard_helper_event_anchorability is None
        else membership_keyboard_helper_event_anchorability.get("conclusions", {}).get(
            "compiled_no_anchor_surfaces"
        ),
        "keyboard_helper_event_anchorability_b251_is_shared_compiled_no_anchor_surface_across_keybdAP_and_keybdB": None
        if membership_keyboard_helper_event_anchorability is None
        else membership_keyboard_helper_event_anchorability.get("conclusions", {}).get(
            "b251_is_shared_compiled_no_anchor_surface_across_keybdAP_and_keybdB"
        ),
        "keyboard_helper_event_anchorability_b0_is_compiled_but_page_specific_between_keybdAP_and_keybdB": None
        if membership_keyboard_helper_event_anchorability is None
        else membership_keyboard_helper_event_anchorability.get("conclusions", {}).get(
            "b0_is_compiled_but_page_specific_between_keybdAP_and_keybdB"
        ),
        "keyboard_helper_compiled_no_anchor_families_b251_is_one_shared_cross_page_compiled_no_anchor_family": None
        if membership_keyboard_helper_compiled_no_anchor_families is None
        else membership_keyboard_helper_compiled_no_anchor_families.get("conclusions", {}).get(
            "b251_is_one_shared_cross_page_compiled_no_anchor_family"
        ),
        "keyboard_helper_compiled_no_anchor_families_b251_shared_non_empty_payload_length_hex": None
        if membership_keyboard_helper_compiled_no_anchor_families is None
        else membership_keyboard_helper_compiled_no_anchor_families.get("conclusions", {}).get(
            "b251_shared_non_empty_payload_length_hex"
        ),
        "keyboard_helper_compiled_no_anchor_families_b0_is_split_into_page_specific_compiled_no_anchor_families": None
        if membership_keyboard_helper_compiled_no_anchor_families is None
        else membership_keyboard_helper_compiled_no_anchor_families.get("conclusions", {}).get(
            "b0_is_split_into_page_specific_compiled_no_anchor_families"
        ),
        "keyboard_helper_compiled_no_anchor_families_b0_shared_non_empty_prefix_length_hex": None
        if membership_keyboard_helper_compiled_no_anchor_families is None
        else membership_keyboard_helper_compiled_no_anchor_families.get("families", {})
        .get("page_specific_b0", {})
        .get("shared_non_empty_prefix_length_hex"),
        "keyboard_helper_compiled_no_anchor_families_b0_page_specific_split_starts_after_shared_btlen_if_field_lt_prefix": None
        if membership_keyboard_helper_compiled_no_anchor_families is None
        else membership_keyboard_helper_compiled_no_anchor_families.get("conclusions", {}).get(
            "b0_page_specific_split_starts_after_shared_btlen_if_field_lt_prefix"
        ),
        "keyboard_helper_compiled_no_anchor_fragment_absence_zero_hit_fragments": None
        if membership_keyboard_helper_compiled_no_anchor_fragment_absence is None
        else membership_keyboard_helper_compiled_no_anchor_fragment_absence.get("conclusions", {}).get(
            "zero_hit_fragments"
        ),
        "keyboard_helper_compiled_no_anchor_fragment_absence_b251_full_payload_and_page_command_have_zero_hits": None
        if membership_keyboard_helper_compiled_no_anchor_fragment_absence is None
        else membership_keyboard_helper_compiled_no_anchor_fragment_absence.get("conclusions", {}).get(
            "b251_full_payload_and_page_command_have_zero_hits"
        ),
        "keyboard_helper_compiled_no_anchor_fragment_absence_b0_full_payloads_shared_prefix_and_if_field_lt_fragment_all_have_zero_hits": None
        if membership_keyboard_helper_compiled_no_anchor_fragment_absence is None
        else membership_keyboard_helper_compiled_no_anchor_fragment_absence.get("conclusions", {}).get(
            "b0_full_payloads_shared_prefix_and_if_field_lt_fragment_all_have_zero_hits"
        ),
        "keyboard_helper_keybdAP_callsite_count": None
        if membership_keyboard_helper_callsite_families is None
        else membership_keyboard_helper_callsite_families.get("conclusions", {}).get(
            "keybdAP_callsite_count"
        ),
        "keyboard_helper_keybdB_callsite_count": None
        if membership_keyboard_helper_callsite_families is None
        else membership_keyboard_helper_callsite_families.get("conclusions", {}).get(
            "keybdB_callsite_count"
        ),
        "keyboard_helper_keybdAP_only_unique_callsite_is_csvAdd_tName": None
        if membership_keyboard_helper_callsite_families is None
        else membership_keyboard_helper_callsite_families.get("conclusions", {}).get(
            "keybdAP_only_unique_callsite_is_csvAdd_tName"
        ),
        "keyboard_helper_keybdB_currently_only_appears_in_csvAdd_numeric_fields": None
        if membership_keyboard_helper_callsite_families is None
        else membership_keyboard_helper_callsite_families.get("conclusions", {}).get(
            "keybdB_currently_only_appears_in_csvAdd_numeric_fields"
        ),
        "main_page_anchor_window_hex": None
        if membership_wrapper_main_page_anchor is None
        else membership_wrapper_main_page_anchor.get("conclusions", {}).get(
            "main_page_anchor_window_hex"
        ),
        "main_page_slot_core_slots": None
        if membership_wrapper_main_page_slot_mapping is None
        else membership_wrapper_main_page_slot_mapping.get("conclusions", {}).get("core_slots"),
        "btnopenfile_branch_target_resources": None
        if membership_btnopenfile_branch_target_pages is None
        else membership_btnopenfile_branch_target_pages.get("conclusions", {}).get(
            "unique_branch_target_resources"
        ),
        "btnopenfile_default_textviewer_branch_window_hex": None
        if membership_btnopenfile_default_textviewer_branch is None
        else membership_btnopenfile_default_textviewer_branch.get("conclusions", {}).get(
            "compiled_default_branch_window_hex"
        ),
        "open_common_families": [item.get("family") for item in ranked_open],
        "next_open_family": None if not ranked_open else ranked_open[0].get("family"),
        "deprioritized_secondary_families": [item.get("family") for item in deprioritized],
        "next_search_focus": None if membership_search_frame is None else membership_search_frame.get("remaining_allowed_search_space", {}).get("next_search_focus"),
        "next_search_oracle_case_ids": []
        if membership_oracle_sources is None
        else [item.get("case_id") for item in membership_oracle_sources.get("priority_order", [])],
        "lifecycle_scheduler_oracle_frontier_top_ranked_family": None
        if membership_lifecycle_scheduler_oracle_frontier is None
        else membership_lifecycle_scheduler_oracle_frontier.get("conclusions", {}).get(
            "top_ranked_family_from_current_ranking_report"
        ),
        "lifecycle_scheduler_oracle_frontier_top_candidate_ids": []
        if membership_lifecycle_scheduler_oracle_frontier is None
        else [
            item.get("candidate_id")
            for item in membership_lifecycle_scheduler_oracle_frontier.get("sections", {}).get(
                "ranked_next_candidates", []
            )
        ],
        "lifecycle_scheduler_oracle_frontier_case49_audio_post_primary_descriptor_is_the_only_complete_official_lifecycle_oracle": None
        if membership_lifecycle_scheduler_oracle_frontier is None
        else membership_lifecycle_scheduler_oracle_frontier.get("conclusions", {}).get(
            "case49_audio_post_primary_descriptor_is_the_only_complete_official_lifecycle_oracle"
        ),
        "lifecycle_scheduler_oracle_frontier_shared_scheduler_record_candidate_remains_undecoded_but_ranked_ahead_of_blind_slot_writes": None
        if membership_lifecycle_scheduler_oracle_frontier is None
        else membership_lifecycle_scheduler_oracle_frontier.get("conclusions", {}).get(
            "shared_scheduler_record_candidate_remains_undecoded_but_ranked_ahead_of_blind_slot_writes"
        ),
        "lifecycle_scheduler_oracle_frontier_hidden_tail_preanchor_corridor_is_a_secondary_wrapper_membership_candidate_not_a_page_load_oracle": None
        if membership_lifecycle_scheduler_oracle_frontier is None
        else membership_lifecycle_scheduler_oracle_frontier.get("conclusions", {}).get(
            "hidden_tail_preanchor_corridor_is_a_secondary_wrapper_membership_candidate_not_a_page_load_oracle"
        ),
        "post_primary_scheduler_page_index_binding_matrix_candidate_page_index_match_pages": []
        if membership_post_primary_scheduler_page_index_binding_matrix is None
        else membership_post_primary_scheduler_page_index_binding_matrix.get("conclusions", {}).get(
            "candidate_page_index_match_pages"
        ),
        "post_primary_scheduler_page_index_binding_matrix_candidate_page_index_matches_omit_main_and_noSDcardError_runtime_indices": None
        if membership_post_primary_scheduler_page_index_binding_matrix is None
        else membership_post_primary_scheduler_page_index_binding_matrix.get("conclusions", {}).get(
            "candidate_page_index_matches_omit_main_and_noSDcardError_runtime_indices"
        ),
        "post_primary_scheduler_page_index_binding_matrix_candidate_binding_pattern_strengthens_secondary_wrapper_page_membership_hypothesis_over_primary_branch_only_hypothesis": None
        if membership_post_primary_scheduler_page_index_binding_matrix is None
        else membership_post_primary_scheduler_page_index_binding_matrix.get("conclusions", {}).get(
            "candidate_binding_pattern_strengthens_secondary_wrapper_page_membership_hypothesis_over_primary_branch_only_hypothesis"
        ),
        "post_primary_scheduler_neighborhood_specificity_candidate_rank_is_1_in_official_case49_audio_neighborhood": None
        if membership_post_primary_scheduler_neighborhood_specificity is None
        else membership_post_primary_scheduler_neighborhood_specificity.get("conclusions", {}).get(
            "candidate_rank_is_1_in_official_case49_audio_neighborhood"
        ),
        "post_primary_scheduler_neighborhood_specificity_candidate_rank_is_1_in_generated_negative_neighborhood": None
        if membership_post_primary_scheduler_neighborhood_specificity is None
        else membership_post_primary_scheduler_neighborhood_specificity.get("conclusions", {}).get(
            "candidate_rank_is_1_in_generated_negative_neighborhood"
        ),
        "post_primary_scheduler_neighborhood_specificity_top_score_family_is_confined_to_the_candidate_overlap_cluster_in_both_sources": None
        if membership_post_primary_scheduler_neighborhood_specificity is None
        else membership_post_primary_scheduler_neighborhood_specificity.get("conclusions", {}).get(
            "top_score_family_is_confined_to_the_candidate_overlap_cluster_in_both_sources"
        ),
        "post_primary_scheduler_neighborhood_specificity_candidate_specificity_supports_secondary_wrapper_page_membership_hypothesis_over_primary_branch_only_hypothesis": None
        if membership_post_primary_scheduler_neighborhood_specificity is None
        else membership_post_primary_scheduler_neighborhood_specificity.get("conclusions", {}).get(
            "candidate_specificity_supports_secondary_wrapper_page_membership_hypothesis_over_primary_branch_only_hypothesis"
        ),
        "scheduler_candidate_to_page_graph_container_correlation_candidate_omits_main_and_noSDcardError_despite_their_primary_branch_status": None
        if membership_scheduler_candidate_to_page_graph_container_correlation is None
        else membership_scheduler_candidate_to_page_graph_container_correlation.get("conclusions", {}).get(
            "candidate_omits_main_and_noSDcardError_despite_their_primary_branch_status"
        ),
        "scheduler_candidate_to_page_graph_container_correlation_candidate_alignment_is_stronger_for_secondary_wrapper_pages_than_for_primary_branch_targets": None
        if membership_scheduler_candidate_to_page_graph_container_correlation is None
        else membership_scheduler_candidate_to_page_graph_container_correlation.get("conclusions", {}).get(
            "candidate_alignment_is_stronger_for_secondary_wrapper_pages_than_for_primary_branch_targets"
        ),
        "scheduler_candidate_to_page_graph_container_correlation_candidate_has_concrete_correlated_compiled_anchors_in_three_independent_secondary_wrapper_subsystems": None
        if membership_scheduler_candidate_to_page_graph_container_correlation is None
        else membership_scheduler_candidate_to_page_graph_container_correlation.get("conclusions", {}).get(
            "candidate_has_concrete_correlated_compiled_anchors_in_three_independent_secondary_wrapper_subsystems"
        ),
        "post_primary_scheduler_candidate_core_window_size_bytes": None
        if membership_post_primary_scheduler_candidate_envelope_field_boundary is None
        else membership_post_primary_scheduler_candidate_envelope_field_boundary.get("conclusions", {}).get(
            "candidate_core_window_size_bytes"
        ),
        "post_primary_scheduler_candidate_core_start_is_a_hard_left_boundary_for_the_full_signal_window": None
        if membership_post_primary_scheduler_candidate_envelope_field_boundary is None
        else membership_post_primary_scheduler_candidate_envelope_field_boundary.get("conclusions", {}).get(
            "candidate_core_start_is_a_hard_left_boundary_for_the_full_signal_window"
        ),
        "post_primary_scheduler_candidate_has_a_soft_right_extension_zone_but_not_a_stronger_alternative_core": None
        if membership_post_primary_scheduler_candidate_envelope_field_boundary is None
        else membership_post_primary_scheduler_candidate_envelope_field_boundary.get("conclusions", {}).get(
            "candidate_has_a_soft_right_extension_zone_but_not_a_stronger_alternative_core"
        ),
        "post_primary_scheduler_candidate_boundary_supports_field_boundary_recovery_without_decoding_field_roles": None
        if membership_post_primary_scheduler_candidate_envelope_field_boundary is None
        else membership_post_primary_scheduler_candidate_envelope_field_boundary.get("conclusions", {}).get(
            "envelope_supports_field_boundary_recovery_without_decoding_field_roles"
        ),
        "post_primary_scheduler_core_to_dual_record_owner_family_correlation_candidate_core_is_not_a_literal_u32_subsequence_of_the_exact_0x5662E_owner_family_record": None
        if membership_post_primary_scheduler_core_to_dual_record_owner_family_correlation is None
        else membership_post_primary_scheduler_core_to_dual_record_owner_family_correlation.get("conclusions", {}).get(
            "candidate_core_is_not_a_literal_u32_subsequence_of_the_exact_0x5662E_owner_family_record"
        ),
        "post_primary_scheduler_core_to_dual_record_owner_family_correlation_dual_record_owner_family_candidate_is_the_best_current_nonlocal_context_for_the_bounded_scheduler_core": None
        if membership_post_primary_scheduler_core_to_dual_record_owner_family_correlation is None
        else membership_post_primary_scheduler_core_to_dual_record_owner_family_correlation.get("conclusions", {}).get(
            "dual_record_owner_family_candidate_is_the_best_current_nonlocal_context_for_the_bounded_scheduler_core"
        ),
        "post_primary_scheduler_core_to_dual_record_owner_family_correlation_candidate_should_now_be_treated_as_a_member_core_signal_correlated_to_a_dual_record_owner_family_not_as_a_literal_record_dump": None
        if membership_post_primary_scheduler_core_to_dual_record_owner_family_correlation is None
        else membership_post_primary_scheduler_core_to_dual_record_owner_family_correlation.get("conclusions", {}).get(
            "candidate_should_now_be_treated_as_a_member_core_signal_correlated_to_a_dual_record_owner_family_not_as_a_literal_record_dump"
        ),
        "wrapper_start_record_stride_neighborhood_dual_subfamily_only_0x5654A_and_0x5662E_are_current_event_offset_0x34_candidates_inside_the_measured_stride_neighborhood": None
        if membership_wrapper_start_record_stride_neighborhood_dual_subfamily is None
        else membership_wrapper_start_record_stride_neighborhood_dual_subfamily.get("conclusions", {}).get(
            "only_0x5654A_and_0x5662E_are_current_event_offset_0x34_candidates_inside_the_measured_stride_neighborhood"
        ),
        "wrapper_start_record_stride_neighborhood_dual_subfamily_only_0x5654A_and_0x5662E_share_the_current_0x18_byte_common_prefix_subfamily": None
        if membership_wrapper_start_record_stride_neighborhood_dual_subfamily is None
        else membership_wrapper_start_record_stride_neighborhood_dual_subfamily.get("conclusions", {}).get(
            "only_0x5654A_and_0x5662E_share_the_current_0x18_byte_common_prefix_subfamily"
        ),
        "wrapper_start_record_stride_neighborhood_dual_subfamily_start_record_cluster_should_be_treated_as_a_heterogeneous_0xE4_stride_neighborhood_with_a_distinguished_dual_record_subfamily": None
        if membership_wrapper_start_record_stride_neighborhood_dual_subfamily is None
        else membership_wrapper_start_record_stride_neighborhood_dual_subfamily.get("conclusions", {}).get(
            "start_record_cluster_should_be_treated_as_a_heterogeneous_0xE4_stride_neighborhood_with_a_distinguished_dual_record_subfamily"
        ),
        "wrapper_start_record_dual_subfamily_to_stride_boundary_owner_extent_dual_subfamily_is_currently_bounded_on_the_left_by_same_stride_control_0x56466": None
        if membership_wrapper_start_record_dual_subfamily_to_stride_boundary_owner_extent is None
        else membership_wrapper_start_record_dual_subfamily_to_stride_boundary_owner_extent.get("conclusions", {}).get(
            "dual_subfamily_is_currently_bounded_on_the_left_by_same_stride_control_0x56466"
        ),
        "wrapper_start_record_dual_subfamily_to_stride_boundary_owner_extent_dual_subfamily_is_currently_bounded_on_the_right_by_same_stride_control_0x56712": None
        if membership_wrapper_start_record_dual_subfamily_to_stride_boundary_owner_extent is None
        else membership_wrapper_start_record_dual_subfamily_to_stride_boundary_owner_extent.get("conclusions", {}).get(
            "dual_subfamily_is_currently_bounded_on_the_right_by_same_stride_control_0x56712"
        ),
        "wrapper_start_record_dual_subfamily_to_stride_boundary_owner_extent_owner_extent_recovery_should_now_treat_the_dual_record_subfamily_boundary_as_narrower_than_the_full_same_stride_run": None
        if membership_wrapper_start_record_dual_subfamily_to_stride_boundary_owner_extent is None
        else membership_wrapper_start_record_dual_subfamily_to_stride_boundary_owner_extent.get("conclusions", {}).get(
            "owner_extent_recovery_should_now_treat_the_dual_record_subfamily_boundary_as_narrower_than_the_full_same_stride_run"
        ),
        "wrapper_start_record_shared_stride_run_schema_partition_measured_shared_stride_run_is_identical_between_case43_and_case44": None
        if membership_wrapper_start_record_shared_stride_run_schema_partition is None
        else membership_wrapper_start_record_shared_stride_run_schema_partition.get("conclusions", {}).get(
            "measured_shared_stride_run_is_identical_between_case43_and_case44"
        ),
        "wrapper_start_record_shared_stride_run_schema_partition_only_0x5654A_and_0x5662E_currently_form_the_event_offset_dual_subfamily_inside_the_measured_shared_stride_run": None
        if membership_wrapper_start_record_shared_stride_run_schema_partition is None
        else membership_wrapper_start_record_shared_stride_run_schema_partition.get("conclusions", {}).get(
            "only_0x5654A_and_0x5662E_currently_form_the_event_offset_dual_subfamily_inside_the_measured_shared_stride_run"
        ),
        "wrapper_start_record_shared_stride_run_schema_partition_the_shared_stride_run_contains_distinct_control_classes_outside_the_current_event_offset_subfamily": None
        if membership_wrapper_start_record_shared_stride_run_schema_partition is None
        else membership_wrapper_start_record_shared_stride_run_schema_partition.get("conclusions", {}).get(
            "the_shared_stride_run_contains_distinct_control_classes_outside_the_current_event_offset_subfamily"
        ),
        "wrapper_start_record_progressive_marker_series_main_page_event_table_correlation_each_progressive_series_row_plus_0x34_matches_one_expected_main_page_button_event_table_offset": None
        if membership_wrapper_start_record_progressive_marker_series_main_page_event_table_correlation is None
        else membership_wrapper_start_record_progressive_marker_series_main_page_event_table_correlation.get("conclusions", {}).get(
            "each_progressive_series_row_plus_0x34_matches_one_expected_main_page_button_event_table_offset"
        ),
        "wrapper_start_record_progressive_marker_series_main_page_event_table_correlation_each_progressive_series_row_maps_to_the_expected_main_page_button_name": None
        if membership_wrapper_start_record_progressive_marker_series_main_page_event_table_correlation is None
        else membership_wrapper_start_record_progressive_marker_series_main_page_event_table_correlation.get("conclusions", {}).get(
            "each_progressive_series_row_maps_to_the_expected_main_page_button_name"
        ),
        "wrapper_start_record_progressive_marker_series_main_page_event_table_correlation_btnOpenFile_btnRenameFile_and_btnDelFile_rows_exactly_hit_known_main_page_anchor_offsets": None
        if membership_wrapper_start_record_progressive_marker_series_main_page_event_table_correlation is None
        else membership_wrapper_start_record_progressive_marker_series_main_page_event_table_correlation.get("conclusions", {}).get(
            "btnOpenFile_btnRenameFile_and_btnDelFile_rows_exactly_hit_known_main_page_anchor_offsets"
        ),
        "wrapper_start_record_main_page_button_event_descriptor_ladder_marker_words_increment_by_constant_0x100_across_the_descriptor_ladder": None
        if membership_wrapper_start_record_main_page_button_event_descriptor_ladder is None
        else membership_wrapper_start_record_main_page_button_event_descriptor_ladder.get("conclusions", {}).get(
            "marker_words_increment_by_constant_0x100_across_the_descriptor_ladder"
        ),
        "wrapper_start_record_main_page_button_event_descriptor_ladder_field_0x1C_increments_by_constant_0x54_across_the_descriptor_ladder": None
        if membership_wrapper_start_record_main_page_button_event_descriptor_ladder is None
        else membership_wrapper_start_record_main_page_button_event_descriptor_ladder.get("conclusions", {}).get(
            "field_0x1C_increments_by_constant_0x54_across_the_descriptor_ladder"
        ),
        "wrapper_start_record_main_page_button_event_descriptor_ladder_field_0x38_and_field_0x3C_both_increment_by_constant_0x2A0000_across_the_descriptor_ladder": None
        if membership_wrapper_start_record_main_page_button_event_descriptor_ladder is None
        else membership_wrapper_start_record_main_page_button_event_descriptor_ladder.get("conclusions", {}).get(
            "field_0x38_and_field_0x3C_both_increment_by_constant_0x2A0000_across_the_descriptor_ladder"
        ),
        "wrapper_start_record_main_page_button_event_descriptor_ladder_field_0x34_follows_main_page_button_event_table_order_but_not_a_constant_numeric_stride": None
        if membership_wrapper_start_record_main_page_button_event_descriptor_ladder is None
        else membership_wrapper_start_record_main_page_button_event_descriptor_ladder.get("conclusions", {}).get(
            "field_0x34_follows_main_page_button_event_table_order_but_not_a_constant_numeric_stride"
        ),
        "wrapper_start_record_button_event_ladder_0x1c_secondary_descriptor_chain_field_0x1C_forms_a_seven_entry_secondary_descriptor_chain": None
        if membership_wrapper_start_record_button_event_ladder_0x1c_secondary_descriptor_chain is None
        else membership_wrapper_start_record_button_event_ladder_0x1c_secondary_descriptor_chain.get("conclusions", {}).get(
            "field_0x1C_forms_a_seven_entry_secondary_descriptor_chain"
        ),
        "wrapper_start_record_button_event_ladder_0x1c_secondary_descriptor_chain_field_0x1C_secondary_descriptor_offsets_increment_by_constant_0x54": None
        if membership_wrapper_start_record_button_event_ladder_0x1c_secondary_descriptor_chain is None
        else membership_wrapper_start_record_button_event_ladder_0x1c_secondary_descriptor_chain.get("conclusions", {}).get(
            "field_0x1C_secondary_descriptor_offsets_increment_by_constant_0x54"
        ),
        "wrapper_start_record_button_event_ladder_0x1c_secondary_descriptor_chain_field_0x1C_secondary_descriptor_chain_is_cross_case_identical_between_case43_and_case44": None
        if membership_wrapper_start_record_button_event_ladder_0x1c_secondary_descriptor_chain is None
        else membership_wrapper_start_record_button_event_ladder_0x1c_secondary_descriptor_chain.get("conclusions", {}).get(
            "field_0x1C_secondary_descriptor_chain_is_cross_case_identical_between_case43_and_case44"
        ),
        "wrapper_start_record_button_event_ladder_0x1c_secondary_descriptor_chain_field_0x1C_secondary_descriptor_chain_rows_are_not_all_byte_identical_to_each_other": None
        if membership_wrapper_start_record_button_event_ladder_0x1c_secondary_descriptor_chain is None
        else membership_wrapper_start_record_button_event_ladder_0x1c_secondary_descriptor_chain.get("conclusions", {}).get(
            "field_0x1C_secondary_descriptor_chain_rows_are_not_all_byte_identical_to_each_other"
        ),
        "wrapper_start_record_secondary_descriptor_chain_schema_partition_no_u32_offsets_are_globally_invariant_across_all_seven_secondary_rows": None
        if membership_wrapper_start_record_secondary_descriptor_chain_schema_partition is None
        else membership_wrapper_start_record_secondary_descriptor_chain_schema_partition.get("conclusions", {}).get(
            "no_u32_offsets_are_globally_invariant_across_all_seven_secondary_rows"
        ),
        "wrapper_start_record_secondary_descriptor_chain_schema_partition_secondary_descriptor_chain_partitions_into_three_coarse_head_families": None
        if membership_wrapper_start_record_secondary_descriptor_chain_schema_partition is None
        else membership_wrapper_start_record_secondary_descriptor_chain_schema_partition.get("conclusions", {}).get(
            "secondary_descriptor_chain_partitions_into_three_coarse_head_families"
        ),
        "wrapper_start_record_secondary_descriptor_chain_schema_partition_btnDelDir_and_btnRenameFile_form_the_tightest_same_family_pair_inside_the_secondary_chain": None
        if membership_wrapper_start_record_secondary_descriptor_chain_schema_partition is None
        else membership_wrapper_start_record_secondary_descriptor_chain_schema_partition.get("conclusions", {}).get(
            "btnDelDir_and_btnRenameFile_form_the_tightest_same_family_pair_inside_the_secondary_chain"
        ),
        "wrapper_start_record_secondary_descriptor_chain_schema_partition_btnOpenFile_and_btnDelFile_form_the_tightest_a0_head_pair_inside_the_secondary_chain": None
        if membership_wrapper_start_record_secondary_descriptor_chain_schema_partition is None
        else membership_wrapper_start_record_secondary_descriptor_chain_schema_partition.get("conclusions", {}).get(
            "btnOpenFile_and_btnDelFile_form_the_tightest_a0_head_pair_inside_the_secondary_chain"
        ),
        "wrapper_start_record_secondary_descriptor_chain_button_order_correlation_head_family_sequence_by_main_page_button_order_is_a0_2e_zero_2e_a0_2e_a0": None
        if membership_wrapper_start_record_secondary_descriptor_chain_button_order_correlation is None
        else membership_wrapper_start_record_secondary_descriptor_chain_button_order_correlation.get("conclusions", {}).get(
            "head_family_sequence_by_main_page_button_order_is_a0_2e_zero_2e_a0_2e_a0"
        ),
        "wrapper_start_record_secondary_descriptor_chain_button_order_correlation_no_secondary_head_family_occupies_one_single_contiguous_button_order_block": None
        if membership_wrapper_start_record_secondary_descriptor_chain_button_order_correlation is None
        else membership_wrapper_start_record_secondary_descriptor_chain_button_order_correlation.get("conclusions", {}).get(
            "no_secondary_head_family_occupies_one_single_contiguous_button_order_block"
        ),
        "wrapper_start_record_secondary_descriptor_chain_button_order_correlation_btnDelDir_and_btnRenameFile_same_family_correlation_is_stronger_than_button_order_adjacency": None
        if membership_wrapper_start_record_secondary_descriptor_chain_button_order_correlation is None
        else membership_wrapper_start_record_secondary_descriptor_chain_button_order_correlation.get("conclusions", {}).get(
            "btnDelDir_and_btnRenameFile_same_family_correlation_is_stronger_than_button_order_adjacency"
        ),
        "wrapper_start_record_secondary_descriptor_chain_button_order_correlation_btnOpenFile_and_btnDelFile_same_family_correlation_is_stronger_than_button_order_adjacency": None
        if membership_wrapper_start_record_secondary_descriptor_chain_button_order_correlation is None
        else membership_wrapper_start_record_secondary_descriptor_chain_button_order_correlation.get("conclusions", {}).get(
            "btnOpenFile_and_btnDelFile_same_family_correlation_is_stronger_than_button_order_adjacency"
        ),
        "wrapper_start_record_secondary_descriptor_class_to_local_structure_correlation_secondary_head_family_correlates_with_reference_like_member_arity_4_3_1": None
        if membership_wrapper_start_record_secondary_descriptor_class_to_local_structure_correlation is None
        else membership_wrapper_start_record_secondary_descriptor_class_to_local_structure_correlation.get("conclusions", {}).get(
            "secondary_head_family_correlates_with_reference_like_member_arity_4_3_1"
        ),
        "wrapper_start_record_secondary_descriptor_class_to_local_structure_correlation_dense_local_corridor_0xA07C_0xA0A4_covers_twenty_one_of_twenty_two_reference_like_high_words": None
        if membership_wrapper_start_record_secondary_descriptor_class_to_local_structure_correlation is None
        else membership_wrapper_start_record_secondary_descriptor_class_to_local_structure_correlation.get("conclusions", {}).get(
            "dense_local_corridor_0xA07C_0xA0A4_covers_twenty_one_of_twenty_two_reference_like_high_words"
        ),
        "wrapper_start_record_secondary_descriptor_class_to_local_structure_correlation_btnDelFile_is_the_only_secondary_row_with_reference_like_member_outside_dense_local_corridor": None
        if membership_wrapper_start_record_secondary_descriptor_class_to_local_structure_correlation is None
        else membership_wrapper_start_record_secondary_descriptor_class_to_local_structure_correlation.get("conclusions", {}).get(
            "btnDelFile_is_the_only_secondary_row_with_reference_like_member_outside_dense_local_corridor"
        ),
        "wrapper_start_record_secondary_descriptor_class_to_local_structure_correlation_reference_like_dense_member_mins_progress_monotonically_with_main_page_button_order": None
        if membership_wrapper_start_record_secondary_descriptor_class_to_local_structure_correlation is None
        else membership_wrapper_start_record_secondary_descriptor_class_to_local_structure_correlation.get("conclusions", {}).get(
            "reference_like_dense_member_mins_progress_monotonically_with_main_page_button_order"
        ),
        "wrapper_start_record_secondary_descriptor_reference_like_payload_scope_dense_preview_decodes_as_lexical_payload_fragments_including_miao_mie_min_ming_miu_runs": None
        if membership_wrapper_start_record_secondary_descriptor_reference_like_payload_scope is None
        else membership_wrapper_start_record_secondary_descriptor_reference_like_payload_scope.get("conclusions", {}).get(
            "dense_preview_decodes_as_lexical_payload_fragments_including_miao_mie_min_ming_miu_runs"
        ),
        "wrapper_start_record_secondary_descriptor_reference_like_payload_scope_outlier_ae84_preview_decodes_as_tai_family_hanzi_payload_not_control_header": None
        if membership_wrapper_start_record_secondary_descriptor_reference_like_payload_scope is None
        else membership_wrapper_start_record_secondary_descriptor_reference_like_payload_scope.get("conclusions", {}).get(
            "outlier_ae84_preview_decodes_as_tai_family_hanzi_payload_not_control_header"
        ),
        "wrapper_start_record_secondary_descriptor_reference_like_payload_scope_all_current_reference_like_high_words_are_out_of_range_in_case42_datarecord_object_region": None
        if membership_wrapper_start_record_secondary_descriptor_reference_like_payload_scope is None
        else membership_wrapper_start_record_secondary_descriptor_reference_like_payload_scope.get("conclusions", {}).get(
            "all_current_reference_like_high_words_are_out_of_range_in_case42_datarecord_object_region"
        ),
        "wrapper_start_record_secondary_descriptor_reference_like_payload_scope_all_current_reference_like_high_words_are_out_of_range_in_case49_audio_official_compile_object_region": None
        if membership_wrapper_start_record_secondary_descriptor_reference_like_payload_scope is None
        else membership_wrapper_start_record_secondary_descriptor_reference_like_payload_scope.get("conclusions", {}).get(
            "all_current_reference_like_high_words_are_out_of_range_in_case49_audio_official_compile_object_region"
        ),
        "wrapper_start_record_secondary_descriptor_compact_local_offset_scope_distinct_compact_local_offsets_form_three_small_shared_local_clusters": None
        if membership_wrapper_start_record_secondary_descriptor_compact_local_offset_scope is None
        else membership_wrapper_start_record_secondary_descriptor_compact_local_offset_scope.get("conclusions", {}).get(
            "distinct_compact_local_offsets_form_three_small_shared_local_clusters"
        ),
        "wrapper_start_record_secondary_descriptor_compact_local_offset_scope_all_compact_local_offset_windows_are_identical_between_case43_and_case44": None
        if membership_wrapper_start_record_secondary_descriptor_compact_local_offset_scope is None
        else membership_wrapper_start_record_secondary_descriptor_compact_local_offset_scope.get("conclusions", {}).get(
            "all_compact_local_offset_windows_are_identical_between_case43_and_case44"
        ),
        "wrapper_start_record_secondary_descriptor_compact_local_offset_scope_all_compact_local_offset_windows_differ_from_case42_datarecord_at_the_same_offsets": None
        if membership_wrapper_start_record_secondary_descriptor_compact_local_offset_scope is None
        else membership_wrapper_start_record_secondary_descriptor_compact_local_offset_scope.get("conclusions", {}).get(
            "all_compact_local_offset_windows_differ_from_case42_datarecord_at_the_same_offsets"
        ),
        "wrapper_start_record_secondary_descriptor_compact_local_offset_scope_all_compact_local_offset_windows_differ_from_case49_audio_at_the_same_offsets": None
        if membership_wrapper_start_record_secondary_descriptor_compact_local_offset_scope is None
        else membership_wrapper_start_record_secondary_descriptor_compact_local_offset_scope.get("conclusions", {}).get(
            "all_compact_local_offset_windows_differ_from_case49_audio_at_the_same_offsets"
        ),
        "wrapper_start_record_secondary_descriptor_compact_local_offset_main_page_slot_anchor_correlation_case43_and_case44_compact_window_slot_hits_are_identical": None
        if membership_wrapper_start_record_secondary_descriptor_compact_local_offset_main_page_slot_anchor_correlation is None
        else membership_wrapper_start_record_secondary_descriptor_compact_local_offset_main_page_slot_anchor_correlation.get("conclusions", {}).get(
            "case43_and_case44_compact_window_slot_hits_are_identical"
        ),
        "wrapper_start_record_secondary_descriptor_compact_local_offset_main_page_slot_anchor_correlation_compact_centers_0x222_through_0x23C_all_include_exact_fbrowser0_txt_slot_hit": None
        if membership_wrapper_start_record_secondary_descriptor_compact_local_offset_main_page_slot_anchor_correlation is None
        else membership_wrapper_start_record_secondary_descriptor_compact_local_offset_main_page_slot_anchor_correlation.get("conclusions", {}).get(
            "compact_centers_0x222_through_0x23C_all_include_exact_fbrowser0_txt_slot_hit"
        ),
        "wrapper_start_record_secondary_descriptor_compact_local_offset_main_page_slot_anchor_correlation_compact_center_0x43F_contains_exact_msg_y_and_fbpath_y_slot_hits": None
        if membership_wrapper_start_record_secondary_descriptor_compact_local_offset_main_page_slot_anchor_correlation is None
        else membership_wrapper_start_record_secondary_descriptor_compact_local_offset_main_page_slot_anchor_correlation.get("conclusions", {}).get(
            "compact_center_0x43F_contains_exact_msg_y_and_fbpath_y_slot_hits"
        ),
        "wrapper_start_record_secondary_descriptor_compact_local_offset_main_page_slot_anchor_correlation_compact_centers_0x121_and_0x131_still_have_no_exact_known_main_page_slot_hits": None
        if membership_wrapper_start_record_secondary_descriptor_compact_local_offset_main_page_slot_anchor_correlation is None
        else membership_wrapper_start_record_secondary_descriptor_compact_local_offset_main_page_slot_anchor_correlation.get("conclusions", {}).get(
            "compact_centers_0x121_and_0x131_still_have_no_exact_known_main_page_slot_hits"
        ),
        "wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood_btnNewDir_btnNewFile_btnDelDir_y_slots_form_a_regular_0x2A_ladder": None
        if membership_wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood is None
        else membership_wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood.get("conclusions", {}).get(
            "btnNewDir_btnNewFile_btnDelDir_y_slots_form_a_regular_0x2A_ladder"
        ),
        "wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood_offset_0x121_sits_two_bytes_before_btnNewFile_y_slot_0x123": None
        if membership_wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood is None
        else membership_wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood.get("conclusions", {}).get(
            "offset_0x121_sits_two_bytes_before_btnNewFile_y_slot_0x123"
        ),
        "wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood_offset_0x131_sits_fourteen_bytes_after_btnNewFile_y_and_twenty_eight_bytes_before_btnDelDir_y": None
        if membership_wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood is None
        else membership_wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood.get("conclusions", {}).get(
            "offset_0x131_sits_fourteen_bytes_after_btnNewFile_y_and_twenty_eight_bytes_before_btnDelDir_y"
        ),
        "wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood_button_y_neighborhood_window_is_identical_between_case43_and_case44": None
        if membership_wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood is None
        else membership_wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood.get("conclusions", {}).get(
            "button_y_neighborhood_window_is_identical_between_case43_and_case44"
        ),
        "wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood_button_y_neighborhood_window_differs_in_case42_and_case49": None
        if membership_wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood is None
        else membership_wrapper_start_record_secondary_descriptor_compact_offset_unresolved_pair_btny_neighborhood.get("conclusions", {}).get(
            "button_y_neighborhood_window_differs_in_case42_and_case49"
        ),
        "wrapper_start_record_secondary_descriptor_btnnewfile_local_slice_btnnewfile_local_slice_starts_two_bytes_before_btnNewFile_y_slot": None
        if membership_wrapper_start_record_secondary_descriptor_btnnewfile_local_slice is None
        else membership_wrapper_start_record_secondary_descriptor_btnnewfile_local_slice.get("conclusions", {}).get(
            "btnnewfile_local_slice_starts_two_bytes_before_btnNewFile_y_slot"
        ),
        "wrapper_start_record_secondary_descriptor_btnnewfile_local_slice_offset_0x131_sits_fourteen_bytes_after_btnNewFile_y_and_nine_bytes_before_btnNewFile_txt": None
        if membership_wrapper_start_record_secondary_descriptor_btnnewfile_local_slice is None
        else membership_wrapper_start_record_secondary_descriptor_btnnewfile_local_slice.get("conclusions", {}).get(
            "offset_0x131_sits_fourteen_bytes_after_btnNewFile_y_and_nine_bytes_before_btnNewFile_txt"
        ),
        "wrapper_start_record_secondary_descriptor_btnnewfile_local_slice_btnnewfile_local_slice_is_identical_between_case43_and_case44": None
        if membership_wrapper_start_record_secondary_descriptor_btnnewfile_local_slice is None
        else membership_wrapper_start_record_secondary_descriptor_btnnewfile_local_slice.get("conclusions", {}).get(
            "btnnewfile_local_slice_is_identical_between_case43_and_case44"
        ),
        "wrapper_start_record_secondary_descriptor_btnnewfile_local_slice_btnnewfile_local_slice_differs_in_case42_and_case49": None
        if membership_wrapper_start_record_secondary_descriptor_btnnewfile_local_slice is None
        else membership_wrapper_start_record_secondary_descriptor_btnnewfile_local_slice.get("conclusions", {}).get(
            "btnnewfile_local_slice_differs_in_case42_and_case49"
        ),
        "wrapper_start_record_sidebar_button_local_slice_ladder_sidebar_button_y_slots_form_a_regular_0x2A_ladder": None
        if membership_wrapper_start_record_sidebar_button_local_slice_ladder is None
        else membership_wrapper_start_record_sidebar_button_local_slice_ladder.get("conclusions", {}).get(
            "sidebar_button_y_slots_form_a_regular_0x2A_ladder"
        ),
        "wrapper_start_record_sidebar_button_local_slice_ladder_sidebar_button_txt_slots_form_a_regular_0x2A_ladder": None
        if membership_wrapper_start_record_sidebar_button_local_slice_ladder is None
        else membership_wrapper_start_record_sidebar_button_local_slice_ladder.get("conclusions", {}).get(
            "sidebar_button_txt_slots_form_a_regular_0x2A_ladder"
        ),
        "wrapper_start_record_sidebar_button_local_slice_ladder_sidebar_button_local_slices_all_have_fixed_length_0x19": None
        if membership_wrapper_start_record_sidebar_button_local_slice_ladder is None
        else membership_wrapper_start_record_sidebar_button_local_slice_ladder.get("conclusions", {}).get(
            "sidebar_button_local_slices_all_have_fixed_length_0x19"
        ),
        "wrapper_start_record_sidebar_button_local_slice_ladder_sidebar_button_local_slices_are_identical_between_case43_and_case44_position_by_position": None
        if membership_wrapper_start_record_sidebar_button_local_slice_ladder is None
        else membership_wrapper_start_record_sidebar_button_local_slice_ladder.get("conclusions", {}).get(
            "sidebar_button_local_slices_are_identical_between_case43_and_case44_position_by_position"
        ),
        "wrapper_start_record_sidebar_button_local_slice_ladder_btnNewFile_local_slice_is_one_member_of_the_shared_sidebar_button_local_slice_ladder": None
        if membership_wrapper_start_record_sidebar_button_local_slice_ladder is None
        else membership_wrapper_start_record_sidebar_button_local_slice_ladder.get("conclusions", {}).get(
            "btnNewFile_local_slice_is_one_member_of_the_shared_sidebar_button_local_slice_ladder"
        ),
        "wrapper_start_record_btnnewfile_local_slice_neighbor_overlap_btnNewFile_local_slice_is_most_similar_to_btnDelDir_and_btnRenameFile": None
        if membership_wrapper_start_record_btnnewfile_local_slice_neighbor_overlap is None
        else membership_wrapper_start_record_btnnewfile_local_slice_neighbor_overlap.get("conclusions", {}).get(
            "btnNewFile_local_slice_is_most_similar_to_btnDelDir_and_btnRenameFile"
        ),
        "wrapper_start_record_btnnewfile_local_slice_neighbor_overlap_btnNewFile_local_slice_overlap_with_btnDelDir_and_btnRenameFile_is_17_bytes_each": None
        if membership_wrapper_start_record_btnnewfile_local_slice_neighbor_overlap is None
        else membership_wrapper_start_record_btnnewfile_local_slice_neighbor_overlap.get("conclusions", {}).get(
            "btnNewFile_local_slice_overlap_with_btnDelDir_and_btnRenameFile_is_17_bytes_each"
        ),
        "wrapper_start_record_btnnewfile_local_slice_neighbor_overlap_btnNewFile_local_slice_overlap_with_btnNewDir_btnOpenFile_and_btnUp_is_only_11_bytes_each": None
        if membership_wrapper_start_record_btnnewfile_local_slice_neighbor_overlap is None
        else membership_wrapper_start_record_btnnewfile_local_slice_neighbor_overlap.get("conclusions", {}).get(
            "btnNewFile_local_slice_overlap_with_btnNewDir_btnOpenFile_and_btnUp_is_only_11_bytes_each"
        ),
        "wrapper_start_record_btnnewfile_local_slice_neighbor_overlap_btnNewFile_local_slice_overlap_with_btnDelFile_is_the_lowest_current_neighbor_match": None
        if membership_wrapper_start_record_btnnewfile_local_slice_neighbor_overlap is None
        else membership_wrapper_start_record_btnnewfile_local_slice_neighbor_overlap.get("conclusions", {}).get(
            "btnNewFile_local_slice_overlap_with_btnDelFile_is_the_lowest_current_neighbor_match"
        ),
        "wrapper_start_record_sidebar_mid_triplet_subfamily_btnNewFile_btnDelDir_and_btnRenameFile_form_the_current_strongest_sidebar_local_triplet": None
        if membership_wrapper_start_record_sidebar_mid_triplet_subfamily is None
        else membership_wrapper_start_record_sidebar_mid_triplet_subfamily.get("conclusions", {}).get(
            "btnNewFile_btnDelDir_and_btnRenameFile_form_the_current_strongest_sidebar_local_triplet"
        ),
        "wrapper_start_record_sidebar_mid_triplet_subfamily_btnNewFile_matches_btnDelDir_and_btnRenameFile_at_17_bytes_each": None
        if membership_wrapper_start_record_sidebar_mid_triplet_subfamily is None
        else membership_wrapper_start_record_sidebar_mid_triplet_subfamily.get("conclusions", {}).get(
            "btnNewFile_matches_btnDelDir_and_btnRenameFile_at_17_bytes_each"
        ),
        "wrapper_start_record_sidebar_mid_triplet_subfamily_triplet_shares_fourteen_common_byte_positions": None
        if membership_wrapper_start_record_sidebar_mid_triplet_subfamily is None
        else membership_wrapper_start_record_sidebar_mid_triplet_subfamily.get("conclusions", {}).get(
            "triplet_shares_fourteen_common_byte_positions"
        ),
        "wrapper_start_record_sidebar_mid_triplet_subfamily_btnDelDir_and_btnRenameFile_are_closer_to_btnNewFile_than_to_each_other": None
        if membership_wrapper_start_record_sidebar_mid_triplet_subfamily is None
        else membership_wrapper_start_record_sidebar_mid_triplet_subfamily.get("conclusions", {}).get(
            "btnDelDir_and_btnRenameFile_are_closer_to_btnNewFile_than_to_each_other"
        ),
        "wrapper_start_record_sidebar_mid_triplet_common_core_partition_triplet_common_core_spans_fourteen_byte_positions": None
        if membership_wrapper_start_record_sidebar_mid_triplet_common_core_partition is None
        else membership_wrapper_start_record_sidebar_mid_triplet_common_core_partition.get("conclusions", {}).get(
            "triplet_common_core_spans_fourteen_byte_positions"
        ),
        "wrapper_start_record_sidebar_mid_triplet_common_core_partition_all_triplet_differentials_are_confined_to_the_first_fifteen_bytes": None
        if membership_wrapper_start_record_sidebar_mid_triplet_common_core_partition is None
        else membership_wrapper_start_record_sidebar_mid_triplet_common_core_partition.get("conclusions", {}).get(
            "all_triplet_differentials_are_confined_to_the_first_fifteen_bytes"
        ),
        "wrapper_start_record_sidebar_mid_triplet_common_core_partition_triplet_shares_a_contiguous_ten_byte_suffix_from_index_15_through_24": None
        if membership_wrapper_start_record_sidebar_mid_triplet_common_core_partition is None
        else membership_wrapper_start_record_sidebar_mid_triplet_common_core_partition.get("conclusions", {}).get(
            "triplet_shares_a_contiguous_ten_byte_suffix_from_index_15_through_24"
        ),
        "wrapper_start_record_sidebar_mid_triplet_common_core_partition_btnNewFile_btnDelDir_btnRenameFile_triplet_should_now_be_treated_as_one_shared_local_core_plus_small_differential_prefix_family": None
        if membership_wrapper_start_record_sidebar_mid_triplet_common_core_partition is None
        else membership_wrapper_start_record_sidebar_mid_triplet_common_core_partition.get("conclusions", {}).get(
            "btnNewFile_btnDelDir_btnRenameFile_triplet_should_now_be_treated_as_one_shared_local_core_plus_small_differential_prefix_family"
        ),
        "wrapper_start_record_sidebar_mid_triplet_differential_ownership_differential_prefix_splits_into_seven_singleton_nonzero_sites_and_four_mixed_two_button_sites": None
        if membership_wrapper_start_record_sidebar_mid_triplet_differential_ownership is None
        else membership_wrapper_start_record_sidebar_mid_triplet_differential_ownership.get("conclusions", {}).get(
            "differential_prefix_splits_into_seven_singleton_nonzero_sites_and_four_mixed_two_button_sites"
        ),
        "wrapper_start_record_sidebar_mid_triplet_differential_ownership_btnRenameFile_is_the_only_button_present_in_every_mixed_two_button_site": None
        if membership_wrapper_start_record_sidebar_mid_triplet_differential_ownership is None
        else membership_wrapper_start_record_sidebar_mid_triplet_differential_ownership.get("conclusions", {}).get(
            "btnRenameFile_is_the_only_button_present_in_every_mixed_two_button_site"
        ),
        "wrapper_start_record_sidebar_mid_triplet_differential_ownership_btnNewFile_and_btnDelDir_do_not_share_any_mixed_two_button_site_without_btnRenameFile": None
        if membership_wrapper_start_record_sidebar_mid_triplet_differential_ownership is None
        else membership_wrapper_start_record_sidebar_mid_triplet_differential_ownership.get("conclusions", {}).get(
            "btnNewFile_and_btnDelDir_do_not_share_any_mixed_two_button_site_without_btnRenameFile"
        ),
        "wrapper_start_record_sidebar_mid_triplet_differential_ownership_no_differential_prefix_site_reuses_one_shared_nonzero_value_across_two_buttons_against_a_third_outlier": None
        if membership_wrapper_start_record_sidebar_mid_triplet_differential_ownership is None
        else membership_wrapper_start_record_sidebar_mid_triplet_differential_ownership.get("conclusions", {}).get(
            "no_differential_prefix_site_reuses_one_shared_nonzero_value_across_two_buttons_against_a_third_outlier"
        ),
        "wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition_mixed_sites_split_into_a_three_site_btnNewFile_btnRenameFile_partition_and_a_singleton_btnDelDir_btnRenameFile_partition": None
        if membership_wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition is None
        else membership_wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition.get("conclusions", {}).get(
            "mixed_sites_split_into_a_three_site_btnNewFile_btnRenameFile_partition_and_a_singleton_btnDelDir_btnRenameFile_partition"
        ),
        "wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition_btnRenameFile_is_the_only_bridge_button_across_both_mixed_pair_partitions": None
        if membership_wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition is None
        else membership_wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition.get("conclusions", {}).get(
            "btnRenameFile_is_the_only_bridge_button_across_both_mixed_pair_partitions"
        ),
        "wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition_btnDelDir_is_absent_from_the_three_site_btnNewFile_btnRenameFile_partition": None
        if membership_wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition is None
        else membership_wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition.get("conclusions", {}).get(
            "btnDelDir_is_absent_from_the_three_site_btnNewFile_btnRenameFile_partition"
        ),
        "wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition_btnNewFile_is_absent_from_the_singleton_btnDelDir_btnRenameFile_partition": None
        if membership_wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition is None
        else membership_wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition.get("conclusions", {}).get(
            "btnNewFile_is_absent_from_the_singleton_btnDelDir_btnRenameFile_partition"
        ),
        "wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition_indices_7_and_8_form_the_only_adjacent_mixed_site_subrun": None
        if membership_wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition is None
        else membership_wrapper_start_record_sidebar_mid_triplet_mixed_pair_partition.get("conclusions", {}).get(
            "indices_7_and_8_form_the_only_adjacent_mixed_site_subrun"
        ),
        "wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_subrun_partition_btnNewFile_btnRenameFile_three_site_lane_splits_into_isolated_index_4_and_adjacent_subrun_7_8": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_subrun_partition is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_subrun_partition.get("conclusions", {}).get(
            "btnNewFile_btnRenameFile_three_site_lane_splits_into_isolated_index_4_and_adjacent_subrun_7_8"
        ),
        "wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_subrun_partition_adjacent_subrun_7_8_shares_btnRenameFile_value_0x01_while_isolated_index_4_carries_0xFF": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_subrun_partition is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_subrun_partition.get("conclusions", {}).get(
            "adjacent_subrun_7_8_shares_btnRenameFile_value_0x01_while_isolated_index_4_carries_0xFF"
        ),
        "wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_subrun_partition_adjacent_subrun_7_8_still_splits_by_btnNewFile_values_0xC4_and_0x20": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_subrun_partition is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_subrun_partition.get("conclusions", {}).get(
            "adjacent_subrun_7_8_still_splits_by_btnNewFile_values_0xC4_and_0x20"
        ),
        "wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_subrun_partition_btnDelDir_remains_zero_across_the_full_btnNewFile_btnRenameFile_three_site_lane": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_subrun_partition is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_subrun_partition.get("conclusions", {}).get(
            "btnDelDir_remains_zero_across_the_full_btnNewFile_btnRenameFile_three_site_lane"
        ),
        "wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_adjacent_subrun_value_split_adjacent_subrun_7_8_keeps_btnDelDir_zero_and_btnRenameFile_0x01_constant": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_adjacent_subrun_value_split is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_adjacent_subrun_value_split.get("conclusions", {}).get(
            "adjacent_subrun_7_8_keeps_btnDelDir_zero_and_btnRenameFile_0x01_constant"
        ),
        "wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_adjacent_subrun_value_split_adjacent_subrun_7_8_splits_only_by_btnNewFile_value_0xC4_vs_0x20": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_adjacent_subrun_value_split is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_adjacent_subrun_value_split.get("conclusions", {}).get(
            "adjacent_subrun_7_8_splits_only_by_btnNewFile_value_0xC4_vs_0x20"
        ),
        "wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_adjacent_subrun_value_split_index_7_and_index_8_remain_the_only_members_of_the_adjacent_subrun": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_adjacent_subrun_value_split is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_adjacent_subrun_value_split.get("conclusions", {}).get(
            "index_7_and_index_8_remain_the_only_members_of_the_adjacent_subrun"
        ),
        "wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_isolated_index4_outlier_index_4_is_the_only_non_adjacent_mixed_site_in_the_btnNewFile_btnRenameFile_lane": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_isolated_index4_outlier is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_isolated_index4_outlier.get("conclusions", {}).get(
            "index_4_is_the_only_non_adjacent_mixed_site_in_the_btnNewFile_btnRenameFile_lane"
        ),
        "wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_isolated_index4_outlier_index_4_is_the_only_btnNewFile_btnRenameFile_mixed_site_with_btnRenameFile_0xFF": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_isolated_index4_outlier is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_isolated_index4_outlier.get("conclusions", {}).get(
            "index_4_is_the_only_btnNewFile_btnRenameFile_mixed_site_with_btnRenameFile_0xFF"
        ),
        "wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_isolated_index4_outlier_index_4_keeps_btnDelDir_zero_but_shifts_both_nonzero_values_away_from_the_adjacent_subrun_7_8_pattern": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_isolated_index4_outlier is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_isolated_index4_outlier.get("conclusions", {}).get(
            "index_4_keeps_btnDelDir_zero_but_shifts_both_nonzero_values_away_from_the_adjacent_subrun_7_8_pattern"
        ),
        "wrapper_start_record_sidebar_mid_triplet_btndeldir_renamefile_singleton_index11_index_11_is_the_only_mixed_site_in_the_btnDelDir_btnRenameFile_lane": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btndeldir_renamefile_singleton_index11 is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btndeldir_renamefile_singleton_index11.get("conclusions", {}).get(
            "index_11_is_the_only_mixed_site_in_the_btnDelDir_btnRenameFile_lane"
        ),
        "wrapper_start_record_sidebar_mid_triplet_btndeldir_renamefile_singleton_index11_index_11_keeps_btnNewFile_zero_while_btnDelDir_is_0x01_and_btnRenameFile_is_0x32": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btndeldir_renamefile_singleton_index11 is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btndeldir_renamefile_singleton_index11.get("conclusions", {}).get(
            "index_11_keeps_btnNewFile_zero_while_btnDelDir_is_0x01_and_btnRenameFile_is_0x32"
        ),
        "wrapper_start_record_sidebar_mid_triplet_btndeldir_renamefile_singleton_index11_index_11_is_the_only_remaining_mixed_site_not_in_the_btnNewFile_btnRenameFile_three_site_lane": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btndeldir_renamefile_singleton_index11 is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btndeldir_renamefile_singleton_index11.get("conclusions", {}).get(
            "index_11_is_the_only_remaining_mixed_site_not_in_the_btnNewFile_btnRenameFile_three_site_lane"
        ),
        "wrapper_start_record_sidebar_mid_triplet_singleton_endpoint_contrast_indices_4_and_11_are_the_only_current_singleton_mixed_site_endpoints": None
        if membership_wrapper_start_record_sidebar_mid_triplet_singleton_endpoint_contrast is None
        else membership_wrapper_start_record_sidebar_mid_triplet_singleton_endpoint_contrast.get("conclusions", {}).get(
            "indices_4_and_11_are_the_only_current_singleton_mixed_site_endpoints"
        ),
        "wrapper_start_record_sidebar_mid_triplet_singleton_endpoint_contrast_both_singleton_endpoints_include_btnRenameFile_but_rotate_the_zero_button_between_btnDelDir_and_btnNewFile": None
        if membership_wrapper_start_record_sidebar_mid_triplet_singleton_endpoint_contrast is None
        else membership_wrapper_start_record_sidebar_mid_triplet_singleton_endpoint_contrast.get("conclusions", {}).get(
            "both_singleton_endpoints_include_btnRenameFile_but_rotate_the_zero_button_between_btnDelDir_and_btnNewFile"
        ),
        "wrapper_start_record_sidebar_mid_triplet_singleton_endpoint_contrast_index4_and_index11_form_distinct_endpoint_shapes_7D_FF_vs_01_32_around_shared_btnRenameFile_membership": None
        if membership_wrapper_start_record_sidebar_mid_triplet_singleton_endpoint_contrast is None
        else membership_wrapper_start_record_sidebar_mid_triplet_singleton_endpoint_contrast.get("conclusions", {}).get(
            "index4_and_index11_form_distinct_endpoint_shapes_7D_FF_vs_01_32_around_shared_btnRenameFile_membership"
        ),
        "wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_nonzero_pair_index_4_splits_cleanly_into_btnDelDir_zero_plus_btnNewFile_0x7D_plus_btnRenameFile_0xFF": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_nonzero_pair is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_nonzero_pair.get("conclusions", {}).get(
            "index_4_splits_cleanly_into_btnDelDir_zero_plus_btnNewFile_0x7D_plus_btnRenameFile_0xFF"
        ),
        "wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_nonzero_pair_btnRenameFile_carries_the_larger_nonzero_byte_inside_index_4": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_nonzero_pair is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_nonzero_pair.get("conclusions", {}).get(
            "btnRenameFile_carries_the_larger_nonzero_byte_inside_index_4"
        ),
        "wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_nonzero_pair_index_4_is_the_only_current_btnNewFile_btnRenameFile_mixed_site_with_a_zero_plus_two_nonzero_ordered_pair_shape": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_nonzero_pair is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_nonzero_pair.get("conclusions", {}).get(
            "index_4_is_the_only_current_btnNewFile_btnRenameFile_mixed_site_with_a_zero_plus_two_nonzero_ordered_pair_shape"
        ),
        "wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_bitmask_relation_btnNewFile_0x7D_is_a_strict_bit_subset_of_btnRenameFile_0xFF_at_index_4": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_bitmask_relation is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_bitmask_relation.get("conclusions", {}).get(
            "btnNewFile_0x7D_is_a_strict_bit_subset_of_btnRenameFile_0xFF_at_index_4"
        ),
        "wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_bitmask_relation_index_4_nonzero_pair_or_mask_is_0xFF_and_and_mask_is_0x7D": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_bitmask_relation is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_bitmask_relation.get("conclusions", {}).get(
            "index_4_nonzero_pair_or_mask_is_0xFF_and_and_mask_is_0x7D"
        ),
        "wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_bitmask_relation_index_4_nonzero_pair_differs_only_by_xor_mask_0x82_at_bit_positions_1_and_7": None
        if membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_bitmask_relation is None
        else membership_wrapper_start_record_sidebar_mid_triplet_btnnewfile_renamefile_index4_bitmask_relation.get("conclusions", {}).get(
            "index_4_nonzero_pair_differs_only_by_xor_mask_0x82_at_bit_positions_1_and_7"
        ),
        "next_search_window_oracle_case_id": None
        if membership_search_window is None
        else membership_search_window.get("preferred_complete_official_window", {}).get("case_id"),
        "next_search_window_offset_hex": None
        if membership_search_window is None
        else membership_search_window.get("preferred_complete_official_window", {}).get("offset_hex"),
        "blocked_slot_write_exclusions": []
        if membership_search_window is None
        else [item.get("slot_hex") for item in membership_search_window.get("blocked_slot_write_exclusions", [])],
        "explicit_non_candidates": shortlist.get("explicit_non_candidates"),
    }


def _hmisafe_sample_chain_summary(result: dict[str, Any] | None) -> dict[str, Any]:
    if result is None:
        return {
            "status": "missing",
            "hmi": None,
            "true_pre_tft": None,
            "official_final_tft": None,
            "reproduced_final_sha256": None,
            "byte_identical": None,
            "body_unchanged": None,
            "all_changes_confined_to_header_or_eof4": None,
            "hmisafe_is_resource_packer_on_observed_boundary": None,
            "footer": None,
            "remaining_uncertainty": None,
        }

    sample = result.get("sample_chain", {})
    finalization = result.get("finalization", {})
    mutation = result.get("mutation_boundary", {})
    evidence = result.get("evidence", {})
    finalizer_conclusion = evidence.get("finalizer_report_conclusion", {})
    computed_values = finalization.get("computed_values", {})
    diff = finalization.get("byte_diff_against_official_final", {})
    return {
        "status": result.get("status"),
        "hmi": sample.get("hmi"),
        "true_pre_tft": sample.get("true_pre_tft"),
        "official_final_tft": sample.get("official_final_tft"),
        "reproduced_final_sha256": sample.get("reproduced_final_in_memory", {}).get("sha256"),
        "byte_identical": diff.get("byte_identical"),
        "diff_count": diff.get("diff_count"),
        "body_unchanged": mutation.get("body_range", {}).get("unchanged"),
        "all_changes_confined_to_header_or_eof4": mutation.get(
            "all_changes_confined_to_header_or_eof4"
        ),
        "hmisafe_is_resource_packer_on_observed_boundary": mutation.get(
            "hmisafe_is_resource_packer_on_observed_boundary"
        ),
        "footer": computed_values.get("footer"),
        "footer_hex": computed_values.get("footer_hex"),
        "file_crc": computed_values.get("file_crc"),
        "file_crc_hex": computed_values.get("file_crc_hex"),
        "remaining_uncertainty": finalizer_conclusion.get("remaining_uncertainty"),
    }


def _next_probe_run_summary(result: dict[str, Any] | None) -> dict[str, Any]:
    if result is None:
        return {
            "status": "missing",
            "summary": None,
            "candidate_tft": None,
            "checksum_valid": None,
            "hmisafe_all_ok": None,
            "ready_for_live_upload": None,
            "hardware_quarantine_blocked": None,
            "uploaded": None,
            "safe_to_flash": None,
            "result_json": None,
        }

    summary = result.get("summary", {})
    candidate = result.get("candidate_tft", {})
    checksum = result.get("checksum", {})
    hmisafe = result.get("hmisafe", {})
    field_map_invariants = result.get("field_map_invariants", {})
    readiness = result.get("readiness", {}).get("summary", {})
    return {
        "status": result.get("bundle_status"),
        "target": result.get("target"),
        "result_json": result.get("result_json"),
        "summary": summary,
        "candidate_tft": {
            "path": candidate.get("path"),
            "expected_sha256": candidate.get("expected_sha256"),
            "actual_sha256": candidate.get("actual_sha256"),
            "sha256_match": candidate.get("sha256_match"),
        },
        "checksum_valid": checksum.get("valid"),
        "hmisafe_all_ok": hmisafe.get("all_ok"),
        "field_map_invariants_ok": field_map_invariants.get("summary", {}).get("ok"),
        "field_map_failed_hard_checks": field_map_invariants.get("summary", {}).get("failed_hard_checks"),
        "ready_for_live_upload": summary.get(
            "ready_for_live_upload", readiness.get("ready_for_live_upload")
        ),
        "hardware_quarantine_blocked": summary.get(
            "hardware_quarantine_blocked", readiness.get("hardware_quarantine_blocked")
        ),
        "uploaded": summary.get("uploaded"),
        "safe_to_flash": summary.get("safe_to_flash"),
        "steps": result.get("steps"),
    }


def _no_upload_runtime_summary(result: dict[str, Any] | None) -> dict[str, Any]:
    if result is None:
        return {
            "status": "missing",
            "summary": None,
            "candidate_tft": None,
            "offline_gates": None,
            "serial_preflight": None,
            "no_upload_live_smoke": None,
        }

    summary = result.get("summary", {})
    serial_preflight = result.get("serial_preflight", {})
    live_smoke = result.get("no_upload_live_smoke", {})
    return {
        "status": result.get("status"),
        "summary": summary,
        "candidate_tft": result.get("candidate_tft"),
        "offline_gates": result.get("offline_gates"),
        "serial_preflight": {
            "connect_ok": serial_preflight.get("connect_ok"),
            "model": serial_preflight.get("model"),
            "model_ok": serial_preflight.get("model_ok"),
            "runtime_ok": serial_preflight.get("runtime_ok"),
            "public_upload_ready": serial_preflight.get("public_upload_ready"),
            "diagnosis": serial_preflight.get("diagnosis"),
        },
        "no_upload_live_smoke": {
            "uploaded": live_smoke.get("uploaded"),
            "serial_checks_ok": live_smoke.get("serial_checks_ok"),
            "failed_serial_check_count": len(live_smoke.get("failed_serial_checks") or []),
        },
    }


def _runtime_recovery_summary(result: dict[str, Any] | None) -> dict[str, Any]:
    if result is None:
        return {
            "status": "missing",
            "summary": None,
            "serial": None,
            "action": None,
            "camera": None,
        }

    camera = result.get("camera", {})
    stats = camera.get("stats") or {}
    return {
        "status": result.get("status"),
        "summary": result.get("summary"),
        "serial": result.get("serial"),
        "action": result.get("action"),
        "camera": {
            "captured": camera.get("captured"),
            "use_as_state_proof": camera.get("use_as_state_proof"),
            "mean_luma": stats.get("mean_luma"),
            "bytes": stats.get("bytes"),
        },
    }


def _artifact_ref(path: Path) -> dict[str, Any]:
    return {
        "path": _relative_artifact(path),
        "exists": path.exists(),
        "sha256": _sha256_file(path) if path.exists() else None,
    }


def _relative_artifact(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
