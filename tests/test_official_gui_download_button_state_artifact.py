from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/official_gui_download_button_state_2026-05-21.json")


class OfficialGuiDownloadButtonStateArtifactTests(unittest.TestCase):
    def test_artifact_confirms_button_enabled_but_non_transitioning(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "captured")
        self.assertTrue(payload["button"]["exists"])
        self.assertTrue(payload["button"]["is_enabled"])
        self.assertTrue(payload["button"]["is_visible"])
        self.assertTrue(payload["conclusions"]["button_is_present_and_enabled"])
        self.assertTrue(payload["conclusions"]["failure_is_not_explained_by_a_disabled_button"])


if __name__ == "__main__":
    unittest.main()
