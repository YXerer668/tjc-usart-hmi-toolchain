from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_pointer_closure_report_2026-05-21.json")


class Page1FilebrowserPointerClosureReportArtifactTests(unittest.TestCase):
    def test_artifact_shows_page1_filebrowser_pointer_closure_survives(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        single = payload["cases"]["single_page_filebrowser_working"]
        page1_fb = payload["cases"]["page1_filebrowser_local_multipt"]
        compare = payload["comparisons"]["single_page_filebrowser_vs_page1_filebrowser"]
        conclusions = payload["conclusions"]

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertEqual(payload["status"], "page-pointer-closure-compared")
        self.assertTrue(page1_fb["target_page_row"]["hash_offset_matches_target_hash_block"])
        self.assertTrue(page1_fb["target_page_row"]["user_offset_points_to_nonzero_user_record"])
        self.assertTrue(page1_fb["target_object_event_offset_matches_last_event_start"])
        self.assertEqual(single["target_page_row"]["primary_pre_string_len"], page1_fb["target_page_row"]["primary_pre_string_len"])
        self.assertEqual(compare["hash_offset_delta"], 6)
        self.assertEqual(compare["target_event_offset_deltas"], [6, 6, 6, 6, 6])
        self.assertTrue(conclusions["single_page_filebrowser_and_page1_filebrowser_share_same_page_level_shape_except_expected_shift"])
        self.assertTrue(conclusions["all_target_rows_keep_basic_pointer_closure"])


if __name__ == "__main__":
    unittest.main()
