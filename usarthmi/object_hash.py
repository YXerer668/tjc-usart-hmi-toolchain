from __future__ import annotations

OBJECT_NAME_HASH_WIDTH = 14


def nextion_crc32(data: bytes, *, salt: int = 0xFFFFFFFF, xor_out: int = 0) -> int:
    """Return the CRC32 variant used by Nextion/TJC TFT metadata."""

    words = list(data) + [0]
    words[0] = (words[0] ^ salt) & 0xFFFFFFFF
    poly = 0x104C11DB7
    reg = 0

    for word in words:
        word &= 0xFFFFFFFF
        for _ in range(32):
            reg <<= 1
            if word >= 0x80000000:
                reg += 1
            word = (word << 1) & 0xFFFFFFFF
            if reg >= 0x100000000:
                reg ^= poly

    return (reg & 0xFFFFFFFF) ^ xor_out


def object_name_hash(name: str, *, width: int = OBJECT_NAME_HASH_WIDTH) -> int:
    """Hash a page/object name for compiled TFT hash/index lists.

    The editor hashes ASCII names padded with NUL bytes to a 14-byte field.
    This has been verified against local TJC 1.67.6 fixtures and public
    Nextion 1.65.1 TFT/HMI pairs.
    """

    encoded = name.encode("ascii")
    if len(encoded) > width:
        raise ValueError(f"Object name {name!r} is {len(encoded)} bytes; maximum supported is {width}")
    return nextion_crc32(encoded.ljust(width, b"\x00"))
