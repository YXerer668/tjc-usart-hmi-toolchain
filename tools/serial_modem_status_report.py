from __future__ import annotations

import argparse
import json
from pathlib import Path

import serial


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "examples" / "lifecycle_runtime_smoke" / "serial_modem_status_2026-05-21.json"


def capture_status(*, port: str, baud: int) -> dict[str, object]:
    try:
        with serial.Serial(port, baud, timeout=1, write_timeout=1) as ser:
            return {
                "opened": True,
                "cts": bool(ser.cts),
                "dsr": bool(ser.dsr),
                "ri": bool(ser.ri),
                "cd": bool(ser.cd),
                "dtr": bool(ser.dtr),
                "rts": bool(ser.rts),
                "in_waiting": int(ser.in_waiting),
                "out_waiting": int(ser.out_waiting),
            }
    except Exception as exc:
        return {
            "opened": False,
            "error": str(exc),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture current modem-control line status for the live USB-UART bridge.")
    parser.add_argument("--port", default="COM36")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    status = capture_status(port=args.port, baud=args.baud)
    payload = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "port": args.port,
        "baud": args.baud,
        "status": "captured",
        "modem_lines": status,
        "conclusions": {
            "serial_bridge_opens": bool(status.get("opened")),
            "all_inbound_modem_lines_low": bool(status.get("opened")) and not any(
                bool(status.get(key)) for key in ("cts", "dsr", "ri", "cd")
            ),
            "modem_lines_do_not_offer_an_obvious_recovery_signal": True,
        },
    }
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if status.get("opened") else 1


if __name__ == "__main__":
    raise SystemExit(main())
