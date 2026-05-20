from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usarthmi.page_format import parse_page_data
from usarthmi.tft_patch import (
    _field_int,
    _find_hash_block,
    _header,
    _header_int,
    _object_name_hash_or_error,
    _read_header2_u16,
    _record_header_flag,
    _record_header_unknown2,
    _refresh_tft_headers,
    _header2_xor_key,
)
from usarthmi.tft_toolchain import inspect_tft


SOURCE_TFT = ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "output.tft"
PAGE1_PA = ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "target_1.pa"
PAGE0_PA = ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "target_0.pa"
OUT_DIR = ROOT / "reverse_usarthmi" / "page1_filebrowser_post_primary_marker_probe_20260521"
OUT_TFT = OUT_DIR / "output.tft"
PATCH_REPORT = OUT_DIR / "patch_report.json"

MARKER_BLOCK = bytes.fromhex("04 00 00 00 09 1f 04 34")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    source_raw = bytearray(SOURCE_TFT.read_bytes())
    inspection = inspect_tft(SOURCE_TFT)
    header1 = _header(inspection, "Header1")
    header2 = _header(inspection, "Header2")
    model = str(inspection.get("model") or "")
    model_series = _header_int(header1, "model_series")
    object_start = _header_int(header2, "unknown_objects_address")
    attr_relative = _header_int(header2, "static_usercode_address")
    user_relative = _header_int(header2, "usercode_address")
    picture_relative = _header_int(header2, "pictures_address") - _header_int(header2, "unknown_objects_address")
    if None in {model_series, object_start, attr_relative, user_relative, picture_relative}:
        raise RuntimeError("Missing required TFT offsets")
    assert model_series is not None
    assert object_start is not None
    assert attr_relative is not None
    assert user_relative is not None
    assert picture_relative is not None

    page1 = parse_page_data(PAGE1_PA.read_bytes())
    page0 = parse_page_data(PAGE0_PA.read_bytes())
    tail = source_raw[object_start:]
    page1_hash_offset, page1_hash_data = _find_hash_block(tail, _expected_hashes(page1))
    page0_hash_offset, _page0_hash_data = _find_hash_block(tail, _expected_hashes(page0))
    page1_primary_size_field = page1_hash_offset + 4 + len(page1_hash_data)
    page1_primary_offset = page1_primary_size_field + 4
    page1_primary_size = int.from_bytes(tail[page1_primary_size_field:page1_primary_size_field + 4], "little")
    insert_rel = page1_primary_offset + page1_primary_size
    insert_abs = object_start + insert_rel

    old_attr_relative = attr_relative
    old_user_relative = user_relative
    old_picture_relative = picture_relative
    old_page1_row = source_raw[object_start + picture_relative : object_start + picture_relative + 16]
    old_page0_row = source_raw[object_start + picture_relative + 16 : object_start + picture_relative + 32]

    patched = bytearray(source_raw[:insert_abs] + MARKER_BLOCK + source_raw[insert_abs:])

    delta = len(MARKER_BLOCK)
    new_attr_relative = old_attr_relative + delta
    new_user_relative = old_user_relative + delta
    new_picture_relative = old_picture_relative + delta

    page1_row_abs = object_start + new_picture_relative
    page0_row_abs = page1_row_abs + 16

    # page1 row: user section moves after the insertion, hash/primary stay put.
    _write_u32(patched, page1_row_abs + 8, int.from_bytes(old_page1_row[8:12], "little") + delta)

    # page0 row: both its hash section and user section moved.
    _write_u32(patched, page0_row_abs + 4, int.from_bytes(old_page0_row[4:8], "little") + delta)
    _write_u32(patched, page0_row_abs + 8, int.from_bytes(old_page0_row[8:12], "little") + delta)

    for record_offset_abs in _record_offsets_after(
        patched,
        search_start_abs=object_start + new_picture_relative + 32,
        blocks=page0.blocks,
    ):
        _write_u32(patched, record_offset_abs + 0x34, int.from_bytes(patched[record_offset_abs + 0x34:record_offset_abs + 0x38], "little") + delta)

    object_count = len(page0.blocks) + len(page1.blocks)
    _refresh_tft_headers(
        patched,
        model=model,
        model_series=model_series,
        object_start=object_start,
        object_count=object_count,
        attr_relative=new_attr_relative,
        user_relative=new_user_relative,
        picture_relative=new_picture_relative,
    )

    OUT_TFT.write_bytes(patched)
    report = _build_report(
        source_raw=source_raw,
        patched=patched,
        object_start=object_start,
        insert_rel=insert_rel,
        old_attr_relative=old_attr_relative,
        new_attr_relative=new_attr_relative,
        old_user_relative=old_user_relative,
        new_user_relative=new_user_relative,
        old_picture_relative=old_picture_relative,
        new_picture_relative=new_picture_relative,
        old_page1_row=old_page1_row,
        old_page0_row=old_page0_row,
        old_page0_hash_offset=page0_hash_offset,
    )
    PATCH_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def _build_report(
    *,
    source_raw: bytes,
    patched: bytes,
    object_start: int,
    insert_rel: int,
    old_attr_relative: int,
    new_attr_relative: int,
    old_user_relative: int,
    new_user_relative: int,
    old_picture_relative: int,
    new_picture_relative: int,
    old_page1_row: bytes,
    old_page0_row: bytes,
    old_page0_hash_offset: int,
) -> dict[str, object]:
    new_tail = patched[object_start:]
    page1 = parse_page_data(PAGE1_PA.read_bytes())
    page0 = parse_page_data(PAGE0_PA.read_bytes())
    new_page1_hash_offset, _ = _find_hash_block(new_tail, _expected_hashes(page1))
    new_page0_hash_offset, _ = _find_hash_block(new_tail, _expected_hashes(page0))
    new_page1_row = patched[object_start + new_picture_relative : object_start + new_picture_relative + 16]
    new_page0_row = patched[object_start + new_picture_relative + 16 : object_start + new_picture_relative + 32]
    page0_record_offsets = _record_offsets_after(
        patched,
        search_start_abs=object_start + new_picture_relative + 32,
        blocks=page0.blocks,
    )
    return {
        "source_tft": str(SOURCE_TFT),
        "output_tft": str(OUT_TFT),
        "insert_offset_hex": hex(object_start + insert_rel),
        "inserted_hex": MARKER_BLOCK.hex(" "),
        "old_post_primary_head_hex": source_raw[object_start + insert_rel : object_start + insert_rel + 11].hex(" "),
        "new_post_primary_head_hex": patched[object_start + insert_rel : object_start + insert_rel + 19].hex(" "),
        "old_attr_relative_hex": hex(old_attr_relative),
        "new_attr_relative_hex": hex(new_attr_relative),
        "old_user_relative_hex": hex(old_user_relative),
        "new_user_relative_hex": hex(new_user_relative),
        "old_picture_relative_hex": hex(old_picture_relative),
        "new_picture_relative_hex": hex(new_picture_relative),
        "old_page1_row_hex": old_page1_row.hex(" "),
        "new_page1_row_hex": new_page1_row.hex(" "),
        "old_page0_row_hex": old_page0_row.hex(" "),
        "new_page0_row_hex": new_page0_row.hex(" "),
        "old_page0_hash_offset_hex": hex(old_page0_hash_offset),
        "new_page0_hash_offset_hex": hex(new_page0_hash_offset),
        "new_page1_hash_offset_hex": hex(new_page1_hash_offset),
        "page0_record_offsets_hex": [hex(offset) for offset in page0_record_offsets],
        "page0_event_offsets_hex": [
            hex(int.from_bytes(patched[offset + 0x34:offset + 0x38], "little"))
            for offset in page0_record_offsets
        ],
        "note": "inserted the single-page file-browser post_primary_page_load marker block before page0 sections and adjusted later headers/rows/page0 event offsets for a future live probe",
    }


def _expected_hashes(page) -> dict[int, int]:
    return {
        _field_int(block, "id"): _object_name_hash_or_error(block.objname)
        for block in page.blocks
        if block.objname
    }


def _record_offsets_after(raw: bytes, *, search_start_abs: int, blocks) -> list[int]:
    offsets: list[int] = []
    cursor = search_start_abs
    for block in blocks:
        pattern = bytes([
            ord(block.type_code),
            _field_int(block, "id"),
            _record_header_unknown2(block.type_code),
            _record_header_flag(block.type_code),
        ])
        hit = raw.find(pattern, cursor)
        if hit < 0:
            raise RuntimeError(f"Unable to locate mirror record for {block.objname!r}")
        offsets.append(hit)
        cursor = hit + 4
    return offsets


def _write_u32(raw: bytearray, offset: int, value: int) -> None:
    raw[offset:offset + 4] = int(value).to_bytes(4, "little")


if __name__ == "__main__":
    raise SystemExit(main())
