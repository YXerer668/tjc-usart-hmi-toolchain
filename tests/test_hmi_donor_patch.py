from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import subprocess
import sys

from usarthmi.hmi_donor_patch import (
    _parse_graft_spec,
    _parse_field_spec,
    _parse_move_spec,
    _parse_text_spec,
    _refresh_end_fields,
    normalize_patch_spec,
    patch_hmi_donor,
)
from usarthmi.hmi_inspect import inspect_hmi
from usarthmi.page_format import BlockField, PageBlock


CASE_83_HMI = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_83_datarecord_textselect_button_official_positive_oracle\lcd_test.HMI")


class HMIDonorPatchTests(unittest.TestCase):
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
