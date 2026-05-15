from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tools.program_s_oracle_probe import probe_program_s
from usarthmi.tft_patch import _compile_event_line, _event_item
from usarthmi.tft_toolchain import TftToolchainError


def _sample_hmi(program_s: bytes) -> bytes:
    resources = [
        ("Program.s", program_s),
        ("0.pa", b"\x00page0\x00"),
    ]
    header = bytearray(len(resources).to_bytes(4, "little"))
    data = bytearray()
    current_offset = 4 + 28 * len(resources)
    for index, (name, payload) in enumerate(resources):
        header.extend(name.encode("ascii").ljust(16, b"\x00"))
        header.extend(current_offset.to_bytes(4, "little"))
        header.extend(len(payload).to_bytes(4, "little"))
        header.extend((index + 1).to_bytes(4, "little"))
        data.extend(payload)
        current_offset += len(payload)
    return bytes(header + data)


def _compiled_item(line: str) -> bytes:
    payload = _compile_event_line(line, context=None)
    assert payload is not None
    return _event_item(payload)


class ProgramSOracleProbeTests(unittest.TestCase):
    def test_reports_compiled_line_and_contiguous_block_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            hmi = tmp / "sample.HMI"
            tft = tmp / "sample.tft"
            hmi.write_bytes(_sample_hmi(b"printh 23 02 41\r\npage 0\r\n"))
            block = _compiled_item("printh 23 02 41") + _compiled_item("page 0")
            tft.write_bytes(b"prefix" + block + b"suffix")

            report = probe_program_s(hmi, tft)

        self.assertEqual(report["summary"]["compiled_line_count"], 2)
        self.assertGreaterEqual(report["summary"]["line_match_count"], 2)
        self.assertEqual(report["summary"]["block_match_count"], 1)
        self.assertEqual(report["block_matches"][0]["line_range"], "1-2")
        self.assertEqual(report["block_matches"][0]["matches"][0]["region"], "whole_file_unknown")

    def test_global_startup_lines_compile_but_do_not_fake_missing_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            hmi = tmp / "sample.HMI"
            tft = tmp / "sample.tft"
            hmi.write_bytes(_sample_hmi(b"baud=9600\r\ndim=100\r\npage 0\r\n"))
            tft.write_bytes(b"\x00" * 32 + _compiled_item("page 0") + b"\x00" * 8)

            report = probe_program_s(hmi, tft)

        statuses = [item["compile_status"] for item in report["program_s_lines"]]
        self.assertEqual(statuses, ["compiled", "compiled", "compiled"])
        self.assertEqual(report["summary"]["compiled_line_count"], 3)
        self.assertEqual(report["summary"]["unsupported_line_count"], 0)
        self.assertEqual(report["summary"]["line_match_count"], 1)

    def test_fixture_proven_global_startup_assignment_bytes(self) -> None:
        expected = {
            "baud=9600": "0b 00 00 00 04 04 30 00 00 3d 03 80 25 00 00",
            "dim=100": "09 00 00 00 04 04 10 00 00 3d 31 30 30",
            "recmod=0": "07 00 00 00 04 08 0f 00 00 3d 30",
        }
        for line, expected_hex in expected.items():
            with self.subTest(line=line):
                self.assertEqual(_compiled_item(line).hex(" "), expected_hex)

    def test_unproven_baud_values_remain_unsupported(self) -> None:
        with self.assertRaisesRegex(TftToolchainError, "Only official fixture-proven baud=9600"):
            _compile_event_line("baud=115200", context=None)


CASE_ROOT = Path(r"C:\Users\SinYu\Desktop\case_for_codex")
BASELINE_HMI = CASE_ROOT / "case_00_baseline" / "lcd_test.HMI"
BASELINE_TFT = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"


@unittest.skipUnless(
    BASELINE_HMI.exists() and BASELINE_TFT.exists(),
    "local official baseline HMI/TFT pair is not available",
)
class ProgramSOracleOfficialFixtureTests(unittest.TestCase):
    def test_baseline_program_s_supported_tail_items_match_objects_region(self) -> None:
        report = probe_program_s(BASELINE_HMI, BASELINE_TFT)

        self.assertEqual(report["tft_meta"]["model"], "TJC8048X543_011")
        self.assertEqual(report["summary"]["compiled_line_count"], 5)
        self.assertEqual(report["summary"]["unsupported_line_count"], 1)
        self.assertGreaterEqual(report["summary"]["line_match_count"], 5)
        self.assertEqual(report["summary"]["block_match_count"], 1)
        match = report["block_matches"][0]["matches"][0]
        self.assertIn("unknown_objects_address", match["region"])
        self.assertEqual(match["confidence"], "high")
        self.assertEqual(match["offset_hex"], "0xAE00E6")


if __name__ == "__main__":
    unittest.main()
