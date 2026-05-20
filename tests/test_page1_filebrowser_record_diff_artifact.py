from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_record_diff_2026-05-20.json")


class Page1FilebrowserRecordDiffArtifactTests(unittest.TestCase):
    def test_artifact_confirms_body_identity_and_header_delta(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertEqual(payload["status"], "record-diffed")
        self.assertEqual(payload["fbrowser_user_slot_count"], 60)
        self.assertEqual(payload["fbrowser_user_slot_diffs"], [])
        self.assertEqual(payload["fbrowser_mirror_value_diffs"], [])
        self.assertEqual(payload["working_single_second_event_offset"], 0x207)
        self.assertEqual(payload["failing_multi_second_event_offset"], 0x1E5)
        self.assertEqual(payload["working_single_hits_hex"], ["0xae037f", "0xae1cee"])
        self.assertEqual(payload["failing_multi_hits_hex"], ["0xae035d", "0xae2c5f"])
        self.assertTrue(payload["conclusions"]["user_slot_body_identical"])
        self.assertTrue(payload["conclusions"]["mirror_value_tail_identical"])


if __name__ == "__main__":
    unittest.main()
