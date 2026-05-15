from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from usarthmi.event_bytecode import decode_event_table
from usarthmi.hmi_inspect import inspect_hmi
from usarthmi.tft_checksum import inspect_tft_checksum
from usarthmi.tft_patch import (
    _augment_seed_templates,
    _build_event_layout,
    _build_event_compile_context,
    _build_primary_block,
    _build_object_event_table,
    _build_page_event_table,
    _load_tail_seed,
    _user_slot_count,
    patch_added_object_tft,
    patch_basic_tft,
    patch_multi_page_tft,
    patch_rebuild_page_tft,
)
from usarthmi.page_format import load_page_file, parse_page_data
from tools.live_case_smoke import _load_hmi_page0, _make_clean_page


CASE_ROOT = Path(r"C:\Users\SinYu\Desktop\case_for_codex")
EXTRACT_ROOT = (
    Path(__file__).resolve().parents[1]
    / "reverse_usarthmi"
    / "case_compare"
)


@unittest.skipUnless(CASE_ROOT.exists() and EXTRACT_ROOT.exists(), "local TJC case fixtures are not available")
class TftPatchTests(unittest.TestCase):
    def test_basic_patch_reproduces_known_cases_exactly(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        for case_name in (
            "case_01_t0_text_hello",
            "case_02_t0_x_plus10",
            "case_03_b0_text_test",
        ):
            with self.subTest(case=case_name), tempfile.TemporaryDirectory() as temp_dir:
                out = Path(temp_dir) / f"{case_name}.tft"
                patch_basic_tft(
                    baseline_tft,
                    baseline_pa=baseline_pa,
                    target_pa=EXTRACT_ROOT / case_name / "extract" / "0.pa",
                    out_tft=out,
                )
                generated = out.read_bytes()
                official = (CASE_ROOT / case_name / "lcd_test.tft").read_bytes()
                self.assertEqual(generated, official)

    def test_added_object_patch_reproduces_known_cases_exactly(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        for case_name in (
            "case_04_add_text",
            "case_05_add_button",
            "case_06_add_picture",
            "case_16_number_basic",
        ):
            with self.subTest(case=case_name), tempfile.TemporaryDirectory() as temp_dir:
                out = Path(temp_dir) / f"{case_name}.tft"
                patch_added_object_tft(
                    baseline_tft,
                    baseline_pa=baseline_pa,
                    target_pa=EXTRACT_ROOT / case_name / "extract" / "0.pa",
                    out_tft=out,
                )
                generated = out.read_bytes()
                official = (CASE_ROOT / case_name / "lcd_test.tft").read_bytes()
                self.assertEqual(generated, official)

    def test_added_object_patch_accepts_new_object_names(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        target_pa = EXTRACT_ROOT / "case_04_add_text" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            renamed_pa = temp / "renamed.pa"
            out = temp / "renamed.tft"
            page = load_page_file(target_pa)
            page.blocks[-1].set_string("objname", "note1")
            renamed_pa.write_bytes(page.serialize())

            patch_added_object_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pa=renamed_pa,
                out_tft=out,
            )

            info = inspect_tft_checksum(out)
            self.assertTrue(info["valid"])

    def test_added_object_patch_accepts_multiple_new_objects(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            target_pa = temp / "multi.pa"
            out = temp / "multi.tft"
            page = _build_multi_added_page()
            target_pa.write_bytes(page.serialize())

            result = patch_added_object_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pa=target_pa,
                out_tft=out,
            ).to_dict()

            self.assertEqual(result["added_count"], 3)
            self.assertEqual([item["name"] for item in result["added_objects"]], ["note1", "btn1", "pic1"])
            info = inspect_tft_checksum(out)
            self.assertTrue(info["valid"])

    def test_added_object_patch_accepts_gbk_text(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            target_pa = temp / "gbk_text.pa"
            out = temp / "gbk_text.tft"
            page = load_page_file(baseline_pa)
            text = load_page_file(EXTRACT_ROOT / "case_04_add_text" / "extract" / "0.pa").blocks[-1].clone()
            _configure_added_block(text, object_id=4, name="cn1", x=64, y=64, w=220, h=48)
            text.set_string("txt", "中文OK", encoding="gbk")
            text.set_int("txt_maxl", len("中文OK".encode("gbk")), width=2)
            page.blocks.append(text)
            target_pa.write_bytes(page.serialize())

            result = patch_added_object_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pa=target_pa,
                out_tft=out,
            ).to_dict()

            self.assertEqual(result["added_count"], 1)
            info = inspect_tft_checksum(out)
            self.assertTrue(info["valid"])

    def test_event_table_builder_matches_empty_seed_events(self) -> None:
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        page = load_page_file(baseline_pa)

        self.assertEqual(
            _build_page_event_table(page.blocks[0]),
            bytes.fromhex(
                "00 00 00 00 04 00 00 00 64 6f 77 6e 00 00 00 00 "
                "02 00 00 00 75 70 00 00 00 00 06 00 00 00 75 6e "
                "6c 6f 61 64 00 00 00 00"
            ),
        )
        for block in page.blocks[1:]:
            with self.subTest(block=block.objname):
                self.assertEqual(
                    _build_object_event_table(block),
                    bytes.fromhex(
                        "00 00 00 00 04 00 00 00 64 6f 77 6e 00 00 00 00 "
                        "02 00 00 00 75 70 00 00 00 00"
                    ),
                )

    def test_event_table_builder_compiles_printh_up_event(self) -> None:
        source_pa = EXTRACT_ROOT / "case_05_add_button" / "extract" / "0.pa"
        page = load_page_file(source_pa)
        button = page.blocks[-1].clone()
        button.set_event("codesup-", ["printh 23 02 54 45"])

        event_data = _build_object_event_table(button)

        self.assertIn(b"\x04\x00\x00\x00down", event_data)
        self.assertIn(b"\x02\x00\x00\x00up", event_data)
        self.assertIn(b"\x0e\x00\x00\x00\x09\x0f\x0823 02 54 45", event_data)

    def test_page_event_table_builder_separates_load_and_loadend(self) -> None:
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        page = load_page_file(baseline_pa)
        page_block = page.blocks[0].clone()
        page_block.set_event("codesload-", ["printh 23 02 50 01"])
        page_block.set_event("codesloadend-", ["vis evtbtn,0"])

        event_data = _build_page_event_table(page_block)

        self.assertIn(b"\x0e\x00\x00\x00\x09\x0f\x0823 02 50 01", event_data)
        self.assertIn(b"\x03\x00\x00\x00\x09\x30\x08", event_data)
        self.assertIn(b"\x0b\x00\x00\x00\x09\x05\x04evtbtn,0", event_data)
        self.assertIn(b"\x04\x00\x00\x00down", event_data)

    def test_event_table_builder_accepts_rawhex_probe(self) -> None:
        source_pa = EXTRACT_ROOT / "case_05_add_button" / "extract" / "0.pa"
        page = load_page_file(source_pa)
        button = page.blocks[-1].clone()
        button.set_event("codesup-", ["rawhex 09 0a 08 32 33 20 30 32"])

        event_data = _build_object_event_table(button)

        self.assertIn(b"\x08\x00\x00\x00\x09\x0a\x0823 02", event_data)

    def test_event_table_builder_compiles_numeric_field_events(self) -> None:
        source_pa = EXTRACT_ROOT / "case_19_timer" / "extract" / "0.pa"
        page = load_page_file(source_pa)
        button = next(block for block in page.blocks if block.objname == "b0")
        timer = next(block for block in page.blocks if block.objname == "tm0")
        button.set_event("codesdown-", ["tm0.en=1"])
        timer.set_event("codestimer-", ["tm0.en=0"])

        event_layout = _build_event_layout(page.blocks, 0x149, image_button_layout=False)

        timer_slot_start = 0
        for block in page.blocks:
            if block.objname == "tm0":
                break
            timer_slot_start += _user_slot_count(block)
        tm0_en_ref = (timer_slot_start + 8).to_bytes(4, "little")
        self.assertIn(b"\x07\x00\x00\x00\x01" + tm0_en_ref + b"=1", event_layout.data)
        self.assertIn(b"\x07\x00\x00\x00\x01" + tm0_en_ref + b"=0", event_layout.data)
        self.assertEqual(event_layout.callbacks[2]["codesdown-"], event_layout.offsets[2] + 12)
        self.assertEqual(event_layout.callbacks[4]["codestimer-"], event_layout.offsets[4] + 13)

    def test_event_table_builder_compiles_number_increment_event(self) -> None:
        source_pa = EXTRACT_ROOT / "case_16_number_basic" / "extract" / "0.pa"
        page = load_page_file(source_pa)
        button = next(block for block in page.blocks if block.objname == "b0")
        number = next(block for block in page.blocks if block.objname == "numval")
        button.set_event("codesdown-", ["numval.val++"])

        event_layout = _build_event_layout(page.blocks, 0x149, image_button_layout=False)

        number_slot_start = 0
        for block in page.blocks:
            if block is number:
                break
            number_slot_start += _user_slot_count(block)
        numval_ref = (number_slot_start + 27).to_bytes(4, "little")
        self.assertIn(b"\x07\x00\x00\x00\x01" + numval_ref + b"++", event_layout.data)
        self.assertEqual(event_layout.callbacks[2]["codesdown-"], event_layout.offsets[2] + 12)

    def test_event_table_builder_keeps_multi_line_numeric_event_order(self) -> None:
        source_pa = EXTRACT_ROOT / "case_16_number_basic" / "extract" / "0.pa"
        page = load_page_file(source_pa)
        button = next(block for block in page.blocks if block.objname == "b0")
        button.set_event(
            "codesdown-",
            [
                "numval.val=10",
                "numval.val++",
                "numval.val++",
                "numval.val--",
            ],
        )

        event_data = _build_object_event_table(button, context=_build_event_compile_context(page.blocks))
        items = [
            (item.get("operator"), item.get("value"))
            for item in decode_event_table(event_data)
            if item["kind"] == "property_event"
        ]

        self.assertEqual(items, [("=", "10"), ("++", None), ("++", None), ("--", None)])

    def test_event_table_builder_compiles_vis_event(self) -> None:
        source_pa = EXTRACT_ROOT / "case_05_add_button" / "extract" / "0.pa"
        page = load_page_file(source_pa)
        button = page.blocks[-1].clone()
        button.set_event("codesdown-", ["vis label0,0"])

        event_data = _build_object_event_table(button)

        self.assertIn(b"\x0b\x00\x00\x00\x09\x05\x04label0,0", event_data)

    def test_event_table_builder_compiles_ref_event(self) -> None:
        source_pa = EXTRACT_ROOT / "case_05_add_button" / "extract" / "0.pa"
        page = load_page_file(source_pa)
        button = page.blocks[-1].clone()
        button.set_event("codesdown-", ["ref label0"])

        event_data = _build_object_event_table(button)

        self.assertIn(b"\x09\x00\x00\x00\x09\x03\x04label0", event_data)

    def test_checksum_matches_official_cases(self) -> None:
        for case_name in (
            "case_00_baseline",
            "case_01_t0_text_hello",
            "case_02_t0_x_plus10",
            "case_03_b0_text_test",
            "case_04_add_text",
            "case_05_add_button",
            "case_06_add_picture",
        ):
            with self.subTest(case=case_name):
                info = inspect_tft_checksum(CASE_ROOT / case_name / "lcd_test.tft")
                self.assertTrue(info["valid"])

    @unittest.skipUnless(
        all((CASE_ROOT / name / "lcd_test.HMI").exists() for name in (
            "case_17_slider",
            "case_18_gauge",
            "case_20_progress",
            "case_21_qrcode",
        )),
        "local extra-control fixtures are not available",
    )
    def test_added_object_patch_accepts_single_extra_visual_controls(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        for case_name in (
            "case_17_slider",
            "case_18_gauge",
            "case_20_progress",
            "case_21_qrcode",
        ):
            with self.subTest(case=case_name), tempfile.TemporaryDirectory() as temp_dir:
                temp = Path(temp_dir)
                target_pa = temp / "extra_visual.pa"
                out = temp / "extra_visual.tft"
                page = load_page_file(baseline_pa)
                extra = _load_case_last_block(case_name)
                _configure_added_block(extra, object_id=4, name=extra.objname or "extra1", x=80, y=120, w=200, h=80)
                page.blocks.append(extra)
                target_pa.write_bytes(page.serialize())

                result = patch_added_object_tft(
                    baseline_tft,
                    baseline_pa=baseline_pa,
                    target_pa=target_pa,
                    out_tft=out,
                ).to_dict()

                self.assertEqual(result["added_count"], 1)
                info = inspect_tft_checksum(out)
                self.assertTrue(info["valid"])

    @unittest.skipUnless(
        all((CASE_ROOT / name / "lcd_test.tft").exists() and (CASE_ROOT / name / "lcd_test.HMI").exists() for name in (
            "case_17_slider",
            "case_18_gauge",
            "case_20_progress",
            "case_21_qrcode",
        )),
        "local extra-control fixtures are not available",
    )
    def test_added_object_patch_reproduces_extra_visual_controls_exactly(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        for case_name in (
            "case_17_slider",
            "case_18_gauge",
            "case_20_progress",
            "case_21_qrcode",
        ):
            with self.subTest(case=case_name), tempfile.TemporaryDirectory() as temp_dir:
                temp = Path(temp_dir)
                target_pa = temp / "0.pa"
                out = temp / f"{case_name}.tft"
                _write_case_page0(case_name, target_pa)

                patch_added_object_tft(
                    baseline_tft,
                    baseline_pa=baseline_pa,
                    target_pa=target_pa,
                    out_tft=out,
                )

                self.assertEqual(out.read_bytes(), (CASE_ROOT / case_name / "lcd_test.tft").read_bytes())

    def test_added_object_patch_accepts_mixed_extra_visual_layouts(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            target_pa = temp / "mixed_extra_visual.pa"
            out = temp / "mixed_extra_visual.tft"
            page = load_page_file(baseline_pa)
            slider = _load_case_last_block("case_17_slider")
            progress = _load_case_last_block("case_20_progress")
            _configure_added_block(slider, object_id=4, name="sld1", x=56, y=118, w=330, h=40)
            _configure_added_block(progress, object_id=5, name="bar1", x=56, y=206, w=330, h=30)
            page.blocks.extend([slider, progress])
            target_pa.write_bytes(page.serialize())

            result = patch_added_object_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pa=target_pa,
                out_tft=out,
            ).to_dict()

            self.assertEqual(result["added_count"], 2)
            self.assertEqual(result["section_offsets"]["prefix_delta"]["value"], 40)
            info = inspect_tft_checksum(out)
            self.assertTrue(info["valid"])

    @unittest.skipUnless(
        all((CASE_ROOT / name / "lcd_test.HMI").exists() for name in (
            "case_22_scrolling_text",
            "case_23_dual_state_button",
            "case_24_state_button",
            "case_25_hotspot_touch_area",
            "case_26_variable_numeric_string",
            "case_27_waveform_basic",
            "case_28_checkbox",
            "case_29_radio",
            "case_30_crop_image",
            "case_45_touchcap_current_gui",
            "case_46_expicture_current_gui",
        )),
        "local new-control fixtures are not available",
    )
    def test_added_object_patch_accepts_known_extra_controls(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        for case_name in (
            "case_22_scrolling_text",
            "case_23_dual_state_button",
            "case_24_state_button",
            "case_25_hotspot_touch_area",
            "case_26_variable_numeric_string",
            "case_27_waveform_basic",
            "case_28_checkbox",
            "case_29_radio",
            "case_30_crop_image",
            "case_45_touchcap_current_gui",
            "case_46_expicture_current_gui",
        ):
            with self.subTest(case=case_name), tempfile.TemporaryDirectory() as temp_dir:
                out = Path(temp_dir) / "new_control.tft"

                result = patch_added_object_tft(
                    baseline_tft,
                    baseline_pa=baseline_pa,
                    target_pa=EXTRACT_ROOT / case_name / "extract" / "0.pa",
                    out_tft=out,
                ).to_dict()

                self.assertGreaterEqual(result["added_count"], 1)
                info = inspect_tft_checksum(out)
                self.assertTrue(info["valid"])

    @unittest.skipUnless(
        (CASE_ROOT / "case_45_touchcap_current_gui" / "lcd_test.tft").exists()
        and (CASE_ROOT / "case_45_touchcap_current_gui" / "official_compile_baseline" / "lcd_test.run").exists()
        and (CASE_ROOT / "case_45_touchcap_current_gui" / "extract_baseline_seed" / "0.pa").exists()
        and (EXTRACT_ROOT / "case_45_touchcap_current_gui" / "extract" / "0.pa").exists(),
        "local touch-capture fixture is not available",
    )
    def test_added_object_patch_reproduces_touch_capture_case_exactly_from_matching_seed(self) -> None:
        case_dir = CASE_ROOT / "case_45_touchcap_current_gui"
        baseline_tft = case_dir / "official_compile_baseline" / "lcd_test.run"
        baseline_pa = case_dir / "extract_baseline_seed" / "0.pa"
        target_pa = EXTRACT_ROOT / "case_45_touchcap_current_gui" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "case_45_touchcap_current_gui.tft"

            patch_added_object_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pa=target_pa,
                out_tft=out,
            )

            self.assertEqual(out.read_bytes(), (case_dir / "lcd_test.tft").read_bytes())

    @unittest.skipUnless(
        (CASE_ROOT / "case_46_expicture_current_gui" / "lcd_test.tft").exists()
        and (CASE_ROOT / "case_46_expicture_current_gui" / "official_compile_baseline" / "lcd_test.run").exists()
        and (CASE_ROOT / "case_46_expicture_current_gui" / "extract_baseline_seed" / "0.pa").exists()
        and (EXTRACT_ROOT / "case_46_expicture_current_gui" / "extract" / "0.pa").exists(),
        "local external-picture fixture is not available",
    )
    def test_added_object_patch_reproduces_external_picture_case_exactly_from_matching_seed(self) -> None:
        case_dir = CASE_ROOT / "case_46_expicture_current_gui"
        baseline_tft = case_dir / "official_compile_baseline" / "lcd_test.run"
        baseline_pa = case_dir / "extract_baseline_seed" / "0.pa"
        target_pa = EXTRACT_ROOT / "case_46_expicture_current_gui" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "case_46_expicture_current_gui.tft"

            patch_added_object_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pa=target_pa,
                out_tft=out,
            )

            self.assertEqual(out.read_bytes(), (case_dir / "lcd_test.tft").read_bytes())

    @unittest.skipUnless(
        (CASE_ROOT / "case_23_dual_state_button" / "lcd_test.tft").exists()
        and (EXTRACT_ROOT / "case_23_dual_state_button" / "extract" / "0.pa").exists(),
        "local dual-state button fixture is not available",
    )
    def test_added_object_patch_reproduces_dual_state_button_case_exactly(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "case_23_dual_state_button.tft"

            patch_added_object_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pa=EXTRACT_ROOT / "case_23_dual_state_button" / "extract" / "0.pa",
                out_tft=out,
            )

            self.assertEqual(out.read_bytes(), (CASE_ROOT / "case_23_dual_state_button" / "lcd_test.tft").read_bytes())

    @unittest.skipUnless(
        (CASE_ROOT / "case_22_scrolling_text" / "lcd_test.tft").exists()
        and (EXTRACT_ROOT / "case_22_scrolling_text" / "extract" / "0.pa").exists(),
        "local scrolling text fixture is not available",
    )
    def test_added_object_patch_reproduces_scrolling_text_case_exactly(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "case_22_scrolling_text.tft"

            patch_added_object_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pa=EXTRACT_ROOT / "case_22_scrolling_text" / "extract" / "0.pa",
                out_tft=out,
            )

            self.assertEqual(out.read_bytes(), (CASE_ROOT / "case_22_scrolling_text" / "lcd_test.tft").read_bytes())

    @unittest.skipUnless(
        (CASE_ROOT / "case_24_state_button" / "lcd_test.tft").exists()
        and (EXTRACT_ROOT / "case_24_state_button" / "extract" / "0.pa").exists(),
        "local state-button fixture is not available",
    )
    def test_added_object_patch_reproduces_state_button_case_exactly(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "case_24_state_button.tft"

            patch_added_object_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pa=EXTRACT_ROOT / "case_24_state_button" / "extract" / "0.pa",
                out_tft=out,
            )

            self.assertEqual(out.read_bytes(), (CASE_ROOT / "case_24_state_button" / "lcd_test.tft").read_bytes())

    @unittest.skipUnless(
        (CASE_ROOT / "case_25_hotspot_touch_area" / "lcd_test.tft").exists()
        and (EXTRACT_ROOT / "case_25_hotspot_touch_area" / "extract" / "0.pa").exists(),
        "local hotspot fixture is not available",
    )
    def test_added_object_patch_reproduces_hotspot_case_exactly(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "case_25_hotspot_touch_area.tft"

            patch_added_object_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pa=EXTRACT_ROOT / "case_25_hotspot_touch_area" / "extract" / "0.pa",
                out_tft=out,
            )

            self.assertEqual(out.read_bytes(), (CASE_ROOT / "case_25_hotspot_touch_area" / "lcd_test.tft").read_bytes())

    @unittest.skipUnless(
        (CASE_ROOT / "case_26_variable_numeric_string" / "lcd_test.tft").exists()
        and (EXTRACT_ROOT / "case_26_variable_numeric_string" / "extract" / "0.pa").exists(),
        "local variable fixture is not available",
    )
    def test_added_object_patch_reproduces_variable_case_exactly(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "case_26_variable_numeric_string.tft"

            patch_added_object_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pa=EXTRACT_ROOT / "case_26_variable_numeric_string" / "extract" / "0.pa",
                out_tft=out,
            )

            self.assertEqual(out.read_bytes(), (CASE_ROOT / "case_26_variable_numeric_string" / "lcd_test.tft").read_bytes())

    @unittest.skipUnless(
        (CASE_ROOT / "case_27_waveform_basic" / "lcd_test.tft").exists()
        and (EXTRACT_ROOT / "case_27_waveform_basic" / "extract" / "0.pa").exists(),
        "local waveform fixture is not available",
    )
    def test_added_object_patch_reproduces_waveform_case_exactly(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "case_27_waveform_basic.tft"

            patch_added_object_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pa=EXTRACT_ROOT / "case_27_waveform_basic" / "extract" / "0.pa",
                out_tft=out,
            )

            self.assertEqual(out.read_bytes(), (CASE_ROOT / "case_27_waveform_basic" / "lcd_test.tft").read_bytes())

    @unittest.skipUnless(
        all(
            (CASE_ROOT / case_name / "lcd_test.tft").exists()
            and (EXTRACT_ROOT / case_name / "extract" / "0.pa").exists()
            for case_name in ("case_28_checkbox", "case_29_radio", "case_30_crop_image")
        ),
        "local checkbox/radio/crop fixtures are not available",
    )
    def test_added_object_patch_reproduces_case28_to_case30_exactly(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        for case_name in ("case_28_checkbox", "case_29_radio", "case_30_crop_image"):
            with self.subTest(case=case_name), tempfile.TemporaryDirectory() as temp_dir:
                out = Path(temp_dir) / f"{case_name}.tft"

                patch_added_object_tft(
                    baseline_tft,
                    baseline_pa=baseline_pa,
                    target_pa=EXTRACT_ROOT / case_name / "extract" / "0.pa",
                    out_tft=out,
                )

                self.assertEqual(out.read_bytes(), (CASE_ROOT / case_name / "lcd_test.tft").read_bytes())

    @unittest.skipUnless(
        (CASE_ROOT / "case_33_all_controls_mixed_stress" / "lcd_test.tft").exists()
        and (EXTRACT_ROOT / "case_33_all_controls_mixed_stress" / "extract" / "0.pa").exists(),
        "local all-controls mixed fixture is not available",
    )
    def test_added_object_patch_reproduces_all_controls_mixed_case_exactly(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "case_33_all_controls_mixed_stress.tft"

            patch_added_object_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pa=EXTRACT_ROOT / "case_33_all_controls_mixed_stress" / "extract" / "0.pa",
                out_tft=out,
            )

            self.assertEqual(out.read_bytes(), (CASE_ROOT / "case_33_all_controls_mixed_stress" / "lcd_test.tft").read_bytes())

    @unittest.skipUnless(
        (CASE_ROOT / "case_23_dual_state_button" / "lcd_test.tft").exists()
        and (EXTRACT_ROOT / "case_23_dual_state_button" / "extract" / "0.pa").exists(),
        "local dual-state button fixture is not available",
    )
    def test_rebuild_page_can_drop_seed_objects_for_clean_dual_state_button(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        seed_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            target_pa = temp / "clean_bt0.pa"
            out = temp / "clean_bt0.tft"

            page = load_page_file(seed_pa)
            page.blocks = [page.blocks[0].clone()]
            button = _load_case_last_block("case_23_dual_state_button")
            _configure_added_block(button, object_id=1, name="bt0", x=120, y=120, w=180, h=80)
            page.blocks.append(button)
            target_pa.write_bytes(page.serialize())

            result = patch_rebuild_page_tft(
                baseline_tft,
                seed_pa=seed_pa,
                target_pa=target_pa,
                out_tft=out,
            ).to_dict()

            self.assertEqual(result["object_count"], 2)
            self.assertEqual(result["removed_seed_objects"], ["t0", "b0", "p0"])
            self.assertEqual([item["name"] for item in result["objects"]], ["page0", "bt0"])
            self.assertTrue(inspect_tft_checksum(out)["valid"])
            rebuilt_seed = _load_tail_seed(out, target_pa, load_page_file(target_pa))
            self.assertEqual(set(rebuilt_seed.hash_by_name), {"page0", "bt0"})

    @unittest.skipUnless(
        (CASE_ROOT / "case_27_waveform_basic" / "lcd_test.HMI").exists(),
        "local waveform fixture is not available",
    )
    def test_live_clean_waveform_inserts_runtime_pads(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        seed_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            target_pa = temp / "clean_waveform_runtime_pad.pa"
            out = temp / "clean_waveform_runtime_pad.tft"

            seed_page = load_page_file(seed_pa)
            target_page = _load_hmi_page0(CASE_ROOT / "case_27_waveform_basic" / "lcd_test.HMI")
            clean_page, _, target_blocks, runtime_pads = _make_clean_page(seed_page, target_page)
            target_pa.write_bytes(clean_page.serialize())

            self.assertEqual([block.objname for block in runtime_pads], ["_wfpad1", "_wfpad2", "_wfpad3"])
            self.assertEqual([(block.objname, _field_int_for_test(block, "id")) for block in target_blocks], [("s0", 4), ("b1", 5)])
            self.assertEqual([block.objname for block in clean_page.blocks], ["page0", "_wfpad1", "_wfpad2", "_wfpad3", "s0", "b1"])

            result = patch_rebuild_page_tft(
                baseline_tft,
                seed_pa=seed_pa,
                target_pa=target_pa,
                out_tft=out,
            ).to_dict()

            self.assertEqual(result["object_count"], 6)
            self.assertTrue(inspect_tft_checksum(out)["valid"])

    @unittest.skipUnless(
        (CASE_ROOT / "case_19_timer" / "lcd_test.tft").exists()
        and (EXTRACT_ROOT / "case_19_timer" / "extract" / "0.pa").exists(),
        "local timer fixture is not available",
    )
    def test_added_object_patch_reproduces_timer_case_exactly(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "case_19_timer.tft"

            patch_added_object_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pa=EXTRACT_ROOT / "case_19_timer" / "extract" / "0.pa",
                out_tft=out,
            )

            self.assertEqual(out.read_bytes(), (CASE_ROOT / "case_19_timer" / "lcd_test.tft").read_bytes())

    @unittest.skipUnless(
        (CASE_ROOT / "case_32_timer_autorun_witness" / "lcd_test.tft").exists()
        and (EXTRACT_ROOT / "case_32_timer_autorun_witness" / "extract" / "0.pa").exists(),
        "local timer autorun fixture is not available",
    )
    def test_added_object_patch_reproduces_timer_autorun_case_exactly(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "case_32_timer_autorun_witness.tft"

            patch_added_object_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pa=EXTRACT_ROOT / "case_32_timer_autorun_witness" / "extract" / "0.pa",
                out_tft=out,
            )

            self.assertEqual(out.read_bytes(), (CASE_ROOT / "case_32_timer_autorun_witness" / "lcd_test.tft").read_bytes())

    @unittest.skipUnless(
        (CASE_ROOT / "case_31_multi_page_navigation" / "lcd_test.tft").exists()
        and (EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "0.pa").exists()
        and (EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "1.pa").exists(),
        "local multi-page fixture is not available",
    )
    def test_multi_page_patch_reproduces_case31_exactly(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "case_31_multi_page_navigation.tft"

            patch_multi_page_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pages=[
                    EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "0.pa",
                    EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "1.pa",
                ],
                out_tft=out,
            )

            self.assertEqual(out.read_bytes(), (CASE_ROOT / "case_31_multi_page_navigation" / "lcd_test.tft").read_bytes())

    @unittest.skipUnless(
        (CASE_ROOT / "case_31_multi_page_navigation" / "lcd_test.tft").exists()
        and (EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "0.pa").exists()
        and (EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "1.pa").exists()
        and (EXTRACT_ROOT / "case_04_add_text" / "extract" / "0.pa").exists()
        and (EXTRACT_ROOT / "case_05_add_button" / "extract" / "0.pa").exists(),
        "local multi-page text/button fixtures are not available",
    )
    def test_multi_page_patch_accepts_page1_text_button_experiment(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            page1_pa = temp / "page1_text_button.pa"
            out = temp / "page1_text_button.tft"
            page1 = load_page_file(EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "1.pa")
            title = load_page_file(EXTRACT_ROOT / "case_04_add_text" / "extract" / "0.pa").blocks[-1].clone()
            button = load_page_file(EXTRACT_ROOT / "case_05_add_button" / "extract" / "0.pa").blocks[-1].clone()
            _configure_added_block(title, object_id=1, name="p1title", x=72, y=64, w=320, h=58)
            title.set_string("txt", "PAGE1")
            title.set_int("txt_maxl", 16, width=2)
            _configure_added_block(button, object_id=2, name="p1btn", x=72, y=154, w=180, h=64)
            button.set_string("txt", "GO")
            button.set_int("txt_maxl", 16, width=2)
            page1.blocks.extend([title, button])
            page1_pa.write_bytes(page1.serialize())

            patch_result = patch_multi_page_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pages=[
                    EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "0.pa",
                    page1_pa,
                ],
                out_tft=out,
            )

            self.assertTrue(inspect_tft_checksum(out)["valid"])
            self.assertEqual(patch_result.page_count, 2)
            self.assertEqual(patch_result.object_count, 7)

    @unittest.skipUnless(
        (CASE_ROOT / "case_31_multi_page_navigation" / "lcd_test.tft").exists()
        and (EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "0.pa").exists()
        and (EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "1.pa").exists()
        and (EXTRACT_ROOT / "case_05_add_button" / "extract" / "0.pa").exists(),
        "local multi-page button-event fixtures are not available",
    )
    def test_multi_page_patch_allows_minimal_page1_button_event_only_when_opted_in(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            page1_pa = temp / "page1_button_event.pa"
            out = temp / "page1_button_event.tft"
            page1 = load_page_file(EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "1.pa")
            button = load_page_file(EXTRACT_ROOT / "case_05_add_button" / "extract" / "0.pa").blocks[-1].clone()
            _configure_added_block(button, object_id=1, name="back0", x=72, y=154, w=180, h=64)
            button.set_string("txt", "BACK")
            button.set_int("txt_maxl", 16, width=2)
            button.set_event("codesup-", ["page 0"])
            page1.blocks.append(button)
            page1_pa.write_bytes(page1.serialize())

            with self.assertRaisesRegex(Exception, "page1 control events"):
                patch_multi_page_tft(
                    baseline_tft,
                    baseline_pa=baseline_pa,
                    target_pages=[
                        EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "0.pa",
                        page1_pa,
                    ],
                    out_tft=out,
                )

            patch_result = patch_multi_page_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pages=[
                    EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "0.pa",
                    page1_pa,
                ],
                out_tft=out,
                allow_experimental_events=True,
            )

            self.assertTrue(inspect_tft_checksum(out)["valid"])
            self.assertTrue(patch_result.experimental_events)
            self.assertEqual(patch_result.object_count, 6)

    @unittest.skipUnless(
        (CASE_ROOT / "case_31_multi_page_navigation" / "lcd_test.tft").exists()
        and (EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "0.pa").exists()
        and (EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "1.pa").exists()
        and (EXTRACT_ROOT / "case_05_add_button" / "extract" / "0.pa").exists()
        and (EXTRACT_ROOT / "case_16_number_basic" / "extract" / "0.pa").exists(),
        "local multi-page numeric button-event fixtures are not available",
    )
    def test_multi_page_patch_allows_page1_button_numeric_event_when_opted_in(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            page1_pa = temp / "page1_button_numeric_event.pa"
            out = temp / "page1_button_numeric_event.tft"
            page0_blocks = load_page_file(EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "0.pa").blocks
            page1 = load_page_file(EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "1.pa")
            number = load_page_file(EXTRACT_ROOT / "case_16_number_basic" / "extract" / "0.pa").blocks[-1].clone()
            button = load_page_file(EXTRACT_ROOT / "case_05_add_button" / "extract" / "0.pa").blocks[-1].clone()
            _configure_added_block(number, object_id=1, name="numval", x=72, y=70, w=220, h=60)
            number.set_int("val", 3, width=4)
            _configure_added_block(button, object_id=2, name="inc0", x=72, y=154, w=180, h=64)
            button.set_string("txt", "INC")
            button.set_int("txt_maxl", 16, width=2)
            button.set_event("codesdown-", ["numval.val++"])
            page1.blocks.extend([number, button])
            page1_pa.write_bytes(page1.serialize())

            with self.assertRaisesRegex(Exception, "page1 control events"):
                patch_multi_page_tft(
                    baseline_tft,
                    baseline_pa=baseline_pa,
                    target_pages=[
                        EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "0.pa",
                        page1_pa,
                    ],
                    out_tft=out,
                )

            patch_result = patch_multi_page_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pages=[
                    EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "0.pa",
                    page1_pa,
                ],
                out_tft=out,
                allow_experimental_events=True,
            )

            self.assertTrue(inspect_tft_checksum(out)["valid"])
            self.assertTrue(patch_result.experimental_events)
            self.assertEqual(patch_result.object_count, 7)
            number_slot_start = sum(_user_slot_count(block) for block in page1.blocks[: page1.blocks.index(number)])
            local_ref = (number_slot_start + 27).to_bytes(4, "little")
            page0_global_ref = (
                sum(_user_slot_count(block) for block in page0_blocks) + number_slot_start + 27
            ).to_bytes(4, "little")
            compiled = _build_object_event_table(button, context=_build_event_compile_context(page1.blocks))
            self.assertIn(b"\x07\x00\x00\x00\x01" + local_ref + b"++", compiled)
            self.assertNotIn(b"\x07\x00\x00\x00\x01" + page0_global_ref + b"++", compiled)

    @unittest.skipUnless(
        (CASE_ROOT / "case_31_multi_page_navigation" / "lcd_test.tft").exists()
        and (EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "0.pa").exists()
        and (EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "1.pa").exists()
        and (EXTRACT_ROOT / "case_04_add_text" / "extract" / "0.pa").exists()
        and (EXTRACT_ROOT / "case_05_add_button" / "extract" / "0.pa").exists(),
        "local multi-page vis button-event fixtures are not available",
    )
    def test_multi_page_patch_allows_page1_button_vis_event_when_opted_in(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            page1_pa = temp / "page1_button_vis_event.pa"
            out = temp / "page1_button_vis_event.tft"
            page1 = load_page_file(EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "1.pa")
            label = load_page_file(EXTRACT_ROOT / "case_04_add_text" / "extract" / "0.pa").blocks[-1].clone()
            hide = load_page_file(EXTRACT_ROOT / "case_05_add_button" / "extract" / "0.pa").blocks[-1].clone()
            show = load_page_file(EXTRACT_ROOT / "case_05_add_button" / "extract" / "0.pa").blocks[-1].clone()
            _configure_added_block(label, object_id=1, name="label0", x=72, y=70, w=280, h=50)
            label.set_string("txt", "VISIBLE")
            label.set_int("txt_maxl", 16, width=2)
            _configure_added_block(hide, object_id=2, name="hide0", x=72, y=154, w=160, h=58)
            hide.set_string("txt", "HIDE")
            hide.set_int("txt_maxl", 16, width=2)
            hide.set_event("codesdown-", ["vis label0,0"])
            _configure_added_block(show, object_id=3, name="show0", x=250, y=154, w=160, h=58)
            show.set_string("txt", "SHOW")
            show.set_int("txt_maxl", 16, width=2)
            show.set_event("codesdown-", ["vis label0,1"])
            page1.blocks.extend([label, hide, show])
            page1_pa.write_bytes(page1.serialize())

            with self.assertRaisesRegex(Exception, "page1 control events"):
                patch_multi_page_tft(
                    baseline_tft,
                    baseline_pa=baseline_pa,
                    target_pages=[
                        EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "0.pa",
                        page1_pa,
                    ],
                    out_tft=out,
                )

            patch_result = patch_multi_page_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pages=[
                    EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "0.pa",
                    page1_pa,
                ],
                out_tft=out,
                allow_experimental_events=True,
            )

            self.assertTrue(inspect_tft_checksum(out)["valid"])
            self.assertTrue(patch_result.experimental_events)
            compiled_hide = _build_object_event_table(hide, context=_build_event_compile_context(page1.blocks))
            compiled_show = _build_object_event_table(show, context=_build_event_compile_context(page1.blocks))
            self.assertIn(b"\x0b\x00\x00\x00\x09\x05\x04label0,0", compiled_hide)
            self.assertIn(b"\x0b\x00\x00\x00\x09\x05\x04label0,1", compiled_show)

    @unittest.skipUnless(
        (CASE_ROOT / "case_31_multi_page_navigation" / "lcd_test.tft").exists()
        and (EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "0.pa").exists()
        and (EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "1.pa").exists()
        and (EXTRACT_ROOT / "case_05_add_button" / "extract" / "0.pa").exists(),
        "local multi-page button-event fixtures are not available",
    )
    def test_multi_page_patch_allows_page1_button_click_to_printh_probe_when_opted_in(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            page1_pa = temp / "page1_button_click_event.pa"
            out = temp / "page1_button_click_event.tft"
            page1 = load_page_file(EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "1.pa")
            fire = load_page_file(EXTRACT_ROOT / "case_05_add_button" / "extract" / "0.pa").blocks[-1].clone()
            sink = load_page_file(EXTRACT_ROOT / "case_05_add_button" / "extract" / "0.pa").blocks[-1].clone()
            _configure_added_block(fire, object_id=1, name="fire0", x=72, y=154, w=180, h=64)
            fire.set_string("txt", "FIRE")
            fire.set_int("txt_maxl", 16, width=2)
            fire.set_event("codesup-", ["click sink0,0"])
            _configure_added_block(sink, object_id=2, name="sink0", x=292, y=154, w=180, h=64)
            sink.set_string("txt", "SINK")
            sink.set_int("txt_maxl", 16, width=2)
            sink.set_event("codesup-", ["printh 23 02 43 4B"])
            page1.blocks.extend([fire, sink])
            page1_pa.write_bytes(page1.serialize())

            with self.assertRaisesRegex(Exception, "page1 control events"):
                patch_multi_page_tft(
                    baseline_tft,
                    baseline_pa=baseline_pa,
                    target_pages=[
                        EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "0.pa",
                        page1_pa,
                    ],
                    out_tft=out,
                )

            patch_result = patch_multi_page_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pages=[
                    EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "0.pa",
                    page1_pa,
                ],
                out_tft=out,
                allow_experimental_events=True,
            )

            self.assertTrue(inspect_tft_checksum(out)["valid"])
            self.assertTrue(patch_result.experimental_events)
            self.assertEqual(patch_result.object_count, 7)
            fire_compiled = _build_object_event_table(fire, context=_build_event_compile_context(page1.blocks))
            sink_compiled = _build_object_event_table(sink, context=_build_event_compile_context(page1.blocks))
            self.assertIn(b"\x09\x00\x08sink0,0", fire_compiled)
            self.assertIn(b"\x09\x0f\x0823 02 43 4B", sink_compiled)

    @unittest.skipUnless(
        (CASE_ROOT / "case_31_multi_page_navigation" / "lcd_test.tft").exists()
        and (EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "0.pa").exists()
        and (EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "1.pa").exists(),
        "local multi-page page-event fixtures are not available",
    )
    def test_multi_page_patch_allows_page1_load_printh_probe_when_opted_in(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            page1_pa = temp / "page1_load_event.pa"
            out = temp / "page1_load_event.tft"
            page1 = load_page_file(EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "1.pa")
            page1.blocks[0].set_event("codesload-", ["printh 23 02 50 4C"])
            page1_pa.write_bytes(page1.serialize())

            with self.assertRaisesRegex(Exception, "page1 page events"):
                patch_multi_page_tft(
                    baseline_tft,
                    baseline_pa=baseline_pa,
                    target_pages=[
                        EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "0.pa",
                        page1_pa,
                    ],
                    out_tft=out,
                )

            patch_result = patch_multi_page_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pages=[
                    EXTRACT_ROOT / "case_31_multi_page_navigation" / "extract" / "0.pa",
                    page1_pa,
                ],
                out_tft=out,
                allow_experimental_events=True,
            )

            self.assertTrue(inspect_tft_checksum(out)["valid"])
            self.assertTrue(patch_result.experimental_events)
            page_compiled = _build_page_event_table(page1.blocks[0])
            self.assertIn(b"\x09\x0f\x0823 02 50 4C", page_compiled)
            self.assertIn(b"\x09\x30\x08", page_compiled)

    def test_added_object_patch_keeps_qrcode_text_pointer_separate(self) -> None:
        baseline_tft = CASE_ROOT / "case_00_baseline" / "lcd_test.tft"
        baseline_pa = EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            target_pa = temp / "qr_text_pointer.pa"
            out = temp / "qr_text_pointer.tft"
            page = load_page_file(baseline_pa)
            title = _load_case_last_block("case_04_add_text")
            qr = _load_case_last_block("case_21_qrcode")
            _configure_added_block(title, object_id=4, name="title", x=40, y=24, w=260, h=48)
            title.set_string("txt", "TITLE TEXT")
            title.set_int("txt_maxl", 32, width=2)
            _configure_added_block(qr, object_id=5, name="qr1", x=360, y=80, w=150, h=150)
            qr.set_string("txt", "QR TEXT")
            qr.set_int("txt_maxl", 30, width=2)
            page.blocks.extend([title, qr])
            target_pa.write_bytes(page.serialize())

            patch_result = patch_added_object_tft(
                baseline_tft,
                baseline_pa=baseline_pa,
                target_pa=target_pa,
                out_tft=out,
            )

            generated_page = load_page_file(target_pa)
            seed = _load_tail_seed(out, target_pa, generated_page)
            base_seed = _load_tail_seed(baseline_tft, baseline_pa, load_page_file(baseline_pa))
            _augment_seed_templates(base_seed, {block.type_code for block in generated_page.blocks})
            _, _, text_pointer_by_id, _ = _build_primary_block(
                base_seed,
                generated_page.blocks,
                event_callbacks=[{} for _ in generated_page.blocks],
            )
            qr_index = next(index for index, block in enumerate(generated_page.blocks) if block.objname == "qr1")
            slot_start = sum(_user_slot_count(block) for block in generated_page.blocks[:qr_index])
            qr_text_slot = slot_start + 23
            tail = seed.raw[seed.object_start:]
            user_offset = patch_result.section_offsets["user"]
            record = tail[user_offset + qr_text_slot * 24 : user_offset + (qr_text_slot + 1) * 24]
            self.assertEqual(int.from_bytes(record[4:8], "little"), text_pointer_by_id[5])

def _build_multi_added_page():
    baseline = load_page_file(EXTRACT_ROOT / "case_00_baseline" / "extract" / "0.pa")
    text = load_page_file(EXTRACT_ROOT / "case_04_add_text" / "extract" / "0.pa").blocks[-1].clone()
    button = load_page_file(EXTRACT_ROOT / "case_05_add_button" / "extract" / "0.pa").blocks[-1].clone()
    picture = load_page_file(EXTRACT_ROOT / "case_06_add_picture" / "extract" / "0.pa").blocks[-1].clone()

    _configure_added_block(text, object_id=4, name="note1", x=355, y=321, w=100, h=31)
    text.set_string("txt", "note1")
    _configure_added_block(button, object_id=5, name="btn1", x=192, y=310, w=100, h=50)
    button.set_string("txt", "BTN1")
    _configure_added_block(picture, object_id=6, name="pic1", x=579, y=346, w=92, h=92)

    baseline.blocks = [*baseline.blocks, text, button, picture]
    return baseline


def _load_case_last_block(case_name: str):
    hmi_path = CASE_ROOT / case_name / "lcd_test.HMI"
    inspection = inspect_hmi(hmi_path)
    raw = hmi_path.read_bytes()
    entry = next(item for item in inspection.entries if item.name == "0.pa")
    return parse_page_data(raw[entry.data_offset : entry.data_offset + entry.length]).blocks[-1].clone()


def _write_case_page0(case_name: str, out_path: Path) -> None:
    hmi_path = CASE_ROOT / case_name / "lcd_test.HMI"
    inspection = inspect_hmi(hmi_path)
    raw = hmi_path.read_bytes()
    entry = next(item for item in inspection.entries if item.name == "0.pa")
    out_path.write_bytes(raw[entry.data_offset : entry.data_offset + entry.length])


def _configure_added_block(block, *, object_id: int, name: str, x: int, y: int, w: int, h: int) -> None:
    block.set_int("id", object_id, width=1)
    block.set_string("objname", name)
    block.set_int("x", x, width=2)
    block.set_int("y", y, width=2)
    block.set_int("w", w, width=2)
    block.set_int("h", h, width=2)
    block.set_int("endx", x + w - 1, width=2)
    block.set_int("endy", y + h - 1, width=2)


def _field_int_for_test(block, name: str) -> int | None:
    field = block.get_field(name)
    if field is None or not field.value:
        return None
    return int.from_bytes(field.value, "little")


if __name__ == "__main__":
    unittest.main()
