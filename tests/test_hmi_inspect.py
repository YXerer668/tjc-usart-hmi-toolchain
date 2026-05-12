from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from usarthmi.hmi_inspect import extract_hmi, inspect_hmi
from usarthmi.page_format import BlockField, HEADER_SIZE, PageBlock, PageFile


def make_sample_hmi() -> bytes:
    resources = [
        ("Program.s", b"baud=9600\r\npage 0\r\n"),
        (
            "0.pa",
            b"\x00page0\x00objname\x00x0\x00bco\x00pco\x00font\x00pic\x00val\x00",
        ),
    ]

    header = bytearray((len(resources)).to_bytes(4, "little"))
    data = bytearray()
    current_offset = 4 + (28 * len(resources))

    for index, (name, payload) in enumerate(resources):
        name_bytes = name.encode("ascii").ljust(16, b"\x00")
        header.extend(name_bytes)
        header.extend(current_offset.to_bytes(4, "little"))
        header.extend(len(payload).to_bytes(4, "little"))
        header.extend((index + 1).to_bytes(4, "little"))
        data.extend(payload)
        current_offset += len(payload)

    return bytes(header + data)


def make_structured_page_hmi() -> bytes:
    header_bytes = bytearray(HEADER_SIZE)
    page = PageFile(
        magic=0x2155,
        total_length=0,
        object_count=0,
        header_bytes=bytes(header_bytes),
        page_name="page0",
        blocks=[
            PageBlock(
                attr_name="att-28",
                attr_marker=0x11,
                fields=[
                    BlockField("type", b"y", 0x11),
                    BlockField("id", b"\x00", 0x11),
                    BlockField("objname", b"page0", None),
                ],
                event_tokens=[
                    "codesload-2&",
                    "//用click去触发",
                    "n0.val=dp",
                    "codesloadend-0",
                    "codesdown-0",
                    "codesup-0",
                    "codesunload-0",
                ],
            ),
            PageBlock(
                attr_name="att-42",
                attr_marker=0x11,
                fields=[
                    BlockField("type", b"b", 0x11),
                    BlockField("id", b"\x01", 0x11),
                    BlockField("objname", b"b0", 0x11),
                    BlockField("x", (10).to_bytes(2, "little"), 0x11),
                    BlockField("y", (20).to_bytes(2, "little"), 0x11),
                    BlockField("w", (80).to_bytes(2, "little"), 0x11),
                    BlockField("h", (32).to_bytes(2, "little"), None),
                ],
                event_tokens=["codesdown-1", "printh ff ff ff", "codesup-0"],
            ),
        ],
    )
    payload = page.serialize()
    resources = [("Program.s", b"baud=9600\r\npage 0\r\n"), ("0.pa", payload)]

    header = bytearray((len(resources)).to_bytes(4, "little"))
    data = bytearray()
    current_offset = 4 + (28 * len(resources))
    for index, (name, resource) in enumerate(resources):
        header.extend(name.encode("ascii").ljust(16, b"\x00"))
        header.extend(current_offset.to_bytes(4, "little"))
        header.extend(len(resource).to_bytes(4, "little"))
        header.extend((index + 1).to_bytes(4, "little"))
        data.extend(resource)
        current_offset += len(resource)
    return bytes(header + data)


class HMIInspectTests(unittest.TestCase):
    def test_inspect_and_extract_sample_hmi(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            hmi_path = tmp_path / "sample.HMI"
            hmi_path.write_bytes(make_sample_hmi())

            inspection = inspect_hmi(hmi_path)
            self.assertEqual(inspection.entry_count, 2)
            self.assertEqual([entry.name for entry in inspection.entries], ["Program.s", "0.pa"])
            self.assertIn("baud=9600", inspection.program_text or "")
            self.assertEqual(inspection.page_names, ["page0"])
            self.assertEqual(inspection.object_names, ["x0"])
            self.assertTrue({"bco", "pco", "font", "pic", "val"}.issubset(inspection.property_names))

            output_dir = tmp_path / "extract"
            written = extract_hmi(hmi_path, output_dir)
            names = {path.name for path in written}
            self.assertIn("Program.s", names)
            self.assertIn("Program_utf8.txt", names)
            self.assertIn("0.pa", names)

    def test_inspect_reports_structured_pa_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            hmi_path = Path(tmp_dir) / "structured.HMI"
            hmi_path.write_bytes(make_structured_page_hmi())

            inspection = inspect_hmi(hmi_path)
            self.assertIsNone(inspection.pa_parse_error)
            self.assertEqual([block.objname for block in inspection.pa_blocks], ["page0", "b0"])
            self.assertEqual(inspection.pa_blocks[0].event_scripts[0].raw_header, "codesload-2&")
            self.assertEqual(inspection.pa_blocks[0].event_scripts[0].lines, ["//用click去触发", "n0.val=dp"])
            self.assertEqual(inspection.pa_blocks[1].fields["x"], 10)
            self.assertEqual(inspection.pa_blocks[1].event_scripts[0].lines, ["printh ff ff ff"])


if __name__ == "__main__":
    unittest.main()
