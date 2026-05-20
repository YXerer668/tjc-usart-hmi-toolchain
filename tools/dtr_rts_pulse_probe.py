from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import serial


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usarthmi.serial_health import probe_serial_health


def pulse_lines(
    *,
    port: str,
    baud: int,
    timeout_ms: int,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    timeout_s = max(timeout_ms, 1) / 1000.0
    result: dict[str, Any] = {
        "port": port,
        "baud": baud,
        "timeout_ms": timeout_ms,
        "steps": [],
        "ok": False,
    }
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
            for step in steps:
                if step.get("dtr") is not None:
                    ser.dtr = bool(step["dtr"])
                if step.get("rts") is not None:
                    ser.rts = bool(step["rts"])
                delay_ms = int(step.get("delay_ms", 0))
                result["steps"].append(
                    {
                        "dtr": ser.dtr,
                        "rts": ser.rts,
                        "delay_ms": delay_ms,
                    }
                )
                if delay_ms > 0:
                    time.sleep(delay_ms / 1000.0)
        result["ok"] = True
    except serial.SerialException as exc:
        result["error"] = str(exc)
    return result


def run_probe(
    *,
    port: str,
    baud: int = 9600,
    timeout_ms: int = 2000,
    settle_ms: int = 500,
    expected_model: str | None = "TJC8048X543_011C",
) -> dict[str, Any]:
    before = probe_serial_health(port=port, baud=baud, timeout_ms=timeout_ms, expected_model=expected_model)
    pulse = pulse_lines(
        port=port,
        baud=baud,
        timeout_ms=timeout_ms,
        steps=[
            {"dtr": False, "rts": False, "delay_ms": 300},
            {"dtr": True, "rts": False, "delay_ms": 300},
            {"dtr": False, "rts": True, "delay_ms": 300},
            {"dtr": True, "rts": True, "delay_ms": 300},
            {"dtr": False, "rts": False, "delay_ms": settle_ms},
        ],
    )
    after = probe_serial_health(port=port, baud=baud, timeout_ms=timeout_ms, expected_model=expected_model)
    report = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": expected_model,
        "status": "probed",
        "before": before,
        "pulse": pulse,
        "after": after,
        "conclusions": {
            "serial_became_responsive_after_pulse": bool(after["summary"]["healthy"]) or bool(after["summary"]["connect_ok"]),
            "no_change_after_pulse": before["commands"][0].get("response", {}).get("kind") == after["commands"][0].get("response", {}).get("kind")
            and before["commands"][1].get("response", {}).get("kind") == after["commands"][1].get("response", {}).get("kind")
            and before["commands"][2].get("response", {}).get("kind") == after["commands"][2].get("response", {}).get("kind"),
        },
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Pulse DTR/RTS on the live USB-UART bridge, then re-probe serial health.")
    parser.add_argument("--port", default="COM36")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--timeout-ms", type=int, default=2000)
    parser.add_argument("--settle-ms", type=int, default=500)
    parser.add_argument("--expected-model", default="TJC8048X543_011C")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = run_probe(
        port=args.port,
        baud=args.baud,
        timeout_ms=args.timeout_ms,
        settle_ms=args.settle_ms,
        expected_model=args.expected_model,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["conclusions"]["serial_became_responsive_after_pulse"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
