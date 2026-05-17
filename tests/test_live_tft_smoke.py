from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.live_tft_smoke import _capture_frame_ffmpeg_dshow
from tools.live_tft_smoke import (
    RuntimeExpectation,
    RuntimeStep,
    _load_expectations,
    _load_runtime_steps,
    _run_serial_checks,
    _transact_check,
    run_smoke,
)


class LiveTftSmokeTests(unittest.TestCase):
    def test_new_controls_demo_smoke_expect_loads_candidate_readbacks(self) -> None:
        expect_path = Path("examples/new_controls_demo/smoke.expect.json")
        config = json.loads(expect_path.read_text(encoding="utf-8"))
        expectations = _load_expectations(str(expect_path), [])
        targets = {item.target: item.expected for item in expectations}

        self.assertEqual(config["page_id"], 0)
        self.assertEqual(config["select_page"], 0)
        self.assertEqual(
            targets,
            {
                "bar1.val": 68,
                "slider1.val": 42,
                "gauge1.val": 75,
                "qr1.txt": "USART HMI",
                "g0.txt": "SCROLLING TEXT",
                "bt0.val": 0,
                "bt1.val": 1,
                "sw0.val": 1,
                "c0.val": 1,
                "r0.val": 1,
                "va0.val": 123,
            },
        )
        self.assertTrue(all(item.attempts == 3 for item in expectations))

    def test_new_controls_demo_hardware_evidence_matches_smoke_expect(self) -> None:
        expect_path = Path("examples/new_controls_demo/smoke.expect.json")
        evidence_path = Path("examples/new_controls_demo/hardware_verified_2026-05-17.json")
        expectations = _load_expectations(str(expect_path), [])
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        expected_targets = {item.target: item.expected for item in expectations}
        passed_targets = {item["target"]: item["actual"] for item in evidence["serial_readback_passed"]}

        self.assertTrue(evidence["summary"]["ok"])
        self.assertEqual(evidence["expect_json"], expect_path.as_posix())
        self.assertEqual(passed_targets, expected_targets)
        self.assertIn("bt1.val", passed_targets)
        self.assertIn("crop-image runtime attribute readback", evidence["not_claimed"][0])
        self.assertEqual(evidence["upload"]["checksum_hex"], "0xCEC1B698")

    def test_external_picture_demo_smoke_expect_loads_readbacks(self) -> None:
        expect_path = Path("examples/external_picture_demo/smoke.expect.json")
        config = json.loads(expect_path.read_text(encoding="utf-8"))
        expectations = _load_expectations(str(expect_path), [])
        targets = {item.target: item.expected for item in expectations}

        self.assertEqual(config["page_id"], 0)
        self.assertEqual(
            targets,
            {
                "exp0.path": "sd0/1.jpg",
                "guard.txt": "guard.txt ok",
            },
        )
        self.assertTrue(all(item.attempts == 3 for item in expectations))

    def test_external_picture_demo_hardware_evidence_matches_smoke_expect(self) -> None:
        expect_path = Path("examples/external_picture_demo/smoke.expect.json")
        evidence_path = Path("examples/external_picture_demo/hardware_verified_2026-05-17.json")
        expectations = _load_expectations(str(expect_path), [])
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        expected_targets = {item.target: item.expected for item in expectations}
        passed_targets = {item["target"]: item["actual"] for item in evidence["serial_readback_passed"]}

        self.assertTrue(evidence["summary"]["ok"])
        self.assertEqual(evidence["expect_json"], expect_path.as_posix())
        self.assertEqual(passed_targets, expected_targets)
        self.assertEqual(evidence["upload"]["checksum_hex"], "0x046E5517")
        self.assertTrue(evidence["summary"]["camera_ok"])
        self.assertIn("pixel-level assertion", evidence["not_claimed"][0])

    def test_xfloat_combobox_demo_smoke_expect_loads_readbacks(self) -> None:
        expect_path = Path("examples/xfloat_combobox_demo/smoke.expect.json")
        config = json.loads(expect_path.read_text(encoding="utf-8"))
        expectations = _load_expectations(str(expect_path), [])
        targets = {item.target: item.expected for item in expectations}

        self.assertEqual(config["page_id"], 0)
        self.assertEqual(config["select_page"], 0)
        self.assertEqual(
            targets,
            {
                "title.txt": "XFLOAT + COMBO",
                "xval.val": 123456,
                "xval.vvs1": 3,
                "cbval.val": 2,
                "cbval.down": 1,
                "cbval.txt": "80V",
            },
        )
        self.assertTrue(all(item.attempts == 3 for item in expectations))

    def test_xfloat_combobox_demo_hardware_evidence_matches_smoke_expect(self) -> None:
        expect_path = Path("examples/xfloat_combobox_demo/smoke.expect.json")
        evidence_path = Path("examples/xfloat_combobox_demo/hardware_verified_2026-05-17.json")
        expectations = _load_expectations(str(expect_path), [])
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        expected_targets = {item.target: item.expected for item in expectations}
        passed_targets = {item["target"]: item["actual"] for item in evidence["serial_readback_passed"]}
        first_attempt_targets = {item["target"] for item in evidence["first_attempt_findings"]}

        self.assertTrue(evidence["final_smoke"]["summary"]["ok"])
        self.assertEqual(evidence["expect_json"], expect_path.as_posix())
        self.assertEqual(passed_targets, expected_targets)
        self.assertEqual(evidence["build"]["checksum_hex"], "0x0250F0A0")
        self.assertIn("xval.vvs0", first_attempt_targets)
        self.assertIn("cbval.qty", first_attempt_targets)
        self.assertIn("dropdown interaction", evidence["not_claimed"][0])

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
                (
                    '{"steps":[{"command":"click ping0,0","expected_kind":"unknown",'
                    '"expected_hex":"23 02 50 31","expected_ascii_preview":"#\\u0002P1","attempts":3}]}'
                ),
                encoding="utf-8",
            )

            steps = _load_runtime_steps(str(expect_path))

        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].command, "click ping0,0")
        self.assertEqual(steps[0].expected_hex, "23 02 50 31")
        self.assertEqual(steps[0].expected_ascii_preview, "#\u0002P1")
        self.assertEqual(steps[0].attempts, 3)

    def test_load_runtime_steps_parses_numeric_range(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            expect_path = Path(temp_dir) / "expect.json"
            expect_path.write_text(
                '{"steps":[{"command":"get n0.val","expected_kind":"number",'
                '"expected_min":1,"expected_max":"5","attempts":3}]}',
                encoding="utf-8",
            )
            steps = _load_runtime_steps(str(expect_path))

        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].command, "get n0.val")
        self.assertEqual(steps[0].expected_min, 1)
        self.assertEqual(steps[0].expected_max, 5)
        self.assertEqual(steps[0].attempts, 3)

    def test_runtime_expectation_attempts_are_loaded_from_expect_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            expect_path = Path(temp_dir) / "expect.json"
            expect_path.write_text(
                '{"expectations":[{"target":"wav0.en","expected":0,"expected_kind":"number","attempts":4}]}',
                encoding="utf-8",
            )

            expectations = _load_expectations(str(expect_path), [])

        self.assertEqual(len(expectations), 1)
        self.assertEqual(expectations[0].target, "wav0.en")
        self.assertEqual(expectations[0].expected, 0)
        self.assertEqual(expectations[0].expected_kind, "number")
        self.assertEqual(expectations[0].attempts, 4)

    def test_expect_json_config_keys_do_not_become_get_expectations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            expect_path = Path(temp_dir) / "expect.json"
            expect_path.write_text(
                """
                {
                  "page_id": 0,
                  "select_page": 0,
                  "steps": [{"command": "click ping0,0", "expected_kind": "unknown"}],
                  "restore_page": 0
                }
                """,
                encoding="utf-8",
            )

            expectations = _load_expectations(str(expect_path), [])
            steps = _load_runtime_steps(str(expect_path))

        self.assertEqual(expectations, [])
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].command, "click ping0,0")

    def test_bare_expect_json_map_still_loads_legacy_expectations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            expect_path = Path(temp_dir) / "expect.json"
            expect_path.write_text('{"wav0.en": 1}', encoding="utf-8")

            expectations = _load_expectations(str(expect_path), [])

        self.assertEqual(len(expectations), 1)
        self.assertEqual(expectations[0].target, "wav0.en")
        self.assertEqual(expectations[0].expected, 1)

    def test_runtime_expectation_attempts_are_passed_to_transact_checks(self) -> None:
        calls: list[tuple[str, str | None, int]] = []

        def fake_connect(_config):  # type: ignore[no-untyped-def]
            calls.append(("connect", None, 1))
            return {"label": "connect", "ok": True}

        def fake_transact(_config, command, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((command, kwargs.get("expected_kind"), int(kwargs.get("attempts", 1))))
            return {"command": command, "ok": True}

        with (
            patch("tools.live_tft_smoke._connect_check", fake_connect),
            patch("tools.live_tft_smoke._transact_check", fake_transact),
        ):
            _run_serial_checks(
                [RuntimeExpectation("wav0.en", 0, expected_kind="number", attempts=3)],
                port="COM36",
                baud=9600,
                timeout_ms=3000,
                expected_page_id=0,
                select_page=None,
                set_expectations=[RuntimeExpectation("wav0.loop", 1, expected_kind="number", attempts=4)],
                runtime_steps=[],
                restore_page=None,
            )

        self.assertEqual(
            calls,
            [
                ("connect", None, 1),
                ("sendme", "page_id", 1),
                ("get wav0.en", "number", 3),
                ("wav0.loop=1", None, 4),
                ("get wav0.loop", "number", 4),
            ],
        )

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

    def test_transact_check_can_match_raw_hex_and_ascii_preview(self) -> None:
        class FakeTransport:
            def __init__(self, _config):  # type: ignore[no-untyped-def]
                pass

            def transact(self, command):  # type: ignore[no-untyped-def]
                return command.encode("ascii") + b"\xff\xff\xff", bytes.fromhex("23 02 50 31")

        with patch("tools.live_tft_smoke.SerialTransport", FakeTransport):
            result = _transact_check(
                object(),
                "click ping0,0",
                expected_kind="unknown",
                expected_hex="23 02 50 31",
                expected_ascii_preview="#\u0002P1",
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["response"]["hex"], "23 02 50 31")
        self.assertEqual(result["response"]["ascii_preview"], "#\u0002P1")

    def test_transact_check_fails_on_unexpected_raw_hex(self) -> None:
        class FakeTransport:
            def __init__(self, _config):  # type: ignore[no-untyped-def]
                pass

            def transact(self, command):  # type: ignore[no-untyped-def]
                return command.encode("ascii") + b"\xff\xff\xff", bytes.fromhex("23 02 50 31")

        with patch("tools.live_tft_smoke.SerialTransport", FakeTransport):
            result = _transact_check(
                object(),
                "click ping0,0",
                expected_kind="unknown",
                expected_hex="23 02 50 32",
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["expected_hex"], "23 02 50 32")

    def test_transact_check_can_match_numeric_range(self) -> None:
        class FakeTransport:
            def __init__(self, _config):  # type: ignore[no-untyped-def]
                pass

            def transact(self, command):  # type: ignore[no-untyped-def]
                return command.encode("ascii") + b"\xff\xff\xff", bytes.fromhex("71 03 00 00 00 ff ff ff")

        with patch("tools.live_tft_smoke.SerialTransport", FakeTransport):
            result = _transact_check(
                object(),
                "get n0.val",
                expected_kind="number",
                expected_min=1,
                expected_max=10,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["actual_value"], 3)

    def test_transact_check_fails_on_numeric_range_miss(self) -> None:
        class FakeTransport:
            def __init__(self, _config):  # type: ignore[no-untyped-def]
                pass

            def transact(self, command):  # type: ignore[no-untyped-def]
                return command.encode("ascii") + b"\xff\xff\xff", bytes.fromhex("71 00 00 00 00 ff ff ff")

        with patch("tools.live_tft_smoke.SerialTransport", FakeTransport):
            result = _transact_check(
                object(),
                "get n0.val",
                expected_kind="number",
                expected_min=1,
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["expected_min"], 1)

    def test_run_smoke_records_checksum_and_blocks_invalid_upload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "out"
            tft_path = Path(temp_dir) / "bad.tft"
            tft_path.write_bytes(b"not-a-real-tft")
            args = Namespace(
                file=str(tft_path),
                out_dir=str(out_dir),
                expect_json=None,
                expect=[],
                set_expect=[],
                upload=True,
                known_current=None,
                skip_if_identical=False,
                port="COM36",
                baud=9600,
                download_baud=921600,
                chunk_size=4096,
                timeout_ms=3000,
                prepare_delay_ms=1000,
                prepare_wait_ms=800,
                allow_unsafe_chunk_size=False,
                progress=False,
                post_upload_wait_s=0,
                select_page=None,
                restore_page=None,
                expected_page_id=0,
                capture=False,
            )

            with (
                patch("tools.live_tft_smoke.inspect_tft_checksum", side_effect=RuntimeError("bad checksum")),
                patch("tools.live_tft_smoke.upload_tft") as upload_tft,
                patch("tools.live_tft_smoke._run_serial_checks", return_value=[]),
            ):
                result = run_smoke(args)

        upload_tft.assert_not_called()
        self.assertFalse(result["checksum"]["valid"])
        self.assertEqual(result["checksum"]["error"], "bad checksum")
        self.assertTrue(result["summary"]["upload_blocked"])
        self.assertTrue(result["summary"]["serial_checks_skipped"])
        self.assertEqual(result["serial_checks"], [])
        self.assertFalse(result["summary"]["ok"])

    def test_run_smoke_blocks_upload_on_model_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "out"
            tft_path = Path(temp_dir) / "candidate.tft"
            tft_path.write_bytes(b"fake-tft")
            args = Namespace(
                file=str(tft_path),
                out_dir=str(out_dir),
                expect_json=None,
                expect=[],
                set_expect=[],
                upload=True,
                known_current=None,
                skip_if_identical=False,
                port="COM36",
                baud=9600,
                download_baud=921600,
                chunk_size=4096,
                timeout_ms=3000,
                prepare_delay_ms=1000,
                prepare_wait_ms=800,
                allow_unsafe_chunk_size=False,
                progress=False,
                post_upload_wait_s=0,
                select_page=None,
                restore_page=None,
                expected_page_id=0,
                capture=False,
                require_model="TJC8048X543_011C",
            )

            with (
                patch("tools.live_tft_smoke.inspect_tft_checksum", return_value={"valid": True}),
                patch(
                    "tools.live_tft_smoke.probe_serial_health",
                    return_value={
                        "summary": {
                            "model": "TJC8048X550_011",
                            "public_upload_ready": False,
                            "diagnosis": "connect returned model 'TJC8048X550_011', expected 'TJC8048X543_011C'",
                        },
                        "commands": [
                            {
                                "name": "connect",
                                "passed": True,
                                "response": {"details": {"model": "TJC8048X550_011"}},
                            }
                        ],
                    },
                ),
                patch("tools.live_tft_smoke.upload_tft") as upload_tft,
                patch("tools.live_tft_smoke._run_serial_checks", return_value=[]),
            ):
                result = run_smoke(args)

        upload_tft.assert_not_called()
        self.assertEqual(result["upload"]["reason"], "model_preflight_failed")
        self.assertEqual(result["model_preflight"]["required_model"], "TJC8048X543_011C")
        self.assertEqual(result["model_preflight"]["actual_model"], "TJC8048X550_011")
        self.assertFalse(result["summary"]["model_preflight_ok"])
        self.assertTrue(result["summary"]["upload_blocked"])
        self.assertTrue(result["summary"]["serial_checks_skipped"])
        self.assertFalse(result["summary"]["ok"])


if __name__ == "__main__":
    unittest.main()
