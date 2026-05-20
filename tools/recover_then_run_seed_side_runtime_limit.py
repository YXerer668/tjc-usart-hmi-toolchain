from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
USARTHMI_CMD = ROOT / "usarthmi.cmd"
RECOVERY_TOOL = ROOT / "tools" / "official_hmi_download_recovery.py"
RUNNER_TOOL = ROOT / "tools" / "run_seed_side_multipt_runtime_limit_smokes.py"
DEFAULT_RECOVERY_HMI = ROOT / "reverse_usarthmi" / "official_page1_textselect_minimal_oracle_20260519" / "lcd_test.HMI"


def _run_json_command(cmd: list[str]) -> dict[str, Any]:
    completed = subprocess.run(cmd, text=True, capture_output=True, check=False, encoding="utf-8", errors="replace")
    if completed.returncode not in {0, 1}:
        raise RuntimeError(f"Command failed rc={completed.returncode}\ncmd={' '.join(cmd)}\nstdout={completed.stdout}\nstderr={completed.stderr}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Command did not return JSON\ncmd={' '.join(cmd)}\nstdout={completed.stdout}\nstderr={completed.stderr}") from exc


def _serial_command(command: str, *, port: str, baud: int, timeout_ms: int) -> list[str]:
    return [
        str(USARTHMI_CMD),
        "--json",
        command,
        "--port",
        port,
        "--baud",
        str(baud),
        "--timeout-ms",
        str(timeout_ms),
    ]


def serial_snapshot(*, port: str, baud: int, timeout_ms: int) -> dict[str, Any]:
    connect = _run_json_command(_serial_command("connect", port=port, baud=baud, timeout_ms=timeout_ms))
    sendme = _run_json_command(_serial_command("sendme", port=port, baud=baud, timeout_ms=timeout_ms))
    connect_kind = connect.get("response", {}).get("kind")
    sendme_kind = sendme.get("response", {}).get("kind")
    return {
        "connect": connect,
        "sendme": sendme,
        "responsive": connect_kind != "none" or sendme_kind != "none",
    }


def build_recovery_command(
    *,
    hmi: Path,
    port: str,
    download_baud: int,
    wait_s: float,
) -> list[str]:
    return [
        sys.executable,
        str(RECOVERY_TOOL),
        str(hmi),
        "--port",
        port,
        "--download-baud",
        str(download_baud),
        "--start-download",
        "--download-wait-s",
        str(wait_s),
    ]


def build_runner_command(
    *,
    out_dir: Path,
    port: str,
    baud: int,
    download_baud: int,
    timeout_ms: int,
    capture: bool,
) -> list[str]:
    cmd = [
        sys.executable,
        str(RUNNER_TOOL),
        "--out-dir",
        str(out_dir),
        "--with-textselect-control",
        "--port",
        port,
        "--baud",
        str(baud),
        "--download-baud",
        str(download_baud),
        "--timeout-ms",
        str(timeout_ms),
    ]
    if capture:
        cmd.append("--capture")
    return cmd


def classify_path(before: dict[str, Any], after: dict[str, Any] | None, runner_ran: bool) -> str:
    if before["responsive"]:
        return "runner_started_without_recovery" if runner_ran else "ready_without_recovery"
    if after is None:
        return "blocked_before_recovery"
    if after["responsive"]:
        return "recovered_then_ran_runner" if runner_ran else "recovered_without_runner"
    return "still_silent_after_recovery"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check COM36, optionally try official GUI recovery, then run the prepared seed-side runtime-limit runner.")
    parser.add_argument("--out-dir", required=True, help="Parent output directory for summaries and optional runner results.")
    parser.add_argument("--port", default="COM36")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--download-baud", type=int, default=921600)
    parser.add_argument("--timeout-ms", type=int, default=3000)
    parser.add_argument("--recovery-hmi", default=str(DEFAULT_RECOVERY_HMI))
    parser.add_argument("--recovery-wait-s", type=float, default=260.0)
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-recovery", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    recovery_hmi = Path(args.recovery_hmi).resolve()
    recovery_cmd = build_recovery_command(
        hmi=recovery_hmi,
        port=args.port,
        download_baud=args.download_baud,
        wait_s=args.recovery_wait_s,
    )
    runner_cmd = build_runner_command(
        out_dir=out_dir / "seed_side_runner",
        port=args.port,
        baud=args.baud,
        download_baud=args.download_baud,
        timeout_ms=args.timeout_ms,
        capture=args.capture,
    )

    summary: dict[str, Any] = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "prepared" if args.dry_run else "ran",
        "out_dir": str(out_dir),
        "commands": {
            "serial_connect": _serial_command("connect", port=args.port, baud=args.baud, timeout_ms=args.timeout_ms),
            "serial_sendme": _serial_command("sendme", port=args.port, baud=args.baud, timeout_ms=args.timeout_ms),
            "official_recovery": recovery_cmd,
            "seed_side_runner": runner_cmd,
        },
    }

    if args.dry_run:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    before = serial_snapshot(port=args.port, baud=args.baud, timeout_ms=args.timeout_ms)
    summary["before"] = before

    after = None
    runner_result = None
    recovery_result = None
    runner_ran = False

    if before["responsive"]:
        runner_result = _run_json_command(runner_cmd)
        runner_ran = True
    elif not args.skip_recovery:
        recovery_result = _run_json_command(recovery_cmd)
        after = serial_snapshot(port=args.port, baud=args.baud, timeout_ms=args.timeout_ms)
        if after["responsive"]:
            runner_result = _run_json_command(runner_cmd)
            runner_ran = True

    summary["recovery"] = recovery_result
    summary["after_recovery"] = after
    summary["runner"] = runner_result
    summary["classification"] = classify_path(before, after, runner_ran)
    summary_path = out_dir / "recover_then_seed_side_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if runner_ran else 1


if __name__ == "__main__":
    raise SystemExit(main())
