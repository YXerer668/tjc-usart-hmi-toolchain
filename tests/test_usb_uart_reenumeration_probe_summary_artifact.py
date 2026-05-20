from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/usb_uart_reenumeration_probe_summary_2026-05-21.json")


class UsbUartReenumerationProbeSummaryArtifactTests(unittest.TestCase):
    def test_summary_confirms_reenumeration_had_no_effect(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "probe-summarized")
        self.assertTrue(payload["disable_ok"])
        self.assertTrue(payload["enable_ok"])
        self.assertEqual(payload["before_connect_kind"], "none")
        self.assertEqual(payload["after_connect_kind"], "none")
        self.assertTrue(payload["conclusions"]["usb_uart_bridge_reenumeration_succeeds_but_screen_stays_silent"])
        self.assertTrue(payload["conclusions"]["no_change_after_reenumeration"])


if __name__ == "__main__":
    unittest.main()
