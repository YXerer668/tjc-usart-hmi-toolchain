from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASE51_CASE52 = ROOT / "examples" / "case51_case52_lifecycle_dispatch_candidates_20260518.json"
CASE52 = ROOT / "examples" / "case52_lifecycle_dispatch_candidates_20260518.json"
PAGE1_SLOT = ROOT / "reverse_usarthmi" / "page1_load_callback_slot_probe" / "hardware_probe_2026-05-15.json"
LOCAL_POSITIVE = ROOT / "examples" / "lifecycle_runtime_smoke" / "page0_load_local_generated_verified_2026-05-18.json"


@unittest.skipUnless(
    CASE51_CASE52.exists() and CASE52.exists() and PAGE1_SLOT.exists() and LOCAL_POSITIVE.exists(),
    "local lifecycle report inputs are not available",
)
class LifecycleRuntimeEquivalenceReportTests(unittest.TestCase):
    def test_report_compares_official_oracles_local_positive_and_slot_negative(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "lifecycle_matrix.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/lifecycle_runtime_equivalence_report.py",
                    "--case51-case52",
                    str(CASE51_CASE52),
                    "--case52",
                    str(CASE52),
                    "--page1-slot-probe",
                    str(PAGE1_SLOT),
                    "--local-page0-positive",
                    str(LOCAL_POSITIVE),
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
            self.assertEqual(saved["interpretation"], payload["interpretation"])
            rows = {row["label"]: row for row in payload["rows"]}
            self.assertEqual(rows["official_case51_page0_load"]["scheduler_path"], "page_event_boundary_without_page_callback")
            self.assertEqual(rows["official_case52_page1_load"]["scheduler_path"], "object_callbacks_only")
            self.assertEqual(rows["page1_slot_write_negative"]["runtime_result"], "no_printh_seen_after_slot_write")
            self.assertEqual(rows["local_generated_page0_load_positive"]["scheduler_path"], "post_primary_page_event")
            self.assertIn("observed AA 52 10 01", rows["local_generated_page0_load_positive"]["runtime_result"])
            self.assertFalse(payload["interpretation"]["official_page_load_uses_callback_slots"])
            self.assertFalse(payload["interpretation"]["page1_lifecycle_recovered"])


if __name__ == "__main__":
    unittest.main()
