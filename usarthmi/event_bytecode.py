from __future__ import annotations

from typing import Any


COMMAND_PREFIXES: dict[bytes, tuple[str, str]] = {
    b"\x09\x00\x08": ("command", "click"),
    b"\x09\x03\x04": ("command", "ref"),
    b"\x09\x05\x04": ("command", "vis"),
    b"\x09\x09\x04": ("command", "tsw"),
    b"\x09\x0c\x04": ("command", "page"),
    b"\x09\x0f\x08": ("command", "printh"),
    b"\x09\x1f\x04": ("separator", "post_primary_page_load"),
    b"\x09\x28\x04": ("command", "play"),
    b"\x09\x30\x08": ("separator", "loadend"),
}

ASCII_MARKERS = {"down", "up", "unload", "timer", "slide", "playend"}


def decode_event_table(data: bytes) -> list[dict[str, Any]]:
    """Decode the recovered length-prefixed USART HMI event bytecode table.

    The decoder is intentionally descriptive rather than executable. It is used
    by fixture probes to make event tables reviewable before any writer behavior
    is trusted on hardware.
    """

    items: list[dict[str, Any]] = []
    cursor = 0
    index = 0
    while cursor + 4 <= len(data):
        length = int.from_bytes(data[cursor : cursor + 4], "little")
        payload_start = cursor + 4
        payload_end = payload_start + length
        if payload_end > len(data):
            items.append(
                {
                    "index": index,
                    "offset": cursor,
                    "offset_hex": f"0x{cursor:X}",
                    "length": length,
                    "kind": "truncated",
                    "payload_hex": data[payload_start:].hex(" "),
                }
            )
            return items
        payload = data[payload_start:payload_end]
        item = {
            "index": index,
            "offset": cursor,
            "offset_hex": f"0x{cursor:X}",
            "length": length,
            "payload_hex": payload.hex(" "),
            **_decode_payload(payload),
        }
        items.append(item)
        cursor = payload_end
        index += 1
    if cursor != len(data):
        items.append(
            {
                "index": index,
                "offset": cursor,
                "offset_hex": f"0x{cursor:X}",
                "length": len(data) - cursor,
                "kind": "trailing_bytes",
                "payload_hex": data[cursor:].hex(" "),
            }
        )
    return items


def _decode_payload(payload: bytes) -> dict[str, Any]:
    if not payload:
        return {"kind": "empty"}

    ascii_text = _printable_ascii(payload)
    if ascii_text in ASCII_MARKERS:
        return {"kind": "marker", "name": ascii_text}

    if payload.startswith(b"\x01") and len(payload) >= 6:
        slot = int.from_bytes(payload[1:5], "little")
        op_text = _ascii(payload[5:])
        decoded: dict[str, Any] = {
            "kind": "property_event",
            "slot": slot,
            "slot_hex": f"0x{slot:X}",
            "operation": op_text,
        }
        if op_text.startswith("="):
            decoded["operator"] = "="
            decoded["value"] = op_text[1:]
        elif op_text in {"++", "--"}:
            decoded["operator"] = op_text
        return decoded

    if payload.startswith(b"\x04\x08\x12\x00\x00="):
        return {
            "kind": "global_assignment",
            "name": "volume",
            "operator": "=",
            "value": _ascii(payload[6:]),
        }

    for prefix, (kind, command) in COMMAND_PREFIXES.items():
        if payload.startswith(prefix):
            decoded = {"kind": kind, "command": command}
            args = payload[len(prefix) :]
            if args:
                decoded["args"] = _ascii(args)
            return decoded

    if ascii_text:
        return {"kind": "ascii", "text": ascii_text}
    return {"kind": "unknown"}


def _ascii(data: bytes) -> str:
    try:
        return data.decode("ascii")
    except UnicodeDecodeError:
        return ""


def _printable_ascii(data: bytes) -> str:
    text = _ascii(data)
    if text and all(32 <= ord(char) < 127 for char in text):
        return text
    return ""
