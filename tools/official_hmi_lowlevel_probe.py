from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.official_hmi_session import (  # noqa: E402
    compute_file_sha256,
    load_cached_json_if_same_input,
    save_json_with_input_hash,
)
from usarthmi.tft_event_index import inspect_tft_event_index  # noqa: E402


DEFAULT_HARNESS = Path(r"D:\reverse\USART HMI_decompile\tools\OfficialHeadlessCompile.exe")
RUNTIME_CLEAN_HARNESS = Path(
    r"D:\reverse\USART HMI_decompile\tools\headless_debugger\harness_runtime_clean\OfficialHeadlessCompile.exe"
)
EMPTY_SHELL_OUTPUT_SIZE = 11_403_460


def main() -> int:
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
    args = parser.parse_args()

    report = probe_official_lowlevel_hmi(
        args.hmi.resolve(),
        args.out_dir.resolve(),
        harness=args.harness.resolve(),
        run_compile=not args.skip_compile,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def probe_official_lowlevel_hmi(
    hmi_path: Path,
    out_dir: Path,
    *,
    harness: Path = DEFAULT_HARNESS,
    run_compile: bool = True,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    if not hmi_path.exists():
        raise FileNotFoundError(f"HMI does not exist: {hmi_path}")
    harness = _resolve_harness(harness)

    input_hash = compute_file_sha256(hmi_path)
    report_path = out_dir / f"{hmi_path.stem}.official_lowlevel.json"
    compile_tft = out_dir / f"{hmi_path.stem}.lowlevel.tft"
    compile_required = [compile_tft] if run_compile else []
    cached = load_cached_json_if_same_input(
        report_path,
        input_path=hmi_path,
        input_hash_key="input_hmi_sha256",
        input_hash=input_hash,
        required_files=compile_required,
    )
    if cached is not None:
        cached["cache_hit"] = True
        return cached

    open_json = out_dir / "open_lowlevel.result.json"
    open_result = _run_harness(
        harness,
        ["--open-lowlevel", str(hmi_path), str(open_json)],
    )
    open_summary = _summarize_open_result(open_result, open_json)

    compile_summary: dict[str, Any] | None = None
    if run_compile:
        compile_json = out_dir / "compile_lowlevel.result.json"
        compile_result = _run_harness(
            harness,
            ["--compile-lowlevel", str(hmi_path), str(compile_tft), str(compile_json)],
        )
        compile_summary = _summarize_compile_result(
            compile_result,
            compile_json,
            compile_tft,
            hmi_path=hmi_path,
            out_dir=out_dir,
        )

    report = {
        "schema_version": 1,
        "mode": "official_hmi_lowlevel_probe",
        "hmi": str(hmi_path),
        "harness": str(harness),
        "open_lowlevel": open_summary,
        "compile_lowlevel": compile_summary,
        "accepted_by_open_lowlevel": open_summary["accepted"],
        "accepted_by_compile_lowlevel": (
            None if compile_summary is None else compile_summary["compiled_success"] and not compile_summary["empty_shell_class"]
        ),
    }
    return save_json_with_input_hash(
        report_path,
        report,
        input_path=hmi_path,
        input_hash_key="input_hmi_sha256",
        input_hash=input_hash,
    )


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
    hmi_path: Path,
    out_dir: Path,
) -> dict[str, Any]:
    payload = _load_json_if_exists(result_json)
    page_lines = _extract_page_lines(result.stdout)
    event_index_json = out_dir / "compile_lowlevel.event_index.json"
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
        "event_index_json": str(event_index_json) if event_index_json.exists() else None,
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
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
