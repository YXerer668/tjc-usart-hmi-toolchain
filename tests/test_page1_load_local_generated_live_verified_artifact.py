from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_load_local_generated_live_verified_2026-05-20.json")


class Page1LoadLocalGeneratedLiveVerifiedArtifactTests(unittest.TestCase):
    def test_artifact_captures_local_page1_load_positive(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertEqual(payload["status"], "live-positive")
        self.assertTrue(payload["build_summary"]["checksum_valid"])
        self.assertEqual(payload["live_sequence"][1]["hex"], "23 02 50 4c")
        self.assertEqual(payload["live_sequence"][2]["value"], 0)
        self.assertEqual(payload["live_sequence"][3]["value"], "LOAD")
        self.assertTrue(payload["conclusions"]["local_generator_reproduces_minimal_page1_load_dispatch"])


if __name__ == "__main__":
    unittest.main()
