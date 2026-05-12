from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from PIL import Image

from usarthmi.preview import render_scene_preview
from usarthmi.scene import load_scene
from usarthmi.zi_font import ZiFont


FONT_BASELINE = Path("reverse_usarthmi/font_baselines/ui_cn_en_32/UiCNEN32GBFull.zi")
SCENE_BASELINE = Path("reverse_usarthmi/font_baselines/ui_cn_en_32/scene.json")


@unittest.skipUnless(FONT_BASELINE.exists(), "local Chinese/English .zi baseline is not available")
class ZiFontPreviewTests(unittest.TestCase):
    def test_zi_font_renders_gbk_chinese_and_ascii(self) -> None:
        font = ZiFont(FONT_BASELINE)
        self.assertEqual(font.encoding_name, "gb2312")
        self.assertEqual(font.character_height, 32)
        self.assertGreater(font.character_count, 8000)

        image = font.render_text("主菜单 OK 123", (0, 0, 0))
        self.assertGreater(image.width, 80)
        self.assertEqual(image.height, 32)
        self.assertIsNotNone(image.getchannel("A").getbbox())

    @unittest.skipUnless(SCENE_BASELINE.exists(), "local font baseline scene is not available")
    def test_scene_preview_can_use_zi_font(self) -> None:
        scene = load_scene(SCENE_BASELINE)
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "preview.png"
            render_scene_preview(scene, out, font_paths={0: FONT_BASELINE})
            self.assertTrue(out.exists())
            with Image.open(out) as image:
                self.assertEqual(image.size, (800, 480))


if __name__ == "__main__":
    unittest.main()
