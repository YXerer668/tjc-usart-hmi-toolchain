from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_narrowing_experiments_2026-05-20.json")


class Page1FilebrowserNarrowingExperimentsArtifactTests(unittest.TestCase):
    def test_artifact_rules_out_name_and_geometry_as_primary_cause(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertEqual(payload["status"], "narrowed")
        self.assertEqual(payload["experiments"]["v4_refresh"]["qty"], 0)
        self.assertEqual(payload["experiments"]["unique_names"]["qty"], 0)
        self.assertEqual(payload["experiments"]["exact_page0_cluster"]["qty"], 0)
        self.assertEqual(payload["experiments"]["load_wrapper"]["load_marker_observed"], "23 02 46 42")
        self.assertEqual(payload["experiments"]["load_wrapper"]["qty"], 0)
        self.assertEqual(payload["experiments"]["page0_qty_semantics"]["qty"], 14)
        self.assertEqual(payload["experiments"]["fbrowser_runtime_index_patch"]["qty"], 0)
        self.assertTrue(payload["experiments"]["record_diff"]["user_slot_body_identical"])
        self.assertTrue(payload["experiments"]["record_diff"]["mirror_value_tail_identical"])
        self.assertEqual(payload["experiments"]["mirror_event_offset_patch"]["qty"], 0)
        self.assertFalse(payload["conclusions"]["enumeration_display_recovered"])
        self.assertFalse(payload["conclusions"]["cross_page_companion_name_collision_primary_cause"])
        self.assertFalse(payload["conclusions"]["page0_vs_page1_filebrowser_cluster_geometry_primary_cause"])
        self.assertFalse(payload["conclusions"]["narrow_fixed_load_wrapper_sufficient_for_filebrowser_enumeration"])
        self.assertTrue(payload["conclusions"]["qty_semantics_confirmed"])
        self.assertFalse(payload["conclusions"]["fbrowser_runtime_index_patch_sufficient"])
        self.assertFalse(payload["conclusions"]["mirror_event_offset_patch_sufficient"])


if __name__ == "__main__":
    unittest.main()
