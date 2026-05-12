from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from usarthmi.protocol import build_get, parse_response
from usarthmi.tft_download import DEFAULT_DOWNLOAD_BAUD, PUBLIC_WHMI_CHUNK_SIZE, upload_tft
from usarthmi.transport import SerialConfig, SerialTransport


@dataclass(slots=True)
class RuntimeExpectation:
    target: str
    expected: Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload and/or runtime-smoke a TFT on a live USART HMI screen.")
    parser.add_argument("--file", required=True, help="TFT file to upload when --upload is set.")
    parser.add_argument("--out-dir", required=True, help="Directory for smoke_result.json and optional capture.")
    parser.add_argument("--expect-json", help="JSON expectation file, either {target: value} or a list of entries.")
    parser.add_argument("--expect", action="append", default=[], help="Runtime expectation as target=value, repeatable.")
    parser.add_argument("--port", default="COM36")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--download-baud", type=int, default=DEFAULT_DOWNLOAD_BAUD)
    parser.add_argument("--chunk-size", type=int, default=PUBLIC_WHMI_CHUNK_SIZE)
    parser.add_argument("--allow-unsafe-chunk-size", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=3000)
    parser.add_argument("--prepare-delay-ms", type=int, default=1000)
    parser.add_argument("--prepare-wait-ms", type=int, default=800)
    parser.add_argument("--post-upload-wait-s", type=float, default=2.0)
    parser.add_argument("--expected-page-id", type=int, default=0)
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--known-current", help="Trusted current TFT for exact-file upload skipping.")
    parser.add_argument("--skip-if-identical", action="store_true")
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--camera-index", type=int, default=1)
    parser.add_argument("--camera-backend", choices=["default", "dshow", "msmf"], default="dshow")
    parser.add_argument("--camera-warmup-frames", type=int, default=20)
    args = parser.parse_args()

    result = run_smoke(args)
    out_dir = Path(result["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / "smoke_result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["summary"]["ok"] else 1


def run_smoke(args: argparse.Namespace) -> dict[str, Any]:
    tft_path = Path(args.file).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    expectations = _load_expectations(args.expect_json, args.expect)
    upload_result = None
    known_current = Path(args.known_current).resolve() if args.known_current else None
    if args.upload:
        upload_result = upload_tft(
            tft_path,
            port=args.port,
            baud=args.baud,
            download_baud=args.download_baud,
            chunk_size=args.chunk_size,
            timeout_ms=max(args.timeout_ms, 8000),
            prepare_delay_ms=args.prepare_delay_ms,
            prepare_wait_ms=args.prepare_wait_ms,
            known_current=known_current,
            skip_if_identical=args.skip_if_identical,
            allow_unsafe_chunk_size=args.allow_unsafe_chunk_size,
            progress=_make_progress() if args.progress else None,
        ).to_dict()
        time.sleep(max(0.0, args.post_upload_wait_s))

    serial_checks = _run_serial_checks(
        expectations,
        port=args.port,
        baud=args.baud,
        timeout_ms=args.timeout_ms,
        expected_page_id=args.expected_page_id,
    )
    camera = _capture_frame(args, out_dir) if args.capture else None
    checks_ok = all(item["ok"] for item in serial_checks)

    return {
        "tft_file": str(tft_path),
        "out_dir": str(out_dir),
        "port": args.port,
        "baud": args.baud,
        "download_baud": args.download_baud,
        "chunk_size": args.chunk_size,
        "public_whmi_chunk_size": PUBLIC_WHMI_CHUNK_SIZE,
        "upload": upload_result,
        "expectations": [{"target": item.target, "expected": item.expected} for item in expectations],
        "serial_checks": serial_checks,
        "camera": camera,
        "summary": {
            "ok": (not args.upload or upload_result is not None) and checks_ok,
            "uploaded": bool(upload_result and not upload_result.get("skipped")),
            "upload_skipped": bool(upload_result and upload_result.get("skipped")),
            "serial_checks_ok": checks_ok,
            "camera_captured": camera is not None,
        },
    }


def _load_expectations(expect_json: str | None, inline: list[str]) -> list[RuntimeExpectation]:
    expectations: list[RuntimeExpectation] = []
    if expect_json:
        raw = json.loads(Path(expect_json).read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            items = raw.get("expectations", raw)
            if isinstance(items, dict):
                expectations.extend(RuntimeExpectation(str(key), value) for key, value in items.items())
            elif isinstance(items, list):
                expectations.extend(_expectation_from_entry(entry) for entry in items)
            else:
                raise ValueError("expect-json must contain an object or list under 'expectations'")
        elif isinstance(raw, list):
            expectations.extend(_expectation_from_entry(entry) for entry in raw)
        else:
            raise ValueError("expect-json must be a JSON object or list")

    for item in inline:
        target, sep, raw_value = item.partition("=")
        if not sep:
            raise ValueError(f"--expect requires target=value: {item}")
        expectations.append(RuntimeExpectation(target.strip(), _parse_expected_value(raw_value.strip())))
    return expectations


def _expectation_from_entry(entry: Any) -> RuntimeExpectation:
    if not isinstance(entry, dict):
        raise ValueError(f"Expectation entry must be an object: {entry!r}")
    target = entry.get("target") or entry.get("name")
    if not target:
        raise ValueError(f"Expectation entry is missing target: {entry!r}")
    return RuntimeExpectation(str(target), entry.get("expected"))


def _parse_expected_value(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _run_serial_checks(
    expectations: list[RuntimeExpectation],
    *,
    port: str,
    baud: int,
    timeout_ms: int,
    expected_page_id: int,
) -> list[dict[str, Any]]:
    config = SerialConfig(port=port, baud=baud, timeout_ms=timeout_ms)
    checks = [
        _transact_check(config, "connect", expected_kind="connect"),
        _transact_check(config, "sendme", expected_kind="page_id", expected_value=expected_page_id),
    ]
    for item in expectations:
        checks.append(
            _transact_check(
                config,
                build_get(item.target),
                expected_value=item.expected,
                label=item.target,
            )
        )
    return checks


def _transact_check(
    config: SerialConfig,
    command: str,
    *,
    expected_kind: str | None = None,
    expected_value: Any | None = None,
    label: str | None = None,
) -> dict[str, Any]:
    try:
        payload, response = SerialTransport(config).transact(command)
        parsed = parse_response(response).to_dict()
        actual_value = parsed.get("value")
        ok = True
        expectation = "response received"
        if expected_kind is not None:
            ok = ok and parsed.get("kind") == expected_kind
            expectation = f"kind == {expected_kind}"
        if expected_value is not None:
            ok = ok and actual_value == expected_value
            expectation = f"value == {expected_value!r}"
        return {
            "label": label or command,
            "command": command,
            "sent_hex": payload.hex(" "),
            "response": parsed,
            "expected_kind": expected_kind,
            "expected_value": expected_value,
            "actual_value": actual_value,
            "ok": ok,
            "expectation": expectation,
        }
    except Exception as exc:
        return {
            "label": label or command,
            "command": command,
            "ok": False,
            "error": str(exc),
            "expected_kind": expected_kind,
            "expected_value": expected_value,
        }


def _capture_frame(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    capture_path = out_dir / "camera_after_smoke.jpg"
    cmd = [
        sys.executable,
        str(WORKSPACE_ROOT / "tools" / "capture_hmi_screen.py"),
        "--camera-index",
        str(args.camera_index),
        "--backend",
        args.camera_backend,
        "--autofocus",
        "--warmup-frames",
        str(args.camera_warmup_frames),
        "--output-dir",
        str(out_dir),
        "--filename",
        capture_path.name,
    ]
    completed = subprocess.run(cmd, text=True, capture_output=True, check=False)
    try:
        payload = json.loads(completed.stdout) if completed.stdout.strip() else {}
    except json.JSONDecodeError:
        payload = {"stdout": completed.stdout}
    payload["returncode"] = completed.returncode
    if completed.stderr.strip():
        payload["stderr"] = completed.stderr.strip()
    return payload


def _make_progress():
    last = {"t": 0.0}

    def progress(bytes_sent: int, total: int, chunks_sent: int) -> None:
        now = time.monotonic()
        if now - last["t"] < 1.0 and bytes_sent < total:
            return
        last["t"] = now
        ratio = (bytes_sent / total * 100.0) if total else 100.0
        print(f"upload {bytes_sent}/{total} bytes ({ratio:5.1f}%), chunks={chunks_sent}", file=sys.stderr, flush=True)

    return progress


if __name__ == "__main__":
    raise SystemExit(main())
