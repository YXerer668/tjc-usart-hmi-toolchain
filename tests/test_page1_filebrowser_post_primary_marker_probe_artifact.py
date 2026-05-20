from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("reverse_usarthmi/page1_filebrowser_post_primary_marker_probe_20260521/patch_report.json")


class Page1FilebrowserPostPrimaryMarkerProbeArtifactTests(unittest.TestCase):
    def test_patch_report_captures_inserted_post_primary_marker(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["inserted_hex"], "04 00 00 00 09 1f 04 34")
        self.assertEqual(payload["old_post_primary_head_hex"], "03 00 00 00 09 30 08 00 00 00 00")
        self.assertEqual(
            payload["new_post_primary_head_hex"],
            "04 00 00 00 09 1f 04 34 03 00 00 00 09 30 08 00 00 00 00",
        )
        self.assertEqual(payload["old_page0_hash_offset_hex"], "0x74e")
        self.assertEqual(payload["new_page0_hash_offset_hex"], "0x756")
        self.assertEqual(payload["new_page1_hash_offset_hex"], "0x227")
        self.assertEqual(payload["page0_event_offsets_hex"], ["0x19f", "0x1c7", "0x1e1", "0x1fb"])


if __name__ == "__main__":
    unittest.main()
