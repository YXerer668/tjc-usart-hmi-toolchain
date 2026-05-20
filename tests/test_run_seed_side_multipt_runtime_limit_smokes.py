from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.run_seed_side_multipt_runtime_limit_smokes import (
    PROBES,
    ProbeSpec,
    build_smoke_command,
    classify_results,
)


class RunSeedSideMultiPageRuntimeLimitSmokesTests(unittest.TestCase):
    def test_build_smoke_command_uses_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            cmd = build_smoke_command(
                PROBES[0],
                out_dir=out_dir,
                port="COM36",
                baud=9600,
                download_baud=921600,
                timeout_ms=3000,
                post_upload_wait_s=2.0,
                capture=False,
            )
        self.assertIn("live_tft_smoke.py", cmd[1])
        self.assertIn("page0_filestream_multipt_blank_page1_probe_20260521", cmd[3])
        self.assertIn("page0_filestream_multipt_blank_page1_smoke_2026-05-21.json", cmd[7])
        self.assertIn("--upload", cmd)

    def test_classify_results_prefers_a_type_specific_runtime_limitation(self) -> None:
        results = {
            "page0_filestream_blank_page1": {"summary": {"ok": True}},
            "page0_filebrowser_blank_page1": {"summary": {"ok": False}},
        }
        classification = classify_results(results)
        self.assertEqual(classification["label"], "filestream_positive_and_filebrowser_negative")

    def test_classify_results_reports_both_negative(self) -> None:
        results = {
            "page0_filestream_blank_page1": {"summary": {"ok": False}},
            "page0_filebrowser_blank_page1": {"summary": {"ok": False}},
        }
        classification = classify_results(results)
        self.assertEqual(classification["label"], "both_negative")

    def test_classify_results_prefers_textselect_filestream_filebrowser_split(self) -> None:
        results = {
            "page0_textselect_blank_page1": {"summary": {"ok": True}},
            "page0_filestream_blank_page1": {"summary": {"ok": True}},
            "page0_filebrowser_blank_page1": {"summary": {"ok": False}},
        }
        classification = classify_results(results)
        self.assertEqual(classification["label"], "textselect_positive_filestream_positive_filebrowser_negative")

    def test_build_smoke_command_supports_optional_textselect_probe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            probe = ProbeSpec(
                "page0_textselect_blank_page1",
                Path("reverse_usarthmi/page0_textselect_multipt_blank_page1_probe_20260521/output.tft"),
                Path("examples/lifecycle_runtime_smoke/page0_textselect_multipt_blank_page1_smoke_2026-05-21.json"),
            )
            cmd = build_smoke_command(
                probe,
                out_dir=out_dir,
                port="COM36",
                baud=9600,
                download_baud=921600,
                timeout_ms=3000,
                post_upload_wait_s=2.0,
                capture=False,
            )
        self.assertIn("page0_textselect_multipt_blank_page1_probe_20260521", cmd[3])
        self.assertIn("page0_textselect_multipt_blank_page1_smoke_2026-05-21.json", cmd[7])


if __name__ == "__main__":
    unittest.main()
