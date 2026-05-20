from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_primary_record_equivalence_2026-05-21.json")


class Page1FilebrowserPrimaryRecordEquivalenceReportArtifactTests(unittest.TestCase):
    def test_artifact_confirms_primary_records_are_identical(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        comparisons = payload["comparisons"]
        conclusions = payload["conclusions"]

        self.assertEqual(payload["status"], "primary-record-equivalent")
        self.assertEqual(len(comparisons), 5)
        self.assertTrue(all(item["equal"] for item in comparisons))
        self.assertTrue(all(item["start_delta"] == 0 for item in comparisons))
        self.assertTrue(conclusions["all_five_primary_records_identical"])
        self.assertTrue(conclusions["primary_record_lengths_match"])
        self.assertTrue(conclusions["primary_record_starts_do_not_shift"])
        self.assertTrue(conclusions["remaining_gap_is_outside_primary_object_records"])


if __name__ == "__main__":
    unittest.main()
