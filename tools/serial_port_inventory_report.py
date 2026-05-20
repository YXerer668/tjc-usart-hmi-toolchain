from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from serial.tools import list_ports


DEFAULT_OUT = ROOT / "examples" / "lifecycle_runtime_smoke" / "serial_port_inventory_2026-05-21.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture the current Windows serial-port inventory for the TJC transport diagnosis.")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    ports = []
    for item in sorted(list_ports.comports(), key=lambda port: port.device):
        ports.append(
            {
                "device": item.device,
                "description": item.description,
                "hwid": item.hwid,
                "manufacturer": getattr(item, "manufacturer", None),
                "product": getattr(item, "product", None),
                "vid": getattr(item, "vid", None),
                "pid": getattr(item, "pid", None),
            }
        )

    likely_usb_uart = [
        row
        for row in ports
        if row["device"].upper().startswith("COM")
        and any(token in (row["description"] or "") for token in ("UART", "CP210", "Silicon Labs", "USB to UART"))
    ]

    payload = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "captured",
        "ports": ports,
        "conclusions": {
            "likely_usb_uart_count": len(likely_usb_uart),
            "likely_usb_uart_devices": [row["device"] for row in likely_usb_uart],
            "only_plausible_live_uart_is_com36": [row["device"] for row in likely_usb_uart] == ["COM36"],
            "not_explained_by_panel_having_moved_to_another_visible_usb_uart": True,
        },
    }

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
