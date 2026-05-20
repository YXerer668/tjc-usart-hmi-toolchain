from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_post_primary_probe_report_2026-05-21.json")


class Page1FilebrowserPostPrimaryProbeReportArtifactTests(unittest.TestCase):
    def test_artifact_marks_probe_ready_and_structurally_consistent(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        baseline = payload["baseline_local_multi_page"]
        probe = payload["post_primary_probe"]
        single = payload["single_page_reference"]
        conclusions = payload["conclusions"]

        self.assertEqual(payload["status"], "probe-ready-offline")
        self.assertEqual(probe["post_primary_head_hex"], single["post_primary_head_hex"])
        self.assertEqual(baseline["page1_hash_offset"], probe["page1_hash_offset"])
        self.assertEqual(probe["page0_hash_offset"] - baseline["page0_hash_offset"], 8)
        self.assertEqual(probe["page0_event_offsets"], [415, 455, 481, 507])
        self.assertTrue(conclusions["probe_inserts_single_page_post_primary_head"])
        self.assertTrue(conclusions["probe_page1_hash_offset_still_matches_target_hash_block"])
        self.assertTrue(conclusions["probe_page0_hash_offset_still_matches_target_hash_block"])
        self.assertTrue(conclusions["probe_page0_user_offset_still_matches_target_slot_span"])
        self.assertTrue(conclusions["probe_changes_only_expected_page0_follow_on_offsets"])
        self.assertTrue(conclusions["probe_is_ready_for_next_live_reburn"])


if __name__ == "__main__":
    unittest.main()
