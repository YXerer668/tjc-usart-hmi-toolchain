from __future__ import annotations

import hashlib
import json
from collections import Counter
import os
from pathlib import Path
import re
from typing import Any, Callable

if os.name == "nt":
    import ctypes
    import msvcrt
    from ctypes import wintypes

from .event_bytecode import decode_event_table
from .hmi_inspect import HMIParseError, PABlockSummary, _parse_entries, inspect_hmi
from .page_format import PageBlock, parse_page_data
from .tft_patch import (
    TYPE_USER_SLOT_COUNTS,
    TYPE_RECORD_HEADER_FLAGS,
    _build_event_compile_context,
    _build_object_event_table,
    _build_page_event_table,
    _build_post_primary_page_event,
    _event_user_slot_count,
    _header,
    _header_int,
)
from .tft_toolchain import TftToolchainError, inspect_tft


CALLBACK_SLOT_OFFSETS = {
    "slot_0x0c": 0x0C,
    "slot_0x10": 0x10,
    "slot_0x14": 0x14,
    "event_offset_0x34": 0x34,
}

EVENT_HEADERS = {
    "codesload": "load",
    "codesloadend": "loadend",
    "codesdown": "down",
    "codesup": "up",
    "codesunload": "unload",
    "codestimer": "timer",
    "codesslide": "slide",
}

EVENT_HEADER_RE = re.compile(r"^(codes[A-Za-z0-9_]+)-(\d+)")
PAGE_LOAD_COMMAND_PREFIXES = (
    ("repo", b"\x09\x18\x08"),
    ("findfile", b"\x09\x29\x08"),
    ("newfile", b"\x09\x19\x08"),
    ("page", b"\x09\x0c\x04"),
)
PAGE_EVENT_PRECEDING_PREVIEW_BYTES = 64
PAGE_EVENT_FOLLOWING_PREVIEW_BYTES = 512

EVENT_INDEX_NOT_CLAIMED = [
    "complete official event compiler compatibility",
    "complete official scheduler/runtime equivalence",
    "hardware runtime proof",
    "safe-to-flash output",
]

if os.name == "nt":
    _GENERIC_READ = 0x80000000
    _FILE_SHARE_READ = 0x00000001
    _FILE_SHARE_WRITE = 0x00000002
    _FILE_SHARE_DELETE = 0x00000004
    _OPEN_EXISTING = 3
    _FILE_ATTRIBUTE_NORMAL = 0x00000080
    _INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

    _CreateFileW = ctypes.windll.kernel32.CreateFileW
    _CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    _CreateFileW.restype = wintypes.HANDLE

    _CloseHandle = ctypes.windll.kernel32.CloseHandle
    _CloseHandle.argtypes = [wintypes.HANDLE]
    _CloseHandle.restype = wintypes.BOOL


def inspect_tft_event_index(
    hmi_path: str | Path,
    tft_path: str | Path,
    *,
    force_post_primary_page_load: bool = False,
    out_path: str | Path | None = None,
) -> dict[str, Any]:
    """Inspect HMI source events against event-index evidence in a TFT/run file.

    This is a read-only reverse-engineering report. It does not upload, patch, or
    prove runtime behavior.
    """

    source_hmi = Path(hmi_path).resolve()
    source_tft = Path(tft_path).resolve()
    page = parse_page_data(_hmi_resource(source_hmi, "0.pa"))
    context, context_error = _probe_compile_context(page.blocks)
    tft_raw = source_tft.read_bytes()
    tft = inspect_tft(source_tft)
    header2 = _header(tft, "Header2")
    object_start = _header_int(header2, "unknown_objects_address")
    if object_start is None:
        raise TftToolchainError("TFT Header2 does not expose unknown_objects_address")
    object_region = tft_raw[object_start:]

    post_primary_page_event, post_primary_error = _try_build_event_table(
        lambda: _build_post_primary_page_event(
            page.blocks,
            context=context,
            force=force_post_primary_page_load,
        )
    )
    post_primary_matches = _all_matches(object_region, post_primary_page_event)
    page_load_command_candidates = _page_load_command_candidates(page.blocks[0], object_region)
    page_event_prefix_probe = _page_event_prefix_probe(page.blocks[0], object_region, context=context)

    block_reports = [
        _block_event_report(
            block,
            index,
            object_region,
            context=context,
            page_name=page.page_name,
        )
        for index, block in enumerate(page.blocks)
    ]
    additional_pages = _additional_page_reports(source_hmi, object_region)
    all_page_summary = _all_page_summary(
        primary_page={"resource": "0.pa", "page_name": page.page_name, "blocks": block_reports},
        additional_pages=additional_pages,
    )
    event_compile_errors = _event_compile_errors(block_reports)
    diagnosis = _diagnose(
        block_reports,
        post_primary_matches=post_primary_matches,
        page_event_prefix_probe=page_event_prefix_probe,
    )
    source_event_slots = [
        slot
        for block in block_reports
        for slot in block.get("source_event_slots", [])
        if int(slot.get("line_count", 0)) > 0
    ]
    compiled_table_matches = sum(len(block.get("event_table_matches", [])) for block in block_reports)
    report: dict[str, Any] = {
        "schema_version": 1,
        "mode": "tft_event_index_inspect",
        "hmi": str(source_hmi),
        "tft": str(source_tft),
        "editor_version": tft.get("editor_version"),
        "model": tft.get("model"),
        "object_start": object_start,
        "object_start_hex": f"0x{object_start:X}",
        "object_region_length": len(object_region),
        "object_region_length_hex": f"0x{len(object_region):X}",
        "page": {
            "name": page.page_name,
            "object_count": len(page.blocks),
        },
        "summary": {
            "source_event_slot_count": len(source_event_slots),
            "compiled_event_table_match_count": compiled_table_matches,
            "post_primary_page_event_match_count": len(post_primary_matches),
            "page_event_prefix_match_count": len(page_event_prefix_probe["matches"]),
            "page_load_phase_match_count": len(page_event_prefix_probe.get("load_phase_matches", [])),
            "page_load_command_candidate_count": len(page_load_command_candidates["matches"]),
            "event_compile_error_count": len(event_compile_errors),
            "scheduler_path": diagnosis["scheduler_path"],
            "compile_context_available": context_error is None,
            "safe_to_flash": False,
        },
        "all_page_summary": all_page_summary,
        "compile_context": {
            "available": context_error is None,
            "error": context_error,
            "unsupported_type_codes": _unsupported_type_codes(page.blocks),
        },
        "post_primary_page_event": {
            "force_post_primary_page_load": force_post_primary_page_load,
            "length": len(post_primary_page_event),
            "error": post_primary_error,
            "hex_prefix": post_primary_page_event[:64].hex(" "),
            "items": decode_event_table(post_primary_page_event),
            "matches": [_offset_item(value) for value in post_primary_matches],
            "descriptors": _post_primary_descriptors(
                object_region,
                post_primary_page_event,
                post_primary_matches,
            ),
            "reference_targets": [
                {
                    "name": "post_primary_page_event_start",
                    "value": value,
                    "value_hex": f"0x{value:X}",
                    "references": [_offset_item(ref) for ref in _all_u32_references(object_region, value)],
                }
                for value in post_primary_matches
            ],
        },
        "page_event_prefix_probe": page_event_prefix_probe,
        "page_load_command_candidates": page_load_command_candidates,
        "blocks": block_reports,
        "additional_pages": additional_pages,
        "event_compile_errors": event_compile_errors,
        "diagnosis": diagnosis,
        "blocking_gaps": _blocking_gaps(
            diagnosis,
            context_error=context_error,
            event_compile_errors=event_compile_errors,
        ),
        "safe_to_flash": False,
        "not_claimed": list(EVENT_INDEX_NOT_CLAIMED),
    }
    if out_path is not None:
        target = Path(out_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["output_json"] = str(target)
    return report


def inspect_tft_event_index_batch(
    paths: list[str | Path] | tuple[str | Path, ...],
    *,
    force_post_primary_page_load: bool = False,
    include_object_only: bool = False,
    out_path: str | Path | None = None,
) -> dict[str, Any]:
    """Scan HMI files and classify nearby TFT/run event-index oracles."""

    hmi_scan = _scan_hmi_event_files([Path(path) for path in paths])
    fixtures = [
        item
        for item in hmi_scan["files"]
        if item.get("parse_ok")
        and (
            int(item.get("page_event_count", 0)) > 0
            or (include_object_only and int(item.get("object_event_count", 0)) > 0)
        )
    ]
    items: list[dict[str, Any]] = []
    for fixture in fixtures:
        hmi_path = Path(fixture["path"])
        candidates = _tft_candidates_for_hmi(hmi_path)
        probes = []
        for candidate in candidates:
            try:
                report = inspect_tft_event_index(
                    hmi_path,
                    candidate["path"],
                    force_post_primary_page_load=force_post_primary_page_load,
                )
                probes.append(_event_index_probe_summary(candidate, report))
            except Exception as exc:  # pragma: no cover - report keeps fixture failures visible.
                probes.append(
                    {
                        "candidate": _candidate_summary(candidate),
                        "ok": False,
                        "error": str(exc),
                    }
                )
        items.append(
            {
                "hmi": str(hmi_path),
                "page_event_count": int(fixture.get("page_event_count", 0)),
                "object_event_count": int(fixture.get("object_event_count", 0)),
                "event_name_counts": fixture.get("event_name_counts", {}),
                "eventful_blocks": fixture.get("eventful_blocks", []),
                "candidate_count": len(candidates),
                "probes": probes,
                "best_probe": _best_event_index_probe(probes),
            }
        )

    report = {
        "schema_version": 1,
        "mode": "tft_event_index_batch",
        "inputs": [str(Path(path).resolve()) for path in paths],
        "summary": _summarize_event_index_batch(hmi_scan, items),
        "hmi_scan_summary": hmi_scan["summary"],
        "items": items,
        "safe_to_flash": False,
        "not_claimed": list(EVENT_INDEX_NOT_CLAIMED),
    }
    if out_path is not None:
        target = Path(out_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["output_json"] = str(target)
    return report


def _block_event_report(
    block: PageBlock,
    index: int,
    object_region: bytes,
    *,
    context: Any,
    page_name: str = "page0",
    scan_empty_events: bool = True,
) -> dict[str, Any]:
    source_event_slots = _source_event_slots(block.event_tokens)
    event_table, event_table_error = _try_build_event_table(
        lambda: (
            _build_page_event_table(block, context=context)
            if index == 0
            else _build_object_event_table(block, context=context)
        )
    )
    has_non_empty_event = any(int(slot.get("line_count", 0)) > 0 for slot in source_event_slots)
    has_non_empty_page_load = any(
        slot.get("event") == "load" and int(slot.get("line_count", 0)) > 0
        for slot in source_event_slots
    )
    event_matches = (
        _all_matches(object_region, event_table)
        if scan_empty_events or has_non_empty_event
        else []
    )
    page_load_phase_matches: list[dict[str, Any]] = []
    if index == 0 and has_non_empty_page_load and not event_matches:
        load_phase_prefix = _page_load_phase_prefix(event_table)
        if load_phase_prefix and load_phase_prefix != event_table:
            page_load_phase_matches = _page_event_prefix_descriptors(
                object_region,
                load_phase_prefix,
                _all_matches(object_region, load_phase_prefix),
            )
    first_executable = _first_executable_offset(event_table)
    reference_targets = _dedupe_reference_targets(
        [
            *_reference_targets(event_matches, len(event_table), first_executable),
            *_page_load_phase_reference_targets(page_load_phase_matches),
        ]
    )
    return {
        "index": index,
        "kind": "page" if index == 0 else "object",
        "page": page_name,
        "objname": block.objname,
        "type_code": _display_type_code(block.type_code),
        "id": _block_id(block),
        "source_event_slots": source_event_slots,
        "event_tokens": list(block.event_tokens),
        "event_table_length": len(event_table),
        "event_table_error": event_table_error,
        "event_table_sha256": hashlib.sha256(event_table).hexdigest() if event_table else None,
        "event_table_hex_prefix": event_table[:64].hex(" "),
        "event_table_items": decode_event_table(event_table),
        "event_table_matches": [_offset_item(value) for value in event_matches],
        "page_load_phase_matches": page_load_phase_matches,
        "first_non_empty_item_offset_in_table": first_executable,
        "first_non_empty_item_offset_in_table_hex": f"0x{first_executable:X}" if first_executable is not None else None,
        "reference_targets": [
            {
                "name": item["name"],
                "value": item["value"],
                "value_hex": f"0x{item['value']:X}",
                "references": [_offset_item(value) for value in _all_u32_references(object_region, item["value"])],
            }
            for item in reference_targets
        ],
        "record_candidates": _record_candidates(object_region, block, reference_targets),
    }


def _scan_hmi_event_files(paths: list[Path]) -> dict[str, Any]:
    files = _collect_hmi_files(paths)
    results = [_scan_hmi_event_file(path) for path in files]
    return {"summary": _summarize_hmi_event_scan(results), "files": results}


def _collect_hmi_files(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []
    for path in paths:
        resolved = path.expanduser().resolve()
        if resolved.is_dir():
            candidates = [
                candidate
                for candidate in resolved.rglob("*")
                if candidate.is_file() and candidate.suffix.lower() == ".hmi"
            ]
        elif resolved.is_file() and resolved.suffix.lower() == ".hmi":
            candidates = [resolved]
        else:
            candidates = []
        for candidate in candidates:
            if candidate not in seen:
                seen.add(candidate)
                files.append(candidate)
    return sorted(files, key=lambda item: str(item).lower())


def _scan_hmi_event_file(path: Path) -> dict[str, Any]:
    try:
        inspection = inspect_hmi(path)
    except (HMIParseError, OSError, ValueError) as exc:
        return {
            "path": str(path),
            "parse_ok": False,
            "error": str(exc),
            "eventful_blocks": [],
            "interesting": False,
        }
    eventful_blocks = [_eventful_block(block) for block in inspection.pa_blocks]
    eventful_blocks = [item for item in eventful_blocks if item is not None]
    page_event_count = sum(1 for block in eventful_blocks if block["role"] == "page")
    object_event_count = sum(1 for block in eventful_blocks if block["role"] == "object")
    event_name_counts = Counter(
        script["name"]
        for block in eventful_blocks
        for script in block["non_empty_events"]
    )
    return {
        "path": str(path),
        "parse_ok": True,
        "entry_count": inspection.entry_count,
        "page_names": inspection.page_names,
        "object_names": inspection.object_names,
        "pa_parse_error": inspection.pa_parse_error,
        "page_event_count": page_event_count,
        "object_event_count": object_event_count,
        "event_name_counts": dict(sorted(event_name_counts.items())),
        "eventful_blocks": eventful_blocks,
        "interesting": bool(page_event_count or object_event_count or inspection.pa_parse_error),
    }


def _eventful_block(block: PABlockSummary) -> dict[str, Any] | None:
    non_empty = [
        {
            "raw_header": script.raw_header,
            "name": script.name,
            "line_count": script.line_count,
            "line_preview": script.lines[:4],
        }
        for script in block.event_scripts
        if script.line_count > 0
    ]
    if not non_empty:
        return None
    return {
        "index": block.index,
        "role": _block_role(block),
        "objname": block.objname,
        "type_code": block.type_code,
        "id": block.fields.get("id"),
        "non_empty_events": non_empty,
    }


def _block_role(block: PABlockSummary) -> str:
    if block.index == 0 or block.type_code == "y" or (block.objname or "").startswith("page"):
        return "page"
    return "object"


def _summarize_hmi_event_scan(results: list[dict[str, Any]]) -> dict[str, Any]:
    parse_ok = sum(1 for item in results if item.get("parse_ok"))
    event_counts = Counter(
        name
        for item in results
        if item.get("parse_ok")
        for name, count in item.get("event_name_counts", {}).items()
        for _ in range(int(count))
    )
    return {
        "scanned": len(results),
        "parse_ok": parse_ok,
        "parse_failed": len(results) - parse_ok,
        "page_event_fixture_count": sum(
            1 for item in results if item.get("parse_ok") and int(item.get("page_event_count", 0)) > 0
        ),
        "object_event_fixture_count": sum(
            1 for item in results if item.get("parse_ok") and int(item.get("object_event_count", 0)) > 0
        ),
        "interesting_count": sum(1 for item in results if item.get("interesting")),
        "event_name_counts": dict(sorted(event_counts.items())),
    }


def _tft_candidates_for_hmi(hmi_path: Path) -> list[dict[str, Any]]:
    case_root = _case_root_for_path(hmi_path)
    stem = hmi_path.stem
    stem_lower = stem.lower()
    raw_candidates: list[tuple[str, Path]] = [
        ("same_dir_same_stem_tft", hmi_path.with_suffix(".tft")),
        ("same_dir_same_stem_TFT", hmi_path.with_suffix(".TFT")),
        ("same_dir_same_stem_run", hmi_path.with_suffix(".run")),
    ]
    if stem_lower == "source_raw":
        raw_candidates.extend(
            [
                ("same_dir_source_raw_tft", hmi_path.parent / "source_raw.tft"),
                ("same_dir_source_raw_run", hmi_path.parent / "source_raw.run"),
            ]
        )
    if case_root is not None:
        if hmi_path.parent.name.lower() == "official_wiki":
            for output_dir in _newest_dirs(hmi_path.parent.glob("official_work_output*")):
                raw_candidates.extend(
                    _official_output_candidates(
                        output_dir,
                        stem,
                        "official_wiki_work_output",
                    )
                )
            raw_candidates.extend(
                _official_output_candidates(
                    hmi_path.parent / "official_compile",
                    stem,
                    "official_wiki_official_compile",
                )
            )
        raw_candidates.extend(
            [
                ("official_compile_same_stem_run", case_root / "official_compile" / f"{stem}.run"),
                ("official_compile_same_stem_tft", case_root / "official_compile" / f"{stem}.tft"),
            ]
        )
        if stem_lower == "source_raw":
            raw_candidates.extend(
                [
                    ("official_compile_source_raw_run", case_root / "official_compile" / "source_raw.run"),
                    ("official_compile_source_raw_tft", case_root / "official_compile" / "source_raw.tft"),
                ]
            )
        for output_dir in _newest_dirs(case_root.glob("official_work_output*")):
            raw_candidates.extend(
                _official_output_candidates(
                    output_dir,
                    stem,
                    "case_work_output",
                )
            )
        if _allow_case_root_lcd_test(hmi_path):
            raw_candidates.append(("case_root_lcd_test_tft", case_root / "lcd_test.tft"))

    seen: set[Path] = set()
    candidates: list[dict[str, Any]] = []
    for reason, path in raw_candidates:
        resolved = path.resolve()
        if resolved in seen or not resolved.exists() or not resolved.is_file():
            continue
        seen.add(resolved)
        candidates.append(
            {
                "path": resolved,
                "reason": reason,
                "confidence": _candidate_confidence(reason),
                "size": resolved.stat().st_size,
            }
        )
    return candidates


def _official_output_candidates(base_dir: Path, stem: str, prefix: str) -> list[tuple[str, Path]]:
    return [
        (f"{prefix}_same_stem_output_tft", base_dir / "output" / f"{stem}.tft"),
        (f"{prefix}_same_stem_run", base_dir / f"{stem}.run"),
        (f"{prefix}_same_stem_tft", base_dir / f"{stem}.tft"),
    ]


def _newest_dirs(paths: Any) -> list[Path]:
    dirs = [path for path in paths if path.is_dir()]
    return sorted(dirs, key=lambda path: (path.stat().st_mtime, path.name.lower()), reverse=True)


def _case_root_for_path(path: Path) -> Path | None:
    for parent in [path, *path.parents]:
        if parent.name.startswith("case_"):
            return parent
    return None


def _allow_case_root_lcd_test(path: Path) -> bool:
    if path.parent.name.lower() in {"official_wiki", "extract"} and path.stem.lower() != "lcd_test":
        return False
    return True


def _candidate_confidence(reason: str) -> str:
    if (
        reason.startswith("same_dir")
        or reason == "official_compile_same_stem_run"
        or reason.startswith("official_wiki_")
        or reason.startswith("case_work_output_")
    ):
        return "high"
    if reason.startswith("official_compile"):
        return "medium"
    return "low"


def _candidate_summary(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": str(candidate["path"]),
        "reason": candidate["reason"],
        "confidence": candidate["confidence"],
        "size": candidate["size"],
    }


def _event_index_probe_summary(candidate: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate": _candidate_summary(candidate),
        "ok": True,
        "complete": _event_index_probe_complete(report),
        "model": report.get("model"),
        "editor_version": report.get("editor_version"),
        "compile_context": report.get("compile_context"),
        "summary": report.get("summary"),
        "all_page_summary": report.get("all_page_summary"),
        "additional_pages": [_compact_additional_page_report(page) for page in report.get("additional_pages", [])],
        "post_primary_page_event": {
            "length": report.get("post_primary_page_event", {}).get("length"),
            "error": report.get("post_primary_page_event", {}).get("error"),
            "matches": report.get("post_primary_page_event", {}).get("matches", []),
            "descriptors": report.get("post_primary_page_event", {}).get("descriptors", []),
        },
        "page_event_prefix_probe": report.get("page_event_prefix_probe", {}),
        "page_load_command_candidates": report.get("page_load_command_candidates", {}),
        "event_compile_errors": report.get("event_compile_errors", []),
        "diagnosis": report.get("diagnosis"),
        "blocking_gaps": report.get("blocking_gaps", []),
    }


def _compact_additional_page_report(page: dict[str, Any]) -> dict[str, Any]:
    return {
        "resource": page.get("resource"),
        "resource_index": page.get("resource_index"),
        "page_name": page.get("page_name"),
        "object_count": page.get("object_count"),
        "compile_context": page.get("compile_context"),
        "summary": page.get("summary"),
        "event_compile_error_examples": [
            _compact_event_compile_error(error)
            for error in page.get("event_compile_errors", [])[:5]
        ],
        "eventful_blocks": [
            {
                "index": block.get("index"),
                "kind": block.get("kind"),
                "page": block.get("page"),
                "objname": block.get("objname"),
                "type_code": block.get("type_code"),
                "event_table_matches": block.get("event_table_matches", []),
                "page_load_phase_matches": [
                    {
                        "offset_hex": item.get("offset_hex"),
                        "prefix_length": item.get("prefix_length"),
                    }
                    for item in block.get("page_load_phase_matches", [])
                ],
                "source_event_slots": _compact_source_event_slots(block.get("source_event_slots", [])),
            }
            for block in page.get("blocks", [])
            if any(int(slot.get("line_count", 0)) > 0 for slot in block.get("source_event_slots", []))
        ],
    }


def _compact_event_compile_error(error: dict[str, Any]) -> dict[str, Any]:
    return {
        "index": error.get("index"),
        "kind": error.get("kind"),
        "objname": error.get("objname"),
        "type_code": error.get("type_code"),
        "event_table_error": error.get("event_table_error"),
        "source_event_slots": _compact_source_event_slots(error.get("source_event_slots", [])),
    }


def _compact_source_event_slots(slots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "event": slot.get("event"),
            "raw_header": slot.get("raw_header"),
            "line_count": slot.get("line_count"),
            "line_preview": slot.get("lines", [])[:4],
        }
        for slot in slots
        if int(slot.get("line_count", 0)) > 0
    ]


def _event_index_probe_complete(report: dict[str, Any]) -> bool:
    diagnosis = report.get("diagnosis", {})
    scheduler_path = report.get("summary", {}).get("scheduler_path")
    return (
        bool(report.get("compile_context", {}).get("available"))
        and int(report.get("summary", {}).get("event_compile_error_count", 0)) == 0
        and scheduler_path != "unbound_or_empty"
        and scheduler_path != "page_event_boundary_without_page_callback"
        and not (diagnosis.get("page_load_non_empty") and scheduler_path == "object_callbacks_only")
    )


def _best_event_index_probe(probes: list[dict[str, Any]]) -> dict[str, Any] | None:
    ok_probes = [probe for probe in probes if probe.get("ok")]
    if not ok_probes:
        return None
    return sorted(ok_probes, key=_event_index_probe_rank)[0]


def _event_index_probe_rank(probe: dict[str, Any]) -> tuple[int, int, int]:
    complete_rank = 0 if probe.get("complete") else 1
    candidate = probe.get("candidate", {})
    confidence_rank = {"high": 0, "medium": 1, "low": 2}.get(candidate.get("confidence"), 3)
    path_rank = {
        "post_primary_page_event": 0,
        "normal_page_table_with_page_callback": 1,
        "normal_page_table_without_page_callback": 2,
        "page_event_boundary_without_page_callback": 3,
        "object_callbacks_only": 4,
        "unbound_or_empty": 5,
    }.get(probe.get("diagnosis", {}).get("scheduler_path"), 5)
    return (complete_rank, confidence_rank, path_rank)


def _summarize_event_index_batch(hmi_scan: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    scheduler_counts = Counter(
        item["best_probe"]["diagnosis"]["scheduler_path"]
        for item in items
        if item.get("best_probe")
    )
    complete_scheduler_counts = Counter(
        item["best_probe"]["diagnosis"]["scheduler_path"]
        for item in items
        if item.get("best_probe") and item["best_probe"].get("complete")
    )
    return {
        "hmi_scanned": hmi_scan["summary"]["scanned"],
        "page_event_hmi_count": sum(1 for item in items if item["page_event_count"] > 0),
        "object_only_hmi_count": sum(
            1 for item in items if item["page_event_count"] == 0 and item["object_event_count"] > 0
        ),
        "items_with_candidates": sum(1 for item in items if item["candidate_count"] > 0),
        "items_with_successful_probe": sum(1 for item in items if item.get("best_probe")),
        "items_with_complete_probe": sum(
            1 for item in items if item.get("best_probe") and item["best_probe"].get("complete")
        ),
        "items_with_dispatch_evidence": sum(
            1
            for item in items
            if item.get("best_probe")
            and item["best_probe"].get("diagnosis", {}).get("scheduler_path") != "unbound_or_empty"
        ),
        "items_with_additional_page_event_matches": sum(
            1
            for item in items
            if item.get("best_probe")
            and int(item["best_probe"].get("all_page_summary", {}).get("additional_page_count", 0)) > 0
            and any(
                int(page.get("compiled_event_table_match_count", 0)) > 0
                for page in item["best_probe"].get("all_page_summary", {}).get("pages", [])[1:]
            )
        ),
        "all_page_compiled_event_table_match_count": sum(
            int(item["best_probe"].get("all_page_summary", {}).get("compiled_event_table_match_count", 0))
            for item in items
            if item.get("best_probe")
        ),
        "all_page_event_compile_error_count": sum(
            int(item["best_probe"].get("all_page_summary", {}).get("event_compile_error_count", 0))
            for item in items
            if item.get("best_probe")
        ),
        "event_compile_error_count": sum(
            len(item["best_probe"].get("event_compile_errors", []))
            for item in items
            if item.get("best_probe")
        ),
        "scheduler_path_counts": dict(sorted(scheduler_counts.items())),
        "complete_scheduler_path_counts": dict(sorted(complete_scheduler_counts.items())),
        "event_compile_error_hmis": [
            {
                "hmi": item["hmi"],
                "count": len(item["best_probe"].get("event_compile_errors", [])),
                "examples": item["best_probe"].get("event_compile_errors", [])[:5],
            }
            for item in items
            if item.get("best_probe") and item["best_probe"].get("event_compile_errors")
        ],
        "no_candidate_hmis": [item["hmi"] for item in items if item["candidate_count"] == 0],
        "no_successful_probe_hmis": [
            item["hmi"]
            for item in items
            if item["candidate_count"] > 0 and item.get("best_probe") is None
        ],
        "incomplete_best_probes": [
            {
                "hmi": item["hmi"],
                "scheduler_path": item["best_probe"]["diagnosis"]["scheduler_path"],
                "compile_context_error": item["best_probe"].get("compile_context", {}).get("error"),
                "blocking_gaps": item["best_probe"].get("blocking_gaps", []),
            }
            for item in items
            if item.get("best_probe") and not item["best_probe"].get("complete")
        ],
    }


def _hmi_resource(path: Path, name: str) -> bytes:
    raw = _read_hmi_bytes(path)
    if len(raw) < 4:
        raise TftToolchainError(f"HMI too small: {path}")
    entry_count = int.from_bytes(raw[:4], "little")
    for entry in _parse_entries(raw, entry_count):
        if entry.name == name and entry.in_file:
            return raw[entry.data_offset : entry.data_offset + entry.length]
    raise TftToolchainError(f"HMI resource {name!r} not found in {path}")


def _additional_page_reports(hmi_path: Path, object_region: bytes) -> list[dict[str, Any]]:
    pages = []
    prior_slot_offset = 0
    for resource in _hmi_page_resources(hmi_path):
        parsed_page: Any | None = None
        if resource["name"] == "0.pa":
            try:
                parsed_page = parse_page_data(resource["data"])
                prior_slot_offset += _event_context_slot_count(parsed_page.blocks)
            except ValueError:
                pass
            continue
        try:
            page = parse_page_data(resource["data"])
            parsed_page = page
        except ValueError as exc:
            event_compile_errors = [
                {
                    "index": None,
                    "kind": "page",
                    "objname": resource["name"],
                    "type_code": None,
                    "event_table_error": str(exc),
                    "source_event_slots": [],
                }
            ]
            pages.append(
                {
                    "resource": resource["name"],
                    "resource_index": resource["resource_index"],
                    "parse_error": str(exc),
                    "compile_context": {"available": False, "error": str(exc), "unsupported_type_codes": []},
                    "summary": {
                        "source_event_slot_count": 0,
                        "compiled_event_table_match_count": 0,
                        "event_compile_error_count": 1,
                    },
                    "blocks": [],
                    "event_compile_errors": event_compile_errors,
                }
            )
            continue
        variant = _best_additional_page_context_report(
            page.blocks,
            object_region,
            page_name=page.page_name,
            global_slot_offset=prior_slot_offset,
        )
        context_error = variant["context_error"]
        block_reports = variant["block_reports"]
        event_compile_errors = variant["event_compile_errors"]
        source_event_slots = [
            slot
            for block in block_reports
            for slot in block.get("source_event_slots", [])
            if int(slot.get("line_count", 0)) > 0
        ]
        pages.append(
            {
                "resource": resource["name"],
                "resource_index": resource["resource_index"],
                "page_name": page.page_name,
                "object_count": len(page.blocks),
                "compile_context": {
                    "available": context_error is None,
                    "error": context_error,
                    "variant": variant["variant"],
                    "slot_offset": variant["slot_offset"],
                    "unsupported_type_codes": _unsupported_type_codes(page.blocks),
                },
                "summary": {
                    "source_event_slot_count": len(source_event_slots),
                    "compiled_event_table_match_count": sum(
                        len(block.get("event_table_matches", [])) for block in block_reports
                    ),
                    "page_load_phase_match_count": sum(
                        len(block.get("page_load_phase_matches", [])) for block in block_reports
                    ),
                    "event_compile_error_count": len(event_compile_errors),
                },
                "event_compile_errors": event_compile_errors,
                "blocks": block_reports,
            }
        )
        if parsed_page is not None:
            prior_slot_offset += _event_context_slot_count(parsed_page.blocks)
    return pages


def _best_additional_page_context_report(
    blocks: list[PageBlock],
    object_region: bytes,
    *,
    page_name: str,
    global_slot_offset: int,
) -> dict[str, Any]:
    variants = [
        _additional_page_context_report(
            blocks,
            object_region,
            page_name=page_name,
            variant="page_local",
            slot_offset=0,
        )
    ]
    if global_slot_offset:
        variants.append(
            _additional_page_context_report(
                blocks,
                object_region,
                page_name=page_name,
                variant="global_slot_offset",
                slot_offset=global_slot_offset,
            )
        )
    return sorted(variants, key=_additional_page_context_rank)[0]


def _additional_page_context_rank(report: dict[str, Any]) -> tuple[int, int, int]:
    match_count = sum(
        len(block.get("event_table_matches", [])) + len(block.get("page_load_phase_matches", []))
        for block in report["block_reports"]
    )
    error_count = len(report["event_compile_errors"])
    variant_rank = 0 if report["variant"] == "page_local" else 1
    return (-match_count, error_count, variant_rank)


def _additional_page_context_report(
    blocks: list[PageBlock],
    object_region: bytes,
    *,
    page_name: str,
    variant: str,
    slot_offset: int,
) -> dict[str, Any]:
    context, context_error = _probe_compile_context(blocks, slot_offset=slot_offset)
    if context_error is None:
        block_reports = [
            _block_event_report(
                block,
                index,
                object_region,
                context=context,
                page_name=page_name,
                scan_empty_events=False,
            )
            for index, block in enumerate(blocks)
        ]
        event_compile_errors = _event_compile_errors(block_reports)
    else:
        block_reports = []
        event_compile_errors = [
            {
                "index": None,
                "kind": "page",
                "objname": page_name,
                "type_code": None,
                "event_table_error": context_error,
                "source_event_slots": [],
            }
        ]
    return {
        "variant": variant,
        "slot_offset": slot_offset,
        "context_error": context_error,
        "block_reports": block_reports,
        "event_compile_errors": event_compile_errors,
    }


def _hmi_page_resources(path: Path) -> list[dict[str, Any]]:
    raw = _read_hmi_bytes(path)
    if len(raw) < 4:
        raise TftToolchainError(f"HMI too small: {path}")
    entry_count = int.from_bytes(raw[:4], "little")
    resources = []
    for entry in _parse_entries(raw, entry_count):
        if not entry.in_file or not entry.name.lower().endswith(".pa"):
            continue
        resources.append(
            {
                "name": entry.name,
                "page_index": _page_resource_index(entry.name),
                "resource_index": entry.index,
                "data": raw[entry.data_offset : entry.data_offset + entry.length],
            }
        )
    return sorted(resources, key=lambda item: (item["page_index"], item["name"]))


def _page_resource_index(name: str) -> int:
    stem = Path(name).stem
    try:
        return int(stem)
    except ValueError:
        return 0x7FFFFFFF


def _read_hmi_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except PermissionError as exc:
        if os.name != "nt":
            raise
        return _read_bytes_windows_shared(path, exc)


def _read_bytes_windows_shared(path: Path, original_exc: PermissionError | None = None) -> bytes:
    if os.name != "nt":
        if original_exc is not None:
            raise original_exc
        raise PermissionError(str(path))

    handle = _CreateFileW(
        str(path),
        _GENERIC_READ,
        _FILE_SHARE_READ | _FILE_SHARE_WRITE | _FILE_SHARE_DELETE,
        None,
        _OPEN_EXISTING,
        _FILE_ATTRIBUTE_NORMAL,
        None,
    )
    if handle == _INVALID_HANDLE_VALUE:
        if original_exc is not None:
            raise original_exc
        raise ctypes.WinError(ctypes.get_last_error())

    try:
        fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | getattr(os, "O_BINARY", 0))
    except OSError:
        _CloseHandle(handle)
        if original_exc is not None:
            raise original_exc
        raise

    with os.fdopen(fd, "rb") as stream:
        return stream.read()


def _all_page_summary(primary_page: dict[str, Any], additional_pages: list[dict[str, Any]]) -> dict[str, Any]:
    pages = [primary_page, *additional_pages]
    source_event_slot_count = 0
    compiled_event_table_match_count = 0
    event_compile_error_count = 0
    pages_with_event_matches = 0
    eventful_pages = 0
    page_summaries = []
    for page in pages:
        blocks = page.get("blocks", [])
        source_slots = [
            slot
            for block in blocks
            for slot in block.get("source_event_slots", [])
            if int(slot.get("line_count", 0)) > 0
        ]
        match_count = sum(len(block.get("event_table_matches", [])) for block in blocks)
        phase_match_count = sum(len(block.get("page_load_phase_matches", [])) for block in blocks)
        compile_errors = page.get("event_compile_errors", [])
        source_event_slot_count += len(source_slots)
        compiled_event_table_match_count += match_count
        event_compile_error_count += len(compile_errors)
        if source_slots:
            eventful_pages += 1
        if match_count:
            pages_with_event_matches += 1
        page_summaries.append(
            {
                "resource": page.get("resource"),
                "page_name": page.get("page_name"),
                "source_event_slot_count": len(source_slots),
                "compiled_event_table_match_count": match_count,
                "page_load_phase_match_count": phase_match_count,
                "event_compile_error_count": len(compile_errors),
            }
        )
    return {
        "page_count": len(pages),
        "additional_page_count": len(additional_pages),
        "eventful_page_count": eventful_pages,
        "pages_with_event_matches": pages_with_event_matches,
        "source_event_slot_count": source_event_slot_count,
        "compiled_event_table_match_count": compiled_event_table_match_count,
        "event_compile_error_count": event_compile_error_count,
        "pages": page_summaries,
    }


def _probe_compile_context(blocks: list[PageBlock], *, slot_offset: int = 0) -> tuple[Any, str | None]:
    try:
        context = _build_event_compile_context(blocks)
        if slot_offset:
            context.field_slot_by_ref = {
                key: value + slot_offset
                for key, value in context.field_slot_by_ref.items()
            }
        return context, None
    except (KeyError, TftToolchainError) as exc:
        return None, str(exc)


def _event_context_slot_count(blocks: list[PageBlock]) -> int:
    has_file_browser_widget = any(block.type_code == "A" for block in blocks)
    return sum(_event_user_slot_count(block, has_file_browser_widget=has_file_browser_widget) for block in blocks)


def _try_build_event_table(builder: Callable[[], bytes]) -> tuple[bytes, str | None]:
    try:
        return builder(), None
    except (KeyError, TftToolchainError) as exc:
        return b"", str(exc)


def _source_event_slots(tokens: list[str]) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        match = EVENT_HEADER_RE.match(token.rstrip("&"))
        if not match:
            index += 1
            continue
        raw_name, count_text = match.groups()
        line_count = int(count_text)
        lines = tokens[index + 1 : index + 1 + line_count]
        slots.append(
            {
                "event": EVENT_HEADERS.get(raw_name, raw_name),
                "raw_header": token,
                "line_count": line_count,
                "lines": lines,
            }
        )
        index += 1 + line_count
    return slots


def _unsupported_type_codes(blocks: list[PageBlock]) -> list[str]:
    values = {
        _display_type_code(block.type_code)
        for block in blocks
        if block.type_code is not None and block.type_code not in TYPE_USER_SLOT_COUNTS
    }
    return sorted(value for value in values if value is not None)


def _event_compile_errors(block_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    errors = []
    for block in block_reports:
        error = block.get("event_table_error")
        if not error:
            continue
        non_empty_slots = [
            slot
            for slot in block.get("source_event_slots", [])
            if int(slot.get("line_count", 0)) > 0
        ]
        errors.append(
            {
                "index": block.get("index"),
                "kind": block.get("kind"),
                "objname": block.get("objname"),
                "type_code": block.get("type_code"),
                "event_table_error": error,
                "source_event_slots": non_empty_slots,
            }
        )
    return errors


def _record_candidates(region: bytes, block: PageBlock, targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    block_id = _block_id(block)
    if block.type_code is None or block_id is None:
        return []
    header_flag = TYPE_RECORD_HEADER_FLAGS.get(block.type_code, 0x37)
    header = block.type_code.encode("latin1") + int(block_id).to_bytes(1, "little") + bytes([0, header_flag])
    offsets = _all_matches(region, header)
    target_values = {item["value"] for item in targets}
    candidates = []
    for offset in offsets:
        record = region[offset : offset + 0x60]
        slots = {}
        for name, slot_offset in CALLBACK_SLOT_OFFSETS.items():
            if len(record) < slot_offset + 4:
                continue
            value = int.from_bytes(record[slot_offset : slot_offset + 4], "little")
            slots[name] = {
                "offset": slot_offset,
                "offset_hex": f"0x{slot_offset:X}",
                "value": value,
                "value_hex": f"0x{value:X}",
                "raw_hex": record[slot_offset : slot_offset + 4].hex(" "),
                "points_to_event_target": value in target_values,
                "event_target_matches": _slot_target_matches(value, targets),
            }
        candidates.append(
            {
                "relative_offset": offset,
                "relative_offset_hex": f"0x{offset:X}",
                "header_hex": header.hex(" "),
                "slots": slots,
            }
        )
    return candidates


def _reference_targets(
    matches: list[int],
    event_table_length: int,
    first_executable: int | None,
) -> list[dict[str, Any]]:
    targets = []
    for match in matches:
        targets.append(
            {
                "name": "event_table_start",
                "value": match,
                "table_start": match,
                "table_end": match + event_table_length,
            }
        )
        if first_executable is not None and first_executable < event_table_length:
            targets.append(
                {
                    "name": "first_executable",
                    "value": match + first_executable,
                    "table_start": match,
                    "table_end": match + event_table_length,
                }
            )
    return _dedupe_reference_targets(targets)


def _page_load_phase_reference_targets(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    targets = []
    for match in matches:
        start = match.get("offset")
        end = match.get("end")
        if start is None or end is None:
            continue
        targets.append(
            {
                "name": "page_load_phase_start",
                "value": int(start),
                "table_start": int(start),
                "table_end": int(end),
            }
        )
        first_executable = match.get("first_executable_absolute")
        if first_executable is not None:
            targets.append(
                {
                    "name": "page_load_phase_first_executable",
                    "value": int(first_executable),
                    "table_start": int(start),
                    "table_end": int(end),
                }
            )
    return _dedupe_reference_targets(targets)


def _dedupe_reference_targets(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for item in targets:
        key = (item["name"], item["value"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def _slot_target_matches(value: int, targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matches = []
    for target in targets:
        table_start = int(target.get("table_start", target["value"]))
        table_end = int(target.get("table_end", target["value"] + 1))
        exact = value == target["value"]
        inside_table = table_start <= value < table_end
        if not exact and not inside_table:
            continue
        matches.append(
            {
                "name": target["name"],
                "exact": exact,
                "inside_event_table": inside_table,
                "delta_from_table_start": value - table_start,
                "delta_hex": f"0x{value - table_start:X}",
            }
        )
    return matches


def _post_primary_descriptors(
    region: bytes,
    event_table: bytes,
    matches: list[int],
) -> list[dict[str, Any]]:
    descriptors = []
    first_executable = _first_executable_offset(event_table)
    payload_hash = hashlib.sha256(event_table).hexdigest() if event_table else None
    for offset in matches:
        end = offset + len(event_table)
        first_executable_abs = offset + first_executable if first_executable is not None else None
        descriptors.append(
            {
                "offset": offset,
                "offset_hex": f"0x{offset:X}",
                "end": end,
                "end_hex": f"0x{end:X}",
                "length": len(event_table),
                "payload_sha256": payload_hash,
                "item_count": len(decode_event_table(event_table)),
                "first_executable_offset": first_executable,
                "first_executable_offset_hex": f"0x{first_executable:X}" if first_executable is not None else None,
                "first_executable_absolute": first_executable_abs,
                "first_executable_absolute_hex": f"0x{first_executable_abs:X}" if first_executable_abs is not None else None,
                "references": {
                    "table_start": [_offset_item(value) for value in _all_u32_references(region, offset)],
                    "first_executable": (
                        [_offset_item(value) for value in _all_u32_references(region, first_executable_abs)]
                        if first_executable_abs is not None
                        else []
                    ),
                },
                "context_before_hex": region[max(0, offset - 32) : offset].hex(" "),
                "context_after_hex": region[end : min(len(region), end + 32)].hex(" "),
            }
        )
    return descriptors


def _page_event_prefix_probe(
    block: PageBlock,
    region: bytes,
    *,
    context: Any,
) -> dict[str, Any]:
    event_table, error = _try_build_event_table(lambda: _build_page_event_table(block, context=context))
    prefix = _drop_final_empty_item(event_table)
    load_phase_prefix = _page_load_phase_prefix(event_table)
    if error is not None or not prefix or prefix == event_table:
        return {
            "length": len(event_table),
            "prefix_length": len(prefix),
            "load_phase_prefix_length": len(load_phase_prefix),
            "error": error,
            "matches": [],
            "load_phase_matches": [],
        }
    full_matches = _all_matches(region, event_table)
    prefix_matches = [] if full_matches else _all_matches(region, prefix)
    load_phase_matches: list[int] = []
    if (
        not full_matches
        and load_phase_prefix
        and load_phase_prefix not in {event_table, prefix}
    ):
        load_phase_matches = _all_matches(region, load_phase_prefix)
    return {
        "length": len(event_table),
        "prefix_length": len(prefix),
        "load_phase_prefix_length": len(load_phase_prefix),
        "error": error,
        "full_matches": [_offset_item(value) for value in full_matches],
        "matches": _page_event_prefix_descriptors(region, prefix, prefix_matches),
        "load_phase_matches": _page_event_prefix_descriptors(
            region,
            load_phase_prefix,
            load_phase_matches,
        ),
    }


def _drop_final_empty_item(event_table: bytes) -> bytes:
    if len(event_table) >= 4 and event_table[-4:] == b"\x00\x00\x00\x00":
        return event_table[:-4]
    return event_table


def _page_load_phase_prefix(event_table: bytes) -> bytes:
    down_marker = b"\x04\x00\x00\x00down"
    index = event_table.find(down_marker)
    if index <= 0:
        return b""
    return event_table[:index]


def _page_event_prefix_descriptors(region: bytes, prefix: bytes, matches: list[int]) -> list[dict[str, Any]]:
    descriptors = []
    payload_hash = hashlib.sha256(prefix).hexdigest() if prefix else None
    first_executable = _first_executable_offset(prefix)
    for offset in matches:
        end = offset + len(prefix)
        first_executable_abs = offset + first_executable if first_executable is not None else None
        head_window = region[max(0, offset - PAGE_EVENT_PRECEDING_PREVIEW_BYTES) : offset]
        tail_window = region[end : min(len(region), end + PAGE_EVENT_FOLLOWING_PREVIEW_BYTES)]
        tail_preview = _complete_event_table_preview(tail_window)
        tail_items = tail_preview["items"]
        immediate_hidden_items = _initial_hidden_event_items(tail_items)
        descriptors.append(
            {
                "offset": offset,
                "offset_hex": f"0x{offset:X}",
                "end": end,
                "end_hex": f"0x{end:X}",
                "prefix_length": len(prefix),
                "prefix_sha256": payload_hash,
                "first_executable_offset": first_executable,
                "first_executable_offset_hex": f"0x{first_executable:X}" if first_executable is not None else None,
                "first_executable_absolute": first_executable_abs,
                "first_executable_absolute_hex": f"0x{first_executable_abs:X}" if first_executable_abs is not None else None,
                "prefix_items": decode_event_table(prefix),
                "immediate_hidden_items": immediate_hidden_items,
                "head_hex_suffix": head_window.hex(" "),
                "head_preview_bytes": len(head_window),
                "tail_hex_prefix": tail_window[:80].hex(" "),
                "tail_preview_bytes": len(tail_window),
                "tail_decoded_bytes": tail_preview["decoded_bytes"],
                "tail_decoded_bytes_hex": tail_preview["decoded_bytes_hex"],
                "tail_preview_truncated": tail_preview["truncated"],
                "tail_next_item_length": tail_preview["next_item_length"],
                "tail_next_item_length_hex": tail_preview["next_item_length_hex"],
                "tail_items": tail_items,
                "references": {
                    "prefix_start": [_offset_item(value) for value in _all_u32_references(region, offset)],
                    "first_executable": [
                        _offset_item(value) for value in _all_u32_references(region, first_executable_abs)
                    ],
                    "prefix_end": [_offset_item(value) for value in _all_u32_references(region, end)],
                },
            }
        )
    return descriptors


def _complete_event_table_preview(data: bytes) -> dict[str, Any]:
    cursor = 0
    while cursor + 4 <= len(data):
        length = int.from_bytes(data[cursor : cursor + 4], "little")
        next_cursor = cursor + 4 + length
        if next_cursor > len(data):
            break
        cursor = next_cursor
    next_item_length = int.from_bytes(data[cursor : cursor + 4], "little") if cursor + 4 <= len(data) else None
    return {
        "decoded_bytes": cursor,
        "decoded_bytes_hex": f"0x{cursor:X}",
        "truncated": cursor < len(data),
        "next_item_length": next_item_length,
        "next_item_length_hex": f"0x{next_item_length:X}" if next_item_length is not None else None,
        "items": decode_event_table(data[:cursor]),
    }


def _initial_hidden_event_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hidden_items = []
    for item in items:
        if item.get("kind") in {"empty", "marker"}:
            break
        hidden_items.append(item)
    return hidden_items


def _page_load_command_candidates(block: PageBlock, region: bytes) -> dict[str, Any]:
    source_commands = _page_load_source_commands(block)
    descriptors = []
    seen: set[tuple[str, int]] = set()
    for command in source_commands:
        prefix = bytes.fromhex(command["prefix_hex"])
        for payload_offset in _all_matches(region, prefix):
            item_offset = payload_offset - 4
            if item_offset < 0:
                continue
            length = int.from_bytes(region[item_offset:payload_offset], "little")
            if length < len(prefix) or payload_offset + length > len(region):
                continue
            payload = region[payload_offset : payload_offset + length]
            if not payload.startswith(prefix):
                continue
            key = (command["command"], item_offset)
            if key in seen:
                continue
            seen.add(key)
            descriptors.append(
                {
                    "command": command["command"],
                    "source_line": command["source_line"],
                    "item_offset": item_offset,
                    "item_offset_hex": f"0x{item_offset:X}",
                    "payload_offset": payload_offset,
                    "payload_offset_hex": f"0x{payload_offset:X}",
                    "length": length,
                    "payload_hex": payload.hex(" "),
                    "decoded": decode_event_table(region[item_offset : payload_offset + length])[0],
                    "context_before_hex": region[max(0, item_offset - 16) : item_offset].hex(" "),
                    "context_after_hex": region[payload_offset + length : min(len(region), payload_offset + length + 32)].hex(" "),
                }
            )
    return {
        "source_commands": source_commands,
        "matches": sorted(descriptors, key=lambda item: (item["item_offset"], item["command"])),
    }


def _page_load_source_commands(block: PageBlock) -> list[dict[str, Any]]:
    commands = []
    for slot in _source_event_slots(block.event_tokens):
        if slot.get("event") != "load":
            continue
        for line in slot.get("lines", []):
            stripped = line.split("//", 1)[0].strip()
            lowered = stripped.lower()
            for command, prefix in PAGE_LOAD_COMMAND_PREFIXES:
                if lowered == command or lowered.startswith(command + " "):
                    commands.append(
                        {
                            "command": command,
                            "source_line": line,
                            "prefix_hex": prefix.hex(" "),
                        }
                    )
                    break
    return commands


def _first_executable_offset(event_table: bytes) -> int | None:
    cursor = 0
    while cursor + 4 <= len(event_table):
        length = int.from_bytes(event_table[cursor : cursor + 4], "little")
        payload_start = cursor + 4
        payload_end = payload_start + length
        if payload_end > len(event_table):
            return None
        payload = event_table[payload_start:payload_end]
        if payload.startswith(b"\x09") or payload.startswith(b"\x01") or payload.startswith(b"\x04"):
            return cursor
        cursor = payload_end
    return None


def _all_matches(data: bytes, needle: bytes) -> list[int]:
    if not needle:
        return []
    offsets = []
    start = 0
    while True:
        found = data.find(needle, start)
        if found < 0:
            return offsets
        offsets.append(found)
        start = found + 1


def _all_u32_references(data: bytes, value: int | None) -> list[int]:
    if value is None or value < 0 or value > 0xFFFFFFFF:
        return []
    return _all_matches(data, value.to_bytes(4, "little"))


def _offset_item(value: int) -> dict[str, Any]:
    return {"value": value, "hex": f"0x{value:X}"}


def _display_type_code(type_code: str | None) -> str | None:
    if type_code is None:
        return None
    return type_code if type_code.isprintable() else f"0x{ord(type_code):02X}"


def _block_id(block: PageBlock) -> int | None:
    field = block.get_field("id")
    if field is None or not field.value:
        return None
    return int.from_bytes(field.value, "little")


def _is_callback_slot(name: str) -> bool:
    return name.startswith("slot_")


def _diagnose(
    block_reports: list[dict[str, Any]],
    *,
    post_primary_matches: list[int],
    page_event_prefix_probe: dict[str, Any] | None = None,
) -> dict[str, Any]:
    page = block_reports[0] if block_reports else None
    page_load_non_empty = False
    if page:
        page_load_non_empty = any(
            token.startswith(("codesload-", "codesloadend-")) and not token.endswith("-0")
            for token in page["event_tokens"]
        )
    page_load_phase_matches = (page_event_prefix_probe or {}).get("load_phase_matches", [])
    page_load_phase_found = bool(page_load_phase_matches)
    page_callbacks = _slot_refs(block_reports[:1], callback_slots_only=True)
    object_callbacks = _slot_refs(block_reports[1:], callback_slots_only=True)
    page_event_offsets = _slot_refs(block_reports[:1], names={"event_offset_0x34"})
    page_event_offset_candidates = _slot_refs(
        block_reports[:1],
        names={"event_offset_0x34"},
        require_target_match=False,
        include_values=True,
    )
    object_event_offsets = _slot_refs(block_reports[1:], names={"event_offset_0x34"})
    scheduler_path = _scheduler_path(
        page_load_non_empty=page_load_non_empty,
        page_event_table_found=bool(page and page["event_table_matches"]),
        page_load_phase_found=page_load_phase_found,
        post_primary_page_event_found=bool(post_primary_matches),
        page_callbacks=page_callbacks,
        object_callbacks=object_callbacks,
        page_event_offsets=page_event_offsets,
        page_event_offset_candidates=page_event_offset_candidates,
    )
    return {
        "page_load_non_empty": page_load_non_empty,
        "page_event_table_found": bool(page and page["event_table_matches"]),
        "page_load_phase_found": page_load_phase_found,
        "page_load_phase_refs": [
            {
                "offset_hex": item.get("offset_hex"),
                "prefix_length": item.get("prefix_length"),
                "prefix_sha256": item.get("prefix_sha256"),
            }
            for item in page_load_phase_matches
        ],
        "post_primary_page_event_found": bool(post_primary_matches),
        "page_callback_like_slots": page_callbacks,
        "object_callback_like_slots": object_callbacks,
        "page_event_offset_0x34_refs": page_event_offsets,
        "page_event_offset_0x34_candidates": page_event_offset_candidates,
        "object_event_offset_0x34_refs": object_event_offsets,
        "scheduler_path": scheduler_path,
        "upload_risk": _upload_risk(scheduler_path),
        "recommended_writer_action": _recommended_writer_action(scheduler_path),
        "interpretation": _interpretation(
            page_load_non_empty=page_load_non_empty,
            page_event_table_found=bool(page and page["event_table_matches"]),
            page_load_phase_found=page_load_phase_found,
            post_primary_page_event_found=bool(post_primary_matches),
            page_callbacks=page_callbacks,
            object_callbacks=object_callbacks,
            page_event_offsets=page_event_offsets,
            page_event_offset_candidates=page_event_offset_candidates,
        ),
    }


def _slot_refs(
    block_reports: list[dict[str, Any]],
    *,
    names: set[str] | None = None,
    callback_slots_only: bool = False,
    require_target_match: bool = True,
    include_values: bool = False,
) -> list[dict[str, Any]]:
    refs = []
    for block in block_reports:
        for candidate in block["record_candidates"]:
            slots = [
                name
                for name, slot in candidate["slots"].items()
                if (slot.get("points_to_event_target") or not require_target_match)
                and (names is None or name in names)
                and (not callback_slots_only or _is_callback_slot(name))
                and (
                    require_target_match
                    or slot.get("value") not in (None, 0, 0xFFFFFFFF)
                )
            ]
            if slots:
                item = {
                    "record_offset_hex": candidate["relative_offset_hex"],
                    "slots": slots,
                }
                if block.get("objname") is not None:
                    item["objname"] = block["objname"]
                if include_values:
                    item["values"] = [
                        {
                            "slot": name,
                            "value": candidate["slots"][name].get("value"),
                            "value_hex": candidate["slots"][name].get("value_hex"),
                            "points_to_event_target": candidate["slots"][name].get("points_to_event_target"),
                        }
                        for name in slots
                    ]
                refs.append(item)
    return refs


def _scheduler_path(
    *,
    page_load_non_empty: bool,
    page_event_table_found: bool,
    page_load_phase_found: bool,
    post_primary_page_event_found: bool,
    page_callbacks: list[dict[str, Any]],
    object_callbacks: list[dict[str, Any]],
    page_event_offsets: list[dict[str, Any]],
    page_event_offset_candidates: list[dict[str, Any]],
) -> str:
    if page_load_non_empty and post_primary_page_event_found:
        return "post_primary_page_event"
    if page_load_non_empty and page_event_table_found and page_event_offsets and not page_callbacks:
        return "normal_page_table_without_page_callback"
    if page_load_non_empty and page_load_phase_found and page_event_offset_candidates and not page_callbacks:
        return "page_event_boundary_without_page_callback"
    if page_load_non_empty and page_callbacks:
        return "normal_page_table_with_page_callback"
    if object_callbacks:
        return "object_callbacks_only"
    return "unbound_or_empty"


def _upload_risk(scheduler_path: str) -> str:
    return {
        "post_primary_page_event": "research_only",
        "normal_page_table_without_page_callback": "high",
        "page_event_boundary_without_page_callback": "high",
        "normal_page_table_with_page_callback": "medium",
        "object_callbacks_only": "low_for_object_events_only",
        "unbound_or_empty": "unknown",
    }.get(scheduler_path, "unknown")


def _recommended_writer_action(scheduler_path: str) -> str:
    if scheduler_path == "post_primary_page_event":
        return (
            "Keep page-load generation fixture-gated: official media-style TFTs relocate page-load bytecode "
            "into a post-primary chunk, so do not burn an ad-hoc page-load build until this chunk is reproduced "
            "byte-for-byte for the target layout."
        )
    if scheduler_path == "normal_page_table_without_page_callback":
        return (
            "Do not burn callback-slot guesses. The normal page event table exists, but no recovered page-level "
            "callback cache points at executable code; compare against an official page-load oracle first."
        )
    if scheduler_path == "page_event_boundary_without_page_callback":
        return (
            "Keep page-load generation fixture-gated. A page record event_offset_0x34 boundary is visible, "
            "but no page callback slot points to the lifecycle first executable; runtime entry from the wrapper "
            "still needs official or live proof."
        )
    if scheduler_path == "normal_page_table_with_page_callback":
        return "Inspect the referenced descriptor and then validate on hardware with a minimal recovery TFT ready."
    if scheduler_path == "object_callbacks_only":
        return "Continue object-event bytecode work; this fixture does not prove page-load scheduling."
    return "Collect a smaller official oracle before adding writer behavior."


def _interpretation(
    *,
    page_load_non_empty: bool,
    page_event_table_found: bool,
    page_load_phase_found: bool,
    post_primary_page_event_found: bool,
    page_callbacks: list[dict[str, Any]],
    object_callbacks: list[dict[str, Any]],
    page_event_offsets: list[dict[str, Any]],
    page_event_offset_candidates: list[dict[str, Any]],
) -> str:
    if page_load_non_empty and post_primary_page_event_found:
        return (
            "Official-style media page-load bytecode is present after the primary records. "
            "Do not expect the normal page event table search alone to find codesload."
        )
    if page_load_non_empty and page_event_table_found and page_event_offsets and not page_callbacks:
        return (
            "Page-load bytecode is present and the mirror event_offset_0x34 points to the page event table, "
            "but no recovered callback-cache slot points to the executable item. The page-load scheduler path "
            "is still separate from object click/timer callback caches."
        )
    if page_load_non_empty and page_load_phase_found and page_event_offset_candidates and not page_callbacks:
        return (
            "Page-load bytecode is present inline and page record event_offset_0x34 points to a page "
            "event-table or wrapper boundary, but no recovered page callback-cache slot points to the "
            "lifecycle first executable. Runtime entry from the wrapper is still unmapped."
        )
    if page_load_non_empty and page_load_phase_found and not page_callbacks:
        return (
            "Page-load bytecode is present inline in the object region, but no recovered callback-cache "
            "or page event-offset reference points to its executable item. Runtime scheduling is still unmapped."
        )
    if page_load_non_empty and not page_callbacks and object_callbacks:
        return (
            "Page-load bytecode is present and object callbacks are visible, "
            "but no page callback-like slot points to the page event table. "
            "Compare against an official page-load oracle."
        )
    if page_load_non_empty and page_callbacks:
        return "A page callback-like reference exists; inspect the referenced descriptor and live behavior."
    if object_callbacks:
        return "Object event callback-like references are visible; page load is empty or not the target of this fixture."
    return "No callback-like references were found by this narrow probe."


def _blocking_gaps(
    diagnosis: dict[str, Any],
    *,
    context_error: str | None,
    event_compile_errors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    if context_error is not None:
        gaps.append(
            {
                "code": "EVENT_COMPILE_CONTEXT_UNAVAILABLE",
                "message": "The source HMI contains object types or event references the local event table builder cannot map yet.",
                "detail": context_error,
            }
        )
    if event_compile_errors:
        gaps.append(
            {
                "code": "EVENT_BYTECODE_UNSUPPORTED_LINES",
                "message": "One or more non-empty source event slots contain commands the local minimal bytecode compiler does not support yet.",
                "count": len(event_compile_errors),
                "examples": event_compile_errors[:5],
            }
        )
    scheduler_path = diagnosis.get("scheduler_path")
    if scheduler_path in {
        "post_primary_page_event",
        "normal_page_table_without_page_callback",
        "page_event_boundary_without_page_callback",
        "unbound_or_empty",
    } or (
        diagnosis.get("page_load_non_empty") and scheduler_path == "object_callbacks_only"
    ):
        gaps.append(
            {
                "code": "SCHEDULER_RUNTIME_EQUIVALENCE_UNPROVEN",
                "message": "The report locates event bytes but does not prove complete official runtime scheduling.",
                "scheduler_path": scheduler_path,
            }
        )
    if scheduler_path == "unbound_or_empty":
        gaps.append(
            {
                "code": "EVENT_DISPATCH_UNMAPPED",
                "message": "No callback-like compiled dispatch reference was found for this fixture.",
            }
        )
    return gaps
