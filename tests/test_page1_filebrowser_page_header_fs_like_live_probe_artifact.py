from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_page_header_fs_like_live_probe_2026-05-21.json")


class Page1FilebrowserPageHeaderFsLikeLiveProbeArtifactTests(unittest.TestCase):
    def test_artifact_captures_fs_like_page_header_patch_wedging_runtime(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertEqual(payload["status"], "live-probed")
        self.assertEqual(payload["before"]["sendme"]["response"]["value"], 0)
        self.assertEqual(payload["before"]["dir"]["response"]["value"], "sd0/")
        self.assertEqual(payload["before"]["qty"]["response"]["value"], 0)
        self.assertEqual(payload["sendme_after_page1"]["response"]["kind"], "none")
        self.assertEqual(payload["after"]["sendme"]["response"]["kind"], "none")
        self.assertEqual(payload["after"]["dir"]["response"]["kind"], "none")
        self.assertEqual(payload["after"]["qty"]["response"]["kind"], "none")


if __name__ == "__main__":
    unittest.main()
