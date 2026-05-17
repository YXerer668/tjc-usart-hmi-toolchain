from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from usarthmi.editor import (
    FIXTURE_WIDGET_TEMPLATE_CASES,
    build_scene,
    _is_supported_experimental_page1_event_widget,
    _is_supported_experimental_page1_page_events,
)
from usarthmi.event_bytecode import decode_event_table
from usarthmi.hmi_inspect import inspect_hmi
from usarthmi.object_hash import object_name_hash
from usarthmi.page_format import load_page_file
from usarthmi.scene import (
    SUPPORTED_WIDGET_TYPES,
    UNSUPPORTED_CURRENT_TARGET_WIDGET_TYPES,
    WidgetSpec,
    load_scene,
    validate_scene,
)
from usarthmi.tft_patch import TYPE_RECORD_LENGTHS, TYPE_USER_SLOT_COUNTS, _record_header_flag
from usarthmi.tft_patch import _build_event_compile_context, _build_event_layout, _build_object_event_table, _user_slot_count
from usarthmi.tft_reverse import reverse_tft_tail
from usarthmi.tft_toolchain import inspect_tft


SEED_HMI = Path(r"D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI")
BASELINE_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft")
SOURCE_IMAGE = next(Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_07_image_source_png_jpg").glob("*"), None)
BUTTON_NORMAL = Path("examples/menu_demo/assets/play.png")
BUTTON_PRESSED = Path("examples/menu_demo/assets/play_pressed.png")
NUMBER_DEMO_FULL_REBUILD_SCENE = Path("examples/number_demo/full_page_rebuild_scene.json")
NUMBER_DEMO_REORDER_SCENE = Path("examples/number_demo/reorder_broadening_scene.json")
NUMBER_DEMO_EVENT_MATRIX_SCENE = Path("examples/number_demo/event_matrix_scene.json")
NUMBER_DEMO_VIS_PROMOTION_SCENE = Path("examples/number_demo/vis_promotion_scene.json")
NUMBER_DEMO_TSW_PROMOTION_SCENE = Path("examples/number_demo/tsw_promotion_scene.json")
BUILTIN_CONTROLS_DEMO_SCENE = Path("examples/builtin_controls_demo/scene.json")
NEW_CONTROLS_DEMO_SCENE = Path("examples/new_controls_demo/scene.json")
XFLOAT_COMBOBOX_DEMO_SCENE = Path("examples/xfloat_combobox_demo/scene.json")
EXTERNAL_PICTURE_DEMO_SCENE = Path("examples/external_picture_demo/scene.json")
TOUCH_CAPTURE_DEMO_SCENE = Path("examples/touch_capture_demo/scene.json")
MEDIA_GMOV_SMOKE_SCENE = Path("examples/media_single_gmov_smoke/scene.json")
MEDIA_VIDEO_SD_SMOKE_SCENE = Path("examples/media_single_video_sd_smoke/scene.json")
MEDIA_AUDIO_SD_SMOKE_SCENE = Path("examples/media_single_audio_sd_smoke/scene.json")
WIDGET_CAPABILITY_MATRIX = Path("examples/widget_capability_matrix_2026-05-17.json")
ALL_SUPPORTED_CONTROLS_COMPLETION_AUDIT = Path("examples/all_supported_controls_completion_audit_2026-05-17.json")
LIVE_WIDGET_PROOF_MATRIX = Path("examples/live_widget_proof_matrix_2026-05-17.json")
LEGACY_BASIC_CONTROLS_DEMO_SCENE = Path("examples/legacy_basic_controls_demo/scene.json")
FONT_ZI = Path("build_font_scene.zi")
GB2312_FONT_ZI = Path("reverse_usarthmi/font_baselines/ui_cn_en_32/UiCNEN32GBFull.zi")
BUILTIN_WIDGET_TYPE_CODES = {
    "button": "b",
    "image": "p",
    "number": "6",
    "text": "t",
    "timer": "3",
}
SCENE_WIDGET_TYPE_CODES = BUILTIN_WIDGET_TYPE_CODES | {
    widget_type: type_code for widget_type, (_case_name, type_code) in FIXTURE_WIDGET_TEMPLATE_CASES.items()
}
CASE_12_HMI = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_12_text_yellow_font0\lcd_test.HMI")
CASE_12_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_12_text_yellow_font0\lcd_test.tft")
CASE_13_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_13_image_button_only\lcd_test.tft")
CASE_14_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_14_text_plus_image_button\lcd_test.tft")
CASE_16_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_16_number_basic\lcd_test.tft")
CASE_ROOT = Path(r"C:\Users\SinYu\Desktop\case_for_codex")
CASE_19_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_19_timer\lcd_test.tft")
CASE_31_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_31_multi_page_navigation\lcd_test.tft")
CASE_36_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_36_xfloat\lcd_test.tft")
CASE_37_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_37_combobox\lcd_test.tft")
CASE_46_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_46_expicture_current_gui\lcd_test.tft")
CASE_COMPARE_ROOT = Path(__file__).resolve().parents[1] / "reverse_usarthmi" / "case_compare"
CASE_14_EXTRACT = CASE_COMPARE_ROOT / "case_14_text_plus_image_button" / "extract"


@unittest.skipUnless(SEED_HMI.exists() and BASELINE_TFT.exists(), "local TJC seed HMI/TFT fixtures are not available")
class EditorTftBuildTests(unittest.TestCase):
    def test_current_target_supported_widget_types_have_tft_writer_path(self) -> None:
        built_in_writer_types = {"button", "image", "number", "text", "timer"}
        fixture_writer_types = set(FIXTURE_WIDGET_TEMPLATE_CASES)
        writer_types = built_in_writer_types | fixture_writer_types
        unsupported_types = set(UNSUPPORTED_CURRENT_TARGET_WIDGET_TYPES)

        self.assertFalse(set(SUPPORTED_WIDGET_TYPES) & unsupported_types)
        self.assertEqual(set(SUPPORTED_WIDGET_TYPES) - writer_types, set())

    def test_widget_capability_matrix_matches_code_constants(self) -> None:
        matrix = json.loads(WIDGET_CAPABILITY_MATRIX.read_text(encoding="utf-8"))
        built_in_writer_types = set(matrix["built_in_writer_types"])
        fixture_writer_cases = matrix["fixture_backed_writer_types"]
        fixture_writer_types = set(fixture_writer_cases)
        unsupported_types = set(matrix["current_target_unsupported"])

        self.assertEqual(built_in_writer_types, {"button", "image", "number", "text", "timer"})
        self.assertEqual(fixture_writer_types, set(FIXTURE_WIDGET_TEMPLATE_CASES))
        for widget_type, (case_name, type_code) in FIXTURE_WIDGET_TEMPLATE_CASES.items():
            with self.subTest(fixture_widget_type=widget_type):
                self.assertEqual(
                    fixture_writer_cases[widget_type],
                    {"case": case_name, "type": _matrix_type_code(type_code)},
                )
        self.assertEqual(unsupported_types, set(UNSUPPORTED_CURRENT_TARGET_WIDGET_TYPES))
        self.assertEqual(matrix["current_target_unsupported"], UNSUPPORTED_CURRENT_TARGET_WIDGET_TYPES)
        self.assertTrue(Path(matrix["current_target_unsupported_evidence"]).exists())
        self.assertEqual(set(SUPPORTED_WIDGET_TYPES), built_in_writer_types | fixture_writer_types)
        full_rebuild_coverage = matrix["full_page_rebuild_offline_coverage"]
        covered_types = set()
        for group_name, group in full_rebuild_coverage.items():
            covered_types.update(group["types"])
            evidence_path = Path(group["evidence"])
            self.assertTrue(evidence_path.exists())
            evidence_types = _matrix_evidence_widget_types(evidence_path)
            with self.subTest(coverage_group=group_name):
                self.assertEqual(set(group["types"]) - evidence_types, set())
        self.assertEqual(set(SUPPORTED_WIDGET_TYPES), covered_types)
        scene_examples = matrix["scene_examples"]
        self.assertEqual(set(SUPPORTED_WIDGET_TYPES), set(scene_examples))
        for widget_type, example in scene_examples.items():
            with self.subTest(widget_type=widget_type):
                scene_path = Path(example["scene"])
                evidence_path = Path(example["evidence"])
                self.assertTrue(scene_path.exists())
                self.assertTrue(evidence_path.exists())
                scene = load_scene(scene_path)
                widget_types = {widget.type for page in scene.pages for widget in page.widgets}
                self.assertIn(widget_type, widget_types)

    def test_all_supported_controls_completion_audit_matches_capability_matrix(self) -> None:
        matrix = json.loads(WIDGET_CAPABILITY_MATRIX.read_text(encoding="utf-8"))
        audit = json.loads(ALL_SUPPORTED_CONTROLS_COMPLETION_AUDIT.read_text(encoding="utf-8"))

        self.assertEqual(audit["target"], matrix["target"])
        self.assertEqual(audit["source_capability_matrix"], WIDGET_CAPABILITY_MATRIX.as_posix())
        self.assertEqual(set(audit["completed_current_target_supported_widget_types"]), set(SUPPORTED_WIDGET_TYPES))
        self.assertEqual(audit["excluded_current_target_unsupported"], UNSUPPORTED_CURRENT_TARGET_WIDGET_TYPES)
        self.assertEqual(audit["current_target_unsupported_evidence"], matrix["current_target_unsupported_evidence"])
        self.assertTrue(Path(audit["current_target_unsupported_evidence"]).exists())

        writer_evidence = audit["writer_path_evidence"]
        built_in_writer_types = set(writer_evidence["built_in_writer_types"])
        fixture_writer_cases = writer_evidence["fixture_backed_writer_types"]
        self.assertEqual(built_in_writer_types, set(matrix["built_in_writer_types"]))
        self.assertEqual(fixture_writer_cases, matrix["fixture_backed_writer_types"])
        self.assertEqual(set(SUPPORTED_WIDGET_TYPES), built_in_writer_types | set(fixture_writer_cases))

        self.assertEqual(audit["full_page_rebuild_offline_coverage"], matrix["full_page_rebuild_offline_coverage"])
        covered_types = set()
        for group in audit["full_page_rebuild_offline_coverage"].values():
            covered_types.update(group["types"])
            self.assertTrue(Path(group["evidence"]).exists())
        self.assertEqual(set(SUPPORTED_WIDGET_TYPES), covered_types)

        self.assertEqual(audit["scene_examples"], matrix["scene_examples"])
        self.assertEqual(set(SUPPORTED_WIDGET_TYPES), set(audit["scene_examples"]))

        legacy_demo = audit["legacy_demos"][LEGACY_BASIC_CONTROLS_DEMO_SCENE.as_posix()]
        legacy_scene = load_scene(LEGACY_BASIC_CONTROLS_DEMO_SCENE)
        legacy_widget_types = {widget.type for page in legacy_scene.pages for widget in page.widgets}
        self.assertEqual(legacy_demo["role"], "basic-smoke-only")
        self.assertTrue(legacy_demo["not_completion_evidence"])
        self.assertEqual(set(legacy_demo["covers_widget_types"]), legacy_widget_types)
        self.assertNotEqual(legacy_widget_types, set(SUPPORTED_WIDGET_TYPES))
        self.assertFalse(Path("examples/all_controls_demo").exists())

        for claim in matrix["not_claimed"]:
            with self.subTest(not_claimed=claim):
                self.assertIn(claim, audit["not_claimed"])

        success_criteria = {item["id"]: item for item in audit["success_criteria"]}
        self.assertEqual(
            set(success_criteria),
            {
                "current-target-supported-set",
                "writer-paths",
                "offline-scene-coverage",
                "unsupported-target-drops",
                "legacy-demo-boundary",
            },
        )
        self.assertTrue(all(item["status"] == "passed" for item in success_criteria.values()))

    def test_live_widget_proof_matrix_tracks_supported_control_runtime_gap(self) -> None:
        audit = json.loads(ALL_SUPPORTED_CONTROLS_COMPLETION_AUDIT.read_text(encoding="utf-8"))
        live_matrix = json.loads(LIVE_WIDGET_PROOF_MATRIX.read_text(encoding="utf-8"))
        supported_types = set(audit["completed_current_target_supported_widget_types"])

        self.assertEqual(live_matrix["target"], audit["target"])
        self.assertEqual(live_matrix["source_completion_audit"], ALL_SUPPORTED_CONTROLS_COMPLETION_AUDIT.as_posix())
        self.assertEqual(set(live_matrix["widgets"]), supported_types)
        self.assertIn("live COM36 proof for every widget", live_matrix["not_claimed"])

        valid_statuses = set(live_matrix["status_values"])
        committed_live_types = set(live_matrix["committed_live_proof_widget_types"])
        actual_committed_live_types = set()
        for widget_type, entry in live_matrix["widgets"].items():
            with self.subTest(widget_type=widget_type):
                self.assertEqual(entry["scene"], audit["scene_examples"][widget_type]["scene"])
                self.assertEqual(entry["offline_evidence"], audit["scene_examples"][widget_type]["evidence"])
                self.assertTrue(Path(entry["scene"]).exists())
                self.assertTrue(Path(entry["offline_evidence"]).exists())
                self.assertIn(entry["live_status"], valid_statuses)
                self.assertTrue(entry["next_live_action"])
                for evidence_key in ("live_evidence", "live_expectations_or_docs"):
                    for evidence_path in entry.get(evidence_key, []):
                        self.assertTrue(Path(evidence_path).exists(), evidence_path)
                if entry["live_status"] == "committed-live-proof":
                    actual_committed_live_types.add(widget_type)
                    self.assertTrue(entry.get("live_evidence"))

        self.assertEqual(actual_committed_live_types, committed_live_types)
        self.assertLess(len(committed_live_types), len(supported_types))

    def test_widget_capability_matrix_scene_examples_build_clean_rebuild_tfts(self) -> None:
        matrix = json.loads(WIDGET_CAPABILITY_MATRIX.read_text(encoding="utf-8"))
        unique_scene_paths = sorted({Path(example["scene"]) for example in matrix["scene_examples"].values()})

        self.assertEqual(
            set(unique_scene_paths),
            {
                BUILTIN_CONTROLS_DEMO_SCENE,
                NEW_CONTROLS_DEMO_SCENE,
                XFLOAT_COMBOBOX_DEMO_SCENE,
                EXTERNAL_PICTURE_DEMO_SCENE,
                TOUCH_CAPTURE_DEMO_SCENE,
                MEDIA_GMOV_SMOKE_SCENE,
                MEDIA_VIDEO_SD_SMOKE_SCENE,
                MEDIA_AUDIO_SD_SMOKE_SCENE,
            },
        )
        for scene_path in unique_scene_paths:
            with self.subTest(scene=str(scene_path)), tempfile.TemporaryDirectory() as temp_dir:
                scene = load_scene(scene_path)
                manifest = build_scene(scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)
                target_page = load_page_file(manifest["target_pa"])
                expected_objects = [("page0", "y")] + [
                    (widget.id, SCENE_WIDGET_TYPE_CODES[widget.type]) for widget in scene.pages[0].widgets
                ]

                self.assertTrue(Path(manifest["output_tft"]).exists())
                self.assertTrue(manifest["tft_checksum"]["valid"])
                self.assertEqual(manifest["tft_patch"]["mode"], "experimental_clean_page_tft_rebuild")
                self.assertEqual(manifest["tft_patch"]["removed_seed_objects"], ["t0", "b0", "p0"])
                self.assertEqual([(block.objname, block.type_code) for block in target_page.blocks], expected_objects)
                self.assertEqual([_field_int(block, "id") for block in target_page.blocks], list(range(len(expected_objects))))

    @unittest.skipUnless(
        BUILTIN_CONTROLS_DEMO_SCENE.exists(),
        "local builtin-controls full-rebuild scene is not available",
    )
    def test_builtin_controls_demo_full_page_rebuild_covers_builtin_controls(self) -> None:
        scene = load_scene(BUILTIN_CONTROLS_DEMO_SCENE)

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

            output_tft = Path(manifest["output_tft"])
            target_page = load_page_file(manifest["target_pa"])
            self.assertTrue(output_tft.exists())
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertEqual(manifest["tft_patch"]["mode"], "experimental_clean_page_tft_rebuild")
            self.assertEqual(manifest["tft_patch"]["object_count"], 6)
            self.assertEqual(manifest["tft_patch"]["removed_seed_objects"], ["t0", "b0", "p0"])
            self.assertEqual(
                [(block.objname, block.type_code) for block in target_page.blocks],
                [
                    ("page0", "y"),
                    ("title", "t"),
                    ("btn0", "b"),
                    ("num0", "6"),
                    ("pic0", "p"),
                    ("tm0", "3"),
                ],
            )

            blocks = {block.objname: block for block in target_page.blocks}
            self.assertEqual(_field_int(blocks["num0"], "val"), 7)
            self.assertEqual(_field_int(blocks["num0"], "lenth"), 3)
            self.assertEqual(_field_int(blocks["pic0"], "pic"), 0)
            self.assertEqual(_field_int(blocks["tm0"], "tim"), 1000)
            self.assertEqual(_field_int(blocks["tm0"], "en"), 0)
            self.assertIn("num0.val++", blocks["btn0"].event_tokens)
            self.assertIn("printh 23 02 42 49", blocks["btn0"].event_tokens)
            self.assertIn("num0.val++", blocks["tm0"].event_tokens)

            context = _build_event_compile_context(target_page.blocks)
            number_slot_start = sum(
                _user_slot_count(block) for block in target_page.blocks[: target_page.blocks.index(blocks["num0"])]
            )
            local_ref = (number_slot_start + 27).to_bytes(4, "little")
            button_event_table = _build_object_event_table(blocks["btn0"], context=context)
            timer_event_table = _build_object_event_table(blocks["tm0"], context=context)
            self.assertIn(b"\x07\x00\x00\x00\x01" + local_ref + b"++", button_event_table)
            self.assertIn(b"\x07\x00\x00\x00\x01" + local_ref + b"++", timer_event_table)
            self.assertIn(
                len(b"\x09\x0f\x0823 02 42 49").to_bytes(4, "little") + b"\x09\x0f\x0823 02 42 49",
                button_event_table,
            )

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
                                    "length": 5,
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
            self.assertEqual(_field_int(number, "lenth"), 5)

    @unittest.skipUnless(CASE_36_TFT.exists(), "local official xfloat fixture is not available")
    def test_scene_build_matches_official_xfloat_tail_layout(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "xfloat-case36", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "x0",
                                "type": "xfloat",
                                "x": 0,
                                "y": 0,
                                "w": 100,
                                "h": 30,
                                "value": 0,
                                "style": {"vvs0": 0, "vvs1": 0},
                            }
                        ],
                    }
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

            output_tft = Path(manifest["output_tft"])
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertEqual(manifest["tft_patch"]["added_count"], 1)
            self.assertEqual(_tft_compiled_tail_without_checksum(output_tft), _tft_compiled_tail_without_checksum(CASE_36_TFT))

            target_page = load_page_file(manifest["target_pa"])
            xfloat = target_page.blocks[-1]
            self.assertEqual(xfloat.objname, "x0")
            self.assertEqual(xfloat.type_code, ";")
            self.assertEqual(_compiled_primary_value(output_tft, Path(manifest["target_pa"]), "x0", ";", 0x44, 4), 0)
            self.assertEqual(_compiled_primary_value(output_tft, Path(manifest["target_pa"]), "x0", ";", 0x48, 1), 0)
            self.assertEqual(_compiled_primary_value(output_tft, Path(manifest["target_pa"]), "x0", ";", 0x49, 1), 0)

    @unittest.skipUnless((CASE_ROOT / "case_36_xfloat" / "lcd_test.HMI").exists(), "local xfloat fixture is not available")
    def test_scene_build_patches_xfloat_runtime_values(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "xfloat-values", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "xval",
                                "type": "xfloat",
                                "x": 308,
                                "y": 241,
                                "w": 196,
                                "h": 45,
                                "value": 123456,
                                "style": {"vvs0": 0, "vvs1": 3},
                            }
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
            self.assertEqual(_compiled_primary_value(output_tft, target_pa, "xval", ";", 0x44, 4), 123456)
            self.assertEqual(_compiled_primary_value(output_tft, target_pa, "xval", ";", 0x48, 1), 0)
            self.assertEqual(_compiled_primary_value(output_tft, target_pa, "xval", ";", 0x49, 1), 3)

    @unittest.skipUnless(CASE_37_TFT.exists(), "local official combobox fixture is not available")
    def test_scene_build_matches_official_combobox_tail_layout(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "combobox-case37", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "cb0",
                                "type": "combobox",
                                "x": 0,
                                "y": 0,
                                "w": 100,
                                "h": 42,
                            }
                        ],
                    }
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

            output_tft = Path(manifest["output_tft"])
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertEqual(manifest["tft_patch"]["added_count"], 1)
            self.assertEqual(_tft_compiled_tail_without_checksum(output_tft), _tft_compiled_tail_without_checksum(CASE_37_TFT))

            target_page = load_page_file(manifest["target_pa"])
            combo = target_page.blocks[-1]
            self.assertEqual(combo.objname, "cb0")
            self.assertEqual(combo.type_code, "=")
            self.assertEqual(_compiled_primary_value(output_tft, Path(manifest["target_pa"]), "cb0", "=", 0x5F, 1), 0)

    @unittest.skipUnless((CASE_ROOT / "case_37_combobox" / "lcd_test.HMI").exists(), "local combobox fixture is not available")
    def test_scene_build_patches_combobox_runtime_values(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "combobox-values", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "cbval",
                                "type": "combobox",
                                "x": 20,
                                "y": 40,
                                "w": 160,
                                "h": 42,
                                "value": 2,
                                "style": {"down": 1, "qty": 3},
                            }
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
            self.assertEqual(_compiled_primary_value(output_tft, target_pa, "cbval", "=", 0x5F, 1), 2)
            self.assertEqual(_compiled_primary_value(output_tft, target_pa, "cbval", "=", 0x65, 1), 1)
            self.assertEqual(_compiled_primary_value(output_tft, target_pa, "cbval", "=", 0x5D, 1), 3)

    @unittest.skipUnless(
        XFLOAT_COMBOBOX_DEMO_SCENE.exists()
        and all((CASE_ROOT / case_name / "lcd_test.HMI").exists() for case_name in ("case_36_xfloat", "case_37_combobox")),
        "local xfloat/combobox full-rebuild fixtures are not available",
    )
    def test_xfloat_combobox_demo_full_page_rebuild_covers_value_controls(self) -> None:
        scene = load_scene(XFLOAT_COMBOBOX_DEMO_SCENE)

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

            output_tft = Path(manifest["output_tft"])
            target_pa = Path(manifest["target_pa"])
            target_page = load_page_file(target_pa)
            self.assertTrue(output_tft.exists())
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertEqual(manifest["tft_patch"]["mode"], "experimental_clean_page_tft_rebuild")
            self.assertEqual(manifest["tft_patch"]["object_count"], 6)
            self.assertEqual(manifest["tft_patch"]["removed_seed_objects"], ["t0", "b0", "p0"])
            self.assertEqual(
                [(block.objname, block.type_code) for block in target_page.blocks],
                [
                    ("page0", "y"),
                    ("title", "t"),
                    ("xval", ";"),
                    ("cbval", "="),
                    ("hint", "t"),
                    ("hint2", "t"),
                ],
            )
            self.assertEqual(_compiled_primary_value(output_tft, target_pa, "xval", ";", 0x44, 4), 123456)
            self.assertEqual(_compiled_primary_value(output_tft, target_pa, "xval", ";", 0x48, 1), 0)
            self.assertEqual(_compiled_primary_value(output_tft, target_pa, "xval", ";", 0x49, 1), 3)
            self.assertEqual(_compiled_primary_value(output_tft, target_pa, "cbval", "=", 0x5F, 1), 2)
            self.assertEqual(_compiled_primary_value(output_tft, target_pa, "cbval", "=", 0x65, 1), 1)
            self.assertEqual(_compiled_primary_value(output_tft, target_pa, "cbval", "=", 0x5D, 1), 3)

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
        (CASE_ROOT / "case_45_touchcap_current_gui" / "lcd_test.HMI").exists(),
        "local touch-capture fixture is not available",
    )
    def test_scene_build_emits_touch_capture_widget_without_geometry(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "touch-capture-scene", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {"id": "tc_scene", "type": "touch-capture", "value": 0},
                        ],
                    }
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

            self.assertTrue(Path(manifest["output_tft"]).exists())
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertEqual(manifest["tft_patch"]["added_count"], 1)
            target_page = load_page_file(manifest["target_pa"])
            self.assertEqual(target_page.blocks[-1].objname, "tc_scene")
            self.assertEqual(target_page.blocks[-1].type_code, "\x05")

    @unittest.skipUnless(
        TOUCH_CAPTURE_DEMO_SCENE.exists()
        and (CASE_ROOT / "case_45_touchcap_current_gui" / "lcd_test.HMI").exists(),
        "local touch-capture fixture or demo scene is not available",
    )
    def test_touch_capture_full_page_rebuild_minimal_control(self) -> None:
        scene = load_scene(TOUCH_CAPTURE_DEMO_SCENE)

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

            target_page = load_page_file(manifest["target_pa"])
            self.assertTrue(Path(manifest["output_tft"]).exists())
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertEqual(manifest["tft_patch"]["mode"], "experimental_clean_page_tft_rebuild")
            self.assertEqual(manifest["tft_patch"]["object_count"], 3)
            self.assertEqual(manifest["tft_patch"]["removed_seed_objects"], ["t0", "b0", "p0"])
            self.assertEqual(
                [(block.objname, block.type_code) for block in target_page.blocks],
                [("page0", "y"), ("title", "t"), ("tc0", "\x05")],
            )

    @unittest.skipUnless(
        CASE_46_TFT.exists()
        and (CASE_ROOT / "case_46_expicture_current_gui" / "official_compile_baseline" / "lcd_test.run").exists(),
        "local external-picture fixture is not available",
    )
    def test_scene_build_matches_official_external_picture_tail_layout(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "external-picture-scene", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "exp0",
                                "type": "external-picture",
                                "x": 0,
                                "y": 0,
                                "w": 120,
                                "h": 120,
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
                baseline_tft=CASE_ROOT / "case_46_expicture_current_gui" / "official_compile_baseline" / "lcd_test.run",
            )

            output_tft = Path(manifest["output_tft"])
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertEqual(output_tft.read_bytes(), CASE_46_TFT.read_bytes())
            target_page = load_page_file(manifest["target_pa"])
            self.assertEqual(target_page.blocks[-1].objname, "exp0")
            self.assertEqual(target_page.blocks[-1].type_code, "<")

    @unittest.skipUnless(
        CASE_46_TFT.exists()
        and (CASE_ROOT / "case_46_expicture_current_gui" / "official_compile_baseline" / "lcd_test.run").exists(),
        "local external-picture fixture is not available",
    )
    def test_scene_build_emits_external_picture_path_buffer(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "external-picture-path", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "sdpic",
                                "type": "expicture",
                                "x": 24,
                                "y": 32,
                                "w": 320,
                                "h": 180,
                                "resources": {"path": "A001.JPG"},
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
                baseline_tft=CASE_ROOT / "case_46_expicture_current_gui" / "official_compile_baseline" / "lcd_test.run",
            )

            output_tft = Path(manifest["output_tft"])
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertIn(b"A001.JPG", output_tft.read_bytes())
            target_page = load_page_file(manifest["target_pa"])
            block = target_page.blocks[-1]
            self.assertEqual(block.objname, "sdpic")
            self.assertEqual(block.type_code, "<")

    @unittest.skipUnless(
        CASE_46_TFT.exists(),
        "local external-picture fixture is not available",
    )
    def test_scene_build_external_picture_keeps_live_healthy_resource_baseline(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "external-picture-good-resource", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "exp0",
                                "type": "external-picture",
                                "x": 0,
                                "y": 0,
                                "w": 120,
                                "h": 120,
                                "resources": {"path": "sd0/1.jpg"},
                            },
                        ],
                    }
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

            output_tft = Path(manifest["output_tft"])
            baseline_info = inspect_tft(BASELINE_TFT)["parsed"]
            output_info = inspect_tft(output_tft)["parsed"]
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertEqual(manifest["tft_patch"]["added_count"], 1)
            self.assertIn(b"sd0/1.jpg", output_tft.read_bytes())
            self.assertEqual(
                output_info["Header1"]["ressource_files_size"],
                baseline_info["Header1"]["ressource_files_size"],
            )
            self.assertEqual(
                output_info["Header1"]["ressource_files_crc"],
                baseline_info["Header1"]["ressource_files_crc"],
            )
            self.assertEqual(
                output_info["Header2"]["unknown_objects_address"],
                baseline_info["Header2"]["unknown_objects_address"],
            )

    @unittest.skipUnless(
        (Path(__file__).resolve().parents[1] / "examples" / "external_picture_demo" / "scene.json").exists()
        and (CASE_ROOT / "case_46_expicture_current_gui" / "lcd_test.HMI").exists(),
        "local external-picture demo fixture is not available",
    )
    def test_external_picture_demo_builds_with_live_healthy_baseline(self) -> None:
        scene = load_scene(EXTERNAL_PICTURE_DEMO_SCENE)

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

            output_tft = Path(manifest["output_tft"])
            output_info = inspect_tft(output_tft)["parsed"]
            baseline_info = inspect_tft(BASELINE_TFT)["parsed"]
            target_page = load_page_file(manifest["target_pa"])
            object_names = [block.objname for block in target_page.blocks]
            exp0_primary_path = _compiled_page_primary_value(output_tft, target_page, "exp0", "<", 0x3C, 4)
            exp0_user_path = _compiled_page_user_record_word1(output_tft, target_page, "exp0", slot_index=19)
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertIn("exp0", object_names)
            self.assertIn("guard", object_names)
            self.assertIn(b"sd0/1.jpg", output_tft.read_bytes())
            self.assertEqual(exp0_user_path, exp0_primary_path)
            self.assertEqual(output_info["Header1"]["ressource_files_size"], baseline_info["Header1"]["ressource_files_size"])
            self.assertEqual(output_info["Header1"]["ressource_files_crc"], baseline_info["Header1"]["ressource_files_crc"])
            self.assertEqual(output_info["Header2"]["unknown_objects_address"], baseline_info["Header2"]["unknown_objects_address"])

    @unittest.skipUnless(
        EXTERNAL_PICTURE_DEMO_SCENE.exists()
        and (CASE_ROOT / "case_46_expicture_current_gui" / "lcd_test.HMI").exists(),
        "local external-picture demo fixture is not available",
    )
    def test_external_picture_demo_full_page_rebuild_preserves_sd_path_object(self) -> None:
        scene = load_scene(EXTERNAL_PICTURE_DEMO_SCENE)

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

            output_tft = Path(manifest["output_tft"])
            output_info = inspect_tft(output_tft)["parsed"]
            baseline_info = inspect_tft(BASELINE_TFT)["parsed"]
            target_page = load_page_file(manifest["target_pa"])
            exp0_primary_path = _compiled_page_primary_value(output_tft, target_page, "exp0", "<", 0x3C, 4)
            exp0_user_path = _compiled_page_user_record_word1(output_tft, target_page, "exp0", slot_index=19)

            self.assertTrue(output_tft.exists())
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertEqual(manifest["tft_patch"]["mode"], "experimental_clean_page_tft_rebuild")
            self.assertEqual(manifest["tft_patch"]["object_count"], 9)
            self.assertEqual(manifest["tft_patch"]["removed_seed_objects"], ["t0", "b0", "p0"])
            self.assertEqual(
                [(block.objname, block.type_code) for block in target_page.blocks],
                [
                    ("page0", "y"),
                    ("title", "t"),
                    ("badge", "t"),
                    ("frame", "t"),
                    ("exp0", "<"),
                    ("status", "t"),
                    ("pathbox", "t"),
                    ("guard", "t"),
                    ("footer", "t"),
                ],
            )
            self.assertIn(b"sd0/1.jpg", output_tft.read_bytes())
            self.assertEqual(exp0_user_path, exp0_primary_path)
            self.assertEqual(output_info["Header1"]["ressource_files_size"], baseline_info["Header1"]["ressource_files_size"])
            self.assertEqual(output_info["Header1"]["ressource_files_crc"], baseline_info["Header1"]["ressource_files_crc"])
            self.assertEqual(output_info["Header2"]["unknown_objects_address"], baseline_info["Header2"]["unknown_objects_address"])

    @unittest.skipUnless(
        CASE_46_TFT.exists()
        and (CASE_ROOT / "case_46_expicture_current_gui" / "official_compile_baseline" / "lcd_test.run").exists(),
        "local external-picture fixture is not available",
    )
    def test_scene_build_external_picture_path_only_changes_path_slot_and_checksum(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "external-picture-path-diff", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "exp0",
                                "type": "external-picture",
                                "x": 0,
                                "y": 0,
                                "w": 120,
                                "h": 120,
                                "resources": {"path": "A001.JPG"},
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
                baseline_tft=CASE_ROOT / "case_46_expicture_current_gui" / "official_compile_baseline" / "lcd_test.run",
            )

            official = CASE_46_TFT.read_bytes()
            generated = Path(manifest["output_tft"]).read_bytes()
            diff_indexes = [index for index, (left, right) in enumerate(zip(official, generated)) if left != right]
            self.assertEqual(diff_indexes[:8], list(range(0xA80397, 0xA8039F)))
            self.assertEqual(diff_indexes[8:], list(range(len(generated) - 4, len(generated))))
            self.assertEqual(generated[0xA80397:0xA8039F], b"A001.JPG")
            self.assertTrue(manifest["tft_checksum"]["valid"])

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

    @unittest.skipUnless(
        SEED_HMI.exists()
        and BASELINE_TFT.exists()
        and NEW_CONTROLS_DEMO_SCENE.exists()
        and all((CASE_ROOT / case_name / "lcd_test.HMI").exists() for case_name in (
            "case_17_slider",
            "case_18_gauge",
            "case_20_progress",
            "case_21_qrcode",
            "case_22_scrolling_text",
            "case_23_dual_state_button",
            "case_24_state_button",
            "case_25_hotspot_touch_area",
            "case_26_variable_numeric_string",
            "case_27_waveform_basic",
            "case_28_checkbox",
            "case_29_radio",
            "case_30_crop_image",
        )),
        "local new-controls full-rebuild fixtures are not available",
    )
    def test_new_controls_demo_full_page_rebuild_covers_fixture_backed_controls(self) -> None:
        scene = load_scene(NEW_CONTROLS_DEMO_SCENE)

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

            self.assertTrue(Path(manifest["output_tft"]).exists())
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertEqual(manifest["tft_patch"]["mode"], "experimental_clean_page_tft_rebuild")
            self.assertEqual(manifest["tft_patch"]["object_count"], 15)

            target_page = load_page_file(manifest["target_pa"])
            self.assertEqual(
                [(block.objname, block.type_code) for block in target_page.blocks],
                [
                    ("page0", "y"),
                    ("bar1", "j"),
                    ("slider1", "\x01"),
                    ("gauge1", "z"),
                    ("qr1", ":"),
                    ("g0", "7"),
                    ("bt0", "5"),
                    ("bt1", "5"),
                    ("sw0", "C"),
                    ("c0", "8"),
                    ("r0", "9"),
                    ("m0", "m"),
                    ("q0", "q"),
                    ("va0", "4"),
                    ("s0", "\x00"),
                ],
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

    def test_scene_build_emits_page1_plain_control_tft(self) -> None:
        page1_widgets = [
            {"id": "p1t", "type": "text", "x": 40, "y": 30, "w": 160, "h": 40, "text": "P1"},
            {"id": "p1b", "type": "button", "x": 220, "y": 30, "w": 120, "h": 50, "text": "BTN"},
            {"id": "n1", "type": "number", "x": 40, "y": 100, "w": 120, "h": 40, "value": 123},
            {"id": "img1", "type": "image", "x": 220, "y": 100, "w": 96, "h": 64, "resources": {"pic": 0}},
            {"id": "bar1", "type": "progress", "x": 40, "y": 160, "w": 220, "h": 28, "value": 68},
            {"id": "slider1", "type": "slider", "x": 40, "y": 220, "w": 220, "h": 40, "value": 42},
            {"id": "gauge1", "type": "gauge", "x": 360, "y": 80, "w": 160, "h": 160, "value": 75},
            {"id": "check1", "type": "checkbox", "x": 560, "y": 80, "w": 28, "h": 28, "value": 1},
            {"id": "radio1", "type": "radio", "x": 610, "y": 80, "w": 28, "h": 28, "value": 1},
        ]
        for widgets in (page1_widgets, list(reversed(page1_widgets))):
            scene = validate_scene(
                {
                    "project": {"name": "multi-page-page1-plain-controls", "default_page": "page0"},
                    "canvas": {"width": 800, "height": 480, "background_color": 65535},
                    "assets": {},
                    "pages": [
                        {"id": "page0", "layout": {"type": "absolute"}, "widgets": []},
                        {"id": "page1", "layout": {"type": "absolute"}, "widgets": widgets},
                    ],
                }
            )

            with self.subTest(order=[item["id"] for item in widgets]), tempfile.TemporaryDirectory() as temp_dir:
                manifest = build_scene(scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

                self.assertTrue(Path(manifest["output_tft"]).exists())
                self.assertTrue(manifest["tft_checksum"]["valid"])
                self.assertEqual(manifest["tft_patch"]["mode"], "experimental_multi_page_tft_patch")
                self.assertEqual(manifest["tft_patch"]["page_count"], 2)
                self.assertEqual(manifest["tft_patch"]["object_count"], 14)

                page1_path = Path(manifest["target_pages"][1])
                page1 = load_page_file(page1_path)
                self.assertEqual([block.objname for block in page1.blocks], ["page1", *[item["id"] for item in widgets]])
                self.assertEqual(
                    _compiled_page_hash_ids(Path(manifest["output_tft"]), page1_path),
                    {block.objname: _field_int(block, "id") for block in page1.blocks},
                )
                checks = {
                    "n1": ("6", 0x44, 4, 123),
                    "img1": ("p", 0x38, 2, 0),
                    "bar1": ("j", 0x3A, 1, 68),
                    "slider1": ("\x01", 0x42, 2, 42),
                    "gauge1": ("z", 0x3C, 2, 75),
                    "check1": ("8", 0x40, 1, 1),
                    "radio1": ("9", 0x3C, 1, 1),
                }
                for name, (type_code, offset, width, expected) in checks.items():
                    with self.subTest(name=name):
                        self.assertEqual(
                            _compiled_page_primary_value(
                                Path(manifest["output_tft"]),
                                page1_path,
                                name,
                                type_code,
                                offset,
                                width,
                            ),
                            expected,
                        )
                self.assertEqual(
                    _compiled_page1_mirror_headers(Path(manifest["output_tft"]), page1),
                    [
                        bytes([ord(block.type_code), _field_int(block, "id"), 0, _record_header_flag(block.type_code)])
                        for block in page1.blocks
                    ],
                )

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
                                "events": {"up": ["page 1"]},
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
            self.assertIn("page 1", back_button.event_tokens)

    def test_scene_build_emits_two_way_seed_page0_and_page1_button_events(self) -> None:
        scene = validate_scene(
            {
                "project": {
                    "name": "multi-page-two-way-button-event",
                    "default_page": "page0",
                    "experimental_multi_page_events": True,
                    "patch_seed_page0_widgets": True,
                },
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "b0",
                                "type": "button",
                                "x": 192,
                                "y": 239,
                                "w": 100,
                                "h": 50,
                                "text": "TO P1",
                                "events": {"up": ["page 0"]},
                            }
                        ],
                    },
                    {
                        "id": "page1",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "back0",
                                "type": "button",
                                "x": 72,
                                "y": 154,
                                "w": 180,
                                "h": 64,
                                "text": "BACK",
                                "events": {"up": ["page 1"]},
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
            page0 = load_page_file(manifest["target_pages"][0])
            page1 = load_page_file(manifest["target_pages"][1])
            seed_button = next(block for block in page0.blocks if block.objname == "b0")
            back_button = next(block for block in page1.blocks if block.objname == "back0")
            self.assertIn("codesup-1", seed_button.event_tokens)
            self.assertIn("page 0", seed_button.event_tokens)
            self.assertEqual(seed_button.get_field("txt").value.decode("gbk"), "TO P1")
            self.assertIn("codesup-1", back_button.event_tokens)
            self.assertIn("page 1", back_button.event_tokens)

    def test_scene_build_rejects_seed_page0_patch_without_opt_in(self) -> None:
        scene = validate_scene(
            {
                "project": {
                    "name": "multi-page-bad-page0-patch",
                    "default_page": "page0",
                    "experimental_multi_page_events": True,
                },
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "b0",
                                "type": "button",
                                "x": 192,
                                "y": 239,
                                "w": 100,
                                "h": 50,
                                "events": {"up": ["page 0"]},
                            }
                        ],
                    },
                    {"id": "page1", "layout": {"type": "absolute"}, "widgets": []},
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(Exception, "seed object layout unchanged"):
                build_scene(scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

    def test_page1_experimental_button_event_aliases_match_tft_patcher(self) -> None:
        for line in (
            "page 0",
            "page 1",
            "page page0",
            "page page1",
            "numval.val++",
            "numval.val=7",
            "printh 23 02 54 45",
            "printh AA bb 00",
        ):
            with self.subTest(line=line):
                widget = WidgetSpec("back0", "button", events={"up": [line]})
                self.assertTrue(_is_supported_experimental_page1_event_widget(widget))

        for line in ("page 2", "printh", "printh GG", "click probe0,0", "vis label0,0", "rawhex 09 0c 04 31"):
            with self.subTest(line=line):
                widget = WidgetSpec("back0", "button", events={"up": [line]})
                self.assertFalse(_is_supported_experimental_page1_event_widget(widget))

        hide = WidgetSpec("hide0", "button", events={"down": ["vis label0,0"]})
        show = WidgetSpec("show0", "button", events={"down": ["vis label0,1"]})
        refresh = WidgetSpec("ref0", "button", events={"down": ["ref label0"]})
        touch_disable = WidgetSpec("tsw0", "button", events={"down": ["tsw label0,0"]})
        touch_all = WidgetSpec("tswall0", "button", events={"down": ["tsw 255,1"]})
        label = WidgetSpec("label0", "text")
        self.assertTrue(_is_supported_experimental_page1_event_widget(hide, page1_widgets=[hide, show, label]))
        self.assertTrue(_is_supported_experimental_page1_event_widget(show, page1_widgets=[hide, show, label]))
        self.assertTrue(_is_supported_experimental_page1_event_widget(refresh, page1_widgets=[refresh, label]))
        self.assertTrue(_is_supported_experimental_page1_event_widget(touch_disable, page1_widgets=[touch_disable, label]))
        self.assertTrue(_is_supported_experimental_page1_event_widget(touch_all, page1_widgets=[touch_all, label]))

        self_hide = WidgetSpec("hide0", "button", events={"down": ["vis hide0,0"]})
        self_ref = WidgetSpec("ref0", "button", events={"down": ["ref ref0"]})
        missing = WidgetSpec("bad0", "button", events={"down": ["vis missing0,0"]})
        missing_ref = WidgetSpec("bad2", "button", events={"down": ["ref missing0"]})
        missing_tsw = WidgetSpec("bad3", "button", events={"down": ["tsw missing0,0"]})
        bad_state = WidgetSpec("bad1", "button", events={"down": ["vis label0,2"]})
        self.assertFalse(_is_supported_experimental_page1_event_widget(self_hide, page1_widgets=[self_hide, label]))
        self.assertFalse(_is_supported_experimental_page1_event_widget(self_ref, page1_widgets=[self_ref, label]))
        self.assertFalse(_is_supported_experimental_page1_event_widget(missing, page1_widgets=[missing, label]))
        self.assertFalse(_is_supported_experimental_page1_event_widget(missing_ref, page1_widgets=[missing_ref, label]))
        self.assertFalse(_is_supported_experimental_page1_event_widget(missing_tsw, page1_widgets=[missing_tsw, label]))
        self.assertFalse(_is_supported_experimental_page1_event_widget(bad_state, page1_widgets=[bad_state, label]))

    def test_page1_experimental_page_load_event_allow_list_is_narrow(self) -> None:
        self.assertTrue(
            _is_supported_experimental_page1_page_events({"load": ["printh 23 02 50 4C"]})
        )

        for events in (
            {"load": ["printh 23 02 50"]},
            {"load": ["printh 23 02 50 4C 00"]},
            {"loadend": ["printh 23 02 50 4C"]},
            {"load": ["printh 23 02 50 4C", "printh 23 02 50 4D"]},
            {"load": ["page 1"]},
            {"load": ["click sink0,0"]},
            {"load": ["rawhex 09 0c 04 31"]},
        ):
            with self.subTest(events=events):
                self.assertFalse(_is_supported_experimental_page1_page_events(events))

    def test_page1_experimental_click_event_requires_same_page_printh_target(self) -> None:
        fire = WidgetSpec("fire0", "button", events={"up": ["click sink0,0"]})
        sink = WidgetSpec("sink0", "button", events={"up": ["printh 23 02 43 4B"]})
        number = WidgetSpec("numval", "number")
        self.assertTrue(_is_supported_experimental_page1_event_widget(fire, page1_widgets=[fire, sink]))

        with self.subTest("self click is rejected"):
            self_click = WidgetSpec("fire0", "button", events={"up": ["click fire0,0"]})
            self.assertFalse(
                _is_supported_experimental_page1_event_widget(self_click, page1_widgets=[self_click, sink])
            )

        with self.subTest("missing target is rejected"):
            self.assertFalse(_is_supported_experimental_page1_event_widget(fire, page1_widgets=[fire]))

        with self.subTest("non-button target is rejected"):
            bad_target = WidgetSpec("numval", "button", events={"up": ["click numval,0"]})
            self.assertFalse(
                _is_supported_experimental_page1_event_widget(bad_target, page1_widgets=[bad_target, number])
            )

        with self.subTest("target click cascade is rejected"):
            loop_sink = WidgetSpec("sink0", "button", events={"up": ["click fire0,0"]})
            self.assertFalse(_is_supported_experimental_page1_event_widget(fire, page1_widgets=[fire, loop_sink]))

        with self.subTest("target non-printh event is rejected"):
            page_sink = WidgetSpec("sink0", "button", events={"up": ["page 1"]})
            self.assertFalse(_is_supported_experimental_page1_event_widget(fire, page1_widgets=[fire, page_sink]))

    def test_scene_build_emits_experimental_page1_button_printh_event_tft_when_enabled(self) -> None:
        scene = validate_scene(
            {
                "project": {
                    "name": "multi-page-page1-button-printh-event",
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
                                "id": "probe0",
                                "type": "button",
                                "x": 72,
                                "y": 154,
                                "w": 180,
                                "h": 64,
                                "text": "PING",
                                "events": {"up": ["printh 23 02 50 31"]},
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
            page1 = load_page_file(manifest["target_pages"][1])
            probe_button = next(block for block in page1.blocks if block.objname == "probe0")
            self.assertIn("codesup-1", probe_button.event_tokens)
            self.assertIn("printh 23 02 50 31", probe_button.event_tokens)

    def test_scene_build_emits_experimental_page1_button_click_event_tft_when_enabled(self) -> None:
        scene = validate_scene(
            {
                "project": {
                    "name": "multi-page-page1-button-click-event",
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
                                "id": "fire0",
                                "type": "button",
                                "x": 72,
                                "y": 154,
                                "w": 180,
                                "h": 64,
                                "text": "FIRE",
                                "events": {"up": ["click sink0,0"]},
                            },
                            {
                                "id": "sink0",
                                "type": "button",
                                "x": 292,
                                "y": 154,
                                "w": 180,
                                "h": 64,
                                "text": "SINK",
                                "events": {"up": ["printh 23 02 43 4B"]},
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
            page1 = load_page_file(manifest["target_pages"][1])
            fire_button = next(block for block in page1.blocks if block.objname == "fire0")
            sink_button = next(block for block in page1.blocks if block.objname == "sink0")
            self.assertIn("codesup-1", fire_button.event_tokens)
            self.assertIn("click sink0,0", fire_button.event_tokens)
            self.assertIn("codesup-1", sink_button.event_tokens)
            self.assertIn("printh 23 02 43 4B", sink_button.event_tokens)

    def test_scene_build_emits_experimental_page1_button_ref_tsw_event_tft_when_enabled(self) -> None:
        scene = validate_scene(
            {
                "project": {
                    "name": "multi-page-page1-button-ref-tsw-event",
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
                                "id": "label0",
                                "type": "text",
                                "x": 72,
                                "y": 70,
                                "w": 280,
                                "h": 50,
                                "text": "REFRESH ME",
                            },
                            {
                                "id": "ref0",
                                "type": "button",
                                "x": 72,
                                "y": 154,
                                "w": 150,
                                "h": 58,
                                "text": "REF",
                                "events": {"down": ["ref label0"]},
                            },
                            {
                                "id": "tsw0",
                                "type": "button",
                                "x": 242,
                                "y": 154,
                                "w": 150,
                                "h": 58,
                                "text": "TSW0",
                                "events": {"down": ["tsw label0,0"]},
                            },
                            {
                                "id": "all0",
                                "type": "button",
                                "x": 412,
                                "y": 154,
                                "w": 150,
                                "h": 58,
                                "text": "ALL",
                                "events": {"down": ["tsw 255,1"]},
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
            page1 = load_page_file(manifest["target_pages"][1])
            ref_button = next(block for block in page1.blocks if block.objname == "ref0")
            tsw_button = next(block for block in page1.blocks if block.objname == "tsw0")
            all_button = next(block for block in page1.blocks if block.objname == "all0")
            self.assertIn("ref label0", ref_button.event_tokens)
            self.assertIn("tsw label0,0", tsw_button.event_tokens)
            self.assertIn("tsw 255,1", all_button.event_tokens)

    def test_scene_build_emits_experimental_page1_load_printh_event_tft_when_enabled(self) -> None:
        scene = validate_scene(
            {
                "project": {
                    "name": "multi-page-page1-load-printh-event",
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
                        "events": {"load": ["printh 23 02 50 4C"]},
                        "widgets": [
                            {
                                "id": "p1title",
                                "type": "text",
                                "x": 72,
                                "y": 64,
                                "w": 320,
                                "h": 58,
                                "text": "LOAD",
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
            summary = manifest["tft_patch"]["experimental_event_summary"]
            self.assertEqual(len(summary["page1_page_events"]), 1)
            self.assertEqual(
                summary["page1_page_events"][0]["runtime_status"],
                "compile_only_scheduler_unrecovered",
            )
            self.assertEqual(summary["page1_object_events"], [])
            page1 = load_page_file(manifest["target_pages"][1])
            self.assertIn("codesload-1", page1.blocks[0].event_tokens)
            self.assertIn("printh 23 02 50 4C", page1.blocks[0].event_tokens)

    def test_scene_build_emits_experimental_page1_button_numeric_event_tft_when_enabled(self) -> None:
        scene = validate_scene(
            {
                "project": {
                    "name": "multi-page-page1-button-numeric-event",
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
                                "id": "numval",
                                "type": "number",
                                "x": 72,
                                "y": 70,
                                "w": 220,
                                "h": 60,
                                "value": 3,
                            },
                            {
                                "id": "inc0",
                                "type": "button",
                                "x": 72,
                                "y": 154,
                                "w": 180,
                                "h": 64,
                                "text": "INC",
                                "events": {"down": ["numval.val++"]},
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
            inc_button = next(block for block in page1.blocks if block.objname == "inc0")
            self.assertIn("codesdown-1", inc_button.event_tokens)
            self.assertIn("numval.val++", inc_button.event_tokens)

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
                                "events": {"up": ["page 1"]},
                            }
                        ],
                    },
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(Exception, "page1 widget events"):
                build_scene(bad_scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

        bad_page_event_scene = validate_scene(
            {
                "project": {"name": "bad-page1-load-event", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480},
                "assets": {},
                "pages": [
                    {"id": "page0", "layout": {"type": "absolute"}, "widgets": []},
                    {
                        "id": "page1",
                        "layout": {"type": "absolute"},
                        "events": {"load": ["printh 23 02 50 4C"]},
                        "widgets": [],
                    },
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(Exception, "page1 events"):
                build_scene(bad_page_event_scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

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
                                "type": "qrcode",
                                "x": 10,
                                "y": 10,
                                "w": 100,
                                "h": 32,
                                "text": "NOPE",
                            }
                        ],
                    },
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(
                Exception,
                "page1 supports only text/button/number/image/progress/slider/gauge/checkbox/radio",
            ):
                build_scene(bad_scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

    def test_scene_build_rejects_page1_new_image_resources(self) -> None:
        bad_scene = validate_scene(
            {
                "project": {"name": "bad-page1-image-resource", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480},
                "assets": {},
                "pages": [
                    {"id": "page0", "layout": {"type": "absolute"}, "widgets": []},
                    {
                        "id": "page1",
                        "layout": {"type": "absolute"},
                        "widgets": [
                            {
                                "id": "img1",
                                "type": "image",
                                "x": 10,
                                "y": 10,
                                "w": 100,
                                "h": 60,
                                "resources": {"asset": "newpic"},
                            }
                        ],
                    },
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(Exception, "page1 widget resources"):
                build_scene(bad_scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

    def test_scene_build_can_minimize_seed_objects_in_bounds(self) -> None:
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
                self.assertEqual(_field_int(block, "x"), 799)
                self.assertEqual(_field_int(block, "y"), 479)
                self.assertEqual(_field_int(block, "w"), 1)
                self.assertEqual(_field_int(block, "h"), 1)
            self.assertEqual(target_page.blocks[-1].objname, "note1")
            self.assertTrue(manifest["tft_checksum"]["valid"])

    def test_scene_full_page_rebuild_drops_seed_and_keeps_number_button_event(self) -> None:
        scene = load_scene(NUMBER_DEMO_FULL_REBUILD_SCENE)

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(
                scene,
                SEED_HMI,
                temp_dir,
                baseline_tft=BASELINE_TFT,
            )

            self.assertEqual(manifest["tft_patch"]["mode"], "experimental_clean_page_tft_rebuild")
            self.assertEqual(manifest["tft_patch"]["removed_seed_objects"], ["t0", "b0", "p0"])
            self.assertEqual(
                [item["name"] for item in manifest["tft_patch"]["objects"]],
                ["page0", "title", "incbtn", "numval"],
            )
            self.assertEqual(
                [item["id"] for item in manifest["tft_patch"]["objects"]],
                [0, 1, 2, 3],
            )
            self.assertEqual(
                [item["type"] for item in manifest["tft_patch"]["objects"]],
                ["y", "t", "b", "6"],
            )
            self.assertTrue(manifest["tft_checksum"]["valid"])

            target_page = load_page_file(manifest["target_pa"])
            target_names = [block.objname for block in target_page.blocks]
            self.assertEqual(target_names, ["page0", "title", "incbtn", "numval"])
            self.assertFalse({"t0", "b0", "p0"} & set(target_names))
            self.assertEqual([_field_int(block, "id") for block in target_page.blocks], [0, 1, 2, 3])
            self.assertEqual(len({object_name_hash(name) for name in target_names}), len(target_names))

            incbtn = next(block for block in target_page.blocks if block.objname == "incbtn")
            self.assertIn("codesdown-2", incbtn.event_tokens)
            self.assertIn("numval.val++", incbtn.event_tokens)
            self.assertIn("printh 23 02 4e 31", incbtn.event_tokens)

            numval = next(block for block in target_page.blocks if block.objname == "numval")
            self.assertEqual(_field_int(numval, "val"), 123)
            self.assertEqual(_field_int(numval, "lenth"), 3)

    @unittest.skipUnless(GB2312_FONT_ZI.exists(), "local verified GB2312 .zi font fixture is not available")
    def test_scene_full_page_rebuild_reorders_supported_widgets_with_gb2312_font(self) -> None:
        scene = load_scene(NUMBER_DEMO_REORDER_SCENE)

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(
                scene,
                SEED_HMI,
                temp_dir,
                baseline_tft=BASELINE_TFT,
                font_zi=GB2312_FONT_ZI,
            )

            self.assertEqual(manifest["tft_patch"]["mode"], "experimental_clean_page_tft_rebuild")
            self.assertEqual(manifest["tft_patch"]["removed_seed_objects"], ["t0", "b0", "p0"])
            self.assertEqual(
                [item["name"] for item in manifest["tft_patch"]["objects"]],
                ["page0", "status", "incbtn", "title", "footer", "numval"],
            )
            self.assertEqual(
                [item["id"] for item in manifest["tft_patch"]["objects"]],
                [0, 1, 2, 3, 4, 5],
            )
            self.assertEqual(
                [item["type"] for item in manifest["tft_patch"]["objects"]],
                ["y", "t", "b", "t", "t", "6"],
            )
            self.assertEqual(manifest["tft_font_patch"]["font_info"]["font_name"], "UiCNEN32GBFull")
            self.assertEqual(manifest["tft_font_patch"]["font_info"]["encoding_name"], "gb2312")
            self.assertTrue(manifest["tft_checksum"]["valid"])

            target_page = load_page_file(manifest["target_pa"])
            target_names = [block.objname for block in target_page.blocks]
            self.assertEqual(target_names, ["page0", "status", "incbtn", "title", "footer", "numval"])
            self.assertFalse({"t0", "b0", "p0"} & set(target_names))
            self.assertEqual(len({object_name_hash(name) for name in target_names}), len(target_names))

            incbtn = next(block for block in target_page.blocks if block.objname == "incbtn")
            self.assertEqual(_field_int(incbtn, "id"), 2)
            self.assertIn("codesdown-2", incbtn.event_tokens)
            self.assertIn("numval.val++", incbtn.event_tokens)
            self.assertIn("printh 23 02 4e 31", incbtn.event_tokens)

            numval = next(block for block in target_page.blocks if block.objname == "numval")
            self.assertEqual(_field_int(numval, "id"), 5)
            self.assertEqual(_field_int(numval, "val"), 123)
            self.assertEqual(_field_int(numval, "lenth"), 3)

            number_slot_start = sum(_user_slot_count(block) for block in target_page.blocks[: target_page.blocks.index(numval)])
            local_ref = (number_slot_start + 27).to_bytes(4, "little")
            compiled = _build_object_event_table(incbtn, context=_build_event_compile_context(target_page.blocks))
            self.assertIn(b"\x07\x00\x00\x00\x01" + local_ref + b"++", compiled)

    @unittest.skipUnless(GB2312_FONT_ZI.exists(), "local verified GB2312 .zi font fixture is not available")
    def test_scene_full_page_rebuild_preserves_same_page_event_matrix_offline(self) -> None:
        scene = load_scene(NUMBER_DEMO_EVENT_MATRIX_SCENE)

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(
                scene,
                SEED_HMI,
                temp_dir,
                baseline_tft=BASELINE_TFT,
                font_zi=GB2312_FONT_ZI,
            )

            self.assertEqual(manifest["tft_patch"]["mode"], "experimental_clean_page_tft_rebuild")
            self.assertEqual(manifest["tft_patch"]["removed_seed_objects"], ["t0", "b0", "p0"])
            self.assertEqual(
                [item["name"] for item in manifest["tft_patch"]["objects"]],
                ["page0", "refbtn", "visbtn", "tswbtn", "incbtn", "label0", "numval"],
            )
            self.assertEqual(
                [item["id"] for item in manifest["tft_patch"]["objects"]],
                [0, 1, 2, 3, 4, 5, 6],
            )
            self.assertEqual(
                [item["type"] for item in manifest["tft_patch"]["objects"]],
                ["y", "b", "b", "b", "b", "t", "6"],
            )
            self.assertEqual(manifest["tft_font_patch"]["font_info"]["font_name"], "UiCNEN32GBFull")
            self.assertEqual(manifest["tft_font_patch"]["font_info"]["encoding_name"], "gb2312")
            self.assertTrue(manifest["tft_checksum"]["valid"])

            target_page = load_page_file(manifest["target_pa"])
            target_names = [block.objname for block in target_page.blocks]
            self.assertEqual(target_names, ["page0", "refbtn", "visbtn", "tswbtn", "incbtn", "label0", "numval"])
            self.assertFalse({"t0", "b0", "p0"} & set(target_names))
            self.assertEqual(len({object_name_hash(name) for name in target_names}), len(target_names))

            blocks = {block.objname: block for block in target_page.blocks}
            self.assertEqual(_field_int(blocks["label0"], "id"), 5)
            self.assertEqual(_field_int(blocks["numval"], "id"), 6)
            self.assertEqual(_field_int(blocks["numval"], "val"), 123)
            self.assertEqual(_field_int(blocks["numval"], "lenth"), 3)

            self.assertIn("codesdown-1", blocks["refbtn"].event_tokens)
            self.assertIn("ref label0", blocks["refbtn"].event_tokens)
            self.assertIn("codesdown-1", blocks["visbtn"].event_tokens)
            self.assertIn("vis label0,0", blocks["visbtn"].event_tokens)
            self.assertIn("codesdown-1", blocks["tswbtn"].event_tokens)
            self.assertIn("tsw label0,0", blocks["tswbtn"].event_tokens)
            self.assertIn("codesdown-1", blocks["incbtn"].event_tokens)
            self.assertIn("numval.val++", blocks["incbtn"].event_tokens)

            context = _build_event_compile_context(target_page.blocks)
            event_layout = _build_event_layout(target_page.blocks, 0, image_button_layout=False)
            for object_name in ("refbtn", "visbtn", "tswbtn", "incbtn"):
                callback_offset = event_layout.callbacks[target_page.blocks.index(blocks[object_name])]["codesdown-"]
                self.assertNotEqual(callback_offset, 0xFFFFFFFF)
                self.assertGreaterEqual(callback_offset, 0)

            self.assertIn(
                len(b"\x09\x03\x04label0").to_bytes(4, "little") + b"\x09\x03\x04label0",
                _build_object_event_table(blocks["refbtn"], context=context),
            )
            ref_items = decode_event_table(_build_object_event_table(blocks["refbtn"], context=context))
            self.assertEqual([(item.get("command"), item.get("args")) for item in ref_items if item["kind"] == "command"], [("ref", "label0")])
            self.assertIn(
                len(b"\x09\x05\x04label0,0").to_bytes(4, "little") + b"\x09\x05\x04label0,0",
                _build_object_event_table(blocks["visbtn"], context=context),
            )
            vis_items = decode_event_table(_build_object_event_table(blocks["visbtn"], context=context))
            self.assertEqual([(item.get("command"), item.get("args")) for item in vis_items if item["kind"] == "command"], [("vis", "label0,0")])
            self.assertIn(
                len(b"\x09\x09\x04label0,0").to_bytes(4, "little") + b"\x09\x09\x04label0,0",
                _build_object_event_table(blocks["tswbtn"], context=context),
            )
            tsw_items = decode_event_table(_build_object_event_table(blocks["tswbtn"], context=context))
            self.assertEqual([(item.get("command"), item.get("args")) for item in tsw_items if item["kind"] == "command"], [("tsw", "label0,0")])
            number_slot_start = sum(
                _user_slot_count(block) for block in target_page.blocks[: target_page.blocks.index(blocks["numval"])]
            )
            local_ref = (number_slot_start + 27).to_bytes(4, "little")
            inc_event_table = _build_object_event_table(blocks["incbtn"], context=context)
            self.assertIn(b"\x07\x00\x00\x00\x01" + local_ref + b"++", inc_event_table)
            inc_items = decode_event_table(inc_event_table)
            self.assertEqual(
                [(item.get("kind"), item.get("operator"), item.get("slot")) for item in inc_items if item["kind"] == "property_event"],
                [("property_event", "++", int.from_bytes(local_ref, "little"))],
            )

    @unittest.skipUnless(GB2312_FONT_ZI.exists(), "local verified GB2312 .zi font fixture is not available")
    def test_scene_full_page_rebuild_prepares_single_family_vis_promotion_offline(self) -> None:
        scene = load_scene(NUMBER_DEMO_VIS_PROMOTION_SCENE)

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(
                scene,
                SEED_HMI,
                temp_dir,
                baseline_tft=BASELINE_TFT,
                font_zi=GB2312_FONT_ZI,
            )

            self.assertEqual(manifest["tft_patch"]["mode"], "experimental_clean_page_tft_rebuild")
            self.assertEqual(manifest["tft_patch"]["removed_seed_objects"], ["t0", "b0", "p0"])
            self.assertEqual(
                [item["name"] for item in manifest["tft_patch"]["objects"]],
                ["page0", "title", "hidebtn", "showbtn", "label0"],
            )
            self.assertEqual(
                [item["id"] for item in manifest["tft_patch"]["objects"]],
                [0, 1, 2, 3, 4],
            )
            self.assertEqual(
                [item["type"] for item in manifest["tft_patch"]["objects"]],
                ["y", "t", "b", "b", "t"],
            )
            self.assertEqual(manifest["tft_font_patch"]["font_info"]["font_name"], "UiCNEN32GBFull")
            self.assertEqual(manifest["tft_font_patch"]["font_info"]["encoding_name"], "gb2312")
            self.assertTrue(manifest["tft_checksum"]["valid"])

            target_page = load_page_file(manifest["target_pa"])
            target_names = [block.objname for block in target_page.blocks]
            self.assertEqual(target_names, ["page0", "title", "hidebtn", "showbtn", "label0"])
            self.assertFalse({"t0", "b0", "p0"} & set(target_names))
            self.assertEqual(len({object_name_hash(name) for name in target_names}), len(target_names))

            blocks = {block.objname: block for block in target_page.blocks}
            self.assertEqual(_field_int(blocks["label0"], "id"), 4)
            self.assertIn("vis label0,0", blocks["hidebtn"].event_tokens)
            self.assertIn("printh 23 02 56 30", blocks["hidebtn"].event_tokens)
            self.assertIn("vis label0,1", blocks["showbtn"].event_tokens)
            self.assertIn("printh 23 02 56 31", blocks["showbtn"].event_tokens)

            context = _build_event_compile_context(target_page.blocks)
            event_layout = _build_event_layout(target_page.blocks, 0, image_button_layout=False)
            for object_name in ("hidebtn", "showbtn"):
                callback_offset = event_layout.callbacks[target_page.blocks.index(blocks[object_name])]["codesdown-"]
                self.assertNotEqual(callback_offset, 0xFFFFFFFF)
                self.assertGreaterEqual(callback_offset, 0)

            hide_event_table = _build_object_event_table(blocks["hidebtn"], context=context)
            show_event_table = _build_object_event_table(blocks["showbtn"], context=context)
            self.assertIn(
                len(b"\x09\x05\x04label0,0").to_bytes(4, "little") + b"\x09\x05\x04label0,0",
                hide_event_table,
            )
            self.assertIn(
                len(b"\x09\x05\x04label0,1").to_bytes(4, "little") + b"\x09\x05\x04label0,1",
                show_event_table,
            )
            hide_marker = b"\x09\x0f\x0823 02 56 30"
            show_marker = b"\x09\x0f\x0823 02 56 31"
            self.assertIn(len(hide_marker).to_bytes(4, "little") + hide_marker, hide_event_table)
            self.assertIn(len(show_marker).to_bytes(4, "little") + show_marker, show_event_table)

            hide_items = decode_event_table(hide_event_table)
            show_items = decode_event_table(show_event_table)
            self.assertEqual(
                [(item.get("command"), item.get("args")) for item in hide_items if item.get("command") == "vis"],
                [("vis", "label0,0")],
            )
            self.assertIn(("printh", "23 02 56 30"), [(item.get("command"), item.get("args")) for item in hide_items])
            self.assertEqual(
                [(item.get("command"), item.get("args")) for item in show_items if item.get("command") == "vis"],
                [("vis", "label0,1")],
            )
            self.assertIn(("printh", "23 02 56 31"), [(item.get("command"), item.get("args")) for item in show_items])

    @unittest.skipUnless(GB2312_FONT_ZI.exists(), "local verified GB2312 .zi font fixture is not available")
    def test_scene_full_page_rebuild_prepares_single_family_tsw_promotion_offline(self) -> None:
        scene = load_scene(NUMBER_DEMO_TSW_PROMOTION_SCENE)

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(
                scene,
                SEED_HMI,
                temp_dir,
                baseline_tft=BASELINE_TFT,
                font_zi=GB2312_FONT_ZI,
            )

            self.assertEqual(manifest["tft_patch"]["mode"], "experimental_clean_page_tft_rebuild")
            self.assertEqual(manifest["tft_patch"]["removed_seed_objects"], ["t0", "b0", "p0"])
            self.assertEqual(
                [item["name"] for item in manifest["tft_patch"]["objects"]],
                ["page0", "title", "disablebtn", "enablebtn", "targetbtn"],
            )
            self.assertEqual(
                [item["id"] for item in manifest["tft_patch"]["objects"]],
                [0, 1, 2, 3, 4],
            )
            self.assertEqual(
                [item["type"] for item in manifest["tft_patch"]["objects"]],
                ["y", "t", "b", "b", "b"],
            )
            self.assertEqual(manifest["tft_font_patch"]["font_info"]["font_name"], "UiCNEN32GBFull")
            self.assertEqual(manifest["tft_font_patch"]["font_info"]["encoding_name"], "gb2312")
            self.assertTrue(manifest["tft_checksum"]["valid"])

            target_page = load_page_file(manifest["target_pa"])
            target_names = [block.objname for block in target_page.blocks]
            self.assertEqual(target_names, ["page0", "title", "disablebtn", "enablebtn", "targetbtn"])
            self.assertFalse({"t0", "b0", "p0"} & set(target_names))
            self.assertEqual(len({object_name_hash(name) for name in target_names}), len(target_names))

            blocks = {block.objname: block for block in target_page.blocks}
            self.assertEqual(_field_int(blocks["targetbtn"], "id"), 4)
            self.assertIn("tsw targetbtn,0", blocks["disablebtn"].event_tokens)
            self.assertIn("printh 23 02 54 30", blocks["disablebtn"].event_tokens)
            self.assertIn("tsw targetbtn,1", blocks["enablebtn"].event_tokens)
            self.assertIn("printh 23 02 54 31", blocks["enablebtn"].event_tokens)
            self.assertIn("printh 23 02 54 47", blocks["targetbtn"].event_tokens)

            context = _build_event_compile_context(target_page.blocks)
            event_layout = _build_event_layout(target_page.blocks, 0, image_button_layout=False)
            for object_name in ("disablebtn", "enablebtn", "targetbtn"):
                callback_offset = event_layout.callbacks[target_page.blocks.index(blocks[object_name])]["codesdown-"]
                self.assertNotEqual(callback_offset, 0xFFFFFFFF)
                self.assertGreaterEqual(callback_offset, 0)

            disable_event_table = _build_object_event_table(blocks["disablebtn"], context=context)
            enable_event_table = _build_object_event_table(blocks["enablebtn"], context=context)
            target_event_table = _build_object_event_table(blocks["targetbtn"], context=context)
            self.assertIn(
                len(b"\x09\x09\x04targetbtn,0").to_bytes(4, "little") + b"\x09\x09\x04targetbtn,0",
                disable_event_table,
            )
            self.assertIn(
                len(b"\x09\x09\x04targetbtn,1").to_bytes(4, "little") + b"\x09\x09\x04targetbtn,1",
                enable_event_table,
            )
            disable_marker = b"\x09\x0f\x0823 02 54 30"
            enable_marker = b"\x09\x0f\x0823 02 54 31"
            target_marker = b"\x09\x0f\x0823 02 54 47"
            self.assertIn(len(disable_marker).to_bytes(4, "little") + disable_marker, disable_event_table)
            self.assertIn(len(enable_marker).to_bytes(4, "little") + enable_marker, enable_event_table)
            self.assertIn(len(target_marker).to_bytes(4, "little") + target_marker, target_event_table)

            disable_items = decode_event_table(disable_event_table)
            enable_items = decode_event_table(enable_event_table)
            target_items = decode_event_table(target_event_table)
            self.assertEqual(
                [(item.get("command"), item.get("args")) for item in disable_items if item.get("command") == "tsw"],
                [("tsw", "targetbtn,0")],
            )
            self.assertIn(("printh", "23 02 54 30"), [(item.get("command"), item.get("args")) for item in disable_items])
            self.assertEqual(
                [(item.get("command"), item.get("args")) for item in enable_items if item.get("command") == "tsw"],
                [("tsw", "targetbtn,1")],
            )
            self.assertIn(("printh", "23 02 54 31"), [(item.get("command"), item.get("args")) for item in enable_items])
            self.assertEqual(
                [(item.get("command"), item.get("args")) for item in target_items if item.get("command") == "printh"],
                [("printh", "23 02 54 47")],
            )

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

    @unittest.skipUnless(FONT_ZI.exists(), "local generated .zi font fixture is not available")
    def test_scene_build_can_patch_hmi_and_tft_font(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "font-patched-scene", "default_page": "page0"},
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
                                "text": "FONT TEST 123",
                                "style": {"font_id": 0},
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
                font_zi=FONT_ZI,
            )

            output_hmi = Path(manifest["output_hmi"])
            self.assertEqual(_hmi_entry_data(output_hmi, "0.zi"), FONT_ZI.read_bytes())
            self.assertEqual(manifest["hmi_font_patch"]["entry_name"], "0.zi")
            self.assertEqual(manifest["hmi_font_patch"]["zi_size"], FONT_ZI.stat().st_size)
            self.assertEqual(manifest["tft_font_patch"]["font_info"]["font_name"], "SimSun32scene")
            self.assertTrue(manifest["tft_checksum"]["valid"])

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


def _matrix_type_code(type_code: str) -> str:
    if len(type_code) == 1 and ord(type_code) < 0x20:
        return f"0x{ord(type_code):02X}"
    return type_code


def _matrix_evidence_widget_types(evidence_path: Path) -> set[str]:
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    scene_paths: set[Path] = set()
    for key in ("scene", "artifact"):
        value = evidence.get(key)
        if isinstance(value, str) and value.endswith(".json"):
            scene_paths.add(Path(value))
    for slice_info in evidence.get("verified_slices", []):
        value = slice_info.get("scene")
        if isinstance(value, str):
            scene_paths.add(Path(value))
    for slice_info in evidence.get("single_media_smoke_slices", []):
        value = slice_info.get("scene")
        if isinstance(value, str):
            scene_paths.add(Path(value))

    widget_types = {
        rebuilt_object["widget"]
        for rebuilt_object in evidence.get("rebuilt_objects", [])
        if isinstance(rebuilt_object, dict) and "widget" in rebuilt_object
    }
    for scene_path in scene_paths:
        scene = load_scene(scene_path)
        widget_types.update(widget.type for page in scene.pages for widget in page.widgets)
    return widget_types


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


def _compiled_page_hash_ids(tft_path: Path, pa_path: Path) -> dict[str, int]:
    page = load_page_file(pa_path)
    hash_data = _compiled_page_hash_data(tft_path, page)
    ids_by_hash = {
        int.from_bytes(hash_data[offset : offset + 4], "little"): int.from_bytes(hash_data[offset + 4 : offset + 6], "little")
        for offset in range(0, len(hash_data), 6)
    }
    return {
        block.objname: ids_by_hash[object_name_hash(block.objname)]
        for block in page.blocks
        if block.objname
    }


def _compiled_page_primary_value(
    tft_path: Path,
    pa_path: Path | object,
    object_name: str,
    type_code: str,
    offset: int,
    width: int,
) -> int:
    page = load_page_file(pa_path) if isinstance(pa_path, Path) else pa_path
    primary = _compiled_page_primary_data(tft_path, page)
    block_index = next(index for index, block in enumerate(page.blocks) if block.objname == object_name)
    record_start = int.from_bytes(primary[block_index * 4 : block_index * 4 + 4], "little") - 0x10
    if record_start < 0:
        raise AssertionError(f"invalid primary record offset for {object_name!r}")
    if offset + width > TYPE_RECORD_LENGTHS[type_code]:
        raise AssertionError(f"primary value read exceeds known record length for {object_name!r}")
    return int.from_bytes(primary[record_start + offset : record_start + offset + width], "little")


def _compiled_page_user_record_word1(tft_path: Path, page, object_name: str, *, slot_index: int) -> int:
    raw = tft_path.read_bytes()
    header2 = inspect_tft(tft_path)["parsed"]["Header2"]
    object_start = _header2_int(header2, "unknown_objects_address")
    user_start = object_start + _header2_int(header2, "usercode_address")
    slot_base = 0
    for block in page.blocks:
        if block.objname == object_name:
            record_start = user_start + (slot_base + slot_index) * 24
            return int.from_bytes(raw[record_start + 4 : record_start + 8], "little")
        slot_base += TYPE_USER_SLOT_COUNTS[block.type_code]
    raise AssertionError(f"user record for {object_name!r} was not found")


def _compiled_page_primary_data(tft_path: Path, page) -> bytes:
    raw = tft_path.read_bytes()
    object_start = _tft_object_start(tft_path)
    tail = raw[object_start:]
    hash_data = _expected_page_hash_data(page)
    marker = len(hash_data).to_bytes(4, "little") + hash_data
    hash_offset = tail.find(marker)
    if hash_offset < 0:
        raise AssertionError(f"compiled hash block for {page.page_name!r} was not found")
    primary_offset = hash_offset + len(marker)
    primary_size = int.from_bytes(tail[primary_offset : primary_offset + 4], "little")
    start = primary_offset + 4
    return tail[start : start + primary_size]


def _compiled_page_hash_data(tft_path: Path, page) -> bytes:
    raw = tft_path.read_bytes()
    object_start = _tft_object_start(tft_path)
    tail = raw[object_start:]
    hash_data = _expected_page_hash_data(page)
    marker = len(hash_data).to_bytes(4, "little") + hash_data
    hash_offset = tail.find(marker)
    if hash_offset < 0:
        raise AssertionError(f"compiled hash block for {page.page_name!r} was not found")
    return tail[hash_offset + 4 : hash_offset + 4 + len(hash_data)]


def _expected_page_hash_data(page) -> bytes:
    entries = []
    for block in page.blocks:
        if not block.objname:
            raise AssertionError("page block without objname cannot be hashed")
        entries.append((object_name_hash(block.objname), _field_int(block, "id")))
    entries.sort(key=lambda item: item[0])
    return b"".join(value.to_bytes(4, "little") + object_id.to_bytes(2, "little") for value, object_id in entries)


def _tft_object_start(tft_path: Path) -> int:
    header2 = inspect_tft(tft_path)["parsed"]["Header2"]
    return _header2_int(header2, "unknown_objects_address")


def _compiled_page1_mirror_headers(tft_path: Path, page) -> list[bytes]:
    raw = tft_path.read_bytes()
    header2 = inspect_tft(tft_path)["parsed"]["Header2"]
    object_start = _header2_int(header2, "unknown_objects_address")
    mirror_start = _header2_int(header2, "pictures_address") - object_start
    tail = raw[object_start:]
    record_len = 0x38 + 41 * 2
    records_start = mirror_start + 0x20
    return [
        tail[records_start + index * record_len : records_start + index * record_len + 4]
        for index, _block in enumerate(page.blocks)
    ]


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
