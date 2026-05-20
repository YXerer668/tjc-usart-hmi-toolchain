from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/index_2026-05-21.json")


class LifecycleRuntimeSmokeIndexArtifactTests(unittest.TestCase):
    def test_index_points_at_current_blocker_recovery_and_runner_entries(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "prepared")
        self.assertTrue(any(item.endswith("transport_silence_status_2026-05-21.json") for item in payload["current_blocker"]["artifacts"]))
        self.assertTrue(payload["external_recovery"]["desktop_bundle_dir"].endswith("TJC_SD_RECOVERY_CURRENT"))
        self.assertIn("recover_then_run_seed_side_runtime_limit.py", payload["post_recovery_runner"]["orchestrator"])
        self.assertIn("run_seed_side_multipt_runtime_limit_smokes.py", payload["post_recovery_runner"]["direct_runner"])
        self.assertTrue(any(item.endswith("current_target_full_completion_audit_2026-05-20.json") for item in payload["top_status_files"]))


if __name__ == "__main__":
    unittest.main()
