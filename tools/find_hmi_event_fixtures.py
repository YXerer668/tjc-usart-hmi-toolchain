from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from usarthmi.hmi_inspect import HMIParseError, PAEventScript, PABlockSummary, inspect_hmi

PAGE_EVENT_NAMES = {
    "codesload",
    "codesloadend",
    "codesdown",
    "codesup",
    "codesunload",
}
EVENT_HEADER_RE = re.compile(r"^(codes[A-Za-z0-9_]+)-(\d+)")


def scan_paths(paths: list[Path]) -> dict[str, Any]:
    files = _collect_hmi_files(paths)
    results = [_scan_file(path) for path in files]
    summary = _summarize_results(results)
    return {"summary": summary, "files": results}


def _collect_hmi_files(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []
    for path in paths:
        resolved = path.expanduser().resolve()
        candidates: list[Path]
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


def _scan_file(path: Path) -> dict[str, Any]:
    try:
        inspection = inspect_hmi(path)
    except (HMIParseError, OSError, ValueError) as exc:
        return {
            "path": str(path),
            "parse_ok": False,
            "error": str(exc),
            "eventful_blocks": [],
            "fallback_event_tokens": [],
            "interesting": False,
        }

    eventful_blocks = [_eventful_block(block) for block in inspection.pa_blocks]
    eventful_blocks = [item for item in eventful_blocks if item is not None]
    fallback_tokens = _fallback_event_tokens(inspection.pa_strings)
    page_event_count = sum(1 for block in eventful_blocks if block["role"] == "page")
    object_event_count = sum(1 for block in eventful_blocks if block["role"] == "object")
    event_name_counts = Counter(
        script["name"]
        for block in eventful_blocks
        for script in block["non_empty_events"]
    )
    interesting = bool(page_event_count or object_event_count or fallback_tokens or inspection.pa_parse_error)

    return {
        "path": str(path),
        "parse_ok": True,
        "entry_count": inspection.entry_count,
        "page_names": inspection.page_names,
        "object_names": inspection.object_names,
        "property_names": inspection.property_names,
        "pa_parse_error": inspection.pa_parse_error,
        "page_event_count": page_event_count,
        "object_event_count": object_event_count,
        "event_name_counts": dict(sorted(event_name_counts.items())),
        "eventful_blocks": eventful_blocks,
        "fallback_event_tokens": fallback_tokens,
        "interesting": interesting,
    }


def _eventful_block(block: PABlockSummary) -> dict[str, Any] | None:
    non_empty = [_script_summary(script) for script in block.event_scripts if script.line_count > 0]
    if not non_empty:
        return None
    role = _block_role(block)
    return {
        "index": block.index,
        "role": role,
        "objname": block.objname,
        "type_code": block.type_code,
        "id": block.fields.get("id"),
        "x": block.fields.get("x"),
        "y": block.fields.get("y"),
        "w": block.fields.get("w"),
        "h": block.fields.get("h"),
        "non_empty_events": non_empty,
    }


def _block_role(block: PABlockSummary) -> str:
    if block.index == 0 or block.type_code == "y" or (block.objname or "").startswith("page"):
        return "page"
    return "object"


def _script_summary(script: PAEventScript) -> dict[str, Any]:
    return {
        "raw_header": script.raw_header,
        "name": script.name,
        "line_count": script.line_count,
        "is_page_event_name": script.name in PAGE_EVENT_NAMES,
        "line_preview": script.lines[:4],
    }


def _fallback_event_tokens(pa_strings: list[Any]) -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    for item in pa_strings:
        text = item.text.strip()
        match = EVENT_HEADER_RE.match(text)
        if match is not None and int(match.group(2)) > 0:
            tokens.append({"offset": item.offset, "offset_hex": f"0x{item.offset:X}", "text": text})
    return tokens[:80]


def _summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    parse_ok = sum(1 for item in results if item.get("parse_ok"))
    page_event_files = [
        item["path"]
        for item in results
        if item.get("parse_ok") and int(item.get("page_event_count", 0)) > 0
    ]
    object_event_files = [
        item["path"]
        for item in results
        if item.get("parse_ok") and int(item.get("object_event_count", 0)) > 0
    ]
    pa_parse_errors = [
        {"path": item["path"], "error": item.get("pa_parse_error")}
        for item in results
        if item.get("parse_ok") and item.get("pa_parse_error")
    ]
    container_errors = [
        {"path": item["path"], "error": item.get("error")}
        for item in results
        if not item.get("parse_ok")
    ]
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
        "pa_parse_error_count": len(pa_parse_errors),
        "page_event_fixture_count": len(page_event_files),
        "object_event_fixture_count": len(object_event_files),
        "interesting_count": sum(1 for item in results if item.get("interesting")),
        "event_name_counts": dict(sorted(event_counts.items())),
        "page_event_files": page_event_files,
        "object_event_files": object_event_files,
        "pa_parse_errors": pa_parse_errors,
        "container_errors": container_errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan HMI fixtures for non-empty page/object event scripts.",
    )
    parser.add_argument("paths", nargs="+", type=Path, help="HMI files or directories to scan recursively")
    parser.add_argument("--out", type=Path, help="Write JSON report to this path")
    parser.add_argument("--compact", action="store_true", help="Emit compact JSON")
    args = parser.parse_args(argv)

    report = scan_paths(args.paths)
    indent = None if args.compact else 2
    text = json.dumps(report, ensure_ascii=False, indent=indent)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
