from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from usarthmi.editor import build_scene
from usarthmi.hmi_inspect import inspect_hmi
from usarthmi.page_format import load_page_file
from usarthmi.scene import validate_scene
from usarthmi.tft_reverse import reverse_tft_tail
from usarthmi.tft_toolchain import inspect_tft


SEED_HMI = Path(r"D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI")
BASELINE_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft")
SOURCE_IMAGE = next(Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_07_image_source_png_jpg").glob("*"), None)
BUTTON_NORMAL = Path("examples/menu_demo/assets/play.png")
BUTTON_PRESSED = Path("examples/menu_demo/assets/play_pressed.png")
CASE_12_HMI = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_12_text_yellow_font0\lcd_test.HMI")
CASE_12_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_12_text_yellow_font0\lcd_test.tft")
CASE_13_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_13_image_button_only\lcd_test.tft")
CASE_14_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_14_text_plus_image_button\lcd_test.tft")
CASE_16_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_16_number_basic\lcd_test.tft")
CASE_ROOT = Path(r"C:\Users\SinYu\Desktop\case_for_codex")
CASE_19_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_19_timer\lcd_test.tft")
CASE_31_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_31_multi_page_navigation\lcd_test.tft")
CASE_COMPARE_ROOT = Path(__file__).resolve().parents[1] / "reverse_usarthmi" / "case_compare"
CASE_14_EXTRACT = CASE_COMPARE_ROOT / "case_14_text_plus_image_button" / "extract"


@unittest.skipUnless(SEED_HMI.exists() and BASELINE_TFT.exists(), "local TJC seed HMI/TFT fixtures are not available")
class EditorTftBuildTests(unittest.TestCase):
    def test_scene_build_emits_multi_object_tft(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "multi-scene", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "note1",
                                "type": "text",
                                "x": 355,
                                "y": 321,
                                "w": 100,
                                "h": 31,
                                "text": "note1",
                            },
                            {
                                "id": "btn1",
                                "type": "button",
                                "x": 192,
                                "y": 310,
                                "w": 100,
                                "h": 50,
                                "text": "BTN1",
                            },
                            {
                                "id": "pic1",
                                "type": "image",
                                "x": 579,
                                "y": 346,
                                "w": 92,
                                "h": 92,
                                "resources": {"pic": 0},
                            },
                        ],
                    }
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(
                scene,
                SEED_HMI,
                temp_dir,
                baseline_tft=BASELINE_TFT,
            )
            self.assertTrue(Path(manifest["output_tft"]).exists())
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertEqual(manifest["tft_patch"]["added_count"], 3)

            target_page = load_page_file(manifest["target_pa"])
            self.assertEqual([block.objname for block in target_page.blocks[-3:]], ["note1", "btn1", "pic1"])
            self.assertEqual([block.type_code for block in target_page.blocks[-3:]], ["t", "b", "p"])

    @unittest.skipUnless(CASE_19_TFT.exists(), "local official timer fixture is not available")
    def test_scene_build_emits_timer_tft(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "timer-scene", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
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
                            }
                        ],
                    }
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(
                scene,
                SEED_HMI,
                temp_dir,
                baseline_tft=BASELINE_TFT,
            )
            self.assertTrue(Path(manifest["output_tft"]).exists())
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertEqual(manifest["tft_patch"]["added_count"], 1)

            target_page = load_page_file(manifest["target_pa"])
            timer = target_page.blocks[-1]
            self.assertEqual(timer.objname, "tm0")
            self.assertEqual(timer.type_code, "3")
            self.assertEqual(_field_int(timer, "tim"), 400)
            self.assertEqual(_field_int(timer, "en"), 1)

    @unittest.skipUnless(CASE_16_TFT.exists(), "local official number fixture is not available")
    def test_scene_build_emits_number_tft(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "number-scene", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "numval",
                                "type": "number",
                                "x": 80,
                                "y": 220,
                                "w": 200,
                                "h": 60,
                                "value": 12345,
                                "style": {
                                    "font_id": 0,
                                    "background_color": 65535,
                                    "foreground_color": 0,
                                },
                            }
                        ],
                    }
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(
                scene,
                SEED_HMI,
                temp_dir,
                baseline_tft=BASELINE_TFT,
            )
            self.assertTrue(Path(manifest["output_tft"]).exists())
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertEqual(manifest["tft_patch"]["added_count"], 1)

            target_page = load_page_file(manifest["target_pa"])
            number = target_page.blocks[-1]
            self.assertEqual(number.objname, "numval")
            self.assertEqual(number.type_code, "6")
            self.assertEqual(_field_int(number, "val"), 12345)

    @unittest.skipUnless(
        all(
            (CASE_ROOT / case_name / "lcd_test.tft").exists()
            and (CASE_ROOT / case_name / "lcd_test.HMI").exists()
            for case_name, *_ in (
                ("case_17_slider", "slider", "slider1", 80, 300, 400, 40),
                ("case_18_gauge", "gauge", "gauge1", 200, 200, 300, 300),
                ("case_20_progress", "progress", "bar1", 80, 350, 500, 30),
                ("case_21_qrcode", "qrcode", "qr1", 350, 100, 200, 200),
                ("case_22_scrolling_text", "scrolling-text", "g0", 0, 0, 240, 30),
                ("case_23_dual_state_button", "dual-button", "bt0", 0, 0, 60, 60),
                ("case_24_state_button", "state-button", "sw0", 0, 0, 80, 30),
                ("case_25_hotspot_touch_area", "hotspot", "m0", 0, 0, 60, 60),
                ("case_28_checkbox", "checkbox", "c0", 0, 0, 20, 20),
                ("case_30_crop_image", "crop-image", "q0", 0, 0, 60, 60),
            )
        ),
        "local official advanced-control fixtures are not available",
    )
    def test_scene_build_reproduces_official_advanced_single_widget_cases(self) -> None:
        cases = [
            ("case_17_slider", "slider", "slider1", 80, 300, 400, 40, "\x01"),
            ("case_18_gauge", "gauge", "gauge1", 200, 200, 300, 300, "z"),
            ("case_20_progress", "progress", "bar1", 80, 350, 500, 30, "j"),
            ("case_21_qrcode", "qrcode", "qr1", 350, 100, 200, 200, ":"),
            ("case_22_scrolling_text", "scrolling-text", "g0", 0, 0, 240, 30, "7"),
            ("case_23_dual_state_button", "dual-button", "bt0", 0, 0, 60, 60, "5"),
            ("case_24_state_button", "state-button", "sw0", 0, 0, 80, 30, "C"),
            ("case_25_hotspot_touch_area", "hotspot", "m0", 0, 0, 60, 60, "m"),
            ("case_28_checkbox", "checkbox", "c0", 0, 0, 20, 20, "8"),
            ("case_30_crop_image", "crop-image", "q0", 0, 0, 60, 60, "q"),
        ]
        for case_name, widget_type, widget_id, x, y, w, h, type_code in cases:
            scene = validate_scene(
                {
                    "project": {"name": f"scene-{case_name}", "default_page": "page0"},
                    "canvas": {"width": 800, "height": 480, "background_color": 65535},
                    "assets": {},
                    "pages": [
                        {
                            "id": "page0",
                            "layout": {"type": "absolute"},
                            "widgets": [
                                {
                                    "id": widget_id,
                                    "type": widget_type,
                                    "x": x,
                                    "y": y,
                                    "w": w,
                                    "h": h,
                                }
                            ],
                        }
                    ],
                }
            )
            with self.subTest(case=case_name), tempfile.TemporaryDirectory() as temp_dir:
                manifest = build_scene(scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

                self.assertEqual(Path(manifest["output_tft"]).read_bytes(), (CASE_ROOT / case_name / "lcd_test.tft").read_bytes())
                target_page = load_page_file(manifest["target_pa"])
                self.assertEqual(target_page.blocks[-1].objname, widget_id)
                self.assertEqual(target_page.blocks[-1].type_code, type_code)

    @unittest.skipUnless(
        all((CASE_ROOT / case_name / "lcd_test.HMI").exists() for case_name in (
            "case_26_variable_numeric_string",
            "case_27_waveform_basic",
            "case_29_radio",
        )),
        "local experimental advanced-control fixtures are not available",
    )
    def test_scene_build_emits_experimental_variable_waveform_radio_controls(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "experimental-controls", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {"id": "va_test", "type": "variable", "text": "abc", "value": 42},
                            {"id": "wave0", "type": "waveform", "x": 24, "y": 24, "w": 160, "h": 120},
                            {"id": "radio0", "type": "radio", "x": 220, "y": 48, "w": 20, "h": 20, "value": 1},
                        ],
                    }
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

            self.assertTrue(Path(manifest["output_tft"]).exists())
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertEqual(manifest["tft_patch"]["added_count"], 3)
            target_page = load_page_file(manifest["target_pa"])
            self.assertEqual([block.objname for block in target_page.blocks[-3:]], ["va_test", "wave0", "radio0"])
            self.assertEqual([block.type_code for block in target_page.blocks[-3:]], ["4", "\x00", "9"])

    def test_scene_build_patches_advanced_runtime_values(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "advanced-values", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {"id": "bar1", "type": "progress", "x": 40, "y": 36, "w": 260, "h": 28, "value": 68},
                            {"id": "slider1", "type": "slider", "x": 40, "y": 88, "w": 260, "h": 40, "value": 42},
                            {"id": "sw0", "type": "state-button", "x": 170, "y": 226, "w": 120, "h": 42, "value": 1},
                            {"id": "va0", "type": "variable", "value": 123},
                            {"id": "gauge1", "type": "gauge", "x": 350, "y": 24, "w": 180, "h": 180, "value": 76},
                            {"id": "c0", "type": "checkbox", "x": 332, "y": 236, "w": 24, "h": 24, "value": 0},
                            {"id": "r0", "type": "radio", "x": 392, "y": 236, "w": 24, "h": 24, "value": 0},
                        ],
                    }
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

            output_tft = Path(manifest["output_tft"])
            target_pa = Path(manifest["target_pa"])
            self.assertTrue(manifest["tft_checksum"]["valid"])
            checks = {
                "bar1": ("j", 0x3A, 1, 68),
                "slider1": ("\x01", 0x42, 2, 42),
                "sw0": ("C", 0x39, 1, 1),
                "va0": ("4", 0x0C, 4, 123),
                "gauge1": ("z", 0x3C, 2, 76),
                "c0": ("8", 0x40, 1, 0),
                "r0": ("9", 0x3C, 1, 0),
            }
            for name, (type_code, offset, width, expected) in checks.items():
                with self.subTest(name=name):
                    self.assertEqual(
                        _compiled_primary_value(output_tft, target_pa, name, type_code, offset, width),
                        expected,
                    )

    @unittest.skipUnless(CASE_31_TFT.exists(), "local official multi-page fixture is not available")
    def test_scene_build_reproduces_official_multi_page_case31(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "multi-page-case31", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [],
                    },
                    {
                        "id": "page1",
                        "layout": {"type": "absolute"},
                        "widgets": [],
                    },
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(
                scene,
                SEED_HMI,
                temp_dir,
                baseline_tft=BASELINE_TFT,
            )

            self.assertEqual(Path(manifest["output_tft"]).read_bytes(), CASE_31_TFT.read_bytes())
            self.assertEqual(manifest["tft_patch"]["mode"], "experimental_multi_page_tft_patch")
            self.assertEqual(manifest["tft_patch"]["page_count"], 2)
            self.assertEqual(len(manifest["target_pages"]), 2)
            self.assertTrue(Path(manifest["target_pages"][1]).exists())
            self.assertIn("1.pa", {entry.name for entry in inspect_hmi(manifest["output_hmi"]).entries})

    def test_scene_build_emits_experimental_page1_text_button_tft(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "multi-page-page1-text-button", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {"id": "page0", "layout": {"type": "absolute"}, "widgets": []},
                    {
                        "id": "page1",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "p1title",
                                "type": "text",
                                "x": 72,
                                "y": 64,
                                "w": 320,
                                "h": 58,
                                "text": "PAGE1",
                                "style": {"font_id": 0, "background_color": 65535, "foreground_color": 0},
                            },
                            {
                                "id": "p1btn",
                                "type": "button",
                                "x": 72,
                                "y": 154,
                                "w": 180,
                                "h": 64,
                                "text": "GO",
                                "style": {"font_id": 0, "background_color": 65504, "foreground_color": 0},
                            },
                        ],
                    },
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(
                scene,
                SEED_HMI,
                temp_dir,
                baseline_tft=BASELINE_TFT,
            )

            self.assertTrue(Path(manifest["output_tft"]).exists())
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertEqual(manifest["tft_patch"]["mode"], "experimental_multi_page_tft_patch")
            self.assertEqual(manifest["tft_patch"]["page_count"], 2)
            self.assertEqual(manifest["tft_patch"]["object_count"], 7)

            page1 = load_page_file(manifest["target_pages"][1])
            self.assertEqual([block.objname for block in page1.blocks], ["page1", "p1title", "p1btn"])
            self.assertEqual([block.type_code for block in page1.blocks], ["y", "t", "b"])
            self.assertIn("1.pa", {entry.name for entry in inspect_hmi(manifest["output_hmi"]).entries})

    def test_scene_build_emits_experimental_page1_button_event_tft_when_enabled(self) -> None:
        scene = validate_scene(
            {
                "project": {
                    "name": "multi-page-page1-button-event",
                    "default_page": "page0",
                    "experimental_multi_page_events": True,
                },
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {"id": "page0", "layout": {"type": "absolute"}, "widgets": []},
                    {
                        "id": "page1",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "p1title",
                                "type": "text",
                                "x": 72,
                                "y": 64,
                                "w": 320,
                                "h": 58,
                                "text": "PAGE1",
                            },
                            {
                                "id": "back0",
                                "type": "button",
                                "x": 72,
                                "y": 154,
                                "w": 180,
                                "h": 64,
                                "text": "BACK",
                                "events": {"up": ["page 0"]},
                            },
                        ],
                    },
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(
                scene,
                SEED_HMI,
                temp_dir,
                baseline_tft=BASELINE_TFT,
            )

            self.assertTrue(Path(manifest["output_tft"]).exists())
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertTrue(manifest["tft_patch"]["experimental_events"])
            self.assertEqual(manifest["tft_patch"]["object_count"], 7)
            page1 = load_page_file(manifest["target_pages"][1])
            back_button = next(block for block in page1.blocks if block.objname == "back0")
            self.assertIn("codesup-1", back_button.event_tokens)
            self.assertIn("page 0", back_button.event_tokens)

    def test_scene_build_rejects_page1_events_without_experimental_flag(self) -> None:
        bad_scene = validate_scene(
            {
                "project": {"name": "bad-page1-event", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480},
                "assets": {},
                "pages": [
                    {"id": "page0", "layout": {"type": "absolute"}, "widgets": []},
                    {
                        "id": "page1",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "back0",
                                "type": "button",
                                "x": 10,
                                "y": 10,
                                "w": 120,
                                "h": 48,
                                "text": "BACK",
                                "events": {"up": ["page 0"]},
                            }
                        ],
                    },
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(Exception, "page1 widget events"):
                build_scene(bad_scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

    def test_scene_build_rejects_unsupported_multi_page_shapes(self) -> None:
        bad_scene = validate_scene(
            {
                "project": {"name": "bad-multipage", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480},
                "assets": {},
                "pages": [
                    {"id": "page0", "layout": {"type": "absolute"}, "widgets": []},
                    {
                        "id": "page1",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "later",
                                "type": "number",
                                "x": 10,
                                "y": 10,
                                "w": 100,
                                "h": 32,
                                "value": 123,
                            }
                        ],
                    },
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(Exception, "page1 supports only text/button"):
                build_scene(bad_scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

    def test_scene_build_can_move_seed_objects_offscreen(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "clean-scene", "default_page": "page0", "clean_seed_objects": True},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "note1",
                                "type": "text",
                                "x": 100,
                                "y": 100,
                                "w": 120,
                                "h": 32,
                                "text": "clean",
                            }
                        ],
                    }
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(
                scene,
                SEED_HMI,
                temp_dir,
                baseline_tft=BASELINE_TFT,
            )
            target_page = load_page_file(manifest["target_pa"])
            for block in target_page.blocks[1:4]:
                self.assertGreaterEqual(_field_int(block, "x"), 800)
                self.assertGreaterEqual(_field_int(block, "y"), 480)
                self.assertEqual(_field_int(block, "w"), 1)
                self.assertEqual(_field_int(block, "h"), 1)
            self.assertEqual(target_page.blocks[-1].objname, "note1")
            self.assertTrue(manifest["tft_checksum"]["valid"])

    def test_scene_build_patches_text_record_metadata(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "text-metadata", "default_page": "page0", "clean_seed_objects": True},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "fontmsg",
                                "type": "text",
                                "x": 120,
                                "y": 96,
                                "w": 560,
                                "h": 88,
                                "text": "FONT TEST 123",
                                "style": {
                                    "font_id": 0,
                                    "background_color": 65535,
                                    "foreground_color": 0,
                                },
                            }
                        ],
                    }
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(
                scene,
                SEED_HMI,
                temp_dir,
                baseline_tft=BASELINE_TFT,
            )
            reverse = reverse_tft_tail(
                manifest["output_tft"],
                hmi_pa_path=manifest["target_pa"],
                context_bytes=8,
            )
            text_block = next(
                block
                for block in reverse["hmi_page"]["blocks"]
                if block.get("objname") == "fontmsg"
            )
            candidate = text_block["compiled_record_candidate"]
            record_offset = reverse["object_region"]["start"] + candidate["header_relative_offset"]
            record = Path(manifest["output_tft"]).read_bytes()[record_offset : record_offset + 0x54]

            self.assertEqual(record[0x39], 0)
            self.assertEqual(int.from_bytes(record[0x46:0x48], "little"), len("FONT TEST 123"))
            self.assertEqual(_field_int(load_page_file(manifest["target_pa"]).blocks[-1], "txt_maxl"), 13)

    @unittest.skipUnless(CASE_12_TFT.exists(), "local official case_12 fixture is not available")
    def test_scene_build_reproduces_official_stock_text_case(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "official-text-case", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "fontmsg",
                                "type": "text",
                                "x": 80,
                                "y": 70,
                                "w": 640,
                                "h": 120,
                                "text": "newtxt",
                                "style": {
                                    "font_id": 0,
                                    "background_color": 65504,
                                    "foreground_color": 0,
                                },
                            }
                        ],
                    }
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(
                scene,
                SEED_HMI,
                temp_dir,
                baseline_tft=BASELINE_TFT,
            )
            self.assertEqual(Path(manifest["output_tft"]).read_bytes(), CASE_12_TFT.read_bytes())

    def test_scene_tft_build_rejects_unpacked_new_image_resources(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "bad-assets", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "pic_new",
                                "type": "image",
                                "x": 10,
                                "y": 10,
                                "w": 50,
                                "h": 50,
                                "resources": {"pic": 1234},
                            }
                        ],
                    }
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(Exception, "cannot pack new image resources"):
                build_scene(scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

    @unittest.skipUnless(SOURCE_IMAGE is not None and SOURCE_IMAGE.exists(), "local imported-image fixture is not available")
    def test_scene_build_packs_new_picture_resource(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "image-scene", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {
                    "photo": {
                        "id": "photo",
                        "source": str(SOURCE_IMAGE),
                    }
                },
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "photo1",
                                "type": "image",
                                "x": 162,
                                "y": 87,
                                "w": 489,
                                "h": 342,
                                "resources": {"asset": "photo"},
                            }
                        ],
                    }
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(
                scene,
                SEED_HMI,
                temp_dir,
                baseline_tft=BASELINE_TFT,
            )

            self.assertTrue(Path(manifest["resource_seed_tft"]).exists())
            self.assertTrue(Path(manifest["output_tft"]).exists())
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertEqual(manifest["tft_picture_pack"]["picture_count"], 2)
            self.assertEqual(
                manifest["tft_picture_pack"]["new_object_start"],
                manifest["tft_picture_pack"]["old_object_start"],
            )
            self.assertGreater(manifest["tft_picture_pack"]["trimmed_resource_tail_bytes"], 0)
            self.assertEqual(manifest["tft_picture_pack"]["pictures"][0]["picture_id"], 1)
            self.assertLess(manifest["tft_picture_pack"]["pictures"][0]["jpeg_quality"], 95)
            _assert_picture_resource_directory_shifted(
                BASELINE_TFT,
                Path(manifest["resource_seed_tft"]),
            )

            target_page = load_page_file(manifest["target_pa"])
            self.assertEqual(target_page.blocks[-1].objname, "photo1")
            self.assertEqual(target_page.blocks[-1].type_code, "p")
            pic_field = target_page.blocks[-1].get_field("pic")
            self.assertIsNotNone(pic_field)
            self.assertEqual(int.from_bytes(pic_field.value, "little"), 1)

    @unittest.skipUnless(BUTTON_NORMAL.exists() and BUTTON_PRESSED.exists(), "local button-image fixtures are not available")
    def test_scene_build_packs_image_button_states(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "image-button-scene", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {
                    "play": {
                        "id": "play",
                        "normal": str(BUTTON_NORMAL),
                        "pressed": str(BUTTON_PRESSED),
                    }
                },
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "playbtn",
                                "type": "button",
                                "x": 320,
                                "y": 196,
                                "w": 160,
                                "h": 96,
                                "text": "PLAY",
                                "resources": {"asset": "play"},
                            }
                        ],
                    }
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(
                scene,
                SEED_HMI,
                temp_dir,
                baseline_tft=BASELINE_TFT,
            )

            self.assertTrue(Path(manifest["resource_seed_tft"]).exists())
            self.assertTrue(Path(manifest["output_tft"]).exists())
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertEqual(manifest["tft_picture_pack"]["picture_count"], 3)
            self.assertEqual(
                manifest["tft_picture_pack"]["new_object_start"],
                manifest["tft_picture_pack"]["old_object_start"],
            )
            _assert_picture_resource_directory_shifted(
                BASELINE_TFT,
                Path(manifest["resource_seed_tft"]),
            )
            self.assertEqual(
                [item["picture_id"] for item in manifest["tft_picture_pack"]["pictures"]],
                [1, 2],
            )

            target_page = load_page_file(manifest["target_pa"])
            button = target_page.blocks[-1]
            self.assertEqual(button.objname, "playbtn")
            self.assertEqual(button.type_code, "b")
            self.assertEqual(_field_int(button, "sta"), 2)
            self.assertEqual(_field_int(button, "pic"), 1)
            self.assertEqual(_field_int(button, "pic2"), 2)

    @unittest.skipUnless(BUTTON_NORMAL.exists() and BUTTON_PRESSED.exists(), "local button-image fixtures are not available")
    def test_scene_build_keeps_tft_picture_records_sorted_by_id(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "sorted-picture-records", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {
                    "zphoto": {
                        "id": "zphoto",
                        "source": str(BUTTON_NORMAL),
                    },
                    "abadge": {
                        "id": "abadge",
                        "source": str(BUTTON_PRESSED),
                    },
                },
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "photo1",
                                "type": "image",
                                "x": 40,
                                "y": 80,
                                "w": 160,
                                "h": 96,
                                "resources": {"asset": "zphoto"},
                            },
                            {
                                "id": "badge1",
                                "type": "image",
                                "x": 240,
                                "y": 80,
                                "w": 160,
                                "h": 96,
                                "resources": {"asset": "abadge"},
                            },
                        ],
                    }
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(
                scene,
                SEED_HMI,
                temp_dir,
                baseline_tft=BASELINE_TFT,
            )
            ids = _tft_picture_record_ids(Path(manifest["resource_seed_tft"]))

            self.assertEqual(ids[:3], [0, 1, 2])
            self.assertEqual(manifest["assets"]["abadge"]["resource_id"], 1)
            self.assertEqual(manifest["assets"]["zphoto"]["resource_id"], 2)

    @unittest.skipUnless(
        CASE_14_EXTRACT.exists() and BUTTON_NORMAL.exists() and BUTTON_PRESSED.exists(),
        "local official HMI image-resource fixture is not available",
    )
    def test_scene_build_writes_picture_resources_into_hmi(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "hmi-image-resources", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {
                    "play": {
                        "id": "play",
                        "normal": str(BUTTON_NORMAL),
                        "pressed": str(BUTTON_PRESSED),
                    }
                },
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "playbtn",
                                "type": "button",
                                "x": 320,
                                "y": 300,
                                "w": 160,
                                "h": 96,
                                "text": "",
                                "resources": {"asset": "play"},
                            }
                        ],
                    }
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(
                scene,
                SEED_HMI,
                temp_dir,
                baseline_tft=BASELINE_TFT,
            )
            output_hmi = Path(manifest["output_hmi"])
            entries = inspect_hmi(output_hmi).entries
            names = {entry.name for entry in entries}

            self.assertTrue({"1.is", "2.is", "1.i", "2.i"}.issubset(names))
            self.assertEqual([item["picture_id"] for item in manifest["hmi_picture_resources"]], [1, 2])
            for entry_name in ("1.is", "2.is", "1.i", "2.i"):
                self.assertEqual(
                    _hmi_entry_data(output_hmi, entry_name),
                    (CASE_14_EXTRACT / entry_name).read_bytes(),
                )

    @unittest.skipUnless(
        CASE_13_TFT.exists() and CASE_14_TFT.exists() and BUTTON_NORMAL.exists() and BUTTON_PRESSED.exists(),
        "local official image-button fixtures are not available",
    )
    def test_scene_build_matches_official_image_button_tail_layout(self) -> None:
        cases = [
            (
                "case13",
                CASE_13_TFT,
                [
                    {
                        "id": "playbtn",
                        "type": "button",
                        "x": 320,
                        "y": 300,
                        "w": 160,
                        "h": 96,
                        "text": "",
                        "resources": {"asset": "play"},
                    }
                ],
            ),
            (
                "case14",
                CASE_14_TFT,
                [
                    {
                        "id": "playbtn",
                        "type": "button",
                        "x": 320,
                        "y": 300,
                        "w": 160,
                        "h": 96,
                        "text": "",
                        "resources": {"asset": "play"},
                    },
                    {
                        "id": "fontmsg",
                        "type": "text",
                        "x": 80,
                        "y": 70,
                        "w": 640,
                        "h": 120,
                        "text": "newtxt",
                        "style": {
                            "font_id": 0,
                            "background_color": 65504,
                            "foreground_color": 0,
                        },
                    },
                ],
            ),
        ]

        for case_name, official_tft, widgets in cases:
            scene = validate_scene(
                {
                    "project": {"name": case_name, "default_page": "page0"},
                    "canvas": {"width": 800, "height": 480, "background_color": 65535},
                    "assets": {
                        "play": {
                            "id": "play",
                            "normal": str(BUTTON_NORMAL),
                            "pressed": str(BUTTON_PRESSED),
                        }
                    },
                    "pages": [
                        {
                            "id": "page0",
                            "layout": {"type": "absolute"},
                            "widgets": widgets,
                        }
                    ],
                }
            )
            with self.subTest(case=case_name), tempfile.TemporaryDirectory() as temp_dir:
                manifest = build_scene(
                    scene,
                    SEED_HMI,
                    temp_dir,
                    baseline_tft=BASELINE_TFT,
                )
                self.assertEqual(Path(manifest["output_tft"]).read_bytes(), official_tft.read_bytes())
                generated_tail = _tft_compiled_tail_without_checksum(Path(manifest["output_tft"]))
                official_tail = _tft_compiled_tail_without_checksum(official_tft)

                self.assertEqual(generated_tail, official_tail)

def _field_int(block, name: str) -> int:
    field = block.get_field(name)
    assert field is not None
    return int.from_bytes(field.value, "little")


def _resource_dir_u32(path: Path, offset: int) -> int:
    raw = path.read_bytes()
    return int.from_bytes(raw[0x20000 + offset : 0x20000 + offset + 4], "little")


def _tft_compiled_tail_without_checksum(path: Path) -> bytes:
    raw = path.read_bytes()
    header2 = inspect_tft(path)["parsed"]["Header2"]
    object_start = _header2_int(header2, "unknown_objects_address")
    return raw[object_start:-4]


def _compiled_primary_value(
    tft_path: Path,
    pa_path: Path,
    object_name: str,
    type_code: str,
    offset: int,
    width: int,
) -> int:
    raw = tft_path.read_bytes()
    reverse = reverse_tft_tail(tft_path, hmi_pa_path=pa_path, context_bytes=0)
    object_start = reverse["object_region"]["start"]
    for block in reverse["hmi_page"]["blocks"]:
        if block.get("objname") != object_name:
            continue
        candidate = block.get("compiled_record_candidate")
        if candidate:
            record = raw[
                object_start + candidate["header_relative_offset"] :
                object_start + candidate["record_end_relative_offset"]
            ]
            return int.from_bytes(record[offset : offset + width], "little")
        break

    page = load_page_file(pa_path)
    block = next(item for item in page.blocks if item.objname == object_name)
    object_id = _field_int(block, "id")
    header = bytes([ord(type_code), object_id, 0, 0x07 if type_code == "4" else 0x37])
    position = raw.find(header, object_start, object_start + 0x8000)
    if position < 0:
        raise AssertionError(f"compiled primary record for {object_name!r} was not found")
    return int.from_bytes(raw[position + offset : position + offset + width], "little")


def _hmi_entry_data(path: Path, entry_name: str) -> bytes:
    raw = path.read_bytes()
    entry = next(item for item in inspect_hmi(path).entries if item.name == entry_name)
    return raw[entry.data_offset : entry.data_offset + entry.length]


def _tft_picture_record_ids(path: Path) -> list[int]:
    raw = path.read_bytes()
    header2 = inspect_tft(path)["parsed"]["Header2"]
    start = _header2_int(header2, "videos_address")
    first_offset = int.from_bytes(raw[start + 8 : start + 12], "little")
    count = first_offset // 24
    return [
        int.from_bytes(raw[start + index * 24 + 4 : start + index * 24 + 8], "little")
        for index in range(count)
    ]


def _header2_int(header2: dict, key: str) -> int:
    value = header2[key]
    if isinstance(value, str) and value.startswith("0x"):
        return int(value, 16)
    return int(value)


def _assert_picture_resource_directory_shifted(baseline: Path, candidate: Path) -> None:
    baseline_picture_end = _resource_dir_u32(baseline, 0x60)
    candidate_picture_end = _resource_dir_u32(candidate, 0x60)
    inserted = candidate_picture_end - baseline_picture_end
    assert inserted > 0
    assert _resource_dir_u32(candidate, 0x58) == _resource_dir_u32(baseline, 0x58) + inserted
    for offset in (0x6C, 0x78, 0x84):
        assert _resource_dir_u32(candidate, offset) == _resource_dir_u32(baseline, offset) + inserted


if __name__ == "__main__":
    unittest.main()
