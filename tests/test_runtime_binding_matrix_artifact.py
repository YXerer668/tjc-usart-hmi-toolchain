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
        self.assertEqual(payload["summary"]["page1_advanced_compile_positive_runtime_negative_count"], 5)
        self.assertEqual(payload["summary"]["page1_ordinary_lifecycle_negative_count"], 1)
        self.assertTrue(payload["summary"]["page_navigation_layer_proven"])
        self.assertFalse(payload["summary"]["page_local_advanced_registration_recovered"])
        self.assertEqual(payload["summary"]["highest_leverage_gap"], "general scheduler/lifecycle and page-local advanced runtime registration")
        self.assertEqual(rows["page0_load_local_positive"]["scheduler_path"], "post_primary_page_event")
        self.assertEqual(rows["page1_local_load_negative"]["runtime_signal"], "missing_load_marker_and_invalid_reference")
        self.assertEqual(rows["page1_text_select"]["runtime_signal"], "invalid_reference")
        self.assertEqual(rows["page1_file_browser"]["runtime_signal"], "invalid_reference")


if __name__ == "__main__":
    unittest.main()
