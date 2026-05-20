from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/sd_recovery_package_2026-05-21.json")


class SdRecoveryPackageArtifactTests(unittest.TestCase):
    def test_artifact_identifies_known_good_sd_recovery_package(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "package-identified")
        self.assertTrue(payload["conclusions"]["sd_recovery_package_exists"])
        self.assertTrue(payload["conclusions"]["sd_recovery_state_currently_cleared"])
        self.assertEqual(payload["tft"]["bytes"], 11409248)
        self.assertRegex(payload["tft"]["sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
