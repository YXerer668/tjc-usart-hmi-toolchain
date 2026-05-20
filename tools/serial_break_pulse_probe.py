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


def run_probe(
    *,
    port: str,
    baud: int = 9600,
    timeout_ms: int = 2000,
    expected_model: str | None = "TJC8048X543_011C",
    break_ms: int = 500,
    settle_ms: int = 800,
) -> dict[str, Any]:
    before = probe_serial_health(port=port, baud=baud, timeout_ms=timeout_ms, expected_model=expected_model)
    pulse: dict[str, Any] = {
        "port": port,
        "baud": baud,
        "break_ms": break_ms,
        "settle_ms": settle_ms,
        "ok": False,
    }
    timeout_s = max(timeout_ms, 1) / 1000.0
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
            pulse["break_condition_before"] = bool(ser.break_condition)
            ser.break_condition = True
            time.sleep(max(break_ms, 0) / 1000.0)
            ser.break_condition = False
            time.sleep(max(settle_ms, 0) / 1000.0)
            pulse["break_condition_after"] = bool(ser.break_condition)
            pulse["ok"] = True
    except Exception as exc:
        pulse["error"] = str(exc)
    after = probe_serial_health(port=port, baud=baud, timeout_ms=timeout_ms, expected_model=expected_model)
    return {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": expected_model,
        "status": "probed",
        "port": port,
        "before": before,
        "pulse": pulse,
        "after": after,
        "conclusions": {
            "serial_became_responsive_after_break_pulse": bool(after["summary"]["healthy"]) or bool(after["summary"]["connect_ok"]),
            "no_change_after_break_pulse": before["commands"][0].get("response", {}).get("kind") == after["commands"][0].get("response", {}).get("kind")
            and before["commands"][1].get("response", {}).get("kind") == after["commands"][1].get("response", {}).get("kind")
            and before["commands"][2].get("response", {}).get("kind") == after["commands"][2].get("response", {}).get("kind"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Pulse TX BREAK on the live USB-UART bridge, then re-probe serial health.")
    parser.add_argument("--port", default="COM36")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--timeout-ms", type=int, default=2000)
    parser.add_argument("--break-ms", type=int, default=500)
    parser.add_argument("--settle-ms", type=int, default=800)
    parser.add_argument("--expected-model", default="TJC8048X543_011C")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = run_probe(
        port=args.port,
        baud=args.baud,
        timeout_ms=args.timeout_ms,
        expected_model=args.expected_model,
        break_ms=args.break_ms,
        settle_ms=args.settle_ms,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["conclusions"]["serial_became_responsive_after_break_pulse"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
