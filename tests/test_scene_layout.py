from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from usarthmi.layout import resolve_page_layout
from usarthmi.page_format import BlockField, PageBlock, PageFile
from usarthmi.preview import render_page_preview, render_scene_preview
from usarthmi.scene import WidgetSpec, load_scene, validate_scene
from PIL import Image


class SceneLayoutTests(unittest.TestCase):
    def test_json_and_yaml_scene_match(self) -> None:
        base = Path(__file__).resolve().parents[1] / "examples" / "menu_demo"
        scene_json = load_scene(base / "scene.json")
        scene_yaml = load_scene(base / "scene.yaml")
        self.assertEqual(scene_json.to_dict(), scene_yaml.to_dict())

    def test_absolute_layout(self) -> None:
        widgets = [WidgetSpec(id="a", type="text", x=10, y=20, w=30, h=40)]
        placed = resolve_page_layout(widgets, {"type": "absolute"}, 800, 480)
        self.assertEqual((placed[0].x, placed[0].y, placed[0].w, placed[0].h), (10, 20, 30, 40))

    def test_row_layout(self) -> None:
        widgets = [
            WidgetSpec(id="a", type="text", h=30),
            WidgetSpec(id="b", type="text", h=30),
        ]
        placed = resolve_page_layout(widgets, {"type": "row", "gap": 10}, 210, 30)
        self.assertEqual((placed[0].x, placed[0].w), (0, 100))
        self.assertEqual((placed[1].x, placed[1].w), (110, 100))

    def test_column_layout(self) -> None:
        widgets = [
            WidgetSpec(id="a", type="text", w=40),
            WidgetSpec(id="b", type="text", w=40),
        ]
        placed = resolve_page_layout(widgets, {"type": "column", "gap": 10}, 40, 210)
        self.assertEqual((placed[0].y, placed[0].h), (0, 100))
        self.assertEqual((placed[1].y, placed[1].h), (110, 100))

    def test_grid_layout(self) -> None:
        widgets = [WidgetSpec(id=f"w{i}", type="button") for i in range(4)]
        placed = resolve_page_layout(widgets, {"type": "grid", "columns": 2, "gap": 10}, 210, 210)
        self.assertEqual((placed[0].x, placed[0].y), (0, 0))
        self.assertEqual((placed[1].x, placed[1].y), (110, 0))
        self.assertEqual((placed[2].x, placed[2].y), (0, 110))

    def test_timer_layout_is_nonvisual(self) -> None:
        widgets = [
            WidgetSpec(id="tm0", type="timer"),
            WidgetSpec(id="a", type="button", h=30),
            WidgetSpec(id="b", type="button", h=30),
        ]
        placed = resolve_page_layout(widgets, {"type": "row", "gap": 10}, 210, 30)
        self.assertEqual((placed[0].x, placed[0].y, placed[0].w, placed[0].h), (0, 0, 1, 1))
        self.assertEqual((placed[1].x, placed[1].w), (0, 100))
        self.assertEqual((placed[2].x, placed[2].w), (110, 100))

    def test_stack_layout(self) -> None:
        widgets = [WidgetSpec(id="bg", type="image"), WidgetSpec(id="fg", type="text")]
        placed = resolve_page_layout(widgets, {"type": "stack"}, 320, 240)
        for widget in placed:
            self.assertEqual((widget.x, widget.y, widget.w, widget.h), (0, 0, 320, 240))

    def test_anchor_layout(self) -> None:
        widget = WidgetSpec(
            id="br",
            type="button",
            w=40,
            h=20,
            layout={"type": "anchor", "right": 10, "bottom": 5},
        )
        placed = resolve_page_layout([widget], {"type": "anchor"}, 200, 100)
        self.assertEqual((placed[0].x, placed[0].y), (150, 75))

    def test_scene_events_round_trip(self) -> None:
        scene = load_scene(Path(__file__).resolve().parents[1] / "examples" / "event_demo" / "scene.json")
        self.assertEqual(scene.pages[0].events["load"], ["printh 23 02 50 01"])
        self.assertEqual(scene.pages[0].widgets[0].events["up"], ["printh 23 02 54 45"])
        self.assertEqual(scene.to_dict()["pages"][0]["widgets"][0]["events"]["up"], ["printh 23 02 54 45"])

        payload = scene.to_dict()
        payload["pages"][0]["events"]["loadend"] = "vis evtbtn,0"
        payload["pages"][0]["widgets"][0]["events"]["slide"] = "printh 23 02 53 4c"
        payload["pages"][0]["widgets"][0]["events"]["timer"] = ["printh 23 02 54 4d"]
        round_trip = validate_scene(payload)
        self.assertEqual(round_trip.pages[0].events["loadend"], ["vis evtbtn,0"])
        self.assertEqual(round_trip.pages[0].widgets[0].events["slide"], ["printh 23 02 53 4c"])
        self.assertEqual(round_trip.pages[0].widgets[0].events["timer"], ["printh 23 02 54 4d"])

    def test_timer_widget_is_valid_scene_type(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "timer-scene", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "tm0",
                                "type": "timer",
                                "value": 400,
                                "style": {"enabled": True},
                                "events": {"timer": ["printh 23 02 54 4d"]},
                            }
                        ],
                    }
                ],
            }
        )

        self.assertEqual(scene.pages[0].widgets[0].type, "timer")
        self.assertEqual(scene.pages[0].widgets[0].events["timer"], ["printh 23 02 54 4d"])

    def test_scene_preview_renders_png(self) -> None:
        base = Path(__file__).resolve().parents[1] / "examples" / "menu_demo"
        scene = load_scene(base / "scene.json")
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "preview.png"
            render_scene_preview(scene, target)
            self.assertTrue(target.exists())
            with Image.open(target) as image:
                self.assertEqual(image.size, (800, 480))

    def test_external_picture_demo_preview_renders_png(self) -> None:
        base = Path(__file__).resolve().parents[1] / "examples" / "external_picture_demo"
        scene = load_scene(base / "scene.json")
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "external_picture_preview.png"
            render_scene_preview(scene, target)
            self.assertTrue(target.exists())
            with Image.open(target) as image:
                self.assertEqual(image.size, (800, 480))

    def test_page_preview_renders_png(self) -> None:
        page = PageFile(
            magic=0x1AB9451B,
            total_length=0,
            object_count=2,
            header_bytes=b"\x00" * 0x38,
            page_name="page0",
            blocks=[
                _block("page0", "y", {"id": 0, "x": 0, "y": 0, "w": 800, "h": 480, "bco": 65535}),
                _block(
                    "note1",
                    "t",
                    {
                        "id": 1,
                        "x": 355,
                        "y": 321,
                        "w": 100,
                        "h": 31,
                        "bco": 65535,
                        "pco": 0,
                        "xcen": 1,
                        "ycen": 1,
                        "txt": "note1",
                    },
                ),
            ],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "page_preview.png"
            render_page_preview(page, target)
            self.assertTrue(target.exists())
            with Image.open(target) as image:
                self.assertEqual(image.size, (800, 480))


def _block(objname: str, type_code: str, values: dict[str, int | str]) -> PageBlock:
    fields = [
        BlockField("type", type_code.encode("ascii"), 0x11),
        BlockField("objname", objname.encode("ascii"), 0x11),
    ]
    for name, value in values.items():
        if isinstance(value, str):
            payload = value.encode("ascii")
            marker = 0x11
        else:
            width = 1 if name in {"id", "xcen", "ycen"} else 2
            payload = int(value).to_bytes(width, "little")
            marker = 0x12
        fields.append(BlockField(name, payload, marker))
    return PageBlock(attr_name="att-0", attr_marker=0, fields=fields, event_tokens=[])


if __name__ == "__main__":
    unittest.main()
