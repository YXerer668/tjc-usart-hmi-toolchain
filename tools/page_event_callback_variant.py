from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from usarthmi.tft_checksum import inspect_tft_checksum, update_tft_checksum


SLOT_ALIASES = {
    "0x0c": 0x0C,
    "0c": 0x0C,
    "down": 0x0C,
    "load": 0x0C,
    "0x10": 0x10,
    "10": 0x10,
    "up": 0x10,
    "0x14": 0x14,
    "14": 0x14,
    "timer": 0x14,
}


def build_variant(
    binding_report_path: Path,
    *,
    out_tft: Path,
    out_report: Path,
    slot: int,
    target: str,
) -> dict[str, Any]:
    binding = json.loads(binding_report_path.read_text(encoding="utf-8"))
    source_tft = Path(binding["output_tft"])
    page_block = binding["page1"]["blocks"][0]
    if page_block["index"] != 0 or page_block["type_code"] != "y":
        raise SystemExit("Binding report does not describe a page block at page1.blocks[0]")
    matches = page_block["event_table_matches"]
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one page event table match, got {len(matches)}")
    table_start = int(matches[0]["value"])
    table_length = int(page_block["event_table_length"])
    if target == "table-start":
        target_offset = table_start
    else:
        raise SystemExit(f"Unsupported target mode: {target}")

    record_start = int(page_block["mirror_record_relative_offset"])
    write_relative = record_start + slot
    data = bytearray(source_tft.read_bytes())
    object_start = int(binding["object_start"])
    write_absolute = object_start + write_relative
    old_bytes = bytes(data[write_absolute : write_absolute + 4])
    new_bytes = target_offset.to_bytes(4, "little")
    data[write_absolute : write_absolute + 4] = new_bytes
    patched = update_tft_checksum(bytes(data))

    out_tft.parent.mkdir(parents=True, exist_ok=True)
    out_tft.write_bytes(patched)
    checksum = inspect_tft_checksum(out_tft)
    changed_offsets = _changed_offsets(source_tft.read_bytes(), patched)
    report = {
        "source_binding_report": str(binding_report_path),
        "source_tft": str(source_tft),
        "out_tft": str(out_tft),
        "candidate": {
            "slot": slot,
            "slot_hex": f"0x{slot:X}",
            "target_mode": target,
            "target_relative_offset": target_offset,
            "target_relative_offset_hex": f"0x{target_offset:X}",
            "event_table_range": {
                "start": table_start,
                "start_hex": f"0x{table_start:X}",
                "end": table_start + table_length,
                "end_hex": f"0x{table_start + table_length:X}",
                "length": table_length,
            },
            "page_mirror_record_relative_offset": record_start,
            "page_mirror_record_relative_offset_hex": f"0x{record_start:X}",
            "write_relative_offset": write_relative,
            "write_relative_offset_hex": f"0x{write_relative:X}",
            "write_absolute_offset": write_absolute,
            "write_absolute_offset_hex": f"0x{write_absolute:X}",
            "old_bytes_hex": old_bytes.hex(" "),
            "new_bytes_hex": new_bytes.hex(" "),
        },
        "checksum": checksum,
        "diff": {
            "changed_offset_count": len(changed_offsets),
            "changed_offsets": changed_offsets[:32],
            "expected": "one 4-byte callback write plus the trailing 4-byte checksum",
        },
        "safety_notes": [
            "This variant changes only one page mirror callback slot and then recomputes the final TFT checksum.",
            "It is intended as a narrow scheduler-binding probe, not a supported writer feature.",
        ],
    }
    out_report.parent.mkdir(parents=True, exist_ok=True)
    out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _changed_offsets(before: bytes, after: bytes) -> list[dict[str, Any]]:
    if len(before) != len(after):
        raise SystemExit("Variant changed file length; refusing to continue")
    offsets = []
    for index, (old, new) in enumerate(zip(before, after)):
        if old == new:
            continue
        offsets.append(
            {
                "offset": index,
                "offset_hex": f"0x{index:X}",
                "old": old,
                "new": new,
                "old_hex": f"0x{old:02X}",
                "new_hex": f"0x{new:02X}",
            }
        )
    return offsets


def _parse_slot(value: str) -> int:
    key = value.strip().lower()
    if key not in SLOT_ALIASES:
        raise argparse.ArgumentTypeError(f"unknown slot {value!r}; use 0x0c, 0x10, or 0x14")
    return SLOT_ALIASES[key]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Patch one page1 page mirror callback slot for a narrow page-load scheduler probe."
    )
    parser.add_argument("--binding-report", required=True, type=Path)
    parser.add_argument("--out-tft", required=True, type=Path)
    parser.add_argument("--out-report", required=True, type=Path)
    parser.add_argument("--slot", required=True, type=_parse_slot)
    parser.add_argument("--target", choices=["table-start"], default="table-start")
    args = parser.parse_args()

    report = build_variant(
        args.binding_report.resolve(),
        out_tft=args.out_tft.resolve(),
        out_report=args.out_report.resolve(),
        slot=args.slot,
        target=args.target,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
