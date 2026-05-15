from __future__ import annotations

import unittest

from tools.page_event_callback_slot_status import summarize_callback_slot_probe


class PageEventCallbackSlotStatusTests(unittest.TestCase):
    def test_live_failed_slots_are_recorded_as_negative_evidence(self) -> None:
        report = summarize_callback_slot_probe()
        self.assertEqual(report["tested_slots"], ["0x0C", "0x10", "0x14"])
        self.assertFalse(report["summary"]["page1_load_scheduler_recovered"])
        self.assertTrue(report["summary"]["all_candidates_failed_cleanly"])
        self.assertEqual(
            report["summary"]["avoid_repeating_blind_slots"],
            ["0x0C", "0x10", "0x14"],
        )
        self.assertIn("official two-page/page-load oracle", report["summary"]["recommended_next_path"])

    def test_variant_reports_are_narrow_valid_checksum_patches(self) -> None:
        report = summarize_callback_slot_probe()
        for candidate in report["candidates"]:
            with self.subTest(candidate=candidate["name"]):
                self.assertTrue(candidate["checksum_valid"])
                self.assertTrue(candidate["page_switching_preserved"])
                self.assertFalse(candidate["expected_printh_seen"])
                self.assertEqual(candidate["target_relative_offset_hex"], "0x14B")
                self.assertEqual(candidate["changed_offset_count"], 8)


if __name__ == "__main__":
    unittest.main()
