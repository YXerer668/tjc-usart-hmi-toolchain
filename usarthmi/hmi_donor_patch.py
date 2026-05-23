from __future__ import annotations

import argparse
from hashlib import sha256
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any

from .editor import _rebuild_hmi_container
from .hmi_cfs import (
    NATIVE_CFS_PRIMARY_TABLE_OFFSET,
    find_native_cfs_record,
    parse_native_cfs_table,
    refresh_native_cfs_crc,
    rewrite_native_cfs_record,
)
from .hmi_inspect import inspect_hmi
from .hmi_pagesafe import inspect_page_safe_status, refresh_page_safe_header
from .page_format import parse_page_data


PATCH_SPEC_SCHEMA_VERSION = 1
RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES = "preserve_non_page_entries"
DEFAULT_DONOR_CORPUS_ROOT = Path(__file__).resolve().parents[1] / "reverse_usarthmi" / "hmi_donor_lowlevel_probe_20260522"
SHADOW_SYNC_MODE_AUTO = "auto"
SHADOW_SYNC_MODE_OFF = "off"
SHADOW_SYNC_MODE_CASE83_DELETE_B1_GUI = "case83-delete-b1-gui"
SHADOW_SYNC_MODE_NATIVE_PAGE_PROMOTE = "native-page-promote"
CASE83_DELETE_B1_SHADOW_SYNC = {
    "family_id": "case83_page0_basic_delete_v1",
    "page_name": "page0",
    "donor_active_sha256": "6329aec77b4570588b176ccb98129bd9796d3aeb88ee59ef9a16c2cf8970c56b",
    "minimal_shadow_sha256": "580c14e04d25916e01d6c4478e70659d6b4cae8af2ad77d8e1658eb26e46540b",
    "supporting_shadow_sha256": "be53559ece1f94d35824c75810550db07e05733959a1ee93cab2ca4eb6600c24",
    "authoritative_shadow_length": 7476,
    "expected_donor_objects": [
        {"name": "page0", "type": "y"},
        {"name": "t0", "type": "t"},
        {"name": "b0", "type": "b"},
        {"name": "p0", "type": "p"},
        {"name": "bar1", "type": "j"},
        {"name": "data0", "type": "B"},
        {"name": "select0", "type": "D"},
        {"name": "b1", "type": "b"},
    ],
    "expected_patched_objects": [
        {"name": "page0", "type": "y"},
        {"name": "t0", "type": "t"},
        {"name": "b0", "type": "b"},
        {"name": "p0", "type": "p"},
        {"name": "bar1", "type": "j"},
        {"name": "data0", "type": "B"},
        {"name": "select0", "type": "D"},
    ],
}
PAGE_DATAINFO_ADDR_OFFSET = 0x08
PAGE_DATAINFO_QTY_OFFSET = 0x0C
PAGE_DATAINFO_RECORD_SIZE = 12


def build_donor_patch_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Patch the active page of a donor .HMI while preserving the donor container/shadow chain. "
            "Supports delete, move, direct field edits, and cross-donor graft/add."
        )
    )
    parser.add_argument("donor_hmi", type=Path, nargs="?", help="Input donor .HMI")
    parser.add_argument("--out-dir", type=Path, required=True, help="Output directory")
    parser.add_argument("--spec-json", type=Path, help="Patch spec JSON file")
    parser.add_argument("--page-entry", default="0.pa", help="Page entry to patch")
    parser.add_argument("--delete-obj", action="append", default=[], help="Delete one object by name")
    parser.add_argument(
        "--move-obj",
        action="append",
        default=[],
        help="Move object geometry as name:x:y:w:h",
    )
    parser.add_argument(
        "--set-int",
        action="append",
        default=[],
        help="Set integer field as obj.field=value",
    )
    parser.add_argument(
        "--set-str",
        action="append",
        default=[],
        help="Set string field as obj.field=text",
    )
    parser.add_argument(
        "--graft-obj",
        action="append",
        default=[],
        help="Add one block from another donor as source_hmi|page|source_obj|target_obj|x|y|w|h",
    )
    parser.add_argument(
        "--probe-lowlevel",
        action="store_true",
        help="Run tools/official_hmi_lowlevel_probe.py on the patched output",
    )
    parser.add_argument(
        "--probe-reopen",
        action="store_true",
        help="Run tools/official_hmi_reopen_probe.py on a copy of the generated output",
    )
    parser.add_argument(
        "--shadow-sync-mode",
        choices=[
            SHADOW_SYNC_MODE_AUTO,
            SHADOW_SYNC_MODE_OFF,
            SHADOW_SYNC_MODE_CASE83_DELETE_B1_GUI,
            SHADOW_SYNC_MODE_NATIVE_PAGE_PROMOTE,
        ],
        default=None,
        help="Experimental donor-family shadow sync mode. Omit to use the default auto fail-closed path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_donor_patch_parser()
    args = parser.parse_args(argv)
    if args.spec_json is not None and args.donor_hmi is not None:
        parser.error("donor_hmi positional argument must be omitted when --spec-json is used")
    if args.spec_json is None and args.donor_hmi is None:
        parser.error("donor_hmi is required unless --spec-json is provided")
    spec = load_patch_spec_json(args.spec_json) if args.spec_json is not None else None
    if spec is not None:
        spec = dict(spec)
        if args.probe_lowlevel:
            spec["probe_lowlevel"] = True
        if args.probe_reopen:
            spec["probe_reopen"] = True
        if args.shadow_sync_mode is not None:
            spec["shadow_sync_mode"] = args.shadow_sync_mode
    report = patch_hmi_donor(
        donor_hmi=None if args.donor_hmi is None else args.donor_hmi.resolve(),
        out_dir=args.out_dir.resolve(),
        page_entry=args.page_entry,
        delete_objects=list(args.delete_obj),
        graft_specs=list(args.graft_obj),
        move_specs=list(args.move_obj),
        int_specs=list(args.set_int),
        str_specs=list(args.set_str),
        probe_lowlevel=args.probe_lowlevel,
        probe_reopen=args.probe_reopen,
        shadow_sync_mode=args.shadow_sync_mode,
        spec=spec,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def generate_reopen_safe_fixture(
    control_type: str,
    out_dir: str | Path,
    *,
    corpus_root: str | Path = DEFAULT_DONOR_CORPUS_ROOT,
) -> dict[str, Any]:
    corpus = Path(corpus_root).resolve()
    control_map_path = corpus / "reopen_safe_control_map.json"
    if not control_map_path.exists():
        raise FileNotFoundError(f"reopen-safe control map does not exist: {control_map_path}")
    payload = json.loads(control_map_path.read_text(encoding="utf-8"))
    controls = payload.get("controls") or {}
    entry = controls.get(control_type)
    if entry is None:
        known = ", ".join(sorted(controls))
        raise ValueError(f"reopen-safe control {control_type!r} is not available; known: {known}")
    case_id = str(entry["case_id"])
    spec_path = corpus / "fixture_corpus" / "specs" / f"{case_id}.json"
    if not spec_path.exists():
        raise FileNotFoundError(f"reopen-safe patch spec does not exist: {spec_path}")
    spec = load_patch_spec_json(spec_path)
    spec = dict(spec)
    spec["probe_lowlevel"] = True
    spec["probe_reopen"] = True
    report = patch_hmi_donor(
        donor_hmi=None,
        out_dir=Path(out_dir).resolve(),
        spec=spec,
        probe_lowlevel=True,
        probe_reopen=True,
    )
    report["reopen_safe_control_type"] = control_type
    report["reopen_safe_source_case_id"] = case_id
    report["reopen_safe_control_map_json"] = str(control_map_path)
    return report


def patch_hmi_donor(
    *,
    donor_hmi: Path | None,
    out_dir: Path,
    page_entry: str = "0.pa",
    delete_objects: list[str] | None = None,
    graft_specs: list[str] | None = None,
    move_specs: list[str] | None = None,
    int_specs: list[str] | None = None,
    str_specs: list[str] | None = None,
    probe_lowlevel: bool = False,
    probe_reopen: bool = False,
    shadow_sync_mode: str = SHADOW_SYNC_MODE_AUTO,
    spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    normalized_spec = normalize_patch_spec(
        spec
        if spec is not None
        else build_patch_spec(
            donor_hmi=donor_hmi,
            page_entry=page_entry,
            delete_objects=delete_objects or [],
            graft_specs=graft_specs or [],
            move_specs=move_specs or [],
            int_specs=int_specs or [],
            str_specs=str_specs or [],
            probe_lowlevel=probe_lowlevel,
            probe_reopen=probe_reopen,
            shadow_sync_mode=shadow_sync_mode,
        )
    )

    donor_hmi = Path(normalized_spec["donor_path"]).resolve()
    page_entry = str(normalized_spec["page"])
    probe_lowlevel = bool(normalized_spec.get("probe_lowlevel", False))
    probe_reopen = bool(normalized_spec.get("probe_reopen", False))

    inspection = inspect_hmi(donor_hmi)
    raw = donor_hmi.read_bytes()
    entry = next((item for item in inspection.entries if item.name == page_entry), None)
    if entry is None:
        raise ValueError(f"Page entry {page_entry!r} not found in {donor_hmi}")
    page = parse_page_data(raw[entry.data_offset : entry.data_offset + entry.length])
    blocks_by_name = {block.objname: block for block in page.blocks if block.objname}
    operations: list[dict[str, Any]] = []

    for operation in normalized_spec["operations"]:
        kind = operation["kind"]
        if kind == "delete":
            objname = operation["object"]
            if objname == page.page_name:
                raise ValueError("Refusing to delete the page root block")
            if objname not in blocks_by_name:
                raise ValueError(f"Delete target {objname!r} not found in {donor_hmi}")
            page.blocks = [block for block in page.blocks if block.objname != objname]
            operations.append({"kind": "delete", "object": objname})
            blocks_by_name.pop(objname, None)
            continue

        if kind == "graft":
            source_hmi = Path(operation["source_hmi"]).resolve()
            source_page = operation["source_page"]
            source_obj = operation["source_object"]
            target_obj = operation["target_object"]
            x = int(operation["x"])
            y = int(operation["y"])
            w = int(operation["w"])
            h = int(operation["h"])
            if target_obj in blocks_by_name:
                raise ValueError(f"Graft target object {target_obj!r} already exists")
            source_inspection = inspect_hmi(source_hmi)
            source_raw = source_hmi.read_bytes()
            source_entry = next((item for item in source_inspection.entries if item.name == source_page), None)
            if source_entry is None:
                raise ValueError(f"Graft source page {source_page!r} not found in {source_hmi}")
            source_page_data = parse_page_data(
                source_raw[source_entry.data_offset : source_entry.data_offset + source_entry.length]
            )
            source_block = next((block for block in source_page_data.blocks if block.objname == source_obj), None)
            if source_block is None:
                raise ValueError(f"Graft source object {source_obj!r} not found in {source_hmi}:{source_page}")
            cloned = source_block.clone()
            next_id = max((_block_int(block, "id") for block in page.blocks), default=0) + 1
            cloned.set_string("objname", target_obj, encoding="ascii")
            cloned.set_int("id", next_id, width=1)
            cloned.set_int("x", x, width=2)
            cloned.set_int("y", y, width=2)
            cloned.set_int("w", w, width=2)
            cloned.set_int("h", h, width=2)
            cloned.set_int("endx", x + w - 1, width=2)
            cloned.set_int("endy", y + h - 1, width=2)
            page.blocks.append(cloned)
            blocks_by_name[target_obj] = cloned
            operations.append(
                {
                    "kind": "graft",
                    "source_hmi": str(source_hmi),
                    "source_page": source_page,
                    "source_object": source_obj,
                    "target_object": target_obj,
                    "x": x,
                    "y": y,
                    "w": w,
                    "h": h,
                }
            )
            continue

        if kind == "move":
            objname = operation["object"]
            x = int(operation["x"])
            y = int(operation["y"])
            w = int(operation["w"])
            h = int(operation["h"])
            block = _require_block(blocks_by_name, objname)
            block.set_int("x", x, width=2)
            block.set_int("y", y, width=2)
            block.set_int("w", w, width=2)
            block.set_int("h", h, width=2)
            block.set_int("endx", x + w - 1, width=2)
            block.set_int("endy", y + h - 1, width=2)
            operations.append({"kind": "move", "object": objname, "x": x, "y": y, "w": w, "h": h})
            continue

        if kind == "set-int":
            objname = operation["object"]
            field_name = operation["field"]
            value = int(operation["value"])
            block = _require_block(blocks_by_name, objname)
            field = block.get_field(field_name)
            if field is None:
                raise ValueError(f"Integer field {objname}.{field_name} not found")
            width = max(1, int(getattr(field, "merrylenth", 0) or 0) or len(field.value))
            block.set_int(field_name, value, width=width)
            if field_name in {"x", "y", "w", "h"}:
                _refresh_end_fields(block)
            operations.append({"kind": "set-int", "object": objname, "field": field_name, "value": value})
            continue

        if kind == "set-str":
            objname = operation["object"]
            field_name = operation["field"]
            value = str(operation["value"])
            block = _require_block(blocks_by_name, objname)
            if block.get_field(field_name) is None:
                raise ValueError(f"String field {objname}.{field_name} not found")
            block.set_string(field_name, value, encoding="gbk")
            operations.append({"kind": "set-str", "object": objname, "field": field_name, "value": value})
            continue

        raise ValueError(f"Unsupported patch operation kind: {kind!r}")

    generated_hmi = out_dir / "generated.HMI"
    rebuilt = _rebuild_hmi_container(
        raw,
        inspection.entries,
        replacements={page_entry: page.serialize()},
        additions=[],
    )
    generated_hmi.write_bytes(rebuilt)
    shadow_sync = _maybe_apply_experimental_shadow_sync(
        donor_raw=raw,
        donor_entries=inspection.entries,
        generated_hmi=generated_hmi,
        normalized_spec=normalized_spec,
    )
    shadow_report_path = out_dir / "shadow_sync_report.json"
    shadow_report_path.write_text(json.dumps(shadow_sync, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    input_donor_copy = out_dir / "input_donor.HMI"
    if donor_hmi.resolve() != input_donor_copy.resolve():
        shutil.copy2(donor_hmi, input_donor_copy)

    patch_spec_path = out_dir / "patch_spec.json"
    patch_spec_path.write_text(json.dumps(normalized_spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    generated_inspection = inspect_hmi(generated_hmi)
    generated_raw = generated_hmi.read_bytes()
    generated_entry = next((item for item in generated_inspection.entries if item.name == page_entry), None)
    if generated_entry is None:
        raise RuntimeError(f"Generated page entry {page_entry!r} not found in {generated_hmi}")
    generated_page = parse_page_data(
        generated_raw[generated_entry.data_offset : generated_entry.data_offset + generated_entry.length]
    )

    actual_objects = _block_listing(generated_page.blocks)
    expected_objects = normalized_spec["expectations"]["objects"] or actual_objects
    expected_strings = normalized_spec["expectations"]["strings"]
    expected_ints = normalized_spec["expectations"]["ints"]
    string_results = _evaluate_string_expectations(generated_page.blocks, expected_strings)
    int_results = _evaluate_int_expectations(generated_page.blocks, expected_ints)
    donor_resources = _non_page_entry_fingerprint(inspection)
    generated_resources = _non_page_entry_fingerprint(generated_inspection)

    report: dict[str, Any] = {
        "schema_version": 1,
        "mode": "hmi_donor_patch",
        "case_id": normalized_spec["case_id"],
        "donor_hmi": str(donor_hmi),
        "input_donor_hmi": str(input_donor_copy),
        "output_hmi": str(generated_hmi),
        "patch_spec_json": str(patch_spec_path),
        "page_entry": page_entry,
        "page_name": generated_page.page_name,
        "page_matches_expected": normalized_spec["expectations"]["page_name"] == generated_page.page_name,
        "control_type": normalized_spec.get("control_type"),
        "control_name": normalized_spec.get("control_name"),
        "donor_kind": normalized_spec.get("donor_kind"),
        "generated_kind": "generated",
        "exact_donor": bool(normalized_spec.get("exact_donor", False)),
        "notes": normalized_spec.get("notes", ""),
        "operations": operations,
        "expected_objects": expected_objects,
        "actual_objects": actual_objects,
        "objects_match_expected": expected_objects == actual_objects,
        "expected_strings": expected_strings,
        "string_results": string_results,
        "strings_match_expected": all(item["matches"] for item in string_results),
        "expected_ints": expected_ints,
        "int_results": int_results,
        "ints_match_expected": all(item["matches"] for item in int_results),
        "resource_policy": normalized_spec["expectations"]["resource_policy"],
        "shadow_sync_mode": str(normalized_spec.get("shadow_sync_mode") or SHADOW_SYNC_MODE_OFF),
        "donor_resources": donor_resources,
        "generated_resources": generated_resources,
        "resources_match_expected": donor_resources == generated_resources,
        "experimental_shadow_sync_applied": bool(shadow_sync.get("applied", False)),
        "experimental_shadow_sync_family_id": shadow_sync.get("family_id"),
        "experimental_shadow_sync_reason": shadow_sync.get("reason"),
        "shadow_sync_report_json": str(shadow_report_path),
        "official_gui_reopen_ok": None,
        "official_gui_reopen_changed": None,
        "official_gui_reopen_before_objects": None,
        "official_gui_reopen_after_objects": None,
        "official_gui_reopen_json": None,
        "official_gui_reopen_error": None,
    }

    manifest = {
        "schema_version": 1,
        "mode": "hmi_donor_patch_manifest",
        "case_id": normalized_spec["case_id"],
        "donor_hmi": str(donor_hmi),
        "input_donor_hmi": str(input_donor_copy),
        "patch_spec_json": str(patch_spec_path),
        "generated_hmi": str(generated_hmi),
        "page_entry": page_entry,
        "operations": operations,
        "shadow_sync_report_json": str(shadow_report_path),
        "capability_result_json": str(out_dir / "capability_result.json"),
        "patch_report_json": str(out_dir / "patch_report.json"),
    }

    if probe_lowlevel:
        probe_dir = out_dir / "official_lowlevel_probe"
        command = [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "tools" / "official_hmi_lowlevel_probe.py"),
            str(generated_hmi),
            "--out-dir",
            str(probe_dir),
        ]
        proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode:
            raise RuntimeError(
                "official_hmi_lowlevel_probe.py failed with "
                f"exit code {proc.returncode}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            )
        lowlevel_report = json.loads(proc.stdout)
        report["official_lowlevel_probe"] = lowlevel_report
        report["open_lowlevel_ok"] = lowlevel_report["accepted_by_open_lowlevel"]
        report["compile_lowlevel_ok"] = lowlevel_report["accepted_by_compile_lowlevel"]
        open_json = probe_dir / "open_lowlevel.result.json"
        compile_json = probe_dir / "compile_lowlevel.result.json"
        official_json = probe_dir / f"{generated_hmi.stem}.official_lowlevel.json"
        open_output_json = out_dir / "open_lowlevel.output.json"
        compile_output_json = out_dir / "compile_lowlevel.output.json"
        official_output_json = out_dir / "official_lowlevel_probe.json"
        if open_json.exists():
            shutil.copy2(open_json, open_output_json)
        if compile_json.exists():
            shutil.copy2(compile_json, compile_output_json)
        if official_json.exists():
            shutil.copy2(official_json, official_output_json)
        report["open_lowlevel_output_json"] = str(open_output_json) if open_output_json.exists() else None
        report["compile_lowlevel_output_json"] = str(compile_output_json) if compile_output_json.exists() else None
        report["official_lowlevel_probe_json"] = str(official_output_json) if official_output_json.exists() else None
        manifest["open_lowlevel_output_json"] = report["open_lowlevel_output_json"]
        manifest["compile_lowlevel_output_json"] = report["compile_lowlevel_output_json"]
        manifest["official_lowlevel_probe_json"] = report["official_lowlevel_probe_json"]
    else:
        report["open_lowlevel_ok"] = None
        report["compile_lowlevel_ok"] = None

    if probe_reopen:
        reopen = _safe_reopen_probe(generated_hmi, out_dir / "official_reopen_probe")
        report.update(reopen)
        if report["official_gui_reopen_ok"] is False:
            report["failed_reason"] = "official GUI reopen/save changed the object list"
        elif report["official_gui_reopen_ok"] is None and report["official_gui_reopen_error"]:
            report["failed_reason"] = report["official_gui_reopen_error"]
        manifest["official_gui_reopen_json"] = report["official_gui_reopen_json"]

    report["confidence"] = _derive_confidence(report)

    capability_result_path = out_dir / "capability_result.json"
    patch_report_path = out_dir / "patch_report.json"
    manifest_path = out_dir / "manifest.json"
    capability_result_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    patch_report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["capability_result_json"] = str(capability_result_path)
    report["report_json"] = str(patch_report_path)
    report["manifest_json"] = str(manifest_path)
    return report


def build_patch_spec(
    *,
    donor_hmi: Path | None,
    page_entry: str,
    delete_objects: list[str],
    graft_specs: list[str],
    move_specs: list[str],
    int_specs: list[str],
    str_specs: list[str],
    probe_lowlevel: bool,
    probe_reopen: bool,
    shadow_sync_mode: str,
) -> dict[str, Any]:
    if donor_hmi is None:
        raise ValueError("donor_hmi is required when a patch spec JSON is not provided")
    operations: list[dict[str, Any]] = []
    for objname in delete_objects:
        operations.append({"kind": "delete", "object": objname})
    for spec in graft_specs:
        source_hmi, source_page, source_obj, target_obj, x, y, w, h = _parse_graft_spec(spec)
        operations.append(
            {
                "kind": "graft",
                "source_hmi": str(source_hmi),
                "source_page": source_page,
                "source_object": source_obj,
                "target_object": target_obj,
                "x": x,
                "y": y,
                "w": w,
                "h": h,
            }
        )
    for spec in move_specs:
        objname, x, y, w, h = _parse_move_spec(spec)
        operations.append({"kind": "move", "object": objname, "x": x, "y": y, "w": w, "h": h})
    for spec in int_specs:
        objname, field_name, value = _parse_field_spec(spec)
        operations.append({"kind": "set-int", "object": objname, "field": field_name, "value": value})
    for spec in str_specs:
        objname, field_name, value = _parse_text_spec(spec)
        operations.append({"kind": "set-str", "object": objname, "field": field_name, "value": value})
    if not operations:
        raise ValueError("At least one patch operation is required")
    expected_strings = [
        {"object": op["object"], "field": op["field"], "value": op["value"]}
        for op in operations
        if op["kind"] == "set-str"
    ]
    expected_ints = [
        {"object": op["object"], "field": op["field"], "value": op["value"]}
        for op in operations
        if op["kind"] == "set-int"
    ]
    donor_case_id = donor_hmi.parent.name if donor_hmi.stem.lower() == "lcd_test" else donor_hmi.stem
    return {
        "schema_version": PATCH_SPEC_SCHEMA_VERSION,
        "case_id": donor_case_id,
        "donor_path": str(Path(donor_hmi).resolve()),
        "page": page_entry,
        "probe_lowlevel": probe_lowlevel,
        "probe_reopen": probe_reopen,
        "shadow_sync_mode": str(shadow_sync_mode or SHADOW_SYNC_MODE_AUTO),
        "exact_donor": True,
        "donor_kind": "exact",
        "operations": operations,
        "expectations": {
            "page_name": "page0",
            "objects": [],
            "strings": expected_strings,
            "ints": expected_ints,
            "resource_policy": RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
        },
    }


def _maybe_apply_experimental_shadow_sync(
    *,
    donor_raw: bytes,
    donor_entries,
    generated_hmi: Path,
    normalized_spec: dict[str, Any],
) -> dict[str, Any]:
    generated_inspection = inspect_hmi(generated_hmi)
    generated_raw = generated_hmi.read_bytes()
    donor_candidates = _summarize_pa_like_entries(donor_raw, donor_entries)
    generated_candidates_before = _summarize_pa_like_entries(generated_raw, generated_inspection.entries)
    report: dict[str, Any] = {
        "schema_version": 1,
        "mode": "experimental_shadow_sync",
        "family_id": None,
        "applied": False,
        "reason": "not_applicable",
        "donor_candidates": donor_candidates,
        "generated_candidates_before": generated_candidates_before,
        "generated_candidates_after": None,
        "active_entry_index": None,
        "authoritative_shadow_index": None,
        "payload_changed_entry_indices": [],
        "native_named_0pa_before": None,
        "native_named_0pa_after": None,
    }
    shadow_sync_mode = str(normalized_spec.get("shadow_sync_mode") or SHADOW_SYNC_MODE_OFF)
    operation_kinds = {str(item.get("kind")) for item in normalized_spec.get("operations", [])}
    if shadow_sync_mode == SHADOW_SYNC_MODE_OFF:
        report["reason"] = "shadow_sync_mode_off"
        return report
    if shadow_sync_mode == SHADOW_SYNC_MODE_NATIVE_PAGE_PROMOTE:
        return _maybe_promote_active_named_page(
            generated_hmi=generated_hmi,
            generated_raw=generated_raw,
            generated_inspection=generated_inspection,
            generated_candidates_before=generated_candidates_before,
            normalized_spec=normalized_spec,
            report=report,
        )
    if shadow_sync_mode == SHADOW_SYNC_MODE_AUTO:
        if not (operation_kinds & {"delete", "graft"}):
            report["reason"] = "auto_skipped_non_structural_operation"
            return report
        auto_match = _match_case83_delete_shadow_sync(
            normalized_spec=normalized_spec,
            donor_candidates=donor_candidates,
            generated_candidates=generated_candidates_before,
        )
        if auto_match["eligible"]:
            match = auto_match
        else:
            auto_report = _maybe_promote_active_named_page(
                generated_hmi=generated_hmi,
                generated_raw=generated_raw,
                generated_inspection=generated_inspection,
                generated_candidates_before=generated_candidates_before,
                normalized_spec=normalized_spec,
                report=report,
            )
            if auto_report.get("applied"):
                return auto_report
            report["reason"] = f"auto_no_matching_strategy:{auto_report.get('reason')}"
            return report
    elif shadow_sync_mode != SHADOW_SYNC_MODE_CASE83_DELETE_B1_GUI:
        report["reason"] = f"unsupported_shadow_sync_mode:{shadow_sync_mode}"
        return report
    else:
        match = _match_case83_delete_shadow_sync(
            normalized_spec=normalized_spec,
            donor_candidates=donor_candidates,
            generated_candidates=generated_candidates_before,
        )
    if not match["eligible"]:
        report["reason"] = match["reason"]
        return report

    active_entry = next((entry for entry in generated_inspection.entries if entry.name == "0.pa"), None)
    if active_entry is None:
        report["family_id"] = CASE83_DELETE_B1_SHADOW_SYNC["family_id"]
        report["reason"] = "generated_active_entry_missing"
        return report

    report["family_id"] = CASE83_DELETE_B1_SHADOW_SYNC["family_id"]
    report["active_entry_index"] = int(active_entry.index)
    report["authoritative_shadow_index"] = int(match["authoritative_shadow_index"])
    expected_after_delete = list(match["expected_objects_after_delete"])
    native_table = parse_native_cfs_table(generated_raw, NATIVE_CFS_PRIMARY_TABLE_OFFSET)
    native_page = find_native_cfs_record(native_table, "0.pa")
    if native_page is None:
        report["reason"] = "native_named_0pa_missing"
        return report
    native_page_before = generated_raw[native_page.data_offset : native_page.data_offset + native_page.length]
    report["native_named_0pa_before"] = {
        **native_page.to_dict(),
        "sha256": sha256(native_page_before).hexdigest(),
        "page_safe": inspect_page_safe_status(native_page_before).to_dict(),
    }
    try:
        native_page_data = parse_page_data(native_page_before)
    except Exception as exc:
        report["reason"] = f"native_named_0pa_parse_failed:{type(exc).__name__}"
        report["error"] = str(exc)
        return report
    native_page_objects = _block_listing(native_page_data.blocks)
    if native_page.length != CASE83_DELETE_B1_SHADOW_SYNC["authoritative_shadow_length"]:
        report["reason"] = "native_named_0pa_length_mismatch"
        return report
    if native_page_objects != CASE83_DELETE_B1_SHADOW_SYNC["expected_donor_objects"]:
        report["reason"] = "native_named_0pa_object_graph_mismatch"
        report["native_named_0pa_before"]["objects"] = native_page_objects
        return report

    delete_index = int(match["delete_object_index"])
    rewritten_page = _rewrite_native_named_page_delete(native_page_before, delete_index)
    patched_raw = bytearray(generated_raw)
    patched_raw[native_page.data_offset : native_page.data_offset + native_page.length] = rewritten_page
    try:
        generated_hmi.write_bytes(patched_raw)
        after_inspection = inspect_hmi(generated_hmi)
        after_raw = generated_hmi.read_bytes()
    except Exception as exc:
        generated_hmi.write_bytes(generated_raw)
        report["reason"] = f"rewrite_failed:{type(exc).__name__}"
        report["error"] = str(exc)
        return report

    changed_payload_indices = _diff_payload_entry_indices(
        generated_raw,
        generated_inspection.entries,
        after_raw,
        after_inspection.entries,
    )
    expected_changed = {int(match["authoritative_shadow_index"])}
    if set(changed_payload_indices) != expected_changed:
        generated_hmi.write_bytes(generated_raw)
        report["reason"] = (
            f"payload_change_invariant_failed:expected={sorted(expected_changed)} "
            f"actual={changed_payload_indices}"
        )
        return report

    generated_candidates_after = _summarize_pa_like_entries(after_raw, after_inspection.entries)
    after_active = next((item for item in generated_candidates_after if item["entry_name"] == "0.pa"), None)
    after_shadow = next(
        (item for item in generated_candidates_after if item["index"] == int(match["authoritative_shadow_index"])),
        None,
    )
    if after_active is None or after_shadow is None:
        generated_hmi.write_bytes(generated_raw)
        report["reason"] = "post_rewrite_candidates_missing"
        return report
    if after_active["objects"] != expected_after_delete:
        generated_hmi.write_bytes(generated_raw)
        report["reason"] = "post_rewrite_active_page_mismatch"
        report["generated_candidates_after"] = generated_candidates_after
        return report
    if after_shadow["length"] != CASE83_DELETE_B1_SHADOW_SYNC["authoritative_shadow_length"]:
        generated_hmi.write_bytes(generated_raw)
        report["reason"] = "post_rewrite_named_page_length_changed"
        report["generated_candidates_after"] = generated_candidates_after
        return report
    if after_shadow["objects"] != after_active["objects"]:
        generated_hmi.write_bytes(generated_raw)
        report["reason"] = "post_rewrite_shadow_still_conflicts_with_active"
        report["generated_candidates_after"] = generated_candidates_after
        return report
    native_table_after = parse_native_cfs_table(after_raw, NATIVE_CFS_PRIMARY_TABLE_OFFSET)
    native_page_after = find_native_cfs_record(native_table_after, "0.pa")
    if native_page_after is None:
        generated_hmi.write_bytes(generated_raw)
        report["reason"] = "post_rewrite_native_named_0pa_missing"
        return report
    native_page_after_bytes = after_raw[native_page_after.data_offset : native_page_after.data_offset + native_page_after.length]
    report["native_named_0pa_after"] = {
        **native_page_after.to_dict(),
        "sha256": sha256(native_page_after_bytes).hexdigest(),
        "page_safe": inspect_page_safe_status(native_page_after_bytes).to_dict(),
    }
    if report["native_named_0pa_after"]["page_safe"]["safe_ok"] is not True:
        generated_hmi.write_bytes(generated_raw)
        report["reason"] = "post_rewrite_native_named_0pa_not_pagesafe"
        return report

    report["applied"] = True
    report["reason"] = "applied_case83_delete_b1_native_named_page_tombstone"
    report["generated_candidates_after"] = generated_candidates_after
    report["payload_changed_entry_indices"] = changed_payload_indices
    return report


def _match_case83_delete_shadow_sync(
    *,
    normalized_spec: dict[str, Any],
    donor_candidates: list[dict[str, Any]],
    generated_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    if not normalized_spec.get("exact_donor", False):
        return {"eligible": False, "reason": "non_exact_donor"}
    operations = normalized_spec["operations"]
    if len(operations) != 1 or operations[0].get("kind") != "delete":
        return {"eligible": False, "reason": "operation_not_calibrated"}
    delete_object = str(operations[0]["object"])
    donor_expected = CASE83_DELETE_B1_SHADOW_SYNC["expected_donor_objects"]
    if delete_object == donor_expected[0]["name"]:
        return {"eligible": False, "reason": "delete_root_not_allowed"}
    expected_after_delete = [item for item in donor_expected if item["name"] != delete_object]
    if len(expected_after_delete) != len(donor_expected) - 1:
        return {"eligible": False, "reason": "delete_target_not_in_case83_family"}

    donor_active = next((item for item in donor_candidates if item["entry_name"] == "0.pa"), None)
    if donor_active is None or not donor_active["parse_ok"]:
        return {"eligible": False, "reason": "donor_active_page_missing"}
    if donor_active["sha256"] != CASE83_DELETE_B1_SHADOW_SYNC["donor_active_sha256"]:
        return {"eligible": False, "reason": "donor_active_hash_mismatch"}
    if donor_active["objects"] != donor_expected:
        return {"eligible": False, "reason": "donor_active_object_graph_mismatch"}
    donor_hashes = {item["sha256"] for item in donor_candidates if item["parse_ok"]}
    if CASE83_DELETE_B1_SHADOW_SYNC["minimal_shadow_sha256"] not in donor_hashes:
        return {"eligible": False, "reason": "donor_minimal_shadow_missing"}
    if CASE83_DELETE_B1_SHADOW_SYNC["supporting_shadow_sha256"] not in donor_hashes:
        return {"eligible": False, "reason": "donor_supporting_shadow_missing"}

    generated_active = next((item for item in generated_candidates if item["entry_name"] == "0.pa"), None)
    if generated_active is None or not generated_active["parse_ok"]:
        return {"eligible": False, "reason": "generated_active_page_missing"}
    if generated_active["page_name"] != CASE83_DELETE_B1_SHADOW_SYNC["page_name"]:
        return {"eligible": False, "reason": "generated_page_name_mismatch"}
    if generated_active["objects"] != expected_after_delete:
        return {"eligible": False, "reason": "generated_active_object_graph_not_matching_requested_delete"}

    authoritative = [
        item
        for item in generated_candidates
        if item["anonymous_pa"]
        and item["parse_ok"]
        and item["page_name"] == CASE83_DELETE_B1_SHADOW_SYNC["page_name"]
        and item["length"] == CASE83_DELETE_B1_SHADOW_SYNC["authoritative_shadow_length"]
        and item["sha256"] == CASE83_DELETE_B1_SHADOW_SYNC["donor_active_sha256"]
    ]
    if len(authoritative) != 1:
        return {"eligible": False, "reason": "authoritative_shadow_not_unique"}
    if authoritative[0]["objects"] != donor_expected:
        return {"eligible": False, "reason": "authoritative_shadow_object_graph_mismatch"}
    delete_index = next((i for i, item in enumerate(donor_expected) if item["name"] == delete_object), -1)
    if delete_index < 0:
        return {"eligible": False, "reason": "delete_target_index_not_found"}
    return {
        "eligible": True,
        "reason": "matched_case83_native_page_delete_manifest",
        "authoritative_shadow_index": int(authoritative[0]["index"]),
        "active_entry_index": int(generated_active["index"]),
        "delete_object": delete_object,
        "delete_object_index": delete_index,
        "expected_objects_after_delete": expected_after_delete,
    }


def _summarize_pa_like_entries(raw: bytes, entries) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        name_bytes = _entry_name_bytes(raw, entry)
        if not _is_pa_like_entry(entry, name_bytes):
            continue
        data = _entry_data(raw, entry)
        row: dict[str, Any] = {
            "index": int(entry.index),
            "entry_name": entry.name,
            "name_hex": name_bytes.hex(" "),
            "length": int(entry.length),
            "field3_hex": f"0x{int(entry.field3):X}",
            "anonymous_pa": bool(not entry.name and name_bytes[1:4] == b".pa"),
            "sha256": sha256(data).hexdigest(),
        }
        try:
            page = parse_page_data(data)
            objects = _block_listing(page.blocks)
            row.update(
                {
                    "parse_ok": True,
                    "parse_error": None,
                    "page_name": page.page_name,
                    "objects": objects,
                    "object_names": [item["name"] for item in objects],
                }
            )
        except Exception as exc:
            row.update(
                {
                    "parse_ok": False,
                    "parse_error": f"{type(exc).__name__}: {exc}",
                    "page_name": None,
                    "objects": [],
                    "object_names": [],
                }
            )
        rows.append(row)
    return rows


def _rebuild_hmi_container_with_index_overrides(
    seed_bytes: bytes,
    entries,
    *,
    overrides: dict[int, dict[str, Any]],
) -> bytes:
    original_data_start = min(entry.data_offset for entry in entries if entry.in_file)
    directory_end = 4 + len(entries) * 28
    data_start = max(original_data_start, directory_end)
    result = bytearray(seed_bytes[:original_data_start])
    if len(result) < data_start:
        result.extend(b"\x00" * (data_start - len(result)))
    result[0:4] = len(entries).to_bytes(4, "little")
    result[4:directory_end] = b"\x00" * (directory_end - 4)

    cursor = data_start
    for entry in entries:
        override = overrides.get(int(entry.index), {})
        name_bytes = bytes(override.get("name_bytes", _entry_name_bytes(seed_bytes, entry)))
        field3 = int(override.get("field3", entry.field3))
        data = bytes(override.get("data", _entry_data(seed_bytes, entry)))
        base = 4 + int(entry.index) * 28
        result[base : base + 16] = name_bytes.ljust(16, b"\x00")[:16]
        result[base + 16 : base + 20] = cursor.to_bytes(4, "little")
        result[base + 20 : base + 24] = len(data).to_bytes(4, "little")
        result[base + 24 : base + 28] = field3.to_bytes(4, "little")
        if len(result) != cursor:
            raise RuntimeError("Internal HMI rebuild cursor drifted during shadow sync")
        result.extend(data)
        cursor += len(data)
    return bytes(result)


def _diff_payload_entry_indices(before_raw: bytes, before_entries, after_raw: bytes, after_entries) -> list[int]:
    if len(before_entries) != len(after_entries):
        raise RuntimeError("Entry count changed during shadow sync rewrite")
    changed: list[int] = []
    for before_entry, after_entry in zip(before_entries, after_entries):
        if before_entry.index != after_entry.index:
            raise RuntimeError("Entry ordering changed during shadow sync rewrite")
        if _entry_data(before_raw, before_entry) != _entry_data(after_raw, after_entry):
            changed.append(int(before_entry.index))
    return changed


def _is_pa_like_entry(entry, name_bytes: bytes) -> bool:
    return entry.name.endswith(".pa") or name_bytes[1:4] == b".pa"


def _entry_name_bytes(raw: bytes, entry) -> bytes:
    return raw[entry.dir_offset : entry.dir_offset + 16]


def _entry_data(raw: bytes, entry) -> bytes:
    return raw[entry.data_offset : entry.data_offset + entry.length]


def _rewrite_native_named_page_delete(page_bytes: bytes, delete_index: int) -> bytes:
    page = bytearray(page_bytes)
    object_count = struct.unpack_from("<I", page, PAGE_DATAINFO_QTY_OFFSET)[0]
    if object_count <= delete_index:
        raise ValueError(f"delete_index {delete_index} outside page datainformation count {object_count}")
    table_offset = struct.unpack_from("<I", page, PAGE_DATAINFO_ADDR_OFFSET)[0]
    for index in range(delete_index, object_count - 1):
        src = table_offset + (index + 1) * PAGE_DATAINFO_RECORD_SIZE
        dst = table_offset + index * PAGE_DATAINFO_RECORD_SIZE
        page[dst : dst + PAGE_DATAINFO_RECORD_SIZE] = page[src : src + PAGE_DATAINFO_RECORD_SIZE]
    return refresh_page_safe_header(page, datainformation_qyt=object_count - 1)


def _maybe_promote_active_named_page(
    *,
    generated_hmi: Path,
    generated_raw: bytes,
    generated_inspection,
    generated_candidates_before: list[dict[str, Any]],
    normalized_spec: dict[str, Any],
    report: dict[str, Any],
) -> dict[str, Any]:
    if not normalized_spec.get("exact_donor", False):
        report["reason"] = "non_exact_donor"
        return report

    active_entry = next((entry for entry in generated_inspection.entries if entry.name == "0.pa"), None)
    if active_entry is None:
        report["reason"] = "generated_active_entry_missing"
        return report
    active_candidate = next((item for item in generated_candidates_before if item["entry_name"] == "0.pa"), None)
    if active_candidate is None or not active_candidate["parse_ok"]:
        report["reason"] = "generated_active_page_missing"
        return report

    expected_objects = normalized_spec["expectations"]["objects"] or report["actual_objects"]
    if active_candidate["objects"] != expected_objects:
        report["reason"] = "generated_active_object_graph_mismatch"
        return report

    native_table = parse_native_cfs_table(generated_raw, NATIVE_CFS_PRIMARY_TABLE_OFFSET)
    native_page = find_native_cfs_record(native_table, "0.pa")
    if native_page is None:
        report["reason"] = "native_named_0pa_missing"
        return report

    native_page_before = generated_raw[native_page.data_offset : native_page.data_offset + native_page.length]
    report["native_named_0pa_before"] = {
        **native_page.to_dict(),
        "sha256": sha256(native_page_before).hexdigest(),
        "page_safe": inspect_page_safe_status(native_page_before).to_dict(),
    }
    if active_entry.data_offset == native_page.data_offset and active_entry.length == native_page.length:
        report["reason"] = "native_named_0pa_already_points_to_active_page"
        return report

    active_page_before = _entry_data(generated_raw, active_entry)
    active_page_after = refresh_page_safe_header(active_page_before, datasize=active_entry.length)
    active_page_status = inspect_page_safe_status(active_page_after)
    if active_page_status.safe_ok is not True:
        report["reason"] = "active_named_page_not_pagesafe_after_refresh"
        report["active_named_0pa"] = {
            "entry_index": int(active_entry.index),
            "data_offset": int(active_entry.data_offset),
            "length": int(active_entry.length),
            "page_safe": active_page_status.to_dict(),
        }
        return report

    patched_raw = bytearray(generated_raw)
    patched_raw[active_entry.data_offset : active_entry.data_offset + active_entry.length] = active_page_after
    patched_raw = bytearray(
        rewrite_native_cfs_record(
            patched_raw,
            offset=NATIVE_CFS_PRIMARY_TABLE_OFFSET,
            record_index=native_page.index,
            data_offset=active_entry.data_offset,
            length=active_entry.length,
        )
    )
    patched_raw = bytearray(refresh_native_cfs_crc(patched_raw, offset=NATIVE_CFS_PRIMARY_TABLE_OFFSET))

    try:
        generated_hmi.write_bytes(patched_raw)
        after_inspection = inspect_hmi(generated_hmi)
        after_raw = generated_hmi.read_bytes()
    except Exception as exc:
        generated_hmi.write_bytes(generated_raw)
        report["reason"] = f"rewrite_failed:{type(exc).__name__}"
        report["error"] = str(exc)
        return report

    changed_payload_indices = _diff_payload_entry_indices(
        generated_raw,
        generated_inspection.entries,
        after_raw,
        after_inspection.entries,
    )
    if set(changed_payload_indices) != {int(active_entry.index)}:
        generated_hmi.write_bytes(generated_raw)
        report["reason"] = (
            f"payload_change_invariant_failed:expected={[int(active_entry.index)]} actual={changed_payload_indices}"
        )
        return report

    native_table_after = parse_native_cfs_table(after_raw, NATIVE_CFS_PRIMARY_TABLE_OFFSET)
    native_page_after = find_native_cfs_record(native_table_after, "0.pa")
    if native_page_after is None:
        generated_hmi.write_bytes(generated_raw)
        report["reason"] = "post_rewrite_native_named_0pa_missing"
        return report
    native_page_after_bytes = after_raw[native_page_after.data_offset : native_page_after.data_offset + native_page_after.length]
    native_page_after_status = inspect_page_safe_status(native_page_after_bytes)
    report["native_named_0pa_after"] = {
        **native_page_after.to_dict(),
        "sha256": sha256(native_page_after_bytes).hexdigest(),
        "page_safe": native_page_after_status.to_dict(),
    }
    if native_page_after.data_offset != active_entry.data_offset or native_page_after.length != active_entry.length:
        generated_hmi.write_bytes(generated_raw)
        report["reason"] = "post_rewrite_native_named_0pa_not_retargeted"
        return report
    if native_page_after_status.safe_ok is not True:
        generated_hmi.write_bytes(generated_raw)
        report["reason"] = "post_rewrite_native_named_0pa_not_pagesafe"
        return report

    generated_candidates_after = _summarize_pa_like_entries(after_raw, after_inspection.entries)
    after_active = next((item for item in generated_candidates_after if item["entry_name"] == "0.pa"), None)
    if after_active is None or after_active["objects"] != expected_objects:
        generated_hmi.write_bytes(generated_raw)
        report["reason"] = "post_rewrite_active_page_mismatch"
        report["generated_candidates_after"] = generated_candidates_after
        return report

    report["applied"] = True
    report["family_id"] = "native_named_page_promote_v1"
    report["active_entry_index"] = int(active_entry.index)
    report["authoritative_shadow_index"] = int(native_page.index)
    report["reason"] = "applied_native_named_page_promote"
    report["generated_candidates_after"] = generated_candidates_after
    report["payload_changed_entry_indices"] = changed_payload_indices
    return report


def load_patch_spec_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Patch spec JSON must contain one object: {path}")
    return payload


def normalize_patch_spec(spec: dict[str, Any]) -> dict[str, Any]:
    if int(spec.get("schema_version", 0) or 0) != PATCH_SPEC_SCHEMA_VERSION:
        raise ValueError(
            f"Patch spec schema_version must be {PATCH_SPEC_SCHEMA_VERSION}, got {spec.get('schema_version')!r}"
        )
    donor_path = spec.get("donor_path") or spec.get("donor_hmi")
    if not donor_path:
        raise ValueError("Patch spec missing donor_path")
    operations = spec.get("operations")
    if not isinstance(operations, list) or not operations:
        raise ValueError("Patch spec must contain a non-empty operations list")

    normalized_ops: list[dict[str, Any]] = []
    for index, raw_op in enumerate(operations):
        if not isinstance(raw_op, dict):
            raise ValueError(f"Patch operation #{index} must be a JSON object")
        kind = raw_op.get("kind")
        if kind == "delete":
            normalized_ops.append({"kind": "delete", "object": _required_str(raw_op, "object", index)})
            continue
        if kind == "move":
            normalized_ops.append(
                {
                    "kind": "move",
                    "object": _required_str(raw_op, "object", index),
                    "x": _required_int(raw_op, "x", index),
                    "y": _required_int(raw_op, "y", index),
                    "w": _required_int(raw_op, "w", index),
                    "h": _required_int(raw_op, "h", index),
                }
            )
            continue
        if kind == "set-int":
            normalized_ops.append(
                {
                    "kind": "set-int",
                    "object": _required_str(raw_op, "object", index),
                    "field": _required_str(raw_op, "field", index),
                    "value": _required_int(raw_op, "value", index),
                }
            )
            continue
        if kind == "set-str":
            if "value" not in raw_op:
                raise ValueError(f"Patch operation #{index} missing value")
            normalized_ops.append(
                {
                    "kind": "set-str",
                    "object": _required_str(raw_op, "object", index),
                    "field": _required_str(raw_op, "field", index),
                    "value": str(raw_op["value"]),
                }
            )
            continue
        if kind == "graft":
            normalized_ops.append(
                {
                    "kind": "graft",
                    "source_hmi": str(Path(_required_str(raw_op, "source_hmi", index)).resolve()),
                    "source_page": _required_str(raw_op, "source_page", index),
                    "source_object": _required_str(raw_op, "source_object", index),
                    "target_object": _required_str(raw_op, "target_object", index),
                    "x": _required_int(raw_op, "x", index),
                    "y": _required_int(raw_op, "y", index),
                    "w": _required_int(raw_op, "w", index),
                    "h": _required_int(raw_op, "h", index),
                }
            )
            continue
        raise ValueError(f"Unsupported patch operation kind at #{index}: {kind!r}")

    expectations = spec.get("expectations") or {}
    if not isinstance(expectations, dict):
        raise ValueError("Patch spec expectations must be a JSON object")

    return {
        "schema_version": PATCH_SPEC_SCHEMA_VERSION,
        "case_id": str(spec.get("case_id") or Path(str(donor_path)).stem),
        "donor_path": str(Path(str(donor_path)).resolve()),
        "page": str(spec.get("page") or spec.get("page_entry") or "0.pa"),
        "probe_lowlevel": bool(spec.get("probe_lowlevel", False)),
        "probe_reopen": bool(spec.get("probe_reopen", False)),
        "shadow_sync_mode": str(spec.get("shadow_sync_mode") or SHADOW_SYNC_MODE_AUTO),
        "exact_donor": bool(spec.get("exact_donor", False)),
        "donor_kind": str(spec.get("donor_kind") or ("exact" if spec.get("exact_donor", False) else "derived")),
        "control_type": spec.get("control_type"),
        "control_name": spec.get("control_name"),
        "notes": str(spec.get("notes") or ""),
        "operations": normalized_ops,
        "expectations": {
            "page_name": str(expectations.get("page_name") or "page0"),
            "objects": _normalize_object_expectations(expectations.get("objects") or []),
            "strings": _normalize_string_expectations(expectations.get("strings") or []),
            "ints": _normalize_int_expectations(expectations.get("ints") or []),
            "resource_policy": str(
                expectations.get("resource_policy") or RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES
            ),
        },
    }


def _required_str(payload: dict[str, Any], key: str, index: int) -> str:
    value = payload.get(key)
    if value in (None, ""):
        raise ValueError(f"Patch operation #{index} missing {key}")
    return str(value)


def _required_int(payload: dict[str, Any], key: str, index: int) -> int:
    if key not in payload:
        raise ValueError(f"Patch operation #{index} missing {key}")
    return int(payload[key])


def _normalize_object_expectations(items: list[Any]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"Object expectation #{index} must be a JSON object")
        name = item.get("name")
        type_code = item.get("type")
        if not name or not type_code:
            raise ValueError(f"Object expectation #{index} requires name and type")
        normalized.append({"name": str(name), "type": str(type_code)})
    return normalized


def _normalize_string_expectations(items: list[Any]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"String expectation #{index} must be a JSON object")
        if "value" not in item:
            raise ValueError(f"String expectation #{index} missing value")
        normalized.append(
            {
                "object": _required_str(item, "object", index),
                "field": _required_str(item, "field", index),
                "value": str(item["value"]),
            }
        )
    return normalized


def _normalize_int_expectations(items: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"Int expectation #{index} must be a JSON object")
        normalized.append(
            {
                "object": _required_str(item, "object", index),
                "field": _required_str(item, "field", index),
                "value": _required_int(item, "value", index),
            }
        )
    return normalized


def _block_listing(blocks) -> list[dict[str, str]]:
    return [{"name": str(block.objname or ""), "type": str(block.type_code or "")} for block in blocks]


def _evaluate_string_expectations(blocks, expectations: list[dict[str, str]]) -> list[dict[str, Any]]:
    blocks_by_name = {block.objname: block for block in blocks if block.objname}
    results: list[dict[str, Any]] = []
    for item in expectations:
        block = blocks_by_name.get(item["object"])
        actual = None
        if block is not None and block.get_field(item["field"]) is not None:
            actual = block.get_field(item["field"]).value.decode("gbk", errors="ignore")
        results.append({**item, "actual": actual, "matches": actual == item["value"]})
    return results


def _evaluate_int_expectations(blocks, expectations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocks_by_name = {block.objname: block for block in blocks if block.objname}
    results: list[dict[str, Any]] = []
    for item in expectations:
        block = blocks_by_name.get(item["object"])
        actual = None
        if block is not None and block.get_field(item["field"]) is not None:
            actual = _block_int(block, item["field"])
        results.append({**item, "actual": actual, "matches": actual == item["value"]})
    return results


def _non_page_entry_fingerprint(inspection) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for entry in inspection.entries:
        if not entry.in_file:
            continue
        lower = entry.name.lower()
        if lower.endswith(".pa") or not entry.name:
            continue
        result.append(
            {
                "name": entry.name,
                "length": int(entry.length),
                "field3_hex": f"0x{int(entry.field3):X}",
            }
        )
    return result


def _derive_confidence(report: dict[str, Any]) -> str:
    if report.get("official_gui_reopen_ok") is False:
        return "failed"
    if report.get("official_gui_reopen_ok") is None and report.get("official_gui_reopen_error"):
        return "blocked"
    if report.get("open_lowlevel_ok") is False or report.get("compile_lowlevel_ok") is False:
        return "failed"
    if (
        report.get("page_matches_expected")
        and report.get("objects_match_expected")
        and report.get("strings_match_expected")
        and report.get("ints_match_expected")
        and report.get("resources_match_expected")
        and report.get("open_lowlevel_ok") is True
        and report.get("compile_lowlevel_ok") is True
    ):
            return "confirmed"
    if report.get("open_lowlevel_ok") is True and report.get("compile_lowlevel_ok") is True:
        return "likely"
    return "blocked"


def _safe_reopen_probe(hmi_path: Path, out_dir: Path) -> dict[str, Any]:
    try:
        return _run_reopen_probe(hmi_path, out_dir)
    except Exception as exc:
        return {
            "official_gui_reopen_ok": None,
            "official_gui_reopen_changed": None,
            "official_gui_reopen_before_objects": None,
            "official_gui_reopen_after_objects": None,
            "official_gui_reopen_json": None,
            "official_gui_reopen_error": f"{type(exc).__name__}: {exc}",
        }


def _run_reopen_probe(hmi_path: Path, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    reopen_input = out_dir / "reopen_input.HMI"
    shutil.copy2(hmi_path, reopen_input)
    command = [
        sys.executable,
        str(Path(__file__).resolve().parents[1] / "tools" / "official_hmi_reopen_probe.py"),
        str(reopen_input),
        "--out-dir",
        str(out_dir),
        "--page-index",
        "0",
        "--timeout-s",
        "120",
    ]
    proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode:
        raise RuntimeError(
            "official_hmi_reopen_probe.py failed with "
            f"exit code {proc.returncode}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    reopen = json.loads(proc.stdout)
    before_blocks = [{"name": item["objname"], "type": item["type_code"]} for item in reopen["before_blocks"]]
    after_blocks = [{"name": item["objname"], "type": item["type_code"]} for item in reopen["after_blocks"]]
    return {
        "official_gui_reopen_ok": (not reopen["changed"] and before_blocks == after_blocks),
        "official_gui_reopen_changed": bool(reopen["changed"]),
        "official_gui_reopen_before_objects": before_blocks,
        "official_gui_reopen_after_objects": after_blocks,
        "official_gui_reopen_json": str(out_dir / "reopen_probe.json"),
        "official_gui_reopen_error": None,
    }


def _require_block(blocks_by_name, objname: str):
    block = blocks_by_name.get(objname)
    if block is None:
        raise ValueError(f"Object {objname!r} not found")
    return block


def _parse_move_spec(spec: str) -> tuple[str, int, int, int, int]:
    objname, payload = spec.split(":", 1)
    parts = [int(item.strip(), 0) for item in payload.split(":")]
    if len(parts) != 4:
        raise ValueError(f"Invalid move spec {spec!r}; expected name:x:y:w:h")
    return objname, parts[0], parts[1], parts[2], parts[3]


def _parse_field_spec(spec: str) -> tuple[str, str, int]:
    left, value_text = spec.split("=", 1)
    objname, field_name = left.split(".", 1)
    return objname, field_name, int(value_text.strip(), 0)


def _parse_text_spec(spec: str) -> tuple[str, str, str]:
    left, value_text = spec.split("=", 1)
    objname, field_name = left.split(".", 1)
    return objname, field_name, value_text


def _parse_graft_spec(spec: str) -> tuple[Path, str, str, str, int, int, int, int]:
    parts = [item.strip() for item in spec.split("|")]
    if len(parts) != 8:
        raise ValueError(
            f"Invalid graft spec {spec!r}; expected source_hmi|page|source_obj|target_obj|x|y|w|h"
        )
    return (
        Path(parts[0]).resolve(),
        parts[1],
        parts[2],
        parts[3],
        int(parts[4], 0),
        int(parts[5], 0),
        int(parts[6], 0),
        int(parts[7], 0),
    )


def _refresh_end_fields(block) -> None:
    x = _block_int(block, "x")
    y = _block_int(block, "y")
    w = _block_int(block, "w")
    h = _block_int(block, "h")
    if w > 0 and block.get_field("endx") is not None:
        block.set_int("endx", x + w - 1, width=2)
    if h > 0 and block.get_field("endy") is not None:
        block.set_int("endy", y + h - 1, width=2)


def _block_int(block, field_name: str) -> int:
    field = block.get_field(field_name)
    if field is None or not field.value:
        return 0
    return int.from_bytes(field.value, "little")




if __name__ == "__main__":
    raise SystemExit(main())
