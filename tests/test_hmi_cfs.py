from __future__ import annotations

from pathlib import Path

from usarthmi.hmi_cfs import (
    NATIVE_CFS_PRIMARY_TABLE_OFFSET,
    compute_native_cfs_crc,
    find_native_cfs_record,
    parse_native_cfs_table,
    refresh_native_cfs_crc,
    rewrite_native_cfs_record,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_FIXTURE = (
    REPO_ROOT
    / "reverse_usarthmi"
    / "hmi_donor_lowlevel_probe_20260522"
    / "fixture_corpus"
    / "fixtures"
    / "page0_basic_delete"
    / "generated.HMI"
)


def test_parse_native_cfs_primary_table_for_baseline_fixture() -> None:
    raw = BASELINE_FIXTURE.read_bytes()
    table = parse_native_cfs_table(raw, NATIVE_CFS_PRIMARY_TABLE_OFFSET)
    assert table.count == 14

    names = [record.name for record in table.records]
    assert "main.HMI" in names
    assert "Program.s" in names
    assert "0.zi" in names
    assert "0.i" in names
    assert "0.pa" in names

    page = find_native_cfs_record(table, "0.pa")
    assert page is not None
    assert page.index == 11
    assert page.data_offset == 18152508
    assert page.length == 7476


def test_native_cfs_crc_matches_primary_table_trailer_for_baseline_fixture() -> None:
    raw = BASELINE_FIXTURE.read_bytes()
    table = parse_native_cfs_table(raw, NATIVE_CFS_PRIMARY_TABLE_OFFSET)
    assert table.trailing_crc == compute_native_cfs_crc(raw, offset=NATIVE_CFS_PRIMARY_TABLE_OFFSET)


def test_rewrite_native_cfs_record_and_refresh_crc_updates_trailer() -> None:
    raw = BASELINE_FIXTURE.read_bytes()
    table = parse_native_cfs_table(raw, NATIVE_CFS_PRIMARY_TABLE_OFFSET)
    page = find_native_cfs_record(table, "0.pa")
    assert page is not None

    mutated = rewrite_native_cfs_record(
        raw,
        offset=NATIVE_CFS_PRIMARY_TABLE_OFFSET,
        record_index=page.index,
        data_offset=page.data_offset + 16,
        length=page.length + 32,
    )
    refreshed = refresh_native_cfs_crc(mutated, offset=NATIVE_CFS_PRIMARY_TABLE_OFFSET)
    updated_table = parse_native_cfs_table(refreshed, NATIVE_CFS_PRIMARY_TABLE_OFFSET)
    updated_page = find_native_cfs_record(updated_table, "0.pa")
    assert updated_page is not None
    assert updated_page.data_offset == page.data_offset + 16
    assert updated_page.length == page.length + 32
    assert updated_table.trailing_crc == compute_native_cfs_crc(refreshed, offset=NATIVE_CFS_PRIMARY_TABLE_OFFSET)
