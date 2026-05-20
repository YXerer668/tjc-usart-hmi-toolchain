from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/transport_silence_status_2026-05-21.json")


class TransportSilenceStatusArtifactTests(unittest.TestCase):
    def test_artifact_summarizes_local_transport_dead_end(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        evidence = payload["evidence"]
        conclusions = payload["conclusions"]

        self.assertEqual(payload["status"], "transport-silence-summarized")
        self.assertTrue(evidence["serial_baud_sweep"]["all_bauds_silent"])
        self.assertTrue(evidence["serial_port_inventory"]["only_plausible_live_uart_is_com36"])
        self.assertTrue(evidence["camera_status"]["screen_not_black"])
        self.assertTrue(evidence["official_gui_button_probe"]["all_local_methods_failed"])
        self.assertTrue(evidence["official_gui_button_probe"]["bm_click_invoked"])
        self.assertEqual(evidence["orchestrated_recovery"]["classification"], "still_silent_after_recovery")
        self.assertFalse(evidence["public_whmi_entry_probe"]["ack_received"])
        self.assertTrue(evidence["sd_recovery_package"]["package_ready"])
        self.assertTrue(evidence["sd_recovery_handoff"]["verify_cmd"].endswith("00_先双击_校验恢复包.cmd"))
        self.assertTrue(evidence["sd_recovery_handoff"]["followup_cmd"].endswith("01_SD恢复完成后双击_继续验证.cmd"))
        self.assertTrue(evidence["sd_recovery_handoff"]["manual_gui_cmd"].endswith("02_如需手动官方下载恢复.cmd"))
        self.assertTrue(conclusions["runtime_silence_not_explained_by_baud_drift"])
        self.assertTrue(conclusions["runtime_silence_not_explained_by_port_enumeration_drift"])
        self.assertTrue(conclusions["panel_is_visibly_powered_not_black"])
        self.assertTrue(conclusions["official_gui_local_interaction_not_sufficient_to_start_download"])
        self.assertTrue(conclusions["public_whmi_entry_is_also_silent"])
        self.assertTrue(conclusions["seed_side_runtime_limiter_runner_is_currently_blocked_by_transport"])
        self.assertTrue(conclusions["external_sd_recovery_bundle_is_ready"])


if __name__ == "__main__":
    unittest.main()
