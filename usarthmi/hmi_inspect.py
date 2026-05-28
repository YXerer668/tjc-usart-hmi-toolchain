from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re

ENTRY_NAME_SIZE = 16
ENTRY_SIZE = 28
MIN_ASCII_RUN = 2
OBJECT_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*\d+$")
PAGE_NAME_RE = re.compile(r"^page\d+$")
EVENT_HEADER_RE = re.compile(r"^(codes[A-Za-z0-9_]+)-(\d+)")

KNOWN_PA_PROPERTIES = {
    "aph",
    "bco",
    "bco1",
    "bco2",
    "bpic",
    "borderc",
    "borderw",
    "ch",
    "codesdown-0",
    "codesload-0",
    "codesloadend-0",
    "codesslide-0",
    "codestimer-0",
    "codesunload-0",
    "codesup-0",
    "dez",
    "dis",
    "drag",
    "down",
    "effect",
    "endx",
    "endy",
    "en",
    "first",
    "font",
    "format",
    "groupid0",
    "groupid1",
    "hig",
    "id",
    "isbr",
    "key",
    "left",
    "lockobj",
    "maxval",
    "minval",
    "mode",
    "movex",
    "movey",
    "objname",
    "path",
    "pco",
    "pco2",
    "pic",
    "pic1",
    "pic2",
    "picc",
    "picc1",
    "picc2",
    "ppic",
    "psta",
    "right",
    "sendkey",
    "spax",
    "spay",
    "sta",
    "style",
    "tim",
    "time",
    "type",
    "val",
    "vscope",
    "vvs0",
    "vvs1",
    "vvs2",
    "w",
    "wid",
    "x",
    "xcen",
    "y",
    "ycen",
}

SUMMARY_FIELD_NAMES = (
    "id",
    "x",
    "y",
    "w",
    "h",
    "sta",
    "style",
    "mode",
    "psta",
    "pic",
    "picc",
    "pic1",
    "picc1",
    "pic2",
    "picc2",
    "bpic",
    "ppic",
    "font",
    "bco",
    "bco1",
    "bco2",
    "pco",
    "pco2",
    "val",
    "maxval",
    "minval",
    "ch",
    "wid",
    "hig",
    "dis",
    "format",
    "up",
    "down",
    "left",
    "tim",
    "en",
    "dez",
    "txt",
    "txt_maxl",
    "path",
    "vvs0",
    "vvs1",
    "vvs2",
)


class HMIParseError(ValueError):
    """Raised when an HMI container cannot be parsed safely."""


@dataclass(slots=True)
class HMIEntry:
    index: int
    dir_offset: int
    name: str
    name_hex: str
    data_offset: int
    length: int
    field3: int
    in_file: bool

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["dir_offset_hex"] = f"0x{self.dir_offset:X}"
        data["data_offset_hex"] = f"0x{self.data_offset:08X}"
        data["field3_hex"] = f"0x{self.field3:08X}"
        return data


@dataclass(slots=True)
class PAString:
    offset: int
    text: str

    def to_dict(self) -> dict[str, object]:
        return {"offset": self.offset, "offset_hex": f"0x{self.offset:X}", "text": self.text}


@dataclass(slots=True)
class PAEventScript:
    raw_header: str
    name: str
    line_count: int
    lines: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "raw_header": self.raw_header,
            "name": self.name,
            "line_count": self.line_count,
            "lines": self.lines,
        }


@dataclass(slots=True)
class PABlockSummary:
    index: int
    attr_name: str
    type_code: str | None
    objname: str | None
    fields: dict[str, object]
    event_tokens: list[str]
    event_scripts: list[PAEventScript]

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "attr_name": self.attr_name,
            "type_code": self.type_code,
            "objname": self.objname,
            "fields": self.fields,
            "event_tokens": self.event_tokens,
            "event_scripts": [item.to_dict() for item in self.event_scripts],
        }


@dataclass(slots=True)
class PAPageSummary:
    entry_index: int
    entry_name: str
    page_index: int | None
    data_offset: int
    length: int
    parse_status: str
    parse_error: str | None
    strings: list[PAString]
    page_names: list[str]
    object_names: list[str]
    property_names: list[str]
    blocks: list[PABlockSummary]

    def to_dict(self) -> dict[str, object]:
        return {
            "entry_index": self.entry_index,
            "entry_name": self.entry_name,
            "page_index": self.page_index,
            "data_offset": self.data_offset,
            "data_offset_hex": f"0x{self.data_offset:08X}",
            "length": self.length,
            "parse_status": self.parse_status,
            "parse_error": self.parse_error,
            "strings": [item.to_dict() for item in self.strings],
            "page_names": self.page_names,
            "object_names": self.object_names,
            "property_names": self.property_names,
            "blocks": [item.to_dict() for item in self.blocks],
        }


@dataclass(slots=True)
class HMIInspection:
    path: Path
    entry_count: int
    entries: list[HMIEntry]
    program_text: str | None
    pa_strings: list[PAString]
    page_names: list[str]
    object_names: list[str]
    property_names: list[str]
    pa_blocks: list[PABlockSummary]
    pa_parse_error: str | None
    pa_pages: list[PAPageSummary]

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "entry_count": self.entry_count,
            "entries": [entry.to_dict() for entry in self.entries],
            "program_text": self.program_text,
            "pa_strings": [item.to_dict() for item in self.pa_strings],
            "page_names": self.page_names,
            "object_names": self.object_names,
            "property_names": self.property_names,
            "pa_blocks": [item.to_dict() for item in self.pa_blocks],
            "pa_parse_error": self.pa_parse_error,
            "pa_page_count": len(self.pa_pages),
            "pa_pages": [item.to_dict() for item in self.pa_pages],
        }


def inspect_hmi(path: str | Path) -> HMIInspection:
    file_path = Path(path).resolve()
    raw = file_path.read_bytes()
    if len(raw) < 4:
        raise HMIParseError("File is too small to be a USART HMI container")

    entry_count = int.from_bytes(raw[0:4], "little")
    directory_end = 4 + (entry_count * ENTRY_SIZE)
    if entry_count <= 0 or directory_end > len(raw):
        raise HMIParseError("Unsupported or corrupt HMI directory layout")

    entries = _parse_entries(raw, entry_count)
    resources = {
        entry.name: raw[entry.data_offset : entry.data_offset + entry.length]
        for entry in entries
        if entry.in_file
    }

    program_text = None
    if "Program.s" in resources:
        program_text = _decode_text(resources["Program.s"])

    pa_pages = [_summarize_pa_page(raw, entry) for entry in _pa_entries(entries) if entry.in_file]

    pa_strings: list[PAString] = []
    page_names: list[str] = []
    object_names: list[str] = []
    property_names: list[str] = []
    pa_blocks: list[PABlockSummary] = []
    pa_parse_error = None
    if "0.pa" in resources:
        primary_page = next((item for item in pa_pages if item.entry_name == "0.pa"), None)
        if primary_page is None:
            primary_page = _summarize_pa_data("0.pa", -1, 0, resources["0.pa"])
        pa_strings = primary_page.strings
        page_names = primary_page.page_names
        object_names = primary_page.object_names
        property_names = primary_page.property_names
        pa_blocks = primary_page.blocks
        pa_parse_error = primary_page.parse_error

    return HMIInspection(
        path=file_path,
        entry_count=entry_count,
        entries=entries,
        program_text=program_text,
        pa_strings=pa_strings,
        page_names=page_names,
        object_names=object_names,
        property_names=property_names,
        pa_blocks=pa_blocks,
        pa_parse_error=pa_parse_error,
        pa_pages=pa_pages,
    )


def extract_hmi(path: str | Path, out_dir: str | Path) -> list[Path]:
    file_path = Path(path).resolve()
    output_dir = Path(out_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    raw = file_path.read_bytes()
    inspection = inspect_hmi(file_path)
    written: list[Path] = []
    seen_names: set[str] = set()

    for entry in inspection.entries:
        if not entry.in_file or entry.length == 0:
            continue
        name = _safe_file_name(entry.name or f"entry_{entry.index}.bin")
        if name in seen_names:
            stem, dot, suffix = name.partition(".")
            name = f"{stem}_{entry.index}"
            if dot:
                name = f"{name}.{suffix}"
        seen_names.add(name)

        target = output_dir / name
        target.write_bytes(raw[entry.data_offset : entry.data_offset + entry.length])
        written.append(target)

        if entry.name == "Program.s":
            utf8_target = output_dir / "Program_utf8.txt"
            utf8_target.write_text(_decode_text(target.read_bytes()), encoding="utf-8")
            written.append(utf8_target)

    return written


def _parse_entries(raw: bytes, entry_count: int) -> list[HMIEntry]:
    entries: list[HMIEntry] = []
    for index in range(entry_count):
        base = 4 + index * ENTRY_SIZE
        name_bytes = raw[base : base + ENTRY_NAME_SIZE]
        data_offset = int.from_bytes(raw[base + 16 : base + 20], "little")
        length = int.from_bytes(raw[base + 20 : base + 24], "little")
        field3 = int.from_bytes(raw[base + 24 : base + 28], "little")
        in_file = data_offset + length <= len(raw)
        entries.append(
            HMIEntry(
                index=index,
                dir_offset=base,
                name=_decode_name(name_bytes),
                name_hex=name_bytes.hex(" "),
                data_offset=data_offset,
                length=length,
                field3=field3,
                in_file=in_file,
            )
        )
    return entries


def _pa_entries(entries: list[HMIEntry]) -> list[HMIEntry]:
    return sorted((entry for entry in entries if entry.name.endswith(".pa")), key=_pa_entry_sort_key)


def _pa_entry_sort_key(entry: HMIEntry) -> tuple[int, int | str, int]:
    stem = entry.name[:-3]
    if stem.isdigit():
        return (0, int(stem), entry.index)
    return (1, stem, entry.index)


def _decode_name(name_bytes: bytes) -> str:
    chars = []
    for value in name_bytes:
        if value == 0:
            break
        chars.append(chr(value) if 32 <= value <= 126 else "_")
    return "".join(chars).strip("_")


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "gbk"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")


def _extract_ascii_runs(data: bytes, min_length: int = MIN_ASCII_RUN) -> list[PAString]:
    runs: list[PAString] = []
    start = -1
    for index, value in enumerate(data):
        printable = 32 <= value <= 126 or value == 9
        if printable and start < 0:
            start = index
        if not printable and start >= 0:
            if index - start >= min_length:
                text = data[start:index].decode("ascii", errors="ignore")
                runs.append(PAString(offset=start, text=text))
            start = -1
    if start >= 0 and len(data) - start >= min_length:
        runs.append(PAString(offset=start, text=data[start:].decode("ascii", errors="ignore")))
    return runs


def _summarize_pa_page(raw: bytes, entry: HMIEntry) -> PAPageSummary:
    data = raw[entry.data_offset : entry.data_offset + entry.length]
    return _summarize_pa_data(entry.name, entry.index, entry.data_offset, data)


def _summarize_pa_data(entry_name: str, entry_index: int, data_offset: int, data: bytes) -> PAPageSummary:
    strings = _extract_ascii_runs(data)
    page_names = sorted({item.text for item in strings if PAGE_NAME_RE.match(item.text)})
    property_names = sorted({item.text for item in strings if item.text in KNOWN_PA_PROPERTIES})
    object_names = sorted(
        {
            item.text
            for item in strings
            if OBJECT_NAME_RE.match(item.text)
            and item.text not in KNOWN_PA_PROPERTIES
            and not PAGE_NAME_RE.match(item.text)
        }
    )
    page_index = _pa_page_index(entry_name)
    parse_error = None
    blocks: list[PABlockSummary] = []
    parse_status = "ok"
    try:
        blocks = _summarize_pa_blocks(data)
    except ValueError as exc:
        parse_status = "error"
        parse_error = str(exc)

    return PAPageSummary(
        entry_index=entry_index,
        entry_name=entry_name,
        page_index=page_index,
        data_offset=data_offset,
        length=len(data),
        parse_status=parse_status,
        parse_error=parse_error,
        strings=strings,
        page_names=page_names,
        object_names=object_names,
        property_names=property_names,
        blocks=blocks,
    )


def _pa_page_index(entry_name: str) -> int | None:
    stem = entry_name[:-3]
    if stem.isdigit():
        return int(stem)
    return None


def _summarize_pa_blocks(data: bytes) -> list[PABlockSummary]:
    from .page_format import parse_page_data

    page = parse_page_data(data)
    summaries: list[PABlockSummary] = []
    for index, block in enumerate(page.blocks):
        fields = {name: value for name in SUMMARY_FIELD_NAMES if (value := _field_value(block, name)) is not None}
        summaries.append(
            PABlockSummary(
                index=index,
                attr_name=block.attr_name,
                type_code=block.type_code,
                objname=block.objname,
                fields=fields,
                event_tokens=list(block.event_tokens),
                event_scripts=_event_scripts(block.event_tokens),
            )
        )
    return summaries


def _field_value(block, name: str) -> object | None:
    field = block.get_field(name)
    if field is None:
        return None
    if name == "txt":
        return _decode_text(field.value).rstrip("\x00")
    if 0 < len(field.value) <= 4:
        return int.from_bytes(field.value, "little", signed=False)
    if not field.value:
        return 0
    return field.value.hex(" ")


def _event_scripts(tokens: list[str]) -> list[PAEventScript]:
    scripts: list[PAEventScript] = []
    cursor = 0
    while cursor < len(tokens):
        raw_header = tokens[cursor]
        cursor += 1
        match = EVENT_HEADER_RE.match(raw_header.strip())
        if match is None:
            continue
        line_count = int(match.group(2))
        lines = tokens[cursor : cursor + line_count]
        cursor += line_count
        scripts.append(
            PAEventScript(
                raw_header=raw_header,
                name=match.group(1),
                line_count=line_count,
                lines=lines,
            )
        )
    return scripts


def _safe_file_name(name: str) -> str:
    safe_chars = []
    for char in name:
        if char.isalnum() or char in {".", "-", "_"}:
            safe_chars.append(char)
        else:
            safe_chars.append("_")
    safe = "".join(safe_chars).strip("_")
    return safe or "entry.bin"
