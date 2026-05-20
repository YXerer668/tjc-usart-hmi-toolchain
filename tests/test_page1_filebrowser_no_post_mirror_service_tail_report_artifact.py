from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_no_post_mirror_service_tail_2026-05-21.json")


class Page1FilebrowserNoPostMirrorServiceTailReportArtifactTests(unittest.TestCase):
    def test_artifact_rules_out_meaningful_tail_after_mirror_records(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        conclusions = payload["conclusions"]

        self.assertEqual(payload["status"], "no-post-mirror-service-tail")
        self.assertTrue(conclusions["page1_to_page0_mirror_sets_are_adjacent_in_multipt_filebrowser"])
        self.assertTrue(conclusions["page1_to_page0_mirror_sets_are_adjacent_in_multipt_filestream"])
        self.assertTrue(conclusions["final_mirror_record_to_file_end_is_tiny_across_cases"])
        self.assertTrue(conclusions["no_room_for_meaningful_post_mirror_global_service_table"])


if __name__ == "__main__":
    unittest.main()
