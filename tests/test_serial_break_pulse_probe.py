from __future__ import annotations

import unittest
from unittest.mock import patch

from tools.serial_break_pulse_probe import run_probe


class _FakeSerial:
    def __init__(self, *args, **kwargs) -> None:
        self.break_condition = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class SerialBreakPulseProbeTests(unittest.TestCase):
    def test_break_pulse_reports_no_change_when_health_same(self) -> None:
        fake_health = {
            "summary": {"healthy": False, "connect_ok": False},
            "commands": [
                {"response": {"kind": "none"}},
                {"response": {"kind": "none"}},
                {"response": {"kind": "none"}},
            ],
        }
        with (
            patch("tools.serial_break_pulse_probe.probe_serial_health", side_effect=[fake_health, fake_health]),
            patch("tools.serial_break_pulse_probe.serial.Serial", _FakeSerial),
        ):
            report = run_probe(port="COM36")
        self.assertFalse(report["conclusions"]["serial_became_responsive_after_break_pulse"])
        self.assertTrue(report["conclusions"]["no_change_after_break_pulse"])


if __name__ == "__main__":
    unittest.main()
