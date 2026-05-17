from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
import re
from typing import Any

from .object_hash import object_name_hash
from .hmi_inspect import inspect_hmi
from .page_format import PageBlock, load_page_file, parse_page_data
from .tft_checksum import _crc32_like, update_tft_checksum
from .tft_reverse import reverse_tft_tail
from .tft_toolchain import TftToolchainError, _load_tfttool_module, inspect_tft


COORD_FIELDS = ("x", "y", "w", "h", "endx", "endy")
TYPE_RECORD_LENGTHS = {
    "y": 0x40,
    "t": 0x54,
    "b": 0x54,
    "p": 0x3C,
    "\x02": 0x68,  # GMOV animation
    "\x03": 0x68,  # video
    "\x04": 0x68,  # audio
    "\x05": 0x24,  # touch capture
    "<": 0x44,  # external picture / SD image
    "\x00": 0x5C,  # waveform
    ";": 0x50,  # virtual float / xfloat
    "=": 0x90,  # combo box
    "4": 0x10,  # variable
    "5": 0x58,  # dual-state button
    "6": 0x54,  # number
    "7": 0x60,  # scrolling text
    "8": 0x48,  # checkbox
    "9": 0x40,  # radio
    "\x01": 0x54,  # slider
    "3": 0x24,  # timer
    "C": 0x50,  # state button
    "m": 0x3C,  # hotspot/touch area
    "q": 0x44,  # crop image
    "z": 0x50,  # gauge
    "j": 0x40,  # progress bar
    ":": 0x48,  # QR code
}
TYPE_USER_SLOT_COUNTS = {
    "y": 33,
    "t": 41,
    "b": 42,
    "p": 28,
    "\x02": 39,
    "\x03": 38,
    "\x04": 20,
    "\x05": 10,
    "<": 29,
    "\x00": 41,
    ";": 39,
    "=": 57,
    "4": 11,
    "5": 42,
    "6": 41,
    "7": 48,
    "8": 31,
    "9": 30,
    "\x01": 40,
    "3": 11,
    "C": 38,
    "m": 27,
    "q": 30,
    "z": 40,
    "j": 33,
    ":": 33,
}
SUPPORTED_PAGE1_BUTTON_EVENT_LINES = frozenset({"page 0", "page 1", "page page0", "page page1"})
TEXT_POINTER_RECORD_OFFSETS = {
    "t": 0x48,
    "b": 0x4C,
    "5": 0x4C,
    "7": 0x4C,
    "C": 0x48,
    ":": 0x44,
}
KNOWN_EXTRA_TYPE_CASES = {
    "\x02": "case_47_gmov",
    "\x03": "case_48_video",
    "\x04": "case_49_audio",
    "\x00": "case_27_waveform_basic",
    ";": "case_36_xfloat",
    "=": "case_37_combobox",
    "4": "case_26_variable_numeric_string",
    "5": "case_23_dual_state_button",
    "6": "case_16_number_basic",
    "7": "case_22_scrolling_text",
    "8": "case_28_checkbox",
    "9": "case_29_radio",
    "\x01": "case_17_slider",
    "z": "case_18_gauge",
    "3": "case_19_timer",
    "C": "case_24_state_button",
    "m": "case_25_hotspot_touch_area",
    "q": "case_30_crop_image",
    "\x05": "case_45_touchcap_current_gui",
    "<": "case_46_expicture_current_gui",
    "j": "case_20_progress",
    ":": "case_21_qrcode",
}
DEFAULT_CASE_ROOT = Path(r"C:\Users\SinYu\Desktop\case_for_codex")
IMAGE_BUTTON_USER_SLOT_COUNT = 41
MIRROR_VALUE_COUNT = 41
IMAGE_BUTTON_MIRROR_VALUE_COUNT = 42
IMAGE_BUTTON_MIRROR_EXTRA_INDEX = 17
IMAGE_BUTTON_PREFIX_INSERT_OFFSET = 0x86
IMAGE_BUTTON_PREFIX_INSERT = bytes.fromhex("92 48 C9 76")
PREFIX_DESCRIPTOR_START = 0x3E
PREFIX_SYSTEM_EVENT_LAYOUT_SIZE = 0x5F
TIMER_TYPE_CODE = "3"
VARIABLE_TYPE_CODE = "4"
MEDIA_TYPE_CODES = {"\x02", "\x03", "\x04"}
NON_VISUAL_COORD_TYPES = {TIMER_TYPE_CODE, VARIABLE_TYPE_CODE, "\x04", "\x05"}
COMPACT_STRING_LAYOUT_TYPES = {TIMER_TYPE_CODE, "\x05", "<", "5", "6", "7", "8", "C", "m", "q", "="}
MIXED_COMPACT_PRIMARY_TYPES = {"5", "6", "7", "8", "m", "q"}
MIXED_DESCRIPTOR_LAYOUT_KEY = "__mixed__"
TIMER_AUTORUN_DESCRIPTOR_LAYOUT_KEY = "__timer_autorun__"
OFFICIAL_MIXED_DESCRIPTOR_LAYOUTS = {
    MIXED_DESCRIPTOR_LAYOUT_KEY: "case_33_all_controls_mixed_stress",
    TIMER_AUTORUN_DESCRIPTOR_LAYOUT_KEY: "case_32_timer_autorun_witness",
}
TYPE_RECORD_HEADER_FLAGS = {
    "\x04": 0x27,
    "\x05": 0x27,
    TIMER_TYPE_CODE: 0x27,
    VARIABLE_TYPE_CODE: 0x07,
}
EVENT_FIELD_USER_SLOTS = {
    "\x02": {
        "vid": 20,
        "en": 23,
        "loop": 24,
        "dis": 25,
    },
    "\x03": {
        "vid": 20,
        "en": 21,
        "loop": 22,
        "fps": 23,
        "dis": 24,
    },
    "\x04": {
        "vid": 8,
        "en": 9,
        "loop": 10,
        "fps": 11,
        "dis": 12,
    },
    # Recovered from official timer-control TFTs:
    #   tm0.en=1  -> 01 <slot_start+8> 00 00 00 3d 31
    #   n0.val++  -> 01 <slot_start+27> 00 00 00 2b 2b
    TIMER_TYPE_CODE: {
        "tim": 7,
        "en": 8,
    },
    "6": {
        "val": 27,
    },
    ";": {
        "val": 27,
        "vvs0": 28,
        "vvs1": 29,
    },
}
EVENT_ASSIGN_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(-?\d+)\s*$")
EVENT_UNARY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)(\+\+|--)\s*$")
EVENT_PRINTH_HEX_RE = re.compile(r"^printh\s+[0-9A-Fa-f]{2}(?:\s+[0-9A-Fa-f]{2})*\s*$")
EVENT_CLICK_RE = re.compile(r"^click\s+([A-Za-z_][A-Za-z0-9_]*),([01])\s*$", flags=re.IGNORECASE)
EVENT_VIS_RE = re.compile(r"^vis\s+([A-Za-z_][A-Za-z0-9_]*),([01])\s*$", flags=re.IGNORECASE)
EVENT_TSW_RE = re.compile(r"^tsw\s+([A-Za-z_][A-Za-z0-9_]*|255),([01])\s*$", flags=re.IGNORECASE)
EVENT_REF_RE = re.compile(r"^ref\s+([A-Za-z_][A-Za-z0-9_]*)\s*$", flags=re.IGNORECASE)


def is_supported_page1_button_event_line(line: str) -> bool:
    """Return whether a page1 button event is inside the conservative V1 allow-list."""
    stripped = line.strip()
    normalized = stripped.lower()
    if normalized in SUPPORTED_PAGE1_BUTTON_EVENT_LINES:
        return True
    if EVENT_PRINTH_HEX_RE.match(stripped) is not None:
        return True
    return EVENT_ASSIGN_RE.match(normalized) is not None or EVENT_UNARY_RE.match(normalized) is not None


def is_page1_printh_probe_event_line(line: str) -> bool:
    """Return whether an event line is an explicit hex-only printh probe."""
    return EVENT_PRINTH_HEX_RE.match(line.strip()) is not None


def is_page1_fixed_printh_probe_event_line(line: str, *, byte_count: int = 4) -> bool:
    """Return whether an event line is a fixed-size explicit hex printh probe."""
    stripped = line.strip()
    if EVENT_PRINTH_HEX_RE.match(stripped) is None:
        return False
    return len(stripped.split()) == byte_count + 1


def parse_page1_button_click_event_line(line: str) -> tuple[str, int] | None:
    """Parse the deliberately tiny page1 click allow-list shape."""
    match = EVENT_CLICK_RE.match(line.strip())
    if match is None:
        return None
    return match.group(1), int(match.group(2))


def parse_page1_button_vis_event_line(line: str) -> tuple[str, int] | None:
    """Parse the deliberately tiny page1 vis allow-list shape."""
    match = EVENT_VIS_RE.match(line.strip())
    if match is None:
        return None
    return match.group(1), int(match.group(2))


def parse_page1_button_tsw_event_line(line: str) -> tuple[str, int] | None:
    """Parse the deliberately tiny page1 tsw allow-list shape."""
    match = EVENT_TSW_RE.match(line.strip())
    if match is None:
        return None
    return match.group(1), int(match.group(2))


def parse_page1_button_ref_event_line(line: str) -> str | None:
    """Parse the deliberately tiny page1 ref allow-list shape."""
    match = EVENT_REF_RE.match(line.strip())
    if match is None:
        return None
    return match.group(1)


IMAGE_BUTTON_MIRROR_RELATIVE_VALUES = (
    9,
    10,
    23,
    None,
    4,
    None,
    None,
    None,
    None,
    None,
    11,
    12,
    26,
    None,
    19,
    None,
    None,
    22,
    30,
    None,
    24,
    None,
    3,
    20,
    32,
    None,
    None,
    6,
    31,
    None,
    15,
    13,
    27,
    28,
    14,
    29,
    25,
    None,
    1,
    21,
    None,
    0,
)
HEADER1_FILE_SIZE_OFFSET = 0x3C
HEADER1_CRC_OFFSET = 0xC4
HEADER2_START = 0xC8
HEADER2_CRC_OFFSET = HEADER2_START + 0xC4
HEADER2_FIELD_OFFSETS = {
    "static_usercode_address": 0x00,
    "app_attributes_data_address": 0x04,
    "usercode_address": 0x0C,
    "pictures_address": 0x18,
    "gmovs_address": 0x1C,
    "image_button_prefix_count": 0x34,
    "videos_count": 0x38,
    # TFTTool labels this as audios_count, but these local TJC 1.67.6
    # fixtures use it as the page object count.
    "compiled_object_count": 0x3A,
}


@dataclass(slots=True)
class BasicPatchResult:
    baseline_tft: str
    baseline_pa: str
    target_pa: str
    out_tft: str
    file_size: int
    checksum_mode: str
    patched_coordinates: int
    patched_text_slots: int
    final_word_note: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": "experimental_basic_tft_patch",
            "baseline_tft": self.baseline_tft,
            "baseline_pa": self.baseline_pa,
            "target_pa": self.target_pa,
            "out_tft": self.out_tft,
            "file_size": self.file_size,
            "checksum_mode": self.checksum_mode,
            "patched_coordinates": self.patched_coordinates,
            "patched_text_slots": self.patched_text_slots,
            "final_word_note": self.final_word_note,
            "warnings": [
                "V0 only supports unchanged object count/type/order.",
                "V0 patches coordinate sequences and fixed-size text slots in an official baseline TFT.",
                "The final 4-byte TFT checksum is recomputed, but the object-tail generator is still limited to same-layout patches.",
            ],
        }


@dataclass(slots=True)
class AddedObjectPatchResult:
    baseline_tft: str
    baseline_pa: str
    target_pa: str
    out_tft: str
    file_size: int
    object_count: int
    added_objects: list[dict[str, Any]]
    section_offsets: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        added_object = self.added_objects[0] if len(self.added_objects) == 1 else None
        added_names = [item["name"] for item in self.added_objects]
        added_types = [item["type"] for item in self.added_objects]
        return {
            "mode": "experimental_added_objects_tft_patch",
            "baseline_tft": self.baseline_tft,
            "baseline_pa": self.baseline_pa,
            "target_pa": self.target_pa,
            "out_tft": self.out_tft,
            "file_size": self.file_size,
            "object_count": self.object_count,
            "added_count": len(self.added_objects),
            "added_objects": self.added_objects,
            "added_names": added_names,
            "added_types": added_types,
            "added_object": added_object["name"] if added_object else "",
            "added_type": added_object["type"] if added_object else "",
            "section_offsets": {
                key: {"value": value, "hex": f"0x{value:X}"}
                for key, value in self.section_offsets.items()
            },
            "warnings": [
                "Experimental V1 supports appending one or more known object records to the current seed layout.",
                "Object-name hashes are generated with the recovered 14-byte padded Nextion/TJC CRC32 algorithm.",
                "Header CRCs, encrypted Header2 fields, and the final TFT checksum are recomputed.",
            ],
        }


@dataclass(slots=True)
class RebuildPagePatchResult:
    baseline_tft: str
    seed_pa: str
    target_pa: str
    out_tft: str
    file_size: int
    object_count: int
    objects: list[dict[str, Any]]
    removed_seed_objects: list[str]
    section_offsets: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": "experimental_clean_page_tft_rebuild",
            "baseline_tft": self.baseline_tft,
            "seed_pa": self.seed_pa,
            "target_pa": self.target_pa,
            "out_tft": self.out_tft,
            "file_size": self.file_size,
            "object_count": self.object_count,
            "objects": self.objects,
            "removed_seed_objects": self.removed_seed_objects,
            "section_offsets": {
                key: {"value": value, "hex": f"0x{value:X}"}
                for key, value in self.section_offsets.items()
            },
            "warnings": [
                "Experimental clean rebuild: the baseline TFT is used only as a binary shell and template source.",
                "The target page object/hash/user/mirror tail is rebuilt from target_pa, so omitted seed objects are not intentionally kept.",
                "This still depends on recovered templates for each object type; validate with checksum, serial get tests, and camera capture.",
            ],
        }


@dataclass(slots=True)
class MultiPagePatchResult:
    baseline_tft: str
    baseline_pa: str
    target_pages: list[str]
    out_tft: str
    file_size: int
    page_count: int
    object_count: int
    section_offsets: dict[str, int]
    experimental_events: bool = False
    experimental_event_summary: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        warnings = [
            "Experimental multi-page V1 supports the official case31 page-order layout.",
            "Non-seed-page controls are limited to text/button/number/progress/slider/gauge.",
            "Do not use this yet for arbitrary page events, timers, resources, waveform, or arbitrary multi-page layouts.",
        ]
        if self.experimental_events:
            warnings.append(
                "Page1 experimental events are opt-in; page1 button events are live-proven, while page1 load printh probes are compile/probe-only until the extra-page load scheduler is recovered."
            )
        event_summary = self.experimental_event_summary or {
            "page1_page_events": [],
            "page1_object_events": [],
        }
        if event_summary.get("page1_page_events"):
            warnings.append(
                "Page1 page-level events are compile-only: bytecode is emitted, but the extra-page load scheduler callback is not recovered."
            )
        return {
            "mode": "experimental_multi_page_tft_patch",
            "baseline_tft": self.baseline_tft,
            "baseline_pa": self.baseline_pa,
            "target_pages": self.target_pages,
            "out_tft": self.out_tft,
            "file_size": self.file_size,
            "page_count": self.page_count,
            "object_count": self.object_count,
            "experimental_events": self.experimental_events,
            "experimental_event_summary": event_summary,
            "section_offsets": {
                key: {"value": value, "hex": f"0x{value:X}"}
                for key, value in self.section_offsets.items()
            },
            "warnings": warnings,
        }


@dataclass(slots=True)
class _UserRecordTemplate:
    slot_index: int
    word1_mode: str
    word1_delta: int
    word2: int
    word3: int
    word4: int
    word5: int


@dataclass(slots=True)
class _TailSeed:
    baseline_tft: Path
    baseline_pa: Path
    raw: bytes
    object_start: int
    model: str
    model_series: int
    prefix_head: bytes
    page_event: bytes
    object_event: bytes
    compiled_prefix: bytes
    prefix_inserts: dict[str, list[tuple[int, bytes]]]
    user_header: bytes
    primary_templates: dict[str, bytes]
    user_templates: dict[str, list[_UserRecordTemplate]]
    mirror_templates: dict[str, list[int | None]]
    mirror_layout_templates: dict[str, dict[str, list[int | None]]]
    mirror_descriptor_sequences: dict[str, list[bytes]]
    primary_final_markers: dict[str, bytes]
    primary_string_prefix_paddings: dict[str, int]
    primary_string_suffix_paddings: dict[str, int]
    hash_by_name: dict[str, int]


@dataclass(slots=True)
class _EventLayout:
    data: bytes
    offsets: list[int]
    callbacks: list[dict[str, int]]


@dataclass(slots=True)
class _EventCompileContext:
    field_slot_by_ref: dict[tuple[str, str], int]


def patch_basic_tft(
    baseline_tft: str | Path,
    *,
    baseline_pa: str | Path,
    target_pa: str | Path,
    out_tft: str | Path,
    checksum_mode: str = "recompute",
) -> BasicPatchResult:
    """Patch a same-layout TFT using target .pa coordinates and text.

    This is a deliberately narrow V0 writer. It proves and automates the fields
    we have already reversed, without pretending the full compiler is complete.
    """

    if checksum_mode not in {"recompute", "keep", "zero"}:
        raise TftToolchainError("checksum_mode must be 'recompute', 'keep', or 'zero'")

    baseline_tft_path = Path(baseline_tft).resolve()
    baseline_pa_path = Path(baseline_pa).resolve()
    target_pa_path = Path(target_pa).resolve()
    out_path = Path(out_tft).resolve()

    baseline_page = load_page_file(baseline_pa_path)
    target_page = load_page_file(target_pa_path)
    _validate_same_layout(baseline_page.blocks, target_page.blocks)

    payload = bytearray(baseline_tft_path.read_bytes())
    inspection = inspect_tft(baseline_tft_path)
    header1 = _header(inspection, "Header1")
    header2 = _header(inspection, "Header2")
    model_series = _header_int(header1, "model_series")
    object_start = _header_int(header2, "unknown_objects_address")
    if object_start is None:
        raise TftToolchainError("Unable to locate unknown_objects_address in baseline TFT")
    if model_series is None:
        raise TftToolchainError("Unable to locate model_series in baseline TFT")
    tail = memoryview(payload)[object_start:]

    patched_coordinates = 0
    for base_block, target_block in zip(baseline_page.blocks, target_page.blocks):
        old_coords = _coord_payload(base_block)
        new_coords = _coord_payload(target_block)
        if old_coords == new_coords:
            continue
        patched_coordinates += _replace_all(tail, old_coords, new_coords)

    reverse = reverse_tft_tail(baseline_tft_path, hmi_pa_path=baseline_pa_path)
    block_reverse = {
        item.get("objname"): item
        for item in (reverse.get("hmi_page", {}).get("blocks", []))
    }

    patched_text_slots = 0
    target_by_name = {block.objname: block for block in target_page.blocks}
    for base_block in baseline_page.blocks:
        objname = base_block.objname
        if objname is None:
            continue
        base_text = _field_text(base_block, "txt")
        target_text = _field_text(target_by_name[objname], "txt")
        if base_text is None or target_text is None or base_text == target_text:
            continue
        text_offset = _compiled_text_offset(block_reverse.get(objname))
        if text_offset is None:
            raise TftToolchainError(f"Unable to locate compiled text slot for {objname}")
        slot_len = _text_slot_len(base_block)
        encoded = _encode_display_text(target_text)
        if len(encoded) > slot_len:
            raise TftToolchainError(
                f"Target text for {objname} is {len(encoded)} bytes, exceeds slot length {slot_len}"
            )
        absolute = object_start + text_offset
        payload[absolute : absolute + slot_len] = b"\x00" * slot_len
        payload[absolute : absolute + len(encoded)] = encoded
        patched_text_slots += 1

    if checksum_mode == "recompute":
        payload = bytearray(update_tft_checksum(bytes(payload), series=model_series))
    elif checksum_mode == "zero":
        payload[-4:] = b"\x00\x00\x00\x00"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(payload)

    return BasicPatchResult(
        baseline_tft=str(baseline_tft_path),
        baseline_pa=str(baseline_pa_path),
        target_pa=str(target_pa_path),
        out_tft=str(out_path),
        file_size=len(payload),
        checksum_mode=checksum_mode,
        patched_coordinates=patched_coordinates,
        patched_text_slots=patched_text_slots,
        final_word_note="Final 4-byte TFT checksum is recomputed when checksum_mode=recompute.",
    )


def patch_added_object_tft(
    baseline_tft: str | Path,
    *,
    baseline_pa: str | Path,
    target_pa: str | Path,
    out_tft: str | Path,
) -> AddedObjectPatchResult:
    """Recompile the current seed's TFT object tail after appending objects.

    This is still intentionally narrow, but it generates the object primary
    records, 24-byte user/attribute records, mirror records, encrypted Header2
    fields, header CRCs, and final TFT checksum instead of copying a full
    official target TFT.
    """

    baseline_tft_path = Path(baseline_tft).resolve()
    baseline_pa_path = Path(baseline_pa).resolve()
    target_pa_path = Path(target_pa).resolve()
    out_path = Path(out_tft).resolve()

    baseline_page = load_page_file(baseline_pa_path)
    target_page = load_page_file(target_pa_path)
    added_blocks = _validate_added_objects(baseline_page.blocks, target_page.blocks)

    seed = _load_tail_seed(baseline_tft_path, baseline_pa_path, baseline_page)
    _augment_seed_templates(seed, {block.type_code for block in target_page.blocks})
    tail, sections = _build_added_object_tail(seed, target_page.blocks)
    payload = bytearray(seed.raw[: seed.object_start] + tail)
    image_button_layout = _uses_full_image_button_layout(target_page.blocks)

    _refresh_tft_headers(
        payload,
        model=seed.model,
        model_series=seed.model_series,
        object_start=seed.object_start,
        object_count=len(target_page.blocks),
        attr_relative=sections["attr"],
        user_relative=sections["user"],
        picture_relative=sections["pic"],
        prefix_delta=sections["prefix_delta"],
        image_button_layout=image_button_layout,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(payload)

    return AddedObjectPatchResult(
        baseline_tft=str(baseline_tft_path),
        baseline_pa=str(baseline_pa_path),
        target_pa=str(target_pa_path),
        out_tft=str(out_path),
        file_size=len(payload),
        object_count=len(target_page.blocks),
        added_objects=[_added_block_summary(block) for block in added_blocks],
        section_offsets=sections,
    )


def patch_rebuild_page_tft(
    baseline_tft: str | Path,
    *,
    seed_pa: str | Path,
    target_pa: str | Path,
    out_tft: str | Path,
) -> RebuildPagePatchResult:
    """Rebuild the compiled page tail from target_pa without keeping seed objects.

    Unlike patch_added_object_tft(), this path does not require the target page
    to preserve the seed page's existing object list. The seed TFT still
    provides headers, resources, and per-type binary templates, but the compiled
    page object/index/user/mirror sections come only from target_pa.
    """

    baseline_tft_path = Path(baseline_tft).resolve()
    seed_pa_path = Path(seed_pa).resolve()
    target_pa_path = Path(target_pa).resolve()
    out_path = Path(out_tft).resolve()

    seed_page = load_page_file(seed_pa_path)
    target_page = load_page_file(target_pa_path)
    _validate_rebuild_page(target_page.blocks)

    seed = _load_tail_seed(baseline_tft_path, seed_pa_path, seed_page)
    _augment_seed_templates(seed, {block.type_code for block in target_page.blocks})
    # The baseline TFT is still the source of truth for encrypted headers,
    # resource tables, and per-type binary templates. The target .pa owns only
    # the rebuilt page/object tail, which keeps this path narrow and repeatable.
    tail, sections = _build_added_object_tail(seed, target_page.blocks)
    payload = bytearray(seed.raw[: seed.object_start] + tail)
    image_button_layout = _uses_full_image_button_layout(target_page.blocks)

    _refresh_tft_headers(
        payload,
        model=seed.model,
        model_series=seed.model_series,
        object_start=seed.object_start,
        object_count=len(target_page.blocks),
        attr_relative=sections["attr"],
        user_relative=sections["user"],
        picture_relative=sections["pic"],
        prefix_delta=sections["prefix_delta"],
        image_button_layout=image_button_layout,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(payload)

    target_names = {block.objname for block in target_page.blocks if block.objname}
    seed_names = [block.objname for block in seed_page.blocks if block.objname]
    return RebuildPagePatchResult(
        baseline_tft=str(baseline_tft_path),
        seed_pa=str(seed_pa_path),
        target_pa=str(target_pa_path),
        out_tft=str(out_path),
        file_size=len(payload),
        object_count=len(target_page.blocks),
        objects=[_added_block_summary(block) for block in target_page.blocks],
        removed_seed_objects=[name for name in seed_names if name and name not in target_names],
        section_offsets=sections,
    )


def patch_multi_page_tft(
    baseline_tft: str | Path,
    *,
    baseline_pa: str | Path,
    target_pages: list[str | Path],
    out_tft: str | Path,
    allow_experimental_events: bool = False,
) -> MultiPagePatchResult:
    """Compile the recovered two-page tail layout.

    V1 keeps the proven case31 path byte-for-byte and only widens page1 to
    plain text/button controls. More page/event/resource combinations still
    fail closed until official fixtures prove their layout.
    """

    baseline_tft_path = Path(baseline_tft).resolve()
    baseline_pa_path = Path(baseline_pa).resolve()
    target_page_paths = [Path(path).resolve() for path in target_pages]
    out_path = Path(out_tft).resolve()

    if len(target_page_paths) != 2:
        raise TftToolchainError("Multi-page TFT patch V1 requires exactly two target .pa files")

    seed_page = load_page_file(baseline_pa_path)
    pages = [load_page_file(path) for path in target_page_paths]
    _validate_same_layout(seed_page.blocks, pages[0].blocks)
    _validate_supported_multi_pages(pages, allow_experimental_events=allow_experimental_events)

    seed = _load_tail_seed(baseline_tft_path, baseline_pa_path, seed_page)
    _augment_seed_templates(seed, {block.type_code for page in pages for block in page.blocks})
    # Multi-page support is intentionally fixture-shaped: page directories and
    # object sections are rebuilt only for the recovered two-page layout, while
    # event scheduling stays fail-closed unless explicitly enabled for probes.
    tail, sections = _build_multi_page_tail(seed, pages)
    payload = bytearray(seed.raw[: seed.object_start] + tail)

    _refresh_tft_headers(
        payload,
        model=seed.model,
        model_series=seed.model_series,
        object_start=seed.object_start,
        object_count=sum(len(page.blocks) for page in pages),
        attr_relative=sections["attr"],
        user_relative=sections["user"],
        picture_relative=sections["pic"],
        prefix_delta=sections["prefix_delta"],
        gmovs_relative_offset=0x20,
        videos_count=len(pages),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(payload)

    return MultiPagePatchResult(
        baseline_tft=str(baseline_tft_path),
        baseline_pa=str(baseline_pa_path),
        target_pages=[str(path) for path in target_page_paths],
        out_tft=str(out_path),
        file_size=len(payload),
        page_count=len(pages),
        object_count=sum(len(page.blocks) for page in pages),
        section_offsets=sections,
        experimental_events=allow_experimental_events,
        experimental_event_summary=_summarize_multi_page_experimental_events(pages),
    )


def _validate_supported_multi_pages(pages: list[Any], *, allow_experimental_events: bool) -> None:
    if len(pages) != 2:
        raise TftToolchainError("Multi-page V1 supports exactly two pages")
    all_names: set[str] = set()
    for page_index, page in enumerate(pages):
        if not page.blocks or page.blocks[0].type_code != "y":
            raise TftToolchainError("Multi-page V1 requires every .pa to start with a page object")
        _validate_unique_names_and_ids(page.blocks)
        for block in page.blocks:
            if block.objname in all_names:
                raise TftToolchainError(
                    f"Multi-page V1 requires object names to be unique across pages: {block.objname!r}"
                )
            all_names.add(block.objname or "")
            if block.type_code not in TYPE_RECORD_LENGTHS:
                raise TftToolchainError(f"Unsupported object type in multi-page TFT tail: {block.type_code!r}")
        if page_index == 0:
            continue
        for block_index, block in enumerate(page.blocks):
            if block_index == 0:
                if any(lines for lines in _events_by_prefix(block).values()) and not (
                    allow_experimental_events and _is_supported_page1_page_event_block(block)
                ):
                    raise TftToolchainError("Multi-page V1 page1 page events are not supported yet")
                continue
            if block.type_code not in {"t", "b", "6", "p", "j", "\x01", "z", "8", "9"}:
                raise TftToolchainError(
                    "Multi-page V1 page1 supports only text/button/number/image/progress/slider/gauge/checkbox/radio controls"
                )
            if any(lines for lines in _events_by_prefix(block).values()) and not (
                allow_experimental_events
                and _is_supported_page1_button_event_block(block, page1_blocks=page.blocks)
            ):
                raise TftToolchainError("Multi-page V1 page1 control events are not supported yet")
            if block.type_code == "b" and _field_int(block, "sta") == 2:
                raise TftToolchainError("Multi-page V1 page1 image buttons are not supported yet")


def _is_supported_page1_page_event_block(block: PageBlock) -> bool:
    if block.type_code != "y":
        return False
    event_items = [
        (prefix, lines)
        for prefix, lines in _events_by_prefix(block).items()
        if lines
    ]
    if len(event_items) != 1:
        return False
    prefix, lines = event_items[0]
    return (
        prefix == "codesload-"
        and len(lines) == 1
        and is_page1_fixed_printh_probe_event_line(lines[0], byte_count=4)
    )


def _summarize_multi_page_experimental_events(pages: list[Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "page1_page_events": [],
        "page1_object_events": [],
    }
    if len(pages) < 2:
        return summary
    for block_index, block in enumerate(pages[1].blocks):
        for prefix, lines in _events_by_prefix(block).items():
            if not lines:
                continue
            item = {
                "page_index": 1,
                "block_index": block_index,
                "objname": block.objname,
                "type_code": _display_type_code(block.type_code),
                "event_prefix": prefix,
                "lines": lines,
            }
            if block_index == 0:
                item.update(
                    {
                        "event_family": "page_level",
                        "runtime_status": "compile_only_scheduler_unrecovered",
                        "note": (
                            "The page-load bytecode is present in the TFT, but the extra-page "
                            "scheduler callback binding has not been recovered; the 2026-05-15 "
                            "page1_load_printh live probe did not observe the printh payload."
                        ),
                    }
                )
                summary["page1_page_events"].append(item)
            else:
                item.update(
                    {
                        "event_family": _classify_page1_object_event_line(lines[0]),
                        "runtime_status": "live_proven_event_family",
                        "note": (
                            "This object event shape is within the page1 button event families "
                            "that have been live-smoked on the TJC8048X543_011C; each new scene "
                            "should still be validated with serial readback or camera evidence."
                        ),
                    }
                )
                summary["page1_object_events"].append(item)
    return summary


def _classify_page1_object_event_line(line: str) -> str:
    if is_page1_printh_probe_event_line(line):
        return "printh_probe"
    if parse_page1_button_click_event_line(line) is not None:
        return "button_click"
    if parse_page1_button_vis_event_line(line) is not None:
        return "vis"
    if parse_page1_button_tsw_event_line(line) is not None:
        return "tsw"
    if parse_page1_button_ref_event_line(line) is not None:
        return "ref"
    normalized = line.strip().lower()
    if EVENT_ASSIGN_RE.match(normalized) is not None:
        return "numeric_assignment"
    if EVENT_UNARY_RE.match(normalized) is not None:
        return "numeric_unary"
    return "unknown"


def _display_type_code(type_code: str) -> str:
    return type_code if type_code.isprintable() else f"0x{ord(type_code):02X}"


def _is_supported_page1_button_event_block(
    block: PageBlock,
    *,
    page1_blocks: list[PageBlock] | None = None,
) -> bool:
    event_item = _single_page1_button_event_block(block)
    if event_item is None:
        return False
    _, line = event_item
    if is_supported_page1_button_event_line(line):
        return True
    if page1_blocks is None:
        return False
    return (
        _is_supported_page1_button_click_event_block(block, line=line, page1_blocks=page1_blocks)
        or _is_supported_page1_button_vis_event_block(block, line=line, page1_blocks=page1_blocks)
        or _is_supported_page1_button_tsw_event_block(block, line=line, page1_blocks=page1_blocks)
        or _is_supported_page1_button_ref_event_block(block, line=line, page1_blocks=page1_blocks)
    )


def _single_page1_button_event_block(block: PageBlock) -> tuple[str, str] | None:
    if block.type_code != "b":
        return None
    event_items = [
        (prefix, lines)
        for prefix, lines in _events_by_prefix(block).items()
        if lines
    ]
    if len(event_items) != 1:
        return None
    prefix, lines = event_items[0]
    if prefix not in {"codesdown-", "codesup-"} or len(lines) != 1:
        return None
    return prefix, lines[0]


def _is_supported_page1_button_click_event_block(
    block: PageBlock,
    *,
    line: str,
    page1_blocks: list[PageBlock],
) -> bool:
    parsed = parse_page1_button_click_event_line(line)
    if parsed is None:
        return False
    target_name, _ = parsed
    if target_name == block.objname:
        return False
    target_block = next((candidate for candidate in page1_blocks if candidate.objname == target_name), None)
    if target_block is None or target_block.type_code != "b":
        return False
    target_event_item = _single_page1_button_event_block(target_block)
    if target_event_item is None:
        return False
    _, target_line = target_event_item
    return is_page1_printh_probe_event_line(target_line)


def _is_supported_page1_button_vis_event_block(
    block: PageBlock,
    *,
    line: str,
    page1_blocks: list[PageBlock],
) -> bool:
    parsed = parse_page1_button_vis_event_line(line)
    if parsed is None:
        return False
    target_name, _ = parsed
    if target_name == block.objname:
        return False
    return any(candidate.objname == target_name for candidate in page1_blocks)


def _is_supported_page1_button_tsw_event_block(
    block: PageBlock,
    *,
    line: str,
    page1_blocks: list[PageBlock],
) -> bool:
    parsed = parse_page1_button_tsw_event_line(line)
    if parsed is None:
        return False
    target_name, _ = parsed
    if target_name == "255":
        return True
    if target_name == block.objname:
        return False
    return any(candidate.objname == target_name for candidate in page1_blocks)


def _is_supported_page1_button_ref_event_block(
    block: PageBlock,
    *,
    line: str,
    page1_blocks: list[PageBlock],
) -> bool:
    target_name = parse_page1_button_ref_event_line(line)
    if target_name is None:
        return False
    if target_name == block.objname:
        return False
    return any(candidate.objname == target_name for candidate in page1_blocks)


def _validate_same_layout(base_blocks: list[PageBlock], target_blocks: list[PageBlock]) -> None:
    if len(base_blocks) != len(target_blocks):
        raise TftToolchainError(
            f"Basic patch requires same object count: baseline={len(base_blocks)}, target={len(target_blocks)}"
        )
    for index, (base, target) in enumerate(zip(base_blocks, target_blocks)):
        if base.type_code != target.type_code or base.objname != target.objname:
            raise TftToolchainError(
                f"Basic patch requires same object order at index {index}: "
                f"{base.type_code}:{base.objname} != {target.type_code}:{target.objname}"
            )


def _validate_added_objects(base_blocks: list[PageBlock], target_blocks: list[PageBlock]) -> list[PageBlock]:
    if len(target_blocks) <= len(base_blocks):
        raise TftToolchainError(
            "Added-object patch requires at least one appended object: "
            f"baseline={len(base_blocks)}, target={len(target_blocks)}"
        )
    for index, (base, target) in enumerate(zip(base_blocks, target_blocks)):
        if base.type_code != target.type_code or base.objname != target.objname:
            raise TftToolchainError(
                f"Added-object patch requires unchanged existing object order at index {index}: "
                f"{base.type_code}:{base.objname} != {target.type_code}:{target.objname}"
            )
    added_blocks = target_blocks[len(base_blocks) :]
    for block in added_blocks:
        if block.type_code not in TYPE_RECORD_LENGTHS:
            raise TftToolchainError(f"Added-object patch currently does not support {block.type_code!r}")
    for block in target_blocks:
        if block.type_code not in TYPE_RECORD_LENGTHS:
            raise TftToolchainError(f"Unsupported object type in TFT tail generator: {block.type_code!r}")
    _validate_unique_names_and_ids(target_blocks)
    return added_blocks


def _validate_rebuild_page(target_blocks: list[PageBlock]) -> None:
    if not target_blocks:
        raise TftToolchainError("Clean page rebuild requires at least a page block")
    if target_blocks[0].type_code != "y":
        raise TftToolchainError(
            f"Clean page rebuild expects the first block to be page type 'y', got {target_blocks[0].type_code!r}"
        )
    for block in target_blocks:
        if block.type_code not in TYPE_RECORD_LENGTHS:
            raise TftToolchainError(f"Unsupported object type in TFT page rebuild: {block.type_code!r}")
    _validate_unique_names_and_ids(target_blocks)


def _validate_unique_names_and_ids(blocks: list[PageBlock]) -> None:
    names: dict[str, str] = {}
    ids: dict[int, str] = {}
    for block in blocks:
        name = block.objname
        if not name:
            raise TftToolchainError("Object without objname cannot be compiled")
        if name in names:
            raise TftToolchainError(f"Duplicate object name in target page: {name!r}")
        names[name] = name
        object_id = _required_field_int(block, "id")
        if not 0 <= object_id <= 0xFF:
            raise TftToolchainError(f"Object id for {name!r} must fit in one byte, got {object_id}")
        if object_id in ids:
            raise TftToolchainError(f"Duplicate object id in target page: {object_id}")
        ids[object_id] = name


def _validate_extra_layout_mix(seed: _TailSeed, blocks: list[PageBlock]) -> None:
    extra_types = sorted({
        block.type_code
        for block in blocks
        if block.type_code in seed.mirror_layout_templates
    })
    if len(extra_types) <= 1:
        return
    readable = ", ".join(repr(item) for item in extra_types)
    raise TftToolchainError(
        "Mixed advanced extra-control TFT layouts are not supported yet: "
        f"{readable}. Build one advanced control type per page/TFT for now, "
        "or provide an official mixed-control fixture so the combined prefix/mirror layout can be learned."
    )


def _added_block_summary(block: PageBlock) -> dict[str, Any]:
    return {
        "name": block.objname or "",
        "type": block.type_code or "",
        "id": _required_field_int(block, "id"),
        "x": _field_int(block, "x"),
        "y": _field_int(block, "y"),
        "w": _field_int(block, "w"),
        "h": _field_int(block, "h"),
    }


def _augment_seed_templates(seed: _TailSeed, needed_types: set[str]) -> None:
    missing = sorted(type_code for type_code in needed_types if type_code not in seed.primary_templates)
    if not missing:
        return

    case_root = Path(DEFAULT_CASE_ROOT)
    loaded_roots: dict[str, _TailSeed] = {}
    loaded_pages: dict[str, Any] = {}
    unresolved: list[str] = []
    for type_code in missing:
        case_name = KNOWN_EXTRA_TYPE_CASES.get(type_code)
        if not case_name:
            unresolved.append(type_code)
            continue
        case_seed = loaded_roots.get(case_name)
        if case_seed is None:
            case_dir = case_root / case_name
            case_tft, case_hmi = _case_fixture_paths(case_dir)
            if case_tft is None or case_hmi is None:
                unresolved.append(type_code)
                continue
            case_page = _load_hmi_page0(case_hmi)
            case_seed = _load_tail_seed(case_tft, case_hmi, case_page)
            loaded_roots[case_name] = case_seed
            loaded_pages[case_name] = case_page
        else:
            case_page = loaded_pages[case_name]

        if type_code in case_seed.primary_templates:
            seed.primary_templates[type_code] = case_seed.primary_templates[type_code]
            seed.user_templates[type_code] = case_seed.user_templates[type_code]
            seed.mirror_templates[type_code] = case_seed.mirror_templates[type_code]
            seed.mirror_layout_templates[type_code] = {
                key: list(value)
                for key, value in case_seed.mirror_templates.items()
            }
            seed.mirror_descriptor_sequences[type_code] = _prefix_descriptor_sequence(case_seed.compiled_prefix)
            seed.primary_final_markers[type_code] = case_seed.primary_final_markers.get(
                "",
                b"\x00\x00\x00\x00",
            )
            seed.primary_string_prefix_paddings[type_code] = case_seed.primary_string_prefix_paddings.get("", 0)
            seed.primary_string_suffix_paddings[type_code] = case_seed.primary_string_suffix_paddings.get("", 0)
            if type_code == VARIABLE_TYPE_CODE or type_code in MEDIA_TYPE_CODES:
                seed.prefix_inserts[type_code] = []
            else:
                seed.prefix_inserts[type_code] = _derive_prefix_insertions_for_case(seed, case_seed, case_page)
        else:
            unresolved.append(type_code)

    if unresolved:
        readable = ", ".join(repr(item) for item in unresolved)
        raise TftToolchainError(
            "Missing compiled TFT templates for object type(s): "
            f"{readable}. Provide official case fixtures under {case_root} or avoid these controls."
        )


def _case_fixture_paths(case_dir: Path) -> tuple[Path | None, Path | None]:
    candidates = [
        (case_dir / "lcd_test.tft", case_dir / "lcd_test.HMI"),
        (case_dir / "official_compile" / "source_raw.run", case_dir / "official_wiki" / "source_raw.HMI"),
    ]
    for case_tft, case_hmi in candidates:
        if case_tft.exists() and case_hmi.exists():
            return case_tft, case_hmi
    return None, None


def _load_hmi_page0(hmi_path: Path):
    inspection = inspect_hmi(hmi_path)
    raw = hmi_path.read_bytes()
    entry = next((item for item in inspection.entries if item.name == "0.pa"), None)
    if entry is None or not entry.in_file:
        raise TftToolchainError(f"0.pa not found in {hmi_path}")
    return parse_page_data(raw[entry.data_offset : entry.data_offset + entry.length])


def _load_tail_seed(
    baseline_tft: Path,
    baseline_pa: Path,
    baseline_page: Any,
) -> _TailSeed:
    raw = baseline_tft.read_bytes()
    inspection = inspect_tft(baseline_tft)
    header1 = _header(inspection, "Header1")
    header2 = _header(inspection, "Header2")
    object_start = _header_int(header2, "unknown_objects_address")
    picture_start = _header_int(header2, "pictures_address")
    attr_start = _header_int(header2, "static_usercode_address")
    user_start = _header_int(header2, "usercode_address")
    model = str(inspection.get("model") or "")
    model_series = _header_int(header1, "model_series")
    if None in {object_start, picture_start, attr_start, user_start, model_series}:
        raise TftToolchainError("Unable to inspect required TFT header fields")
    assert object_start is not None
    assert picture_start is not None
    assert attr_start is not None
    assert user_start is not None
    assert model_series is not None

    tail = raw[object_start:]
    if len(tail) < 0x187:
        raise TftToolchainError("Baseline TFT object tail is too short for current seed template extraction")

    by_id = {_field_int(block, "id"): block.objname for block in baseline_page.blocks}
    expected_hash_by_id = {
        object_id: _object_name_hash_or_error(name)
        for object_id, name in by_id.items()
        if object_id is not None and name
    }
    baseline_hash_offset, hash_data = _find_hash_block(tail, expected_hash_by_id)
    compiled_prefix = tail[:baseline_hash_offset]
    prefix_head_end = _prefix_event_layout_start(compiled_prefix)
    prefix_head = tail[:prefix_head_end]
    page_event = tail[prefix_head_end : prefix_head_end + 0x28]
    object_event = tail[prefix_head_end + 0x28 : prefix_head_end + 0x42]
    hash_by_name: dict[str, int] = {}
    for offset in range(0, len(hash_data), 6):
        object_hash = int.from_bytes(hash_data[offset : offset + 4], "little")
        object_id = int.from_bytes(hash_data[offset + 4 : offset + 6], "little")
        name = by_id.get(object_id)
        if name:
            expected_hash = _object_name_hash_or_error(name)
            if expected_hash != object_hash:
                raise TftToolchainError(
                    f"Recovered TFT object hash mismatch for {name!r}: "
                    f"compiled=0x{object_hash:08X}, computed=0x{expected_hash:08X}"
                )
            hash_by_name[name] = object_hash

    primary_block_offset = baseline_hash_offset + 4 + len(hash_data)
    primary_size = int.from_bytes(tail[primary_block_offset : primary_block_offset + 4], "little")
    primary_data_start = primary_block_offset + 4
    if primary_data_start + primary_size > len(tail):
        raise TftToolchainError("Baseline TFT primary object block is truncated")
    primary_data = tail[primary_data_start : primary_data_start + primary_size]

    value_offsets = [
        int.from_bytes(tail[primary_data_start + index * 4 : primary_data_start + index * 4 + 4], "little")
        for index in range(len(baseline_page.blocks))
    ]
    record_start = primary_data_start + len(baseline_page.blocks) * 4
    primary_templates: dict[str, bytes] = {}
    cursor = record_start
    for block in baseline_page.blocks:
        type_code = block.type_code
        if type_code not in TYPE_RECORD_LENGTHS:
            raise TftToolchainError(f"Unsupported baseline object type: {type_code!r}")
        length = TYPE_RECORD_LENGTHS[type_code]
        primary_templates.setdefault(type_code, bytes(tail[cursor : cursor + length]))
        cursor += length
    primary_final_marker = primary_data[-4:] if len(primary_data) >= 4 else b"\x00\x00\x00\x00"
    prefix_padding, suffix_padding = _recover_primary_string_padding(
        primary_data,
        baseline_page.blocks,
        record_start - primary_data_start,
        primary_final_marker,
    )

    user_header = tail[attr_start:user_start]
    if len(user_header) != 0x24:
        raise TftToolchainError("Baseline user/attribute header is not the expected 0x24 bytes")

    user_templates: dict[str, list[_UserRecordTemplate]] = {}
    slot_start = 0
    for block, value_base in zip(baseline_page.blocks, value_offsets):
        type_code = block.type_code
        slot_count = TYPE_USER_SLOT_COUNTS[type_code]
        entries: list[_UserRecordTemplate] = []
        for slot_index in range(slot_count):
            record = tail[user_start + (slot_start + slot_index) * 24 : user_start + (slot_start + slot_index + 1) * 24]
            if record == b"\x00" * 24:
                continue
            words = [int.from_bytes(record[index : index + 4], "little") for index in range(0, 24, 4)]
            if (
                words[5] in {0x0B3F, 0x193F}
                or (type_code == "b" and words[5] in {0x1F3F, 0x333F})
                or (type_code == ":" and words[5] == 0x1F3F)
                or (type_code == "=" and words[5] == 0x213F)
            ):
                word1_mode = "text_pointer"
                word1_delta = words[1] - value_base
            elif (type_code == "=" and words[5] == 0x1013F) or (type_code == "<" and words[5] == 0x1003F):
                word1_mode = "path_pointer"
                word1_delta = words[1] - value_base
            elif type_code == "m" and words[1] < value_base:
                word1_mode = "absolute"
                word1_delta = words[1]
            else:
                word1_mode = "value_delta"
                word1_delta = words[1] - value_base
            entries.append(
                _UserRecordTemplate(
                    slot_index=slot_index,
                    word1_mode=word1_mode,
                    word1_delta=word1_delta,
                    word2=words[2],
                    word3=words[3],
                    word4=words[4],
                    word5=words[5],
                )
            )
        user_templates.setdefault(type_code, entries)
        slot_start += slot_count

    mirror_start = picture_start - object_start
    mirror_templates: dict[str, list[int | None]] = {}
    mirror_offsets = _find_mirror_record_offsets(tail, mirror_start, baseline_page.blocks)
    slot_start = 0
    for index, block in enumerate(baseline_page.blocks):
        type_code = block.type_code
        record_start = mirror_offsets[index]
        if index + 1 < len(mirror_offsets):
            record_end = mirror_offsets[index + 1]
        elif index > 0:
            record_end = record_start + (mirror_offsets[index] - mirror_offsets[index - 1])
        else:
            record_end = record_start + 0x8A
        record = tail[record_start:record_end]
        if len(record) < 0x8A or (len(record) - 0x38) % 2:
            raise TftToolchainError("Baseline mirror object record is truncated")
        values: list[int | None] = []
        for offset in range(0x38, len(record), 2):
            value = int.from_bytes(record[offset : offset + 2], "little")
            values.append(None if value == 0xFFFF else value - slot_start)
        mirror_templates.setdefault(type_code, values)
        slot_start += TYPE_USER_SLOT_COUNTS[type_code]

    return _TailSeed(
        baseline_tft=baseline_tft,
        baseline_pa=baseline_pa,
        raw=raw,
        object_start=object_start,
        model=model,
        model_series=model_series,
        prefix_head=prefix_head,
        page_event=page_event,
        object_event=object_event,
        compiled_prefix=compiled_prefix,
        prefix_inserts={},
        user_header=user_header,
        primary_templates=primary_templates,
        user_templates=user_templates,
        mirror_templates=mirror_templates,
        mirror_layout_templates={},
        mirror_descriptor_sequences={"": _prefix_descriptor_sequence(compiled_prefix)},
        primary_final_markers={"": primary_final_marker},
        primary_string_prefix_paddings={"": prefix_padding},
        primary_string_suffix_paddings={"": suffix_padding},
        hash_by_name=hash_by_name,
    )


def _find_hash_block(tail: bytes, expected_hash_by_id: dict[int, int]) -> tuple[int, bytes]:
    hash_size = len(expected_hash_by_id) * 6
    search_end = min(len(tail) - 4 - hash_size, 0x2000)
    for offset in range(0x100, max(search_end, 0x100)):
        if int.from_bytes(tail[offset : offset + 4], "little") != hash_size:
            continue
        data = tail[offset + 4 : offset + 4 + hash_size]
        seen: dict[int, int] = {}
        valid = True
        for cursor in range(0, len(data), 6):
            object_hash = int.from_bytes(data[cursor : cursor + 4], "little")
            object_id = int.from_bytes(data[cursor + 4 : cursor + 6], "little")
            if expected_hash_by_id.get(object_id) != object_hash:
                valid = False
                break
            seen[object_id] = object_hash
        if valid and set(seen) == set(expected_hash_by_id):
            return offset, data
    raise TftToolchainError("Unable to locate compiled TFT object hash/index block")


def _prefix_descriptor_sequence(prefix: bytes) -> list[bytes]:
    end = int.from_bytes(prefix[:4], "little")
    if end < PREFIX_DESCRIPTOR_START or end > len(prefix):
        raise TftToolchainError("TFT prefix descriptor table has an invalid end offset")
    descriptor_bytes = prefix[PREFIX_DESCRIPTOR_START:end]
    if len(descriptor_bytes) % 4:
        raise TftToolchainError("TFT prefix descriptor table is not 4-byte aligned")
    return [
        descriptor_bytes[offset : offset + 4]
        for offset in range(0, len(descriptor_bytes), 4)
    ]


def _prefix_event_layout_start(prefix: bytes) -> int:
    descriptor_sentinel_offset = int.from_bytes(prefix[:4], "little")
    event_start = descriptor_sentinel_offset + 4 + PREFIX_SYSTEM_EVENT_LAYOUT_SIZE
    if event_start > len(prefix):
        raise TftToolchainError("TFT prefix event layout start exceeds compiled prefix length")
    return event_start


def _recover_primary_string_padding(
    primary_data: bytes,
    blocks: list[PageBlock],
    offset_table_size: int,
    final_marker: bytes,
) -> tuple[int, int]:
    if not primary_data or len(primary_data) < offset_table_size:
        return 0, 0
    value_offsets = [
        int.from_bytes(primary_data[index : index + 4], "little")
        for index in range(0, offset_table_size, 4)
    ]
    if len(value_offsets) != len(blocks):
        return 0, 0
    record_end = max(
        (
            value_offset - 0x10 + TYPE_RECORD_LENGTHS.get(block.type_code, 0)
            for block, value_offset in zip(blocks, value_offsets)
        ),
        default=offset_table_size,
    )
    string_start = record_end + 4
    marker_start = len(primary_data) - len(final_marker)
    if string_start > marker_start:
        return 0, 0

    encoded_text_offsets: list[int] = []
    expected_string_slots = 0
    for block in blocks:
        for field_name, _pointer_offset, slot_len in _string_pointer_fields(block):
            expected_string_slots += slot_len
            text = _field_text(block, field_name) or ""
            encoded = _encode_display_text(text)
            if not encoded:
                continue
            found = primary_data.find(encoded, string_start, marker_start)
            if found >= 0:
                encoded_text_offsets.append(found)

    if not expected_string_slots:
        return 0, 0
    prefix_padding = 0
    if encoded_text_offsets:
        prefix_padding = max(0, min(encoded_text_offsets) - string_start)
    suffix_start = string_start + prefix_padding + expected_string_slots
    suffix_padding = max(0, marker_start - suffix_start)
    return prefix_padding, suffix_padding


def _find_mirror_record_offsets(tail: bytes, mirror_start: int, blocks: list[PageBlock]) -> list[int]:
    offsets: list[int] = []
    cursor = mirror_start + 0x10
    for block in blocks:
        type_code = block.type_code
        object_id = _required_field_int(block, "id")
        header = bytes([ord(type_code), object_id, 0, _record_header_flag(type_code)])
        found = tail.find(header, cursor, min(len(tail), cursor + 0x400))
        if found < 0:
            raise TftToolchainError(
                f"Unable to locate mirror record for {block.objname or type_code!r}"
            )
        offsets.append(found)
        cursor = found + 0x38
    return offsets


def _build_added_object_tail(
    seed: _TailSeed,
    target_blocks: list[PageBlock],
) -> tuple[bytes, dict[str, int]]:
    object_count = len(target_blocks)
    image_button_layout = _uses_full_image_button_layout(target_blocks)
    if _uses_mixed_compact_primary_layout(seed, target_blocks):
        _augment_official_mixed_layout(seed)
    mirror_layout_type = _mirror_layout_type_for_blocks(seed, target_blocks)
    descriptor_sequence = _single_media_descriptor_sequence(seed, target_blocks)
    prefix_head = _prefix_head_for_layout(
        seed.prefix_head,
        image_button_layout=image_button_layout,
        extra_insertions=_prefix_insertions_for_blocks(seed, target_blocks),
        descriptor_sequence=descriptor_sequence,
    )
    if descriptor_sequence is None and mirror_layout_type is not None:
        descriptor_sequence = _prefix_descriptor_sequence(prefix_head)
    post_primary_page_load = _uses_post_primary_page_load(target_blocks)
    event_layout = _build_event_layout(
        target_blocks,
        len(prefix_head),
        image_button_layout=image_button_layout,
        post_primary_page_load=post_primary_page_load,
    )
    prefix = prefix_head + event_layout.data
    hash_offset = len(prefix)
    hash_entries = []
    for block in target_blocks:
        name = block.objname
        if not name:
            raise TftToolchainError("Object without objname cannot be hashed")
        object_hash = _object_name_hash_or_error(name)
        object_id = _required_field_int(block, "id")
        hash_entries.append((object_hash, object_id))
    hash_entries.sort(key=lambda item: item[0])
    hash_data = b"".join(
        object_hash.to_bytes(4, "little") + object_id.to_bytes(2, "little")
        for object_hash, object_id in hash_entries
    )

    out = bytearray(prefix)
    out.extend(_code_block(hash_data))
    primary_offset = len(out)
    primary_data, value_offsets, text_pointer_by_id, primary_pre_string_len = _build_primary_block(
        seed,
        target_blocks,
        event_callbacks=event_layout.callbacks,
    )
    out.extend(_code_block(primary_data))
    post_primary_event_context = _build_event_compile_context(target_blocks)
    post_primary_page_event = _build_post_primary_page_event(
        target_blocks,
        context=post_primary_event_context,
    )
    if post_primary_page_event:
        out.extend(post_primary_page_event)
    elif any(block.type_code in MEDIA_TYPE_CODES for block in target_blocks):
        out.extend(_code_block(bytes.fromhex("09 1f 04 31")))
        out.extend(_code_block(b"\x09\x30\x08"))
        out.extend(_code_block(b""))
    elif any(block.type_code in {"\x00", "\x01", "\x05", "7", "=", TIMER_TYPE_CODE} for block in target_blocks):
        marker = "35" if (
            _uses_mixed_compact_primary_layout(seed, target_blocks)
            and any(block.type_code == TIMER_TYPE_CODE for block in target_blocks)
        ) else "34"
        out.extend(_code_block(bytes.fromhex(f"09 1f 04 {marker}")))
        if _uses_mixed_compact_primary_layout(seed, target_blocks) and any(
            block.type_code == "\x00" for block in target_blocks
        ):
            out.extend(_code_block(bytes.fromhex("09 1f 04 37")))
        out.extend(_code_block(b"\x09\x30\x08"))
        out.extend(_code_block(b""))
    else:
        if _uses_mixed_compact_primary_layout(seed, target_blocks) and any(
            block.type_code == "\x00" for block in target_blocks
        ):
            out.extend(_code_block(bytes.fromhex("09 1f 04 37")))
        out.extend(_code_block(b"\x09\x30\x08"))
        out.extend(_code_block(b""))

    attr_offset = len(out)
    user_offset = attr_offset + len(seed.user_header)
    out.extend(seed.user_header)
    out.extend(
        _build_user_records(
            seed,
            target_blocks,
            value_offsets,
            text_pointer_by_id,
            max_picture_id=_max_picture_id(target_blocks),
        )
    )

    out.extend(_pre_mirror_padding(target_blocks))
    picture_offset = len(out)
    out.extend(
        _build_mirror_records(
            seed,
            target_blocks,
            value_offsets,
            mirror_layout_type=mirror_layout_type,
            mirror_value_count=_mirror_value_count_for_layout(
                seed,
                target_blocks,
                image_button_layout=image_button_layout,
                mirror_layout_type=mirror_layout_type,
                descriptor_sequence=descriptor_sequence,
            ),
            descriptor_sequence=descriptor_sequence,
            hash_offset=hash_offset,
            user_offset=user_offset,
            primary_pre_string_len=primary_pre_string_len,
            event_offsets=event_layout.offsets,
            event_callbacks=event_layout.callbacks,
            image_button_layout=image_button_layout,
        )
    )
    padding_offset = len(out)
    padding_size = (-len(out)) % 4
    if padding_size:
        padding_byte = (
            b"\xFF"
            if image_button_layout
            or any(
                block.type_code in {"\x00", "\x01", "4", "9", "C", "q", ":", "=", TIMER_TYPE_CODE}
                or block.type_code in MEDIA_TYPE_CODES
                for block in target_blocks
            )
            else b"\x00"
        )
        out.extend(padding_byte * padding_size)
    out.extend(b"\x00\x00\x00\x00")
    return bytes(out), {
        "hash": hash_offset,
        "primary": primary_offset,
        "attr": attr_offset,
        "user": user_offset,
        "pic": picture_offset,
        "padding": padding_offset,
        "prefix_delta": int.from_bytes(prefix_head[:4], "little") - int.from_bytes(seed.prefix_head[:4], "little"),
        "tail": len(out),
    }


def _pre_mirror_padding(blocks: list[PageBlock]) -> bytes:
    if any(block.type_code == ";" for block in blocks):
        return b"\x00" * 0x30
    return b""


def _build_multi_page_tail(
    seed: _TailSeed,
    pages: list[Any],
) -> tuple[bytes, dict[str, int]]:
    page0_blocks = pages[0].blocks
    extra_pages = [page.blocks for page in pages[1:]]
    extra_page_blocks = [block for blocks in extra_pages for block in blocks]
    extra_page_objects = [blocks[0] for blocks in extra_pages]
    all_user_blocks = [*extra_page_blocks, *page0_blocks]
    mirror_descriptor_sequence = seed.mirror_descriptor_sequences[""]
    mirror_value_count = len(mirror_descriptor_sequence)

    prefix_head = _multi_page_prefix_head(seed.prefix_head, extra_page_objects)
    out = bytearray(prefix_head)

    extra_page_infos: list[dict[str, Any]] = []
    for page_blocks in extra_pages:
        info, _primary_offset = _append_multi_page_page_sections(
            out,
            seed,
            page_blocks,
            event_context=_build_event_compile_context(page_blocks),
        )
        extra_page_infos.append(info)

    page0_info, page0_primary_offset = _append_multi_page_page_sections(
        out,
        seed,
        page0_blocks,
        event_context=_build_event_compile_context(page0_blocks),
    )

    attr_offset = len(out)
    user_offset = attr_offset + len(seed.user_header)
    out.extend(seed.user_header)

    for runtime_index, info in enumerate(extra_page_infos):
        user_records = _build_user_records(
            seed,
            info["blocks"],
            info["value_offsets"],
            info["text_pointer_by_id"],
            max_picture_id=_max_picture_id(info["blocks"]),
        )
        out.extend(_set_user_records_runtime_index(user_records, runtime_index))

    page0_user_records = _build_user_records(
        seed,
        page0_blocks,
        page0_info["value_offsets"],
        page0_info["text_pointer_by_id"],
        max_picture_id=_max_picture_id(all_user_blocks),
    )
    out.extend(_set_user_records_runtime_index(page0_user_records, len(extra_page_infos)))

    picture_offset = len(out)
    out.extend(
        _build_multi_page_mirror_records(
            seed,
            extra_page_infos=extra_page_infos,
            page0_blocks=page0_blocks,
            page0_hash_offset=page0_info["hash_offset"],
            page0_user_offset=user_offset + sum(info["slot_count"] for info in extra_page_infos) * 24,
            page0_primary_pre_string_len=page0_info["primary_pre_string_len"],
            page0_value_offsets=page0_info["value_offsets"],
            page0_event_offsets=page0_info["event_offsets"],
            page0_event_callbacks=page0_info["event_callbacks"],
            first_user_offset=user_offset,
            mirror_value_count=mirror_value_count,
            mirror_descriptor_sequence=mirror_descriptor_sequence,
        )
    )
    padding_offset = len(out)
    padding_size = (-len(out)) % 4
    if padding_size:
        out.extend(b"\xFF" * padding_size)
    out.extend(b"\x00\x00\x00\x00")
    return bytes(out), {
        "hash": page0_info["hash_offset"],
        "primary": page0_primary_offset,
        "attr": attr_offset,
        "user": user_offset,
        "pic": picture_offset,
        "padding": padding_offset,
        "prefix_delta": len(prefix_head) - len(seed.prefix_head),
        "tail": len(out),
    }


def _append_multi_page_page_sections(
    out: bytearray,
    seed: _TailSeed,
    page_blocks: list[PageBlock],
    *,
    event_context: _EventCompileContext,
) -> tuple[dict[str, Any], int]:
    event_offsets: list[int] = []
    event_callbacks: list[dict[str, int]] = []
    for index, block in enumerate(page_blocks):
        block_offset = len(out)
        event_offsets.append(block_offset)
        if index == 0:
            out.extend(_build_page_event_table(block, context=event_context))
            event_callbacks.append({})
        else:
            out.extend(_build_object_event_table(block, context=event_context))
            event_callbacks.append(_object_event_callback_offsets(block, block_offset, context=event_context))

    hash_offset = len(out)
    hash_entries = []
    for block in page_blocks:
        name = block.objname
        if not name:
            raise TftToolchainError("Object without objname cannot be hashed")
        hash_entries.append((_object_name_hash_or_error(name), _required_field_int(block, "id")))
    hash_entries.sort(key=lambda item: item[0])
    hash_data = b"".join(
        object_hash.to_bytes(4, "little") + object_id.to_bytes(2, "little")
        for object_hash, object_id in hash_entries
    )
    out.extend(_code_block(hash_data))

    primary_data, value_offsets, text_pointer_by_id, primary_pre_string_len = _build_primary_block(
        seed,
        page_blocks,
        event_callbacks=event_callbacks,
    )
    primary_offset = len(out)
    out.extend(_code_block(primary_data))
    out.extend(_code_block(b"\x09\x30\x08"))
    out.extend(_code_block(b""))
    return (
        {
            "blocks": page_blocks,
            "event_offsets": event_offsets,
            "event_callbacks": event_callbacks,
            "hash_offset": hash_offset,
            "value_offsets": value_offsets,
            "text_pointer_by_id": text_pointer_by_id,
            "primary_pre_string_len": primary_pre_string_len,
            "slot_count": sum(_user_slot_count(block) for block in page_blocks),
        },
        primary_offset,
    )


def _multi_page_prefix_head(prefix_head: bytes, extra_page_blocks: list[PageBlock]) -> bytes:
    if len(extra_page_blocks) != 1:
        raise TftToolchainError("Multi-page V1 supports exactly one extra page")
    page_block = extra_page_blocks[0]
    if not page_block.objname:
        raise TftToolchainError("Extra page object must have an objname")

    out = bytearray(prefix_head)
    delta = 6
    _add_prefix_u32(out, 0, delta)
    _add_prefix_u32(out, 0x1C, delta)
    _add_prefix_u32(out, 0x20, delta)

    # The official two-page fixture maps the original seed page to runtime
    # index 1 and inserts the new page as runtime index 0 in this prefix table.
    out[0x40:0x42] = (1).to_bytes(2, "little")
    out[0x42:0x42] = (
        _object_name_hash_or_error(page_block.objname).to_bytes(4, "little")
        + (0).to_bytes(2, "little")
    )
    return bytes(out)


def _build_multi_page_mirror_records(
    seed: _TailSeed,
    *,
    extra_page_infos: list[dict[str, Any]],
    page0_blocks: list[PageBlock],
    page0_hash_offset: int,
    page0_user_offset: int,
    page0_primary_pre_string_len: int,
    page0_value_offsets: list[int],
    page0_event_offsets: list[int],
    page0_event_callbacks: list[dict[str, int]],
    first_user_offset: int,
    mirror_value_count: int,
    mirror_descriptor_sequence: list[bytes],
) -> bytes:
    out = bytearray()
    user_cursor = first_user_offset
    for runtime_index, info in enumerate(extra_page_infos):
        out.extend(((len(info["blocks"]) << 16) | runtime_index).to_bytes(4, "little"))
        out.extend(int(info["hash_offset"]).to_bytes(4, "little"))
        out.extend(user_cursor.to_bytes(4, "little"))
        out.extend(int(info["primary_pre_string_len"]).to_bytes(4, "little"))
        user_cursor += int(info["slot_count"]) * 24

    out.extend(((len(page0_blocks) << 16) | len(extra_page_infos)).to_bytes(4, "little"))
    out.extend(page0_hash_offset.to_bytes(4, "little"))
    out.extend(page0_user_offset.to_bytes(4, "little"))
    out.extend(page0_primary_pre_string_len.to_bytes(4, "little"))

    for info in extra_page_infos:
        out.extend(
            _build_multi_page_mirror_page_records(
                seed,
                info["blocks"],
                info["value_offsets"],
                info["event_offsets"],
                info["event_callbacks"],
                mirror_value_count=mirror_value_count,
                mirror_descriptor_sequence=mirror_descriptor_sequence,
            )
        )
    out.extend(
        _build_multi_page_mirror_page_records(
            seed,
            page0_blocks,
            page0_value_offsets,
            page0_event_offsets,
            page0_event_callbacks,
            mirror_value_count=mirror_value_count,
            mirror_descriptor_sequence=mirror_descriptor_sequence,
        )
    )
    return bytes(out)


def _set_user_records_runtime_index(data: bytes, runtime_index: int) -> bytes:
    out = bytearray(data)
    for offset in range(0, len(out), 24):
        record = out[offset : offset + 24]
        if record and record != b"\x00" * len(record):
            out[offset + 16] = runtime_index & 0xFF
    return bytes(out)


def _build_multi_page_mirror_page_records(
    seed: _TailSeed,
    blocks: list[PageBlock],
    value_offsets: list[int],
    event_offsets: list[int],
    event_callbacks: list[dict[str, int]],
    *,
    mirror_value_count: int,
    mirror_descriptor_sequence: list[bytes],
) -> bytes:
    out = bytearray()
    slot_start = 0
    for index, (block, value_base) in enumerate(zip(blocks, value_offsets)):
        type_code = block.type_code
        object_id = _required_field_int(block, "id")
        record = bytearray(bytes([ord(type_code), object_id, 0, _record_header_flag(type_code)]) + b"\xFF" * 24)
        for event_name, callback_offset in event_callbacks[index].items():
            field_offset = _mirror_event_callback_field_offset(event_name)
            if field_offset is not None:
                record[field_offset : field_offset + 4] = callback_offset.to_bytes(4, "little")
        record.extend(value_base.to_bytes(4, "little"))
        record.extend(b"\x00\x00\x7F\x00")
        record.extend(b"\x00\x00\x00\x00")
        record.extend(_mirror_coord_payload(block))
        record.extend(event_offsets[index].to_bytes(4, "little"))
        for item in _mirror_values_for_block(
            seed,
            block,
            image_button_layout=False,
            mirror_layout_type=None,
            mirror_value_count=mirror_value_count,
            descriptor_sequence=mirror_descriptor_sequence,
        ):
            value = 0xFFFF if item is None else slot_start + item
            record.extend(value.to_bytes(2, "little"))
        expected_length = 0x38 + mirror_value_count * 2
        if len(record) != expected_length:
            raise TftToolchainError(
                f"Internal multi-page mirror record length mismatch for {block.objname}: "
                f"expected 0x{expected_length:X}, got 0x{len(record):X}"
            )
        out.extend(record)
        slot_start += _user_slot_count(block)
    return bytes(out)


def _build_event_layout(
    target_blocks: list[PageBlock],
    base_offset: int,
    *,
    image_button_layout: bool,
    post_primary_page_load: bool = False,
) -> _EventLayout:
    data = bytearray()
    offsets: list[int] = []
    callbacks: list[dict[str, int]] = []
    context = _build_event_compile_context(target_blocks)
    for index, block in enumerate(target_blocks):
        block_offset = base_offset + len(data)
        offsets.append(block_offset)
        if index == 0:
            event_data = _build_page_event_table(
                block,
                context=context,
                include_load_scripts=not post_primary_page_load,
            )
            event_data = _page_event_for_layout(event_data, image_button_layout=image_button_layout)
            callbacks.append({})
        else:
            event_data = _build_object_event_table(block, context=context)
            callbacks.append(_object_event_callback_offsets(block, block_offset, context=context))
        data.extend(event_data)
    return _EventLayout(data=bytes(data), offsets=offsets, callbacks=callbacks)


def _build_page_event_table(
    block: PageBlock,
    *,
    context: _EventCompileContext | None = None,
    include_load_scripts: bool = True,
) -> bytes:
    events = _events_by_prefix(block)
    load_lines = events.get("codesload-", []) if include_load_scripts else []
    loadend_lines = events.get("codesloadend-", []) if include_load_scripts else []
    load_phase = _compile_event_script(load_lines, context=context)
    if load_lines or loadend_lines:
        # Official TFTs separate pre-load and post-load page events with this
        # sentinel item. Empty pages omit it, which keeps seed reproduction exact.
        load_phase = load_phase[:-4] + _event_item(b"\x09\x30\x08") + _compile_event_script(loadend_lines, context=context)
    return b"".join(
        [
            load_phase,
            _event_item(b"down"),
            _compile_event_script(events.get("codesdown-", []), context=context),
            _event_item(b"up"),
            _compile_event_script(events.get("codesup-", []), context=context),
            _event_item(b"unload"),
            _compile_event_script(events.get("codesunload-", []), context=context),
        ]
    )


def _build_object_event_table(block: PageBlock, *, context: _EventCompileContext | None = None) -> bytes:
    events = _events_by_prefix(block)
    if block.type_code == VARIABLE_TYPE_CODE and not events:
        return _compile_event_script([], context=context)
    if block.type_code == "\x04":
        return b"".join(
            [
                _compile_event_script([], context=context),
                _event_item(b"playend"),
                _compile_event_script(events.get("codesplayend-", []), context=context),
            ]
        )
    parts = [
        _compile_event_script([], context=context),
        _event_item(b"down"),
        _compile_event_script(events.get("codesdown-", []), context=context),
        _event_item(b"up"),
        _compile_event_script(events.get("codesup-", []), context=context),
    ]
    if block.type_code == "\x01":
        parts.extend(
            [
                _event_item(b"slide"),
                _compile_event_script(events.get("codesslide-", []), context=context),
            ]
        )
    elif block.type_code == TIMER_TYPE_CODE:
        parts = [
            _compile_event_script([], context=context),
            _event_item(b"timer"),
            _compile_event_script(events.get("codestimer-", []), context=context),
        ]
    elif block.type_code in MEDIA_TYPE_CODES:
        parts.extend(
            [
                _event_item(b"playend"),
                _compile_event_script(events.get("codesplayend-", []), context=context),
            ]
        )
    return b"".join(parts)


def _uses_post_primary_page_load(target_blocks: list[PageBlock]) -> bool:
    if not target_blocks or not any(block.type_code in MEDIA_TYPE_CODES for block in target_blocks):
        return False
    events = _events_by_prefix(target_blocks[0])
    return bool(events.get("codesload-", []) or events.get("codesloadend-", []))


def _build_post_primary_page_event(
    target_blocks: list[PageBlock],
    *,
    context: _EventCompileContext,
    force: bool = False,
) -> bytes:
    if not (force or _uses_post_primary_page_load(target_blocks)):
        return b""
    events = _events_by_prefix(target_blocks[0])
    load_lines = events.get("codesload-", [])
    loadend_lines = events.get("codesloadend-", [])
    if not load_lines and not loadend_lines:
        return b""
    out = bytearray()
    out.extend(_code_block(bytes.fromhex("09 1f 04 35")))
    load_script = _compile_event_script(load_lines, context=context)
    out.extend(load_script[:-4])
    out.extend(_code_block(b"\x09\x30\x08"))
    out.extend(_compile_event_script(loadend_lines, context=context))
    return bytes(out)


def _object_event_callback_offsets(
    block: PageBlock,
    block_offset: int,
    *,
    context: _EventCompileContext | None,
) -> dict[str, int]:
    """Return direct event-code entry pointers used by the runtime scheduler.

    The mirror record still stores the full event table offset, but official
    TFTs also cache the first executable item for each non-empty event. Without
    these pointers, the event table is present but click/timer callbacks never
    run on device.
    """

    events = _events_by_prefix(block)
    callbacks: dict[str, int] = {}
    cursor = block_offset

    cursor += len(_compile_event_script([], context=context))
    if block.type_code == "\x04":
        cursor += len(_event_item(b"playend"))
        return callbacks
    if block.type_code == TIMER_TYPE_CODE:
        cursor += len(_event_item(b"timer"))
        if _event_script_has_payload(events.get("codestimer-", []), context=context):
            callbacks["codestimer-"] = cursor
        return callbacks

    cursor += len(_event_item(b"down"))
    down_lines = events.get("codesdown-", [])
    if _event_script_has_payload(down_lines, context=context):
        callbacks["codesdown-"] = cursor
    cursor += len(_compile_event_script(down_lines, context=context))

    cursor += len(_event_item(b"up"))
    up_lines = events.get("codesup-", [])
    if _event_script_has_payload(up_lines, context=context):
        callbacks["codesup-"] = cursor

    if block.type_code in MEDIA_TYPE_CODES:
        cursor += len(_compile_event_script(up_lines, context=context))
        cursor += len(_event_item(b"playend"))
        # The mirror callback cache slot for non-empty media playend scripts is
        # still unrecovered. Empty playend tables are emitted because official
        # media objects include the marker unconditionally.
    return callbacks


def _event_script_has_payload(lines: list[str], *, context: _EventCompileContext | None) -> bool:
    for line in lines:
        if _compile_event_line(line, context=context) is not None:
            return True
    return False


def _build_event_compile_context(target_blocks: list[PageBlock]) -> _EventCompileContext:
    field_slot_by_ref: dict[tuple[str, str], int] = {}
    slot_start = 0
    for block in target_blocks:
        name = block.objname
        if name:
            for field_name, relative_slot in EVENT_FIELD_USER_SLOTS.get(block.type_code, {}).items():
                field_slot_by_ref[(name, field_name)] = slot_start + relative_slot
        slot_start += _user_slot_count(block)
    return _EventCompileContext(field_slot_by_ref=field_slot_by_ref)


def _events_by_prefix(block: PageBlock) -> dict[str, list[str]]:
    events: dict[str, list[str]] = {}
    tokens = list(block.event_tokens)
    cursor = 0
    while cursor < len(tokens):
        name = tokens[cursor]
        cursor += 1
        if not name.startswith("codes"):
            continue
        try:
            line_count = int(name.rsplit("-", 1)[1])
        except (IndexError, ValueError):
            line_count = 0
        prefix = name.rsplit("-", 1)[0] + "-"
        lines = tokens[cursor : cursor + line_count]
        cursor += line_count
        events[prefix] = lines
    return events


def _compile_event_script(lines: list[str], *, context: _EventCompileContext | None = None) -> bytes:
    out = bytearray()
    for line in lines:
        payload = _compile_event_line(line, context=context)
        if payload is None:
            continue
        out.extend(_event_item(payload))
    out.extend(_event_item(b""))
    return bytes(out)


def _compile_event_line(line: str, *, context: _EventCompileContext | None = None) -> bytes | None:
    stripped = _strip_event_comment(line).strip()
    if not stripped or stripped.startswith("//"):
        return None

    compiled_property_event = _compile_property_event(stripped, context=context)
    if compiled_property_event is not None:
        return compiled_property_event

    lower = stripped.lower()
    if lower.startswith("page "):
        target = stripped[5:].strip()
        if not target:
            raise TftToolchainError(f"Unsupported empty page event line: {line!r}")
        return b"\x09\x0c\x04" + target.encode("ascii")

    if lower.startswith("printh "):
        payload = stripped[7:].strip()
        if not payload:
            raise TftToolchainError(f"Unsupported empty printh event line: {line!r}")
        return b"\x09\x0f\x08" + payload.encode("ascii")

    if lower.startswith("click "):
        payload = stripped[6:].strip()
        if not payload:
            raise TftToolchainError(f"Unsupported empty click event line: {line!r}")
        return b"\x09\x00\x08" + payload.encode("ascii")

    if lower.startswith("ref "):
        payload = stripped[4:].strip()
        if not payload:
            raise TftToolchainError(f"Unsupported empty ref event line: {line!r}")
        return b"\x09\x03\x04" + payload.encode("ascii")

    if lower.startswith("vis "):
        payload = stripped[4:].strip()
        if not payload:
            raise TftToolchainError(f"Unsupported empty vis event line: {line!r}")
        return b"\x09\x05\x04" + payload.encode("ascii")

    if lower.startswith("tsw "):
        payload = stripped[4:].strip()
        if not payload:
            raise TftToolchainError(f"Unsupported empty tsw event line: {line!r}")
        return b"\x09\x09\x04" + payload.encode("ascii")

    if lower.startswith("play "):
        payload = stripped[5:].strip()
        if not payload:
            raise TftToolchainError(f"Unsupported empty play event line: {line!r}")
        return b"\x09\x28\x04" + payload.encode("ascii")

    if lower.startswith("rawhex "):
        payload = stripped[7:].strip()
        if not payload:
            raise TftToolchainError(f"Unsupported empty rawhex event line: {line!r}")
        try:
            return bytes.fromhex(payload)
        except ValueError as exc:
            raise TftToolchainError(f"Invalid rawhex event payload: {line!r}") from exc

    raise TftToolchainError(
        "Unsupported event line for the current minimal logic compiler: "
        f"{line!r}. Supported V1 event commands are page/printh/click/ref/vis/tsw/play/rawhex "
        "and numeric object-field assignment/inc/dec such as tm0.en=1."
    )


def _strip_event_comment(line: str) -> str:
    return line.split("//", 1)[0]


def _compile_property_event(line: str, *, context: _EventCompileContext | None) -> bytes | None:
    global_assign = _compile_global_assignment_event(line)
    if global_assign is not None:
        return global_assign

    assign = EVENT_ASSIGN_RE.match(line)
    if assign is not None:
        object_name, field_name, value = assign.groups()
        slot = _event_field_slot(object_name, field_name, context=context, source=line)
        return b"\x01" + slot.to_bytes(4, "little") + b"=" + value.encode("ascii")

    unary = EVENT_UNARY_RE.match(line)
    if unary is not None:
        object_name, field_name, operator = unary.groups()
        slot = _event_field_slot(object_name, field_name, context=context, source=line)
        return b"\x01" + slot.to_bytes(4, "little") + operator.encode("ascii")

    return None


def _compile_global_assignment_event(line: str) -> bytes | None:
    """Compile the small fixture-proven global assignment subset.

    These opcodes are observed in Program.s startup code. Keep this as a
    whitelist rather than a generic name=value compiler; arbitrary Program.s
    variables still need separate official oracles.
    """

    global_assign = re.match(r"^volume\s*=\s*(-?\d+)\s*$", line, flags=re.IGNORECASE)
    if global_assign is not None:
        value = global_assign.group(1)
        return b"\x04\x08\x12\x00\x00=" + value.encode("ascii")

    dim_assign = re.match(r"^dim\s*=\s*(-?\d+)\s*$", line, flags=re.IGNORECASE)
    if dim_assign is not None:
        value = dim_assign.group(1)
        return b"\x04\x04\x10\x00\x00=" + value.encode("ascii")

    recmod_assign = re.match(r"^recmod\s*=\s*(-?\d+)\s*$", line, flags=re.IGNORECASE)
    if recmod_assign is not None:
        value = recmod_assign.group(1)
        return b"\x04\x08\x0f\x00\x00=" + value.encode("ascii")

    baud_assign = re.match(r"^baud\s*=\s*(\d+)\s*$", line, flags=re.IGNORECASE)
    if baud_assign is not None:
        value = int(baud_assign.group(1))
        if value != 9600:
            raise TftToolchainError(
                "Unsupported Program.s baud assignment for the current minimal compiler: "
                f"baud={value}. Only official fixture-proven baud=9600 is enabled."
            )
        return b"\x04\x04\x30\x00\x00=\x03" + value.to_bytes(4, "little")

    return None


def _event_field_slot(
    object_name: str,
    field_name: str,
    *,
    context: _EventCompileContext | None,
    source: str,
) -> int:
    if context is None:
        raise TftToolchainError(f"Event line {source!r} requires a compiled object context")
    slot = context.field_slot_by_ref.get((object_name, field_name))
    if slot is None:
        raise TftToolchainError(
            f"Unsupported event field reference {object_name}.{field_name!s} in {source!r}. "
            "Only recovered numeric fields can be compiled currently."
        )
    return slot


def _event_item(payload: bytes) -> bytes:
    return len(payload).to_bytes(4, "little") + payload


def _build_primary_block(
    seed: _TailSeed,
    target_blocks: list[PageBlock],
    *,
    event_callbacks: list[dict[str, int]],
) -> tuple[bytes, list[int], dict[int, int], int]:
    object_count = len(target_blocks)
    mixed_compact_primary = _uses_mixed_compact_primary_layout(seed, target_blocks)
    first_value = 0x10 + object_count * 4
    value_offsets: list[int] = []
    cursor = first_value
    for block in target_blocks:
        value_offsets.append(cursor)
        cursor += _primary_record_length(block.type_code, mixed_compact=mixed_compact_primary)

    primary_pre_string_len = object_count * 4 + sum(
        _primary_record_length(block.type_code, mixed_compact=mixed_compact_primary)
        for block in target_blocks
    )
    data = bytearray(b"".join(value.to_bytes(4, "little") for value in value_offsets))
    text_slots: list[tuple[str, int]] = []
    text_pointer_by_id: dict[int, int] = {}
    string_cursor = 0
    consumed_string_suffix_padding = 0
    compact_tail_layout = any(block.type_code in COMPACT_STRING_LAYOUT_TYPES for block in target_blocks)
    media_layout_type = _primary_media_layout_type(target_blocks)
    string_prefix_padding = (
        _primary_media_padding(seed.primary_string_prefix_paddings, media_layout_type)
        if media_layout_type is not None
        else 0
    )
    string_pointer_bias = 0x10 if compact_tail_layout else 0x14
    for index, (block, value_base) in enumerate(zip(target_blocks, value_offsets)):
        type_code = block.type_code
        record = bytearray(seed.primary_templates[type_code])
        object_id = _required_field_int(block, "id")
        record[0] = ord(type_code)
        record[1] = object_id
        record[2] = 0
        record[3] = _record_header_flag(type_code)
        _apply_event_callback_fields(record, event_callbacks[index])
        if type_code == TIMER_TYPE_CODE:
            _patch_timer_record(record, block)
        elif type_code == VARIABLE_TYPE_CODE:
            pass
        elif type_code in NON_VISUAL_COORD_TYPES:
            pass
        else:
            record[0x1C:0x20] = value_base.to_bytes(4, "little")
            record[0x28:0x34] = _coord_payload(block)
        if type_code == "t":
            _patch_text_record(record, block)
        elif type_code == "b":
            _patch_button_record(record, block)
        elif type_code == "6":
            _patch_number_record(record, block)
        elif type_code == ";":
            _patch_xfloat_record(record, block)
        elif type_code == "=":
            _patch_combobox_record(record, block)
        elif type_code == "\x01":
            _patch_slider_record(record, block)
        elif type_code == "z":
            _patch_gauge_record(record, block)
        elif type_code == "j":
            _patch_progress_record(record, block)
        elif type_code == "5":
            _patch_dual_state_button_record(record, block)
        elif type_code == "C":
            _patch_state_button_record(record, block)
        elif type_code == "8":
            _patch_checkbox_record(record, block)
        elif type_code == "9":
            _patch_radio_record(record, block)
        elif type_code == VARIABLE_TYPE_CODE:
            _patch_variable_record(record, block)
        string_fields = _string_pointer_fields(block)
        if string_fields:
            pointer_map: dict[str, int] = {}
            for field_name, pointer_offset, slot_len in string_fields:
                if media_layout_type == "\x04" and type_code == "t" and field_name == "txt":
                    extra_slot = _primary_media_padding(seed.primary_string_suffix_paddings, media_layout_type)
                    slot_len += extra_slot
                    consumed_string_suffix_padding += extra_slot
                text = _field_text(block, field_name) or ""
                pointer = primary_pre_string_len + string_pointer_bias + string_prefix_padding + string_cursor
                pointer_map[field_name] = pointer
                record[pointer_offset : pointer_offset + 4] = pointer.to_bytes(4, "little")
                text_slots.append((text, slot_len))
                string_cursor += slot_len
            if set(pointer_map) == {"txt"}:
                text_pointer_by_id[object_id] = pointer_map["txt"]
            else:
                text_pointer_by_id[object_id] = pointer_map
        elif type_code == "p":
            picture_id = _field_int(block, "pic") or 0
            record[0x38:0x3A] = picture_id.to_bytes(2, "little")
        elif type_code in {"\x02", "\x03", "\x04"}:
            _patch_media_record(record, block)
        data.extend(record[: _primary_record_length(type_code, mixed_compact=mixed_compact_primary)])

    if not compact_tail_layout:
        data.extend(b"\x00\x00\x00\x00")
        if media_layout_type is not None:
            data.extend(b"\x00" * string_prefix_padding)
    for text, slot_len in text_slots:
        encoded = _encode_display_text(text)
        if len(encoded) > slot_len:
            raise TftToolchainError(f"Text {text!r} exceeds compiled text slot length {slot_len}")
        data.extend(encoded.ljust(slot_len, b"\x00"))
    if media_layout_type is not None:
        suffix_padding = _primary_media_padding(seed.primary_string_suffix_paddings, media_layout_type)
        data.extend(b"\x00" * max(0, suffix_padding - consumed_string_suffix_padding))
    data.extend(_primary_final_marker(seed, target_blocks, value_offsets))
    _patch_waveform_primary_runtime_anchors(
        data,
        target_blocks,
        value_offsets,
        mixed_compact_primary=mixed_compact_primary,
    )
    mirror_pre_string_len = primary_pre_string_len - 4 if compact_tail_layout else primary_pre_string_len
    return bytes(data), value_offsets, text_pointer_by_id, mirror_pre_string_len


def _primary_final_marker(
    seed: _TailSeed,
    target_blocks: list[PageBlock],
    value_offsets: list[int],
) -> bytes:
    for block in target_blocks:
        if block.type_code == "\x00":
            # Official append and mixed fixtures keep this marker stable even
            # when the waveform object's value record moves later in the page.
            return (0x114).to_bytes(4, "little")
    media_layout_type = _primary_media_layout_type(target_blocks)
    if media_layout_type is not None:
        return seed.primary_final_markers.get(
            media_layout_type,
            seed.primary_final_markers.get("", b"\x00\x00\x00\x00"),
        )
    return b"\x00\x00\x00\x00"


def _primary_media_padding(paddings: dict[str, int], media_layout_type: str) -> int:
    return paddings.get(media_layout_type, paddings.get("", 0))


def _primary_media_layout_type(target_blocks: list[PageBlock]) -> str | None:
    for block in target_blocks:
        if block.type_code in MEDIA_TYPE_CODES:
            return block.type_code
    return None


def _patch_waveform_primary_runtime_anchors(
    data: bytearray,
    target_blocks: list[PageBlock],
    value_offsets: list[int],
    *,
    mixed_compact_primary: bool,
) -> None:
    primary_size = len(data)
    for block, value_offset in zip(target_blocks, value_offsets):
        if block.type_code != "\x00":
            continue
        record_length = _primary_record_length(block.type_code, mixed_compact=mixed_compact_primary)
        record_start = value_offset - 0x10
        anchor_offset = record_start + record_length - 4
        data[anchor_offset : anchor_offset + 4] = (primary_size + 0x0C).to_bytes(4, "little")


def _primary_record_length(type_code: str, *, mixed_compact: bool) -> int:
    length = TYPE_RECORD_LENGTHS[type_code]
    if mixed_compact and type_code in MIXED_COMPACT_PRIMARY_TYPES:
        return length - 4
    return length


def _apply_event_callback_fields(record: bytearray, callbacks: dict[str, int]) -> None:
    for event_name, callback_offset in callbacks.items():
        field_offset = _mirror_event_callback_field_offset(event_name)
        if field_offset is not None:
            record[field_offset : field_offset + 4] = callback_offset.to_bytes(4, "little")


def _patch_text_record(record: bytearray, block: PageBlock) -> None:
    sta = _field_int(block, "sta")
    if sta is not None:
        record[0x38] = sta & 0xFF
    style = _field_int(block, "style")
    if style is not None:
        record[0x39] = style & 0xFF

    # Text records are shorter than button records because the text pointer
    # starts at 0x48. The proven runtime fields live immediately before it.
    _write_record_u16_from_field(record, 0x3A, block, "borderc")
    # Official 1.67.6 TFTs leave the byte at 0x3C zero even when the HMI .pa
    # borderw field contains the editor default, so keep that template byte.
    _write_record_u8_from_field(record, 0x3D, block, "font")

    if sta == 2:
        _write_record_u16_from_field(record, 0x3E, block, "pic")
    elif sta == 0:
        _write_record_u16_from_field(record, 0x3E, block, "picc")
    else:
        _write_record_u16_from_field(record, 0x3E, block, "bco")

    _write_record_u16_from_field(record, 0x40, block, "pco")
    _write_record_u8_from_field(record, 0x42, block, "xcen")
    _write_record_u8_from_field(record, 0x43, block, "ycen")
    _write_record_u8_from_field(record, 0x44, block, "pw")
    _write_record_u16_from_field(record, 0x46, block, "txt_maxl")


def _patch_button_record(record: bytearray, block: PageBlock) -> None:
    sta = _field_int(block, "sta")
    if sta is not None:
        record[0x38] = sta & 0xFF
    style = _field_int(block, "style")
    if sta == 2:
        record[0x39] = 0
    elif style is not None:
        record[0x39] = style & 0xFF

    # The compiled button record reuses the two 16-bit background slots at
    # 0x3E/0x40 depending on sta: solid color uses bco/bco2, full-image uses
    # pic/pic2, and crop-image uses picc/picc2.
    if sta == 2:
        _write_record_u16_from_field(record, 0x3E, block, "pic")
        _write_record_u16_from_field(record, 0x40, block, "pic2", fallback_field="pic")
    elif sta == 0:
        _write_record_u16_from_field(record, 0x3E, block, "picc")
        _write_record_u16_from_field(record, 0x40, block, "picc2", fallback_field="picc")
    else:
        _write_record_u16_from_field(record, 0x3E, block, "bco")
        _write_record_u16_from_field(record, 0x40, block, "bco2")

    _write_record_u16_from_field(record, 0x42, block, "pco")
    _write_record_u16_from_field(record, 0x44, block, "pco2")
    _write_record_u8_from_field(record, 0x46, block, "xcen")
    _write_record_u8_from_field(record, 0x47, block, "ycen")
    _write_record_u16_from_field(record, 0x4A, block, "txt_maxl")


def _patch_number_record(record: bytearray, block: PageBlock) -> None:
    sta = _field_int(block, "sta")
    if sta is not None:
        record[0x38] = sta & 0xFF
    style = _field_int(block, "style")
    if style is not None:
        record[0x39] = style & 0xFF

    _write_record_u16_from_field(record, 0x3A, block, "borderc")
    _write_record_u8_from_field(record, 0x3D, block, "font")

    if sta == 2:
        _write_record_u16_from_field(record, 0x3E, block, "pic")
    elif sta == 0:
        _write_record_u16_from_field(record, 0x3E, block, "picc")
    else:
        _write_record_u16_from_field(record, 0x3E, block, "bco")

    _write_record_u16_from_field(record, 0x40, block, "pco")
    _write_record_u8_from_field(record, 0x42, block, "xcen")
    _write_record_u8_from_field(record, 0x43, block, "ycen")
    value = _field_int(block, "val")
    if value is not None:
        record[0x44:0x48] = (value & 0xFFFFFFFF).to_bytes(4, "little")
    _write_record_u16_from_field(record, 0x48, block, "lenth")
    _write_record_u16_from_field(record, 0x4A, block, "format")
    _write_record_u16_from_field(record, 0x4C, block, "isbr")
    _write_record_u16_from_field(record, 0x4E, block, "spax")
    _write_record_u16_from_field(record, 0x50, block, "spay")


def _patch_xfloat_record(record: bytearray, block: PageBlock) -> None:
    sta = _field_int(block, "sta")
    if sta is not None:
        record[0x38] = sta & 0xFF
    style = _field_int(block, "style")
    if style is not None:
        record[0x39] = style & 0xFF

    _write_record_u16_from_field(record, 0x3A, block, "borderc")
    _write_record_u8_from_field(record, 0x3D, block, "font")

    if sta == 2:
        _write_record_u16_from_field(record, 0x3E, block, "pic")
    elif sta == 0:
        _write_record_u16_from_field(record, 0x3E, block, "picc")
    else:
        _write_record_u16_from_field(record, 0x3E, block, "bco")

    _write_record_u16_from_field(record, 0x40, block, "pco")
    _write_record_u8_from_field(record, 0x42, block, "xcen")
    _write_record_u8_from_field(record, 0x43, block, "ycen")
    value = _field_int(block, "val")
    if value is not None:
        record[0x44:0x48] = (value & 0xFFFFFFFF).to_bytes(4, "little")
    _write_record_u8_from_field(record, 0x48, block, "vvs0")
    _write_record_u8_from_field(record, 0x49, block, "vvs1")
    _write_record_u8_from_field(record, 0x4C, block, "isbr")
    _write_record_u8_from_field(record, 0x4D, block, "spax")
    _write_record_u8_from_field(record, 0x4E, block, "spay")


def _patch_combobox_record(record: bytearray, block: PageBlock) -> None:
    sta = _field_int(block, "sta")
    if sta is not None:
        record[0x38] = sta & 0xFF
    style = _field_int(block, "style")
    if style is not None:
        record[0x39] = style & 0xFF

    _write_record_u16_from_field(record, 0x3A, block, "borderc")
    _write_record_u8_from_field(record, 0x3D, block, "font")

    if sta == 2:
        _write_record_u16_from_field(record, 0x3E, block, "pic")
    elif sta == 0:
        _write_record_u16_from_field(record, 0x3E, block, "picc")
    else:
        _write_record_u16_from_field(record, 0x3E, block, "bco")

    _write_record_u16_from_field(record, 0x40, block, "pco")
    _write_record_u8_from_field(record, 0x42, block, "xcen")
    _write_record_u8_from_field(record, 0x43, block, "ycen")
    _write_record_u8_from_field(record, 0x44, block, "spax")
    _write_record_u8_from_field(record, 0x45, block, "dis")
    _write_record_u16_from_field(record, 0x46, block, "txt_maxl")
    _write_record_u8_from_field(record, 0x4C, block, "up")
    _write_record_u16_from_field(record, 0x4E, block, "pco3")
    _write_record_u16_from_field(record, 0x50, block, "pco1")
    _write_record_u16_from_field(record, 0x52, block, "bco1")
    _write_record_u16_from_field(record, 0x56, block, "path_m")
    _write_record_u8_from_field(record, 0x5C, block, "dir")
    _write_record_u8_from_field(record, 0x5D, block, "qty")
    _write_record_u8_from_field(record, 0x5E, block, "vvs0")
    _write_record_u8_from_field(record, 0x5F, block, "val")
    _write_record_u16_from_field(record, 0x60, block, "bco2")
    _write_record_u16_from_field(record, 0x62, block, "pco2")
    _write_record_u8_from_field(record, 0x64, block, "hig")
    _write_record_u8_from_field(record, 0x65, block, "down")
    _write_record_u8_from_field(record, 0x66, block, "mode")
    _write_record_u8_from_field(record, 0x67, block, "wid")
    _write_record_u8_from_field(record, 0x68, block, "vvs1")
    _write_record_u8_from_field(record, 0x69, block, "ch")
    _write_record_u8_from_field(record, 0x6A, block, "drastate")


def _patch_timer_record(record: bytearray, block: PageBlock) -> None:
    tim = _field_int(block, "tim")
    if tim is not None:
        record[0x1C:0x1E] = (tim & 0xFFFF).to_bytes(2, "little")
    en = _field_int(block, "en")
    if en is not None:
        record[0x1E] = en & 0xFF


def _patch_media_record(record: bytearray, block: PageBlock) -> None:
    _write_record_u16_from_field(record, 0x38, block, "vid")
    _write_record_u8_from_field(record, 0x3A, block, "en")
    _write_record_u8_from_field(record, 0x3B, block, "loop")
    _write_record_u8_from_field(record, 0x3C, block, "fps")
    _write_record_u16_from_field(record, 0x3E, block, "dis")
    _write_record_u32_from_field(record, 0x40, block, "tim")
    _write_record_u32_from_field(record, 0x44, block, "stim")
    _write_record_u32_from_field(record, 0x48, block, "qty")


def _patch_slider_record(record: bytearray, block: PageBlock) -> None:
    _write_record_u8_from_field(record, 0x38, block, "mode")
    _write_record_u8_from_field(record, 0x39, block, "sta")
    _write_record_u8_from_field(record, 0x3A, block, "psta")
    _write_record_u8_from_field(record, 0x3B, block, "wid")
    _write_record_u8_from_field(record, 0x3C, block, "hig")
    _write_record_u8_from_field(record, 0x3D, block, "dis")
    _write_record_u16_from_field(record, 0x3E, block, "bco")
    _write_record_u16_from_field(record, 0x40, block, "pco")
    _write_record_u16_from_field(record, 0x42, block, "val")
    _write_record_u16_from_field(record, 0x44, block, "maxval")
    _write_record_u16_from_field(record, 0x46, block, "minval")
    _write_record_u8_from_field(record, 0x48, block, "ch")


def _patch_gauge_record(record: bytearray, block: PageBlock) -> None:
    _write_record_u8_from_field(record, 0x38, block, "sta")
    _write_record_u16_from_field(record, 0x3C, block, "val")
    _write_record_u16_from_field(record, 0x3E, block, "format")
    _write_record_u16_from_field(record, 0x40, block, "up")
    _write_record_u16_from_field(record, 0x42, block, "down")
    _write_record_u16_from_field(record, 0x44, block, "left")
    _write_record_u16_from_field(record, 0x46, block, "pco")
    _write_record_u16_from_field(record, 0x48, block, "pco2")
    _write_record_u8_from_field(record, 0x4A, block, "hig")
    _write_record_u8_from_field(record, 0x4C, block, "wid")
    _write_record_u8_from_field(record, 0x4D, block, "vvs0")
    _write_record_u8_from_field(record, 0x4E, block, "vvs1")
    _write_record_u8_from_field(record, 0x4F, block, "vvs2")


def _patch_progress_record(record: bytearray, block: PageBlock) -> None:
    _write_record_u8_from_field(record, 0x38, block, "sta")
    _write_record_u8_from_field(record, 0x39, block, "dez")
    _write_record_u8_from_field(record, 0x3A, block, "val")
    _write_record_u8_from_field(record, 0x3B, block, "dis")
    _write_record_u16_from_field(record, 0x3C, block, "bco")
    _write_record_u16_from_field(record, 0x3E, block, "pco")


def _patch_dual_state_button_record(record: bytearray, block: PageBlock) -> None:
    _write_record_u8_from_field(record, 0x38, block, "sta")
    _write_record_u8_from_field(record, 0x39, block, "style")
    _write_record_u16_from_field(record, 0x3A, block, "borderc")
    _write_record_u16_from_field(record, 0x3E, block, "bco")
    _write_record_u16_from_field(record, 0x40, block, "bco2")
    _write_record_u16_from_field(record, 0x42, block, "pco")
    _write_record_u16_from_field(record, 0x44, block, "pco2")
    _write_record_u8_from_field(record, 0x46, block, "xcen")
    _write_record_u8_from_field(record, 0x47, block, "ycen")
    _write_record_u8_from_field(record, 0x48, block, "val")
    _write_record_u16_from_field(record, 0x4A, block, "txt_maxl")
    _write_record_u16_from_field(record, 0x4C, block, "isbr")
    _write_record_u16_from_field(record, 0x4E, block, "spax")
    _write_record_u16_from_field(record, 0x50, block, "spay")


def _patch_state_button_record(record: bytearray, block: PageBlock) -> None:
    _write_record_u8_from_field(record, 0x38, block, "dez")
    _write_record_u8_from_field(record, 0x39, block, "val")
    _write_record_u16_from_field(record, 0x3A, block, "bco")
    _write_record_u16_from_field(record, 0x3C, block, "pco")
    _write_record_u16_from_field(record, 0x3E, block, "bco2")
    _write_record_u16_from_field(record, 0x40, block, "pco2")
    _write_record_u16_from_field(record, 0x42, block, "pco1")
    _write_record_u8_from_field(record, 0x44, block, "font")
    _write_record_u8_from_field(record, 0x45, block, "dis")
    _write_record_u16_from_field(record, 0x46, block, "txt_maxl")


def _patch_checkbox_record(record: bytearray, block: PageBlock) -> None:
    _write_record_u8_from_field(record, 0x38, block, "style")
    # Official 1.67.6 keeps this byte zero even when .pa borderw is 2.
    _write_record_u16_from_field(record, 0x3A, block, "borderc")
    _write_record_u16_from_field(record, 0x3C, block, "bco")
    _write_record_u16_from_field(record, 0x3E, block, "pco")
    _write_record_u8_from_field(record, 0x40, block, "val")


def _patch_radio_record(record: bytearray, block: PageBlock) -> None:
    _write_record_u16_from_field(record, 0x38, block, "bco")
    _write_record_u16_from_field(record, 0x3A, block, "pco")
    _write_record_u8_from_field(record, 0x3C, block, "val")


def _patch_variable_record(record: bytearray, block: PageBlock) -> None:
    value = _field_int(block, "val")
    if value is not None:
        record[0x0C:0x10] = (value & 0xFFFFFFFF).to_bytes(4, "little")


def _write_record_u16_from_field(
    record: bytearray,
    offset: int,
    block: PageBlock,
    field_name: str,
    *,
    fallback_field: str | None = None,
) -> None:
    value = _field_int(block, field_name)
    if value is None and fallback_field is not None:
        value = _field_int(block, fallback_field)
    if value is None:
        return
    record[offset : offset + 2] = (value & 0xFFFF).to_bytes(2, "little")


def _write_record_u8_from_field(record: bytearray, offset: int, block: PageBlock, field_name: str) -> None:
    value = _field_int(block, field_name)
    if value is None:
        return
    record[offset] = value & 0xFF


def _write_record_u32_from_field(record: bytearray, offset: int, block: PageBlock, field_name: str) -> None:
    value = _field_int(block, field_name)
    if value is None:
        return
    record[offset : offset + 4] = (value & 0xFFFFFFFF).to_bytes(4, "little")


def _build_user_records(
    seed: _TailSeed,
    target_blocks: list[PageBlock],
    value_offsets: list[int],
    text_pointer_by_id: dict[int, Any],
    *,
    max_picture_id: int | None,
) -> bytes:
    out = bytearray()
    for block, value_base in zip(target_blocks, value_offsets):
        type_code = block.type_code
        object_id = _required_field_int(block, "id")
        slots = [b"\x00" * 24 for _ in range(_user_slot_count(block))]
        for template in _user_record_templates_for_block(seed, block):
            if template.slot_index >= len(slots):
                continue
            if template.word1_mode == "text_pointer":
                word1 = _object_text_pointer(text_pointer_by_id, object_id, "txt")
            elif template.word1_mode == "path_pointer":
                word1 = _object_text_pointer(text_pointer_by_id, object_id, "path")
            elif template.word1_mode == "absolute":
                word1 = template.word1_delta
            else:
                word1 = value_base + template.word1_delta
            word2 = _user_record_word2(template, block, max_picture_id=max_picture_id)
            words = [
                value_base,
                word1,
                word2,
                template.word3,
                _user_record_word4(template, block, object_id),
                template.word5,
            ]
            slots[template.slot_index] = b"".join(word.to_bytes(4, "little") for word in words)
        out.extend(b"".join(slots))
    return bytes(out)


def _user_record_word4(template: _UserRecordTemplate, block: PageBlock, object_id: int) -> int:
    if block.type_code == VARIABLE_TYPE_CODE:
        return template.word4
    return (template.word4 & 0xFFFF00FF) | (object_id << 8)


def _user_record_word2(
    template: _UserRecordTemplate,
    block: PageBlock,
    *,
    max_picture_id: int | None,
) -> int:
    if max_picture_id is None:
        return template.word2
    if block.type_code == "p" and template.slot_index == 19:
        return max_picture_id
    if block.type_code == "b" and _field_int(block, "sta") == 2 and template.slot_index in {21, 22}:
        return max_picture_id
    return template.word2


def _max_picture_id(blocks: list[PageBlock]) -> int | None:
    values: list[int] = []
    for block in blocks:
        for field_name in ("pic", "picc", "pic2", "picc2"):
            value = _field_int(block, field_name)
            if value is not None and value != 0xFFFF:
                values.append(value)
    return max(values) if values else None


def _uses_full_image_button_layout(blocks: list[PageBlock]) -> bool:
    return any(block.type_code == "b" and _field_int(block, "sta") == 2 for block in blocks)


def _prefix_insertions_for_blocks(seed: _TailSeed, blocks: list[PageBlock]) -> list[tuple[int, bytes]]:
    type_insertions = [
        seed.prefix_inserts[type_code]
        for type_code in sorted({block.type_code for block in blocks})
        if seed.prefix_inserts.get(type_code)
    ]
    if len(type_insertions) <= 1:
        return [item for insertions in type_insertions for item in insertions]

    descriptor_insertions = _mixed_descriptor_insertions_for_blocks(seed, blocks)
    if descriptor_insertions is not None:
        return descriptor_insertions

    insertions: list[tuple[int, bytes]] = []
    for items in type_insertions:
        insertions.extend(_descriptor_insertions(items))
    return insertions


def _mixed_descriptor_insertions_for_blocks(
    seed: _TailSeed,
    blocks: list[PageBlock],
) -> list[tuple[int, bytes]] | None:
    desired: set[bytes] = set(seed.mirror_descriptor_sequences[""])
    for type_code in {block.type_code for block in blocks}:
        desired.update(seed.mirror_descriptor_sequences.get(type_code, []))

    _augment_official_mixed_layout(seed)
    candidates = [
        sequence
        for key, sequence in seed.mirror_descriptor_sequences.items()
        if key in OFFICIAL_MIXED_DESCRIPTOR_LAYOUTS and desired.issubset(set(sequence))
    ]
    if not candidates:
        return None

    canonical_order = min(candidates, key=len)
    desired_sequence = [descriptor for descriptor in canonical_order if descriptor in desired]
    return _descriptor_insertions_from_sequence(seed.mirror_descriptor_sequences[""], desired_sequence)


def _augment_official_mixed_layout(seed: _TailSeed) -> None:
    for layout_key, case_name in OFFICIAL_MIXED_DESCRIPTOR_LAYOUTS.items():
        _augment_official_descriptor_layout(seed, layout_key, case_name)


def _augment_official_descriptor_layout(seed: _TailSeed, layout_key: str, case_name: str) -> None:
    if layout_key in seed.mirror_descriptor_sequences:
        return
    case_root = Path(DEFAULT_CASE_ROOT)
    case_dir = case_root / case_name
    case_tft = case_dir / "lcd_test.tft"
    case_hmi = case_dir / "lcd_test.HMI"
    if not case_tft.exists() or not case_hmi.exists():
        return
    try:
        case_page = _load_hmi_page0(case_hmi)
        case_seed = _load_tail_seed(case_tft, case_hmi, case_page)
    except TftToolchainError:
        return
    seed.mirror_descriptor_sequences[layout_key] = _prefix_descriptor_sequence(
        case_seed.compiled_prefix
    )
    seed.mirror_layout_templates[layout_key] = {
        type_code: list(values)
        for type_code, values in case_seed.mirror_templates.items()
    }


def _descriptor_insertions_from_sequence(
    base_sequence: list[bytes],
    desired_sequence: list[bytes],
) -> list[tuple[int, bytes]]:
    insertions: list[tuple[int, bytes]] = []
    base_index = 0
    for descriptor in desired_sequence:
        if base_index < len(base_sequence) and descriptor == base_sequence[base_index]:
            base_index += 1
            continue
        insertions.append((PREFIX_DESCRIPTOR_START + base_index * 4, descriptor))
    return insertions


def _uses_mixed_compact_primary_layout(seed: _TailSeed, blocks: list[PageBlock]) -> bool:
    contributing_types = [
        type_code
        for type_code in {block.type_code for block in blocks}
        if seed.prefix_inserts.get(type_code)
    ]
    return len(contributing_types) > 1


def _descriptor_insertions(insertions: list[tuple[int, bytes]]) -> list[tuple[int, bytes]]:
    expanded: list[tuple[int, bytes]] = []
    for offset, payload in insertions:
        if len(payload) % 4:
            expanded.append((offset, payload))
            continue
        for cursor in range(0, len(payload), 4):
            expanded.append((offset + cursor, payload[cursor : cursor + 4]))
    return expanded


def _single_media_descriptor_sequence(seed: _TailSeed, blocks: list[PageBlock]) -> list[bytes] | None:
    media_types = {
        block.type_code
        for block in blocks
        if block.type_code in MEDIA_TYPE_CODES
    }
    if len(media_types) != 1:
        return None
    media_type = next(iter(media_types))
    return seed.mirror_descriptor_sequences.get(media_type)


def _derive_prefix_insertions_for_case(
    seed: _TailSeed,
    case_seed: _TailSeed,
    case_page: Any,
) -> list[tuple[int, bytes]]:
    image_button_layout = _uses_full_image_button_layout(case_page.blocks)
    generated_head = _prefix_head_for_layout(
        seed.prefix_head,
        image_button_layout=image_button_layout,
        extra_insertions=[],
    )
    generated_layout = _build_event_layout(
        case_page.blocks,
        len(generated_head),
        image_button_layout=image_button_layout,
    )
    generated_prefix = generated_head + generated_layout.data
    actual_prefix = case_seed.compiled_prefix

    insertions: list[tuple[int, bytes]] = []
    matcher = SequenceMatcher(None, generated_prefix, actual_prefix, autojunk=False)
    for tag, first_start, first_end, second_start, second_end in matcher.get_opcodes():
        if tag == "insert":
            insertions.append(
                _canonical_prefix_insertion(
                    generated_prefix,
                    first_start,
                    actual_prefix[second_start:second_end],
                )
            )

    patched = _apply_prefix_insertions(generated_prefix, insertions)
    if patched != actual_prefix:
        raise TftToolchainError(
            f"Unable to derive exact TFT prefix insertions from {case_seed.baseline_tft}"
        )
    return insertions


def _mirror_layout_type_for_blocks(seed: _TailSeed, blocks: list[PageBlock]) -> str | None:
    if _uses_mixed_compact_primary_layout(seed, blocks):
        for layout_key in OFFICIAL_MIXED_DESCRIPTOR_LAYOUTS:
            if layout_key in seed.mirror_layout_templates and all(
                block.type_code in seed.mirror_layout_templates[layout_key] for block in blocks
            ):
                return layout_key
    candidates = [
        block.type_code
        for block in blocks
        if block.type_code in seed.mirror_layout_templates
    ]
    if not candidates:
        return None
    return max(
        sorted(set(candidates)),
        key=lambda type_code: max(len(values) for values in seed.mirror_layout_templates[type_code].values()),
    )


def _mirror_value_count_for_layout(
    seed: _TailSeed,
    blocks: list[PageBlock],
    *,
    image_button_layout: bool,
    mirror_layout_type: str | None,
    descriptor_sequence: list[bytes] | None = None,
) -> int:
    if descriptor_sequence is not None and not image_button_layout:
        return len(descriptor_sequence)
    layout_templates = seed.mirror_layout_templates.get(mirror_layout_type or "", {})
    widths = [
        len(layout_templates.get(block.type_code, seed.mirror_templates[block.type_code]))
        for block in blocks
    ]
    if image_button_layout:
        widths.append(IMAGE_BUTTON_MIRROR_VALUE_COUNT)
    return max(widths, default=MIRROR_VALUE_COUNT)


def _prefix_head_for_layout(
    prefix_head: bytes,
    *,
    image_button_layout: bool,
    extra_insertions: list[tuple[int, bytes]],
    descriptor_sequence: list[bytes] | None = None,
) -> bytes:
    patched = _apply_prefix_insertions(prefix_head, list(extra_insertions))
    if descriptor_sequence is not None:
        if image_button_layout:
            raise TftToolchainError("Descriptor-sequence replacement is not supported with image-button layout yet")
        patched = _replace_prefix_descriptor_sequence(patched, descriptor_sequence)
    if not image_button_layout:
        return patched
    offset = IMAGE_BUTTON_PREFIX_INSERT_OFFSET + _prefix_inserted_bytes_before(
        extra_insertions,
        IMAGE_BUTTON_PREFIX_INSERT_OFFSET,
    )
    if len(patched) <= offset + len(IMAGE_BUTTON_PREFIX_INSERT):
        raise TftToolchainError("TFT prefix template is too short for image-button layout patch")
    if patched[offset : offset + len(IMAGE_BUTTON_PREFIX_INSERT)] == IMAGE_BUTTON_PREFIX_INSERT:
        return patched

    out = bytearray(
        patched[:offset]
        + IMAGE_BUTTON_PREFIX_INSERT
        + patched[offset:]
    )
    del out[len(patched) :]
    _add_prefix_u32(out, 0x00, 4)
    _add_prefix_u32(out, 0x24, 4)
    return bytes(out)


def _replace_prefix_descriptor_sequence(prefix: bytes, descriptor_sequence: list[bytes]) -> bytes:
    end = int.from_bytes(prefix[:4], "little")
    if end < PREFIX_DESCRIPTOR_START or end > len(prefix):
        raise TftToolchainError("TFT prefix descriptor table has an invalid end offset")
    descriptor_bytes = b"".join(descriptor_sequence)
    old_size = end - PREFIX_DESCRIPTOR_START
    if old_size == len(descriptor_bytes) and prefix[PREFIX_DESCRIPTOR_START:end] == descriptor_bytes:
        return prefix
    out = bytearray(prefix[:PREFIX_DESCRIPTOR_START] + descriptor_bytes + prefix[end:])
    delta = len(descriptor_bytes) - old_size
    if delta:
        _add_prefix_u32(out, 0x00, delta)
        _add_prefix_u32(out, 0x24, delta)
    return bytes(out)


def _prefix_inserted_bytes_before(insertions: list[tuple[int, bytes]], offset: int) -> int:
    seen: set[tuple[int, bytes]] = set()
    total = 0
    for item_offset, payload in insertions:
        item = (item_offset, payload)
        if item in seen:
            continue
        seen.add(item)
        if item_offset < offset:
            total += len(payload)
    return total


def _apply_prefix_insertions(prefix: bytes, insertions: list[tuple[int, bytes]]) -> bytes:
    if not insertions:
        return prefix
    deduped: list[tuple[int, bytes]] = []
    seen: set[tuple[int, bytes]] = set()
    for item in insertions:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    deduped.sort(key=lambda item: item[0])
    patched = bytearray(prefix)
    shift = 0
    for offset, payload in deduped:
        if not payload:
            continue
        if offset < 0 or offset > len(prefix):
            raise TftToolchainError(f"TFT prefix insertion offset out of range: 0x{offset:X}")
        cursor = offset + shift
        patched[cursor:cursor] = payload
        shift += len(payload)
    if shift:
        _add_prefix_u32(patched, 0x00, shift)
        _add_prefix_u32(patched, 0x24, shift)
    return bytes(patched)


def _canonical_prefix_insertion(prefix: bytes, offset: int, payload: bytes) -> tuple[int, bytes]:
    """Choose a stable representation for ambiguous repeated-byte insertions.

    SequenceMatcher may report the same official insertion at two neighboring
    offsets when the payload repeats bytes already present in the seed prefix.
    Single-control cases still reproduce exactly either way, but mixed layouts
    must dedupe these equivalent insertions before applying several control
    templates at once.
    """

    while payload and offset < len(prefix) and payload[0] == prefix[offset]:
        payload = payload[1:] + prefix[offset : offset + 1]
        offset += 1
    return offset, payload


def _add_prefix_u32(buffer: bytearray, offset: int, delta: int) -> None:
    value = int.from_bytes(buffer[offset : offset + 4], "little")
    buffer[offset : offset + 4] = (value + delta).to_bytes(4, "little")


def _page_event_for_layout(page_event: bytes, *, image_button_layout: bool) -> bytes:
    if not image_button_layout:
        return page_event

    # TJC 1.67.6 adds one empty page-event block before the normal down/up
    # entries when a full-image button (sta=2) is present. The body is still
    # a sequence of length-prefixed event strings, so a zero-length block is
    # just four zero bytes after the leading load event.
    extra_empty_event = b"\x00\x00\x00\x00"
    if page_event.startswith(extra_empty_event * 2):
        return page_event
    if page_event.startswith(extra_empty_event):
        return page_event[:4] + extra_empty_event + page_event[4:]
    return extra_empty_event + page_event


def _build_mirror_records(
    seed: _TailSeed,
    target_blocks: list[PageBlock],
    value_offsets: list[int],
    *,
    mirror_layout_type: str | None,
    mirror_value_count: int,
    descriptor_sequence: list[bytes] | None,
    hash_offset: int,
    user_offset: int,
    primary_pre_string_len: int,
    event_offsets: list[int],
    event_callbacks: list[dict[str, int]],
    image_button_layout: bool,
) -> bytes:
    out = bytearray()
    out.extend((len(target_blocks) << 16).to_bytes(4, "little"))
    out.extend(hash_offset.to_bytes(4, "little"))
    out.extend(user_offset.to_bytes(4, "little"))
    out.extend(primary_pre_string_len.to_bytes(4, "little"))

    slot_start = 0
    for index, (block, value_base) in enumerate(zip(target_blocks, value_offsets)):
        type_code = block.type_code
        object_id = _required_field_int(block, "id")
        record = bytearray(bytes([ord(type_code), object_id, 0, _record_header_flag(type_code)]) + b"\xFF" * 24)
        for event_name, callback_offset in event_callbacks[index].items():
            field_offset = _mirror_event_callback_field_offset(event_name)
            if field_offset is not None:
                record[field_offset : field_offset + 4] = callback_offset.to_bytes(4, "little")
        record.extend(value_base.to_bytes(4, "little"))
        record.extend(b"\x00\x00\x7F\x00")
        record.extend(b"\x00\x00\x00\x00")
        record.extend(_mirror_coord_payload(block))
        if index == 0:
            event_offset = event_offsets[index] + 4 if image_button_layout else event_offsets[index]
        else:
            event_offset = event_offsets[index]
        record.extend(event_offset.to_bytes(4, "little"))
        for item in _mirror_values_for_block(
            seed,
            block,
            image_button_layout=image_button_layout,
            mirror_layout_type=mirror_layout_type,
            mirror_value_count=mirror_value_count,
            descriptor_sequence=descriptor_sequence,
        ):
            value = 0xFFFF if item is None else slot_start + item
            record.extend(value.to_bytes(2, "little"))
        expected_length = 0x38 + mirror_value_count * 2
        if len(record) != expected_length:
            raise TftToolchainError(
                f"Internal mirror record length mismatch for {block.objname}: "
                f"expected 0x{expected_length:X}, got 0x{len(record):X}"
            )
        out.extend(record)
        slot_start += _user_slot_count(block)
    return bytes(out)


def _mirror_event_callback_field_offset(event_name: str) -> int | None:
    if event_name == "codesdown-":
        return 0x0C
    if event_name == "codesup-":
        return 0x10
    if event_name == "codestimer-":
        return 0x14
    return None


def _mirror_values_for_block(
    seed: _TailSeed,
    block: PageBlock,
    *,
    image_button_layout: bool,
    mirror_layout_type: str | None,
    mirror_value_count: int,
    descriptor_sequence: list[bytes] | None = None,
) -> list[int | None]:
    if image_button_layout and block.type_code == "b" and _field_int(block, "sta") == 2:
        values = list(IMAGE_BUTTON_MIRROR_RELATIVE_VALUES)
    else:
        if descriptor_sequence is not None:
            layout_templates = seed.mirror_layout_templates.get(mirror_layout_type or "", {})
            if (
                mirror_layout_type
                and descriptor_sequence == seed.mirror_descriptor_sequences.get(mirror_layout_type)
                and block.type_code in layout_templates
            ):
                values = list(layout_templates[block.type_code])
            else:
                values = _mirror_values_by_descriptors(seed, block, descriptor_sequence)
        else:
            layout_templates = seed.mirror_layout_templates.get(mirror_layout_type or "", {})
            values = list(layout_templates.get(block.type_code, seed.mirror_templates[block.type_code]))
        if image_button_layout:
            values.insert(IMAGE_BUTTON_MIRROR_EXTRA_INDEX, None)
    if len(values) > mirror_value_count:
        raise TftToolchainError(
            f"Unexpected mirror template width for {block.objname}: "
            f"{len(values)} > layout width {mirror_value_count}"
        )
    if len(values) < mirror_value_count:
        values.extend([None] * (mirror_value_count - len(values)))
    return values


def _mirror_values_by_descriptors(
    seed: _TailSeed,
    block: PageBlock,
    descriptor_sequence: list[bytes],
) -> list[int | None]:
    type_code = block.type_code
    value_by_descriptor: dict[bytes, int | None] = {}

    def merge(sequence: list[bytes], values: list[int | None]) -> None:
        for descriptor, value in zip(sequence, values):
            existing = value_by_descriptor.get(descriptor)
            if existing is not None and value is not None and existing != value:
                raise TftToolchainError(
                    f"Conflicting TFT mirror descriptor mapping for object type {type_code!r}"
                )
            if descriptor not in value_by_descriptor or value_by_descriptor[descriptor] is None:
                value_by_descriptor[descriptor] = value

    base_sequence = seed.mirror_descriptor_sequences[""]
    if type_code in seed.mirror_descriptor_sequences:
        merge(seed.mirror_descriptor_sequences[type_code], seed.mirror_layout_templates[type_code][type_code])
    else:
        merge(base_sequence, seed.mirror_templates[type_code])
        for layout_type, sequence in seed.mirror_descriptor_sequences.items():
            if not layout_type:
                continue
            layout_templates = seed.mirror_layout_templates.get(layout_type, {})
            if type_code in layout_templates:
                merge(sequence, layout_templates[type_code])

    return [value_by_descriptor.get(descriptor) for descriptor in descriptor_sequence]


def _user_slot_count(block: PageBlock) -> int:
    if block.type_code == "b" and _field_int(block, "sta") == 2:
        return IMAGE_BUTTON_USER_SLOT_COUNT
    return TYPE_USER_SLOT_COUNTS[block.type_code]


def _user_record_templates_for_block(
    seed: _TailSeed,
    block: PageBlock,
) -> list[_UserRecordTemplate]:
    templates = seed.user_templates[block.type_code]
    if block.type_code != "b" or _field_int(block, "sta") != 2:
        return templates

    shifted: list[_UserRecordTemplate] = []
    for template in templates:
        # Official full-image buttons have one fewer user slot than the
        # baseline solid-color button. The dropped slot is the normal-button
        # style/color slot before the image id fields; following metadata
        # shifts down by one.
        if template.slot_index == 20:
            continue
        if template.slot_index > 20:
            shifted.append(
                _UserRecordTemplate(
                    slot_index=template.slot_index - 1,
                    word1_mode=template.word1_mode,
                    word1_delta=template.word1_delta,
                    word2=template.word2,
                    word3=template.word3,
                    word4=template.word4,
                    word5=template.word5,
                )
            )
        else:
            shifted.append(template)
    return shifted


def _refresh_tft_headers(
    payload: bytearray,
    *,
    model: str,
    model_series: int,
    object_start: int,
    object_count: int,
    attr_relative: int,
    user_relative: int,
    picture_relative: int,
    prefix_delta: int = 0,
    image_button_layout: bool = False,
    gmovs_relative_offset: int = 0x10,
    videos_count: int | None = None,
) -> None:
    raw = bytearray(payload)
    if len(raw) < HEADER2_CRC_OFFSET + 4:
        raise TftToolchainError("TFT payload is too short for header refresh")

    raw[HEADER1_FILE_SIZE_OFFSET : HEADER1_FILE_SIZE_OFFSET + 4] = len(raw).to_bytes(4, "little")
    raw[HEADER1_CRC_OFFSET : HEADER1_CRC_OFFSET + 4] = _crc32_like(list(raw[:HEADER1_CRC_OFFSET])).to_bytes(4, "little")

    key = _header2_xor_key(model)
    _write_header2_field(raw, key, HEADER2_FIELD_OFFSETS["static_usercode_address"], attr_relative.to_bytes(4, "little"))
    _write_header2_field(raw, key, HEADER2_FIELD_OFFSETS["app_attributes_data_address"], attr_relative.to_bytes(4, "little"))
    _write_header2_field(raw, key, HEADER2_FIELD_OFFSETS["usercode_address"], user_relative.to_bytes(4, "little"))
    picture_absolute = object_start + picture_relative
    _write_header2_field(raw, key, HEADER2_FIELD_OFFSETS["pictures_address"], picture_absolute.to_bytes(4, "little"))
    _write_header2_field(raw, key, HEADER2_FIELD_OFFSETS["gmovs_address"], (picture_absolute + gmovs_relative_offset).to_bytes(4, "little"))
    if prefix_delta:
        current = _read_header2_u16(raw, key, HEADER2_FIELD_OFFSETS["image_button_prefix_count"])
        _write_header2_field(
            raw,
            key,
            HEADER2_FIELD_OFFSETS["image_button_prefix_count"],
            (current + prefix_delta).to_bytes(2, "little"),
        )
    if videos_count is not None:
        _write_header2_field(raw, key, HEADER2_FIELD_OFFSETS["videos_count"], int(videos_count).to_bytes(2, "little"))
    _write_header2_field(raw, key, HEADER2_FIELD_OFFSETS["compiled_object_count"], object_count.to_bytes(2, "little"))
    raw[HEADER2_CRC_OFFSET : HEADER2_CRC_OFFSET + 4] = _crc32_like(list(raw[HEADER2_START:HEADER2_CRC_OFFSET])).to_bytes(4, "little")

    raw[:] = update_tft_checksum(bytes(raw), series=model_series)
    payload[:] = raw


def _read_header2_u16(raw: bytes, key: bytes, relative_offset: int) -> int:
    start = HEADER2_START + relative_offset
    decoded = bytes(raw[start + index] ^ key[(relative_offset + index) % 4] for index in range(2))
    return int.from_bytes(decoded, "little")


def _header2_xor_key(model: str) -> bytes:
    module = _load_tfttool_module()
    key = int(module.TFTFile._modelXORs.get(model, 0))
    return key.to_bytes(4, "little") if key else b"\x00\x00\x00\x00"


def _write_header2_field(raw: bytearray, key: bytes, relative_offset: int, decoded: bytes) -> None:
    start = HEADER2_START + relative_offset
    for index, value in enumerate(decoded):
        raw[start + index] = value ^ key[(relative_offset + index) % 4]


def _code_block(data: bytes) -> bytes:
    return len(data).to_bytes(4, "little") + data


def _required_field_int(block: PageBlock, name: str) -> int:
    value = _field_int(block, name)
    if value is None:
        raise TftToolchainError(f"Missing integer field {name!r} in object {block.objname!r}")
    return value


def _object_name_hash_or_error(name: str) -> int:
    try:
        return object_name_hash(name)
    except (UnicodeEncodeError, ValueError) as exc:
        raise TftToolchainError(str(exc)) from exc


def _coord_payload(block: PageBlock) -> bytes:
    values = []
    for name in COORD_FIELDS:
        value = _field_int(block, name)
        if value is None:
            raise TftToolchainError(f"Missing coordinate field {name} in {block.objname}")
        values.append(value)
    return b"".join(value.to_bytes(2, "little") for value in values)


def _mirror_coord_payload(block: PageBlock) -> bytes:
    if block.type_code == "\x04":
        return bytes.fromhex("ce ff 00 00 32 00 32 00 ff ff 31 00")
    if block.type_code in NON_VISUAL_COORD_TYPES:
        return bytes.fromhex("00 00 00 00 01 00 01 00 00 00 00 00")
    return _coord_payload(block)


def _record_header_flag(type_code: str) -> int:
    return TYPE_RECORD_HEADER_FLAGS.get(type_code, 0x37)


def _replace_all(buf: memoryview, old: bytes, new: bytes) -> int:
    if len(old) != len(new):
        raise ValueError("replacement length must not change")
    data = buf.tobytes()
    count = 0
    start = 0
    while True:
        offset = data.find(old, start)
        if offset < 0:
            return count
        buf[offset : offset + len(old)] = new
        count += 1
        start = offset + len(old)


def _compiled_text_offset(block_reverse: dict[str, Any] | None) -> int | None:
    if not block_reverse:
        return None
    candidate = block_reverse.get("compiled_record_candidate")
    if not isinstance(candidate, dict):
        return None
    text_pointer = candidate.get("text_pointer_candidate")
    if not isinstance(text_pointer, dict):
        return None
    value = text_pointer.get("text_relative_offset")
    return int(value) if isinstance(value, int) else None


def _text_slot_len(block: PageBlock) -> int:
    txt_maxl = _field_int(block, "txt_maxl")
    if txt_maxl is not None:
        if block.type_code == "=":
            return txt_maxl + 4
        if block.type_code == "C":
            return txt_maxl + 4
        return txt_maxl + 2
    text = _field_text(block, "txt")
    return max(len(_encode_display_text(text)) if text else 0, 1)


def _path_slot_len(block: PageBlock) -> int:
    path_m = _field_int(block, "path_m")
    if path_m is not None:
        return path_m + 4
    text = _field_text(block, "path")
    return max(len(_encode_display_text(text)) if text else 0, 1)


def _string_pointer_fields(block: PageBlock) -> list[tuple[str, int, int]]:
    if block.type_code == "=":
        return [
            ("txt", 0x48, _text_slot_len(block)),
            ("path", 0x58, _path_slot_len(block)),
        ]
    if block.type_code == "<":
        return [("path", 0x3C, _external_picture_path_slot_len(block))]
    pointer_offset = TEXT_POINTER_RECORD_OFFSETS.get(block.type_code or "")
    if pointer_offset is None:
        return []
    return [("txt", pointer_offset, _text_slot_len(block))]


def _external_picture_path_slot_len(block: PageBlock) -> int:
    path_m = _field_int(block, "path_m")
    if path_m is not None:
        # Official external-picture objects reserve path_m+1 bytes; the
        # default path_m=255 produces a 256-byte runtime path buffer.
        return path_m + 1
    text = _field_text(block, "path")
    return max(len(_encode_display_text(text)) if text else 0, 1)


def _object_text_pointer(pointer_map: dict[int, Any], object_id: int, field_name: str) -> int:
    value = pointer_map[object_id]
    if isinstance(value, dict):
        return int(value[field_name])
    if field_name != "txt":
        raise TftToolchainError(f"Missing compiled text pointer for object {object_id} field {field_name!r}")
    return int(value)


def _header(inspection: dict[str, Any], name: str) -> dict[str, Any]:
    parsed = inspection.get("parsed")
    if not isinstance(parsed, dict) or not isinstance(parsed.get(name), dict):
        raise TftToolchainError(f"Unable to inspect TFT {name}")
    return parsed[name]


def _header_int(header: dict[str, Any], key: str) -> int | None:
    value = header.get(key)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError:
            return None
    return None


def _field_int(block: PageBlock, name: str) -> int | None:
    field = block.get_field(name)
    if field is None or not (0 < len(field.value) <= 4):
        return None
    return int.from_bytes(field.value, "little")


def _field_text(block: PageBlock, name: str) -> str | None:
    field = block.get_field(name)
    if field is None:
        return None
    try:
        return field.value.decode("gbk")
    except UnicodeDecodeError:
        return field.value.decode("gbk", errors="replace")


def _encode_display_text(text: str) -> bytes:
    return text.encode("gbk")
