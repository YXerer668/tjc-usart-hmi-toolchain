from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from usarthmi.transport import TERMINATOR
from usarthmi.tft_download import (
    PUBLIC_WHMI_CHUNK_SIZE,
    _wait_for_ack,
    _write_command,
    plan_upload,
    upload_tft,
)


class FakeSerial:
    def __init__(self) -> None:
        self.data = bytearray()

    def write(self, payload: bytes | str) -> None:
        if isinstance(payload, str):
            payload = payload.encode("ascii")
        self.data.extend(payload)


class EmptyReadSerial:
    def read(self, size: int = 1) -> bytes:
        return b""


class TftDownloadTests(unittest.TestCase):
    def test_write_command_adds_optional_address_and_terminator(self) -> None:
        ser = FakeSerial()
        _write_command(ser, "connect", address=0x1234)  # type: ignore[arg-type]
        self.assertEqual(bytes(ser.data), b"\x34\x12connect" + TERMINATOR)

    def test_plan_upload_compares_4096_byte_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            baseline = root / "baseline.tft"
            candidate = root / "candidate.tft"
            baseline.write_bytes(b"A" * 4096 + b"B" * 4096 + b"\xFF" * 4096)
            candidate.write_bytes(b"A" * 4096 + b"C" * 4096 + b"\xFF" * 4096)

            plan = plan_upload(candidate, baseline_path=baseline, chunk_size=4096, download_baud=40960)
            data = plan.to_dict()

            self.assertEqual(data["total_chunks"], 3)
            self.assertEqual(data["identical_chunks"], 2)
            self.assertEqual(data["different_chunks"], 1)
            self.assertEqual(data["identical_bytes"], 8192)
            self.assertEqual(data["identical_prefix_bytes"], 4096)
            self.assertFalse(data["identical_full_file"])
            self.assertEqual(data["changed_range_count"], 1)
            self.assertEqual(data["changed_bytes"], 4096)
            self.assertEqual(data["sparse_candidate_ratio"], 0.333333)
            self.assertEqual(data["candidate_truncated_bytes"], 0)
            self.assertEqual(
                data["changed_ranges"],
                [
                    {
                        "start": 4096,
                        "end": 8192,
                        "length": 4096,
                        "start_chunk": 1,
                        "end_chunk_exclusive": 2,
                    }
                ],
            )
            self.assertEqual(data["all_ff_chunks"], 1)
            self.assertTrue(data["public_whmi_wri_requires_full_stream"])
            self.assertFalse(data["sparse_chunk_upload_supported"])
            self.assertEqual(data["estimated_serial_min_s"], 3.0)

    def test_upload_skip_if_identical_returns_before_serial_open(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            known_current = root / "known_current.tft"
            candidate = root / "candidate.tft"
            payload = b"same TFT bytes"
            known_current.write_bytes(payload)
            candidate.write_bytes(payload)

            result = upload_tft(
                candidate,
                port="COM_SHOULD_NOT_BE_OPENED",
                known_current=known_current,
                skip_if_identical=True,
            ).to_dict()

            self.assertTrue(result["skipped"])
            self.assertEqual(result["bytes_sent"], 0)
            self.assertEqual(result["chunks_sent"], 0)
            self.assertEqual(result["known_current_file_size"], len(payload))
            self.assertIn("upload skipped", result["skip_reason"])
            self.assertEqual(result["public_whmi_chunk_size"], PUBLIC_WHMI_CHUNK_SIZE)

    def test_upload_rejects_non_4096_chunk_size_before_serial_open(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate = Path(temp_dir) / "candidate.tft"
            candidate.write_bytes(b"not actually uploaded")

            with self.assertRaisesRegex(Exception, "Unsupported chunk_size=2048"):
                upload_tft(
                    candidate,
                    port="COM_SHOULD_NOT_BE_OPENED",
                    chunk_size=2048,
                )

    def test_initial_whmi_ack_timeout_explains_runtime_wedge(self) -> None:
        with self.assertRaisesRegex(Exception, "runtime commands such as sendme/get dim do not respond"):
            _wait_for_ack(EmptyReadSerial(), 0.001, "initial whmi-wri ack")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
