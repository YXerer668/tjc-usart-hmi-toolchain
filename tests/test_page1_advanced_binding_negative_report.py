from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "reverse_usarthmi" / "advanced_direct_tft_multi_page_text_select_sliding_text_event_20260518"


@unittest.skipUnless(BUILD_DIR.exists(), "local page1 advanced negative build artifacts are not available")
class Page1AdvancedBindingNegativeReportTests(unittest.TestCase):
    def test_report_summarizes_runtime_binding_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "page1_binding_negative.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/page1_advanced_binding_negative_report.py",
                    str(BUILD_DIR),
                    "--out",
                    str(out),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(result.stdout)
            saved = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(saved["diagnosis"], payload["diagnosis"])
            self.assertEqual(payload["page_name"], "page1")
            self.assertEqual(payload["build_manifest"]["mode"], "experimental_multi_page_tft_patch")
            self.assertEqual(payload["build_manifest"]["experimental_events"], True)
            self.assertEqual(payload["event_index_summary"]["page_summary"]["source_event_slot_count"], 1)
            self.assertEqual(payload["event_index_summary"]["page_summary"]["compiled_event_table_match_count"], 1)
            self.assertTrue(payload["diagnosis"]["page_navigation_ok"])
            self.assertTrue(payload["diagnosis"]["event_bytes_compiled"])
            self.assertTrue(payload["diagnosis"]["page_runtime_lookup_failed"])
            self.assertTrue(payload["diagnosis"]["runtime_event_dispatch_failed"])
            self.assertTrue(payload["diagnosis"]["hash_ids_match_source"])
            self.assertTrue(payload["diagnosis"]["mirror_headers_match_source"])
            self.assertEqual(payload["diagnosis"]["likely_layer"], "page_local_runtime_binding")
            self.assertEqual(payload["compiled_page_layout"]["hash_ids"]["select1"], 1)
            self.assertEqual(payload["compiled_page_layout"]["mirror_headers"][0], "79 00 00 37")
            self.assertEqual(payload["compiled_page_layout"]["per_record_length"], 156)
            self.assertEqual(payload["compiled_page_layout"]["mirror_value_count_guess"], 50)
            self.assertEqual(payload["compiled_page_layout"]["mirror_headers"], payload["compiled_page_layout"]["expected_mirror_headers"])
            self.assertEqual(
                [item["command"] for item in payload["live_smoke"]["failed_runtime_lookups"]],
                ["get select1.val", "get slt1.txt", "get event1.txt"],
            )
            self.assertEqual(payload["live_smoke"]["failed_clicks"][0]["command"], "click event1,1")


if __name__ == "__main__":
    unittest.main()
