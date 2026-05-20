from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_vs_filestream_local_multipt_diff_2026-05-21.json")


class Page1FilebrowserVsFilestreamLocalMultiPageDiffArtifactTests(unittest.TestCase):
    def test_artifact_captures_actual_tail_deltas(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        fb = payload["cases"]["filebrowser"]
        fs = payload["cases"]["filestream"]

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertEqual(payload["status"], "actual-local-multipt-compared")
        self.assertEqual(fb["actual_prefix_row8"], fs["actual_prefix_row8"])
        self.assertEqual(fb["actual_page_header_words"][0], fs["actual_page_header_words"][0])
        self.assertEqual(fb["actual_page_header_words"][3], fs["actual_page_header_words"][3])
        self.assertNotEqual(fb["actual_page_header_words"][1], fs["actual_page_header_words"][1])
        self.assertNotEqual(fb["actual_page_header_words"][2], fs["actual_page_header_words"][2])
        self.assertNotEqual(fb["actual_second_record_event_offset"], fs["actual_second_record_event_offset"])


if __name__ == "__main__":
    unittest.main()
