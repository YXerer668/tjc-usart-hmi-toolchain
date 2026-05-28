from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.official_gui_mdbg import resolve_object_index
from usarthmi.official_gui_automation import resolve_official_gui_control
from usarthmi.editor import _replace_hmi_entry
from usarthmi.hmi_inspect import inspect_hmi


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = REPO_ROOT / "build" / "official_gui_host_select"
SOURCE_PATH = REPO_ROOT / "tools" / "OfficialGuiHostSelect.cs"
HOST_EXE_NAME = "UsartHmiHostAutomation.exe"
EXE_PATH = BUILD_DIR / HOST_EXE_NAME
PACKAGED_EXE_PATH = REPO_ROOT / "tools" / HOST_EXE_NAME
LEGACY_HEADLESS_RUNTIME_DIR = Path(r"D:\reverse\USART HMI_decompile\tools\headless_debugger\harness_runtime_clean")
DEFAULT_INSTALL_DIR = LEGACY_HEADLESS_RUNTIME_DIR
STANDARD_INSTALL_DIRS = (
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "USART HMI",
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "USART HMI",
)
OFFICIAL_DIR_ENV = "USARTHMI_OFFICIAL_DIR"
RUNTIME_ROOT_ENV = "USARTHMI_HEADLESS_RUNTIME_ROOT"
RUN_IN_PLACE_ENV = "USARTHMI_HEADLESS_RUN_IN_PLACE"
MAIN_HMI_APPMEDATA_OFFSET = 40
MAIN_HMI_RAM1OPEN_OFFSET = 37
APPMEDATA_HEX_BYTES = 24
ARG_NONE = "__CODEX_NONE__"
DEFAULT_MANAGED_APPMEDATA_STRING = "1000-17FF\r\n"
SOFT_OPEN_MEDATA_FILENAME = "DEFSoftOpen_MedataMakeEn.bin"
SOFT_OPEN_3DPRINTER_FILENAME = "DEFSoftOpen_3DprinterEn.bin"


def ensure_binary() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    if PACKAGED_EXE_PATH.exists() and (
        not EXE_PATH.exists() or EXE_PATH.stat().st_mtime < PACKAGED_EXE_PATH.stat().st_mtime
    ):
        shutil.copy2(PACKAGED_EXE_PATH, EXE_PATH)
    if EXE_PATH.exists() and EXE_PATH.stat().st_mtime >= SOURCE_PATH.stat().st_mtime:
        return
    csc_path = _find_csc()
    if csc_path is None:
        if PACKAGED_EXE_PATH.exists():
            shutil.copy2(PACKAGED_EXE_PATH, EXE_PATH)
            return
        raise FileNotFoundError(
            "No .NET Framework C# compiler found. Install/enable .NET Framework developer tools "
            f"or ship a prebuilt {HOST_EXE_NAME} beside OfficialGuiHostSelect.cs."
        )
    if (not EXE_PATH.exists()) or EXE_PATH.stat().st_mtime < SOURCE_PATH.stat().st_mtime:
        cmd = [
            str(csc_path),
            "/nologo",
            "/target:exe",
            "/platform:x86",
            f"/out:{EXE_PATH}",
            "/r:System.dll",
            "/r:System.Drawing.dll",
            "/r:System.Windows.Forms.dll",
            str(SOURCE_PATH),
        ]
        subprocess.run(cmd, check=True)


def _candidate_csc_paths() -> list[Path]:
    candidates: list[Path] = []
    if os.environ.get("CSC"):
        candidates.append(Path(os.environ["CSC"]))
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    candidates.extend(
        [
            windir / "Microsoft.NET" / "Framework" / "v4.0.30319" / "csc.exe",
            windir / "Microsoft.NET" / "Framework" / "v2.0.50727" / "csc.exe",
        ]
    )
    return candidates


def _find_csc() -> Path | None:
    for candidate in _candidate_csc_paths():
        if candidate.exists():
            return candidate
    return None


def run_probe(
    *,
    hmi_path: Path,
    page_index: int,
    page_resource: str,
    object_index: int,
    report_path: Path,
    patch_fields: list[tuple[str, str]] | None = None,
    patch_events: list[tuple[str, list[str]]] | None = None,
    create_control_var_name: str | None = None,
    add_page_name: str | None = None,
    macro_lines: list[str] | None = None,
    compile_output_path: Path | None = None,
    override_appmedata_string: str | None = None,
    override_ram1_open: int | None = None,
    force_save: bool = False,
    force_page_dump: bool = False,
    install_dir: Path | None = None,
) -> dict[str, object]:
    ensure_binary()
    metadata_hint = _extract_main_hmi_metadata_hint(hmi_path)
    _apply_managed_runtime_defaults_for_control(
        metadata_hint,
        create_control_var_name=create_control_var_name,
    )
    if override_appmedata_string is not None:
        metadata_hint["appmedata_string"] = str(override_appmedata_string)
    if override_ram1_open is not None:
        metadata_hint["ram1_open"] = int(override_ram1_open)
    chosen_install_dir = _choose_install_dir(
        install_dir=install_dir,
        metadata_hint=metadata_hint,
    )
    runtime_soft_open_markers = _ensure_runtime_soft_open_markers(
        chosen_install_dir,
        metadata_hint=metadata_hint,
        create_control_var_name=create_control_var_name,
    )
    stage_name = f"{EXE_PATH.stem}_{report_path.stem}_{os.getpid()}_{int(time.time() * 1000)}{EXE_PATH.suffix}"
    stage_path = chosen_install_dir / stage_name
    shutil.copy2(EXE_PATH, stage_path)
    patch_spec_path = None
    macro_spec_path = None
    page_dump_path = report_path.with_suffix(report_path.suffix + ".page.bin")
    for stale_path in (
        report_path,
        report_path.with_suffix(report_path.suffix + ".trace.log"),
        page_dump_path,
        report_path.with_suffix(report_path.suffix + ".macro.tsv"),
    ):
        try:
            stale_path.unlink()
        except FileNotFoundError:
            pass
    if macro_lines:
        macro_spec_path = report_path.with_suffix(report_path.suffix + ".macro.tsv")
        macro_spec_path.parent.mkdir(parents=True, exist_ok=True)
        macro_spec_path.write_text("\n".join(macro_lines) + "\n", encoding="utf-8")
    if patch_fields or patch_events:
        patch_spec_path = report_path.with_suffix(report_path.suffix + ".patch.tsv")
        patch_spec_path.parent.mkdir(parents=True, exist_ok=True)
        patch_lines = [f"field\t{name}\t{value}" for name, value in (patch_fields or [])]
        for event_name, lines in patch_events or []:
            patch_lines.append(f"event\t{event_name}\t{'\\n'.join(lines)}")
        patch_spec_path.write_text("\n".join(patch_lines) + "\n", encoding="utf-8")
    cmd = [
        str(stage_path),
        str(hmi_path.resolve()),
        str(int(page_index)),
        str(int(object_index)),
        str(report_path.resolve()),
        str(chosen_install_dir.resolve()),
        str(page_resource or ARG_NONE),
    ]
    cmd.append(str(patch_spec_path.resolve()) if patch_spec_path is not None else ARG_NONE)
    cmd.append(str(create_control_var_name) if create_control_var_name is not None else ARG_NONE)
    cmd.append(str(compile_output_path.resolve()) if compile_output_path is not None else ARG_NONE)
    cmd.append(
        str(metadata_hint["appmedata_string"]).replace("\r", "\\r").replace("\n", "\\n")
        if metadata_hint["appmedata_string"]
        else ARG_NONE
    )
    cmd.append(str(metadata_hint["ram1_open"]) if metadata_hint["ram1_open"] is not None else ARG_NONE)
    cmd.append("1" if force_save else "0")
    cmd.append("1" if force_page_dump else "0")
    cmd.append(str(add_page_name) if add_page_name else ARG_NONE)
    cmd.append(str(macro_spec_path.resolve()) if macro_spec_path is not None else ARG_NONE)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    deadline = time.time() + (240.0 if macro_spec_path is not None else 90.0)
    mutates_page_payload = bool(patch_fields or patch_events or create_control_var_name)
    mutates_hmi_payload = bool(mutates_page_payload or add_page_name or macro_spec_path is not None)
    expect_page_dump = bool(force_page_dump or (mutates_page_payload and not add_page_name and macro_spec_path is None))
    while time.time() < deadline:
        exited = proc.poll() is not None
        ready = report_path.exists() and (not expect_page_dump or page_dump_path.exists())
        if exited:
            break
        if ready:
            break
        time.sleep(0.2)
    if proc.poll() is None:
        if report_path.exists() and (not expect_page_dump or page_dump_path.exists()):
            proc.terminate()
            try:
                proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                proc.kill()
        else:
            proc.kill()
    stdout, stderr = proc.communicate(timeout=5.0)
    artifact_ready = report_path.exists() and (not expect_page_dump or page_dump_path.exists())
    effective_returncode = 0 if artifact_ready else proc.returncode
    result: dict[str, object] = {
        "command": cmd,
        "returncode": effective_returncode,
        "raw_returncode": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "report_path": str(report_path.resolve()),
        "report_exists": report_path.exists(),
        "patch_spec_path": None if patch_spec_path is None else str(patch_spec_path.resolve()),
        "macro_spec_path": None if macro_spec_path is None else str(macro_spec_path.resolve()),
        "page_dump_path": str(page_dump_path.resolve()),
        "page_dump_exists": page_dump_path.exists(),
        "artifact_ready": artifact_ready,
        "create_control_var_name": create_control_var_name,
        "add_page_name": add_page_name,
        "compile_output_path": None if compile_output_path is None else str(compile_output_path.resolve()),
        "force_save": bool(force_save),
        "force_page_dump": bool(force_page_dump),
        "install_dir": str(chosen_install_dir.resolve()),
        "runtime_soft_open_markers": runtime_soft_open_markers,
    }
    report_json = None
    if report_path.exists():
        try:
            report_json = json.loads(report_path.read_text(encoding="utf-8-sig"))
        except Exception:
            report_json = None
    if mutates_hmi_payload:
        saved_project = bool(isinstance(report_json, dict) and int(report_json.get("saved_project", 0) or 0) == 1)
        if mutates_page_payload and page_dump_path.exists() and not saved_project:
            raw = hmi_path.read_bytes()
            inspection = inspect_hmi(hmi_path)
            replacement = page_dump_path.read_bytes()
            patched = _replace_hmi_entry(raw, inspection.entries, page_resource, replacement)
            if not saved_project and isinstance(report_json, dict):
                patched = _patch_main_hmi_metadata(
                    patched,
                    inspection=inspect_hmi_from_raw(hmi_path, patched),
                    appmedata_hex=report_json.get("appmedata_hex"),
                    ram1_open=report_json.get("ram1_open"),
                )
            hmi_path.write_bytes(patched)
            result["patched_hmi_via_page_dump"] = True
        elif mutates_page_payload and page_dump_path.exists() and saved_project:
            result["page_dump_kept_as_evidence"] = True
        if saved_project:
            result["saved_hmi_in_place"] = True
    elif isinstance(report_json, dict) and int(report_json.get("saved_project", 0) or 0) == 1:
        result["saved_hmi_in_place"] = True
    if report_path.exists():
        result["report_json"] = report_json
    try:
        stage_path.unlink()
    except Exception:
        pass
    return result


def _control_requires_managed_runtime(create_control_var_name: str | None) -> bool:
    lowered = str(create_control_var_name or "").strip().lower()
    return "vp" in lowered or lowered == "printer3d"


def _apply_managed_runtime_defaults_for_control(
    metadata_hint: dict[str, object],
    *,
    create_control_var_name: str | None,
) -> None:
    if not _control_requires_managed_runtime(create_control_var_name):
        return
    if not str(metadata_hint.get("appmedata_string") or "").strip():
        metadata_hint["appmedata_string"] = DEFAULT_MANAGED_APPMEDATA_STRING
    if int(metadata_hint.get("ram1_open") or 0) != 1:
        metadata_hint["ram1_open"] = 1


def _choose_install_dir(*, install_dir: Path | None, metadata_hint: dict[str, object]) -> Path:
    source_dir = _resolve_official_install_dir(install_dir)
    if os.environ.get(RUN_IN_PLACE_ENV) == "1" and _install_dir_is_writable(source_dir):
        return source_dir
    return _prepare_writable_runtime(source_dir)


def _resolve_official_install_dir(install_dir: Path | None) -> Path:
    explicit = [install_dir] if install_dir is not None else []
    env_dir = [Path(os.environ[OFFICIAL_DIR_ENV])] if os.environ.get(OFFICIAL_DIR_ENV) else []
    candidates = [path for path in [*explicit, *env_dir, *STANDARD_INSTALL_DIRS, LEGACY_HEADLESS_RUNTIME_DIR] if path is not None]
    seen: set[str] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            resolved = candidate
        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)
        if _looks_like_official_install(resolved):
            return resolved
        if install_dir is not None and candidate == install_dir:
            raise FileNotFoundError(
                f"Official USART HMI runtime not found at {candidate}; expected USART HMI.exe and ACTR.dll"
            )
    searched = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(
        "Official USART HMI install not found. Pass --install-dir, set "
        f"{OFFICIAL_DIR_ENV}, or install USART HMI in the standard location. Searched: {searched}"
    )


def _looks_like_official_install(path: Path) -> bool:
    return (path / "USART HMI.exe").is_file() and (path / "ACTR.dll").is_file()


def _runtime_cache_root() -> Path:
    if os.environ.get(RUNTIME_ROOT_ENV):
        return Path(os.environ[RUNTIME_ROOT_ENV])
    local_app_data = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    return local_app_data / "USARTHMIHeadless" / "official_runtimes"


def _install_fingerprint(source_dir: Path) -> str:
    digest = hashlib.sha256()
    digest.update(str(source_dir.resolve()).lower().encode("utf-8", errors="replace"))
    for name in ("USART HMI.exe", "ACTR.dll"):
        path = source_dir / name
        stat = path.stat()
        digest.update(name.encode("ascii"))
        digest.update(str(stat.st_size).encode("ascii"))
        digest.update(str(int(stat.st_mtime_ns)).encode("ascii"))
    return digest.hexdigest()


def _prepare_writable_runtime(source_dir: Path) -> Path:
    fingerprint = _install_fingerprint(source_dir)
    runtime_dir = _runtime_cache_root() / f"official_{fingerprint[:16]}"
    manifest_path = runtime_dir / ".codex_headless_runtime.json"
    if _looks_like_official_install(runtime_dir) and manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        except Exception:
            manifest = {}
        if manifest.get("fingerprint") == fingerprint and manifest.get("source_dir") == str(source_dir.resolve()):
            return runtime_dir
    runtime_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, runtime_dir, dirs_exist_ok=True, ignore=_runtime_copy_ignore)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_dir": str(source_dir.resolve()),
                "fingerprint": fingerprint,
                "created_at_epoch": time.time(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if not _looks_like_official_install(runtime_dir):
        raise FileNotFoundError(f"Prepared runtime is incomplete: {runtime_dir}")
    return runtime_dir


def _runtime_copy_ignore(_directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        lowered = name.lower()
        if lowered in {"work", "__pycache__", ".pytest_cache"}:
            ignored.add(name)
        elif lowered.endswith((".log", ".tmp", ".bak")):
            ignored.add(name)
    return ignored


def _install_dir_is_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / f".codex_write_probe_{os.getpid()}_{int(time.time() * 1000)}.tmp"
        probe.write_text("ok", encoding="ascii")
        probe.unlink()
        return True
    except Exception:
        return False


def _required_soft_open_markers(
    *,
    metadata_hint: dict[str, object],
    create_control_var_name: str | None,
) -> dict[str, str]:
    markers: dict[str, str] = {}
    appmedata_string = str(metadata_hint.get("appmedata_string") or "").strip()
    ram1_open = int(metadata_hint.get("ram1_open") or 0)
    lowered = str(create_control_var_name or "").strip().lower()
    require_medata = bool(appmedata_string) or ram1_open == 1 or _control_requires_managed_runtime(create_control_var_name)
    if require_medata:
        markers[SOFT_OPEN_MEDATA_FILENAME] = "1\n"
    if lowered == "printer3d":
        markers[SOFT_OPEN_3DPRINTER_FILENAME] = "1\n"
    return markers


def _ensure_runtime_soft_open_markers(
    install_dir: Path,
    *,
    metadata_hint: dict[str, object],
    create_control_var_name: str | None,
) -> list[str]:
    install_dir.mkdir(parents=True, exist_ok=True)
    touched: list[str] = []
    for filename, value in _required_soft_open_markers(
        metadata_hint=metadata_hint,
        create_control_var_name=create_control_var_name,
    ).items():
        path = install_dir / filename
        path.write_text(value, encoding="ascii")
        touched.append(str(path.resolve()))
    return touched


def inspect_hmi_from_raw(path: Path, raw: bytes):
    temp_path = path.with_suffix(path.suffix + ".codex-temp-inspect")
    temp_path.write_bytes(raw)
    try:
        return inspect_hmi(temp_path)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def _read_bytes_with_retry(path: Path, *, attempts: int = 12, delay_s: float = 0.25) -> bytes:
    last_error: Exception | None = None
    for _ in range(max(1, int(attempts))):
        try:
            return path.read_bytes()
        except (PermissionError, OSError) as exc:
            last_error = exc
            time.sleep(delay_s)
    if last_error is not None:
        raise last_error
    return path.read_bytes()


def _inspect_hmi_with_retry(path: Path, *, attempts: int = 12, delay_s: float = 0.25):
    last_error: Exception | None = None
    for _ in range(max(1, int(attempts))):
        try:
            return inspect_hmi(path)
        except (PermissionError, OSError) as exc:
            last_error = exc
            time.sleep(delay_s)
    if last_error is not None:
        raise last_error
    return inspect_hmi(path)


def _patch_main_hmi_metadata(raw: bytes, *, inspection, appmedata_hex: object, ram1_open: object) -> bytes:
    main_entry = next((entry for entry in inspection.entries if entry.name == "main.HMI" and entry.in_file), None)
    if main_entry is None:
        return raw
    main_bytes = bytearray(raw[main_entry.data_offset : main_entry.data_offset + main_entry.length])
    if isinstance(appmedata_hex, str) and len(appmedata_hex) == APPMEDATA_HEX_BYTES * 2 and len(main_bytes) >= MAIN_HMI_APPMEDATA_OFFSET + APPMEDATA_HEX_BYTES:
        main_bytes[MAIN_HMI_APPMEDATA_OFFSET : MAIN_HMI_APPMEDATA_OFFSET + APPMEDATA_HEX_BYTES] = bytes.fromhex(appmedata_hex)
    if isinstance(ram1_open, int) and len(main_bytes) > MAIN_HMI_RAM1OPEN_OFFSET:
        main_bytes[MAIN_HMI_RAM1OPEN_OFFSET] = int(ram1_open) & 0xFF
    return _replace_hmi_entry(raw, inspection.entries, "main.HMI", bytes(main_bytes))


def _extract_main_hmi_metadata_hint(hmi_path: Path) -> dict[str, object]:
    raw = _read_bytes_with_retry(hmi_path)
    inspection = _inspect_hmi_with_retry(hmi_path)
    main_entry = next((entry for entry in inspection.entries if entry.name == "main.HMI" and entry.in_file), None)
    if main_entry is None:
        return {"appmedata_string": "", "ram1_open": None}
    main_bytes = raw[main_entry.data_offset : main_entry.data_offset + main_entry.length]
    ram1_open = int(main_bytes[MAIN_HMI_RAM1OPEN_OFFSET]) if len(main_bytes) > MAIN_HMI_RAM1OPEN_OFFSET else None
    appmedata_string = ""
    if len(main_bytes) >= MAIN_HMI_APPMEDATA_OFFSET + APPMEDATA_HEX_BYTES:
        fields = [
            int.from_bytes(main_bytes[offset : offset + 2], "little")
            for offset in range(MAIN_HMI_APPMEDATA_OFFSET, MAIN_HMI_APPMEDATA_OFFSET + APPMEDATA_HEX_BYTES, 2)
        ]
        lines = []
        for idx in range(0, len(fields), 2):
            start = fields[idx]
            end = fields[idx + 1]
            if start or end:
                lines.append(f"{start:04X}-{end:04X}")
        if lines:
            appmedata_string = "\r\n".join(lines) + "\r\n"
    return {"appmedata_string": appmedata_string, "ram1_open": ram1_open}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a managed-host probe that opens the official GUI and selects an existing object without debugger func-eval.")
    parser.add_argument("--hmi-path", type=Path, required=True)
    parser.add_argument("--page-index", type=int, default=0)
    parser.add_argument("--page-resource", default="0.pa")
    parser.add_argument("--object-index", type=int)
    parser.add_argument("--object-name")
    parser.add_argument("--create-control")
    parser.add_argument("--compile-output", type=Path)
    parser.add_argument("--set", action="append", default=[], help="Repeatable field patch in name=value form")
    parser.add_argument("--event", action="append", default=[], help="Repeatable event patch in event=line1\\nline2 form")
    parser.add_argument("--save", action="store_true", help="Invoke official filecaozuo(save) even without a patch")
    parser.add_argument("--dump-page", action="store_true", help="Invoke official Myapp.OutPutPageFile for the selected/current page")
    parser.add_argument("--report-path", type=Path)
    parser.add_argument(
        "--install-dir",
        type=Path,
        help="Official USART HMI install/runtime directory. Defaults to auto-discovery.",
    )
    args = parser.parse_args()

    object_index = args.object_index
    if args.object_name is not None:
        object_index = resolve_object_index(
            hmi_path=args.hmi_path,
            page_resource=args.page_resource,
            object_name=str(args.object_name),
        )
    create_control_var_name = None
    if args.create_control is not None:
        control = resolve_official_gui_control(str(args.create_control))
        create_control_var_name = control.decompiled_var_name
        object_index = -1
    if object_index is None:
        if args.save or args.dump_page or args.compile_output is not None:
            object_index = -1
        else:
            raise SystemExit(
                "--object-index, --object-name, --create-control, --save, --dump-page, or --compile-output is required"
            )

    if args.report_path is None:
        label = args.object_name if args.object_name is not None else f"idx{object_index}"
        report_path = BUILD_DIR / f"{args.hmi_path.stem}_page{args.page_index}_{label}.json"
    else:
        report_path = args.report_path

    patch_fields: list[tuple[str, str]] = []
    for item in args.set:
        if "=" not in item:
            raise SystemExit(f"--set must use name=value form: {item!r}")
        name, value = item.split("=", 1)
        patch_fields.append((name, value))
    patch_events: list[tuple[str, list[str]]] = []
    for item in args.event:
        if "=" not in item:
            raise SystemExit(f"--event must use event=line1\\\\nline2 form: {item!r}")
        event_name, value = item.split("=", 1)
        patch_events.append((event_name, value.split("\\n")))

    result = run_probe(
        hmi_path=args.hmi_path,
        page_index=args.page_index,
        object_index=int(object_index),
        report_path=report_path,
        page_resource=args.page_resource,
        patch_fields=patch_fields,
        patch_events=patch_events,
        create_control_var_name=create_control_var_name,
        compile_output_path=args.compile_output,
        force_save=args.save,
        force_page_dump=args.dump_page,
        install_dir=args.install_dir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["returncode"] == 0 else int(result["returncode"])


if __name__ == "__main__":
    raise SystemExit(main())
