from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/official_gui_download_recovery_attempt_2026-05-21.json")


class OfficialGuiDownloadRecoveryAttempt20260521ArtifactTests(unittest.TestCase):
    def test_artifact_captures_progress_without_runtime_recovery(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertEqual(payload["status"], "attempted_progress_but_not_recovered")
        self.assertEqual(payload["configured_port"], "COM36")
        self.assertTrue(payload["start_download_clicked"])
        self.assertEqual(payload["dialog_observation"]["start_button_text_transition"]["before"], "联机并开始下载")
        self.assertEqual(payload["dialog_observation"]["start_button_text_transition"]["after"], "停止")
        self.assertEqual(payload["post_attempt_runtime"]["connect_kind"], "connect")
        self.assertEqual(payload["post_attempt_runtime"]["sendme_kind"], "none")


if __name__ == "__main__":
    unittest.main()
