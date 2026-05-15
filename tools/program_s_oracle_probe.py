from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from usarthmi.hmi_inspect import inspect_hmi
from usarthmi.tft_patch import _compile_event_line, _event_item
from usarthmi.tft_toolchain import TftToolchainError, inspect_tft


RESOURCE_REGION_NAMES = {
    "audios_address",
    "fonts_address",
    "gmovs_address",
    "pictures_address",
    "videos_address",
}

CODE_LIKE_REGION_NAMES = {
    "app_attributes_data_address",
    "static_usercode_address",
    "unknown_objects_address",
    "unknown_pages_address",
    "usercode_address",
}


def probe_program_s(
    hmi_path: Path,
    tft_path: Path,
    *,
    min_match_len: int = 8,
) -> dict[str, Any]:
    hmi = inspect_hmi(hmi_path)
    raw = tft_path.read_bytes()
    regions, tft_meta = _region_map(tft_path, len(raw))
    compiled_lines = _compile_program_lines(hmi.program_text or "", raw, regions, min_match_len=min_match_len)
    block_matches = _compiled_block_matches(compiled_lines, raw, regions, min_match_len=min_match_len)
    summary = _summarize(compiled_lines, block_matches)
    return {
        "hmi": str(hmi_path.resolve()),
        "tft": str(tft_path.resolve()),
        "tft_size": len(raw),
        "tft_size_hex": f"0x{len(raw):X}",
        "min_match_len": min_match_len,
        "tft_meta": tft_meta,
        "regions": regions,
        "program_s_lines": compiled_lines,
        "block_matches": block_matches,
        "summary": summary,
    }


def _compile_program_lines(
    program_text: str,
    tft_raw: bytes,
    regions: list[dict[str, Any]],
    *,
    min_match_len: int,
) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for line_no, line in enumerate(program_text.splitlines(), start=1):
        stripped = line.split("//", 1)[0].strip()
        report: dict[str, Any] = {
            "line_no": line_no,
            "source": line,
            "stripped": stripped,
        }
        if not stripped:
            report.update({"compile_status": "empty_or_comment", "compiled_hex": None, "matches": []})
            reports.append(report)
            continue
        try:
            payload = _compile_event_line(line, context=None)
        except TftToolchainError as exc:
            report.update(
                {
                    "compile_status": "unsupported",
                    "error": str(exc),
                    "compiled_hex": None,
                    "matches": [],
                }
            )
            reports.append(report)
            continue
        if payload is None:
            report.update({"compile_status": "empty_or_comment", "compiled_hex": None, "matches": []})
            reports.append(report)
            continue
        item = _event_item(payload)
        matches = _match_reports(
            tft_raw,
            item,
            regions,
            min_match_len=min_match_len,
            pattern_kind="line_item",
        )
        report.update(
            {
                "compile_status": "compiled",
                "payload_hex": payload.hex(" "),
                "compiled_hex": item.hex(" "),
                "compiled_len": len(item),
                "matches": matches,
            }
        )
        reports.append(report)
    return reports


def _compiled_block_matches(
    line_reports: list[dict[str, Any]],
    tft_raw: bytes,
    regions: list[dict[str, Any]],
    *,
    min_match_len: int,
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    previous_line_no: int | None = None

    for report in line_reports:
        if report.get("compile_status") != "compiled":
            if current:
                blocks.append(_block_report(current, tft_raw, regions, min_match_len=min_match_len))
                current = []
                previous_line_no = None
            continue
        line_no = int(report["line_no"])
        if previous_line_no is not None and line_no != previous_line_no + 1:
            blocks.append(_block_report(current, tft_raw, regions, min_match_len=min_match_len))
            current = []
        current.append(report)
        previous_line_no = line_no

    if current:
        blocks.append(_block_report(current, tft_raw, regions, min_match_len=min_match_len))
    return [block for block in blocks if block["line_count"] >= 2]


def _block_report(
    line_reports: list[dict[str, Any]],
    tft_raw: bytes,
    regions: list[dict[str, Any]],
    *,
    min_match_len: int,
) -> dict[str, Any]:
    compiled_hex = "".join("".join(str(item["compiled_hex"]).split()) for item in line_reports)
    compiled = bytes.fromhex(compiled_hex)
    line_numbers = [int(item["line_no"]) for item in line_reports]
    return {
        "line_start": line_numbers[0],
        "line_end": line_numbers[-1],
        "line_range": f"{line_numbers[0]}-{line_numbers[-1]}",
        "line_count": len(line_reports),
        "compiled_len": len(compiled),
        "compiled_hex": compiled.hex(" "),
        "matches": _match_reports(
            tft_raw,
            compiled,
            regions,
            min_match_len=min_match_len,
            pattern_kind="compiled_block",
        ),
    }


def _match_reports(
    raw: bytes,
    pattern: bytes,
    regions: list[dict[str, Any]],
    *,
    min_match_len: int,
    pattern_kind: str,
) -> list[dict[str, Any]]:
    if len(pattern) < min_match_len:
        return []
    offsets = list(_all_matches(raw, pattern))
    return [
        _offset_report(
            raw,
            offset,
            len(pattern),
            regions,
            duplicate_count=len(offsets),
            min_match_len=min_match_len,
            pattern_kind=pattern_kind,
        )
        for offset in offsets
    ]


def _offset_report(
    raw: bytes,
    offset: int,
    match_len: int,
    regions: list[dict[str, Any]],
    *,
    duplicate_count: int,
    min_match_len: int,
    pattern_kind: str,
) -> dict[str, Any]:
    region = _region_for_offset(regions, offset)
    return {
        "offset": offset,
        "offset_hex": f"0x{offset:X}",
        "region": region["name"],
        "region_start_hex": f"0x{region['start']:X}",
        "region_end_hex": f"0x{region['end']:X}" if region["end"] is not None else None,
        "match_len": match_len,
        "duplicate_count": duplicate_count,
        "confidence": _confidence(
            match_len,
            duplicate_count=duplicate_count,
            region_name=region["name"],
            min_match_len=min_match_len,
            pattern_kind=pattern_kind,
        ),
        "context_before_hex": raw[max(0, offset - 8) : offset].hex(" "),
        "context_after_hex": raw[offset + match_len : min(len(raw), offset + match_len + 8)].hex(" "),
    }


def _confidence(
    match_len: int,
    *,
    duplicate_count: int,
    region_name: str,
    min_match_len: int,
    pattern_kind: str,
) -> str:
    if match_len < min_match_len or duplicate_count > 1:
        return "low"
    if _region_has_any(region_name, RESOURCE_REGION_NAMES):
        return "low"
    if pattern_kind == "compiled_block" and match_len >= 12 and _region_has_any(region_name, CODE_LIKE_REGION_NAMES):
        return "high"
    if match_len >= 12 and _region_has_any(region_name, CODE_LIKE_REGION_NAMES):
        return "medium"
    return "medium"


def _region_has_any(region_name: str, names: set[str]) -> bool:
    return bool(set(region_name.split("+")) & names)


def _all_matches(raw: bytes, pattern: bytes) -> Iterable[int]:
    if not pattern:
        return
    start = 0
    while True:
        offset = raw.find(pattern, start)
        if offset < 0:
            return
        yield offset
        start = offset + 1


def _region_for_offset(regions: list[dict[str, Any]], offset: int) -> dict[str, Any]:
    for region in regions:
        end = region["end"]
        if offset >= region["start"] and (end is None or offset < end):
            return region
    return {"name": "unknown_gap", "start": 0, "end": None}


def _region_map(tft_path: Path, file_size: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        tft = inspect_tft(tft_path)
    except Exception as exc:
        return (
            [{"name": "whole_file_unknown", "start": 0, "end": file_size}],
            {"available": False, "error": str(exc)},
        )

    header2 = tft.get("parsed", {}).get("Header2", {})
    starts: dict[int, list[str]] = {0: ["file_start"]}
    for name, value in header2.items():
        if not name.endswith("_address"):
            continue
        parsed = _parse_int(value)
        if parsed is None or parsed < 0 or parsed >= file_size:
            continue
        starts.setdefault(parsed, []).append(name)

    ordered = sorted(starts.items())
    regions: list[dict[str, Any]] = []
    for index, (start, names) in enumerate(ordered):
        end = ordered[index + 1][0] if index + 1 < len(ordered) else file_size
        regions.append(
            {
                "name": "+".join(sorted(names)),
                "start": start,
                "start_hex": f"0x{start:X}",
                "end": end,
                "end_hex": f"0x{end:X}",
                "length": end - start,
            }
        )
    return (
        regions,
        {
            "available": True,
            "editor_version": tft.get("editor_version"),
            "model": tft.get("model"),
            "usercode_decode_error": tft.get("usercode_decode_error"),
        },
    )


def _parse_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError:
            return None
    return None


def _summarize(line_reports: list[dict[str, Any]], block_matches: list[dict[str, Any]]) -> dict[str, Any]:
    compiled = [item for item in line_reports if item.get("compile_status") == "compiled"]
    unsupported = [item for item in line_reports if item.get("compile_status") == "unsupported"]
    line_match_count = sum(len(item.get("matches", [])) for item in compiled)
    high_blocks = [
        match
        for block in block_matches
        for match in block.get("matches", [])
        if match.get("confidence") == "high"
    ]
    return {
        "line_count": len(line_reports),
        "compiled_line_count": len(compiled),
        "unsupported_line_count": len(unsupported),
        "line_match_count": line_match_count,
        "block_match_count": sum(len(block.get("matches", [])) for block in block_matches),
        "high_confidence_block_match_count": len(high_blocks),
        "overall": "high" if high_blocks else ("medium" if line_match_count else "none"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Probe where HMI Program.s startup code appears in an official TFT/run file."
    )
    parser.add_argument("hmi", type=Path, help="Input .HMI file")
    parser.add_argument("tft", type=Path, help="Official .tft or .run oracle file")
    parser.add_argument("--out", type=Path, help="Optional JSON output path")
    parser.add_argument("--min-match-len", type=int, default=8, help="Small patterns below this length are ignored")
    args = parser.parse_args(argv)

    report = probe_program_s(args.hmi, args.tft, min_match_len=args.min_match_len)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
