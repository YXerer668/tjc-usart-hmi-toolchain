from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_load_wrapper_trim_variant_live_negative_2026-05-20.json")


class Page1LoadWrapperTrimVariantLiveNegativeArtifactTests(unittest.TestCase):
    def test_artifact_captures_failed_wrapper_trim_hypothesis(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertEqual(payload["status"], "live-negative")
        self.assertEqual(payload["variant"]["wrapper_len"], 29)
        self.assertEqual(payload["variant"]["new_event_offset_hex"], "0x168")
        self.assertTrue(payload["variant"]["checksum_valid"])
        self.assertEqual(payload["live_sequence"][0]["value"], 0)
        self.assertEqual(payload["live_sequence"][2]["result_kind"], "none")
        self.assertFalse(payload["conclusions"]["local_wrapper_trim_recovers_page1_load_dispatch"])
        self.assertIn("deeper than just removing", payload["conclusions"]["narrowing"])


if __name__ == "__main__":
    unittest.main()
