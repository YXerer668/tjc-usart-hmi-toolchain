from __future__ import annotations

from pathlib import Path

from usarthmi.hmi_cfs import NATIVE_CFS_PRIMARY_TABLE_OFFSET, find_native_cfs_record, parse_native_cfs_table


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
