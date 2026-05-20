from __future__ import annotations

import json
import unittest
from pathlib import Path


FB = Path("examples/lifecycle_runtime_smoke/page0_filebrowser_multipt_blank_page1_smoke_2026-05-21.json")
FS = Path("examples/lifecycle_runtime_smoke/page0_filestream_multipt_blank_page1_smoke_2026-05-21.json")


class SeedSideMultiPageRuntimeLimitSmokeConfigTests(unittest.TestCase):
    def test_filebrowser_smoke_config_targets_runtime_page1(self) -> None:
        payload = json.loads(FB.read_text(encoding="utf-8"))
        self.assertEqual(payload["page_id"], 1)
        self.assertEqual(payload["select_page"], 1)
        self.assertEqual(payload["restore_page"], 0)
        self.assertEqual(payload["expectations"][0]["target"], "fbrowser0.dir")
        self.assertEqual(payload["expectations"][1]["target"], "fbrowser0.filter")
        self.assertEqual(payload["steps"][0]["command"], "get fbrowser0.qty")
        self.assertEqual(payload["steps"][0]["expected_min"], 1)

    def test_filestream_smoke_config_targets_runtime_page1(self) -> None:
        payload = json.loads(FS.read_text(encoding="utf-8"))
        self.assertEqual(payload["page_id"], 1)
        self.assertEqual(payload["select_page"], 1)
        self.assertEqual(payload["restore_page"], 0)
        self.assertEqual([item["target"] for item in payload["expectations"]], ["fs0.en", "fs0.val"])


if __name__ == "__main__":
    unittest.main()
