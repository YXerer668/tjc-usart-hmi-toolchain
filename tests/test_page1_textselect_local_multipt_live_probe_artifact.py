from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_textselect_local_multipt_live_probe_2026-05-21.json")


class Page1TextSelectLocalMultiPageLiveProbeArtifactTests(unittest.TestCase):
    def test_artifact_captures_local_builder_runtime_positive(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertEqual(payload["status"], "live-probed")
        self.assertEqual(payload["before"]["sendme"]["response"]["value"], 0)
        self.assertEqual(payload["sendme_after_page1"]["response"]["value"], 1)
        self.assertEqual(payload["after"]["sendme"]["response"]["value"], 0)
        self.assertEqual(payload["after"]["select0"]["response"]["kind"], "number")
        self.assertEqual(payload["after"]["select0"]["response"]["value"], 0)


if __name__ == "__main__":
    unittest.main()
