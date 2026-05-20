from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/recovery_priority_2026-05-21.json")


class RecoveryPriorityArtifactTests(unittest.TestCase):
    def test_artifact_prioritizes_seed_side_runner_over_more_byte_patching(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "prepared")
        self.assertEqual(payload["top_priority_after_panel_recovery"]["id"], "desktop_sd_recovery_handoff")
        self.assertIn("00_先双击_校验恢复包.cmd", payload["top_priority_after_panel_recovery"]["command"])
        self.assertEqual(payload["secondary_priority_after_panel_recovery"]["id"], "recover_then_seed_side_orchestrator")
        self.assertIn("01_SD恢复完成后双击_继续验证.cmd", payload["secondary_priority_after_panel_recovery"]["command"])
        self.assertEqual(payload["external_recovery_package"]["id"], "sd_recovery_case31_backup")
        self.assertTrue(payload["external_recovery_package"]["tft"].endswith("recovery_sd_card/lcd_test.tft"))


if __name__ == "__main__":
    unittest.main()
