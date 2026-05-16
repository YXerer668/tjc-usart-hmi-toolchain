from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools.page_event_post_primary_diff import (
    DEFAULT_LEFT_HMI,
    DEFAULT_LEFT_TFT,
    DEFAULT_RIGHT_REPORT,
    build_post_primary_diff,
)


class PageEventPostPrimaryDiffUnitTests(unittest.TestCase):
    def test_diff_reports_payload_and_live_outcome_differences(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            left_report = root / "left.json"
            right_dir = root / "right"
            right_dir.mkdir()
            right_report = right_dir / "right.json"
            live_report = right_dir / "live_failure_2026-05-15.json"

            left_report.write_text(
                json.dumps(_report("left", offset=0x8DA, length=32, payload_hash="aaa")),
                encoding="utf-8",
            )
            right_report.write_text(
                json.dumps(
                    _report(
                        "right",
                        offset=0x3C5,
                        length=37,
                        payload_hash="bbb",
                        force=True,
                    )
                ),
                encoding="utf-8",
            )
            live_report.write_text(
                json.dumps(
                    {
                        "probe": "event_demo_post_primary_probe_20260515",
                        "purpose": "negative live test",
                        "build": {
                            "checksum_valid": True,
                            "post_primary_page_event_found_by_probe": True,
                        },
                        "conclusion": "runtime command parser unresponsive except for connect",
                    }
                ),
                encoding="utf-8",
            )

            diff = build_post_primary_diff(
                left_report=left_report,
                right_report=right_report,
                left_hmi=None,
                left_tft=None,
                right_hmi=None,
                right_tft=None,
            )

            self.assertFalse(diff["comparison"]["same_payload_sha256"])
            self.assertEqual(diff["comparison"]["length_delta_right_minus_left"], 5)
            self.assertEqual(diff["comparison"]["offset_delta_right_minus_left"], 0x3C5 - 0x8DA)
            self.assertEqual(
                diff["comparison"]["diagnosis_paths"],
                {"left": "post_primary_page_event", "right": "post_primary_page_event"},
            )
            self.assertIn("generated force-post-primary", " ".join(diff["decision"]["notes"]))
            self.assertFalse(diff["decision"]["safe_to_burn_more_force_post_primary"])
            self.assertEqual(
                diff["right"]["live_outcome"]["conclusion"],
                "runtime command parser unresponsive except for connect",
            )
            self.assertEqual(diff["comparison"]["context_after_common_prefix"]["length"], 9)
            self.assertEqual(diff["comparison"]["context_after_common_prefix_word_count"], 2)
            self.assertEqual(
                [word["u32_hex"] for word in diff["comparison"]["context_after_common_prefix_words"]],
                ["0x00000001", "0x00000002"],
            )


@unittest.skipUnless(
    DEFAULT_LEFT_HMI.exists() and DEFAULT_LEFT_TFT.exists() and DEFAULT_RIGHT_REPORT.exists(),
    "local post-primary official/generated fixtures are not available",
)
class PageEventPostPrimaryDiffFixtureTests(unittest.TestCase):
    def test_local_official_vs_generated_post_primary_diff(self) -> None:
        diff = build_post_primary_diff()

        self.assertEqual(
            diff["left"]["post_primary_page_event"]["descriptor"]["offset_hex"],
            "0x8DA",
        )
        self.assertEqual(
            diff["left"]["post_primary_page_event"]["descriptor"]["payload_sha256"],
            "351515b69f4905ccc4f36d371113f8a7093031530c7ed0a25e485bbcdbb45cbc",
        )
        self.assertEqual(
            diff["right"]["post_primary_page_event"]["descriptor"]["offset_hex"],
            "0x3C5",
        )
        self.assertEqual(diff["comparison"]["length_delta_right_minus_left"], 5)
        self.assertFalse(diff["comparison"]["same_payload_sha256"])
        self.assertEqual(diff["comparison"]["context_after_common_prefix"]["length"], 32)
        self.assertTrue(diff["comparison"]["shared_adjacent_context_candidate"])
        self.assertEqual(diff["comparison"]["context_after_common_prefix_word_count"], 8)
        self.assertEqual(
            diff["comparison"]["context_after_common_prefix_words"][0]["u32_hex"],
            "0xD073BAFB",
        )
        self.assertEqual(
            diff["comparison"]["context_after_common_prefix_words"][-1]["u32_hex"],
            "0x00000004",
        )
        self.assertFalse(diff["decision"]["safe_to_burn_more_force_post_primary"])
        self.assertIn("live negative evidence", " ".join(diff["decision"]["notes"]))
        self.assertIn("scheduler-record candidate", " ".join(diff["decision"]["notes"]))


def _report(
    label: str,
    *,
    offset: int,
    length: int,
    payload_hash: str,
    force: bool = False,
) -> dict[str, object]:
    return {
        "hmi": f"{label}.HMI",
        "tft": f"{label}.tft",
        "model": "TJC8048X543_011C",
        "editor_version": "test",
        "diagnosis": {"scheduler_path": "post_primary_page_event"},
        "post_primary_page_event": {
            "force_post_primary_page_load": force,
            "length": length,
            "items": [
                {
                    "kind": "separator",
                    "command": "post_primary_page_load",
                    "length": 4,
                    "payload_hex": "09 1f 04 35",
                }
            ],
            "descriptors": [
                {
                    "offset": offset,
                    "offset_hex": f"0x{offset:X}",
                    "length": length,
                    "payload_sha256": payload_hash,
                    "first_executable_offset": 0,
                    "references": {
                        "table_start": [],
                        "first_executable": [],
                    },
                    "context_before_hex": "00 11 22",
                    "context_after_hex": "01 00 00 00 02 00 00 00 ff",
                }
            ],
        },
    }


if __name__ == "__main__":
    unittest.main()
