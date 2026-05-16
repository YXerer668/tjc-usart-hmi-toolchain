from __future__ import annotations

from pathlib import Path
import unittest

from tools.page_event_oracle_probe import _slot_target_matches, probe_hmi_tft


ROOT = Path(__file__).resolve().parents[1]
CASE_ROOT = Path(r"C:\Users\SinYu\Desktop\case_for_codex")
EVENT_DEMO_HMI = ROOT / "reverse_usarthmi" / "event_demo_live_probe_20260515" / "output.hmi"
EVENT_DEMO_TFT = ROOT / "reverse_usarthmi" / "event_demo_live_probe_20260515" / "output.tft"
CASE42_PAGE_EVENT_HMI = CASE_ROOT / "case_42_datarecord" / "official_wiki" / "source_raw.HMI"
CASE42_ROOT_TFT = CASE_ROOT / "case_42_datarecord" / "lcd_test.tft"
CASE49_AUDIO_HMI = CASE_ROOT / "case_49_audio" / "official_wiki" / "source_raw.HMI"
CASE49_AUDIO_RUN = CASE_ROOT / "case_49_audio" / "official_compile" / "source_raw.run"


class PageEventOracleUnitTests(unittest.TestCase):
    def test_slot_target_matches_distinguish_exact_and_inside_table(self) -> None:
        targets = [
            {
                "name": "event_table_start",
                "value": 0x100,
                "table_start": 0x100,
                "table_end": 0x130,
            },
            {
                "name": "first_executable",
                "value": 0x10C,
                "table_start": 0x100,
                "table_end": 0x130,
            },
        ]

        exact = _slot_target_matches(0x10C, targets)
        inside = _slot_target_matches(0x118, targets)

        self.assertEqual(
            [(item["name"], item["exact"], item["delta_hex"]) for item in exact],
            [("event_table_start", False, "0xC"), ("first_executable", True, "0xC")],
        )
        self.assertEqual(
            [(item["name"], item["exact"], item["delta_hex"]) for item in inside],
            [("event_table_start", False, "0x18"), ("first_executable", False, "0x18")],
        )


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


@unittest.skipUnless(
    CASE49_AUDIO_HMI.exists() and CASE49_AUDIO_RUN.exists(),
    "local official audio page-load oracle is not available",
)
class PageEventOracleOfficialFixtureTests(unittest.TestCase):
    def test_audio_page_load_uses_post_primary_chunk(self) -> None:
        report = probe_hmi_tft(CASE49_AUDIO_HMI, CASE49_AUDIO_RUN)
        diagnosis = report["diagnosis"]

        self.assertTrue(report["compile_context"]["available"])
        self.assertTrue(diagnosis["page_load_non_empty"])
        self.assertFalse(diagnosis["page_event_table_found"])
        self.assertTrue(diagnosis["post_primary_page_event_found"])
        self.assertEqual(diagnosis["scheduler_path"], "post_primary_page_event")
        self.assertEqual(report["post_primary_page_event"]["matches"][0]["hex"], "0x8DA")
        descriptor = report["post_primary_page_event"]["descriptors"][0]
        self.assertEqual(descriptor["offset_hex"], "0x8DA")
        self.assertEqual(descriptor["length"], report["post_primary_page_event"]["length"])
        self.assertEqual(descriptor["first_executable_offset_hex"], "0x0")
        self.assertEqual(len(descriptor["payload_sha256"]), 64)
        self.assertTrue(descriptor["context_before_hex"])
        self.assertTrue(descriptor["context_after_hex"])

    def test_unsupported_datarecord_fixture_fails_soft(self) -> None:
        if not (CASE42_PAGE_EVENT_HMI.exists() and CASE42_ROOT_TFT.exists()):
            self.skipTest("local datarecord fixture is not available")

        report = probe_hmi_tft(CASE42_PAGE_EVENT_HMI, CASE42_ROOT_TFT)

        self.assertFalse(report["compile_context"]["available"])
        self.assertIn("B", report["compile_context"]["unsupported_type_codes"])
        self.assertIn("repo primaryKey.val,0", report["blocks"][0]["event_table_error"])


if __name__ == "__main__":
    unittest.main()
