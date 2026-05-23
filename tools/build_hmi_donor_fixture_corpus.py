from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.official_hmi_lowlevel_probe import probe_official_lowlevel_hmi  # noqa: E402
from usarthmi.hmi_donor_patch import (  # noqa: E402
    PATCH_SPEC_SCHEMA_VERSION,
    RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
    _block_int,
    patch_hmi_donor,
)
from usarthmi.hmi_inspect import inspect_hmi  # noqa: E402
from usarthmi.page_format import parse_page_data  # noqa: E402
from usarthmi.widgets import WidgetWriter, iter_widget_type_infos  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
CASE_ROOT = Path(r"C:\Users\SinYu\Desktop\case_for_codex")
DEFAULT_OUT_ROOT = REPO_ROOT / "reverse_usarthmi" / "hmi_donor_lowlevel_probe_20260522"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the donor HMI fixture corpus, low-level summaries, and capability matrix."
    )
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT, help="Corpus output root")
    parser.add_argument("--probe-reopen", action="store_true", help="Also run official GUI reopen/save probes on donor and generated HMI copies")
    args = parser.parse_args()

    report = build_hmi_donor_fixture_corpus(args.out_root.resolve(), probe_reopen=args.probe_reopen)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def build_hmi_donor_fixture_corpus(out_root: Path, *, probe_reopen: bool = False) -> dict[str, Any]:
    out_root.mkdir(parents=True, exist_ok=True)
    specs_dir = out_root / "fixture_corpus" / "specs"
    fixtures_dir = out_root / "fixture_corpus" / "fixtures"
    donors_dir = out_root / "fixture_corpus" / "donor_probes"
    specs_dir.mkdir(parents=True, exist_ok=True)
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    donors_dir.mkdir(parents=True, exist_ok=True)

    schema_path = out_root / "patch_spec.schema.json"
    schema_path.write_text(json.dumps(_patch_spec_schema(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    donor_specs = _donor_probe_specs()
    fixture_specs = _fixture_specs()
    donor_specs.extend(_auto_exact_donor_specs(existing_case_ids={spec["case_id"] for spec in donor_specs}))
    fixture_specs.extend(_auto_modified_fixture_specs(existing_case_ids={spec["case_id"] for spec in fixture_specs}))

    donor_records = []
    for spec in donor_specs:
        probe_dir = donors_dir / spec["case_id"]
        probe_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(spec["donor_path"], probe_dir / "input_donor.HMI")
        result = probe_official_lowlevel_hmi(
            Path(spec["donor_path"]).resolve(),
            probe_dir,
            run_compile=True,
        )
        record = _summarize_donor_probe(spec, result)
        if probe_reopen:
            record.update(_safe_reopen_record_fields(Path(spec["donor_path"]), probe_dir / "official_reopen_probe"))
            _reconcile_reopen_status(record)
        capability_result = probe_dir / "capability_result.json"
        capability_result.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest = probe_dir / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "mode": "hmi_donor_probe_manifest",
                    "case_id": spec["case_id"],
                    "input_donor_hmi": str(probe_dir / "input_donor.HMI"),
                    "official_lowlevel_probe_json": str(probe_dir / f"{Path(spec['donor_path']).stem}.official_lowlevel.json"),
                    "open_lowlevel_output_json": str(probe_dir / "open_lowlevel.result.json"),
                    "compile_lowlevel_output_json": str(probe_dir / "compile_lowlevel.result.json"),
                    "capability_result_json": str(capability_result),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        donor_records.append(record)
    historical_case80 = _historical_case80_failed_record(donors_dir / "donor_case80_exact_historical_failed")
    if historical_case80 is not None:
        donor_records.append(historical_case80)

    fixture_records = []
    for spec in fixture_specs:
        spec_path = specs_dir / f"{spec['case_id']}.json"
        spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        fixture_dir = fixtures_dir / spec["case_id"]
        report = patch_hmi_donor(
            donor_hmi=None,
            out_dir=fixture_dir,
            spec=spec,
            probe_lowlevel=bool(spec.get("probe_lowlevel", True)),
        )
        record = _summarize_patch_fixture(spec, report)
        if probe_reopen:
            record.update(_safe_reopen_record_fields(Path(report["output_hmi"]), fixture_dir / "official_reopen_probe"))
            _reconcile_reopen_status(record)
        capability_result = fixture_dir / "capability_result.json"
        capability_result.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest_path = fixture_dir / "manifest.json"
        manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_payload.update(
            {
                "schema_path": str(schema_path),
                "spec_source_json": str(spec_path),
                "capability_result_json": str(capability_result),
            }
        )
        manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        fixture_records.append(record)

    summary_path = out_root / "donor_patch_capability_summary.json"
    summary_payload = {
        "schema_version": 1,
        "date": "2026-05-22",
        "schema_path": str(schema_path),
        "records": donor_records + fixture_records,
    }
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    reopen_safe_map_path = out_root / "reopen_safe_control_map.json"
    reopen_safe_map_path.write_text(
        json.dumps(_build_reopen_safe_control_map(summary_payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    matrix_path = out_root / "donor_patch_capability_matrix.md"
    matrix_path.write_text(_render_matrix(summary_payload), encoding="utf-8")

    corpus_manifest_path = out_root / "fixture_corpus" / "corpus_manifest.json"
    corpus_manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "schema_path": str(schema_path),
                "summary_json": str(summary_path),
                "matrix_md": str(matrix_path),
                "reopen_safe_control_map_json": str(reopen_safe_map_path),
                "specs_dir": str(specs_dir),
                "fixtures_dir": str(fixtures_dir),
                "donor_probes_dir": str(donors_dir),
                "fixture_case_ids": [spec["case_id"] for spec in fixture_specs],
                "donor_probe_case_ids": [spec["case_id"] for spec in donor_specs],
                "probe_reopen": probe_reopen,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "schema_path": str(schema_path),
        "summary_json": str(summary_path),
        "matrix_md": str(matrix_path),
        "reopen_safe_control_map_json": str(reopen_safe_map_path),
        "corpus_manifest_json": str(corpus_manifest_path),
        "fixture_case_ids": [spec["case_id"] for spec in fixture_specs],
        "donor_probe_case_ids": [spec["case_id"] for spec in donor_specs],
        "probe_reopen": probe_reopen,
    }


def _build_reopen_safe_control_map(summary: dict[str, Any]) -> dict[str, Any]:
    records = summary["records"]
    mapping: dict[str, Any] = {"schema_version": 1, "controls": {}}
    for record in records:
        if record["kind"] != "generated_fixture":
            continue
        if not (
            record.get("open_lowlevel_ok")
            and record.get("compile_lowlevel_ok")
            and record.get("official_gui_reopen_ok") is True
        ):
            continue
        control_type = record["control_type"]
        mapping["controls"].setdefault(
            control_type,
            {
                "case_id": record["case_id"],
                "generated_path": record["generated_path"],
                "operation": record["operation"],
                "control_name": record["control_name"],
                "confidence": record["confidence"],
            },
        )
    return mapping


def _patch_spec_schema() -> dict[str, Any]:
    return {
        "schema_version": PATCH_SPEC_SCHEMA_VERSION,
        "title": "HMI Donor Patch Spec",
        "description": "Validated donor/template-based HMI patch spec for the donor patch fixture factory.",
        "required_top_level_fields": ["schema_version", "case_id", "donor_path", "page", "operations"],
        "top_level_fields": {
            "case_id": "Stable fixture id",
            "donor_path": "Input donor HMI path",
            "page": "Target page entry, currently 0.pa",
            "probe_lowlevel": "Whether to run official open-lowlevel / compile-lowlevel",
            "control_type": "Human-readable control type label",
            "control_name": "Primary control/object name under study",
            "exact_donor": "Whether donor_path is an exact official donor",
            "donor_kind": "exact or derived",
            "notes": "Free-form notes carried into capability results",
            "expectations": {
                "page_name": "Expected parsed page name",
                "objects": [{"name": "objname", "type": "type code"}],
                "strings": [{"object": "objname", "field": "txt/path/filter/etc", "value": "string"}],
                "ints": [{"object": "objname", "field": "val/maxval/en/etc", "value": 1}],
                "resource_policy": RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
            },
        },
        "operation_kinds": {
            "delete": {"required": ["kind", "object"]},
            "move": {"required": ["kind", "object", "x", "y", "w", "h"]},
            "set-int": {"required": ["kind", "object", "field", "value"]},
            "set-str": {"required": ["kind", "object", "field", "value"]},
            "graft": {
                "required": [
                    "kind",
                    "source_hmi",
                    "source_page",
                    "source_object",
                    "target_object",
                    "x",
                    "y",
                    "w",
                    "h",
                ]
            },
        },
        "failure_policy": {
            "missing_required_field": "error",
            "invalid_operation_kind": "error",
            "missing_source_object": "error",
            "missing_target_field": "error",
            "nonzero_exit_on_error": True,
        },
    }


def _fixture_specs() -> list[dict[str, Any]]:
    case12 = str((CASE_ROOT / "case_12_text_yellow_font0" / "lcd_test.HMI").resolve())
    case13 = str((CASE_ROOT / "case_13_image_button_only" / "lcd_test.HMI").resolve())
    case16 = str((CASE_ROOT / "case_16_number_basic" / "lcd_test.HMI").resolve())
    case19 = str((CASE_ROOT / "case_19_timer" / "lcd_test.HMI").resolve())
    case42 = str((CASE_ROOT / "case_42_datarecord" / "lcd_test.HMI").resolve())
    case43 = str((CASE_ROOT / "case_43_filebrowser" / "lcd_test.HMI").resolve())
    case44 = str((CASE_ROOT / "case_44_filestream" / "lcd_test.HMI").resolve())
    case83 = str((CASE_ROOT / "case_83_datarecord_textselect_button_official_positive_oracle" / "lcd_test.HMI").resolve())
    case85 = str((CASE_ROOT / "case_85_datarecord_sltext_official_positive_oracle" / "lcd_test.HMI").resolve())
    return [
        {
            "schema_version": PATCH_SPEC_SCHEMA_VERSION,
            "case_id": "page0_text_set_str",
            "donor_path": case12,
            "page": "0.pa",
            "probe_lowlevel": True,
            "control_type": "text",
            "control_name": "fontmsg",
            "exact_donor": True,
            "donor_kind": "exact",
            "notes": "Confirmed built-in text set-str on a text donor page.",
            "operations": [{"kind": "set-str", "object": "fontmsg", "field": "txt", "value": "demo"}],
            "expectations": {
                "page_name": "page0",
                "objects": _objects(
                    ("page0", "y"),
                    ("t0", "t"),
                    ("b0", "b"),
                    ("p0", "p"),
                    ("fontmsg", "t"),
                ),
                "strings": [{"object": "fontmsg", "field": "txt", "value": "demo"}],
                "ints": [],
                "resource_policy": RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
            },
        },
        {
            "schema_version": PATCH_SPEC_SCHEMA_VERSION,
            "case_id": "page0_image_move",
            "donor_path": case13,
            "page": "0.pa",
            "probe_lowlevel": True,
            "control_type": "image",
            "control_name": "p0",
            "exact_donor": True,
            "donor_kind": "exact",
            "notes": "Confirmed built-in image move using the baseline p0 picture block.",
            "operations": [{"kind": "move", "object": "p0", "x": 581, "y": 224, "w": 92, "h": 92}],
            "expectations": {
                "page_name": "page0",
                "objects": _objects(
                    ("page0", "y"),
                    ("t0", "t"),
                    ("b0", "b"),
                    ("p0", "p"),
                    ("playbtn", "b"),
                ),
                "strings": [],
                "ints": [],
                "resource_policy": RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
            },
        },
        {
            "schema_version": PATCH_SPEC_SCHEMA_VERSION,
            "case_id": "page0_number_set_int",
            "donor_path": case16,
            "page": "0.pa",
            "probe_lowlevel": True,
            "control_type": "number",
            "control_name": "numval",
            "exact_donor": True,
            "donor_kind": "exact",
            "notes": "Confirmed built-in number set-int(val).",
            "operations": [{"kind": "set-int", "object": "numval", "field": "val", "value": 124}],
            "expectations": {
                "page_name": "page0",
                "objects": _objects(
                    ("page0", "y"),
                    ("t0", "t"),
                    ("b0", "b"),
                    ("p0", "p"),
                    ("numval", "6"),
                ),
                "strings": [],
                "ints": [{"object": "numval", "field": "val", "value": 124}],
                "resource_policy": RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
            },
        },
        {
            "schema_version": PATCH_SPEC_SCHEMA_VERSION,
            "case_id": "page0_timer_set_int",
            "donor_path": case19,
            "page": "0.pa",
            "probe_lowlevel": True,
            "control_type": "timer",
            "control_name": "tm0",
            "exact_donor": True,
            "donor_kind": "exact",
            "notes": "Confirmed built-in timer set-int(tim/en).",
            "operations": [
                {"kind": "set-int", "object": "tm0", "field": "tim", "value": 500},
                {"kind": "set-int", "object": "tm0", "field": "en", "value": 1},
            ],
            "expectations": {
                "page_name": "page0",
                "objects": _objects(
                    ("page0", "y"),
                    ("t0", "t"),
                    ("b0", "b"),
                    ("p0", "p"),
                    ("tm0", "3"),
                ),
                "strings": [],
                "ints": [{"object": "tm0", "field": "tim", "value": 500}, {"object": "tm0", "field": "en", "value": 1}],
                "resource_policy": RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
            },
        },
        {
            "schema_version": PATCH_SPEC_SCHEMA_VERSION,
            "case_id": "page0_basic_add_text_or_button",
            "donor_path": case85,
            "page": "0.pa",
            "probe_lowlevel": True,
            "shadow_sync_mode": "native-page-promote",
            "control_type": "button",
            "control_name": "b1",
            "exact_donor": True,
            "donor_kind": "exact",
            "notes": "Confirmed basic add through donor graft: add b1 from case83 into case85 donor.",
            "operations": [
                {
                    "kind": "graft",
                    "source_hmi": case83,
                    "source_page": "0.pa",
                    "source_object": "b1",
                    "target_object": "b1",
                    "x": 120,
                    "y": 120,
                    "w": 100,
                    "h": 50,
                }
            ],
            "expectations": {
                "page_name": "page0",
                "objects": _objects(
                    ("page0", "y"),
                    ("t0", "t"),
                    ("b0", "b"),
                    ("p0", "p"),
                    ("bar1", "j"),
                    ("data0", "B"),
                    ("slt0", ">"),
                    ("b1", "b"),
                ),
                "strings": [],
                "ints": [],
                "resource_policy": RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
            },
        },
        {
            "schema_version": PATCH_SPEC_SCHEMA_VERSION,
            "case_id": "page0_basic_delete",
            "donor_path": case83,
            "page": "0.pa",
            "probe_lowlevel": True,
            "shadow_sync_mode": "case83-delete-b1-gui",
            "control_type": "button",
            "control_name": "b1",
            "exact_donor": True,
            "donor_kind": "exact",
            "notes": "Confirmed basic delete on exact case83 donor.",
            "operations": [{"kind": "delete", "object": "b1"}],
            "expectations": {
                "page_name": "page0",
                "objects": _objects(
                    ("page0", "y"),
                    ("t0", "t"),
                    ("b0", "b"),
                    ("p0", "p"),
                    ("bar1", "j"),
                    ("data0", "B"),
                    ("select0", "D"),
                ),
                "strings": [],
                "ints": [],
                "resource_policy": RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
            },
        },
        {
            "schema_version": PATCH_SPEC_SCHEMA_VERSION,
            "case_id": "page0_basic_move",
            "donor_path": case83,
            "page": "0.pa",
            "probe_lowlevel": True,
            "control_type": "button",
            "control_name": "b1",
            "exact_donor": True,
            "donor_kind": "exact",
            "notes": "Confirmed basic move on exact case83 donor.",
            "operations": [{"kind": "move", "object": "b1", "x": 120, "y": 120, "w": 100, "h": 50}],
            "expectations": {
                "page_name": "page0",
                "objects": _objects(
                    ("page0", "y"),
                    ("t0", "t"),
                    ("b0", "b"),
                    ("p0", "p"),
                    ("bar1", "j"),
                    ("data0", "B"),
                    ("select0", "D"),
                    ("b1", "b"),
                ),
                "strings": [],
                "ints": [],
                "resource_policy": RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
            },
        },
        {
            "schema_version": PATCH_SPEC_SCHEMA_VERSION,
            "case_id": "page0_basic_set_txt",
            "donor_path": case83,
            "page": "0.pa",
            "probe_lowlevel": True,
            "control_type": "button",
            "control_name": "b1",
            "exact_donor": True,
            "donor_kind": "exact",
            "notes": "Confirmed basic set-str on exact case83 donor.",
            "operations": [{"kind": "set-str", "object": "b1", "field": "txt", "value": "lowlvl"}],
            "expectations": {
                "page_name": "page0",
                "objects": _objects(
                    ("page0", "y"),
                    ("t0", "t"),
                    ("b0", "b"),
                    ("p0", "p"),
                    ("bar1", "j"),
                    ("data0", "B"),
                    ("select0", "D"),
                    ("b1", "b"),
                ),
                "strings": [{"object": "b1", "field": "txt", "value": "lowlvl"}],
                "ints": [],
                "resource_policy": RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
            },
        },
        {
            "schema_version": PATCH_SPEC_SCHEMA_VERSION,
            "case_id": "page0_filebrowser_add_or_preserve",
            "donor_path": case42,
            "page": "0.pa",
            "probe_lowlevel": True,
            "shadow_sync_mode": "native-page-promote",
            "control_type": "file-browser",
            "control_name": "fbrowser0",
            "exact_donor": True,
            "donor_kind": "exact",
            "notes": "Confirmed file-browser add by grafting case43 fbrowser0 into case42 donor.",
            "operations": [
                {
                    "kind": "graft",
                    "source_hmi": case43,
                    "source_page": "0.pa",
                    "source_object": "fbrowser0",
                    "target_object": "fbrowser0",
                    "x": 40,
                    "y": 40,
                    "w": 240,
                    "h": 240,
                }
            ],
            "expectations": {
                "page_name": "page0",
                "objects": _objects(
                    ("page0", "y"),
                    ("t0", "t"),
                    ("b0", "b"),
                    ("p0", "p"),
                    ("data0", "B"),
                    ("fbrowser0", "A"),
                ),
                "strings": [],
                "ints": [],
                "resource_policy": RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
            },
        },
        {
            "schema_version": PATCH_SPEC_SCHEMA_VERSION,
            "case_id": "page0_textselect_add_or_preserve",
            "donor_path": case85,
            "page": "0.pa",
            "probe_lowlevel": True,
            "shadow_sync_mode": "native-page-promote",
            "control_type": "text-select",
            "control_name": "select0",
            "exact_donor": True,
            "donor_kind": "exact",
            "notes": "Confirmed text-select add by grafting case83 select0 into case85 donor.",
            "operations": [
                {
                    "kind": "graft",
                    "source_hmi": case83,
                    "source_page": "0.pa",
                    "source_object": "select0",
                    "target_object": "select0",
                    "x": 466,
                    "y": 78,
                    "w": 100,
                    "h": 32,
                }
            ],
            "expectations": {
                "page_name": "page0",
                "objects": _objects(
                    ("page0", "y"),
                    ("t0", "t"),
                    ("b0", "b"),
                    ("p0", "p"),
                    ("bar1", "j"),
                    ("data0", "B"),
                    ("slt0", ">"),
                    ("select0", "D"),
                ),
                "strings": [],
                "ints": [],
                "resource_policy": RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
            },
        },
        {
            "schema_version": PATCH_SPEC_SCHEMA_VERSION,
            "case_id": "page0_datarecord_add_or_preserve",
            "donor_path": case43,
            "page": "0.pa",
            "probe_lowlevel": True,
            "shadow_sync_mode": "native-page-promote",
            "control_type": "data-record",
            "control_name": "data0",
            "exact_donor": True,
            "donor_kind": "exact",
            "notes": "Confirmed data-record add by grafting case42 data0 into case43 donor.",
            "operations": [
                {
                    "kind": "graft",
                    "source_hmi": case42,
                    "source_page": "0.pa",
                    "source_object": "data0",
                    "target_object": "data0",
                    "x": 40,
                    "y": 40,
                    "w": 240,
                    "h": 240,
                }
            ],
            "expectations": {
                "page_name": "page0",
                "objects": _objects(
                    ("page0", "y"),
                    ("t0", "t"),
                    ("b0", "b"),
                    ("p0", "p"),
                    ("fbrowser0", "A"),
                    ("data0", "B"),
                ),
                "strings": [],
                "ints": [],
                "resource_policy": RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
            },
        },
        {
            "schema_version": PATCH_SPEC_SCHEMA_VERSION,
            "case_id": "page0_filestream_add_or_preserve",
            "donor_path": case42,
            "page": "0.pa",
            "probe_lowlevel": True,
            "shadow_sync_mode": "native-page-promote",
            "control_type": "file-stream",
            "control_name": "fs0",
            "exact_donor": True,
            "donor_kind": "exact",
            "notes": "Confirmed file-stream add by grafting case44 fs0 into case42 donor.",
            "operations": [
                {
                    "kind": "graft",
                    "source_hmi": case44,
                    "source_page": "0.pa",
                    "source_object": "fs0",
                    "target_object": "fs0",
                    "x": 40,
                    "y": 40,
                    "w": 240,
                    "h": 240,
                }
            ],
            "expectations": {
                "page_name": "page0",
                "objects": _objects(
                    ("page0", "y"),
                    ("t0", "t"),
                    ("b0", "b"),
                    ("p0", "p"),
                    ("data0", "B"),
                    ("fs0", "?"),
                ),
                "strings": [],
                "ints": [],
                "resource_policy": RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
            },
        },
        {
            "schema_version": PATCH_SPEC_SCHEMA_VERSION,
            "case_id": "case80_like_from_case83_delete_b1",
            "donor_path": case83,
            "page": "0.pa",
            "probe_lowlevel": True,
            "shadow_sync_mode": "case83-delete-b1-gui",
            "control_type": "button",
            "control_name": "b1",
            "exact_donor": True,
            "donor_kind": "exact",
            "notes": "Key control case: case80 exact donor fails low-level, but deleting b1 from case83 exact donor yields a case80-like HMI that passes.",
            "operations": [{"kind": "delete", "object": "b1"}],
            "expectations": {
                "page_name": "page0",
                "objects": _objects(
                    ("page0", "y"),
                    ("t0", "t"),
                    ("b0", "b"),
                    ("p0", "p"),
                    ("bar1", "j"),
                    ("data0", "B"),
                    ("select0", "D"),
                ),
                "strings": [],
                "ints": [],
                "resource_policy": RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
            },
        },
        {
            "schema_version": PATCH_SPEC_SCHEMA_VERSION,
            "case_id": "page0_datarecord_move_set_int",
            "donor_path": case42,
            "page": "0.pa",
            "probe_lowlevel": True,
            "control_type": "data-record",
            "control_name": "data0",
            "exact_donor": True,
            "donor_kind": "exact",
            "notes": "Confirmed data-record move and set-int(maxval).",
            "operations": [
                {"kind": "move", "object": "data0", "x": 40, "y": 40, "w": 240, "h": 240},
                {"kind": "set-int", "object": "data0", "field": "maxval", "value": 1001},
            ],
            "expectations": {
                "page_name": "page0",
                "objects": _objects(("page0", "y"), ("t0", "t"), ("b0", "b"), ("p0", "p"), ("data0", "B")),
                "strings": [],
                "ints": [{"object": "data0", "field": "maxval", "value": 1001}],
                "resource_policy": RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
            },
        },
        {
            "schema_version": PATCH_SPEC_SCHEMA_VERSION,
            "case_id": "page0_filebrowser_move_set_str",
            "donor_path": case43,
            "page": "0.pa",
            "probe_lowlevel": True,
            "control_type": "file-browser",
            "control_name": "fbrowser0",
            "exact_donor": True,
            "donor_kind": "exact",
            "notes": "Confirmed file-browser move and set-str(filter).",
            "operations": [
                {"kind": "move", "object": "fbrowser0", "x": 40, "y": 40, "w": 240, "h": 240},
                {"kind": "set-str", "object": "fbrowser0", "field": "filter", "value": "*.bmp"},
            ],
            "expectations": {
                "page_name": "page0",
                "objects": _objects(("page0", "y"), ("t0", "t"), ("b0", "b"), ("p0", "p"), ("fbrowser0", "A")),
                "strings": [{"object": "fbrowser0", "field": "filter", "value": "*.bmp"}],
                "ints": [],
                "resource_policy": RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
            },
        },
        {
            "schema_version": PATCH_SPEC_SCHEMA_VERSION,
            "case_id": "page0_filestream_set_int",
            "donor_path": case44,
            "page": "0.pa",
            "probe_lowlevel": True,
            "control_type": "file-stream",
            "control_name": "fs0",
            "exact_donor": True,
            "donor_kind": "exact",
            "notes": "Confirmed file-stream set-int(en/val).",
            "operations": [
                {"kind": "set-int", "object": "fs0", "field": "en", "value": 1},
                {"kind": "set-int", "object": "fs0", "field": "val", "value": 1},
            ],
            "expectations": {
                "page_name": "page0",
                "objects": _objects(("page0", "y"), ("t0", "t"), ("b0", "b"), ("p0", "p"), ("fs0", "?")),
                "strings": [],
                "ints": [{"object": "fs0", "field": "en", "value": 1}, {"object": "fs0", "field": "val", "value": 1}],
                "resource_policy": RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
            },
        },
        {
            "schema_version": PATCH_SPEC_SCHEMA_VERSION,
            "case_id": "page0_textselect_set_int",
            "donor_path": case83,
            "page": "0.pa",
            "probe_lowlevel": True,
            "control_type": "text-select",
            "control_name": "select0",
            "exact_donor": True,
            "donor_kind": "exact",
            "notes": "Confirmed text-select set-int(val).",
            "operations": [{"kind": "set-int", "object": "select0", "field": "val", "value": 1}],
            "expectations": {
                "page_name": "page0",
                "objects": _objects(
                    ("page0", "y"),
                    ("t0", "t"),
                    ("b0", "b"),
                    ("p0", "p"),
                    ("bar1", "j"),
                    ("data0", "B"),
                    ("select0", "D"),
                    ("b1", "b"),
                ),
                "strings": [],
                "ints": [{"object": "select0", "field": "val", "value": 1}],
                "resource_policy": RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
            },
        },
        {
            "schema_version": PATCH_SPEC_SCHEMA_VERSION,
            "case_id": "page0_textselect_delete",
            "donor_path": case83,
            "page": "0.pa",
            "probe_lowlevel": True,
            "shadow_sync_mode": "case83-delete-b1-gui",
            "control_type": "text-select",
            "control_name": "select0",
            "exact_donor": True,
            "donor_kind": "exact",
            "notes": "Confirmed text-select delete on exact case83 donor.",
            "operations": [{"kind": "delete", "object": "select0"}],
            "expectations": {
                "page_name": "page0",
                "objects": _objects(
                    ("page0", "y"),
                    ("t0", "t"),
                    ("b0", "b"),
                    ("p0", "p"),
                    ("bar1", "j"),
                    ("data0", "B"),
                    ("b1", "b"),
                ),
                "strings": [],
                "ints": [],
                "resource_policy": RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
            },
        },
        {
            "schema_version": PATCH_SPEC_SCHEMA_VERSION,
            "case_id": "page0_sltext_move_set_str",
            "donor_path": case85,
            "page": "0.pa",
            "probe_lowlevel": True,
            "control_type": "sliding-text",
            "control_name": "slt0",
            "exact_donor": True,
            "donor_kind": "exact",
            "notes": "Confirmed sliding-text move and set-str(txt).",
            "operations": [
                {"kind": "move", "object": "slt0", "x": 260, "y": 140, "w": 220, "h": 120},
                {"kind": "set-str", "object": "slt0", "field": "txt", "value": "demo"},
            ],
            "expectations": {
                "page_name": "page0",
                "objects": _objects(
                    ("page0", "y"),
                    ("t0", "t"),
                    ("b0", "b"),
                    ("p0", "p"),
                    ("bar1", "j"),
                    ("data0", "B"),
                    ("slt0", ">"),
                ),
                "strings": [{"object": "slt0", "field": "txt", "value": "demo"}],
                "ints": [],
                "resource_policy": RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
            },
        },
    ]


def _donor_probe_specs() -> list[dict[str, Any]]:
    return [
        _donor_probe_spec(
            "donor_text_exact",
            CASE_ROOT / "case_12_text_yellow_font0" / "lcd_test.HMI",
            "text",
            "fontmsg",
            "Exact built-in text donor probe from case12 text page.",
        ),
        _donor_probe_spec(
            "donor_image_exact",
            CASE_ROOT / "case_13_image_button_only" / "lcd_test.HMI",
            "image",
            "p0",
            "Exact built-in image donor probe using the baseline p0 picture block.",
        ),
        _donor_probe_spec(
            "donor_number_exact",
            CASE_ROOT / "case_16_number_basic" / "lcd_test.HMI",
            "number",
            "numval",
            "Exact built-in number donor probe from case16.",
        ),
        _donor_probe_spec(
            "donor_timer_exact",
            CASE_ROOT / "case_19_timer" / "lcd_test.HMI",
            "timer",
            "tm0",
            "Exact built-in timer donor probe from case19.",
        ),
        _donor_probe_spec(
            "donor_case42_exact",
            CASE_ROOT / "case_42_datarecord" / "lcd_test.HMI",
            "data-record",
            "data0",
            "Exact case42 donor is low-level accepted and usable as a donor/template lane.",
        ),
        _donor_probe_spec(
            "donor_case43_exact",
            CASE_ROOT / "case_43_filebrowser" / "lcd_test.HMI",
            "file-browser",
            "fbrowser0",
            "Exact case43 donor is low-level accepted and usable as a donor/template lane.",
        ),
        _donor_probe_spec(
            "donor_case44_exact",
            CASE_ROOT / "case_44_filestream" / "lcd_test.HMI",
            "file-stream",
            "fs0",
            "Exact case44 donor is low-level accepted and usable as a donor/template lane.",
        ),
        _donor_probe_spec(
            "donor_case80_exact_current",
            CASE_ROOT / "case_80_datarecord_textselect_official_positive_oracle" / "lcd_test.HMI",
            "data-record+text-select",
            "data0/select0",
            "Current exact case80 donor is low-level accepted. Historical negative evidence still exists for an older exact sample and is recorded separately.",
        ),
        _donor_probe_spec(
            "donor_case83_exact",
            CASE_ROOT / "case_83_datarecord_textselect_button_official_positive_oracle" / "lcd_test.HMI",
            "data-record+text-select+button",
            "data0/select0/b1",
            "Exact case83 donor is low-level accepted and currently the strongest exact mixed donor lane.",
        ),
        _donor_probe_spec(
            "donor_case85_exact",
            CASE_ROOT / "case_85_datarecord_sltext_official_positive_oracle" / "lcd_test.HMI",
            "data-record+sliding-text",
            "data0/slt0",
            "Exact case85 donor is low-level accepted and supports both preserve and patch lanes.",
        ),
    ]


def _donor_probe_spec(case_id: str, path: Path, control_type: str, control_name: str, notes: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "donor_path": str(path.resolve()),
        "control_type": control_type,
        "control_name": control_name,
        "page": "0.pa",
        "notes": notes,
    }


def _auto_exact_donor_specs(*, existing_case_ids: set[str]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    manual_types = {"data-record", "file-browser", "file-stream"}
    for info in iter_widget_type_infos():
        if info.writer != WidgetWriter.FIXTURE or not info.fixture_case or info.type_code is None:
            continue
        if info.type in manual_types:
            continue
        donor_path = _resolve_fixture_hmi_path(info.fixture_case)
        if donor_path is None:
            continue
        primary = _load_primary_fixture_block(donor_path, info.type_code)
        if primary is None:
            continue
        case_id = f"donor_{info.type.replace('-', '_')}_exact"
        if case_id in existing_case_ids:
            continue
        specs.append(
            _donor_probe_spec(
                case_id,
                donor_path,
                info.type,
                primary["objname"],
                f"Exact {info.type} donor ({info.fixture_case}) is low-level acceptance probe from the canonical fixture case.",
            )
        )
    return specs


def _auto_modified_fixture_specs(*, existing_case_ids: set[str]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    manual_types = {"button", "data-record", "file-browser", "file-stream", "sliding-text", "text-select"}
    for info in iter_widget_type_infos():
        if info.writer != WidgetWriter.FIXTURE or not info.fixture_case or info.type_code is None:
            continue
        if info.type in manual_types:
            continue
        donor_path = _resolve_fixture_hmi_path(info.fixture_case)
        if donor_path is None:
            continue
        primary = _load_primary_fixture_block(donor_path, info.type_code)
        if primary is None:
            continue
        case_id = f"page0_{info.type.replace('-', '_')}_auto_modify"
        if case_id in existing_case_ids:
            continue
        spec = _auto_modified_fixture_spec(info.type, donor_path, primary)
        if spec is not None:
            specs.append(spec)
    return specs


def _resolve_fixture_hmi_path(case_name: str) -> Path | None:
    direct = CASE_ROOT / case_name / "lcd_test.HMI"
    if direct.exists():
        return direct
    official = CASE_ROOT / case_name / "official_wiki" / "source_raw.HMI"
    if official.exists():
        return official
    return None


def _load_primary_fixture_block(donor_path: Path, type_code: str) -> dict[str, Any] | None:
    inspection = inspect_hmi(donor_path)
    raw = donor_path.read_bytes()
    entry = next((item for item in inspection.entries if item.name == "0.pa"), None)
    if entry is None:
        return None
    page = parse_page_data(raw[entry.data_offset : entry.data_offset + entry.length])
    matches = [block for block in page.blocks if block.type_code == type_code]
    if not matches:
        return None
    block = matches[0]
    return {
        "objname": str(block.objname or ""),
        "can_move": all(block.get_field(name) is not None for name in ("x", "y", "w", "h", "endx", "endy")),
        "int_fields": [
            name
            for name in ("val", "en", "maxval", "tim", "dis", "vid", "wid", "ch", "font", "bco", "pco", "pic", "picc")
            if block.get_field(name) is not None
        ],
        "str_fields": [
            name
            for name in ("txt", "filter", "path", "dir")
            if block.get_field(name) is not None
        ],
        "x": _block_int(block, "x"),
        "y": _block_int(block, "y"),
        "w": _block_int(block, "w"),
        "h": _block_int(block, "h"),
    }


def _auto_modified_fixture_spec(control_type: str, donor_path: Path, primary: dict[str, Any]) -> dict[str, Any] | None:
    objname = primary["objname"]
    operations: list[dict[str, Any]] = []
    expected_strings: list[dict[str, Any]] = []
    expected_ints: list[dict[str, Any]] = []
    note = ""

    if primary["can_move"] and primary["w"] > 0 and primary["h"] > 0:
        operations.append(
            {
                "kind": "move",
                "object": objname,
                "x": int(primary["x"]) + 1,
                "y": int(primary["y"]) + 1,
                "w": int(primary["w"]),
                "h": int(primary["h"]),
            }
        )
        note = "Auto-generated minimal mutation uses geometry move on the primary donor block."
    elif primary["int_fields"]:
        field = primary["int_fields"][0]
        value = 1
        operations.append({"kind": "set-int", "object": objname, "field": field, "value": value})
        expected_ints.append({"object": objname, "field": field, "value": value})
        note = f"Auto-generated minimal mutation uses integer field {field} on the primary donor block."
    elif primary["str_fields"]:
        field = primary["str_fields"][0]
        value = "demo"
        operations.append({"kind": "set-str", "object": objname, "field": field, "value": value})
        expected_strings.append({"object": objname, "field": field, "value": value})
        note = f"Auto-generated minimal mutation uses string field {field} on the primary donor block."
    else:
        return None

    return {
        "schema_version": PATCH_SPEC_SCHEMA_VERSION,
        "case_id": f"page0_{control_type.replace('-', '_')}_auto_modify",
        "donor_path": str(donor_path.resolve()),
        "page": "0.pa",
        "probe_lowlevel": True,
        "control_type": control_type,
        "control_name": objname,
        "exact_donor": True,
        "donor_kind": "exact",
        "notes": note,
        "operations": operations,
        "expectations": {
            "page_name": "page0",
            "objects": [],
            "strings": expected_strings,
            "ints": expected_ints,
            "resource_policy": RESOURCE_EXPECTATION_PRESERVE_NON_PAGE_ENTRIES,
        },
    }


def _summarize_donor_probe(spec: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    actual_objects = _inspect_page_objects(Path(spec["donor_path"]))
    open_ok = result["accepted_by_open_lowlevel"]
    compile_ok = result["accepted_by_compile_lowlevel"]
    notes = spec["notes"]
    if not open_ok:
        notes = f"{notes} open-lowlevel rejected this donor; compare with case80_like_from_case83_delete_b1."
    confidence = "confirmed" if open_ok and compile_ok else "failed"
    return {
        "kind": "exact_donor_probe",
        "case_id": spec["case_id"],
        "donor_path": spec["donor_path"],
        "generated_path": spec["donor_path"],
        "operation": "preserve-exact-donor",
        "operations": [],
        "control_type": spec["control_type"],
        "control_name": spec["control_name"],
        "page": spec["page"],
        "open_lowlevel_ok": open_ok,
        "compile_lowlevel_ok": compile_ok,
        "expected_objects": actual_objects,
        "actual_objects": actual_objects,
        "object_expectation_ok": True,
        "page_expectation_ok": True,
        "string_expectation_ok": True,
        "resource_expectation_ok": True,
        "notes": notes,
        "confidence": confidence,
        "donor_kind": "exact",
        "generated_kind": "exact",
        "exact_donor": True,
        "probe_input_sha256": result.get("input_hmi_sha256"),
        "open_lowlevel_output_json": str(Path(result["open_lowlevel"]["result_json"]).resolve()),
        "compile_lowlevel_output_json": str(Path(result["compile_lowlevel"]["result_json"]).resolve()) if result.get("compile_lowlevel") else None,
        "capability_result_json": str((Path(result["open_lowlevel"]["result_json"]).parent / "capability_result.json").resolve()),
        "manifest_json": str((Path(result["open_lowlevel"]["result_json"]).parent / "manifest.json").resolve()),
        "dynamic_snapshot_goal_a_ready": bool(open_ok and compile_ok),
        "failed_reason": None if open_ok and compile_ok else "open-lowlevel rejected exact donor",
        "official_gui_reopen_ok": None,
        "official_gui_reopen_changed": None,
        "official_gui_reopen_before_objects": None,
        "official_gui_reopen_after_objects": None,
        "official_gui_reopen_json": None,
    }


def _summarize_patch_fixture(spec: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    operation_summary = "+".join(op["kind"] for op in report["operations"])
    return {
        "kind": "generated_fixture",
        "case_id": spec["case_id"],
        "donor_path": spec["donor_path"],
        "generated_path": report["output_hmi"],
        "operation": operation_summary,
        "operations": report["operations"],
        "control_type": spec["control_type"],
        "control_name": spec["control_name"],
        "page": spec["page"],
        "open_lowlevel_ok": report["open_lowlevel_ok"],
        "compile_lowlevel_ok": report["compile_lowlevel_ok"],
        "expected_objects": report["expected_objects"],
        "actual_objects": report["actual_objects"],
        "object_expectation_ok": report["objects_match_expected"],
        "page_expectation_ok": report["page_matches_expected"],
        "string_expectation_ok": report["strings_match_expected"],
        "resource_expectation_ok": report["resources_match_expected"],
        "notes": spec["notes"],
        "confidence": report["confidence"],
        "donor_kind": spec.get("donor_kind", "exact"),
        "generated_kind": "generated",
        "exact_donor": bool(spec.get("exact_donor", False)),
        "probe_input_sha256": report.get("official_lowlevel_probe", {}).get("input_hmi_sha256"),
        "open_lowlevel_output_json": report.get("open_lowlevel_output_json"),
        "compile_lowlevel_output_json": report.get("compile_lowlevel_output_json"),
        "capability_result_json": report.get("capability_result_json"),
        "manifest_json": report.get("manifest_json"),
        "dynamic_snapshot_goal_a_ready": bool(
            report.get("open_lowlevel_ok")
            and report.get("compile_lowlevel_ok")
            and report.get("page_matches_expected")
            and report.get("objects_match_expected")
            and report.get("strings_match_expected")
            and report.get("resources_match_expected")
        ),
        "failed_reason": None if report.get("confidence") != "failed" else "generated fixture rejected by low-level gate",
        "official_gui_reopen_ok": None,
        "official_gui_reopen_changed": None,
        "official_gui_reopen_before_objects": None,
        "official_gui_reopen_after_objects": None,
        "official_gui_reopen_json": None,
    }


def _run_reopen_probe(hmi_path: Path, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    reopen_input = out_dir / "reopen_input.HMI"
    shutil.copy2(hmi_path, reopen_input)
    command = [
        sys.executable,
        str(REPO_ROOT / "tools" / "official_hmi_reopen_probe.py"),
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
    return json.loads(proc.stdout)


def _reopen_record_fields(reopen: dict[str, Any]) -> dict[str, Any]:
    before_blocks = [{"name": item["objname"], "type": item["type_code"]} for item in reopen["before_blocks"]]
    after_blocks = [{"name": item["objname"], "type": item["type_code"]} for item in reopen["after_blocks"]]
    reopen_ok = not reopen["changed"] and before_blocks == after_blocks
    return {
        "official_gui_reopen_ok": reopen_ok,
        "official_gui_reopen_changed": bool(reopen["changed"]),
        "official_gui_reopen_before_objects": before_blocks,
        "official_gui_reopen_after_objects": after_blocks,
        "official_gui_reopen_json": str(Path(reopen["screenshot"]).parent / "reopen_probe.json"),
        "official_gui_reopen_error": None,
    }


def _safe_reopen_record_fields(hmi_path: Path, out_dir: Path) -> dict[str, Any]:
    try:
        return _reopen_record_fields(_run_reopen_probe(hmi_path, out_dir))
    except Exception as exc:
        return {
            "official_gui_reopen_ok": None,
            "official_gui_reopen_changed": None,
            "official_gui_reopen_before_objects": None,
            "official_gui_reopen_after_objects": None,
            "official_gui_reopen_json": None,
            "official_gui_reopen_error": f"{type(exc).__name__}: {exc}",
        }


def _reconcile_reopen_status(record: dict[str, Any]) -> None:
    reopen_ok = record.get("official_gui_reopen_ok")
    if reopen_ok is True:
        return
    if reopen_ok is False:
        record["confidence"] = "failed"
        record["failed_reason"] = "official GUI reopen/save changed the object list"
        record["dynamic_snapshot_goal_a_ready"] = False
        return
    if record.get("official_gui_reopen_error"):
        record["confidence"] = "blocked"
        record["failed_reason"] = record["official_gui_reopen_error"]
        record["dynamic_snapshot_goal_a_ready"] = False


def _render_matrix(summary: dict[str, Any]) -> str:
    records = summary["records"]
    donor_rows = [row for row in records if row["kind"] in {"exact_donor_probe", "historical_lowlevel_probe"}]
    fixture_rows = [row for row in records if row["kind"] == "generated_fixture"]

    def yesno(value: bool | None) -> str:
        if value is True:
            return "yes"
        if value is False:
            return "no"
        return "n/a"

    def object_summary(row: dict[str, Any]) -> str:
        return ", ".join(f"{item['name']}:{item['type']}" for item in row["actual_objects"])

    lines = [
        "# Donor Patch Capability Matrix",
        "",
        "This directory captures the donor/template-based HMI fixture factory. It is not a from-scratch HMI writer.",
        "",
        "Boundary:",
        "- The factory preserves donor container shape and page shadow chain.",
        "- `open-lowlevel` / `compile-lowlevel` acceptance is recorded here; it is not runtime proof.",
        "- A failed donor does not prove the control payload itself is impossible; container shape can dominate the result.",
        "",
        "## Exact Donors",
        "",
        "| case_id | donor_kind | generated_kind | generated_path | control | open-lowlevel | compile-lowlevel | gui-reopen | object list | page ok | objects ok | strings ok | resources ok | failed reason | confidence | notes |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in donor_rows:
        lines.append(
            f"| {row['case_id']} | {row['donor_kind']} | {row['generated_kind']} | `{_display_path(row['generated_path'])}` | {row['control_type']} | {yesno(row['open_lowlevel_ok'])} | {yesno(row['compile_lowlevel_ok'])} | {yesno(row.get('official_gui_reopen_ok'))} | {object_summary(row)} | {yesno(row['page_expectation_ok'])} | {yesno(row['object_expectation_ok'])} | {yesno(row['string_expectation_ok'])} | {yesno(row['resource_expectation_ok'])} | {row['failed_reason'] or ''} | {row['confidence']} | {row['notes']} |"
        )

    lines.extend(
        [
            "",
            "## Generated Fixtures",
            "",
            "| case_id | donor_kind | generated_kind | operation | control | generated_path | open-lowlevel | compile-lowlevel | gui-reopen | object list | page ok | objects ok | strings ok | resources ok | failed reason | confidence |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for row in fixture_rows:
        lines.append(
            f"| {row['case_id']} | {row['donor_kind']} | {row['generated_kind']} | {row['operation']} | {row['control_type']}:{row['control_name']} | `{_display_path(row['generated_path'])}` | {yesno(row['open_lowlevel_ok'])} | {yesno(row['compile_lowlevel_ok'])} | {yesno(row.get('official_gui_reopen_ok'))} | {object_summary(row)} | {yesno(row['page_expectation_ok'])} | {yesno(row['object_expectation_ok'])} | {yesno(row['string_expectation_ok'])} | {yesno(row['resource_expectation_ok'])} | {row['failed_reason'] or ''} | {row['confidence']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `case42/43/44/80(current)/83/85` exact donors are currently usable because the official low-level path accepts them directly.",
            "- A historical exact `case80` sample still exists in the artifact trail and failed low-level earlier. That negative must not be confused with the current donor bytes.",
            "- `case80_like_from_case83_delete_b1` remains important because it proves a case80-like visible page shape can be produced from a different donor container lineage and still pass low-level.",
            "- The practical rule is to trust donor container revision/container shape first, control payload second.",
            "",
            "## Goal A Handoff",
            "",
            "The following fixtures are ready to feed the dynamic snapshot Goal A lane because they are low-level accepted and their page/object/string/resource expectations are recorded in JSON:",
            "",
        ]
    )
    for row in fixture_rows:
        if row["dynamic_snapshot_goal_a_ready"]:
            lines.append(f"- `{row['case_id']}`")
    lines.extend(
        [
            "",
            "For a case80-like generated sample, prefer `case80_like_from_case83_delete_b1`; for the current exact case80 donor, keep the historical failed record in mind and do not generalize across donor revisions.",
            "",
        ]
    )
    return "\n".join(lines)


def _display_path(raw_path: str) -> str:
    path = Path(raw_path)
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except Exception:
        try:
            return str(path.resolve().relative_to(CASE_ROOT))
        except Exception:
            return str(path)


def _historical_case80_failed_record(out_dir: Path) -> dict[str, Any] | None:
    historical_json = REPO_ROOT / "reverse_usarthmi" / "hmi_donor_lowlevel_probe_20260522" / "case80_exact" / "lcd_test.official_lowlevel.json"
    if not historical_json.exists():
        return None
    payload = json.loads(historical_json.read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    copied_open = out_dir / "open_lowlevel.result.json"
    copied_compile = out_dir / "compile_lowlevel.result.json"
    copied_probe = out_dir / "historical_case80_exact.official_lowlevel.json"
    source_open = historical_json.parent / "open_lowlevel.result.json"
    source_compile = historical_json.parent / "compile_lowlevel.result.json"
    if source_open.exists():
        shutil.copy2(source_open, copied_open)
    if source_compile.exists():
        shutil.copy2(source_compile, copied_compile)
    shutil.copy2(historical_json, copied_probe)
    donor_path = str(payload["hmi"])
    actual_objects = _inspect_page_objects(Path(donor_path))
    record = {
        "kind": "historical_lowlevel_probe",
        "case_id": "donor_case80_exact_historical_failed",
        "donor_path": donor_path,
        "generated_path": donor_path,
        "operation": "historical-exact-donor-probe",
        "operations": [],
        "control_type": "data-record+text-select",
        "control_name": "data0/select0",
        "page": "0.pa",
        "open_lowlevel_ok": payload["accepted_by_open_lowlevel"],
        "compile_lowlevel_ok": payload["accepted_by_compile_lowlevel"],
        "expected_objects": actual_objects,
        "actual_objects": actual_objects,
        "object_expectation_ok": True,
        "page_expectation_ok": True,
        "string_expectation_ok": True,
        "resource_expectation_ok": True,
        "notes": (
            "Historical negative control: an earlier exact case80 donor sample failed open-lowlevel/compile-lowlevel. "
            "This record is kept to show donor revision sensitivity."
        ),
        "confidence": "failed",
        "donor_kind": "historical-exact",
        "generated_kind": "historical-exact",
        "exact_donor": True,
        "probe_input_sha256": payload.get("input_hmi_sha256"),
        "open_lowlevel_output_json": str(copied_open) if copied_open.exists() else None,
        "compile_lowlevel_output_json": str(copied_compile) if copied_compile.exists() else None,
        "capability_result_json": str(out_dir / "capability_result.json"),
        "manifest_json": str(out_dir / "manifest.json"),
        "dynamic_snapshot_goal_a_ready": False,
        "failed_reason": "historical exact donor sample was rejected by low-level gate",
    }
    (out_dir / "capability_result.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "mode": "historical_hmi_donor_probe_manifest",
                "case_id": record["case_id"],
                "historical_probe_json": str(copied_probe),
                "open_lowlevel_output_json": record["open_lowlevel_output_json"],
                "compile_lowlevel_output_json": record["compile_lowlevel_output_json"],
                "capability_result_json": record["capability_result_json"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return record


def _inspect_page_objects(path: Path, page_entry: str = "0.pa") -> list[dict[str, str]]:
    inspection = inspect_hmi(path)
    raw = path.read_bytes()
    entry = next(item for item in inspection.entries if item.name == page_entry)
    page = parse_page_data(raw[entry.data_offset : entry.data_offset + entry.length])
    return [{"name": str(block.objname or ""), "type": str(block.type_code or "")} for block in page.blocks]


def _objects(*pairs: tuple[str, str]) -> list[dict[str, str]]:
    return [{"name": name, "type": type_code} for name, type_code in pairs]


if __name__ == "__main__":
    raise SystemExit(main())
