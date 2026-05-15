from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from usarthmi.serial_health import probe_serial_health


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe TJC/USART HMI serial runtime health.")
    parser.add_argument("--port", required=True, help="Serial port, for example COM36")
    parser.add_argument("--baud", type=int, default=9600, help="Command baud rate")
    parser.add_argument("--timeout-ms", type=int, default=3000, help="Per-command timeout")
    parser.add_argument("--expected-model", help="Expected model, for example TJC8048X543_011C")
    parser.add_argument("--out", type=Path, help="Write JSON report to this path")
    args = parser.parse_args(argv)

    report = probe_serial_health(
        port=args.port,
        baud=args.baud,
        timeout_ms=args.timeout_ms,
        expected_model=args.expected_model,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["summary"]["healthy"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
