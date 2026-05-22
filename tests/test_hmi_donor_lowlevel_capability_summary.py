from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("reverse_usarthmi/hmi_donor_lowlevel_probe_20260522/donor_patch_capability_summary.json")


class HMIDonorLowlevelCapabilitySummaryTests(unittest.TestCase):
    def test_summary_has_required_record_shape_and_known_case80_controls(self) -> None:
        if not ARTIFACT.exists():
            self.skipTest(f"local donor patch summary artifact missing: {ARTIFACT}")
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], 1)
        self.assertIn("schema_path", payload)
        records = payload["records"]
        self.assertTrue(records)

        required_fields = {
            "case_id",
            "donor_path",
            "generated_path",
            "operation",
            "control_type",
            "control_name",
            "page",
            "open_lowlevel_ok",
            "compile_lowlevel_ok",
            "expected_objects",
            "actual_objects",
            "notes",
            "confidence",
        }
        for record in records:
            with self.subTest(case_id=record["case_id"]):
                self.assertEqual(set(required_fields) - set(record), set())

        records_by_id = {record["case_id"]: record for record in records}

        self.assertTrue(records_by_id["donor_case80_exact_current"]["open_lowlevel_ok"])
        self.assertTrue(records_by_id["donor_case80_exact_current"]["compile_lowlevel_ok"])
        self.assertFalse(records_by_id["donor_case80_exact_historical_failed"]["open_lowlevel_ok"])
        self.assertFalse(records_by_id["donor_case80_exact_historical_failed"]["compile_lowlevel_ok"])
        self.assertTrue(records_by_id["case80_like_from_case83_delete_b1"]["open_lowlevel_ok"])
        self.assertTrue(records_by_id["case80_like_from_case83_delete_b1"]["compile_lowlevel_ok"])

    def test_generated_fixture_records_cover_required_fixture_names(self) -> None:
        if not ARTIFACT.exists():
            self.skipTest(f"local donor patch summary artifact missing: {ARTIFACT}")
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        records_by_id = {record["case_id"]: record for record in payload["records"]}
        required_fixtures = {
            "page0_basic_add_text_or_button",
            "page0_basic_delete",
            "page0_basic_move",
            "page0_basic_set_txt",
            "page0_filebrowser_add_or_preserve",
            "page0_textselect_add_or_preserve",
            "page0_datarecord_add_or_preserve",
            "page0_filestream_add_or_preserve",
            "case80_like_from_case83_delete_b1",
        }
        for case_id in required_fixtures:
            with self.subTest(case_id=case_id):
                record = records_by_id[case_id]
                self.assertEqual(record["kind"], "generated_fixture")
                self.assertTrue(record["open_lowlevel_ok"])
                self.assertTrue(record["compile_lowlevel_ok"])
                self.assertTrue(record["dynamic_snapshot_goal_a_ready"])
