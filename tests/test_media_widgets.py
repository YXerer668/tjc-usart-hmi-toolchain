from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from usarthmi.object_hash import object_name_hash
from usarthmi.editor import EditorError, build_scene
from usarthmi.page_format import load_page_file
from usarthmi.preview import render_hmi_preview, render_scene_preview
from usarthmi.scene import load_scene, validate_scene
from usarthmi.tft_checksum import inspect_tft_checksum
from usarthmi.tft_media import GMOV_HEADER_SIZE, pack_gmov_resources, pack_gmov_resources_into_tft
from usarthmi.tft_patch import (
    EVENT_FIELD_USER_SLOTS,
    TYPE_RECORD_LENGTHS,
    TYPE_USER_SLOT_COUNTS,
    _find_hash_block,
    _load_tail_seed,
    _prefix_descriptor_sequence,
    _record_header_flag,
    patch_rebuild_page_tft,
)
from usarthmi.tft_toolchain import inspect_tft


CASE_ROOT = Path(r"C:\Users\SinYu\Desktop\case_for_codex")
SEED_HMI = Path(r"D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI")


class MediaWidgetTests(unittest.TestCase):
    def test_single_audio_play_expectation_toggles_and_restores_en(self) -> None:
        expect_path = Path(__file__).resolve().parents[1] / "examples" / "media_single_audio_sd_smoke" / "play.expect.json"
        data = json.loads(expect_path.read_text(encoding="utf-8"))

        self.assertEqual(data["expectations"]["wav0.en"], 0)
        steps = data["steps"]
        self.assertEqual([step["label"] for step in steps], ["start wav0", "verify wav0 started", "stop wav0", "verify wav0 stopped"])
        self.assertEqual(steps[0]["command"], "wav0.en=1")
        self.assertEqual(steps[1]["command"], "get wav0.en")
        self.assertEqual(steps[1]["expected_kind"], "number")
        self.assertEqual(steps[1]["expected_value"], 1)
        self.assertEqual(steps[2]["command"], "wav0.en=0")
        self.assertEqual(steps[3]["command"], "get wav0.en")
        self.assertEqual(steps[3]["expected_kind"], "number")
        self.assertEqual(steps[3]["expected_value"], 0)

    def test_media_widget_aliases_are_supported(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "media-aliases", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "widgets": [
                            {"id": "gm0", "type": "gmov", "x": 0, "y": 0, "w": 100, "h": 60},
                            {"id": "v0", "type": "video", "x": 120, "y": 0, "w": 100, "h": 60},
                            {"id": "wav0", "type": "wav"},
                        ],
                    }
                ],
            }
        )

        widget_types = [widget.type for widget in scene.pages[0].widgets]
        self.assertEqual(widget_types, ["animation", "video", "audio"])

    def test_cli_can_append_media_widgets_to_scene(self) -> None:
        scene_doc = {
            "project": {"name": "media-cli", "default_page": "page0"},
            "canvas": {"width": 800, "height": 480},
            "assets": {},
            "pages": [{"id": "page0", "widgets": []}],
        }
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            scene_path = Path(temp_dir) / "scene.json"
            scene_path.write_text(json.dumps(scene_doc, indent=2), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "usarthmi",
                    "--json",
                    "hmi",
                    "add-video",
                    "--scene",
                    str(scene_path),
                    "--id",
                    "v0",
                    "--x",
                    "12",
                    "--y",
                    "34",
                    "--w",
                    "200",
                    "--h",
                    "120",
                    "--path",
                    "sd0/video/demo.video",
                    "--enabled",
                    "--loop",
                    "1",
                    "--fps",
                    "25",
                ],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "usarthmi",
                    "--json",
                    "hmi",
                    "add-audio",
                    "--scene",
                    str(scene_path),
                    "--id",
                    "wav0",
                    "--path",
                    "sd0/music/demo.wav",
                    "--disabled",
                ],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "usarthmi",
                    "--json",
                    "hmi",
                    "add-widget",
                    "--scene",
                    str(scene_path),
                    "--id",
                    "exp0",
                    "--type",
                    "expic",
                    "--x",
                    "300",
                    "--y",
                    "40",
                    "--w",
                    "160",
                    "--h",
                    "90",
                    "--resource",
                    "path=sd0/1.jpg",
                    "--style",
                    "path_m=24",
                ],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
            )

            scene = load_scene(scene_path)
            widgets = {widget.id: widget for widget in scene.pages[0].widgets}
            self.assertEqual(widgets["v0"].type, "video")
            self.assertEqual((widgets["v0"].x, widgets["v0"].y, widgets["v0"].w, widgets["v0"].h), (12, 34, 200, 120))
            self.assertEqual(widgets["v0"].resources["path"], "sd0/video/demo.video")
            self.assertEqual(widgets["v0"].style["en"], 1)
            self.assertEqual(widgets["v0"].style["loop"], 1)
            self.assertEqual(widgets["v0"].style["fps"], 25)
            self.assertEqual(widgets["wav0"].type, "audio")
            self.assertEqual(widgets["wav0"].resources["path"], "sd0/music/demo.wav")
            self.assertEqual(widgets["wav0"].style["en"], 0)
            self.assertEqual(widgets["exp0"].type, "external-picture")
            self.assertEqual(widgets["exp0"].resources["path"], "sd0/1.jpg")
            self.assertEqual(widgets["exp0"].style["path_m"], 24)

    @unittest.skipUnless(
        SEED_HMI.exists()
        and all((CASE_ROOT / case / "official_wiki" / "source_raw.HMI").exists() for case in ("case_47_gmov", "case_48_video", "case_49_audio")),
        "local media widget fixtures are not available",
    )
    def test_media_demo_builds_hmi_without_tft(self) -> None:
        scene = load_scene(Path(__file__).resolve().parents[1] / "examples" / "media_widgets_demo" / "scene.json")
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(scene, SEED_HMI, temp_dir)

            self.assertTrue(Path(manifest["output_hmi"]).exists())
            self.assertIsNone(manifest["output_tft"])
            target_page = load_page_file(Path(manifest["target_pa"]))
            generated = {block.objname: block for block in target_page.blocks}
            self.assertEqual(generated["gm0"].type_code, "\x02")
            self.assertEqual(generated["v0"].type_code, "\x03")
            self.assertEqual(generated["wav0"].type_code, "\x04")
            self.assertEqual(generated["gm0"].get_field("path").value.decode("ascii"), "sd0/anim/official_0.gmov")
            self.assertEqual(generated["v0"].get_field("path").value.decode("ascii"), "sd0/video/official_0.video")
            self.assertEqual(generated["wav0"].get_field("path").value.decode("ascii"), "sd0/music/official_0.wav")

            preview_path = Path(temp_dir) / "hmi_preview.png"
            render_hmi_preview(manifest["output_hmi"], preview_path, show_labels=False)
            image = Image.open(preview_path).convert("RGB")
            bottom_badge = image.crop((20, 410, 400, 470))
            data = bottom_badge.tobytes()
            dark_pixels = sum(
                1
                for index in range(0, len(data), 3)
                if data[index] < 80 and data[index + 1] < 100 and data[index + 2] < 120
            )
            self.assertGreater(dark_pixels, 100)

    def test_media_demo_preview_renders_png(self) -> None:
        scene = load_scene(Path(__file__).resolve().parents[1] / "examples" / "media_widgets_demo" / "scene.json")
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "media_preview.png"
            render_scene_preview(scene, target)
            self.assertTrue(target.exists())
            self.assertGreater(target.stat().st_size, 1000)

    def test_implicit_audio_preview_badge_is_visible(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "audio-preview", "default_page": "page0"},
                "canvas": {"width": 800, "height": 480, "background_color": 65535},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "widgets": [{"id": "wav0", "type": "audio", "resources": {"path": "sd0/music/demo.wav"}}],
                    }
                ],
            }
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "audio_preview.png"
            render_scene_preview(scene, target)
            image = Image.open(target).convert("RGB")
            bottom_badge = image.crop((20, 410, 400, 470))
            data = bottom_badge.tobytes()
            dark_pixels = sum(
                1
                for index in range(0, len(data), 3)
                if data[index] < 80 and data[index + 1] < 100 and data[index + 2] < 120
            )
            self.assertGreater(dark_pixels, 100)

    @unittest.skipUnless(SEED_HMI.exists(), "seed HMI is not available")
    def test_media_demo_rejects_tft_build_with_clear_error(self) -> None:
        scene_path = Path(__file__).resolve().parents[1] / "examples" / "media_widgets_demo" / "scene.json"
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        if not baseline_tft.exists():
            self.skipTest("baseline TFT is not available")
        for force_drop_seed in (False, True):
            with self.subTest(force_drop_seed=force_drop_seed), tempfile.TemporaryDirectory() as temp_dir:
                scene = load_scene(scene_path)
                if force_drop_seed:
                    scene.project.pop("clean_seed_objects", None)
                    scene.project["drop_seed_objects"] = True
                with self.assertRaisesRegex(EditorError, "media widgets path supports only one media fixture per page"):
                    build_scene(scene, SEED_HMI, temp_dir, baseline_tft=baseline_tft)

    @unittest.skipUnless(
        SEED_HMI.exists() and (CASE_ROOT / "case_00_baseline" / "lcd_test.tft").exists(),
        "seed HMI or baseline TFT is not available",
    )
    def test_single_gmov_scene_build_emits_tft(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "single-gmov-live", "default_page": "page0", "clean_seed_objects": True},
                "canvas": {"width": 800, "height": 480, "background_color": 2153},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "widgets": [
                            {
                                "id": "gm0",
                                "type": "animation",
                                "x": 80,
                                "y": 110,
                                "w": 640,
                                "h": 260,
                                "style": {"en": 0, "loop": 1, "dis": 100},
                            }
                        ],
                    }
                ],
            }
        )
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(scene, SEED_HMI, temp_dir, baseline_tft=baseline_tft)

            self.assertIsNotNone(manifest["output_tft"])
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertEqual(
                [item["name"] for item in manifest["tft_patch"]["added_objects"] if item["type"] == "\x02"],
                ["gm0"],
            )

    @unittest.skipUnless(
        SEED_HMI.exists()
        and (CASE_ROOT / "case_00_baseline" / "lcd_test.tft").exists()
        and all(
            (CASE_ROOT / case / "official_compile" / "source_raw.run").exists()
            for case in ("case_48_video", "case_49_audio")
        ),
        "seed, baseline TFT, or official video/audio fixtures are not available",
    )
    def test_single_video_and_audio_scene_builds_emit_clean_tfts(self) -> None:
        cases = [
            (
                "single-video-sd",
                {
                    "id": "v0",
                    "type": "video",
                    "x": 80,
                    "y": 90,
                    "w": 320,
                    "h": 180,
                    "resources": {"path": "sd0/video/official_0.video"},
                    "style": {"en": 0, "loop": 0, "fps": 1, "dis": 100},
                },
                "v0",
                "\x03",
                "sd0/video/official_0.video",
            ),
            (
                "single-audio-sd",
                {
                    "id": "wav0",
                    "type": "audio",
                    "resources": {"path": "sd0/music/official_0.wav"},
                    "style": {"en": 0, "loop": 0, "fps": 1, "dis": 100},
                },
                "wav0",
                "\x04",
                "sd0/music/official_0.wav",
            ),
        ]
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        for name, widget, object_name, type_code, path in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp_dir:
                scene = validate_scene(
                    {
                        "project": {"name": name, "default_page": "page0", "drop_seed_objects": True},
                        "canvas": {"width": 800, "height": 480, "background_color": 2153},
                        "assets": {},
                        "pages": [{"id": "page0", "widgets": [widget]}],
                    }
                )
                manifest = build_scene(scene, SEED_HMI, temp_dir, baseline_tft=baseline_tft)

                self.assertIsNotNone(manifest["output_tft"])
                self.assertTrue(manifest["tft_checksum"]["valid"])
                self.assertEqual(manifest["tft_patch"]["mode"], "experimental_clean_page_tft_rebuild")
                self.assertEqual(manifest["tft_patch"]["object_count"], 2)

                page, primary_records, _user_records = _compiled_records(
                    Path(manifest["output_tft"]),
                    Path(manifest["target_pa"]),
                )
                self.assertEqual([block.objname for block in page.blocks], ["page0", object_name])
                block = page.blocks[1]
                record, _value_base = primary_records[object_name]
                self.assertEqual(block.type_code, type_code)
                self.assertEqual(block.get_field("path").value.decode("ascii"), path)
                self.assertEqual(record[:4], bytes([ord(type_code), 1, 0, _record_header_flag(type_code)]))
                self.assertEqual(record[0x3A], 0)
                self.assertEqual(record[0x3B], 0)
                self.assertEqual(record[0x3C], 1)
                self.assertEqual(int.from_bytes(record[0x3E:0x40], "little"), 100)

    @unittest.skipUnless(
        SEED_HMI.exists() and (CASE_ROOT / "case_00_baseline" / "lcd_test.tft").exists(),
        "seed HMI or baseline TFT is not available",
    )
    def test_single_sd_media_smoke_examples_build_tfts(self) -> None:
        examples = [
            ("media_single_gmov_smoke", "gm0", "\x02", None),
            ("media_single_video_sd_smoke", "v0", "\x03", "sd0/video/official_0.video"),
            ("media_single_audio_sd_smoke", "wav0", "\x04", "sd0/music/official_0.wav"),
        ]
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        for example_name, object_name, type_code, expected_path in examples:
            with self.subTest(example=example_name), tempfile.TemporaryDirectory() as temp_dir:
                scene = load_scene(Path(__file__).resolve().parents[1] / "examples" / example_name / "scene.json")
                manifest = build_scene(scene, SEED_HMI, temp_dir, baseline_tft=baseline_tft)

                self.assertIsNotNone(manifest["output_tft"])
                self.assertTrue(manifest["tft_checksum"]["valid"])
                self.assertEqual(manifest["tft_patch"]["mode"], "experimental_clean_page_tft_rebuild")
                page = load_page_file(Path(manifest["target_pa"]))
                generated = {block.objname: block for block in page.blocks}
                self.assertEqual(generated[object_name].type_code, type_code)
                if expected_path is not None:
                    self.assertEqual(generated[object_name].get_field("path").value.decode("ascii"), expected_path)

    @unittest.skipUnless(
        all(
            (CASE_ROOT / case / "official_compile" / "source_raw.run").exists()
            and (CASE_ROOT / case / "official_wiki" / "extract" / "0.pa").exists()
            for case in ("case_47_gmov", "case_48_video", "case_49_audio")
        ),
        "official media TFT compile fixtures are not available",
    )
    def test_official_media_tft_tail_templates_are_recovered(self) -> None:
        cases = [
            ("case_47_gmov", "\x02", 0x68, 39, 0x37),
            ("case_48_video", "\x03", 0x68, 38, 0x37),
            ("case_49_audio", "\x04", 0x68, 20, 0x27),
        ]
        for case_name, type_code, record_length, slot_count, header_flag in cases:
            with self.subTest(case_name=case_name):
                run_path = CASE_ROOT / case_name / "official_compile" / "source_raw.run"
                page_path = CASE_ROOT / case_name / "official_wiki" / "extract" / "0.pa"
                page = load_page_file(page_path)
                seed = _load_tail_seed(run_path, page_path, page)
                self.assertEqual(TYPE_RECORD_LENGTHS[type_code], record_length)
                self.assertEqual(TYPE_USER_SLOT_COUNTS[type_code], slot_count)
                self.assertEqual(len(seed.primary_templates[type_code]), record_length)
                self.assertEqual(seed.primary_templates[type_code][3], header_flag)

        self.assertEqual(EVENT_FIELD_USER_SLOTS["\x02"]["vid"], 20)
        self.assertEqual(EVENT_FIELD_USER_SLOTS["\x03"]["en"], 21)
        self.assertEqual(EVENT_FIELD_USER_SLOTS["\x04"]["en"], 9)

    @unittest.skipUnless(
        SEED_HMI.exists()
        and (CASE_ROOT / "case_00_baseline" / "lcd_test.tft").exists()
        and all((CASE_ROOT / case / "official_compile" / "source_raw.run").exists() for case in ("case_47_gmov", "case_48_video", "case_49_audio")),
        "seed, baseline TFT, or official media fixtures are not available",
    )
    def test_lowlevel_media_tft_rebuild_emits_consistent_records(self) -> None:
        scene = load_scene(Path(__file__).resolve().parents[1] / "examples" / "media_widgets_demo" / "scene.json")
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(scene, SEED_HMI, temp_dir)
            output_tft = Path(temp_dir) / "media_lowlevel.tft"
            patch_rebuild_page_tft(
                baseline_tft,
                seed_pa=manifest["baseline_pa"],
                target_pa=manifest["target_pa"],
                out_tft=output_tft,
            )
            self.assertTrue(inspect_tft_checksum(output_tft)["valid"])

            page, primary_records, user_records = _compiled_records(output_tft, Path(manifest["target_pa"]))
            by_name = {block.objname: block for block in page.blocks}
            checks = {
                "gm0": {"type": "\x02", "en": 0, "loop": 1, "dis": 100},
                "v0": {"type": "\x03", "en": 0, "loop": 0, "fps": 1, "dis": 100},
                "wav0": {"type": "\x04", "en": 0, "loop": 0, "fps": 1, "dis": 100},
            }
            for name, expected in checks.items():
                block = by_name[name]
                record, value_base = primary_records[name]
                self.assertEqual(record[:4], bytes([ord(expected["type"]), _field_int(block, "id"), 0, _record_header_flag(expected["type"])]))
                self.assertEqual(record[0x3A], expected["en"])
                self.assertEqual(record[0x3B], expected["loop"])
                self.assertEqual(record[0x3C], expected.get("fps", 0))
                self.assertEqual(int.from_bytes(record[0x3E:0x40], "little"), expected["dis"])

                slot_base = _user_slot_base(page.blocks, name)
                for field_name, field_offset in _MEDIA_FIELD_OFFSETS[expected["type"]].items():
                    slot_index = EVENT_FIELD_USER_SLOTS[expected["type"]][field_name]
                    raw_record = user_records[(slot_base + slot_index) * 24 : (slot_base + slot_index + 1) * 24]
                    words = [int.from_bytes(raw_record[index : index + 4], "little") for index in range(0, 24, 4)]
                    self.assertEqual(words[0], value_base)
                    self.assertEqual(words[1], value_base + field_offset)

    @unittest.skipUnless(
        SEED_HMI.exists()
        and (CASE_ROOT / "case_00_baseline" / "lcd_test.tft").exists()
        and (CASE_ROOT / "case_48_video" / "official_compile" / "source_raw.run").exists(),
        "seed, baseline TFT, or official video fixture is not available",
    )
    def test_single_media_rebuild_uses_official_descriptor_sequence(self) -> None:
        scene = validate_scene(
            {
                "project": {"name": "single-video", "default_page": "page0", "clean_seed_objects": True},
                "canvas": {"width": 800, "height": 480, "background_color": 0},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "widgets": [
                            {
                                "id": "v0",
                                "type": "video",
                                "x": 20,
                                "y": 20,
                                "w": 320,
                                "h": 180,
                                "style": {"en": 0, "loop": 0, "fps": 1, "dis": 100},
                            }
                        ],
                    }
                ],
            }
        )
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(scene, SEED_HMI, temp_dir)
            output_tft = Path(temp_dir) / "single_video_lowlevel.tft"
            patch_rebuild_page_tft(
                baseline_tft,
                seed_pa=manifest["baseline_pa"],
                target_pa=manifest["target_pa"],
                out_tft=output_tft,
            )
            official_run = CASE_ROOT / "case_48_video" / "official_compile" / "source_raw.run"
            official_page = CASE_ROOT / "case_48_video" / "official_wiki" / "extract" / "0.pa"
            official_seed = _load_tail_seed(official_run, official_page, load_page_file(official_page))
            self.assertEqual(
                _compiled_prefix_descriptor_sequence(output_tft, Path(manifest["target_pa"])),
                _prefix_descriptor_sequence(official_seed.compiled_prefix),
            )

    @unittest.skipUnless(
        all(
            (CASE_ROOT / case / "official_compile" / "source_raw.run").exists()
            and (CASE_ROOT / case / "official_wiki" / "extract" / "0.pa").exists()
            for case in ("case_47_gmov", "case_48_video", "case_49_audio")
        ),
        "official media fixtures are not available",
    )
    def test_official_media_fixtures_rebuild_byte_for_byte(self) -> None:
        for case in ("case_47_gmov", "case_48_video", "case_49_audio"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp_dir:
                official_run = CASE_ROOT / case / "official_compile" / "source_raw.run"
                official_page = CASE_ROOT / case / "official_wiki" / "extract" / "0.pa"
                rebuilt = Path(temp_dir) / "rebuilt.run"

                patch_rebuild_page_tft(
                    official_run,
                    seed_pa=official_page,
                    target_pa=official_page,
                    out_tft=rebuilt,
                )

                self.assertEqual(rebuilt.read_bytes(), official_run.read_bytes())

    @unittest.skipUnless(
        (CASE_ROOT / "case_47_gmov" / "official_verified_media" / "source_raw_543_verified.tft").exists()
        and all((CASE_ROOT / "case_47_gmov" / "official_wiki" / "extract" / f"{index}.gmov").exists() for index in range(4)),
        "official verified GMOV TFT oracle is not available",
    )
    def test_gmov_resource_pack_matches_official_verified_tft(self) -> None:
        case_dir = CASE_ROOT / "case_47_gmov"
        gmov_paths = [case_dir / "official_wiki" / "extract" / f"{index}.gmov" for index in range(4)]
        result, packed = pack_gmov_resources(gmov_paths)

        official_tft = case_dir / "official_verified_media" / "source_raw_543_verified.tft"
        official_raw = official_tft.read_bytes()
        header2 = inspect_tft(official_tft)["parsed"]["Header2"]
        gmov_start = int(header2["audios_address"], 16)
        gmov_end = int(header2["fonts_address"], 16)

        self.assertEqual(result.header_table_size, len(gmov_paths) * GMOV_HEADER_SIZE)
        self.assertEqual([resource.payload_offset_in_block for resource in result.resources], [0x130, 0x3270B, 0x5308A, 0x63A3C])
        self.assertEqual(result.total_size, gmov_end - gmov_start)
        self.assertEqual(packed, official_raw[gmov_start:gmov_end])
        for index, path in enumerate(gmov_paths):
            raw_header = path.read_bytes()[:GMOV_HEADER_SIZE]
            packed_header = packed[index * GMOV_HEADER_SIZE : (index + 1) * GMOV_HEADER_SIZE]
            self.assertEqual(packed_header[:8], raw_header[:8])
            self.assertEqual(packed_header[12:], raw_header[12:])
            self.assertEqual(
                int.from_bytes(packed_header[8:12], "little"),
                result.resources[index].payload_offset_in_block,
            )

    @unittest.skipUnless(
        all((CASE_ROOT / "case_47_gmov" / "official_wiki" / "extract" / f"{index}.gmov").exists() for index in range(4)),
        "official GMOV resources are not available",
    )
    def test_gmov_resource_pack_sorts_explicit_resource_ids(self) -> None:
        case_dir = CASE_ROOT / "case_47_gmov" / "official_wiki" / "extract"
        ordered = [(index, case_dir / f"{index}.gmov") for index in range(4)]
        shuffled = [ordered[2], ordered[0], ordered[3], ordered[1]]

        ordered_result, ordered_pack = pack_gmov_resources(ordered)
        shuffled_result, shuffled_pack = pack_gmov_resources(shuffled)

        self.assertEqual(shuffled_pack, ordered_pack)
        self.assertEqual([resource.resource_id for resource in shuffled_result.resources], [0, 1, 2, 3])
        self.assertEqual(
            [resource.payload_offset_in_block for resource in shuffled_result.resources],
            [resource.payload_offset_in_block for resource in ordered_result.resources],
        )

    @unittest.skipUnless(
        (CASE_ROOT / "case_00_baseline" / "lcd_test.tft").exists()
        and (CASE_ROOT / "case_47_gmov" / "official_verified_media" / "source_raw_543_verified.tft").exists()
        and all((CASE_ROOT / "case_47_gmov" / "official_wiki" / "extract" / f"{index}.gmov").exists() for index in range(4)),
        "baseline TFT or official verified GMOV oracle is not available",
    )
    def test_gmov_resource_pack_can_be_inserted_into_baseline_tft(self) -> None:
        case_dir = CASE_ROOT / "case_47_gmov"
        gmov_paths = [case_dir / "official_wiki" / "extract" / f"{index}.gmov" for index in range(4)]
        _pack_result, expected_block = pack_gmov_resources(gmov_paths)
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"

        with tempfile.TemporaryDirectory() as temp_dir:
            out_tft = Path(temp_dir) / "with_gmov.tft"
            result = pack_gmov_resources_into_tft(baseline_tft, gmov_paths, out_tft=out_tft)

            self.assertTrue(inspect_tft_checksum(out_tft)["valid"])
            raw = out_tft.read_bytes()
            header1 = inspect_tft(out_tft)["parsed"]["Header1"]
            header2 = inspect_tft(out_tft)["parsed"]["Header2"]
            gmov_start = int(header2["audios_address"], 16)
            gmov_end = int(header2["fonts_address"], 16)
            self.assertEqual(result.resource_count, 4)
            self.assertEqual(result.gmov_resource_size, len(expected_block))
            self.assertEqual(raw[gmov_start:gmov_end], expected_block)
            self.assertEqual(int(header2["unknown_objects_address"], 16), result.new_object_start)
            self.assertEqual(int(header1["ressource_files_size"]), result.new_resource_size)
            self.assertEqual(int(header2["unknown_res1"], 16), 4)

    @unittest.skipUnless(
        SEED_HMI.exists()
        and (CASE_ROOT / "case_00_baseline" / "lcd_test.tft").exists()
        and all((CASE_ROOT / "case_47_gmov" / "official_wiki" / "extract" / f"{index}.gmov").exists() for index in range(4)),
        "seed, baseline TFT, or official GMOV resources are not available",
    )
    def test_scene_build_packs_internal_gmov_resources(self) -> None:
        gmov_paths = [
            str(CASE_ROOT / "case_47_gmov" / "official_wiki" / "extract" / f"{index}.gmov")
            for index in range(4)
        ]
        scene = validate_scene(
            {
                "project": {"name": "internal-gmov", "default_page": "page0", "clean_seed_objects": True},
                "canvas": {"width": 800, "height": 480, "background_color": 2153},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "widgets": [
                            {
                                "id": "gm0",
                                "type": "animation",
                                "x": 80,
                                "y": 110,
                                "w": 640,
                                "h": 260,
                                "resources": {"sources": gmov_paths},
                                "style": {"en": 0, "loop": 1, "dis": 100},
                            }
                        ],
                    }
                ],
            }
        )
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(scene, SEED_HMI, temp_dir, baseline_tft=baseline_tft)

            self.assertIsNotNone(manifest["output_tft"])
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertEqual(manifest["tft_gmov_pack"]["resource_count"], 4)
            page, primary_records, _user_records = _compiled_records(Path(manifest["output_tft"]), Path(manifest["target_pa"]))
            gm0 = next(block for block in page.blocks if block.objname == "gm0")
            record, _value_base = primary_records["gm0"]
            self.assertEqual(_field_int(gm0, "vid"), 0)
            self.assertEqual(int.from_bytes(record[0x38:0x3A], "little"), 0)

    @unittest.skipUnless(
        SEED_HMI.exists()
        and (CASE_ROOT / "case_00_baseline" / "lcd_test.tft").exists()
        and all((CASE_ROOT / "case_47_gmov" / "official_wiki" / "extract" / f"{index}.gmov").exists() for index in range(4)),
        "seed, baseline TFT, or official GMOV resources are not available",
    )
    def test_scene_build_can_drop_seed_objects_for_minimal_gmov_page(self) -> None:
        gmov_paths = [
            str(CASE_ROOT / "case_47_gmov" / "official_wiki" / "extract" / f"{index}.gmov")
            for index in range(4)
        ]
        scene = validate_scene(
            {
                "project": {
                    "name": "minimal-internal-gmov",
                    "default_page": "page0",
                    "drop_seed_objects": True,
                },
                "canvas": {"width": 800, "height": 480, "background_color": 2153},
                "assets": {},
                "pages": [
                    {
                        "id": "page0",
                        "widgets": [
                            {
                                "id": "gm0",
                                "type": "animation",
                                "x": 301,
                                "y": 115,
                                "w": 162,
                                "h": 102,
                                "resources": {"sources": gmov_paths},
                                "style": {"en": 1, "loop": 1, "dis": 50},
                            }
                        ],
                    }
                ],
            }
        )
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(scene, SEED_HMI, temp_dir, baseline_tft=baseline_tft)

            self.assertIsNotNone(manifest["output_tft"])
            self.assertTrue(manifest["tft_checksum"]["valid"])
            page = load_page_file(Path(manifest["target_pa"]))
            self.assertEqual([block.objname for block in page.blocks], ["page0", "gm0"])
            self.assertEqual([block.type_code for block in page.blocks], ["y", "\x02"])
            self.assertEqual(_field_int(page.blocks[1], "id"), 1)
            self.assertEqual(manifest["tft_patch"]["mode"], "experimental_clean_page_tft_rebuild")

_MEDIA_FIELD_OFFSETS = {
    "\x02": {"vid": 0x38, "en": 0x3A, "loop": 0x3B, "dis": 0x3E},
    "\x03": {"vid": 0x38, "en": 0x3A, "loop": 0x3B, "fps": 0x3C, "dis": 0x3E},
    "\x04": {"vid": 0x38, "en": 0x3A, "loop": 0x3B, "fps": 0x3C, "dis": 0x3E},
}


def _compiled_records(tft_path: Path, page_path: Path):
    raw = tft_path.read_bytes()
    header2 = inspect_tft(tft_path)["parsed"]["Header2"]
    object_start = int(header2["unknown_objects_address"], 16)
    tail = raw[object_start:]
    page = load_page_file(page_path)
    expected_hashes = {
        _field_int(block, "id"): object_name_hash(block.objname or "")
        for block in page.blocks
        if block.objname
    }
    hash_offset, hash_data = _find_hash_block(tail, expected_hashes)
    primary_size_offset = hash_offset + 4 + len(hash_data)
    primary_size = int.from_bytes(tail[primary_size_offset : primary_size_offset + 4], "little")
    primary_start = primary_size_offset + 4
    record_start = primary_start + len(page.blocks) * 4
    value_offsets = [
        int.from_bytes(tail[primary_start + index * 4 : primary_start + index * 4 + 4], "little")
        for index in range(len(page.blocks))
    ]
    cursor = record_start
    primary_records = {}
    for block, value_base in zip(page.blocks, value_offsets, strict=False):
        record_len = TYPE_RECORD_LENGTHS[block.type_code]
        primary_records[block.objname] = (tail[cursor : cursor + record_len], value_base)
        cursor += record_len
    assert cursor <= primary_start + primary_size

    user_start = int(header2["usercode_address"], 16)
    total_slots = sum(TYPE_USER_SLOT_COUNTS[block.type_code] for block in page.blocks)
    return page, primary_records, tail[user_start : user_start + total_slots * 24]


def _compiled_prefix_descriptor_sequence(tft_path: Path, page_path: Path) -> list[bytes]:
    raw = tft_path.read_bytes()
    header2 = inspect_tft(tft_path)["parsed"]["Header2"]
    object_start = int(header2["unknown_objects_address"], 16)
    tail = raw[object_start:]
    page = load_page_file(page_path)
    expected_hashes = {
        _field_int(block, "id"): object_name_hash(block.objname or "")
        for block in page.blocks
        if block.objname
    }
    hash_offset, _hash_data = _find_hash_block(tail, expected_hashes)
    return _prefix_descriptor_sequence(tail[:hash_offset])


def _user_slot_base(blocks, target_name: str) -> int:
    slot_base = 0
    for block in blocks:
        if block.objname == target_name:
            return slot_base
        slot_base += TYPE_USER_SLOT_COUNTS[block.type_code]
    raise AssertionError(f"Object not found: {target_name}")


def _field_int(block, name: str) -> int:
    field = block.get_field(name)
    if field is None:
        raise AssertionError(f"Missing field {name!r} in {block.objname!r}")
    value = field.value
    if isinstance(value, bytes):
        return int.from_bytes(value, "little")
    return int(value)


if __name__ == "__main__":
    unittest.main()
