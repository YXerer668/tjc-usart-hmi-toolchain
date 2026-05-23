from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import subprocess
import sys

from usarthmi.hmi_donor_patch import (
    SHADOW_SYNC_MODE_CASE83_DELETE_B1_GUI,
    SHADOW_SYNC_MODE_NATIVE_PAGE_PROMOTE,
    SHADOW_SYNC_MODE_OFF,
    _parse_graft_spec,
    _parse_field_spec,
    _parse_move_spec,
    _parse_text_spec,
    _refresh_end_fields,
    generate_reopen_safe_fixture,
    normalize_patch_spec,
    patch_hmi_donor,
)
from usarthmi.hmi_cfs import NATIVE_CFS_PRIMARY_TABLE_OFFSET, find_native_cfs_record, parse_native_cfs_table
from usarthmi.hmi_inspect import inspect_hmi
from usarthmi.hmi_pagesafe import inspect_page_safe_status
from usarthmi.page_format import BlockField, PageBlock, parse_page_data


CASE_83_HMI = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_83_datarecord_textselect_button_official_positive_oracle\lcd_test.HMI")
CORPUS_ROOT = Path(r"C:\Users\SinYu\Documents\Codex\2026-05-03\files-mentioned-by-the-user-delay\reverse_usarthmi\hmi_donor_lowlevel_probe_20260522")
PAGE0_BASIC_DELETE_FIXTURE_DIR = CORPUS_ROOT / "fixture_corpus" / "fixtures" / "page0_basic_delete"
PAGE0_BASIC_DELETE_DONOR = PAGE0_BASIC_DELETE_FIXTURE_DIR / "input_donor.HMI"
FILEBROWSER_ADD_SPEC = CORPUS_ROOT / "fixture_corpus" / "specs" / "page0_filebrowser_add_or_preserve.json"
BASIC_ADD_SPEC = CORPUS_ROOT / "fixture_corpus" / "specs" / "page0_basic_add_text_or_button.json"
TEXTSELECT_ADD_SPEC = CORPUS_ROOT / "fixture_corpus" / "specs" / "page0_textselect_add_or_preserve.json"
DATARECORD_ADD_SPEC = CORPUS_ROOT / "fixture_corpus" / "specs" / "page0_datarecord_add_or_preserve.json"
FILESTREAM_ADD_SPEC = CORPUS_ROOT / "fixture_corpus" / "specs" / "page0_filestream_add_or_preserve.json"


class HMIDonorPatchTests(unittest.TestCase):
    def _load_promote_spec(self, spec_path: Path) -> dict[str, object] | None:
        if not spec_path.exists():
            self.skipTest(f"repo-local spec missing: {spec_path}")
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        donor_path = Path(spec["donor_path"])
        source_path = Path(spec["operations"][0]["source_hmi"])
        if not donor_path.exists() or not source_path.exists():
            self.skipTest(f"local donor/source HMI paths for {spec_path.name} are not available")
        spec["probe_reopen"] = True
        return spec

    def _assert_promote_spec_passes(self, spec_path: Path, *, force_mode: str | None = SHADOW_SYNC_MODE_NATIVE_PAGE_PROMOTE) -> None:
        spec = self._load_promote_spec(spec_path)
        if force_mode is None:
            spec.pop("shadow_sync_mode", None)
        else:
            spec["shadow_sync_mode"] = force_mode
        with tempfile.TemporaryDirectory() as temp_dir:
            report = patch_hmi_donor(
                donor_hmi=None,
                out_dir=Path(temp_dir),
                spec=spec,
                probe_lowlevel=True,
                probe_reopen=True,
            )
            self.assertTrue(report["experimental_shadow_sync_applied"])
            self.assertEqual(report["experimental_shadow_sync_reason"], "applied_native_named_page_promote")
            self.assertTrue(report["open_lowlevel_ok"])
            self.assertTrue(report["compile_lowlevel_ok"])
            self.assertTrue(report["official_gui_reopen_ok"])

    def test_parse_move_spec(self) -> None:
        self.assertEqual(_parse_move_spec("b1:10:20:30:40"), ("b1", 10, 20, 30, 40))

    def test_parse_field_spec(self) -> None:
        self.assertEqual(_parse_field_spec("b1.val=255"), ("b1", "val", 255))

    def test_parse_text_spec(self) -> None:
        self.assertEqual(_parse_text_spec("b1.txt=newtxt"), ("b1", "txt", "newtxt"))

    def test_parse_graft_spec(self) -> None:
        spec = r"C:\tmp\src.HMI|0.pa|b1|b9|10|20|30|40"
        parsed = _parse_graft_spec(spec)
        self.assertEqual(parsed[1:], ("0.pa", "b1", "b9", 10, 20, 30, 40))
        self.assertTrue(str(parsed[0]).lower().endswith(r"tmp\src.hmi"))

    def test_refresh_end_fields_uses_current_geometry(self) -> None:
        block = PageBlock(
            attr_name="block",
            attr_marker=0x12,
            fields=[
                BlockField("x", (10).to_bytes(2, "little"), 0x12),
                BlockField("y", (20).to_bytes(2, "little"), 0x12),
                BlockField("w", (30).to_bytes(2, "little"), 0x12),
                BlockField("h", (40).to_bytes(2, "little"), 0x12),
                BlockField("endx", (0).to_bytes(2, "little"), 0x12),
                BlockField("endy", (0).to_bytes(2, "little"), 0x12),
            ],
            event_tokens=[],
        )
        _refresh_end_fields(block)
        self.assertEqual(int.from_bytes(block.get_field("endx").value, "little"), 39)
        self.assertEqual(int.from_bytes(block.get_field("endy").value, "little"), 59)

    def test_normalize_patch_spec_rejects_missing_required_operation_field(self) -> None:
        spec = {
            "schema_version": 1,
            "case_id": "bad-spec",
            "donor_path": r"C:\tmp\dummy.HMI",
            "page": "0.pa",
            "operations": [{"kind": "move", "object": "b1", "x": 1, "y": 2, "w": 3}],
        }
        with self.assertRaisesRegex(ValueError, "missing h"):
            normalize_patch_spec(spec)

    @unittest.skipUnless(CASE_83_HMI.exists(), "local case83 donor HMI is not available")
    def test_patch_hmi_donor_can_delete_b1_from_case83(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = patch_hmi_donor(
                donor_hmi=CASE_83_HMI,
                out_dir=Path(temp_dir),
                delete_objects=["b1"],
                probe_lowlevel=False,
            )
            output_hmi = Path(report["output_hmi"])
            blocks = {(block.objname, block.type_code) for block in inspect_hmi(output_hmi).pa_blocks}
            self.assertNotIn(("b1", "b"), blocks)
            self.assertIn(("select0", "D"), blocks)
            self.assertTrue(Path(report["patch_spec_json"]).exists())
            self.assertTrue(Path(report["capability_result_json"]).exists())
            self.assertTrue(Path(report["manifest_json"]).exists())

    @unittest.skipUnless(CASE_83_HMI.exists(), "local case83 donor HMI is not available")
    def test_cli_donor_patch_returns_json_report(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        script = repo_root / "tools" / "hmi_donor_patch.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    str(CASE_83_HMI),
                    "--out-dir",
                    temp_dir,
                    "--delete-obj",
                    "b1",
                ],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["operations"][0], {"kind": "delete", "object": "b1"})
            self.assertTrue(Path(payload["output_hmi"]).exists())

    def test_cli_donor_patch_spec_json_missing_required_field_returns_nonzero(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        script = repo_root / "tools" / "hmi_donor_patch.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            spec_path = temp_path / "bad_spec.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "case_id": "bad-spec",
                        "donor_path": str(CASE_83_HMI),
                        "page": "0.pa",
                        "operations": [{"kind": "set-int", "object": "b1", "field": "val"}],
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--spec-json",
                    str(spec_path),
                    "--out-dir",
                    str(temp_path / "out"),
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing value", result.stderr.lower())

    def test_generate_reopen_safe_fixture_uses_control_map_when_available(self) -> None:
        control_map = CORPUS_ROOT / "reopen_safe_control_map.json"
        if not control_map.exists():
            self.skipTest(f"local reopen-safe control map missing: {control_map}")
        with tempfile.TemporaryDirectory() as temp_dir:
            report = generate_reopen_safe_fixture("text", temp_dir, corpus_root=CORPUS_ROOT)
            self.assertEqual(report["reopen_safe_control_type"], "text")
            self.assertEqual(report["reopen_safe_source_case_id"], "page0_text_set_str")
            self.assertTrue(Path(report["output_hmi"]).exists())
            self.assertTrue(report["open_lowlevel_ok"])
            self.assertTrue(report["compile_lowlevel_ok"])
            self.assertTrue(report["official_gui_reopen_ok"])

    def test_cli_reopen_safe_fixture_returns_verified_report(self) -> None:
        control_map = CORPUS_ROOT / "reopen_safe_control_map.json"
        if not control_map.exists():
            self.skipTest(f"local reopen-safe control map missing: {control_map}")
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "usarthmi",
                    "--json",
                    "hmi",
                    "reopen-safe-fixture",
                    "text",
                    "--out-dir",
                    temp_dir,
                    "--corpus-root",
                    str(CORPUS_ROOT),
                ],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["reopen_safe_control_type"], "text")
            self.assertTrue(payload["open_lowlevel_ok"])
            self.assertTrue(payload["compile_lowlevel_ok"])
            self.assertTrue(payload["official_gui_reopen_ok"])

    def test_delete_b1_applies_calibrated_shadow_sync(self) -> None:
        if not PAGE0_BASIC_DELETE_DONOR.exists():
            self.skipTest(f"repo-local donor copy missing: {PAGE0_BASIC_DELETE_DONOR}")
        with tempfile.TemporaryDirectory() as temp_dir:
            report = patch_hmi_donor(
                donor_hmi=PAGE0_BASIC_DELETE_DONOR,
                out_dir=Path(temp_dir),
                delete_objects=["b1"],
                probe_lowlevel=False,
                probe_reopen=False,
                shadow_sync_mode=SHADOW_SYNC_MODE_CASE83_DELETE_B1_GUI,
            )
            self.assertTrue(report["experimental_shadow_sync_applied"])
            shadow_report = json.loads(Path(report["shadow_sync_report_json"]).read_text(encoding="utf-8"))
            self.assertTrue(shadow_report["applied"])
            self.assertEqual(shadow_report["authoritative_shadow_index"], 11)
            self.assertEqual(
                shadow_report["reason"],
                "applied_case83_delete_b1_native_named_page_tombstone",
            )
            self.assertTrue(shadow_report["native_named_0pa_after"]["page_safe"]["safe_ok"])

            output_hmi = Path(report["output_hmi"])
            inspection = inspect_hmi(output_hmi)
            raw = output_hmi.read_bytes()
            pa_rows = {}
            for entry in inspection.entries:
                base = 4 + entry.index * 28
                name_bytes = raw[base : base + 16]
                if entry.name != "0.pa" and name_bytes[1:4] != b".pa":
                    continue
                page = parse_page_data(raw[entry.data_offset : entry.data_offset + entry.length])
                pa_rows[entry.index] = {
                    "name": entry.name,
                    "length": entry.length,
                    "objects": [(block.objname, block.type_code) for block in page.blocks if block.objname],
                }

            self.assertEqual(pa_rows[11]["length"], 7476)
            self.assertEqual(pa_rows[14]["length"], 6509)
            self.assertEqual(pa_rows[11]["objects"], pa_rows[14]["objects"])
            self.assertNotIn(("b1", "b"), pa_rows[11]["objects"])

            native_table = parse_native_cfs_table(raw, NATIVE_CFS_PRIMARY_TABLE_OFFSET)
            native_page = find_native_cfs_record(native_table, "0.pa")
            self.assertIsNotNone(native_page)
            native_status = inspect_page_safe_status(
                raw[native_page.data_offset : native_page.data_offset + native_page.length]
            )
            self.assertTrue(native_status.safe_ok)
            self.assertEqual(native_status.datainformation_qyt, 7)

    def test_shadow_sync_auto_applies_by_default_for_case83_delete(self) -> None:
        if not PAGE0_BASIC_DELETE_DONOR.exists():
            self.skipTest(f"repo-local donor copy missing: {PAGE0_BASIC_DELETE_DONOR}")
        with tempfile.TemporaryDirectory() as temp_dir:
            report = patch_hmi_donor(
                donor_hmi=PAGE0_BASIC_DELETE_DONOR,
                out_dir=Path(temp_dir),
                delete_objects=["b1"],
                probe_lowlevel=False,
                probe_reopen=False,
            )
            self.assertTrue(report["experimental_shadow_sync_applied"])
            self.assertEqual(
                report["experimental_shadow_sync_reason"],
                "applied_case83_delete_b1_native_named_page_tombstone",
            )

    def test_shadow_sync_can_be_forced_off(self) -> None:
        if not PAGE0_BASIC_DELETE_DONOR.exists():
            self.skipTest(f"repo-local donor copy missing: {PAGE0_BASIC_DELETE_DONOR}")
        with tempfile.TemporaryDirectory() as temp_dir:
            report = patch_hmi_donor(
                donor_hmi=PAGE0_BASIC_DELETE_DONOR,
                out_dir=Path(temp_dir),
                delete_objects=["b1"],
                probe_lowlevel=False,
                probe_reopen=False,
                shadow_sync_mode=SHADOW_SYNC_MODE_OFF,
            )
            self.assertFalse(report["experimental_shadow_sync_applied"])
            self.assertEqual(report["experimental_shadow_sync_reason"], "shadow_sync_mode_off")

    def test_move_does_not_apply_calibrated_shadow_sync_when_mode_enabled(self) -> None:
        if not PAGE0_BASIC_DELETE_DONOR.exists():
            self.skipTest(f"repo-local donor copy missing: {PAGE0_BASIC_DELETE_DONOR}")
        with tempfile.TemporaryDirectory() as temp_dir:
            report = patch_hmi_donor(
                donor_hmi=PAGE0_BASIC_DELETE_DONOR,
                out_dir=Path(temp_dir),
                move_specs=["b1:10:20:30:40"],
                probe_lowlevel=False,
                probe_reopen=False,
                shadow_sync_mode=SHADOW_SYNC_MODE_CASE83_DELETE_B1_GUI,
            )
            self.assertFalse(report["experimental_shadow_sync_applied"])
            self.assertEqual(report["experimental_shadow_sync_reason"], "operation_not_calibrated")

    def test_move_does_not_apply_auto_shadow_sync_by_default(self) -> None:
        if not PAGE0_BASIC_DELETE_DONOR.exists():
            self.skipTest(f"repo-local donor copy missing: {PAGE0_BASIC_DELETE_DONOR}")
        with tempfile.TemporaryDirectory() as temp_dir:
            report = patch_hmi_donor(
                donor_hmi=PAGE0_BASIC_DELETE_DONOR,
                out_dir=Path(temp_dir),
                move_specs=["b1:10:20:30:40"],
                probe_lowlevel=False,
                probe_reopen=False,
            )
            self.assertFalse(report["experimental_shadow_sync_applied"])
            self.assertEqual(report["experimental_shadow_sync_reason"], "auto_skipped_non_structural_operation")

    def test_delete_b1_mode_can_pass_lowlevel_and_gui_reopen(self) -> None:
        if not PAGE0_BASIC_DELETE_DONOR.exists():
            self.skipTest(f"repo-local donor copy missing: {PAGE0_BASIC_DELETE_DONOR}")
        with tempfile.TemporaryDirectory() as temp_dir:
            report = patch_hmi_donor(
                donor_hmi=PAGE0_BASIC_DELETE_DONOR,
                out_dir=Path(temp_dir),
                delete_objects=["b1"],
                probe_lowlevel=True,
                probe_reopen=True,
                shadow_sync_mode=SHADOW_SYNC_MODE_CASE83_DELETE_B1_GUI,
            )
            self.assertTrue(report["open_lowlevel_ok"])
            self.assertTrue(report["compile_lowlevel_ok"])
            self.assertTrue(report["official_gui_reopen_ok"])

    def test_delete_select0_mode_can_pass_lowlevel_and_gui_reopen(self) -> None:
        if not PAGE0_BASIC_DELETE_DONOR.exists():
            self.skipTest(f"repo-local donor copy missing: {PAGE0_BASIC_DELETE_DONOR}")
        with tempfile.TemporaryDirectory() as temp_dir:
            report = patch_hmi_donor(
                donor_hmi=PAGE0_BASIC_DELETE_DONOR,
                out_dir=Path(temp_dir),
                delete_objects=["select0"],
                probe_lowlevel=True,
                probe_reopen=True,
                shadow_sync_mode=SHADOW_SYNC_MODE_CASE83_DELETE_B1_GUI,
            )
            self.assertTrue(report["experimental_shadow_sync_applied"])
            self.assertTrue(report["open_lowlevel_ok"])
            self.assertTrue(report["compile_lowlevel_ok"])
            self.assertTrue(report["official_gui_reopen_ok"])

    def test_filebrowser_add_native_page_promote_can_pass_lowlevel_and_gui_reopen(self) -> None:
        self._assert_promote_spec_passes(FILEBROWSER_ADD_SPEC)

    def test_basic_add_native_page_promote_can_pass_lowlevel_and_gui_reopen(self) -> None:
        self._assert_promote_spec_passes(BASIC_ADD_SPEC)

    def test_basic_add_auto_mode_can_pass_lowlevel_and_gui_reopen(self) -> None:
        self._assert_promote_spec_passes(BASIC_ADD_SPEC, force_mode=None)

    def test_textselect_add_native_page_promote_can_pass_lowlevel_and_gui_reopen(self) -> None:
        self._assert_promote_spec_passes(TEXTSELECT_ADD_SPEC)

    def test_datarecord_add_native_page_promote_can_pass_lowlevel_and_gui_reopen(self) -> None:
        self._assert_promote_spec_passes(DATARECORD_ADD_SPEC)

    def test_filestream_add_native_page_promote_can_pass_lowlevel_and_gui_reopen(self) -> None:
        self._assert_promote_spec_passes(FILESTREAM_ADD_SPEC)
