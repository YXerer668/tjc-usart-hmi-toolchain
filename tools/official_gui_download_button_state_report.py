from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "examples" / "lifecycle_runtime_smoke" / "official_gui_download_button_state_2026-05-21.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Record the current official GUI download button state from a captured probe snippet.")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    payload = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "captured",
        "button": {
            "text": "联机并开始下载",
            "exists": True,
            "is_enabled": True,
            "is_visible": True,
            "friendly_class_name": "Button",
            "legacy_state": 1048576,
        },
        "conclusions": {
            "button_is_present_and_enabled": True,
            "failure_is_not_explained_by_a_disabled_button": True,
            "start_transition_failure_occurs_despite_enabled_button_state": True,
        },
    }
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
