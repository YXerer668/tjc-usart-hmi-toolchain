from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agent_preview import generate_agent_preview
from .design_ops import (
    design_align_widgets,
    design_distribute_widgets,
    design_match_size_widgets,
    design_move_widget,
    design_resize_widget,
    replay_agent_patch,
)
from .editor_capabilities import editor_capability_manifest, editor_completion_audit
from .editor import build_scene
from .event_logic import graph_scene_events, lint_scene_events, list_event_command_snippets
from .event_simulator import simulate_scene_event
from .export_bundle import export_scene_bundle
from .hmi_import import import_hmi_project
from .hmi_inspect import inspect_hmi
from .hmi_donor_patch import patch_hmi_donor
from .hmi_donor_patch import generate_lowlevel_compatible_fixture, generate_reopen_safe_fixture
from .hmi_roundtrip import check_hmi_roundtrip
from .scene import SceneModel, load_scene, validate_scene
from .scene_check import check_scene_project
from .scenario_runner import run_scene_scenario
from .scene_smoke import run_scene_smoke
from .sd_recovery_guard import pending_sd_recovery_reason
from .target_status import (
    builder_calibration_status,
    current_target_completion_audit,
    next_live_probe_bundle,
    page1_filebrowser_frontier,
    page1_filebrowser_native_init_compare_targets,
    target_status_summary,
)
from .target_invariants import check_next_probe_tft_invariants
from .target_probe import run_next_live_probe_bundle
from .scene_edit import (
    add_scene_asset,
    add_scene_page,
    add_scene_widget,
    append_scene_event_command,
    clear_scene_event,
    copy_scene_widget,
    copy_scene_widget_to_page,
    cut_scene_widget,
    create_scene_document,
    delete_scene_asset,
    delete_scene_page,
    delete_scene_widget,
    duplicate_scene_page,
    duplicate_scene_widget,
    edit_scene_event_command,
    get_scene_event,
    list_scene_event_commands,
    list_scene_assets,
    list_scene_events,
    move_scene_widget,
    paste_scene_widget,
    save_scene_document_as,
    set_scene_event,
    update_scene_asset,
    update_scene_page,
    update_scene_project,
    update_scene_widget,
)
from .tft_checksum import inspect_tft_checksum
from .tft_toolchain import inspect_tft, list_supported_tft_models
from .tft_event_index import inspect_tft_event_index, inspect_tft_event_index_batch
from .widget_templates import get_widget_template, list_widget_templates
from .widgets import (
    WidgetSupport,
    get_widget_type_info,
    iter_widget_type_infos,
    normalize_widget_type,
    widget_capability_manifest,
)


def validate_scene_document(payload: dict[str, Any]) -> SceneModel:
    """Validate a raw scene dictionary and return the normalized scene model."""
    return validate_scene(payload)


def validate_scene_file(path: str | Path) -> SceneModel:
    """Load and validate a JSON/YAML scene file."""
    return load_scene(path)


def create_scene_file(
    scene_path: str | Path,
    *,
    project_name: str | None = None,
    width: int = 800,
    height: int = 480,
    default_page: str = "page0",
    background_color: int = 65535,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create a new empty scene JSON/YAML file."""
    return create_scene_document(
        scene_path,
        project_name=project_name,
        width=width,
        height=height,
        default_page=default_page,
        background_color=background_color,
        overwrite=overwrite,
    )


def save_scene_file_as(source_path: str | Path, dest_path: str | Path, *, overwrite: bool = False) -> dict[str, Any]:
    """Validate and save a scene document under a new path."""
    return save_scene_document_as(source_path, dest_path, overwrite=overwrite)


def check_scene_file(
    scene_path: str | Path,
    *,
    out_dir: str | Path | None = None,
    target: str = "TJC8048X543_011C",
    simulate_events: bool = False,
    max_event_slots: int = 50,
    max_steps: int = 128,
    scenario_paths: list[str | Path] | tuple[str | Path, ...] | None = None,
) -> dict[str, Any]:
    """Create an offline editor-style validation/capability/event check report."""
    return check_scene_project(
        scene_path,
        out_dir=out_dir,
        target=target,
        simulate_events=simulate_events,
        max_event_slots=max_event_slots,
        max_steps=max_steps,
        scenario_paths=scenario_paths,
    )


def import_hmi_file(
    hmi_path: str | Path,
    out_dir: str | Path,
    *,
    target: str = "TJC8048X543_011C",
    overwrite: bool = False,
) -> dict[str, Any]:
    """Import an official HMI file into a lossy editable scene plus agent preview bundle."""
    return import_hmi_project(hmi_path, out_dir, target=target, overwrite=overwrite)


def check_hmi_roundtrip_file(
    hmi_path: str | Path,
    out_dir: str | Path,
    *,
    target: str = "TJC8048X543_011C",
    overwrite: bool = False,
    source_tft: str | Path | None = None,
) -> dict[str, Any]:
    """Import and regenerate an HMI file, then report structural roundtrip loss."""
    return check_hmi_roundtrip(hmi_path, out_dir, target=target, overwrite=overwrite, source_tft=source_tft)


def patch_hmi_donor_file(
    donor_hmi: str | Path,
    out_dir: str | Path,
    *,
    page_entry: str = "0.pa",
    delete_objects: list[str] | tuple[str, ...] | None = None,
    graft_specs: list[str] | tuple[str, ...] | None = None,
    move_specs: list[str] | tuple[str, ...] | None = None,
    int_specs: list[str] | tuple[str, ...] | None = None,
    str_specs: list[str] | tuple[str, ...] | None = None,
    probe_lowlevel: bool = False,
) -> dict[str, Any]:
    """Patch a donor HMI page while preserving the donor container/shadow chain."""
    return patch_hmi_donor(
        donor_hmi=Path(donor_hmi).resolve(),
        out_dir=Path(out_dir).resolve(),
        page_entry=page_entry,
        delete_objects=list(delete_objects or []),
        graft_specs=list(graft_specs or []),
        move_specs=list(move_specs or []),
        int_specs=list(int_specs or []),
        str_specs=list(str_specs or []),
        probe_lowlevel=probe_lowlevel,
    )


def generate_reopen_safe_hmi_fixture(
    control_type: str,
    out_dir: str | Path,
    *,
    corpus_root: str | Path | None = None,
) -> dict[str, Any]:
    """Generate the canonical reopen-safe donor fixture for one control type."""
    if corpus_root is None:
        return generate_reopen_safe_fixture(control_type, out_dir)
    return generate_reopen_safe_fixture(control_type, out_dir, corpus_root=corpus_root)


def generate_lowlevel_compatible_hmi_fixture(
    control_type: str,
    out_dir: str | Path,
    *,
    corpus_root: str | Path | None = None,
) -> dict[str, Any]:
    """Generate the canonical lowlevel-compatible donor fixture for one control type."""
    if corpus_root is None:
        return generate_lowlevel_compatible_fixture(control_type, out_dir)
    return generate_lowlevel_compatible_fixture(control_type, out_dir, corpus_root=corpus_root)


def inspect_tft_event_index_file(
    hmi_path: str | Path,
    tft_path: str | Path,
    *,
    force_post_primary_page_load: bool = False,
    out_path: str | Path | None = None,
) -> dict[str, Any]:
    """Inspect HMI source events against compiled TFT event-index evidence."""
    return inspect_tft_event_index(
        hmi_path,
        tft_path,
        force_post_primary_page_load=force_post_primary_page_load,
        out_path=out_path,
    )


def inspect_tft_event_index_batch_files(
    paths: list[str | Path] | tuple[str | Path, ...],
    *,
    force_post_primary_page_load: bool = False,
    include_object_only: bool = False,
    out_path: str | Path | None = None,
) -> dict[str, Any]:
    """Scan HMI files for nearby official TFT/run event-index evidence."""
    return inspect_tft_event_index_batch(
        paths,
        force_post_primary_page_load=force_post_primary_page_load,
        include_object_only=include_object_only,
        out_path=out_path,
    )


def build_scene_artifacts(
    scene_path: str | Path,
    seed_hmi: str | Path,
    out_dir: str | Path,
    *,
    baseline_tft: str | Path | None = None,
    font_zi: str | Path | None = None,
    font_entry: str = "0.zi",
) -> dict[str, Any]:
    """Build output.hmi and, when a compatible baseline is supplied, output.tft."""
    scene = load_scene(scene_path)
    return build_scene(
        scene,
        seed_hmi,
        out_dir,
        baseline_tft=baseline_tft,
        font_zi=font_zi,
        font_entry=font_entry,
    )


def export_scene_bundle_document(
    scene_path: str | Path,
    out_dir: str | Path,
    *,
    seed_hmi: str | Path | None = None,
    baseline_tft: str | Path | None = None,
    font_zi: str | Path | None = None,
    font_entry: str = "0.zi",
    target: str = "TJC8048X543_011C",
) -> dict[str, Any]:
    """Create an offline compile-style export bundle without uploading hardware."""
    return export_scene_bundle(
        scene_path,
        out_dir,
        seed_hmi=seed_hmi,
        baseline_tft=baseline_tft,
        font_zi=font_zi,
        font_entry=font_entry,
        target=target,
    )


def get_editor_capability_manifest() -> dict[str, Any]:
    """Return the current desktop/headless editor capability manifest."""
    return editor_capability_manifest()


def get_editor_completion_audit() -> dict[str, Any]:
    """Return the current official-editor parity audit checklist."""
    return editor_completion_audit()


def get_current_target_completion_audit() -> dict[str, Any]:
    """Return the current target completion audit artifact."""
    return current_target_completion_audit()


def get_current_target_status_summary() -> dict[str, Any]:
    """Return a compact current-target status summary for tools and agents."""
    return target_status_summary()


def get_builder_calibration_status() -> dict[str, Any]:
    """Return the current builder-facing calibration status artifact."""
    return builder_calibration_status()


def get_page1_filebrowser_frontier_report() -> dict[str, Any]:
    """Return the current page1 file-browser frontier report."""
    return page1_filebrowser_frontier()


def get_page1_filebrowser_native_init_compare_targets_report() -> dict[str, Any]:
    """Return the current page1 file-browser native-init compare-targets report."""
    return page1_filebrowser_native_init_compare_targets()


def get_next_live_probe_bundle() -> dict[str, Any]:
    """Return the exact next live-probe bundle for the current target."""
    return next_live_probe_bundle()


def check_next_probe_invariants(tft_path: str | Path | None = None) -> dict[str, Any]:
    """Check the current next-probe TFT against the builder field-map invariants."""
    return check_next_probe_tft_invariants(tft_path)


def run_next_live_probe(
    *,
    preflight: bool = False,
    live_smoke: bool = False,
    upload: bool = False,
    allow_hardware_quarantine: bool = False,
    allow_pending_sd_recovery: bool = False,
    capture: bool = False,
    progress: bool = False,
    port: str = "COM36",
    baud: int = 9600,
    download_baud: int = 921600,
    timeout_ms: int = 3000,
    out_dir: str | Path | None = None,
    result_json: str | Path | None = None,
) -> dict[str, Any]:
    """Run safe portions of the current target's next live-probe bundle."""
    return run_next_live_probe_bundle(
        preflight=preflight,
        live_smoke=live_smoke,
        upload=upload,
        allow_hardware_quarantine=allow_hardware_quarantine,
        allow_pending_sd_recovery=allow_pending_sd_recovery,
        capture=capture,
        progress=progress,
        port=port,
        baud=baud,
        download_baud=download_baud,
        timeout_ms=timeout_ms,
        out_dir=out_dir,
        result_json=result_json,
    )


def append_scene_event_command_document(
    scene_path: str | Path,
    event_path: str,
    *,
    command: str,
    target: str | None = None,
    value: str | int | None = None,
    op: str = "=",
    attribute: str = "val",
    hex_bytes: str | list[str] | list[int] | tuple[str | int, ...] | None = None,
    delay_ms: int | None = None,
    raw_line: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Append one structured event command line to a scene event slot."""
    return append_scene_event_command(
        scene_path,
        event_path,
        command=command,
        target=target,
        value=value,
        op=op,
        attribute=attribute,
        hex_bytes=hex_bytes,
        delay_ms=delay_ms,
        raw_line=raw_line,
        dry_run=dry_run,
    )


def copy_scene_widget_document(scene_path: str | Path, *, page_id: str, widget_id: str) -> dict[str, Any]:
    """Return a widget clipboard payload without modifying the scene."""
    return copy_scene_widget(scene_path, page_id=page_id, widget_id=widget_id)


def cut_scene_widget_document(scene_path: str | Path, *, page_id: str, widget_id: str) -> dict[str, Any]:
    """Copy one widget to a clipboard payload, then remove it from the scene."""
    return cut_scene_widget(scene_path, page_id=page_id, widget_id=widget_id)


def paste_scene_widget_document(
    scene_path: str | Path,
    *,
    page_id: str,
    widget: dict[str, Any],
    new_id: str | None = None,
    offset_x: int = 16,
    offset_y: int = 16,
    x: int | None = None,
    y: int | None = None,
) -> dict[str, Any]:
    """Paste a widget clipboard payload into a scene page."""
    return paste_scene_widget(
        scene_path,
        page_id=page_id,
        widget=widget,
        new_id=new_id,
        offset_x=offset_x,
        offset_y=offset_y,
        x=x,
        y=y,
    )


def copy_scene_widget_to_page_document(
    scene_path: str | Path,
    *,
    source_page_id: str,
    widget_id: str,
    target_page_id: str,
    new_id: str | None = None,
    offset_x: int = 16,
    offset_y: int = 16,
    x: int | None = None,
    y: int | None = None,
) -> dict[str, Any]:
    """Copy a widget and paste it into a target page in one operation."""
    return copy_scene_widget_to_page(
        scene_path,
        source_page_id=source_page_id,
        widget_id=widget_id,
        target_page_id=target_page_id,
        new_id=new_id,
        offset_x=offset_x,
        offset_y=offset_y,
        x=x,
        y=y,
    )


def design_move_widget_document(
    scene_path: str | Path,
    out_dir: str | Path | None,
    *,
    page_id: str,
    widget_id: str,
    x: int | None = None,
    y: int | None = None,
    dx: int = 0,
    dy: int = 0,
    snap: int = 1,
    clamp: bool = True,
    source: str = "api-design-move",
) -> dict[str, Any]:
    """Move one widget and write design_session/agent_patch artifacts."""
    return design_move_widget(
        scene_path,
        out_dir,
        page_id=page_id,
        widget_id=widget_id,
        x=x,
        y=y,
        dx=dx,
        dy=dy,
        snap=snap,
        clamp=clamp,
        source=source,
    )


def design_resize_widget_document(
    scene_path: str | Path,
    out_dir: str | Path | None,
    *,
    page_id: str,
    widget_id: str,
    w: int | None = None,
    h: int | None = None,
    dw: int = 0,
    dh: int = 0,
    min_size: int = 1,
    snap: int = 1,
    clamp: bool = True,
    source: str = "api-design-resize",
) -> dict[str, Any]:
    """Resize one widget and write design_session/agent_patch artifacts."""
    return design_resize_widget(
        scene_path,
        out_dir,
        page_id=page_id,
        widget_id=widget_id,
        w=w,
        h=h,
        dw=dw,
        dh=dh,
        min_size=min_size,
        snap=snap,
        clamp=clamp,
        source=source,
    )


def design_align_widgets_document(
    scene_path: str | Path,
    out_dir: str | Path | None,
    *,
    page_id: str,
    widget_ids: list[str] | tuple[str, ...],
    edge: str,
    anchor: str = "first",
    snap: int = 1,
    clamp: bool = True,
    source: str = "api-design-align",
) -> dict[str, Any]:
    """Align widgets on one page and write design_session/agent_patch artifacts."""
    return design_align_widgets(
        scene_path,
        out_dir,
        page_id=page_id,
        widget_ids=widget_ids,
        edge=edge,
        anchor=anchor,
        snap=snap,
        clamp=clamp,
        source=source,
    )


def design_distribute_widgets_document(
    scene_path: str | Path,
    out_dir: str | Path | None,
    *,
    page_id: str,
    widget_ids: list[str] | tuple[str, ...],
    axis: str,
    snap: int = 1,
    clamp: bool = True,
    source: str = "api-design-distribute",
) -> dict[str, Any]:
    """Distribute widgets on one page and write design_session/agent_patch artifacts."""
    return design_distribute_widgets(
        scene_path,
        out_dir,
        page_id=page_id,
        widget_ids=widget_ids,
        axis=axis,
        snap=snap,
        clamp=clamp,
        source=source,
    )


def design_match_size_widgets_document(
    scene_path: str | Path,
    out_dir: str | Path | None,
    *,
    page_id: str,
    widget_ids: list[str] | tuple[str, ...],
    mode: str,
    anchor: str = "first",
    min_size: int = 1,
    snap: int = 1,
    clamp: bool = True,
    source: str = "api-design-match-size",
) -> dict[str, Any]:
    """Match widget width/height on one page and write design_session/agent_patch artifacts."""
    return design_match_size_widgets(
        scene_path,
        out_dir,
        page_id=page_id,
        widget_ids=widget_ids,
        mode=mode,
        anchor=anchor,
        min_size=min_size,
        snap=snap,
        clamp=clamp,
        source=source,
    )


def replay_agent_patch_document(
    scene_path: str | Path,
    patch_path: str | Path,
    out_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Replay a design agent_patch.json against a scene file."""
    return replay_agent_patch(scene_path, patch_path, out_dir)


def list_scene_event_slots(scene_path: str | Path, *, include_empty: bool = True) -> dict[str, Any]:
    """List known scene event slots with support-boundary metadata."""
    return list_scene_events(scene_path, include_empty=include_empty)


def get_scene_event_slot(scene_path: str | Path, event_path: str) -> dict[str, Any]:
    """Read one scene event slot, such as page0.load or page0.btn0.down."""
    return get_scene_event(scene_path, event_path)


def set_scene_event_slot(
    scene_path: str | Path,
    event_path: str,
    lines: str | list[str] | tuple[str, ...],
    *,
    append: bool = False,
) -> dict[str, Any]:
    """Set one scene event slot and save the source scene file."""
    return set_scene_event(scene_path, event_path, lines, append=append)


def clear_scene_event_slot(scene_path: str | Path, event_path: str) -> dict[str, Any]:
    """Clear one scene event slot and save the source scene file."""
    return clear_scene_event(scene_path, event_path)


def list_scene_event_commands_document(scene_path: str | Path, event_path: str) -> dict[str, Any]:
    """List parsed command lines for one scene event slot."""
    return list_scene_event_commands(scene_path, event_path)


def edit_scene_event_command_document(
    scene_path: str | Path,
    event_path: str,
    *,
    action: str,
    index: int | None = None,
    to_index: int | None = None,
    line: str | None = None,
    command: str | None = None,
    target: str | None = None,
    value: str | int | None = None,
    op: str = "=",
    attribute: str = "val",
    hex_bytes: str | list[str] | list[int] | tuple[str | int, ...] | None = None,
    delay_ms: int | None = None,
    raw_line: str | None = None,
    dry_run: bool = False,
    simulate: bool = False,
    out_dir: str | Path | None = None,
    max_steps: int = 128,
) -> dict[str, Any]:
    """Patch one command line inside an event slot and optionally simulate before/after."""
    return edit_scene_event_command(
        scene_path,
        event_path,
        action=action,
        index=index,
        to_index=to_index,
        line=line,
        command=command,
        target=target,
        value=value,
        op=op,
        attribute=attribute,
        hex_bytes=hex_bytes,
        delay_ms=delay_ms,
        raw_line=raw_line,
        dry_run=dry_run,
        simulate=simulate,
        out_dir=out_dir,
        max_steps=max_steps,
    )


def lint_scene_event_logic(scene_path: str | Path) -> dict[str, Any]:
    """Analyze scene event code references and structured command coverage."""
    return lint_scene_events(scene_path)


def graph_scene_event_navigation(scene_path: str | Path) -> dict[str, Any]:
    """Return page navigation edges inferred from structured event commands."""
    return graph_scene_events(scene_path)


def list_event_snippets() -> dict[str, Any]:
    """Return supported event command snippets for CLI, GUI, and agents."""
    return list_event_command_snippets()


def get_widget_template_document(
    widget_type: str,
    *,
    widget_id: str | None = None,
    x: int = 40,
    y: int = 40,
) -> dict[str, Any]:
    """Return a starter widget document for the toolbox or external agents."""
    return get_widget_template(widget_type, widget_id=widget_id, x=x, y=y)


def list_widget_template_documents() -> dict[str, Any]:
    """Return all registered starter widget templates."""
    return list_widget_templates()


def simulate_scene_event_document(
    scene_path: str | Path,
    event_path: str,
    *,
    out_dir: str | Path | None = None,
    initial_page: str | None = None,
    max_steps: int = 128,
) -> dict[str, Any]:
    """Run a guarded offline simulation of one event slot and optional trace bundle."""
    return simulate_scene_event(
        scene_path,
        event_path,
        out_dir=out_dir,
        initial_page=initial_page,
        max_steps=max_steps,
    )


def run_scene_scenario_document(
    scene_path: str | Path,
    scenario_path: str | Path,
    *,
    out_dir: str | Path | None = None,
    initial_page: str | None = None,
    max_steps: int | None = None,
) -> dict[str, Any]:
    """Run an offline multi-step scene scenario with trigger/assert steps."""
    return run_scene_scenario(
        scene_path,
        scenario_path,
        out_dir=out_dir,
        initial_page=initial_page,
        max_steps=max_steps,
    )


def run_scene_smoke_document(
    scene_path: str | Path,
    *,
    seed_hmi: str | Path,
    baseline_tft: str | Path,
    out_dir: str | Path,
    expect_json: str | Path | None = None,
    check_expect_path: str | Path | None = None,
    write_expect_path: str | Path | None = None,
    skip_build: bool = False,
    preflight: bool = False,
    smoke: bool = False,
    upload: bool = False,
    capture: bool = False,
    port: str = "COM36",
    baud: int = 9600,
    download_baud: int = 921600,
    timeout_ms: int = 3000,
    expected_model: str = "TJC8048X543_011C",
    progress: bool = False,
    known_current: str | Path | None = None,
    skip_if_identical: bool = False,
    allow_hardware_quarantine: bool = False,
    allow_pending_sd_recovery: bool = False,
) -> dict[str, Any]:
    """Build a scene and optionally continue into readiness, preflight, and live smoke."""
    return run_scene_smoke(
        scene_path,
        seed_hmi=seed_hmi,
        baseline_tft=baseline_tft,
        out_dir=out_dir,
        expect_json=expect_json,
        check_expect_path=check_expect_path,
        write_expect_path=write_expect_path,
        skip_build=skip_build,
        preflight=preflight,
        smoke=smoke,
        upload=upload,
        capture=capture,
        port=port,
        baud=baud,
        download_baud=download_baud,
        timeout_ms=timeout_ms,
        expected_model=expected_model,
        progress=progress,
        known_current=known_current,
        skip_if_identical=skip_if_identical,
        allow_hardware_quarantine=allow_hardware_quarantine,
        allow_pending_sd_recovery=allow_pending_sd_recovery,
    )


def list_scene_asset_documents(scene_path: str | Path) -> dict[str, Any]:
    """List asset documents in a scene file."""
    return list_scene_assets(scene_path)


def add_scene_asset_document(scene_path: str | Path, *, asset_id: str, asset: dict[str, Any]) -> dict[str, Any]:
    """Add one asset to a scene and save the source scene file."""
    return add_scene_asset(scene_path, asset_id=asset_id, asset=asset)


def update_scene_asset_document(
    scene_path: str | Path,
    *,
    asset_id: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Update one scene asset and save the source scene file."""
    return update_scene_asset(scene_path, asset_id=asset_id, updates=updates)


def delete_scene_asset_document(scene_path: str | Path, *, asset_id: str, force: bool = False) -> dict[str, Any]:
    """Delete one scene asset and save the source scene file."""
    return delete_scene_asset(scene_path, asset_id=asset_id, force=force)


def add_scene_widget_document(scene_path: str | Path, *, page_id: str, widget: dict[str, Any]) -> dict[str, Any]:
    """Append one widget to a scene page and save the source scene file."""
    return add_scene_widget(scene_path, page_id=page_id, widget=widget)


def update_scene_widget_document(
    scene_path: str | Path,
    *,
    page_id: str,
    widget_id: str,
    updates: dict[str, Any],
    rewrite_event_references: bool = False,
) -> dict[str, Any]:
    """Update one widget in a scene page and save the source scene file."""
    return update_scene_widget(
        scene_path,
        page_id=page_id,
        widget_id=widget_id,
        updates=updates,
        rewrite_event_references=rewrite_event_references,
    )


def delete_scene_widget_document(scene_path: str | Path, *, page_id: str, widget_id: str) -> dict[str, Any]:
    """Delete one widget from a scene page and save the source scene file."""
    return delete_scene_widget(scene_path, page_id=page_id, widget_id=widget_id)


def duplicate_scene_widget_document(
    scene_path: str | Path,
    *,
    page_id: str,
    widget_id: str,
    new_id: str | None = None,
    offset_x: int = 16,
    offset_y: int = 16,
) -> dict[str, Any]:
    """Duplicate one widget in a scene page and save the source scene file."""
    return duplicate_scene_widget(
        scene_path,
        page_id=page_id,
        widget_id=widget_id,
        new_id=new_id,
        offset_x=offset_x,
        offset_y=offset_y,
    )


def move_scene_widget_document(
    scene_path: str | Path,
    *,
    page_id: str,
    widget_id: str,
    direction: str,
) -> dict[str, Any]:
    """Move one widget in page z-order and save the source scene file."""
    return move_scene_widget(scene_path, page_id=page_id, widget_id=widget_id, direction=direction)


def add_scene_page_document(
    scene_path: str | Path,
    *,
    page_id: str,
    layout: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one page to a scene and save the source scene file."""
    return add_scene_page(scene_path, page_id=page_id, layout=layout)


def duplicate_scene_page_document(
    scene_path: str | Path,
    *,
    page_id: str,
    new_id: str | None = None,
) -> dict[str, Any]:
    """Duplicate one page in a scene and save the source scene file."""
    return duplicate_scene_page(scene_path, page_id=page_id, new_id=new_id)


def delete_scene_page_document(scene_path: str | Path, *, page_id: str) -> dict[str, Any]:
    """Delete one page from a scene and save the source scene file."""
    return delete_scene_page(scene_path, page_id=page_id)


def update_scene_project_document(
    scene_path: str | Path,
    *,
    name: str | None = None,
    default_page: str | None = None,
    width: int | None = None,
    height: int | None = None,
    background_color: int | None = None,
) -> dict[str, Any]:
    """Update project and canvas metadata in a scene file."""
    return update_scene_project(
        scene_path,
        name=name,
        default_page=default_page,
        width=width,
        height=height,
        background_color=background_color,
    )


def update_scene_page_document(
    scene_path: str | Path,
    *,
    page_id: str,
    new_id: str | None = None,
    layout: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Update one page id or layout in a scene file."""
    return update_scene_page(scene_path, page_id=page_id, new_id=new_id, layout=layout)


def inspect_hmi_file(path: str | Path) -> dict[str, Any]:
    """Inspect an HMI container and return JSON-friendly metadata."""
    return inspect_hmi(path).to_dict()


def inspect_tft_file(path: str | Path) -> dict[str, Any]:
    """Inspect a TFT file with the local TFTTool wrapper."""
    return inspect_tft(path)


def get_tft_readiness(path: str | Path) -> dict[str, Any]:
    """Return the offline readiness summary for a TFT build artifact."""
    tft_path = Path(path).resolve()
    checksum = inspect_tft_checksum(tft_path)
    build_manifest = _load_build_manifest_metadata(tft_path)
    quarantine_reason = _dangerous_tft_quarantine_reason(tft_path)
    sd_reason = pending_sd_recovery_reason()
    checksum_ok = bool(checksum.get("valid"))
    delivery_status = build_manifest.get("delivery_status") if build_manifest else None
    manifest_ready = None
    manifest_reason = None
    if isinstance(delivery_status, dict):
        ready_value = delivery_status.get("ready_for_live_upload")
        manifest_ready = bool(ready_value) if isinstance(ready_value, bool) else None
        raw_reason = delivery_status.get("reason")
        manifest_reason = str(raw_reason) if raw_reason else None
    ready = checksum_ok and not quarantine_reason and not sd_reason and (manifest_ready is not False)
    if not checksum_ok:
        diagnosis = "TFT checksum is invalid; do not upload until it is repaired."
    elif quarantine_reason:
        diagnosis = quarantine_reason
    elif sd_reason:
        diagnosis = sd_reason
    elif manifest_ready is False and manifest_reason:
        diagnosis = manifest_reason
    else:
        diagnosis = "offline build appears eligible for live upload; run serial preflight next."
    return {
        "file": str(tft_path),
        "summary": {
            "ready_for_live_upload": ready,
            "tft_checksum_valid": checksum_ok,
            "build_manifest_present": build_manifest is not None,
            "hardware_quarantine_blocked": bool(quarantine_reason),
            "sd_recovery_blocked": bool(sd_reason),
            "diagnosis": diagnosis,
        },
        "checksum": checksum,
        "build_manifest": build_manifest,
        "dangerous_tft_quarantine_reason": quarantine_reason,
        "sd_recovery_pending_reason": sd_reason,
    }


def list_tft_models() -> list[dict[str, Any]]:
    """Return TFT models known by the local TFTTool wrapper."""
    return list_supported_tft_models()


def list_widget_capabilities(
    *,
    support: str | WidgetSupport | None = None,
    include_aliases: bool = False,
) -> list[dict[str, Any]]:
    """Return widget capability metadata for tools, docs, or future UI frontends."""
    parsed_support = _parse_support(support)
    return [
        info.to_dict(include_aliases=include_aliases)
        for info in iter_widget_type_infos(support=parsed_support)
    ]


def get_widget_capability(widget_type: str, *, include_aliases: bool = False) -> dict[str, Any]:
    """Return normalized metadata for a widget type or alias."""
    info = get_widget_type_info(widget_type)
    if info is None:
        normalized = normalize_widget_type(widget_type)
        return {
            "type": normalized,
            "support": "unknown",
            "writer": "none",
            "reason": "widget type is not registered",
        }
    return info.to_dict(include_aliases=include_aliases)


def get_capability_manifest(*, include_aliases: bool = False) -> dict[str, Any]:
    """Return a structured snapshot of the current target capability registry."""
    return widget_capability_manifest(include_aliases=include_aliases)


def _load_build_manifest_metadata(tft_path: Path) -> dict[str, Any] | None:
    manifest_path = tft_path.with_name("manifest.json")
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return {
        "manifest_path": str(manifest_path),
        "delivery_status": manifest.get("delivery_status"),
        "oracle_alignment": manifest.get("oracle_alignment"),
        "hardware_quarantine": manifest.get("hardware_quarantine"),
        "tft_patch": manifest.get("tft_patch"),
    }


def _touch_capture_quarantine_reason(tft_path: Path) -> str | None:
    manifest_path = tft_path.with_name("manifest.json")
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    for page in manifest.get("pages", []):
        for widget in page.get("widgets", []):
            if widget.get("type") == "touch-capture":
                return f"sibling manifest {manifest_path} contains widget {widget.get('id')!r} type touch-capture"
    return None


def _manifest_hardware_quarantine_reason(tft_path: Path) -> str | None:
    manifest = _load_build_manifest_metadata(tft_path)
    if manifest is None:
        return None
    quarantine = manifest.get("hardware_quarantine")
    if not isinstance(quarantine, dict) or not quarantine.get("active"):
        return None
    reason = str(quarantine.get("reason") or "").strip()
    patch_path = str(quarantine.get("patch_path") or "").strip()
    manifest_path = manifest.get("manifest_path")
    if not reason:
        if patch_path:
            return f"sibling manifest {manifest_path} declares an active hardware quarantine (patch_path={patch_path})"
        return f"sibling manifest {manifest_path} declares an active hardware quarantine"
    if patch_path:
        return f"sibling manifest {manifest_path} declares an active hardware quarantine (patch_path={patch_path}): {reason}"
    return f"sibling manifest {manifest_path} declares an active hardware quarantine: {reason}"


def _case83_event_quarantine_reason(tft_path: Path) -> str | None:
    return None


def _dangerous_tft_quarantine_reason(tft_path: Path) -> str | None:
    return (
        _manifest_hardware_quarantine_reason(tft_path)
        or _touch_capture_quarantine_reason(tft_path)
        or _case83_event_quarantine_reason(tft_path)
    )


def _parse_support(value: str | WidgetSupport | None) -> WidgetSupport | None:
    if value is None or isinstance(value, WidgetSupport):
        return value
    try:
        return WidgetSupport(value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in WidgetSupport)
        raise ValueError(f"support must be one of: {allowed}") from exc
