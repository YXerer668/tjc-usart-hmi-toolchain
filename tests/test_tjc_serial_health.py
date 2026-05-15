from __future__ import annotations

import unittest

from tools.tjc_serial_health import _classify_health


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


if __name__ == "__main__":
    unittest.main()
