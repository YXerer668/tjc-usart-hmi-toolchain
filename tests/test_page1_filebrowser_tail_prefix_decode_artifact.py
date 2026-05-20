from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_tail_prefix_decode_2026-05-21.json")


class Page1FilebrowserTailPrefixDecodeArtifactTests(unittest.TestCase):
    def test_artifact_captures_prefix_head_and_page1_section_deltas(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        cases = {item["label"]: item for item in payload["cases"]}

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertEqual(payload["status"], "tail-prefix-decoded")

        working = cases["working_load"]
        failing = cases["failing_filebrowser"]

        self.assertEqual(working["prefix_head_len"], 331)
        self.assertEqual(working["page1_hash_offset"], 357)
        self.assertEqual(working["page1_primary_pre_string_len"], 156)
        self.assertEqual(working["page1_slot_count"], 74)

        self.assertEqual(failing["prefix_head_len"], 407)
        self.assertEqual(failing["page1_hash_offset"], 511)
        self.assertEqual(failing["page1_primary_pre_string_len"], 472)
        self.assertEqual(failing["page1_slot_count"], 204)
        self.assertEqual(failing["page1_event_offsets"], [0, 407, 433, 459, 485])


if __name__ == "__main__":
    unittest.main()
