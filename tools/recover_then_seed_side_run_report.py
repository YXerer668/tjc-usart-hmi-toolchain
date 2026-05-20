from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "reverse_usarthmi" / "recover_then_seed_side_run_20260521" / "recover_then_seed_side_summary.json"
DEFAULT_OUT = ROOT / "examples" / "lifecycle_runtime_smoke" / "recover_then_seed_side_run_2026-05-21.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Repackage the latest recover-then-seed-side live attempt into a stable lifecycle artifact.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    report = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "live-recovery-attempted",
        "source_summary": str(Path(args.input).resolve()),
        "before_responsive": payload["before"]["responsive"],
        "after_recovery_responsive": payload["after_recovery"]["responsive"] if payload.get("after_recovery") else None,
        "runner_started": payload.get("runner") is not None,
        "classification": payload["classification"],
        "key_findings": {
            "connect_kind_before": payload["before"]["connect"]["response"]["kind"],
            "sendme_kind_before": payload["before"]["sendme"]["response"]["kind"],
            "official_recovery_selected_port": payload["recovery"]["selected_port"],
            "official_recovery_selected_download_baud": payload["recovery"]["selected_download_baud"],
            "official_recovery_start_transitioned": payload["recovery"]["start_attempt"]["transitioned"],
            "official_recovery_start_final_text": payload["recovery"]["start_attempt"]["final_text"],
            "connect_kind_after": payload["after_recovery"]["connect"]["response"]["kind"] if payload.get("after_recovery") else None,
            "sendme_kind_after": payload["after_recovery"]["sendme"]["response"]["kind"] if payload.get("after_recovery") else None,
        },
        "conclusions": {
            "panel_still_silent_after_orchestrated_recovery": payload["classification"] == "still_silent_after_recovery",
            "seed_side_runtime_limiter_runner_blocked_by_transport": payload.get("runner") is None,
            "next_live_step_requires_physical_or_external_recovery_not_more_local_runner_work": True,
        },
    }
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
