from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "examples" / "lifecycle_runtime_smoke" / "dtr_rts_pulse_probe_2026-05-21.json"
DEFAULT_OUT = ROOT / "examples" / "lifecycle_runtime_smoke" / "dtr_rts_pulse_probe_summary_2026-05-21.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize the DTR/RTS pulse probe result.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    report = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "probe-summarized",
        "steps": payload["pulse"]["steps"],
        "before_connect_kind": payload["before"]["commands"][0]["response"]["kind"],
        "after_connect_kind": payload["after"]["commands"][0]["response"]["kind"],
        "before_sendme_kind": payload["before"]["commands"][1]["response"]["kind"],
        "after_sendme_kind": payload["after"]["commands"][1]["response"]["kind"],
        "conclusions": {
            "dtr_rts_pulse_did_not_restore_serial_responsiveness": payload["conclusions"]["serial_became_responsive_after_pulse"] is False,
            "dtr_rts_pulse_showed_no_observable_change": payload["conclusions"]["no_change_after_pulse"] is True,
        },
    }
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
