from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_local_multipt_advanced_isolation_2026-05-21.json")


class Page1LocalMultiPageAdvancedIsolationArtifactTests(unittest.TestCase):
    def test_artifact_isolates_filebrowser_as_remaining_local_gap(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertEqual(payload["status"], "isolated")
        self.assertTrue(payload["probes"]["text_select"]["runtime_positive"])
        self.assertEqual(payload["probes"]["text_select"]["after_page0_readback"]["select0.val"], 0)
        self.assertTrue(payload["probes"]["file_stream"]["runtime_positive"])
        self.assertEqual(payload["probes"]["file_stream"]["after_page0_readback"]["fs0.en"], 0)
        self.assertFalse(payload["probes"]["file_browser"]["runtime_positive"])
        self.assertEqual(payload["probes"]["file_browser"]["representative_after_page0_readback"]["fbrowser0.qty"], 0)
        self.assertFalse(payload["conclusions"]["local_multi_page_builder_general_advanced_path_broken"])
        self.assertTrue(payload["conclusions"]["local_multi_page_builder_page1_file_browser_still_negative"])


if __name__ == "__main__":
    unittest.main()
