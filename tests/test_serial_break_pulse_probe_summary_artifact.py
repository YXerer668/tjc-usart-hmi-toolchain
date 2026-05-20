from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/serial_break_pulse_probe_summary_2026-05-21.json")


class SerialBreakPulseProbeSummaryArtifactTests(unittest.TestCase):
    def test_summary_confirms_no_change_after_break_pulse(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "probe-summarized")
        self.assertEqual(payload["before_connect_kind"], "none")
        self.assertEqual(payload["after_connect_kind"], "none")
        self.assertEqual(payload["before_sendme_kind"], "none")
        self.assertEqual(payload["after_sendme_kind"], "none")
        self.assertTrue(payload["conclusions"]["serial_break_pulse_did_not_restore_serial_responsiveness"])
        self.assertTrue(payload["conclusions"]["serial_break_pulse_showed_no_observable_change"])


if __name__ == "__main__":
    unittest.main()
