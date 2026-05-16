from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools.page_event_scheduler_matrix import (
    DEFAULT_BATCH_REPORT,
    DEFAULT_HARDWARE_PROBE,
    build_scheduler_matrix,
)


class PageEventSchedulerMatrixUnitTests(unittest.TestCase):
    def test_matrix_combines_oracle_paths_and_negative_slots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            batch_report = root / "batch.json"
            slot_probe = _write_slot_probe(root / "slot_probe")
            batch_report.write_text(
                json.dumps(_batch_report(), ensure_ascii=False),
                encoding="utf-8",
            )

            matrix = build_scheduler_matrix(batch_report, slot_probe)

            self.assertEqual(
                matrix["oracle_summary"]["complete_scheduler_path_counts"],
                {"post_primary_page_event": 1},
            )
            self.assertEqual(
                matrix["oracle_summary"]["oracle_quality_counts"],
                {"complete": 1, "unsupported_command": 1},
            )
            self.assertEqual(
                matrix["scheduler_paths"]["post_primary_page_event"]["complete_count"],
                1,
            )
            self.assertEqual(
                matrix["scheduler_paths"]["post_primary_page_event"]["oracles"][0]["case_id"],
                "case_49_audio",
            )
            self.assertEqual(
                matrix["scheduler_paths"]["unbound_or_empty"]["oracle_quality_counts"],
                {"unsupported_command": 1},
            )
            self.assertEqual(
                matrix["scheduler_paths"]["unbound_or_empty"]["oracles"][0]["case_id"],
                "case_42_datarecord",
            )
            self.assertEqual(
                matrix["scheduler_paths"]["unbound_or_empty"]["oracles"][0][
                    "unsupported_commands"
                ],
                ["repo primaryKey.val,0"],
            )
            self.assertTrue(matrix["decision"]["do_not_repeat_blind_slot_writes"])
            self.assertEqual(
                matrix["decision"]["blocked_repeated_slots"],
                ["0x0C", "0x10", "0x14"],
            )
            self.assertIn(
                "blind_write_page_mirror_slots",
                matrix["decision"]["forbidden_actions"],
            )
            self.assertIn(
                "collect_complete_official_two_page_page_load_oracle",
                matrix["decision"]["allowed_next_actions"],
            )
            self.assertIn(
                "post-primary",
                matrix["decision"]["recommended_next_step"],
            )


@unittest.skipUnless(
    DEFAULT_BATCH_REPORT.exists() and DEFAULT_HARDWARE_PROBE.exists(),
    "local page-event scheduler evidence is not available",
)
class PageEventSchedulerMatrixFixtureTests(unittest.TestCase):
    def test_local_scheduler_matrix_records_current_guardrails(self) -> None:
        matrix = build_scheduler_matrix()

        self.assertEqual(
            matrix["oracle_summary"]["complete_scheduler_path_counts"],
            {"post_primary_page_event": 1},
        )
        self.assertEqual(
            matrix["page1_load_negative_slot_probe"]["tested_slots"],
            ["0x0C", "0x10", "0x14"],
        )
        self.assertTrue(
            matrix["page1_load_negative_slot_probe"]["all_candidates_failed_cleanly"]
        )
        self.assertFalse(
            matrix["page1_load_negative_slot_probe"]["page1_load_scheduler_recovered"]
        )
        self.assertTrue(matrix["decision"]["do_not_repeat_blind_slot_writes"])
        self.assertEqual(
            matrix["decision"]["confidence"],
            "high_for_guardrail_medium_for_scheduler_recovery",
        )


def _batch_report() -> dict[str, object]:
    unsupported = (
        "Unsupported event line for the current minimal logic compiler: "
        "'repo primaryKey.val,0'. Supported V1 event commands are page/printh."
    )
    return {
        "summary": {
            "hmi_scanned": 2,
            "page_event_hmi_count": 2,
            "items_with_successful_probe": 2,
            "items_with_complete_probe": 1,
            "scheduler_path_counts": {
                "post_primary_page_event": 1,
                "unbound_or_empty": 1,
            },
            "complete_scheduler_path_counts": {"post_primary_page_event": 1},
            "incomplete_best_probes": [
                {
                    "hmi": r"C:\cases\case_42_datarecord\official_wiki\source_raw.HMI",
                    "scheduler_path": "unbound_or_empty",
                    "page_event_table_error": unsupported,
                    "compile_context_error": "'B'",
                }
            ],
        },
        "items": [
            {
                "hmi": r"C:\cases\case_49_audio\official_wiki\source_raw.HMI",
                "page_event_count": 1,
                "object_event_count": 6,
                "event_name_counts": {"codesload": 1},
                "best_probe": {
                    "ok": True,
                    "complete": True,
                    "model": "TJC8048X543_011C",
                    "editor_version": "1.67.6",
                    "compile_context": {"available": True, "error": None},
                    "page_event_table_error": None,
                    "candidate": {
                        "path": r"C:\cases\case_49_audio\official_compile\source_raw.run",
                        "reason": "official_compile_same_stem_run",
                        "confidence": "high",
                        "size": 1453872,
                    },
                    "diagnosis": {
                        "scheduler_path": "post_primary_page_event",
                        "upload_risk": "research_only",
                        "recommended_writer_action": "Keep page-load generation fixture-gated.",
                    },
                },
            },
            {
                "hmi": r"C:\cases\case_42_datarecord\official_wiki\source_raw.HMI",
                "page_event_count": 1,
                "object_event_count": 5,
                "event_name_counts": {"codesload": 1},
                "best_probe": {
                    "ok": True,
                    "complete": False,
                    "model": "TJC8048X543_011C",
                    "editor_version": "1.67.6",
                    "compile_context": {"available": False, "error": "'B'"},
                    "page_event_table_error": unsupported,
                    "candidate": {
                        "path": r"C:\cases\case_42_datarecord\lcd_test.tft",
                        "reason": "case_root_lcd_test_tft",
                        "confidence": "low",
                        "size": 11014940,
                    },
                    "diagnosis": {
                        "scheduler_path": "unbound_or_empty",
                        "upload_risk": "unknown",
                        "recommended_writer_action": "Collect a smaller official oracle.",
                    },
                },
            },
        ],
    }


def _write_slot_probe(root: Path) -> Path:
    root.mkdir(parents=True)
    candidates = []
    for slot_hex, name, write_offset in [
        ("0x0C", "slot_0c_table_start", "0xAE1DB3"),
        ("0x10", "slot_10_table_start", "0xAE1DB7"),
        ("0x14", "slot_14_table_start", "0xAE1DBB"),
    ]:
        candidates.append(
            {
                "name": name,
                "slot_hex": slot_hex,
                "write_absolute_offset_hex": write_offset,
                "checksum_hex": "0x12345678",
                "serial_result": {
                    "initial_sendme_hex": "66 00 ff ff ff",
                    "after_page_1_sendme_hex": "66 01 ff ff ff",
                    "after_page_0_sendme_hex": "66 00 ff ff ff",
                    "expected_printh_seen": False,
                },
                "conclusion": "Failed cleanly.",
            }
        )
        variant_dir = root / name
        variant_dir.mkdir()
        (variant_dir / "variant_report_2026-05-15.json").write_text(
            json.dumps(
                {
                    "candidate": {
                        "write_absolute_offset_hex": write_offset,
                        "target_relative_offset_hex": "0x14B",
                    },
                    "diff": {"changed_offset_count": 8},
                    "checksum": {"valid": True},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    hardware_probe = root / "hardware_probe.json"
    hardware_probe.write_text(
        json.dumps(
            {
                "probe": "page1_load_callback_slot_probe",
                "date": "2026-05-15",
                "purpose": "Unit-test negative slot evidence.",
                "device": {"model": "TJC8048X543_011C"},
                "candidates": candidates,
                "overall_conclusion": "No tested blind slot triggered page load.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return hardware_probe


if __name__ == "__main__":
    unittest.main()
