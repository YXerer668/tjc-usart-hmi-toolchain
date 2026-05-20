from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/official_gui_download_button_probe_summary_2026-05-21.json")


class OfficialGuiDownloadButtonProbeSummaryArtifactTests(unittest.TestCase):
    def test_summary_confirms_multiple_methods_failed_to_enter_running_state(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "probe-summarized")
        self.assertFalse(payload["start_transitioned"])
        self.assertEqual(payload["final_button_text"], "联机并开始下载")
        self.assertTrue(payload["bm_click_invoked"])
        self.assertTrue(payload["conclusions"]["all_local_button_interaction_methods_failed_to_enter_running_state"])
        self.assertTrue(payload["conclusions"]["not_explained_by_simple_missed_click"])


if __name__ == "__main__":
    unittest.main()
