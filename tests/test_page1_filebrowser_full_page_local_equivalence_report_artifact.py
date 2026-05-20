from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_full_page_local_equivalence_2026-05-21.json")


class Page1FilebrowserFullPageLocalEquivalenceReportArtifactTests(unittest.TestCase):
    def test_artifact_confirms_all_page_local_objects_survive_equivalently(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        comparison = payload["comparison"]
        conclusions = payload["conclusions"]

        self.assertEqual(payload["status"], "full-page-local-equivalent")
        self.assertEqual(comparison["full_page_user_record_equal_count"], 204)
        self.assertEqual(comparison["full_page_user_record_total"], 204)
        self.assertEqual(comparison["event_offset_deltas"], [6, 6, 6, 6, 6])
        self.assertEqual(len(set(comparison["record_offset_deltas"])), 1)
        self.assertTrue(conclusions["all_204_page_local_user_records_identical"])
        self.assertTrue(conclusions["all_five_mirror_records_shift_by_same_absolute_record_delta"])
        self.assertTrue(conclusions["all_five_mirror_event_offsets_shift_by_plus_6_only"])
        self.assertTrue(conclusions["page_local_companion_objects_are_not_the_primary_gap"])
        self.assertTrue(conclusions["remaining_gap_is_above_full_page_local_wiring"])


if __name__ == "__main__":
    unittest.main()
