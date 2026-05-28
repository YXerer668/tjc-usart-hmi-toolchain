from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .agent_preview import generate_agent_preview
from .editor import build_scene
from .event_logic import analyze_scene_events
from .scene import load_scene
from .target_status import target_status_summary
from .widgets import CURRENT_TARGET, WidgetSupport, WidgetWriter, get_widget_type_info


EXPORT_SCHEMA_VERSION = 1
EXPORT_NOT_CLAIMED = (
    "export bundle does not upload to hardware",
    "export bundle is not proof of live runtime behavior",
    "preview output is not camera evidence",
    "output.tft is only emitted when a compatible baseline is supplied and local writer guards pass",
    "fixture-backed HMI-only widgets are not direct/native TFT rebuild support",
)


def export_scene_bundle(
    scene_path: str | Path,
    out_dir: str | Path,
    *,
    seed_hmi: str | Path | None = None,
    baseline_tft: str | Path | None = None,
    font_zi: str | Path | None = None,
    font_entry: str = "0.zi",
    target: str = CURRENT_TARGET,
) -> dict[str, Any]:
    """Create an offline compile-style export bundle without touching hardware."""
    source = Path(scene_path).resolve()
    output_dir = Path(out_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "export_report.json"
    target_status = target_status_summary()

    report: dict[str, Any] = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input": {
            "scene_path": str(source),
            "scene_sha256": _sha256_file(source),
            "seed_hmi": str(Path(seed_hmi).resolve()) if seed_hmi is not None else None,
            "baseline_tft": str(Path(baseline_tft).resolve()) if baseline_tft is not None else None,
            "font_zi": str(Path(font_zi).resolve()) if font_zi is not None else None,
            "font_entry": font_entry,
            "target": target,
        },
        "phases": {},
        "outputs": {"export_report_json": str(report_path)},
        "target_status": target_status,
        "summary": {},
        "diagnostics": [],
        "warnings": [],
        "not_claimed": list(EXPORT_NOT_CLAIMED),
        "hardware_policy": {
            "allow_upload": False,
            "allow_readback": True,
            "upload_requires_explicit_user_request": True,
            "default_port": "COM36",
        },
    }

    try:
        scene = load_scene(source)
        event_analysis = analyze_scene_events(scene)
        widgets = _scene_widget_capability_summary(scene)
        report["phases"]["validate"] = {"status": "ok"}
        report["summary"].update(
            {
                "pages": len(scene.pages),
                "widgets": sum(len(page.widgets) for page in scene.pages),
                "events": event_analysis["summary"]["event_slot_count"],
                "widget_capabilities": widgets["summary"],
                "safe_to_flash": False,
            }
        )
        report["diagnostics"].extend(event_analysis.get("diagnostics", []))
        report["warnings"].extend(widgets["warnings"])
    except Exception as exc:  # noqa: BLE001 - report should still be written for agent review.
        report["phases"]["validate"] = {"status": "failed", "error": str(exc)}
        report["summary"]["safe_to_flash"] = False
        _write_report(report_path, report)
        return report

    try:
        context = generate_agent_preview(source, output_dir, target=target)
        report["phases"]["agent_preview"] = {"status": "ok"}
        report["outputs"].update(
            {
                "preview_png": context["outputs"]["preview_png"],
                "annotated_preview_png": context["outputs"]["annotated_preview_png"],
                "agent_context_json": context["outputs"]["agent_context_json"],
                "capability_report_json": context["outputs"]["capability_report_json"],
                "editor_audit_json": context["outputs"]["editor_audit_json"],
                "target_status_json": context["outputs"]["target_status_json"],
                "build_manifest_json": context["outputs"]["build_manifest_json"],
                "diagnostics_json": context["outputs"]["diagnostics_json"],
                "event_snippets_json": context["outputs"]["event_snippets_json"],
                "scenario_template_yaml": context["outputs"]["scenario_template_yaml"],
            }
        )
        report["diagnostics"].extend(context.get("diagnostics", []))
    except Exception as exc:  # noqa: BLE001 - keep report instead of failing silently.
        report["phases"]["agent_preview"] = {"status": "failed", "error": str(exc)}

    if seed_hmi is None:
        report["phases"]["build"] = {
            "status": "skipped",
            "reason": "seed_hmi not supplied; export contains preview/agent artifacts only",
        }
        report["summary"]["hmi_built"] = False
        report["summary"]["tft_built"] = False
    else:
        try:
            build = build_scene(
                scene,
                seed_hmi,
                output_dir,
                baseline_tft=baseline_tft,
                font_zi=font_zi,
                font_entry=font_entry,
            )
            tft_built = bool(build.get("output_tft"))
            report["phases"]["build"] = {
                "status": "ok",
                "hmi_built": bool(build.get("output_hmi")),
                "tft_built": tft_built,
            }
            report["outputs"].update(
                {
                    "output_hmi": build.get("output_hmi"),
                    "output_tft": build.get("output_tft"),
                    "manifest_json": str(output_dir / "manifest.json"),
                    "build_preview_png": build.get("preview_png"),
                    "target_pa": build.get("target_pa"),
                    "target_pages": build.get("target_pages"),
                    "smoke_expect_json": (build.get("live_smoke") or {}).get("smoke_expect_json"),
                }
            )
            report["summary"]["hmi_built"] = bool(build.get("output_hmi"))
            report["summary"]["tft_built"] = tft_built
            report["summary"]["tft_checksum_valid"] = bool((build.get("tft_checksum") or {}).get("valid"))
            report["summary"]["smoke_expect_generated"] = bool((build.get("live_smoke") or {}).get("smoke_expect_json"))
            report["warnings"].extend(build.get("warnings", []))
            if not baseline_tft:
                report["warnings"].append("baseline_tft not supplied; HMI built but TFT output was intentionally skipped.")
        except Exception as exc:  # noqa: BLE001 - compile-style report should capture guarded failures.
            report["phases"]["build"] = {"status": "failed", "error": str(exc)}
            report["summary"]["hmi_built"] = (output_dir / "output.hmi").exists()
            report["summary"]["tft_built"] = (output_dir / "output.tft").exists()
            if (output_dir / "output.hmi").exists():
                report["outputs"]["output_hmi"] = str(output_dir / "output.hmi")
            if (output_dir / "output.tft").exists():
                report["outputs"]["output_tft"] = str(output_dir / "output.tft")
            report["warnings"].append(str(exc))

    report["summary"]["ok"] = _report_ok(report)
    report["summary"]["safe_to_flash"] = False
    _write_report(report_path, report)
    _inject_export_report(report)
    return report


def _scene_widget_capability_summary(scene) -> dict[str, Any]:
    summary = {"supported": 0, "pending": 0, "unsupported-current-target": 0, "unknown": 0}
    warnings: list[dict[str, Any]] = []
    for page in scene.pages:
        for widget in page.widgets:
            info = get_widget_type_info(widget.type)
            if info is None:
                summary["unknown"] += 1
                warnings.append(
                    {
                        "severity": "warning",
                        "code": "UNKNOWN_WIDGET_TYPE",
                        "page": page.id,
                        "widget": widget.id,
                        "message": f"Widget {widget.id!r} type {widget.type!r} is not registered",
                    }
                )
                continue
            summary[info.support.value] = summary.get(info.support.value, 0) + 1
            if info.support == WidgetSupport.PENDING and info.writer == WidgetWriter.FIXTURE:
                warnings.append(
                    {
                        "severity": "warning",
                        "code": "FIXTURE_BACKED_HMI_ONLY_WIDGET",
                        "page": page.id,
                        "widget": widget.id,
                        "type": widget.type,
                        "message": "Fixture-backed HMI-only widget can be exported to HMI, but direct TFT rebuild is not claimed.",
                    }
                )
    return {"summary": summary, "warnings": warnings}


def _report_ok(report: dict[str, Any]) -> bool:
    failed = [phase for phase in report["phases"].values() if phase.get("status") == "failed"]
    return not failed


def _inject_export_report(report: dict[str, Any]) -> None:
    context_path = report.get("outputs", {}).get("agent_context_json")
    if not context_path:
        return
    path = Path(context_path)
    if not path.exists():
        return
    try:
        context = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    context["export_report"] = {
        "path": report["outputs"]["export_report_json"],
        "summary": report["summary"],
        "phases": report["phases"],
        "target_status": report.get("target_status"),
        "not_claimed": list(EXPORT_NOT_CLAIMED),
    }
    path.write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()
