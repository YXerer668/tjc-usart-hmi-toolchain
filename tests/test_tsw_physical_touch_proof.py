from __future__ import annotations

import argparse
import unittest
from unittest.mock import patch

from tools import tsw_physical_touch_proof as proof


class FakeSerial:
    def __init__(self) -> None:
        self.writes: list[bytes] = []

    def write(self, payload: bytes) -> None:
        self.writes.append(payload)

    def flush(self) -> None:
        pass


class SerialContext:
    def __init__(self) -> None:
        self.serial = FakeSerial()

    def __enter__(self) -> FakeSerial:
        return self.serial

    def __exit__(self, *args: object) -> None:
        pass


def args(**overrides: object) -> argparse.Namespace:
    defaults = {
        "port": "COM_TEST",
        "baud": 9600,
        "no_ack": False,
        "baseline_timeout_s": 0.01,
        "disabled_window_s": 0.01,
        "recovery_timeout_s": 0.01,
        "expect_title": "TSW PROMOTION",
        "skip_title_check": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class TswPhysicalTouchProofTests(unittest.TestCase):
    def test_decode_string_response_reads_gbk_title(self) -> None:
        value, encoding = proof.decode_string_response(b"\x70TSW PROMOTION\xff\xff\xff")

        self.assertEqual(value, "TSW PROMOTION")
        self.assertEqual(encoding, "gbk")

    def test_set_title_never_writes_or_refs_target_button(self) -> None:
        ser = FakeSerial()
        with patch.object(proof, "read_for", return_value=b""):
            proof.set_title(ser, "TRY TARGET")  # type: ignore[arg-type]

        sent = b"".join(ser.writes).decode("ascii", errors="replace")
        self.assertIn('title.txt="TRY TARGET"', sent)
        self.assertIn("ref title", sent)
        self.assertNotIn("targetbtn", sent)

    def test_no_user_confirmation_returns_before_opening_serial(self) -> None:
        with patch.object(proof, "run_ack", return_value={"ok": False, "result": "timeout"}), patch.object(
            proof.serial, "Serial"
        ) as serial_mock:
            report = proof.finalize_summary(proof.run_proof(args()))

        self.assertEqual(report["status"], "no_user_confirmation")
        self.assertFalse(report["summary"]["physical_touch_lockout_live_observed"])
        serial_mock.assert_not_called()

    def test_baseline_timeout_aborts_before_disable(self) -> None:
        serial_context = SerialContext()
        with patch.object(proof, "run_ack", return_value={"ok": True, "result": "continue"}), patch.object(
            proof.serial, "Serial", return_value=serial_context
        ), patch.object(proof, "read_for", return_value=b""), patch.object(
            proof, "read_title", return_value={"ok": True, "actual": "TSW PROMOTION"}
        ), patch.object(
            proof, "tap_button", return_value={"object": "enablebtn", "ok": True, "counts": {"T1": 1}}
        ) as tap_mock, patch.object(proof, "set_title") as title_mock, patch.object(
            proof,
            "wait_for_marker",
            return_value={
                "label": "baseline_enabled_wait_for_target",
                "counts": {"TG": 0, "T0": 0, "T1": 0},
            },
        ):
            report = proof.finalize_summary(proof.run_proof(args()))

        self.assertEqual(report["status"], "baseline_timeout")
        self.assertFalse(report["summary"]["physical_touch_lockout_live_observed"])
        self.assertEqual([call.args[1] for call in tap_mock.call_args_list], ["enablebtn"])
        self.assertEqual([call.args[1] for call in title_mock.call_args_list], ["TAP TARGET"])

    def test_wrong_page_aborts_before_releasing_or_disabling(self) -> None:
        serial_context = SerialContext()
        with patch.object(proof, "run_ack", return_value={"ok": True, "result": "continue"}), patch.object(
            proof.serial, "Serial", return_value=serial_context
        ), patch.object(proof, "read_for", return_value=b""), patch.object(
            proof, "read_title", return_value={"ok": False, "actual": "OTHER PAGE"}
        ), patch.object(proof, "tap_button") as tap_mock, patch.object(
            proof, "set_title"
        ) as title_mock:
            report = proof.finalize_summary(proof.run_proof(args()))

        self.assertEqual(report["status"], "wrong_page")
        self.assertFalse(report["summary"]["physical_touch_lockout_live_observed"])
        tap_mock.assert_not_called()
        title_mock.assert_not_called()

    def test_success_summary_requires_no_disabled_target_marker(self) -> None:
        serial_context = SerialContext()
        wait_results = [
            {
                "label": "baseline_enabled_wait_for_target",
                "counts": {"TG": 1, "T0": 0, "T1": 0},
            },
            {
                "label": "reenabled_wait_for_target",
                "counts": {"TG": 1, "T0": 0, "T1": 0},
            },
        ]
        with patch.object(proof, "run_ack", return_value={"ok": True, "result": "continue"}), patch.object(
            proof.serial, "Serial", return_value=serial_context
        ), patch.object(proof, "read_for", return_value=b""), patch.object(
            proof, "read_title", return_value={"ok": True, "actual": "TSW PROMOTION"}
        ), patch.object(
            proof,
            "tap_button",
            side_effect=[
                {"object": "enablebtn", "ok": True, "counts": {"T1": 1}},
                {"object": "disablebtn", "ok": True, "counts": {"T0": 1}},
                {"object": "enablebtn", "ok": True, "counts": {"T1": 1}},
            ],
        ), patch.object(proof, "set_title") as title_mock, patch.object(
            proof, "wait_for_marker", side_effect=wait_results
        ), patch.object(
            proof,
            "observe_window",
            return_value={"label": "disabled_try_target", "counts": {"TG": 0, "T0": 0, "T1": 0}},
        ):
            report = proof.finalize_summary(proof.run_proof(args()))

        self.assertEqual(report["status"], "completed")
        self.assertTrue(report["summary"]["physical_touch_lockout_live_observed"])
        self.assertEqual(
            [call.args[1] for call in title_mock.call_args_list],
            ["TAP TARGET", "TRY TARGET", "TAP AGAIN"],
        )


if __name__ == "__main__":
    unittest.main()
