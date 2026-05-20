from __future__ import annotations

import unittest
from unittest.mock import patch

from tools.dtr_rts_pulse_probe import pulse_lines


class _FakeSerial:
    def __init__(self, *args, **kwargs) -> None:
        self.dtr = False
        self.rts = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def reset_input_buffer(self) -> None:
        pass

    def reset_output_buffer(self) -> None:
        pass


class DtrRtsPulseProbeTests(unittest.TestCase):
    def test_pulse_lines_records_step_states(self) -> None:
        with patch("tools.dtr_rts_pulse_probe.serial.Serial", _FakeSerial):
            report = pulse_lines(
                port="COM36",
                baud=9600,
                timeout_ms=1000,
                steps=[
                    {"dtr": False, "rts": False, "delay_ms": 0},
                    {"dtr": True, "rts": False, "delay_ms": 0},
                    {"dtr": False, "rts": True, "delay_ms": 0},
                ],
            )
        self.assertTrue(report["ok"])
        self.assertEqual(len(report["steps"]), 3)
        self.assertEqual(report["steps"][1]["dtr"], True)
        self.assertEqual(report["steps"][2]["rts"], True)


if __name__ == "__main__":
    unittest.main()
