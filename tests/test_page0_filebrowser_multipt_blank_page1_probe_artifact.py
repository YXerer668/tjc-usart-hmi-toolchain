from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page0_filebrowser_multipt_blank_page1_probe_2026-05-21.json")


class Page0FilebrowserMultiPageBlankPage1ProbeArtifactTests(unittest.TestCase):
    def test_artifact_prepares_runtime_limitation_falsification_probe(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "probe-prepared")
        self.assertEqual(payload["page0_blocks"][-1], ["fbrowser0", "A"])
        self.assertEqual(payload["page1_blocks"], [["page1", "y"]])
        self.assertEqual(payload["live_hypothesis"]["runtime_mapping"]["page 1"], "seed-side page0 carrying fbrowser0")
        self.assertIn("get fbrowser0.qty", payload["live_hypothesis"]["commands"])


if __name__ == "__main__":
    unittest.main()
