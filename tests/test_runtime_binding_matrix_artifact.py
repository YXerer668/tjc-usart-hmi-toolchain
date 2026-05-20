from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/runtime_binding_matrix_2026-05-20.json")


class RuntimeBindingMatrixArtifactTests(unittest.TestCase):
    def test_artifact_has_expected_shape(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        rows = {item["id"]: item for item in payload["rows"]}

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertEqual(payload["summary"]["page0_advanced_positive_count"], 5)
        self.assertTrue(payload["summary"]["page1_runtime_page_mapping_confirmed"])
        self.assertEqual(payload["summary"]["page1_ordinary_binding_positive_count"], 1)
        self.assertEqual(payload["summary"]["page1_advanced_binding_positive_count"], 4)
        self.assertEqual(payload["summary"]["page1_advanced_binding_negative_count"], 1)
        self.assertFalse(payload["summary"]["page1_load_marker_recovered"])
        self.assertEqual(payload["summary"]["page1_remaining_controls_requiring_correct_page_recheck_count"], 0)
        self.assertEqual(
            payload["summary"]["highest_leverage_gap"],
            "page-load scheduler recovery and page1 file-browser-specific runtime binding",
        )
        self.assertEqual(rows["page0_load_local_positive"]["scheduler_path"], "post_primary_page_event")
        self.assertEqual(rows["page1_local_text_positive_mapping_corrected"]["runtime_readback"]["p1title.txt"], "LOAD")
        self.assertEqual(rows["page1_load_marker_unrecovered"]["runtime_signal"], "none")
        self.assertEqual(rows["page1_text_select_positive_mapping_corrected"]["runtime_readback"]["select0.val"], 0)
        self.assertEqual(
            rows["page1_sliding_text_positive_mapping_corrected"]["runtime_readback"]["slt0.txt"],
            "000\r\n111\r\n222\r\n333\r\n444\r\n666\r\n777\r\n777\r\n888\r\n999",
        )
        self.assertEqual(rows["page1_data_record_positive_mapping_corrected"]["runtime_readback"]["data0.maxval"], 1000)
        self.assertEqual(rows["page1_file_stream_positive_mapping_corrected"]["runtime_readback"]["fs0.en"], 0)
        self.assertEqual(rows["page1_file_browser_runtime_negative"]["runtime_signal"], "invalid_reference")


if __name__ == "__main__":
    unittest.main()
