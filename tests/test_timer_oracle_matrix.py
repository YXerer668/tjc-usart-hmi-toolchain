from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tools.timer_oracle_matrix import _sibling_tft, _summary


class TimerOracleMatrixTests(unittest.TestCase):
    def test_summary_identifies_compiled_non_empty_timer_oracle(self) -> None:
        reports = [
            {
                "path": "empty_timer.HMI",
                "parse_ok": True,
                "timer_count": 1,
                "non_empty_timer_event_count": 0,
                "timer_blocks": [
                    {
                        "events": [
                            {"raw_header": "codestimer-0", "line_count": 0},
                        ],
                    },
                ],
                "sibling_tft": "empty_timer.tft",
            },
            {
                "path": "real_timer.HMI",
                "parse_ok": True,
                "timer_count": 1,
                "non_empty_timer_event_count": 1,
                "timer_blocks": [
                    {
                        "events": [
                            {"raw_header": "codestimer-2", "line_count": 2},
                        ],
                    },
                ],
                "sibling_tft": "real_timer.tft",
            },
        ]

        summary = _summary(reports)

        self.assertEqual(summary["timer_fixture_count"], 2)
        self.assertEqual(summary["non_empty_timer_event_fixture_count"], 1)
        self.assertEqual(summary["timer_event_headers"], {"codestimer-0": 1, "codestimer-2": 1})
        self.assertEqual(summary["compiled_timer_oracle_files"], ["real_timer.HMI"])

    def test_sibling_tft_prefers_matching_stem(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            hmi = Path(temp_dir) / "probe.HMI"
            tft = Path(temp_dir) / "probe.tft"
            hmi.write_bytes(b"dummy")
            tft.write_bytes(b"dummy")

            self.assertEqual(_sibling_tft(hmi), str(tft))


if __name__ == "__main__":
    unittest.main()
