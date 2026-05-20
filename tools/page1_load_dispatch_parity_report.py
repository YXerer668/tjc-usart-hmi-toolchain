from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.page_event_binding_probe import probe_manifest
from usarthmi.tft_toolchain import inspect_tft


DEFAULT_OFFICIAL = ROOT / "examples" / "case52_06_page1_load_printh_only_official_event_index.json"
DEFAULT_LOCAL_MANIFEST = ROOT / "reverse_usarthmi" / "page1_load_printh_probe_20260520" / "manifest.json"
DEFAULT_OUT = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_load_dispatch_parity_report_2026-05-20.json"


def build_report(*, official_event_index: Path, local_manifest: Path) -> dict[str, Any]:
    official = json.loads(official_event_index.read_text(encoding="utf-8"))
    local = probe_manifest(local_manifest)
    official_tft_path = Path(official["tft"])
    official_tft = inspect_tft(official_tft_path)
    official_h2 = official_tft["parsed"]["Header2"]
    official_object_start = int(official_h2["unknown_objects_address"], 16)
    official_pictures_address = int(official_h2["pictures_address"], 16)
    official_tail = official_tft_path.read_bytes()[official_object_start:]
    official_mirror_start = official_pictures_address - official_object_start
    official_page1_dir = official_tail[official_mirror_start : official_mirror_start + 16]
    official_page1_hash_offset = int.from_bytes(official_page1_dir[4:8], "little")

    official_page = next(page for page in official["additional_pages"] if page["page_name"] == "page1")
    official_block = next(block for block in official_page["blocks"] if block["objname"] == "page1")
    official_phase = official_block["page_load_phase_matches"][0]
    official_record = official_block["record_candidates"][0]
    local_block = local["page1"]["blocks"][0]
    local_page1_hash_offset = local["section_offsets"]["hash"]["value"]

    return {
        "schema_version": 1,
        "date": "2026-05-20",
        "target": "TJC8048X543_011C",
        "mode": "page1_load_dispatch_parity_report",
        "official_oracle": {
            "source": str(official_event_index),
            "page_resource": official_page["resource"],
            "page1_hash_offset_hex": f"0x{official_page1_hash_offset:X}",
            "compile_context": official_page["compile_context"],
            "page_summary": official_page["summary"],
            "event_tokens": official_block["event_tokens"],
            "event_table_matches": official_block["event_table_matches"],
            "page_load_phase_match": {
                "offset_hex": official_phase["offset_hex"],
                "end_hex": official_phase["end_hex"],
                "prefix_length": official_phase["prefix_length"],
                "first_executable_absolute_hex": official_phase["first_executable_absolute_hex"],
                "prefix_items": official_phase["prefix_items"],
                "prefix_end_references": official_phase["references"]["prefix_end"],
            },
            "record_candidate": {
                "relative_offset_hex": official_record["relative_offset_hex"],
                "header_hex": official_record["header_hex"],
                "slots": official_record["slots"],
            },
            "runtime_conclusion": "official page1 load dispatch is live-positive on corrected runtime page 0",
        },
        "local_generated_probe": {
            "source": str(local_manifest),
            "section_offsets": local["section_offsets"],
            "page1_hash_offset_hex": f"0x{local_page1_hash_offset:X}",
            "mirror_record_len_hex": local["mirror_record_len_hex"],
            "event_tokens": local_block["event_tokens"],
            "event_table_length": local_block["event_table_length"],
            "event_table_matches": local_block["event_table_matches"],
            "mirror_event_offset_field": local_block["mirror_event_offset_field"],
            "callback_slots": local_block["callback_slots"],
            "runtime_conclusion": "local generated page1 load dispatch is still live-negative on corrected runtime page 0",
        },
        "comparison": {
            "official_uses_inline_load_phase_wrapper": bool(official_block["page_load_phase_matches"]) and not bool(official_block["event_table_matches"]),
            "local_uses_normal_page_event_table": bool(local_block["event_table_matches"]),
            "official_callback_slots_empty": all(
                slot["value_hex"] == "0xFFFFFFFF"
                for name, slot in official_record["slots"].items()
                if name in {"slot_0x0c", "slot_0x10", "slot_0x14"}
            ),
            "local_callback_slots_empty": all(
                slot["value_hex"] == "0xFFFFFFFF"
                for slot in local_block["callback_slots"].values()
            ),
            "official_wrapper_starts_after_hash": official_phase["offset"] > official_page1_hash_offset,
            "local_page_event_table_starts_before_hash": local_block["event_table_matches"][0]["value"] < local_page1_hash_offset,
            "official_and_local_share_event_offset_style": (
                official_record["slots"]["event_offset_0x34"]["value_hex"] == "0x0"
                and local_block["mirror_event_offset_field"]["hex"] == "0x14B"
            ),
            "likely_missing_layer": (
                "local build still emits page1 load as a normal page event table with mirror event_offset_0x34 "
                "pointing at that table before the page1 hash block, while the official oracle uses an inline page-load phase wrapper "
                "after the page1 hash block "
                "without a normal page event-table match. The missing piece is likely the official page1 load "
                "wrapper/layout path rather than a simple callback-slot fill."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare official page1 load dispatch structure against the local generated page1 load probe.")
    parser.add_argument("--official-event-index", type=Path, default=DEFAULT_OFFICIAL)
    parser.add_argument("--local-manifest", type=Path, default=DEFAULT_LOCAL_MANIFEST)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    report = build_report(
        official_event_index=args.official_event_index.resolve(),
        local_manifest=args.local_manifest.resolve(),
    )
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
