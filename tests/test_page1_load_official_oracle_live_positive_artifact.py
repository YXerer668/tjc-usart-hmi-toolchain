from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_load_official_oracle_live_positive_2026-05-20.json")


class Page1LoadOfficialOracleLivePositiveArtifactTests(unittest.TestCase):
    def test_artifact_captures_official_positive_vs_local_negative(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertTrue(payload["conclusions"]["runtime_supports_page1_load_dispatch"])
        self.assertEqual(payload["conclusions"]["correct_runtime_page_for_generated_or_official_page1"], 0)
        self.assertFalse(payload["conclusions"]["local_generator_reproduces_page1_load_dispatch"])

        official = payload["official_oracle"]["runtime_sequence"]
        self.assertEqual(official[0]["value"], 0)
        self.assertEqual(official[2]["value"], 1)
        self.assertEqual(official[3]["hex"], "aa 52 10 01")
        self.assertEqual(official[4]["value"], 0)

        local = payload["local_generated_probe"]
        self.assertEqual(local["runtime_page_0_readback"]["p1title.txt"], "LOAD")
        self.assertEqual(local["switch_back_to_runtime_page_0_marker"]["result_kind"], "none")


if __name__ == "__main__":
    unittest.main()
