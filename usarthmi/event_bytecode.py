from __future__ import annotations

from typing import Any


COMMAND_PREFIXES: dict[bytes, tuple[str, str]] = {
    b"\x09\x00\x08": ("command", "click"),
    b"\x09\x03\x04": ("command", "ref"),
    b"\x09\x05\x04": ("command", "vis"),
    b"\x09\x09\x04": ("command", "tsw"),
    b"\x09\x0c\x04": ("command", "page"),
    b"\x09\x0f\x08": ("command", "printh"),
    b"\x09\x19\x08": ("command", "newfile"),
    b"\x09\x1f\x04": ("separator", "post_primary_page_load"),
    b"\x09\x28\x04": ("command", "play"),
    b"\x09\x29\x08": ("command", "findfile"),
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

    if payload.startswith(b"\x01") and len(payload) >= 7 and payload[5:6] == b"(" and payload.endswith(b")"):
        return _decode_method_call(payload)

    if payload.startswith(b"\x01") and len(payload) >= 6:
        slot = int.from_bytes(payload[1:5], "little")
        op_data = payload[5:]
        op_text = _ascii(op_data)
        decoded: dict[str, Any] = {
            "kind": "property_event",
            "slot": slot,
            "slot_hex": f"0x{slot:X}",
            "operation": op_text,
        }
        if op_data.startswith(b"+=") or op_data.startswith(b"-="):
            decoded["operator"] = op_data[:2].decode("ascii")
            _decode_assignment_rhs(decoded, op_data[2:])
        elif op_data.startswith(b"="):
            decoded["operator"] = "="
            _decode_assignment_rhs(decoded, op_data[1:])
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

    if payload.startswith(b"\x09\x29\x08"):
        return _decode_file_command("findfile", payload[3:])

    if payload.startswith(b"\x09\x19\x08"):
        return _decode_file_command("newfile", payload[3:])

    if payload.startswith(b"\x09\x02\x08"):
        return _decode_two_part_command("btlen", payload[3:], ("source", "target"))

    if payload.startswith(b"\x09\x18\x08"):
        return {
            "kind": "command",
            "command": "repo",
            "target": _decode_operand(payload[3:]),
        }

    if payload.startswith(b"\x09\x12\x04"):
        return _decode_two_part_command("wepo", payload[3:], ("target", "index"))

    if payload.startswith(b"\x09\x27\x04"):
        return _decode_four_part_command("covx", payload[3:])

    if payload.startswith(b"\x09\x00\x04"):
        return _decode_sys_eq_condition(payload[3:])

    if payload.startswith(b"\x09\x04\x08"):
        return _decode_four_part_command("spstr", payload[3:], ("source", "target", "separator", "index"))

    if payload.startswith(b"\x54\x20"):
        return {
            "kind": "jump",
            "command": "else_jump",
            "skip_bytes": _decode_operand(payload[2:]),
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


def _decode_method_call(payload: bytes) -> dict[str, Any]:
    slot = int.from_bytes(payload[1:5], "little")
    return {
        "kind": "method_call",
        "slot": slot,
        "slot_hex": f"0x{slot:X}",
        "args": [_decode_operand(part.strip()) for part in _split_command_args(payload[6:-1])],
    }


def _decode_assignment_rhs(decoded: dict[str, Any], rhs: bytes) -> None:
    expression = _decode_expression(rhs)
    if expression is not None:
        decoded["expression"] = expression
        return
    text = _decode_event_text(rhs)
    if text:
        decoded["value"] = text
    else:
        decoded["operand"] = _decode_operand(rhs)


def _decode_file_command(command: str, data: bytes) -> dict[str, Any]:
    path, sep, operand = data.partition(b",")
    decoded: dict[str, Any] = {
        "kind": "command",
        "command": command,
        "path": _decode_event_text(path),
    }
    if sep:
        decoded["target" if command == "findfile" else "size"] = _decode_operand(operand)
    return decoded


def _decode_two_part_command(command: str, data: bytes, names: tuple[str, str]) -> dict[str, Any]:
    left, sep, right = data.partition(b",")
    decoded: dict[str, Any] = {
        "kind": "command",
        "command": command,
        names[0]: _decode_operand(left),
    }
    if sep:
        decoded[names[1]] = _decode_operand(right)
    return decoded


def _decode_four_part_command(
    command: str,
    data: bytes,
    names: tuple[str, str, str, str] = ("source", "target", "source_type", "target_type"),
) -> dict[str, Any]:
    parts = _split_command_args(data)
    decoded: dict[str, Any] = {"kind": "command", "command": command}
    if len(parts) >= 1:
        decoded[names[0]] = _decode_operand(parts[0])
    if len(parts) >= 2:
        decoded[names[1]] = _decode_operand(parts[1])
    if len(parts) >= 3:
        decoded[names[2]] = _decode_operand(parts[2])
    if len(parts) >= 4:
        decoded[names[3]] = _decode_operand(parts[3])
    return decoded


def _decode_expression(data: bytes) -> dict[str, Any] | None:
    left, sep, right = data.partition(b"+")
    if not sep:
        return None
    return {
        "operator": "+",
        "left": _decode_operand(left),
        "right": _decode_operand(right),
    }


def _decode_sys_eq_condition(data: bytes) -> dict[str, Any]:
    left = _decode_operand(data[:5])
    rest = data[5:]
    left_kind = left.get("kind")
    decoded: dict[str, Any] = {
        "kind": "condition",
        "command": "if_sys_eq" if left_kind == "sys_ref" else "if_field_eq",
        "left": left,
    }
    if rest.startswith(b","):
        parts = rest[1:].split(b",", 2)
        if len(parts) == 3:
            condition_code = _ascii(parts[1])
            operator = {"1": "==", "2": "<", "6": "!="}.get(condition_code, f"code_{condition_code}")
            suffix = {"==": "eq", "<": "lt", "!=": "ne"}.get(operator, "unknown")
            decoded["command"] = f"if_{'sys' if left_kind == 'sys_ref' else 'field'}_{suffix}"
            decoded["operator"] = operator
            expected_text = _decode_event_text(parts[0])
            if expected_text:
                decoded["expected"] = expected_text
            else:
                decoded["right"] = _decode_operand(parts[0])
            decoded["true_code"] = condition_code
            decoded["false_skip_bytes"] = _decode_operand(parts[2])
    return decoded


def _decode_operand(data: bytes) -> dict[str, Any]:
    data = data.strip()
    if len(data) == 5 and data.startswith(b"\x01"):
        slot = int.from_bytes(data[1:5], "little")
        return {"kind": "field_ref", "slot": slot, "slot_hex": f"0x{slot:X}"}
    if len(data) == 5 and data.startswith(b"\x03"):
        return {"kind": "integer", "value": int.from_bytes(data[1:5], "little")}
    if len(data) == 5 and data.startswith(b"\x05"):
        index = int.from_bytes(data[1:5], "little")
        return {"kind": "sys_ref", "index": index, "name": f"sys{index}"}
    if data == b"\x04\x04\x00\x00\x00":
        return {"kind": "global_ref", "name": "dp"}
    text = _decode_event_text(data)
    if text:
        return {"kind": "text", "value": text}
    return {"kind": "raw", "payload_hex": data.hex(" ")}


def _split_command_args(data: bytes) -> list[bytes]:
    return data.split(b",") if data else []


def _decode_event_text(data: bytes) -> str:
    if not data:
        return ""
    for encoding in ("ascii", "utf-8", "gbk"):
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        if _is_readable_event_text(text):
            return text
    return ""


def _is_readable_event_text(text: str) -> bool:
    return bool(text) and all(char in "\r\n\t" or ord(char) >= 32 for char in text)


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
