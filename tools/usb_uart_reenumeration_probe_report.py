from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "examples" / "lifecycle_runtime_smoke" / "usb_uart_reenumeration_probe_2026-05-21.json"
DEFAULT_OUT = ROOT / "examples" / "lifecycle_runtime_smoke" / "usb_uart_reenumeration_probe_summary_2026-05-21.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize the USB-UART bridge re-enumeration probe.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    summary = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "probe-summarized",
        "instance_id": payload["instance_id"],
        "disable_ok": payload["disable"]["ok"],
        "enable_ok": payload["enable"]["ok"],
        "before_connect_kind": payload["before"]["commands"][0]["response"]["kind"],
        "after_connect_kind": payload["after"]["commands"][0]["response"]["kind"],
        "conclusions": {
            "usb_uart_bridge_reenumeration_succeeds_but_screen_stays_silent": payload["disable"]["ok"] and payload["enable"]["ok"] and not payload["conclusions"]["serial_became_responsive_after_reenumeration"],
            "no_change_after_reenumeration": payload["conclusions"]["no_change_after_reenumeration"],
        },
    }
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
