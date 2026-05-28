from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from .tft_checksum import _crc32_like, update_tft_checksum
from .tft_patch import (
    HEADER1_CRC_OFFSET,
    HEADER1_FILE_SIZE_OFFSET,
    HEADER2_CRC_OFFSET,
    HEADER2_FIELD_OFFSETS,
    HEADER2_START,
    _header,
    _header2_xor_key,
    _header_int,
    _write_header2_field,
)
from .tft_toolchain import TftToolchainError, inspect_tft


HEADER1_RESOURCE_ADDRESS_OFFSET = 0x34
HEADER1_RESOURCE_CRC_OFFSET = 0x44
HEADER2_OBJECTS_ADDRESS_OFFSET = 0x14
HEADER2_VIDEOS_ADDRESS_OFFSET = 0x20
HEADER2_AUDIOS_ADDRESS_OFFSET = 0x24
HEADER2_FONTS_ADDRESS_OFFSET = 0x28
HEADER2_MAINCODE_ADDRESS_OFFSET = 0x2C
HEADER2_PICTURE_REGION_END_LOW_OFFSET = 0x30
HEADER2_FONTS_COUNT_OFFSET = 0x3C
RESOURCE_DIRECTORY_PICTURE_SIZE_OFFSET = 0x58
RESOURCE_DIRECTORY_PICTURE_END_OFFSET = 0x60
RESOURCE_DIRECTORY_SHIFTED_OFFSETS = (0x6C, 0x78, 0x84)
PICTURE_RESOURCE_MAGIC = b"\x0a\x60\x01\x04"
PICTURE_RESOURCE_RECORD_SIZE = 24
PICTURE_BLOCK_HEADER_SIZE = 20
JPEG_QUALITY_STEPS = (96, 95, 90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40, 35, 30, 25, 20)
DEFAULT_JPEG_QUALITY = 96
OFFICIAL_JPEG_SUBSAMPLING = 2
OFFICIAL_JPEG_DPI = (96, 96)


@dataclass(slots=True)
class PackedPictureResource:
    picture_id: int
    source: str
    logical_width: int
    logical_height: int
    compiled_width: int
    compiled_height: int
    jpeg_size: int
    block_size: int
    jpeg_quality: int
    scale_percent: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "picture_id": self.picture_id,
            "source": self.source,
            "logical_width": self.logical_width,
            "logical_height": self.logical_height,
            "compiled_width": self.compiled_width,
            "compiled_height": self.compiled_height,
            "jpeg_size": self.jpeg_size,
            "block_size": self.block_size,
            "jpeg_quality": self.jpeg_quality,
            "scale_percent": self.scale_percent,
        }


@dataclass(slots=True)
class HmiPictureResource:
    picture_id: int
    source: str
    logical_width: int
    logical_height: int
    image_entry_name: str
    source_entry_name: str
    image_entry_size: int
    source_entry_size: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "picture_id": self.picture_id,
            "source": self.source,
            "logical_width": self.logical_width,
            "logical_height": self.logical_height,
            "image_entry_name": self.image_entry_name,
            "source_entry_name": self.source_entry_name,
            "image_entry_size": self.image_entry_size,
            "source_entry_size": self.source_entry_size,
        }


@dataclass(slots=True)
class PicturePackResult:
    baseline_tft: str
    out_tft: str
    resource_address: int
    image_resource_address: int
    old_object_start: int
    new_object_start: int
    inserted_bytes: int
    resource_padding: int
    trimmed_resource_tail_bytes: int
    picture_count: int
    pictures: list[PackedPictureResource]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": "experimental_tft_picture_resource_pack",
            "baseline_tft": self.baseline_tft,
            "out_tft": self.out_tft,
            "resource_address": self.resource_address,
            "resource_address_hex": f"0x{self.resource_address:X}",
            "image_resource_address": self.image_resource_address,
            "image_resource_address_hex": f"0x{self.image_resource_address:X}",
            "old_object_start": self.old_object_start,
            "old_object_start_hex": f"0x{self.old_object_start:X}",
            "new_object_start": self.new_object_start,
            "new_object_start_hex": f"0x{self.new_object_start:X}",
            "inserted_bytes": self.inserted_bytes,
            "resource_padding": self.resource_padding,
            "trimmed_resource_tail_bytes": self.trimmed_resource_tail_bytes,
            "picture_count": self.picture_count,
            "pictures": [picture.to_dict() for picture in self.pictures],
            "warnings": [
                "Experimental V1 packs JPEG-backed picture resources into the current TJC 800x480 TFT layout.",
                "PNG/JPG inputs are padded to 16-pixel boundaries and JPEG-encoded for the screen resource section.",
                "The resource region size and object start address are preserved; newly inserted picture bytes consume trailing zero padding.",
                "New picture ids are proven for picture objects; image-button packing is experimental and maps states through compiled background slots.",
            ],
        }


def compile_hmi_picture_resource(
    source: str | Path,
    picture_id: int,
    *,
    quality: int = DEFAULT_JPEG_QUALITY,
) -> tuple[HmiPictureResource, bytes, bytes]:
    """Compile one HMI picture resource pair.

    USART HMI stores each imported picture twice in the .HMI container:
    `N.i` is the screen JPEG payload, and `N.is` keeps the original source
    image bytes with a short format tag such as `png` or `jpg`.
    """

    src = Path(source).resolve()
    source_bytes = src.read_bytes()
    source_tag = _hmi_source_tag(src)
    info, block = compile_picture_resource(src, picture_id, quality=quality)
    image_entry = _picture_record(
        picture_id=0,
        block_offset=PICTURE_RESOURCE_RECORD_SIZE,
        logical_width=info.logical_width,
        logical_height=info.logical_height,
        block_size=len(block),
    ) + block
    source_entry = _source_picture_record(
        logical_width=info.logical_width,
        logical_height=info.logical_height,
        payload_size=len(source_bytes),
        tag_size=len(source_tag),
    ) + source_tag + source_bytes
    resource = HmiPictureResource(
        picture_id=int(picture_id),
        source=str(src),
        logical_width=info.logical_width,
        logical_height=info.logical_height,
        image_entry_name=f"{int(picture_id)}.i",
        source_entry_name=f"{int(picture_id)}.is",
        image_entry_size=len(image_entry),
        source_entry_size=len(source_entry),
    )
    return resource, image_entry, source_entry


def compile_picture_resource(
    source: str | Path,
    picture_id: int,
    *,
    quality: int = DEFAULT_JPEG_QUALITY,
    max_block_size: int | None = None,
) -> tuple[PackedPictureResource, bytes]:
    """Compile a local PNG/JPG into the TFT picture block payload.

    The official editor pads the stored JPEG dimensions to multiples of 16.
    The page object can still keep the logical width/height from the source.
    """

    src = Path(source).resolve()
    if not src.exists():
        raise TftToolchainError(f"Picture source not found: {src}")
    if not 0 <= int(picture_id) <= 0xFFFF:
        raise TftToolchainError(f"Picture id must fit in 16 bits, got {picture_id}")

    original = _open_picture_rgb(src)
    quality_steps = tuple(step for step in JPEG_QUALITY_STEPS if step <= int(quality))
    if not quality_steps:
        quality_steps = (int(quality),)

    scale_percent = 100
    image = original
    while image.width >= 16 and image.height >= 16:
        best: tuple[PackedPictureResource, bytes] | None = None
        for candidate_quality in quality_steps:
            info, block = _encode_picture_resource(
                image,
                picture_id=int(picture_id),
                source=src,
                quality=candidate_quality,
                scale_percent=scale_percent,
            )
            if best is None or info.block_size < best[0].block_size:
                best = (info, block)
            if max_block_size is None or info.block_size <= max_block_size:
                return info, block
        if max_block_size is None:
            assert best is not None
            return best

        next_scale = max(10, int(scale_percent * 0.9))
        if next_scale == scale_percent:
            break
        scale_percent = next_scale
        new_width = max(16, original.width * scale_percent // 100)
        new_height = max(16, original.height * scale_percent // 100)
        image = original.resize((new_width, new_height), Image.Resampling.LANCZOS)

    raise TftToolchainError(
        f"Picture {src} cannot be compressed into the available TFT resource budget "
        f"({max_block_size} bytes)"
    )


def pack_picture_resources_into_tft(
    baseline_tft: str | Path,
    pictures: list[tuple[int, str | Path]],
    *,
    out_tft: str | Path,
) -> PicturePackResult:
    baseline_path = Path(baseline_tft).resolve()
    out_path = Path(out_tft).resolve()
    if not pictures:
        raise TftToolchainError("No picture resources were provided")

    inspection = inspect_tft(baseline_path)
    header1 = _header(inspection, "Header1")
    header2 = _header(inspection, "Header2")
    model = str(inspection.get("model") or "")
    model_series = _required_header_int(header1, "model_series")
    resource_address = _required_header_int(header1, "ressources_files_address")
    resource_size = _required_header_int(header1, "ressource_files_size")
    image_resource_address = _required_header_int(header2, "videos_address")
    old_object_start = _required_header_int(header2, "unknown_objects_address")
    if resource_address + resource_size != old_object_start:
        raise TftToolchainError(
            "TFT resource region does not end at unknown_objects_address: "
            f"resource_end=0x{resource_address + resource_size:X}, objects=0x{old_object_start:X}"
        )

    raw = baseline_path.read_bytes()
    records, picture_region_end = _parse_picture_resource_records(raw, image_resource_address)
    existing_ids = {record["picture_id"] for record in records}
    pictures = sorted(pictures, key=lambda item: int(item[0]))
    resource = raw[resource_address:old_object_start]
    padding_capacity = _padding_tail_length(resource)
    table_growth = len(pictures) * PICTURE_RESOURCE_RECORD_SIZE
    if table_growth >= padding_capacity:
        raise TftToolchainError(
            "TFT resource region does not have enough trailing padding for new picture table records"
        )
    picture_budget = padding_capacity - table_growth
    compiled = _compile_picture_resources_to_budget(
        pictures,
        existing_ids=existing_ids,
        picture_budget=picture_budget,
    )
    return _pack_compiled_picture_resources(
        baseline_path=baseline_path,
        out_path=out_path,
        header1=header1,
        header2=header2,
        model=model,
        model_series=model_series,
        resource_address=resource_address,
        resource_size=resource_size,
        image_resource_address=image_resource_address,
        old_object_start=old_object_start,
        records=records,
        picture_region_end=picture_region_end,
        compiled=compiled,
    )


def pack_hmi_picture_entries_into_tft(
    baseline_tft: str | Path,
    pictures: list[tuple[int, bytes, str]],
    *,
    out_tft: str | Path,
) -> PicturePackResult:
    baseline_path = Path(baseline_tft).resolve()
    out_path = Path(out_tft).resolve()
    if not pictures:
        raise TftToolchainError("No HMI picture entries were provided")

    inspection = inspect_tft(baseline_path)
    header1 = _header(inspection, "Header1")
    header2 = _header(inspection, "Header2")
    model = str(inspection.get("model") or "")
    model_series = _required_header_int(header1, "model_series")
    resource_address = _required_header_int(header1, "ressources_files_address")
    resource_size = _required_header_int(header1, "ressource_files_size")
    image_resource_address = _required_header_int(header2, "videos_address")
    old_object_start = _required_header_int(header2, "unknown_objects_address")
    if resource_address + resource_size != old_object_start:
        raise TftToolchainError(
            "TFT resource region does not end at unknown_objects_address: "
            f"resource_end=0x{resource_address + resource_size:X}, objects=0x{old_object_start:X}"
        )

    raw = baseline_path.read_bytes()
    records, picture_region_end = _parse_picture_resource_records(raw, image_resource_address)
    existing_ids = {record["picture_id"] for record in records}
    compiled = _precompiled_hmi_picture_resources(
        pictures,
        existing_ids=existing_ids,
    )
    return _pack_compiled_picture_resources(
        baseline_path=baseline_path,
        out_path=out_path,
        header1=header1,
        header2=header2,
        model=model,
        model_series=model_series,
        resource_address=resource_address,
        resource_size=resource_size,
        image_resource_address=image_resource_address,
        old_object_start=old_object_start,
        records=records,
        picture_region_end=picture_region_end,
        compiled=compiled,
    )


def _pack_compiled_picture_resources(
    *,
    baseline_path: Path,
    out_path: Path,
    header1: dict[str, Any],
    header2: dict[str, Any],
    model: str,
    model_series: int,
    resource_address: int,
    resource_size: int,
    image_resource_address: int,
    old_object_start: int,
    records: list[dict[str, Any]],
    picture_region_end: int,
    compiled: list[tuple[PackedPictureResource, bytes]],
) -> PicturePackResult:
    raw = baseline_path.read_bytes()
    resource = raw[resource_address:old_object_start]

    old_table_size = len(records) * PICTURE_RESOURCE_RECORD_SIZE
    new_table_size = (len(records) + len(compiled)) * PICTURE_RESOURCE_RECORD_SIZE
    old_blocks = raw[image_resource_address + old_table_size : picture_region_end]

    new_records = bytearray()
    for record in records:
        record_data = bytearray(record["raw"])
        shifted_offset = int(record["block_offset"]) + (len(compiled) * PICTURE_RESOURCE_RECORD_SIZE)
        record_data[8:12] = shifted_offset.to_bytes(4, "little")
        new_records.extend(record_data)

    block_cursor = new_table_size + len(old_blocks)
    new_blocks = bytearray()
    for info, block in compiled:
        new_records.extend(
            _picture_record(
                picture_id=info.picture_id,
                block_offset=block_cursor,
                logical_width=info.logical_width,
                logical_height=info.logical_height,
                block_size=len(block),
            )
        )
        new_blocks.extend(block)
        block_cursor += len(block)

    old_picture_region = raw[image_resource_address:picture_region_end]
    new_picture_region = bytes(new_records) + old_blocks + bytes(new_blocks)
    inserted_bytes = len(new_picture_region) - len(old_picture_region)

    image_relative = image_resource_address - resource_address
    picture_end_relative = picture_region_end - resource_address
    new_resource_unpadded = (
        resource[:image_relative]
        + new_picture_region
        + resource[picture_end_relative:]
    )
    overflow = max(0, len(new_resource_unpadded) - resource_size)
    if overflow:
        trimmed_tail = new_resource_unpadded[resource_size:]
        if not _is_padding_tail(trimmed_tail):
            raise TftToolchainError(
                "Packed picture resources do not fit in the fixed TFT resource region; "
                f"would need to discard {overflow} non-padding bytes before object section"
            )
        fixed_resource = new_resource_unpadded[:resource_size]
        resource_padding = 0
    else:
        fixed_resource = new_resource_unpadded + (b"\x00" * (resource_size - len(new_resource_unpadded)))
        resource_padding = resource_size - len(new_resource_unpadded)
    new_object_start = old_object_start

    new_raw = bytearray(
        raw[:resource_address]
        + fixed_resource
        + raw[old_object_start:]
    )

    _refresh_picture_resource_headers(
        new_raw,
        header1=header1,
        header2=header2,
        model=model,
        model_series=model_series,
        resource_address=resource_address,
        resource_size=resource_size,
        image_resource_address=image_resource_address,
        old_object_start=old_object_start,
        inserted_bytes=inserted_bytes,
        picture_region_end=picture_region_end,
        picture_count=len(records) + len(compiled),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(new_raw)
    return PicturePackResult(
        baseline_tft=str(baseline_path),
        out_tft=str(out_path),
        resource_address=resource_address,
        image_resource_address=image_resource_address,
        old_object_start=old_object_start,
        new_object_start=new_object_start,
        inserted_bytes=inserted_bytes,
        resource_padding=resource_padding,
        trimmed_resource_tail_bytes=overflow,
        picture_count=len(records) + len(compiled),
        pictures=[info for info, _block in compiled],
    )


def _compile_picture_resources_to_budget(
    pictures: list[tuple[int, str | Path]],
    *,
    existing_ids: set[int],
    picture_budget: int,
) -> list[tuple[PackedPictureResource, bytes]]:
    used_ids = set(existing_ids)
    compiled: list[tuple[PackedPictureResource, bytes]] = []
    for picture_id, source in pictures:
        picture_id = int(picture_id)
        if picture_id in used_ids:
            raise TftToolchainError(f"Picture id {picture_id} already exists in baseline TFT")
        info, block = compile_picture_resource(source, picture_id)
        compiled.append((info, block))
        used_ids.add(info.picture_id)

    if sum(len(block) for _info, block in compiled) <= picture_budget:
        return compiled

    budgets = _split_picture_budget([len(block) for _info, block in compiled], picture_budget)
    used_ids = set(existing_ids)
    compressed: list[tuple[PackedPictureResource, bytes]] = []
    for (picture_id, source), budget in zip(pictures, budgets):
        picture_id = int(picture_id)
        if picture_id in used_ids:
            raise TftToolchainError(f"Picture id {picture_id} already exists in baseline TFT")
        info, block = compile_picture_resource(source, picture_id, max_block_size=budget)
        compressed.append((info, block))
        used_ids.add(info.picture_id)

    total_size = sum(len(block) for _info, block in compressed)
    if total_size > picture_budget:
        raise TftToolchainError(
            "Compressed picture resources still exceed the fixed TFT resource padding: "
            f"{total_size} > {picture_budget}"
        )
    return compressed


def _precompiled_hmi_picture_resources(
    pictures: list[tuple[int, bytes, str]],
    *,
    existing_ids: set[int],
) -> list[tuple[PackedPictureResource, bytes]]:
    used_ids = set(existing_ids)
    compiled: list[tuple[PackedPictureResource, bytes]] = []
    for picture_id, entry_data, source_label in pictures:
        picture_id = int(picture_id)
        if picture_id in used_ids:
            raise TftToolchainError(f"Picture id {picture_id} already exists in baseline TFT")
        info, block = _parse_hmi_picture_entry_resource(
            picture_id=picture_id,
            entry_data=entry_data,
            source_label=source_label,
        )
        compiled.append((info, block))
        used_ids.add(info.picture_id)
    return compiled


def _parse_hmi_picture_entry_resource(
    *,
    picture_id: int,
    entry_data: bytes,
    source_label: str,
) -> tuple[PackedPictureResource, bytes]:
    if len(entry_data) < PICTURE_RESOURCE_RECORD_SIZE:
        raise TftToolchainError("HMI picture entry is shorter than the 24-byte picture record header")
    if entry_data[:4] != PICTURE_RESOURCE_MAGIC:
        raise TftToolchainError("HMI picture entry does not start with the expected picture resource magic")
    block_offset = int.from_bytes(entry_data[8:12], "little")
    logical_width = int.from_bytes(entry_data[0x0C:0x0E], "little")
    logical_height = int.from_bytes(entry_data[0x0E:0x10], "little")
    block_size = int.from_bytes(entry_data[0x10:0x14], "little")
    if block_offset < PICTURE_RESOURCE_RECORD_SIZE:
        raise TftToolchainError(f"HMI picture entry has invalid block offset {block_offset}")
    block = entry_data[block_offset : block_offset + block_size]
    if len(block) != block_size:
        raise TftToolchainError(
            "HMI picture entry block payload is truncated: "
            f"expected {block_size} bytes, found {len(block)}"
        )
    jpeg_size = max(0, block_size - PICTURE_BLOCK_HEADER_SIZE)
    info = PackedPictureResource(
        picture_id=int(picture_id),
        source=str(source_label),
        logical_width=logical_width,
        logical_height=logical_height,
        compiled_width=logical_width,
        compiled_height=logical_height,
        jpeg_size=jpeg_size,
        block_size=block_size,
        jpeg_quality=DEFAULT_JPEG_QUALITY,
        scale_percent=100,
    )
    return info, block


def _split_picture_budget(sizes: list[int], budget: int) -> list[int]:
    if not sizes or budget <= 0:
        raise TftToolchainError("No TFT picture resource budget is available")
    minimum = PICTURE_BLOCK_HEADER_SIZE + 1
    if budget < minimum * len(sizes):
        raise TftToolchainError(
            "TFT resource padding is too small even for minimal picture block headers"
        )

    total = sum(sizes)
    if total <= 0:
        return [budget // len(sizes)] * len(sizes)

    budgets = [max(minimum, (budget * size) // total) for size in sizes]
    delta = budget - sum(budgets)
    budgets[-1] += delta
    while budgets[-1] < minimum:
        donor = max(range(len(budgets) - 1), key=lambda index: budgets[index])
        transfer = min(minimum - budgets[-1], budgets[donor] - minimum)
        if transfer <= 0:
            raise TftToolchainError("Unable to split TFT picture resource budget safely")
        budgets[donor] -= transfer
        budgets[-1] += transfer
    return budgets


def _encode_picture_resource(
    image: Image.Image,
    *,
    picture_id: int,
    source: Path,
    quality: int,
    scale_percent: int,
) -> tuple[PackedPictureResource, bytes]:
    logical_width, logical_height = image.size
    compiled_width = _align(logical_width, 16)
    compiled_height = _align(logical_height, 16)
    canvas = Image.new("RGB", (compiled_width, compiled_height), (0, 0, 0))
    canvas.paste(image, (0, 0))

    buffer = BytesIO()
    canvas.save(
        buffer,
        format="JPEG",
        quality=quality,
        subsampling=OFFICIAL_JPEG_SUBSAMPLING,
        dpi=OFFICIAL_JPEG_DPI,
        optimize=False,
        progressive=False,
    )
    jpeg = buffer.getvalue()
    block = (
        b"\x00\x00\x00\x00"
        + compiled_width.to_bytes(4, "little")
        + compiled_height.to_bytes(4, "little")
        + b"\x00\x00\x00\x00"
        + b"\x00\x00\x00\x00"
        + jpeg
    )
    info = PackedPictureResource(
        picture_id=picture_id,
        source=str(source),
        logical_width=logical_width,
        logical_height=logical_height,
        compiled_width=compiled_width,
        compiled_height=compiled_height,
        jpeg_size=len(jpeg),
        block_size=len(block),
        jpeg_quality=quality,
        scale_percent=scale_percent,
    )
    return info, block


def _open_picture_rgb(path: Path) -> Image.Image:
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        if _has_transparency(image):
            rgba = image.convert("RGBA")
            background = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
            background.alpha_composite(rgba)
            return background.convert("RGB")
        return image.convert("RGB")


def _has_transparency(image: Image.Image) -> bool:
    if image.mode in {"RGBA", "LA"}:
        return True
    if image.mode == "P" and "transparency" in image.info:
        return True
    return False


def _refresh_picture_resource_headers(
    raw: bytearray,
    *,
    header1: dict[str, Any],
    header2: dict[str, Any],
    model: str,
    model_series: int,
    resource_address: int,
    resource_size: int,
    image_resource_address: int,
    old_object_start: int,
    inserted_bytes: int,
    picture_region_end: int,
    picture_count: int,
) -> None:
    raw[HEADER1_FILE_SIZE_OFFSET : HEADER1_FILE_SIZE_OFFSET + 4] = len(raw).to_bytes(4, "little")
    _refresh_resource_directory(
        raw,
        resource_address=resource_address,
        image_resource_address=image_resource_address,
        picture_region_end=picture_region_end,
        inserted_bytes=inserted_bytes,
    )
    resource_crc = _crc32_like(
        list(_iter_words_le(raw[resource_address : resource_address + resource_size]))
    )
    raw[HEADER1_RESOURCE_CRC_OFFSET : HEADER1_RESOURCE_CRC_OFFSET + 4] = resource_crc.to_bytes(4, "little")

    key = _header2_xor_key(model)
    new_picture_region_end = picture_region_end + inserted_bytes
    _write_header2_field(raw, key, HEADER2_OBJECTS_ADDRESS_OFFSET, old_object_start.to_bytes(4, "little"))
    _write_header2_field(raw, key, HEADER2_VIDEOS_ADDRESS_OFFSET, image_resource_address.to_bytes(4, "little"))
    _write_header2_field(
        raw,
        key,
        HEADER2_PICTURE_REGION_END_LOW_OFFSET,
        (new_picture_region_end & 0xFFFF).to_bytes(2, "little"),
    )
    for key_name, field_offset in (
        ("audios_address", HEADER2_AUDIOS_ADDRESS_OFFSET),
        ("fonts_address", HEADER2_FONTS_ADDRESS_OFFSET),
        ("unknown_maincode_binary", HEADER2_MAINCODE_ADDRESS_OFFSET),
    ):
        value = _header_int(header2, key_name)
        if value is None:
            continue
        if picture_region_end <= value < old_object_start:
            value += inserted_bytes
        _write_header2_field(raw, key, field_offset, value.to_bytes(4, "little"))
    _write_header2_field(raw, key, HEADER2_FONTS_COUNT_OFFSET, picture_count.to_bytes(2, "little"))

    raw[HEADER2_CRC_OFFSET : HEADER2_CRC_OFFSET + 4] = _crc32_like(
        list(raw[HEADER2_START:HEADER2_CRC_OFFSET])
    ).to_bytes(4, "little")
    raw[HEADER1_CRC_OFFSET : HEADER1_CRC_OFFSET + 4] = _crc32_like(
        list(raw[:HEADER1_CRC_OFFSET])
    ).to_bytes(4, "little")
    raw[:] = update_tft_checksum(bytes(raw), series=model_series)


def _refresh_resource_directory(
    raw: bytearray,
    *,
    resource_address: int,
    image_resource_address: int,
    picture_region_end: int,
    inserted_bytes: int,
) -> None:
    """Update the small resource directory at the start of the TFT resource area."""

    if inserted_bytes == 0:
        return
    new_picture_region_end = picture_region_end + inserted_bytes
    _write_resource_directory_u32(
        raw,
        resource_address,
        RESOURCE_DIRECTORY_PICTURE_SIZE_OFFSET,
        new_picture_region_end - image_resource_address,
    )
    _write_resource_directory_u32(
        raw,
        resource_address,
        RESOURCE_DIRECTORY_PICTURE_END_OFFSET,
        new_picture_region_end - resource_address,
    )

    shifted_threshold = picture_region_end - resource_address
    for field_offset in RESOURCE_DIRECTORY_SHIFTED_OFFSETS:
        value = _read_resource_directory_u32(raw, resource_address, field_offset)
        if value >= shifted_threshold:
            _write_resource_directory_u32(
                raw,
                resource_address,
                field_offset,
                value + inserted_bytes,
            )


def _parse_picture_resource_records(raw: bytes, image_resource_address: int) -> tuple[list[dict[str, Any]], int]:
    first = raw[image_resource_address : image_resource_address + PICTURE_RESOURCE_RECORD_SIZE]
    if len(first) != PICTURE_RESOURCE_RECORD_SIZE or first[:4] != PICTURE_RESOURCE_MAGIC:
        raise TftToolchainError(
            f"Unable to locate TFT picture resource table at 0x{image_resource_address:X}"
        )
    first_block_offset = int.from_bytes(first[8:12], "little")
    if first_block_offset == 0 or first_block_offset % PICTURE_RESOURCE_RECORD_SIZE:
        raise TftToolchainError(f"Unexpected first picture block offset: 0x{first_block_offset:X}")
    count = first_block_offset // PICTURE_RESOURCE_RECORD_SIZE
    records = []
    picture_region_end = image_resource_address + first_block_offset
    for index in range(count):
        start = image_resource_address + index * PICTURE_RESOURCE_RECORD_SIZE
        raw_record = raw[start : start + PICTURE_RESOURCE_RECORD_SIZE]
        if len(raw_record) != PICTURE_RESOURCE_RECORD_SIZE or raw_record[:4] != PICTURE_RESOURCE_MAGIC:
            raise TftToolchainError(f"Picture resource record {index} has an unexpected header")
        block_offset = int.from_bytes(raw_record[8:12], "little")
        block_size = int.from_bytes(raw_record[0x10:0x14], "little")
        if block_size < PICTURE_BLOCK_HEADER_SIZE:
            raise TftToolchainError(f"Picture resource record {index} has invalid block size {block_size}")
        picture_region_end = max(picture_region_end, image_resource_address + block_offset + block_size)
        records.append(
            {
                "raw": raw_record,
                "picture_id": int.from_bytes(raw_record[4:8], "little"),
                "block_offset": block_offset,
                "logical_width": int.from_bytes(raw_record[0x0C:0x0E], "little"),
                "logical_height": int.from_bytes(raw_record[0x0E:0x10], "little"),
                "block_size": block_size,
            }
        )
    return records, picture_region_end


def _picture_record(
    *,
    picture_id: int,
    block_offset: int,
    logical_width: int,
    logical_height: int,
    block_size: int,
) -> bytes:
    return (
        PICTURE_RESOURCE_MAGIC
        + picture_id.to_bytes(4, "little")
        + block_offset.to_bytes(4, "little")
        + logical_width.to_bytes(2, "little")
        + logical_height.to_bytes(2, "little")
        + block_size.to_bytes(4, "little")
        + b"\x00\x00\x00\x00"
    )


def _source_picture_record(
    *,
    logical_width: int,
    logical_height: int,
    payload_size: int,
    tag_size: int,
) -> bytes:
    return (
        b"\x0a\x64\x01\x01"
        + (0).to_bytes(4, "little")
        + (PICTURE_RESOURCE_RECORD_SIZE + tag_size).to_bytes(4, "little")
        + logical_width.to_bytes(2, "little")
        + logical_height.to_bytes(2, "little")
        + payload_size.to_bytes(4, "little")
        + b"\x00\x00\x00\x00"
    )


def _hmi_source_tag(path: Path) -> bytes:
    suffix = path.suffix.lower().lstrip(".")
    if suffix == "jpeg":
        suffix = "jpg"
    if suffix not in {"png", "jpg"}:
        raise TftToolchainError(f"Unsupported HMI picture source type for {path}")
    return suffix.encode("ascii")


def _required_header_int(header: dict[str, Any], key: str) -> int:
    value = _header_int(header, key)
    if value is None:
        raise TftToolchainError(f"Unable to inspect TFT header field {key!r}")
    return value


def _iter_words_le(data: bytes):
    if len(data) % 4:
        raise TftToolchainError("Word CRC input must be 4-byte aligned")
    for offset in range(0, len(data), 4):
        yield int.from_bytes(data[offset : offset + 4], "little")


def _align(value: int, alignment: int) -> int:
    return ((value + alignment - 1) // alignment) * alignment


def _is_padding_tail(data: bytes) -> bool:
    return all(value in {0x00, 0xFF} for value in data)


def _padding_tail_length(data: bytes) -> int:
    count = 0
    for value in reversed(data):
        if value not in {0x00, 0xFF}:
            break
        count += 1
    return count


def _read_resource_directory_u32(raw: bytes, resource_address: int, field_offset: int) -> int:
    start = resource_address + field_offset
    return int.from_bytes(raw[start : start + 4], "little")


def _write_resource_directory_u32(
    raw: bytearray,
    resource_address: int,
    field_offset: int,
    value: int,
) -> None:
    start = resource_address + field_offset
    raw[start : start + 4] = value.to_bytes(4, "little")
