from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_prefix_offset_live_probe_2026-05-21.json")


class Page1FilebrowserPrefixOffsetLiveProbeArtifactTests(unittest.TestCase):
    def test_artifact_captures_prefix_offset_patch_breaking_binding(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertEqual(payload["status"], "live-probed")
        self.assertEqual(payload["serial_readback"]["sendme"]["response"]["value"], 0)
        self.assertEqual(payload["serial_readback"]["dir"]["response"]["kind"], "invalid_reference")
        self.assertEqual(payload["serial_readback"]["filter"]["response"]["kind"], "invalid_reference")
        self.assertEqual(payload["serial_readback"]["qty"]["response"]["kind"], "invalid_reference")
        self.assertEqual(payload["serial_readback"]["txt"]["response"]["kind"], "invalid_reference")


if __name__ == "__main__":
    unittest.main()
