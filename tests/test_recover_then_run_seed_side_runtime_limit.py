from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.recover_then_run_seed_side_runtime_limit import (
    build_recovery_command,
    build_runner_command,
    classify_path,
)


class RecoverThenRunSeedSideRuntimeLimitTests(unittest.TestCase):
    def test_build_recovery_command_points_at_official_tool(self) -> None:
        cmd = build_recovery_command(
            hmi=Path("reverse_usarthmi/official_page1_textselect_minimal_oracle_20260519/lcd_test.HMI"),
            port="COM36",
            download_baud=921600,
            wait_s=260.0,
        )
        self.assertIn("official_hmi_download_recovery.py", cmd[1])
        self.assertIn("--start-download", cmd)

    def test_build_runner_command_uses_textselect_control(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cmd = build_runner_command(
                out_dir=Path(tmp),
                port="COM36",
                baud=9600,
                download_baud=921600,
                timeout_ms=3000,
                capture=False,
            )
        self.assertIn("run_seed_side_multipt_runtime_limit_smokes.py", cmd[1])
        self.assertIn("--with-textselect-control", cmd)

    def test_classify_path_prefers_recovered_then_runner(self) -> None:
        before = {"responsive": False}
        after = {"responsive": True}
        self.assertEqual(classify_path(before, after, True), "recovered_then_ran_runner")
        self.assertEqual(classify_path({"responsive": True}, None, True), "runner_started_without_recovery")
        self.assertEqual(classify_path({"responsive": False}, {"responsive": False}, False), "still_silent_after_recovery")


if __name__ == "__main__":
    unittest.main()
