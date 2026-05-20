from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/public_whmi_entry_probe_summary_2026-05-21.json")


class PublicWhmiEntryProbeSummaryArtifactTests(unittest.TestCase):
    def test_summary_confirms_upload_entry_silence(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "probe-summarized")
        self.assertFalse(payload["ack_received"])
        self.assertTrue(payload["conclusions"]["public_whmi_entry_is_silent"])
        self.assertTrue(payload["conclusions"]["runtime_silence_has_now_escalated_to_upload_entry_silence"])
        self.assertTrue(payload["conclusions"]["next_step_requires_physical_or_external_recovery"])


if __name__ == "__main__":
    unittest.main()
