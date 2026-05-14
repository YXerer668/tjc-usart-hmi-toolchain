from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .tft_checksum import _crc32_like, update_tft_checksum
from .tft_patch import (
    HEADER1_CRC_OFFSET,
    HEADER1_FILE_SIZE_OFFSET,
    HEADER2_CRC_OFFSET,
    HEADER2_START,
    _header2_xor_key,
    _write_header2_field,
)
from .tft_toolchain import TftToolchainError, inspect_tft


GmovSource = str | Path | tuple[int, str | Path]
GMOV_MAGIC = b"GMOV"
GMOV_HEADER_SIZE = 0x4C
GMOV_PAYLOAD_OFFSET_FIELD = 0x08
TFT_RESOURCE_SIZE_OFFSET = 0x40
TFT_RESOURCE_CRC_OFFSET = 0x44
HEADER2_OBJECTS_ADDRESS_OFFSET = 0x14
HEADER2_AUDIOS_ADDRESS_OFFSET = 0x24
HEADER2_FONTS_ADDRESS_OFFSET = 0x28
HEADER2_MAINCODE_ADDRESS_OFFSET = 0x2C
HEADER2_GMOV_COUNT_OFFSET = 0x3E
RESOURCE_DIRECTORY_GMOV_START_OFFSET = 0x6C
RESOURCE_DIRECTORY_GMOV_SIZE_OFFSET = 0x70
RESOURCE_DIRECTORY_GMOV_END_OFFSET = 0x78
RESOURCE_DIRECTORY_MAINCODE_OFFSET = 0x84
TFT_RESOURCE_ALIGNMENT = 0x20000


@dataclass(slots=True)
class PackedGmovResource:
    resource_id: int
    table_index: int
    source: str
    original_size: int
    header_size: int
    header_offset_in_table: int
    original_header_offset_field: int
    patched_header_offset_field: int
    payload_offset_in_block: int
    payload_size: int
    frame_count: int
    width: int
    height: int

    @property
    def gmov_id(self) -> int:
        return self.resource_id

    @property
    def payload_offset(self) -> int:
        return self.payload_offset_in_block

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "gmov_id": self.resource_id,
            "table_index": self.table_index,
            "source": self.source,
            "original_size": self.original_size,
            "header_size": self.header_size,
            "header_offset_in_table": self.header_offset_in_table,
            "header_offset_in_table_hex": f"0x{self.header_offset_in_table:X}",
            "original_header_offset_field": self.original_header_offset_field,
            "original_header_offset_field_hex": f"0x{self.original_header_offset_field:X}",
            "patched_header_offset_field": self.patched_header_offset_field,
            "patched_header_offset_field_hex": f"0x{self.patched_header_offset_field:X}",
            "payload_offset_in_block": self.payload_offset_in_block,
            "payload_offset_in_block_hex": f"0x{self.payload_offset_in_block:X}",
            "payload_offset": self.payload_offset_in_block,
            "payload_offset_hex": f"0x{self.payload_offset_in_block:X}",
            "payload_size": self.payload_size,
            "payload_end_in_block": self.payload_offset_in_block + self.payload_size,
            "payload_end_in_block_hex": f"0x{self.payload_offset_in_block + self.payload_size:X}",
            "frame_count": self.frame_count,
            "width": self.width,
            "height": self.height,
        }


@dataclass(slots=True)
class GmovPackResult:
    header_size: int
    header_table_size: int
    payload_size: int
    total_size: int
    resources: list[PackedGmovResource]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": "tjc_gmov_resource_pack",
            "header_size": self.header_size,
            "header_table_size": self.header_table_size,
            "header_table_size_hex": f"0x{self.header_table_size:X}",
            "payload_size": self.payload_size,
            "total_size": self.total_size,
            "resources": [resource.to_dict() for resource in self.resources],
            "warnings": [
                "GMOV packing is fixture-proven for USART HMI 800x480 TJC8048X543_011 output.",
                "The raw per-file GMOV header is preserved except header[8:12], which becomes the payload offset inside the packed block.",
                "Header2 labels in TFTTool can be misleading for media blocks; verified GMOV data may sit between audios_address and fonts_address.",
            ],
        }


@dataclass(slots=True)
class TftGmovPackResult:
    baseline_tft: str
    out_tft: str
    resource_address: int
    old_resource_size: int
    new_resource_size: int
    old_object_start: int
    new_object_start: int
    gmov_resource_address: int
    gmov_resource_size: int
    resource_count: int
    pack: GmovPackResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": "experimental_tft_gmov_resource_pack",
            "baseline_tft": self.baseline_tft,
            "out_tft": self.out_tft,
            "resource_address": self.resource_address,
            "resource_address_hex": f"0x{self.resource_address:X}",
            "old_resource_size": self.old_resource_size,
            "old_resource_size_hex": f"0x{self.old_resource_size:X}",
            "new_resource_size": self.new_resource_size,
            "new_resource_size_hex": f"0x{self.new_resource_size:X}",
            "old_object_start": self.old_object_start,
            "old_object_start_hex": f"0x{self.old_object_start:X}",
            "new_object_start": self.new_object_start,
            "new_object_start_hex": f"0x{self.new_object_start:X}",
            "gmov_resource_address": self.gmov_resource_address,
            "gmov_resource_address_hex": f"0x{self.gmov_resource_address:X}",
            "gmov_resource_size": self.gmov_resource_size,
            "resource_count": self.resource_count,
            "pack": self.pack.to_dict(),
            "warnings": [
                "Experimental V1 packs internal GMOV resources into the resource directory media slot.",
                "This is byte-proven against the official GMOV block, but live playback still needs panel validation for generated scene TFTs.",
            ],
        }


def pack_gmov_resources(sources: list[GmovSource]) -> tuple[GmovPackResult, bytes]:
    """Pack raw `.gmov` HMI resources into the TFT GMOV block layout.

    Official USART HMI output for the current TJC8048X543_011 fixture stores
    multiple GMOV resources as a compact block:

    1. all 0x4C-byte raw GMOV headers first;
    2. header[8:12] patched from 0x4C to the resource payload offset inside
       the packed block;
    3. each raw payload (`file[0x4C:]`) appended in the same order.

    The function intentionally validates the observed V1 shape instead of
    guessing alternate GMOV variants. If a future fixture uses another header
    length, it should fail loudly and become a new reverse-engineering case.
    """

    entries = _normalize_sources(sources)
    if not entries:
        raise TftToolchainError("No GMOV resources were provided")

    headers: list[bytes] = []
    payloads: list[bytes] = []
    resources: list[PackedGmovResource] = []
    header_table_size = len(entries) * GMOV_HEADER_SIZE
    payload_offset = header_table_size

    for table_index, (resource_id, path) in enumerate(entries):
        raw = path.read_bytes()
        _validate_gmov(path, raw)

        header = bytearray(raw[:GMOV_HEADER_SIZE])
        payload = raw[GMOV_HEADER_SIZE:]
        original_offset = int.from_bytes(
            header[GMOV_PAYLOAD_OFFSET_FIELD : GMOV_PAYLOAD_OFFSET_FIELD + 4],
            "little",
        )
        # Official TFT output stores all GMOV headers first, then all payloads.
        # Raw .gmov files point at payload offset 0x4C; in the packed TFT block
        # that field must point at the payload position inside the shared block.
        header[GMOV_PAYLOAD_OFFSET_FIELD : GMOV_PAYLOAD_OFFSET_FIELD + 4] = payload_offset.to_bytes(4, "little")

        headers.append(bytes(header))
        payloads.append(payload)
        resources.append(
            PackedGmovResource(
                resource_id=resource_id,
                table_index=table_index,
                source=str(path),
                original_size=len(raw),
                header_size=GMOV_HEADER_SIZE,
                header_offset_in_table=table_index * GMOV_HEADER_SIZE,
                original_header_offset_field=original_offset,
                patched_header_offset_field=payload_offset,
                payload_offset_in_block=payload_offset,
                payload_size=len(payload),
                frame_count=int.from_bytes(raw[0x0C:0x10], "little"),
                width=int.from_bytes(raw[0x10:0x12], "little"),
                height=int.from_bytes(raw[0x12:0x14], "little"),
            )
        )
        payload_offset += len(payload)

    packed = b"".join(headers) + b"".join(payloads)
    result = GmovPackResult(
        header_size=GMOV_HEADER_SIZE,
        header_table_size=header_table_size,
        payload_size=sum(len(payload) for payload in payloads),
        total_size=len(packed),
        resources=resources,
    )
    return result, packed


def pack_gmov_resources_into_tft(
    baseline_tft: str | Path,
    sources: list[GmovSource],
    *,
    out_tft: str | Path,
) -> TftGmovPackResult:
    baseline_path = Path(baseline_tft).resolve()
    out_path = Path(out_tft).resolve()
    pack_result, packed_gmov = pack_gmov_resources(sources)

    inspection = inspect_tft(baseline_path)
    header1 = _section(inspection, "Header1")
    header2 = _section(inspection, "Header2")
    model = str(inspection.get("model") or "")
    model_series = _required_header_int(header1, "model_series")
    resource_address = _required_header_int(header1, "ressources_files_address")
    old_resource_size = _required_header_int(header1, "ressource_files_size")
    old_object_start = _required_header_int(header2, "unknown_objects_address")
    if old_object_start != resource_address + old_resource_size:
        raise TftToolchainError(
            "TFT resource region does not end at unknown_objects_address: "
            f"resource_end=0x{resource_address + old_resource_size:X}, objects=0x{old_object_start:X}"
        )

    raw = baseline_path.read_bytes()
    resource = raw[resource_address:old_object_start]
    gmov_start = _read_resource_directory_u32(resource, RESOURCE_DIRECTORY_GMOV_START_OFFSET)
    old_gmov_size = _read_resource_directory_u32(resource, RESOURCE_DIRECTORY_GMOV_SIZE_OFFSET)
    old_gmov_end = gmov_start + old_gmov_size
    if gmov_start > len(resource) or old_gmov_end > len(resource):
        raise TftToolchainError(
            f"GMOV resource directory points outside the resource region: start=0x{gmov_start:X}, size=0x{old_gmov_size:X}"
        )
    tail = resource[old_gmov_end:]
    if not _is_padding_tail(tail):
        raise TftToolchainError(
            "Current V1 can replace only an empty/padding GMOV resource tail; "
            f"non-padding data follows old GMOV end 0x{old_gmov_end:X}"
        )

    gmov_end = gmov_start + len(packed_gmov)
    new_resource_size = _align(gmov_end, TFT_RESOURCE_ALIGNMENT)
    fixed_resource = resource[:gmov_start] + packed_gmov + (b"\x00" * (new_resource_size - gmov_end))
    new_object_start = resource_address + new_resource_size
    object_delta = new_object_start - old_object_start

    payload = bytearray(raw[:resource_address] + fixed_resource + raw[old_object_start:])
    # The media block lives inside the fixed resource area, before compiled
    # object records. Moving its end shifts the object section, so Header2 and
    # the resource-directory pointers must be updated together.
    _write_resource_directory_u32(payload, resource_address, RESOURCE_DIRECTORY_GMOV_SIZE_OFFSET, len(packed_gmov))
    _write_resource_directory_u32(payload, resource_address, RESOURCE_DIRECTORY_GMOV_END_OFFSET, gmov_end)
    _write_resource_directory_u32(payload, resource_address, RESOURCE_DIRECTORY_MAINCODE_OFFSET, gmov_end)

    payload[HEADER1_FILE_SIZE_OFFSET : HEADER1_FILE_SIZE_OFFSET + 4] = len(payload).to_bytes(4, "little")
    payload[TFT_RESOURCE_SIZE_OFFSET : TFT_RESOURCE_SIZE_OFFSET + 4] = new_resource_size.to_bytes(4, "little")
    resource_crc = _crc32_like(list(_iter_words_le(payload[resource_address:new_object_start])))
    payload[TFT_RESOURCE_CRC_OFFSET : TFT_RESOURCE_CRC_OFFSET + 4] = resource_crc.to_bytes(4, "little")

    key = _header2_xor_key(model)
    _write_header2_field(payload, key, HEADER2_OBJECTS_ADDRESS_OFFSET, new_object_start.to_bytes(4, "little"))
    for field_name, field_offset in (
        ("pictures_address", 0x18),
        ("gmovs_address", 0x1C),
    ):
        value = _optional_header_int(header2, field_name)
        if value is not None and value >= old_object_start:
            _write_header2_field(payload, key, field_offset, (value + object_delta).to_bytes(4, "little"))
    _write_header2_field(
        payload,
        key,
        HEADER2_AUDIOS_ADDRESS_OFFSET,
        (resource_address + gmov_start).to_bytes(4, "little"),
    )
    _write_header2_field(
        payload,
        key,
        HEADER2_FONTS_ADDRESS_OFFSET,
        (resource_address + gmov_end).to_bytes(4, "little"),
    )
    _write_header2_field(
        payload,
        key,
        HEADER2_MAINCODE_ADDRESS_OFFSET,
        (resource_address + gmov_end).to_bytes(4, "little"),
    )
    _write_header2_field(payload, key, HEADER2_GMOV_COUNT_OFFSET, len(pack_result.resources).to_bytes(2, "little"))
    payload[HEADER2_CRC_OFFSET : HEADER2_CRC_OFFSET + 4] = _crc32_like(
        list(payload[HEADER2_START:HEADER2_CRC_OFFSET])
    ).to_bytes(4, "little")
    payload[HEADER1_CRC_OFFSET : HEADER1_CRC_OFFSET + 4] = _crc32_like(
        list(payload[:HEADER1_CRC_OFFSET])
    ).to_bytes(4, "little")
    payload[:] = update_tft_checksum(bytes(payload), series=model_series)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(payload)
    return TftGmovPackResult(
        baseline_tft=str(baseline_path),
        out_tft=str(out_path),
        resource_address=resource_address,
        old_resource_size=old_resource_size,
        new_resource_size=new_resource_size,
        old_object_start=old_object_start,
        new_object_start=new_object_start,
        gmov_resource_address=resource_address + gmov_start,
        gmov_resource_size=len(packed_gmov),
        resource_count=len(pack_result.resources),
        pack=pack_result,
    )


def _normalize_sources(sources: list[GmovSource]) -> list[tuple[int, Path]]:
    normalized: list[tuple[int, Path]] = []
    explicit_ids = False
    for index, source in enumerate(sources):
        if isinstance(source, tuple):
            explicit_ids = True
            resource_id, path = source
        else:
            resource_id, path = index, source
        normalized.append((int(resource_id), Path(path).resolve()))

    if explicit_ids:
        seen: set[int] = set()
        for resource_id, _path in normalized:
            if resource_id in seen:
                raise TftToolchainError(f"Duplicate GMOV resource id: {resource_id}")
            seen.add(resource_id)
        normalized.sort(key=lambda item: item[0])
        expected = list(range(len(normalized)))
        actual = [resource_id for resource_id, _path in normalized]
        if actual != expected:
            raise TftToolchainError(
                f"GMOV resource ids must be contiguous from 0 for V1, got {actual}"
            )
    return normalized


def _validate_gmov(path: Path, raw: bytes) -> None:
    if len(raw) < GMOV_HEADER_SIZE:
        raise TftToolchainError(f"GMOV resource is too small: {path}")
    if raw[:4] != GMOV_MAGIC:
        raise TftToolchainError(f"GMOV resource does not start with GMOV magic: {path}")
    header_size = int.from_bytes(raw[GMOV_PAYLOAD_OFFSET_FIELD : GMOV_PAYLOAD_OFFSET_FIELD + 4], "little")
    if header_size != GMOV_HEADER_SIZE:
        raise TftToolchainError(
            f"Unsupported GMOV header size in {path}: 0x{header_size:X}; expected 0x{GMOV_HEADER_SIZE:X}"
        )


def _section(inspection: dict[str, Any], name: str) -> dict[str, Any]:
    parsed = inspection.get("parsed")
    if not isinstance(parsed, dict) or not isinstance(parsed.get(name), dict):
        raise TftToolchainError(f"Unable to inspect TFT {name}")
    return parsed[name]


def _required_header_int(section: dict[str, Any], name: str) -> int:
    value = _optional_header_int(section, name)
    if value is None:
        raise TftToolchainError(f"Unable to inspect TFT header field {name!r}")
    return value


def _optional_header_int(section: dict[str, Any], name: str) -> int | None:
    value = section.get(name)
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise TftToolchainError(f"TFT header field {name!r} is not an integer")


def _iter_words_le(data: bytes):
    if len(data) % 4:
        raise TftToolchainError("Word CRC input must be 4-byte aligned")
    for offset in range(0, len(data), 4):
        yield int.from_bytes(data[offset : offset + 4], "little")


def _read_resource_directory_u32(resource: bytes, field_offset: int) -> int:
    return int.from_bytes(resource[field_offset : field_offset + 4], "little")


def _write_resource_directory_u32(raw: bytearray, resource_address: int, field_offset: int, value: int) -> None:
    start = resource_address + field_offset
    raw[start : start + 4] = int(value).to_bytes(4, "little")


def _align(value: int, alignment: int) -> int:
    return ((value + alignment - 1) // alignment) * alignment


def _is_padding_tail(data: bytes) -> bool:
    return all(value in {0x00, 0xFF} for value in data)
