from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "examples" / "lifecycle_runtime_smoke" / "public_whmi_entry_probe_2026-05-21.json"
DEFAULT_OUT = ROOT / "examples" / "lifecycle_runtime_smoke" / "public_whmi_entry_probe_summary_2026-05-21.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize the latest public whmi-wri entry probe.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    summary = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "probe-summarized",
        "input_artifact": str(Path(args.input).resolve()),
        "command": payload["command"],
        "ack_received": payload["ack_received"],
        "elapsed_s": payload["elapsed_s"],
        "diagnosis": payload["diagnosis"],
        "conclusions": {
            "public_whmi_entry_is_silent": payload["ack_received"] is False,
            "runtime_silence_has_now_escalated_to_upload_entry_silence": True,
            "next_step_requires_physical_or_external_recovery": True,
        },
    }
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
