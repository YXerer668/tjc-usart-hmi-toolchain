from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from usarthmi.hmi_inspect import extract_hmi
from usarthmi.object_hash import nextion_crc32, object_name_hash
from usarthmi.page_format import PageFile, load_page_file


KNOWN_TJC_OBJECT_HASHES = {
    "page0": 0xAC967926,
    "t0": 0xC02992D9,
    "b0": 0xCE1A7436,
    "p0": 0x56156502,
    "t1": 0xB64689A1,
    "b1": 0xB8756F4E,
    "p1": 0x207A7E7A,
}


class ObjectHashTests(unittest.TestCase):
    def test_object_name_hash_matches_recovered_tjc_values(self) -> None:
        for name, expected in KNOWN_TJC_OBJECT_HASHES.items():
            with self.subTest(name=name):
                self.assertEqual(object_name_hash(name), expected)

    def test_hash_is_nextion_crc32_over_14_byte_padded_name(self) -> None:
        self.assertEqual(
            object_name_hash("t0"),
            nextion_crc32(b"t0".ljust(14, b"\x00")),
        )
        self.assertEqual(
            object_name_hash("page0"),
            nextion_crc32(b"page0".ljust(14, b"\x00")),
        )

    def test_local_tjc_hash_block_is_reconstructed(self) -> None:
        tft = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_04_add_text\lcd_test.tft")
        page_path = (
            Path(__file__).resolve().parents[1]
            / "reverse_usarthmi"
            / "case_extracts"
            / "case_04_add_text"
            / "0.pa"
        )
        if not tft.exists() or not page_path.exists():
            self.skipTest("local TJC added-object fixture is not present")

        page = load_page_file(page_path)
        block = _compiled_hash_block(page)
        raw = tft.read_bytes()
        self.assertNotEqual(raw.find(len(block).to_bytes(4, "little") + block), -1)

    def test_public_nextion_pages_reconstruct_hash_blocks(self) -> None:
        root = Path(__file__).resolve().parents[1]
        hmi = root / "github_refs" / "Gaggiuino_35" / "Nextion_43" / "Nextion_43_18MAY2024.HMI"
        tft = root / "github_refs" / "Gaggiuino_35" / "Nextion_43" / "Nextion_43_18MAY2024_0_Deg.tft"
        if not hmi.exists() or not tft.exists():
            self.skipTest("optional public Nextion HMI/TFT fixtures are not present")

        raw = tft.read_bytes()
        checked = 0
        matched = 0
        with tempfile.TemporaryDirectory() as temp_dir:
            extract_hmi(hmi, temp_dir)
            for page_path in Path(temp_dir).glob("*.pa"):
                page = load_page_file(page_path)
                block = _compiled_hash_block(page)
                checked += 1
                if raw.find(len(block).to_bytes(4, "little") + block) >= 0:
                    matched += 1

        self.assertGreaterEqual(checked, 10)
        self.assertEqual(matched, checked)


def _compiled_hash_block(page: PageFile) -> bytes:
    entries: list[tuple[int, int]] = []
    for block in page.blocks:
        name = block.objname
        if not name:
            raise AssertionError("page block has no objname")
        field = block.get_field("id")
        if field is None:
            raise AssertionError(f"{name} has no id")
        object_id = int.from_bytes(field.value, "little")
        entries.append((object_name_hash(name), object_id))
    entries.sort(key=lambda item: item[0])
    return b"".join(
        object_hash.to_bytes(4, "little") + object_id.to_bytes(2, "little")
        for object_hash, object_id in entries
    )


if __name__ == "__main__":
    unittest.main()
