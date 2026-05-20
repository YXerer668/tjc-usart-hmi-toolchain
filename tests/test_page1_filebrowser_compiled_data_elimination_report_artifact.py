from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_compiled_data_elimination_2026-05-21.json")


class Page1FilebrowserCompiledDataEliminationReportArtifactTests(unittest.TestCase):
    def test_artifact_marks_compiled_data_envelope_exhausted(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "compiled-data-eliminated")
        self.assertTrue(payload["evidence"]["authoring_gap_separated"])
        self.assertTrue(payload["evidence"]["pointer_closure_valid"])
        self.assertTrue(payload["evidence"]["attr_user_header_identical"])
        self.assertTrue(payload["evidence"]["object_local_user_and_mirror_identical"])
        self.assertTrue(payload["evidence"]["full_page_local_user_identical"])
        self.assertTrue(payload["evidence"]["primary_records_identical"])
        self.assertTrue(payload["evidence"]["prefix_head_equivalent_after_generic_multipt_normalization"])
        self.assertTrue(payload["evidence"]["page_event_table_byte_identical"])
        self.assertTrue(payload["evidence"]["no_post_mirror_service_tail"])
        self.assertTrue(payload["conclusions"]["compiled_data_envelope_exhausted"])
        self.assertTrue(payload["conclusions"]["remaining_gap_is_not_locatable_in_current_object_tail_compiled_data"])


if __name__ == "__main__":
    unittest.main()
