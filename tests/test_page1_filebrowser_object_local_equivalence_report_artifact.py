from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_object_local_equivalence_2026-05-21.json")


class Page1FilebrowserObjectLocalEquivalenceReportArtifactTests(unittest.TestCase):
    def test_artifact_confirms_object_local_wiring_survives_multipt(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        comparison = payload["comparison"]
        conclusions = payload["conclusions"]

        self.assertEqual(payload["status"], "object-local-equivalent")
        self.assertEqual(comparison["user_record_equal_count"], 60)
        self.assertEqual(comparison["mirror_abs_value_equal_count"], 60)
        self.assertEqual(comparison["mirror_record_event_offset_delta"], 6)
        self.assertTrue(conclusions["all_60_actual_user_records_identical"])
        self.assertTrue(conclusions["all_60_actual_mirror_abs_slot_values_identical"])
        self.assertTrue(conclusions["only_object_local_delta_is_page_level_event_offset_shift"])
        self.assertTrue(conclusions["remaining_gap_is_outside_object_local_a_type_wiring"])


if __name__ == "__main__":
    unittest.main()
