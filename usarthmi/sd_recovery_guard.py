from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
SD_RECOVERY_STATE_PATH = WORKSPACE_ROOT / "reverse_usarthmi" / "recovery_sd_card" / "sd_recovery_state.json"


def _timestamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def load_sd_recovery_state(path: Path | None = None) -> dict[str, Any] | None:
    state_path = path or SD_RECOVERY_STATE_PATH
    if not state_path.exists():
        return None
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def save_sd_recovery_state(payload: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    state_path = path or SD_RECOVERY_STATE_PATH
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def mark_sd_recovery_pending(*, note: str = "", path: Path | None = None) -> dict[str, Any]:
    existing = load_sd_recovery_state(path) or {}
    payload = {
        "pending": True,
        "marked_at": _timestamp(),
        "note": note,
        "cleared_at": None,
        "clear_note": None,
        "previous": existing if existing else None,
    }
    return save_sd_recovery_state(payload, path)


def clear_sd_recovery_pending(*, note: str = "", path: Path | None = None) -> dict[str, Any]:
    existing = load_sd_recovery_state(path) or {}
    payload = {
        "pending": False,
        "marked_at": existing.get("marked_at"),
        "note": existing.get("note", ""),
        "cleared_at": _timestamp(),
        "clear_note": note,
        "previous": existing if existing else None,
    }
    return save_sd_recovery_state(payload, path)


def pending_sd_recovery_reason(path: Path | None = None) -> str | None:
    payload = load_sd_recovery_state(path)
    if not payload or not payload.get("pending"):
        return None
    note = str(payload.get("note") or "").strip()
    marked_at = str(payload.get("marked_at") or "").strip()
    suffix = []
    if marked_at:
        suffix.append(f"marked_at={marked_at}")
    if note:
        suffix.append(f"note={note}")
    detail = ", ".join(suffix)
    if detail:
        detail = f" ({detail})"
    return (
        "sd recovery state is still pending; remove the SD card and power-cycle once "
        f"before any new serial upload or live smoke{detail}"
    )
