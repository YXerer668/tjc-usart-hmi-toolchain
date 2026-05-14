from __future__ import annotations

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.live_tft_smoke import _capture_frame_ffmpeg_dshow


class LiveTftSmokeTests(unittest.TestCase):
    def test_ffmpeg_dshow_capture_uses_named_usb_cam_and_warmup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)

            def fake_run(cmd, **_kwargs):  # type: ignore[no-untyped-def]
                self.assertEqual(cmd[0], "ffmpeg")
                self.assertIn("video=USB Cam", cmd)
                self.assertIn("2560x1440", cmd)
                self.assertIn("-ss", cmd)
                (out_dir / "camera_after_smoke.jpg").write_bytes(b"jpg")
                return SimpleNamespace(returncode=0, stdout="", stderr="ok")

            args = Namespace(
                camera_device="USB Cam",
                camera_width=2560,
                camera_height=1440,
                camera_framerate=30,
                camera_pixel_format="yuyv422",
                camera_warmup_s=1.0,
            )

            with patch("tools.live_tft_smoke.subprocess.run", fake_run):
                result = _capture_frame_ffmpeg_dshow(args, out_dir)

            self.assertTrue(result["ok"])
            self.assertEqual(result["capture_method"], "ffmpeg-dshow")
            self.assertEqual(result["device"], "USB Cam")
            self.assertEqual(result["bytes"], 3)


if __name__ == "__main__":
    unittest.main()
