from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

HEADER_SIZE = 0x38
EVENT_PREFIXES = (
    "codesdown-",
    "codesup-",
    "codesload-",
    "codesloadend-",
    "codesunload-",
    "codestimer-",
    "codesslide-",
)
KNOWN_FIELDS = {
    "type",
    "id",
    "objname",
    "vscope",
    "drag",
    "disup",
    "sendkey",
    "aph",
    "movex",
    "movey",
    "x",
    "y",
    "w",
    "h",
    "endx",
    "endy",
    "effect",
    "first",
    "time",
    "lockobj",
    "sta",
    "style",
    "borderc",
    "borderw",
    "font",
    "pic",
    "picc",
    "bco",
    "pic2",
    "picc2",
    "bco2",
    "pco",
    "pco2",
    "xcen",
    "ycen",
    "val",
    "txt",
    "txt_maxl",
    "isbr",
    "spax",
    "spay",
    "newtxt",
    "pw",
    "key",
    "up",
    "down",
    "left",
    "right",
    "groupid0",
    "groupid1",
    "vvs0",
    "vvs1",
}
FIELD_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


@dataclass(slots=True)
class BlockField:
    name: str
    value: bytes
    marker: int | None

    def clone(self) -> "BlockField":
        return BlockField(self.name, bytes(self.value), self.marker)


@dataclass(slots=True)
class PageBlock:
    attr_name: str
    attr_marker: int
    fields: list[BlockField]
    event_tokens: list[str]

    def clone(self) -> "PageBlock":
        return PageBlock(
            attr_name=self.attr_name,
            attr_marker=self.attr_marker,
            fields=[field.clone() for field in self.fields],
            event_tokens=list(self.event_tokens),
        )

    @property
    def type_code(self) -> str | None:
        field = self.get_field("type")
        if field is None or not field.value:
            return None
        return field.value.decode("ascii", errors="ignore")

    @property
    def objname(self) -> str | None:
        field = self.get_field("objname")
        if field is None:
            return None
        return field.value.decode("ascii", errors="ignore")

    def get_field(self, name: str) -> BlockField | None:
        for field in self.fields:
            if field.name == name:
                return field
        return None

    def set_string(self, name: str, value: str, encoding: str = "ascii") -> None:
        encoded = value.encode(encoding, errors="ignore")
        field = self.get_field(name)
        if field is None:
            self._append_field(name, encoded, 0)
            return
        field.value = encoded

    def set_int(self, name: str, value: int, width: int | None = None, marker: int = 0x12) -> None:
        field = self.get_field(name)
        if field is None:
            size = width or 2
            self._append_field(name, int(value).to_bytes(size, "little", signed=False), marker)
            return
        size = width or max(1, len(field.value))
        field.value = int(value).to_bytes(size, "little", signed=False)

    def set_event(self, name_prefix: str, lines: list[str]) -> None:
        events = _parse_event_specs(self.event_tokens)
        replaced = False
        for index, (event_name, _) in enumerate(events):
            if event_name.startswith(name_prefix):
                events[index] = (f"{name_prefix}{len(lines)}", list(lines))
                replaced = True
                break
        if not replaced:
            events.append((f"{name_prefix}{len(lines)}", list(lines)))
        self.event_tokens = _build_event_tokens(events)

    def serialize(self) -> bytes:
        parts = [
            len(self.attr_name).to_bytes(4, "little"),
            self.attr_name.encode("ascii"),
        ]
        for field in self.fields:
            name_bytes = field.name.encode("ascii")
            if len(name_bytes) > 16:
                raise ValueError(f"Field name too long: {field.name}")
            chunk = name_bytes.ljust(16, b"\x00") + field.value
            parts.append(len(chunk).to_bytes(4, "little"))
            parts.append(chunk)

        for token in self.event_tokens:
            encoded = _encode_event_token(token)
            parts.append(len(encoded).to_bytes(4, "little"))
            parts.append(encoded)
        parts.append((0).to_bytes(4, "little"))
        return b"".join(parts)

    def _append_field(self, name: str, value: bytes, marker: int) -> None:
        self.fields.append(BlockField(name=name, value=value, marker=None))


@dataclass(slots=True)
class PageFile:
    magic: int
    total_length: int
    object_count: int
    header_bytes: bytes
    page_name: str
    blocks: list[PageBlock]

    def serialize(self) -> bytes:
        block_bytes = [block.serialize() for block in self.blocks]
        table_size = len(block_bytes) * 12
        rel_offsets = []
        cursor = table_size
        for payload in block_bytes:
            rel_offsets.append((cursor, len(payload), 0))
            cursor += len(payload)

        header = bytearray(self.header_bytes[:HEADER_SIZE])
        header[0x04:0x08] = (HEADER_SIZE + table_size + sum(len(item) for item in block_bytes)).to_bytes(4, "little")
        header[0x0C:0x10] = len(block_bytes).to_bytes(4, "little")
        header[0x18:0x28] = self.page_name.encode("ascii")[:16].ljust(16, b"\x00")

        table = bytearray()
        for rel_offset, block_length, unknown in rel_offsets:
            table.extend(rel_offset.to_bytes(4, "little"))
            table.extend(block_length.to_bytes(4, "little"))
            table.extend(unknown.to_bytes(4, "little"))
        return bytes(header + table + b"".join(block_bytes))

    def parsed_end_offset(self) -> int:
        return HEADER_SIZE + (len(self.blocks) * 12) + sum(len(block.serialize()) for block in self.blocks)

    def trailing_tail(self, original_bytes: bytes) -> bytes:
        end = self.parsed_end_offset()
        return original_bytes[end:]

    def raw_block_bounds(self, original_bytes: bytes) -> tuple[int, int]:
        if not self.blocks:
            table_end = HEADER_SIZE + (self.object_count * 12)
            return table_end, table_end
        first_start = None
        last_end = None
        for index in range(self.object_count):
            base = HEADER_SIZE + index * 12
            rel_offset = int.from_bytes(original_bytes[base : base + 4], "little")
            block_length = int.from_bytes(original_bytes[base + 4 : base + 8], "little")
            block_start = HEADER_SIZE + rel_offset
            block_end = block_start + block_length
            if first_start is None or block_start < first_start:
                first_start = block_start
            if last_end is None or block_end > last_end:
                last_end = block_end
        assert first_start is not None and last_end is not None
        return first_start, last_end

    def hidden_gap_after_table(self, original_bytes: bytes) -> bytes:
        table_end = HEADER_SIZE + (self.object_count * 12)
        first_start, _ = self.raw_block_bounds(original_bytes)
        return original_bytes[table_end:first_start]

    def post_block_tail(self, original_bytes: bytes) -> bytes:
        _, last_end = self.raw_block_bounds(original_bytes)
        return original_bytes[last_end:]


def parse_page_data(data: bytes) -> PageFile:
    if len(data) < HEADER_SIZE:
        raise ValueError("Page data is too short")
    total_length = int.from_bytes(data[0x04:0x08], "little")
    object_count = int.from_bytes(data[0x0C:0x10], "little")
    page_name = data[0x18:0x28].split(b"\x00", 1)[0].decode("ascii", errors="ignore")
    blocks = []
    table_start = HEADER_SIZE
    for index in range(object_count):
        base = table_start + index * 12
        rel_offset = int.from_bytes(data[base : base + 4], "little")
        block_length = int.from_bytes(data[base + 4 : base + 8], "little")
        block_start = HEADER_SIZE + rel_offset
        block_end = block_start + block_length
        blocks.append(parse_block_bytes(data[block_start:block_end]))
    return PageFile(
        magic=int.from_bytes(data[0x00:0x04], "little"),
        total_length=total_length,
        object_count=object_count,
        header_bytes=data[:HEADER_SIZE],
        page_name=page_name,
        blocks=blocks,
    )


def parse_block_bytes(block: bytes) -> PageBlock:
    attr_len = int.from_bytes(block[:4], "little")
    attr_name = block[4 : 4 + attr_len].decode("ascii", errors="ignore")
    cursor = 4 + attr_len

    fields: list[BlockField] = []
    event_tokens: list[str] = []
    event_mode = False
    while cursor < len(block):
        if cursor + 4 > len(block):
            raise ValueError(f"Truncated chunk header in block {attr_name!r} at offset {cursor}")
        chunk_len = int.from_bytes(block[cursor : cursor + 4], "little")
        cursor += 4
        if chunk_len == 0:
            if cursor != len(block):
                raise ValueError(f"Unexpected bytes after block terminator in {attr_name!r}")
            break
        if cursor + chunk_len > len(block):
            raise ValueError(f"Chunk overruns block {attr_name!r} at offset {cursor}")
        chunk = block[cursor : cursor + chunk_len]
        cursor += chunk_len

        if not event_mode and chunk_len >= 16:
            field_name = _decode_field_name_chunk(chunk[:16])
            if field_name is not None:
                fields.append(BlockField(name=field_name, value=chunk[16:], marker=None))
                continue

        text = _decode_event_token(chunk)
        if text is None:
            raise ValueError(f"Unable to parse chunk in block {attr_name!r} at offset {cursor - chunk_len}")
        event_mode = True
        event_tokens.append(text)

    return PageBlock(
        attr_name=attr_name,
        attr_marker=0,
        fields=fields,
        event_tokens=event_tokens,
    )


def load_page_file(path: str | Path) -> PageFile:
    return parse_page_data(Path(path).read_bytes())


def page_parsed_end_offset(page: PageFile) -> int:
    return page.parsed_end_offset()


def page_trailing_tail(page_data: bytes) -> bytes:
    page = parse_page_data(page_data)
    return page.trailing_tail(page_data)


def page_raw_block_bounds(page_data: bytes) -> tuple[int, int]:
    page = parse_page_data(page_data)
    return page.raw_block_bounds(page_data)


def page_hidden_gap_after_table(page_data: bytes) -> bytes:
    page = parse_page_data(page_data)
    return page.hidden_gap_after_table(page_data)


def page_post_block_tail(page_data: bytes) -> bytes:
    page = parse_page_data(page_data)
    return page.post_block_tail(page_data)


def find_first_block(page: PageFile, type_code: str) -> PageBlock:
    for block in page.blocks:
        if block.type_code == type_code:
            return block
    raise KeyError(f"No block of type '{type_code}' found")


def find_block_by_objname(page: PageFile, objname: str) -> PageBlock:
    for block in page.blocks:
        if block.objname == objname:
            return block
    raise KeyError(f"No block named '{objname}' found")


def _decode_field_name_chunk(chunk: bytes) -> str | None:
    if len(chunk) < 16 or chunk[0] == 0:
        return None
    end = 16
    for index, value in enumerate(chunk):
        if value == 0:
            end = index
            if any(item != 0 for item in chunk[index:]):
                return None
            break
    try:
        text = chunk[:end].decode("ascii")
    except UnicodeDecodeError:
        return None
    if text in KNOWN_FIELDS or text.startswith(EVENT_PREFIXES):
        return text
    if FIELD_NAME_RE.match(text):
        return text
    return None


def _find_field_end(
    block: bytes,
    value_start: int,
) -> tuple[str, int, int | None, list[str] | None] | None:
    for value_end in range(value_start, len(block) + 1):
        events = _parse_event_section(block[value_end:])
        if events is not None:
            return ("event", value_end, None, events)

        if value_end + 4 <= len(block):
            marker = int.from_bytes(block[value_end : value_end + 4], "little")
            if marker <= 0x40:
                next_name = _decode_field_name_chunk(block[value_end + 4 : value_end + 20])
                if next_name is not None:
                    return ("marker", value_end, marker, None)
    return None


def _parse_event_section(data: bytes) -> list[str] | None:
    cursor = 0
    tokens: list[str] = []
    while cursor + 4 <= len(data):
        length = int.from_bytes(data[cursor : cursor + 4], "little")
        cursor += 4
        if length == 0:
            return tokens if cursor == len(data) else None
        if cursor + length > len(data):
            return None
        payload = data[cursor : cursor + length]
        text = _decode_event_token(payload)
        if text is None:
            return None
        tokens.append(text)
        cursor += length
    return None


def _decode_event_token(data: bytes) -> str | None:
    if not _is_text_like(data):
        return None
    for encoding in ("ascii", "utf-8", "gbk"):
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        if _is_printable_text(text):
            return text
    return None


def _encode_event_token(text: str) -> bytes:
    for encoding in ("ascii", "gbk", "utf-8"):
        try:
            return text.encode(encoding)
        except UnicodeEncodeError:
            continue
    return text.encode("gbk", errors="ignore")


def _is_text_like(data: bytes) -> bool:
    return all(value >= 32 or value in {9, 10, 13} for value in data)


def _is_printable_text(text: str) -> bool:
    return all(char.isprintable() or char in "\t\r\n" for char in text)


def _parse_event_specs(tokens: list[str]) -> list[tuple[str, list[str]]]:
    specs: list[tuple[str, list[str]]] = []
    cursor = 0
    while cursor < len(tokens):
        name = tokens[cursor]
        cursor += 1
        if not name.startswith(EVENT_PREFIXES):
            continue
        try:
            line_count = int(name.rsplit("-", 1)[1])
        except (IndexError, ValueError):
            line_count = 0
        lines = tokens[cursor : cursor + line_count]
        cursor += line_count
        specs.append((name, lines))
    return specs


def _build_event_tokens(specs: list[tuple[str, list[str]]]) -> list[str]:
    tokens: list[str] = []
    for name, lines in specs:
        tokens.append(name)
        tokens.extend(lines)
    return tokens
