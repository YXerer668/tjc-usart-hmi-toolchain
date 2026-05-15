from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools.page_event_callback_variant import build_variant


ROOT = Path(__file__).resolve().parents[1]
BINDING_REPORT = (
    ROOT
    / "reverse_usarthmi"
    / "page1_load_printh_event_probe"
    / "scheduler_binding_probe_2026-05-15.json"
)


def _source_tft_exists() -> bool:
    if not BINDING_REPORT.exists():
        return False
    report = json.loads(BINDING_REPORT.read_text(encoding="utf-8"))
    return Path(report["output_tft"]).exists()


@unittest.skipUnless(
    BINDING_REPORT.exists() and _source_tft_exists(),
    "local page1 load probe TFT is not available",
)
class PageEventCallbackVariantTests(unittest.TestCase):
    def test_callback_variant_changes_only_one_slot_and_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            report = build_variant(
                BINDING_REPORT,
                out_tft=tmp_path / "slot_10_table_start.tft",
                out_report=tmp_path / "slot_10_table_start.json",
                slot=0x10,
                target="table-start",
            )

        self.assertEqual(report["candidate"]["slot"], 0x10)
        self.assertEqual(report["candidate"]["target_relative_offset_hex"], "0x14B")
        self.assertEqual(report["candidate"]["old_bytes_hex"], "ff ff ff ff")
        self.assertEqual(report["candidate"]["new_bytes_hex"], "4b 01 00 00")
        self.assertEqual(report["diff"]["changed_offset_count"], 8)
        self.assertTrue(report["checksum"]["valid"])


if __name__ == "__main__":
    unittest.main()
