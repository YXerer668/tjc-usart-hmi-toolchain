from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/transport_silence_camera_status_2026-05-21.json")


class TransportSilenceCameraStatusArtifactTests(unittest.TestCase):
    def test_artifact_confirms_panel_is_not_visually_black(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "captured")
        self.assertTrue(payload["conclusions"]["screen_not_black"])
        self.assertTrue(payload["conclusions"]["panel_appears_powered_enough_for_camera_visibility"])
        self.assertGreater(payload["current_camera"]["mean_luma"], 20)


if __name__ == "__main__":
    unittest.main()
