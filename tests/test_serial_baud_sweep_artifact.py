from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/serial_baud_sweep_2026-05-21.json")


class SerialBaudSweepArtifactTests(unittest.TestCase):
    def test_artifact_confirms_all_scanned_bauds_are_silent(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "swept")
        self.assertGreaterEqual(len(payload["rows"]), 10)
        self.assertTrue(all(row["connect_kind"] == "none" for row in payload["rows"]))
        self.assertTrue(payload["conclusions"]["all_common_and_high_bauds_silent"])
        self.assertTrue(payload["conclusions"]["not_explained_by_simple_command_baud_drift"])


if __name__ == "__main__":
    unittest.main()
