from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from test_hmi_inspect import make_sample_hmi, make_structured_page_hmi
from tools.find_hmi_event_fixtures import scan_paths


class FindHMIEventFixturesTests(unittest.TestCase):
    def test_scan_reports_page_and_object_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            event_hmi = root / "structured.HMI"
            event_hmi.write_bytes(make_structured_page_hmi())
            plain_hmi = root / "plain.HMI"
            plain_hmi.write_bytes(make_sample_hmi())

            report = scan_paths([root])

            self.assertEqual(report["summary"]["scanned"], 2)
            self.assertEqual(report["summary"]["parse_ok"], 2)
            self.assertEqual(report["summary"]["page_event_fixture_count"], 1)
            self.assertEqual(report["summary"]["object_event_fixture_count"], 1)
            structured = next(item for item in report["files"] if item["path"].endswith("structured.HMI"))
            self.assertEqual(structured["page_event_count"], 1)
            self.assertEqual(structured["object_event_count"], 1)
            page_block = structured["eventful_blocks"][0]
            self.assertEqual(page_block["role"], "page")
            self.assertEqual(page_block["non_empty_events"][0]["name"], "codesload")
            self.assertEqual(page_block["non_empty_events"][0]["line_preview"], ["//用click去触发", "n0.val=dp"])

    def test_scan_reports_corrupt_hmi_without_raising(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            bad_hmi = root / "bad.HMI"
            bad_hmi.write_bytes(b"\x01")

            report = scan_paths([bad_hmi])

            self.assertEqual(report["summary"]["scanned"], 1)
            self.assertEqual(report["summary"]["parse_failed"], 1)
            self.assertFalse(report["files"][0]["parse_ok"])


if __name__ == "__main__":
    unittest.main()
