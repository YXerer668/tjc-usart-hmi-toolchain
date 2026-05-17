from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.live_tft_smoke import _load_runtime_steps
from usarthmi.editor import build_scene
from usarthmi.page_format import load_page_file
from usarthmi.scene import load_scene


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
SCENE_PATH = WORKSPACE_ROOT / "examples" / "waveform_demo" / "scene.json"
EXPECT_PATH = WORKSPACE_ROOT / "examples" / "waveform_demo" / "smoke.expect.json"
DEMO_DIR = WORKSPACE_ROOT / "examples" / "waveform_demo"
SEED_HMI = Path(r"D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI")
BASELINE_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft")


class WaveformDemoTests(unittest.TestCase):
    def test_smoke_expect_keeps_waveform_runtime_add_step_pending(self) -> None:
        expect = json.loads(EXPECT_PATH.read_text(encoding="utf-8"))
        steps = _load_runtime_steps(str(EXPECT_PATH))

        self.assertEqual(expect["page_id"], 0)
        self.assertEqual(expect["select_page"], 0)
        self.assertEqual([item["target"] for item in expect["expectations"]], ["s0.x", "b1.txt"])
        self.assertIn("set_expectations", expect)

        add_steps = [step for step in steps if step.command == "add s0.id,0,50"]
        self.assertEqual(len(add_steps), 1)
        self.assertEqual(add_steps[0].expected_kind, "none")

        invalid_reference_commands = {step.command for step in steps if step.expected_kind == "invalid_reference"}
        self.assertEqual(invalid_reference_commands, {"get t0.txt", "get b0.txt", "get p0.pic"})

    def test_demo_folder_does_not_claim_hardware_verification(self) -> None:
        self.assertEqual(list(DEMO_DIR.glob("hardware_verified*.json")), [])
        self.assertEqual(list(DEMO_DIR.glob("*hardware*verified*.json")), [])

    @unittest.skipUnless(
        SEED_HMI.exists() and BASELINE_TFT.exists(),
        "local TJC seed HMI/TFT fixtures are not available",
    )
    def test_waveform_demo_builds_offline_clean_rebuild_with_runtime_pads(self) -> None:
        scene = load_scene(SCENE_PATH)

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = build_scene(scene, SEED_HMI, temp_dir, baseline_tft=BASELINE_TFT)

            self.assertTrue(Path(manifest["output_tft"]).exists())
            self.assertTrue(manifest["tft_checksum"]["valid"])
            self.assertEqual(manifest["tft_patch"]["mode"], "experimental_clean_page_tft_rebuild")
            self.assertEqual(manifest["tft_patch"]["object_count"], 6)

            target_page = load_page_file(manifest["tft_patch"]["target_pa"])
            objects = [(block.objname, block.type_code, _field_int(block, "id")) for block in target_page.blocks]
            self.assertEqual(
                objects,
                [
                    ("page0", "y", 0),
                    ("_wfpad1", "t", 1),
                    ("_wfpad2", "b", 2),
                    ("_wfpad3", "p", 3),
                    ("s0", "\x00", 4),
                    ("b1", "b", 5),
                ],
            )


def _field_int(block, name: str) -> int:
    field = block.get_field(name)
    assert field is not None
    return int.from_bytes(field.value, "little")


if __name__ == "__main__":
    unittest.main()
