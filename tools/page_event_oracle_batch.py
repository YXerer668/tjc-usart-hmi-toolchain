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

from tools.find_hmi_event_fixtures import scan_paths
from tools.page_event_oracle_probe import probe_hmi_tft


def build_batch_report(
    paths: list[Path],
    *,
    force_post_primary_page_load: bool = False,
    include_object_only: bool = False,
) -> dict[str, Any]:
    hmi_scan = scan_paths(paths)
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
                report = probe_hmi_tft(
                    hmi_path,
                    candidate["path"],
                    force_post_primary_page_load=force_post_primary_page_load,
                )
                probes.append(_probe_summary(candidate, report))
            except Exception as exc:  # pragma: no cover - kept visible in JSON reports.
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
                "best_probe": _best_probe(probes),
            }
        )

    return {
        "inputs": [str(path) for path in paths],
        "summary": _summarize_batch(hmi_scan, items),
        "hmi_scan_summary": hmi_scan["summary"],
        "items": items,
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
    if reason.startswith("same_dir") or reason == "official_compile_same_stem_run":
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


def _probe_summary(candidate: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    diagnosis = report["diagnosis"]
    page_block = report["blocks"][0] if report["blocks"] else {}
    complete = (
        bool(report.get("compile_context", {}).get("available"))
        and page_block.get("event_table_error") is None
        and report["post_primary_page_event"]["error"] is None
    )
    return {
        "candidate": _candidate_summary(candidate),
        "ok": True,
        "complete": complete,
        "model": report.get("model"),
        "editor_version": report.get("editor_version"),
        "compile_context": report.get("compile_context"),
        "page_event_table_length": page_block.get("event_table_length"),
        "page_event_table_error": page_block.get("event_table_error"),
        "page_event_table_matches": page_block.get("event_table_matches", []),
        "post_primary_page_event": {
            "length": report["post_primary_page_event"]["length"],
            "error": report["post_primary_page_event"]["error"],
            "matches": report["post_primary_page_event"]["matches"],
            "descriptors": report["post_primary_page_event"].get("descriptors", []),
        },
        "diagnosis": diagnosis,
    }


def _best_probe(probes: list[dict[str, Any]]) -> dict[str, Any] | None:
    ok_probes = [probe for probe in probes if probe.get("ok")]
    if not ok_probes:
        return None
    return sorted(ok_probes, key=_probe_rank)[0]


def _probe_rank(probe: dict[str, Any]) -> tuple[int, int]:
    complete_rank = 0 if probe.get("complete") else 1
    candidate = probe.get("candidate", {})
    confidence_rank = {"high": 0, "medium": 1, "low": 2}.get(candidate.get("confidence"), 3)
    path_rank = {
        "post_primary_page_event": 0,
        "normal_page_table_with_page_callback": 1,
        "normal_page_table_without_page_callback": 2,
        "object_callbacks_only": 3,
        "unbound_or_empty": 4,
    }.get(probe.get("diagnosis", {}).get("scheduler_path"), 5)
    return (complete_rank, confidence_rank, path_rank)


def _summarize_batch(hmi_scan: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
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
    no_candidate = [item["hmi"] for item in items if item["candidate_count"] == 0]
    no_successful_probe = [
        item["hmi"]
        for item in items
        if item["candidate_count"] > 0 and item.get("best_probe") is None
    ]
    incomplete_best_probe = [
        {
            "hmi": item["hmi"],
            "scheduler_path": item["best_probe"]["diagnosis"]["scheduler_path"],
            "page_event_table_error": item["best_probe"].get("page_event_table_error"),
            "compile_context_error": item["best_probe"].get("compile_context", {}).get("error"),
        }
        for item in items
        if item.get("best_probe") and not item["best_probe"].get("complete")
    ]
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
        "scheduler_path_counts": dict(sorted(scheduler_counts.items())),
        "complete_scheduler_path_counts": dict(sorted(complete_scheduler_counts.items())),
        "no_candidate_hmis": no_candidate,
        "no_successful_probe_hmis": no_successful_probe,
        "incomplete_best_probes": incomplete_best_probe,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Batch-classify HMI page-event fixtures against nearby TFT/run oracles.",
    )
    parser.add_argument("paths", nargs="+", type=Path, help="HMI files or directories to scan recursively")
    parser.add_argument("--out", type=Path, help="Write JSON report to this path")
    parser.add_argument(
        "--force-post-primary-page-load",
        action="store_true",
        help="Also search the experimental post-primary page-load chunk for non-media pages.",
    )
    parser.add_argument(
        "--include-object-only",
        action="store_true",
        help="Also classify HMI files with object events but no page events.",
    )
    parser.add_argument("--compact", action="store_true", help="Emit compact JSON")
    args = parser.parse_args(argv)

    report = build_batch_report(
        args.paths,
        force_post_primary_page_load=args.force_post_primary_page_load,
        include_object_only=args.include_object_only,
    )
    text = json.dumps(report, ensure_ascii=False, indent=None if args.compact else 2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
