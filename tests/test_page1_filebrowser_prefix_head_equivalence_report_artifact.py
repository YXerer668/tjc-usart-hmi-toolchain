from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_prefix_head_equivalence_2026-05-21.json")


class Page1FilebrowserPrefixHeadEquivalenceReportArtifactTests(unittest.TestCase):
    def test_artifact_confirms_prefix_head_and_event_table_reduce_to_generic_multipt_delta(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        conclusions = payload["conclusions"]

        self.assertEqual(payload["status"], "prefix-head-equivalent")
        self.assertTrue(conclusions["page_event_table_is_byte_identical"])
        self.assertTrue(conclusions["prefix_head_collapses_to_single_page_after_generic_multipt_normalization"])
        self.assertTrue(conclusions["only_generic_multipt_head_transforms_remain"])
        self.assertTrue(conclusions["no_filebrowser_specific_prefix_head_delta_survives_after_normalization"])


if __name__ == "__main__":
    unittest.main()
