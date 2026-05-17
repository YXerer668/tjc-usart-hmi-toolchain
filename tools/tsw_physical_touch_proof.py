from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

import serial


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACK_SCRIPT = REPO_ROOT / "tools" / "wait_user_ack.ps1"
DEFAULT_OUT = (
    REPO_ROOT
    / "reverse_usarthmi"
    / "number_demo_tsw_promotion_gb2312font_20260516"
    / f"physical_touch_proof_{dt.datetime.now():%Y%m%d_%H%M%S}.json"
)
TERM = b"\xff\xff\xff"
MARKERS = {
    "TG": bytes.fromhex("23 02 54 47"),
    "T0": bytes.fromhex("23 02 54 30"),
    "T1": bytes.fromhex("23 02 54 31"),
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def hex_bytes(data: bytes) -> str:
    return " ".join(f"{byte:02X}" for byte in data)


def marker_counts(data: bytes) -> dict[str, int]:
    return {name: data.count(marker) for name, marker in MARKERS.items()}


def encode_command(command: str) -> bytes:
    return command.encode("ascii") + TERM


def read_for(ser: serial.Serial, seconds: float) -> bytes:
    deadline = time.monotonic() + seconds
    chunks: list[bytes] = []
    while time.monotonic() < deadline:
        chunk = ser.read(512)
        if chunk:
            chunks.append(chunk)
        else:
            time.sleep(0.01)
    return b"".join(chunks)


def send_command(ser: serial.Serial, command: str, settle_s: float = 0.1) -> dict[str, Any]:
    started = utc_now()
    ser.write(encode_command(command))
    ser.flush()
    data = read_for(ser, settle_s)
    return {
        "started_at_utc": started,
        "command": command,
        "hex": hex_bytes(data),
        "counts": marker_counts(data),
    }


def decode_string_response(data: bytes) -> tuple[str | None, str | None]:
    stripped = data[:-3] if data.endswith(TERM) else data
    if not stripped or stripped[0] != 0x70:
        return None, None
    payload = stripped[1:]
    for encoding in ("gbk", "utf-8", "ascii"):
        try:
            return payload.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return payload.decode("gbk", errors="replace"), "gbk-replace"


def read_title(ser: serial.Serial, expected: str) -> dict[str, Any]:
    started = utc_now()
    ser.write(encode_command("get title.txt"))
    ser.flush()
    data = read_for(ser, 0.5)
    value, encoding = decode_string_response(data)
    return {
        "started_at_utc": started,
        "command": "get title.txt",
        "expected": expected,
        "actual": value,
        "encoding": encoding,
        "hex": hex_bytes(data),
        "ok": value == expected,
    }


def tap_button(ser: serial.Serial, obj: str, expected: str) -> dict[str, Any]:
    started = utc_now()
    down = send_command(ser, f"click {obj},1", 0.25)
    up = send_command(ser, f"click {obj},0", 0.15)
    data = bytes.fromhex((down["hex"] + " " + up["hex"]).strip()) if (down["hex"] or up["hex"]) else b""
    counts = marker_counts(data)
    return {
        "started_at_utc": started,
        "object": obj,
        "commands": [down, up],
        "expected_marker": expected,
        "hex": hex_bytes(data),
        "counts": counts,
        "ok": counts.get(expected, 0) >= 1,
    }


def set_title(ser: serial.Serial, text: str) -> dict[str, Any]:
    # Title-only prompts avoid refreshing or rewriting targetbtn after disable.
    started = utc_now()
    commands = [
        send_command(ser, f'title.txt="{text}"', 0.1),
        send_command(ser, "ref title", 0.1),
    ]
    data = bytes.fromhex(
        " ".join(item["hex"] for item in commands if item["hex"]).strip()
    ) if any(item["hex"] for item in commands) else b""
    return {
        "started_at_utc": started,
        "title": text,
        "commands": commands,
        "hex": hex_bytes(data),
        "counts": marker_counts(data),
    }


def wait_for_marker(
    ser: serial.Serial, marker_name: str, timeout_s: float, label: str
) -> dict[str, Any]:
    started = utc_now()
    marker = MARKERS[marker_name]
    deadline = time.monotonic() + timeout_s
    data = bytearray()
    seen_at: str | None = None

    while time.monotonic() < deadline:
        chunk = ser.read(512)
        if chunk:
            data.extend(chunk)
            if marker in data:
                seen_at = utc_now()
                data.extend(read_for(ser, 0.25))
                break
        else:
            time.sleep(0.01)

    return {
        "label": label,
        "started_at_utc": started,
        "timeout_s": timeout_s,
        "wait_for": marker_name,
        "seen": seen_at is not None,
        "seen_at_utc": seen_at,
        "hex": hex_bytes(bytes(data)),
        "counts": marker_counts(bytes(data)),
    }


def observe_window(ser: serial.Serial, seconds: float, label: str) -> dict[str, Any]:
    started = utc_now()
    data = read_for(ser, seconds)
    return {
        "label": label,
        "started_at_utc": started,
        "duration_s": seconds,
        "hex": hex_bytes(data),
        "counts": marker_counts(data),
    }


def run_ack(args: argparse.Namespace) -> dict[str, Any]:
    if args.no_ack:
        return {
            "ok": True,
            "result": "continue",
            "skipped": True,
            "reason": "--no-ack",
        }

    command = [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(args.ack_script),
        "-Title",
        args.ack_title,
        "-Message",
        args.ack_message,
        "-ContinueText",
        args.continue_text,
        "-CancelText",
        args.cancel_text,
        "-TimeoutSeconds",
        str(args.ack_timeout_s),
    ]
    started = utc_now()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        payload = {"ok": False, "result": "parse_error", "stdout": completed.stdout}
    payload.update(
        {
            "command": command,
            "returncode": completed.returncode,
            "started_at_utc": started,
            "stderr": completed.stderr.strip(),
        }
    )
    return payload


def dry_run_report(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "source": "codex_tsw_physical_touch_proof_runner",
        "created_at_utc": utc_now(),
        "status": "dry_run",
        "port": args.port,
        "baud": args.baud,
        "ack_script": str(args.ack_script),
        "protocol": [
            "Run blocking confirmation popup first.",
            "Open COM port only after confirmation.",
            "Release targetbtn/disablebtn/enablebtn.",
            "Verify title.txt is the expected TSW PROMOTION page unless skipped.",
            "Set title to TAP TARGET and wait for physical TARGET TG.",
            "Abort before disable if baseline TG is not captured.",
            "Serial-click DISABLE and verify T0.",
            "Set title to TRY TARGET without writing/ref targetbtn.",
            "Observe disabled window for TG.",
            "Serial-click ENABLE and verify T1.",
            "Set title to TAP AGAIN and wait for recovery TG.",
            "Restore page 0 at the end.",
        ],
        "claim_rule": (
            "physical_touch_lockout_live_observed is true only when state markers "
            "are OK, baseline TG is captured, disabled-window TG is zero, and "
            "recovery TG is captured."
        ),
    }


def run_proof(args: argparse.Namespace) -> dict[str, Any]:
    report: dict[str, Any] = {
        "source": "codex_tsw_physical_touch_proof_runner",
        "created_at_utc": utc_now(),
        "port": args.port,
        "baud": args.baud,
        "input_path": "physical finger touch for TARGET windows; serial click only sets DISABLE/ENABLE state",
        "safety_rules": [
            "Do not write or ref targetbtn after disable.",
            "Abort before disable if baseline TG is not captured.",
            "Restore page 0 at the end.",
        ],
        "ack": run_ack(args),
        "pre_release": [],
        "ui_prompts": [],
        "state_commands": [],
        "windows": [],
    }

    if not report["ack"].get("ok"):
        report["status"] = "no_user_confirmation"
        report["summary"] = {"physical_touch_lockout_live_observed": False}
        return report

    try:
        with serial.Serial(args.port, args.baud, timeout=0.02, write_timeout=1.0) as ser:
            time.sleep(0.2)
            read_for(ser, 0.4)
            if not args.skip_title_check:
                report["page_check"] = read_title(ser, args.expect_title)
                if not report["page_check"]["ok"]:
                    report["status"] = "wrong_page"
                    return report
            for obj in ("targetbtn", "disablebtn", "enablebtn"):
                report["pre_release"].append(send_command(ser, f"click {obj},0", 0.05))

            report["state_commands"].append(tap_button(ser, "enablebtn", "T1"))
            report["ui_prompts"].append(set_title(ser, "TAP TARGET"))
            baseline = wait_for_marker(
                ser,
                "TG",
                args.baseline_timeout_s,
                "baseline_enabled_wait_for_target",
            )
            report["windows"].append(baseline)
            if baseline["counts"]["TG"] < 1:
                report["status"] = "baseline_timeout"
                return report

            report["state_commands"].append(tap_button(ser, "disablebtn", "T0"))
            report["ui_prompts"].append(set_title(ser, "TRY TARGET"))
            report["windows"].append(
                observe_window(ser, args.disabled_window_s, "disabled_try_target")
            )

            report["state_commands"].append(tap_button(ser, "enablebtn", "T1"))
            report["ui_prompts"].append(set_title(ser, "TAP AGAIN"))
            report["windows"].append(
                wait_for_marker(
                    ser,
                    "TG",
                    args.recovery_timeout_s,
                    "reenabled_wait_for_target",
                )
            )
            report["status"] = "completed"
    finally:
        try:
            with serial.Serial(args.port, args.baud, timeout=0.02, write_timeout=1.0) as ser:
                time.sleep(0.1)
                report["restore"] = send_command(ser, "page 0", 0.4)
        except Exception as exc:  # pragma: no cover - hardware cleanup best effort
            report["restore_error"] = repr(exc)

    return report


def finalize_summary(report: dict[str, Any]) -> dict[str, Any]:
    windows = {item["label"]: item["counts"] for item in report.get("windows", [])}
    baseline_tg = windows.get("baseline_enabled_wait_for_target", {}).get("TG", 0)
    disabled_tg = windows.get("disabled_try_target", {}).get("TG", 0)
    recovery_tg = windows.get("reenabled_wait_for_target", {}).get("TG", 0)
    state_markers_ok = all(item.get("ok") for item in report.get("state_commands", []))
    summary = {
        "baseline_tg_count": baseline_tg,
        "disabled_tg_count": disabled_tg,
        "recovery_tg_count": recovery_tg,
        "state_markers_ok": state_markers_ok,
        "physical_touch_lockout_live_observed": bool(
            state_markers_ok
            and baseline_tg >= 1
            and disabled_tg == 0
            and recovery_tg >= 1
        ),
    }
    report["summary"] = summary
    if "status" not in report:
        report["status"] = "completed"
    return report


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="User-gated physical-touch proof runner for the TSW PROMOTION fixture."
    )
    parser.add_argument("--port", default="COM36")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--ack-script", type=Path, default=DEFAULT_ACK_SCRIPT)
    parser.add_argument("--ack-timeout-s", type=int, default=300)
    parser.add_argument("--ack-title", default="TJC touch needed")
    parser.add_argument(
        "--ack-message",
        default=(
            "看到 TSW PROMOTION 页面后点继续；接下来只按屏幕标题提示触摸 TARGET。"
        ),
    )
    parser.add_argument("--continue-text", default="继续")
    parser.add_argument("--cancel-text", default="取消")
    parser.add_argument("--baseline-timeout-s", type=float, default=120.0)
    parser.add_argument("--disabled-window-s", type=float, default=20.0)
    parser.add_argument("--recovery-timeout-s", type=float, default=120.0)
    parser.add_argument("--expect-title", default="TSW PROMOTION")
    parser.add_argument("--skip-title-check", action="store_true")
    parser.add_argument("--no-ack", action="store_true", help="Skip popup; for manual lab use only.")
    parser.add_argument("--dry-run", action="store_true", help="Describe the protocol without opening serial.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.dry_run:
        report = dry_run_report(args)
    else:
        report = finalize_summary(run_proof(args))

    write_report(args.out, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if args.dry_run:
        return 0
    status = report.get("status")
    if status == "no_user_confirmation":
        return 2
    if status == "baseline_timeout":
        return 3
    if status == "wrong_page":
        return 4
    if report.get("summary", {}).get("physical_touch_lockout_live_observed"):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
