from __future__ import annotations

import argparse
from pathlib import Path

from tools import codex_touchsafe_official_pipeline as pipeline


def test_field_value_range_reads_raw_page_chunk() -> None:
    page = build_single_block_page({"endx": (519).to_bytes(2, "little"), "endy": (437).to_bytes(2, "little")})

    assert pipeline.read_field_int(page, 0, "endx") == 519
    assert pipeline.read_field_int(page, 0, "endy") == 437
    assert pipeline.read_field_int(page, 0, "missing") is None


def test_matches_expect_checks_response_fields() -> None:
    parsed = {"response": {"kind": "page_id", "value": 3}}

    assert pipeline.matches_expect(parsed, {"kind": "page_id", "value": 3})
    assert not pipeline.matches_expect(parsed, {"kind": "page_id", "value": 0})


def test_normalize_config_defaults_to_build_only() -> None:
    args = argparse.Namespace(
        spec=None,
        source_hmi=Path("build/source/lcd_test.HMI"),
        patch_plan=None,
        out_dir=Path("build/out"),
        name="case1",
        title=None,
        install_dir=None,
        port=None,
        baud=None,
        download_baud=None,
        chunk_size=None,
        flash=False,
        no_flash=False,
        skip_preview=False,
        skip_official_compile=False,
        camera=False,
        serial_smoke=False,
        dry_run=False,
    )

    config = pipeline.normalize_config({}, args)

    assert config["name"] == "case1"
    assert config["flash"] is False
    assert config["target"]["port"] == "COM36"
    assert config["target"]["expected_connect"]["model"] == "TJC8048X543_011C"


def build_single_block_page(fields: dict[str, bytes]) -> bytes:
    body = bytearray()
    body.extend((0).to_bytes(4, "little"))
    for name, value in fields.items():
        raw_name = name.encode("ascii").ljust(16, b"\x00")
        chunk = raw_name + value
        body.extend(len(chunk).to_bytes(4, "little"))
        body.extend(chunk)

    page = bytearray(0x38 + 12 + len(body))
    page[0x38 : 0x3C] = (12).to_bytes(4, "little")
    page[0x3C : 0x40] = len(body).to_bytes(4, "little")
    page[0x38 + 12 :] = body
    return bytes(page)
