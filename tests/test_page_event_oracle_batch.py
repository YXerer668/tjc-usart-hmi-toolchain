from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tools.page_event_oracle_batch import (
    _allow_case_root_lcd_test,
    _best_probe,
    _tft_candidates_for_hmi,
    build_batch_report,
)


CASE_ROOT = Path(r"C:\Users\SinYu\Desktop\case_for_codex")
CASE49_AUDIO_HMI = CASE_ROOT / "case_49_audio" / "official_wiki" / "source_raw.HMI"
CASE49_AUDIO_RUN = CASE_ROOT / "case_49_audio" / "official_compile" / "source_raw.run"


class PageEventOracleBatchUnitTests(unittest.TestCase):
    def test_tft_candidates_prefer_nearby_official_compile_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "case_99_page_event"
            hmi = root / "official_wiki" / "source_raw.HMI"
            hmi.parent.mkdir(parents=True)
            hmi.write_bytes(b"hmi")
            official_run = root / "official_compile" / "source_raw.run"
            official_run.parent.mkdir()
            official_run.write_bytes(b"run")
            root_tft = root / "lcd_test.tft"
            root_tft.write_bytes(b"tft")

            candidates = _tft_candidates_for_hmi(hmi)

            self.assertEqual(
                [(item["reason"], item["confidence"]) for item in candidates],
                [
                    ("official_compile_same_stem_run", "high"),
                ],
            )

    def test_official_wiki_source_raw_without_same_stem_output_does_not_use_lcd_test(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "case_41_sltext"
            hmi = root / "official_wiki" / "source_raw.HMI"
            hmi.parent.mkdir(parents=True)
            hmi.write_bytes(b"hmi")
            lcd_test = root / "lcd_test.tft"
            lcd_test.write_bytes(b"wrong oracle")

            candidates = _tft_candidates_for_hmi(hmi)

            self.assertEqual(candidates, [])

    def test_official_wiki_named_fixture_does_not_use_source_raw_or_lcd_test(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "case_37_combobox"
            hmi = root / "official_wiki" / "combobox_demo.HMI"
            hmi.parent.mkdir(parents=True)
            hmi.write_bytes(b"hmi")
            official_source_raw = root / "official_compile" / "source_raw.run"
            official_source_raw.parent.mkdir()
            official_source_raw.write_bytes(b"wrong oracle")
            lcd_test = root / "lcd_test.tft"
            lcd_test.write_bytes(b"wrong oracle")

            candidates = _tft_candidates_for_hmi(hmi)

            self.assertEqual(candidates, [])

    def test_root_lcd_test_fixture_still_accepts_case_root_lcd_test_tft(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "case_01_text"
            hmi = root / "lcd_test.HMI"
            hmi.parent.mkdir(parents=True)
            hmi.write_bytes(b"hmi")
            tft = root / "lcd_test.tft"
            tft.write_bytes(b"tft")

            candidates = _tft_candidates_for_hmi(hmi)

            self.assertEqual(
                [(item["reason"], "lcd_test.tft" in str(item["path"])) for item in candidates],
                [("same_dir_same_stem_tft", True)],
            )

    def test_case_root_lcd_test_guardrail(self) -> None:
        self.assertFalse(
            _allow_case_root_lcd_test(Path(r"C:\cases\case_41\official_wiki\source_raw.HMI"))
        )
        self.assertFalse(
            _allow_case_root_lcd_test(Path(r"C:\cases\case_41\official_wiki\demo.HMI"))
        )
        self.assertTrue(_allow_case_root_lcd_test(Path(r"C:\cases\case_01\lcd_test.HMI")))

    def test_best_probe_ranks_complete_probe_before_confidence(self) -> None:
        probes = [
            {
                "ok": True,
                "complete": True,
                "candidate": {"confidence": "low"},
                "diagnosis": {"scheduler_path": "post_primary_page_event"},
            },
            {
                "ok": True,
                "complete": False,
                "candidate": {"confidence": "high"},
                "diagnosis": {"scheduler_path": "normal_page_table_without_page_callback"},
            },
        ]

        self.assertEqual(
            _best_probe(probes)["diagnosis"]["scheduler_path"],
            "post_primary_page_event",
        )


@unittest.skipUnless(
    CASE49_AUDIO_HMI.exists() and CASE49_AUDIO_RUN.exists(),
    "local official audio page-load oracle is not available",
)
class PageEventOracleBatchFixtureTests(unittest.TestCase):
    def test_batch_report_classifies_audio_page_load_oracle(self) -> None:
        report = build_batch_report([CASE49_AUDIO_HMI])

        self.assertEqual(report["summary"]["page_event_hmi_count"], 1)
        self.assertEqual(report["summary"]["items_with_successful_probe"], 1)
        self.assertEqual(report["summary"]["items_with_complete_probe"], 1)
        self.assertEqual(
            report["summary"]["scheduler_path_counts"],
            {"post_primary_page_event": 1},
        )
        self.assertEqual(
            report["summary"]["complete_scheduler_path_counts"],
            {"post_primary_page_event": 1},
        )
        item = report["items"][0]
        self.assertTrue(item["best_probe"]["complete"])
        self.assertEqual(
            item["best_probe"]["candidate"]["reason"],
            "official_compile_same_stem_run",
        )
        self.assertEqual(
            item["best_probe"]["diagnosis"]["scheduler_path"],
            "post_primary_page_event",
        )
        descriptor = item["best_probe"]["post_primary_page_event"]["descriptors"][0]
        self.assertEqual(descriptor["offset_hex"], "0x8DA")
        self.assertEqual(descriptor["length"], 32)
        self.assertEqual(
            descriptor["payload_sha256"],
            "351515b69f4905ccc4f36d371113f8a7093031530c7ed0a25e485bbcdbb45cbc",
        )


if __name__ == "__main__":
    unittest.main()
