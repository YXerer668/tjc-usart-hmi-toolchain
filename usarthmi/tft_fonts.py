from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .tft_checksum import _crc32_like, update_tft_checksum
from .tft_font_pack import ZI_MAGIC, parse_zi_file
from .tft_images import HEADER1_RESOURCE_CRC_OFFSET, _iter_words_le
from .tft_patch import HEADER1_CRC_OFFSET, _header, _header_int
from .tft_toolchain import TftToolchainError, inspect_tft


@dataclass(slots=True)
class TftFontPatchResult:
    baseline_tft: str
    font_path: str
    out_tft: str
    file_size: int
    font_start: int
    font_end: int
    old_font_span: int
    new_font_size: int
    zero_padding: int
    font_info: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": "experimental_tft_font_patch",
            "baseline_tft": self.baseline_tft,
            "font_path": self.font_path,
            "out_tft": self.out_tft,
            "file_size": self.file_size,
            "font_start": self.font_start,
            "font_start_hex": f"0x{self.font_start:X}",
            "font_end": self.font_end,
            "font_end_hex": f"0x{self.font_end:X}",
            "old_font_span": self.old_font_span,
            "new_font_size": self.new_font_size,
            "zero_padding": self.zero_padding,
            "font_info": self.font_info,
            "warnings": [
                "Experimental V1 replaces the first embedded .zi font in place.",
                "The TFT file size and section addresses are preserved; unused bytes in the old font span are zero-filled.",
                "Only replacing a same-or-smaller font resource is supported in this safe pass.",
            ],
        }


def patch_tft_font(
    baseline_tft: str | Path,
    *,
    font_path: str | Path,
    out_tft: str | Path,
) -> TftFontPatchResult:
    baseline = Path(baseline_tft).resolve()
    font = Path(font_path).resolve()
    output = Path(out_tft).resolve()
    raw = bytearray(baseline.read_bytes())
    replacement = font.read_bytes()
    font_info = parse_zi_file(font)

    inspection = inspect_tft(baseline)
    header1 = _header(inspection, "Header1")
    header2 = _header(inspection, "Header2")
    model_series = _header_int(header1, "model_series")
    resource_address = _header_int(header1, "ressources_files_address")
    resource_size = _header_int(header1, "ressource_files_size")
    object_start = _header_int(header2, "unknown_objects_address")
    if model_series is None or resource_address is None or resource_size is None or object_start is None:
        raise TftToolchainError("Unable to inspect required TFT header/resource fields")

    font_start = raw.find(ZI_MAGIC, resource_address, object_start)
    if font_start < 0:
        raise TftToolchainError("Unable to locate embedded .zi font magic in TFT resource area")
    font_end = _font_span_end(header2, font_start, object_start)
    old_span = font_end - font_start
    if old_span <= 0:
        raise TftToolchainError("Unable to determine embedded .zi font span")
    if len(replacement) > old_span:
        raise TftToolchainError(
            f"Replacement font is larger than the safe in-place span: {len(replacement)} > {old_span}"
        )

    raw[font_start:font_end] = replacement + (b"\x00" * (old_span - len(replacement)))
    _refresh_font_patch_checksums(
        raw,
        resource_address=resource_address,
        resource_size=resource_size,
        model_series=model_series,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    return TftFontPatchResult(
        baseline_tft=str(baseline),
        font_path=str(font),
        out_tft=str(output),
        file_size=len(raw),
        font_start=font_start,
        font_end=font_end,
        old_font_span=old_span,
        new_font_size=len(replacement),
        zero_padding=old_span - len(replacement),
        font_info={
            "font_name": font_info["font_name"],
            "encoding_name": font_info["encoding_name"],
            "char_height": font_info["char_height"],
            "char_width": font_info["char_width"],
            "char_count": font_info["char_count"],
            "version": font_info["version"],
        },
    )


def _font_span_end(header2: dict[str, Any], font_start: int, object_start: int) -> int:
    candidates: list[int] = []
    for key in ("fonts_address", "audios_address", "unknown_maincode_binary", "pictures_address", "gmovs_address"):
        value = _header_int(header2, key)
        if value is not None and value > font_start:
            candidates.append(value)
    if object_start > font_start:
        candidates.append(object_start)
    return min(candidates) if candidates else object_start


def _refresh_font_patch_checksums(
    raw: bytearray,
    *,
    resource_address: int,
    resource_size: int,
    model_series: int,
) -> None:
    resource = raw[resource_address : resource_address + resource_size]
    if len(resource) != resource_size:
        raise TftToolchainError("TFT resource area is truncated")
    resource_crc = _crc32_like(list(_iter_words_le(resource)))
    raw[HEADER1_RESOURCE_CRC_OFFSET : HEADER1_RESOURCE_CRC_OFFSET + 4] = resource_crc.to_bytes(4, "little")
    raw[HEADER1_CRC_OFFSET : HEADER1_CRC_OFFSET + 4] = _crc32_like(list(raw[:HEADER1_CRC_OFFSET])).to_bytes(4, "little")
    raw[:] = update_tft_checksum(bytes(raw), series=model_series)
