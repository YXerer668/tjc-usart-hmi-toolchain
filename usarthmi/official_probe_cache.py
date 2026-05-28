from __future__ import annotations

from hashlib import sha256
import json
import shutil
import time
from pathlib import Path
from typing import Any, Iterable


OFFICIAL_LOWLEVEL_CACHE_SCHEMA_VERSION = 1
OFFICIAL_LOWLEVEL_CACHE_NAMESPACE = "official_lowlevel_probe"
DEFAULT_OFFICIAL_LOWLEVEL_CACHE_ROOT = (
    Path(__file__).resolve().parents[1] / "artifacts_cache" / OFFICIAL_LOWLEVEL_CACHE_NAMESPACE
)


def stable_json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_jsonable(payload: Any) -> str:
    return sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def compute_file_sha256(path: str | Path) -> str:
    file_path = Path(path)
    last_error: Exception | None = None
    for _ in range(3):
        try:
            return sha256(file_path.read_bytes()).hexdigest()
        except (OSError, PermissionError) as exc:
            last_error = exc
            time.sleep(0.2)
    stat = file_path.stat()
    fallback = f"stat:{stat.st_size}:{stat.st_mtime_ns}:{last_error!r}".encode("utf-8")
    return sha256(fallback).hexdigest()


def fingerprint_source_files(paths: Iterable[str | Path]) -> dict[str, Any]:
    entries = []
    for raw_path in paths:
        path = Path(raw_path).resolve()
        entries.append(
            {
                "path": str(path),
                "sha256": compute_file_sha256(path),
            }
        )
    return {
        "files": entries,
        "sha256": sha256_jsonable(entries),
    }


def build_official_lowlevel_probe_request(
    *,
    hmi_path: str | Path,
    harness_path: str | Path,
    run_compile: bool,
    patch_spec_path: str | Path | None = None,
    patch_spec_payload: Any | None = None,
    source_version_paths: Iterable[str | Path] | None = None,
    request_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    hmi = Path(hmi_path).resolve()
    harness = Path(harness_path).resolve()
    tool_version = fingerprint_source_files(source_version_paths or [])
    patch_spec = _build_patch_spec_fingerprint(
        patch_spec_path=patch_spec_path,
        patch_spec_payload=patch_spec_payload,
    )
    probe_command = {
        "mode": "official_hmi_lowlevel_probe",
        "run_compile": bool(run_compile),
        "logical_steps": ["open_lowlevel", "compile_lowlevel"] if run_compile else ["open_lowlevel"],
    }
    request = {
        "schema_version": OFFICIAL_LOWLEVEL_CACHE_SCHEMA_VERSION,
        "cache_namespace": OFFICIAL_LOWLEVEL_CACHE_NAMESPACE,
        "input_hmi": {
            "path": str(hmi),
            "sha256": compute_file_sha256(hmi),
        },
        "patch_spec": patch_spec,
        "probe_command": probe_command,
        "probe_command_sha256": sha256_jsonable(probe_command),
        "tool_version": tool_version,
        "official_probe_version": {
            "resolved_harness_path": str(harness),
            "resolved_harness_sha256": compute_file_sha256(harness),
            "sha256": sha256_jsonable(
                {
                    "path": str(harness),
                    "sha256": compute_file_sha256(harness),
                }
            ),
        },
        "request_context": request_context or {},
    }
    request_sha256 = sha256_jsonable(request)
    request["request_sha256"] = request_sha256
    request["cache_key"] = request_sha256
    return request


def resolve_official_lowlevel_cache_root(cache_root: str | Path | None = None) -> Path:
    root = Path(cache_root).resolve() if cache_root is not None else DEFAULT_OFFICIAL_LOWLEVEL_CACHE_ROOT.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def official_lowlevel_cache_dir(request: dict[str, Any], *, cache_root: str | Path | None = None) -> Path:
    return resolve_official_lowlevel_cache_root(cache_root) / str(request["cache_key"])


def materialize_cached_official_lowlevel_probe(
    request: dict[str, Any],
    *,
    out_dir: str | Path,
    hmi_stem: str,
    run_compile: bool,
    cache_root: str | Path | None = None,
) -> dict[str, Any] | None:
    cached = load_cached_official_lowlevel_probe(
        request,
        run_compile=run_compile,
        cache_root=cache_root,
    )
    if cached is None:
        return None

    out_path = Path(out_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)
    local_paths = local_official_lowlevel_probe_paths(out_path, hmi_stem=hmi_stem, run_compile=run_compile)
    canonical_paths = cached["canonical_paths"]
    _copy_if_exists(canonical_paths["open_lowlevel_result_json"], local_paths["open_lowlevel_result_json"])
    if run_compile:
        _copy_if_exists(canonical_paths["compile_lowlevel_result_json"], local_paths["compile_lowlevel_result_json"])
        _copy_if_exists(canonical_paths["compiled_tft"], local_paths["compiled_tft"])
        _copy_if_exists(canonical_paths["compile_event_index_json"], local_paths["compile_event_index_json"])
    _copy_if_exists(cached["manifest_path"], local_paths["cache_manifest_json"])

    materialized = rewrite_official_lowlevel_report_paths(
        cached["report"],
        request=request,
        report_path=local_paths["report_json"],
        local_paths=local_paths,
        cache_dir=cached["cache_dir"],
        cache_manifest_path=local_paths["cache_manifest_json"],
        cache_hit=True,
        cache_miss=False,
    )
    local_paths["report_json"].write_text(json.dumps(materialized, ensure_ascii=False, indent=2), encoding="utf-8")
    return materialized


def load_cached_official_lowlevel_probe(
    request: dict[str, Any],
    *,
    run_compile: bool,
    cache_root: str | Path | None = None,
) -> dict[str, Any] | None:
    cache_dir = official_lowlevel_cache_dir(request, cache_root=cache_root)
    manifest_path = cache_dir / "cache_manifest.json"
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if manifest.get("schema_version") != OFFICIAL_LOWLEVEL_CACHE_SCHEMA_VERSION:
        return None
    if manifest.get("cache_namespace") != OFFICIAL_LOWLEVEL_CACHE_NAMESPACE:
        return None
    if manifest.get("request_sha256") != request.get("request_sha256"):
        return None
    canonical_paths = canonical_official_lowlevel_cache_paths(cache_dir)
    artifacts = manifest.get("artifacts") or {}
    required_keys = {"report_json", "open_lowlevel_result_json"}
    if run_compile:
        required_keys.update({"compile_lowlevel_result_json", "compiled_tft"})
    for artifact_key in required_keys:
        metadata = artifacts.get(artifact_key)
        if not _validate_cached_artifact(cache_dir, metadata):
            return None
    optional_event_index = artifacts.get("compile_event_index_json")
    if optional_event_index and optional_event_index.get("required"):
        if not _validate_cached_artifact(cache_dir, optional_event_index):
            return None
    report_path = canonical_paths["report_json"]
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if report.get("probe_request_sha256") != request.get("request_sha256"):
        return None
    return {
        "cache_dir": cache_dir,
        "manifest_path": manifest_path,
        "manifest": manifest,
        "canonical_paths": canonical_paths,
        "report": report,
    }


def store_cached_official_lowlevel_probe(
    request: dict[str, Any],
    *,
    cache_root: str | Path | None = None,
    report: dict[str, Any],
    artifact_sources: dict[str, str | Path | None],
    run_compile: bool,
) -> dict[str, Any]:
    cache_dir = official_lowlevel_cache_dir(request, cache_root=cache_root)
    cache_dir.mkdir(parents=True, exist_ok=True)
    canonical_paths = canonical_official_lowlevel_cache_paths(cache_dir)
    for artifact_key in ("open_lowlevel_result_json", "compile_lowlevel_result_json", "compiled_tft", "compile_event_index_json"):
        source = artifact_sources.get(artifact_key)
        target = canonical_paths[artifact_key]
        if source is None:
            continue
        source_path = Path(source)
        if not source_path.exists():
            continue
        _copy_if_exists(source_path, target)

    canonical_report = rewrite_official_lowlevel_report_paths(
        report,
        request=request,
        report_path=canonical_paths["report_json"],
        local_paths=canonical_paths,
        cache_dir=cache_dir,
        cache_manifest_path=None,
        cache_hit=False,
        cache_miss=True,
    )
    canonical_paths["report_json"].write_text(json.dumps(canonical_report, ensure_ascii=False, indent=2), encoding="utf-8")

    artifacts = {
        "report_json": _artifact_metadata(canonical_paths["report_json"], required=True),
        "open_lowlevel_result_json": _artifact_metadata(canonical_paths["open_lowlevel_result_json"], required=True),
        "compile_lowlevel_result_json": _artifact_metadata(
            canonical_paths["compile_lowlevel_result_json"],
            required=run_compile,
        ),
        "compiled_tft": _artifact_metadata(canonical_paths["compiled_tft"], required=run_compile),
        "compile_event_index_json": _artifact_metadata(canonical_paths["compile_event_index_json"], required=False),
    }
    manifest = {
        "schema_version": OFFICIAL_LOWLEVEL_CACHE_SCHEMA_VERSION,
        "cache_namespace": OFFICIAL_LOWLEVEL_CACHE_NAMESPACE,
        "cache_key": request["cache_key"],
        "request_sha256": request["request_sha256"],
        "request": request,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "artifacts": artifacts,
    }
    manifest_path = cache_dir / "cache_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "cache_dir": cache_dir,
        "manifest_path": manifest_path,
        "canonical_paths": canonical_paths,
    }


def rewrite_official_lowlevel_report_paths(
    report: dict[str, Any],
    *,
    request: dict[str, Any],
    report_path: Path,
    local_paths: dict[str, Path | None],
    cache_dir: Path,
    cache_manifest_path: Path | None,
    cache_hit: bool,
    cache_miss: bool,
) -> dict[str, Any]:
    rewritten = json.loads(json.dumps(report))
    rewritten["report_json"] = str(report_path)
    rewritten["input_hmi_sha256"] = request["input_hmi"]["sha256"]
    rewritten["patch_spec_sha256"] = request["patch_spec"]["sha256"]
    rewritten["probe_request_sha256"] = request["request_sha256"]
    rewritten["probe_command_sha256"] = request["probe_command_sha256"]
    rewritten["cache_key"] = request["cache_key"]
    rewritten["tool_version_sha256"] = request["tool_version"]["sha256"]
    rewritten["official_probe_version_sha256"] = request["official_probe_version"]["sha256"]
    rewritten["cache_hit"] = cache_hit
    rewritten["cache_miss"] = cache_miss
    rewritten["cache"] = {
        "schema_version": OFFICIAL_LOWLEVEL_CACHE_SCHEMA_VERSION,
        "cache_namespace": OFFICIAL_LOWLEVEL_CACHE_NAMESPACE,
        "cache_key": request["cache_key"],
        "request_sha256": request["request_sha256"],
        "cache_dir": str(cache_dir),
        "cache_manifest_json": None if cache_manifest_path is None else str(cache_manifest_path),
    }
    rewritten["open_lowlevel"]["result_json"] = str(local_paths["open_lowlevel_result_json"])
    if rewritten.get("compile_lowlevel") is not None:
        compile_payload = dict(rewritten["compile_lowlevel"])
        compile_payload["result_json"] = (
            None if local_paths["compile_lowlevel_result_json"] is None else str(local_paths["compile_lowlevel_result_json"])
        )
        compile_payload["compiled_tft"] = None if local_paths["compiled_tft"] is None else str(local_paths["compiled_tft"])
        compile_payload["event_index_json"] = (
            None if local_paths["compile_event_index_json"] is None or not local_paths["compile_event_index_json"].exists() else str(local_paths["compile_event_index_json"])
        )
        rewritten["compile_lowlevel"] = compile_payload
    return rewritten


def local_official_lowlevel_probe_paths(out_dir: str | Path, *, hmi_stem: str, run_compile: bool) -> dict[str, Path | None]:
    root = Path(out_dir).resolve()
    return {
        "report_json": root / f"{hmi_stem}.official_lowlevel.json",
        "open_lowlevel_result_json": root / "open_lowlevel.result.json",
        "compile_lowlevel_result_json": root / "compile_lowlevel.result.json" if run_compile else None,
        "compiled_tft": root / f"{hmi_stem}.lowlevel.tft" if run_compile else None,
        "compile_event_index_json": root / "compile_lowlevel.event_index.json" if run_compile else None,
        # Keep the local probe-side filename short enough for deep fixture-corpus
        # paths on Windows; callers can still remap or copy it outward under the
        # longer public-facing name when needed.
        "cache_manifest_json": root / "cache_manifest.json",
    }


def canonical_official_lowlevel_cache_paths(cache_dir: str | Path) -> dict[str, Path]:
    root = Path(cache_dir).resolve()
    return {
        "report_json": root / "capability_result.json",
        "open_lowlevel_result_json": root / "open_lowlevel.result.json",
        "compile_lowlevel_result_json": root / "compile_lowlevel.result.json",
        "compiled_tft": root / "compiled.lowlevel.tft",
        "compile_event_index_json": root / "compile_lowlevel.event_index.json",
    }


def _artifact_metadata(path: Path, *, required: bool) -> dict[str, Any]:
    exists = path.exists()
    return {
        "relative_path": path.name,
        "required": required,
        "exists": exists,
        "sha256": compute_file_sha256(path) if exists else None,
        "bytes": path.stat().st_size if exists else None,
    }


def _build_patch_spec_fingerprint(
    *,
    patch_spec_path: str | Path | None,
    patch_spec_payload: Any | None,
) -> dict[str, Any]:
    if patch_spec_payload is not None:
        return {
            "source": "payload",
            "path": None,
            "sha256": sha256_jsonable(patch_spec_payload),
        }
    if patch_spec_path is not None:
        path = Path(patch_spec_path).resolve()
        return {
            "source": "path",
            "path": str(path),
            "sha256": compute_file_sha256(path),
        }
    return {
        "source": None,
        "path": None,
        "sha256": None,
    }


def _copy_if_exists(source: str | Path, target: str | Path) -> None:
    source_path = Path(source)
    target_path = Path(target)
    if not source_path.exists():
        return
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)


def _validate_cached_artifact(cache_dir: Path, metadata: dict[str, Any] | None) -> bool:
    if not metadata:
        return False
    relative_path = metadata.get("relative_path")
    if not relative_path:
        return False
    artifact_path = cache_dir / str(relative_path)
    if not artifact_path.exists():
        return False
    expected_sha256 = metadata.get("sha256")
    if expected_sha256 and compute_file_sha256(artifact_path) != expected_sha256:
        return False
    return True
