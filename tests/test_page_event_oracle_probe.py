from __future__ import annotations

from pathlib import Path
import unittest

from tools.page_event_oracle_probe import probe_hmi_tft


ROOT = Path(__file__).resolve().parents[1]
EVENT_DEMO_HMI = ROOT / "reverse_usarthmi" / "event_demo_live_probe_20260515" / "output.hmi"
EVENT_DEMO_TFT = ROOT / "reverse_usarthmi" / "event_demo_live_probe_20260515" / "output.tft"


@unittest.skipUnless(
    EVENT_DEMO_HMI.exists() and EVENT_DEMO_TFT.exists(),
    "local event_demo live probe build artifacts are not available",
)
class PageEventOracleProbeTests(unittest.TestCase):
    def test_event_demo_separates_page_load_from_button_callback(self) -> None:
        report = probe_hmi_tft(EVENT_DEMO_HMI, EVENT_DEMO_TFT)
        diagnosis = report["diagnosis"]

        self.assertTrue(diagnosis["page_load_non_empty"])
        self.assertTrue(diagnosis["page_event_table_found"])
        self.assertFalse(diagnosis["page_callback_like_slots"])
        self.assertTrue(diagnosis["page_event_offset_0x34_refs"])
        self.assertTrue(diagnosis["object_callback_like_slots"])
        self.assertTrue(diagnosis["object_event_offset_0x34_refs"])


if __name__ == "__main__":
    unittest.main()
