from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_authoring_gap_2026-05-20.json")


class Page1FilebrowserAuthoringGapReportArtifactTests(unittest.TestCase):
    def test_artifact_shows_authoring_gap_not_runtime_negative(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertEqual(payload["status"], "page1-filebrowser-authoring-gap")
        self.assertGreater(payload["summary"]["scan_hmi_count"], 0)
        self.assertEqual(payload["summary"]["scan_saved_page1_filebrowser_count"], 0)
        self.assertFalse(payload["summary"]["clone_saved_page1_filebrowser"])
        self.assertFalse(payload["conclusions"]["page1_filebrowser_saved_by_official_or_clone_hmi"])
        self.assertFalse(payload["conclusions"]["page1_filebrowser_runtime_negative_proof_exists"])
        self.assertIn("authoring/save gap", payload["conclusions"]["narrowing"])
        self.assertEqual(payload["official_minimal_case"]["confirmation_status"], "failed")
        self.assertEqual(payload["official_minimal_case"]["page1_blocks"], [["page1", "y"], ["v0", "\u0003"]])

        clone_blocks = payload["clone_case"]["page1_blocks"]
        self.assertEqual(clone_blocks, [["page1", "y"]])


if __name__ == "__main__":
    unittest.main()
