from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/serial_port_inventory_2026-05-21.json")


class SerialPortInventoryArtifactTests(unittest.TestCase):
    def test_artifact_confirms_com36_is_only_plausible_usb_uart(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        conclusions = payload["conclusions"]

        self.assertEqual(payload["status"], "captured")
        self.assertEqual(conclusions["likely_usb_uart_count"], 1)
        self.assertEqual(conclusions["likely_usb_uart_devices"], ["COM36"])
        self.assertTrue(conclusions["only_plausible_live_uart_is_com36"])
        self.assertTrue(conclusions["not_explained_by_panel_having_moved_to_another_visible_usb_uart"])


if __name__ == "__main__":
    unittest.main()
