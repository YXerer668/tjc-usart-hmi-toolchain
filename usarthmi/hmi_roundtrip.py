from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .editor import build_scene
from .hmi_import import import_hmi_project
from .hmi_inspect import HMIInspection, PABlockSummary, inspect_hmi
from .scene import load_scene
from .tft_event_index import inspect_tft_event_index
from .widgets import CURRENT_TARGET, WidgetSupport, WidgetWriter, get_widget_type_info


ROUNDTRIP_NOT_CLAIMED = [
    "TFT rebuild equivalence",
    "official event scheduler equivalence",
    "hardware runtime proof",
    "byte-perfect roundtrip unless summary.byte_perfect is true",
    "complete resource/font reconstruction",
]


def check_hmi_roundtrip(
    hmi_path: str | Path,
    out_dir: str | Path,
    *,
    target: str = CURRENT_TARGET,
    overwrite: bool = False,
    source_tft: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(hmi_path).resolve()
    output_dir = Path(out_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "roundtrip_report.json"
    source_inspect_path = output_dir / "source.inspect.json"
    regenerated_inspect_path = output_dir / "regenerated.inspect.json"
    if report_path.exists() and not overwrite:
        raise FileExistsError(f"Roundtrip output already exists: {report_path}")

    source_raw = source.read_bytes()
    source_sha = sha256(source_raw).hexdigest()
    source_inspection = inspect_hmi(source)
    _write_json(source_inspect_path, source_inspection.to_dict())

    import_result = import_hmi_project(source, output_dir, target=target, overwrite=overwrite)
    scene_path = Path(import_result["scene_path"])
    scene = load_scene(scene_path)
    scene.project["drop_seed_objects"] = True
    build_dir = output_dir / "regenerated"
    build_result = build_scene(scene, source, build_dir)
    regenerated_hmi = Path(build_result["output_hmi"])
    regenerated_raw = regenerated_hmi.read_bytes()
    regenerated_sha = sha256(regenerated_raw).hexdigest()
    regenerated_inspection = inspect_hmi(regenerated_hmi)
    _write_json(regenerated_inspect_path, regenerated_inspection.to_dict())
    event_index_report = None
    event_index_path = output_dir / "event_index.inspect.json"
    if source_tft is not None:
        event_index_report = inspect_tft_event_index(source, source_tft, out_path=event_index_path)

    comparison = _compare_roundtrip(source_inspection, regenerated_inspection, scene)
    byte_perfect = source_raw == regenerated_raw
    blocking = _blocking_issues(byte_perfect, comparison, event_index_report=event_index_report)
    report = {
        "schema_version": 1,
        "input": {
            "hmi_path": str(source),
            "sha256": source_sha,
            "target": target,
        },
        "outputs": {
            "source_inspect_json": str(source_inspect_path),
            "scene_imported_json": str(scene_path),
            "import_report_json": import_result["import_report"],
            "agent_context_json": import_result["agent_context"],
            "regenerated_hmi": str(regenerated_hmi),
            "regenerated_inspect_json": str(regenerated_inspect_path),
            "build_manifest_json": str(build_dir / "manifest.json"),
            "roundtrip_report_json": str(report_path),
            "event_index_json": str(event_index_path) if event_index_report is not None else None,
        },
        "summary": {
            "byte_perfect": byte_perfect,
            "source_sha256": source_sha,
            "regenerated_sha256": regenerated_sha,
            "source_bytes": len(source_raw),
            "regenerated_bytes": len(regenerated_raw),
            "pages_source": len(source_inspection.page_names),
            "pages_regenerated": len(regenerated_inspection.page_names),
            "objects_source": comparison["counts"]["source_objects"],
            "objects_regenerated": comparison["counts"]["regenerated_objects"],
            "preserved_objects": len(comparison["preserved"]["objects"]),
            "changed_objects": len(comparison["changed"]["objects"]),
            "approximated_objects": len(comparison["approximated"]),
            "placeholder_objects": len(comparison["placeholders"]),
            "dropped_objects": len(comparison["dropped"]),
            "added_objects": len(comparison["added"]),
            "source_event_script_count": comparison["counts"]["source_event_scripts"],
            "regenerated_event_script_count": comparison["counts"]["regenerated_event_scripts"],
            "source_resource_count": comparison["counts"]["source_resources"],
            "regenerated_resource_count": comparison["counts"]["regenerated_resources"],
            "event_index_source_tft_available": event_index_report is not None,
            "event_index_scheduler_path": (
                event_index_report.get("summary", {}).get("scheduler_path")
                if event_index_report is not None
                else None
            ),
            "event_index_blocking_gaps": (
                len(event_index_report.get("blocking_gaps", []))
                if event_index_report is not None
                else None
            ),
            "blocking_issues": len(blocking),
            "safe_to_flash": False,
        },
        **comparison,
        "event_index_status": _event_index_status(event_index_report),
        "blocking_byte_perfect": blocking,
        "safe_to_flash": False,
        "not_claimed": list(ROUNDTRIP_NOT_CLAIMED),
    }
    _write_json(report_path, report)
    return report


def _compare_roundtrip(
    source: HMIInspection,
    regenerated: HMIInspection,
    scene,
) -> dict[str, Any]:
    source_objects = _object_summaries(source)
    regenerated_objects = _object_summaries(regenerated)
    source_by_name = _objects_by_name(source_objects)
    regenerated_by_name = _objects_by_name(regenerated_objects)
    preserved: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    added: list[dict[str, Any]] = []

    for name in sorted(source_by_name):
        source_item = source_by_name[name]
        regenerated_item = regenerated_by_name.get(name)
        if regenerated_item is None:
            dropped.append(source_item)
            continue
        deltas = _object_deltas(source_item, regenerated_item)
        if deltas:
            changed.append({"object": name, "source": source_item, "regenerated": regenerated_item, "fields": deltas})
        else:
            preserved.append(source_item)
    for name in sorted(set(regenerated_by_name) - set(source_by_name)):
        added.append(regenerated_by_name[name])

    source_resources = _resource_summaries(source)
    regenerated_resources = _resource_summaries(regenerated)
    resource_comparison = _compare_resources(source_resources, regenerated_resources)
    scene_status = _scene_import_status(scene)
    return {
        "counts": {
            "source_objects": len(source_objects),
            "regenerated_objects": len(regenerated_objects),
            "source_event_scripts": _event_script_count(source),
            "regenerated_event_scripts": _event_script_count(regenerated),
            "source_resources": len(source_resources),
            "regenerated_resources": len(regenerated_resources),
        },
        "preserved": {
            "pages": sorted(set(source.page_names) & set(regenerated.page_names)),
            "objects": preserved,
            "resources": resource_comparison["preserved"],
        },
        "changed": {
            "objects": changed,
            "resources": resource_comparison["changed"],
        },
        "approximated": scene_status["approximated"],
        "placeholders": scene_status["placeholders"],
        "dropped": dropped,
        "added": added,
        "resources": resource_comparison,
        "events": {
            "source_script_count": _event_script_count(source),
            "regenerated_script_count": _event_script_count(regenerated),
            "status": "preserved-count" if _event_script_count(source) == _event_script_count(regenerated) else "changed-count",
        },
    }


def _object_summaries(inspection: HMIInspection) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for block in inspection.pa_blocks:
        if block.type_code == "y":
            continue
        name = block.objname or f"{block.attr_name}:{block.index}"
        result.append(
            {
                "name": name,
                "type_code": block.type_code,
                "index": block.index,
                "fields": _stable_fields(block),
                "event_script_count": len(block.event_scripts),
            }
        )
    return sorted(result, key=lambda item: (str(item["name"]), int(item["index"])))


def _objects_by_name(objects: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    counts = Counter(str(item["name"]) for item in objects)
    result: dict[str, dict[str, Any]] = {}
    for item in objects:
        name = str(item["name"])
        key = name if counts[name] == 1 else f"{name}#{item['index']}"
        result[key] = item
    return result


def _stable_fields(block: PABlockSummary) -> dict[str, Any]:
    keys = ("x", "y", "w", "h", "id", "val", "txt", "pic", "picc", "font", "bco", "pco")
    return {key: block.fields[key] for key in keys if key in block.fields}


def _object_deltas(source: dict[str, Any], regenerated: dict[str, Any]) -> list[dict[str, Any]]:
    deltas: list[dict[str, Any]] = []
    if source.get("type_code") != regenerated.get("type_code"):
        deltas.append({"field": "type_code", "source": source.get("type_code"), "regenerated": regenerated.get("type_code")})
    keys = sorted(set(source.get("fields", {})) | set(regenerated.get("fields", {})))
    for key in keys:
        left = source.get("fields", {}).get(key)
        right = regenerated.get("fields", {}).get(key)
        if left != right:
            deltas.append({"field": key, "source": left, "regenerated": right})
    if source.get("event_script_count") != regenerated.get("event_script_count"):
        deltas.append(
            {
                "field": "event_script_count",
                "source": source.get("event_script_count"),
                "regenerated": regenerated.get("event_script_count"),
            }
        )
    return deltas


def _resource_summaries(inspection: HMIInspection) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    for entry in inspection.entries:
        lower = entry.name.lower()
        if lower == "program.s" or lower.endswith(".pa"):
            continue
        resources.append(
            {
                "name": entry.name,
                "length": entry.length,
                "field3": entry.field3,
                "in_file": entry.in_file,
            }
        )
    return sorted(resources, key=lambda item: str(item["name"]))


def _compare_resources(source: list[dict[str, Any]], regenerated: list[dict[str, Any]]) -> dict[str, Any]:
    source_by_name = {str(item["name"]): item for item in source}
    regenerated_by_name = {str(item["name"]): item for item in regenerated}
    preserved: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    added: list[dict[str, Any]] = []
    for name in sorted(source_by_name):
        source_item = source_by_name[name]
        regenerated_item = regenerated_by_name.get(name)
        if regenerated_item is None:
            dropped.append(source_item)
        elif source_item == regenerated_item:
            preserved.append(source_item)
        else:
            changed.append({"name": name, "source": source_item, "regenerated": regenerated_item})
    for name in sorted(set(regenerated_by_name) - set(source_by_name)):
        added.append(regenerated_by_name[name])
    return {
        "source": source,
        "regenerated": regenerated,
        "preserved": preserved,
        "changed": changed,
        "dropped": dropped,
        "added": added,
    }


def _scene_import_status(scene) -> dict[str, list[dict[str, Any]]]:
    approximated: list[dict[str, Any]] = []
    placeholders: list[dict[str, Any]] = []
    for page in scene.pages:
        for widget in page.widgets:
            binding = widget.bindings.get("hmi_import", {})
            item = {
                "page": page.id,
                "object": widget.id,
                "type": widget.type,
                "source_type_code": binding.get("source_type_code"),
            }
            if binding.get("placeholder"):
                placeholders.append({**item, "reason": "unknown source type imported as visible placeholder"})
                continue
            info = get_widget_type_info(widget.type)
            if (
                info is not None
                and info.writer == WidgetWriter.FIXTURE
                and (info.build_scope is not None or info.can_build_tft is not None)
            ):
                approximated.append(
                    {
                        **item,
                        "fixture_case": info.fixture_case,
                        "reason": "fixture-backed limited-claim widget; byte-perfect roundtrip and arbitrary TFT synthesis are not claimed",
                    }
                )
    return {"approximated": approximated, "placeholders": placeholders}


def _event_script_count(inspection: HMIInspection) -> int:
    return sum(len(block.event_scripts) for block in inspection.pa_blocks)


def _event_index_status(event_index_report: dict[str, Any] | None) -> dict[str, Any]:
    if event_index_report is None:
        return {
            "source_tft_available": False,
            "scheduler_index_parsed": False,
            "reason": "Pass --source-tft with an official .tft/.run oracle to include compiled event-index evidence.",
        }
    return {
        "source_tft_available": True,
        "scheduler_index_parsed": True,
        "scheduler_path": event_index_report.get("summary", {}).get("scheduler_path"),
        "source_event_slot_count": event_index_report.get("summary", {}).get("source_event_slot_count"),
        "post_primary_page_event_match_count": event_index_report.get("summary", {}).get("post_primary_page_event_match_count"),
        "blocking_gaps": event_index_report.get("blocking_gaps", []),
        "safe_to_flash": False,
        "not_claimed": event_index_report.get("not_claimed", []),
    }


def _blocking_issues(
    byte_perfect: bool,
    comparison: dict[str, Any],
    *,
    event_index_report: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not byte_perfect:
        issues.append({"code": "HMI_BYTES_DIFFER", "message": "Regenerated HMI bytes do not match the source HMI."})
    if comparison["dropped"]:
        issues.append({"code": "DROPPED_OBJECTS", "count": len(comparison["dropped"]), "message": "One or more source objects are missing after regeneration."})
    if comparison["placeholders"]:
        issues.append({"code": "PLACEHOLDER_OBJECTS", "count": len(comparison["placeholders"]), "message": "One or more source objects were imported as placeholders."})
    if comparison["changed"]["objects"]:
        issues.append({"code": "CHANGED_OBJECTS", "count": len(comparison["changed"]["objects"]), "message": "One or more source objects changed structurally after regeneration."})
    if comparison["resources"]["dropped"] or comparison["resources"]["changed"]:
        issues.append({"code": "RESOURCE_DIFF", "message": "Resource entries are not byte/metadata identical after regeneration."})
    if comparison["events"]["status"] != "preserved-count":
        issues.append({"code": "EVENT_SCRIPT_COUNT_DIFF", "message": "Event script counts differ after regeneration."})
    if event_index_report is not None and event_index_report.get("blocking_gaps"):
        issues.append(
            {
                "code": "EVENT_INDEX_BLOCKING_GAPS",
                "count": len(event_index_report.get("blocking_gaps", [])),
                "message": "Compiled TFT event-index evidence still has scheduler or compiler blockers.",
            }
        )
    return issues


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
