from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from usarthmi.hmi_inspect import inspect_hmi
from usarthmi.page_format import load_page_file, parse_page_data
from usarthmi.tft_checksum import inspect_tft_checksum
from usarthmi.tft_patch import _augment_seed_templates, _build_multi_page_tail, _load_tail_seed, _refresh_tft_headers


ROOT = Path(__file__).resolve().parents[1]
BASELINE_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft")
SEED_PA = ROOT / "reverse_usarthmi" / "page1_load_printh_probe_rebuild_20260520" / "seed_0.pa"
PAGE0_PA = ROOT / "reverse_usarthmi" / "page1_load_printh_probe_rebuild_20260520" / "target_0.pa"
OFFICIAL_TEXTSELECT_HMI = (
    ROOT / "reverse_usarthmi" / "official_page1_textselect_minimal_oracle_20260519" / "lcd_test.HMI"
)


@unittest.skipUnless(
    BASELINE_TFT.exists() and SEED_PA.exists() and PAGE0_PA.exists() and OFFICIAL_TEXTSELECT_HMI.exists(),
    "local page1 text-select fixtures are not available",
)
class Page1TextSelectLocalMultiPageBuilderTests(unittest.TestCase):
    def test_local_builder_accepts_official_page1_textselect_page(self) -> None:
        inspection = inspect_hmi(OFFICIAL_TEXTSELECT_HMI)
        raw_hmi = OFFICIAL_TEXTSELECT_HMI.read_bytes()
        page1_entry = next(entry for entry in inspection.entries if entry.name == "1.pa")
        page0 = load_page_file(PAGE0_PA)
        page1 = parse_page_data(raw_hmi[page1_entry.data_offset : page1_entry.data_offset + page1_entry.length])
        seed_page = parse_page_data(SEED_PA.read_bytes())
        seed = _load_tail_seed(BASELINE_TFT, SEED_PA, seed_page)
        _augment_seed_templates(seed, {block.type_code for block in page0.blocks + page1.blocks})

        with tempfile.TemporaryDirectory() as temp_dir:
            out_tft = Path(temp_dir) / "page1_textselect_local_multipt.tft"
            tail, sections = _build_multi_page_tail(seed, [page0, page1])
            payload = bytearray(seed.raw[: seed.object_start] + tail)
            _refresh_tft_headers(
                payload,
                model=seed.model,
                model_series=seed.model_series,
                object_start=seed.object_start,
                object_count=len(page0.blocks) + len(page1.blocks),
                attr_relative=sections["attr"],
                user_relative=sections["user"],
                picture_relative=sections["pic"],
                prefix_delta=sections["prefix_delta"],
                gmovs_relative_offset=0x20,
                videos_count=2,
            )
            out_tft.write_bytes(payload)
            checksum = inspect_tft_checksum(out_tft)
            self.assertTrue(checksum["valid"])
            self.assertGreater(out_tft.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
