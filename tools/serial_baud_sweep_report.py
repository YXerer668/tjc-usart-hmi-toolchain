from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usarthmi.serial_health import probe_serial_health


DEFAULT_OUT = ROOT / "examples" / "lifecycle_runtime_smoke" / "serial_baud_sweep_2026-05-21.json"
DEFAULT_BAUDS = [2400, 4800, 9600, 19200, 57600, 115200, 230400, 256000, 512000, 921600]


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe a TJC/USART HMI panel across common baud rates and record whether any command mode answers.")
    parser.add_argument("--port", default="COM36")
    parser.add_argument("--timeout-ms", type=int, default=2000)
    parser.add_argument("--expected-model", default="TJC8048X543_011C")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    rows = []
    for baud in DEFAULT_BAUDS:
        report = probe_serial_health(
            port=args.port,
            baud=baud,
            timeout_ms=args.timeout_ms,
            expected_model=args.expected_model,
        )
        rows.append(
            {
                "baud": baud,
                "connect_kind": report["commands"][0].get("response", {}).get("kind"),
                "sendme_kind": report["commands"][1].get("response", {}).get("kind"),
                "get_dim_kind": report["commands"][2].get("response", {}).get("kind"),
                "healthy": report["summary"]["healthy"],
                "diagnosis": report["summary"]["diagnosis"],
            }
        )

    payload = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": args.expected_model,
        "port": args.port,
        "status": "swept",
        "rows": rows,
        "conclusions": {
            "all_common_and_high_bauds_silent": all(row["connect_kind"] == "none" for row in rows),
            "not_explained_by_simple_command_baud_drift": all(not row["healthy"] for row in rows),
        },
    }

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if any(row["healthy"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
