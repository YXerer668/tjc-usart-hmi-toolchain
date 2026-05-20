from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/sd_recovery_handoff_2026-05-21.json")


class SdRecoveryHandoffArtifactTests(unittest.TestCase):
    def test_artifact_points_at_generated_desktop_bundle(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "handoff-prepared")
        self.assertTrue(payload["bundle_dir"].endswith("TJC_SD_RECOVERY_CURRENT"))
        self.assertTrue(payload["bundle_zip"].endswith("TJC_SD_RECOVERY_CURRENT.zip"))
        self.assertTrue(payload["manifest_path"].endswith("package_manifest.json"))
        self.assertEqual(
            payload["repo_source_sha256"],
            "8a0bcbec7092056822bb044cb49bba985921b40c4ef72a3c05fe5443e52a65e8",
        )
        self.assertTrue(payload["followup_command_file"].endswith("恢复后运行.txt"))
        self.assertTrue(payload["followup_powershell_file"].endswith("恢复后运行.ps1"))
        self.assertTrue(payload["followup_cmd_file"].endswith("恢复后运行.cmd"))
        self.assertTrue(payload["verify_powershell_file"].endswith("校验恢复包.ps1"))
        self.assertTrue(payload["verify_cmd_file"].endswith("校验恢复包.cmd"))
        self.assertTrue(payload["ordered_verify_cmd"].endswith("00_先双击_校验恢复包.cmd"))
        self.assertTrue(payload["ordered_followup_cmd"].endswith("01_SD恢复完成后双击_继续验证.cmd"))
        self.assertTrue(payload["status_summary_file"].endswith("当前状态摘要.md"))


if __name__ == "__main__":
    unittest.main()
