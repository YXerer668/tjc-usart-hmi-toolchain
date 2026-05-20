from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "reverse_usarthmi" / "recovery_sd_card"
PACKAGE_TFT = PACKAGE_DIR / "lcd_test.tft"
README = PACKAGE_DIR / "README_恢复说明.md"
STATE = PACKAGE_DIR / "sd_recovery_state.json"
OUT_PATH = ROOT / "examples" / "lifecycle_runtime_smoke" / "sd_recovery_package_2026-05-21.json"


def main() -> int:
    raw = PACKAGE_TFT.read_bytes()
    state = json.loads(STATE.read_text(encoding="utf-8"))
    report = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "package-identified",
        "package_dir": str(PACKAGE_DIR.relative_to(ROOT)),
        "tft": {
            "path": str(PACKAGE_TFT.relative_to(ROOT)),
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "identity": "known-good official case_31_multi_page_navigation TFT backup",
        },
        "readme": str(README.relative_to(ROOT)),
        "sd_recovery_state": state,
        "conclusions": {
            "sd_recovery_package_exists": True,
            "sd_recovery_state_currently_cleared": state.get("pending") is False,
            "package_ready_for_external_use_if_panel_remains_transport_silent": True,
        },
    }
    OUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
