from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usarthmi.hmi_inspect import inspect_hmi
from usarthmi.page_format import parse_page_data


CLONE_HMI = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_B4_page1_filebrowser_hmi_clone_oracle\lcd_test.HMI")
CLONE_LIVE_NEGATIVE = ROOT / "examples" / "advanced_direct_tft_demo" / "page1_filebrowser_official_clone_live_negative_2026-05-20.json"
LOCAL_LIVE_NEGATIVE = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_local_multipt_live_probe_2026-05-21.json"
POINTER_CLOSURE = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_pointer_closure_report_2026-05-21.json"
OUT_PATH = ROOT / "examples" / "lifecycle_runtime_smoke" / "page1_filebrowser_clone_vs_local_report_2026-05-21.json"


def main() -> int:
    clone_live = json.loads(CLONE_LIVE_NEGATIVE.read_text(encoding="utf-8"))
    local_live = json.loads(LOCAL_LIVE_NEGATIVE.read_text(encoding="utf-8"))
    pointer = json.loads(POINTER_CLOSURE.read_text(encoding="utf-8"))
    clone_blocks = _page_blocks(CLONE_HMI, "1.pa")

    payload = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "clone-vs-local-compared",
        "official_clone_case": {
            "hmi": str(CLONE_HMI),
            "saved_page1_blocks": clone_blocks,
            "compiled_success": clone_live["official_compile"]["compiled_success"],
            "compiled_output_size": clone_live["official_compile"]["compiled_output_size"],
            "live_sendme_page_id": clone_live["live_smoke"]["sendme"]["page_id"],
            "readback_kinds": {
                key: value["kind"] for key, value in clone_live["live_smoke"]["readback"].items()
            },
        },
        "local_current_code_case": {
            "artifact": str(LOCAL_LIVE_NEGATIVE.relative_to(ROOT)),
            "saved_page1_blocks": pointer["cases"]["page1_filebrowser_local_multipt"]["page_blocks"],
            "after_page0_readback": {
                "dir_kind": local_live["after"]["dir"]["response"]["kind"],
                "dir_value": local_live["after"]["dir"]["response"]["value"],
                "filter_kind": local_live["after"]["filter"]["response"]["kind"],
                "filter_value": local_live["after"]["filter"]["response"]["value"],
                "qty_kind": local_live["after"]["qty"]["response"]["kind"],
                "qty_value": local_live["after"]["qty"]["response"]["value"],
                "txt_kind": local_live["after"]["txt"]["response"]["kind"],
                "txt_value": local_live["after"]["txt"]["response"]["value"],
            },
            "pointer_closure": {
                "target_row_hash_valid": pointer["conclusions"]["page1_filebrowser_target_row_hash_offset_valid"],
                "target_row_user_valid": pointer["conclusions"]["page1_filebrowser_target_row_user_offset_valid"],
                "target_object_event_offset_valid": pointer["conclusions"]["page1_filebrowser_target_object_event_offset_valid"],
            },
        },
        "conclusions": {
            "official_clone_is_authoring_gap_not_runtime_a_type_enumeration_gap": (
                clone_blocks == [["page1", "y"]]
                and all(kind == "invalid_reference" for kind in {
                    value["kind"] for value in clone_live["live_smoke"]["readback"].values()
                })
            ),
            "local_current_code_recovers_object_survival_and_field_binding": (
                any(type_code == "A" for _name, type_code in pointer["cases"]["page1_filebrowser_local_multipt"]["page_blocks"])
                and local_live["after"]["dir"]["response"]["kind"] == "string"
                and local_live["after"]["filter"]["response"]["kind"] == "string"
            ),
            "remaining_local_gap_is_enumeration_display_not_object_survival": (
                local_live["after"]["qty"]["response"]["kind"] == "number"
                and local_live["after"]["qty"]["response"]["value"] == 0
            ),
            "recommended_oracle_boundary": (
                "do not treat the official clone invalid_reference case as the same class as the current local multi-page file-browser failure; "
                "the clone currently proves an authoring/save gap, while the local current-code case is a deeper A-type enumeration/display gap."
            ),
        },
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _page_blocks(hmi_path: Path, entry_name: str) -> list[list[str]]:
    raw = hmi_path.read_bytes()
    inspection = inspect_hmi(hmi_path)
    entry = next((item for item in inspection.entries if item.name == entry_name), None)
    if entry is None or not entry.in_file:
        return []
    page = parse_page_data(raw[entry.data_offset : entry.data_offset + entry.length])
    return [[block.objname, block.type_code] for block in page.blocks]


if __name__ == "__main__":
    raise SystemExit(main())
