from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usarthmi.page_format import load_page_file
from usarthmi.object_hash import object_name_hash
from usarthmi.tft_patch import _record_header_flag
from usarthmi.tft_toolchain import inspect_tft


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize a page1 advanced-control runtime binding failure from build artifacts."
    )
    parser.add_argument("build_dir", type=Path, help="Build directory containing manifest.json and related artifacts")
    parser.add_argument("--page-index", type=int, default=1, help="Target page index to summarize")
    parser.add_argument("--out", type=Path, help="Optional output JSON path")
    args = parser.parse_args()

    report = build_report(args.build_dir.resolve(), page_index=args.page_index)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


def build_report(build_dir: Path, *, page_index: int) -> dict[str, Any]:
    manifest_path = build_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target_pages = [Path(path) for path in manifest.get("target_pages", [])]
    if page_index >= len(target_pages):
        raise ValueError(f"page_index {page_index} is out of range for {build_dir}")
    target_page_path = target_pages[page_index]
    target_page = load_page_file(target_page_path)

    event_index_path = _pick_one(build_dir.glob("event_index*.json"))
    event_index = _load_json(event_index_path)
    smoke_path = _pick_one(build_dir.glob("smoke_*/*smoke_result.json"))
    smoke = _load_json(smoke_path)

    page_name = target_page.page_name or f"page{page_index}"
    page_event_summary = _page_event_index_summary(event_index, page_name=page_name, page_index=page_index)
    failed_lookups = _failed_runtime_lookups(smoke)
    failed_clicks = _failed_clicks(smoke)
    compiled_layout = _compiled_page_layout(
        Path(manifest["output_tft"]),
        target_page,
        build_manifest=manifest.get("tft_patch", {}),
    )

    report = {
        "schema_version": 1,
        "mode": "page1_advanced_binding_negative_report",
        "build_dir": str(build_dir),
        "page_index": page_index,
        "page_name": page_name,
        "artifacts": {
            "manifest": str(manifest_path),
            "target_page": str(target_page_path),
            "event_index": str(event_index_path) if event_index_path else None,
            "smoke_result": str(smoke_path) if smoke_path else None,
            "output_hmi": manifest.get("output_hmi"),
            "output_tft": manifest.get("output_tft"),
        },
        "build_manifest": {
            "mode": manifest.get("tft_patch", {}).get("mode"),
            "file_size": manifest.get("tft_patch", {}).get("file_size"),
            "page_count": manifest.get("tft_patch", {}).get("page_count"),
            "object_count": manifest.get("tft_patch", {}).get("object_count"),
            "experimental_events": manifest.get("tft_patch", {}).get("experimental_events"),
            "section_offsets": manifest.get("tft_patch", {}).get("section_offsets"),
            "checksum": manifest.get("tft_checksum"),
            "page_object_events": manifest.get("tft_patch", {})
            .get("experimental_event_summary", {})
            .get("page1_object_events", []),
        },
        "page_source_objects": [_page_block_summary(block) for block in target_page.blocks],
        "compiled_page_layout": compiled_layout,
        "event_index_summary": page_event_summary,
        "live_smoke": {
            "summary": smoke.get("summary") if smoke else None,
            "page_switch": _find_serial_check(smoke, command=f"page {page_index}"),
            "sendme": _find_serial_check(smoke, command="sendme"),
            "failed_runtime_lookups": failed_lookups,
            "failed_clicks": failed_clicks,
            "camera": smoke.get("camera") if smoke else None,
        },
    }
    report["diagnosis"] = _diagnosis(report)
    return report


def _load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    raw = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le"):
        try:
            return json.loads(raw.decode(encoding))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise ValueError(f"unable to decode JSON file {path}")


def _pick_one(paths: Any) -> Path | None:
    items = sorted(Path(path) for path in paths)
    return items[0] if items else None


def _page_block_summary(block: Any) -> dict[str, Any]:
    return {
        "objname": block.objname,
        "type_code": block.type_code,
        "id": _field_int(block, "id"),
        "geometry": {
            "x": _field_int(block, "x"),
            "y": _field_int(block, "y"),
            "w": _field_int(block, "w"),
            "h": _field_int(block, "h"),
        },
        "event_tokens": list(block.event_tokens),
    }


def _field_int(block: Any, name: str) -> int | None:
    field = next((item for item in block.fields if item.name == name), None)
    if field is None or field.value is None:
        return None
    raw = field.value
    if isinstance(raw, bytes):
        return int.from_bytes(raw, "little")
    if isinstance(raw, int):
        return raw
    return None


def _page_event_index_summary(
    event_index: dict[str, Any] | None,
    *,
    page_name: str,
    page_index: int,
) -> dict[str, Any] | None:
    if event_index is None:
        return None
    all_page_summary = event_index.get("all_page_summary", {})
    page_summary = next(
        (
            item
            for item in all_page_summary.get("pages", [])
            if item.get("page_name") == page_name or item.get("resource") == f"{page_index}.pa"
        ),
        None,
    )
    return {
        "top_level_summary": event_index.get("summary"),
        "all_page_summary": all_page_summary,
        "page_summary": page_summary,
    }


def _compiled_page_layout(tft_path: Path, page: Any, *, build_manifest: dict[str, Any]) -> dict[str, Any]:
    hash_offset, compiled_hash_ids = _compiled_page_hash_ids(tft_path, page)
    pic_offset = int(build_manifest.get("section_offsets", {}).get("pic", {}).get("value", 0))
    padding_offset = int(build_manifest.get("section_offsets", {}).get("padding", {}).get("value", 0))
    page_count = int(build_manifest.get("page_count", 0) or 0)
    object_count = int(build_manifest.get("object_count", 0) or 0)
    summary_bytes = 0x10 * page_count
    per_record_length = (padding_offset - pic_offset - summary_bytes) // max(object_count, 1)
    mirror_headers = _compiled_page_mirror_headers(
        tft_path,
        page,
        pic_offset=pic_offset,
        summary_bytes=summary_bytes,
        per_record_length=per_record_length,
    )
    expected_headers = [
        bytes([ord(block.type_code), _field_int(block, "id"), 0, _record_header_flag(block.type_code)]).hex(" ")
        for block in page.blocks
    ]
    return {
        "hash_offset": hash_offset,
        "hash_ids": compiled_hash_ids,
        "hash_ids_match_source": compiled_hash_ids == {block.objname: _field_int(block, "id") for block in page.blocks},
        "mirror_headers": mirror_headers,
        "expected_mirror_headers": expected_headers,
        "mirror_headers_match_source": mirror_headers == expected_headers,
        "per_record_length": per_record_length,
        "mirror_value_count_guess": max((per_record_length - 0x38) // 2, 0),
        "object_start": _header2_int(tft_path, "unknown_objects_address"),
        "pictures_address": _header2_int(tft_path, "pictures_address"),
        "usercode_address": _header2_int(tft_path, "usercode_address"),
    }


def _compiled_page_hash_ids(tft_path: Path, page: Any) -> tuple[int, dict[str, int]]:
    raw = tft_path.read_bytes()
    object_start = _header2_int(tft_path, "unknown_objects_address")
    tail = raw[object_start:]
    entries = []
    for block in page.blocks:
        if not block.objname:
            continue
        entries.append((object_name_hash(block.objname), _field_int(block, "id")))
    entries.sort(key=lambda item: item[0])
    hash_data = b"".join(
        value.to_bytes(4, "little") + object_id.to_bytes(2, "little")
        for value, object_id in entries
    )
    marker = len(hash_data).to_bytes(4, "little") + hash_data
    hash_offset = tail.find(marker)
    ids_by_hash = {
        int.from_bytes(hash_data[offset : offset + 4], "little"): int.from_bytes(hash_data[offset + 4 : offset + 6], "little")
        for offset in range(0, len(hash_data), 6)
    }
    compiled_hash_ids = {
        block.objname: ids_by_hash[object_name_hash(block.objname)]
        for block in page.blocks
        if block.objname
    }
    return hash_offset, compiled_hash_ids


def _compiled_page_mirror_headers(
    tft_path: Path,
    page: Any,
    *,
    pic_offset: int,
    summary_bytes: int,
    per_record_length: int,
) -> list[str]:
    raw = tft_path.read_bytes()
    object_start = _header2_int(tft_path, "unknown_objects_address")
    tail = raw[object_start:]
    records_start = pic_offset + summary_bytes
    return [
        tail[records_start + index * per_record_length : records_start + index * per_record_length + 4].hex(" ")
        for index, _block in enumerate(page.blocks)
    ]


def _header2_int(tft_path: Path, key: str) -> int:
    header2 = inspect_tft(tft_path)["parsed"]["Header2"]
    value = header2[key]
    if isinstance(value, str) and value.startswith("0x"):
        return int(value, 16)
    return int(value)


def _failed_runtime_lookups(smoke: dict[str, Any] | None) -> list[dict[str, Any]]:
    if smoke is None:
        return []
    failed = []
    for item in smoke.get("serial_checks", []):
        response = item.get("response", {})
        command = str(item.get("command") or "")
        if response.get("kind") != "invalid_reference":
            continue
        if not command.startswith("get "):
            continue
        failed.append(
            {
                "label": item.get("label"),
                "command": command,
                "response_kind": response.get("kind"),
                "response_hex": response.get("hex"),
                "attempt": item.get("attempt"),
                "attempts": item.get("attempts"),
            }
        )
    return failed


def _failed_clicks(smoke: dict[str, Any] | None) -> list[dict[str, Any]]:
    if smoke is None:
        return []
    failed = []
    for item in smoke.get("serial_checks", []):
        command = str(item.get("command") or "")
        if not command.startswith("click "):
            continue
        if item.get("ok", False):
            continue
        response = item.get("response", {})
        failed.append(
            {
                "label": item.get("label"),
                "command": command,
                "response_kind": response.get("kind"),
                "response_hex": response.get("hex"),
                "expected_hex": item.get("expected_hex"),
                "attempt": item.get("attempt"),
                "attempts": item.get("attempts"),
            }
        )
    return failed


def _find_serial_check(smoke: dict[str, Any] | None, *, command: str) -> dict[str, Any] | None:
    if smoke is None:
        return None
    return next((item for item in smoke.get("serial_checks", []) if item.get("command") == command), None)


def _diagnosis(report: dict[str, Any]) -> dict[str, Any]:
    page_switch = report["live_smoke"].get("page_switch") or {}
    sendme = report["live_smoke"].get("sendme") or {}
    failed_lookups = report["live_smoke"].get("failed_runtime_lookups", [])
    failed_clicks = report["live_smoke"].get("failed_clicks", [])
    page_summary = (report.get("event_index_summary") or {}).get("page_summary") or {}
    source_event_slots = int(page_summary.get("source_event_slot_count") or 0)
    compiled_matches = int(page_summary.get("compiled_event_table_match_count") or 0)
    compile_errors = int(page_summary.get("event_compile_error_count") or 0)

    return {
        "page_navigation_ok": bool(page_switch.get("ok")) and bool(sendme.get("ok")),
        "page_runtime_lookup_failed": bool(failed_lookups),
        "event_bytes_compiled": source_event_slots > 0 and compiled_matches > 0 and compile_errors == 0,
        "runtime_event_dispatch_failed": bool(failed_clicks),
        "hash_ids_match_source": bool((report.get("compiled_page_layout") or {}).get("hash_ids_match_source")),
        "mirror_headers_match_source": bool((report.get("compiled_page_layout") or {}).get("mirror_headers_match_source")),
        "likely_layer": "page_local_runtime_binding" if failed_lookups and not compile_errors else "unknown",
        "summary": (
            "Page navigation reached the target page and event bytes compiled. The compiled page1 hash ids and mirror "
            "record headers still match the source objects, but page-local object lookups returned invalid_reference "
            "and click probes did not dispatch. Treat this as a deeper runtime binding failure, not a positive page1 "
            "advanced-control support signal."
        ),
    }


if __name__ == "__main__":
    raise SystemExit(main())
