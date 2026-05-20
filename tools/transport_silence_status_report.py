from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "examples" / "lifecycle_runtime_smoke" / "transport_silence_status_2026-05-21.json"


def _load(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def main() -> int:
    baud = _load("examples/lifecycle_runtime_smoke/serial_baud_sweep_2026-05-21.json")
    ports = _load("examples/lifecycle_runtime_smoke/serial_port_inventory_2026-05-21.json")
    modem = _load("examples/lifecycle_runtime_smoke/serial_modem_status_2026-05-21.json")
    button = _load("examples/lifecycle_runtime_smoke/official_gui_download_button_probe_summary_2026-05-21.json")
    button_state = _load("examples/lifecycle_runtime_smoke/official_gui_download_button_state_2026-05-21.json")
    orchestrated = _load("examples/lifecycle_runtime_smoke/recover_then_seed_side_run_2026-05-21.json")
    whmi = _load("examples/lifecycle_runtime_smoke/public_whmi_entry_probe_summary_2026-05-21.json")
    pulse = _load("examples/lifecycle_runtime_smoke/dtr_rts_pulse_probe_summary_2026-05-21.json")
    reenum = _load("examples/lifecycle_runtime_smoke/usb_uart_reenumeration_probe_summary_2026-05-21.json")
    camera = _load("examples/lifecycle_runtime_smoke/transport_silence_camera_status_2026-05-21.json")
    sd_pkg = _load("examples/lifecycle_runtime_smoke/sd_recovery_package_2026-05-21.json")
    sd_handoff = _load("examples/lifecycle_runtime_smoke/sd_recovery_handoff_2026-05-21.json")

    payload = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "transport-silence-summarized",
        "evidence": {
            "serial_baud_sweep": {
                "artifact": "examples/lifecycle_runtime_smoke/serial_baud_sweep_2026-05-21.json",
                "all_bauds_silent": baud["conclusions"]["all_common_and_high_bauds_silent"],
            },
            "serial_port_inventory": {
                "artifact": "examples/lifecycle_runtime_smoke/serial_port_inventory_2026-05-21.json",
                "only_plausible_live_uart_is_com36": ports["conclusions"]["only_plausible_live_uart_is_com36"],
            },
            "serial_modem_status": {
                "artifact": "examples/lifecycle_runtime_smoke/serial_modem_status_2026-05-21.json",
                "bridge_opens": modem["conclusions"]["serial_bridge_opens"],
                "all_inbound_modem_lines_low": modem["conclusions"]["all_inbound_modem_lines_low"],
            },
            "official_gui_button_probe": {
                "artifact": "examples/lifecycle_runtime_smoke/official_gui_download_button_probe_summary_2026-05-21.json",
                "all_local_methods_failed": button["conclusions"]["all_local_button_interaction_methods_failed_to_enter_running_state"],
                "bm_click_invoked": button["bm_click_invoked"],
            },
            "official_gui_button_state": {
                "artifact": "examples/lifecycle_runtime_smoke/official_gui_download_button_state_2026-05-21.json",
                "is_enabled": button_state["button"]["is_enabled"],
                "is_visible": button_state["button"]["is_visible"],
            },
            "orchestrated_recovery": {
                "artifact": "examples/lifecycle_runtime_smoke/recover_then_seed_side_run_2026-05-21.json",
                "classification": orchestrated["classification"],
                "runner_started": orchestrated["runner_started"],
            },
            "public_whmi_entry_probe": {
                "artifact": "examples/lifecycle_runtime_smoke/public_whmi_entry_probe_summary_2026-05-21.json",
                "ack_received": whmi["ack_received"],
            },
            "dtr_rts_pulse_probe": {
                "artifact": "examples/lifecycle_runtime_smoke/dtr_rts_pulse_probe_summary_2026-05-21.json",
                "no_change_after_pulse": pulse["conclusions"]["dtr_rts_pulse_showed_no_observable_change"],
            },
            "usb_uart_reenumeration_probe": {
                "artifact": "examples/lifecycle_runtime_smoke/usb_uart_reenumeration_probe_summary_2026-05-21.json",
                "disable_enable_ok": reenum["disable_ok"] and reenum["enable_ok"],
                "no_change_after_reenumeration": reenum["conclusions"]["no_change_after_reenumeration"],
            },
            "camera_status": {
                "artifact": "examples/lifecycle_runtime_smoke/transport_silence_camera_status_2026-05-21.json",
                "screen_not_black": camera["conclusions"]["screen_not_black"],
                "mean_luma": camera["current_camera"]["mean_luma"],
            },
            "sd_recovery_package": {
                "artifact": "examples/lifecycle_runtime_smoke/sd_recovery_package_2026-05-21.json",
                "package_ready": sd_pkg["conclusions"]["package_ready_for_external_use_if_panel_remains_transport_silent"],
                "repo_sha256": sd_pkg["tft"]["sha256"],
            },
            "sd_recovery_handoff": {
                "artifact": "examples/lifecycle_runtime_smoke/sd_recovery_handoff_2026-05-21.json",
                "bundle_dir": sd_handoff["bundle_dir"],
                "bundle_zip": sd_handoff["bundle_zip"],
                "verify_cmd": sd_handoff["ordered_verify_cmd"],
                "followup_cmd": sd_handoff["ordered_followup_cmd"],
                "manual_gui_cmd": sd_handoff["manual_gui_cmd"],
                "status_summary_file": sd_handoff["status_summary_file"],
            },
        },
        "conclusions": {
            "runtime_silence_not_explained_by_baud_drift": baud["conclusions"]["not_explained_by_simple_command_baud_drift"],
            "runtime_silence_not_explained_by_port_enumeration_drift": ports["conclusions"]["not_explained_by_panel_having_moved_to_another_visible_usb_uart"],
            "usb_uart_bridge_itself_still_opens": modem["conclusions"]["serial_bridge_opens"],
            "panel_is_visibly_powered_not_black": camera["conclusions"]["screen_not_black"],
            "official_gui_local_interaction_not_sufficient_to_start_download": button["conclusions"]["not_explained_by_simple_missed_click"],
            "official_gui_start_failure_not_explained_by_disabled_button": button_state["conclusions"]["failure_is_not_explained_by_a_disabled_button"],
            "public_whmi_entry_is_also_silent": whmi["conclusions"]["public_whmi_entry_is_silent"],
            "dtr_rts_recovery_path_showed_no_change": pulse["conclusions"]["dtr_rts_pulse_showed_no_observable_change"],
            "usb_uart_reenumeration_showed_no_change": reenum["conclusions"]["no_change_after_reenumeration"],
            "seed_side_runtime_limiter_runner_is_currently_blocked_by_transport": orchestrated["conclusions"]["seed_side_runtime_limiter_runner_blocked_by_transport"],
            "external_sd_recovery_bundle_is_ready": sd_pkg["conclusions"]["package_ready_for_external_use_if_panel_remains_transport_silent"],
            "best_current_repo_side_state": "local software automation is prepared; the panel is visibly powered but transport-silent all the way up through the public upload entrypoint, so further progress now depends on external recovery restoring at least one responsive command path",
        },
    }

    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
