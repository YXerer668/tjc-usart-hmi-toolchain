from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from usarthmi.hmi_donors import (
    block_signature_of,
    find_lowlevel_accepted_complex_hmi_donor,
    find_proven_complex_hmi_donor,
)


class _Block:
    def __init__(self, objname: str, type_code: str) -> None:
        self.objname = objname
        self.type_code = type_code


class HMIDonorTests(unittest.TestCase):
    def test_block_signature_of_uses_objname_and_type_code(self) -> None:
        signature = block_signature_of([_Block("page0", "y"), _Block("data0", "B")])
        self.assertEqual(signature, (("page0", "y"), ("data0", "B")))

    def test_case80_signature_selects_proven_donor_when_fixture_exists(self) -> None:
        blocks = [
            _Block("page0", "y"),
            _Block("t0", "t"),
            _Block("b0", "b"),
            _Block("p0", "p"),
            _Block("bar1", "j"),
            _Block("data0", "B"),
            _Block("select0", "D"),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            donor_path = root / "case_80_datarecord_textselect_official_positive_oracle" / "lcd_test.HMI"
            donor_path.parent.mkdir(parents=True, exist_ok=True)
            donor_path.write_bytes(b"fixture")
            with patch("usarthmi.hmi_donors.DEFAULT_CASE_ROOT", root):
                self.assertEqual(find_proven_complex_hmi_donor(blocks), donor_path)

    def test_case85_signature_is_selected_after_lowlevel_acceptance(self) -> None:
        blocks = [
            _Block("page0", "y"),
            _Block("t0", "t"),
            _Block("b0", "b"),
            _Block("p0", "p"),
            _Block("bar1", "j"),
            _Block("data0", "B"),
            _Block("slt0", ">"),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            donor_path = root / "case_85_datarecord_sltext_official_positive_oracle" / "lcd_test.HMI"
            donor_path.parent.mkdir(parents=True, exist_ok=True)
            donor_path.write_bytes(b"fixture")
            with patch("usarthmi.hmi_donors.DEFAULT_CASE_ROOT", root):
                self.assertEqual(find_proven_complex_hmi_donor(blocks), donor_path)
                self.assertEqual(find_lowlevel_accepted_complex_hmi_donor(blocks), donor_path)

    def test_case80_signature_is_selected_for_current_lowlevel_accepted_donor(self) -> None:
        blocks = [
            _Block("page0", "y"),
            _Block("t0", "t"),
            _Block("b0", "b"),
            _Block("p0", "p"),
            _Block("bar1", "j"),
            _Block("data0", "B"),
            _Block("select0", "D"),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            donor_path = root / "case_80_datarecord_textselect_official_positive_oracle" / "lcd_test.HMI"
            donor_path.parent.mkdir(parents=True, exist_ok=True)
            donor_path.write_bytes(b"fixture")
            with patch("usarthmi.hmi_donors.DEFAULT_CASE_ROOT", root):
                self.assertEqual(find_proven_complex_hmi_donor(blocks), donor_path)
                self.assertEqual(find_lowlevel_accepted_complex_hmi_donor(blocks), donor_path)
