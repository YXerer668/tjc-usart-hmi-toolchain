from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import serial


TERM = b"\xff\xff\xff"


def main() -> int:
    parser = argparse.ArgumentParser(description="Drive USART HMI e-contest template motion from the host serial port.")
    parser.add_argument("--port", default="COM36")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--frames", type=int, default=72)
    parser.add_argument("--interval-ms", type=int, default=130)
    parser.add_argument("--profile", choices=["header", "power_converter"], default="header")
    parser.add_argument("--out", type=Path, default=Path("build/econtest_serial_motion_demo.json"))
    args = parser.parse_args()

    report: dict[str, object] = {
        "port": args.port,
        "baud": args.baud,
        "frames_requested": args.frames,
        "profile": args.profile,
        "frames": [],
        "invalid_reference_count": 0,
        "invalid_reference_samples": [],
    }

    with serial.Serial(args.port, args.baud, timeout=0.01, write_timeout=1) as ser:
        ser.reset_input_buffer()
        send(ser, "bkcmd=0", report, pause=0.04)
        for index in range(max(args.frames, 0)):
            phase = index % 3
            commands = [
                f"vis sweep_a,{1 if phase == 0 else 0}",
                f"vis sweep_b,{1 if phase == 1 else 0}",
                f"vis sweep_c,{1 if phase == 2 else 0}",
                f"beat.val={index % 1000}",
            ]
            if args.profile == "power_converter":
                commands.extend(
                    [
                        f"m0.val={11800 + (index * 37) % 520}",
                        f"m1.val={4920 + (index * 23) % 220}",
                        f"eff_bar.val={82 + (index % 14)}",
                        f"temp_guard.val={30 + (index % 30)}",
                    ]
                )
            for command in commands:
                send(ser, command, report)
            if index % 6 == 0:
                for command in refresh_commands(args.profile):
                    send(ser, command, report)
            report["frames"].append({"index": index, "phase": phase})  # type: ignore[index]
            time.sleep(max(args.interval_ms, 0) / 1000.0)
        send(ser, "bkcmd=2", report, pause=0.08)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"frames": len(report["frames"]), "invalid_reference_count": report["invalid_reference_count"], "report": str(args.out)}, indent=2))
    return 0


def refresh_commands(profile: str) -> list[str]:
    commands = ["ref beat", "ref sweep_a", "ref sweep_b", "ref sweep_c"]
    if profile == "power_converter":
        commands.extend(["ref m0", "ref m1", "ref eff_bar", "ref temp_guard"])
    return commands


def send(ser: serial.Serial, command: str, report: dict[str, object], *, pause: float = 0.0) -> bytes:
    ser.write(command.encode("ascii") + TERM)
    ser.flush()
    if pause:
        time.sleep(pause)
    deadline = time.monotonic() + 0.025
    response = bytearray()
    while time.monotonic() < deadline:
        chunk = ser.read(64)
        if chunk:
            response.extend(chunk)
        else:
            time.sleep(0.002)
    raw = bytes(response)
    if b"\x1a\xff\xff\xff" in raw:
        report["invalid_reference_count"] = int(report["invalid_reference_count"]) + 1
        samples = report["invalid_reference_samples"]  # type: ignore[assignment]
        if isinstance(samples, list) and len(samples) < 8:
            samples.append({"command": command, "hex": raw.hex(" ")})
    return raw


if __name__ == "__main__":
    raise SystemExit(main())
