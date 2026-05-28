from __future__ import annotations

from dataclasses import replace
from hashlib import sha1, sha256
import json
from pathlib import Path
import re
from typing import Any

from PIL import Image

from .hmi_donors import (
    find_prefix_proven_complex_hmi_donor_entry,
    find_proven_complex_hmi_donor,
    find_proven_complex_hmi_donor_entry,
)
from .hmi_cfs import (
    NATIVE_CFS_PRIMARY_TABLE_OFFSET,
    find_native_cfs_record,
    parse_native_cfs_table,
    refresh_native_cfs_crc,
    rewrite_native_cfs_record,
)
from .hmi_inspect import inspect_hmi
from .hmi_pagesafe import inspect_page_safe_status, refresh_page_safe_header
from .layout import resolve_page_layout
from .page_format import (
    find_block_by_objname,
    load_page_file,
    page_hidden_gap_after_table,
    page_parsed_end_offset,
    page_post_block_tail,
    page_raw_block_bounds,
    parse_page_data,
)
from .preview import render_scene_preview
from .scene import SceneModel, save_scene_json, widget_to_dict
from .font_toolchain import replace_hmi_font
from .tft_checksum import inspect_tft_checksum
from .tft_fonts import patch_tft_font
from .tft_images import (
    _parse_picture_resource_records,
    compile_hmi_picture_resource,
    pack_hmi_picture_entries_into_tft,
    pack_picture_resources_into_tft,
)
from .tft_media import pack_gmov_resources_into_tft
from .tft_hmisafe import finalize_tft
from .tft_prehmisafe import compare_pre_hmisafe, decode_known_pre_hmisafe_fields, derive_synthetic_pre_hmisafe_from_final
from .tft_toolchain import inspect_tft
from .tft_patch import (
    DEFAULT_CASE_ROOT,
    MULTI_PAGE_PHYSICAL_ROW_ORDER_CASE31_LAYOUT,
    MULTI_PAGE_PHYSICAL_ROW_ORDER_PAGE0_FIRST,
    TYPE_RECORD_LENGTHS,
    _blocks_match_fixture_replay_shape,
    _event_tokens_match_blocks,
    build_added_object_pre_hmisafe_tft,
    build_multi_page_pre_hmisafe_tft,
    build_rebuild_page_pre_hmisafe_tft,
    patch_added_object_tft,
    patch_multi_page_tft,
    patch_rebuild_page_tft,
    is_page1_fixed_printh_probe_event_line,
    is_page1_printh_probe_event_line,
    is_supported_page1_button_event_line,
    parse_page1_button_click_event_line,
    parse_page1_button_ref_event_line,
    parse_page1_button_tsw_event_line,
    parse_page1_button_vis_event_line,
)
from .widgets import (
    AUTHORING_WIDGET_TEMPLATE_CASES,
    EXPERIMENTAL_DIRECT_TFT_FIXTURE_WIDGET_TYPES,
    HMI_ONLY_FIXTURE_WIDGET_TYPES,
)


class EditorError(RuntimeError):
    """Raised when scene build or page patching fails."""


NON_VISUAL_WIDGET_TYPE_CODES = {"3", "4", "\x04", "\x05", "?"}
STYLE_FIELD_ALIASES = {
    "background_color": "bco",
    "foreground_color": "pco",
    "border_color": "borderc",
    "font_id": "font",
    "enabled": "en",
    "interval_ms": "tim",
    "length": "lenth",
    "digits": "lenth",
}
RESOURCE_FIELD_ALIASES = {
    "normal": "pic",
    "pressed": "pic2",
    "crop": "picc",
}
PAGE1_PLAIN_WIDGET_TYPES = {
    "text",
    "button",
    "number",
    "image",
    "progress",
    "slider",
    "gauge",
    "checkbox",
    "radio",
}
PAGE1_PLAIN_WIDGET_TYPES_LABEL = "text/button/number/image/progress/slider/gauge/checkbox/radio"
MEDIA_WIDGET_TYPE_CODES = {"\x02", "\x03", "\x04"}
SEED_PAGE0_PATCH_WIDGET_TYPES = {"button"}
ADVANCED_FILE_RUNTIME_TYPE_CODES = {"D", ">", "A", "B", "?"}
EVENT_METHOD_CALL_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\((.*?)\)\s*$")
FILE_STREAM_OPEN_TEXT_REF_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\.open\(\s*([A-Za-z_][A-Za-z0-9_]*)\.txt\s*\)\s*$"
)
PRINTH_EVENT_LINE_RE = re.compile(r"^\s*printh\s+(?:[0-9A-Fa-f]{2})(?:\s+[0-9A-Fa-f]{2})*\s*$")
PRE_HMISAFE_MANAGED_SNAPSHOT_FIELDS = (
    "staticstrBeg",
    "AppAllvasAddr",
    "AppAllvasQty",
    "attdataaddr",
    "resourcesfileddr",
    "strdataaddr",
    "pageadd",
    "objxinxiadd",
    "picxinxiadd",
    "gmovxinxiadd",
    "videoxinxiadd",
    "wavxinxiadd",
    "zimoxinxiadd",
    "MainCodeHex",
    "pageqyt",
    "objqyt",
    "picqyt",
    "gmovqyt",
    "videoqyt",
    "wavqyt",
    "zimoqyt",
    "res1",
    "encode",
)
_PRE_HMISAFE_MANAGED_SNAPSHOT_BY_REFERENCE_TFT = {
    str(
        Path(
            r"C:\Users\SinYu\Desktop\case_for_codex\case_72_filestream_official_gui_fs0_open_t1_probe\official_work_output_20260518_fs0_open\output\lcd_test.tft"
        ).resolve()
    ): Path(
        r"D:\reverse\USART HMI_decompile\dynamic_probe\official_compile_state\raw_snapshots\case72_typed_20260523_C2\000_C2_pre_HmiSafe.json"
    ),
    str(
        Path(
            r"C:\Users\SinYu\Desktop\case_for_codex\case_80_datarecord_textselect_official_positive_oracle\official_work_output_after_gui_create_20260518_round2\output\lcd_test.tft"
        ).resolve()
    ): Path(
        r"D:\reverse\USART HMI_decompile\dynamic_probe\official_compile_state\raw_snapshots\case80_typed_20260523_C2\000_C2_pre_HmiSafe.json"
    ),
    str(
        Path(
            r"C:\Users\SinYu\Desktop\case_for_codex\case_80_datarecord_textselect_official_positive_oracle\official_work_output_after_gui_create_20260519\output\lcd_test.tft"
        ).resolve()
    ): Path(
        r"D:\reverse\USART HMI_decompile\dynamic_probe\official_compile_state\raw_snapshots\case80_typed_20260523_C2\000_C2_pre_HmiSafe.json"
    ),
    str(
        Path(
            r"C:\Users\SinYu\Desktop\case_for_codex\case_83_datarecord_textselect_button_official_positive_oracle\official_work_output_after_gui_create_20260518_round2\output\lcd_test.tft"
        ).resolve()
    ): Path(
        r"D:\reverse\USART HMI_decompile\dynamic_probe\official_compile_state\raw_snapshots\case83_typed_20260523_C2\000_C2_pre_HmiSafe.json"
    ),
    str(
        Path(
            r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\reverse_usarthmi\case83_official_gui_event_oracle2_20260520\official_compile\output\source_raw.tft"
        ).resolve()
    ): Path(
        r"D:\reverse\USART HMI_decompile\dynamic_probe\official_compile_state\raw_snapshots\case83event_typed_20260523_C2\000_C2_pre_HmiSafe.json"
    ),
    str(
        Path(
            r"C:\Users\SinYu\Desktop\case_for_codex\case_85_datarecord_sltext_official_positive_oracle\official_work_output_after_gui_create_20260519\output\lcd_test.tft"
        ).resolve()
    ): Path(
        r"D:\reverse\USART HMI_decompile\dynamic_probe\official_compile_state\raw_snapshots\case85_typed_20260523_C2\000_C2_pre_HmiSafe.json"
    ),
    str(
        Path(
            r"C:\Users\SinYu\Desktop\case_for_codex\case_56_advanced_mix_filebrowser_textselect_oracle\official_work_output_after_gui_create_20260518\output\lcd_test.tft"
        ).resolve()
    ): Path(
        r"D:\reverse\USART HMI_decompile\dynamic_probe\official_compile_state\raw_snapshots\case56_typed_20260523_C2\000_C2_pre_HmiSafe.json"
    ),
}
_PRE_HMISAFE_TRUE_PRE_BY_REFERENCE_TFT = {
    str(
        Path(
            r"C:\Users\SinYu\Desktop\case_for_codex\case_72_filestream_official_gui_fs0_open_t1_probe\official_work_output_20260518_fs0_open\output\lcd_test.tft"
        ).resolve()
    ): Path(r"D:\reverse\USART HMI_decompile\dynamic_probe\x32dbg_hmisafe_capture_case72_20260523\pre_hmisafe_x32dbg.tft"),
    str(
        Path(
            r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\reverse_usarthmi\case83_official_gui_event_oracle2_20260520\official_compile\output\source_raw.tft"
        ).resolve()
    ): Path(r"D:\reverse\USART HMI_decompile\dynamic_probe\x32dbg_hmisafe_capture_case83event_20260523\pre_hmisafe_x32dbg.tft"),
    str(
        Path(
            r"C:\Users\SinYu\Desktop\case_for_codex\case_80_datarecord_textselect_official_positive_oracle\official_work_output_after_gui_create_20260519\output\lcd_test.tft"
        ).resolve()
    ): Path(r"D:\reverse\USART HMI_decompile\dynamic_probe\x32dbg_hmisafe_capture_case80_20260523\pre_hmisafe_x32dbg.tft"),
    str(
        Path(
            r"C:\Users\SinYu\Desktop\case_for_codex\case_83_datarecord_textselect_button_official_positive_oracle\official_work_output_after_gui_create_20260518_round2\output\lcd_test.tft"
        ).resolve()
    ): Path(r"D:\reverse\USART HMI_decompile\dynamic_probe\x32dbg_hmisafe_capture_case83_20260523\pre_hmisafe_x32dbg.tft"),
    str(
        Path(
            r"C:\Users\SinYu\Desktop\case_for_codex\case_85_datarecord_sltext_official_positive_oracle\official_work_output_after_gui_create_20260519\output\lcd_test.tft"
        ).resolve()
    ): Path(r"D:\reverse\USART HMI_decompile\dynamic_probe\x32dbg_hmisafe_capture_case85_20260523\pre_hmisafe_x32dbg.tft"),
    str(
        Path(
            r"C:\Users\SinYu\Desktop\case_for_codex\case_56_advanced_mix_filebrowser_textselect_oracle\official_work_output_after_gui_create_20260518\output\lcd_test.tft"
        ).resolve()
    ): Path(r"D:\reverse\USART HMI_decompile\dynamic_probe\x32dbg_hmisafe_capture_case56_20260523\pre_hmisafe_x32dbg.tft"),
}
_OFFICIAL_BUILDER_NEGATIVE_ARTIFACTS_BY_PATCH_PATH = {
    "case85_exact_event_case_seed": Path(
        r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\examples\advanced_direct_tft_demo\datarecord_sliding_text_existing_b0_event_official_compile_negative_2026-05-23.json"
    )
}
_OFFICIAL_COMPLEX_HMI_COMPILE_POSITIVE_ARTIFACT = Path(
    r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\examples\advanced_direct_tft_demo\official_hmi_roundtrip_supported_datarecord_mixes_2026-05-19.json"
)
_OFFICIAL_COMPLEX_HMI_STATUS_BY_TARGET_PAGE_SHA256 = {
    "599445728496c45b194bbbd41d1640b74aa64fc55efe87c63a586163429a03a0": {
        "status": "non_exact_page_official_compile_negative",
        "evidence": Path(
            r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\examples\advanced_direct_tft_demo\current_code_datarecord_hmi_compile_status_2026-05-23.json"
        ),
        "detail_artifact": Path(
            r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\examples\advanced_direct_tft_demo\case80_current_hmi_compile_delta_2026-05-23.json"
        ),
        "reason": "the current worktree's case80 current-code 0.pa survives official acceptance but still compiles to the empty-shell class",
    },
    "233cc51bdf3ee66519801a100e2339a51c6529bcb85804029f3eccc089741737": {
        "status": "non_exact_page_official_compile_negative",
        "evidence": Path(
            r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\examples\advanced_direct_tft_demo\current_code_datarecord_hmi_compile_status_2026-05-23.json"
        ),
        "detail_artifact": Path(
            r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\examples\advanced_direct_tft_demo\case83_current_hmi_compile_delta_2026-05-23.json"
        ),
        "reason": "the current worktree's case83 current-code 0.pa survives official acceptance but still compiles to the empty-shell class",
    },
    "2afbcf88009c70a790c5f502386cf062d16f0b4ef7dfc05de1c95e66102056f5": {
        "status": "non_exact_page_official_compile_negative",
        "evidence": Path(
            r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\examples\advanced_direct_tft_demo\current_code_datarecord_hmi_compile_status_2026-05-23.json"
        ),
        "detail_artifact": Path(
            r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\examples\advanced_direct_tft_demo\case85_current_hmi_compile_delta_2026-05-23.json"
        ),
        "reason": "the current worktree's case85 current-code 0.pa survives official acceptance but still compiles to the empty-shell class",
    },
}
_OFFICIAL_COMPLEX_HMI_STATUS_BY_TARGET_PAGE_SHA_AND_CONTAINER = {
    ("599445728496c45b194bbbd41d1640b74aa64fc55efe87c63a586163429a03a0", "page0-bar1-data0-exact-delete-select0-b1-from-case83"): {
        "status": "prefix_donor_container_compile_positive_nonparity",
        "evidence": Path(
            r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\examples\advanced_direct_tft_demo\current_code_datarecord_hmi_compile_status_2026-05-23.json"
        ),
        "detail_artifact": Path(
            r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\examples\advanced_direct_tft_demo\case80_current_hmi_compile_delta_2026-05-23.json"
        ),
        "reason": "the current worktree's case80 current-code page compiles positively through the bar1+data0 prefix donor container, but still lands in the donor-class positive output rather than the exact case80 official class",
        "compiled_output_size": 11413000,
        "compiled_object_region_length": 9736,
        "compiled_object_region_length_hex": "0x2608",
        "target_exact_parity": False,
    },
    ("086ba2fd6ef2c02631e0fdda6d432a5880ee4460adaf84b0aed6d386913053a7", "case80-exact"): {
        "status": "prefix_donor_container_compile_positive_nonparity",
        "evidence": Path(
            r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\examples\advanced_direct_tft_demo\current_code_datarecord_hmi_compile_status_2026-05-23.json"
        ),
        "detail_artifact": Path(
            r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\examples\advanced_direct_tft_demo\case83_current_hmi_compile_delta_2026-05-23.json"
        ),
        "reason": "the current worktree's case83 current-code page compiles positively through the case80 exact donor container, but still lands in the case80-class positive output rather than the exact case83 official class",
        "compiled_output_size": 11415672,
        "compiled_object_region_length": 12408,
        "compiled_object_region_length_hex": "0x3078",
        "target_exact_parity": False,
    },
    ("2afbcf88009c70a790c5f502386cf062d16f0b4ef7dfc05de1c95e66102056f5", "page0-bar1-data0-exact-delete-select0-b1-from-case83"): {
        "status": "prefix_donor_container_compile_positive_nonparity",
        "evidence": Path(
            r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\examples\advanced_direct_tft_demo\current_code_datarecord_hmi_compile_status_2026-05-23.json"
        ),
        "detail_artifact": Path(
            r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\examples\advanced_direct_tft_demo\case85_current_hmi_compile_delta_2026-05-23.json"
        ),
        "reason": "the current worktree's case85 current-code page compiles positively through the bar1+data0 prefix donor container, but still lands in the donor-class positive output rather than the exact case85 official class",
        "compiled_output_size": 11413000,
        "compiled_object_region_length": 9736,
        "compiled_object_region_length_hex": "0x2608",
        "target_exact_parity": False,
    },
}
_EXACT_DONOR_PAGE_SHA_AND_DONOR_POSITIVE = {
    ("599445728496c45b194bbbd41d1640b74aa64fc55efe87c63a586163429a03a0", "case80-exact"): {
        "status": "exact_donor_container_compile_positive_target_exact",
        "evidence": Path(
            r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\examples\advanced_direct_tft_demo\case80_current_exact_donor_compile_positive_20260524.json"
        ),
        "detail_artifact": Path(
            r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\examples\advanced_direct_tft_demo\case80_current_hmi_compile_delta_2026-05-23.json"
        ),
        "reason": "the current worktree's case80 current-code page compiles positively in the exact case80 donor container and reaches the exact case80 official compile class",
        "compiled_output_size": 11415672,
        "compiled_object_region_length": 12408,
        "compiled_object_region_length_hex": "0x3078",
        "target_exact_parity": True,
    },
    ("086ba2fd6ef2c02631e0fdda6d432a5880ee4460adaf84b0aed6d386913053a7", "case83-exact"): {
        "status": "exact_donor_container_compile_positive_target_exact",
        "evidence": Path(
            r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\examples\advanced_direct_tft_demo\case83_current_exact_donor_compile_positive_20260524.json"
        ),
        "detail_artifact": Path(
            r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\examples\advanced_direct_tft_demo\case83_current_hmi_compile_delta_2026-05-23.json"
        ),
        "reason": "the current worktree's case83 current-code page compiles positively in the exact case83 donor container and reaches the exact case83 official compile class",
        "compiled_output_size": 11417020,
        "compiled_object_region_length": 13756,
        "compiled_object_region_length_hex": "0x35BC",
        "target_exact_parity": True,
    },
}
_PREFIX_DONOR_HMI_ONLY_STATUS_BY_TARGET_PAGE_SHA_AND_DONOR_AND_POSTFIX = {
    (
        "a489e8b19e0f0e17339ad562759011f4d7d7b05d9ed16aa0723b054f7948333b",
        "case85-exact-unproven-hmi-roundtrip",
        ("native_named_page_promote_case85_new_button_noevent",),
    ): {
        "status": "prefix_donor_hmi_compile_positive_donor_parity",
        "evidence": Path(
            r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\examples\advanced_direct_tft_demo\case85_new_button_noevent_hmi_compile_positive_20260524.json"
        ),
        "detail_artifact": Path(
            r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\examples\advanced_direct_tft_demo\case85_new_button_noevent_hmi_compile_delta_20260524.json"
        ),
        "reason": "the public case85 no-event data-record plus sliding-text plus ordinary button HMI path now reaches donor-graft compile parity after slt0 donor-geometry normalization plus native named 0.pa promote",
        "compiled_output_size": 11416356,
        "compiled_object_region_length": 13092,
        "compiled_object_region_length_hex": "0x3324",
        "compiled_tft_sha256": "02cad838dfd8945c7b6cec4acd5fd51024de1be79d4f366e375c9e8ca9b6ac64",
        "target_exact_parity": False,
        "target_donor_parity": True,
    },
    (
        "5243c0b963fe1637555d9f50f11543b5a42d43472a444c0e41608ae465a9c5a6",
        "case85-exact-unproven-hmi-roundtrip",
        ("native_named_page_promote_case85_new_button_event_hmi_only",),
    ): {
        "status": "prefix_donor_hmi_compile_positive_class_only",
        "evidence": Path(
            r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\examples\advanced_direct_tft_demo\case85_new_button_event_hmi_compile_positive_20260524.json"
        ),
        "detail_artifact": Path(
            r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\examples\advanced_direct_tft_demo\datarecord_sliding_text_button_path_blocker_2026-05-20.json"
        ),
        "reason": "the public case85 event-bearing new-button HMI path now compiles positively after native named 0.pa promote, but direct-TFT/event authoring parity is still open",
        "compiled_output_size": 11416372,
        "compiled_object_region_length": 13108,
        "compiled_object_region_length_hex": "0x3334",
        "compiled_tft_sha256": "d2dabb9992d2d9274a09db3f7c3b2cfd8ec8e3e1446992b72b772f775f209aac",
        "target_exact_parity": False,
        "target_donor_parity": False,
    },
}
_CASE85_NEW_BUTTON_NOEVENT_BLOCK_SIGNATURE = (
    ("page0", "y"),
    ("t0", "t"),
    ("b0", "b"),
    ("p0", "p"),
    ("bar1", "j"),
    ("data0", "B"),
    ("slt0", ">"),
    ("b1", "b"),
)
_CASE85_NEW_BUTTON_EVENT_BLOCK_SIGNATURE = (
    ("page0", "y"),
    ("t0", "t"),
    ("b0", "b"),
    ("p0", "p"),
    ("bar1", "j"),
    ("data0", "B"),
    ("slt0", ">"),
    ("eventbtn", "b"),
)
_CASE85_BUTTON_FAMILY_BLOCK_PREFIX = _CASE85_NEW_BUTTON_EVENT_BLOCK_SIGNATURE[:-1]


def import_asset(source: str | Path, out_dir: str | Path) -> dict[str, Any]:
    src = Path(source).resolve()
    out_base = Path(out_dir).resolve()
    out_base.mkdir(parents=True, exist_ok=True)

    image = Image.open(src).convert("RGBA")
    digest = sha1(src.read_bytes()).hexdigest()[:12]
    png_path = out_base / f"{src.stem}_{digest}.png"
    raw_path = out_base / f"{src.stem}_{digest}.rgb565"
    image.save(png_path)
    raw_path.write_bytes(_image_to_rgb565(image))
    return {
        "source": str(src),
        "normalized_png": str(png_path),
        "rgb565": str(raw_path),
        "width": image.width,
        "height": image.height,
        "digest": digest,
        "resource_id": int(digest[:4], 16) & 0xFFFF,
    }


def build_scene(
    scene: SceneModel,
    seed_hmi: str | Path,
    out_dir: str | Path,
    *,
    baseline_tft: str | Path | None = None,
    font_zi: str | Path | None = None,
    font_entry: str = "0.zi",
) -> dict[str, Any]:
    seed_path = Path(seed_hmi).resolve()
    build_dir = Path(out_dir).resolve()
    build_dir.mkdir(parents=True, exist_ok=True)
    asset_dir = build_dir / "assets"
    asset_dir.mkdir(exist_ok=True)

    normalized_pages = []
    for page in scene.pages:
        normalized_widgets = resolve_page_layout(
            page.widgets,
            page.layout,
            int(scene.canvas["width"]),
            int(scene.canvas["height"]),
        )
        normalized_pages.append(replace(page, widgets=normalized_widgets))

    normalized_scene = SceneModel(
        project=scene.project,
        canvas=scene.canvas,
        assets=scene.assets,
        pages=normalized_pages,
    )
    if len(normalized_scene.pages) > 1:
        _validate_multi_page_scene_support(normalized_scene)

    manifest_assets: dict[str, Any] = {}
    for asset_key, asset in scene.assets.items():
        manifest_assets[asset_key] = _import_scene_asset(asset, asset_dir)
    packed_picture_ids = _assign_tft_picture_resource_ids(seed_path, normalized_scene, manifest_assets)
    gmov_sources = _collect_tft_gmov_sources(normalized_scene)
    font_zi_path = Path(font_zi).resolve() if font_zi is not None else None

    output_hmi = build_dir / "output.hmi"
    hmi_picture_resources, official_hmi_container_status = build_hmi(normalized_scene, manifest_assets, seed_path, output_hmi)
    hmi_font_patch = None
    if font_zi_path is not None:
        hmi_font_patch = replace_hmi_font(output_hmi, font_zi_path, output_hmi, entry_name=font_entry)
    preview_png = render_scene_preview(normalized_scene, build_dir / "preview.png", manifest_assets=manifest_assets)
    baseline_pa = build_dir / "seed_0.pa"
    target_pa = build_dir / "target_0.pa"
    _write_hmi_entry(seed_path, "0.pa", baseline_pa)
    target_pages = []
    for index, _page in enumerate(normalized_pages):
        page_path = build_dir / f"target_{index}.pa"
        _write_hmi_entry(output_hmi, f"{index}.pa", page_path)
        target_pages.append(page_path)
    target_page_analysis = _target_page_analysis_metadata(target_pages)
    official_hmi_compile_status = _official_complex_hmi_compile_status_metadata(
        target_pages,
        container_status=official_hmi_container_status,
    )
    fixture_picture_resources: list[dict[str, Any]] = []
    fixture_tft_picture_entries: list[tuple[int, bytes, str]] = []
    fixture_picture_resources, fixture_tft_picture_entries = _seed_fixture_picture_resources(
        normalized_scene,
        target_pages=target_pages,
        output_hmi=output_hmi,
    )
    if fixture_picture_resources:
        hmi_picture_resources.extend(fixture_picture_resources)

    output_tft = None
    output_pre_hmisafe_tft = None
    pre_hmisafe_finalization = None
    pre_hmisafe_alignment = None
    pre_hmisafe_managed_snapshot_alignment = None
    pre_hmisafe_true_pre_alignment = None
    official_builder_pre_status = None
    pre_hmisafe_status = {
        "available": False,
        "reason": "baseline_tft not provided",
    }
    tft_patch = None
    tft_checksum = None
    oracle_alignment = None
    tft_picture_pack = None
    tft_gmov_pack = None
    tft_font_patch = None
    resource_seed_tft = None
    warnings = [
        "Image assets are normalized and assigned resource ids; TFT image resource packing is experimental.",
    ]
    if font_zi_path is not None:
        warnings.append("Scene font .zi replacement is experimental and limited to an existing HMI/TFT font slot.")
    if baseline_tft is not None:
        _validate_tft_build_has_no_hmi_only_widgets(normalized_scene)
        _validate_fixture_replay_widgets_have_no_scene_events(normalized_scene)
        baseline_tft_path = Path(baseline_tft).resolve()
        tft_seed_path = baseline_tft_path
        fixture_tft_picture_entries = _filter_fixture_tft_picture_entries(
            baseline_tft_path,
            fixture_tft_picture_entries,
        )
        if fixture_tft_picture_entries:
            resource_seed_tft_path = build_dir / "resource_seed_fixture.tft"
            pack_result = pack_hmi_picture_entries_into_tft(
                baseline_tft_path,
                fixture_tft_picture_entries,
                out_tft=resource_seed_tft_path,
            )
            tft_seed_path = resource_seed_tft_path
            resource_seed_tft = str(resource_seed_tft_path)
            tft_picture_pack = pack_result.to_dict()
        picture_sources = _merge_picture_sources(
            _collect_tft_picture_sources(manifest_assets, packed_picture_ids),
        )
        if picture_sources:
            resource_seed_tft_path = build_dir / "resource_seed.tft"
            pack_result = pack_picture_resources_into_tft(
                tft_seed_path,
                picture_sources,
                out_tft=resource_seed_tft_path,
            )
            tft_seed_path = resource_seed_tft_path
            resource_seed_tft = str(resource_seed_tft_path)
            tft_picture_pack = pack_result.to_dict()
        if gmov_sources:
            resource_seed_tft_path = build_dir / "resource_seed_gmov.tft"
            pack_result = pack_gmov_resources_into_tft(
                tft_seed_path,
                gmov_sources,
                out_tft=resource_seed_tft_path,
            )
            tft_seed_path = resource_seed_tft_path
            resource_seed_tft = str(resource_seed_tft_path)
            tft_gmov_pack = pack_result.to_dict()
        if font_zi_path is not None:
            font_seed_tft_path = build_dir / "resource_seed_font.tft"
            font_result = patch_tft_font(
                tft_seed_path,
                font_path=font_zi_path,
                out_tft=font_seed_tft_path,
            )
            tft_seed_path = font_seed_tft_path
            resource_seed_tft = str(font_seed_tft_path)
            tft_font_patch = font_result.to_dict()
        output_tft_path = build_dir / "output.tft"
        if len(target_pages) == 1:
            if normalized_scene.project.get("drop_seed_objects") or normalized_scene.project.get("delete_seed_objects"):
                _validate_tft_target_support(
                    baseline_pa,
                    target_pa,
                    packed_picture_ids=packed_picture_ids,
                    clean_rebuild=True,
                )
                pre_hmisafe_tft_path = build_dir / "output.pre_hmisafe.tft"
                build_rebuild_page_pre_hmisafe_tft(
                    tft_seed_path,
                    seed_pa=baseline_pa,
                    target_pa=target_pa,
                    out_tft=pre_hmisafe_tft_path,
                )
                output_pre_hmisafe_tft = str(pre_hmisafe_tft_path)
                pre_hmisafe_status = {
                    "available": True,
                    "reason": "builder-generated clean rebuild pre-HmiSafe candidate",
                }
                patch_result = patch_rebuild_page_tft(
                    tft_seed_path,
                    seed_pa=baseline_pa,
                    target_pa=target_pa,
                    out_tft=output_tft_path,
                )
            else:
                _validate_tft_target_support(baseline_pa, target_pa, packed_picture_ids=packed_picture_ids)
                pre_hmisafe_tft_path = build_dir / "output.pre_hmisafe.tft"
                pre_result = build_added_object_pre_hmisafe_tft(
                    tft_seed_path,
                    baseline_pa=baseline_pa,
                    target_pa=target_pa,
                    out_tft=pre_hmisafe_tft_path,
                )
                if pre_result is not None:
                    output_pre_hmisafe_tft = str(pre_hmisafe_tft_path)
                    pre_hmisafe_status = {
                        "available": True,
                        "reason": "builder-generated added-object pre-HmiSafe candidate",
                    }
                else:
                    pre_hmisafe_status = {
                        "available": False,
                        "reason": "special replay/fixture/exact-tail append path does not emit a builder-generated pre-HmiSafe candidate",
                    }
                patch_result = patch_added_object_tft(
                    tft_seed_path,
                    baseline_pa=baseline_pa,
                    target_pa=target_pa,
                    out_tft=output_tft_path,
                )
        else:
            if packed_picture_ids:
                raise EditorError("Multi-page TFT scene build does not support new image resources yet")
            pre_hmisafe_tft_path = build_dir / "output.pre_hmisafe.tft"
            build_multi_page_pre_hmisafe_tft(
                tft_seed_path,
                baseline_pa=baseline_pa,
                target_pages=target_pages,
                out_tft=pre_hmisafe_tft_path,
                physical_page_row_order=_multi_page_physical_row_order(normalized_scene),
                normalize_trailing_filebrowser_xfloat_order=_multi_page_trailing_filebrowser_xfloat_normalization_enabled(normalized_scene),
                allow_experimental_page1_filebrowser=_experimental_page1_filebrowser_enabled(normalized_scene),
                allow_experimental_events=_experimental_multi_page_events_enabled(normalized_scene),
            )
            output_pre_hmisafe_tft = str(pre_hmisafe_tft_path)
            pre_hmisafe_status = {
                "available": True,
                "reason": "builder-generated multi-page pre-HmiSafe candidate",
            }
            patch_result = patch_multi_page_tft(
                tft_seed_path,
                baseline_pa=baseline_pa,
                target_pages=target_pages,
                out_tft=output_tft_path,
                physical_page_row_order=_multi_page_physical_row_order(normalized_scene),
                normalize_trailing_filebrowser_xfloat_order=_multi_page_trailing_filebrowser_xfloat_normalization_enabled(normalized_scene),
                allow_experimental_page1_filebrowser=_experimental_page1_filebrowser_enabled(normalized_scene),
                allow_experimental_events=_experimental_multi_page_events_enabled(normalized_scene),
            )
        output_tft = str(output_tft_path)
        tft_patch = patch_result.to_dict()
        tft_checksum = inspect_tft_checksum(output_tft_path)
        oracle_alignment = _oracle_alignment_metadata(output_tft_path, patch_result)
        if output_pre_hmisafe_tft is not None:
            pre_path = Path(output_pre_hmisafe_tft)
            rebuilt_from_pre, info = finalize_tft(pre_path.read_bytes())
            pre_hmisafe_finalization = {
                "input_pre_hmisafe_tft": str(pre_path),
                "byte_identical_to_output_tft": rebuilt_from_pre == output_tft_path.read_bytes(),
                "finalizer_info": info.to_dict(),
            }
            pre_hmisafe_alignment = _pre_hmisafe_alignment_metadata(
                pre_path,
                output_tft_path=output_tft_path,
                oracle_alignment=oracle_alignment,
            )
            pre_hmisafe_managed_snapshot_alignment = _pre_hmisafe_managed_snapshot_alignment_metadata(
                pre_path,
                oracle_alignment=oracle_alignment,
            )
            pre_hmisafe_true_pre_alignment = _pre_hmisafe_true_pre_alignment_metadata(
                pre_path,
                oracle_alignment=oracle_alignment,
            )
            official_builder_pre_status = _official_builder_pre_status_metadata(
                tft_patch=tft_patch,
                oracle_alignment=oracle_alignment,
                pre_hmisafe_alignment=pre_hmisafe_alignment,
                pre_hmisafe_managed_snapshot_alignment=pre_hmisafe_managed_snapshot_alignment,
                pre_hmisafe_true_pre_alignment=pre_hmisafe_true_pre_alignment,
            )
    else:
        warnings.append("output_tft is not emitted unless baseline_tft is provided.")

    normalized_path = build_dir / "scene.normalized.json"
    save_scene_json(normalized_scene, normalized_path)
    hardware_quarantine = _hardware_quarantine_metadata(normalized_scene, tft_patch=tft_patch)
    live_smoke = _build_live_smoke_metadata(
        normalized_scene,
        build_dir=build_dir,
        output_tft=Path(output_tft) if output_tft is not None else None,
    )

    manifest = {
        "seed_hmi": str(seed_path),
        "baseline_tft": str(Path(baseline_tft).resolve()) if baseline_tft is not None else None,
        "resource_seed_tft": resource_seed_tft,
        "baseline_pa": str(baseline_pa),
        "target_pa": str(target_pa),
        "target_pages": [str(path) for path in target_pages],
        "target_page_analysis": target_page_analysis,
        "official_hmi_container_status": official_hmi_container_status,
        "output_hmi": str(output_hmi),
        "official_hmi_compile_status": official_hmi_compile_status,
        "output_tft": output_tft,
        "output_pre_hmisafe_tft": output_pre_hmisafe_tft,
        "pre_hmisafe_finalization": pre_hmisafe_finalization,
        "pre_hmisafe_alignment": pre_hmisafe_alignment,
        "pre_hmisafe_managed_snapshot_alignment": pre_hmisafe_managed_snapshot_alignment,
        "pre_hmisafe_true_pre_alignment": pre_hmisafe_true_pre_alignment,
        "official_builder_pre_status": official_builder_pre_status,
        "pre_hmisafe_status": pre_hmisafe_status,
        "tft_picture_pack": tft_picture_pack,
        "tft_gmov_pack": tft_gmov_pack,
        "tft_font_patch": tft_font_patch,
        "hmi_picture_resources": hmi_picture_resources,
        "fixture_picture_resources": fixture_picture_resources,
        "fixture_tft_picture_entries": [
            {"picture_id": int(picture_id), "source": str(source_label)}
            for picture_id, _entry_data, source_label in fixture_tft_picture_entries
        ],
        "hmi_font_patch": hmi_font_patch,
        "preview_png": str(preview_png),
        "tft_patch": tft_patch,
        "tft_checksum": tft_checksum,
        "oracle_alignment": oracle_alignment,
        "assets": manifest_assets,
        "pages": [
            {
                "id": page.id,
                "widgets": [widget_to_dict(widget) for widget in page.widgets],
            }
            for page in normalized_pages
        ],
        "hardware_quarantine": hardware_quarantine,
        "delivery_status": _delivery_status_metadata(output_tft, oracle_alignment, hardware_quarantine),
        "live_smoke": live_smoke,
        "warnings": warnings,
    }
    manifest_path = build_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def _oracle_alignment_metadata(output_tft_path: Path, patch_result: Any) -> dict[str, Any] | None:
    baseline_tft = getattr(patch_result, "baseline_tft", None)
    oracle_tft = getattr(patch_result, "oracle_tft", None) or baseline_tft
    if not oracle_tft:
        return None
    oracle_path = Path(str(oracle_tft))
    if not oracle_path.exists():
        return {
            "baseline_tft": str(Path(str(baseline_tft))) if baseline_tft else None,
            "reference_tft": str(oracle_path),
            "reference_kind": "oracle_tft" if oracle_tft != baseline_tft else "baseline_tft",
            "available": False,
            "byte_identical_to_reference": None,
            "byte_identical_to_baseline": None,
        }
    output_bytes = output_tft_path.read_bytes()
    oracle_bytes = oracle_path.read_bytes()
    baseline_path = Path(str(baseline_tft)) if baseline_tft else None
    baseline_match = None
    baseline_sha = None
    baseline_size = None
    if baseline_path is not None and baseline_path.exists():
        baseline_bytes = baseline_path.read_bytes()
        baseline_match = output_bytes == baseline_bytes
        baseline_sha = sha256(baseline_bytes).hexdigest()
        baseline_size = len(baseline_bytes)
    return {
        "baseline_tft": str(baseline_path) if baseline_path is not None else None,
        "reference_tft": str(oracle_path),
        "reference_kind": "oracle_tft" if oracle_tft != baseline_tft else "baseline_tft",
        "available": True,
        "byte_identical_to_reference": output_bytes == oracle_bytes,
        "byte_identical_to_baseline": baseline_match,
        "output_sha256": sha256(output_bytes).hexdigest(),
        "reference_sha256": sha256(oracle_bytes).hexdigest(),
        "baseline_sha256": baseline_sha,
        "output_size": len(output_bytes),
        "reference_size": len(oracle_bytes),
        "baseline_size": baseline_size,
    }


def _target_page_analysis_metadata(target_pages: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page_path in target_pages:
        if not page_path.exists():
            rows.append({"path": str(page_path), "available": False})
            continue
        page_bytes = page_path.read_bytes()
        page = parse_page_data(page_bytes)
        gap = page_hidden_gap_after_table(page_bytes)
        post_tail = page_post_block_tail(page_bytes)
        first_block_offset, last_block_end_offset = page_raw_block_bounds(page_bytes)
        rows.append(
            {
                "path": str(page_path),
                "available": True,
                "byte_length": len(page_bytes),
                "page_name": page.page_name,
                "block_order": [str(block.objname or "") for block in page.blocks],
                "parsed_end_offset": page_parsed_end_offset(page),
                "raw_block_bounds": {
                    "first_block_offset": first_block_offset,
                    "last_block_end_offset": last_block_end_offset,
                },
                "hidden_gap_length": len(gap),
                "hidden_gap_sha256": sha256(gap).hexdigest() if gap else None,
                "post_block_tail_length": len(post_tail),
                "post_block_tail_sha256": sha256(post_tail).hexdigest() if post_tail else None,
            }
        )
    return rows


def _safe_hmi_page_context(hmi_path: Path) -> tuple[Any, bytes, Any, Any] | None:
    try:
        inspection = inspect_hmi(hmi_path)
        raw = hmi_path.read_bytes()
    except OSError:
        return None
    page_entry = next((entry for entry in inspection.entries if entry.name == "0.pa" and entry.in_file), None)
    if page_entry is None:
        return None
    page = parse_page_data(raw[page_entry.data_offset : page_entry.data_offset + page_entry.length])
    return inspection, raw, page_entry, page


def _apply_known_official_hmi_page_normalizations(page, *, exact_container_donor, official_page) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    if exact_container_donor is None:
        return changes
    if exact_container_donor.donor_id == "case83-exact":
        current_select = find_block_by_objname(page, "select0")
        exact_select = find_block_by_objname(official_page, "select0")
        for field_name in ("x", "y", "endx", "endy"):
            current_field = current_select.get_field(field_name)
            exact_field = exact_select.get_field(field_name)
            if current_field is None or exact_field is None:
                continue
            current_value = int.from_bytes(current_field.value, "little")
            exact_value = int.from_bytes(exact_field.value, "little")
            if current_value == exact_value:
                continue
            current_select.set_int(field_name, exact_value, width=len(current_field.value))
            changes.append(
                {
                    "object": "select0",
                    "field": field_name,
                    "before": current_value,
                    "after": exact_value,
                    "source": "exact_case83_donor_geometry",
                }
            )

        current_b1 = find_block_by_objname(page, "b1")
        exact_b1 = find_block_by_objname(official_page, "b1")
        for field_name in ("x", "y", "endx", "endy"):
            current_field = current_b1.get_field(field_name)
            exact_field = exact_b1.get_field(field_name)
            if current_field is None or exact_field is None:
                continue
            current_value = int.from_bytes(current_field.value, "little")
            exact_value = int.from_bytes(exact_field.value, "little")
            if current_value == exact_value:
                continue
            current_b1.set_int(field_name, exact_value, width=len(current_field.value))
            changes.append(
                {
                    "object": "b1",
                    "field": field_name,
                    "before": current_value,
                    "after": exact_value,
                    "source": "exact_case83_donor_geometry",
                }
            )
        current_val = current_b1.get_field("val")
        exact_val = exact_b1.get_field("val")
        if current_val is not None and exact_val is not None and current_val.marker != exact_val.marker:
            changes.append(
                {
                    "object": "b1",
                    "field": "val.marker",
                    "before": current_val.marker,
                    "after": exact_val.marker,
                    "source": "exact_case83_donor_marker",
                }
            )
            current_val.marker = exact_val.marker
        return changes
    if exact_container_donor.donor_id != "case85-exact-unproven-hmi-roundtrip":
        return changes

    current_block = find_block_by_objname(page, "slt0")
    exact_block = find_block_by_objname(official_page, "slt0")
    for field_name in ("x", "y", "endx", "endy"):
        current_field = current_block.get_field(field_name)
        exact_field = exact_block.get_field(field_name)
        if current_field is None or exact_field is None:
            continue
        current_value = int.from_bytes(current_field.value, "little")
        exact_value = int.from_bytes(exact_field.value, "little")
        if current_value == exact_value:
            continue
        current_block.set_int(field_name, exact_value, width=len(current_field.value))
        changes.append(
            {
                "object": "slt0",
                "field": field_name,
                "before": current_value,
                "after": exact_value,
                "source": "exact_case85_donor_geometry",
            }
        )
    return changes


def _apply_known_prefix_hmi_page_normalizations(page, *, prefix_container_donor, official_page) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    if prefix_container_donor is None:
        return changes
    if prefix_container_donor.donor_id != "case85-exact-unproven-hmi-roundtrip":
        return changes
    if tuple((str(getattr(block, "objname", "") or ""), str(getattr(block, "type_code", "") or "")) for block in page.blocks) != _CASE85_NEW_BUTTON_NOEVENT_BLOCK_SIGNATURE:
        return changes

    current_b1 = find_block_by_objname(page, "b1")
    if current_b1 is None or _block_has_scene_event_lines(current_b1):
        return changes

    current_slt0 = find_block_by_objname(page, "slt0")
    donor_slt0 = find_block_by_objname(official_page, "slt0")
    for field_name in ("x", "y", "endx", "endy"):
        current_field = current_slt0.get_field(field_name)
        donor_field = donor_slt0.get_field(field_name)
        if current_field is None or donor_field is None:
            continue
        current_value = int.from_bytes(current_field.value, "little")
        donor_value = int.from_bytes(donor_field.value, "little")
        if current_value == donor_value:
            continue
        current_slt0.set_int(field_name, donor_value, width=len(current_field.value))
        changes.append(
            {
                "object": "slt0",
                "field": field_name,
                "before": current_value,
                "after": donor_value,
                "source": "case85_new_button_prefix_donor_geometry",
            }
        )
    return changes


def _official_complex_hmi_compile_status_metadata(
    target_pages: list[Path],
    *,
    container_status: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if len(target_pages) != 1:
        return None
    target_page_path = target_pages[0]
    if not target_page_path.exists():
        return None
    target_page = load_page_file(target_page_path)
    target_page_bytes = target_page_path.read_bytes()
    target_page_sha256 = sha256(target_page_bytes).hexdigest()
    prefix_hmi_only_key = None
    if container_status is not None:
        prefix_hmi_only_key = (
            target_page_sha256,
            container_status.get("selected_container_donor_id"),
            tuple(container_status.get("container_postfixes") or []),
        )
        known_prefix_hmi_only = _PREFIX_DONOR_HMI_ONLY_STATUS_BY_TARGET_PAGE_SHA_AND_DONOR_AND_POSTFIX.get(prefix_hmi_only_key)
        if known_prefix_hmi_only is not None:
            return {
                "available": True,
                "target_page": str(target_page_path),
                "donor_hmi": str(container_status.get("selected_container_hmi")),
                "target_page_byte_identical_to_donor": False,
                "target_page_size": len(target_page_bytes),
                "donor_page_size": None,
                "target_page_sha256": target_page_sha256,
                "container_status": container_status,
                "status": known_prefix_hmi_only["status"],
                "evidence": str(known_prefix_hmi_only["evidence"]),
                "detail_artifact": str(known_prefix_hmi_only["detail_artifact"]),
                "reason": known_prefix_hmi_only["reason"],
                "compiled_output_size": known_prefix_hmi_only["compiled_output_size"],
                "compiled_object_region_length": known_prefix_hmi_only["compiled_object_region_length"],
                "compiled_object_region_length_hex": known_prefix_hmi_only["compiled_object_region_length_hex"],
                "compiled_tft_sha256": known_prefix_hmi_only["compiled_tft_sha256"],
                "target_exact_parity": known_prefix_hmi_only["target_exact_parity"],
                "target_donor_parity": known_prefix_hmi_only["target_donor_parity"],
            }
    donor_hmi = _official_complex_hmi_container_seed(target_page.blocks)
    donor_entry = find_proven_complex_hmi_donor_entry(target_page.blocks)
    if donor_hmi is None or not donor_hmi.exists():
        return None

    donor_hmi = donor_hmi.resolve()
    donor_inspection = inspect_hmi(donor_hmi)
    donor_page_entry = next((entry for entry in donor_inspection.entries if entry.name == "0.pa"), None)
    if donor_page_entry is None or not donor_page_entry.in_file:
        return None
    donor_bytes = donor_hmi.read_bytes()
    donor_page_bytes = donor_bytes[donor_page_entry.data_offset : donor_page_entry.data_offset + donor_page_entry.length]
    byte_identical = target_page_bytes == donor_page_bytes
    status = {
        "available": True,
        "target_page": str(target_page_path),
        "donor_hmi": str(donor_hmi),
        "target_page_byte_identical_to_donor": byte_identical,
        "target_page_size": len(target_page_bytes),
        "donor_page_size": len(donor_page_bytes),
        "target_page_sha256": target_page_sha256,
        "container_status": container_status,
    }
    if container_status is not None:
        exact_positive_key = (status["target_page_sha256"], container_status.get("selected_container_donor_id"))
        known_exact_positive = _EXACT_DONOR_PAGE_SHA_AND_DONOR_POSITIVE.get(exact_positive_key)
        if known_exact_positive is not None and container_status.get("selected_strategy") == "exact_donor_rebuild":
            status.update(
                {
                    "status": known_exact_positive["status"],
                    "evidence": str(known_exact_positive["evidence"]),
                    "detail_artifact": str(known_exact_positive["detail_artifact"]),
                    "reason": known_exact_positive["reason"],
                    "compiled_output_size": known_exact_positive["compiled_output_size"],
                    "compiled_object_region_length": known_exact_positive["compiled_object_region_length"],
                    "compiled_object_region_length_hex": known_exact_positive["compiled_object_region_length_hex"],
                    "target_exact_parity": known_exact_positive["target_exact_parity"],
                }
            )
            return status
        positive_key = (status["target_page_sha256"], container_status.get("selected_container_donor_id"))
        known_positive = _OFFICIAL_COMPLEX_HMI_STATUS_BY_TARGET_PAGE_SHA_AND_CONTAINER.get(positive_key)
        if known_positive is not None and container_status.get("selected_strategy") == "prefix_donor_rebuild":
            status.update(
                {
                    "status": known_positive["status"],
                    "evidence": str(known_positive["evidence"]),
                    "detail_artifact": str(known_positive["detail_artifact"]),
                    "reason": known_positive["reason"],
                    "compiled_output_size": known_positive["compiled_output_size"],
                    "compiled_object_region_length": known_positive["compiled_object_region_length"],
                    "compiled_object_region_length_hex": known_positive["compiled_object_region_length_hex"],
                    "target_exact_parity": known_positive["target_exact_parity"],
                }
            )
            return status
    if byte_identical:
        status.update(
            {
                "status": "exact_donor_page_compile_proven",
                "evidence": str(Path(donor_entry.evidence).resolve()) if donor_entry is not None else str(_OFFICIAL_COMPLEX_HMI_COMPILE_POSITIVE_ARTIFACT),
                "donor_id": donor_entry.donor_id if donor_entry is not None else None,
                "reason": "target 0.pa is byte-identical to the proven official donor page",
            }
        )
        return status

    known_status = _OFFICIAL_COMPLEX_HMI_STATUS_BY_TARGET_PAGE_SHA256.get(status["target_page_sha256"])
    if known_status is not None:
        status.update(
            {
                "status": known_status["status"],
                "evidence": str(known_status["evidence"]),
                "detail_artifact": str(known_status["detail_artifact"]) if known_status.get("detail_artifact") else None,
                "reason": known_status["reason"],
            }
        )
        return status

    status.update(
        {
            "status": "non_exact_donor_page_compile_unverified",
            "evidence": str(_OFFICIAL_COMPLEX_HMI_COMPILE_POSITIVE_ARTIFACT),
            "reason": "donor signature is compile-proven only for the exact donor page bytes",
        }
    )
    return status


def _pre_hmisafe_alignment_metadata(
    pre_tft_path: Path,
    *,
    output_tft_path: Path,
    oracle_alignment: dict[str, Any] | None,
) -> dict[str, Any]:
    if oracle_alignment is None or not oracle_alignment.get("available"):
        return {
            "available": False,
            "reason": "reference final tft is not available",
        }
    if not oracle_alignment.get("byte_identical_to_reference"):
        return {
            "available": False,
            "reason": "output final tft is not byte-identical to the external reference final",
            "reference_tft": oracle_alignment.get("reference_tft"),
            "reference_kind": oracle_alignment.get("reference_kind"),
        }

    reference_tft = oracle_alignment.get("reference_tft")
    if not reference_tft:
        return {
            "available": False,
            "reason": "reference final tft path is missing",
        }
    reference_path = Path(str(reference_tft))
    if not reference_path.exists():
        return {
            "available": False,
            "reason": "reference final tft path does not exist",
            "reference_tft": str(reference_path),
            "reference_kind": oracle_alignment.get("reference_kind"),
        }

    pre_bytes = pre_tft_path.read_bytes()
    reference_final = reference_path.read_bytes()
    synthetic_pre = derive_synthetic_pre_hmisafe_from_final(reference_final)
    compare = compare_pre_hmisafe(pre_bytes, synthetic_pre, max_first_diffs=32)
    return {
        "available": True,
        "reference_kind": "synthetic_from_reference_final",
        "reference_tft": str(reference_path),
        "input_pre_hmisafe_tft": str(pre_tft_path),
        "byte_identical_to_reference": compare["byte_identical"],
        "diff_count": compare["diff_count"],
        "sections": compare["sections"],
        "known_field_diffs": compare["known_field_diffs"],
        "first_diff_ranges": compare["first_diff_ranges"],
        "reference_final_sha256": sha256(reference_final).hexdigest(),
        "reference_final_size": len(reference_final),
        "output_final_tft": str(output_tft_path),
    }


def _pre_hmisafe_managed_snapshot_alignment_metadata(
    pre_tft_path: Path,
    *,
    oracle_alignment: dict[str, Any] | None,
) -> dict[str, Any]:
    if oracle_alignment is None or not oracle_alignment.get("available"):
        return {
            "available": False,
            "reason": "reference final tft is not available",
        }
    if not oracle_alignment.get("byte_identical_to_reference"):
        return {
            "available": False,
            "reason": "output final tft is not byte-identical to the external reference final",
            "reference_tft": oracle_alignment.get("reference_tft"),
            "reference_kind": oracle_alignment.get("reference_kind"),
        }

    reference_tft = oracle_alignment.get("reference_tft")
    if not reference_tft:
        return {
            "available": False,
            "reason": "reference final tft path is missing",
        }
    reference_path = Path(str(reference_tft)).resolve()
    snapshot_path = _PRE_HMISAFE_MANAGED_SNAPSHOT_BY_REFERENCE_TFT.get(str(reference_path))
    if snapshot_path is None:
        return {
            "available": False,
            "reason": "no official managed C2 snapshot is mapped for this reference final tft",
            "reference_tft": str(reference_path),
        }
    if not snapshot_path.exists():
        return {
            "available": False,
            "reason": "official managed C2 snapshot path does not exist",
            "reference_tft": str(reference_path),
            "snapshot_path": str(snapshot_path),
        }

    builder_fields = decode_known_pre_hmisafe_fields(pre_tft_path.read_bytes())
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8-sig"))
    snapshot_appinf1 = snapshot.get("appinf1") or {}
    mismatches = []
    for field_name in PRE_HMISAFE_MANAGED_SNAPSHOT_FIELDS:
        builder_value = builder_fields[field_name]
        snapshot_value = snapshot_appinf1.get(field_name)
        if builder_value == snapshot_value:
            continue
        mismatches.append(
            {
                "field": field_name,
                "builder": builder_value,
                "snapshot": snapshot_value,
            }
        )

    return {
        "available": True,
        "reference_tft": str(reference_path),
        "snapshot_path": str(snapshot_path),
        "snapshot_stage": snapshot.get("stage"),
        "field_count": len(PRE_HMISAFE_MANAGED_SNAPSHOT_FIELDS),
        "field_match": not mismatches,
        "mismatches": mismatches,
        "snapshot_counts": snapshot.get("counts"),
    }


def _pre_hmisafe_true_pre_alignment_metadata(
    pre_tft_path: Path,
    *,
    oracle_alignment: dict[str, Any] | None,
) -> dict[str, Any]:
    if oracle_alignment is None or not oracle_alignment.get("available"):
        return {
            "available": False,
            "reason": "reference final tft is not available",
        }
    if not oracle_alignment.get("byte_identical_to_reference"):
        return {
            "available": False,
            "reason": "output final tft is not byte-identical to the external reference final",
            "reference_tft": oracle_alignment.get("reference_tft"),
            "reference_kind": oracle_alignment.get("reference_kind"),
        }

    reference_tft = oracle_alignment.get("reference_tft")
    if not reference_tft:
        return {
            "available": False,
            "reason": "reference final tft path is missing",
        }
    reference_path = Path(str(reference_tft)).resolve()
    true_pre_path = _PRE_HMISAFE_TRUE_PRE_BY_REFERENCE_TFT.get(str(reference_path))
    if true_pre_path is None:
        return {
            "available": False,
            "reason": "no true pre-HmiSafe capture is mapped for this reference final tft",
            "reference_tft": str(reference_path),
        }
    if not true_pre_path.exists():
        return {
            "available": False,
            "reason": "mapped true pre-HmiSafe capture path does not exist",
            "reference_tft": str(reference_path),
            "true_pre_tft": str(true_pre_path),
        }

    compare = compare_pre_hmisafe(pre_tft_path.read_bytes(), true_pre_path.read_bytes(), max_first_diffs=32)
    return {
        "available": True,
        "reference_tft": str(reference_path),
        "true_pre_tft": str(true_pre_path),
        "byte_identical_to_reference": compare["byte_identical"],
        "diff_count": compare["diff_count"],
        "sections": compare["sections"],
        "known_field_diffs": compare["known_field_diffs"],
        "first_diff_ranges": compare["first_diff_ranges"],
    }


def _official_builder_pre_status_metadata(
    *,
    tft_patch: dict[str, Any] | None,
    oracle_alignment: dict[str, Any] | None,
    pre_hmisafe_alignment: dict[str, Any] | None,
    pre_hmisafe_managed_snapshot_alignment: dict[str, Any] | None,
    pre_hmisafe_true_pre_alignment: dict[str, Any] | None,
) -> dict[str, Any]:
    patch_path = None if tft_patch is None else tft_patch.get("patch_path", "")
    if pre_hmisafe_true_pre_alignment and pre_hmisafe_true_pre_alignment.get("available"):
        return {
            "status": "true_pre_exact",
            "reason": "builder pre-HmiSafe file is byte-identical to a captured official true pre-HmiSafe sample",
            "artifact": pre_hmisafe_true_pre_alignment.get("true_pre_tft"),
        }
    if (
        pre_hmisafe_managed_snapshot_alignment
        and pre_hmisafe_managed_snapshot_alignment.get("available")
        and pre_hmisafe_managed_snapshot_alignment.get("field_match")
        and pre_hmisafe_alignment
        and pre_hmisafe_alignment.get("available")
        and pre_hmisafe_alignment.get("byte_identical_to_reference")
    ):
        return {
            "status": "managed_snapshot_exact",
            "reason": "builder pre-HmiSafe appinf1 fields match the official C2_pre_HmiSafe managed snapshot and the file also matches the synthetic pre derived from the official final",
            "artifact": pre_hmisafe_managed_snapshot_alignment.get("snapshot_path"),
        }
    if pre_hmisafe_alignment and pre_hmisafe_alignment.get("available") and pre_hmisafe_alignment.get(
        "byte_identical_to_reference"
    ):
        return {
            "status": "synthetic_reference_exact",
            "reason": "builder pre-HmiSafe file matches the synthetic pre derived from the official final, but no stronger official managed/native pre artifact is mapped",
            "artifact": pre_hmisafe_alignment.get("reference_tft"),
        }
    negative_artifact = _OFFICIAL_BUILDER_NEGATIVE_ARTIFACTS_BY_PATCH_PATH.get(str(patch_path or ""))
    if negative_artifact is not None and negative_artifact.exists():
        return {
            "status": "official_builder_negative",
            "reason": "official builder evidence is negative for this lane; the public build diverges from the official pre-HmiSafe path",
            "artifact": str(negative_artifact),
        }
    if oracle_alignment and oracle_alignment.get("available") and not oracle_alignment.get("byte_identical_to_reference"):
        return {
            "status": "oracle_mismatch",
            "reason": "output final tft is not byte-identical to the external reference final",
            "artifact": oracle_alignment.get("reference_tft"),
        }
    return {
        "status": "unresolved",
        "reason": "no official pre-HmiSafe evidence summary is available for this lane yet",
        "artifact": None,
    }


def _hardware_quarantine_metadata(scene: SceneModel, *, tft_patch: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if any(widget.type == "touch-capture" for page in scene.pages for widget in page.widgets):
        return {
            "active": True,
            "reason": (
                "touch-capture live probes are quarantined after the 2026-05-17 runtime wedge; "
                "do not upload without explicit recovery planning"
            ),
            "kind": "touch_capture_runtime_wedge",
        }
    if _experimental_page1_filebrowser_enabled(scene):
        return {
            "active": True,
            "reason": (
                "page1 file-browser is an offline-built runtime probe path; do not upload it as a general "
                "supported scene until the prepared single live probe passes after panel recovery"
            ),
            "kind": "page1_filebrowser_runtime_probe",
        }
    return None


def _delivery_status_metadata(
    output_tft: str | None,
    oracle_alignment: dict[str, Any] | None,
    hardware_quarantine: dict[str, Any] | None,
) -> dict[str, Any]:
    has_tft = bool(output_tft)
    oracle_aligned = bool(oracle_alignment and oracle_alignment.get("byte_identical_to_reference"))
    quarantined = bool(hardware_quarantine and hardware_quarantine.get("active"))
    if not has_tft:
        return {
            "pc_build_status": "no_tft",
            "hardware_status": "not_applicable",
            "ready_for_live_upload": False,
            "reason": "output_tft was not emitted for this build",
        }
    if oracle_aligned and quarantined:
        return {
            "pc_build_status": "oracle_aligned",
            "hardware_status": "quarantined",
            "ready_for_live_upload": False,
            "reason": str(hardware_quarantine.get("reason") or ""),
        }
    if oracle_aligned:
        return {
            "pc_build_status": "oracle_aligned",
            "hardware_status": "not_quarantined",
            "ready_for_live_upload": True,
            "reason": "output_tft is byte-identical to its declared oracle/baseline reference",
        }
    if quarantined:
        return {
            "pc_build_status": "tft_built",
            "hardware_status": "quarantined",
            "ready_for_live_upload": False,
            "reason": str(hardware_quarantine.get("reason") or ""),
        }
    return {
        "pc_build_status": "tft_built",
        "hardware_status": "not_quarantined",
        "ready_for_live_upload": True,
        "reason": "output_tft exists but is not byte-identical to a declared oracle/baseline reference",
    }


def _build_live_smoke_metadata(
    scene: SceneModel,
    *,
    build_dir: Path,
    output_tft: Path | None,
) -> dict[str, Any] | None:
    if output_tft is None:
        return None
    payload = _build_live_smoke_expectation_payload(scene)
    if payload is None:
        return None
    smoke_expect_path = build_dir / "smoke.expect.json"
    smoke_expect_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    scene_path = build_dir / "scene.normalized.json"
    base_command = (
        f'python -m usarthmi --json scene smoke "{scene_path}" '
        f'--out "{build_dir}" --skip-build'
    )
    return {
        "smoke_expect_json": str(smoke_expect_path),
        "source": payload.get("source"),
        "page_id": payload["page_id"],
        "select_page": payload["select_page"],
        "expectation_count": len(payload.get("expectations", [])),
        "set_expectation_count": len(payload.get("set_expectations", [])),
        "step_count": len(payload.get("steps", [])),
        "generation_warnings": list(payload.get("generation_warnings", [])),
        "recommended_command": base_command,
        "recommended_preflight_command": f"{base_command} --preflight",
        "recommended_live_command": f"{base_command} --smoke --upload",
    }


def _build_live_smoke_expectation_payload(scene: SceneModel) -> dict[str, Any] | None:
    page_index, page = _default_scene_page(scene)
    explicit = _explicit_live_smoke_config(scene)
    auto_expectations_enabled = bool(explicit.get("auto_expectations", explicit.get("auto", True)))
    auto_steps_enabled = bool(explicit.get("auto_steps", explicit.get("auto", True)))
    expectations: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    set_expectations: list[dict[str, Any]] = []
    warnings: list[str] = []
    if auto_expectations_enabled or auto_steps_enabled:
        for widget in page.widgets:
            if auto_expectations_enabled:
                expectations.extend(_live_smoke_expectations_for_widget(widget))
            if auto_steps_enabled:
                widget_steps, widget_warnings = _live_smoke_steps_for_widget(widget)
                steps.extend(widget_steps)
                warnings.extend(widget_warnings)
    expectations = _merge_expectation_entries(expectations, explicit.get("expectations"))
    set_expectations = _merge_expectation_entries([], explicit.get("set_expectations"))
    steps.extend(_normalize_live_smoke_steps(explicit.get("steps")))
    warnings.extend(_normalize_string_list(explicit.get("generation_warnings")))
    if not expectations and not set_expectations and not steps:
        return None
    page_id = int(explicit.get("page_id", page_index))
    select_page = explicit.get("select_page", page_id)
    payload: dict[str, Any] = {
        "generated_from_scene": True,
        "source": {
            "auto_expectations": auto_expectations_enabled,
            "auto_steps": auto_steps_enabled,
            "explicit_live_smoke": bool(explicit),
        },
        "page_id": page_id,
        "select_page": select_page,
        "expectations": expectations,
        "not_claimed": [
            "auto-generated smoke expectations cover only stable scene-derived readbacks and simple click-dispatched printh markers",
            "event side effects, file-system/media behavior, physical touch, lifecycle dispatch, and camera-visible layout are not proven by this file alone",
        ],
    }
    restore_page = explicit.get("restore_page")
    if restore_page is not None:
        payload["restore_page"] = restore_page
    if set_expectations:
        payload["set_expectations"] = set_expectations
    if steps:
        payload["steps"] = steps
    if warnings:
        payload["generation_warnings"] = warnings
    return payload


def _default_scene_page(scene: SceneModel) -> tuple[int, Any]:
    default_page_id = str(scene.project.get("default_page") or scene.pages[0].id)
    for index, page in enumerate(scene.pages):
        if page.id == default_page_id:
            return index, page
    return 0, scene.pages[0]


def _live_smoke_expectations_for_widget(widget) -> list[dict[str, Any]]:
    expectations: list[dict[str, Any]] = []
    text_widget_types = {"button", "text", "scrolling-text", "sliding-text", "qrcode"}
    value_widget_types = {
        "number",
        "progress",
        "slider",
        "gauge",
        "checkbox",
        "radio",
        "dual-button",
        "state-button",
        "combobox",
        "xfloat",
        "variable",
    }
    if widget.type in text_widget_types and widget.text is not None:
        expectations.append(_live_smoke_expectation(f"{widget.id}.txt", widget.text, "string"))
    if widget.type in value_widget_types and widget.value is not None:
        expectations.append(_live_smoke_expectation(f"{widget.id}.val", widget.value, "number"))
    if widget.type == "external-picture":
        path = widget.resources.get("path")
        if isinstance(path, str) and path:
            expectations.append(_live_smoke_expectation(f"{widget.id}.path", path, "string"))
    if widget.type == "data-record":
        maxval = widget.style.get("maxval")
        if isinstance(maxval, int):
            expectations.append(_live_smoke_expectation(f"{widget.id}.maxval", maxval, "number"))
        path = widget.resources.get("path")
        if isinstance(path, str) and path:
            expectations.append(_live_smoke_expectation(f"{widget.id}.path", path, "string"))
    if widget.type == "text-select" and widget.value is not None:
        expectations.append(_live_smoke_expectation(f"{widget.id}.val", widget.value, "number"))
    if widget.type == "file-browser":
        directory = widget.resources.get("dir")
        file_filter = widget.resources.get("filter")
        if isinstance(directory, str) and directory:
            expectations.append(_live_smoke_expectation(f"{widget.id}.dir", directory, "string"))
        if isinstance(file_filter, str) and file_filter:
            expectations.append(_live_smoke_expectation(f"{widget.id}.filter", file_filter, "string"))
    if widget.type == "file-stream":
        enabled = widget.style.get("en")
        if enabled is not None:
            expectations.append(_live_smoke_expectation(f"{widget.id}.en", int(bool(enabled)), "number"))
        if widget.value is not None:
            expectations.append(_live_smoke_expectation(f"{widget.id}.val", widget.value, "number"))
    if widget.type in {"animation", "audio", "video"}:
        enabled = widget.style.get("en")
        if enabled is not None:
            expectations.append(_live_smoke_expectation(f"{widget.id}.en", int(bool(enabled)), "number"))
    return expectations


def _live_smoke_expectation(target: str, expected: Any, expected_kind: str) -> dict[str, Any]:
    return {
        "target": target,
        "expected": expected,
        "expected_kind": expected_kind,
        "attempts": 3,
    }


def _live_smoke_steps_for_widget(widget) -> tuple[list[dict[str, Any]], list[str]]:
    steps: list[dict[str, Any]] = []
    warnings: list[str] = []
    click_events = {"down": 1, "up": 0}
    for slot, click_value in click_events.items():
        lines = list(widget.events.get(slot) or [])
        if not lines:
            continue
        printh_hex = _event_printh_hex(lines)
        if printh_hex is None:
            warnings.append(
                f"{widget.id}.{slot} contains event logic without a direct printh marker; post-click assertions still need manual smoke design"
            )
            continue
        steps.append(
            {
                "label": f"{widget.id}.{slot}.printh",
                "command": f"click {widget.id},{click_value}",
                "expected_kind": "unknown",
                "expected_hex": printh_hex,
                "attempts": 3,
            }
        )
        if any(not PRINTH_EVENT_LINE_RE.match(str(line).strip()) for line in lines):
            warnings.append(
                f"{widget.id}.{slot} mixes printh with additional event logic; generated smoke verifies only the emitted marker bytes"
            )
    return steps, warnings


def _event_printh_hex(lines: list[str]) -> str | None:
    chunks: list[str] = []
    for raw_line in lines:
        line = str(raw_line).strip()
        match = PRINTH_EVENT_LINE_RE.match(line)
        if not match:
            continue
        _, _, hex_text = line.partition(" ")
        normalized = " ".join(part for part in hex_text.split() if part)
        if normalized:
            chunks.append(normalized.upper())
    if not chunks:
        return None
    return " ".join(chunks)


def _explicit_live_smoke_config(scene: SceneModel) -> dict[str, Any]:
    payload = scene.project.get("live_smoke")
    if not isinstance(payload, dict):
        return {}
    return payload


def _merge_expectation_entries(
    auto_entries: list[dict[str, Any]],
    explicit_entries: Any,
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for entry in auto_entries:
        target = str(entry.get("target") or "")
        if not target:
            continue
        if target not in merged:
            order.append(target)
        merged[target] = dict(entry)
    for entry in _normalize_expectation_entries(explicit_entries):
        target = str(entry.get("target") or "")
        if not target:
            continue
        if target not in merged:
            order.append(target)
        merged[target] = entry
    return [merged[target] for target in order]


def _normalize_expectation_entries(entries: Any) -> list[dict[str, Any]]:
    if entries is None:
        return []
    if isinstance(entries, dict):
        result = []
        for target, expected in entries.items():
            result.append(_live_smoke_expectation(str(target), expected, _guess_expected_kind(expected)))
        return result
    if not isinstance(entries, list):
        return []
    result: list[dict[str, Any]] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        target = item.get("target") or item.get("name")
        if not target:
            continue
        normalized = dict(item)
        normalized["target"] = str(target)
        normalized.setdefault("attempts", 3)
        if "expected_kind" not in normalized and "expected" in normalized:
            normalized["expected_kind"] = _guess_expected_kind(normalized.get("expected"))
        result.append(normalized)
    return result


def _normalize_live_smoke_steps(entries: Any) -> list[dict[str, Any]]:
    if not isinstance(entries, list):
        return []
    result: list[dict[str, Any]] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        command = item.get("command")
        if not isinstance(command, str) or not command.strip():
            continue
        normalized = dict(item)
        normalized["command"] = command
        normalized.setdefault("attempts", 3)
        result.append(normalized)
    return result


def _normalize_string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item) for item in values if str(item).strip()]


def _guess_expected_kind(value: Any) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "number"
    return "string"


def build_hmi(
    scene: SceneModel,
    manifest_assets: dict[str, Any],
    seed_hmi: Path,
    output_hmi: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    inspection = inspect_hmi(seed_hmi)
    seed_bytes = seed_hmi.read_bytes()
    seed_entries = inspection.entries
    page_entry = next(entry for entry in seed_entries if entry.name == "0.pa")
    page_data = seed_bytes[page_entry.data_offset : page_entry.data_offset + page_entry.length]
    page = parse_page_data(page_data)

    seed_page_block = next(block.clone() for block in page.blocks if block.type_code == "y")
    unknown_blocks = [block.clone() for block in page.blocks if block.type_code not in {"y"}]
    if scene.project.get("drop_seed_objects"):
        unknown_blocks = []
    elif scene.project.get("delete_seed_objects"):
        delete_names = {str(name) for name in scene.project.get("delete_seed_objects") or []}
        unknown_blocks = [block for block in unknown_blocks if block.objname not in delete_names]
        for next_id, block in enumerate(unknown_blocks, start=1):
            block.set_int("id", next_id, width=1)
    elif scene.project.get("clean_seed_objects"):
        _minimize_seed_objects_in_bounds(
            unknown_blocks,
            width=int(scene.canvas["width"]),
            height=int(scene.canvas["height"]),
        )

    template_page_button = load_page_file(r"C:\Program Files (x86)\USART HMI\keyboardch\800480\1.page")
    button_proto = _first_block_of_type(page.blocks, "b") or find_block_by_objname(template_page_button, "b0").clone()
    number_proto = _first_block_of_type(page.blocks, "6")
    if number_proto is None:
        number_proto = _load_case_last_block("case_16_number_basic")
    timer_proto = _first_block_of_type(page.blocks, "3")
    if timer_proto is None:
        timer_proto = _load_case_last_block("case_19_timer")
    text_proto = _first_block_of_type(page.blocks, "t")
    if text_proto is None:
        template_page_text = load_page_file(r"C:\Program Files (x86)\USART HMI\keyboardch\800480\2.page")
        text_proto = find_block_by_objname(template_page_text, "t0").clone()
    picture_proto = _first_block_of_type(page.blocks, "p")
    advanced_protos = _load_fixture_widget_templates(
        widget.type
        for scene_page in scene.pages
        for widget in scene_page.widgets
    )

    # Update page styling from scene canvas.
    if "background_color" in scene.canvas:
        seed_page_block.set_int("bco", int(scene.canvas["background_color"]), width=2)

    page0 = next(page for page in scene.pages if page.id == "page0")
    container_status: dict[str, Any] = {
        "exact_donor_id": None,
        "exact_donor_hmi": None,
        "prefix_donor_id": None,
        "prefix_donor_hmi": None,
        "selected_strategy": "seed_rebuild",
        "selected_container_donor_id": None,
        "selected_container_hmi": None,
        "page_normalizations": [],
    }
    _apply_event_fields(seed_page_block, page0.events, owner="page0")

    if scene.project.get("drop_seed_objects"):
        next_id = 1
    elif scene.project.get("delete_seed_objects"):
        next_id = max((_block_int(block, "id") or 0) for block in [seed_page_block, *unknown_blocks]) + 1
    else:
        next_id = max((_block_int(block, "id") or 0) for block in page.blocks) + 1
    generated_blocks = []
    if _patch_seed_page0_widgets_enabled(scene):
        patchable_names = {block.objname for block in unknown_blocks if block.objname}
        patch_widgets = [widget for widget in page0.widgets if widget.id in patchable_names]
        generate_widgets = [widget for widget in page0.widgets if widget.id not in patchable_names]
        _apply_seed_page0_widget_patches(unknown_blocks, patch_widgets, manifest_assets=manifest_assets)
    else:
        generate_widgets = list(page0.widgets)
    for widget in generate_widgets:
        block = _build_widget_block(
            widget,
            next_id,
            button_proto=button_proto,
            picture_proto=picture_proto,
            number_proto=number_proto,
            timer_proto=timer_proto,
            text_proto=text_proto,
            advanced_protos=advanced_protos,
            manifest_assets=manifest_assets,
        )
        if block is None:
            raise EditorError(f"Scene widget type {widget.type!r} cannot be emitted by the HMI builder yet")
        generated_blocks.append(block)
        next_id += 1

    page.blocks = [seed_page_block] + unknown_blocks + generated_blocks
    exact_container_donor = find_proven_complex_hmi_donor_entry(page.blocks)
    prefix_container_donor = find_prefix_proven_complex_hmi_donor_entry(page.blocks)
    if exact_container_donor is not None:
        container_status["exact_donor_id"] = exact_container_donor.donor_id
        container_status["exact_donor_hmi"] = str(exact_container_donor.hmi_path)
    if prefix_container_donor is not None:
        container_status["prefix_donor_id"] = prefix_container_donor.donor_id
        container_status["prefix_donor_hmi"] = str(prefix_container_donor.hmi_path)
    exact_container_ctx = (
        _safe_hmi_page_context(exact_container_donor.hmi_path)
        if exact_container_donor is not None
        else None
    )
    if exact_container_ctx is None and exact_container_donor is not None:
        container_status["exact_donor_unavailable"] = True
    prefix_container_ctx = (
        _safe_hmi_page_context(prefix_container_donor.hmi_path)
        if prefix_container_donor is not None
        else None
    )
    if prefix_container_ctx is None and prefix_container_donor is not None:
        container_status["prefix_donor_unavailable"] = True
    official_container_hmi = exact_container_donor.hmi_path if exact_container_ctx is not None and exact_container_donor is not None else None
    if exact_container_ctx is not None:
        official_inspection, official_bytes, official_page_entry, official_page = exact_container_ctx
        page.header_bytes = official_page.header_bytes
        container_status["page_normalizations"] = _apply_known_official_hmi_page_normalizations(
            page,
            exact_container_donor=exact_container_donor,
            official_page=official_page,
        )
    elif prefix_container_ctx is not None and prefix_container_donor is not None:
        _prefix_inspection, _prefix_bytes, _prefix_page_entry, prefix_page = prefix_container_ctx
        container_status["page_normalizations"] = _apply_known_prefix_hmi_page_normalizations(
            page,
            prefix_container_donor=prefix_container_donor,
            official_page=prefix_page,
        )
    rebuilt_page = page.serialize()
    rebuilt_page_sha = sha256(rebuilt_page).hexdigest()
    page_entries = _build_extra_page_entries(
        page,
        scene.pages[1:],
        button_proto=button_proto,
        picture_proto=picture_proto,
        number_proto=number_proto,
        text_proto=text_proto,
        advanced_protos=advanced_protos,
        manifest_assets=manifest_assets,
    )
    picture_entries, picture_manifest = _build_hmi_picture_entries(seed_entries, manifest_assets)
    if (exact_container_ctx is not None or prefix_container_ctx is not None) and not page_entries and not picture_entries:
        if exact_container_ctx is not None:
            official_inspection, official_bytes, official_page_entry, official_page = exact_container_ctx
        else:
            assert prefix_container_ctx is not None
            official_inspection, official_bytes, official_page_entry, official_page = prefix_container_ctx
        if _blocks_match_fixture_replay_shape(page.blocks, official_page.blocks) and _event_tokens_match_blocks(
            page.blocks,
            official_page.blocks,
        ):
            rebuilt_hmi = official_bytes
            if exact_container_ctx is not None and exact_container_donor is not None:
                container_status["selected_strategy"] = "exact_donor_reused"
                container_status["selected_container_donor_id"] = exact_container_donor.donor_id
                container_status["selected_container_hmi"] = str(exact_container_donor.hmi_path)
            elif prefix_container_ctx is not None and prefix_container_donor is not None:
                container_status["selected_strategy"] = "prefix_donor_reused"
                container_status["selected_container_donor_id"] = prefix_container_donor.donor_id
                container_status["selected_container_hmi"] = str(prefix_container_donor.hmi_path)
            output_hmi.write_bytes(rebuilt_hmi)
            return picture_manifest, container_status
        rebuild_seed_bytes = official_bytes
        rebuild_seed_entries = official_inspection.entries
        if exact_container_ctx is not None and exact_container_donor is not None:
            selected_container_donor = exact_container_donor
        else:
            selected_container_donor = prefix_container_donor
        if (
            exact_container_ctx is not None
            and prefix_container_ctx is not None
            and prefix_container_donor is not None
            and (
                exact_container_donor is None
                or (rebuilt_page_sha, exact_container_donor.donor_id) not in _EXACT_DONOR_PAGE_SHA_AND_DONOR_POSITIVE
            )
        ):
            prefix_inspection, prefix_bytes, _prefix_page_entry, _prefix_page = prefix_container_ctx
            rebuild_seed_bytes = prefix_bytes
            rebuild_seed_entries = prefix_inspection.entries
            selected_container_donor = prefix_container_donor
        rebuild_page_entry = next(entry for entry in rebuild_seed_entries if entry.name == "0.pa")
        # For exact-donor rebuilds, preserve the old donor 0.pa as a shadow
        # anonymous entry and append the active rebuilt page at the end. The
        # official donor container uses that shape, and case80-current only
        # reaches official exact compile parity when we keep it.
        force_container_rebuild = exact_container_ctx is not None and selected_container_donor is exact_container_donor
        if len(rebuilt_page) == rebuild_page_entry.length and not force_container_rebuild:
            rebuilt_hmi = _replace_hmi_entry_in_place(
                rebuild_seed_bytes,
                rebuild_seed_entries,
                "0.pa",
                rebuilt_page,
            )
        else:
            rebuilt_hmi = _rebuild_hmi_container(
                rebuild_seed_bytes,
                rebuild_seed_entries,
                replacements={"0.pa": rebuilt_page},
                additions=[],
            )
        if exact_container_ctx is not None and selected_container_donor is exact_container_donor:
            container_status["selected_strategy"] = "exact_donor_rebuild"
        else:
            container_status["selected_strategy"] = "prefix_donor_rebuild"
        if selected_container_donor is not None:
            container_status["selected_container_donor_id"] = selected_container_donor.donor_id
            container_status["selected_container_hmi"] = str(selected_container_donor.hmi_path)
    else:
        rebuilt_hmi = _rebuild_hmi_container(
            seed_bytes,
            seed_entries,
            replacements={"0.pa": rebuilt_page},
            additions=[*page_entries, *picture_entries],
        )
    output_hmi.write_bytes(rebuilt_hmi)
    _maybe_apply_known_hmi_container_postfixes(
        output_hmi=output_hmi,
        page_blocks=page.blocks,
        container_status=container_status,
    )
    return picture_manifest, container_status


def _maybe_apply_known_hmi_container_postfixes(
    *,
    output_hmi: Path,
    page_blocks,
    container_status: dict[str, Any],
) -> None:
    if container_status.get("selected_strategy") != "prefix_donor_rebuild":
        return
    if container_status.get("selected_container_donor_id") != "case85-exact-unproven-hmi-roundtrip":
        return

    signature = tuple((str(getattr(block, "objname", "") or ""), str(getattr(block, "type_code", "") or "")) for block in page_blocks)
    if signature == _CASE85_NEW_BUTTON_NOEVENT_BLOCK_SIGNATURE:
        _promote_active_named_page_in_hmi(output_hmi)
        container_status["container_postfixes"] = [
            *container_status.get("container_postfixes", []),
            "native_named_page_promote_case85_new_button_noevent",
        ]
        return
    if signature == _CASE85_NEW_BUTTON_EVENT_BLOCK_SIGNATURE:
        _promote_active_named_page_in_hmi(output_hmi)
        container_status["container_postfixes"] = [
            *container_status.get("container_postfixes", []),
            "native_named_page_promote_case85_new_button_event_hmi_only",
        ]
        return
    if _is_case85_button_family_signature(signature):
        _promote_active_named_page_in_hmi(output_hmi)
        container_status["container_postfixes"] = [
            *container_status.get("container_postfixes", []),
            "native_named_page_promote_case85_button_family_hmi_only",
        ]


def _is_case85_button_family_signature(
    signature: tuple[tuple[str, str], ...],
) -> bool:
    if len(signature) <= len(_CASE85_BUTTON_FAMILY_BLOCK_PREFIX):
        return False
    if signature[: len(_CASE85_BUTTON_FAMILY_BLOCK_PREFIX)] != _CASE85_BUTTON_FAMILY_BLOCK_PREFIX:
        return False
    extras = signature[len(_CASE85_BUTTON_FAMILY_BLOCK_PREFIX) :]
    return all(type_code == "b" for _name, type_code in extras)

def _promote_active_named_page_in_hmi(hmi_path: Path) -> None:
    raw = hmi_path.read_bytes()
    inspection = inspect_hmi(hmi_path)
    active_entry = next((entry for entry in inspection.entries if entry.name == "0.pa"), None)
    if active_entry is None:
        raise EditorError(f"Named active 0.pa missing in {hmi_path}")

    table = parse_native_cfs_table(raw, NATIVE_CFS_PRIMARY_TABLE_OFFSET)
    native_named_page = find_native_cfs_record(table, "0.pa")
    if native_named_page is None:
        raise EditorError(f"Native CFS named 0.pa missing in {hmi_path}")
    if (
        native_named_page.data_offset == active_entry.data_offset
        and native_named_page.length == active_entry.length
    ):
        return

    active_bytes = raw[active_entry.data_offset : active_entry.data_offset + active_entry.length]
    refreshed_active = refresh_page_safe_header(active_bytes, datasize=active_entry.length)
    refreshed_status = inspect_page_safe_status(refreshed_active)
    if refreshed_status.safe_ok is not True:
        raise EditorError(
            f"Unable to promote named 0.pa in {hmi_path}: active page is not pagesafe after refresh"
        )

    patched = bytearray(raw)
    patched[active_entry.data_offset : active_entry.data_offset + active_entry.length] = refreshed_active
    patched = bytearray(
        rewrite_native_cfs_record(
            patched,
            offset=NATIVE_CFS_PRIMARY_TABLE_OFFSET,
            record_index=native_named_page.index,
            data_offset=active_entry.data_offset,
            length=active_entry.length,
        )
    )
    patched = bytearray(refresh_native_cfs_crc(patched, offset=NATIVE_CFS_PRIMARY_TABLE_OFFSET))
    hmi_path.write_bytes(patched)


def _build_extra_page_entries(
    seed_page,
    extra_pages,
    *,
    button_proto,
    picture_proto,
    number_proto,
    text_proto,
    advanced_protos,
    manifest_assets: dict[str, Any],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seed_page_block = next(block.clone() for block in seed_page.blocks if block.type_code == "y")
    for index, page_spec in enumerate(extra_pages, start=1):
        if page_spec.id != f"page{index}":
            raise EditorError(
                "Multi-page HMI/TFT build V1 requires consecutive page ids page0, page1"
            )

        page = parse_page_data(seed_page.serialize())
        page.page_name = page_spec.id
        block = seed_page_block.clone()
        block.set_string("objname", page_spec.id, encoding="ascii")
        block.set_int("id", 0, width=1)
        _apply_event_fields(block, page_spec.events, owner=page_spec.id)
        generated_blocks = []
        for next_id, widget in enumerate(page_spec.widgets, start=1):
            widget_block = _build_widget_block(
                widget,
                next_id,
                button_proto=button_proto,
                picture_proto=picture_proto,
                number_proto=number_proto,
                timer_proto=None,
                text_proto=text_proto,
                advanced_protos=advanced_protos,
                manifest_assets=manifest_assets,
            )
            if widget_block is None:
                raise EditorError(
                    "Multi-page HMI/TFT build V1 extra pages currently support only "
                    f"{PAGE1_PLAIN_WIDGET_TYPES_LABEL} widgets"
                )
            generated_blocks.append(widget_block)
        page.blocks = [block, *generated_blocks]
        entries.append(
            {
                "name": f"{index}.pa",
                "data": page.serialize(),
                "field3": 0x05111600,
                "kind": "page",
            }
        )
    return entries


def _build_widget_block(
    widget,
    next_id: int,
    *,
    button_proto,
    picture_proto,
    number_proto,
    timer_proto,
    text_proto,
    advanced_protos,
    manifest_assets: dict[str, Any],
):
    if widget.type == "button":
        block = button_proto.clone()
        _apply_common_widget_fields(block, widget, next_id)
        _apply_textual_fields(block, widget)
        _apply_color_fields(block, widget)
        _apply_button_asset_fields(block, widget, manifest_assets)
    elif widget.type == "image":
        if picture_proto is None:
            return None
        block = picture_proto.clone()
        _apply_common_widget_fields(block, widget, next_id)
        _apply_picture_fields(block, widget, manifest_assets)
    elif widget.type == "number":
        if number_proto is None:
            return None
        block = number_proto.clone()
        _apply_common_widget_fields(block, widget, next_id)
        block.set_int("val", int(widget.value or 0), width=4)
        _apply_color_fields(block, widget)
        _apply_number_fields(block, widget)
    elif widget.type == "text":
        block = text_proto.clone()
        _apply_common_widget_fields(block, widget, next_id)
        _apply_textual_fields(block, widget)
        _apply_color_fields(block, widget)
    elif widget.type == "timer":
        if timer_proto is None:
            return None
        block = timer_proto.clone()
        _apply_object_identity_fields(block, widget, next_id)
        _apply_timer_fields(block, widget)
    elif widget.type in AUTHORING_WIDGET_TEMPLATE_CASES:
        proto = advanced_protos.get(widget.type)
        if proto is None:
            return None
        block = proto.clone()
        _apply_common_widget_fields(block, widget, next_id)
        _apply_advanced_widget_fields(block, widget, manifest_assets)
    else:
        return None

    _clear_existing_events(block)
    _apply_event_fields(block, widget.events, owner=widget.id)
    return block


def _apply_seed_page0_widget_patches(
    seed_blocks,
    widgets,
    *,
    manifest_assets: dict[str, Any],
) -> None:
    blocks_by_name = {block.objname: block for block in seed_blocks if block.objname}
    for widget in widgets:
        block = blocks_by_name.get(widget.id)
        if block is None:
            raise EditorError(f"Seed page0 patch target {widget.id!r} does not exist")
        if widget.type == "button" and block.type_code != "b":
            raise EditorError(f"Seed page0 patch target {widget.id!r} is not a button")

        if any(value is not None for value in (widget.x, widget.y, widget.w, widget.h)):
            if None in (widget.x, widget.y, widget.w, widget.h):
                raise EditorError(f"Seed page0 patch target {widget.id!r} geometry requires x/y/w/h together")
            _apply_geometry_fields(block, widget)
        _apply_textual_fields(block, widget)
        _apply_color_fields(block, widget)
        _apply_style_fields(block, widget)
        _apply_resource_fields(block, widget, manifest_assets)
        if widget.events:
            _clear_existing_events(block)
            _apply_event_fields(block, widget.events, owner=widget.id)


def _apply_common_widget_fields(block, widget, next_id: int) -> None:
    _apply_object_identity_fields(block, widget, next_id)
    if block.type_code in NON_VISUAL_WIDGET_TYPE_CODES:
        return
    _apply_geometry_fields(block, widget)


def _apply_object_identity_fields(block, widget, next_id: int) -> None:
    block.set_string("objname", widget.id, encoding="ascii")
    block.set_int("id", next_id, width=1)


def _apply_geometry_fields(block, widget) -> None:
    block.set_int("x", int(widget.x or 0), width=2)
    block.set_int("y", int(widget.y or 0), width=2)
    block.set_int("w", int(widget.w or 0), width=2)
    block.set_int("h", int(widget.h or 0), width=2)
    block.set_int("endx", int(widget.x or 0) + int(widget.w or 0) - 1, width=2)
    block.set_int("endy", int(widget.y or 0) + int(widget.h or 0) - 1, width=2)


def _minimize_seed_objects_in_bounds(blocks, *, width: int, height: int) -> None:
    # Keep placeholder seed objects inside the panel bounds. Some firmware builds
    # reject a page whose compiled object table contains off-screen coordinates.
    x = max(min(width - 1, width), 0)
    y = max(min(height - 1, height), 0)
    for block in blocks:
        if block.type_code == "y":
            continue
        block.set_int("x", x, width=2)
        block.set_int("y", y, width=2)
        block.set_int("w", 1, width=2)
        block.set_int("h", 1, width=2)
        block.set_int("endx", x, width=2)
        block.set_int("endy", y, width=2)


def _first_block_of_type(blocks, type_code: str):
    return next((block.clone() for block in blocks if block.type_code == type_code), None)


def _load_fixture_widget_templates(widget_types) -> dict[str, Any]:
    templates: dict[str, Any] = {}
    for widget_type in sorted(set(widget_types)):
        spec = AUTHORING_WIDGET_TEMPLATE_CASES.get(widget_type)
        if spec is None:
            continue
        case_name, type_code = spec
        templates[widget_type] = _load_case_block_of_type(case_name, type_code)
    return templates


def _load_case_last_block(case_name: str):
    hmi_path = DEFAULT_CASE_ROOT / case_name / "lcd_test.HMI"
    if not hmi_path.exists():
        raise EditorError(
            f"Timer/widget template fixture is missing: {hmi_path}. "
            "Provide local case fixtures or avoid this widget type for now."
        )
    inspection = inspect_hmi(hmi_path)
    raw = hmi_path.read_bytes()
    entry = next(item for item in inspection.entries if item.name == "0.pa")
    return parse_page_data(raw[entry.data_offset : entry.data_offset + entry.length]).blocks[-1].clone()


def _load_case_block_of_type(case_name: str, type_code: str):
    hmi_path = _case_hmi_fixture_path(case_name)
    if not hmi_path.exists():
        raise EditorError(
            f"Widget template fixture is missing: {hmi_path}. "
            f"Cannot create fixture-backed widget type {type_code!r} yet."
        )
    inspection = inspect_hmi(hmi_path)
    raw = hmi_path.read_bytes()
    entry = next(item for item in inspection.entries if item.name == "0.pa")
    page = parse_page_data(raw[entry.data_offset : entry.data_offset + entry.length])
    for block in page.blocks:
        if block.type_code == type_code:
            return block.clone()
    raise EditorError(f"Fixture {hmi_path} does not contain widget type {type_code!r}")


def _case_hmi_fixture_path(case_name: str) -> Path:
    direct = DEFAULT_CASE_ROOT / case_name / "lcd_test.HMI"
    if direct.exists():
        return direct
    return DEFAULT_CASE_ROOT / case_name / "official_wiki" / "source_raw.HMI"


def _apply_textual_fields(block, widget) -> None:
    if widget.text is not None:
        block.set_string("txt", widget.text, encoding="gbk")
        existing_max = _block_int(block, "txt_maxl") or 0
        required = len(widget.text.encode("gbk"))
        block.set_int("txt_maxl", max(existing_max, required, 1), width=2)
    font_id = widget.style.get("font_id")
    if font_id is not None:
        block.set_int("font", int(font_id), width=1)


def _apply_color_fields(block, widget) -> None:
    if "background_color" in widget.style and block.get_field("bco"):
        block.set_int("bco", int(widget.style["background_color"]), width=2)
    if "foreground_color" in widget.style and block.get_field("pco"):
        block.set_int("pco", int(widget.style["foreground_color"]), width=2)
    if "border_color" in widget.style and block.get_field("borderc"):
        block.set_int("borderc", int(widget.style["border_color"]), width=2)
    if "style" in widget.style and block.get_field("style"):
        block.set_int("style", int(widget.style["style"]), width=1)


def _apply_number_fields(block, widget) -> None:
    for style_name in ("length", "digits", "lenth", "format"):
        if style_name not in widget.style:
            continue
        field_name = STYLE_FIELD_ALIASES.get(style_name, style_name)
        if block.get_field(field_name) is None:
            raise EditorError(
                f"Style field {style_name!r} is not supported by widget {widget.id!r} ({widget.type})"
            )
        value = int(widget.style[style_name])
        if field_name == "lenth" and not 1 <= value <= 10:
            raise EditorError(f"Number widget {widget.id!r} length must be 1..10, got {value}")
        _set_existing_int_field(block, field_name, value, owner=widget.id)


def _apply_asset_fields(block, widget, manifest_assets: dict[str, Any]) -> None:
    asset_ref = widget.resources.get("asset")
    if not asset_ref:
        return
    asset_info = manifest_assets.get(asset_ref)
    if not asset_info:
        raise EditorError(f"Asset '{asset_ref}' not imported")
    normal_id = int(_variant_resource_id(asset_info, "normal"))
    pressed_id = int(_variant_resource_id(asset_info, "pressed", fallback="normal"))
    disabled_id = _variant_resource_id(asset_info, "disabled")
    if block.get_field("pic"):
        block.set_int("pic", normal_id, width=2)
    if block.get_field("picc"):
        block.set_int("picc", pressed_id, width=2)
    if disabled_id is not None:
        if block.get_field("pic2"):
            block.set_int("pic2", int(disabled_id), width=2)
        if block.get_field("picc2"):
            block.set_int("picc2", int(disabled_id), width=2)


def _apply_button_asset_fields(block, widget, manifest_assets: dict[str, Any]) -> None:
    asset_ref = widget.resources.get("asset")
    if not asset_ref:
        return
    asset_info = manifest_assets.get(asset_ref)
    if not asset_info:
        raise EditorError(f"Asset '{asset_ref}' not imported")

    mode = str(widget.style.get("image_mode", "image")).lower()
    if mode not in {"image", "crop"}:
        raise EditorError(f"Button image_mode must be 'image' or 'crop', got {mode!r}")

    normal_id = int(_variant_resource_id(asset_info, "normal"))
    pressed_id = int(_variant_resource_id(asset_info, "pressed", fallback="normal"))
    disabled_id = _variant_resource_id(asset_info, "disabled")

    if mode == "crop":
        # sta=0 uses crop-image slots. Keep full-image slots untouched.
        block.set_int("sta", 0, width=1)
        if block.get_field("picc"):
            block.set_int("picc", normal_id, width=2)
        if block.get_field("picc2"):
            block.set_int("picc2", pressed_id, width=2)
    else:
        # sta=2 uses full-image slots: pic = normal, pic2 = pressed.
        block.set_int("sta", 2, width=1)
        if block.get_field("pic"):
            block.set_int("pic", normal_id, width=2)
        if block.get_field("pic2"):
            block.set_int("pic2", pressed_id, width=2)

    if disabled_id is not None:
        # The screen has no verified automatic disabled-state switch here yet;
        # keep the ID in the HMI/manifest for later event/usercode work.
        widget.resources.setdefault("disabled_pic", int(disabled_id))


def _apply_picture_fields(block, widget, manifest_assets: dict[str, Any]) -> None:
    explicit_pic = widget.resources.get("pic")
    if explicit_pic is not None:
        block.set_int("pic", int(explicit_pic), width=2)
        return
    _apply_asset_fields(block, widget, manifest_assets)


def _apply_timer_fields(block, widget) -> None:
    tim = widget.style.get("tim", widget.style.get("interval_ms", widget.value))
    if tim is not None:
        block.set_int("tim", int(tim), width=2)
    en = widget.style.get("en", widget.style.get("enabled"))
    if en is not None:
        block.set_int("en", 1 if bool(en) else 0, width=1)


def _apply_advanced_widget_fields(block, widget, manifest_assets: dict[str, Any]) -> None:
    if widget.text is not None:
        if block.get_field("txt") is None:
            raise EditorError(f"Widget {widget.id!r} of type {widget.type!r} does not support text")
        _apply_textual_fields(block, widget)
    else:
        font_id = widget.style.get("font_id")
        if font_id is not None and block.get_field("font") is not None:
            block.set_int("font", int(font_id), width=1)

    if widget.value is not None:
        _set_existing_int_field(block, "val", int(widget.value), owner=widget.id)

    _apply_color_fields(block, widget)
    _apply_style_fields(block, widget)
    _apply_resource_fields(block, widget, manifest_assets)


def _apply_style_fields(block, widget) -> None:
    handled = {
        "background_color",
        "foreground_color",
        "border_color",
        "font_id",
        "image_mode",
    }
    for raw_name, raw_value in widget.style.items():
        if raw_name in handled:
            continue
        field_name = STYLE_FIELD_ALIASES.get(raw_name, raw_name)
        if block.get_field(field_name) is None:
            raise EditorError(
                f"Style field {raw_name!r} is not supported by widget {widget.id!r} ({widget.type})"
            )
        if isinstance(raw_value, bool):
            value = 1 if raw_value else 0
        else:
            value = int(raw_value)
        _set_existing_int_field(block, field_name, value, owner=widget.id)


def _apply_resource_fields(block, widget, manifest_assets: dict[str, Any]) -> None:
    asset_ref = widget.resources.get("asset")
    if asset_ref:
        _apply_asset_fields(block, widget, manifest_assets)

    handled = {"asset", "disabled_pic", "source", "sources", "gmov", "file"}
    for raw_name, raw_value in widget.resources.items():
        if raw_name in handled:
            continue
        field_name = RESOURCE_FIELD_ALIASES.get(raw_name, raw_name)
        if block.get_field(field_name) is None:
            raise EditorError(
                f"Resource field {raw_name!r} is not supported by widget {widget.id!r} ({widget.type})"
            )
        if isinstance(raw_value, str):
            block.set_string(field_name, raw_value, encoding="ascii")
            continue
        _set_existing_int_field(block, field_name, int(raw_value), owner=widget.id)


def _set_existing_int_field(block, name: str, value: int, *, owner: str) -> None:
    field = block.get_field(name)
    if field is None:
        raise EditorError(f"Widget {owner!r} does not have integer field {name!r}")
    block.set_int(name, value, width=max(1, len(field.value)))


def _apply_event_fields(block, events: dict[str, list[str]], *, owner: str) -> None:
    prefixes = {
        "load": "codesload-",
        "loadend": "codesloadend-",
        "down": "codesdown-",
        "up": "codesup-",
        "unload": "codesunload-",
        "timer": "codestimer-",
        "slide": "codesslide-",
    }
    for name, lines in events.items():
        prefix = prefixes.get(name)
        if prefix is None:
            raise EditorError(f"Unsupported event '{name}' on {owner}")
        block.set_event(prefix, list(lines))


def _build_hmi_picture_entries(entries, manifest_assets: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    existing_names = {entry.name for entry in entries if entry.name}
    image_field3 = _field3_template(entries, ".i")
    source_field3 = _field3_template(entries, ".is")
    additions: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []

    for picture_id, source in _collect_hmi_picture_sources(manifest_assets):
        image_name = f"{picture_id}.i"
        source_name = f"{picture_id}.is"
        if image_name in existing_names and source_name in existing_names:
            continue

        resource, image_entry, source_entry = compile_hmi_picture_resource(source, picture_id)
        if source_name not in existing_names:
            additions.append(
                {
                    "name": source_name,
                    "data": source_entry,
                    "field3": source_field3,
                    "kind": "source",
                }
            )
            existing_names.add(source_name)
        if image_name not in existing_names:
            additions.append(
                {
                    "name": image_name,
                    "data": image_entry,
                    "field3": image_field3,
                    "kind": "image",
                }
            )
            existing_names.add(image_name)
        manifest.append(resource.to_dict())

    return additions, manifest


def _collect_hmi_picture_sources(manifest_assets: dict[str, Any]) -> list[tuple[int, str]]:
    sources: dict[int, str] = {}
    for asset_info in manifest_assets.values():
        variants = asset_info.get("variants") or {}
        for variant_name in ("normal", "pressed", "disabled"):
            variant = variants.get(variant_name)
            if not variant or "resource_id" not in variant:
                continue
            sources[int(variant["resource_id"])] = str(variant["source"])
    return sorted(sources.items(), key=lambda item: item[0])


def _merge_picture_sources(*source_groups: list[tuple[int, str | Path]]) -> list[tuple[int, str]]:
    merged: dict[int, str] = {}
    for group in source_groups:
        for picture_id, source in group:
            picture_id = int(picture_id)
            if picture_id in merged:
                continue
            merged[picture_id] = str(Path(source).resolve())
    return [(picture_id, merged[picture_id]) for picture_id in sorted(merged)]


def _seed_fixture_picture_resources(
    scene: SceneModel,
    *,
    target_pages: list[Path],
    output_hmi: Path,
) -> tuple[list[dict[str, Any]], list[tuple[int, bytes, str]]]:
    target_picture_ids: set[int] = set()
    for page_path in target_pages:
        target_picture_ids.update(_page_picture_ids(page_path.read_bytes()))
    existing_names = {entry.name for entry in inspect_hmi(output_hmi).entries if entry.in_file and entry.name}
    missing_picture_ids = sorted(
        picture_id
        for picture_id in target_picture_ids
        if picture_id != 0xFFFF
        and (f"{picture_id}.i" not in existing_names or f"{picture_id}.is" not in existing_names)
    )
    if not missing_picture_ids:
        return [], []

    fixture_resources = _collect_fixture_picture_resources(scene, missing_picture_ids)
    if not fixture_resources:
        return [], []

    inspection = inspect_hmi(output_hmi)
    output_raw = output_hmi.read_bytes()
    output_entries = inspection.entries
    image_field3 = _field3_template(output_entries, ".i")
    source_field3 = _field3_template(output_entries, ".is")
    existing_names = {entry.name for entry in output_entries if entry.name}
    additions: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    tft_entries: list[tuple[int, bytes, str]] = []

    for picture_id in missing_picture_ids:
        resource = fixture_resources.get(picture_id)
        if resource is None:
            continue

        source_name = resource["source_entry_name"]
        image_name = resource["image_entry_name"]
        if source_name not in existing_names:
            additions.append(
                {
                    "name": source_name,
                    "data": resource["source_entry_data"],
                    "field3": source_field3,
                    "kind": "source",
                }
            )
            existing_names.add(source_name)
        if image_name not in existing_names:
            additions.append(
                {
                    "name": image_name,
                    "data": resource["image_entry_data"],
                    "field3": image_field3,
                    "kind": "image",
                }
            )
            existing_names.add(image_name)

        manifest_row = {
            "picture_id": picture_id,
            "fixture_case": resource["fixture_case"],
            "fixture_hmi": str(resource["fixture_hmi"]),
            "image_entry_name": image_name,
            "source_entry_name": source_name,
            "image_entry_size": len(resource["image_entry_data"]),
            "source_entry_size": len(resource["source_entry_data"]),
            "mode": "fixture-copy",
        }
        manifest_rows.append(manifest_row)
        source_label = f"{resource['fixture_case']}:{image_name}"
        tft_entries.append((picture_id, resource["image_entry_data"], source_label))
        manifest_row["tft_entry_source"] = source_label

    if additions:
        rebuilt_hmi = _rebuild_hmi_container(
            output_raw,
            output_entries,
            replacements={},
            additions=additions,
        )
        output_hmi.write_bytes(rebuilt_hmi)

    return manifest_rows, tft_entries


def _filter_fixture_tft_picture_entries(
    baseline_tft: Path,
    picture_entries: list[tuple[int, bytes, str]],
) -> list[tuple[int, bytes, str]]:
    if not picture_entries:
        return []
    header2 = inspect_tft(baseline_tft)["parsed"]["Header2"]
    image_resource_address = int(header2["videos_address"], 16)
    existing_records, _picture_region_end = _parse_picture_resource_records(
        baseline_tft.read_bytes(),
        image_resource_address,
    )
    existing_ids = {int(record["picture_id"]) for record in existing_records}
    return [
        (picture_id, entry_data, source_label)
        for picture_id, entry_data, source_label in picture_entries
        if int(picture_id) not in existing_ids
    ]


def _collect_fixture_picture_resources(
    scene: SceneModel,
    picture_ids: list[int],
) -> dict[int, dict[str, Any]]:
    widget_types: list[str] = []
    seen_widget_types: set[str] = set()
    for page in scene.pages:
        for widget in page.widgets:
            if widget.type in seen_widget_types:
                continue
            seen_widget_types.add(widget.type)
            widget_types.append(widget.type)

    resources: dict[int, dict[str, Any]] = {}
    for widget_type in widget_types:
        spec = AUTHORING_WIDGET_TEMPLATE_CASES.get(widget_type)
        if spec is None:
            continue
        fixture_case, _type_code = spec
        fixture_hmi = _case_hmi_fixture_path(fixture_case)
        if not fixture_hmi.exists():
            continue
        inspection = inspect_hmi(fixture_hmi)
        raw = fixture_hmi.read_bytes()
        entries = {entry.name: entry for entry in inspection.entries if entry.in_file and entry.name}
        for picture_id in picture_ids:
            if picture_id in resources:
                continue
            image_name = f"{picture_id}.i"
            source_name = f"{picture_id}.is"
            image_entry = entries.get(image_name)
            source_entry = entries.get(source_name)
            if image_entry is None or source_entry is None:
                continue
            image_entry_data = raw[image_entry.data_offset : image_entry.data_offset + image_entry.length]
            source_entry_data = raw[source_entry.data_offset : source_entry.data_offset + source_entry.length]
            resources[picture_id] = {
                "fixture_case": fixture_case,
                "fixture_hmi": fixture_hmi,
                "image_entry_name": image_name,
                "source_entry_name": source_name,
                "image_entry_data": image_entry_data,
                "source_entry_data": source_entry_data,
            }
    return resources


def _page_picture_ids(page_bytes: bytes) -> set[int]:
    page = parse_page_data(page_bytes)
    return {value for value in _existing_picture_ids(page.blocks) if value != 0xFFFF}


def _validate_multi_page_scene_support(scene: SceneModel) -> None:
    allow_events = _experimental_multi_page_events_enabled(scene)
    allow_page1_filebrowser = _experimental_page1_filebrowser_enabled(scene)
    patch_seed_page0_widgets = _patch_seed_page0_widgets_enabled(scene)
    if len(scene.pages) != 2:
        raise EditorError("Multi-page build V1 supports exactly two pages: page0 and page1")
    expected_ids = ["page0", "page1"]
    page_ids = [page.id for page in scene.pages]
    if page_ids != expected_ids:
        raise EditorError(f"Multi-page build V1 requires pages {expected_ids}, got {page_ids}")
    if scene.pages[0].events:
        raise EditorError("Multi-page build V1 requires page0 to keep the seed object layout unchanged")
    if scene.pages[0].widgets and not patch_seed_page0_widgets:
        raise EditorError("Multi-page build V1 requires page0 to keep the seed object layout unchanged")
    _validate_seed_page0_widget_patches(
        scene.pages[0].widgets,
        allow_experimental_events=allow_events,
        enabled=patch_seed_page0_widgets,
    )
    if scene.pages[1].events and not (
        allow_events and _is_supported_experimental_page1_page_events(scene.pages[1].events)
    ):
        raise EditorError("Multi-page build V1 does not support page1 events yet")
    seen_ids = {"page0", "page1"}
    for widget in scene.pages[1].widgets:
        page1_filebrowser_probe = allow_page1_filebrowser and widget.type == "file-browser"
        if widget.type not in PAGE1_PLAIN_WIDGET_TYPES and not page1_filebrowser_probe:
            raise EditorError(
                "Multi-page build V1 page1 supports only "
                f"{PAGE1_PLAIN_WIDGET_TYPES_LABEL} widgets"
            )
        if widget.id in seen_ids:
            raise EditorError(f"Multi-page build V1 page1 object name conflicts with {widget.id!r}")
        seen_ids.add(widget.id)
        if widget.events and not (
            allow_events
            and _is_supported_experimental_page1_event_widget(widget, page1_widgets=scene.pages[1].widgets)
        ):
            raise EditorError("Multi-page build V1 does not support page1 widget events yet")
        if page1_filebrowser_probe and widget.events:
            raise EditorError("Multi-page build V1 page1 file-browser events are not supported yet")
        if widget.resources and not (
            (widget.type == "image" and set(widget.resources).issubset({"pic"}))
            or (page1_filebrowser_probe and set(widget.resources).issubset({"dir", "filter"}))
        ):
            raise EditorError("Multi-page build V1 does not support page1 widget resources yet")
        if widget.children:
            raise EditorError("Multi-page build V1 does not support page1 child widgets yet")


def _experimental_multi_page_events_enabled(scene: SceneModel) -> bool:
    return bool(scene.project.get("experimental_multi_page_events"))


def _experimental_page1_filebrowser_enabled(scene: SceneModel) -> bool:
    return bool(scene.project.get("experimental_page1_filebrowser"))


def _multi_page_physical_row_order(scene: SceneModel) -> str:
    value = scene.project.get("multi_page_physical_row_order")
    if value in (None, ""):
        return MULTI_PAGE_PHYSICAL_ROW_ORDER_CASE31_LAYOUT
    if value not in {
        MULTI_PAGE_PHYSICAL_ROW_ORDER_CASE31_LAYOUT,
        MULTI_PAGE_PHYSICAL_ROW_ORDER_PAGE0_FIRST,
    }:
        supported = ", ".join(
            (
                MULTI_PAGE_PHYSICAL_ROW_ORDER_CASE31_LAYOUT,
                MULTI_PAGE_PHYSICAL_ROW_ORDER_PAGE0_FIRST,
            )
        )
        raise EditorError(
            f"project.multi_page_physical_row_order must be one of: {supported}; got {value!r}"
        )
    return str(value)


def _multi_page_trailing_filebrowser_xfloat_normalization_enabled(scene: SceneModel) -> bool:
    return bool(scene.project.get("multi_page_trailing_filebrowser_xfloat_normalization"))


def _patch_seed_page0_widgets_enabled(scene: SceneModel) -> bool:
    return bool(scene.project.get("patch_seed_page0_widgets"))


def _validate_seed_page0_widget_patches(
    widgets,
    *,
    allow_experimental_events: bool,
    enabled: bool,
) -> None:
    if not widgets:
        return
    if not enabled:
        raise EditorError("Multi-page build V1 seed page0 widget patches are not enabled")
    seen_ids: set[str] = set()
    for widget in widgets:
        if widget.id in seen_ids:
            raise EditorError(f"Multi-page build V1 duplicate seed page0 patch target {widget.id!r}")
        seen_ids.add(widget.id)
        if widget.type not in SEED_PAGE0_PATCH_WIDGET_TYPES:
            raise EditorError("Multi-page build V1 seed page0 patch currently supports only button widgets")
        if widget.resources:
            raise EditorError("Multi-page build V1 seed page0 patch does not support widget resources yet")
        if widget.children:
            raise EditorError("Multi-page build V1 seed page0 patch does not support child widgets yet")
        if widget.events and not (
            allow_experimental_events and _is_supported_experimental_seed_page0_event_widget(widget)
        ):
            raise EditorError("Multi-page build V1 seed page0 widget events are not supported yet")


def _is_supported_experimental_seed_page0_event_widget(widget) -> bool:
    event_item = _single_page1_button_event_widget(widget)
    if event_item is None:
        return False
    _, line = event_item
    return is_supported_page1_button_event_line(line) or is_page1_printh_probe_event_line(line)


def _is_supported_experimental_page1_page_events(events: dict[str, list[str]]) -> bool:
    event_items = [(name, lines) for name, lines in events.items() if lines]
    if not event_items or len(event_items) > 2:
        return False
    names = {name for name, _lines in event_items}
    if not names.issubset({"load", "loadend"}):
        return False
    return all(
        len(lines) == 1 and is_page1_fixed_printh_probe_event_line(lines[0], byte_count=4)
        for _event_name, lines in event_items
    )


def _is_supported_experimental_page1_event_widget(widget, *, page1_widgets=None) -> bool:
    event_item = _single_page1_button_event_widget(widget)
    if event_item is None:
        return False
    _, line = event_item
    if is_supported_page1_button_event_line(line):
        return True
    if page1_widgets is None:
        return False
    return (
        _is_supported_page1_button_click_event_widget(widget, line=line, page1_widgets=page1_widgets)
        or _is_supported_page1_button_vis_event_widget(widget, line=line, page1_widgets=page1_widgets)
        or _is_supported_page1_button_tsw_event_widget(widget, line=line, page1_widgets=page1_widgets)
        or _is_supported_page1_button_ref_event_widget(widget, line=line, page1_widgets=page1_widgets)
    )


def _single_page1_button_event_widget(widget) -> tuple[str, str] | None:
    if widget.type != "button":
        return None
    event_items = [(name, lines) for name, lines in widget.events.items() if lines]
    if len(event_items) != 1:
        return None
    event_name, lines = event_items[0]
    if event_name not in {"down", "up"} or len(lines) != 1:
        return None
    return event_name, lines[0]


def _is_supported_page1_button_click_event_widget(widget, *, line: str, page1_widgets) -> bool:
    parsed = parse_page1_button_click_event_line(line)
    if parsed is None:
        return False
    target_name, _ = parsed
    if target_name == widget.id:
        return False
    target_widget = next((candidate for candidate in page1_widgets if candidate.id == target_name), None)
    if target_widget is None or target_widget.type != "button":
        return False
    target_event_item = _single_page1_button_event_widget(target_widget)
    if target_event_item is None:
        return False
    _, target_line = target_event_item
    return is_page1_printh_probe_event_line(target_line)


def _is_supported_page1_button_vis_event_widget(widget, *, line: str, page1_widgets) -> bool:
    parsed = parse_page1_button_vis_event_line(line)
    if parsed is None:
        return False
    target_name, _ = parsed
    if target_name == widget.id:
        return False
    return any(candidate.id == target_name for candidate in page1_widgets)


def _is_supported_page1_button_tsw_event_widget(widget, *, line: str, page1_widgets) -> bool:
    parsed = parse_page1_button_tsw_event_line(line)
    if parsed is None:
        return False
    target_name, _ = parsed
    if target_name == "255":
        return True
    return any(candidate.id == target_name for candidate in page1_widgets)


def _is_supported_page1_button_ref_event_widget(widget, *, line: str, page1_widgets) -> bool:
    target_name = parse_page1_button_ref_event_line(line)
    if target_name is None:
        return False
    if target_name == widget.id:
        return False
    return any(candidate.id == target_name for candidate in page1_widgets)


def _field3_template(entries, suffix: str) -> int:
    for entry in reversed(entries):
        if entry.name.endswith(suffix):
            return entry.field3
    return 0


def _official_complex_hmi_container_seed(blocks) -> Path | None:
    return find_proven_complex_hmi_donor(blocks)


def _rebuild_hmi_container(
    seed_bytes: bytes,
    entries,
    *,
    replacements: dict[str, bytes],
    additions: list[dict[str, Any]],
) -> bytes:
    original_data_start = min(entry.data_offset for entry in entries if entry.in_file)
    source_additions = [item for item in additions if item.get("kind") == "source"]
    image_additions = [item for item in additions if item.get("kind") == "image"]
    page_additions = [item for item in additions if item.get("kind") == "page"]
    last_source_index = _last_entry_index(entries, ".is")
    last_image_index = _last_entry_index(entries, ".i")
    appended_replacements: list[dict[str, Any]] = []

    specs: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if entry.name == "0.pa":
            specs.extend(page_additions)
        data = replacements.get(entry.name)
        name_bytes = bytes.fromhex(entry.name_hex)
        field3 = entry.field3
        if entry.name == "0.pa" and "0.pa" in replacements:
            # Official USART HMI keeps old page revisions as shadow "\0.pa"
            # entries and appends the active named "0.pa" at the end.
            data = seed_bytes[entry.data_offset : entry.data_offset + entry.length]
            name_bytes = b"\x00" + b".pa" + b"\x00" * 12
            field3 = int(entry.field3) | 1
            appended_replacements.append(
                {
                    "name": "0.pa",
                    "data": replacements["0.pa"],
                    "field3": 0x05111600,
                }
            )
        if data is None:
            data = seed_bytes[entry.data_offset : entry.data_offset + entry.length]
        specs.append(
            {
                "name": entry.name,
                "name_bytes": name_bytes,
                "data": data,
                "field3": field3,
            }
        )
        if index == last_source_index:
            specs.extend(source_additions)
        if index == last_image_index:
            specs.extend(image_additions)

    if last_source_index < 0:
        specs.extend(source_additions)
    if last_image_index < 0:
        specs.extend(image_additions)
    specs.extend(appended_replacements)

    directory_end = 4 + len(specs) * 28
    data_start = max(original_data_start, directory_end)

    result = bytearray(seed_bytes[:original_data_start])
    if len(result) < data_start:
        result.extend(b"\x00" * (data_start - len(result)))
    result[0:4] = len(specs).to_bytes(4, "little")
    result[4:directory_end] = b"\x00" * (directory_end - 4)

    cursor = data_start
    for index, spec in enumerate(specs):
        base = 4 + index * 28
        if "name_bytes" in spec:
            name = bytes(spec["name_bytes"])
        else:
            name = str(spec["name"]).encode("ascii", errors="ignore")
        if len(name) > 16:
            raise EditorError(f"HMI entry name is too long: {spec['name']!r}")
        data = bytes(spec["data"])
        result[base : base + 16] = name.ljust(16, b"\x00")
        result[base + 16 : base + 20] = cursor.to_bytes(4, "little")
        result[base + 20 : base + 24] = len(data).to_bytes(4, "little")
        result[base + 24 : base + 28] = int(spec["field3"]).to_bytes(4, "little")
        if len(result) != cursor:
            raise EditorError("Internal HMI rebuild cursor drifted")
        result.extend(data)
        cursor += len(data)
    return bytes(result)


def _last_entry_index(entries, suffix: str) -> int:
    for index in range(len(entries) - 1, -1, -1):
        if entries[index].name.endswith(suffix):
            return index
    return -1


def _replace_hmi_entry(seed_bytes: bytes, entries, target_name: str, replacement: bytes) -> bytes:
    target = next((entry for entry in entries if entry.name == target_name), None)
    if target is None:
        raise EditorError(f"Entry '{target_name}' not found in seed HMI")

    result = bytearray(seed_bytes)
    target_end = target.data_offset + target.length
    last_end = max(entry.data_offset + entry.length for entry in entries)
    if target_end == last_end:
        result[target.data_offset:target_end] = replacement
        new_offset = target.data_offset
    else:
        new_offset = len(result)
        result.extend(replacement)

    base = target.dir_offset
    result[base + 16 : base + 20] = int(new_offset).to_bytes(4, "little")
    result[base + 20 : base + 24] = len(replacement).to_bytes(4, "little")
    return _sync_native_cfs_record_if_present(
        bytes(result),
        entry_name=target_name,
        data_offset=new_offset,
        length=len(replacement),
    )


def _replace_hmi_entry_in_place(seed_bytes: bytes, entries, target_name: str, replacement: bytes) -> bytes:
    target = next((entry for entry in entries if entry.name == target_name), None)
    if target is None:
        raise EditorError(f"Entry '{target_name}' not found in container HMI")
    if len(replacement) != target.length:
        raise EditorError(
            f"Entry '{target_name}' length mismatch for in-place replacement: "
            f"{len(replacement)} != {target.length}"
        )
    result = bytearray(seed_bytes)
    target_end = target.data_offset + target.length
    result[target.data_offset:target_end] = replacement
    return _sync_native_cfs_record_if_present(
        bytes(result),
        entry_name=target_name,
        data_offset=target.data_offset,
        length=target.length,
    )


def _sync_native_cfs_record_if_present(raw: bytes, *, entry_name: str, data_offset: int, length: int) -> bytes:
    patched = raw
    changed = False
    for offset in (NATIVE_CFS_PRIMARY_TABLE_OFFSET,):
        try:
            table = parse_native_cfs_table(patched, offset)
        except Exception:
            continue
        record = find_native_cfs_record(table, entry_name)
        if record is None:
            continue
        if record.data_offset == int(data_offset) and record.length == int(length):
            continue
        patched = rewrite_native_cfs_record(
            patched,
            offset=offset,
            record_index=record.index,
            data_offset=int(data_offset),
            length=int(length),
        )
        patched = refresh_native_cfs_crc(patched, offset=offset)
        changed = True
    return patched if changed else raw


def _write_hmi_entry(hmi_path: Path, entry_name: str, out_path: Path) -> Path:
    inspection = inspect_hmi(hmi_path)
    entry = next((item for item in inspection.entries if item.name == entry_name), None)
    if entry is None or not entry.in_file:
        raise EditorError(f"Entry '{entry_name}' not found in {hmi_path}")
    raw = hmi_path.read_bytes()
    out_path.write_bytes(raw[entry.data_offset : entry.data_offset + entry.length])
    return out_path


def _validate_tft_target_support(
    baseline_pa: Path,
    target_pa: Path,
    *,
    packed_picture_ids: set[int] | None = None,
    clean_rebuild: bool = False,
) -> None:
    baseline_page = load_page_file(baseline_pa)
    target_page = load_page_file(target_pa)
    existing_pics = _existing_picture_ids(baseline_page.blocks)
    packed_pics = set(packed_picture_ids or set())
    allowed_pics = existing_pics | packed_pics
    checked_blocks = target_page.blocks[1:] if clean_rebuild else target_page.blocks[len(baseline_page.blocks) :]
    media_blocks = [block for block in checked_blocks if block.type_code in MEDIA_WIDGET_TYPE_CODES]
    if len(media_blocks) > 1:
        names = ", ".join(repr(block.objname) for block in media_blocks)
        raise EditorError(
            "TFT scene build media widgets path supports only one media fixture per page in this pass: "
            f"{names}. Split GMOV/video/audio smoke tests into separate TFTs until mixed-media scheduling is proven."
        )
    replay_blocks = [block for block in checked_blocks if block.type_code in {"A", "B", "?"}]
    if replay_blocks and len(replay_blocks) != 1:
        names = ", ".join(repr(block.objname) for block in replay_blocks)
        raise EditorError(
            "TFT scene build fixture-shaped direct TFT replay/native-template path supports only one "
            "data-record/file-browser/file-stream control per page in this pass: "
            f"{names}. file-browser/file-stream may be mixed with ordinary native controls, but split "
            "data-record smoke scenes until mixed native synthesis has live proof "
            "for both the ordinary events and the advanced control runtime fields."
        )
    if replay_blocks and replay_blocks[0].type_code in {"A", "?"}:
        replay_block = replay_blocks[0]
        advanced_companions = [
            block
            for block in checked_blocks
            if block is not replay_block and block.type_code in ADVANCED_FILE_RUNTIME_TYPE_CODES
        ]
        if advanced_companions:
            allowed_file_browser_text_companion_mix = (
                replay_block.type_code == "A"
                and len(advanced_companions) == 1
                and advanced_companions[0].type_code in {"D", ">"}
                and not _block_has_scene_event_lines(replay_block)
                and not _block_has_scene_event_lines(advanced_companions[0])
            )
            allowed_file_stream_text_select_mix = (
                replay_block.type_code == "?"
                and len(advanced_companions) == 1
                and advanced_companions[0].type_code in {"D", ">"}
                and not _block_has_scene_event_lines(replay_block)
                and not _block_has_scene_event_lines(advanced_companions[0])
            )
            if not allowed_file_browser_text_companion_mix and not allowed_file_stream_text_select_mix:
                names = ", ".join(repr(block.objname) for block in advanced_companions)
                raise EditorError(
                    "TFT scene build file-browser/file-stream native-template path may be mixed only with "
                    "ordinary native controls/events, or with one no-event text-select/sliding-text next to one "
                    "no-event file-browser plus optional ordinary native controls/events, or with the exact "
                    "two-widget no-event file-stream + text-select/sliding-text shape, in this pass: "
                    f"{names}. Keep other text-select/sliding-text/data-record/file-browser/file-stream mixes "
                    "in separate smoke scenes until mixed advanced runtime fields have live proof."
                )
    for block in checked_blocks:
        if block.type_code not in TYPE_RECORD_LENGTHS:
            raise EditorError(
                "TFT scene build does not know how to compile this object type yet: "
                f"object {block.objname!r} has type {block.type_code!r}"
            )
        if block.type_code == "A":
            continue
        for field_name in ("pic", "picc", "pic2", "picc2"):
            value = _block_int(block, field_name)
            if value is None or value == 0xFFFF:
                continue
            if value in packed_pics and block.type_code not in {"p", "b", "q"}:
                raise EditorError(
                    "TFT scene build can pack new image resources only for picture/button/crop-image objects in this pass: "
                    f"object {block.objname!r} has type {block.type_code!r} and references {field_name}={value}"
                )
            if value not in allowed_pics:
                raise EditorError(
                    "TFT scene build cannot pack new image resources yet: "
                    f"object {block.objname!r} references {field_name}={value}, "
                    f"but only existing seed pictures {sorted(existing_pics)} and packed pictures {sorted(packed_pics)} are available"
                )


def _validate_tft_build_has_no_hmi_only_widgets(scene: SceneModel) -> None:
    hmi_only_widgets = [
        widget
        for page in scene.pages
        for widget in page.widgets
        if (
            widget.type in HMI_ONLY_FIXTURE_WIDGET_TYPES
            and widget.type not in EXPERIMENTAL_DIRECT_TFT_FIXTURE_WIDGET_TYPES
        )
    ]
    if not hmi_only_widgets:
        return
    details = ", ".join(f"{widget.id}:{widget.type}" for widget in hmi_only_widgets)
    raise EditorError(
        "Cannot build TFT: fixture-backed HMI-only widget(s) are present "
        f"({details}). Direct/native TFT rebuild and live behavior are not claimed for these types yet; "
        "build output.hmi only or compile the HMI with the official USART HMI GUI oracle path."
    )


def _validate_fixture_replay_widgets_have_no_scene_events(scene: SceneModel) -> None:
    _validate_file_stream_open_event_allowlist(scene)
    all_event_widgets = [
        widget
        for page in scene.pages
        for widget in page.widgets
        if _widget_has_scene_event_lines(widget)
    ]
    file_browser_event_widgets = [
        widget
        for widget in all_event_widgets
        if widget.type == "file-browser"
    ]
    for widget in file_browser_event_widgets:
        event_names = {name for name, lines in widget.events.items() if lines}
        if event_names - {"down", "up"}:
            raise EditorError(
                "TFT scene build supports only file-browser down/up scene-authored events in this pass: "
                f"{widget.id}:{widget.type} has {sorted(event_names)}."
            )
    if file_browser_event_widgets and len(all_event_widgets) > len(file_browser_event_widgets):
        details = ", ".join(f"{widget.id}:{widget.type}" for widget in all_event_widgets)
        raise EditorError(
            "TFT scene build file-browser-owned event path is limited to the file-browser down/up callbacks "
            "without other scene event widgets in this pass: "
            f"{details}."
        )
    event_widgets = [
        widget
        for widget in all_event_widgets
        if widget.type in {"data-record", "file-stream"}
    ]
    if not event_widgets:
        return
    details = ", ".join(f"{widget.id}:{widget.type}" for widget in event_widgets)
    raise EditorError(
        "TFT scene build fixture-shaped direct TFT replay does not support event scripts "
        "on data-record/file-stream yet: "
        f"{details}. The current replay path would otherwise copy the official fixture TFT "
        "without compiling the requested scene events."
    )


def _validate_file_stream_open_event_allowlist(scene: SceneModel) -> None:
    for page in scene.pages:
        file_stream_ids = {widget.id for widget in page.widgets if widget.type == "file-stream"}
        if not file_stream_ids:
            continue
        event_sources = [(page.id, "page", event_name, lines) for event_name, lines in page.events.items()]
        event_sources.extend(
            (widget.id, widget.type, event_name, lines)
            for widget in page.widgets
            for event_name, lines in widget.events.items()
        )
        if not any(_file_stream_event_calls(lines, file_stream_ids) for _owner_id, _owner_type, _event_name, lines in event_sources):
            continue
        text_ids = {widget.id for widget in page.widgets if widget.type == "text"}
        advanced_companions = [
            widget
            for widget in page.widgets
            if widget.type in {"text-select", "sliding-text", "data-record", "file-browser"}
        ]
        allow_text_select_open_companion = (
            len(advanced_companions) == 1
            and advanced_companions[0].type == "text-select"
            and not _widget_has_scene_event_lines(advanced_companions[0])
        )
        if advanced_companions and not allow_text_select_open_companion:
            advanced_detail = ", ".join(f"{widget.id}:{widget.type}" for widget in advanced_companions)
            raise EditorError(
                "TFT scene build currently supports file-stream open calls only on the plain case72 button/text page "
                "or on the exact no-event file-stream + text-select companion shape: "
                f"{page.id} has unsupported advanced companions {advanced_detail}."
            )
        for owner_id, owner_type, event_name, lines in event_sources:
            _validate_file_stream_event_lines(
                lines,
                event_name=event_name,
                owner_id=owner_id,
                owner_type=owner_type,
                file_stream_ids=file_stream_ids,
                text_ids=text_ids,
            )


def _validate_file_stream_event_lines(
    lines: list[str],
    *,
    event_name: str,
    owner_id: str,
    owner_type: str,
    file_stream_ids: set[str],
    text_ids: set[str],
) -> None:
    calls = _file_stream_event_calls(lines, file_stream_ids)
    if not calls:
        return

    detail = f"{owner_id}:{owner_type}.{event_name}"
    if owner_type != "button" or event_name != "down":
        raise EditorError(
            "TFT scene build supports file-stream open calls only from ordinary button.down "
            f"in the case72 PC-oracle path: {detail}."
        )
    if len(calls) != 1 or len(lines) != 3 or calls[0][0] != 1:
        raise EditorError(
            "TFT scene build supports only the case72-style three-line button.down wrapper "
            f"`printh / fs0.open(text.txt) / printh` for file-stream open calls: {detail}."
        )
    if PRINTH_EVENT_LINE_RE.match(lines[0]) is None or PRINTH_EVENT_LINE_RE.match(lines[2]) is None:
        raise EditorError(
            "TFT scene build requires before/after printh markers around the case72 file-stream open call: "
            f"{detail}."
        )

    call_line = lines[1]
    open_call = FILE_STREAM_OPEN_TEXT_REF_RE.match(call_line)
    if open_call is None:
        raise EditorError(
            "TFT scene build supports only `fs0.open(text_widget.txt)` in the case72 PC-oracle path: "
            f"{detail} has {call_line!r}."
        )
    stream_id, text_id = open_call.groups()
    if stream_id not in file_stream_ids or text_id not in text_ids:
        raise EditorError(
            "TFT scene build file-stream open calls must reference same-page file-stream and text widgets: "
            f"{detail} has {call_line!r}."
        )


def _file_stream_event_calls(lines: list[str], file_stream_ids: set[str]) -> list[tuple[int, re.Match[str]]]:
    calls: list[tuple[int, re.Match[str]]] = []
    for index, line in enumerate(lines):
        method = EVENT_METHOD_CALL_RE.match(line)
        if method is not None and method.group(1) in file_stream_ids:
            calls.append((index, method))
    return calls


def _widget_has_scene_event_lines(widget) -> bool:
    return any(bool(lines) for lines in widget.events.values())


def _block_has_scene_event_lines(block) -> bool:
    tokens = list(block.event_tokens)
    cursor = 0
    while cursor < len(tokens):
        name = tokens[cursor]
        cursor += 1
        if not name.startswith("codes"):
            continue
        try:
            line_count = int(name.rsplit("-", 1)[1])
        except (IndexError, ValueError):
            line_count = 0
        cursor += max(line_count, 0)
        if line_count > 0:
            return True
    return False


def _existing_picture_ids(blocks) -> set[int]:
    values = {0xFFFF}
    for block in blocks:
        for field_name in ("pic", "pic1", "picc", "picc1", "pic2", "picc2"):
            value = _block_int(block, field_name)
            if value is not None:
                values.add(value)
    return values


def _block_int(block, name: str) -> int | None:
    field = block.get_field(name)
    if field is None or not field.value:
        return None
    return int.from_bytes(field.value, "little")


def _assign_tft_picture_resource_ids(
    seed_hmi: Path,
    scene: SceneModel,
    manifest_assets: dict[str, Any],
) -> set[int]:
    if not manifest_assets:
        return set()
    inspection = inspect_hmi(seed_hmi)
    seed_bytes = seed_hmi.read_bytes()
    page_entry = next(entry for entry in inspection.entries if entry.name == "0.pa")
    page = parse_page_data(seed_bytes[page_entry.data_offset : page_entry.data_offset + page_entry.length])
    existing_pics = {value for value in _existing_picture_ids(page.blocks) if value != 0xFFFF}
    next_picture_id = (max(existing_pics) + 1) if existing_pics else 0
    referenced_assets = _referenced_asset_keys(scene)
    packed_ids: set[int] = set()
    for asset_key in sorted(referenced_assets):
        asset_info = manifest_assets.get(asset_key)
        if not asset_info:
            raise EditorError(f"Asset '{asset_key}' not imported")
        variants = asset_info.get("variants") or {}
        for variant_name in ("normal", "pressed", "disabled"):
            variant = variants.get(variant_name)
            if not variant:
                continue
            while next_picture_id in existing_pics or next_picture_id in packed_ids:
                next_picture_id += 1
            variant["resource_id"] = next_picture_id
            packed_ids.add(next_picture_id)
            next_picture_id += 1
        normal_id = _variant_resource_id(asset_info, "normal")
        if normal_id is not None:
            asset_info["resource_id"] = int(normal_id)
    return packed_ids


def _referenced_asset_keys(scene: SceneModel) -> set[str]:
    keys: set[str] = set()
    for page in scene.pages:
        for widget in page.widgets:
            asset_key = widget.resources.get("asset")
            if asset_key:
                keys.add(str(asset_key))
    return keys


def _collect_tft_picture_sources(
    manifest_assets: dict[str, Any],
    packed_picture_ids: set[int],
) -> list[tuple[int, str]]:
    sources: list[tuple[int, str]] = []
    for asset_info in manifest_assets.values():
        variants = asset_info.get("variants") or {}
        for variant_name in ("normal", "pressed", "disabled"):
            variant = variants.get(variant_name)
            if not variant:
                continue
            picture_id = int(variant["resource_id"])
            if picture_id in packed_picture_ids:
                sources.append((picture_id, str(variant["source"])))
    return sources


def _collect_tft_gmov_sources(scene: SceneModel) -> list[str]:
    source_dir = Path(scene.project.get("_source_dir") or ".").resolve()
    sources: list[str] = []
    seen: dict[str, int] = {}
    for page in scene.pages:
        for widget in page.widgets:
            if widget.type != "animation":
                continue
            raw_sources = _widget_gmov_sources(widget)
            if not raw_sources:
                continue
            first_index: int | None = None
            for raw_source in raw_sources:
                path = _resolve_resource_source(raw_source, source_dir)
                key = str(path)
                if key not in seen:
                    seen[key] = len(sources)
                    sources.append(key)
                if first_index is None:
                    first_index = seen[key]
            if first_index is not None and "vid" not in widget.resources:
                widget.resources["vid"] = first_index
    return sources


def _widget_gmov_sources(widget) -> list[str]:
    value = widget.resources.get("sources")
    if value is not None:
        if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
            raise EditorError(f"Widget {widget.id!r} resources.sources must be a list of paths")
        return list(value)
    for key in ("source", "gmov", "file"):
        value = widget.resources.get(key)
        if value is not None:
            if not isinstance(value, str) or not value:
                raise EditorError(f"Widget {widget.id!r} resources.{key} must be a non-empty path")
            return [value]
    return []


def _resolve_resource_source(value: str, source_dir: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = source_dir / path
    path = path.resolve()
    if not path.exists():
        raise EditorError(f"GMOV resource source not found: {path}")
    return path


def _image_to_rgb565(image: Image.Image) -> bytes:
    output = bytearray()
    rgba = image.convert("RGBA").tobytes()
    for offset in range(0, len(rgba), 4):
        red, green, blue, alpha = rgba[offset : offset + 4]
        if alpha == 0:
            red = green = blue = 0
        value = ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)
        output.extend(value.to_bytes(2, "little"))
    return bytes(output)


def _clear_existing_events(block) -> None:
    prefixes = []
    for token in block.event_tokens:
        if token.startswith("codes"):
            prefix = token.rsplit("-", 1)[0] + "-"
            if prefix not in prefixes:
                prefixes.append(prefix)
    for prefix in prefixes:
        block.set_event(prefix, [])


def _import_scene_asset(asset, out_dir: Path) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "id": asset.id,
        "source": asset.source,
        "variants": {},
    }

    if asset.normal or asset.pressed or asset.disabled:
        if asset.normal:
            manifest["variants"]["normal"] = import_asset(asset.normal, out_dir)
        if asset.pressed:
            manifest["variants"]["pressed"] = import_asset(asset.pressed, out_dir)
        if asset.disabled:
            manifest["variants"]["disabled"] = import_asset(asset.disabled, out_dir)
        if "normal" not in manifest["variants"] and asset.source:
            manifest["variants"]["normal"] = import_asset(asset.source, out_dir)
    else:
        manifest["variants"]["normal"] = import_asset(asset.source, out_dir)

    primary = manifest["variants"]["normal"]
    manifest.update(
        {
            "normalized_png": primary["normalized_png"],
            "rgb565": primary["rgb565"],
            "width": primary["width"],
            "height": primary["height"],
            "digest": primary["digest"],
            "resource_id": primary["resource_id"],
        }
    )
    return manifest


def _variant_resource_id(asset_info: dict[str, Any], variant: str, fallback: str | None = None) -> int | None:
    variants = asset_info.get("variants", {})
    if variant in variants:
        return int(variants[variant]["resource_id"])
    if fallback and fallback in variants:
        return int(variants[fallback]["resource_id"])
    if variant == "normal" and "resource_id" in asset_info:
        return int(asset_info["resource_id"])
    return None
