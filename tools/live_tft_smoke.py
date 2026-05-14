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
    attempts: int = 1


@dataclass(slots=True)
class RuntimeStep:
    command: str
    label: str | None = None
    expected_kind: str | None = None
    expected_value: Any | None = None
    delay_ms: int = 0
    attempts: int = 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload and/or runtime-smoke a TFT on a live USART HMI screen.")
    parser.add_argument("--file", required=True, help="TFT file to upload when --upload is set.")
    parser.add_argument("--out-dir", required=True, help="Directory for smoke_result.json and optional capture.")
    parser.add_argument("--expect-json", help="JSON expectation file, either {target: value} or a list of entries.")
    parser.add_argument("--expect", action="append", default=[], help="Runtime expectation as target=value, repeatable.")
    parser.add_argument("--set-expect", action="append", default=[], help="Write then verify target=value, repeatable.")
    parser.add_argument("--port", default="COM36")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--download-baud", type=int, default=DEFAULT_DOWNLOAD_BAUD)
    parser.add_argument("--chunk-size", type=int, default=PUBLIC_WHMI_CHUNK_SIZE)
    parser.add_argument("--allow-unsafe-chunk-size", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=3000)
    parser.add_argument("--prepare-delay-ms", type=int, default=1000)
    parser.add_argument("--prepare-wait-ms", type=int, default=800)
    parser.add_argument("--post-upload-wait-s", type=float, default=2.0)
    parser.add_argument("--select-page", help="Optional page command value to send before runtime checks, for example 1.")
    parser.add_argument("--restore-page", help="Optional page command value to send after runtime checks, for example 0.")
    parser.add_argument("--expected-page-id", type=int)
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--known-current", help="Trusted current TFT for exact-file upload skipping.")
    parser.add_argument("--skip-if-identical", action="store_true")
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--capture", action="store_true")
    parser.add_argument(
        "--capture-method",
        choices=["ffmpeg-dshow", "opencv"],
        default="ffmpeg-dshow",
        help="Camera capture backend. ffmpeg-dshow is the known-good path for the local USB Cam.",
    )
    parser.add_argument("--camera-device", default="USB Cam", help="DirectShow camera device name for ffmpeg-dshow.")
    parser.add_argument("--camera-width", type=int, default=2560)
    parser.add_argument("--camera-height", type=int, default=1440)
    parser.add_argument("--camera-framerate", type=int, default=30)
    parser.add_argument("--camera-pixel-format", default="yuyv422")
    parser.add_argument("--camera-warmup-s", type=float, default=1.0)
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

    expectation_config = _load_expectation_config(args.expect_json)
    expectations = _load_expectations(args.expect_json, args.expect)
    set_expectations = _load_set_expectations(args.expect_json, args.set_expect)
    runtime_steps = _load_runtime_steps(args.expect_json)
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

    select_page = args.select_page
    if select_page is None and "select_page" in expectation_config:
        select_page = str(expectation_config["select_page"])
    restore_page = args.restore_page
    if restore_page is None and "restore_page" in expectation_config:
        restore_page = str(expectation_config["restore_page"])
    expected_page_id = args.expected_page_id
    if expected_page_id is None:
        expected_page_id = int(expectation_config.get("page_id", 0))

    serial_checks = _run_serial_checks(
        expectations,
        port=args.port,
        baud=args.baud,
        timeout_ms=args.timeout_ms,
        expected_page_id=expected_page_id,
        select_page=select_page,
        set_expectations=set_expectations,
        runtime_steps=runtime_steps,
        restore_page=restore_page,
    )
    camera = _capture_frame(args, out_dir) if args.capture else None
    checks_ok = all(item["ok"] for item in serial_checks)
    camera_ok = camera is None or bool(camera.get("ok"))

    return {
        "tft_file": str(tft_path),
        "out_dir": str(out_dir),
        "port": args.port,
        "baud": args.baud,
        "download_baud": args.download_baud,
        "chunk_size": args.chunk_size,
        "public_whmi_chunk_size": PUBLIC_WHMI_CHUNK_SIZE,
        "upload": upload_result,
        "expectations": [
            {"target": item.target, "expected": item.expected, "attempts": item.attempts}
            for item in expectations
        ],
        "set_expectations": [
            {"target": item.target, "expected": item.expected, "attempts": item.attempts}
            for item in set_expectations
        ],
        "runtime_steps": [
            {
                "command": item.command,
                "label": item.label,
                "expected_kind": item.expected_kind,
                "expected_value": item.expected_value,
                "delay_ms": item.delay_ms,
                "attempts": item.attempts,
            }
            for item in runtime_steps
        ],
        "serial_checks": serial_checks,
        "camera": camera,
        "summary": {
            "ok": (not args.upload or upload_result is not None) and checks_ok and camera_ok,
            "uploaded": bool(upload_result and not upload_result.get("skipped")),
            "upload_skipped": bool(upload_result and upload_result.get("skipped")),
            "serial_checks_ok": checks_ok,
            "camera_captured": bool(camera and camera.get("ok")),
            "camera_ok": camera_ok,
        },
    }


def _load_expectation_config(expect_json: str | None) -> dict[str, Any]:
    if not expect_json:
        return {}
    raw = json.loads(Path(expect_json).read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


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


def _load_set_expectations(expect_json: str | None, inline: list[str]) -> list[RuntimeExpectation]:
    expectations: list[RuntimeExpectation] = []
    if expect_json:
        raw = json.loads(Path(expect_json).read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            items = raw.get("set_expectations", [])
            if isinstance(items, dict):
                expectations.extend(RuntimeExpectation(str(key), value) for key, value in items.items())
            elif isinstance(items, list):
                expectations.extend(_expectation_from_entry(entry) for entry in items)
            else:
                raise ValueError("set_expectations must be an object or list")
    for item in inline:
        target, sep, raw_value = item.partition("=")
        if not sep:
            raise ValueError(f"--set-expect requires target=value: {item}")
        expectations.append(RuntimeExpectation(target.strip(), _parse_expected_value(raw_value.strip())))
    return expectations


def _load_runtime_steps(expect_json: str | None) -> list[RuntimeStep]:
    config = _load_expectation_config(expect_json)
    items = config.get("steps", [])
    if not items:
        return []
    if not isinstance(items, list):
        raise ValueError("steps must be a list")
    steps: list[RuntimeStep] = []
    for entry in items:
        if not isinstance(entry, dict):
            raise ValueError(f"Step entry must be an object: {entry!r}")
        command = entry.get("command")
        if not command:
            raise ValueError(f"Step entry is missing command: {entry!r}")
        expected_value = entry.get("expected_value", entry.get("expected"))
        attempts = int(entry.get("attempts", 1))
        if attempts < 1:
            raise ValueError(f"Step attempts must be >= 1: {entry!r}")
        steps.append(
            RuntimeStep(
                command=str(command),
                label=str(entry["label"]) if entry.get("label") is not None else None,
                expected_kind=str(entry["expected_kind"]) if entry.get("expected_kind") is not None else None,
                expected_value=expected_value,
                delay_ms=int(entry.get("delay_ms", 0)),
                attempts=attempts,
            )
        )
    return steps


def _expectation_from_entry(entry: Any) -> RuntimeExpectation:
    if not isinstance(entry, dict):
        raise ValueError(f"Expectation entry must be an object: {entry!r}")
    target = entry.get("target") or entry.get("name")
    if not target:
        raise ValueError(f"Expectation entry is missing target: {entry!r}")
    attempts = int(entry.get("attempts", 1))
    if attempts < 1:
        raise ValueError(f"Expectation attempts must be >= 1: {entry!r}")
    return RuntimeExpectation(str(target), entry.get("expected"), attempts=attempts)


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
    select_page: str | None,
    set_expectations: list[RuntimeExpectation],
    runtime_steps: list[RuntimeStep],
    restore_page: str | None,
) -> list[dict[str, Any]]:
    config = SerialConfig(port=port, baud=baud, timeout_ms=timeout_ms)
    checks = [_connect_check(config)]
    if select_page is not None:
        checks.append(_transact_check(config, f"page {select_page}", label=f"page {select_page}"))
    checks.append(_transact_check(config, "sendme", expected_kind="page_id", expected_value=expected_page_id))
    for item in expectations:
        checks.append(
            _transact_check(
                config,
                build_get(item.target),
                expected_value=item.expected,
                label=item.target,
                attempts=item.attempts,
            )
        )
    for item in set_expectations:
        checks.append(
            _transact_check(
                config,
                f"{item.target}={item.expected}",
                label=f"set {item.target}",
                attempts=item.attempts,
            )
        )
        checks.append(
            _transact_check(
                config,
                build_get(item.target),
                expected_value=item.expected,
                label=f"verify {item.target}",
                attempts=item.attempts,
            )
        )
    for item in runtime_steps:
        if item.delay_ms > 0:
            time.sleep(item.delay_ms / 1000.0)
        checks.append(
            _transact_check(
                config,
                item.command,
                expected_kind=item.expected_kind,
                expected_value=item.expected_value,
                label=item.label,
                attempts=item.attempts,
            )
        )
    if restore_page is not None:
        checks.append(_transact_check(config, f"page {restore_page}", label=f"restore page {restore_page}"))
    return checks


def _transact_check(
    config: SerialConfig,
    command: str,
    *,
    expected_kind: str | None = None,
    expected_value: Any | None = None,
    label: str | None = None,
    attempts: int = 1,
) -> dict[str, Any]:
    history: list[dict[str, Any]] = []
    last: dict[str, Any] | None = None
    for attempt in range(1, max(1, attempts) + 1):
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
            result = {
                "label": label or command,
                "command": command,
                "sent_hex": payload.hex(" "),
                "response": parsed,
                "expected_kind": expected_kind,
                "expected_value": expected_value,
                "actual_value": actual_value,
                "attempt": attempt,
                "attempts": max(1, attempts),
                "ok": ok,
                "expectation": expectation,
            }
        except Exception as exc:
            result = {
                "label": label or command,
                "command": command,
                "attempt": attempt,
                "attempts": max(1, attempts),
                "ok": False,
                "error": str(exc),
                "expected_kind": expected_kind,
                "expected_value": expected_value,
            }
        if result["ok"]:
            if history:
                result["retry_history"] = history
            return result
        history.append(result)
        last = result
        if attempt < max(1, attempts):
            time.sleep(0.2)
    assert last is not None
    last["retry_history"] = history[:-1]
    return last


def _connect_check(config: SerialConfig, *, attempts: int = 3, delay_s: float = 0.5) -> dict[str, Any]:
    last: dict[str, Any] | None = None
    history: list[dict[str, Any]] = []
    for attempt in range(1, attempts + 1):
        check = _transact_check(config, "connect", expected_kind="connect", label="connect")
        check["attempt"] = attempt
        history.append(check)
        if check.get("ok"):
            if attempt > 1:
                check["retry_history"] = history[:-1]
            return check
        last = check
        if attempt < attempts:
            time.sleep(delay_s)
    assert last is not None
    last["retry_history"] = history[:-1]
    return last


def _capture_frame(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    if args.capture_method == "ffmpeg-dshow":
        return _capture_frame_ffmpeg_dshow(args, out_dir)
    return _capture_frame_opencv(args, out_dir)


def _capture_frame_ffmpeg_dshow(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    capture_path = out_dir / "camera_after_smoke.jpg"
    video_size = f"{args.camera_width}x{args.camera_height}"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-f",
        "dshow",
        "-pixel_format",
        args.camera_pixel_format,
        "-video_size",
        video_size,
        "-framerate",
        str(args.camera_framerate),
        "-i",
        f"video={args.camera_device}",
    ]
    if args.camera_warmup_s > 0:
        cmd.extend(["-ss", str(args.camera_warmup_s)])
    cmd.extend(["-frames:v", "1", "-update", "1", str(capture_path)])

    completed = subprocess.run(cmd, text=True, capture_output=True, check=False)
    ok = completed.returncode == 0 and capture_path.exists()
    payload: dict[str, Any] = {
        "capture_method": "ffmpeg-dshow",
        "path": str(capture_path.resolve()),
        "device": args.camera_device,
        "width": args.camera_width,
        "height": args.camera_height,
        "framerate": args.camera_framerate,
        "pixel_format": args.camera_pixel_format,
        "warmup_s": args.camera_warmup_s,
        "returncode": completed.returncode,
        "ok": ok,
    }
    if capture_path.exists():
        payload["bytes"] = capture_path.stat().st_size
    if completed.stderr.strip():
        payload["stderr"] = completed.stderr.strip()
    if completed.stdout.strip():
        payload["stdout"] = completed.stdout.strip()
    return payload


def _capture_frame_opencv(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
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
    payload["capture_method"] = "opencv"
    payload["ok"] = completed.returncode == 0 and bool(payload.get("path"))
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
