from __future__ import annotations

import io
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from usarthmi.cli import main
from usarthmi.serial_health import _classify_health


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


if __name__ == "__main__":
    unittest.main()
