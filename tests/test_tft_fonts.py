from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from usarthmi.tft_checksum import inspect_tft_checksum
from usarthmi.tft_fonts import patch_tft_font


BASELINE_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft")
FONT_ZI = Path("build_font_scene.zi")


@unittest.skipUnless(BASELINE_TFT.exists() and FONT_ZI.exists(), "local TFT/font fixtures are not available")
class TftFontPatchTests(unittest.TestCase):
    def test_patch_tft_font_replaces_font_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "font_patched.tft"
            result = patch_tft_font(BASELINE_TFT, font_path=FONT_ZI, out_tft=out).to_dict()

            self.assertTrue(out.exists())
            self.assertEqual(result["file_size"], BASELINE_TFT.stat().st_size)
            self.assertGreater(result["old_font_span"], result["new_font_size"])
            self.assertEqual(result["font_info"]["font_name"], "SimSun32scene")
            self.assertTrue(inspect_tft_checksum(out)["valid"])


if __name__ == "__main__":
    unittest.main()
