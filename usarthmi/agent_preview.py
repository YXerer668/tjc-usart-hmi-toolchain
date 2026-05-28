from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from . import __version__
from .editor_capabilities import editor_capability_manifest, editor_completion_audit
from .event_logic import analyze_scene_events, list_event_command_snippets
from .layout import resolve_page_layout
from .preview import render_scene_preview
from .scene import SceneModel, WidgetSpec, load_scene, save_scene_json
from .scene_edit import collect_scene_event_slots, event_model_manifest
from .target_status import target_status_summary
from .widgets import CURRENT_TARGET, WidgetSupport, WidgetWriter, get_widget_type_info, widget_capability_manifest


AGENT_PREVIEW_SCHEMA_VERSION = 1
NON_VISUAL_WIDGET_TYPES = {"audio", "timer", "touch-capture", "variable", "file-stream"}


def generate_agent_preview(
    scene_path: str | Path,
    out_dir: str | Path,
    *,
    target: str = CURRENT_TARGET,
    page_id: str | None = None,
) -> dict[str, Any]:
    """Generate a read-only preview bundle intended for humans and agents."""
    source_path = Path(scene_path).resolve()
    output_dir = Path(out_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    scene = load_scene(source_path)
    effective_page_id = _resolve_preview_page_id(scene, page_id)
    preview_path = render_scene_preview(scene, output_dir / "preview.png", page_id=effective_page_id)
    normalized_path = save_scene_json(scene, output_dir / "scene.normalized.json")
    project = _scene_project_context(scene)
    pages = _scene_pages_context(scene)
    assets = _scene_assets_context(scene)
    widgets = _flatten_widgets(scene)
    events = collect_scene_event_slots(scene, include_empty=False)
    event_analysis = analyze_scene_events(scene)
    target_status = target_status_summary()
    diagnostics = _diagnose_scene(scene, widgets)
    annotated_path = _render_annotated_preview(preview_path, output_dir / "preview.annotated.png", widgets, page_id=effective_page_id)
    context_path = output_dir / "agent_context.json"
    capability_report_path = output_dir / "capability_report.json"
    editor_audit_path = output_dir / "editor_audit.json"
    target_status_path = output_dir / "target_status.json"
    diagnostics_path = output_dir / "diagnostics.json"
    build_manifest_path = output_dir / "build_manifest.json"
    event_snippets_path = output_dir / "event_snippets.json"
    scenario_template_path = output_dir / "scenario.template.yaml"
    safe_commands = [
        f'python -m usarthmi --json scene save-as "{source_path}" "{source_path.with_name(source_path.stem + "_copy" + source_path.suffix)}"',
        f'python -m usarthmi --json scene validate "{source_path}"',
        f'python -m usarthmi --json scene check "{source_path}" --out-dir "{output_dir}" --simulate-events',
        f'python -m usarthmi --json scene check "{source_path}" --out-dir "{output_dir}" --simulate-events --scenario "{scenario_template_path}"',
        f'python -m usarthmi --json scene smoke "{source_path}" --out "{output_dir}"',
        f'python -m usarthmi --json scene preview "{source_path}" --out "{preview_path}"',
        f'python -m usarthmi --json scene agent-preview "{source_path}" --out-dir "{output_dir}"',
        f'python -m usarthmi --json scene export "{source_path}" --out-dir "{output_dir}"',
        f'python -m usarthmi --json scene simulate "{source_path}" {effective_page_id}.<widget>.up --out-dir "{output_dir}"',
        f'python -m usarthmi --json scene scenario run "{source_path}" "<scenario.yaml>" --out-dir "{output_dir}"',
        f'python -m usarthmi --json scene events lint "{source_path}"',
        f'python -m usarthmi --json scene events graph "{source_path}"',
        f'python -m usarthmi --json scene events append-command "{source_path}" {effective_page_id}.<widget>.up --command vis --target <widget> --value 1',
        f'python -m usarthmi --json scene events commands list "{source_path}" {effective_page_id}.<widget>.up',
        f'python -m usarthmi --json scene events commands replace "{source_path}" {effective_page_id}.<widget>.up --index 0 --command page --target <page_id> --dry-run --simulate --out-dir "{output_dir}"',
        f'python -m usarthmi --json scene project update "{source_path}" --name "<project>" --default-page {effective_page_id}',
        f'python -m usarthmi --json scene pages update "{source_path}" {effective_page_id} --id <new_page_id>',
        f'python -m usarthmi --json scene widgets update "{source_path}" {effective_page_id}.<widget> --x <x> --y <y>',
        f'python -m usarthmi --json scene design move "{source_path}" {effective_page_id}.<widget> --x <x> --y <y> --out-dir "{output_dir}"',
        f'python -m usarthmi --json scene design resize "{source_path}" {effective_page_id}.<widget> --w <w> --h <h> --out-dir "{output_dir}"',
        f'python -m usarthmi --json scene design align "{source_path}" {effective_page_id}.<widget_a> {effective_page_id}.<widget_b> --edge left --anchor first --out-dir "{output_dir}"',
        f'python -m usarthmi --json scene design distribute "{source_path}" {effective_page_id}.<widget_a> {effective_page_id}.<widget_b> {effective_page_id}.<widget_c> --axis horizontal --out-dir "{output_dir}"',
        f'python -m usarthmi --json scene design match-size "{source_path}" {effective_page_id}.<widget_a> {effective_page_id}.<widget_b> --mode width --anchor first --out-dir "{output_dir}"',
        "python -m usarthmi --json widgets template <widget_type> --id <widget_id> --x <x> --y <y>",
        "python -m usarthmi --json editor capabilities",
        "python -m usarthmi --json editor audit",
        "python -m usarthmi --json target summary",
        "python -m usarthmi --json target audit",
        "python -m usarthmi --json target calibration",
        "python -m usarthmi --json target next-probe",
        'python -m usarthmi --json target run-next-probe --result-json "reverse_usarthmi\\next_probe\\run_next_probe_result.json"',
        f'python -m usarthmi --json scene widgets cut "{source_path}" {effective_page_id}.<widget>',
        f'python -m usarthmi --json scene widgets copy-to "{source_path}" {effective_page_id}.<widget> {effective_page_id} --id <new_id>',
        f'python -m usarthmi --json scene widgets duplicate "{source_path}" {effective_page_id}.<widget> --id <new_id>',
        f'python -m usarthmi --json scene widgets move "{source_path}" {effective_page_id}.<widget> --direction up',
        f'python -m usarthmi --json scene pages add "{source_path}" page1',
        f'python -m usarthmi --json scene assets list "{source_path}"',
        "python -m usarthmi --json capabilities --include-aliases",
    ]
    dangerous_commands = [
        {
            "command": "python -m usarthmi --json tft upload --file <output.tft> --port COM36 --progress",
            "reason": "writes to the physical panel over serial",
        }
    ]
    context = {
        "schema_version": AGENT_PREVIEW_SCHEMA_VERSION,
        "tool": {"name": "usarthmi", "version": __version__},
        "input": {
            "scene_path": str(source_path),
            "scene_sha256": _sha256_file(source_path),
            "target": target,
            "page_id": effective_page_id,
        },
        "outputs": {
            "preview_png": str(preview_path),
            "annotated_preview_png": str(annotated_path),
            "normalized_scene_json": str(normalized_path),
            "agent_context_json": str(context_path),
            "capability_report_json": str(capability_report_path),
            "editor_audit_json": str(editor_audit_path),
            "target_status_json": str(target_status_path),
            "diagnostics_json": str(diagnostics_path),
            "build_manifest_json": str(build_manifest_path),
            "event_snippets_json": str(event_snippets_path),
            "scenario_template_yaml": str(scenario_template_path),
        },
        "canvas": {
            "width": int(scene.canvas["width"]),
            "height": int(scene.canvas["height"]),
            "background_color": int(scene.canvas.get("background_color", 65535)),
        },
        "project": project,
        "pages": pages,
        "assets": assets,
        "widgets": widgets,
        "events": events,
        "event_summary": event_analysis["event_summary"],
        "navigation_graph": event_analysis["navigation_graph"],
        "event_diagnostics": event_analysis["diagnostics"],
        "event_capabilities": event_analysis["event_capabilities"],
        "event_model": event_model_manifest(),
        "editor_capabilities": editor_capability_manifest(),
        "target_status": target_status,
        "diagnostics": [*diagnostics, *event_analysis["diagnostics"]],
        "agent_interface": {
            "contract": "Agents edit the scene/project file and call headless commands; the desktop GUI is not the automation surface.",
            "editable_inputs": [str(source_path)],
            "readable_outputs": {
                "preview": str(preview_path),
                "annotated_preview": str(annotated_path),
                "context": str(context_path),
                "diagnostics": str(diagnostics_path),
                "capabilities": str(capability_report_path),
                "editor_audit": str(editor_audit_path),
                "target_status": str(target_status_path),
                "manifest": str(build_manifest_path),
                "event_snippets": str(event_snippets_path),
            },
            "safe_commands": safe_commands,
            "dangerous_commands": dangerous_commands,
            "project_editing": {
                "new": f'python -m usarthmi --json scene new "<scene.json>" --name "<project>" --width 800 --height 480',
                "save_as": f'python -m usarthmi --json scene save-as "{source_path}" "<copy.json>"',
                "update": f'python -m usarthmi --json scene project update "{source_path}" --name "<project>" --default-page {effective_page_id} --width 800 --height 480',
            },
            "scene_checking": {
                "check": f'python -m usarthmi --json scene check "{source_path}" --out-dir "{output_dir}"',
                "check_with_event_simulation": f'python -m usarthmi --json scene check "{source_path}" --out-dir "{output_dir}" --simulate-events',
                "check_with_scenario": f'python -m usarthmi --json scene check "{source_path}" --out-dir "{output_dir}" --simulate-events --scenario "{scenario_template_path}"',
                "scene_smoke": f'python -m usarthmi --json scene smoke "{source_path}" --out "{output_dir}"',
            },
            "target_status": {
                "summary": "python -m usarthmi --json target summary",
                "audit": "python -m usarthmi --json target audit",
                "calibration": "python -m usarthmi --json target calibration",
                "next_probe": "python -m usarthmi --json target next-probe",
                "run_next_probe_offline": 'python -m usarthmi --json target run-next-probe --result-json "reverse_usarthmi\\next_probe\\run_next_probe_result.json"',
                "summary_json": str(target_status_path),
            },
            "event_editing": {
                "list": f'python -m usarthmi --json scene events list "{source_path}" --non-empty',
                "lint": f'python -m usarthmi --json scene events lint "{source_path}"',
                "graph": f'python -m usarthmi --json scene events graph "{source_path}"',
                "snippets": 'python -m usarthmi --json scene events snippets',
                "simulate": f'python -m usarthmi --json scene simulate "{source_path}" {effective_page_id}.<widget>.up --out-dir "{output_dir}"',
                "scenario_run": f'python -m usarthmi --json scene scenario run "{source_path}" "{scenario_template_path}" --out-dir "{output_dir}"',
                "get": f'python -m usarthmi --json scene events get "{source_path}" {effective_page_id}.<widget>.<event>',
                "set": f'python -m usarthmi --json scene events set "{source_path}" {effective_page_id}.<widget>.<event> --line "<code>"',
                "set_from_file": f'python -m usarthmi --json scene events set "{source_path}" {effective_page_id}.<widget>.<event> --from-file <event.txt>',
                "append_command": f'python -m usarthmi --json scene events append-command "{source_path}" {effective_page_id}.<widget>.<event> --command vis --target <widget> --value 1',
                "commands_list": f'python -m usarthmi --json scene events commands list "{source_path}" {effective_page_id}.<widget>.<event>',
                "commands_insert": f'python -m usarthmi --json scene events commands insert "{source_path}" {effective_page_id}.<widget>.<event> --index 0 --command vis --target <widget> --value 1 --dry-run --simulate --out-dir "{output_dir}"',
                "commands_replace": f'python -m usarthmi --json scene events commands replace "{source_path}" {effective_page_id}.<widget>.<event> --index 0 --command page --target <page_id> --dry-run --simulate --out-dir "{output_dir}"',
                "commands_delete": f'python -m usarthmi --json scene events commands delete "{source_path}" {effective_page_id}.<widget>.<event> --index 0 --dry-run --simulate --out-dir "{output_dir}"',
                "commands_move": f'python -m usarthmi --json scene events commands move "{source_path}" {effective_page_id}.<widget>.<event> --from-index 1 --to-index 0 --dry-run --simulate --out-dir "{output_dir}"',
                "clear": f'python -m usarthmi --json scene events clear "{source_path}" {effective_page_id}.<widget>.<event>',
            },
            "widget_editing": {
                "update": f'python -m usarthmi --json scene widgets update "{source_path}" {effective_page_id}.<widget> --x <x> --y <y> --text "<text>"',
                "rename_with_event_rewrite": f'python -m usarthmi --json scene widgets update "{source_path}" {effective_page_id}.<widget> --id <new_widget_id> --rewrite-event-references',
                "design_move": f'python -m usarthmi --json scene design move "{source_path}" {effective_page_id}.<widget> --x <x> --y <y> --out-dir "{output_dir}"',
                "design_resize": f'python -m usarthmi --json scene design resize "{source_path}" {effective_page_id}.<widget> --w <w> --h <h> --out-dir "{output_dir}"',
                "design_align": f'python -m usarthmi --json scene design align "{source_path}" {effective_page_id}.<widget_a> {effective_page_id}.<widget_b> --edge left --anchor first --out-dir "{output_dir}"',
                "design_distribute": f'python -m usarthmi --json scene design distribute "{source_path}" {effective_page_id}.<widget_a> {effective_page_id}.<widget_b> {effective_page_id}.<widget_c> --axis horizontal --out-dir "{output_dir}"',
                "design_match_size": f'python -m usarthmi --json scene design match-size "{source_path}" {effective_page_id}.<widget_a> {effective_page_id}.<widget_b> --mode width --anchor first --out-dir "{output_dir}"',
                "replay_agent_patch": f'python -m usarthmi --json scene design replay "{source_path}" "{output_dir / "agent_patch.json"}" --out-dir "{output_dir}"',
                "template": "python -m usarthmi --json widgets template <widget_type> --id <widget_id> --x <x> --y <y>",
                "copy": f'python -m usarthmi --json scene widgets copy "{source_path}" {effective_page_id}.<widget>',
                "cut": f'python -m usarthmi --json scene widgets cut "{source_path}" {effective_page_id}.<widget>',
                "paste": f'python -m usarthmi --json scene widgets paste "{source_path}" {effective_page_id} --from-file <widget_clipboard.json>',
                "copy_to": f'python -m usarthmi --json scene widgets copy-to "{source_path}" {effective_page_id}.<widget> {effective_page_id} --id <new_id>',
                "duplicate": f'python -m usarthmi --json scene widgets duplicate "{source_path}" {effective_page_id}.<widget> --id <new_id>',
                "move": f'python -m usarthmi --json scene widgets move "{source_path}" {effective_page_id}.<widget> --direction up',
                "delete": f'python -m usarthmi --json scene widgets delete "{source_path}" {effective_page_id}.<widget>',
            },
            "page_editing": {
                "add": f'python -m usarthmi --json scene pages add "{source_path}" page1',
                "duplicate": f'python -m usarthmi --json scene pages duplicate "{source_path}" page0 --id page1',
                "update": f'python -m usarthmi --json scene pages update "{source_path}" {effective_page_id} --id <new_page_id> --layout-json "{{\\"type\\":\\"absolute\\"}}"',
                "delete": f'python -m usarthmi --json scene pages delete "{source_path}" page1',
            },
            "asset_editing": {
                "list": f'python -m usarthmi --json scene assets list "{source_path}"',
                "add": f'python -m usarthmi --json scene assets add "{source_path}" asset0 --source <image-path>',
                "update": f'python -m usarthmi --json scene assets update "{source_path}" asset0 --source <image-path>',
                "delete": f'python -m usarthmi --json scene assets delete "{source_path}" asset0 --force',
            },
        },
        "hardware_policy": {
            "allow_upload": False,
            "allow_readback": True,
            "require_manual_confirm": True,
            "default_port": "COM36",
            "upload_requires_explicit_user_request": True,
        },
        "safe_commands": safe_commands,
        "dangerous_commands": dangerous_commands,
        "not_claimed": [
            "preview output is not live panel evidence",
            "agent-preview does not build or upload a TFT",
            "agent-preview does not prove runtime behavior",
            "event_summary is scene-source analysis, not complete official event bytecode proof",
            "normalized scene output is a helper artifact, not a byte-perfect official editor oracle",
        ],
    }
    capability_report = _build_capability_report(widgets)
    diagnostics_path.write_text(json.dumps(context["diagnostics"], ensure_ascii=False, indent=2), encoding="utf-8")
    capability_report_path.write_text(json.dumps(capability_report, ensure_ascii=False, indent=2), encoding="utf-8")
    editor_audit_path.write_text(json.dumps(editor_completion_audit(), ensure_ascii=False, indent=2), encoding="utf-8")
    target_status_path.write_text(json.dumps(target_status, ensure_ascii=False, indent=2), encoding="utf-8")
    event_snippets_path.write_text(json.dumps(list_event_command_snippets(), ensure_ascii=False, indent=2), encoding="utf-8")
    scenario_template_path.write_text(_scenario_template(scene, effective_page_id), encoding="utf-8")
    build_manifest_path.write_text(
        json.dumps(_build_manifest(context, capability_report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    context_path.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    return context


def _build_capability_report(widgets: list[dict[str, Any]]) -> dict[str, Any]:
    by_support: dict[str, int] = {}
    by_writer: dict[str, int] = {}
    used_types: dict[str, dict[str, Any]] = {}
    for widget in widgets:
        capability = widget.get("capability", {})
        support = str(capability.get("support", "unknown"))
        writer = str(capability.get("writer", "none"))
        by_support[support] = by_support.get(support, 0) + 1
        by_writer[writer] = by_writer.get(writer, 0) + 1
        used_types.setdefault(
            widget["type"],
            {
                "type": widget["type"],
                "support": support,
                "writer": writer,
                "build_scope": capability.get("build_scope"),
                "not_claimed": capability.get("not_claimed") or [],
                "widget_ids": [],
            },
        )["widget_ids"].append(widget["id"])
    return {
        "target": CURRENT_TARGET,
        "widgets_total": len(widgets),
        "by_support": by_support,
        "by_writer": by_writer,
        "used_types": sorted(used_types.values(), key=lambda item: item["type"]),
        "registry": widget_capability_manifest(include_aliases=True),
    }


def _scenario_template(scene: SceneModel, page_id: str) -> str:
    for slot in collect_scene_event_slots(scene, include_empty=False):
        event_path = slot.get("path")
        if isinstance(event_path, str) and event_path:
            return (
                "# Agent-editable offline scenario. This does not upload or prove hardware behavior.\n"
                "name: smoke_event\n"
                f"initial_page: {page_id}\n"
                "steps:\n"
                f"  - trigger: {event_path}\n"
            )
    return (
        "# Replace <widget> with a real object id before running this scenario.\n"
        "name: smoke_navigation\n"
        f"initial_page: {page_id}\n"
        "steps:\n"
        f"  - trigger: {page_id}.<widget>.up\n"
        "  - assert:\n"
        f"      current_page: {page_id}\n"
        "      widgets:\n"
        f"        {page_id}.<widget>.visible: true\n"
    )


def _build_manifest(context: dict[str, Any], capability_report: dict[str, Any]) -> dict[str, Any]:
    diagnostics = context["diagnostics"]
    severe = [item for item in diagnostics if item.get("severity") in {"error", "warning"}]
    limited_claim_types = [
        item
        for item in capability_report["used_types"]
        if item.get("build_scope") is not None or item.get("not_claimed")
    ]
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "tool": context["tool"],
        "target": context["input"]["target"],
        "target_status": context["target_status"],
        "input": context["input"],
        "outputs": context["outputs"],
        "canvas": context["canvas"],
        "project": context["project"],
        "page_count": len(context.get("pages", [])),
        "widget_count": capability_report["widgets_total"],
        "asset_count": len(context.get("assets", [])),
        "event_count": len(context.get("events", [])),
        "capability_summary": {
            "by_support": capability_report["by_support"],
            "by_writer": capability_report["by_writer"],
            "limited_claim_types": limited_claim_types,
        },
        "diagnostic_summary": {
            "total": len(diagnostics),
            "errors_or_warnings": len(severe),
        },
        "safe_to_flash": False,
        "safety_reason": "agent-preview is an offline artifact bundle; physical upload is a separate explicit operation.",
        "hardware_policy": context["hardware_policy"],
    }


def _scene_assets_context(scene: SceneModel) -> list[dict[str, Any]]:
    return [
        {
            "key": key,
            "id": asset.id,
            "source": asset.source,
            "normal": asset.normal,
            "pressed": asset.pressed,
            "disabled": asset.disabled,
        }
        for key, asset in scene.assets.items()
    ]


def _resolve_preview_page_id(scene: SceneModel, page_id: str | None) -> str:
    if page_id:
        return page_id
    default_page = scene.project.get("default_page")
    if isinstance(default_page, str) and default_page:
        return default_page
    return scene.pages[0].id


def _scene_project_context(scene: SceneModel) -> dict[str, Any]:
    return {
        key: value
        for key, value in scene.project.items()
        if not str(key).startswith("_")
    }


def _scene_pages_context(scene: SceneModel) -> list[dict[str, Any]]:
    default_page = scene.project.get("default_page")
    return [
        {
            "index": index,
            "id": page.id,
            "layout": dict(page.layout),
            "is_default": page.id == default_page,
            "event_count": sum(1 for lines in page.events.values() if lines),
            "widget_count": len(page.widgets),
        }
        for index, page in enumerate(scene.pages)
    ]


def _flatten_widgets(scene: SceneModel) -> list[dict[str, Any]]:
    width = int(scene.canvas["width"])
    height = int(scene.canvas["height"])
    flattened: list[dict[str, Any]] = []
    for page_index, page in enumerate(scene.pages):
        widgets = resolve_page_layout(page.widgets, page.layout, width, height)
        for z_index, widget in enumerate(widgets):
            capability = _widget_capability(widget)
            flattened.append(
                {
                    "page": page.id,
                    "page_index": page_index,
                    "z_index": z_index,
                    "id": widget.id,
                    "type": widget.type,
                    "bbox": _bbox(widget),
                    "text": widget.text,
                    "value": widget.value,
                    "style": dict(widget.style),
                    "resources": dict(widget.resources),
                    "bindings": dict(widget.bindings),
                    "events": {key: list(lines) for key, lines in widget.events.items()},
                    "capability": capability,
                    "writer_available": capability.get("writer") in {WidgetWriter.BUILT_IN.value, WidgetWriter.FIXTURE.value},
                    "warnings": _widget_warnings(widget, capability, width, height, scene.assets),
                }
            )
    return flattened


def _widget_capability(widget: WidgetSpec) -> dict[str, Any]:
    info = get_widget_type_info(widget.type)
    if info is None:
        return {
            "support": "unknown",
            "writer": "none",
            "reason": "widget type is not registered",
        }
    return info.to_dict(include_aliases=True)


def _widget_warnings(
    widget: WidgetSpec,
    capability: dict[str, Any],
    canvas_width: int,
    canvas_height: int,
    scene_assets: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []
    if capability.get("support") != WidgetSupport.SUPPORTED.value:
        warnings.append(f"capability status is {capability.get('support')}")
    x, y, w, h = _bbox(widget)
    if widget.type not in NON_VISUAL_WIDGET_TYPES and (w <= 0 or h <= 0):
        warnings.append("visual widget has non-positive geometry")
    if w > 0 and h > 0 and (x < 0 or y < 0 or x + w > canvas_width or y + h > canvas_height):
        warnings.append("widget extends beyond canvas")
    asset_ref = widget.resources.get("asset")
    if asset_ref is not None and asset_ref not in scene_assets:
        warnings.append("asset reference is missing from scene assets")
    return warnings


def _diagnose_scene(scene: SceneModel, widgets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    page_matches: dict[str, int] = {}
    for page in scene.pages:
        page_matches[page.id] = page_matches.get(page.id, 0) + 1
    for page_id, count in page_matches.items():
        if count > 1:
            diagnostics.append(
                {
                    "severity": "error",
                    "code": "DUPLICATE_PAGE_ID",
                    "message": f"Page id {page_id!r} appears {count} times",
                    "pages": [page_id],
                }
            )
    default_page = scene.project.get("default_page")
    if default_page and default_page not in page_matches:
        diagnostics.append(
            {
                "severity": "error",
                "code": "MISSING_DEFAULT_PAGE",
                "message": f"project.default_page {default_page!r} does not match any scene page",
                "pages": [default_page],
            }
        )
    ids: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for widget in widgets:
        ids.setdefault((widget["page"], widget["id"]), []).append(widget)
    for (page, widget_id), matches in ids.items():
        if len(matches) > 1:
            diagnostics.append(
                {
                    "severity": "error",
                    "code": "DUPLICATE_WIDGET_ID",
                    "message": f"Widget id {widget_id!r} appears {len(matches)} times on {page}",
                    "widgets": [widget_id],
                }
            )

    width = int(scene.canvas["width"])
    height = int(scene.canvas["height"])
    for widget in widgets:
        x, y, w, h = widget["bbox"]
        if widget["type"] not in NON_VISUAL_WIDGET_TYPES and (w <= 0 or h <= 0):
            diagnostics.append(
                {
                    "severity": "warning",
                    "code": "NON_POSITIVE_GEOMETRY",
                    "message": f"Visual widget {widget['id']!r} has non-positive geometry",
                    "widgets": [widget["id"]],
                }
            )
        if w > 0 and h > 0 and (x < 0 or y < 0 or x + w > width or y + h > height):
            diagnostics.append(
                {
                    "severity": "warning",
                    "code": "OFF_CANVAS",
                    "message": f"Widget {widget['id']!r} extends beyond the {width}x{height} canvas",
                    "widgets": [widget["id"]],
                }
            )
        support = widget.get("capability", {}).get("support")
        if support == WidgetSupport.PENDING.value:
            capability = widget.get("capability", {})
            if capability.get("writer") == WidgetWriter.FIXTURE.value and capability.get("build_scope") == "hmi-only":
                diagnostics.append(
                    {
                        "severity": "warning",
                        "code": "FIXTURE_BACKED_HMI_ONLY_WIDGET",
                        "message": (
                            f"Widget {widget['id']!r} is fixture-backed HMI-only; "
                            "direct TFT rebuild and live behavior are not claimed"
                        ),
                        "widgets": [widget["id"]],
                    }
                )
                continue
            diagnostics.append(
                {
                    "severity": "warning",
                    "code": "PENDING_WIDGET_WRITER",
                    "message": f"Widget {widget['id']!r} uses a local writer with incomplete claim coverage",
                    "widgets": [widget["id"]],
                }
            )
        elif support == WidgetSupport.UNSUPPORTED_CURRENT_TARGET.value:
            diagnostics.append(
                {
                    "severity": "error",
                    "code": "UNSUPPORTED_CURRENT_TARGET_WIDGET",
                    "message": f"Widget {widget['id']!r} is unsupported for the current target",
                    "widgets": [widget["id"]],
                }
            )

    for left_index, left in enumerate(widgets):
        if _is_non_overlap_candidate(left):
            continue
        for right in widgets[left_index + 1 :]:
            if left["page"] != right["page"] or _is_non_overlap_candidate(right):
                continue
            if _overlaps(left["bbox"], right["bbox"]):
                diagnostics.append(
                    {
                        "severity": "info",
                        "code": "OVERLAP",
                        "message": f"Widgets {left['id']!r} and {right['id']!r} overlap",
                        "widgets": [left["id"], right["id"]],
                    }
                )
    return diagnostics


def _render_annotated_preview(
    preview_path: Path,
    out_path: Path,
    widgets: list[dict[str, Any]],
    *,
    page_id: str,
) -> Path:
    image = Image.open(preview_path).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = ImageFont.load_default()
    for index, widget in enumerate(item for item in widgets if item["page"] == page_id):
        x, y, w, h = widget["bbox"]
        if w <= 0 or h <= 0:
            continue
        color = (200, 48, 48, 230) if widget["warnings"] else (28, 96, 145, 210)
        draw.rectangle((x, y, x + w, y + h), outline=color, width=2)
        label = f"{index}:{widget['id']} {widget['type']}"
        label_box = draw.textbbox((0, 0), label, font=font)
        label_w = label_box[2] - label_box[0] + 6
        label_h = label_box[3] - label_box[1] + 4
        label_x = max(min(x, image.width - label_w), 0)
        label_y = max(y - label_h, 0)
        draw.rectangle((label_x, label_y, label_x + label_w, label_y + label_h), fill=(255, 255, 255, 220))
        draw.text((label_x + 3, label_y + 2), label, fill=color, font=font)
    target = Path(out_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.alpha_composite(image, overlay).convert("RGB").save(target)
    return target


def _bbox(widget: WidgetSpec | dict[str, Any]) -> list[int]:
    if isinstance(widget, dict):
        return [int(value) for value in widget["bbox"]]
    return [int(widget.x or 0), int(widget.y or 0), int(widget.w or 0), int(widget.h or 0)]


def _is_non_overlap_candidate(widget: dict[str, Any]) -> bool:
    x, y, w, h = widget["bbox"]
    if w <= 0 or h <= 0 or widget["type"] in NON_VISUAL_WIDGET_TYPES:
        return True
    return widget["type"] == "text" and not widget.get("text") and widget["id"].startswith(("panel", "bg", "topbar"))


def _overlaps(left: list[int], right: list[int]) -> bool:
    lx, ly, lw, lh = left
    rx, ry, rw, rh = right
    return lx < rx + rw and lx + lw > rx and ly < ry + rh and ly + lh > ry


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()
