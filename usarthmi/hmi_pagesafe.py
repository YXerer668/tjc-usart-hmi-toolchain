from __future__ import annotations

from dataclasses import dataclass
import struct
from typing import Any

from .tft_hmisafe import CRC_INIT, acserver_get_file_crc, crc_type10_update


PAGE_HEADER_LEN = 0x38
PAGE_CRC_OFFSET = 0x00
PAGE_DATASIZE_OFFSET = 0x04
PAGE_DATAINFO_ADDR_OFFSET = 0x08
PAGE_DATAINFO_QTY_OFFSET = 0x0C
PAGELOCK_OFFSET = 0x14
HMIFFID_OFFSET = 0x15
FILEVER_OFFSET = 0x16
PAGELEI_OFFSET = 0x17
UPVER0_OFFSET = 0x28
UPVER1_OFFSET = 0x29
UPVER2_OFFSET = 0x2A


@dataclass(frozen=True, slots=True)
class PageSafeStatus:
    size: int
    stored_crc: int
    computed_crc: int
    size_field: int
    datainformation_addr: int
    datainformation_qyt: int
    pagelock: int
    hmiffid: int
    filever: int
    upver0: int
    upver1: int
    upver2: int

    @property
    def safe_ok(self) -> bool:
        return self.stored_crc == self.computed_crc and self.size_field == self.size and self.hmiffid == 0x55

    def to_dict(self) -> dict[str, Any]:
        return {
            "size": self.size,
            "stored_crc": self.stored_crc,
            "stored_crc_hex": f"0x{self.stored_crc:08X}",
            "computed_crc": self.computed_crc,
            "computed_crc_hex": f"0x{self.computed_crc:08X}",
            "size_field": self.size_field,
            "datainformation_addr": self.datainformation_addr,
            "datainformation_qyt": self.datainformation_qyt,
            "pagelock": self.pagelock,
            "hmiffid": self.hmiffid,
            "filever": self.filever,
            "upver0": self.upver0,
            "upver1": self.upver1,
            "upver2": self.upver2,
            "safe_ok": self.safe_ok,
        }


def compute_page_safe_crc(data: bytes | bytearray | memoryview) -> int:
    page = bytes(data)
    if len(page) < PAGE_HEADER_LEN:
        raise ValueError(f"page is too small: {len(page)} bytes")

    crc = acserver_get_file_crc(page, CRC_INIT, 4, len(page) - 4, 10)
    crc = crc_type10_update(crc, page[PAGE_DATASIZE_OFFSET : PAGE_DATASIZE_OFFSET + 4])
    crc = crc_type10_update(crc, page[PAGE_DATAINFO_QTY_OFFSET : PAGE_DATAINFO_QTY_OFFSET + 4])
    crc = crc_type10_update(crc, page[PAGELOCK_OFFSET : PAGELOCK_OFFSET + 1])
    crc = crc_type10_update(crc, page[HMIFFID_OFFSET : HMIFFID_OFFSET + 1])
    return crc


def inspect_page_safe_status(data: bytes | bytearray | memoryview) -> PageSafeStatus:
    page = bytes(data)
    if len(page) < PAGE_HEADER_LEN:
        raise ValueError(f"page is too small: {len(page)} bytes")

    return PageSafeStatus(
        size=len(page),
        stored_crc=struct.unpack_from("<I", page, PAGE_CRC_OFFSET)[0],
        computed_crc=compute_page_safe_crc(page),
        size_field=struct.unpack_from("<I", page, PAGE_DATASIZE_OFFSET)[0],
        datainformation_addr=struct.unpack_from("<I", page, PAGE_DATAINFO_ADDR_OFFSET)[0],
        datainformation_qyt=struct.unpack_from("<I", page, PAGE_DATAINFO_QTY_OFFSET)[0],
        pagelock=page[PAGELOCK_OFFSET],
        hmiffid=page[HMIFFID_OFFSET],
        filever=page[FILEVER_OFFSET],
        upver0=page[UPVER0_OFFSET],
        upver1=page[UPVER1_OFFSET],
        upver2=page[UPVER2_OFFSET],
    )


def refresh_page_safe_header(
    data: bytes | bytearray,
    *,
    datasize: int | None = None,
    datainformation_qyt: int | None = None,
) -> bytes:
    page = bytearray(data)
    if len(page) < PAGE_HEADER_LEN:
        raise ValueError(f"page is too small: {len(page)} bytes")

    if datasize is not None:
        struct.pack_into("<I", page, PAGE_DATASIZE_OFFSET, int(datasize))
    if datainformation_qyt is not None:
        struct.pack_into("<I", page, PAGE_DATAINFO_QTY_OFFSET, int(datainformation_qyt))

    crc = compute_page_safe_crc(page)
    struct.pack_into("<I", page, PAGE_CRC_OFFSET, crc)
    return bytes(page)
