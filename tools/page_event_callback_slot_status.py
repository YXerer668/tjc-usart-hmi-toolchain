from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROBE_DIR = REPO_ROOT / "reverse_usarthmi" / "page1_load_callback_slot_probe"
DEFAULT_HARDWARE_PROBE = DEFAULT_PROBE_DIR / "hardware_probe_2026-05-15.json"


def summarize_callback_slot_probe(
    hardware_probe_path: Path = DEFAULT_HARDWARE_PROBE,
) -> dict[str, Any]:
    """Summarize live-tested page1 load callback slot candidates.

    This deliberately reports negative evidence. The page1 load scheduler is
    still unrecovered, and repeatedly burning the same clean-failed slots wastes
    time and increases hardware churn without adding information.
    """

    hardware_probe = _load_json(hardware_probe_path)
    probe_dir = hardware_probe_path.parent
    candidates: list[dict[str, Any]] = []
    for candidate in hardware_probe.get("candidates", []):
        name = candidate["name"]
        variant_report_path = probe_dir / name / "variant_report_2026-05-15.json"
        variant = _load_json(variant_report_path)
        serial = candidate.get("serial_result", {})
        candidates.append(
            {
                "name": name,
                "slot_hex": candidate.get("slot_hex"),
                "checksum_hex": candidate.get("checksum_hex"),
                "variant_report": _relative_path(variant_report_path),
                "write_absolute_offset_hex": variant["candidate"]["write_absolute_offset_hex"],
                "target_relative_offset_hex": variant["candidate"]["target_relative_offset_hex"],
                "changed_offset_count": variant["diff"]["changed_offset_count"],
                "checksum_valid": bool(variant["checksum"]["valid"]),
                "page_switching_preserved": _page_switching_preserved(serial),
                "expected_printh_seen": bool(serial.get("expected_printh_seen")),
                "conclusion": candidate.get("conclusion", ""),
            }
        )

    failed_cleanly = [
        item
        for item in candidates
        if item["checksum_valid"]
        and item["page_switching_preserved"]
        and not item["expected_printh_seen"]
    ]
    tested_slots = [item["slot_hex"] for item in candidates]
    return {
        "source": _relative_path(hardware_probe_path),
        "probe": hardware_probe.get("probe"),
        "date": hardware_probe.get("date"),
        "purpose": hardware_probe.get("purpose"),
        "device": hardware_probe.get("device", {}),
        "tested_slots": tested_slots,
        "candidates": candidates,
        "summary": {
            "all_candidates_failed_cleanly": len(failed_cleanly) == len(candidates),
            "page1_load_scheduler_recovered": any(item["expected_printh_seen"] for item in candidates),
            "avoid_repeating_blind_slots": tested_slots,
            "recommended_next_path": (
                "Use an official two-page/page-load oracle or deeper scheduler descriptor diff; "
                "do not keep blind-writing page mirror callback slots 0x0C/0x10/0x14."
            ),
        },
        "overall_conclusion": hardware_probe.get("overall_conclusion", ""),
    }


def _page_switching_preserved(serial: dict[str, Any]) -> bool:
    return (
        serial.get("initial_sendme_hex") == "66 00 ff ff ff"
        and serial.get("after_page_1_sendme_hex") == "66 01 ff ff ff"
        and serial.get("after_page_0_sendme_hex") == "66 00 ff ff ff"
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize live-tested page1 load callback slot candidates."
    )
    parser.add_argument(
        "--hardware-probe",
        type=Path,
        default=DEFAULT_HARDWARE_PROBE,
        help="Path to page1_load_callback_slot_probe hardware_probe JSON.",
    )
    parser.add_argument("--out", type=Path, help="Optional output JSON path.")
    args = parser.parse_args()

    report = summarize_callback_slot_probe(args.hardware_probe.resolve())
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
