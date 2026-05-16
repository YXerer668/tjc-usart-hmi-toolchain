from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from usarthmi.hmi_inspect import HMIParseError, PABlockSummary, inspect_hmi


def scan_timer_oracles(paths: list[Path]) -> dict[str, Any]:
    files = _collect_hmi_files(paths)
    reports = [_scan_hmi(path) for path in files]
    return {
        "summary": _summary(reports),
        "files": reports,
    }


def _collect_hmi_files(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []
    for path in paths:
        resolved = path.expanduser().resolve()
        if resolved.is_dir():
            candidates = [
                item
                for item in resolved.rglob("*")
                if item.is_file() and item.suffix.lower() == ".hmi"
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


def _scan_hmi(path: Path) -> dict[str, Any]:
    try:
        inspection = inspect_hmi(path)
    except (HMIParseError, OSError, ValueError) as exc:
        return {
            "path": str(path),
            "parse_ok": False,
            "error": str(exc),
            "timer_blocks": [],
            "interesting": False,
        }

    timer_blocks = [_timer_block_summary(block) for block in inspection.pa_blocks]
    timer_blocks = [item for item in timer_blocks if item is not None]
    non_empty = [
        block
        for block in timer_blocks
        if any(event["name"] == "codestimer" and event["line_count"] > 0 for event in block["events"])
    ]
    return {
        "path": str(path),
        "parse_ok": True,
        "page_names": inspection.page_names,
        "object_names": inspection.object_names,
        "timer_blocks": timer_blocks,
        "timer_count": len(timer_blocks),
        "non_empty_timer_event_count": len(non_empty),
        "sibling_tft": _sibling_tft(path),
        "interesting": bool(timer_blocks),
    }


def _timer_block_summary(block: PABlockSummary) -> dict[str, Any] | None:
    event_headers = [script.raw_header for script in block.event_scripts if script.name == "codestimer"]
    if block.type_code != "3" and not event_headers:
        return None
    events = [
        {
            "raw_header": script.raw_header,
            "name": script.name,
            "line_count": script.line_count,
            "lines": script.lines,
        }
        for script in block.event_scripts
        if script.name == "codestimer"
    ]
    return {
        "index": block.index,
        "objname": block.objname,
        "type_code": block.type_code,
        "id": block.fields.get("id"),
        "tim": block.fields.get("tim"),
        "en": block.fields.get("en"),
        "events": events,
        "has_non_empty_codestimer": any(event["line_count"] > 0 for event in events),
    }


def _sibling_tft(path: Path) -> str | None:
    for suffix in (".tft", ".TFT"):
        candidate = path.with_suffix(suffix)
        if candidate.exists():
            return str(candidate)
    for name in ("lcd_test.tft", "lcd_test.TFT", "source_raw.tft", "source_raw.TFT"):
        candidate = path.parent / name
        if candidate.exists():
            return str(candidate)
    return None


def _summary(reports: list[dict[str, Any]]) -> dict[str, Any]:
    timer_files = [item for item in reports if item.get("timer_count")]
    non_empty_files = [item for item in timer_files if item.get("non_empty_timer_event_count")]
    timer_event_headers = Counter(
        event["raw_header"]
        for item in timer_files
        for block in item.get("timer_blocks", [])
        for event in block.get("events", [])
    )
    return {
        "scanned": len(reports),
        "parse_ok": sum(1 for item in reports if item.get("parse_ok")),
        "parse_failed": sum(1 for item in reports if not item.get("parse_ok")),
        "timer_fixture_count": len(timer_files),
        "non_empty_timer_event_fixture_count": len(non_empty_files),
        "timer_event_headers": dict(sorted(timer_event_headers.items())),
        "timer_files": [item["path"] for item in timer_files],
        "non_empty_timer_event_files": [item["path"] for item in non_empty_files],
        "compiled_timer_oracle_files": [
            item["path"]
            for item in non_empty_files
            if item.get("sibling_tft") is not None
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan HMI fixtures for timer controls and non-empty codestimer scripts.",
    )
    parser.add_argument("paths", nargs="+", type=Path, help="HMI files or directories to scan recursively")
    parser.add_argument("--out", type=Path, help="Write JSON report to this path")
    parser.add_argument("--compact", action="store_true", help="Emit compact JSON")
    args = parser.parse_args(argv)

    report = scan_timer_oracles(args.paths)
    text = json.dumps(report, ensure_ascii=False, indent=None if args.compact else 2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
