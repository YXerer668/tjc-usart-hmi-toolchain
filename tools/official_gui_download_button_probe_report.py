from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "examples" / "lifecycle_runtime_smoke" / "official_gui_download_button_probe_2026-05-21.json"
DEFAULT_OUT = ROOT / "examples" / "lifecycle_runtime_smoke" / "official_gui_download_button_probe_summary_2026-05-21.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize the latest official GUI download-button probe.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    attempts = payload.get("start_attempt", {}).get("attempts", [])
    methods = [item.get("method") for item in attempts]
    summary = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "probe-summarized",
        "input_artifact": str(Path(args.input).resolve()),
        "configured_port": payload.get("selected_port"),
        "configured_download_baud": payload.get("selected_download_baud"),
        "start_transitioned": payload.get("start_attempt", {}).get("transitioned"),
        "final_button_text": payload.get("start_attempt", {}).get("final_text"),
        "attempt_method_count": len(methods),
        "attempt_methods": methods,
        "bm_click_invoked": any(item.get("method") == "bm_click" and item.get("invoked") for item in attempts),
        "conclusions": {
            "all_local_button_interaction_methods_failed_to_enter_running_state": payload.get("start_attempt", {}).get("transitioned") is False,
            "not_explained_by_simple_missed_click": any(item.get("method") == "bm_click" and item.get("invoked") for item in attempts),
        },
    }
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
