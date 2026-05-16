from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.page_event_oracle_probe import probe_hmi_tft  # noqa: E402


CASE_ROOT = Path(r"C:\Users\SinYu\Desktop\case_for_codex")
DEFAULT_LEFT_HMI = CASE_ROOT / "case_49_audio" / "official_wiki" / "source_raw.HMI"
DEFAULT_LEFT_TFT = CASE_ROOT / "case_49_audio" / "official_compile" / "source_raw.run"
DEFAULT_RIGHT_REPORT = (
    REPO_ROOT
    / "reverse_usarthmi"
    / "event_demo_post_primary_probe_20260515"
    / "page_event_oracle_probe_2026-05-15.json"
)


@dataclass(frozen=True)
class PostPrimaryEvidence:
    label: str
    hmi: str | None
    tft: str | None
    model: str | None
    editor_version: str | None
    diagnosis: dict[str, Any]
    post_primary: dict[str, Any]
    live_outcome: dict[str, Any] | None

    @property
    def descriptor(self) -> dict[str, Any] | None:
        descriptors = self.post_primary.get("descriptors") or []
        return descriptors[0] if descriptors else None


def build_post_primary_diff(
    *,
    left_report: Path | None = None,
    right_report: Path | None = DEFAULT_RIGHT_REPORT,
    left_hmi: Path | None = DEFAULT_LEFT_HMI,
    left_tft: Path | None = DEFAULT_LEFT_TFT,
    right_hmi: Path | None = None,
    right_tft: Path | None = None,
    left_label: str = "official_case49_audio",
    right_label: str = "generated_event_demo_force_post_primary",
) -> dict[str, Any]:
    left = _load_evidence(
        label=left_label,
        report_path=left_report,
        hmi_path=left_hmi,
        tft_path=left_tft,
        force_post_primary_page_load=False,
    )
    right = _load_evidence(
        label=right_label,
        report_path=right_report,
        hmi_path=right_hmi,
        tft_path=right_tft,
    )
    comparison = _compare_evidence(left, right)
    return {
        "source": "page_event_post_primary_diff",
        "left": _evidence_summary(left),
        "right": _evidence_summary(right),
        "comparison": comparison,
        "decision": _decision(comparison, left, right),
    }


def _load_evidence(
    *,
    label: str,
    report_path: Path | None,
    hmi_path: Path | None,
    tft_path: Path | None,
    force_post_primary_page_load: bool | None = None,
) -> PostPrimaryEvidence:
    report: dict[str, Any] | None = None
    if report_path is not None and report_path.exists():
        report = _load_json(report_path)
        hmi_path = Path(report["hmi"]) if report.get("hmi") and hmi_path is None else hmi_path
        tft_path = Path(report["tft"]) if report.get("tft") and tft_path is None else tft_path
        post_primary = report.get("post_primary_page_event") or {}
        if force_post_primary_page_load is None:
            force_post_primary_page_load = bool(post_primary.get("force_post_primary_page_load"))

    if hmi_path is not None and tft_path is not None and hmi_path.exists() and tft_path.exists():
        report = probe_hmi_tft(
            hmi_path,
            tft_path,
            force_post_primary_page_load=bool(force_post_primary_page_load),
        )
    if report is None:
        raise FileNotFoundError(
            f"Unable to load post-primary evidence for {label!r}: "
            "provide either a report path or an HMI/TFT pair."
        )

    return PostPrimaryEvidence(
        label=label,
        hmi=report.get("hmi"),
        tft=report.get("tft"),
        model=report.get("model"),
        editor_version=report.get("editor_version"),
        diagnosis=report.get("diagnosis") or {},
        post_primary=report.get("post_primary_page_event") or {},
        live_outcome=_load_sibling_live_outcome(report_path),
    )


def _load_sibling_live_outcome(report_path: Path | None) -> dict[str, Any] | None:
    if report_path is None:
        return None
    live_reports = sorted(report_path.parent.glob("live_*2026-05-15.json"))
    for live_report in live_reports:
        try:
            data = _load_json(live_report)
        except (OSError, json.JSONDecodeError):
            continue
        return {
            "source": _relative_path(live_report),
            "probe": data.get("probe"),
            "purpose": data.get("purpose"),
            "checksum_valid": (data.get("build") or {}).get("checksum_valid"),
            "post_primary_page_event_found_by_probe": (
                data.get("build") or {}
            ).get("post_primary_page_event_found_by_probe"),
            "upload": data.get("upload"),
            "restore_attempt": data.get("restore_attempt"),
            "conclusion": data.get("conclusion"),
        }
    return None


def _compare_evidence(left: PostPrimaryEvidence, right: PostPrimaryEvidence) -> dict[str, Any]:
    left_descriptor = left.descriptor
    right_descriptor = right.descriptor
    left_items = left.post_primary.get("items") or []
    right_items = right.post_primary.get("items") or []
    left_payload_hash = _payload_hash(left_descriptor)
    right_payload_hash = _payload_hash(right_descriptor)
    context_before_common_suffix = _common_suffix_report(
        (left_descriptor or {}).get("context_before_hex"),
        (right_descriptor or {}).get("context_before_hex"),
    )
    context_after_common_prefix = _common_prefix_report(
        (left_descriptor or {}).get("context_after_hex"),
        (right_descriptor or {}).get("context_after_hex"),
    )
    context_after_common_prefix_words = _u32_word_entries(
        context_after_common_prefix.get("hex")
    )
    return {
        "both_have_descriptor": left_descriptor is not None and right_descriptor is not None,
        "same_payload_sha256": (
            left_payload_hash is not None
            and right_payload_hash is not None
            and left_payload_hash == right_payload_hash
        ),
        "left_payload_sha256": left_payload_hash,
        "right_payload_sha256": right_payload_hash,
        "length_delta_right_minus_left": _descriptor_int(right_descriptor, "length")
        - _descriptor_int(left_descriptor, "length"),
        "offset_delta_right_minus_left": _descriptor_int(right_descriptor, "offset")
        - _descriptor_int(left_descriptor, "offset"),
        "item_count_delta_right_minus_left": len(right_items) - len(left_items),
        "first_executable_offset_delta_right_minus_left": _descriptor_optional_delta(
            left_descriptor,
            right_descriptor,
            "first_executable_offset",
        ),
        "item_signatures_equal": _item_signature(left_items) == _item_signature(right_items),
        "left_item_signature": _item_signature(left_items),
        "right_item_signature": _item_signature(right_items),
        "direct_reference_counts": {
            "left": _direct_reference_counts(left_descriptor),
            "right": _direct_reference_counts(right_descriptor),
        },
        "context_before_common_suffix": context_before_common_suffix,
        "context_before_common_suffix_words": _u32_word_entries(
            context_before_common_suffix.get("hex")
        ),
        "context_after_common_prefix": context_after_common_prefix,
        "context_after_common_prefix_words": context_after_common_prefix_words,
        "context_after_common_prefix_word_count": len(context_after_common_prefix_words),
        "shared_adjacent_context_candidate": context_after_common_prefix["length"] >= 16,
        "diagnosis_paths": {
            "left": left.diagnosis.get("scheduler_path"),
            "right": right.diagnosis.get("scheduler_path"),
        },
    }


def _evidence_summary(evidence: PostPrimaryEvidence) -> dict[str, Any]:
    descriptor = evidence.descriptor or {}
    return {
        "label": evidence.label,
        "hmi": evidence.hmi,
        "tft": evidence.tft,
        "model": evidence.model,
        "editor_version": evidence.editor_version,
        "scheduler_path": evidence.diagnosis.get("scheduler_path"),
        "post_primary_page_event": {
            "force_post_primary_page_load": evidence.post_primary.get(
                "force_post_primary_page_load"
            ),
            "length": evidence.post_primary.get("length"),
            "matches": evidence.post_primary.get("matches", []),
            "descriptor": descriptor,
            "items": evidence.post_primary.get("items", []),
        },
        "live_outcome": evidence.live_outcome,
    }


def _decision(
    comparison: dict[str, Any],
    left: PostPrimaryEvidence,
    right: PostPrimaryEvidence,
) -> dict[str, Any]:
    notes: list[str] = []
    if not comparison["both_have_descriptor"]:
        notes.append("One side lacks a post-primary descriptor; collect or regenerate that oracle first.")
    if not comparison["same_payload_sha256"]:
        notes.append("Payload is not byte-for-byte compatible with the official post-primary oracle.")
    if comparison["direct_reference_counts"]["left"] == {"table_start": 0, "first_executable": 0}:
        notes.append("The official descriptor is not referenced by simple u32 table-start fields.")
    if right.live_outcome and right.live_outcome.get("conclusion"):
        notes.append("The generated force-post-primary probe has live negative evidence.")
    if right.diagnosis.get("scheduler_path") == "post_primary_page_event":
        notes.append("Matching the post-primary payload location is not enough to prove safe scheduling.")
    if comparison.get("shared_adjacent_context_candidate"):
        notes.append(
            "Both descriptors share a descriptor-adjacent word tail; treat it as a scheduler-record candidate."
        )

    return {
        "safe_to_burn_more_force_post_primary": False,
        "recommended_next_action": (
            "Diff the descriptor-adjacent bytes and recover the surrounding scheduler record shape "
            "from a minimal official two-page/page-load oracle before another live burn."
        ),
        "notes": notes,
    }


def _item_signature(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    signature = []
    for item in items:
        signature.append(
            {
                "kind": item.get("kind"),
                "command": item.get("command"),
                "name": item.get("name"),
                "operator": item.get("operator"),
                "value": item.get("value"),
                "args": item.get("args"),
                "length": item.get("length"),
                "payload_hex": item.get("payload_hex"),
            }
        )
    return signature


def _direct_reference_counts(descriptor: dict[str, Any] | None) -> dict[str, int]:
    references = (descriptor or {}).get("references") or {}
    return {
        "table_start": len(references.get("table_start") or []),
        "first_executable": len(references.get("first_executable") or []),
    }


def _payload_hash(descriptor: dict[str, Any] | None) -> str | None:
    return (descriptor or {}).get("payload_sha256")


def _descriptor_int(descriptor: dict[str, Any] | None, key: str) -> int:
    value = (descriptor or {}).get(key)
    return int(value) if value is not None else 0


def _descriptor_optional_delta(
    left: dict[str, Any] | None,
    right: dict[str, Any] | None,
    key: str,
) -> int | None:
    left_value = (left or {}).get(key)
    right_value = (right or {}).get(key)
    if left_value is None or right_value is None:
        return None
    return int(right_value) - int(left_value)


def _common_prefix_report(left_hex: str | None, right_hex: str | None) -> dict[str, Any]:
    left = _hex_to_bytes(left_hex)
    right = _hex_to_bytes(right_hex)
    length = 0
    for left_byte, right_byte in zip(left, right):
        if left_byte != right_byte:
            break
        length += 1
    return {"length": length, "hex": left[:length].hex(" ")}


def _common_suffix_report(left_hex: str | None, right_hex: str | None) -> dict[str, Any]:
    left = _hex_to_bytes(left_hex)
    right = _hex_to_bytes(right_hex)
    length = 0
    for left_byte, right_byte in zip(reversed(left), reversed(right)):
        if left_byte != right_byte:
            break
        length += 1
    suffix = left[len(left) - length :] if length else b""
    return {"length": length, "hex": suffix.hex(" ")}


def _u32_word_entries(hex_text: str | None) -> list[dict[str, Any]]:
    data = _hex_to_bytes(hex_text)
    entries = []
    for offset in range(0, len(data) - (len(data) % 4), 4):
        raw = data[offset : offset + 4]
        value = int.from_bytes(raw, byteorder="little")
        entries.append(
            {
                "offset": offset,
                "offset_hex": f"0x{offset:X}",
                "u32": value,
                "u32_hex": f"0x{value:08X}",
                "raw_hex": raw.hex(" "),
            }
        )
    return entries


def _hex_to_bytes(text: str | None) -> bytes:
    if not text:
        return b""
    try:
        return bytes.fromhex(text)
    except ValueError:
        return b""


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Diff official and generated post-primary page-event descriptors."
    )
    parser.add_argument("--left-report", type=Path)
    parser.add_argument("--right-report", type=Path, default=DEFAULT_RIGHT_REPORT)
    parser.add_argument("--left-hmi", type=Path, default=DEFAULT_LEFT_HMI)
    parser.add_argument("--left-tft", type=Path, default=DEFAULT_LEFT_TFT)
    parser.add_argument("--right-hmi", type=Path)
    parser.add_argument("--right-tft", type=Path)
    parser.add_argument("--left-label", default="official_case49_audio")
    parser.add_argument("--right-label", default="generated_event_demo_force_post_primary")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args(argv)

    report = build_post_primary_diff(
        left_report=args.left_report,
        right_report=args.right_report,
        left_hmi=args.left_hmi,
        left_tft=args.left_tft,
        right_hmi=args.right_hmi,
        right_tft=args.right_tft,
        left_label=args.left_label,
        right_label=args.right_label,
    )
    text = json.dumps(report, ensure_ascii=False, indent=None if args.compact else 2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
