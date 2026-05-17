from __future__ import annotations

import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from usarthmi.cli import main
from usarthmi.serial_health import _classify_health
from usarthmi.tft_download import write_last_upload_manifest


def command_result(name: str, kind: str, *, passed: bool = True, model: str | None = None) -> dict:
    response = {"kind": kind}
    if name == "connect" and model is not None:
        response["details"] = {"model": model}
    return {"name": name, "response": response, "passed": passed}


class TJCSerialHealthTests(unittest.TestCase):
    def test_classifies_connect_only_state_as_not_upload_ready(self) -> None:
        summary = _classify_health(
            [
                command_result("connect", "connect", model="TJC8048X543_011C"),
                command_result("sendme", "none", passed=False),
                command_result("get_dim", "none", passed=False),
            ],
            expected_model="TJC8048X543_011C",
        )

        self.assertTrue(summary["connect_ok"])
        self.assertFalse(summary["runtime_ok"])
        self.assertFalse(summary["public_upload_ready"])
        self.assertIn("runtime commands do not respond", summary["diagnosis"])

    def test_classifies_healthy_runtime(self) -> None:
        summary = _classify_health(
            [
                command_result("connect", "connect", model="TJC8048X543_011C"),
                command_result("sendme", "page_id"),
                command_result("get_dim", "number"),
            ],
            expected_model="TJC8048X543_011C",
        )

        self.assertTrue(summary["healthy"])
        self.assertTrue(summary["public_upload_ready"])

    def test_blocks_wrong_model(self) -> None:
        summary = _classify_health(
            [
                command_result("connect", "connect", model="TJC8048X550_011"),
                command_result("sendme", "page_id"),
                command_result("get_dim", "number"),
            ],
            expected_model="TJC8048X543_011C",
        )

        self.assertFalse(summary["connect_ok"])
        self.assertFalse(summary["public_upload_ready"])
        self.assertIn("expected", summary["diagnosis"])

    def test_cli_health_returns_nonzero_when_unhealthy(self) -> None:
        report = {
            "summary": {"healthy": False},
            "commands": [],
        }
        with patch("usarthmi.cli.probe_serial_health", return_value=report), patch(
            "sys.stdout", new_callable=io.StringIO
        ):
            code = main(
                [
                    "--json",
                    "tft",
                    "health",
                    "--port",
                    "COM36",
                    "--expected-model",
                    "TJC8048X543_011C",
                ]
            )

        self.assertEqual(code, 1)

    def test_cli_upload_preflight_blocks_unhealthy_runtime(self) -> None:
        report = {
            "summary": {
                "public_upload_ready": False,
                "connect_ok": True,
                "runtime_ok": False,
                "model": "TJC8048X543_011C",
                "diagnosis": "runtime commands do not respond",
            },
            "commands": [],
        }
        checksum = {"valid": True, "stored_hex": "0x11111111", "calculated_hex": "0x11111111"}
        with patch("usarthmi.cli.inspect_tft_checksum", return_value=checksum), patch(
            "usarthmi.cli.probe_serial_health", return_value=report
        ), patch("usarthmi.cli.upload_tft") as upload_mock, patch("sys.stdout", new_callable=io.StringIO):
            code = main(
                [
                    "--json",
                    "tft",
                    "upload",
                    "--file",
                    "candidate.tft",
                    "--port",
                    "COM36",
                ]
            )

        self.assertEqual(code, 2)
        upload_mock.assert_not_called()

    def test_cli_preflight_combines_checksum_and_serial_health(self) -> None:
        checksum = {"valid": True, "stored_hex": "0x11111111", "calculated_hex": "0x11111111"}
        health = {
            "summary": {
                "public_upload_ready": False,
                "diagnosis": "runtime commands do not respond",
            },
            "commands": [],
        }
        with patch("usarthmi.cli.inspect_tft_checksum", return_value=checksum), patch(
            "usarthmi.cli.probe_serial_health", return_value=health
        ), patch("sys.stdout", new_callable=io.StringIO):
            code = main(
                [
                    "--json",
                    "tft",
                    "preflight",
                    "--file",
                    "candidate.tft",
                    "--port",
                    "COM36",
                    "--expected-model",
                    "TJC8048X543_011C",
                ]
            )

        self.assertEqual(code, 1)

    def test_cli_upload_preflight_blocks_invalid_checksum(self) -> None:
        checksum = {"valid": False, "stored_hex": "0x11111111", "calculated_hex": "0x22222222"}
        with patch("usarthmi.cli.inspect_tft_checksum", return_value=checksum), patch(
            "usarthmi.cli.upload_tft", return_value=SimpleNamespace(to_dict=lambda: {"uploaded": True})
        ) as upload_mock, patch("sys.stdout", new_callable=io.StringIO):
            code = main(
                [
                    "--json",
                    "tft",
                    "upload",
                    "--file",
                    "candidate.tft",
                    "--port",
                    "COM36",
                ]
            )

        self.assertEqual(code, 2)
        upload_mock.assert_not_called()

    def test_cli_upload_can_explicitly_skip_default_preflight(self) -> None:
        with patch("usarthmi.cli.inspect_tft_checksum") as checksum_mock, patch(
            "usarthmi.cli.probe_serial_health"
        ) as health_mock, patch(
            "usarthmi.cli.upload_tft", return_value=SimpleNamespace(to_dict=lambda: {"uploaded": True})
        ) as upload_mock, patch("sys.stdout", new_callable=io.StringIO):
            code = main(
                [
                    "--json",
                    "tft",
                    "upload",
                    "--file",
                    "candidate.tft",
                    "--port",
                    "COM36",
                    "--no-preflight",
                ]
            )

        self.assertEqual(code, 0)
        checksum_mock.assert_not_called()
        health_mock.assert_not_called()
        upload_mock.assert_called_once()

    def test_cli_upload_skip_if_current_returns_before_runtime_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = root / "candidate.tft"
            manifest = root / ".usarthmi_last_upload.json"
            candidate.write_bytes(b"already uploaded")
            write_last_upload_manifest(
                candidate,
                manifest_path=manifest,
                port="COM36",
                baud=9600,
                download_baud=921600,
                chunk_size=4096,
                target_model="TJC8048X543_011C",
                tool_version="test",
            )
            checksum = {"valid": True, "stored_hex": "0x11111111", "calculated_hex": "0x11111111"}
            with patch("usarthmi.cli.inspect_tft_checksum", return_value=checksum), patch(
                "usarthmi.cli.probe_serial_health"
            ) as health_mock, patch("usarthmi.cli.upload_tft") as upload_mock, patch(
                "sys.stdout", new_callable=io.StringIO
            ) as stdout:
                code = main(
                    [
                        "--json",
                        "tft",
                        "upload",
                        "--file",
                        str(candidate),
                        "--port",
                        "COM36",
                        "--skip-if-current",
                        "--current-manifest",
                        str(manifest),
                    ]
                )

        result = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertTrue(result["skipped"])
        self.assertTrue(result["skip_current_manifest"]["skip"])
        self.assertEqual(result["bytes_sent"], 0)
        health_mock.assert_not_called()
        upload_mock.assert_not_called()

    def test_cli_upload_records_current_manifest_after_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = root / "candidate.tft"
            manifest = root / ".usarthmi_last_upload.json"
            candidate.write_bytes(b"new upload")
            checksum = {"valid": True, "stored_hex": "0x11111111", "calculated_hex": "0x11111111"}
            health = {
                "summary": {
                    "public_upload_ready": True,
                    "connect_ok": True,
                    "runtime_ok": True,
                    "model": "TJC8048X543_011C",
                    "diagnosis": "ready",
                },
                "commands": [],
            }
            upload_result = {
                "file_path": str(candidate.resolve()),
                "file_size": candidate.stat().st_size,
                "bytes_sent": candidate.stat().st_size,
                "chunks_sent": 1,
                "skipped": False,
            }
            with patch("usarthmi.cli.inspect_tft_checksum", return_value=checksum), patch(
                "usarthmi.cli.probe_serial_health", return_value=health
            ), patch(
                "usarthmi.cli.upload_tft", return_value=SimpleNamespace(to_dict=lambda: dict(upload_result))
            ), patch("sys.stdout", new_callable=io.StringIO) as stdout:
                code = main(
                    [
                        "--json",
                        "tft",
                        "upload",
                        "--file",
                        str(candidate),
                        "--port",
                        "COM36",
                        "--current-manifest",
                        str(manifest),
                    ]
                )

            result = json.loads(stdout.getvalue())
            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(code, 0)
            self.assertIn("last_upload_manifest", result)
            self.assertEqual(data["tft_size"], candidate.stat().st_size)
            self.assertEqual(data["port"], "COM36")
            self.assertEqual(data["target_model"], "TJC8048X543_011C")

    def test_cli_upload_runs_post_upload_verification_before_recording_current(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = root / "candidate.tft"
            manifest = root / ".usarthmi_last_upload.json"
            candidate.write_bytes(b"new upload")
            checksum = {"valid": True, "stored_hex": "0x11111111", "calculated_hex": "0x11111111"}
            health = {
                "summary": {
                    "public_upload_ready": True,
                    "connect_ok": True,
                    "runtime_ok": True,
                    "model": "TJC8048X543_011C",
                    "diagnosis": "ready",
                },
                "commands": [],
            }
            upload_result = {
                "file_path": str(candidate.resolve()),
                "file_size": candidate.stat().st_size,
                "bytes_sent": candidate.stat().st_size,
                "chunks_sent": 1,
                "skipped": False,
            }
            verification = {
                "summary": {"ok": False, "serial_health_ok": True, "get_checks_ok": False},
                "get_checks": [{"target": "t0.txt", "ok": False}],
            }
            with patch("usarthmi.cli.inspect_tft_checksum", return_value=checksum), patch(
                "usarthmi.cli.probe_serial_health", return_value=health
            ), patch(
                "usarthmi.cli.upload_tft", return_value=SimpleNamespace(to_dict=lambda: dict(upload_result))
            ), patch("usarthmi.cli._run_post_upload_verification", return_value=verification), patch(
                "sys.stdout", new_callable=io.StringIO
            ) as stdout:
                code = main(
                    [
                        "--json",
                        "tft",
                        "upload",
                        "--file",
                        str(candidate),
                        "--port",
                        "COM36",
                        "--current-manifest",
                        str(manifest),
                        "--verify-after-upload",
                        "--verify-get",
                        "t0.txt=nihao",
                    ]
                )

            result = json.loads(stdout.getvalue())
            self.assertEqual(code, 1)
            self.assertFalse(manifest.exists())
            self.assertFalse(result["post_upload_verification"]["summary"]["ok"])
            self.assertNotIn("last_upload_manifest", result)

    def test_cli_upload_skip_if_current_can_still_verify_live_screen(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = root / "candidate.tft"
            manifest = root / ".usarthmi_last_upload.json"
            candidate.write_bytes(b"already uploaded")
            write_last_upload_manifest(
                candidate,
                manifest_path=manifest,
                port="COM36",
                baud=9600,
                download_baud=921600,
                chunk_size=4096,
                target_model="TJC8048X543_011C",
                tool_version="test",
            )
            checksum = {"valid": True, "stored_hex": "0x11111111", "calculated_hex": "0x11111111"}
            verification = {
                "summary": {"ok": True, "serial_health_ok": True, "get_checks_ok": True},
                "get_checks": [{"target": "t0.txt", "ok": True}],
            }
            with patch("usarthmi.cli.inspect_tft_checksum", return_value=checksum), patch(
                "usarthmi.cli._run_post_upload_verification", return_value=verification
            ) as verify_mock, patch("usarthmi.cli.upload_tft") as upload_mock, patch(
                "sys.stdout", new_callable=io.StringIO
            ) as stdout:
                code = main(
                    [
                        "--json",
                        "tft",
                        "upload",
                        "--file",
                        str(candidate),
                        "--port",
                        "COM36",
                        "--skip-if-current",
                        "--current-manifest",
                        str(manifest),
                        "--verify-after-upload",
                    ]
                )

            result = json.loads(stdout.getvalue())
            self.assertEqual(code, 0)
            self.assertTrue(result["skipped"])
            self.assertTrue(result["post_upload_verification"]["summary"]["ok"])
            verify_mock.assert_called_once()
            upload_mock.assert_not_called()

    def test_cli_upload_skip_if_current_can_capture_post_verify_frame(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = root / "candidate.tft"
            manifest = root / ".usarthmi_last_upload.json"
            capture = root / "screen.jpg"
            candidate.write_bytes(b"already uploaded")
            write_last_upload_manifest(
                candidate,
                manifest_path=manifest,
                port="COM36",
                baud=9600,
                download_baud=921600,
                chunk_size=4096,
                target_model="TJC8048X543_011C",
                tool_version="test",
            )
            checksum = {"valid": True, "stored_hex": "0x11111111", "calculated_hex": "0x11111111"}
            health = {
                "summary": {
                    "healthy": True,
                    "public_upload_ready": True,
                    "connect_ok": True,
                    "runtime_ok": True,
                    "model": "TJC8048X543_011C",
                    "diagnosis": "ready",
                },
                "commands": [],
            }

            def fake_capture_run(command, **_kwargs):  # type: ignore[no-untyped-def]
                self.assertIn("--backend", command)
                self.assertIn("msmf", command)
                capture.write_bytes(b"jpg")
                return SimpleNamespace(
                    returncode=0,
                    stdout=json.dumps({"path": str(capture), "bytes": 3}),
                    stderr="",
                )

            with patch("usarthmi.cli.inspect_tft_checksum", return_value=checksum), patch(
                "usarthmi.cli.probe_serial_health", return_value=health
            ), patch("usarthmi.cli.subprocess.run", fake_capture_run), patch(
                "usarthmi.cli.upload_tft"
            ) as upload_mock, patch("sys.stdout", new_callable=io.StringIO) as stdout:
                code = main(
                    [
                        "--json",
                        "tft",
                        "upload",
                        "--file",
                        str(candidate),
                        "--port",
                        "COM36",
                        "--skip-if-current",
                        "--current-manifest",
                        str(manifest),
                        "--verify-after-upload",
                        "--verify-capture",
                        "--verify-capture-output",
                        str(capture),
                    ]
                )

            result = json.loads(stdout.getvalue())
            self.assertEqual(code, 0)
            self.assertTrue(result["post_upload_verification"]["summary"]["camera_captured"])
            self.assertEqual(result["post_upload_verification"]["camera"]["bytes"], 3)
            upload_mock.assert_not_called()

    def test_cli_upload_skip_if_current_can_run_runtime_verify_steps(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = root / "candidate.tft"
            manifest = root / ".usarthmi_last_upload.json"
            candidate.write_bytes(b"already uploaded")
            write_last_upload_manifest(
                candidate,
                manifest_path=manifest,
                port="COM36",
                baud=9600,
                download_baud=921600,
                chunk_size=4096,
                target_model="TJC8048X543_011C",
                tool_version="test",
            )
            checksum = {"valid": True, "stored_hex": "0x11111111", "calculated_hex": "0x11111111"}
            health = {
                "summary": {
                    "healthy": True,
                    "public_upload_ready": True,
                    "connect_ok": True,
                    "runtime_ok": True,
                    "model": "TJC8048X543_011C",
                    "diagnosis": "ready",
                },
                "commands": [],
            }
            calls = []

            class FakeTransport:
                def __init__(self, _config):  # type: ignore[no-untyped-def]
                    pass

                def transact(self, command):  # type: ignore[no-untyped-def]
                    calls.append(command)
                    if command == "sendme":
                        return b"sendme\xff\xff\xff", bytes.fromhex("66 00 ff ff ff")
                    if command == "get t0.txt":
                        return b"get t0.txt\xff\xff\xff", b"\x70nihao\xff\xff\xff"
                    return command.encode("ascii") + b"\xff\xff\xff", b""

            with patch("usarthmi.cli.inspect_tft_checksum", return_value=checksum), patch(
                "usarthmi.cli.probe_serial_health", return_value=health
            ), patch("usarthmi.cli.SerialTransport", FakeTransport), patch(
                "usarthmi.cli.upload_tft"
            ) as upload_mock, patch("sys.stdout", new_callable=io.StringIO) as stdout:
                code = main(
                    [
                        "--json",
                        "tft",
                        "upload",
                        "--file",
                        str(candidate),
                        "--port",
                        "COM36",
                        "--skip-if-current",
                        "--current-manifest",
                        str(manifest),
                        "--verify-after-upload",
                        "--verify-step",
                        '{"command":"sendme","expected_kind":"page_id","expected_value":0}',
                        "--verify-step",
                        '{"command":"get t0.txt","expected_kind":"string","expected_value":"nihao"}',
                    ]
                )

            result = json.loads(stdout.getvalue())
            self.assertEqual(code, 0)
            self.assertTrue(result["post_upload_verification"]["summary"]["runtime_steps_ok"])
            self.assertEqual(calls, ["sendme", "get t0.txt"])
            self.assertEqual(result["post_upload_verification"]["runtime_steps"][0]["response"]["kind"], "page_id")
            self.assertEqual(result["post_upload_verification"]["runtime_steps"][1]["response"]["value"], "nihao")
            upload_mock.assert_not_called()

    def test_cli_upload_runtime_verify_step_shorthand_asserts_get_and_hex(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = root / "candidate.tft"
            manifest = root / ".usarthmi_last_upload.json"
            candidate.write_bytes(b"already uploaded")
            write_last_upload_manifest(
                candidate,
                manifest_path=manifest,
                port="COM36",
                baud=9600,
                download_baud=921600,
                chunk_size=4096,
                target_model="TJC8048X543_011C",
                tool_version="test",
            )
            checksum = {"valid": True, "stored_hex": "0x11111111", "calculated_hex": "0x11111111"}
            health = {
                "summary": {
                    "healthy": True,
                    "public_upload_ready": True,
                    "connect_ok": True,
                    "runtime_ok": True,
                    "model": "TJC8048X543_011C",
                    "diagnosis": "ready",
                },
                "commands": [],
            }

            class FakeTransport:
                def __init__(self, _config):  # type: ignore[no-untyped-def]
                    pass

                def transact(self, command):  # type: ignore[no-untyped-def]
                    if command == "get numval.val":
                        return b"get numval.val\xff\xff\xff", bytes.fromhex("71 7c 00 00 00 ff ff ff")
                    if command == "click incbtn,1":
                        return b"click incbtn,1\xff\xff\xff", bytes.fromhex("23 02 4e 31")
                    return command.encode("ascii") + b"\xff\xff\xff", b""

            with patch("usarthmi.cli.inspect_tft_checksum", return_value=checksum), patch(
                "usarthmi.cli.probe_serial_health", return_value=health
            ), patch("usarthmi.cli.SerialTransport", FakeTransport), patch(
                "usarthmi.cli.upload_tft"
            ) as upload_mock, patch("sys.stdout", new_callable=io.StringIO) as stdout:
                code = main(
                    [
                        "--json",
                        "tft",
                        "upload",
                        "--file",
                        str(candidate),
                        "--port",
                        "COM36",
                        "--skip-if-current",
                        "--current-manifest",
                        str(manifest),
                        "--verify-after-upload",
                        "--verify-step",
                        "get numval.val => 124",
                        "--verify-step",
                        "click incbtn,1 => hex:23 02 4e 31",
                    ]
                )

            result = json.loads(stdout.getvalue())
            self.assertEqual(code, 0)
            steps = result["post_upload_verification"]["runtime_steps"]
            self.assertEqual(steps[0]["expected_kind"], "number")
            self.assertEqual(steps[0]["expected_value"], 124)
            self.assertEqual(steps[1]["expected_hex"], "23 02 4e 31")
            self.assertTrue(result["post_upload_verification"]["summary"]["runtime_steps_ok"])
            upload_mock.assert_not_called()

    def test_cli_upload_post_verify_retries_transient_serial_health_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = root / "candidate.tft"
            manifest = root / ".usarthmi_last_upload.json"
            candidate.write_bytes(b"already uploaded")
            write_last_upload_manifest(
                candidate,
                manifest_path=manifest,
                port="COM36",
                baud=9600,
                download_baud=921600,
                chunk_size=4096,
                target_model="TJC8048X543_011C",
                tool_version="test",
            )
            checksum = {"valid": True, "stored_hex": "0x11111111", "calculated_hex": "0x11111111"}
            transient = {
                "summary": {
                    "healthy": False,
                    "public_upload_ready": False,
                    "connect_ok": False,
                    "runtime_ok": True,
                    "model": None,
                    "diagnosis": "connect did not return comok",
                },
                "commands": [],
            }
            recovered = {
                "summary": {
                    "healthy": True,
                    "public_upload_ready": True,
                    "connect_ok": True,
                    "runtime_ok": True,
                    "model": "TJC8048X543_011C",
                    "diagnosis": "ready",
                },
                "commands": [],
            }

            with patch("usarthmi.cli.inspect_tft_checksum", return_value=checksum), patch(
                "usarthmi.cli.probe_serial_health", side_effect=[transient, recovered]
            ) as health_mock, patch("usarthmi.cli.upload_tft") as upload_mock, patch(
                "sys.stdout", new_callable=io.StringIO
            ) as stdout:
                code = main(
                    [
                        "--json",
                        "tft",
                        "upload",
                        "--file",
                        str(candidate),
                        "--port",
                        "COM36",
                        "--skip-if-current",
                        "--current-manifest",
                        str(manifest),
                        "--verify-after-upload",
                        "--verify-wait-ms",
                        "0",
                        "--verify-health-attempts",
                        "2",
                        "--verify-health-retry-delay-ms",
                        "0",
                    ]
                )

            result = json.loads(stdout.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual(health_mock.call_count, 2)
            serial_health = result["post_upload_verification"]["serial_health"]
            self.assertEqual(serial_health["attempt"], 2)
            self.assertEqual(serial_health["retry_history"][0]["summary"]["connect_ok"], False)
            self.assertTrue(result["post_upload_verification"]["summary"]["serial_health_ok"])
            upload_mock.assert_not_called()

    def test_cli_upload_runtime_verify_step_failure_fails_post_verify(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = root / "candidate.tft"
            manifest = root / ".usarthmi_last_upload.json"
            candidate.write_bytes(b"new upload")
            checksum = {"valid": True, "stored_hex": "0x11111111", "calculated_hex": "0x11111111"}
            health = {
                "summary": {
                    "healthy": True,
                    "public_upload_ready": True,
                    "connect_ok": True,
                    "runtime_ok": True,
                    "model": "TJC8048X543_011C",
                    "diagnosis": "ready",
                },
                "commands": [],
            }
            upload_result = {
                "file_path": str(candidate.resolve()),
                "file_size": candidate.stat().st_size,
                "bytes_sent": candidate.stat().st_size,
                "chunks_sent": 1,
                "skipped": False,
            }

            class FakeTransport:
                def __init__(self, _config):  # type: ignore[no-untyped-def]
                    pass

                def transact(self, command):  # type: ignore[no-untyped-def]
                    return command.encode("ascii") + b"\xff\xff\xff", b"\x70wrong\xff\xff\xff"

            with patch("usarthmi.cli.inspect_tft_checksum", return_value=checksum), patch(
                "usarthmi.cli.probe_serial_health", return_value=health
            ), patch("usarthmi.cli.upload_tft", return_value=SimpleNamespace(to_dict=lambda: dict(upload_result))), patch(
                "usarthmi.cli.SerialTransport", FakeTransport
            ), patch("sys.stdout", new_callable=io.StringIO) as stdout:
                code = main(
                    [
                        "--json",
                        "tft",
                        "upload",
                        "--file",
                        str(candidate),
                        "--port",
                        "COM36",
                        "--current-manifest",
                        str(manifest),
                        "--verify-after-upload",
                        "--verify-step",
                        '{"command":"get t0.txt","expected_kind":"string","expected_value":"nihao"}',
                    ]
                )

            result = json.loads(stdout.getvalue())
            self.assertEqual(code, 1)
            self.assertFalse(result["post_upload_verification"]["summary"]["runtime_steps_ok"])
            self.assertFalse(result["post_upload_verification"]["summary"]["ok"])
            self.assertFalse(manifest.exists())


if __name__ == "__main__":
    unittest.main()
