from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_prefix_rowcount_live_probe_2026-05-21.json")


class Page1FilebrowserPrefixRowcountLiveProbeArtifactTests(unittest.TestCase):
    def test_artifact_captures_rowcount_patch_not_fixing_enumeration(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertEqual(payload["status"], "live-probed")
        self.assertEqual(payload["serial_readback"]["sendme"]["response"]["value"], 0)
        self.assertEqual(payload["serial_readback"]["dir"]["response"]["value"], "sd0/")
        self.assertEqual(payload["serial_readback"]["filter"]["response"]["value"], "*.*")
        self.assertEqual(payload["serial_readback"]["qty"]["response"]["value"], 0)
        self.assertEqual(payload["serial_readback"]["txt"]["response"]["value"], "")


if __name__ == "__main__":
    unittest.main()
