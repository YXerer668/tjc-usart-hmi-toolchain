from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_page_header_diff_2026-05-20.json")


class Page1FilebrowserPageHeaderDiffArtifactTests(unittest.TestCase):
    def test_artifact_captures_actual_page_header_delta(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertEqual(payload["status"], "page-header-diffed")
        self.assertEqual(payload["single_page_working_header"]["count_field"], 0x00050000)
        self.assertEqual(payload["single_page_working_header"]["hash_offset"], 0x221)
        self.assertEqual(payload["single_page_working_header"]["user_offset"], 0x6FE)
        self.assertEqual(payload["single_page_working_header"]["primary_pre_string_len"], 0x1D8)
        self.assertEqual(payload["multi_page_page1_header"]["count_field"], 0x00040001)
        self.assertEqual(payload["multi_page_page1_header"]["hash_offset"], 0x73C)
        self.assertEqual(payload["multi_page_page1_header"]["user_offset"], 0x1BFF)
        self.assertEqual(payload["multi_page_page1_header"]["primary_pre_string_len"], 0x134)


if __name__ == "__main__":
    unittest.main()
