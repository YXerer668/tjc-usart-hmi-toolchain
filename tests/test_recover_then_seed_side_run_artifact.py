from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/recover_then_seed_side_run_2026-05-21.json")


class RecoverThenSeedSideRunArtifactTests(unittest.TestCase):
    def test_artifact_captures_still_silent_after_recovery(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "live-recovery-attempted")
        self.assertFalse(payload["before_responsive"])
        self.assertFalse(payload["after_recovery_responsive"])
        self.assertFalse(payload["runner_started"])
        self.assertEqual(payload["classification"], "still_silent_after_recovery")
        self.assertFalse(payload["key_findings"]["official_recovery_start_transitioned"])
        self.assertEqual(payload["key_findings"]["official_recovery_start_final_text"], "联机并开始下载")
        self.assertTrue(payload["conclusions"]["panel_still_silent_after_orchestrated_recovery"])
        self.assertTrue(payload["conclusions"]["seed_side_runtime_limiter_runner_blocked_by_transport"])


if __name__ == "__main__":
    unittest.main()
