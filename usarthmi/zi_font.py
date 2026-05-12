from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from PIL import Image

from .tft_font_pack import ZI_HEADER_SIZE, ZI_MAGIC


class ZiFontError(RuntimeError):
    """Raised when a .zi font cannot be parsed or rendered."""


@dataclass(frozen=True, slots=True)
class ZiGlyph:
    codepoint: int
    width: int
    kerning_left: int
    kerning_right: int
    data: bytes

    @property
    def total_width(self) -> int:
        return max(self.width + self.kerning_left + self.kerning_right, 1)


class ZiFont:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).resolve()
        self._init_from_bytes(self.path.read_bytes())

    @classmethod
    def from_bytes(cls, raw: bytes, source: str = "<bytes>") -> "ZiFont":
        obj = cls.__new__(cls)
        obj.path = Path(source)
        obj._init_from_bytes(raw)
        return obj

    def _init_from_bytes(self, raw: bytes) -> None:
        if len(raw) < ZI_HEADER_SIZE or not raw.startswith(ZI_MAGIC):
            raise ZiFontError(f"Not a recognized .zi v5/v6 font: {self.path}")

        self.raw = raw
        self.header = raw[:ZI_HEADER_SIZE]
        self.codepage = self.header[0x04]
        self.mode = self.header[0x05]
        self.character_width = self.header[0x06]
        self.character_height = self.header[0x07]
        self.character_count = int.from_bytes(self.header[0x0C:0x10], "little")
        self.version = self.header[0x10]
        self.descriptor_len = self.header[0x11]
        self.file_name_len = self.header[0x20]
        self.align8 = self.header[0x21] == 1
        self._base = ZI_HEADER_SIZE + self.descriptor_len

        descriptor = raw[ZI_HEADER_SIZE : ZI_HEADER_SIZE + self.descriptor_len]
        self.font_name = descriptor[: self.file_name_len].decode("ascii", errors="replace")
        self.encoding_name = descriptor[self.file_name_len :].decode("ascii", errors="replace")
        self.glyphs = self._parse_glyphs()

    def _parse_glyphs(self) -> dict[int, ZiGlyph]:
        table_start = ZI_HEADER_SIZE + self.descriptor_len
        table_end = table_start + self.character_count * 10
        if table_end > len(self.raw):
            raise ZiFontError(f"Truncated .zi character table: {self.path}")

        glyphs: dict[int, ZiGlyph] = {}
        for offset in range(table_start, table_end, 10):
            item = self.raw[offset : offset + 10]
            codepoint = int.from_bytes(item[0:2], "little")
            data_offset = int.from_bytes(item[5:8] + b"\x00", "little")
            if self.align8:
                data_offset *= 8
            data_length = int.from_bytes(item[8:10], "little")
            data_start = self._base + data_offset
            data_end = data_start + data_length
            if data_start < self._base or data_end > len(self.raw):
                continue
            glyphs[codepoint] = ZiGlyph(
                codepoint=codepoint,
                width=item[2],
                kerning_left=item[3],
                kerning_right=item[4],
                data=self.raw[data_start:data_end],
            )
        return glyphs

    def measure_text(self, text: str) -> tuple[int, int]:
        width = sum(self._glyph_for_char(char).total_width for char in text if char not in "\r\n")
        return max(width, 1), max(self.character_height, 1)

    def render_text(self, text: str, color: tuple[int, int, int]) -> Image.Image:
        width, height = self.measure_text(text)
        output = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        cursor = 0
        for char in text:
            if char in "\r\n":
                continue
            glyph = self._glyph_for_char(char)
            mask = self._glyph_mask(glyph.codepoint)
            glyph_img = Image.new("RGBA", mask.size, color + (0,))
            glyph_img.putalpha(mask)
            output.alpha_composite(glyph_img, (cursor, 0))
            cursor += glyph.total_width
        return output

    def _glyph_for_char(self, char: str) -> ZiGlyph:
        codepoint = self._map_char_to_codepoint(char)
        glyph = self.glyphs.get(codepoint)
        if glyph is not None:
            return glyph
        fallback = self.glyphs.get(ord("?")) or next(iter(self.glyphs.values()), None)
        if fallback is None:
            raise ZiFontError(f"Font has no renderable glyphs: {self.path}")
        return fallback

    def _map_char_to_codepoint(self, char: str) -> int:
        encoding = self.encoding_name.lower().replace("_", "-")
        if self.codepage == 2 or encoding in {"gb2312", "gbk"}:
            data = char.encode("gb2312", errors="replace")
            if len(data) == 1:
                return data[0]
            if len(data) >= 2:
                return data[1] * 256 + data[0]
        if self.codepage == 0 or encoding == "ascii":
            return ord(char) if ord(char) < 256 else ord("?")
        return ord(char)

    @lru_cache(maxsize=4096)
    def _glyph_mask(self, codepoint: int) -> Image.Image:
        glyph = self.glyphs[codepoint]
        width = glyph.total_width
        height = max(self.character_height, 1)
        alpha = bytearray(width * height)
        pixel = 0
        data = glyph.data
        if not data:
            return Image.frombytes("L", (width, height), bytes(alpha))

        bitdepth = data[0]
        for item in data[1:]:
            drawing_mode = item >> 6
            drawing_mode2 = (item & 0b00100000) >> 5
            number = item & 0b00011111

            if drawing_mode == 0:
                pixel = self._append_alpha(alpha, pixel, 0 if drawing_mode2 == 0 else 255, number)
            elif drawing_mode == 1:
                pixel = self._append_alpha(alpha, pixel, 0, number)
                pixel = self._append_alpha(alpha, pixel, 255, 1 + int(drawing_mode2 == 1))
            elif drawing_mode == 2:
                if bitdepth == 1:
                    pixel = self._append_alpha(alpha, pixel, 0, number)
                    pixel = self._append_alpha(alpha, pixel, 255, 3 + int(drawing_mode2 == 1))
                else:
                    whites = (item & 0b00111000) >> 3
                    shade = item & 0b00000111
                    pixel = self._append_alpha(alpha, pixel, 0, whites)
                    pixel = self._append_alpha(alpha, pixel, _shade_to_alpha(shade), 1)
            elif drawing_mode == 3:
                if bitdepth == 1:
                    whites = (item & 0b00111000) >> 3
                    blacks = item & 0b00000111
                    pixel = self._append_alpha(alpha, pixel, 0, whites)
                    pixel = self._append_alpha(alpha, pixel, 255, blacks)
                else:
                    shade1 = (item & 0b00111000) >> 3
                    shade2 = item & 0b00000111
                    pixel = self._append_alpha(alpha, pixel, _shade_to_alpha(shade1), 1)
                    pixel = self._append_alpha(alpha, pixel, _shade_to_alpha(shade2), 1)

            if pixel >= len(alpha):
                break

        return Image.frombytes("L", (width, height), bytes(alpha))

    @staticmethod
    def _append_alpha(buffer: bytearray, pixel: int, value: int, count: int) -> int:
        if count <= 0:
            return pixel
        end = min(pixel + count, len(buffer))
        buffer[pixel:end] = bytes([value]) * (end - pixel)
        return pixel + count


def load_zi_fonts(paths: dict[int, str | Path] | None = None) -> dict[int, ZiFont]:
    return {int(font_id): ZiFont(path) for font_id, path in (paths or {}).items()}


def find_zi_fonts_in_directory(directory: str | Path | None) -> dict[int, Path]:
    if directory is None:
        return {}
    root = Path(directory)
    if not root.exists():
        return {}
    fonts: dict[int, Path] = {}
    for path in sorted(root.glob("*.zi")):
        try:
            font_id = int(path.stem)
        except ValueError:
            continue
        fonts.setdefault(font_id, path)
    return fonts


def extract_zi_fonts_from_hmi(raw: bytes, entries: Iterable[object]) -> dict[int, ZiFont]:
    fonts: dict[int, ZiFont] = {}
    for entry in entries:
        name = getattr(entry, "name", "")
        if not name.endswith(".zi"):
            continue
        try:
            font_id = int(name[:-3])
        except ValueError:
            continue
        if not getattr(entry, "in_file", False):
            continue
        start = int(getattr(entry, "data_offset"))
        length = int(getattr(entry, "length"))
        temp_path = f"<hmi:{name}>"
        try:
            fonts[font_id] = ZiFont.from_bytes(raw[start : start + length], temp_path)
        except ZiFontError:
            continue
    return fonts


def _shade_to_alpha(value: int) -> int:
    return max(0, min(255, (255 // 7) * value))
