from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/seed_side_multipt_runtime_limit_probes_2026-05-21.json")


class SeedSideMultiPageRuntimeLimitProbesArtifactTests(unittest.TestCase):
    def test_artifact_prepares_filebrowser_and_filestream_seed_side_probes(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        fb = payload["probes"]["page0_filebrowser_blank_page1"]
        fs = payload["probes"]["page0_filestream_blank_page1"]

        self.assertEqual(payload["status"], "seed-side-probes-prepared")
        self.assertEqual(fb["page0_blocks"][-1], ["fbrowser0", "A"])
        self.assertEqual(fs["page0_blocks"][-1], ["fs0", "?"])
        self.assertEqual(fb["page1_blocks"], [["page1", "y"]])
        self.assertEqual(fs["page1_blocks"], [["page1", "y"]])
        self.assertEqual(payload["live_plan"]["expected_runtime_mapping"]["page 1"], "seed-side page0 carrying the advanced control")


if __name__ == "__main__":
    unittest.main()
