from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import time

import serial

from .transport import TERMINATOR, SerialTransportError


PUBLIC_WHMI_CHUNK_SIZE = 4096
DEFAULT_DOWNLOAD_BAUD = 921600


@dataclass(slots=True)
class TftUploadResult:
    port: str
    initial_baud: int
    download_baud: int
    file_path: str
    file_size: int
    bytes_sent: int
    chunks_sent: int
    chunk_size: int
    elapsed_s: float
    address: int
    prepare_delay_ms: int
    prepare_wait_ms: int
    skipped: bool = False
    skip_reason: str | None = None
    known_current_path: str | None = None
    known_current_file_size: int | None = None
    warnings: list[str] | None = None

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "port": self.port,
            "initial_baud": self.initial_baud,
            "download_baud": self.download_baud,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "bytes_sent": self.bytes_sent,
            "chunks_sent": self.chunks_sent,
            "chunk_size": self.chunk_size,
            "elapsed_s": round(self.elapsed_s, 3),
            "address": self.address,
            "prepare_delay_ms": self.prepare_delay_ms,
            "prepare_wait_ms": self.prepare_wait_ms,
            "skipped": self.skipped,
            "public_whmi_chunk_size": PUBLIC_WHMI_CHUNK_SIZE,
        }
        if self.skip_reason is not None:
            result["skip_reason"] = self.skip_reason
        if self.known_current_path is not None:
            result["known_current_path"] = self.known_current_path
            result["known_current_file_size"] = self.known_current_file_size
        if self.warnings:
            result["warnings"] = self.warnings
        return result


@dataclass(slots=True)
class TftUploadPlan:
    file_path: str
    file_size: int
    chunk_size: int
    total_chunks: int
    download_baud: int
    estimated_serial_min_s: float
    all_ff_chunks: int
    all_zero_chunks: int
    baseline_path: str | None = None
    baseline_file_size: int | None = None
    identical_chunks: int | None = None
    different_chunks: int | None = None
    identical_bytes: int | None = None
    identical_ratio: float | None = None
    identical_prefix_bytes: int | None = None
    identical_full_file: bool | None = None
    changed_ranges: list[dict[str, int]] | None = None
    changed_range_count: int | None = None
    changed_bytes: int | None = None
    sparse_candidate_ratio: float | None = None
    candidate_truncated_bytes: int | None = None

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "file_path": self.file_path,
            "file_size": self.file_size,
            "chunk_size": self.chunk_size,
            "total_chunks": self.total_chunks,
            "download_baud": self.download_baud,
            "estimated_serial_min_s": round(self.estimated_serial_min_s, 3),
            "all_ff_chunks": self.all_ff_chunks,
            "all_zero_chunks": self.all_zero_chunks,
            "public_whmi_wri_requires_full_stream": True,
            "safe_whole_file_skip_supported": True,
            "sparse_chunk_upload_supported": False,
            "notes": [
                "The public whmi-wri protocol streams every byte of the TFT file.",
                "If the candidate file exactly matches a trusted known-current file, upload can be safely skipped before entering download mode.",
                "Identical chunk data is useful for reverse engineering or safety checks, but partial chunks cannot be skipped without a proven sparse-write protocol.",
            ],
        }
        if self.baseline_path is not None:
            result.update(
                {
                    "baseline_path": self.baseline_path,
                    "baseline_file_size": self.baseline_file_size,
                    "identical_chunks": self.identical_chunks,
                    "different_chunks": self.different_chunks,
                    "identical_bytes": self.identical_bytes,
                    "identical_ratio": round(self.identical_ratio or 0.0, 6),
                    "identical_prefix_bytes": self.identical_prefix_bytes,
                    "identical_full_file": self.identical_full_file,
                    "changed_range_count": self.changed_range_count,
                    "changed_bytes": self.changed_bytes,
                    "sparse_candidate_ratio": round(self.sparse_candidate_ratio or 0.0, 6),
                    "candidate_truncated_bytes": self.candidate_truncated_bytes,
                    "changed_ranges": self.changed_ranges or [],
                }
            )
        return result


def upload_tft(
    file_path: str | Path,
    *,
    port: str,
    baud: int = 9600,
    download_baud: int = DEFAULT_DOWNLOAD_BAUD,
    chunk_size: int = PUBLIC_WHMI_CHUNK_SIZE,
    timeout_ms: int = 3000,
    res0: str = "0",
    address: int = 0,
    prepare_delay_ms: int = 2500,
    prepare_wait_ms: int = 1500,
    known_current: str | Path | None = None,
    skip_if_identical: bool = False,
    allow_unsafe_chunk_size: bool = False,
    progress: Callable[[int, int, int], None] | None = None,
) -> TftUploadResult:
    source = Path(file_path).resolve()
    payload = source.read_bytes()
    if chunk_size <= 0:
        raise SerialTransportError("chunk_size must be positive")
    timeout_s = max(timeout_ms, 1) / 1000.0
    started = time.monotonic()
    known_current_path: str | None = None
    known_current_file_size: int | None = None

    if skip_if_identical and known_current is None:
        raise SerialTransportError("skip_if_identical requires a known_current file")

    if known_current is not None:
        current = Path(known_current).resolve()
        current_payload = current.read_bytes()
        known_current_path = str(current)
        known_current_file_size = len(current_payload)
        if skip_if_identical and current_payload == payload:
            return TftUploadResult(
                port=port,
                initial_baud=baud,
                download_baud=download_baud,
                file_path=str(source),
                file_size=len(payload),
                bytes_sent=0,
                chunks_sent=0,
                chunk_size=chunk_size,
                elapsed_s=time.monotonic() - started,
                address=address,
                prepare_delay_ms=prepare_delay_ms,
                prepare_wait_ms=prepare_wait_ms,
                skipped=True,
                skip_reason="candidate matches known-current file; upload skipped",
                known_current_path=known_current_path,
                known_current_file_size=known_current_file_size,
                warnings=_chunk_size_warnings(chunk_size),
            )

    if chunk_size != PUBLIC_WHMI_CHUNK_SIZE and not allow_unsafe_chunk_size:
        raise SerialTransportError(
            f"Unsupported chunk_size={chunk_size}. Current TJC/USART HMI public whmi-wri "
            f"handshake was verified with fixed {PUBLIC_WHMI_CHUNK_SIZE}-byte chunks; "
            "use --allow-unsafe-chunk-size only for deliberate reverse-engineering probes."
        )
    warnings = _chunk_size_warnings(chunk_size)

    try:
        with serial.Serial(
            port,
            baud,
            timeout=timeout_s,
            write_timeout=timeout_s,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
        ) as ser:
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            if prepare_delay_ms > 0:
                _write_command(ser, f"delay={prepare_delay_ms}", address)
                ser.flush()
                time.sleep(max(prepare_wait_ms, 0) / 1000.0)

            _write_command(ser, "\0", address)
            ser.flush()
            time.sleep(0.02)
            ser.reset_input_buffer()

            command = f"whmi-wri {len(payload)},{download_baud},{res0}"
            _write_command(ser, command, address)
            ser.flush()

            time.sleep(0.08)
            if baud != download_baud:
                ser.baudrate = download_baud
            time.sleep(0.05)

            _wait_for_ack(ser, timeout_s, "initial whmi-wri ack")

            chunks_sent = 0
            bytes_sent = 0
            for offset in range(0, len(payload), chunk_size):
                chunk = payload[offset : offset + chunk_size]
                ser.write(chunk)
                ser.flush()
                _wait_for_ack(
                    ser,
                    timeout_s,
                    f"chunk {chunks_sent} at offset {offset} size {len(chunk)}",
                )
                chunks_sent += 1
                bytes_sent += len(chunk)
                if progress is not None:
                    progress(bytes_sent, len(payload), chunks_sent)
    except serial.SerialException as exc:
        raise SerialTransportError(str(exc)) from exc

    return TftUploadResult(
        port=port,
        initial_baud=baud,
        download_baud=download_baud,
        file_path=str(source),
        file_size=len(payload),
        bytes_sent=bytes_sent,
        chunks_sent=chunks_sent,
        chunk_size=chunk_size,
        elapsed_s=time.monotonic() - started,
        address=address,
        prepare_delay_ms=prepare_delay_ms,
        prepare_wait_ms=prepare_wait_ms,
        known_current_path=known_current_path,
        known_current_file_size=known_current_file_size,
        warnings=warnings,
    )


def plan_upload(
    file_path: str | Path,
    *,
    baseline_path: str | Path | None = None,
    chunk_size: int = PUBLIC_WHMI_CHUNK_SIZE,
    download_baud: int = DEFAULT_DOWNLOAD_BAUD,
) -> TftUploadPlan:
    source = Path(file_path).resolve()
    payload = source.read_bytes()
    chunks = list(_iter_chunks(payload, chunk_size))
    all_ff_chunks = sum(1 for chunk in chunks if chunk and all(byte == 0xFF for byte in chunk))
    all_zero_chunks = sum(1 for chunk in chunks if chunk and all(byte == 0x00 for byte in chunk))
    plan = TftUploadPlan(
        file_path=str(source),
        file_size=len(payload),
        chunk_size=chunk_size,
        total_chunks=len(chunks),
        download_baud=download_baud,
        estimated_serial_min_s=(len(payload) * 10.0 / download_baud) if download_baud > 0 else 0.0,
        all_ff_chunks=all_ff_chunks,
        all_zero_chunks=all_zero_chunks,
    )

    if baseline_path is None:
        return plan

    baseline = Path(baseline_path).resolve()
    baseline_payload = baseline.read_bytes()
    baseline_chunks = list(_iter_chunks(baseline_payload, chunk_size))
    compared = min(len(chunks), len(baseline_chunks))
    identical_chunks = 0
    identical_bytes = 0
    for index in range(compared):
        if chunks[index] == baseline_chunks[index]:
            identical_chunks += 1
            identical_bytes += len(chunks[index])

    prefix_bytes = 0
    for left, right in zip(payload, baseline_payload):
        if left != right:
            break
        prefix_bytes += 1

    plan.baseline_path = str(baseline)
    plan.baseline_file_size = len(baseline_payload)
    plan.identical_chunks = identical_chunks
    plan.different_chunks = max(len(chunks), len(baseline_chunks)) - identical_chunks
    plan.identical_bytes = identical_bytes
    plan.identical_ratio = identical_bytes / len(payload) if payload else 1.0
    plan.identical_prefix_bytes = prefix_bytes
    plan.identical_full_file = payload == baseline_payload
    plan.changed_ranges, plan.changed_bytes = _changed_ranges(chunks, baseline_chunks, chunk_size)
    plan.changed_range_count = len(plan.changed_ranges)
    plan.sparse_candidate_ratio = plan.changed_bytes / len(payload) if payload else 0.0
    plan.candidate_truncated_bytes = max(0, len(baseline_payload) - len(payload))
    return plan


def _write_command(ser: serial.Serial, command: str, address: int = 0) -> None:
    if address:
        ser.write(bytes((address & 0xFF, (address >> 8) & 0xFF)))
    ser.write(command.encode("ascii") + TERMINATOR)


def _chunk_size_warnings(chunk_size: int) -> list[str]:
    if chunk_size == PUBLIC_WHMI_CHUNK_SIZE:
        return []
    return [
        f"chunk_size={chunk_size} is not the verified public whmi-wri ACK granularity; "
        f"use {PUBLIC_WHMI_CHUNK_SIZE} unless intentionally probing the bootloader."
    ]


def _iter_chunks(payload: bytes, chunk_size: int) -> list[bytes]:
    if chunk_size <= 0:
        raise SerialTransportError("chunk_size must be positive")
    return [payload[offset : offset + chunk_size] for offset in range(0, len(payload), chunk_size)]


def _changed_ranges(
    chunks: list[bytes],
    baseline_chunks: list[bytes],
    chunk_size: int,
) -> tuple[list[dict[str, int]], int]:
    changed_indices = [
        index
        for index, chunk in enumerate(chunks)
        if index >= len(baseline_chunks) or chunk != baseline_chunks[index]
    ]
    ranges: list[dict[str, int]] = []
    changed_bytes = 0
    range_start: int | None = None
    previous: int | None = None

    for index in changed_indices:
        if range_start is None:
            range_start = index
        elif previous is not None and index != previous + 1:
            changed_bytes += _append_changed_range(ranges, chunks, range_start, previous + 1, chunk_size)
            range_start = index
        previous = index

    if range_start is not None and previous is not None:
        changed_bytes += _append_changed_range(ranges, chunks, range_start, previous + 1, chunk_size)

    return ranges, changed_bytes


def _append_changed_range(
    ranges: list[dict[str, int]],
    chunks: list[bytes],
    start_chunk: int,
    end_chunk_exclusive: int,
    chunk_size: int,
) -> int:
    length = sum(len(chunks[index]) for index in range(start_chunk, end_chunk_exclusive))
    start = start_chunk * chunk_size
    end = start + length
    ranges.append(
        {
            "start": start,
            "end": end,
            "length": length,
            "start_chunk": start_chunk,
            "end_chunk_exclusive": end_chunk_exclusive,
        }
    )
    return length


def _wait_for_ack(ser: serial.Serial, timeout_s: float, label: str) -> None:
    deadline = time.monotonic() + timeout_s
    seen = bytearray()
    while time.monotonic() < deadline:
        data = ser.read(1)
        if not data:
            continue
        if data == b"\x05":
            return
        seen.extend(data)
    suffix = f"; saw {seen.hex(' ')}" if seen else ""
    raise SerialTransportError(f"Timed out waiting for {label}{suffix}")
