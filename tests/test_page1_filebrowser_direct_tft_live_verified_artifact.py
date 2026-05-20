from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_direct_tft_live_verified_2026-05-20.json")


class Page1FilebrowserDirectTftLiveVerifiedArtifactTests(unittest.TestCase):
    def test_artifact_captures_page1_filebrowser_runtime_positive(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertEqual(payload["status"], "live-positive")
        self.assertTrue(payload["build_summary"]["checksum_valid"])
        self.assertEqual(payload["live_readback"]["sendme"]["value"], 0)
        self.assertEqual(payload["live_readback"]["fbrowser0.dir"]["value"], "sd0/")
        self.assertEqual(payload["live_readback"]["fbrowser0.filter"]["value"], "*.*")
        self.assertEqual(payload["live_readback"]["fbrowser0.txt"]["value"], "")
        self.assertTrue(payload["conclusions"]["page1_filebrowser_direct_tft_field_binding_recovered"])
        self.assertFalse(payload["conclusions"]["page1_filebrowser_direct_tft_full_enumeration_recovered"])
        self.assertFalse(payload["conclusions"]["page1_filebrowser_official_authoring_recovered"])


if __name__ == "__main__":
    unittest.main()
