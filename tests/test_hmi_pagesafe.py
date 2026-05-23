from __future__ import annotations

import struct
from pathlib import Path

from usarthmi.hmi_cfs import NATIVE_CFS_PRIMARY_TABLE_OFFSET, find_native_cfs_record, parse_native_cfs_table
from usarthmi.hmi_pagesafe import inspect_page_safe_status, refresh_page_safe_header


REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_DONOR = (
    REPO_ROOT
    / "reverse_usarthmi"
    / "hmi_donor_lowlevel_probe_20260522"
    / "fixture_corpus"
    / "fixtures"
    / "page0_basic_delete"
    / "input_donor.HMI"
)


def _baseline_named_page_bytes() -> bytes:
    raw = BASELINE_DONOR.read_bytes()
    table = parse_native_cfs_table(raw, NATIVE_CFS_PRIMARY_TABLE_OFFSET)
    page = find_native_cfs_record(table, "0.pa")
    assert page is not None
    return raw[page.data_offset : page.data_offset + page.length]


def test_baseline_named_page_is_pagesafe() -> None:
    status = inspect_page_safe_status(_baseline_named_page_bytes())
    assert status.safe_ok is True
    assert status.size_field == status.size == 7476
    assert status.datainformation_qyt == 8
    assert status.hmiffid == 0x55
    assert status.filever == 0x21


def test_refresh_page_safe_header_recomputes_crc_for_count_only_tombstone() -> None:
    baseline = _baseline_named_page_bytes()
    mutated = bytearray(baseline)
    struct.pack_into("<I", mutated, 0x0C, 7)
    refreshed = refresh_page_safe_header(mutated)
    status = inspect_page_safe_status(refreshed)
    assert status.safe_ok is True
    assert status.size_field == status.size == 7476
    assert status.datainformation_qyt == 7
