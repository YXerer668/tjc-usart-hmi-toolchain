from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
import sys
from typing import Any, Callable

import serial


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usarthmi.tft_download import _wait_for_ack, _write_command
from usarthmi.transport import SerialTransportError


def probe_public_whmi_entry(
    *,
    port: str,
    baud: int = 9600,
    download_baud: int = 921600,
    timeout_ms: int = 3000,
    prepare_delay_ms: int = 2500,
    prepare_wait_ms: int = 1500,
    payload_len: int = 0,
    res0: str = "0",
    serial_factory: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    if payload_len != 0:
        raise SerialTransportError("public whmi entry probe only supports payload_len=0 for low-risk probing")
    timeout_s = max(timeout_ms, 1) / 1000.0
    serial_factory = serial_factory or serial.Serial
    started = time.monotonic()
    result: dict[str, Any] = {
        "port": port,
        "baud": baud,
        "download_baud": download_baud,
        "timeout_ms": timeout_ms,
        "prepare_delay_ms": prepare_delay_ms,
        "prepare_wait_ms": prepare_wait_ms,
        "payload_len": payload_len,
        "res0": res0,
        "ack_received": False,
    }
    try:
        with serial_factory(
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
                _write_command(ser, f"delay={prepare_delay_ms}")
                ser.flush()
                time.sleep(max(prepare_wait_ms, 0) / 1000.0)

            _write_command(ser, "\0")
            ser.flush()
            time.sleep(0.02)
            ser.reset_input_buffer()

            command = f"whmi-wri {payload_len},{download_baud},{res0}"
            result["command"] = command
            _write_command(ser, command)
            ser.flush()

            time.sleep(0.08)
            if baud != download_baud:
                ser.baudrate = download_baud
            time.sleep(0.05)

            _wait_for_ack(ser, timeout_s, "initial whmi-wri ack")
            result["ack_received"] = True
            trailing = ser.read(16)
            result["trailing_hex"] = trailing.hex(" ") if trailing else ""
    except (serial.SerialException, SerialTransportError) as exc:
        result["error"] = str(exc)

    result["elapsed_s"] = round(time.monotonic() - started, 3)
    result["healthy"] = bool(result["ack_received"])
    if result["ack_received"]:
        result["diagnosis"] = "public whmi-wri initial ack is reachable; runtime silence is more specific than full public upload-entry silence"
    else:
        result["diagnosis"] = "public whmi-wri initial ack did not appear; the panel is silent even at the public upload entrypoint"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe whether the public whmi-wri upload entry still returns its initial ACK without sending a TFT payload.")
    parser.add_argument("--port", default="COM36")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--download-baud", type=int, default=921600)
    parser.add_argument("--timeout-ms", type=int, default=3000)
    parser.add_argument("--prepare-delay-ms", type=int, default=2500)
    parser.add_argument("--prepare-wait-ms", type=int, default=1500)
    parser.add_argument("--payload-len", type=int, default=0)
    parser.add_argument("--res0", default="0")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = probe_public_whmi_entry(
        port=args.port,
        baud=args.baud,
        download_baud=args.download_baud,
        timeout_ms=args.timeout_ms,
        prepare_delay_ms=args.prepare_delay_ms,
        prepare_wait_ms=args.prepare_wait_ms,
        payload_len=args.payload_len,
        res0=args.res0,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["healthy"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
