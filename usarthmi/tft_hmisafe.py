from __future__ import annotations

import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

UINT32 = 0xFFFFFFFF
CRC_POLY = 0x04C11DB7
CRC_INIT = 0xFFFFFFFF
CRC_CHUNK = 0x100000
TFT_HEADER_LEN = 400
APPFREE10_KEY_SEED = b"A678ert"
VERIFIED_FINALIZE_MODE = 0x03
UNVERIFIED_APPFREE11_MODE = 0x64


class HmiSafeUnsupportedModeError(ValueError):
    """Raised when a TFT asks for an unverified HmiSafe write path."""


def _u32(value: int) -> int:
    return value & UINT32


def _build_crc_table() -> list[int]:
    table: list[int] = []
    for i in range(256):
        crc = i << 24
        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) & UINT32) ^ CRC_POLY
            else:
                crc = (crc << 1) & UINT32
        table.append(crc)
    return table


CRC_TABLE = _build_crc_table()


def crc_type10_update(seed: int, data: bytes | bytearray | memoryview) -> int:
    """ACServer type-10 byte update: poly 0x04c11db7, no reflect, no xorout."""
    crc = seed & UINT32
    for b in data:
        crc = _u32(crc ^ b)
        for _ in range(4):
            crc = _u32((crc << 8) ^ CRC_TABLE[(crc >> 24) & 0xFF])
    return crc


def crc_type11_update(seed: int, data: bytes | bytearray | memoryview) -> int:
    """ACServer type-11 little-endian u32 update."""
    if len(data) & 3:
        return seed & UINT32

    crc = seed & UINT32
    view = memoryview(data)
    for off in range(0, len(view), 4):
        word = struct.unpack_from("<I", view, off)[0]
        crc = _u32(crc ^ word)
        for _ in range(4):
            crc = _u32((crc << 8) ^ CRC_TABLE[(crc >> 24) & 0xFF])
    return crc


def acserver_get_file_crc(
    data: bytes | bytearray,
    seed: int = CRC_INIT,
    beg: int = 0,
    length: int | None = None,
    crctype: int = 10,
    chunk_size: int = CRC_CHUNK,
) -> int:
    """Reproduce achmi.dll ACServerGetFileCRC for in-memory TFT data."""
    if length is None:
        length = len(data) - beg
    if beg < 0 or length < 0 or beg + length > len(data):
        raise ValueError(f"CRC range outside file: beg={beg}, length={length}, size={len(data)}")

    crc = seed & UINT32
    end = beg + length
    pos = beg
    while pos < end:
        n = min(chunk_size, end - pos)
        chunk = memoryview(data)[pos : pos + n]
        if crctype == 10:
            crc = crc_type10_update(crc, chunk)
        else:
            crc = crc_type11_update(crc, chunk)
        pos += n
    return crc


def choose_final_crc_type(mode_byte: int) -> int:
    return 10 if mode_byte in (0x00, 0x01, 0x64) else 11


def hmisafe_finalizer_support(mode_byte: int) -> dict[str, Any]:
    if mode_byte == VERIFIED_FINALIZE_MODE:
        return {
            "supported": True,
            "status": "verified_mode3_byte_identical",
            "note": "mode 3 finalizer is verified by true pre-HmiSafe -> official final byte-identical fixture",
        }
    if mode_byte == UNVERIFIED_APPFREE11_MODE:
        return {
            "supported": False,
            "status": "unverified_appfree11_fail_closed",
            "note": "mode 0x64/Appfree11Encode is recognized from native code but lacks a true pre/final byte-identical sample",
        }
    return {
        "supported": False,
        "status": "unverified_mode_fail_closed",
        "note": f"HmiSafe finalizer mode 0x{mode_byte:02X} is not covered by the verified mode-3 fixture",
    }


def require_verified_finalizer_mode(mode_byte: int) -> None:
    support = hmisafe_finalizer_support(mode_byte)
    if not support["supported"]:
        raise HmiSafeUnsupportedModeError(str(support["note"]))


def model_crc_from_header(header: bytes | bytearray) -> int:
    model_low = struct.unpack_from("<H", header, 0x2E)[0]
    model_high = struct.unpack_from("<H", header, 0x30)[0]
    return _u32(model_low | (model_high << 16))


def appfree10_header_xor_key(model_crc: int) -> int:
    crc = crc_type10_update(CRC_INIT, APPFREE10_KEY_SEED)
    crc = crc_type10_update(crc, struct.pack("<I", model_crc))
    return crc


def xor_appfree10_header_region(header: bytearray, model_crc: int) -> int:
    key_u32 = appfree10_header_xor_key(model_crc)
    key = struct.pack("<I", key_u32)
    for i in range(0x4C):
        header[0xC8 + i] ^= key[i & 3]
    return key_u32


def _add_to_selected_byte(value: int, byte_offset: int, addend: int) -> int:
    shift = byte_offset * 8
    old = (value >> shift) & 0xFF
    new = (old + addend) & 0xFF
    return (value & ~(0xFF << shift)) | (new << shift)


def appfree11_encode_region(region: bytearray, model_crc: int) -> None:
    raise HmiSafeUnsupportedModeError(
        "mode 0x64/Appfree11Encode is recognized but not verified with a true pre/final sample; "
        "HmiSafe finalization is disabled for this path"
    )


def _experimental_appfree11_encode_region(region: bytearray, model_crc: int) -> None:
    """Unverified native Appfree11 translation retained for future sample work."""
    schedule = [0xB6, 0x59, 0x26, 0x58, 0x9C, 0x9C, 0x82, 0xBD]
    local_18 = 0x924F6584
    local_14 = 0xFBAD3BBF
    idx = 0
    param = model_crc & UINT32

    for off in range(0, len(region) & ~3, 4):
        k = schedule[idx]
        word = struct.unpack_from("<I", region, off)[0]

        work = _u32((local_14 << (k & 7)) + local_18 + param)
        mixed = _u32((word ^ work) + work + param)

        next_param = _u32(param * 2)
        next_param = (next_param & 0xFFFFFF00) | (((next_param & 0xFF) + (k ^ 0xBC)) & 0xFF)
        param = next_param

        work = _u32(local_14 + local_18 + param)
        mixed = _u32((work ^ mixed) + work + local_18)

        local_18 = _u32(local_18 * 4)
        local_18 = _add_to_selected_byte(local_18, 3 - (k & 3), k ^ 0x58)

        old_local_14 = local_14
        work2 = _u32((local_18 + param) ^ local_14)
        local_14 = _u32(local_14 * 8)
        work2 = _u32((~work2 - off) - 8)
        local_14 = _add_to_selected_byte(local_14, 3 - (k & 3), k ^ 0x7A)

        out_word = _u32((work2 ^ mixed) + old_local_14 + work2)
        struct.pack_into("<I", region, off, out_word)

        idx = 0 if idx == 7 else idx + 1


@dataclass(frozen=True)
class HmiSafeProfile:
    safe_01: int = 0x01
    safe_02: int = 0x43
    safe_17: int = 0x06
    copy_profile_header: bytes | None = None


@dataclass(frozen=True)
class FinalizeInfo:
    size: int
    mode: int
    final_crc_type: int
    model_crc: int
    header_crc: int
    header_tail_crc: int
    header_xor_key: int | None
    file_crc: int
    footer: int

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["header_crc_hex"] = f"0x{self.header_crc:08X}"
        data["header_tail_crc_hex"] = f"0x{self.header_tail_crc:08X}"
        data["file_crc_hex"] = f"0x{self.file_crc:08X}"
        data["footer_hex"] = f"0x{self.footer:08X}"
        if self.header_xor_key is not None:
            data["header_xor_key_hex"] = f"0x{self.header_xor_key:08X}"
        return data


def refresh_final_tft_checksums(data: bytes | bytearray) -> tuple[bytes, FinalizeInfo]:
    """Refresh CRC fields after patching an already-HmiSafe-finalized TFT.

    Unlike finalize_tft(), this does not reapply the native header patching or
    XOR pass. It is for narrow byte patches against an existing final TFT, such
    as editing an encoded Header2 field with the correct model XOR key.
    """
    if len(data) < TFT_HEADER_LEN + 4:
        raise ValueError(f"TFT is too small: {len(data)} bytes")

    out = bytearray(data)
    header = bytearray(out[:TFT_HEADER_LEN])
    require_verified_finalizer_mode(header[0x15])

    header_crc = crc_type10_update(CRC_INIT, header[:0xC4])
    struct.pack_into("<I", header, 0xC4, header_crc)

    header_tail_crc = crc_type10_update(CRC_INIT, header[0xC8:0x18C])
    struct.pack_into("<I", header, 0x18C, header_tail_crc)
    out[:TFT_HEADER_LEN] = header

    mode = header[0x15]
    crctype = choose_final_crc_type(mode)
    file_crc = acserver_get_file_crc(out, CRC_INIT, 0, len(out) - 4, crctype)
    footer = _u32(file_crc ^ (header[0x2E] ^ header[0x3C] ^ header[0x03]))
    struct.pack_into("<I", out, len(out) - 4, footer)

    return bytes(out), FinalizeInfo(
        size=len(out),
        mode=mode,
        final_crc_type=crctype,
        model_crc=model_crc_from_header(header),
        header_crc=header_crc,
        header_tail_crc=header_tail_crc,
        header_xor_key=None,
        file_crc=file_crc,
        footer=footer,
    )


def patch_tft_header(header: bytearray, profile: HmiSafeProfile | None = None) -> tuple[int, int, int, int | None]:
    if profile is None:
        profile = HmiSafeProfile()
    if len(header) != TFT_HEADER_LEN:
        raise ValueError(f"header must be {TFT_HEADER_LEN} bytes")
    mode = header[0x15]
    require_verified_finalizer_mode(mode)

    header[0x58:0xC8] = b"\xFF" * 0x70
    header[0x114:0x190] = b"\xFF" * 0x7C

    if profile.copy_profile_header is not None:
        ref = profile.copy_profile_header
        header[0x01] = ref[0x01]
        header[0x02] = ref[0x02]
        header[0x17] = ref[0x17]
    else:
        header[0x01] = profile.safe_01 & 0xFF
        header[0x02] = profile.safe_02 & 0xFF
        header[0x17] = profile.safe_17 & 0xFF

    header[0x03] = 0x54
    header[0x32] = 0x21

    header_crc = crc_type10_update(CRC_INIT, header[:0xC4])
    struct.pack_into("<I", header, 0xC4, header_crc)

    model_crc = model_crc_from_header(header)
    header_xor_key = xor_appfree10_header_region(header, model_crc)

    header_tail_crc = crc_type10_update(CRC_INIT, header[0xC8:0x18C])
    struct.pack_into("<I", header, 0x18C, header_tail_crc)
    return header_crc, header_tail_crc, model_crc, header_xor_key


def finalize_tft(data: bytes | bytearray, profile: HmiSafeProfile | None = None) -> tuple[bytes, FinalizeInfo]:
    if len(data) < TFT_HEADER_LEN + 4:
        raise ValueError(f"TFT is too small: {len(data)} bytes")

    out = bytearray(data)
    header = bytearray(out[:TFT_HEADER_LEN])
    header_crc, header_tail_crc, model_crc, header_xor_key = patch_tft_header(header, profile)
    out[:TFT_HEADER_LEN] = header

    mode = header[0x15]
    crctype = choose_final_crc_type(mode)
    file_crc = acserver_get_file_crc(out, CRC_INIT, 0, len(out) - 4, crctype)
    footer = _u32(file_crc ^ (header[0x2E] ^ header[0x3C] ^ header[0x03]))
    struct.pack_into("<I", out, len(out) - 4, footer)

    return bytes(out), FinalizeInfo(
        size=len(out),
        mode=mode,
        final_crc_type=crctype,
        model_crc=model_crc,
        header_crc=header_crc,
        header_tail_crc=header_tail_crc,
        header_xor_key=header_xor_key,
        file_crc=file_crc,
        footer=footer,
    )


def verify_final_tft(data: bytes) -> dict[str, Any]:
    if len(data) < TFT_HEADER_LEN + 4:
        raise ValueError(f"TFT is too small: {len(data)} bytes")
    header = data[:TFT_HEADER_LEN]
    mode = header[0x15]
    crctype = choose_final_crc_type(mode)
    header_crc_expected = crc_type10_update(CRC_INIT, header[:0xC4])
    header_crc_stored = struct.unpack_from("<I", header, 0xC4)[0]
    header_tail_crc_expected = crc_type10_update(CRC_INIT, header[0xC8:0x18C])
    header_tail_crc_stored = struct.unpack_from("<I", header, 0x18C)[0]
    file_crc = acserver_get_file_crc(data, CRC_INIT, 0, len(data) - 4, crctype)
    footer_expected = _u32(file_crc ^ (header[0x2E] ^ header[0x3C] ^ header[0x03]))
    footer_stored = struct.unpack_from("<I", data, len(data) - 4)[0]
    return {
        "size": len(data),
        "mode": mode,
        "crc_type": crctype,
        "model_crc": model_crc_from_header(header),
        "finalizer_supported": hmisafe_finalizer_support(mode)["supported"],
        "finalizer_status": hmisafe_finalizer_support(mode)["status"],
        "finalizer_note": hmisafe_finalizer_support(mode)["note"],
        "header_crc_stored": header_crc_stored,
        "header_crc_expected": header_crc_expected,
        "header_crc_ok": header_crc_stored == header_crc_expected,
        "header_tail_crc_stored": header_tail_crc_stored,
        "header_tail_crc_expected": header_tail_crc_expected,
        "header_tail_crc_ok": header_tail_crc_stored == header_tail_crc_expected,
        "file_crc": file_crc,
        "footer_stored": footer_stored,
        "footer_expected": footer_expected,
        "footer_ok": footer_stored == footer_expected,
    }


def diff_bytes(a: bytes, b: bytes) -> dict[str, Any]:
    diff_count = 0
    first_diff: dict[str, Any] | None = None
    max_len = max(len(a), len(b))
    for off in range(max_len):
        av = a[off] if off < len(a) else None
        bv = b[off] if off < len(b) else None
        if av == bv:
            continue
        diff_count += 1
        if first_diff is None:
            first_diff = {
                "offset": off,
                "ours": None if av is None else f"{av:02x}",
                "expected": None if bv is None else f"{bv:02x}",
                "meaning": explain_offset(off, max_len),
            }
    return {
        "ours_size": len(a),
        "expected_size": len(b),
        "byte_identical": len(a) == len(b) and diff_count == 0,
        "diff_count": diff_count,
        "first_diff": first_diff,
    }


def explain_offset(off: int, size: int) -> str:
    if off >= size - 4:
        return "EOF-4 final little-endian check value"
    if off < TFT_HEADER_LEN:
        if off == 0x01:
            return "header safe byte from achmi global DAT_1000d402"
        if off == 0x02:
            return "header safe byte from achmi global DAT_1000d401"
        if off == 0x03:
            return "TFT marker patched to 0x54"
        if off == 0x17:
            return "header safe byte from achmi global DAT_1000d400"
        if off == 0x32:
            return "header marker patched to 0x21"
        if 0x58 <= off < 0xC4:
            return "native clears header[0x58:0xc4] to 0xff before header CRC"
        if 0xC4 <= off < 0xC8:
            return "type-10 CRC of header[0:0xc4]"
        if 0xC8 <= off < 0x114:
            return "native Appfree10 XOR-encoded header subrange"
        if 0x114 <= off < 0x18C:
            return "native clears header[0x114:0x18c] to 0xff before second header CRC"
        if 0x18C <= off < 0x190:
            return "type-10 CRC of header[0xc8:0x18c]"
        return "managed TFT header field"
    return "TFT body/resource/data area; HmiSafe finalizer should not change this"


def finalize_tft_file(input_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    in_path = Path(input_path)
    out_path = Path(output_path)
    out_data, info = finalize_tft(in_path.read_bytes())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(out_data)
    return {
        "input": str(in_path),
        "output": str(out_path),
        **info.to_dict(),
    }


def verify_final_tft_file(path: str | Path) -> dict[str, Any]:
    final_path = Path(path)
    return {
        "path": str(final_path),
        **verify_final_tft(final_path.read_bytes()),
    }
