from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.page_event_callback_slot_status import (  # noqa: E402
    DEFAULT_HARDWARE_PROBE,
    summarize_callback_slot_probe,
)


DEFAULT_BATCH_REPORT = (
    REPO_ROOT
    / "reverse_usarthmi"
    / "page_lifecycle_oracle_scan_20260515"
    / "batch_page_event_oracles_v2.json"
)


FORBIDDEN_ACTIONS = [
    "blind_write_page_mirror_slots",
    "repeat_page1_load_slots_0x0c_0x10_0x14",
    "extrapolate_object_callback_slots_to_page_lifecycle",
    "treat_partial_oracle_as_scheduler_truth",
]

ALLOWED_NEXT_ACTIONS = [
    "collect_complete_official_two_page_page_load_oracle",
    "diff_post_primary_page_event_descriptor",
    "extend_event_compiler_for_case42_case43_case44_before_scheduler_inference",
    "continue_object_event_work_with_live_or_fixture_proof",
]


def build_scheduler_matrix(
    batch_report_path: Path = DEFAULT_BATCH_REPORT,
    slot_probe_path: Path = DEFAULT_HARDWARE_PROBE,
) -> dict[str, Any]:
    """Combine page-event oracle evidence and live negative slot probes.

    The matrix is intentionally prescriptive: its main job is to prevent future
    automation from repeating already-failed callback-slot burns while pointing
    the next research cycle at official oracle/descriptor evidence.
    """

    batch_report = _load_json(batch_report_path)
    slot_probe = summarize_callback_slot_probe(slot_probe_path)
    oracle_items = [_oracle_item(item) for item in batch_report.get("items", [])]
    scheduler_paths = _scheduler_path_matrix(oracle_items)
    blocked_slots = slot_probe["summary"].get("avoid_repeating_blind_slots", [])

    return {
        "source": "page_event_scheduler_matrix",
        "repo": _repo_info(),
        "inputs": {
            "batch_report": _relative_path(batch_report_path),
            "slot_probe": _relative_path(slot_probe_path),
        },
        "oracle_summary": _oracle_summary(batch_report, oracle_items),
        "scheduler_paths": scheduler_paths,
        "page1_load_negative_slot_probe": {
            "source": slot_probe["source"],
            "device": slot_probe.get("device", {}),
            "tested_slots": slot_probe.get("tested_slots", []),
            "all_candidates_failed_cleanly": slot_probe["summary"].get(
                "all_candidates_failed_cleanly", False
            ),
            "page1_load_scheduler_recovered": slot_probe["summary"].get(
                "page1_load_scheduler_recovered", False
            ),
            "candidates": [
                {
                    "slot_hex": item["slot_hex"],
                    "target_meaning": "table_start",
                    "target_relative_offset_hex": item["target_relative_offset_hex"],
                    "write_absolute_offset_hex": item["write_absolute_offset_hex"],
                    "checksum_hex": item["checksum_hex"],
                    "checksum_valid": item["checksum_valid"],
                    "runtime_page_ok": item["page_switching_preserved"],
                    "event_observed": item["expected_printh_seen"],
                    "result": "negative" if not item["expected_printh_seen"] else "positive",
                    "negative_live_evidence": not item["expected_printh_seen"],
                    "do_not_retry_blindly": not item["expected_printh_seen"],
                }
                for item in slot_probe.get("candidates", [])
            ],
            "overall_conclusion": slot_probe.get("overall_conclusion", ""),
        },
        "decision": {
            "do_not_repeat_blind_slot_writes": bool(blocked_slots),
            "blocked_repeated_slots": blocked_slots,
            "risk_level": "high_for_live_page_lifecycle_writes",
            "requires_live_burn": False,
            "offline_only_until": (
                "a complete official two-page/page-load oracle or byte-for-byte "
                "post-primary scheduler descriptor match is recovered"
            ),
            "forbidden_actions": FORBIDDEN_ACTIONS,
            "allowed_next_actions": ALLOWED_NEXT_ACTIONS,
            "recommended_next_step": (
                "Recover a complete official minimal page-load oracle or diff the "
                "case49 post-primary page-event descriptor before another page-load burn."
            ),
            "confidence": _decision_confidence(scheduler_paths, blocked_slots),
        },
    }


def _oracle_summary(
    batch_report: dict[str, Any],
    oracle_items: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = batch_report.get("summary", {})
    qualities = Counter(item["oracle_quality"] for item in oracle_items)
    source_types = Counter(item["source_type"] for item in oracle_items)
    return {
        "hmi_scanned": summary.get("hmi_scanned"),
        "page_event_hmi_count": summary.get("page_event_hmi_count"),
        "items_with_successful_probe": summary.get("items_with_successful_probe"),
        "items_with_complete_probe": summary.get("items_with_complete_probe"),
        "scheduler_path_counts": summary.get("scheduler_path_counts", {}),
        "complete_scheduler_path_counts": summary.get("complete_scheduler_path_counts", {}),
        "oracle_quality_counts": dict(sorted(qualities.items())),
        "source_type_counts": dict(sorted(source_types.items())),
        "incomplete_best_probes": summary.get("incomplete_best_probes", []),
    }


def _scheduler_path_matrix(oracle_items: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in oracle_items:
        grouped[item["scheduler_path"]].append(item)

    matrix: dict[str, Any] = {}
    for scheduler_path, items in sorted(grouped.items()):
        upload_risks = sorted({item["upload_risk"] for item in items if item["upload_risk"]})
        writer_actions = sorted(
            {
                item["recommended_writer_action"]
                for item in items
                if item["recommended_writer_action"]
            }
        )
        matrix[scheduler_path] = {
            "count": len(items),
            "complete_count": sum(1 for item in items if item["complete"]),
            "oracle_quality_counts": dict(
                sorted(Counter(item["oracle_quality"] for item in items).items())
            ),
            "upload_risks": upload_risks,
            "recommended_writer_actions": writer_actions,
            "oracles": items,
        }
    return matrix


def _oracle_item(item: dict[str, Any]) -> dict[str, Any]:
    best_probe = item.get("best_probe") or {}
    diagnosis = best_probe.get("diagnosis") or {}
    candidate = best_probe.get("candidate") or {}
    compile_context = best_probe.get("compile_context") or {}
    page_event_error = best_probe.get("page_event_table_error")
    post_primary = best_probe.get("post_primary_page_event") or {}
    return {
        "case_id": _case_id(item.get("hmi", "")),
        "hmi": item.get("hmi"),
        "source_type": _source_type(candidate.get("reason", "")),
        "oracle_quality": _oracle_quality(best_probe, page_event_error),
        "complete": bool(best_probe.get("complete")),
        "scheduler_path": diagnosis.get("scheduler_path", "no_probe"),
        "upload_risk": diagnosis.get("upload_risk"),
        "recommended_writer_action": diagnosis.get("recommended_writer_action"),
        "model": best_probe.get("model"),
        "editor_version": best_probe.get("editor_version"),
        "page_event_count": item.get("page_event_count"),
        "object_event_count": item.get("object_event_count"),
        "event_name_counts": item.get("event_name_counts", {}),
        "post_primary_page_event": {
            "length": post_primary.get("length"),
            "matches": post_primary.get("matches", []),
            "descriptors": post_primary.get("descriptors", []),
        },
        "candidate": {
            "path": candidate.get("path"),
            "reason": candidate.get("reason"),
            "confidence": candidate.get("confidence"),
            "size": candidate.get("size"),
        },
        "compile_context": {
            "available": compile_context.get("available"),
            "error": compile_context.get("error"),
        },
        "unsupported_commands": _unsupported_commands(page_event_error),
        "reason_oracle_incomplete": _reason_oracle_incomplete(
            best_probe=best_probe,
            page_event_error=page_event_error,
            compile_context_error=compile_context.get("error"),
        ),
    }


def _oracle_quality(best_probe: dict[str, Any], page_event_error: str | None) -> str:
    if not best_probe:
        return "no_probe"
    if best_probe.get("complete"):
        return "complete"
    if page_event_error and "Unsupported event line" in page_event_error:
        return "unsupported_command"
    if best_probe.get("ok"):
        return "partial"
    return "failed_probe"


def _source_type(reason: str) -> str:
    if reason.startswith("official_compile"):
        return "official"
    if reason.startswith("same_dir"):
        return "nearby_generated"
    if reason == "case_root_lcd_test_tft":
        return "seed_or_generated"
    return "unknown"


def _case_id(path_text: str) -> str | None:
    for part in Path(path_text).parts:
        if re.match(r"^case_\d+", part):
            return part
    return None


def _unsupported_commands(error: str | None) -> list[str]:
    if not error or "Unsupported event line" not in error:
        return []
    marker = "Unsupported event line for the current minimal logic compiler: "
    if marker not in error:
        return [error]
    value = error.split(marker, 1)[1].split(". Supported V1", 1)[0]
    return [value.strip("'")]


def _reason_oracle_incomplete(
    *,
    best_probe: dict[str, Any],
    page_event_error: str | None,
    compile_context_error: str | None,
) -> str | None:
    if not best_probe or best_probe.get("complete"):
        return None
    reasons = []
    if page_event_error:
        reasons.append(page_event_error)
    if compile_context_error:
        reasons.append(f"compile_context_error: {compile_context_error}")
    return " | ".join(reasons) if reasons else "best probe is incomplete"


def _decision_confidence(scheduler_paths: dict[str, Any], blocked_slots: list[str]) -> str:
    has_complete_post_primary = (
        scheduler_paths.get("post_primary_page_event", {}).get("complete_count", 0) > 0
    )
    has_negative_slots = bool(blocked_slots)
    if has_complete_post_primary and has_negative_slots:
        return "high_for_guardrail_medium_for_scheduler_recovery"
    if has_negative_slots:
        return "high_for_guardrail_low_for_scheduler_recovery"
    return "low"


def _repo_info() -> dict[str, Any]:
    return {
        "root": str(REPO_ROOT),
        "commit": _git_output("rev-parse", "--short", "HEAD"),
        "branch": _git_output("branch", "--show-current"),
    }


def _git_output(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a guardrail matrix for page-event scheduler research.",
    )
    parser.add_argument(
        "--batch-report",
        type=Path,
        default=DEFAULT_BATCH_REPORT,
        help="Batch page-event oracle report JSON.",
    )
    parser.add_argument(
        "--slot-probe",
        type=Path,
        default=DEFAULT_HARDWARE_PROBE,
        help="Live page1 callback-slot probe JSON.",
    )
    parser.add_argument("--out", type=Path, help="Optional output JSON path.")
    parser.add_argument("--compact", action="store_true", help="Emit compact JSON.")
    args = parser.parse_args(argv)

    report = build_scheduler_matrix(
        batch_report_path=args.batch_report.resolve(),
        slot_probe_path=args.slot_probe.resolve(),
    )
    text = json.dumps(report, ensure_ascii=False, indent=None if args.compact else 2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
