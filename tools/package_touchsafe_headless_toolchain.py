from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE_NAME = "usarthmi-headless-toolchain"
HOST_EXE = REPO_ROOT / "build" / "official_gui_host_select" / "UsartHmiHostAutomation.exe"
PACKAGED_HOST_EXE = Path("tools/UsartHmiHostAutomation.exe")

REQUIRED_FILES = [
    ".gitignore",
    "pyproject.toml",
    "usarthmi.cmd",
    "tools/codex_touchsafe_official_pipeline.py",
    "tools/codex_apply_hmi_patch_plan.py",
    "tools/codex_hmi_beauty_preview.py",
    "tools/official_hmi_hook_runner.py",
    "tools/official_gui_host_select.py",
    "tools/official_gui_mdbg.py",
    "tools/OfficialGuiHostSelect.cs",
    "tools/touchsafe_headless_bootstrap.ps1",
    "tools/run_touchsafe_pipeline.ps1",
    "tools/run_touchsafe_pipeline.cmd",
    "tools/package_touchsafe_headless_toolchain.py",
    "examples/polished_dashboard_demo/touchsafe_pipeline.md",
    "examples/polished_dashboard_demo/touchsafe_pipeline.template.json",
    "examples/polished_dashboard_demo/touchsafe_headless_package.md",
    "skills/usarthmi-headless-toolchain/SKILL.md",
    "skills/usarthmi-headless-toolchain/agents/openai.yaml",
]

REQUIRED_DIRS = [
    "usarthmi",
]

EXCLUDED_DIR_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
}

EXCLUDED_SUFFIXES = {
    ".bin",
    ".dll",
    ".exe",
    ".hmi",
    ".jpg",
    ".png",
    ".pdb",
    ".rar",
    ".tft",
    ".zip",
    ".zi",
}

ALLOWLISTED_BINARY_FILES = {
    str(PACKAGED_HOST_EXE).replace("\\", "/").lower(),
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a portable source zip for the touch-safe headless USART HMI toolchain.")
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "dist")
    parser.add_argument("--name", default=DEFAULT_PACKAGE_NAME)
    parser.add_argument("--version-label", default=dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
    parser.add_argument("--skip-host-build", action="store_true", help="Do not try to build/copy the C# host executable.")
    parser.add_argument("--require-host-exe", action="store_true", help="Fail if the generated zip cannot include the C# host executable.")
    parser.add_argument("--no-zip", action="store_true", help="Only materialize the package directory.")
    args = parser.parse_args()

    package_dir = (args.out_dir / f"{safe_name(args.name)}-{safe_name(args.version_label)}").resolve()
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True)

    host_included = False
    host_build_error = None
    if not args.skip_host_build:
        try:
            host_included = build_host_exe()
        except Exception as exc:  # pragma: no cover - exact local compiler state varies
            host_build_error = str(exc)
            host_included = HOST_EXE.exists()
    if args.require_host_exe and not host_included:
        raise SystemExit(f"C# host executable is not available: {host_build_error or HOST_EXE}")

    copied = copy_package_tree(package_dir, include_host_exe=host_included)
    manifest = {
        "schema_version": 1,
        "name": args.name,
        "version_label": args.version_label,
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_root": str(REPO_ROOT),
        "entrypoints": {
            "bootstrap": "tools/touchsafe_headless_bootstrap.ps1",
            "run": "tools/run_touchsafe_pipeline.ps1",
            "package": "tools/package_touchsafe_headless_toolchain.py",
            "skill": "skills/usarthmi-headless-toolchain/SKILL.md",
        },
        "requirements": {
            "official_usart_hmi": "Installed on the target machine; auto-discovered or passed with -OfficialDir/--install-dir.",
            "python_source_package": "Python 3.10+ is required for this source package.",
            "csharp_host": "Prebuilt host included when host_exe_included is true; otherwise target needs .NET Framework csc.exe.",
        },
        "host_exe_included": host_included,
        "host_build_error": host_build_error,
        "file_count": len(copied),
        "files": copied,
    }
    write_json(package_dir / "package_manifest.json", manifest)

    zip_path = None
    if not args.no_zip:
        zip_path = package_dir.with_suffix(".zip")
        if zip_path.exists():
            zip_path.unlink()
        write_zip(package_dir, zip_path)

    print(
        json.dumps(
            {
                "status": "ok",
                "package_dir": str(package_dir),
                "zip": None if zip_path is None else str(zip_path),
                "host_exe_included": host_included,
                "file_count": len(copied),
            },
            indent=2,
        )
    )
    return 0


def build_host_exe() -> bool:
    sys.path.insert(0, str(REPO_ROOT))
    from tools import official_gui_host_select

    official_gui_host_select.ensure_binary()
    return HOST_EXE.exists()


def copy_package_tree(package_dir: Path, *, include_host_exe: bool) -> list[str]:
    copied: list[str] = []
    for relative in REQUIRED_FILES:
        source = REPO_ROOT / relative
        if not source.exists():
            raise FileNotFoundError(source)
        copied.append(copy_file(source, package_dir / relative, relative))

    for relative_dir in REQUIRED_DIRS:
        source_dir = REPO_ROOT / relative_dir
        if not source_dir.is_dir():
            raise FileNotFoundError(source_dir)
        for source in sorted(iter_files(source_dir)):
            relative = source.relative_to(REPO_ROOT).as_posix()
            if should_exclude(relative):
                continue
            copied.append(copy_file(source, package_dir / relative, relative))

    if include_host_exe:
        copied.append(copy_file(HOST_EXE, package_dir / PACKAGED_HOST_EXE, PACKAGED_HOST_EXE.as_posix()))

    quickstart = package_dir / "PACKAGE_QUICKSTART.md"
    quickstart.write_text(
        "# USART HMI Headless Toolchain Package\n\n"
        "1. Install the official USART HMI application.\n"
        "2. Run `powershell -ExecutionPolicy Bypass -File .\\tools\\touchsafe_headless_bootstrap.ps1`.\n"
        "3. Run `powershell -ExecutionPolicy Bypass -File .\\tools\\run_touchsafe_pipeline.ps1 -Spec <spec.json>`.\n"
        "4. Inspect `<out-dir>\\pipeline_manifest.json`.\n\n"
        "The source package requires Python 3.10+. Use a separate standalone build if the target must not install Python.\n",
        encoding="utf-8",
    )
    copied.append("PACKAGE_QUICKSTART.md")
    return sorted(dict.fromkeys(copied))


def iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        parts = set(path.relative_to(REPO_ROOT).parts)
        if parts & EXCLUDED_DIR_NAMES:
            continue
        yield path


def should_exclude(relative: str) -> bool:
    normalized = relative.replace("\\", "/").lower()
    if normalized in ALLOWLISTED_BINARY_FILES:
        return False
    return Path(normalized).suffix in EXCLUDED_SUFFIXES


def copy_file(source: Path, destination: Path, relative: str) -> str:
    if should_exclude(relative):
        raise ValueError(f"Refusing to package generated/binary payload: {relative}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return relative.replace("\\", "/")


def write_zip(package_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(package_dir.rglob("*")):
            if path.is_dir():
                continue
            archive.write(path, path.relative_to(package_dir.parent).as_posix())


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def safe_name(value: str) -> str:
    chars = []
    for ch in value:
        if ch.isalnum() or ch in {"-", "_", "."}:
            chars.append(ch)
        else:
            chars.append("-")
    return "".join(chars).strip("-") or "package"


if __name__ == "__main__":
    raise SystemExit(main())
