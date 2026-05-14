from __future__ import annotations

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.external_picture_demo_runner import _run_live_smoke


class ExternalPictureDemoRunnerTests(unittest.TestCase):
    def test_live_smoke_command_forwards_capture_and_expectation_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            output_tft = out_dir / "output.tft"
            output_tft.write_bytes(b"tft")
            expect = out_dir / "smoke.expect.json"
            expect.write_text("{}", encoding="utf-8")

            def fake_run(cmd, **_kwargs):  # type: ignore[no-untyped-def]
                self.assertTrue(any(Path(part).name == "live_tft_smoke.py" for part in cmd))
                self.assertIn("--capture", cmd)
                self.assertIn("--expect-json", cmd)
                self.assertIn(str(expect), cmd)
                return SimpleNamespace(returncode=0, stdout='{"summary":{"ok":true}}', stderr="")

            args = Namespace(
                expect_json=expect,
                port="COM36",
                baud=9600,
                download_baud=921600,
                timeout_ms=3000,
                upload=False,
                capture=True,
                progress=False,
                known_current=None,
                skip_if_identical=False,
            )

            with patch("tools.external_picture_demo_runner.subprocess.run", fake_run):
                result = _run_live_smoke(args, output_tft, out_dir)

            self.assertEqual(result["returncode"], 0)
            self.assertTrue(result["summary"]["ok"])


if __name__ == "__main__":
    unittest.main()
