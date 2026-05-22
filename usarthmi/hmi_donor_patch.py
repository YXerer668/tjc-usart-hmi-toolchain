from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .editor import _rebuild_hmi_container
from .hmi_inspect import inspect_hmi
from .page_format import parse_page_data


PATCH_SPEC_SCHEMA_VERSION = 1
RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES = "preserve_non_page_entries"


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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_donor_patch_parser()
    args = parser.parse_args(argv)
    if args.spec_json is not None and args.donor_hmi is not None:
        parser.error("donor_hmi positional argument must be omitted when --spec-json is used")
    if args.spec_json is None and args.donor_hmi is None:
        parser.error("donor_hmi is required unless --spec-json is provided")
    spec = load_patch_spec_json(args.spec_json) if args.spec_json is not None else None
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
        spec=spec,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


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
        )
    )

    donor_hmi = Path(normalized_spec["donor_path"]).resolve()
    page_entry = str(normalized_spec["page"])
    probe_lowlevel = bool(normalized_spec.get("probe_lowlevel", False))

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
        "donor_resources": donor_resources,
        "generated_resources": generated_resources,
        "resources_match_expected": donor_resources == generated_resources,
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
