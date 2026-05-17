from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools.live_tft_smoke import _load_expectations
from usarthmi.editor import build_scene
from usarthmi.page_format import load_page_file
from usarthmi.scene import load_scene


ROOT = Path(__file__).resolve().parents[1]
CROP_DEMO = ROOT / "examples" / "crop_image_demo"
SCENE_JSON = CROP_DEMO / "scene.json"
EXPECT_JSON = CROP_DEMO / "smoke.expect.json"
EVIDENCE_JSON = CROP_DEMO / "hardware_verified_2026-05-17.json"
HISTORICAL_SMOKE = ROOT / "reverse_usarthmi" / "minimal_control_live" / "case_30_crop_image" / "smoke_result.json"
SEED_HMI = Path(r"D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI")
BASELINE_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft")


class CropImageDemoTests(unittest.TestCase):
    def test_scene_is_focused_crop_image_page(self) -> None:
        scene = load_scene(SCENE_JSON)

        self.assertEqual(scene.project["name"], "crop-image-demo")
        self.assertTrue(scene.project["drop_seed_objects"])
        self.assertEqual(len(scene.pages), 1)
        self.assertEqual(len(scene.pages[0].widgets), 1)

        widget = scene.pages[0].widgets[0]
        self.assertEqual(widget.id, "q0")
        self.assertEqual(widget.type, "crop-image")
        self.assertEqual((widget.x, widget.y, widget.w, widget.h), (0, 0, 60, 60))
        self.assertEqual(widget.resources, {"picc": 65535})

    def test_smoke_expect_uses_only_historically_successful_crop_readbacks(self) -> None:
        historical = json.loads(HISTORICAL_SMOKE.read_text(encoding="utf-8"))
        expect_config = json.loads(EXPECT_JSON.read_text(encoding="utf-8"))
        expectations = _load_expectations(str(EXPECT_JSON), [])

        successful_readbacks = {
            item["command"][4:]: item["response"]["value"]
            for item in historical["serial_checks"]
            if item.get("ok")
            and item.get("command", "").startswith("get ")
            and item.get("response", {}).get("kind") == "number"
        }
        expected_targets = {item.target: item.expected for item in expectations}

        self.assertEqual(expect_config["page_id"], 0)
        self.assertEqual(expect_config["select_page"], 0)
        self.assertEqual(expected_targets, {"q0.x": 0, "q0.picc": 65535})
        self.assertEqual(expected_targets, {key: successful_readbacks[key] for key in expected_targets})
        self.assertTrue(all(item.expected_kind == "number" for item in expectations))
        self.assertTrue(all(item.attempts == 3 for item in expectations))

    @unittest.skipUnless(SEED_HMI.exists() and BASELINE_TFT.exists(), "local TJC seed HMI/TFT fixtures are not available")
    def test_crop_image_demo_builds_offline_with_clean_page_rebuild(self) -> None:
        scene = load_scene(SCENE_JSON)
        historical = json.loads(HISTORICAL_SMOKE.read_text(encoding="utf-8"))

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

            output_tft = Path(manifest["output_tft"])
            self.assertTrue(output_tft.exists())
            self.assertEqual(output_tft.stat().st_size, historical["rebuild"]["file_size"])
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertEqual(manifest["tft_patch"]["mode"], "experimental_clean_page_tft_rebuild")
            self.assertEqual(manifest["tft_patch"]["object_count"], 2)

            target_page = load_page_file(manifest["target_pa"])
            self.assertEqual([(block.objname, block.type_code) for block in target_page.blocks], [("page0", "y"), ("q0", "q")])
            q0 = target_page.blocks[1]
            self.assertEqual(int.from_bytes(q0.get_field("picc").value, "little"), 65535)

    def test_hardware_evidence_matches_smoke_expect(self) -> None:
        evidence = json.loads(EVIDENCE_JSON.read_text(encoding="utf-8"))
        expectations = _load_expectations(str(EXPECT_JSON), [])
        expected_targets = {item.target: item.expected for item in expectations}
        passed_targets = {item["target"]: item["actual"] for item in evidence["serial_readback_passed"]}

        self.assertTrue(evidence["summary"]["ok"])
        self.assertEqual(evidence["expect_json"], EXPECT_JSON.relative_to(ROOT).as_posix())
        self.assertEqual(passed_targets, expected_targets)
        self.assertEqual(evidence["upload"]["checksum_hex"], "0xE921CA14")
        self.assertTrue(evidence["summary"]["camera_ok"])
        self.assertIn("pixel-level assertion", evidence["not_claimed"][0])


if __name__ == "__main__":
    unittest.main()
