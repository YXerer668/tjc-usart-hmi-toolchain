from __future__ import annotations

import unittest

from tools.page_event_oracle_probe import _recommended_writer_action, _scheduler_path, _upload_risk


class PageEventOracleDiagnosisTests(unittest.TestCase):
    def test_post_primary_page_event_is_research_only(self) -> None:
        path = _scheduler_path(
            page_load_non_empty=True,
            page_event_table_found=False,
            post_primary_page_event_found=True,
            page_callbacks=[],
            object_callbacks=[],
            page_event_offsets=[],
        )

        self.assertEqual(path, "post_primary_page_event")
        self.assertEqual(_upload_risk(path), "research_only")
        self.assertIn("post-primary chunk", _recommended_writer_action(path))

    def test_normal_page_table_without_callback_is_high_risk(self) -> None:
        path = _scheduler_path(
            page_load_non_empty=True,
            page_event_table_found=True,
            post_primary_page_event_found=False,
            page_callbacks=[],
            object_callbacks=[{"objname": "b0", "slots": ["slot_0x10"]}],
            page_event_offsets=[{"record_offset_hex": "0x100", "slots": ["event_offset_0x34"]}],
        )

        self.assertEqual(path, "normal_page_table_without_page_callback")
        self.assertEqual(_upload_risk(path), "high")
        self.assertIn("Do not burn callback-slot guesses", _recommended_writer_action(path))

    def test_object_callbacks_do_not_prove_page_load(self) -> None:
        path = _scheduler_path(
            page_load_non_empty=False,
            page_event_table_found=False,
            post_primary_page_event_found=False,
            page_callbacks=[],
            object_callbacks=[{"objname": "b0", "slots": ["slot_0x10"]}],
            page_event_offsets=[],
        )

        self.assertEqual(path, "object_callbacks_only")
        self.assertEqual(_upload_risk(path), "low_for_object_events_only")


if __name__ == "__main__":
    unittest.main()
