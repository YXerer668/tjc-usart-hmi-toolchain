from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/page1_filebrowser_attr_header_equivalence_2026-05-21.json")


class Page1FilebrowserAttrHeaderEquivalenceReportArtifactTests(unittest.TestCase):
    def test_artifact_confirms_attr_user_header_is_identical_across_cases(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        cases = payload["cases"]
        headers = {case["attr_user_header_hex"] for case in cases.values()}

        self.assertEqual(payload["status"], "attr-header-equivalent")
        self.assertEqual(len(headers), 1)
        self.assertTrue(payload["conclusions"]["all_four_attr_user_headers_identical"])
        self.assertTrue(payload["conclusions"]["attr_user_header_not_the_missing_filebrowser_registration_layer"])


if __name__ == "__main__":
    unittest.main()
