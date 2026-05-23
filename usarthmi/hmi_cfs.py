from __future__ import annotations

from dataclasses import dataclass
import struct
from typing import Any


NATIVE_CFS_PRIMARY_TABLE_OFFSET = 0x80000
NATIVE_CFS_SECONDARY_TABLE_OFFSET = 0x380000
NATIVE_CFS_RECORD_SIZE = 0x1C
NATIVE_CFS_MAX_REASONABLE_COUNT = 100000


@dataclass(frozen=True, slots=True)
class NativeCfsRecord:
    index: int
    name: str
    data_offset: int
    length: int
    flags: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "name": self.name,
            "data_offset": self.data_offset,
            "data_offset_hex": f"0x{self.data_offset:08X}",
            "length": self.length,
            "flags": self.flags,
            "flags_hex": f"0x{self.flags:08X}",
        }


@dataclass(frozen=True, slots=True)
class NativeCfsTable:
    offset: int
    count: int
    records: list[NativeCfsRecord]
    trailing_crc: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "offset": self.offset,
            "offset_hex": f"0x{self.offset:08X}",
            "count": self.count,
            "trailing_crc": self.trailing_crc,
            "trailing_crc_hex": None if self.trailing_crc is None else f"0x{self.trailing_crc:08X}",
            "records": [record.to_dict() for record in self.records],
        }


def parse_native_cfs_table(raw: bytes, offset: int = NATIVE_CFS_PRIMARY_TABLE_OFFSET) -> NativeCfsTable:
    if offset + 4 > len(raw):
        raise ValueError(f"native CFS table offset outside file: 0x{offset:X}")
    count = struct.unpack_from("<I", raw, offset)[0]
    if count == 0xFFFFFFFF:
        return NativeCfsTable(offset=offset, count=count, records=[], trailing_crc=None)
    if count > NATIVE_CFS_MAX_REASONABLE_COUNT:
        raise ValueError(f"native CFS count looks unreasonable at 0x{offset:X}: {count}")

    records: list[NativeCfsRecord] = []
    cursor = offset + 4
    for index in range(count):
        end = cursor + NATIVE_CFS_RECORD_SIZE
        if end > len(raw):
            raise ValueError(f"native CFS table truncated at record {index} offset 0x{cursor:X}")
        name_bytes = raw[cursor : cursor + 16]
        data_offset, length, flags = struct.unpack_from("<III", raw, cursor + 16)
        name = name_bytes.split(b"\x00", 1)[0].decode("ascii", errors="ignore")
        records.append(
            NativeCfsRecord(
                index=index,
                name=name,
                data_offset=data_offset,
                length=length,
                flags=flags,
            )
        )
        cursor = end

    trailing_crc = None
    if cursor + 4 <= len(raw):
        trailing_crc = struct.unpack_from("<I", raw, cursor)[0]
    return NativeCfsTable(offset=offset, count=count, records=records, trailing_crc=trailing_crc)


def find_native_cfs_record(table: NativeCfsTable, name: str) -> NativeCfsRecord | None:
    for record in table.records:
        if record.name == name:
            return record
    return None
