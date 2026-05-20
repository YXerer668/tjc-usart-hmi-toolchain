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
        self.assertFalse(payload["conclusions"]["enumeration_display_recovered"])
        self.assertFalse(payload["conclusions"]["cross_page_companion_name_collision_primary_cause"])
        self.assertFalse(payload["conclusions"]["page0_vs_page1_filebrowser_cluster_geometry_primary_cause"])


if __name__ == "__main__":
    unittest.main()
