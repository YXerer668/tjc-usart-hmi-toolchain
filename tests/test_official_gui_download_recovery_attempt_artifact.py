from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/official_gui_download_recovery_attempt_2026-05-21.json")


class OfficialGuiDownloadRecoveryAttemptArtifactTests(unittest.TestCase):
    def test_artifact_captures_unsuccessful_automated_recovery(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertEqual(payload["status"], "attempted_not_recovered")
        self.assertEqual(payload["configured_port"], "COM36")
        self.assertEqual(payload["configured_download_baud"], "921600")
        self.assertTrue(payload["start_download_clicked"])
        self.assertEqual(payload["dialog_observation"]["start_button_text_stayed"], "联机并开始下载")
        self.assertEqual(payload["post_attempt_runtime"]["connect_kind"], "connect")
        self.assertEqual(payload["post_attempt_runtime"]["sendme_kind"], "none")


if __name__ == "__main__":
    unittest.main()
