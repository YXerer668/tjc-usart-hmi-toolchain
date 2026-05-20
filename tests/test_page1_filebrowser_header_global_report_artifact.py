from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_header_global_2026-05-21.json")


class Page1FilebrowserHeaderGlobalReportArtifactTests(unittest.TestCase):
    def test_artifact_confirms_no_filebrowser_specific_header2_runtime_bit(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        conclusions = payload["conclusions"]

        self.assertEqual(payload["status"], "header-global-compared")
        self.assertTrue(conclusions["multi_page_fb_and_fs_share_same_non_offset_runtime_header_shape"])
        self.assertTrue(conclusions["remaining_multi_fb_vs_fs_header2_deltas_are_offsets_or_picture_count_only"])
        self.assertTrue(conclusions["header_globals_do_not_expose_a_filebrowser_specific_runtime_registration_bit"])


if __name__ == "__main__":
    unittest.main()
