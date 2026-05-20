from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/recovery_priority_2026-05-21.json")


class RecoveryPriorityArtifactTests(unittest.TestCase):
    def test_artifact_prioritizes_seed_side_runner_over_more_byte_patching(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "prepared")
        self.assertEqual(payload["top_priority_after_panel_recovery"]["id"], "seed_side_runtime_limitation_falsification")
        self.assertIn("run_seed_side_multipt_runtime_limit_smokes.py", payload["top_priority_after_panel_recovery"]["command"])
        self.assertIn("--with-textselect-control", payload["top_priority_after_panel_recovery"]["command"])
        self.assertEqual(payload["secondary_priority_after_panel_recovery"]["id"], "official_gui_recovery_retry")


if __name__ == "__main__":
    unittest.main()
