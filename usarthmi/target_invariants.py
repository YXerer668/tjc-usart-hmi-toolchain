from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .target_status import BUILDER_FIELD_MAP
from .tft_checksum import inspect_tft_checksum
from .tft_hmisafe import verify_final_tft


def check_next_probe_tft_invariants(
    tft_path: str | Path | None = None,
    *,
    field_map_path: str | Path = BUILDER_FIELD_MAP,
) -> dict[str, Any]:
    """Check the current next-probe TFT against the builder field-map gates."""
    field_map_file = Path(field_map_path)
    field_map = _load_json(field_map_file)
    candidate = field_map["next_probe"]["candidate_tft"]
    target_path = Path(tft_path if tft_path is not None else candidate["path"]).resolve()
    exists = target_path.exists()
    data = target_path.read_bytes() if exists else b""
    actual_sha = _sha256_bytes(data) if exists else None
    expected_sha = str(candidate["sha256"]).lower()

    checksum = inspect_tft_checksum(target_path) if exists else {"valid": False}
    hmisafe = _hmisafe_summary(data) if exists else {"all_ok": False}
    manifest = _load_sibling_manifest(target_path) if exists else None

    checks: list[dict[str, Any]] = []
    add_check(checks, "candidate_tft_exists", exists, "hard", {"path": str(target_path)})
    add_check(
        checks,
        "candidate_sha256_matches_field_map",
        actual_sha == expected_sha,
        "hard",
        {"expected_sha256": expected_sha, "actual_sha256": actual_sha},
    )
    add_check(checks, "tft_checksum_valid", bool(checksum.get("valid")), "hard", checksum)
    add_check(checks, "hmisafe_header_tail_footer_valid", bool(hmisafe.get("all_ok")), "hard", hmisafe)

    filebrowser = field_map["object_membership"]["filebrowser"]
    primary = filebrowser["primary_record"]
    add_check(
        checks,
        "filebrowser_primary_record_header_matches",
        _bytes_at(data, primary["absolute_offset"], len(bytes.fromhex(primary["header_hex"])))
        == bytes.fromhex(primary["header_hex"]),
        "hard",
        {
            "absolute_offset": primary["absolute_offset"],
            "absolute_offset_hex": f"0x{primary['absolute_offset']:X}",
            "expected_hex": primary["header_hex"],
            "actual_hex": _hex_at(data, primary["absolute_offset"], len(bytes.fromhex(primary["header_hex"]))),
        },
    )

    mirror = field_map["known_fields"]["filebrowser_mirror_event_offset"]
    mirror_value = _u32_at(data, mirror["absolute_offset"])
    add_check(
        checks,
        "filebrowser_mirror_event_offset_preserves_rejected_failing_value",
        mirror_value == mirror["failing_value"],
        "hard",
        {
            "absolute_offset": mirror["absolute_offset"],
            "absolute_offset_hex": mirror["absolute_offset_hex"],
            "expected_value": mirror["failing_value"],
            "expected_value_hex": mirror["failing_value_hex"],
            "actual_value": mirror_value,
            "actual_value_hex": None if mirror_value is None else f"0x{mirror_value:X}",
            "reason": "The event_offset-only and count+event_offset patches are live-negative; the current candidate must not silently reapply them.",
        },
    )

    count_candidate = field_map["known_fields"]["filebrowser_primary_buff_marker_count_buffer_candidate"]
    expected_count_bytes = bytes.fromhex(count_candidate["bytes_after"])
    actual_count_bytes = _bytes_at(data, count_candidate["absolute_offset"], len(expected_count_bytes))
    add_check(
        checks,
        "filebrowser_count_buffer_candidate_bytes_present",
        actual_count_bytes == expected_count_bytes,
        "hard",
        {
            "absolute_offset": count_candidate["absolute_offset"],
            "absolute_offset_hex": count_candidate["absolute_offset_hex"],
            "expected_hex": count_candidate["bytes_after"],
            "actual_hex": actual_count_bytes.hex(" ") if actual_count_bytes is not None else None,
            "formula": count_candidate["formula"],
        },
    )

    negative_boundaries = field_map["negative_patch_boundaries"]
    add_check(
        checks,
        "negative_patch_boundaries_are_fail_closed",
        all(bool(value) for value in negative_boundaries.values()),
        "hard",
        negative_boundaries,
    )

    hardware_quarantine = manifest.get("hardware_quarantine") if isinstance(manifest, dict) else None
    add_check(
        checks,
        "sibling_manifest_hardware_quarantine_active",
        isinstance(hardware_quarantine, dict) and bool(hardware_quarantine.get("active")),
        "hard",
        {
            "manifest_path": None if manifest is None else manifest.get("manifest_path"),
            "hardware_quarantine": hardware_quarantine,
        },
    )
    add_check(
        checks,
        "offline_gate_does_not_mark_safe_to_flash",
        field_map["next_probe"]["safe_to_flash"] is False,
        "hard",
        {
            "field_map_safe_to_flash": field_map["next_probe"]["safe_to_flash"],
            "upload_requires_allow_hardware_quarantine": field_map["next_probe"][
                "upload_requires_allow_hardware_quarantine"
            ],
        },
    )

    hard_checks_ok = all(item["ok"] for item in checks if item["severity"] == "hard")
    historical_live_negative = bool(field_map["next_probe"].get("historical_live_probe_was_negative"))
    return {
        "schema_version": 1,
        "target": field_map["target"],
        "field_map": {
            "path": str(field_map_file),
            "sha256": _sha256_file(field_map_file) if field_map_file.exists() else None,
            "status": field_map.get("status"),
        },
        "candidate_tft": {
            "path": str(target_path),
            "expected_sha256": expected_sha,
            "actual_sha256": actual_sha,
            "sha256_match": actual_sha == expected_sha,
        },
        "checksum": checksum,
        "hmisafe": hmisafe,
        "checks": checks,
        "summary": {
            "ok": hard_checks_ok,
            "hard_checks_ok": hard_checks_ok,
            "check_count": len(checks),
            "failed_hard_checks": [item["id"] for item in checks if item["severity"] == "hard" and not item["ok"]],
            "safe_to_flash": False,
            "requires_live_probe": not historical_live_negative,
            "hardware_quarantine_blocked": True,
            "diagnosis": (
                (
                    "historical count-buffer candidate still matches offline field-map invariants, but live evidence "
                    "already proved it insufficient; the current frontier requires a new enum-init/membership candidate"
                )
                if hard_checks_ok and historical_live_negative
                else (
                    "candidate matches offline field-map invariants; live proof is still required"
                    if hard_checks_ok
                    else "candidate failed one or more offline field-map invariant checks"
                )
            ),
        },
        "not_claimed": [
            "Offline invariant success does not prove runtime enumeration on hardware.",
            "The historical count-buffer candidate remains unsafe for general upload and is not the active next probe target.",
        ],
    }


def add_check(checks: list[dict[str, Any]], check_id: str, ok: bool, severity: str, evidence: dict[str, Any]) -> None:
    checks.append(
        {
            "id": check_id,
            "ok": bool(ok),
            "severity": severity,
            "evidence": evidence,
        }
    )


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _load_sibling_manifest(tft_path: Path) -> dict[str, Any] | None:
    manifest_path = tft_path.with_name("manifest.json")
    if not manifest_path.exists():
        return None
    payload = _load_json(manifest_path)
    payload["manifest_path"] = str(manifest_path)
    return payload


def _hmisafe_summary(data: bytes) -> dict[str, Any]:
    verify = verify_final_tft(data)
    return {
        "header_crc_ok": bool(verify["header_crc_ok"]),
        "header_tail_crc_ok": bool(verify["header_tail_crc_ok"]),
        "footer_ok": bool(verify["footer_ok"]),
        "all_ok": bool(verify["header_crc_ok"] and verify["header_tail_crc_ok"] and verify["footer_ok"]),
        "footer_stored": verify["footer_stored"],
        "footer_expected": verify["footer_expected"],
    }


def _bytes_at(data: bytes, offset: int, size: int) -> bytes | None:
    if offset < 0 or size < 0 or offset + size > len(data):
        return None
    return data[offset : offset + size]


def _hex_at(data: bytes, offset: int, size: int) -> str | None:
    chunk = _bytes_at(data, offset, size)
    return None if chunk is None else chunk.hex(" ")


def _u32_at(data: bytes, offset: int) -> int | None:
    chunk = _bytes_at(data, offset, 4)
    return None if chunk is None else int.from_bytes(chunk, "little")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
