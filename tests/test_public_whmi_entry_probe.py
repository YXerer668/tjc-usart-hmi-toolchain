from __future__ import annotations

import unittest

from tools.public_whmi_entry_probe import probe_public_whmi_entry


class _AckSerial:
    def __init__(self, *args, **kwargs) -> None:
        self._reads = [b"\x05", b""]
        self.baudrate = kwargs.get("baudrate", args[1] if len(args) > 1 else 9600)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def reset_input_buffer(self) -> None:
        pass

    def reset_output_buffer(self) -> None:
        pass

    def write(self, payload: bytes) -> None:
        pass

    def flush(self) -> None:
        pass

    def read(self, size: int = 1) -> bytes:
        return self._reads.pop(0) if self._reads else b""


class PublicWhmiEntryProbeTests(unittest.TestCase):
    def test_ack_probe_marks_entry_healthy(self) -> None:
        report = probe_public_whmi_entry(
            port="COM36",
            baud=9600,
            download_baud=921600,
            timeout_ms=10,
            prepare_delay_ms=0,
            prepare_wait_ms=0,
            serial_factory=_AckSerial,
        )
        self.assertTrue(report["ack_received"])
        self.assertTrue(report["healthy"])

    def test_probe_rejects_nonzero_payload_length(self) -> None:
        with self.assertRaisesRegex(Exception, "payload_len=0"):
            probe_public_whmi_entry(
                port="COM36",
                payload_len=1,
                serial_factory=_AckSerial,
            )


if __name__ == "__main__":
    unittest.main()
