from __future__ import annotations

import struct
from typing import Any

from .tft_hmisafe import (
    appfree10_header_xor_key,
    finalize_tft,
    model_crc_from_header,
    require_verified_finalizer_mode,
    verify_final_tft,
)

TFT_HEADER_LEN = 400
PRE_HMISAFE_EOF4 = 0x12345678

HEADER1_FILE_SIZE_OFFSET = 0x3C
HEADER1_CRC_OFFSET = 0xC4
HEADER2_START = 0xC8
HEADER2_CRC_OFFSET = HEADER2_START + 0xC4

LEGACY_BUILDER_HEADER_FIELD_OFFSETS = {
    "static_usercode_address": 0x00,
    "app_attributes_data_address": 0x04,
    "usercode_address": 0x0C,
    "pictures_address": 0x18,
    "gmovs_address": 0x1C,
    "image_button_prefix_count": 0x34,
    "videos_count": 0x38,
    "compiled_object_count": 0x3A,
}

OFFICIAL_APPINF1_FIELD_OFFSETS = {
    "staticstrBeg": (0x00, 4),
    "AppAllvasAddr": (0x04, 4),
    "AppAllvasQty": (0x08, 2),
    "attdataaddr": (0x0C, 4),
    "resourcesfileddr": (0x10, 4),
    "strdataaddr": (0x14, 4),
    "pageadd": (0x18, 4),
    "objxinxiadd": (0x1C, 4),
    "picxinxiadd": (0x20, 4),
    "gmovxinxiadd": (0x24, 4),
    "videoxinxiadd": (0x28, 4),
    "wavxinxiadd": (0x2C, 4),
    "zimoxinxiadd": (0x30, 4),
    "MainCodeHex": (0x34, 4),
    "pageqyt": (0x38, 2),
    "objqyt": (0x3A, 2),
    "picqyt": (0x3C, 2),
    "gmovqyt": (0x3E, 2),
    "videoqyt": (0x40, 2),
    "wavqyt": (0x42, 2),
    "zimoqyt": (0x44, 2),
    "res1": (0x46, 2),
    "encode": (0x48, 1),
}

# These bytes are observed as managed-side zero in the true pre-HmiSafe sample
# and are overwritten later by HmiSafeWriteTFTFileSafe.
NATIVE_OVERWRITTEN_SINGLE_BYTES = (0x01, 0x02, 0x03, 0x17, 0x32)


def build_candidate_pre_hmisafe_tft(
    payload: bytes | bytearray,
    *,
    object_start: int,
    hash_relative: int,
    page_count: int,
    object_count: int,
    attr_relative: int,
    user_relative: int,
    picture_relative: int,
    prefix_delta: int = 0,
    gmovs_relative_offset: int = 0x10,
    seed_final_appinf1: dict[str, int] | None = None,
) -> bytes:
    """Build a builder-side pre-HmiSafe candidate.

    This intentionally stops before the verified native finalizer:

    raw/managed builder payload
      -> candidate pre-HmiSafe TFT
      -> finalize_tft(candidate) for final-byte checks

    The builder currently does not prove every managed header field yet. This
    helper writes the known managed-side appinf1 fields plainly, preserves the
    seed's resource-side appinf1 values where the builder has not yet rebuilt
    them, zeroes the finalizer CRC/scratch zones, and restores EOF-4 to the
    official placeholder.
    """

    if len(payload) < TFT_HEADER_LEN + 4:
        raise ValueError(f"TFT is too small for pre-HmiSafe candidate: {len(payload)} bytes")

    raw = bytearray(payload)
    raw[HEADER1_FILE_SIZE_OFFSET : HEADER1_FILE_SIZE_OFFSET + 4] = len(raw).to_bytes(4, "little")
    raw[HEADER1_CRC_OFFSET : HEADER1_CRC_OFFSET + 4] = b"\x00" * 4
    raw[HEADER2_START:HEADER2_CRC_OFFSET + 4] = b"\x00" * (HEADER2_CRC_OFFSET + 4 - HEADER2_START)
    raw[0x58:HEADER2_START] = b"\x00" * (HEADER2_START - 0x58)
    for off in NATIVE_OVERWRITTEN_SINGLE_BYTES:
        raw[off] = 0

    seed_fields = seed_final_appinf1 or {}
    pageadd = object_start + picture_relative
    objxinxiadd = pageadd + page_count * 16

    _write_u32(raw, HEADER2_START + OFFICIAL_APPINF1_FIELD_OFFSETS["staticstrBeg"][0], attr_relative)
    _write_u32(raw, HEADER2_START + OFFICIAL_APPINF1_FIELD_OFFSETS["AppAllvasAddr"][0], attr_relative)
    _write_u16(
        raw,
        HEADER2_START + OFFICIAL_APPINF1_FIELD_OFFSETS["AppAllvasQty"][0],
        int(seed_fields.get("AppAllvasQty", 3)),
    )
    _write_u32(raw, HEADER2_START + OFFICIAL_APPINF1_FIELD_OFFSETS["attdataaddr"][0], user_relative)
    _write_u32(
        raw,
        HEADER2_START + OFFICIAL_APPINF1_FIELD_OFFSETS["resourcesfileddr"][0],
        int(seed_fields.get("resourcesfileddr", 0x20000)),
    )
    _write_u32(raw, HEADER2_START + OFFICIAL_APPINF1_FIELD_OFFSETS["strdataaddr"][0], object_start)
    _write_u32(raw, HEADER2_START + OFFICIAL_APPINF1_FIELD_OFFSETS["pageadd"][0], pageadd)
    _write_u32(raw, HEADER2_START + OFFICIAL_APPINF1_FIELD_OFFSETS["objxinxiadd"][0], objxinxiadd)

    for name in (
        "picxinxiadd",
        "gmovxinxiadd",
        "videoxinxiadd",
        "wavxinxiadd",
        "zimoxinxiadd",
    ):
        _write_u32(
            raw,
            HEADER2_START + OFFICIAL_APPINF1_FIELD_OFFSETS[name][0],
            int(seed_fields.get(name, 0)),
        )

    _write_u32(
        raw,
        HEADER2_START + OFFICIAL_APPINF1_FIELD_OFFSETS["MainCodeHex"][0],
        int(seed_fields.get("MainCodeHex", 0)) + int(prefix_delta),
    )
    _write_u16(raw, HEADER2_START + OFFICIAL_APPINF1_FIELD_OFFSETS["pageqyt"][0], page_count)
    _write_u16(raw, HEADER2_START + OFFICIAL_APPINF1_FIELD_OFFSETS["objqyt"][0], object_count)
    for name in ("picqyt", "gmovqyt", "videoqyt", "wavqyt", "zimoqyt", "res1"):
        _write_u16(
            raw,
            HEADER2_START + OFFICIAL_APPINF1_FIELD_OFFSETS[name][0],
            int(seed_fields.get(name, 0)),
        )
    raw[HEADER2_START + OFFICIAL_APPINF1_FIELD_OFFSETS["encode"][0]] = int(seed_fields.get("encode", 24)) & 0xFF

    struct.pack_into("<I", raw, len(raw) - 4, PRE_HMISAFE_EOF4)
    return bytes(raw)


def decode_known_pre_hmisafe_fields(data: bytes) -> dict[str, int]:
    if len(data) < TFT_HEADER_LEN + 4:
        raise ValueError(f"TFT is too small: {len(data)} bytes")
    out = {
        "file_size": struct.unpack_from("<I", data, HEADER1_FILE_SIZE_OFFSET)[0],
        "header1_crc": struct.unpack_from("<I", data, HEADER1_CRC_OFFSET)[0],
        "header2_crc": struct.unpack_from("<I", data, HEADER2_CRC_OFFSET)[0],
        "eof4": struct.unpack_from("<I", data, len(data) - 4)[0],
    }
    for name, (relative_offset, size) in OFFICIAL_APPINF1_FIELD_OFFSETS.items():
        out[name] = int.from_bytes(
            data[HEADER2_START + relative_offset : HEADER2_START + relative_offset + size],
            "little",
        )
    return out


def decode_legacy_candidate_header_fields(data: bytes) -> dict[str, int]:
    if len(data) < TFT_HEADER_LEN + 4:
        raise ValueError(f"TFT is too small: {len(data)} bytes")
    return {
        "static_usercode_address": struct.unpack_from(
            "<I", data, HEADER2_START + LEGACY_BUILDER_HEADER_FIELD_OFFSETS["static_usercode_address"]
        )[0],
        "app_attributes_data_address": struct.unpack_from(
            "<I", data, HEADER2_START + LEGACY_BUILDER_HEADER_FIELD_OFFSETS["app_attributes_data_address"]
        )[0],
        "usercode_address": struct.unpack_from(
            "<I", data, HEADER2_START + LEGACY_BUILDER_HEADER_FIELD_OFFSETS["usercode_address"]
        )[0],
        "pictures_address": struct.unpack_from(
            "<I", data, HEADER2_START + LEGACY_BUILDER_HEADER_FIELD_OFFSETS["pictures_address"]
        )[0],
        "gmovs_address": struct.unpack_from(
            "<I", data, HEADER2_START + LEGACY_BUILDER_HEADER_FIELD_OFFSETS["gmovs_address"]
        )[0],
        "image_button_prefix_count": struct.unpack_from(
            "<H", data, HEADER2_START + LEGACY_BUILDER_HEADER_FIELD_OFFSETS["image_button_prefix_count"]
        )[0],
        "videos_count": struct.unpack_from(
            "<H", data, HEADER2_START + LEGACY_BUILDER_HEADER_FIELD_OFFSETS["videos_count"]
        )[0],
        "compiled_object_count": struct.unpack_from(
            "<H", data, HEADER2_START + LEGACY_BUILDER_HEADER_FIELD_OFFSETS["compiled_object_count"]
        )[0],
    }


def decode_final_appinf1_fields(final_tft: bytes) -> dict[str, int]:
    if len(final_tft) < TFT_HEADER_LEN + 4:
        raise ValueError(f"TFT is too small: {len(final_tft)} bytes")
    header = final_tft[:TFT_HEADER_LEN]
    key = struct.pack("<I", appfree10_header_xor_key(model_crc_from_header(header)))
    decoded = bytearray(0x4C)
    for index in range(0x4C):
        decoded[index] = final_tft[HEADER2_START + index] ^ key[index & 3]
    out = {}
    for name, (relative_offset, size) in OFFICIAL_APPINF1_FIELD_OFFSETS.items():
        out[name] = int.from_bytes(decoded[relative_offset : relative_offset + size], "little")
    return out


def compare_pre_hmisafe(candidate: bytes, official: bytes, *, max_first_diffs: int = 64) -> dict[str, Any]:
    byte_equal = candidate == official
    diff_count = 0
    first_diffs: list[dict[str, Any]] = []
    for off, (before, after) in enumerate(zip(official, candidate)):
        if before == after:
            continue
        diff_count += 1
        if len(first_diffs) < max_first_diffs:
            first_diffs.append(
                {
                    "offset": off,
                    "offset_hex": f"0x{off:X}",
                    "official": before,
                    "official_hex": f"0x{before:02X}",
                    "candidate": after,
                    "candidate_hex": f"0x{after:02X}",
                }
            )
    diff_count += abs(len(candidate) - len(official))

    official_fields = decode_known_pre_hmisafe_fields(official)
    candidate_fields = decode_known_pre_hmisafe_fields(candidate)
    field_diffs = []
    for name, official_value in official_fields.items():
        candidate_value = candidate_fields[name]
        if official_value == candidate_value:
            continue
        field_diffs.append(
            {
                "name": name,
                "official": official_value,
                "official_hex": f"0x{official_value:X}",
                "candidate": candidate_value,
                "candidate_hex": f"0x{candidate_value:X}",
            }
        )

    return {
        "byte_identical": byte_equal,
        "size": {
            "official": len(official),
            "candidate": len(candidate),
        },
        "diff_count": diff_count,
        "first_diffs": first_diffs,
        "first_diff_ranges": _diff_ranges(candidate, official),
        "sections": {
            "header_prefix": _region_summary(candidate, official, 0x00, 0x58),
            "header_crc_scratch": _region_summary(candidate, official, 0x58, 0xC8),
            "header2_managed": _region_summary(candidate, official, 0xC8, 0x190),
            "body": _region_summary(candidate, official, 0x190, min(len(candidate), len(official)) - 4),
            "eof4": _region_summary(candidate, official, min(len(candidate), len(official)) - 4, min(len(candidate), len(official))),
        },
        "known_field_diffs": field_diffs,
        "official_fields": official_fields,
        "candidate_fields": candidate_fields,
    }


def finalize_candidate_pre_hmisafe(candidate: bytes) -> dict[str, Any]:
    final_bytes, info = finalize_tft(candidate)
    verify = verify_final_tft(final_bytes)
    return {
        "bytes": final_bytes,
        "info": info.to_dict(),
        "verify": verify,
    }


def derive_synthetic_pre_hmisafe_from_final(final_bytes: bytes) -> bytes:
    """Undo the verified mode-3 finalizer into a synthetic pre-HmiSafe file.

    This is a builder-facing comparison aid for cases where only an official
    final TFT is available. It is not a proof of the true original managed
    header bytes outside the reversible mode-3 path.
    """

    if len(final_bytes) < TFT_HEADER_LEN + 4:
        raise ValueError(f"TFT is too small: {len(final_bytes)} bytes")

    raw = bytearray(final_bytes)
    header = raw[:TFT_HEADER_LEN]
    require_verified_finalizer_mode(header[0x15])
    key = struct.pack("<I", appfree10_header_xor_key(model_crc_from_header(header)))
    for index in range(0x4C):
        raw[HEADER2_START + index] ^= key[index & 3]

    for off in NATIVE_OVERWRITTEN_SINGLE_BYTES:
        raw[off] = 0
    raw[0x58:HEADER2_START] = b"\x00" * (HEADER2_START - 0x58)
    raw[0x114:0x190] = b"\x00" * (0x190 - 0x114)
    raw[HEADER1_CRC_OFFSET : HEADER1_CRC_OFFSET + 4] = b"\x00" * 4
    raw[HEADER2_CRC_OFFSET : HEADER2_CRC_OFFSET + 4] = b"\x00" * 4
    struct.pack_into("<I", raw, len(raw) - 4, PRE_HMISAFE_EOF4)
    return bytes(raw)


def _region_summary(candidate: bytes, official: bytes, start: int, end: int) -> dict[str, Any]:
    if end <= start:
        return {"start": start, "end_exclusive": end, "diff_count": 0}
    diff_count = 0
    for off in range(start, min(end, len(candidate), len(official))):
        if candidate[off] != official[off]:
            diff_count += 1
    return {
        "start": start,
        "start_hex": f"0x{start:X}",
        "end_exclusive": end,
        "end_exclusive_hex": f"0x{end:X}",
        "diff_count": diff_count,
    }


def _diff_ranges(candidate: bytes, official: bytes) -> list[dict[str, int]]:
    limit = min(len(candidate), len(official))
    ranges: list[dict[str, int]] = []
    start: int | None = None
    for off in range(limit):
        different = candidate[off] != official[off]
        if different and start is None:
            start = off
        elif not different and start is not None:
            ranges.append({"start": start, "end_exclusive": off})
            start = None
    if start is not None:
        ranges.append({"start": start, "end_exclusive": limit})
    if len(candidate) != len(official):
        ranges.append({"start": limit, "end_exclusive": max(len(candidate), len(official))})
    return ranges


def _write_u16(raw: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<H", raw, offset, value & 0xFFFF)


def _write_u32(raw: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<I", raw, offset, value & 0xFFFFFFFF)
