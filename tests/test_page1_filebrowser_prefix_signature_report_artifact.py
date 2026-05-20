from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_prefix_signature_2026-05-21.json")


class Page1FilebrowserPrefixSignatureReportArtifactTests(unittest.TestCase):
    def test_artifact_shows_a_type_prefix_signature_mostly_survives_multipt(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        counts = payload["diff_counts"]
        overlap = payload["overlap_ratio"]
        conclusions = payload["conclusions"]

        self.assertEqual(payload["status"], "prefix-signature-compared")
        self.assertGreaterEqual(counts["shifted_overlap"], 400)
        self.assertGreater(overlap["single_shifted_covered_by_multi"], 0.9)
        self.assertGreater(overlap["multi_covered_by_single_shifted"], 0.9)
        self.assertTrue(conclusions["a_type_prefix_signature_is_mostly_preserved_in_multipt"])
        self.assertTrue(conclusions["remaining_prefix_signature_mismatch_is_concentrated_in_small_suffix_region"])
        self.assertTrue(conclusions["prefix_head_is_not_obviously_wholesale_missing_for_a_type"])
        self.assertTrue(conclusions["small_multipt_suffix_region_remains_a_page_global_candidate"])


if __name__ == "__main__":
    unittest.main()
