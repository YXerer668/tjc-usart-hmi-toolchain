from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from .official_probe_cache import (
    build_official_lowlevel_probe_request,
    local_official_lowlevel_probe_paths,
    materialize_cached_official_lowlevel_probe,
    resolve_official_lowlevel_cache_root,
    rewrite_official_lowlevel_report_paths,
    store_cached_official_lowlevel_probe,
)
from .tft_event_index import inspect_tft_event_index


DEFAULT_HARNESS = Path(r"D:\reverse\USART HMI_decompile\tools\OfficialHeadlessCompile.exe")
RUNTIME_CLEAN_HARNESS = Path(
    r"D:\reverse\USART HMI_decompile\tools\headless_debugger\harness_runtime_clean\OfficialHeadlessCompile.exe"
)
EMPTY_SHELL_OUTPUT_SIZE = 11_403_460


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the official headless low-level open/compile harness against one HMI "
            "and summarize whether it survives the official parser/compiler path."
        )
    )
    parser.add_argument("hmi", type=Path, help="Input .HMI file")
    parser.add_argument("--out-dir", type=Path, required=True, help="Directory for JSON and optional compiled TFT")
    parser.add_argument(
        "--harness",
        type=Path,
        default=DEFAULT_HARNESS,
        help="Path to OfficialHeadlessCompile.exe",
    )
    parser.add_argument(
        "--skip-compile",
        action="store_true",
        help="Run only --open-lowlevel and skip --compile-lowlevel",
    )
    parser.add_argument(
        "--cache-root",
        type=Path,
        help="Optional shared cache root; defaults to repo-local artifacts_cache/official_lowlevel_probe",
    )
    parser.add_argument(
        "--patch-spec-json",
        type=Path,
        help="Optional patch spec JSON path to fold into the stable cache key",
    )
    args = parser.parse_args(argv)

    report = probe_official_lowlevel_hmi(
        args.hmi.resolve(),
        args.out_dir.resolve(),
        harness=args.harness.resolve(),
        run_compile=not args.skip_compile,
        cache_root=None if args.cache_root is None else args.cache_root.resolve(),
        patch_spec_path=None if args.patch_spec_json is None else args.patch_spec_json.resolve(),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def probe_official_lowlevel_hmi(
    hmi_path: Path,
    out_dir: Path,
    *,
    harness: Path = DEFAULT_HARNESS,
    run_compile: bool = True,
    cache_root: Path | None = None,
    patch_spec_path: Path | None = None,
    patch_spec_payload: dict[str, Any] | None = None,
    request_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    if not hmi_path.exists():
        raise FileNotFoundError(f"HMI does not exist: {hmi_path}")
    harness = _resolve_harness(harness)
    cache_root = resolve_official_lowlevel_cache_root(cache_root)
    request = build_official_lowlevel_probe_request(
        hmi_path=hmi_path,
        harness_path=harness,
        run_compile=run_compile,
        patch_spec_path=patch_spec_path,
        patch_spec_payload=patch_spec_payload,
        source_version_paths=_source_version_paths(),
        request_context=request_context,
    )
    cached = materialize_cached_official_lowlevel_probe(
        request,
        out_dir=out_dir,
        hmi_stem=hmi_path.stem,
        run_compile=run_compile,
        cache_root=cache_root,
    )
    if cached is not None:
        return cached

    local_paths = local_official_lowlevel_probe_paths(out_dir, hmi_stem=hmi_path.stem, run_compile=run_compile)
    _ensure_local_probe_parent_dirs(local_paths)
    open_result = _run_harness(
        harness,
        ["--open-lowlevel", str(hmi_path), str(local_paths["open_lowlevel_result_json"])],
    )
    open_summary = _summarize_open_result(open_result, local_paths["open_lowlevel_result_json"])

    compile_summary: dict[str, Any] | None = None
    if run_compile:
        compile_result = _run_harness(
            harness,
            ["--compile-lowlevel", str(hmi_path), str(local_paths["compiled_tft"]), str(local_paths["compile_lowlevel_result_json"])],
        )
        compile_summary = _summarize_compile_result(
            compile_result,
            local_paths["compile_lowlevel_result_json"],
            local_paths["compiled_tft"],
            event_index_json=local_paths["compile_event_index_json"],
            hmi_path=hmi_path,
        )

    report = {
        "schema_version": 1,
        "mode": "official_hmi_lowlevel_probe",
        "hmi": str(hmi_path),
        "harness": str(harness),
        "input_hmi_sha256": request["input_hmi"]["sha256"],
        "patch_spec_sha256": request["patch_spec"]["sha256"],
        "probe_request_sha256": request["request_sha256"],
        "cache_key": request["cache_key"],
        "tool_version_sha256": request["tool_version"]["sha256"],
        "official_probe_version_sha256": request["official_probe_version"]["sha256"],
        "open_lowlevel": open_summary,
        "compile_lowlevel": compile_summary,
        "accepted_by_open_lowlevel": open_summary["accepted"],
        "accepted_by_compile_lowlevel": (
            None if compile_summary is None else compile_summary["compiled_success"] and not compile_summary["empty_shell_class"]
        ),
    }

    stored = store_cached_official_lowlevel_probe(
        request,
        cache_root=cache_root,
        report=report,
        artifact_sources=local_paths,
        run_compile=run_compile,
    )
    if stored["manifest_path"].exists():
        _ensure_local_probe_parent_dirs({"cache_manifest_json": local_paths["cache_manifest_json"]})
        local_paths["cache_manifest_json"].write_text(
            stored["manifest_path"].read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    report = rewrite_official_lowlevel_report_paths(
        report,
        request=request,
        report_path=local_paths["report_json"],
        local_paths=local_paths,
        cache_dir=stored["cache_dir"],
        cache_manifest_path=local_paths["cache_manifest_json"],
        cache_hit=False,
        cache_miss=True,
    )
    local_paths["report_json"].write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _run_harness(harness: Path, extra_args: list[str]) -> subprocess.CompletedProcess[str]:
    command = [str(harness), *extra_args]
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(harness.parent),
    )


def _ensure_local_probe_parent_dirs(paths: dict[str, Path | None]) -> None:
    for path in paths.values():
        if path is None:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)


def _resolve_harness(harness: Path) -> Path:
    candidates = [harness]
    if harness == DEFAULT_HARNESS:
        candidates.append(RUNTIME_CLEAN_HARNESS)
    for candidate in candidates:
        if not candidate.exists():
            continue
        if _harness_runtime_ready(candidate):
            return candidate
    if harness.exists():
        return harness
    raise FileNotFoundError(f"Official low-level harness does not exist: {harness}")


def _harness_runtime_ready(harness: Path) -> bool:
    startup_dir = harness.parent
    required = (
        "ApplicationRUN.dll",
        "AppDllPass.dll",
        "ACTR.dll",
        "USART HMI.exe",
    )
    return all((startup_dir / name).exists() for name in required)


def _summarize_open_result(result: subprocess.CompletedProcess[str], result_json: Path) -> dict[str, Any]:
    payload = _load_json_if_exists(result_json)
    return {
        "command_exit_code": result.returncode,
        "accepted": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "result_json": str(result_json),
        "result_payload": payload,
    }


def _summarize_compile_result(
    result: subprocess.CompletedProcess[str],
    result_json: Path,
    compile_tft: Path,
    *,
    event_index_json: Path | None,
    hmi_path: Path,
) -> dict[str, Any]:
    payload = _load_json_if_exists(result_json)
    page_lines = _extract_page_lines(result.stdout)
    object_region_length = None
    object_region_length_hex = None
    event_index_error = None
    if result.returncode == 0 and compile_tft.exists():
        try:
            event_index = inspect_tft_event_index(hmi_path, compile_tft, out_path=event_index_json)
            object_region_length = event_index.get("object_region_length")
            object_region_length_hex = event_index.get("object_region_length_hex")
        except Exception as exc:  # pragma: no cover - depends on local proprietary fixtures
            event_index_error = f"{type(exc).__name__}: {exc}"
    compiled_output_size = compile_tft.stat().st_size if compile_tft.exists() else None
    return {
        "command_exit_code": result.returncode,
        "compiled_success": result.returncode == 0 and compile_tft.exists(),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "result_json": str(result_json),
        "result_payload": payload,
        "compiled_tft": str(compile_tft),
        "compiled_output_size": compiled_output_size,
        "page_lines": page_lines,
        "page_lines_present": bool(page_lines),
        "object_region_length": object_region_length,
        "object_region_length_hex": object_region_length_hex,
        "event_index_json": str(event_index_json) if event_index_json is not None and event_index_json.exists() else None,
        "event_index_error": event_index_error,
        "empty_shell_class": _is_empty_shell_class(
            compiled_output_size=compiled_output_size,
            object_region_length=object_region_length,
            page_lines=page_lines,
        ),
    }


def _extract_page_lines(stdout: str) -> list[str]:
    result: list[str] = []
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if "occupied memory" in lowered or "页面:" in line:
            result.append(line)
    return result


def _is_empty_shell_class(
    *,
    compiled_output_size: int | None,
    object_region_length: int | None,
    page_lines: list[str],
) -> bool:
    if compiled_output_size == EMPTY_SHELL_OUTPUT_SIZE:
        return True
    if object_region_length == 0xC4 and not page_lines:
        return True
    return False


def _load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None


def _source_version_paths() -> list[Path]:
    root = Path(__file__).resolve().parents[1]
    return [
        Path(__file__).resolve(),
        root / "usarthmi" / "official_probe_cache.py",
        root / "tools" / "official_hmi_lowlevel_probe.py",
        root / "usarthmi" / "tft_event_index.py",
    ]
