from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_clone_vs_local_report_2026-05-21.json")


class Page1FilebrowserCloneVsLocalReportArtifactTests(unittest.TestCase):
    def test_artifact_separates_authoring_gap_from_local_enumeration_gap(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "clone-vs-local-compared")
        self.assertEqual(payload["official_clone_case"]["saved_page1_blocks"], [["page1", "y"]])
        self.assertEqual(payload["official_clone_case"]["readback_kinds"]["fbrowser0.dir"], "invalid_reference")
        self.assertEqual(payload["local_current_code_case"]["after_page0_readback"]["dir_kind"], "string")
        self.assertEqual(payload["local_current_code_case"]["after_page0_readback"]["filter_kind"], "string")
        self.assertEqual(payload["local_current_code_case"]["after_page0_readback"]["qty_kind"], "number")
        self.assertEqual(payload["local_current_code_case"]["after_page0_readback"]["qty_value"], 0)
        self.assertTrue(payload["conclusions"]["official_clone_is_authoring_gap_not_runtime_a_type_enumeration_gap"])
        self.assertTrue(payload["conclusions"]["local_current_code_recovers_object_survival_and_field_binding"])
        self.assertTrue(payload["conclusions"]["remaining_local_gap_is_enumeration_display_not_object_survival"])


if __name__ == "__main__":
    unittest.main()
