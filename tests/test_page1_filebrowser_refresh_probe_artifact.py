from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_refresh_probe_2026-05-20.json")


class Page1FilebrowserRefreshProbeArtifactTests(unittest.TestCase):
    def test_artifact_captures_white_surface_after_refresh_attempts(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertEqual(payload["status"], "refresh-probed")
        self.assertEqual(payload["steps"]["before"]["sendme"]["response"]["value"], 0)
        self.assertEqual(payload["steps"]["before"]["qty"]["response"]["value"], 0)
        self.assertEqual(payload["steps"]["after_ref"]["qty"]["response"]["value"], 0)
        self.assertEqual(payload["steps"]["after_page_cycle"]["qty"]["response"]["value"], 0)
        self.assertEqual(payload["steps"]["after_page_cycle"]["txt"]["response"]["value"], "")
        self.assertIn("camera_refresh_after_ref_", payload["camera"]["after_ref"]["path"])
        self.assertIn("camera_refresh_after_pagecycle_", payload["camera"]["after_page_cycle"]["path"])


if __name__ == "__main__":
    unittest.main()
