from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .editor import _build_live_smoke_expectation_payload, build_scene
from .scene import load_scene
from .target_invariants import check_next_probe_tft_invariants
from .target_status import BUILDER_FIELD_MAP, target_status_summary


DEFAULT_SEED = Path(r"D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI")
DEFAULT_BASELINE_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft")
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "reverse_usarthmi" / "scene_smoke"
NEXT_PROBE_QUARANTINE_KIND = "page1_filebrowser_count_buffer_candidate_live_probe"


def build_scene_smoke_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("scene_path", help="Scene JSON/YAML file")
    parser.add_argument("--seed", default=str(DEFAULT_SEED), help="Seed HMI file")
    parser.add_argument("--baseline-tft", default=str(DEFAULT_BASELINE_TFT), help="Baseline TFT file")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--expect-json", help="Override the generated sibling smoke.expect.json")
    parser.add_argument(
        "--check-expect",
        nargs="?",
        const="AUTO",
        help="Compare scene-generated smoke.expect content against a file; omit value to use the conventional sibling path.",
    )
    parser.add_argument(
        "--write-expect",
        nargs="?",
        const="AUTO",
        help="Write scene-generated smoke.expect content to a file; omit value to use the conventional sibling path.",
    )
    parser.add_argument("--skip-build", action="store_true", help="Reuse an existing <out>/output.tft")
    parser.add_argument("--preflight", action="store_true", help="Run serial upload preflight after readiness")
    parser.add_argument("--smoke", action="store_true", help="Run live serial checks with tools/live_tft_smoke.py")
    parser.add_argument("--upload", action="store_true", help="Upload before live smoke checks")
    parser.add_argument("--capture", action="store_true", help="Capture the screen during live smoke")
    parser.add_argument("--port", default="COM36")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--download-baud", type=int, default=921600)
    parser.add_argument("--timeout-ms", type=int, default=3000)
    parser.add_argument("--expected-model", default="TJC8048X543_011C")
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--known-current", help="Known-current TFT path for skip-if-identical runs")
    parser.add_argument("--skip-if-identical", action="store_true")
    parser.add_argument("--allow-hardware-quarantine", action="store_true")
    parser.add_argument("--allow-pending-sd-recovery", action="store_true")
    return parser


def run_scene_smoke(
    scene_path: str | Path,
    *,
    seed_hmi: str | Path = DEFAULT_SEED,
    baseline_tft: str | Path = DEFAULT_BASELINE_TFT,
    out_dir: str | Path = DEFAULT_OUT,
    expect_json: str | Path | None = None,
    check_expect_path: str | Path | None = None,
    write_expect_path: str | Path | None = None,
    skip_build: bool = False,
    preflight: bool = False,
    smoke: bool = False,
    upload: bool = False,
    capture: bool = False,
    port: str = "COM36",
    baud: int = 9600,
    download_baud: int = 921600,
    timeout_ms: int = 3000,
    expected_model: str = "TJC8048X543_011C",
    progress: bool = False,
    known_current: str | Path | None = None,
    skip_if_identical: bool = False,
    allow_hardware_quarantine: bool = False,
    allow_pending_sd_recovery: bool = False,
) -> dict[str, Any]:
    from .api import get_tft_readiness

    source_scene = load_scene(scene_path)
    generated_expect = _generated_expectation_payload(source_scene)
    out_path = Path(out_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)
    output_tft = out_path / "output.tft"
    target_status = target_status_summary()
    target_status_path = out_path / "target_status.json"
    target_status_path.write_text(json.dumps(target_status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    build_result: dict[str, Any] | None = None
    if not skip_build:
        build_result = build_scene(
            source_scene,
            seed_hmi,
            out_path,
            baseline_tft=baseline_tft,
        )
        output_tft = Path(build_result["output_tft"])
    elif not output_tft.exists():
        raise FileNotFoundError(f"--skip-build requested but {output_tft} does not exist")

    manifest = _load_manifest(out_path)
    expect_path = _pick_expect_json(expect_json, manifest)
    expect_check = None
    if check_expect_path is not None:
        expect_check = _check_expect_file(scene_path, generated_expect, check_expect_path)
    expect_write = None
    if write_expect_path is not None:
        expect_write = _write_expect_file(scene_path, generated_expect, write_expect_path)
    readiness = get_tft_readiness(output_tft)
    field_map_invariants, field_map_invariants_path = _maybe_check_field_map_invariants(
        output_tft=output_tft,
        out_dir=out_path,
        manifest=manifest,
    )
    preflight_result = None
    if preflight or smoke or upload or capture:
        preflight_result = _run_preflight(
            output_tft=output_tft,
            port=port,
            baud=baud,
            expected_model=expected_model,
        )
    smoke_result = None
    if smoke or upload or capture:
        if expect_path is None:
            raise RuntimeError(
                "No smoke.expect.json is available for this scene/build. "
                "Add project.live_smoke, rely on auto-generated smoke fields, or pass --expect-json explicitly."
            )
        smoke_result = _run_live_smoke(
            output_tft=output_tft,
            out_dir=out_path,
            expect_json=expect_path,
            port=port,
            baud=baud,
            download_baud=download_baud,
            timeout_ms=timeout_ms,
            upload=upload,
            capture=capture,
            progress=progress,
            allow_hardware_quarantine=allow_hardware_quarantine,
            allow_pending_sd_recovery=allow_pending_sd_recovery,
            known_current=known_current,
            skip_if_identical=skip_if_identical,
        )

    summary = {
        "ok": bool(readiness["summary"]["tft_checksum_valid"])
        and (expect_check is None or bool(expect_check.get("match")))
        and (expect_write is None or bool(expect_write.get("written")))
        and (
            field_map_invariants.get("skipped") is True
            or bool(field_map_invariants.get("summary", {}).get("ok"))
        )
        and (preflight_result is None or bool(preflight_result.get("summary", {}).get("ready")))
        and (smoke_result is None or bool(smoke_result.get("summary", {}).get("ok"))),
        "checksum_valid": bool(readiness["summary"]["tft_checksum_valid"]),
        "expect_check_ok": None if expect_check is None else bool(expect_check.get("match")),
        "expect_write_ok": None if expect_write is None else bool(expect_write.get("written")),
        "field_map_invariants_checked": not bool(field_map_invariants.get("skipped")),
        "field_map_invariants_ok": (
            None if field_map_invariants.get("skipped") else bool(field_map_invariants.get("summary", {}).get("ok"))
        ),
        "ready_for_live_upload": bool(readiness["summary"]["ready_for_live_upload"]),
        "preflight_ok": None if preflight_result is None else bool(preflight_result.get("summary", {}).get("ready")),
        "smoke_ok": None if smoke_result is None else bool(smoke_result.get("summary", {}).get("ok")),
        "uploaded": bool(smoke_result and smoke_result.get("summary", {}).get("uploaded")),
        "camera_captured": bool(smoke_result and smoke_result.get("summary", {}).get("camera_captured")),
        "safe_to_flash": False,
    }
    return {
        "scene": str(Path(scene_path).resolve()),
        "seed": str(Path(seed_hmi).resolve()),
        "baseline_tft": str(Path(baseline_tft).resolve()),
        "out_dir": str(out_path),
        "output_tft": str(output_tft),
        "smoke_expect_json": str(expect_path) if expect_path is not None else None,
        "target_status_json": str(target_status_path),
        "field_map_invariants_json": (
            str(field_map_invariants_path) if field_map_invariants_path is not None else None
        ),
        "build": build_result,
        "manifest": manifest,
        "generated_expect": generated_expect,
        "expect_check": expect_check,
        "expect_write": expect_write,
        "readiness": readiness,
        "field_map_invariants": field_map_invariants,
        "target_status": target_status,
        "preflight": preflight_result,
        "smoke": smoke_result,
        "summary": summary,
    }


def _load_manifest(out_dir: Path) -> dict[str, Any] | None:
    manifest_path = out_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _maybe_check_field_map_invariants(
    *,
    output_tft: Path,
    out_dir: Path,
    manifest: dict[str, Any] | None,
) -> tuple[dict[str, Any], Path | None]:
    gate = _field_map_invariant_gate(output_tft=output_tft, manifest=manifest)
    if not gate["check"]:
        return {
            "skipped": True,
            "reason": gate["reason"],
            "candidate_tft": gate["candidate_tft"],
            "hardware_quarantine": gate.get("hardware_quarantine"),
        }, None

    result = check_next_probe_tft_invariants(output_tft)
    result["trigger"] = gate["reason"]
    result_path = out_dir / "field_map_invariants.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result, result_path


def _field_map_invariant_gate(*, output_tft: Path, manifest: dict[str, Any] | None) -> dict[str, Any]:
    candidate = _load_field_map_candidate()
    expected_path = _resolve_candidate_path(candidate.get("path"))
    expected_sha = str(candidate.get("sha256", "")).lower() or None
    target_path = output_tft.resolve()
    hardware_quarantine = (manifest or {}).get("hardware_quarantine")
    quarantine_kind = hardware_quarantine.get("kind") if isinstance(hardware_quarantine, dict) else None

    payload = {
        "check": False,
        "reason": "output_tft_is_not_current_next_probe_candidate",
        "candidate_tft": {
            "path": str(target_path),
            "expected_path": str(expected_path) if expected_path is not None else None,
            "expected_sha256": expected_sha,
            "actual_sha256": None,
            "sha256_match": False,
        },
        "hardware_quarantine": hardware_quarantine,
    }
    if not target_path.exists():
        payload["reason"] = "output_tft_missing"
        return payload
    if quarantine_kind == NEXT_PROBE_QUARANTINE_KIND:
        payload["check"] = True
        payload["reason"] = "manifest_marks_current_next_probe_candidate"
        return payload
    if expected_path is not None and _same_resolved_path(target_path, expected_path):
        payload["check"] = True
        payload["reason"] = "output_path_matches_current_next_probe_candidate"
        return payload
    if expected_sha is not None:
        actual_sha = _sha256_file(target_path)
        payload["candidate_tft"]["actual_sha256"] = actual_sha
        payload["candidate_tft"]["sha256_match"] = actual_sha == expected_sha
        if actual_sha == expected_sha:
            payload["check"] = True
            payload["reason"] = "output_sha256_matches_current_next_probe_candidate"
    return payload


def _load_field_map_candidate() -> dict[str, Any]:
    if not BUILDER_FIELD_MAP.exists():
        return {}
    payload = json.loads(BUILDER_FIELD_MAP.read_text(encoding="utf-8-sig"))
    candidate = ((payload.get("next_probe") or {}).get("candidate_tft") or {})
    return candidate if isinstance(candidate, dict) else {}


def _resolve_candidate_path(path: Any) -> Path | None:
    if not isinstance(path, str) or not path:
        return None
    return Path(path).resolve()


def _same_resolved_path(left: Path, right: Path) -> bool:
    return str(left).casefold() == str(right).casefold()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pick_expect_json(explicit: str | Path | None, manifest: dict[str, Any] | None) -> Path | None:
    if explicit is not None:
        return Path(explicit).resolve()
    path = ((manifest or {}).get("live_smoke") or {}).get("smoke_expect_json")
    if not path:
        return None
    return Path(str(path)).resolve()


def _generated_expectation_payload(scene) -> dict[str, Any] | None:
    payload = _build_live_smoke_expectation_payload(scene)
    if payload is None:
        return None
    return json.loads(json.dumps(payload, ensure_ascii=False))


def _resolve_expect_target(scene_path: str | Path, explicit: str | Path | None) -> Path:
    if explicit is not None and str(explicit) != "AUTO":
        return Path(explicit).resolve()
    scene_file = Path(scene_path).resolve()
    if scene_file.stem == "scene":
        return scene_file.with_name("smoke.expect.json")
    if scene_file.stem.endswith("_scene"):
        return scene_file.with_name(f"{scene_file.stem[:-6]}_smoke.expect.json")
    return scene_file.with_name(f"{scene_file.stem}.smoke.expect.json")


def _check_expect_file(scene_path: str | Path, generated_payload: dict[str, Any] | None, explicit: str | Path) -> dict[str, Any]:
    target = _resolve_expect_target(scene_path, explicit)
    payload = {
        "path": str(target),
        "exists": target.exists(),
        "generated_available": generated_payload is not None,
        "match": False,
    }
    if generated_payload is None:
        payload["reason"] = "scene does not currently generate a smoke expectation payload"
        return payload
    if not target.exists():
        payload["reason"] = "target expect file does not exist"
        return payload
    existing = json.loads(target.read_text(encoding="utf-8"))
    payload["match"] = _smoke_payloads_equivalent(generated_payload, existing)
    if not payload["match"]:
        payload["reason"] = "generated payload and target file differ"
    return payload


def _write_expect_file(scene_path: str | Path, generated_payload: dict[str, Any] | None, explicit: str | Path) -> dict[str, Any]:
    target = _resolve_expect_target(scene_path, explicit)
    payload = {
        "path": str(target),
        "generated_available": generated_payload is not None,
        "written": False,
        "existed_before": target.exists(),
    }
    if generated_payload is None:
        payload["reason"] = "scene does not currently generate a smoke expectation payload"
        return payload
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(generated_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    payload["written"] = True
    return payload


def _smoke_payloads_equivalent(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return _normalized_smoke_payload(left) == _normalized_smoke_payload(right)


def _normalized_smoke_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "page_id": payload.get("page_id"),
        "select_page": payload.get("select_page"),
        "restore_page": payload.get("restore_page"),
        "expectations": _normalize_expect_entries(payload.get("expectations")),
        "set_expectations": _normalize_expect_entries(payload.get("set_expectations")),
        "steps": payload.get("steps", []),
    }
    if payload.get("generation_warnings") is not None:
        normalized["generation_warnings"] = payload.get("generation_warnings")
    return normalized


def _normalize_expect_entries(entries: Any) -> dict[str, Any] | None:
    if entries is None:
        return None
    if isinstance(entries, dict):
        return dict(sorted(entries.items()))
    if not isinstance(entries, list):
        return entries
    normalized: dict[str, Any] = {}
    for item in entries:
        if not isinstance(item, dict):
            return entries
        target = item.get("target") or item.get("name")
        if not isinstance(target, str):
            return entries
        normalized[target] = item
    return dict(sorted(normalized.items()))


def _run_preflight(*, output_tft: Path, port: str, baud: int, expected_model: str) -> dict[str, Any]:
    cmd = [
        sys.executable,
        "-m",
        "usarthmi",
        "--json",
        "tft",
        "preflight",
        "--file",
        str(output_tft),
        "--port",
        port,
        "--baud",
        str(baud),
        "--expected-model",
        expected_model,
    ]
    completed = subprocess.run(cmd, text=True, capture_output=True, check=False)
    payload = _parse_json_stdout(completed.stdout)
    payload["returncode"] = completed.returncode
    payload["command"] = cmd
    if completed.stderr.strip():
        payload["stderr"] = completed.stderr.strip()
    return payload


def _run_live_smoke(
    *,
    output_tft: Path,
    out_dir: Path,
    expect_json: Path,
    port: str,
    baud: int,
    download_baud: int,
    timeout_ms: int,
    upload: bool,
    capture: bool,
    progress: bool,
    allow_hardware_quarantine: bool,
    allow_pending_sd_recovery: bool,
    known_current: str | Path | None,
    skip_if_identical: bool,
) -> dict[str, Any]:
    smoke_dir = out_dir / ("smoke_capture" if capture else "smoke")
    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parents[1] / "tools" / "live_tft_smoke.py"),
        "--file",
        str(output_tft),
        "--out-dir",
        str(smoke_dir),
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
    ]
    if upload:
        cmd.append("--upload")
    if capture:
        cmd.append("--capture")
    if progress:
        cmd.append("--progress")
    if allow_hardware_quarantine:
        cmd.append("--allow-hardware-quarantine")
    if allow_pending_sd_recovery:
        cmd.append("--allow-pending-sd-recovery")
    if known_current:
        cmd.extend(["--known-current", str(Path(known_current).resolve())])
    if skip_if_identical:
        cmd.append("--skip-if-identical")

    completed = subprocess.run(cmd, text=True, capture_output=True, check=False)
    payload = _parse_json_stdout(completed.stdout)
    payload["returncode"] = completed.returncode
    payload["command"] = cmd
    if completed.stderr.strip():
        payload["stderr"] = completed.stderr.strip()
    if completed.returncode != 0:
        payload.setdefault("summary", {})["ok"] = False
    return payload


def _parse_json_stdout(stdout: str) -> dict[str, Any]:
    if not stdout.strip():
        return {"stdout": stdout}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"stdout": stdout}
