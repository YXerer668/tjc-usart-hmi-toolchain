from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.official_hmi_lowlevel_probe import _extract_page_lines, _harness_runtime_ready, _is_empty_shell_class


class OfficialHMILowlevelProbeTests(unittest.TestCase):
    def test_extract_page_lines_finds_english_and_chinese_compile_lines(self) -> None:
        stdout = "\n".join(
            [
                "stage=FileBianyi",
                "page0 occupied memory 16+340=356",
                "页面:page1 占用内存:16+32972=32988",
                "size=11417020",
            ]
        )
        self.assertEqual(
            _extract_page_lines(stdout),
            ["page0 occupied memory 16+340=356", "页面:page1 占用内存:16+32972=32988"],
        )

    def test_empty_shell_class_matches_known_size(self) -> None:
        self.assertTrue(
            _is_empty_shell_class(
                compiled_output_size=11_403_460,
                object_region_length=None,
                page_lines=[],
            )
        )

    def test_empty_shell_class_matches_old_object_region_without_page_lines(self) -> None:
        self.assertTrue(
            _is_empty_shell_class(
                compiled_output_size=11_410_000,
                object_region_length=0xC4,
                page_lines=[],
            )
        )

    def test_non_empty_compile_is_not_marked_empty_shell(self) -> None:
        self.assertFalse(
            _is_empty_shell_class(
                compiled_output_size=11_417_020,
                object_region_length=0x131C,
                page_lines=["page0 occupied memory 16+340=356"],
            )
        )

    def test_harness_runtime_ready_requires_official_startup_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            harness = root / "OfficialHeadlessCompile.exe"
            harness.write_bytes(b"exe")
            self.assertFalse(_harness_runtime_ready(harness))
            for name in ("ApplicationRUN.dll", "AppDllPass.dll", "ACTR.dll", "USART HMI.exe"):
                (root / name).write_bytes(name.encode("ascii"))
            self.assertTrue(_harness_runtime_ready(harness))
