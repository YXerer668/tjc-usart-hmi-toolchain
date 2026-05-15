from __future__ import annotations

from pathlib import Path
import unittest

from usarthmi.event_bytecode import decode_event_table
from usarthmi.page_format import load_page_file
from usarthmi.tft_patch import (
    _build_event_compile_context,
    _build_object_event_table,
    _header,
    _header_int,
)
from usarthmi.tft_toolchain import inspect_tft


CASE_ROOT = Path(r"C:\Users\SinYu\Desktop\case_for_codex")
CASE49_PA = CASE_ROOT / "case_49_audio" / "official_wiki" / "extract" / "0.pa"
CASE49_TFT = CASE_ROOT / "case_49_audio" / "official_compile" / "source_raw.run"


class EventBytecodeTests(unittest.TestCase):
    def test_decodes_media_assignment_and_play_items(self) -> None:
        assignment_table = bytes.fromhex(
            "00 00 00 00"
            "04 00 00 00 64 6f 77 6e"
            "07 00 00 00 01 d0 00 00 00 3d 30"
            "07 00 00 00 01 d1 00 00 00 3d 31"
            "00 00 00 00"
            "02 00 00 00 75 70"
            "00 00 00 00"
        )
        play_table = bytes.fromhex(
            "00 00 00 00"
            "04 00 00 00 64 6f 77 6e"
            "08 00 00 00 09 28 04 30 2c 30 2c 30"
            "00 00 00 00"
        )

        assignment_items = decode_event_table(assignment_table)
        play_items = decode_event_table(play_table)

        self.assertEqual(assignment_items[1]["name"], "down")
        self.assertEqual(assignment_items[2]["kind"], "property_event")
        self.assertEqual(assignment_items[2]["slot_hex"], "0xD0")
        self.assertEqual(assignment_items[2]["value"], "0")
        self.assertEqual(assignment_items[3]["slot_hex"], "0xD1")
        self.assertEqual(assignment_items[3]["value"], "1")
        self.assertEqual(play_items[2]["kind"], "command")
        self.assertEqual(play_items[2]["command"], "play")
        self.assertEqual(play_items[2]["args"], "0,0,0")

    def test_decodes_page_load_volume_assignment(self) -> None:
        table = bytes.fromhex(
            "04 00 00 00 09 1f 04 35"
            "09 00 00 00 04 08 12 00 00 3d 31 30 30"
            "03 00 00 00 09 30 08"
            "00 00 00 00"
        )

        items = decode_event_table(table)

        self.assertEqual(items[1]["kind"], "global_assignment")
        self.assertEqual(items[1]["name"], "volume")
        self.assertEqual(items[1]["value"], "100")
        self.assertEqual(items[0]["kind"], "separator")
        self.assertEqual(items[0]["command"], "post_primary_page_load")
        self.assertEqual(items[0]["args"], "5")
        self.assertEqual(items[2]["kind"], "separator")
        self.assertEqual(items[2]["command"], "loadend")

    def test_decodes_ref_command(self) -> None:
        table = bytes.fromhex(
            "09 00 00 00 09 03 04 6c 61 62 65 6c 30"
            "00 00 00 00"
        )

        items = decode_event_table(table)

        self.assertEqual(items[0]["kind"], "command")
        self.assertEqual(items[0]["command"], "ref")
        self.assertEqual(items[0]["args"], "label0")


@unittest.skipUnless(
    CASE49_PA.exists() and CASE49_TFT.exists(),
    "local official audio media event fixture is not available",
)
class EventBytecodeOfficialMediaFixtureTests(unittest.TestCase):
    def test_audio_media_events_match_official_tft_bytes(self) -> None:
        page = load_page_file(CASE49_PA)
        context = _build_event_compile_context(page.blocks)
        b0 = next(block for block in page.blocks if block.objname == "b0")
        b3 = next(block for block in page.blocks if block.objname == "b3")
        b0_event_table = _build_object_event_table(b0, context=context)
        b3_event_table = _build_object_event_table(b3, context=context)

        region = _object_region(CASE49_TFT)

        self.assertEqual(region.find(b0_event_table), 0x1AF)
        self.assertEqual(region.find(b3_event_table), 0x252)

        b0_items = decode_event_table(b0_event_table)
        b3_items = decode_event_table(b3_event_table)
        self.assertEqual(
            [(item["slot_hex"], item.get("operator"), item.get("value")) for item in b0_items if item["kind"] == "property_event"],
            [("0xD0", "=", "0"), ("0xD1", "=", "1")],
        )
        self.assertEqual(
            [(item["command"], item.get("args")) for item in b3_items if item["kind"] == "command"],
            [("play", "0,0,0")],
        )


def _object_region(tft_path: Path) -> bytes:
    raw = tft_path.read_bytes()
    inspection = inspect_tft(tft_path)
    object_start = _header_int(_header(inspection, "Header2"), "unknown_objects_address")
    if object_start is None:
        raise AssertionError("TFT Header2 does not expose unknown_objects_address")
    return raw[object_start:]


if __name__ == "__main__":
    unittest.main()
