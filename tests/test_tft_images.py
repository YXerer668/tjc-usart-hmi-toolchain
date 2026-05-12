from __future__ import annotations

from io import BytesIO
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from usarthmi.tft_images import (
    PICTURE_BLOCK_HEADER_SIZE,
    PICTURE_RESOURCE_RECORD_SIZE,
    compile_hmi_picture_resource,
    compile_picture_resource,
)


class TftImageEncodingTests(unittest.TestCase):
    def test_png_transparency_is_flattened_to_black_and_padded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "transparent.png"
            image = Image.new("RGBA", (17, 19), (255, 0, 0, 0))
            image.save(source)

            info, block = compile_picture_resource(source, 7)

            self.assertEqual(info.logical_width, 17)
            self.assertEqual(info.logical_height, 19)
            self.assertEqual(info.compiled_width, 32)
            self.assertEqual(info.compiled_height, 32)
            decoded = Image.open(BytesIO(block[PICTURE_BLOCK_HEADER_SIZE:])).convert("RGB")
            self.assertEqual(decoded.size, (32, 32))
            self.assertLess(max(decoded.getpixel((0, 0))), 3)

    def test_hmi_jpg_source_resource_keeps_original_payload_with_jpg_tag(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "photo.jpeg"
            Image.new("RGB", (29, 33), (30, 120, 210)).save(
                source,
                format="JPEG",
                quality=91,
            )
            source_bytes = source.read_bytes()

            resource, image_entry, source_entry = compile_hmi_picture_resource(source, 3)

            self.assertEqual(resource.image_entry_name, "3.i")
            self.assertEqual(resource.source_entry_name, "3.is")
            self.assertEqual(source_entry[24:27], b"jpg")
            self.assertEqual(source_entry[27:], source_bytes)
            self.assertEqual(int.from_bytes(source_entry[0x0C:0x0E], "little"), 29)
            self.assertEqual(int.from_bytes(source_entry[0x0E:0x10], "little"), 33)
            self.assertEqual(int.from_bytes(source_entry[0x10:0x14], "little"), len(source_bytes))
            self.assertEqual(int.from_bytes(image_entry[8:12], "little"), PICTURE_RESOURCE_RECORD_SIZE)
            self.assertEqual(int.from_bytes(image_entry[0x0C:0x0E], "little"), 29)
            self.assertEqual(int.from_bytes(image_entry[0x0E:0x10], "little"), 33)
            self.assertEqual(int.from_bytes(image_entry[PICTURE_RESOURCE_RECORD_SIZE + 4 : PICTURE_RESOURCE_RECORD_SIZE + 8], "little"), 32)
            self.assertEqual(int.from_bytes(image_entry[PICTURE_RESOURCE_RECORD_SIZE + 8 : PICTURE_RESOURCE_RECORD_SIZE + 12], "little"), 48)

    def test_large_picture_can_shrink_to_fixed_resource_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "noisy.png"
            image = Image.new("RGB", (320, 240))
            pixels = image.load()
            for y in range(image.height):
                for x in range(image.width):
                    pixels[x, y] = (
                        (x * 37 + y * 17) & 0xFF,
                        (x * 11 + y * 53) & 0xFF,
                        (x * 97 + y * 7) & 0xFF,
                    )
            image.save(source)

            info, block = compile_picture_resource(source, 4, max_block_size=8_192)

            self.assertLessEqual(len(block), 8_192)
            self.assertLess(info.scale_percent, 100)
            self.assertLessEqual(info.jpeg_quality, 96)
            self.assertEqual(info.compiled_width % 16, 0)
            self.assertEqual(info.compiled_height % 16, 0)


if __name__ == "__main__":
    unittest.main()
