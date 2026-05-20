from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/current_target_full_completion_audit_2026-05-20.json")


class CurrentTargetCompletionAuditArtifactTests(unittest.TestCase):
    def test_artifact_has_expected_high_level_shape(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertTrue(payload["current_state"]["independent_scene_tft_live_workflow_exists"])
        self.assertTrue(payload["current_state"]["native_scene_smoke_live_proven"])
        self.assertEqual(payload["current_state"]["migration_convergence"]["scene_with_mismatching_conventional_legacy"], 0)
        self.assertEqual(payload["current_state"]["migration_convergence"]["orphan_legacy_expect_count"], 0)
        self.assertEqual(payload["highest_leverage_unsolved_subsystem"]["id"], "scheduler_lifecycle_general_equivalence")
        unfinished_ids = {item["id"] for item in payload["unfinished"]}
        self.assertIn("page1_advanced_runtime_binding", unfinished_ids)
        self.assertIn("full_hmi_replacement", unfinished_ids)
        self.assertIn("cross_model_compiler", unfinished_ids)

    def test_artifact_keeps_page1_advanced_controls_unfinished(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        unfinished = {item["id"]: item for item in payload["unfinished"]}
        page1 = unfinished["page1_advanced_runtime_binding"]
        scheduler = unfinished["scheduler_lifecycle_general_equivalence"]

        self.assertEqual(page1["status"], "unfinished")
        self.assertGreaterEqual(len(page1["evidence"]), 2)
        self.assertIn("page1 page-load scheduler recovery", page1["blocks"])
        self.assertIn("page1 file-browser-specific runtime binding recovery", page1["blocks"])
        self.assertIn("local reproduction of official page1 load dispatch", scheduler["blocks"])


if __name__ == "__main__":
    unittest.main()
