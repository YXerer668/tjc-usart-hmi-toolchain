from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/serial_modem_status_2026-05-21.json")


class SerialModemStatusArtifactTests(unittest.TestCase):
    def test_artifact_records_open_bridge_and_low_inbound_lines(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        status = payload["modem_lines"]

        self.assertEqual(payload["status"], "captured")
        self.assertTrue(status["opened"])
        self.assertFalse(status["cts"])
        self.assertFalse(status["dsr"])
        self.assertFalse(status["ri"])
        self.assertFalse(status["cd"])
        self.assertTrue(payload["conclusions"]["serial_bridge_opens"])
        self.assertTrue(payload["conclusions"]["all_inbound_modem_lines_low"])


if __name__ == "__main__":
    unittest.main()
