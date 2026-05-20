from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/advanced_direct_tft_demo/live_smoke_migration_audit_2026-05-20.json")


class LiveSmokeMigrationAuditArtifactTests(unittest.TestCase):
    def test_artifact_is_self_consistent(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        scenes = payload["scenes"]
        summary = payload["summary"]

        self.assertEqual(summary["scene_count"], len(scenes))
        self.assertEqual(summary["scene_with_live_smoke"], sum(1 for item in scenes if item["has_live_smoke"]))
        self.assertEqual(summary["scene_without_live_smoke"], sum(1 for item in scenes if not item["has_live_smoke"]))
        self.assertEqual(
            summary["scene_with_conventional_legacy_expect"],
            sum(1 for item in scenes if item["conventional_legacy_expect"] is not None),
        )
        self.assertEqual(
            summary["scene_with_matching_conventional_legacy"],
            sum(1 for item in scenes if item["conventional_legacy_match"] is True),
        )
        self.assertEqual(
            summary["scene_with_mismatching_conventional_legacy"],
            sum(1 for item in scenes if item["conventional_legacy_match"] is False),
        )
        self.assertEqual(summary["orphan_legacy_expect_count"], len(payload["orphan_legacy_expect_files"]))

    def test_known_migrated_scenes_are_recorded(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        scenes = {item["scene"]: item for item in payload["scenes"]}

        self.assertEqual(payload["summary"]["scene_with_mismatching_conventional_legacy"], 0)
        self.assertEqual(payload["summary"]["orphan_legacy_expect_count"], 0)
        self.assertTrue(scenes["examples/advanced_direct_tft_demo/file_stream_set_val_button_event_scene.json"]["has_live_smoke"])
        self.assertTrue(scenes["examples/advanced_direct_tft_demo/file_browser_sliding_text_button_event_scene.json"]["has_live_smoke"])
        self.assertTrue(scenes["examples/advanced_direct_tft_demo/data_record_text_select_button_case83_event_scene.json"]["has_live_smoke"])
        self.assertTrue(scenes["examples/advanced_direct_tft_demo/data_record_sliding_text_case85_oracle_aligned_scene.json"]["has_live_smoke"])
        self.assertTrue(scenes["examples/advanced_direct_tft_demo/data_record_text_select_button_case83_oracle_aligned_scene.json"]["has_live_smoke"])


if __name__ == "__main__":
    unittest.main()
