from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from usarthmi.hmi_inspect import inspect_hmi
from usarthmi.page_format import PageBlock, PageFile, load_page_file, parse_page_data
from usarthmi.protocol import ParsedResponse, build_click, build_get, build_set, parse_response
from usarthmi.tft_checksum import inspect_tft_checksum
from usarthmi.tft_download import upload_tft
from usarthmi.tft_patch import patch_rebuild_page_tft
from usarthmi.transport import SerialConfig, SerialTransport


DEFAULT_CASE_ROOT = Path(r"C:\Users\SinYu\Desktop\case_for_codex")
DEFAULT_BASELINE_TFT = DEFAULT_CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
DEFAULT_SEED_PA = (
    Path(__file__).resolve().parents[1]
    / "reverse_usarthmi"
    / "case_compare"
    / "case_00_baseline"
    / "extract"
    / "0.pa"
)
DEFAULT_OUT_ROOT = Path(__file__).resolve().parents[1] / "reverse_usarthmi" / "live_case_smoke"
DEFAULT_OLD_GETS = {
    "t0": "txt",
    "b0": "txt",
    "p0": "pic",
}
TEXT_READBACK_TYPES = {"t", "b", "5", "7", "C", ":"}
IMAGE_RESOURCE_TYPES = {"p", "q"}
IMAGE_RESOURCE_FIELDS = ("pic", "picc")
HOTSPOT_CLICK_TYPES = {"m"}


@dataclass(slots=True)
class SerialCheck:
    command: str
    sent_hex: str
    response: dict[str, Any]
    ok: bool
    expectation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "sent_hex": self.sent_hex,
            "response": self.response,
            "ok": self.ok,
            "expectation": self.expectation,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and optionally live-smoke one clean USART HMI/TJC case.")
    parser.add_argument("case_name", help="Case directory name, for example case_22_scrolling_text")
    parser.add_argument("--case-root", type=Path, default=DEFAULT_CASE_ROOT)
    parser.add_argument("--baseline-tft", type=Path, default=DEFAULT_BASELINE_TFT)
    parser.add_argument("--seed-pa", type=Path, default=DEFAULT_SEED_PA)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--port", default="COM36")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--download-baud", type=int, default=921600)
    parser.add_argument("--timeout-ms", type=int, default=2000)
    parser.add_argument("--post-upload-wait-s", type=float, default=2.0)
    parser.add_argument("--upload", action="store_true", help="Upload the generated clean TFT before serial checks.")
    parser.add_argument("--skip-upload-if-identical", action="store_true")
    parser.add_argument(
        "--require-model",
        default="TJC8048X543_011C",
        help="When uploading, require connect to report this model before whmi-wri. Empty string disables.",
    )
    parser.add_argument("--capture", action="store_true", help="Capture a camera frame after serial checks.")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--camera-backend", choices=["default", "dshow", "msmf"], default="dshow")
    parser.add_argument("--camera-warmup-s", type=float, default=1.0)
    parser.add_argument("--progress", action="store_true", help="Print upload progress to stderr.")
    args = parser.parse_args()

    result = run_smoke(args)
    result_path = Path(result["out_dir"]) / "smoke_result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["summary"]["ok"] else 1


def run_smoke(args: argparse.Namespace) -> dict[str, Any]:
    case_dir = (args.case_root / args.case_name).resolve()
    hmi_path = case_dir / "lcd_test.HMI"
    if not hmi_path.exists():
        raise FileNotFoundError(hmi_path)

    out_dir = (args.out_root / args.case_name).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    clean_pa = out_dir / "clean_0.pa"
    clean_tft = out_dir / "clean.tft"

    seed_page = load_page_file(args.seed_pa)
    target_page = _load_hmi_page0(hmi_path)
    clean_page, seed_object_names, target_blocks, runtime_pad_blocks = _make_clean_page(seed_page, target_page)
    clean_pa.write_bytes(clean_page.serialize())

    rebuild = patch_rebuild_page_tft(
        args.baseline_tft,
        seed_pa=args.seed_pa,
        target_pa=clean_pa,
        out_tft=clean_tft,
    ).to_dict()
    checksum = _inspect_tft_checksum_safe(clean_tft)
    checksum_ok = bool(checksum.get("valid"))

    upload_result = None
    required_model = str(getattr(args, "require_model", "") or "")
    model_preflight = None
    known_current = out_dir / "known_current.tft"
    if args.upload:
        if checksum_ok:
            if required_model:
                model_preflight = _model_preflight_check(
                    port=args.port,
                    baud=args.baud,
                    timeout_ms=args.timeout_ms,
                    required_model=required_model,
                )
            if model_preflight is not None and not model_preflight["ok"]:
                upload_result = {
                    "skipped": True,
                    "blocked": True,
                    "reason": "model_preflight_failed",
                }
            else:
                progress = _make_progress() if args.progress else None
                upload_result = upload_tft(
                    clean_tft,
                    port=args.port,
                    baud=args.baud,
                    download_baud=args.download_baud,
                    timeout_ms=max(args.timeout_ms, 8000),
                    known_current=known_current if known_current.exists() else None,
                    skip_if_identical=bool(args.skip_upload_if_identical and known_current.exists()),
                    progress=progress,
                ).to_dict()
                if not upload_result.get("skipped"):
                    known_current.write_bytes(clean_tft.read_bytes())
                time.sleep(max(0.0, args.post_upload_wait_s))
        else:
            upload_result = {
                "skipped": True,
                "blocked": True,
                "reason": "invalid_tft_checksum",
            }

    serial_checks = []
    serial_checks_skipped = bool(args.upload and upload_result and upload_result.get("blocked"))
    if args.upload and not serial_checks_skipped:
        serial_checks = _run_serial_checks(
            port=args.port,
            baud=args.baud,
            timeout_ms=args.timeout_ms,
            seed_object_names=seed_object_names,
            target_blocks=target_blocks,
        )

    camera = None
    if args.capture:
        camera = _capture_frame(
            out_dir / "camera_after_upload.jpg",
            camera_index=args.camera_index,
            backend=args.camera_backend,
            warmup_s=args.camera_warmup_s,
        )

    checks_ok = all(item.ok for item in serial_checks)
    result = {
        "case_name": args.case_name,
        "case_dir": str(case_dir),
        "out_dir": str(out_dir),
        "clean_pa": str(clean_pa),
        "clean_tft": str(clean_tft),
        "target_objects": [_block_summary(block) for block in target_blocks],
        "runtime_pad_objects": [_block_summary(block) for block in runtime_pad_blocks],
        "seed_object_names": seed_object_names,
        "rebuild": rebuild,
        "checksum": checksum,
        "model_preflight": model_preflight,
        "upload": upload_result,
        "serial_checks": [item.to_dict() for item in serial_checks],
        "camera": camera,
        "summary": {
            "ok": checksum_ok
            and (not args.upload or (upload_result is not None and not upload_result.get("blocked") and checks_ok)),
            "checksum_valid": checksum_ok,
            "model_preflight_ok": None if model_preflight is None else bool(model_preflight["ok"]),
            "uploaded": bool(upload_result and not upload_result.get("skipped")),
            "upload_blocked": bool(upload_result and upload_result.get("blocked")),
            "upload_skipped": bool(upload_result and upload_result.get("skipped")),
            "serial_checks_ok": checks_ok if args.upload else None,
            "serial_checks_skipped": serial_checks_skipped,
            "camera_captured": camera is not None,
        },
    }
    return result


def _load_hmi_page0(hmi_path: Path) -> PageFile:
    inspection = inspect_hmi(hmi_path)
    raw = hmi_path.read_bytes()
    entry = next((item for item in inspection.entries if item.name == "0.pa"), None)
    if entry is None or not entry.in_file:
        raise FileNotFoundError(f"0.pa not found in {hmi_path}")
    return parse_page_data(raw[entry.data_offset : entry.data_offset + entry.length])


def _make_clean_page(seed_page: PageFile, target_page: PageFile) -> tuple[PageFile, list[str], list[PageBlock], list[PageBlock]]:
    seed_names = [block.objname or "" for block in seed_page.blocks if block.objname]
    seed_name_set = set(seed_names)
    page_block = target_page.blocks[0].clone()
    page_block.set_int("id", 0, width=1)

    target_blocks = [
        block.clone()
        for block in target_page.blocks[1:]
        if block.objname and block.objname not in seed_name_set
    ]
    runtime_pad_blocks = _waveform_runtime_pads(seed_page, target_blocks)
    compiled_blocks = [*runtime_pad_blocks, *target_blocks]
    for object_id, block in enumerate(compiled_blocks, start=1):
        block.set_int("id", object_id, width=1)

    clean = target_page
    clean.blocks = [page_block, *compiled_blocks]
    return clean, seed_names, target_blocks, runtime_pad_blocks


def _waveform_runtime_pads(seed_page: PageFile, target_blocks: list[PageBlock]) -> list[PageBlock]:
    if not any(block.type_code == "\x00" for block in target_blocks):
        return []

    pads: list[PageBlock] = []
    for index, source in enumerate(seed_page.blocks[1:4], start=1):
        block = source.clone()
        block.set_string("objname", f"_wfpad{index}")
        _set_geometry(block, 799, 479, 1, 1)
        if block.get_field("txt") is not None:
            block.set_string("txt", "")
        if block.type_code == "b" and block.get_field("val") is not None:
            block.set_int("val", 0)
        if block.type_code == "p" and block.get_field("pic") is not None:
            block.set_int("pic", 0)
        pads.append(block)
    return pads


def _set_geometry(block: PageBlock, x: int, y: int, w: int, h: int) -> None:
    values = {
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "endx": x + w - 1,
        "endy": y + h - 1,
    }
    for name, value in values.items():
        block.set_int(name, value, width=2)


def _run_serial_checks(
    *,
    port: str,
    baud: int,
    timeout_ms: int,
    seed_object_names: list[str],
    target_blocks: list[PageBlock],
) -> list[SerialCheck]:
    transport = SerialTransport(SerialConfig(port=port, baud=baud, timeout_ms=timeout_ms))
    checks: list[SerialCheck] = []
    checks.append(_transact_check(transport, "sendme", lambda response: response.kind == "page_id" and response.value == 0, "page 0"))

    target_names = {block.objname for block in target_blocks if block.objname}
    for name in seed_object_names:
        if name == "page0" or name in target_names:
            continue
        attr = DEFAULT_OLD_GETS.get(name, "id")
        checks.append(
            _transact_check(
                transport,
                build_get(f"{name}.{attr}"),
                lambda response: response.kind == "invalid_reference",
                "old seed object must be invalid",
            )
        )

    for block in target_blocks:
        name = block.objname
        if not name:
            continue
        attr = _default_probe_attr(block)
        checks.append(
            _transact_check(
                transport,
                build_get(f"{name}.{attr}"),
                lambda response: response.kind not in {"invalid_reference", "none"},
                "target object must be readable",
            )
        )

    for block in target_blocks:
        if not block.objname or block.type_code not in IMAGE_RESOURCE_TYPES:
            continue
        name = block.objname
        for attr in IMAGE_RESOURCE_FIELDS:
            if block.get_field(attr) is None:
                continue
            checks.append(
                _transact_check(
                    transport,
                    build_get(f"{name}.{attr}"),
                    lambda response: response.kind == "number",
                    f"image {attr} resource must be readable",
                )
            )
            pic_id = _field_int(block, attr)
            if pic_id is None:
                continue
            checks.append(
                _transact_check(
                    transport,
                    build_set(f"{name}.{attr}", str(pic_id)),
                    lambda response: response.kind in {"none", "number", "unknown", "ascii"},
                    f"image {attr} assignment should not be invalid",
                )
            )
            checks.append(
                _transact_check(
                    transport,
                    build_get(f"{name}.{attr}"),
                    lambda response, expected=pic_id: response.kind == "number" and response.value == expected,
                    f"image {attr} readback should match assignment",
                )
            )

    for block in target_blocks:
        if not block.objname or block.type_code not in HOTSPOT_CLICK_TYPES:
            continue
        checks.append(
            _transact_check(
                transport,
                build_click(block.objname, "down"),
                lambda response: response.kind in {"none", "number", "string", "ascii", "unknown"},
                "hotspot click down should not be invalid",
                attempts=1,
            )
        )

    for block in target_blocks:
        if not block.objname or block.type_code not in TEXT_READBACK_TYPES or block.get_field("txt") is None:
            continue
        name = block.objname
        checks.append(
            _transact_check(
                transport,
                build_set(f"{name}.txt", '"OK"'),
                lambda response: response.kind in {"none", "number", "unknown", "ascii"},
                "text assignment should not be invalid",
            )
        )
        checks.append(
            _transact_check(
                transport,
                build_get(f"{name}.txt"),
                lambda response: response.kind == "string" and response.value == "OK",
                "text readback should match assignment",
            )
        )

    for block in target_blocks:
        if not block.objname or block.get_field("val") is None or block.type_code not in {"5", "C", "8", "9", "b"}:
            continue
        name = block.objname
        before = _transact_check(
            transport,
            build_get(f"{name}.val"),
            lambda response: response.kind == "number",
            "val before click must be readable",
        )
        checks.append(before)
        checks.append(
            _transact_check(
                transport,
                build_click(name, "down"),
                lambda response: response.kind in {"none", "number", "string", "ascii", "unknown"},
                "click down should not be invalid",
                attempts=1,
            )
        )
        checks.append(
            _transact_check(
                transport,
                build_get(f"{name}.val"),
                lambda response: response.kind == "number",
                "val after click must be readable",
            )
        )
        break

    for block in target_blocks:
        if not block.objname or block.get_field("val") is None or block.type_code not in {"\x01", "6", "j", "z"}:
            continue
        name = block.objname
        checks.append(
            _transact_check(
                transport,
                build_set(f"{name}.val", "37"),
                lambda response: response.kind in {"none", "number", "unknown", "ascii"},
                "numeric visual val assignment should not be invalid",
            )
        )
        checks.append(
            _transact_check(
                transport,
                build_get(f"{name}.val"),
                lambda response: response.kind == "number" and response.value == 37,
                "numeric visual val readback should match assignment",
            )
        )

    for block in target_blocks:
        if not block.objname or block.type_code != "3":
            continue
        name = block.objname
        for attr in ("tim", "en"):
            if block.get_field(attr) is None:
                continue
            checks.append(
                _transact_check(
                    transport,
                    build_get(f"{name}.{attr}"),
                    lambda response: response.kind == "number",
                    f"timer {attr} must be readable",
                )
            )
        if block.get_field("en") is not None:
            checks.append(
                _transact_check(
                    transport,
                    build_set(f"{name}.en", "1"),
                    lambda response: response.kind in {"none", "number", "unknown", "ascii"},
                    "timer en assignment should not be invalid",
                )
            )
            checks.append(
                _transact_check(
                    transport,
                    build_get(f"{name}.en"),
                    lambda response: response.kind == "number" and response.value == 1,
                    "timer en readback should match assignment",
                )
            )

    for block in target_blocks:
        if not block.objname or block.type_code != "4" or block.get_field("val") is None:
            continue
        name = block.objname
        checks.append(
            _transact_check(
                transport,
                build_set(f"{name}.val", "123"),
                lambda response: response.kind in {"none", "number", "unknown", "ascii"},
                "variable val assignment should not be invalid",
            )
        )
        checks.append(
            _transact_check(
                transport,
                build_get(f"{name}.val"),
                lambda response: response.kind == "number" and response.value == 123,
                "variable val readback should match assignment",
            )
        )
        break

    for block in target_blocks:
        if not block.objname or block.type_code != "\x00":
            continue
        name = block.objname
        checks.append(
            _transact_check(
                transport,
                f"add {name}.id,0,50",
                lambda response: response.kind not in {"invalid_reference", "invalid_waveform"},
                "waveform add command should not be invalid",
            )
        )
        break

    return checks


def _model_preflight_check(
    *,
    port: str,
    baud: int,
    timeout_ms: int,
    required_model: str,
) -> dict[str, Any]:
    transport = SerialTransport(SerialConfig(port=port, baud=baud, timeout_ms=timeout_ms))
    check = _transact_check(
        transport,
        "connect",
        lambda response: response.kind == "connect",
        "connect preflight",
        attempts=3,
    )
    details = check.response.get("details", {}) if isinstance(check.response, dict) else {}
    actual_model = details.get("model") if isinstance(details, dict) else None
    return {
        "required_model": required_model,
        "actual_model": actual_model,
        "connect": check.to_dict(),
        "ok": check.ok and actual_model == required_model,
    }


def _inspect_tft_checksum_safe(tft_path: Path) -> dict[str, Any]:
    try:
        return inspect_tft_checksum(tft_path)
    except Exception as exc:
        return {
            "path": str(tft_path),
            "file_size": tft_path.stat().st_size if tft_path.exists() else None,
            "valid": False,
            "error": str(exc),
        }


def _transact_check(
    transport: SerialTransport,
    command: str,
    predicate: Any,
    expectation: str,
    *,
    attempts: int = 3,
) -> SerialCheck:
    last_sent = b""
    last_response = ParsedResponse(kind="none", raw=b"", hex="")
    for attempt in range(max(1, attempts)):
        last_sent, raw = transport.transact(command)
        last_response = parse_response(raw)
        if predicate(last_response):
            break
        if attempt + 1 < attempts:
            time.sleep(0.2)
    return SerialCheck(
        command=command,
        sent_hex=last_sent.hex(" "),
        response=last_response.to_dict(),
        ok=bool(predicate(last_response)),
        expectation=expectation,
    )


def _default_probe_attr(block: PageBlock) -> str:
    if block.type_code == "4" and block.get_field("val") is not None:
        return "val"
    if block.get_field("txt") is not None:
        return "txt"
    if block.get_field("val") is not None:
        return "val"
    if block.get_field("x") is not None:
        return "x"
    if block.get_field("pic") is not None:
        return "pic"
    if block.get_field("picc") is not None:
        return "picc"
    return "id"


def _block_summary(block: PageBlock) -> dict[str, Any]:
    return {
        "name": block.objname,
        "type": block.type_code,
        "id": _field_int(block, "id"),
        "x": _field_int(block, "x"),
        "y": _field_int(block, "y"),
        "w": _field_int(block, "w"),
        "h": _field_int(block, "h"),
        "probe_attr": _default_probe_attr(block),
    }


def _field_int(block: PageBlock, name: str) -> int | None:
    field = block.get_field(name)
    if field is None or not field.value or len(field.value) > 4:
        return None
    return int.from_bytes(field.value, "little")


def _capture_frame(
    output_path: Path,
    *,
    camera_index: int,
    backend: str,
    warmup_s: float,
) -> dict[str, Any]:
    import cv2  # type: ignore

    backend_value = {
        "default": 0,
        "dshow": cv2.CAP_DSHOW,
        "msmf": cv2.CAP_MSMF,
    }[backend]
    cap = cv2.VideoCapture(camera_index, backend_value) if backend_value else cv2.VideoCapture(camera_index)
    try:
        if not cap.isOpened():
            raise RuntimeError(f"camera index {camera_index} could not be opened")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        time.sleep(max(0.0, warmup_s))
        frame = None
        ok = False
        for _ in range(12):
            ok, frame = cap.read()
            time.sleep(0.05)
        if not ok or frame is None:
            raise RuntimeError(f"camera index {camera_index} returned no frame")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        saved = bool(cv2.imwrite(str(output_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95]))
        if not saved:
            raise RuntimeError(f"failed to save camera frame to {output_path}")
        height, width = [int(value) for value in frame.shape[:2]]
        return {
            "path": str(output_path.resolve()),
            "camera_index": camera_index,
            "backend": backend,
            "width": width,
            "height": height,
            "bytes": output_path.stat().st_size,
        }
    finally:
        cap.release()


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
