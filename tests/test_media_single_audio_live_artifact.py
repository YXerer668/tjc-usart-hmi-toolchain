from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "media_single_audio_sd_smoke"


class MediaSingleAudioQueuedArtifactTests(unittest.TestCase):
    def test_queued_artifact_matches_expect_files_without_claiming_hardware_verified(self) -> None:
        queued = json.loads((EXAMPLE / "queued_hardware_proof_2026-05-17.json").read_text(encoding="utf-8"))
        smoke = json.loads((EXAMPLE / "smoke.expect.json").read_text(encoding="utf-8"))
        play = json.loads((EXAMPLE / "play.expect.json").read_text(encoding="utf-8"))

        self.assertFalse(queued["hardware_verified"])
        self.assertEqual(queued["status"], "queued_hardware_execution")
        self.assertTrue(queued["offline_build"]["checksum_valid"])
        self.assertRegex(queued["offline_build"]["checksum_hex"], r"^0x[0-9A-F]{8}$")

        smoke_fields = {
            item["target"]: item["expected"]
            for item in smoke["expectations"]
            if item["expected_kind"] == "number"
        }
        self.assertEqual(queued["expected_fields"]["smoke"]["wav0.en"], smoke_fields["wav0.en"])
        self.assertEqual(queued["expected_fields"]["smoke"]["wav0.vid"], smoke_fields["wav0.vid"])
        self.assertEqual(queued["expected_fields"]["smoke"]["wav0.loop"], smoke_fields["wav0.loop"])
        self.assertEqual(queued["expected_fields"]["smoke"]["wav0.fps"], smoke_fields["wav0.fps"])
        self.assertEqual(queued["expected_fields"]["smoke"]["wav0.dis"], smoke_fields["wav0.dis"])
        self.assertEqual(queued["expected_fields"]["smoke"]["wav0.tim"], smoke_fields["wav0.tim"])
        self.assertEqual(smoke["steps"][0]["command"], "get wav0.path")
        self.assertEqual(queued["expected_fields"]["smoke"]["wav0.path"], smoke["steps"][0]["expected_kind"])

        self.assertEqual(play["expectations"]["wav0.en"], queued["expected_fields"]["play"]["initial.wav0.en"])
        self.assertIn("play.expect.json", queued["queued_commands"]["play_smoke"])
        self.assertEqual(play["steps"][1]["expected_value"], queued["expected_fields"]["play"]["after_start.wav0.en"])
        self.assertEqual(play["steps"][3]["expected_value"], queued["expected_fields"]["play"]["after_stop.wav0.en"])

        self.assertNotIn("--port COM36", queued["queued_commands"]["build"])
        self.assertIn("--port COM36", queued["queued_commands"]["upload_smoke"])
        self.assertIn("--port COM36", queued["queued_commands"]["play_smoke"])

    def test_readme_names_the_three_hardware_queue_commands_and_boundaries(self) -> None:
        readme = (EXAMPLE / "README.md").read_text(encoding="utf-8")

        self.assertIn("Build:", readme)
        self.assertIn("Upload smoke:", readme)
        self.assertIn("Play smoke", readme)
        self.assertIn("--upload --progress", readme)
        self.assertIn("does not prove COM36 upload success", readme)
        self.assertIn("physical audio output", readme)


if __name__ == "__main__":
    unittest.main()
