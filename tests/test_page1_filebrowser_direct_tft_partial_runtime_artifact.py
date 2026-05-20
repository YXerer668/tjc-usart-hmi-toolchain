from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_direct_tft_partial_runtime_2026-05-20.json")


class Page1FilebrowserDirectTftPartialRuntimeArtifactTests(unittest.TestCase):
    def test_artifact_captures_partial_runtime_shape(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertEqual(payload["status"], "partial-runtime")
        self.assertTrue(payload["build_summary"]["checksum_valid"])
        self.assertEqual(payload["live_readback"]["sendme"]["value"], 0)
        self.assertEqual(payload["live_readback"]["fbrowser0.dir"]["kind"], "invalid_reference")
        self.assertEqual(payload["live_readback"]["fbrowser0.filter"]["kind"], "invalid_reference")
        self.assertEqual(payload["live_readback"]["fbrowser0.txt"]["kind"], "string")
        self.assertEqual(payload["live_readback"]["fbrowser0.txt"]["value"], "")
        self.assertFalse(payload["conclusions"]["page1_filebrowser_runtime_fully_recovered"])
        self.assertFalse(payload["conclusions"]["page1_filebrowser_runtime_completely_absent"])


if __name__ == "__main__":
    unittest.main()
