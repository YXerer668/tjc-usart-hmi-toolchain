from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/next_live_commands_2026-05-21.json")


class NextLiveCommandsArtifactTests(unittest.TestCase):
    def test_artifact_points_at_current_runner_and_recovery_tool(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        commands = [item["command"] for item in payload["recommended_order"]]

        self.assertEqual(payload["status"], "prepared")
        self.assertIn("run_seed_side_multipt_runtime_limit_smokes.py", commands[0])
        self.assertIn("--with-textselect-control", commands[0])
        self.assertIn("official_hmi_download_recovery.py", commands[2])


if __name__ == "__main__":
    unittest.main()
