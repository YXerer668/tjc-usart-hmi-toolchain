from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_load_dispatch_parity_report_2026-05-20.json")


class Page1LoadDispatchParityReportArtifactTests(unittest.TestCase):
    def test_artifact_captures_wrapper_vs_table_split(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertEqual(payload["mode"], "page1_load_dispatch_parity_report")
        self.assertTrue(payload["comparison"]["official_uses_inline_load_phase_wrapper"])
        self.assertTrue(payload["comparison"]["local_uses_normal_page_event_table"])
        self.assertTrue(payload["comparison"]["official_callback_slots_empty"])
        self.assertTrue(payload["comparison"]["local_callback_slots_empty"])
        self.assertTrue(payload["comparison"]["official_wrapper_starts_after_hash"])
        self.assertTrue(payload["comparison"]["local_page_event_table_starts_before_hash"])
        self.assertIn("wrapper", payload["comparison"]["likely_missing_layer"])

        official = payload["official_oracle"]
        self.assertEqual(official["page1_hash_offset_hex"], "0x191")
        self.assertEqual(official["page_load_phase_match"]["offset_hex"], "0x255")
        self.assertEqual(official["page_load_phase_match"]["first_executable_absolute_hex"], "0x255")
        self.assertEqual(official["page_load_phase_match"]["prefix_items"][0]["args"], "AA 52 10 01")

        local = payload["local_generated_probe"]
        self.assertEqual(local["page1_hash_offset_hex"], "0x2EB")
        self.assertEqual(local["event_table_matches"], [{"value": 331, "hex": "0x14B"}])
        self.assertEqual(local["mirror_event_offset_field"], {"value": 331, "hex": "0x14B"})


if __name__ == "__main__":
    unittest.main()
