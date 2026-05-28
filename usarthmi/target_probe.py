from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .sd_recovery_guard import pending_sd_recovery_reason
from .target_invariants import check_next_probe_tft_invariants
from .target_status import next_live_probe_bundle
from .tft_checksum import inspect_tft_checksum
from .tft_hmisafe import verify_final_tft


ROOT = Path(__file__).resolve().parents[1]


def run_next_live_probe_bundle(
    *,
    preflight: bool = False,
    live_smoke: bool = False,
    upload: bool = False,
    allow_hardware_quarantine: bool = False,
    allow_pending_sd_recovery: bool = False,
    capture: bool = False,
    progress: bool = False,
    port: str = "COM36",
    baud: int = 9600,
    download_baud: int = 921600,
    timeout_ms: int = 3000,
    out_dir: str | Path | None = None,
    result_json: str | Path | None = None,
) -> dict[str, Any]:
    """Run safe portions of the current target's next live-probe bundle."""
    bundle = next_live_probe_bundle()
    candidate_tft = Path(bundle["candidate_tft"]["path"]).resolve()
    expect_json = Path(bundle["probe_files"]["smoke_expect_json"]["path"]).resolve()
    expected_sha = str(bundle["candidate_tft"]["sha256"]).lower()
    actual_sha = _sha256_file(candidate_tft) if candidate_tft.exists() else None
    sha_match = actual_sha == expected_sha
    checksum = inspect_tft_checksum(candidate_tft) if candidate_tft.exists() else {"valid": False}
    hmisafe = _hmisafe_summary(candidate_tft) if candidate_tft.exists() else {"all_ok": False}
    field_map_invariants = check_next_probe_tft_invariants(candidate_tft) if candidate_tft.exists() else {
        "summary": {"ok": False},
        "checks": [],
    }
    readiness = _offline_readiness(candidate_tft, checksum=checksum)
    run_root = Path(out_dir).resolve() if out_dir is not None else candidate_tft.parent / "live_probe"

    preflight_result = None
    if preflight:
        preflight_result = _run_json_command(
            [
                sys.executable,
                "-m",
                "usarthmi",
                "--json",
                "tft",
                "preflight",
                "--file",
                str(candidate_tft),
                "--port",
                port,
                "--baud",
                str(baud),
                "--timeout-ms",
                str(timeout_ms),
                "--expected-model",
                "TJC8048X543_011C",
            ]
        )

    live_smoke_result = None
    if upload and not live_smoke:
        live_smoke_result = {
            "skipped": True,
            "blocked": True,
            "reason": "upload_requires_live_smoke",
            "detail": "Pass --live-smoke together with --upload so the bundle readback checks run after upload.",
        }
    elif live_smoke:
        if not bundle.get("safety_gates", {}).get("live_probe_allowed_now", True):
            frontier = bundle.get("current_frontier") or {}
            live_smoke_result = {
                "skipped": True,
                "blocked": True,
                "reason": "historical_candidate_not_current_frontier",
                "detail": (
                    "The checked-in count-buffer candidate is preserved as a historical live-negative reference. "
                    "Current frontier: "
                    f"{frontier.get('id') or 'unknown'}."
                ),
            }
        elif upload and not allow_hardware_quarantine:
            live_smoke_result = {
                "skipped": True,
                "blocked": True,
                "reason": "hardware_quarantine_requires_explicit_override",
                "detail": "Pass --allow-hardware-quarantine for the one controlled recovery upload.",
            }
        else:
            smoke_out = run_root / ("single_recovery_upload" if upload else "readback_no_upload")
            cmd = [
                sys.executable,
                str(ROOT / "tools" / "live_tft_smoke.py"),
                "--file",
                str(candidate_tft),
                "--out-dir",
                str(smoke_out),
                "--expect-json",
                str(expect_json),
                "--port",
                port,
                "--baud",
                str(baud),
                "--download-baud",
                str(download_baud),
                "--timeout-ms",
                str(timeout_ms),
                "--require-model",
                "TJC8048X543_011C",
            ]
            if upload:
                cmd.extend(["--upload", "--allow-hardware-quarantine"])
            if allow_pending_sd_recovery:
                cmd.append("--allow-pending-sd-recovery")
            if capture:
                cmd.append("--capture")
            if progress:
                cmd.append("--progress")
            live_smoke_result = _run_json_command(cmd)

    steps = {
        "checksum": {
            "executed": True,
            "ok": bool(checksum.get("valid")),
        },
        "hmisafe": {
            "executed": True,
            "ok": bool(hmisafe.get("all_ok")),
        },
        "field_map_invariants": {
            "executed": True,
            "ok": bool(field_map_invariants.get("summary", {}).get("ok")),
            "failed_hard_checks": field_map_invariants.get("summary", {}).get("failed_hard_checks"),
        },
        "offline_readiness": {
            "executed": True,
            "ready_for_live_upload": bool(readiness["summary"]["ready_for_live_upload"]),
            "hardware_quarantine_blocked": bool(readiness["summary"]["hardware_quarantine_blocked"]),
            "sd_recovery_blocked": bool(readiness["summary"]["sd_recovery_blocked"]),
        },
        "preflight": {
            "executed": preflight_result is not None,
            "ok": None if preflight_result is None else preflight_result["returncode"] == 0,
        },
        "live_smoke": {
            "executed": bool(live_smoke and live_smoke_result and not live_smoke_result.get("skipped")),
            "ok": _live_smoke_ok(live_smoke_result),
            "uploaded": bool(
                live_smoke_result
                and live_smoke_result.get("summary", {}).get("uploaded")
                and not live_smoke_result.get("skipped")
            ),
        },
    }
    summary_ok = (
        bool(candidate_tft.exists())
        and sha_match
        and bool(checksum.get("valid"))
        and bool(hmisafe.get("all_ok"))
        and bool(field_map_invariants.get("summary", {}).get("ok"))
        and _optional_step_ok(preflight_result)
        and _optional_live_step_ok(live_smoke_result)
    )
    result_json_path = Path(result_json).resolve() if result_json is not None else None
    result = {
        "schema_version": 1,
        "target": bundle["target"],
        "bundle_status": bundle["status"],
        "result_json": str(result_json_path) if result_json_path is not None else None,
        "candidate_tft": {
            "path": str(candidate_tft),
            "expected_sha256": expected_sha,
            "actual_sha256": actual_sha,
            "sha256_match": sha_match,
        },
        "smoke_expect_json": str(expect_json),
        "checksum": checksum,
        "hmisafe": hmisafe,
        "field_map_invariants": field_map_invariants,
        "readiness": readiness,
        "preflight": preflight_result,
        "live_smoke": live_smoke_result,
        "steps": steps,
        "summary": {
            "ok": summary_ok,
            "safe_to_flash": False,
            "ready_for_live_upload": bool(readiness["summary"]["ready_for_live_upload"]),
            "hardware_quarantine_blocked": bool(readiness["summary"]["hardware_quarantine_blocked"]),
            "field_map_invariants_ok": bool(field_map_invariants.get("summary", {}).get("ok")),
            "sd_recovery_blocked": bool(readiness["summary"]["sd_recovery_blocked"]),
            "preflight_ran": preflight_result is not None,
            "live_smoke_ran": steps["live_smoke"]["executed"],
            "uploaded": steps["live_smoke"]["uploaded"],
            "upload_requires_allow_hardware_quarantine": bool(
                bundle["safety_gates"]["upload_requires_allow_hardware_quarantine"]
            ),
        },
        "not_claimed": [
            "Default run-next-probe does not upload or prove the candidate on hardware.",
            "A live pass still requires the exact upload/readback/camera criteria in target next-probe.",
        ],
    }
    if result_json_path is not None:
        result_json_path.parent.mkdir(parents=True, exist_ok=True)
        result_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def _run_json_command(cmd: list[str]) -> dict[str, Any]:
    completed = subprocess.run(cmd, text=True, capture_output=True, check=False)
    payload = _parse_json_stdout(completed.stdout)
    payload["returncode"] = completed.returncode
    payload["command"] = cmd
    if completed.stderr.strip():
        payload["stderr"] = completed.stderr.strip()
    return payload


def _parse_json_stdout(stdout: str) -> dict[str, Any]:
    if not stdout.strip():
        return {"stdout": stdout}
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return {"stdout": stdout}
    return payload if isinstance(payload, dict) else {"stdout_json": payload}


def _offline_readiness(candidate_tft: Path, *, checksum: dict[str, Any]) -> dict[str, Any]:
    manifest = _load_manifest(candidate_tft)
    quarantine_reason = _manifest_hardware_quarantine_reason(candidate_tft, manifest)
    sd_reason = pending_sd_recovery_reason()
    checksum_ok = bool(checksum.get("valid"))
    delivery_status = manifest.get("delivery_status") if manifest else None
    manifest_ready = None
    manifest_reason = None
    if isinstance(delivery_status, dict):
        ready_value = delivery_status.get("ready_for_live_upload")
        manifest_ready = bool(ready_value) if isinstance(ready_value, bool) else None
        raw_reason = delivery_status.get("reason")
        manifest_reason = str(raw_reason) if raw_reason else None
    ready = checksum_ok and not quarantine_reason and not sd_reason and (manifest_ready is not False)
    if not checksum_ok:
        diagnosis = "TFT checksum is invalid; do not upload until it is repaired."
    elif quarantine_reason:
        diagnosis = quarantine_reason
    elif sd_reason:
        diagnosis = sd_reason
    elif manifest_ready is False and manifest_reason:
        diagnosis = manifest_reason
    else:
        diagnosis = "offline build appears eligible for live upload; run serial preflight next."
    return {
        "file": str(candidate_tft),
        "summary": {
            "ready_for_live_upload": ready,
            "tft_checksum_valid": checksum_ok,
            "build_manifest_present": manifest is not None,
            "hardware_quarantine_blocked": bool(quarantine_reason),
            "sd_recovery_blocked": bool(sd_reason),
            "diagnosis": diagnosis,
        },
        "build_manifest": manifest,
        "dangerous_tft_quarantine_reason": quarantine_reason,
        "sd_recovery_pending_reason": sd_reason,
    }


def _load_manifest(candidate_tft: Path) -> dict[str, Any] | None:
    manifest_path = candidate_tft.with_name("manifest.json")
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return {
        "manifest_path": str(manifest_path),
        "delivery_status": manifest.get("delivery_status"),
        "hardware_quarantine": manifest.get("hardware_quarantine"),
        "target_status": manifest.get("target_status"),
    }


def _manifest_hardware_quarantine_reason(candidate_tft: Path, manifest: dict[str, Any] | None) -> str | None:
    if manifest is None:
        return None
    quarantine = manifest.get("hardware_quarantine")
    if not isinstance(quarantine, dict) or not quarantine.get("active"):
        return None
    reason = str(quarantine.get("reason") or "").strip()
    patch_path = str(quarantine.get("patch_path") or "").strip()
    manifest_path = manifest.get("manifest_path") or str(candidate_tft.with_name("manifest.json"))
    if not reason:
        if patch_path:
            return f"sibling manifest {manifest_path} declares an active hardware quarantine (patch_path={patch_path})"
        return f"sibling manifest {manifest_path} declares an active hardware quarantine"
    if patch_path:
        return f"sibling manifest {manifest_path} declares an active hardware quarantine (patch_path={patch_path}): {reason}"
    return f"sibling manifest {manifest_path} declares an active hardware quarantine: {reason}"


def _hmisafe_summary(path: Path) -> dict[str, Any]:
    verify = verify_final_tft(path.read_bytes())
    return {
        "header_crc_ok": bool(verify["header_crc_ok"]),
        "header_tail_crc_ok": bool(verify["header_tail_crc_ok"]),
        "footer_ok": bool(verify["footer_ok"]),
        "all_ok": bool(verify["header_crc_ok"] and verify["header_tail_crc_ok"] and verify["footer_ok"]),
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _optional_step_ok(result: dict[str, Any] | None) -> bool:
    return result is None or result.get("returncode") == 0


def _optional_live_step_ok(result: dict[str, Any] | None) -> bool:
    if result is None:
        return True
    if result.get("skipped"):
        return False
    if "returncode" in result:
        return result.get("returncode") == 0
    return False


def _live_smoke_ok(result: dict[str, Any] | None) -> bool | None:
    if result is None:
        return None
    if result.get("skipped"):
        return False
    if "returncode" in result:
        return result.get("returncode") == 0
    return False
