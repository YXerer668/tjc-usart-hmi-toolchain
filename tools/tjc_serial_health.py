from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from usarthmi.protocol import parse_response
from usarthmi.transport import SerialConfig, SerialTransport, SerialTransportError


def probe_serial_health(
    *,
    port: str,
    baud: int = 9600,
    timeout_ms: int = 3000,
    expected_model: str | None = None,
    settle_ms: int = 150,
) -> dict[str, Any]:
    commands = [
        {"name": "connect", "command": "connect", "required_kind": "connect"},
        {"name": "sendme", "command": "sendme", "required_kind": "page_id"},
        {"name": "get_dim", "command": "get dim", "required_kind": "number"},
    ]
    config = SerialConfig(port=port, baud=baud, timeout_ms=timeout_ms)
    results = []
    for item in commands:
        if settle_ms > 0 and results:
            time.sleep(settle_ms / 1000.0)
        results.append(_run_probe_command(config, item))

    summary = _classify_health(results, expected_model=expected_model)
    return {
        "port": port,
        "baud": baud,
        "timeout_ms": timeout_ms,
        "expected_model": expected_model,
        "summary": summary,
        "commands": results,
    }


def _run_probe_command(config: SerialConfig, item: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": item["name"],
        "command": item["command"],
        "required_kind": item["required_kind"],
    }
    try:
        sent, response = SerialTransport(config).transact(item["command"])
        parsed = parse_response(response)
        parsed_dict = parsed.to_dict()
        result.update(
            {
                "sent_hex": sent.hex(" "),
                "response": parsed_dict,
                "passed": parsed.kind == item["required_kind"],
            }
        )
    except SerialTransportError as exc:
        result.update({"error": str(exc), "passed": False})
    return result


def _classify_health(results: list[dict[str, Any]], *, expected_model: str | None) -> dict[str, Any]:
    by_name = {item["name"]: item for item in results}
    connect = by_name.get("connect", {})
    sendme = by_name.get("sendme", {})
    get_dim = by_name.get("get_dim", {})
    connect_response = connect.get("response") or {}
    details = connect_response.get("details") or {}
    model = details.get("model")
    model_ok = expected_model is None or model == expected_model
    connect_ok = bool(connect.get("passed")) and model_ok
    runtime_ok = bool(sendme.get("passed")) and bool(get_dim.get("passed"))
    public_upload_ready = connect_ok and runtime_ok

    if connect_ok and not runtime_ok:
        diagnosis = (
            "connect reports the expected panel, but runtime commands do not respond; "
            "public whmi-wri upload may fail until the panel is power-cycled, recovered by the official downloader, "
            "or restored from SD-card TFT."
        )
    elif not connect.get("passed"):
        diagnosis = "connect did not return comok; check COM port, baud rate, wiring, or power."
    elif not model_ok:
        diagnosis = f"connect returned model {model!r}, expected {expected_model!r}; do not upload this TFT."
    elif runtime_ok:
        diagnosis = "serial runtime is healthy enough for normal commands and public whmi-wri upload preflight."
    else:
        diagnosis = "serial health is inconclusive."

    return {
        "connect_ok": connect_ok,
        "model": model,
        "model_ok": model_ok,
        "runtime_ok": runtime_ok,
        "public_upload_ready": public_upload_ready,
        "healthy": public_upload_ready,
        "diagnosis": diagnosis,
    }


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
