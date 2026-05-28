from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from . import __version__
from .api import (
    check_next_probe_invariants,
    generate_agent_preview,
    get_builder_calibration_status,
    get_capability_manifest,
    get_current_target_completion_audit,
    get_current_target_status_summary,
    get_next_live_probe_bundle,
    get_page1_filebrowser_frontier_report,
    get_page1_filebrowser_native_init_compare_targets_report,
    get_widget_capability,
    list_widget_capabilities,
    run_next_live_probe,
)
from .design_ops import (
    design_align_widgets,
    design_distribute_widgets,
    design_match_size_widgets,
    design_move_widget,
    design_resize_widget,
    replay_agent_patch,
)
from .editor import EditorError, build_scene, import_asset
from .editor_capabilities import editor_capability_manifest, editor_completion_audit
from .event_logic import graph_scene_events, lint_scene_events, list_event_command_snippets
from .event_simulator import simulate_scene_event
from .export_bundle import export_scene_bundle
from .font_toolchain import (
    FontToolchainError,
    collect_scene_text,
    ensure_zicli_built,
    generate_zi,
    generate_zi_from_scene,
    replace_hmi_font,
)
from .hmi_inspect import HMIParseError, extract_hmi, inspect_hmi
from .hmi_import import import_hmi_project
from .hmi_donor_patch import generate_lowlevel_compatible_fixture, generate_reopen_safe_fixture, patch_hmi_donor
from .hmi_roundtrip import check_hmi_roundtrip
from .object_hash import OBJECT_NAME_HASH_WIDTH, object_name_hash
from .preview import render_hmi_preview, render_pa_preview, render_scene_preview
from .protocol import (
    ProtocolError,
    build_click,
    build_dim,
    build_get,
    build_page,
    build_raw,
    build_ref,
    build_set,
    build_tsw,
    build_vis,
    parse_response,
)
from .runtime_preview import build_scene_runtime_commands, push_scene_runtime_preview
from .sd_recovery_guard import pending_sd_recovery_reason
from .scene import SceneError, WidgetSpec, load_scene, save_scene_json, validate_scene
from .scene_check import check_scene_project
from .scenario_runner import run_scene_scenario
from .scene_edit import (
    add_scene_asset,
    add_scene_page,
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
from .scene_smoke import build_scene_smoke_parser, run_scene_smoke
from .serial_health import probe_serial_health
from .tft_download import (
    DEFAULT_DOWNLOAD_BAUD,
    DEFAULT_LAST_UPLOAD_MANIFEST,
    PUBLIC_WHMI_CHUNK_SIZE,
    evaluate_skip_if_current,
    plan_upload,
    upload_tft,
    write_last_upload_manifest,
)
from .tft_case_diff import compare_case_folder
from .tft_checksum import inspect_tft_checksum
from .tft_font_pack import TftFontPackError, inspect_tft_font_run, pack_tft_font_run
from .tft_fonts import patch_tft_font
from .tft_hmisafe import diff_bytes as diff_hmisafe_bytes
from .tft_hmisafe import HmiSafeUnsupportedModeError, finalize_tft_file, verify_final_tft_file
from .tft_event_index import inspect_tft_event_index, inspect_tft_event_index_batch
from .tft_patch import patch_added_object_tft, patch_basic_tft, patch_rebuild_page_tft
from .tft_reverse import reverse_tft_tail
from .tft_toolchain import TftToolchainError, inspect_tft, list_supported_tft_models
from .transport import SerialConfig, SerialTransport, SerialTransportError
from .widget_templates import get_widget_template, list_widget_templates
from .widgets import WidgetSupport


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not getattr(args, "command", None):
        parser.print_help()
        return 1

    try:
        if args.command in {
            "raw",
            "connect",
            "sendme",
            "get",
            "set",
            "page",
            "ref",
            "vis",
            "tsw",
            "click",
            "dim",
        }:
            result = _handle_serial_command(args)
        elif args.command == "inspect-hmi":
            result = _handle_inspect_hmi(args)
        elif args.command == "extract-hmi":
            result = _handle_extract_hmi(args)
        elif args.command == "scene":
            result = _handle_scene_command(args)
        elif args.command == "font":
            result = _handle_font_command(args)
        elif args.command == "hmi":
            result = _handle_hmi_command(args)
        elif args.command == "tft":
            result = _handle_tft_command(args)
        elif args.command == "capabilities":
            result = _handle_capabilities_command(args)
        elif args.command == "widgets":
            result = _handle_widgets_command(args)
        elif args.command == "editor":
            result = _handle_editor_command(args)
        elif args.command == "target":
            result = _handle_target_command(args)
        else:
            parser.error(f"Unknown command: {args.command}")
            return 2
    except (
        ProtocolError,
        SerialTransportError,
        HMIParseError,
        FileNotFoundError,
        SceneError,
        EditorError,
        FontToolchainError,
        TftToolchainError,
        TftFontPackError,
        HmiSafeUnsupportedModeError,
    ) as exc:
        if getattr(args, "json", False):
            print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"ERROR: {exc}")
        return 2

    exit_code = 0
    if (
        getattr(args, "command", None) == "tft"
        and getattr(args, "tft_command", None) in {"health", "preflight", "readiness"}
        and not (
            result.get("summary", {}).get("healthy", False)
            if getattr(args, "tft_command", None) in {"health", "preflight"}
            else result.get("summary", {}).get("ready_for_live_upload", False)
        )
    ):
        exit_code = 1
    if (
        getattr(args, "command", None) == "tft"
        and getattr(args, "tft_command", None) == "upload"
        and result.get("post_upload_verification", {}).get("summary", {}).get("ok") is False
    ):
        exit_code = 1
    if (
        getattr(args, "command", None) == "target"
        and getattr(args, "target_command", None) in {"run-next-probe", "check-next-probe"}
        and result.get("summary", {}).get("ok") is False
    ):
        exit_code = 1

    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human_result(args.command, result)
    return exit_code


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="usarthmi", description="USART HMI CLI")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose transport logs")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")
    serial_parent = argparse.ArgumentParser(add_help=False)
    serial_parent.add_argument("--port", required=True, help="Serial port, for example COM36")
    serial_parent.add_argument("--baud", type=int, default=9600, help="Serial baud rate")
    serial_parent.add_argument(
        "--timeout-ms", type=int, default=800, help="Read timeout in milliseconds"
    )

    raw_parser = subparsers.add_parser("raw", parents=[serial_parent], help="Send a raw command")
    raw_parser.add_argument("raw_command", help='Raw command text, for example "get dim"')

    subparsers.add_parser("connect", parents=[serial_parent], help="Send connect")
    subparsers.add_parser("sendme", parents=[serial_parent], help="Send sendme")

    get_parser = subparsers.add_parser("get", parents=[serial_parent], help="Read an attribute")
    get_parser.add_argument("target", help="Attribute path, for example page0.bco")

    set_parser = subparsers.add_parser("set", parents=[serial_parent], help="Write an attribute")
    set_parser.add_argument("target", help="Attribute path, for example page0.bco")
    set_parser.add_argument("value", help="Value to assign")

    page_parser = subparsers.add_parser("page", parents=[serial_parent], help="Switch page")
    page_parser.add_argument("page_id", help="Page id or page name")

    ref_parser = subparsers.add_parser("ref", parents=[serial_parent], help="Refresh object")
    ref_parser.add_argument("object_name", help="Object id/name")

    vis_parser = subparsers.add_parser("vis", parents=[serial_parent], help="Show/hide object")
    vis_parser.add_argument("object_name", help="Object id/name")
    vis_parser.add_argument("state", help="0 or 1")

    tsw_parser = subparsers.add_parser("tsw", parents=[serial_parent], help="Enable/disable touch")
    tsw_parser.add_argument("object_name", help="Object id/name")
    tsw_parser.add_argument("state", help="0 or 1")

    click_parser = subparsers.add_parser("click", parents=[serial_parent], help="Trigger click event")
    click_parser.add_argument("object_name", help="Object id/name")
    click_parser.add_argument("event", help="down/up or 1/0")

    dim_parser = subparsers.add_parser("dim", parents=[serial_parent], help="Set backlight")
    dim_parser.add_argument("value", help="Backlight value")

    inspect_parser = subparsers.add_parser("inspect-hmi", help="Inspect an HMI container")
    inspect_parser.add_argument("path", help="Path to .HMI file")

    extract_parser = subparsers.add_parser("extract-hmi", help="Extract HMI resources")
    extract_parser.add_argument("path", help="Path to .HMI file")
    extract_parser.add_argument("--out", required=True, help="Extraction directory")

    scene_parser = subparsers.add_parser("scene", help="Scene file operations")
    scene_sub = scene_parser.add_subparsers(dest="scene_command")
    scene_new = scene_sub.add_parser("new", help="Create a new empty scene JSON/YAML")
    scene_new.add_argument("scene_path", help="Scene path to create")
    scene_new.add_argument("--name", help="Project name; defaults to the file stem")
    scene_new.add_argument("--width", type=int, default=800, help="Canvas width")
    scene_new.add_argument("--height", type=int, default=480, help="Canvas height")
    scene_new.add_argument("--background-color", type=int, default=65535, help="Canvas background color")
    scene_new.add_argument("--page", default="page0", help="Default page id")
    scene_new.add_argument("--overwrite", action="store_true", help="Overwrite an existing scene file")
    scene_save_as = scene_sub.add_parser("save-as", help="Validate and save a scene under a new path")
    scene_save_as.add_argument("scene_path", help="Source scene JSON/YAML file")
    scene_save_as.add_argument("out", help="Destination scene JSON/YAML file")
    scene_save_as.add_argument("--overwrite", action="store_true", help="Overwrite an existing destination")
    scene_project = scene_sub.add_parser("project", help="Manage scene project and canvas settings")
    scene_project_sub = scene_project.add_subparsers(dest="scene_project_command")
    scene_project_update = scene_project_sub.add_parser("update", help="Update project metadata and canvas settings")
    scene_project_update.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_project_update.add_argument("--name", help="Project name")
    scene_project_update.add_argument("--default-page", help="Default page id")
    scene_project_update.add_argument("--width", type=int, help="Canvas width")
    scene_project_update.add_argument("--height", type=int, help="Canvas height")
    scene_project_update.add_argument("--background-color", type=int, help="Canvas background color")
    scene_validate = scene_sub.add_parser("validate", help="Validate a scene JSON/YAML")
    scene_validate.add_argument("scene_path", help="Scene file path")
    scene_check = scene_sub.add_parser("check", help="Run an offline editor-style scene check report")
    scene_check.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_check.add_argument("--out-dir", help="Write scene_check_report.json to this directory")
    scene_check.add_argument("--target", default="TJC8048X543_011C", help="Target model name")
    scene_check.add_argument("--simulate-events", action="store_true", help="Offline-simulate non-empty event slots")
    scene_check.add_argument("--max-event-slots", type=int, default=50, help="Maximum non-empty event slots to simulate")
    scene_check.add_argument("--max-steps", type=int, default=128, help="Maximum event command lines per simulation")
    scene_check.add_argument("--scenario", action="append", default=[], help="Scenario YAML/JSON file to run; repeatable")
    scene_preview = scene_sub.add_parser("preview", help="Render a scene to a PNG preview")
    scene_preview.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_preview.add_argument("--out", required=True, help="Preview PNG path")
    scene_preview.add_argument("--page", default="page0", help="Page id")
    scene_preview.add_argument("--font", action="append", help="Preview .zi font path, optionally FONT_ID=path")
    scene_agent_preview = scene_sub.add_parser("agent-preview", help="Generate preview files and agent_context.json")
    scene_agent_preview.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_agent_preview.add_argument("--out-dir", required=True, help="Output directory for preview bundle")
    scene_agent_preview.add_argument("--target", default="TJC8048X543_011C", help="Target model name")
    scene_agent_preview.add_argument("--page", help="Page id; defaults to project.default_page")
    scene_push = scene_sub.add_parser("push-preview", help="Push a runtime preview of a scene to the serial screen")
    scene_push.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_push.add_argument("--port", required=True, help="Serial port, for example COM36")
    scene_push.add_argument("--baud", type=int, default=9600, help="Serial baud rate")
    scene_push.add_argument("--page", default="page0", help="Page id")
    scene_push.add_argument("--timeout-ms", type=int, default=800, help="Serial timeout in milliseconds")
    scene_push.add_argument("--delay-ms", type=int, default=70, help="Delay between drawing commands in milliseconds")
    scene_build = scene_sub.add_parser("build", help="Build a scene against a seed HMI")
    scene_build.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_build.add_argument("--seed", required=True, help="Seed HMI file")
    scene_build.add_argument("--out", required=True, help="Output directory")
    scene_build.add_argument("--baseline-tft", help="Optional baseline TFT used to emit output.tft")
    scene_build.add_argument("--font-zi", help="Optional .zi font to patch into output.hmi and output.tft")
    scene_build.add_argument("--font-entry", default="0.zi", help="HMI font entry to replace when --font-zi is used")
    scene_export = scene_sub.add_parser("export", help="Create an offline compile-style bundle and report")
    scene_export.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_export.add_argument("--out-dir", required=True, help="Output directory for preview/build/report artifacts")
    scene_export.add_argument("--seed", help="Optional seed HMI used to emit output.hmi")
    scene_export.add_argument("--baseline-tft", help="Optional baseline TFT used to emit output.tft")
    scene_export.add_argument("--font-zi", help="Optional .zi font to patch into output.hmi and output.tft")
    scene_export.add_argument("--font-entry", default="0.zi", help="HMI font entry to replace when --font-zi is used")
    scene_export.add_argument("--target", default="TJC8048X543_011C", help="Target model name")
    scene_smoke = scene_sub.add_parser("smoke", help="Build a scene and continue into readiness/preflight/live smoke")
    build_scene_smoke_parser(scene_smoke)
    scene_events = scene_sub.add_parser("events", help="List, read, and edit scene-level event scripts")
    scene_events_sub = scene_events.add_subparsers(dest="scene_events_command")
    scene_events_list = scene_events_sub.add_parser("list", help="List known event slots")
    scene_events_list.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_events_list.add_argument("--non-empty", action="store_true", help="Only return event slots that contain script lines")
    scene_events_lint = scene_events_sub.add_parser("lint", help="Analyze event commands and references")
    scene_events_lint.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_events_graph = scene_events_sub.add_parser("graph", help="Build a page-navigation graph from event code")
    scene_events_graph.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_events_sub.add_parser("snippets", help="List structured event command snippets")
    scene_events_get = scene_events_sub.add_parser("get", help="Read one event slot, e.g. page0.btn0.down")
    scene_events_get.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_events_get.add_argument("event_path", help="page.event or page.widget.event")
    scene_events_set = scene_events_sub.add_parser("set", help="Replace one event slot")
    scene_events_set.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_events_set.add_argument("event_path", help="page.event or page.widget.event")
    scene_events_set.add_argument("--line", action="append", default=[], help="Event source line; repeatable")
    scene_events_set.add_argument("--code", help="Multi-line event source text")
    scene_events_set.add_argument("--from-file", help="Read event source text from a file")
    scene_events_set.add_argument("--append", action="store_true", help="Append to the existing event instead of replacing")
    scene_events_append_command = scene_events_sub.add_parser(
        "append-command",
        help="Append one structured guarded command to an event slot",
    )
    scene_events_append_command.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_events_append_command.add_argument("event_path", help="page.event or page.widget.event")
    scene_events_append_command.add_argument(
        "--command",
        dest="event_command",
        required=True,
        choices=("page", "ref", "vis", "tsw", "click", "get", "set", "printh", "delay", "raw"),
        help="Structured event command family",
    )
    scene_events_append_command.add_argument("--target", help="Target page/object/attribute")
    scene_events_append_command.add_argument("--value", help="Command value, for example 0, 1, or text")
    scene_events_append_command.add_argument(
        "--op",
        default="=",
        choices=("=", "++", "--", "+=", "-="),
        help="Assignment operator used by --command set",
    )
    scene_events_append_command.add_argument(
        "--attribute",
        default="val",
        help="Attribute appended to --target for get/set when target has no dot",
    )
    scene_events_append_command.add_argument("--hex", dest="hex_bytes", help="Hex byte string for --command printh")
    scene_events_append_command.add_argument("--delay-ms", type=int, help="Delay in milliseconds for --command delay")
    scene_events_append_command.add_argument("--raw-line", help="Raw event line for --command raw")
    scene_events_append_command.add_argument("--dry-run", action="store_true", help="Build the line without modifying the scene")
    scene_events_commands = scene_events_sub.add_parser(
        "commands",
        help="List and patch individual event command lines",
    )
    scene_events_commands_sub = scene_events_commands.add_subparsers(dest="scene_event_commands_command")
    scene_events_commands_list = scene_events_commands_sub.add_parser("list", help="List parsed command lines in one event slot")
    scene_events_commands_list.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_events_commands_list.add_argument("event_path", help="page.event or page.widget.event")
    scene_events_commands_insert = scene_events_commands_sub.add_parser("insert", help="Insert one event command line")
    scene_events_commands_insert.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_events_commands_insert.add_argument("event_path", help="page.event or page.widget.event")
    scene_events_commands_insert.add_argument("--index", type=int, help="Insert before this zero-based line index; default appends")
    _add_scene_event_command_patch_args(scene_events_commands_insert)
    scene_events_commands_replace = scene_events_commands_sub.add_parser("replace", help="Replace one event command line")
    scene_events_commands_replace.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_events_commands_replace.add_argument("event_path", help="page.event or page.widget.event")
    scene_events_commands_replace.add_argument("--index", type=int, required=True, help="Zero-based line index to replace")
    _add_scene_event_command_patch_args(scene_events_commands_replace)
    scene_events_commands_delete = scene_events_commands_sub.add_parser("delete", help="Delete one event command line")
    scene_events_commands_delete.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_events_commands_delete.add_argument("event_path", help="page.event or page.widget.event")
    scene_events_commands_delete.add_argument("--index", type=int, required=True, help="Zero-based line index to delete")
    _add_scene_event_patch_common_args(scene_events_commands_delete)
    scene_events_commands_move = scene_events_commands_sub.add_parser("move", help="Move one event command line")
    scene_events_commands_move.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_events_commands_move.add_argument("event_path", help="page.event or page.widget.event")
    scene_events_commands_move.add_argument("--from-index", type=int, required=True, help="Zero-based line index to move")
    scene_events_commands_move.add_argument("--to-index", type=int, required=True, help="Zero-based destination index after removal")
    _add_scene_event_patch_common_args(scene_events_commands_move)
    scene_events_clear = scene_events_sub.add_parser("clear", help="Clear one event slot")
    scene_events_clear.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_events_clear.add_argument("event_path", help="page.event or page.widget.event")
    scene_simulate = scene_sub.add_parser("simulate", help="Run an offline simulation of one event slot")
    scene_simulate.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_simulate.add_argument("event_path", help="page.event or page.widget.event, for example page0.btn0.up")
    scene_simulate.add_argument("--out-dir", help="Write runtime_trace.json, runtime_state.json, and simulation_report.json")
    scene_simulate.add_argument("--initial-page", help="Initial runtime page; defaults to the triggered event's page")
    scene_simulate.add_argument("--max-steps", type=int, default=128, help="Maximum event command lines to execute")
    scene_scenario = scene_sub.add_parser("scenario", help="Run offline multi-step scene interaction scenarios")
    scene_scenario_sub = scene_scenario.add_subparsers(dest="scene_scenario_command")
    scene_scenario_run = scene_scenario_sub.add_parser("run", help="Run one YAML/JSON scenario file")
    scene_scenario_run.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_scenario_run.add_argument("scenario_path", help="Scenario YAML/JSON file")
    scene_scenario_run.add_argument("--out-dir", help="Write runtime_trace.json, runtime_state.json, and scenario_report.json")
    scene_scenario_run.add_argument("--initial-page", help="Initial runtime page; defaults to scenario or first trigger page")
    scene_scenario_run.add_argument("--max-steps", type=int, help="Maximum event command lines across all trigger steps")
    scene_assets = scene_sub.add_parser("assets", help="Manage scene assets without opening the GUI")
    scene_assets_sub = scene_assets.add_subparsers(dest="scene_assets_command")
    scene_assets_list = scene_assets_sub.add_parser("list", help="List scene assets")
    scene_assets_list.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_assets_add = scene_assets_sub.add_parser("add", help="Add one scene asset")
    scene_assets_add.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_assets_add.add_argument("asset_id", help="Asset key to add")
    _add_scene_asset_args(scene_assets_add)
    scene_assets_update = scene_assets_sub.add_parser("update", help="Update one scene asset")
    scene_assets_update.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_assets_update.add_argument("asset_id", help="Asset key to update")
    _add_scene_asset_args(scene_assets_update)
    scene_assets_delete = scene_assets_sub.add_parser("delete", help="Delete one scene asset")
    scene_assets_delete.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_assets_delete.add_argument("asset_id", help="Asset key to delete")
    scene_assets_delete.add_argument("--force", action="store_true", help="Delete even when widgets still reference this asset")
    scene_widgets = scene_sub.add_parser("widgets", help="Manage scene widgets without opening the GUI")
    scene_widgets_sub = scene_widgets.add_subparsers(dest="scene_widgets_command")
    scene_widgets_update = scene_widgets_sub.add_parser("update", help="Update one widget's scene properties")
    scene_widgets_update.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_widgets_update.add_argument("widget_path", help="page.widget, for example page0.btn0")
    scene_widgets_update.add_argument("--id", dest="new_id", help="Rename the widget")
    scene_widgets_update.add_argument("--type", dest="widget_type", help="Widget type or alias")
    scene_widgets_update.add_argument("--x", type=int, help="Widget x")
    scene_widgets_update.add_argument("--y", type=int, help="Widget y")
    scene_widgets_update.add_argument("--w", type=int, help="Widget width")
    scene_widgets_update.add_argument("--h", type=int, help="Widget height")
    scene_widgets_update.add_argument("--text", help="Widget text")
    scene_widgets_update.add_argument("--clear-text", action="store_true", help="Clear widget text")
    scene_widgets_update.add_argument("--value", type=int, help="Widget numeric value")
    scene_widgets_update.add_argument("--clear-value", action="store_true", help="Clear widget value")
    scene_widgets_update.add_argument("--style", action="append", help="Patch style key=value; null removes the key")
    scene_widgets_update.add_argument("--style-json", help="Replace style with a JSON object before --style patches")
    scene_widgets_update.add_argument("--resource", action="append", help="Patch resource key=value; null removes the key")
    scene_widgets_update.add_argument("--resources-json", help="Replace resources with a JSON object before --resource patches")
    scene_widgets_update.add_argument("--binding", action="append", help="Patch binding key=value; null removes the key")
    scene_widgets_update.add_argument("--bindings-json", help="Replace bindings with a JSON object before --binding patches")
    scene_widgets_update.add_argument(
        "--rewrite-event-references",
        action="store_true",
        help="When renaming the widget id, rewrite same-page event-script references to the old id",
    )
    scene_widgets_delete = scene_widgets_sub.add_parser("delete", help="Delete one widget, e.g. page0.btn0")
    scene_widgets_delete.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_widgets_delete.add_argument("widget_path", help="page.widget, for example page0.btn0")
    scene_widgets_duplicate = scene_widgets_sub.add_parser("duplicate", help="Duplicate one widget next to the original")
    scene_widgets_duplicate.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_widgets_duplicate.add_argument("widget_path", help="page.widget, for example page0.btn0")
    scene_widgets_duplicate.add_argument("--id", dest="new_id", help="New widget id; default is <id>_copy")
    scene_widgets_duplicate.add_argument("--offset-x", type=int, default=16, help="X offset applied to the duplicate")
    scene_widgets_duplicate.add_argument("--offset-y", type=int, default=16, help="Y offset applied to the duplicate")
    scene_widgets_copy = scene_widgets_sub.add_parser("copy", help="Return a widget clipboard payload without editing the scene")
    scene_widgets_copy.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_widgets_copy.add_argument("widget_path", help="page.widget, for example page0.btn0")
    scene_widgets_cut = scene_widgets_sub.add_parser("cut", help="Copy one widget to a clipboard payload and delete it")
    scene_widgets_cut.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_widgets_cut.add_argument("widget_path", help="page.widget, for example page0.btn0")
    scene_widgets_paste = scene_widgets_sub.add_parser("paste", help="Paste a widget clipboard payload into a page")
    scene_widgets_paste.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_widgets_paste.add_argument("page_id", help="Target page id")
    paste_source = scene_widgets_paste.add_mutually_exclusive_group(required=True)
    paste_source.add_argument("--widget-json", help="Widget JSON object or clipboard JSON object")
    paste_source.add_argument("--from-file", help="Read widget/clipboard JSON from a file")
    scene_widgets_paste.add_argument("--id", dest="new_id", help="New widget id")
    scene_widgets_paste.add_argument("--offset-x", type=int, default=16, help="X offset applied when --x is omitted")
    scene_widgets_paste.add_argument("--offset-y", type=int, default=16, help="Y offset applied when --y is omitted")
    scene_widgets_paste.add_argument("--x", type=int, help="Absolute pasted x")
    scene_widgets_paste.add_argument("--y", type=int, help="Absolute pasted y")
    scene_widgets_copy_to = scene_widgets_sub.add_parser("copy-to", help="Copy one widget and paste it into a target page")
    scene_widgets_copy_to.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_widgets_copy_to.add_argument("widget_path", help="page.widget, for example page0.btn0")
    scene_widgets_copy_to.add_argument("target_page", help="Target page id")
    scene_widgets_copy_to.add_argument("--id", dest="new_id", help="New widget id")
    scene_widgets_copy_to.add_argument("--offset-x", type=int, default=16, help="X offset applied when --x is omitted")
    scene_widgets_copy_to.add_argument("--offset-y", type=int, default=16, help="Y offset applied when --y is omitted")
    scene_widgets_copy_to.add_argument("--x", type=int, help="Absolute pasted x")
    scene_widgets_copy_to.add_argument("--y", type=int, help="Absolute pasted y")
    scene_widgets_move = scene_widgets_sub.add_parser("move", help="Move one widget in page z-order")
    scene_widgets_move.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_widgets_move.add_argument("widget_path", help="page.widget, for example page0.btn0")
    scene_widgets_move.add_argument("--direction", required=True, choices=("up", "down", "front", "back"), help="Z-order move")
    scene_pages = scene_sub.add_parser("pages", help="Manage scene pages without opening the GUI")
    scene_pages_sub = scene_pages.add_subparsers(dest="scene_pages_command")
    scene_pages_add = scene_pages_sub.add_parser("add", help="Append a new empty page")
    scene_pages_add.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_pages_add.add_argument("page_id", help="New page id")
    scene_pages_duplicate = scene_pages_sub.add_parser("duplicate", help="Duplicate one page")
    scene_pages_duplicate.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_pages_duplicate.add_argument("page_id", help="Source page id")
    scene_pages_duplicate.add_argument("--id", dest="new_id", help="New page id; default is <page>_copy")
    scene_pages_delete = scene_pages_sub.add_parser("delete", help="Delete one page")
    scene_pages_delete.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_pages_delete.add_argument("page_id", help="Page id to delete")
    scene_pages_update = scene_pages_sub.add_parser("update", help="Update one page id or layout")
    scene_pages_update.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_pages_update.add_argument("page_id", help="Page id to update")
    scene_pages_update.add_argument("--id", dest="new_id", help="New page id")
    scene_pages_update.add_argument("--layout-json", help="Replace page layout with a JSON object")
    scene_design = scene_sub.add_parser("design", help="Canvas-style design operations with agent patch output")
    scene_design_sub = scene_design.add_subparsers(dest="scene_design_command")
    scene_design_move = scene_design_sub.add_parser("move", help="Move one widget and write agent_patch.json")
    scene_design_move.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_design_move.add_argument("widget_path", help="page.widget, for example page0.btn0")
    scene_design_move.add_argument("--out-dir", help="Output directory for design_session.json and agent_patch.json")
    scene_design_move.add_argument("--x", type=int, help="Absolute x")
    scene_design_move.add_argument("--y", type=int, help="Absolute y")
    scene_design_move.add_argument("--dx", type=int, default=0, help="Relative x delta")
    scene_design_move.add_argument("--dy", type=int, default=0, help="Relative y delta")
    scene_design_move.add_argument("--snap", type=int, default=1, help="Snap grid in pixels")
    scene_design_move.add_argument("--no-clamp", action="store_true", help="Allow geometry outside the canvas")
    scene_design_resize = scene_design_sub.add_parser("resize", help="Resize one widget and write agent_patch.json")
    scene_design_resize.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_design_resize.add_argument("widget_path", help="page.widget, for example page0.btn0")
    scene_design_resize.add_argument("--out-dir", help="Output directory for design_session.json and agent_patch.json")
    scene_design_resize.add_argument("--w", type=int, help="Absolute width")
    scene_design_resize.add_argument("--h", type=int, help="Absolute height")
    scene_design_resize.add_argument("--dw", type=int, default=0, help="Relative width delta")
    scene_design_resize.add_argument("--dh", type=int, default=0, help="Relative height delta")
    scene_design_resize.add_argument("--min-size", type=int, default=1, help="Minimum width/height")
    scene_design_resize.add_argument("--snap", type=int, default=1, help="Snap grid in pixels")
    scene_design_resize.add_argument("--no-clamp", action="store_true", help="Allow geometry outside the canvas")
    scene_design_align = scene_design_sub.add_parser("align", help="Align widgets on one page and write agent_patch.json")
    scene_design_align.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_design_align.add_argument("widget_paths", nargs="+", help="page.widget paths, all on the same page")
    scene_design_align.add_argument("--edge", required=True, choices=("left", "right", "top", "bottom", "hcenter", "vcenter"), help="Alignment edge")
    scene_design_align.add_argument("--anchor", default="first", choices=("first", "last", "canvas"), help="Alignment anchor")
    scene_design_align.add_argument("--out-dir", help="Output directory for design_session.json and agent_patch.json")
    scene_design_align.add_argument("--snap", type=int, default=1, help="Snap grid in pixels")
    scene_design_align.add_argument("--no-clamp", action="store_true", help="Allow geometry outside the canvas")
    scene_design_distribute = scene_design_sub.add_parser("distribute", help="Distribute widgets evenly on one page and write agent_patch.json")
    scene_design_distribute.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_design_distribute.add_argument("widget_paths", nargs="+", help="page.widget paths, all on the same page")
    scene_design_distribute.add_argument("--axis", required=True, choices=("horizontal", "vertical"), help="Distribution axis")
    scene_design_distribute.add_argument("--out-dir", help="Output directory for design_session.json and agent_patch.json")
    scene_design_distribute.add_argument("--snap", type=int, default=1, help="Snap grid in pixels")
    scene_design_distribute.add_argument("--no-clamp", action="store_true", help="Allow geometry outside the canvas")
    scene_design_match_size = scene_design_sub.add_parser("match-size", help="Match widget widths/heights on one page and write agent_patch.json")
    scene_design_match_size.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_design_match_size.add_argument("widget_paths", nargs="+", help="page.widget paths, all on the same page")
    scene_design_match_size.add_argument("--mode", required=True, choices=("width", "height", "both"), help="Size component to match")
    scene_design_match_size.add_argument("--anchor", default="first", choices=("first", "last"), help="Widget whose size should be copied")
    scene_design_match_size.add_argument("--out-dir", help="Output directory for design_session.json and agent_patch.json")
    scene_design_match_size.add_argument("--min-size", type=int, default=1, help="Minimum width/height")
    scene_design_match_size.add_argument("--snap", type=int, default=1, help="Snap grid in pixels")
    scene_design_match_size.add_argument("--no-clamp", action="store_true", help="Allow geometry outside the canvas")
    scene_design_replay = scene_design_sub.add_parser("replay", help="Replay a design agent_patch.json")
    scene_design_replay.add_argument("scene_path", help="Scene JSON/YAML file")
    scene_design_replay.add_argument("patch_path", help="agent_patch.json file")
    scene_design_replay.add_argument("--out-dir", help="Output directory for replay design artifacts")

    hmi_parser = subparsers.add_parser("hmi", help="Scene authoring helpers")
    hmi_sub = hmi_parser.add_subparsers(dest="hmi_command")
    hmi_import_project = hmi_sub.add_parser("import", help="Import an official HMI into a lossy editable scene bundle")
    hmi_import_project.add_argument("hmi_path", help="Official .HMI file")
    hmi_import_project.add_argument("--out-dir", required=True, help="Output directory for imported scene and preview bundle")
    hmi_import_project.add_argument("--target", default="TJC8048X543_011C", help="Target model name")
    hmi_import_project.add_argument("--overwrite", action="store_true", help="Overwrite existing import outputs")
    hmi_roundtrip = hmi_sub.add_parser("roundtrip-check", help="Import, regenerate, and diagnose HMI roundtrip loss")
    hmi_roundtrip.add_argument("hmi_path", help="Official .HMI file")
    hmi_roundtrip.add_argument("--out-dir", required=True, help="Output directory for roundtrip artifacts")
    hmi_roundtrip.add_argument("--target", default="TJC8048X543_011C", help="Target model name")
    hmi_roundtrip.add_argument("--overwrite", action="store_true", help="Overwrite existing roundtrip/import outputs")
    hmi_roundtrip.add_argument("--source-tft", help="Optional official .tft/.run oracle for compiled event-index evidence")
    hmi_import = hmi_sub.add_parser("import-image", help="Normalize a PNG/JPG into build assets")
    hmi_import.add_argument("source", help="PNG/JPG file")
    hmi_import.add_argument("--out", required=True, help="Asset output directory")

    hmi_add_widget = hmi_sub.add_parser("add-widget", help="Append any supported widget type to a scene file")
    hmi_add_widget.add_argument("--scene", required=True, help="Scene JSON file to modify")
    hmi_add_widget.add_argument("--page", default="page0", help="Target page id")
    hmi_add_widget.add_argument("--id", required=True, help="Widget id")
    hmi_add_widget.add_argument("--type", required=True, help="Widget type or alias such as text, scrolling-text, expicture, gmov")
    hmi_add_widget.add_argument("--x", type=int, help="Widget x")
    hmi_add_widget.add_argument("--y", type=int, help="Widget y")
    hmi_add_widget.add_argument("--w", type=int, help="Widget width")
    hmi_add_widget.add_argument("--h", type=int, help="Widget height")
    hmi_add_widget.add_argument("--text", help="Widget text")
    hmi_add_widget.add_argument("--value", type=int, help="Widget numeric value")
    hmi_add_widget.add_argument("--style", action="append", help="Add style key=value; JSON, bool, and int values are accepted")
    hmi_add_widget.add_argument("--resource", action="append", help="Add resource key=value; JSON, bool, and int values are accepted")
    hmi_add_widget.add_argument("--binding", action="append", help="Add binding key=value; JSON, bool, and int values are accepted")

    media_patch_commands = {"add-animation", "add-video", "add-audio"}
    for name in (
        "add-text",
        "add-image",
        "add-button",
        "add-number",
        "add-timer",
        "add-animation",
        "add-video",
        "add-audio",
    ):
        patch_parser = hmi_sub.add_parser(name, help=f"Append a {name[4:]} widget to a scene file")
        patch_parser.add_argument("--scene", required=True, help="Scene JSON file to modify")
        patch_parser.add_argument("--page", default="page0", help="Target page id")
        patch_parser.add_argument("--id", required=True, help="Widget id")
        geometry_required = name not in {"add-timer", "add-audio"}
        patch_parser.add_argument("--x", type=int, required=geometry_required, help="Widget x")
        patch_parser.add_argument("--y", type=int, required=geometry_required, help="Widget y")
        patch_parser.add_argument("--w", type=int, required=geometry_required, help="Widget width")
        patch_parser.add_argument("--h", type=int, required=geometry_required, help="Widget height")
        patch_parser.add_argument("--text", help="Widget text")
        patch_parser.add_argument("--value", type=int, help="Widget numeric value")
        patch_parser.add_argument("--asset", help="Asset key for image/button widgets")
        if name == "add-timer":
            patch_parser.add_argument("--tim", type=int, help="Timer interval in milliseconds")
            patch_parser.add_argument("--enabled", action="store_true", help="Set timer en=1")
            patch_parser.add_argument("--disabled", action="store_true", help="Set timer en=0")
        if name in media_patch_commands:
            patch_parser.add_argument("--enabled", action="store_true", help="Set media en=1")
            patch_parser.add_argument("--disabled", action="store_true", help="Set media en=0")
            patch_parser.add_argument("--path", help="Runtime media path such as sd0/video/demo.video")
            patch_parser.add_argument("--vid", type=int, help="Internal media resource id when using embedded media resources")
            patch_parser.add_argument("--loop", type=int, choices=(0, 1), help="Set media loop property")
            patch_parser.add_argument("--dis", type=int, help="Set media display mode property")
            if name == "add-video":
                patch_parser.add_argument("--fps", type=int, help="Set video frame-rate property")

    hmi_set_page = hmi_sub.add_parser("set-page", help="Update canvas metadata in a scene file")
    hmi_set_page.add_argument("--scene", required=True, help="Scene JSON/YAML file")
    hmi_set_page.add_argument("--background-color", type=int, help="Canvas background color")
    hmi_set_page.add_argument("--width", type=int, help="Canvas width")
    hmi_set_page.add_argument("--height", type=int, help="Canvas height")

    hmi_build = hmi_sub.add_parser("build", help="Build a scene file into an HMI artifact")
    hmi_build.add_argument("--scene", required=True, help="Scene JSON/YAML file")
    hmi_build.add_argument("--seed", required=True, help="Seed HMI")
    hmi_build.add_argument("--out", required=True, help="Output directory")
    hmi_build.add_argument("--baseline-tft", help="Optional baseline TFT used to emit output.tft")
    hmi_build.add_argument("--font-zi", help="Optional .zi font to patch into output.hmi and output.tft")
    hmi_build.add_argument("--font-entry", default="0.zi", help="HMI font entry to replace when --font-zi is used")
    hmi_donor_patch = hmi_sub.add_parser(
        "donor-patch",
        help="Patch a donor HMI page while preserving the donor container/shadow chain",
    )
    hmi_donor_patch.add_argument("donor_hmi", nargs="?", help="Input donor .HMI file")
    hmi_donor_patch.add_argument("--out-dir", required=True, help="Output directory")
    hmi_donor_patch.add_argument("--spec-json", help="Patch spec JSON file")
    hmi_donor_patch.add_argument("--page-entry", default="0.pa", help="Page entry to patch")
    hmi_donor_patch.add_argument("--delete-obj", action="append", default=[], help="Delete one object by name")
    hmi_donor_patch.add_argument(
        "--move-obj",
        action="append",
        default=[],
        help="Move object geometry as name:x:y:w:h",
    )
    hmi_donor_patch.add_argument(
        "--set-int",
        action="append",
        default=[],
        help="Set integer field as obj.field=value",
    )
    hmi_donor_patch.add_argument(
        "--set-str",
        action="append",
        default=[],
        help="Set string field as obj.field=text",
    )
    hmi_donor_patch.add_argument(
        "--graft-obj",
        action="append",
        default=[],
        help="Add one block from another donor as source_hmi|page|source_obj|target_obj|x|y|w|h",
    )
    hmi_donor_patch.add_argument(
        "--probe-lowlevel",
        action="store_true",
        help="Run tools/official_hmi_lowlevel_probe.py on the patched output",
    )
    hmi_donor_patch.add_argument(
        "--probe-reopen",
        action="store_true",
        help="Run tools/official_hmi_reopen_probe.py on a copy of the generated output",
    )
    hmi_reopen_safe = hmi_sub.add_parser(
        "reopen-safe-fixture",
        help="Generate the canonical reopen-safe donor fixture for one control type",
    )
    hmi_reopen_safe.add_argument("control_type", help="Control type such as text, file-browser, xfloat")
    hmi_reopen_safe.add_argument("--out-dir", required=True, help="Output directory")
    hmi_reopen_safe.add_argument("--corpus-root", help="Optional donor corpus root containing reopen_safe_control_map.json")
    hmi_lowlevel_compatible = hmi_sub.add_parser(
        "lowlevel-compatible-fixture",
        help="Generate the canonical lowlevel-compatible donor fixture for one control type",
    )
    hmi_lowlevel_compatible.add_argument("control_type", help="Control type such as text, file-browser, xfloat")
    hmi_lowlevel_compatible.add_argument("--out-dir", required=True, help="Output directory")
    hmi_lowlevel_compatible.add_argument(
        "--corpus-root",
        help="Optional donor corpus root containing lowlevel_compatible_control_map.json",
    )
    hmi_preview_pa = hmi_sub.add_parser("preview-pa", help="Render an extracted .pa page to a PNG preview")
    hmi_preview_pa.add_argument("--pa", required=True, help="Extracted page file such as 0.pa")
    hmi_preview_pa.add_argument("--out", required=True, help="Preview PNG path")
    hmi_preview_pa.add_argument("--width", type=int, help="Preview canvas width")
    hmi_preview_pa.add_argument("--height", type=int, help="Preview canvas height")
    hmi_preview_pa.add_argument("--assets-dir", help="Directory containing extracted picture entries such as 0.i")
    hmi_preview_pa.add_argument("--font", action="append", help="Preview .zi font path, optionally FONT_ID=path")
    hmi_preview_pa.add_argument("--no-labels", action="store_true", help="Hide yellow object-name labels")
    hmi_preview = hmi_sub.add_parser("preview", help="Render a page inside an HMI file to a PNG preview")
    hmi_preview.add_argument("--hmi", required=True, help="Input HMI file")
    hmi_preview.add_argument("--out", required=True, help="Preview PNG path")
    hmi_preview.add_argument("--page", default="0", help="Page entry index/name, for example 0 or 0.pa")
    hmi_preview.add_argument("--width", type=int, help="Preview canvas width")
    hmi_preview.add_argument("--height", type=int, help="Preview canvas height")
    hmi_preview.add_argument("--font", action="append", help="Preview .zi font path, optionally FONT_ID=path")
    hmi_preview.add_argument("--no-labels", action="store_true", help="Hide yellow object-name labels")

    font_parser = subparsers.add_parser("font", help="Font generation and HMI font replacement")
    font_sub = font_parser.add_subparsers(dest="font_command")
    font_build = font_sub.add_parser("build-zicli", help="Build the local ZiCli helper")
    font_gen = font_sub.add_parser("generate-zi", help="Generate a .zi font from text input")
    _add_font_generation_args(font_gen)
    font_scene = font_sub.add_parser("from-scene", help="Generate a .zi subset font from scene text")
    _add_font_generation_args(font_scene, include_scene=True)
    font_replace = font_sub.add_parser("replace-hmi", help="Replace an HMI font entry such as 0.zi")
    font_replace.add_argument("--hmi", required=True, help="Input HMI file")
    font_replace.add_argument("--zi", required=True, help="Replacement .zi file")
    font_replace.add_argument("--out", required=True, help="Output HMI file")
    font_replace.add_argument("--entry", default="0.zi", help="Entry name to replace")

    tft_parser = subparsers.add_parser("tft", help="TFT build operations")
    tft_sub = tft_parser.add_subparsers(dest="tft_command")
    tft_build = tft_sub.add_parser("build", help="Build scene artifacts including experimental TFT metadata")
    tft_build.add_argument("--scene", required=True, help="Scene JSON/YAML file")
    tft_build.add_argument("--seed", required=True, help="Seed HMI")
    tft_build.add_argument("--baseline-tft", help="Baseline TFT used to emit output.tft")
    tft_build.add_argument("--out", required=True, help="Output directory")
    tft_build.add_argument("--font-zi", help="Optional .zi font to patch into output.hmi and output.tft")
    tft_build.add_argument("--font-entry", default="0.zi", help="HMI font entry to replace when --font-zi is used")
    tft_inspect = tft_sub.add_parser("inspect", help="Inspect an existing TFT file using the local TFTTool")
    tft_inspect.add_argument("--file", required=True, help="TFT file path")
    tft_reverse = tft_sub.add_parser("reverse-tail", help="Probe compiled TFT object data against a parsed HMI .pa page")
    tft_reverse.add_argument("--file", required=True, help="TFT file path")
    tft_reverse.add_argument("--hmi-pa", help="Extracted HMI page file such as 0.pa")
    tft_reverse.add_argument("--install-dir", help="USART HMI installation directory for static resource matching")
    tft_reverse.add_argument("--context-bytes", type=int, default=48, help="Hex context around every match")
    tft_event_index = tft_sub.add_parser("event-index", help="Inspect compiled TFT event-index/scheduler evidence")
    tft_event_index_sub = tft_event_index.add_subparsers(dest="tft_event_index_command")
    tft_event_index_inspect = tft_event_index_sub.add_parser("inspect", help="Inspect an HMI/TFT pair for event dispatch evidence")
    tft_event_index_inspect.add_argument("--hmi", required=True, help="Source HMI file containing 0.pa event tokens")
    tft_event_index_inspect.add_argument("--tft", required=True, help="Official or generated TFT/run file to inspect")
    tft_event_index_inspect.add_argument("--out", help="Optional JSON report path")
    tft_event_index_inspect.add_argument(
        "--force-post-primary-page-load",
        action="store_true",
        help="Also search the experimental post-primary page-load chunk for non-media pages",
    )
    tft_event_index_batch = tft_event_index_sub.add_parser(
        "batch",
        help="Batch-scan HMI files for nearby TFT event-index oracles",
    )
    tft_event_index_batch.add_argument("paths", nargs="+", help="HMI files or directories to scan")
    tft_event_index_batch.add_argument("--out", help="Optional JSON report path")
    tft_event_index_batch.add_argument(
        "--force-post-primary-page-load",
        action="store_true",
        help="Also search the experimental post-primary page-load chunk for non-media pages",
    )
    tft_event_index_batch.add_argument(
        "--include-object-only",
        action="store_true",
        help="Include fixtures that have object events but no page-level event script",
    )
    tft_models = tft_sub.add_parser("list-models", help="List TFT models known by the local TFTTool")
    tft_hash_name = tft_sub.add_parser("hash-name", help="Compute a compiled TFT page/object-name hash")
    tft_hash_name.add_argument("name", help="Page/object name, for example t0 or page0")
    tft_hash_name.add_argument("--width", type=int, default=OBJECT_NAME_HASH_WIDTH, help="Padded hash field width")
    tft_pack_fonts = tft_sub.add_parser("pack-fonts", help="Pack one or more .zi files into a TFT-style embedded font run")
    tft_pack_fonts.add_argument("--font", action="append", required=True, help="Input .zi file, repeatable")
    tft_pack_fonts.add_argument("--out", required=True, help="Output packed font-run binary")
    tft_inspect_font_run = tft_sub.add_parser("inspect-font-run", help="Inspect a packed TFT-style font run binary")
    tft_inspect_font_run.add_argument("--file", required=True, help="Packed font-run file path")
    tft_patch_font = tft_sub.add_parser("patch-font", help="Replace the embedded TFT .zi font resource in place")
    tft_patch_font.add_argument("--baseline-tft", required=True, help="Input TFT used as binary seed")
    tft_patch_font.add_argument("--font", required=True, help="Replacement .zi font file")
    tft_patch_font.add_argument("--out", required=True, help="Output TFT path")
    tft_health = tft_sub.add_parser("health", help="Probe whether a serial screen is safe for public TFT upload")
    tft_health.add_argument("--port", required=True, help="Serial port, for example COM36")
    tft_health.add_argument("--baud", type=int, default=9600, help="Current device baud")
    tft_health.add_argument("--timeout-ms", type=int, default=3000, help="Per-command timeout in milliseconds")
    tft_health.add_argument("--expected-model", help="Expected model, for example TJC8048X543_011C")
    tft_preflight = tft_sub.add_parser("preflight", help="Check TFT checksum and serial upload readiness")
    tft_preflight.add_argument("--file", required=True, help="TFT file path")
    tft_preflight.add_argument("--port", required=True, help="Serial port, for example COM36")
    tft_preflight.add_argument("--baud", type=int, default=9600, help="Current device baud")
    tft_preflight.add_argument("--timeout-ms", type=int, default=3000, help="Per-command serial timeout")
    tft_preflight.add_argument(
        "--expected-model",
        default="TJC8048X543_011C",
        help="Expected model, for example TJC8048X543_011C; pass an empty string to skip model matching",
    )
    tft_readiness = tft_sub.add_parser("readiness", help="Offline TFT readiness summary from checksum + sibling build manifest")
    tft_readiness.add_argument("--file", required=True, help="TFT file path")
    tft_upload = tft_sub.add_parser("upload", help="Upload a .tft file to a screen over serial")
    tft_upload.add_argument("--file", required=True, help="TFT file path")
    tft_upload.add_argument("--port", required=True, help="Serial port")
    tft_upload.add_argument("--baud", type=int, default=9600, help="Current device baud")
    tft_upload.add_argument("--download-baud", type=int, default=DEFAULT_DOWNLOAD_BAUD, help="Forced download baud")
    tft_upload.add_argument("--chunk-size", type=int, default=PUBLIC_WHMI_CHUNK_SIZE, help="Chunk size in bytes")
    tft_upload.add_argument(
        "--allow-unsafe-chunk-size",
        action="store_true",
        help="Allow non-4096 chunks for deliberate bootloader probes; normal uploads should not use this",
    )
    tft_upload.add_argument("--timeout-ms", type=int, default=3000, help="Ack timeout in milliseconds")
    tft_upload.add_argument("--address", type=int, default=0, help="Optional HMI address prefix, 0 disables")
    tft_upload.add_argument(
        "--require-runtime-healthy",
        action="store_true",
        help="Deprecated compatibility flag; runtime-health preflight is enabled by default",
    )
    tft_upload.add_argument(
        "--require-valid-checksum",
        action="store_true",
        help="Deprecated compatibility flag; checksum preflight is enabled by default",
    )
    tft_upload.add_argument(
        "--no-preflight",
        action="store_true",
        help="Skip default checksum and serial-health preflight; only use for deliberate recovery/reverse probes",
    )
    tft_upload.add_argument(
        "--allow-quarantined-touch-capture",
        action="store_true",
        help=(
            "Allow upload of a generated TFT whose sibling manifest contains touch-capture; "
            "use only after explicit recovery planning"
        ),
    )
    tft_upload.add_argument(
        "--allow-hardware-quarantine",
        action="store_true",
        help=(
            "Allow upload of a TFT whose manifest or known fixture path is hardware-quarantined; "
            "use only after an explicit recovery/live plan"
        ),
    )
    tft_upload.add_argument(
        "--allow-pending-sd-recovery",
        action="store_true",
        help=(
            "Override the local pending SD-recovery block; use only after the SD card "
            "has been removed and the panel was power-cycled once"
        ),
    )
    tft_upload.add_argument(
        "--expected-model",
        default="TJC8048X543_011C",
        help="Expected model for upload preflight; pass an empty string to skip model matching",
    )
    tft_upload.add_argument(
        "--health-timeout-ms",
        type=int,
        default=3000,
        help="Per-command timeout for --require-runtime-healthy",
    )
    tft_upload.add_argument(
        "--known-current",
        help="Trusted currently-flashed TFT file; used only for safe identical-file skipping",
    )
    tft_upload.add_argument(
        "--skip-if-identical",
        action="store_true",
        help="If --file exactly matches --known-current, skip opening the serial port and do not upload",
    )
    tft_upload.add_argument(
        "--skip-if-current",
        action="store_true",
        help=(
            "Skip upload when --file matches the last successful upload manifest for "
            "the same port, baud, and expected model"
        ),
    )
    tft_upload.add_argument(
        "--current-manifest",
        default=DEFAULT_LAST_UPLOAD_MANIFEST,
        help="Path to the last successful upload manifest",
    )
    tft_upload.add_argument(
        "--no-record-current",
        action="store_true",
        help="Do not update the last successful upload manifest after a successful upload",
    )
    tft_upload.add_argument(
        "--verify-after-upload",
        action="store_true",
        help="Run serial health and optional get assertions after upload or current-manifest skip",
    )
    tft_upload.add_argument(
        "--verify-wait-ms",
        type=int,
        default=1000,
        help="Wait before --verify-after-upload serial checks",
    )
    tft_upload.add_argument(
        "--verify-health-attempts",
        type=int,
        default=3,
        help="Maximum serial-health attempts during --verify-after-upload",
    )
    tft_upload.add_argument(
        "--verify-health-retry-delay-ms",
        type=int,
        default=300,
        help="Delay between serial-health retries during --verify-after-upload",
    )
    tft_upload.add_argument(
        "--verify-get",
        action="append",
        default=[],
        help="Post-upload get assertion as obj.attr=value; repeatable. Without =, only requires a readable response.",
    )
    tft_upload.add_argument(
        "--verify-step",
        action="append",
        default=[],
        help=(
            "Post-upload runtime step as a raw command or JSON object; repeatable. "
            "Raw commands may use 'COMMAND => EXPECTED', 'COMMAND => hex:AA BB', or 'COMMAND => ascii:TEXT'. "
            "JSON fields include command, label, delay_ms, attempts, expect_response, "
            "expected_kind, expected_value, expected_hex, and expected_ascii_preview."
        ),
    )
    tft_upload.add_argument(
        "--verify-capture",
        action="store_true",
        help="Capture a camera frame as part of --verify-after-upload evidence",
    )
    tft_upload.add_argument(
        "--verify-capture-output",
        help="Optional output path for --verify-capture; defaults under reverse_usarthmi/upload_verify_captures",
    )
    tft_upload.add_argument("--verify-camera-index", type=int, default=1, help="Camera index for --verify-capture")
    tft_upload.add_argument(
        "--verify-camera-backend",
        choices=["default", "dshow", "msmf"],
        default="msmf",
        help="OpenCV backend for --verify-capture",
    )
    tft_upload.add_argument(
        "--verify-camera-warmup-frames",
        type=int,
        default=3,
        help="Warmup frames before --verify-capture saves an image",
    )
    tft_upload.add_argument(
        "--verify-capture-timeout-ms",
        type=int,
        default=30000,
        help="Maximum time to wait for --verify-capture",
    )
    tft_upload.add_argument(
        "--prepare-delay-ms",
        type=int,
        default=2500,
        help="Send delay=<ms> before whmi-wri like the official downloader; 0 disables",
    )
    tft_upload.add_argument(
        "--prepare-wait-ms",
        type=int,
        default=1500,
        help="Wait after delay=<ms> before whmi-wri",
    )
    tft_upload.add_argument("--progress", action="store_true", help="Print upload progress to stderr")
    tft_plan = tft_sub.add_parser("plan-upload", help="Analyze TFT chunks before upload")
    tft_plan.add_argument("--file", required=True, help="TFT file path")
    tft_plan.add_argument("--baseline", help="Known-current TFT file for chunk comparison")
    tft_plan.add_argument("--chunk-size", type=int, default=PUBLIC_WHMI_CHUNK_SIZE, help="Chunk size in bytes")
    tft_plan.add_argument("--download-baud", type=int, default=DEFAULT_DOWNLOAD_BAUD, help="Baud used for timing estimate")
    tft_cases = tft_sub.add_parser("compare-cases", help="Compare official one-variable HMI/TFT reverse-engineering cases")
    tft_cases.add_argument("--case-root", required=True, help="Folder containing case_* subdirectories")
    tft_cases.add_argument("--out", required=True, help="Output directory for extracts and JSON reports")
    tft_cases.add_argument("--baseline-case", default="case_00_baseline", help="Baseline case directory name")
    tft_cases.add_argument("--install-dir", help="USART HMI installation directory for static resource matching")
    tft_cases.add_argument("--context-bytes", type=int, default=16, help="Hex context around reverse matches")
    tft_cases.add_argument("--diff-run-limit", type=int, default=64, help="Maximum diff runs stored per case")
    tft_patch = tft_sub.add_parser("patch-basic", help="Experimentally patch same-layout text/coordinate fields in a baseline TFT")
    tft_patch.add_argument("--baseline-tft", required=True, help="Official baseline TFT used as binary template")
    tft_patch.add_argument("--baseline-pa", required=True, help="Extracted baseline 0.pa")
    tft_patch.add_argument("--target-pa", required=True, help="Target extracted 0.pa with same object layout")
    tft_patch.add_argument("--out", required=True, help="Output experimental TFT")
    tft_patch.add_argument(
        "--checksum-mode",
        choices=("recompute", "keep", "zero"),
        default="recompute",
        help="How to handle the final 4-byte TFT checksum",
    )
    tft_patch_add = tft_sub.add_parser("patch-add-object", help="Experimentally rebuild a TFT tail after appending objects")
    tft_patch_add.add_argument("--baseline-tft", required=True, help="Official baseline TFT used as binary seed")
    tft_patch_add.add_argument("--baseline-pa", required=True, help="Extracted baseline 0.pa")
    tft_patch_add.add_argument("--target-pa", required=True, help="Target extracted 0.pa with one or more appended t/b/p objects")
    tft_patch_add.add_argument("--out", required=True, help="Output experimental TFT")
    tft_rebuild_page = tft_sub.add_parser("rebuild-page", help="Experimentally rebuild a clean TFT page from target 0.pa")
    tft_rebuild_page.add_argument("--baseline-tft", required=True, help="TFT used as binary shell and template seed")
    tft_rebuild_page.add_argument("--seed-pa", required=True, help="0.pa matching the baseline TFT template seed")
    tft_rebuild_page.add_argument("--target-pa", required=True, help="Target 0.pa whose object list should replace the seed page")
    tft_rebuild_page.add_argument("--out", required=True, help="Output experimental clean-page TFT")
    tft_checksum = tft_sub.add_parser("checksum", help="Verify the final 4-byte TFT checksum")
    tft_checksum.add_argument("--file", required=True, help="TFT file path")
    tft_hmisafe_finalize = tft_sub.add_parser(
        "hmisafe-finalize",
        help="Apply the reproduced achmi.dll HmiSafe finalizer to a pre-HmiSafe TFT",
    )
    tft_hmisafe_finalize.add_argument("--input", required=True, help="Pre-HmiSafe intermediate TFT")
    tft_hmisafe_finalize.add_argument("--out", required=True, help="Output final TFT path")
    tft_hmisafe_finalize.add_argument("--final", help="Optional official final TFT to byte-compare")
    tft_hmisafe_verify = tft_sub.add_parser(
        "hmisafe-verify",
        help="Verify HmiSafe 400-byte header CRCs and EOF-4 finalizer checksum",
    )
    tft_hmisafe_verify.add_argument("--file", required=True, help="Final TFT file path")

    capabilities_parser = subparsers.add_parser("capabilities", help="Show current target capabilities")
    capabilities_parser.add_argument("--widget", help="Show one widget capability by type or alias")
    capabilities_parser.add_argument(
        "--support",
        choices=[item.value for item in WidgetSupport],
        help="List widgets filtered by support status instead of returning the full manifest",
    )
    capabilities_parser.add_argument("--include-aliases", action="store_true", help="Include accepted widget aliases")

    widgets_parser = subparsers.add_parser("widgets", help="Inspect widget capability metadata")
    widgets_sub = widgets_parser.add_subparsers(dest="widgets_command")
    widgets_list = widgets_sub.add_parser("list", help="List registered widget capabilities")
    widgets_list.add_argument(
        "--support",
        choices=[item.value for item in WidgetSupport],
        help="Filter by support status",
    )
    widgets_list.add_argument("--include-aliases", action="store_true", help="Include accepted aliases")
    widgets_show = widgets_sub.add_parser("show", help="Show one widget capability by type or alias")
    widgets_show.add_argument("widget_type", help="Widget type or alias")
    widgets_show.add_argument("--include-aliases", action="store_true", help="Include accepted aliases")
    widgets_manifest = widgets_sub.add_parser("manifest", help="Show the full widget capability manifest")
    widgets_manifest.add_argument("--include-aliases", action="store_true", help="Include accepted aliases")
    widgets_template = widgets_sub.add_parser("template", help="Show an authoring template for one widget type")
    widgets_template.add_argument("widget_type", help="Widget type or alias")
    widgets_template.add_argument("--id", dest="widget_id", help="Widget id to place in the template")
    widgets_template.add_argument("--x", type=int, default=40, help="Template x coordinate")
    widgets_template.add_argument("--y", type=int, default=40, help="Template y coordinate")
    widgets_sub.add_parser("templates", help="List available widget authoring templates")

    editor_parser = subparsers.add_parser("editor", help="Inspect editor/agent authoring capabilities")
    editor_sub = editor_parser.add_subparsers(dest="editor_command")
    editor_sub.add_parser("capabilities", help="Show desktop/headless editor capability manifest")
    editor_sub.add_parser("audit", help="Show official-editor parity audit checklist")

    target_parser = subparsers.add_parser("target", help="Inspect current target status artifacts")
    target_sub = target_parser.add_subparsers(dest="target_command")
    target_sub.add_parser("summary", help="Show compact current target status summary")
    target_sub.add_parser("audit", help="Show current target completion audit")
    target_sub.add_parser("calibration", help="Show builder-facing calibration status")
    target_sub.add_parser("frontier", help="Show the current page1 file-browser frontier report")
    target_sub.add_parser("compare-targets", help="Show the current page1 file-browser native-init compare-targets report")
    target_sub.add_parser("next-probe", help="Show the exact next live-probe bundle and recovery commands")
    target_check_next_probe = target_sub.add_parser(
        "check-next-probe",
        help="Run offline builder field-map invariants for the current next-probe TFT",
    )
    target_check_next_probe.add_argument("--file", help="Override TFT path; defaults to the field-map next-probe TFT")
    target_run_next_probe = target_sub.add_parser(
        "run-next-probe",
        help="Run safe checks from the exact next live-probe bundle; no upload unless explicitly requested",
    )
    target_run_next_probe.add_argument("--preflight", action="store_true", help="Run serial preflight after offline checks")
    target_run_next_probe.add_argument("--live-smoke", action="store_true", help="Run live readback checks with live_tft_smoke.py")
    target_run_next_probe.add_argument("--upload", action="store_true", help="Upload during live smoke; requires --live-smoke")
    target_run_next_probe.add_argument(
        "--allow-hardware-quarantine",
        action="store_true",
        help="Allow the one controlled quarantined recovery upload",
    )
    target_run_next_probe.add_argument(
        "--allow-pending-sd-recovery",
        action="store_true",
        help="Allow live smoke when the local SD recovery guard is pending",
    )
    target_run_next_probe.add_argument("--capture", action="store_true", help="Capture the screen during live smoke")
    target_run_next_probe.add_argument("--progress", action="store_true", help="Show upload progress during live smoke")
    target_run_next_probe.add_argument("--port", default="COM36")
    target_run_next_probe.add_argument("--baud", type=int, default=9600)
    target_run_next_probe.add_argument("--download-baud", type=int, default=DEFAULT_DOWNLOAD_BAUD)
    target_run_next_probe.add_argument("--timeout-ms", type=int, default=3000)
    target_run_next_probe.add_argument("--out-dir", help="Override live_probe output directory")
    target_run_next_probe.add_argument("--result-json", help="Write the runner result JSON to this path")

    return parser


def _handle_serial_command(args: argparse.Namespace) -> dict[str, Any]:
    command_text = _build_command_text(args)
    config = SerialConfig(
        port=args.port,
        baud=args.baud,
        timeout_ms=args.timeout_ms,
        verbose=args.verbose,
    )
    payload, response = SerialTransport(config).transact(command_text)
    parsed = parse_response(response)
    return {
        "port": args.port,
        "baud": args.baud,
        "command": command_text,
        "sent_hex": payload.hex(" "),
        "response": parsed.to_dict(),
    }


def _handle_inspect_hmi(args: argparse.Namespace) -> dict[str, Any]:
    inspection = inspect_hmi(args.path)
    return inspection.to_dict()


def _handle_extract_hmi(args: argparse.Namespace) -> dict[str, Any]:
    written = extract_hmi(args.path, args.out)
    return {
        "path": str(Path(args.path).resolve()),
        "output_dir": str(Path(args.out).resolve()),
        "files": [str(item) for item in written],
    }


def _handle_scene_command(args: argparse.Namespace) -> dict[str, Any]:
    if args.scene_command == "new":
        return create_scene_document(
            args.scene_path,
            project_name=args.name,
            width=args.width,
            height=args.height,
            default_page=args.page,
            background_color=args.background_color,
            overwrite=args.overwrite,
        )
    if args.scene_command == "save-as":
        return save_scene_document_as(args.scene_path, args.out, overwrite=args.overwrite)
    if args.scene_command == "project":
        return _handle_scene_project_command(args)
    if args.scene_command == "validate":
        scene = load_scene(args.scene_path)
        return {"scene_path": str(Path(args.scene_path).resolve()), "normalized": scene.to_dict()}
    if args.scene_command == "check":
        return check_scene_project(
            args.scene_path,
            out_dir=args.out_dir,
            target=args.target,
            simulate_events=args.simulate_events,
            max_event_slots=args.max_event_slots,
            max_steps=args.max_steps,
            scenario_paths=args.scenario,
        )
    if args.scene_command == "preview":
        scene = load_scene(args.scene_path)
        target = render_scene_preview(
            scene,
            args.out,
            page_id=args.page,
            font_paths=_parse_preview_font_args(args.font),
        )
        return {
            "scene_path": str(Path(args.scene_path).resolve()),
            "page_id": args.page,
            "preview_png": str(target),
        }
    if args.scene_command == "agent-preview":
        return generate_agent_preview(
            args.scene_path,
            args.out_dir,
            target=args.target,
            page_id=args.page,
        )
    if args.scene_command == "push-preview":
        scene = load_scene(args.scene_path)
        result = push_scene_runtime_preview(
            scene,
            port=args.port,
            baud=args.baud,
            page_id=args.page,
            timeout_ms=args.timeout_ms,
            delay_ms=args.delay_ms,
        )
        return {
            "scene_path": str(Path(args.scene_path).resolve()),
            **result.to_dict(),
        }
    if args.scene_command == "build":
        scene = load_scene(args.scene_path)
        return build_scene(
            scene,
            args.seed,
            args.out,
            baseline_tft=args.baseline_tft,
            font_zi=args.font_zi,
            font_entry=args.font_entry,
        )
    if args.scene_command == "export":
        return export_scene_bundle(
            args.scene_path,
            args.out_dir,
            seed_hmi=args.seed,
            baseline_tft=args.baseline_tft,
            font_zi=args.font_zi,
            font_entry=args.font_entry,
            target=args.target,
        )
    if args.scene_command == "smoke":
        return run_scene_smoke(
            args.scene_path,
            seed_hmi=args.seed,
            baseline_tft=args.baseline_tft,
            out_dir=args.out,
            expect_json=args.expect_json,
            check_expect_path=args.check_expect,
            write_expect_path=args.write_expect,
            skip_build=args.skip_build,
            preflight=args.preflight,
            smoke=args.smoke,
            upload=args.upload,
            capture=args.capture,
            port=args.port,
            baud=args.baud,
            download_baud=args.download_baud,
            timeout_ms=args.timeout_ms,
            expected_model=args.expected_model,
            progress=args.progress,
            known_current=args.known_current,
            skip_if_identical=args.skip_if_identical,
            allow_hardware_quarantine=args.allow_hardware_quarantine,
            allow_pending_sd_recovery=args.allow_pending_sd_recovery,
        )
    if args.scene_command == "simulate":
        return simulate_scene_event(
            args.scene_path,
            args.event_path,
            out_dir=args.out_dir,
            initial_page=args.initial_page,
            max_steps=args.max_steps,
        )
    if args.scene_command == "scenario":
        return _handle_scene_scenario_command(args)
    if args.scene_command == "events":
        return _handle_scene_events_command(args)
    if args.scene_command == "assets":
        return _handle_scene_assets_command(args)
    if args.scene_command == "widgets":
        return _handle_scene_widgets_command(args)
    if args.scene_command == "pages":
        return _handle_scene_pages_command(args)
    if args.scene_command == "design":
        return _handle_scene_design_command(args)
    raise SceneError("Unsupported scene subcommand")


def _handle_scene_scenario_command(args: argparse.Namespace) -> dict[str, Any]:
    if args.scene_scenario_command == "run":
        return run_scene_scenario(
            args.scene_path,
            args.scenario_path,
            out_dir=args.out_dir,
            initial_page=args.initial_page,
            max_steps=args.max_steps,
        )
    raise SceneError("Unsupported scene scenario subcommand")


def _handle_scene_events_command(args: argparse.Namespace) -> dict[str, Any]:
    if args.scene_events_command == "list":
        return list_scene_events(args.scene_path, include_empty=not args.non_empty)
    if args.scene_events_command == "lint":
        return lint_scene_events(args.scene_path)
    if args.scene_events_command == "graph":
        return graph_scene_events(args.scene_path)
    if args.scene_events_command == "snippets":
        return list_event_command_snippets()
    if args.scene_events_command == "get":
        return {
            "scene_path": str(Path(args.scene_path).resolve()),
            "event": get_scene_event(args.scene_path, args.event_path),
        }
    if args.scene_events_command == "set":
        lines = _scene_event_lines_from_args(args.line, args.code, args.from_file)
        return {
            "scene_path": str(Path(args.scene_path).resolve()),
            "event": set_scene_event(args.scene_path, args.event_path, lines, append=args.append),
        }
    if args.scene_events_command == "append-command":
        return append_scene_event_command(
            args.scene_path,
            args.event_path,
            command=args.event_command,
            target=args.target,
            value=args.value,
            op=args.op,
            attribute=args.attribute,
            hex_bytes=args.hex_bytes,
            delay_ms=args.delay_ms,
            raw_line=args.raw_line,
            dry_run=args.dry_run,
        )
    if args.scene_events_command == "commands":
        return _handle_scene_event_commands_command(args)
    if args.scene_events_command == "clear":
        return {
            "scene_path": str(Path(args.scene_path).resolve()),
            "event": clear_scene_event(args.scene_path, args.event_path),
        }
    raise SceneError("Unsupported scene events subcommand")


def _handle_scene_event_commands_command(args: argparse.Namespace) -> dict[str, Any]:
    if args.scene_event_commands_command == "list":
        return list_scene_event_commands(args.scene_path, args.event_path)
    if args.scene_event_commands_command in {"insert", "replace"}:
        return edit_scene_event_command(
            args.scene_path,
            args.event_path,
            action=args.scene_event_commands_command,
            index=args.index,
            line=_scene_event_command_line_from_args(args),
            command=args.event_command,
            target=args.target,
            value=args.value,
            op=args.op,
            attribute=args.attribute,
            hex_bytes=args.hex_bytes,
            delay_ms=args.delay_ms,
            raw_line=args.raw_line,
            dry_run=args.dry_run,
            simulate=args.simulate,
            out_dir=args.out_dir,
            max_steps=args.max_steps,
        )
    if args.scene_event_commands_command == "delete":
        return edit_scene_event_command(
            args.scene_path,
            args.event_path,
            action="delete",
            index=args.index,
            dry_run=args.dry_run,
            simulate=args.simulate,
            out_dir=args.out_dir,
            max_steps=args.max_steps,
        )
    if args.scene_event_commands_command == "move":
        return edit_scene_event_command(
            args.scene_path,
            args.event_path,
            action="move",
            index=args.from_index,
            to_index=args.to_index,
            dry_run=args.dry_run,
            simulate=args.simulate,
            out_dir=args.out_dir,
            max_steps=args.max_steps,
        )
    raise SceneError("Unsupported scene event commands subcommand")


def _handle_scene_assets_command(args: argparse.Namespace) -> dict[str, Any]:
    if args.scene_assets_command == "list":
        return list_scene_assets(args.scene_path)
    if args.scene_assets_command == "add":
        return add_scene_asset(args.scene_path, asset_id=args.asset_id, asset=_scene_asset_payload_from_args(args))
    if args.scene_assets_command == "update":
        return update_scene_asset(args.scene_path, asset_id=args.asset_id, updates=_scene_asset_payload_from_args(args))
    if args.scene_assets_command == "delete":
        return delete_scene_asset(args.scene_path, asset_id=args.asset_id, force=args.force)
    raise SceneError("Unsupported scene assets subcommand")


def _handle_scene_project_command(args: argparse.Namespace) -> dict[str, Any]:
    if args.scene_project_command == "update":
        return update_scene_project(
            args.scene_path,
            name=args.name,
            default_page=args.default_page,
            width=args.width,
            height=args.height,
            background_color=args.background_color,
        )
    raise SceneError("Unsupported scene project subcommand")


def _handle_scene_widgets_command(args: argparse.Namespace) -> dict[str, Any]:
    if args.scene_widgets_command == "update":
        page_id, widget_id = _parse_scene_widget_path(args.widget_path)
        return update_scene_widget(
            args.scene_path,
            page_id=page_id,
            widget_id=widget_id,
            updates=_scene_widget_update_payload_from_args(args, page_id=page_id, widget_id=widget_id),
            rewrite_event_references=args.rewrite_event_references,
        )
    if args.scene_widgets_command == "delete":
        page_id, widget_id = _parse_scene_widget_path(args.widget_path)
        return delete_scene_widget(args.scene_path, page_id=page_id, widget_id=widget_id)
    if args.scene_widgets_command == "duplicate":
        page_id, widget_id = _parse_scene_widget_path(args.widget_path)
        return duplicate_scene_widget(
            args.scene_path,
            page_id=page_id,
            widget_id=widget_id,
            new_id=args.new_id,
            offset_x=args.offset_x,
            offset_y=args.offset_y,
        )
    if args.scene_widgets_command == "copy":
        page_id, widget_id = _parse_scene_widget_path(args.widget_path)
        return copy_scene_widget(args.scene_path, page_id=page_id, widget_id=widget_id)
    if args.scene_widgets_command == "cut":
        page_id, widget_id = _parse_scene_widget_path(args.widget_path)
        return cut_scene_widget(args.scene_path, page_id=page_id, widget_id=widget_id)
    if args.scene_widgets_command == "paste":
        return paste_scene_widget(
            args.scene_path,
            page_id=args.page_id,
            widget=_scene_widget_clipboard_payload_from_args(args),
            new_id=args.new_id,
            offset_x=args.offset_x,
            offset_y=args.offset_y,
            x=args.x,
            y=args.y,
        )
    if args.scene_widgets_command == "copy-to":
        source_page_id, widget_id = _parse_scene_widget_path(args.widget_path)
        return copy_scene_widget_to_page(
            args.scene_path,
            source_page_id=source_page_id,
            widget_id=widget_id,
            target_page_id=args.target_page,
            new_id=args.new_id,
            offset_x=args.offset_x,
            offset_y=args.offset_y,
            x=args.x,
            y=args.y,
        )
    if args.scene_widgets_command == "move":
        page_id, widget_id = _parse_scene_widget_path(args.widget_path)
        return move_scene_widget(args.scene_path, page_id=page_id, widget_id=widget_id, direction=args.direction)
    raise SceneError("Unsupported scene widgets subcommand")


def _handle_scene_pages_command(args: argparse.Namespace) -> dict[str, Any]:
    if args.scene_pages_command == "add":
        return add_scene_page(args.scene_path, page_id=args.page_id)
    if args.scene_pages_command == "duplicate":
        return duplicate_scene_page(args.scene_path, page_id=args.page_id, new_id=args.new_id)
    if args.scene_pages_command == "delete":
        return delete_scene_page(args.scene_path, page_id=args.page_id)
    if args.scene_pages_command == "update":
        layout = _parse_json_object_arg(args.layout_json, "--layout-json") if args.layout_json is not None else None
        return update_scene_page(args.scene_path, page_id=args.page_id, new_id=args.new_id, layout=layout)
    raise SceneError("Unsupported scene pages subcommand")


def _handle_scene_design_command(args: argparse.Namespace) -> dict[str, Any]:
    if args.scene_design_command == "move":
        page_id, widget_id = _parse_scene_widget_path(args.widget_path)
        return design_move_widget(
            args.scene_path,
            args.out_dir,
            page_id=page_id,
            widget_id=widget_id,
            x=args.x,
            y=args.y,
            dx=args.dx,
            dy=args.dy,
            snap=args.snap,
            clamp=not args.no_clamp,
            source="cli-scene-design-move",
        )
    if args.scene_design_command == "resize":
        page_id, widget_id = _parse_scene_widget_path(args.widget_path)
        return design_resize_widget(
            args.scene_path,
            args.out_dir,
            page_id=page_id,
            widget_id=widget_id,
            w=args.w,
            h=args.h,
            dw=args.dw,
            dh=args.dh,
            min_size=args.min_size,
            snap=args.snap,
            clamp=not args.no_clamp,
            source="cli-scene-design-resize",
        )
    if args.scene_design_command == "align":
        widget_targets = [_parse_scene_widget_path(value) for value in args.widget_paths]
        page_ids = {page_id for page_id, _widget_id in widget_targets}
        if len(page_ids) != 1:
            raise SceneError("scene design align requires all widget paths to be on the same page")
        page_id = next(iter(page_ids))
        return design_align_widgets(
            args.scene_path,
            args.out_dir,
            page_id=page_id,
            widget_ids=[widget_id for _page_id, widget_id in widget_targets],
            edge=args.edge,
            anchor=args.anchor,
            snap=args.snap,
            clamp=not args.no_clamp,
            source="cli-scene-design-align",
        )
    if args.scene_design_command == "distribute":
        widget_targets = [_parse_scene_widget_path(value) for value in args.widget_paths]
        page_ids = {page_id for page_id, _widget_id in widget_targets}
        if len(page_ids) != 1:
            raise SceneError("scene design distribute requires all widget paths to be on the same page")
        page_id = next(iter(page_ids))
        return design_distribute_widgets(
            args.scene_path,
            args.out_dir,
            page_id=page_id,
            widget_ids=[widget_id for _page_id, widget_id in widget_targets],
            axis=args.axis,
            snap=args.snap,
            clamp=not args.no_clamp,
            source="cli-scene-design-distribute",
        )
    if args.scene_design_command == "match-size":
        widget_targets = [_parse_scene_widget_path(value) for value in args.widget_paths]
        page_ids = {page_id for page_id, _widget_id in widget_targets}
        if len(page_ids) != 1:
            raise SceneError("scene design match-size requires all widget paths to be on the same page")
        page_id = next(iter(page_ids))
        return design_match_size_widgets(
            args.scene_path,
            args.out_dir,
            page_id=page_id,
            widget_ids=[widget_id for _page_id, widget_id in widget_targets],
            mode=args.mode,
            anchor=args.anchor,
            min_size=args.min_size,
            snap=args.snap,
            clamp=not args.no_clamp,
            source="cli-scene-design-match-size",
        )
    if args.scene_design_command == "replay":
        return replay_agent_patch(args.scene_path, args.patch_path, args.out_dir)
    raise SceneError("Unsupported scene design subcommand")


def _handle_hmi_command(args: argparse.Namespace) -> dict[str, Any]:
    if args.hmi_command == "import":
        return import_hmi_project(args.hmi_path, args.out_dir, target=args.target, overwrite=args.overwrite)

    if args.hmi_command == "roundtrip-check":
        return check_hmi_roundtrip(
            args.hmi_path,
            args.out_dir,
            target=args.target,
            overwrite=args.overwrite,
            source_tft=args.source_tft,
        )

    if args.hmi_command == "import-image":
        return import_asset(args.source, args.out)

    if args.hmi_command == "add-widget":
        scene = load_scene(args.scene)
        page = next((item for item in scene.pages if item.id == args.page), None)
        if page is None:
            raise SceneError(f"Page '{args.page}' not found in scene")
        page.widgets.append(
            WidgetSpec(
                id=args.id,
                type=args.type,
                x=args.x,
                y=args.y,
                w=args.w,
                h=args.h,
                text=args.text,
                value=args.value,
                resources=_parse_cli_map(args.resource, "--resource"),
                style=_parse_cli_map(args.style, "--style"),
                bindings=_parse_cli_map(args.binding, "--binding"),
            )
        )
        scene = validate_scene(scene.to_dict())
        save_scene_json(scene, args.scene)
        normalized_page = next(item for item in scene.pages if item.id == args.page)
        normalized_widget = normalized_page.widgets[-1]
        return {"scene_path": str(Path(args.scene).resolve()), "added_widget": {"id": args.id, "type": normalized_widget.type}}

    media_patch_commands = {"add-animation", "add-video", "add-audio"}
    widget_patch_commands = {
        "add-text",
        "add-image",
        "add-button",
        "add-number",
        "add-timer",
        *media_patch_commands,
    }
    if args.hmi_command in widget_patch_commands:
        scene = load_scene(args.scene)
        page = next((item for item in scene.pages if item.id == args.page), None)
        if page is None:
            raise SceneError(f"Page '{args.page}' not found in scene")
        style: dict[str, Any] = {}
        resources: dict[str, Any] = {}
        value = args.value
        if args.asset:
            resources["asset"] = args.asset
        if args.hmi_command in media_patch_commands:
            if args.enabled and args.disabled:
                raise SceneError(f"{args.hmi_command} accepts only one of --enabled or --disabled")
            if args.enabled or args.disabled:
                style["en"] = 1 if args.enabled else 0
            if args.path:
                resources["path"] = args.path
            if args.vid is not None:
                resources["vid"] = args.vid
            for key in ("loop", "dis", "fps"):
                raw_value = getattr(args, key, None)
                if raw_value is not None:
                    style[key] = raw_value
        if args.hmi_command == "add-timer":
            if args.enabled and args.disabled:
                raise SceneError("add-timer accepts only one of --enabled or --disabled")
            if args.tim is not None:
                value = args.tim
            if args.enabled or args.disabled:
                style["enabled"] = bool(args.enabled)
        page.widgets.append(
            WidgetSpec(
                id=args.id,
                type=args.hmi_command.replace("add-", ""),
                x=args.x,
                y=args.y,
                w=args.w,
                h=args.h,
                text=args.text,
                value=value,
                resources=resources,
                style=style,
                bindings={},
            )
        )
        save_scene_json(scene, args.scene)
        return {"scene_path": str(Path(args.scene).resolve()), "added_widget": {"id": args.id, "type": args.hmi_command.replace("add-", "")}}

    if args.hmi_command == "set-page":
        scene = load_scene(args.scene)
        if args.background_color is not None:
            scene.canvas["background_color"] = args.background_color
        if args.width is not None:
            scene.canvas["width"] = args.width
        if args.height is not None:
            scene.canvas["height"] = args.height
        save_scene_json(scene, args.scene)
        return {"scene_path": str(Path(args.scene).resolve()), "canvas": scene.canvas}

    if args.hmi_command == "build":
        scene = load_scene(args.scene)
        return build_scene(
            scene,
            args.seed,
            args.out,
            baseline_tft=args.baseline_tft,
            font_zi=args.font_zi,
            font_entry=args.font_entry,
        )

    if args.hmi_command == "donor-patch":
        return patch_hmi_donor(
            donor_hmi=None if args.donor_hmi is None else Path(args.donor_hmi).resolve(),
            out_dir=Path(args.out_dir).resolve(),
            page_entry=args.page_entry,
            delete_objects=list(args.delete_obj),
            graft_specs=list(args.graft_obj),
            move_specs=list(args.move_obj),
            int_specs=list(args.set_int),
            str_specs=list(args.set_str),
            probe_lowlevel=args.probe_lowlevel,
            probe_reopen=args.probe_reopen,
            spec=None if args.spec_json is None else json.loads(Path(args.spec_json).read_text(encoding="utf-8")),
        )

    if args.hmi_command == "reopen-safe-fixture":
        if args.corpus_root:
            return generate_reopen_safe_fixture(
                args.control_type,
                args.out_dir,
                corpus_root=args.corpus_root,
            )
        return generate_reopen_safe_fixture(args.control_type, args.out_dir)

    if args.hmi_command == "lowlevel-compatible-fixture":
        if args.corpus_root:
            return generate_lowlevel_compatible_fixture(
                args.control_type,
                args.out_dir,
                corpus_root=args.corpus_root,
            )
        return generate_lowlevel_compatible_fixture(args.control_type, args.out_dir)

    if args.hmi_command == "preview-pa":
        return render_pa_preview(
            args.pa,
            args.out,
            width=args.width,
            height=args.height,
            show_labels=not args.no_labels,
            assets_dir=args.assets_dir,
            font_paths=_parse_preview_font_args(args.font),
        )

    if args.hmi_command == "preview":
        return render_hmi_preview(
            args.hmi,
            args.out,
            page=args.page,
            width=args.width,
            height=args.height,
            show_labels=not args.no_labels,
            font_paths=_parse_preview_font_args(args.font),
        )

    raise SceneError("Unsupported hmi subcommand")


def _handle_widgets_command(args: argparse.Namespace) -> dict[str, Any]:
    if args.widgets_command == "list":
        return {
            "widgets": list_widget_capabilities(
                support=args.support,
                include_aliases=args.include_aliases,
            )
        }
    if args.widgets_command == "show":
        return {
            "widget": get_widget_capability(
                args.widget_type,
                include_aliases=args.include_aliases,
            )
        }
    if args.widgets_command == "manifest":
        return get_capability_manifest(include_aliases=args.include_aliases)
    if args.widgets_command == "template":
        return get_widget_template(args.widget_type, widget_id=args.widget_id, x=args.x, y=args.y)
    if args.widgets_command == "templates":
        return list_widget_templates()
    raise SceneError("Unsupported widgets subcommand")


def _handle_editor_command(args: argparse.Namespace) -> dict[str, Any]:
    if args.editor_command == "capabilities":
        return editor_capability_manifest()
    if args.editor_command == "audit":
        return editor_completion_audit()
    raise SceneError("Unsupported editor subcommand")


def _handle_target_command(args: argparse.Namespace) -> dict[str, Any]:
    if args.target_command == "summary":
        return get_current_target_status_summary()
    if args.target_command == "audit":
        return get_current_target_completion_audit()
    if args.target_command == "calibration":
        return get_builder_calibration_status()
    if args.target_command == "frontier":
        return get_page1_filebrowser_frontier_report()
    if args.target_command == "compare-targets":
        return get_page1_filebrowser_native_init_compare_targets_report()
    if args.target_command == "next-probe":
        return get_next_live_probe_bundle()
    if args.target_command == "check-next-probe":
        return check_next_probe_invariants(args.file)
    if args.target_command == "run-next-probe":
        return run_next_live_probe(
            preflight=args.preflight,
            live_smoke=args.live_smoke,
            upload=args.upload,
            allow_hardware_quarantine=args.allow_hardware_quarantine,
            allow_pending_sd_recovery=args.allow_pending_sd_recovery,
            capture=args.capture,
            progress=args.progress,
            port=args.port,
            baud=args.baud,
            download_baud=args.download_baud,
            timeout_ms=args.timeout_ms,
            out_dir=args.out_dir,
            result_json=args.result_json,
        )
    raise SceneError("Unsupported target subcommand")


def _handle_capabilities_command(args: argparse.Namespace) -> dict[str, Any]:
    if args.widget:
        return {
            "widget": get_widget_capability(
                args.widget,
                include_aliases=args.include_aliases,
            )
        }
    if args.support:
        return {
            "widgets": list_widget_capabilities(
                support=args.support,
                include_aliases=args.include_aliases,
            )
        }
    return get_capability_manifest(include_aliases=args.include_aliases)


def _handle_font_command(args: argparse.Namespace) -> dict[str, Any]:
    if args.font_command == "build-zicli":
        path = ensure_zicli_built()
        return {"zicli": str(path)}

    if args.font_command == "generate-zi":
        return generate_zi(
            out_path=args.out,
            font_name=args.font_name,
            font_file=args.font_file,
            name=args.name,
            codepage=args.codepage,
            height=args.height,
            font_size=args.font_size,
            text=args.text,
            text_files=args.text_file,
            include_ascii=args.include_ascii,
            full_codepage=args.full_codepage,
            offset_x=args.offset_x,
            offset_y=args.offset_y,
        )

    if args.font_command == "from-scene":
        result = generate_zi_from_scene(
            args.scene,
            out_path=args.out,
            font_name=args.font_name,
            font_file=args.font_file,
            name=args.name,
            codepage=args.codepage,
            height=args.height,
            font_size=args.font_size,
            include_ascii=args.include_ascii,
            full_codepage=args.full_codepage,
            offset_x=args.offset_x,
            offset_y=args.offset_y,
        )
        result["scene_path"] = str(Path(args.scene).resolve())
        return result

    if args.font_command == "replace-hmi":
        return replace_hmi_font(args.hmi, args.zi, args.out, entry_name=args.entry)

    raise FontToolchainError("Unsupported font subcommand")


def _handle_tft_command(args: argparse.Namespace) -> dict[str, Any]:
    if args.tft_command == "build":
        if not args.baseline_tft:
            raise SceneError("tft build requires --baseline-tft")
        scene = load_scene(args.scene)
        result = build_scene(
            scene,
            args.seed,
            args.out,
            baseline_tft=args.baseline_tft,
            font_zi=args.font_zi,
            font_entry=args.font_entry,
        )
        result["mode"] = "experimental_scene_tft_build"
        return result
    if args.tft_command == "inspect":
        return inspect_tft(args.file)
    if args.tft_command == "reverse-tail":
        return reverse_tft_tail(
            args.file,
            hmi_pa_path=args.hmi_pa,
            install_dir=args.install_dir,
            context_bytes=args.context_bytes,
        )
    if args.tft_command == "event-index":
        if args.tft_event_index_command == "inspect":
            return inspect_tft_event_index(
                args.hmi,
                args.tft,
                force_post_primary_page_load=args.force_post_primary_page_load,
                out_path=args.out,
            )
        if args.tft_event_index_command == "batch":
            return inspect_tft_event_index_batch(
                args.paths,
                force_post_primary_page_load=args.force_post_primary_page_load,
                include_object_only=args.include_object_only,
                out_path=args.out,
            )
        raise SceneError("Unsupported tft event-index subcommand")
    if args.tft_command == "list-models":
        return {"models": list_supported_tft_models()}
    if args.tft_command == "hash-name":
        try:
            value = object_name_hash(args.name, width=args.width)
            padded = args.name.encode("ascii").ljust(args.width, b"\x00")
        except (UnicodeEncodeError, ValueError) as exc:
            raise TftToolchainError(str(exc)) from exc
        return {
            "name": args.name,
            "width": args.width,
            "padded_hex": padded.hex(" "),
            "hash": value,
            "hash_hex": f"0x{value:08X}",
        }
    if args.tft_command == "pack-fonts":
        return pack_tft_font_run(args.font, out_path=args.out)
    if args.tft_command == "inspect-font-run":
        return inspect_tft_font_run(args.file)
    if args.tft_command == "patch-font":
        return patch_tft_font(
            args.baseline_tft,
            font_path=args.font,
            out_tft=args.out,
        ).to_dict()
    if args.tft_command == "health":
        return probe_serial_health(
            port=args.port,
            baud=args.baud,
            timeout_ms=args.timeout_ms,
            expected_model=args.expected_model,
            verbose=args.verbose,
        )
    if args.tft_command == "preflight":
        expected_model = str(args.expected_model or "") or None
        checksum = inspect_tft_checksum(args.file)
        quarantine_reason = _dangerous_tft_quarantine_reason(args.file)
        sd_recovery_reason = pending_sd_recovery_reason()
        build_manifest = _load_build_manifest_metadata(args.file)
        health = probe_serial_health(
            port=args.port,
            baud=args.baud,
            timeout_ms=args.timeout_ms,
            expected_model=expected_model,
            verbose=args.verbose,
        )
        checksum_ok = bool(checksum.get("valid"))
        serial_ready = bool(health["summary"].get("public_upload_ready"))
        blocked_reason = quarantine_reason or sd_recovery_reason
        ready = checksum_ok and serial_ready and not blocked_reason
        if blocked_reason:
            diagnosis = blocked_reason
        elif ready:
            diagnosis = "TFT checksum is valid and serial runtime is ready for public upload."
        elif not checksum_ok and not serial_ready:
            diagnosis = "TFT checksum is invalid and serial runtime is not ready for public upload."
        elif not checksum_ok:
            diagnosis = "TFT checksum is invalid; do not upload until it is repaired."
        else:
            diagnosis = health["summary"]["diagnosis"]
        return {
            "file": str(Path(args.file).resolve()),
            "port": args.port,
            "baud": args.baud,
            "expected_model": expected_model,
            "summary": {
                "healthy": ready,
                "ready": ready,
                "tft_checksum_valid": checksum_ok,
                "serial_upload_ready": serial_ready,
                "hardware_quarantine_blocked": bool(quarantine_reason),
                "sd_recovery_blocked": bool(sd_recovery_reason),
                "diagnosis": diagnosis,
            },
            "checksum": checksum,
            "build_manifest": build_manifest,
            "dangerous_tft_quarantine_reason": quarantine_reason,
            "sd_recovery_pending_reason": sd_recovery_reason,
            "serial_health": health,
        }
    if args.tft_command == "readiness":
        checksum = inspect_tft_checksum(args.file)
        build_manifest = _load_build_manifest_metadata(args.file)
        quarantine_reason = _dangerous_tft_quarantine_reason(args.file)
        sd_recovery_reason = pending_sd_recovery_reason()
        checksum_ok = bool(checksum.get("valid"))
        delivery_status = build_manifest.get("delivery_status") if build_manifest else None
        manifest_ready = None
        manifest_reason = None
        if isinstance(delivery_status, dict):
            ready_value = delivery_status.get("ready_for_live_upload")
            manifest_ready = bool(ready_value) if isinstance(ready_value, bool) else None
            raw_reason = delivery_status.get("reason")
            manifest_reason = str(raw_reason) if raw_reason else None
        ready = checksum_ok and not quarantine_reason and not sd_recovery_reason and (manifest_ready is not False)
        if not checksum_ok:
            diagnosis = "TFT checksum is invalid; do not upload until it is repaired."
        elif quarantine_reason:
            diagnosis = quarantine_reason
        elif sd_recovery_reason:
            diagnosis = sd_recovery_reason
        elif manifest_ready is False and manifest_reason:
            diagnosis = manifest_reason
        else:
            diagnosis = "offline build appears eligible for live upload; run `tft preflight` next for serial health."
        return {
            "file": str(Path(args.file).resolve()),
            "summary": {
                "ready_for_live_upload": ready,
                "tft_checksum_valid": checksum_ok,
                "build_manifest_present": build_manifest is not None,
                "hardware_quarantine_blocked": bool(quarantine_reason),
                "sd_recovery_blocked": bool(sd_recovery_reason),
                "diagnosis": diagnosis,
            },
            "checksum": checksum,
            "build_manifest": build_manifest,
            "dangerous_tft_quarantine_reason": quarantine_reason,
            "sd_recovery_pending_reason": sd_recovery_reason,
        }
    if args.tft_command == "upload":
        preflight_checksum = None
        preflight_health = None
        skip_current_decision = None
        if not (args.allow_hardware_quarantine or args.allow_quarantined_touch_capture):
            quarantine_reason = _dangerous_tft_quarantine_reason(args.file)
            if quarantine_reason:
                raise TftToolchainError(
                    "TFT upload blocked: generated TFT is quarantined after a known runtime wedge. "
                    f"{quarantine_reason} "
                    "Use --allow-hardware-quarantine only with explicit recovery planning."
                )
        if not args.allow_pending_sd_recovery:
            sd_recovery_reason = pending_sd_recovery_reason()
            if sd_recovery_reason:
                raise TftToolchainError(
                    "TFT upload blocked: SD-card recovery state is still pending. "
                    f"{sd_recovery_reason} "
                    "Use --allow-pending-sd-recovery only after the card is removed and the panel was power-cycled."
                )
        run_checksum_preflight = args.require_valid_checksum or not args.no_preflight
        run_runtime_preflight = args.require_runtime_healthy or not args.no_preflight
        expected_model = str(args.expected_model or "") or None
        if run_checksum_preflight:
            preflight_checksum = inspect_tft_checksum(args.file)
            if not preflight_checksum["valid"]:
                raise TftToolchainError(
                    "TFT upload preflight failed: checksum invalid "
                    f"(stored={preflight_checksum['stored_hex']}, "
                    f"calculated={preflight_checksum['calculated_hex']})"
                )
        if args.skip_if_current:
            skip_current_decision = evaluate_skip_if_current(
                args.file,
                manifest_path=args.current_manifest,
                port=args.port,
                baud=args.baud,
                expected_model=expected_model,
            )
            if skip_current_decision["skip"]:
                result = _skipped_current_upload_result(
                    args,
                    skip_current_decision=skip_current_decision,
                )
                if preflight_checksum is not None:
                    result["preflight_checksum"] = preflight_checksum
                if args.verify_after_upload:
                    result["post_upload_verification"] = _run_post_upload_verification(args)
                return result
        if run_runtime_preflight:
            preflight_health = probe_serial_health(
                port=args.port,
                baud=args.baud,
                timeout_ms=args.health_timeout_ms,
                expected_model=expected_model,
                verbose=args.verbose,
            )
            summary = preflight_health["summary"]
            if not summary["public_upload_ready"]:
                raise SerialTransportError(
                    "TFT upload preflight failed: "
                    f"{summary['diagnosis']} "
                    f"(connect_ok={summary['connect_ok']}, runtime_ok={summary['runtime_ok']}, "
                    f"model={summary.get('model')!r})"
                )
        progress = _make_upload_progress() if args.progress else None
        result = upload_tft(
            args.file,
            port=args.port,
            baud=args.baud,
            download_baud=args.download_baud,
            chunk_size=args.chunk_size,
            timeout_ms=args.timeout_ms,
            address=args.address,
            prepare_delay_ms=args.prepare_delay_ms,
            prepare_wait_ms=args.prepare_wait_ms,
            known_current=args.known_current,
            skip_if_identical=args.skip_if_identical,
            allow_unsafe_chunk_size=args.allow_unsafe_chunk_size,
            progress=progress,
        ).to_dict()
        if skip_current_decision is not None:
            result["skip_current_manifest"] = skip_current_decision
        if preflight_checksum is not None:
            result["preflight_checksum"] = preflight_checksum
        if preflight_health is not None:
            result["preflight_health"] = preflight_health
        if args.verify_after_upload:
            result["post_upload_verification"] = _run_post_upload_verification(args)
        verification_ok = _post_upload_verification_ok(result)
        if (
            not args.no_record_current
            and not result.get("skipped")
            and result.get("file_path")
            and verification_ok
        ):
            try:
                result["last_upload_manifest"] = write_last_upload_manifest(
                    result["file_path"],
                    manifest_path=args.current_manifest,
                    port=args.port,
                    baud=args.baud,
                    download_baud=args.download_baud,
                    chunk_size=args.chunk_size,
                    target_model=expected_model,
                    tool_version=__version__,
                    git_head=_current_git_head(),
                    upload_result=result,
                )
            except OSError as exc:
                warnings = result.setdefault("warnings", [])
                if isinstance(warnings, list):
                    warnings.append(f"failed to write last-upload manifest: {exc}")
        return result
    if args.tft_command == "plan-upload":
        return plan_upload(
            args.file,
            baseline_path=args.baseline,
            chunk_size=args.chunk_size,
            download_baud=args.download_baud,
        ).to_dict()
    if args.tft_command == "compare-cases":
        return compare_case_folder(
            args.case_root,
            out_dir=args.out,
            baseline_case=args.baseline_case,
            install_dir=args.install_dir,
            context_bytes=args.context_bytes,
            diff_run_limit=args.diff_run_limit,
        )
    if args.tft_command == "patch-basic":
        return patch_basic_tft(
            args.baseline_tft,
            baseline_pa=args.baseline_pa,
            target_pa=args.target_pa,
            out_tft=args.out,
            checksum_mode=args.checksum_mode,
        ).to_dict()
    if args.tft_command == "patch-add-object":
        return patch_added_object_tft(
            args.baseline_tft,
            baseline_pa=args.baseline_pa,
            target_pa=args.target_pa,
            out_tft=args.out,
        ).to_dict()
    if args.tft_command == "rebuild-page":
        return patch_rebuild_page_tft(
            args.baseline_tft,
            seed_pa=args.seed_pa,
            target_pa=args.target_pa,
            out_tft=args.out,
        ).to_dict()
    if args.tft_command == "checksum":
        return inspect_tft_checksum(args.file)
    if args.tft_command == "hmisafe-finalize":
        result = finalize_tft_file(args.input, args.out)
        if args.final:
            final_data = Path(args.final).read_bytes()
            ours_data = Path(args.out).read_bytes()
            result["diff"] = {"official_final": args.final, **diff_hmisafe_bytes(ours_data, final_data)}
        return result
    if args.tft_command == "hmisafe-verify":
        return verify_final_tft_file(args.file)
    raise SceneError("Unsupported tft subcommand")


def _make_upload_progress():
    last = {"t": 0.0}

    def progress(bytes_sent: int, total: int, chunks_sent: int) -> None:
        now = time.monotonic()
        if now - last["t"] < 1.0 and bytes_sent < total:
            return
        last["t"] = now
        ratio = (bytes_sent / total * 100.0) if total else 100.0
        print(
            f"upload {bytes_sent}/{total} bytes ({ratio:5.1f}%), chunks={chunks_sent}",
            file=sys.stderr,
            flush=True,
        )

    return progress


def _touch_capture_quarantine_reason(tft_file: str | Path) -> str | None:
    tft_path = Path(tft_file)
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
                return f"sibling manifest {manifest_path} contains widget {widget.get('id')!r} type touch-capture."

    for item in manifest.get("tft_patch", {}).get("objects", []):
        if item.get("type") == "\x05":
            return f"sibling manifest {manifest_path} contains object {item.get('name')!r} type 0x05."
    return None


def _manifest_hardware_quarantine_reason(tft_file: str | Path) -> str | None:
    tft_path = Path(tft_file)
    manifest_path = tft_path.with_name("manifest.json")
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    quarantine = manifest.get("hardware_quarantine")
    if not isinstance(quarantine, dict):
        return None
    if not quarantine.get("active"):
        return None
    reason = str(quarantine.get("reason") or "").strip()
    patch_path = str(quarantine.get("patch_path") or "").strip()
    if not reason:
        if patch_path:
            return f"sibling manifest {manifest_path} declares an active hardware quarantine (patch_path={patch_path})."
        return f"sibling manifest {manifest_path} declares an active hardware quarantine."
    if patch_path:
        return f"sibling manifest {manifest_path} declares an active hardware quarantine (patch_path={patch_path}): {reason}"
    return f"sibling manifest {manifest_path} declares an active hardware quarantine: {reason}"


def _load_build_manifest_metadata(tft_file: str | Path) -> dict[str, Any] | None:
    tft_path = Path(tft_file)
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


def _case83_event_quarantine_reason(tft_file: str | Path) -> str | None:
    return None


def _dangerous_tft_quarantine_reason(tft_file: str | Path) -> str | None:
    return (
        _manifest_hardware_quarantine_reason(tft_file)
        or _touch_capture_quarantine_reason(tft_file)
        or _case83_event_quarantine_reason(tft_file)
    )


def _skipped_current_upload_result(
    args: argparse.Namespace,
    *,
    skip_current_decision: dict[str, object],
) -> dict[str, Any]:
    candidate = skip_current_decision["candidate"]
    if not isinstance(candidate, dict):
        raise TftToolchainError("Internal error: skip-if-current decision has no candidate fingerprint")
    return {
        "port": args.port,
        "initial_baud": args.baud,
        "download_baud": args.download_baud,
        "file_path": candidate["path"],
        "file_size": candidate["size"],
        "bytes_sent": 0,
        "chunks_sent": 0,
        "chunk_size": args.chunk_size,
        "elapsed_s": 0.0,
        "address": args.address,
        "prepare_delay_ms": args.prepare_delay_ms,
        "prepare_wait_ms": args.prepare_wait_ms,
        "skipped": True,
        "skip_reason": "candidate matches last successful upload manifest; upload skipped",
        "public_whmi_chunk_size": PUBLIC_WHMI_CHUNK_SIZE,
        "skip_current_manifest": skip_current_decision,
    }


def _run_post_upload_verification(args: argparse.Namespace) -> dict[str, Any]:
    wait_ms = max(0, int(args.verify_wait_ms))
    if wait_ms:
        time.sleep(wait_ms / 1000.0)

    health = _probe_post_upload_serial_health(args)
    get_checks = [_run_verify_get(args, item) for item in args.verify_get]
    runtime_steps = [_run_verify_step(args, item, index=index + 1) for index, item in enumerate(args.verify_step)]
    camera = _capture_post_upload_frame(args) if args.verify_capture else None
    health_ok = bool(health.get("summary", {}).get("healthy"))
    get_ok = all(item["ok"] for item in get_checks)
    runtime_steps_ok = all(item["ok"] for item in runtime_steps)
    camera_ok = camera is None or bool(camera.get("ok"))
    return {
        "wait_ms": wait_ms,
        "serial_health": health,
        "get_checks": get_checks,
        "runtime_steps": runtime_steps,
        "camera": camera,
        "summary": {
            "ok": health_ok and get_ok and runtime_steps_ok and camera_ok,
            "serial_health_ok": health_ok,
            "get_checks_ok": get_ok,
            "runtime_steps_ok": runtime_steps_ok,
            "camera_ok": camera_ok,
            "camera_captured": bool(camera and camera.get("ok")),
        },
    }


def _probe_post_upload_serial_health(args: argparse.Namespace) -> dict[str, Any]:
    expected_model = str(args.expected_model or "") or None
    attempts = max(1, int(getattr(args, "verify_health_attempts", 1) or 1))
    retry_delay_ms = max(0, int(getattr(args, "verify_health_retry_delay_ms", 0) or 0))
    history: list[dict[str, Any]] = []
    for attempt in range(1, attempts + 1):
        health = probe_serial_health(
            port=args.port,
            baud=args.baud,
            timeout_ms=args.health_timeout_ms,
            expected_model=expected_model,
            verbose=args.verbose,
        )
        summary = health.get("summary", {})
        if bool(summary.get("healthy")) or attempt >= attempts:
            health["attempt"] = attempt
            health["attempts"] = attempts
            if history:
                health["retry_history"] = history
            return health
        history.append(
            {
                "attempt": attempt,
                "summary": summary,
            }
        )
        if retry_delay_ms:
            time.sleep(retry_delay_ms / 1000.0)

    raise TftToolchainError("Internal error: post-upload serial health produced no result")


def _run_verify_get(args: argparse.Namespace, expression: str) -> dict[str, Any]:
    target, expected = _parse_verify_get_expression(expression)
    command_text = build_get(target)
    config = SerialConfig(
        port=args.port,
        baud=args.baud,
        timeout_ms=args.health_timeout_ms,
        verbose=args.verbose,
    )
    payload, response = SerialTransport(config).transact(command_text)
    parsed = parse_response(response).to_dict()
    actual = parsed.get("value")
    readable = parsed.get("kind") not in {None, "none", "invalid_reference"}
    value_ok = True if expected is None else actual == expected
    return {
        "target": target,
        "expected": expected,
        "command": command_text,
        "sent_hex": payload.hex(" "),
        "response": parsed,
        "actual": actual,
        "ok": readable and value_ok,
    }


def _parse_verify_get_expression(expression: str) -> tuple[str, Any | None]:
    if "=" not in expression:
        target = expression.strip()
        expected = None
    else:
        target, raw_expected = expression.split("=", 1)
        target = target.strip()
        expected = _coerce_cli_value(raw_expected.strip())
    if not target:
        raise TftToolchainError("--verify-get target cannot be empty")
    return target, expected


def _run_verify_step(args: argparse.Namespace, expression: str, *, index: int) -> dict[str, Any]:
    step = _parse_verify_step_expression(expression, index=index)
    delay_ms = max(0, int(step.get("delay_ms") or 0))
    if delay_ms:
        time.sleep(delay_ms / 1000.0)

    attempts = max(1, int(step.get("attempts") or 1))
    retry_delay_ms = max(0, int(step.get("retry_delay_ms") or 100))
    config = SerialConfig(
        port=args.port,
        baud=args.baud,
        timeout_ms=args.health_timeout_ms,
        verbose=args.verbose,
    )
    last_result: dict[str, Any] | None = None
    retry_history: list[dict[str, Any]] = []
    for attempt in range(1, attempts + 1):
        payload, response = SerialTransport(config).transact(str(step["command"]))
        parsed = parse_response(response).to_dict()
        result = _evaluate_verify_step_response(step, payload, parsed, attempt=attempt, attempts=attempts)
        if result["ok"] or attempt >= attempts:
            if retry_history:
                result["retry_history"] = retry_history
            return result
        retry_history.append(
            {
                "attempt": attempt,
                "ok": result["ok"],
                "response": result["response"],
                "mismatches": result.get("mismatches", []),
            }
        )
        if retry_delay_ms:
            time.sleep(retry_delay_ms / 1000.0)
        last_result = result

    if last_result is None:
        raise TftToolchainError("Internal error: verify step produced no result")
    return last_result


def _parse_verify_step_expression(expression: str, *, index: int) -> dict[str, Any]:
    raw = expression.strip()
    if not raw:
        raise TftToolchainError("--verify-step cannot be empty")
    if raw.startswith("{"):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TftToolchainError(f"--verify-step #{index} JSON is invalid: {exc}") from exc
        if not isinstance(parsed, dict):
            raise TftToolchainError(f"--verify-step #{index} JSON must be an object")
        step = dict(parsed)
    elif "=>" in raw:
        command, expected = raw.split("=>", 1)
        step = {"command": command.strip()}
        step.update(_parse_verify_step_expected(expected, command=command))
    else:
        step = {"command": raw}
    command = str(step.get("command") or "").strip()
    if not command:
        raise TftToolchainError(f"--verify-step #{index} command cannot be empty")
    step["command"] = command
    step.setdefault("label", f"step_{index}")
    return step


def _parse_verify_step_expected(expected: str, *, command: str) -> dict[str, Any]:
    raw_expected = expected.strip()
    if not raw_expected:
        raise TftToolchainError("--verify-step shorthand expected value cannot be empty")
    lowered = raw_expected.lower()
    if lowered.startswith("hex:"):
        return {"expected_hex": raw_expected[4:].strip()}
    if lowered.startswith("ascii:"):
        return {"expected_ascii_preview": raw_expected[6:]}
    if lowered.startswith("kind:"):
        return {"expected_kind": raw_expected[5:].strip()}
    if lowered.startswith("value:"):
        raw_expected = raw_expected[6:].strip()
    value = _coerce_cli_value(raw_expected)
    result: dict[str, Any] = {"expected_value": value}
    command_text = command.strip().lower()
    if command_text.startswith("get "):
        result["expected_kind"] = "number" if isinstance(value, int) and not isinstance(value, bool) else "string"
    elif command_text == "sendme" and isinstance(value, int) and not isinstance(value, bool):
        result["expected_kind"] = "page_id"
    return result


def _evaluate_verify_step_response(
    step: dict[str, Any],
    payload: bytes,
    parsed: dict[str, Any],
    *,
    attempt: int,
    attempts: int,
) -> dict[str, Any]:
    kind = parsed.get("kind")
    value = parsed.get("value")
    response_hex = _normalize_hex_text(str(parsed.get("hex", "")))
    mismatches: list[str] = []

    expected_kind = step.get("expected_kind")
    expected_value = step.get("expected_value")
    expected_hex = step.get("expected_hex")
    expected_ascii_preview = step.get("expected_ascii_preview")
    has_expectations = any(
        key in step
        for key in (
            "expected_kind",
            "expected_value",
            "expected_hex",
            "expected_ascii_preview",
        )
    )
    expect_response = bool(step.get("expect_response", True))

    if expected_kind is not None and kind != expected_kind:
        mismatches.append(f"expected kind {expected_kind!r}, got {kind!r}")
    if "expected_value" in step and value != expected_value:
        mismatches.append(f"expected value {expected_value!r}, got {value!r}")
    if expected_hex is not None and response_hex != _normalize_hex_text(str(expected_hex)):
        mismatches.append(f"expected hex {_normalize_hex_text(str(expected_hex))!r}, got {response_hex!r}")
    if expected_ascii_preview is not None and parsed.get("ascii_preview") != expected_ascii_preview:
        mismatches.append(
            f"expected ascii_preview {expected_ascii_preview!r}, got {parsed.get('ascii_preview')!r}"
        )
    if expect_response and not has_expectations and kind in {None, "none", "invalid_reference", "invalid_waveform"}:
        mismatches.append(f"expected readable response, got {kind!r}")
    if expect_response and has_expectations and kind == "none":
        mismatches.append("expected a response, got none")

    result: dict[str, Any] = {
        "label": step.get("label"),
        "command": step["command"],
        "sent_hex": payload.hex(" "),
        "response": parsed,
        "attempt": attempt,
        "attempts": attempts,
        "expect_response": expect_response,
        "ok": not mismatches,
    }
    for key in (
        "expected_kind",
        "expected_value",
        "expected_hex",
        "expected_ascii_preview",
        "delay_ms",
        "retry_delay_ms",
    ):
        if key in step:
            result[key] = step[key]
    if mismatches:
        result["mismatches"] = mismatches
    return result


def _normalize_hex_text(value: str) -> str:
    compact = value.lower().replace("0x", " ").replace(",", " ")
    parts = compact.split()
    if not parts:
        return ""
    return " ".join(f"{int(part, 16):02x}" for part in parts)


def _post_upload_verification_ok(result: dict[str, Any]) -> bool:
    verification = result.get("post_upload_verification")
    if verification is None:
        return True
    return bool(verification.get("summary", {}).get("ok"))


def _capture_post_upload_frame(args: argparse.Namespace) -> dict[str, Any]:
    script_path = Path.cwd() / "tools" / "capture_hmi_screen.py"
    if not script_path.exists():
        return {
            "ok": False,
            "error": f"capture helper not found: {script_path}",
        }

    output_path = _post_upload_capture_output_path(args)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(script_path),
        "--camera-index",
        str(args.verify_camera_index),
        "--backend",
        args.verify_camera_backend,
        "--warmup-frames",
        str(args.verify_camera_warmup_frames),
        "--output-dir",
        str(output_path.parent),
        "--filename",
        output_path.name,
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=Path.cwd(),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(1, int(args.verify_capture_timeout_ms)) / 1000.0,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "ok": False,
            "path": str(output_path),
            "command": command,
            "error": str(exc),
        }

    parsed: dict[str, Any] | None = None
    if completed.stdout.strip():
        try:
            parsed = json.loads(completed.stdout)
        except json.JSONDecodeError:
            parsed = None
    exists = output_path.exists()
    result = {
        "ok": completed.returncode == 0 and exists,
        "path": str(output_path),
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    if parsed is not None:
        result["capture"] = parsed
    if exists:
        result["bytes"] = output_path.stat().st_size
    if completed.returncode != 0 and not result.get("error"):
        result["error"] = "capture helper returned non-zero"
    elif not exists and not result.get("error"):
        result["error"] = "capture output was not created"
    return result


def _post_upload_capture_output_path(args: argparse.Namespace) -> Path:
    if args.verify_capture_output:
        return Path(args.verify_capture_output).resolve()
    stem = Path(args.file).stem or "upload"
    filename = f"{stem}_verify_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
    return (Path.cwd() / "reverse_usarthmi" / "upload_verify_captures" / filename).resolve()


def _current_git_head() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=Path.cwd(),
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = completed.stdout.strip()
    return value or None


def _build_command_text(args: argparse.Namespace) -> str:
    if args.command == "raw":
        return build_raw(args.raw_command)
    if args.command == "connect":
        return "connect"
    if args.command == "sendme":
        return "sendme"
    if args.command == "get":
        return build_get(args.target)
    if args.command == "set":
        return build_set(args.target, args.value)
    if args.command == "page":
        return build_page(args.page_id)
    if args.command == "ref":
        return build_ref(args.object_name)
    if args.command == "vis":
        return build_vis(args.object_name, args.state)
    if args.command == "tsw":
        return build_tsw(args.object_name, args.state)
    if args.command == "click":
        return build_click(args.object_name, args.event)
    if args.command == "dim":
        return build_dim(args.value)
    raise ProtocolError(f"Unsupported command: {args.command}")


def _add_font_generation_args(parser: argparse.ArgumentParser, include_scene: bool = False) -> None:
    if include_scene:
        parser.add_argument("--scene", required=True, help="Scene JSON/YAML file")
    parser.add_argument("--out", required=True, help="Output .zi file")
    parser.add_argument("--font-name", help="Installed font family name")
    parser.add_argument("--font-file", help="Font file path such as simsun.ttc")
    parser.add_argument("--name", help="Stored .zi font name")
    parser.add_argument("--codepage", default="utf-8", help="ascii, gb2312, utf-8")
    parser.add_argument("--height", type=int, default=32, help="Glyph height in pixels")
    parser.add_argument("--font-size", type=float, help="Rendering font size in pixels")
    if not include_scene:
        parser.add_argument("--text", help="Inline text to include in the font subset")
    parser.add_argument("--text-file", action="append", help="Text file to include in the font subset")
    parser.add_argument("--include-ascii", dest="include_ascii", action="store_true", default=True, help="Include ASCII 32..126")
    parser.add_argument("--no-ascii", dest="include_ascii", action="store_false", help="Do not auto-include ASCII 32..126")
    parser.add_argument("--full-codepage", action="store_true", help="Generate every character in the selected codepage")
    parser.add_argument("--offset-x", type=float, default=0.0, help="Glyph x offset")
    parser.add_argument("--offset-y", type=float, default=0.0, help="Glyph y offset")


def _add_scene_asset_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--id", dest="asset_doc_id", help="Optional stored asset id; defaults to the asset key")
    parser.add_argument("--source", help="Source image path")
    parser.add_argument("--normal", help="Normal-state image path")
    parser.add_argument("--pressed", help="Pressed-state image path")
    parser.add_argument("--disabled", help="Disabled-state image path")


def _add_scene_event_command_patch_args(parser: argparse.ArgumentParser) -> None:
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--line", help="Raw event source line to insert/replace")
    source.add_argument("--from-file", help="Read one event source line from a file")
    parser.add_argument(
        "--command",
        dest="event_command",
        choices=("page", "ref", "vis", "tsw", "click", "get", "set", "printh", "delay", "raw"),
        help="Structured event command family; required when --line/--from-file is not used",
    )
    parser.add_argument("--target", help="Target page/object/attribute")
    parser.add_argument("--value", help="Command value, for example 0, 1, or text")
    parser.add_argument(
        "--op",
        default="=",
        choices=("=", "++", "--", "+=", "-="),
        help="Assignment operator used by --command set",
    )
    parser.add_argument(
        "--attribute",
        default="val",
        help="Attribute appended to --target for get/set when target has no dot",
    )
    parser.add_argument("--hex", dest="hex_bytes", help="Hex byte string for --command printh")
    parser.add_argument("--delay-ms", type=int, help="Delay in milliseconds for --command delay")
    parser.add_argument("--raw-line", help="Raw event line for --command raw")
    _add_scene_event_patch_common_args(parser)


def _add_scene_event_patch_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dry-run", action="store_true", help="Return patch/diff without modifying the scene")
    parser.add_argument("--simulate", action="store_true", help="Run before/after offline simulation")
    parser.add_argument("--out-dir", help="Write event_patch.json, event_diff.json, and optional simulation bundles")
    parser.add_argument("--max-steps", type=int, default=128, help="Maximum simulated event command lines")


def _parse_preview_font_args(values: list[str] | None) -> dict[int, Path]:
    fonts: dict[int, Path] = {}
    next_id = 0
    for value in values or []:
        if "=" in value:
            raw_id, raw_path = value.split("=", 1)
            font_id = int(raw_id.strip())
            path = raw_path.strip()
        else:
            font_id = next_id
            path = value
        fonts[font_id] = Path(path).resolve()
        next_id = max(next_id, font_id + 1)
    return fonts


def _parse_cli_map(values: list[str] | None, option_name: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in values or []:
        if "=" not in item:
            raise SceneError(f"{option_name} expects key=value, got '{item}'")
        key, raw_value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise SceneError(f"{option_name} key cannot be empty")
        result[key] = _coerce_cli_value(raw_value.strip())
    return result


def _scene_event_lines_from_args(lines: list[str], code: str | None, from_file: str | None = None) -> list[str]:
    result: list[str] = []
    if from_file:
        result.extend(line.rstrip() for line in Path(from_file).read_text(encoding="utf-8").splitlines() if line.strip())
    if code:
        result.extend(line.rstrip() for line in code.splitlines() if line.strip())
    result.extend(line.rstrip() for line in lines if line.strip())
    if not result:
        raise SceneError("scene events set requires --line or --code")
    return result


def _scene_event_command_line_from_args(args: argparse.Namespace) -> str | None:
    if getattr(args, "from_file", None):
        if getattr(args, "event_command", None):
            raise SceneError("use either --from-file or --command, not both")
        return Path(args.from_file).read_text(encoding="utf-8")
    if getattr(args, "line", None) is not None:
        if getattr(args, "event_command", None):
            raise SceneError("use either --line or --command, not both")
        return args.line
    return None


def _parse_scene_widget_path(value: str) -> tuple[str, str]:
    parts = [part.strip() for part in value.split(".") if part.strip()]
    if len(parts) != 2:
        raise SceneError("scene widget path must be page.widget, for example page0.btn0")
    return parts[0], parts[1]


def _scene_asset_payload_from_args(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for arg_name, key in (
        ("asset_doc_id", "id"),
        ("source", "source"),
        ("normal", "normal"),
        ("pressed", "pressed"),
        ("disabled", "disabled"),
    ):
        value = getattr(args, arg_name, None)
        if value is not None:
            payload[key] = value
    return payload


def _scene_widget_update_payload_from_args(
    args: argparse.Namespace,
    *,
    page_id: str,
    widget_id: str,
) -> dict[str, Any]:
    scene = load_scene(args.scene_path)
    page = next((item for item in scene.pages if item.id == page_id), None)
    if page is None:
        raise SceneError(f"Page '{page_id}' not found in scene")
    widget = next((item for item in page.widgets if item.id == widget_id), None)
    if widget is None:
        raise SceneError(f"Widget '{widget_id}' not found on page '{page_id}'")

    updates: dict[str, Any] = {}
    for arg_name, key in (
        ("new_id", "id"),
        ("widget_type", "type"),
        ("x", "x"),
        ("y", "y"),
        ("w", "w"),
        ("h", "h"),
    ):
        value = getattr(args, arg_name, None)
        if value is not None:
            updates[key] = value
    if args.clear_text:
        updates["text"] = None
    elif args.text is not None:
        updates["text"] = args.text
    if args.clear_value:
        updates["value"] = None
    elif args.value is not None:
        updates["value"] = args.value
    _merge_widget_map_update(
        updates,
        key="style",
        current=widget.style,
        json_arg=args.style_json,
        patch_args=args.style,
        option_name="--style",
    )
    _merge_widget_map_update(
        updates,
        key="resources",
        current=widget.resources,
        json_arg=args.resources_json,
        patch_args=args.resource,
        option_name="--resource",
    )
    _merge_widget_map_update(
        updates,
        key="bindings",
        current=widget.bindings,
        json_arg=args.bindings_json,
        patch_args=args.binding,
        option_name="--binding",
    )
    if not updates:
        raise SceneError("scene widgets update requires at least one property option")
    return updates


def _merge_widget_map_update(
    updates: dict[str, Any],
    *,
    key: str,
    current: dict[str, Any],
    json_arg: str | None,
    patch_args: list[str] | None,
    option_name: str,
) -> None:
    if json_arg is None and not patch_args:
        return
    merged = _parse_json_object_arg(json_arg, f"--{key}-json") if json_arg is not None else dict(current)
    for patch_key, value in _parse_cli_map(patch_args, option_name).items():
        if value is None:
            merged.pop(patch_key, None)
        else:
            merged[patch_key] = value
    updates[key] = merged


def _parse_json_object_arg(raw: str, option_name: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SceneError(f"{option_name} expects a JSON object: {exc}") from exc
    if not isinstance(value, dict):
        raise SceneError(f"{option_name} expects a JSON object")
    return value


def _scene_widget_clipboard_payload_from_args(args: argparse.Namespace) -> dict[str, Any]:
    if args.from_file:
        raw = Path(args.from_file).read_text(encoding="utf-8")
        value = _parse_json_object_arg(raw, "--from-file")
    else:
        value = _parse_json_object_arg(args.widget_json, "--widget-json")
    if value.get("kind") == "widget" and isinstance(value.get("widget"), dict):
        return value["widget"]
    if isinstance(value.get("clipboard"), dict) and isinstance(value["clipboard"].get("widget"), dict):
        return value["clipboard"]["widget"]
    return value


def _coerce_cli_value(raw_value: str) -> Any:
    lowered = raw_value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    try:
        return int(raw_value, 0)
    except ValueError:
        pass
    if "." in raw_value:
        try:
            return float(raw_value)
        except ValueError:
            pass
    if raw_value.startswith(("{", "[", '"')):
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            pass
    return raw_value


def _print_human_result(command_name: str, result: dict[str, Any]) -> None:
    if command_name in {
        "raw",
        "connect",
        "sendme",
        "get",
        "set",
        "page",
        "ref",
        "vis",
        "tsw",
        "click",
        "dim",
    }:
        print(f"Command: {result['command']}")
        print(f"Port: {result['port']} @ {result['baud']}")
        print(f"Sent: {result['sent_hex']}")
        response = result["response"]
        if not response:
            print("Response: none")
            return
        print(f"Response kind: {response.get('kind', 'none')}")
        if "value" in response:
            print(f"Value: {response['value']}")
        if "ascii_preview" in response:
            print(f"ASCII: {response['ascii_preview']}")
        print(f"HEX: {response.get('hex', '')}")
        details = response.get("details")
        if isinstance(details, dict) and details:
            print("Details:")
            for key, value in details.items():
                print(f"  {key}: {value}")
        return

    if command_name == "inspect-hmi":
        print(f"HMI: {result['path']}")
        print(f"Entries: {result['entry_count']}")
        print("Top-level entries:")
        for entry in result["entries"]:
            print(
                f"  [{entry['index']}] {entry['name'] or '<unnamed>'} "
                f"off={entry['data_offset_hex']} len={entry['length']} in_file={entry['in_file']}"
            )
        if result.get("program_text"):
            print("\nProgram.s:")
            print(result["program_text"])
        print("\nPage names:", ", ".join(result["page_names"]) or "(none)")
        print("Object names:", ", ".join(result["object_names"]) or "(none)")
        print("Property names:", ", ".join(result["property_names"]) or "(none)")
        if result.get("pa_parse_error"):
            print(f"0.pa structured parse: failed ({result['pa_parse_error']})")
        elif result.get("pa_blocks"):
            print("0.pa blocks/events:")
            for block in result["pa_blocks"]:
                label = block.get("objname") or block.get("attr_name") or f"block{block['index']}"
                type_code = block.get("type_code") or "?"
                fields = block.get("fields") or {}
                location = ""
                if all(key in fields for key in ("x", "y", "w", "h")):
                    location = f" x={fields['x']} y={fields['y']} w={fields['w']} h={fields['h']}"
                print(f"  [{block['index']}] {label} type={type_code}{location}")
                for event in block.get("event_scripts", []):
                    lines = event.get("lines") or []
                    if lines:
                        print(f"    {event['raw_header']}: {' | '.join(lines)}")
        print("0.pa strings:")
        for item in result["pa_strings"]:
            print(f"  {item['offset_hex']}: {item['text']}")
        return

    if command_name == "extract-hmi":
        print(f"Extracted {len(result['files'])} file(s) to {result['output_dir']}")
        for path in result["files"]:
            print(f"  {path}")
        return

    print(json.dumps(result, ensure_ascii=False, indent=2))
