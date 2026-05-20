from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_runtime_mapping_reverified_2026-05-20.json")


class Page1RuntimeMappingReverifiedArtifactTests(unittest.TestCase):
    def test_artifact_captures_corrected_runtime_page_mapping(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["target"], "TJC8048X543_011C")
        self.assertTrue(payload["conclusions"]["runtime_page_0_is_generated_or_official_page1"])
        self.assertTrue(payload["conclusions"]["local_page1_ordinary_text_binding_positive"])
        self.assertTrue(payload["conclusions"]["official_page1_text_select_binding_positive"])
        self.assertTrue(payload["conclusions"]["official_page1_sliding_text_binding_positive"])
        self.assertTrue(payload["conclusions"]["official_page1_data_record_binding_positive"])
        self.assertTrue(payload["conclusions"]["official_page1_file_stream_binding_positive"])
        self.assertFalse(payload["conclusions"]["official_page1_file_browser_binding_positive"])
        self.assertFalse(payload["conclusions"]["page1_load_scheduler_recovered"])

        local = payload["fresh_reverification"]["local_generated_page1_load_probe"]
        self.assertEqual(local["runtime_page_0"]["sendme"], 0)
        self.assertEqual(local["runtime_page_0"]["get_p1title_txt"]["value"], "LOAD")
        self.assertEqual(local["runtime_page_1"]["sendme"], 1)
        self.assertEqual(local["runtime_page_1"]["get_p1title_txt"]["kind"], "invalid_reference")

        text_select = payload["fresh_reverification"]["official_gui_page1_text_select"]
        self.assertEqual(text_select["runtime_page_0"]["get_select0_val"]["value"], 0)
        self.assertEqual(text_select["runtime_page_1"]["get_select0_val"]["kind"], "invalid_reference")

        sliding_text = payload["fresh_reverification"]["official_gui_page1_sliding_text"]
        self.assertEqual(
            sliding_text["runtime_page_0"]["get_slt0_txt"]["value"],
            "000\r\n111\r\n222\r\n333\r\n444\r\n666\r\n777\r\n777\r\n888\r\n999",
        )
        self.assertEqual(sliding_text["runtime_page_1"]["get_slt0_txt"]["kind"], "invalid_reference")

        data_record = payload["fresh_reverification"]["official_gui_page1_data_record"]
        self.assertEqual(data_record["runtime_page_0"]["get_data0_maxval"]["value"], 1000)
        self.assertEqual(data_record["runtime_page_0"]["get_data0_path"]["value"], "sd0/1.data")
        self.assertEqual(data_record["runtime_page_1"]["get_data0_maxval"]["kind"], "invalid_reference")

        file_stream = payload["fresh_reverification"]["official_gui_page1_file_stream"]
        self.assertEqual(file_stream["runtime_page_0"]["get_fs0_en"]["value"], 0)
        self.assertEqual(file_stream["runtime_page_0"]["get_fs0_val"]["value"], 0)
        self.assertEqual(file_stream["runtime_page_1"]["get_fs0_en"]["kind"], "invalid_reference")

        file_browser = payload["fresh_reverification"]["official_gui_page1_file_browser"]
        self.assertEqual(file_browser["runtime_page_0"]["get_fbrowser0_dir"]["kind"], "invalid_reference")
        self.assertEqual(file_browser["runtime_page_0"]["get_fbrowser0_filter"]["kind"], "invalid_reference")
        self.assertEqual(file_browser["runtime_page_0"]["get_fbrowser0_txt"]["kind"], "invalid_reference")


if __name__ == "__main__":
    unittest.main()
