from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/advanced_direct_tft_demo/page1_advanced_runtime_scope_report_2026-05-19.json")


class Page1AdvancedRuntimeScopeReportTests(unittest.TestCase):
    def test_scope_report_is_consistent(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "page1-advanced-runtime-scoped-out")
        self.assertEqual(payload["date"], "2026-05-20")
        self.assertEqual(payload["summary"]["count"], 5)
        self.assertFalse(payload["summary"]["filebrowser_mapping_resolved"])
        self.assertEqual(
            payload["summary"]["compile_positive_runtime_negative_controls"],
            ["text-select", "sliding-text", "data-record", "file-stream", "file-browser"],
        )
        self.assertEqual(payload["filebrowser_mapping"]["tested_variants"], 80)
        self.assertEqual(payload["filebrowser_mapping"]["found_candidates"], [])
        for control_name, item in payload["controls"].items():
            with self.subTest(control=control_name):
                self.assertTrue(item["compiled_success"])
                self.assertTrue(item["page_switch_ok"])
                self.assertTrue(item["sendme_ok"])
                self.assertEqual(item["runtime_status"], "invalid_reference")


if __name__ == "__main__":
    unittest.main()
