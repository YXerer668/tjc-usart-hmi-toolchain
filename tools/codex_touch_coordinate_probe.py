from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import serial

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from usarthmi.transport import TERMINATOR  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture physical touch coordinate frames from a TJC/USART HMI panel.")
    parser.add_argument("--port", default="COM36")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--page", default="0")
    parser.add_argument("--target-name", default="logbtn")
    parser.add_argument("--target-rect", default="416,386,104,52", help="x,y,w,h")
    parser.add_argument(
        "--zone",
        action="append",
        default=[],
        help="Extra hit zone as name:x,y,w,h. Can be repeated.",
    )
    args = parser.parse_args()

    target_rect = tuple(int(part.strip()) for part in args.target_rect.split(","))
    if len(target_rect) != 4:
        raise SystemExit("--target-rect must be x,y,w,h")
    zones = {"target": target_rect}
    for spec in args.zone:
        name, rect_text = spec.split(":", 1)
        rect = tuple(int(part.strip()) for part in rect_text.split(","))
        if len(rect) != 4:
            raise SystemExit(f"--zone must be name:x,y,w,h, got {spec!r}")
        zones[name] = rect

    result: dict[str, Any] = {
        "port": args.port,
        "baud": args.baud,
        "duration_s": args.seconds,
        "page": args.page,
        "target_name": args.target_name,
        "target_rect": list(target_rect),
        "zones": {name: list(rect) for name, rect in zones.items()},
        "setup": [],
        "frames": [],
        "summary": {},
    }

    with serial.Serial(args.port, args.baud, timeout=0.02, write_timeout=1.0) as ser:
        ser.reset_input_buffer()
        for command in [
            "bkcmd=3",
            f"page {args.page}",
            "tsw 255,1",
            f"tsw {args.target_name},1",
            f"vis {args.target_name},1",
            f"ref {args.target_name}",
            "sendxy=1",
        ]:
            result["setup"].append(send_command(ser, command))
            time.sleep(0.08)
        result["frames"] = capture_frames(ser, args.seconds, zones)
        result["teardown"] = [send_command(ser, "sendxy=0")]

    touches = [frame for frame in result["frames"] if frame.get("kind") in {"touch_coordinate", "touch_coordinate_sleep"}]
    zone_hits: dict[str, int] = {name: 0 for name in zones}
    for frame in touches:
        for name in frame.get("zones", []):
            zone_hits[name] = zone_hits.get(name, 0) + 1
    inside = [frame for frame in touches if "target" in frame.get("zones", [])]
    markers = [frame for frame in result["frames"] if frame.get("kind") == "ascii"]
    result["summary"] = {
        "touch_frame_count": len(touches),
        "inside_target_count": len(inside),
        "zone_hits": zone_hits,
        "ascii_markers": [frame.get("value") for frame in markers],
        "frames_captured": len(result["frames"]),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0


def send_command(ser: serial.Serial, command: str) -> dict[str, Any]:
    sent = command.encode("ascii") + TERMINATOR
    ser.write(sent)
    ser.flush()
    raw = read_for(ser, 0.18)
    return {"command": command, "sent_hex": sent.hex(" "), "response_hex": raw.hex(" "), "frames": parse_stream(raw, None)}


def capture_frames(ser: serial.Serial, seconds: float, zones: dict[str, tuple[int, int, int, int]]) -> list[dict[str, Any]]:
    deadline = time.monotonic() + max(seconds, 0.1)
    frames: list[dict[str, Any]] = []
    buffer = bytearray()
    while time.monotonic() < deadline:
        chunk = ser.read(ser.in_waiting or 1)
        if chunk:
            buffer.extend(chunk)
            parsed, remainder = parse_available(buffer, zones)
            frames.extend(parsed)
            buffer = bytearray(remainder)
    if buffer:
        frames.extend(parse_stream(bytes(buffer), zones))
    return frames


def read_for(ser: serial.Serial, seconds: float) -> bytes:
    deadline = time.monotonic() + seconds
    data = bytearray()
    while time.monotonic() < deadline:
        chunk = ser.read(ser.in_waiting or 1)
        if chunk:
            data.extend(chunk)
    return bytes(data)


def parse_available(buffer: bytearray, zones: dict[str, tuple[int, int, int, int]]) -> tuple[list[dict[str, Any]], bytes]:
    frames: list[dict[str, Any]] = []
    data = bytes(buffer)
    start = 0
    while True:
        end = data.find(TERMINATOR, start)
        if end < 0:
            return frames, data[start:]
        frame = data[start : end + len(TERMINATOR)]
        frames.extend(parse_frame(frame, zones))
        start = end + len(TERMINATOR)


def parse_stream(raw: bytes, zones: dict[str, tuple[int, int, int, int]] | None) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    start = 0
    while start < len(raw):
        end = raw.find(TERMINATOR, start)
        if end < 0:
            tail = raw[start:]
            if tail:
                frames.append(parse_tail(tail))
            break
        frames.extend(parse_frame(raw[start : end + len(TERMINATOR)], zones))
        start = end + len(TERMINATOR)
    return frames


def parse_frame(raw: bytes, zones: dict[str, tuple[int, int, int, int]] | None) -> list[dict[str, Any]]:
    stripped = raw[:-3] if raw.endswith(TERMINATOR) else raw
    if not stripped:
        return [{"kind": "empty", "hex": raw.hex(" ")}]
    prefix, stripped = split_printable_prefix(stripped)
    items: list[dict[str, Any]] = []
    if prefix:
        items.append({"kind": "ascii", "value": prefix.decode("ascii"), "hex": prefix.hex(" ")})
    if not stripped:
        return items
    code = stripped[0]
    item: dict[str, Any] = {"code": code, "hex": raw.hex(" ")}
    if code in {0x67, 0x68} and len(stripped) >= 6:
        x = int.from_bytes(stripped[1:3], "big", signed=False)
        y = int.from_bytes(stripped[3:5], "big", signed=False)
        event = stripped[5]
        item.update(
            {
                "kind": "touch_coordinate" if code == 0x67 else "touch_coordinate_sleep",
                "x": x,
                "y": y,
                "event": event,
                "event_name": "press" if event == 1 else "release" if event == 0 else str(event),
            }
        )
        if zones is not None:
            item["zones"] = [
                name
                for name, (tx, ty, tw, th) in zones.items()
                if tx <= x < tx + tw and ty <= y < ty + th
            ]
        items.append(item)
        return items
    if code == 0x65 and len(stripped) >= 4:
        item.update({"kind": "touch_event", "page": stripped[1], "component": stripped[2], "event": stripped[3]})
        items.append(item)
        return items
    try:
        text = stripped.decode("ascii")
    except UnicodeDecodeError:
        text = None
    if text and all((ch == "\t" or ch == "\r" or ch == "\n" or 32 <= ord(ch) <= 126) for ch in text):
        item.update({"kind": "ascii", "value": text})
    else:
        item["kind"] = "unknown"
    items.append(item)
    return items


def parse_tail(raw: bytes) -> dict[str, Any]:
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        text = None
    if text and all((ch == "\t" or ch == "\r" or ch == "\n" or 32 <= ord(ch) <= 126) for ch in text):
        return {"kind": "ascii", "value": text, "hex": raw.hex(" ")}
    return {"kind": "partial", "hex": raw.hex(" ")}


def split_printable_prefix(raw: bytes) -> tuple[bytes, bytes]:
    if raw and raw[0] in {0x67, 0x68, 0x65, 0x01, 0x00, 0x1A, 0x1B}:
        return b"", raw
    for offset, value in enumerate(raw):
        if value in {0x67, 0x68, 0x65, 0x01, 0x00, 0x1A, 0x1B}:
            prefix = raw[:offset]
            if prefix and all(32 <= byte <= 126 or byte in {9, 10, 13} for byte in prefix):
                return prefix, raw[offset:]
            break
    return b"", raw


if __name__ == "__main__":
    raise SystemExit(main())
