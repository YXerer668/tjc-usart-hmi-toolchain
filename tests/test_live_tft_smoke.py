from __future__ import annotations

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.live_tft_smoke import _capture_frame_ffmpeg_dshow
from tools.live_tft_smoke import RuntimeStep, _load_runtime_steps, _run_serial_checks, _transact_check


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

    def test_runtime_step_delay_waits_before_step(self) -> None:
        calls: list[str] = []

        def fake_connect(_config):  # type: ignore[no-untyped-def]
            calls.append("connect")
            return {"label": "connect", "ok": True}

        def fake_transact(_config, command, **_kwargs):  # type: ignore[no-untyped-def]
            calls.append(command)
            return {"command": command, "ok": True}

        def fake_sleep(seconds):  # type: ignore[no-untyped-def]
            calls.append(f"sleep:{seconds:g}")

        with (
            patch("tools.live_tft_smoke._connect_check", fake_connect),
            patch("tools.live_tft_smoke._transact_check", fake_transact),
            patch("tools.live_tft_smoke.time.sleep", fake_sleep),
        ):
            _run_serial_checks(
                [],
                port="COM36",
                baud=9600,
                timeout_ms=3000,
                expected_page_id=0,
                select_page=None,
                set_expectations=[],
                runtime_steps=[
                    RuntimeStep(command="wav0.en=1", label="start wav0"),
                    RuntimeStep(command="get wav0.en", label="verify wav0 started", delay_ms=500),
                ],
                restore_page=None,
            )

        self.assertEqual(calls, ["connect", "sendme", "wav0.en=1", "sleep:0.5", "get wav0.en"])

    def test_runtime_step_attempts_are_loaded_from_expect_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            expect_path = Path(temp_dir) / "expect.json"
            expect_path.write_text(
                '{"steps":[{"command":"get wav0.en","expected_kind":"number","attempts":3}]}',
                encoding="utf-8",
            )

            steps = _load_runtime_steps(str(expect_path))

        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].command, "get wav0.en")
        self.assertEqual(steps[0].attempts, 3)

    def test_transact_check_retries_until_expected_value_matches(self) -> None:
        responses = [
            bytes.fromhex("71 00 00 00 00 ff ff ff"),
            bytes.fromhex("71 01 00 00 00 ff ff ff"),
        ]

        class FakeTransport:
            def __init__(self, _config):  # type: ignore[no-untyped-def]
                pass

            def transact(self, command):  # type: ignore[no-untyped-def]
                return command.encode("ascii") + b"\xff\xff\xff", responses.pop(0)

        with patch("tools.live_tft_smoke.SerialTransport", FakeTransport):
            result = _transact_check(
                object(),
                "get wav0.en",
                expected_kind="number",
                expected_value=1,
                attempts=3,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["attempt"], 2)
        self.assertEqual(result["attempts"], 3)
        self.assertEqual(result["actual_value"], 1)
        self.assertEqual(len(result["retry_history"]), 1)


if __name__ == "__main__":
    unittest.main()
