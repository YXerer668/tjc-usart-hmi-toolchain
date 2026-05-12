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
from usarthmi.page_format import PageBlock, PageFile, parse_page_data
from usarthmi.protocol import ParsedResponse, build_get, build_page, parse_response
from usarthmi.tft_download import upload_tft
from usarthmi.transport import SerialConfig, SerialTransport
from tools.live_case_smoke import _capture_frame, _default_probe_attr


DEFAULT_CASE_ROOT = Path(r"C:\Users\SinYu\Desktop\case_for_codex")
DEFAULT_OUT_ROOT = Path(__file__).resolve().parents[1] / "reverse_usarthmi" / "live_page_smoke"


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


@dataclass(slots=True)
class HmiPage:
    page_id: int
    entry_name: str
    page_name: str
    page: PageFile

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_id": self.page_id,
            "entry_name": self.entry_name,
            "page_name": self.page_name,
            "objects": [_block_summary(block) for block in self.page.blocks],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Live-smoke page switching and page-local object scope.")
    parser.add_argument("case_name", nargs="?", help="Case directory name, for example case_31_multi_page_navigation")
    parser.add_argument("--case-root", type=Path, default=DEFAULT_CASE_ROOT)
    parser.add_argument("--hmi", type=Path)
    parser.add_argument("--tft", type=Path)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--port", default="COM36")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--download-baud", type=int, default=921600)
    parser.add_argument("--timeout-ms", type=int, default=2000)
    parser.add_argument("--post-upload-wait-s", type=float, default=2.0)
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--skip-upload-if-identical", action="store_true")
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--camera-backend", choices=["default", "dshow", "msmf"], default="dshow")
    parser.add_argument("--camera-warmup-s", type=float, default=1.0)
    args = parser.parse_args()

    result = run_smoke(args)
    result_path = Path(result["out_dir"]) / "page_smoke_result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["summary"]["ok"] else 1


def run_smoke(args: argparse.Namespace) -> dict[str, Any]:
    hmi_path, tft_path, out_dir = _resolve_paths(args)
    out_dir.mkdir(parents=True, exist_ok=True)
    pages = _load_hmi_pages(hmi_path)
    if not pages:
        raise ValueError(f"No .pa pages found in {hmi_path}")

    upload_result = None
    known_current = out_dir / "known_current.tft"
    if args.upload:
        upload_result = upload_tft(
            tft_path,
            port=args.port,
            baud=args.baud,
            download_baud=args.download_baud,
            timeout_ms=max(args.timeout_ms, 8000),
            known_current=known_current if known_current.exists() else None,
            skip_if_identical=bool(args.skip_upload_if_identical and known_current.exists()),
        ).to_dict()
        if not upload_result.get("skipped"):
            known_current.write_bytes(tft_path.read_bytes())
        time.sleep(max(0.0, args.post_upload_wait_s))

    serial_checks: list[SerialCheck] = []
    if args.upload:
        serial_checks = _run_page_checks(
            port=args.port,
            baud=args.baud,
            timeout_ms=args.timeout_ms,
            pages=pages,
        )

    camera = None
    if args.capture:
        camera = _capture_frame(
            out_dir / "camera_after_page_smoke.jpg",
            camera_index=args.camera_index,
            backend=args.camera_backend,
            warmup_s=args.camera_warmup_s,
        )

    checks_ok = all(item.ok for item in serial_checks)
    return {
        "case_name": args.case_name,
        "hmi": str(hmi_path),
        "tft": str(tft_path),
        "out_dir": str(out_dir),
        "pages": [page.to_dict() for page in pages],
        "upload": upload_result,
        "serial_checks": [item.to_dict() for item in serial_checks],
        "camera": camera,
        "summary": {
            "ok": not args.upload or (upload_result is not None and checks_ok),
            "uploaded": bool(upload_result and not upload_result.get("skipped")),
            "upload_skipped": bool(upload_result and upload_result.get("skipped")),
            "serial_checks_ok": checks_ok if args.upload else None,
            "camera_captured": camera is not None,
        },
    }


def _resolve_paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    if args.case_name:
        case_dir = (args.case_root / args.case_name).resolve()
        hmi_path = (args.hmi or case_dir / "lcd_test.HMI").resolve()
        tft_path = (args.tft or case_dir / "lcd_test.tft").resolve()
        out_dir = (args.out_root / args.case_name).resolve()
    else:
        if args.hmi is None or args.tft is None:
            raise ValueError("Provide case_name, or both --hmi and --tft")
        hmi_path = args.hmi.resolve()
        tft_path = args.tft.resolve()
        out_dir = (args.out_root / hmi_path.stem).resolve()
    if not hmi_path.exists():
        raise FileNotFoundError(hmi_path)
    if not tft_path.exists():
        raise FileNotFoundError(tft_path)
    return hmi_path, tft_path, out_dir


def _load_hmi_pages(hmi_path: Path) -> list[HmiPage]:
    inspection = inspect_hmi(hmi_path)
    raw = hmi_path.read_bytes()
    pages: list[HmiPage] = []
    for entry in inspection.entries:
        if not entry.name.endswith(".pa") or not entry.in_file:
            continue
        page = parse_page_data(raw[entry.data_offset : entry.data_offset + entry.length])
        pages.append(
            HmiPage(
                page_id=len(pages),
                entry_name=entry.name,
                page_name=page.page_name,
                page=page,
            )
        )
    return pages


def _run_page_checks(
    *,
    port: str,
    baud: int,
    timeout_ms: int,
    pages: list[HmiPage],
) -> list[SerialCheck]:
    transport = SerialTransport(SerialConfig(port=port, baud=baud, timeout_ms=timeout_ms))
    checks: list[SerialCheck] = []

    # Drain startup printh frames that otherwise can be mistaken for the first response.
    checks.append(_transact_check(transport, "sendme", lambda _response: True, "startup drain probe"))
    checks.append(_transact_check(transport, "sendme", lambda _response: True, "startup drain probe"))

    for page in pages:
        checks.append(
            _transact_check(
                transport,
                build_page(str(page.page_id)),
                lambda response: response.kind in {"none", "number", "unknown", "ascii"},
                f"numeric page command {page.page_id} should not be invalid",
            )
        )
        checks.append(_expect_page_id(transport, page.page_id))
        _append_page_scope_checks(transport, checks, pages, page)

    for page in pages:
        checks.append(
            _transact_check(
                transport,
                build_page(page.page_name),
                lambda response: response.kind in {"none", "number", "unknown", "ascii"},
                f"name page command {page.page_name} should not be invalid",
            )
        )
        checks.append(_expect_page_id(transport, page.page_id))
        _append_page_scope_checks(transport, checks, pages, page)

    return checks


def _append_page_scope_checks(
    transport: SerialTransport,
    checks: list[SerialCheck],
    pages: list[HmiPage],
    current: HmiPage,
) -> None:
    for page in pages:
        checks.append(
            _transact_check(
                transport,
                build_get(f"{page.page_name}.bco"),
                _number_response if page.page_id == current.page_id else _invalid_reference,
                f"{page.page_name}.bco scope should match current page {current.page_name}",
            )
        )

    current_object_names = {
        block.objname for block in current.page.blocks[1:] if block.objname
    }
    for page in pages:
        for block in page.page.blocks[1:]:
            if not block.objname:
                continue
            attr = _default_probe_attr(block)
            checks.append(
                _transact_check(
                    transport,
                    build_get(f"{block.objname}.{attr}"),
                    _readable_response if block.objname in current_object_names else _invalid_reference,
                    f"{block.objname}.{attr} scope should match current page {current.page_name}",
                )
            )


def _expect_page_id(transport: SerialTransport, page_id: int) -> SerialCheck:
    return _transact_check(
        transport,
        "sendme",
        lambda response, expected=page_id: response.kind == "page_id" and response.value == expected,
        f"sendme should report page {page_id}",
        attempts=3,
    )


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


def _number_response(response: ParsedResponse) -> bool:
    return response.kind == "number"


def _readable_response(response: ParsedResponse) -> bool:
    return response.kind not in {"invalid_reference", "none"}


def _invalid_reference(response: ParsedResponse) -> bool:
    return response.kind == "invalid_reference"


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


if __name__ == "__main__":
    raise SystemExit(main())
