from __future__ import annotations

import time
from typing import Any

from .protocol import parse_response
from .transport import SerialConfig, SerialTransport, SerialTransportError


DEFAULT_HEALTH_COMMANDS = (
    {"name": "connect", "command": "connect", "required_kind": "connect"},
    {"name": "sendme", "command": "sendme", "required_kind": "page_id"},
    {"name": "get_dim", "command": "get dim", "required_kind": "number"},
)


def probe_serial_health(
    *,
    port: str,
    baud: int = 9600,
    timeout_ms: int = 3000,
    expected_model: str | None = None,
    settle_ms: int = 150,
    verbose: bool = False,
) -> dict[str, Any]:
    """Probe whether a TJC/USART HMI panel is safe for public whmi-wri upload.

    `connect` alone is not enough after a bad TFT load: the panel can still
    answer `comok` while normal runtime commands and public upload entry fail.
    """
    config = SerialConfig(port=port, baud=baud, timeout_ms=timeout_ms, verbose=verbose)
    results = []
    for item in DEFAULT_HEALTH_COMMANDS:
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
