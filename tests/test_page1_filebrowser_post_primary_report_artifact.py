from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_post_primary_report_2026-05-21.json")


class Page1FilebrowserPostPrimaryReportArtifactTests(unittest.TestCase):
    def test_artifact_captures_single_page_marker_and_multi_page_gap(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        single = payload["cases"]["single_page_filebrowser_working"]
        single_fs = payload["cases"]["single_page_filestream_working"]
        multi_fb = payload["cases"]["page1_filebrowser_local_multipt"]
        multi_fs = payload["cases"]["page1_filestream_local_multipt"]
        conclusions = payload["conclusions"]

        self.assertEqual(payload["status"], "post-primary-compared")
        self.assertEqual(single["post_primary_items"][0]["command"], "post_primary_page_load")
        self.assertEqual(single["post_primary_items"][1]["command"], "loadend")
        self.assertEqual(single_fs["post_primary_items"][0]["command"], "post_primary_page_load")
        self.assertEqual(single_fs["post_primary_items"][1]["command"], "loadend")
        self.assertEqual(multi_fb["post_primary_head_items"][0]["command"], "loadend")
        self.assertEqual(multi_fs["post_primary_head_items"][0]["command"], "loadend")
        self.assertTrue(conclusions["single_page_filebrowser_has_post_primary_page_load_marker"])
        self.assertTrue(conclusions["single_page_filestream_has_post_primary_page_load_marker"])
        self.assertTrue(conclusions["current_local_page1_filebrowser_lacks_single_page_post_primary_marker"])
        self.assertTrue(conclusions["current_local_page1_filestream_also_lacks_single_page_post_primary_marker"])
        self.assertTrue(conclusions["post_primary_marker_absence_is_a_general_single_page_to_current_multipt_delta"])
        self.assertTrue(conclusions["post_primary_marker_absence_is_not_sufficient_to_explain_page1_filebrowser_failure"])


if __name__ == "__main__":
    unittest.main()
