from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/sd_recovery_handoff_verify_2026-05-21.json")


class SdRecoveryHandoffVerifyArtifactTests(unittest.TestCase):
    def test_verify_artifact_confirms_desktop_bundle_integrity(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["size_ok"])
        self.assertTrue(payload["sha256_ok"])
        self.assertEqual(payload["expected_size"], payload["actual_size"])
        self.assertEqual(payload["expected_sha256"], payload["actual_sha256"])


if __name__ == "__main__":
    unittest.main()
