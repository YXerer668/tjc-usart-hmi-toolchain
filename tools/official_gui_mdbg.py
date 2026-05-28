from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from usarthmi.hmi_inspect import inspect_hmi
from usarthmi.page_format import parse_page_data


INVOKE_MDBG_PS1 = REPO_ROOT / "tools" / "invoke_mdbg_commands.ps1"
DEFAULT_MDBG_EXE = Path(r"D:\reverse\USART HMI_decompile\tools\headless_debugger\mdbg_x86\Mdbg.exe")
DEFAULT_LOG_DIR = REPO_ROOT / "build" / "official_gui_mdbg"


def get_short_path(path: Path) -> str:
    command = (
        "$fso = New-Object -ComObject Scripting.FileSystemObject; "
        f"$fso.GetFile('{str(path.resolve())}').ShortPath"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def invoke_mdbg_commands(
    *,
    commands: Sequence[str],
    log_path: Path,
    mdbg_exe: Path = DEFAULT_MDBG_EXE,
) -> dict[str, object]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(INVOKE_MDBG_PS1),
        "-MdbgExe",
        str(mdbg_exe),
        "-LogPath",
        str(log_path),
        "-CommandsJson",
        json.dumps(list(commands), ensure_ascii=False),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "log_path": str(log_path),
        "log_exists": log_path.exists(),
    }


def attach_dump_current_form(
    *,
    pid: int,
    log_path: Path,
    mdbg_exe: Path = DEFAULT_MDBG_EXE,
) -> dict[str, object]:
    commands = [
        f"attach -ver v2.0.50727 {pid}",
        "thread 0",
        "up 1",
        "print this",
        "set $main=this.currentForm",
        "detach",
        "quit",
    ]
    return invoke_mdbg_commands(commands=commands, log_path=log_path, mdbg_exe=mdbg_exe)


def attach_try_select_existing(
    *,
    pid: int,
    object_index: int,
    log_path: Path,
    capture_thread_number: int = 0,
    eval_thread_number: int | None = None,
    capture_main_up_frames: int = 1,
    eval_up_frames: int = 3,
    mdbg_exe: Path = DEFAULT_MDBG_EXE,
) -> dict[str, object]:
    if eval_thread_number is None:
        eval_thread_number = capture_thread_number
    commands = [
        f"attach -ver v2.0.50727 {pid}",
        f"thread {int(capture_thread_number)}",
        f"up {int(capture_main_up_frames)}",
        "set $main=this.currentForm",
        f"thread {int(eval_thread_number)}",
        f"up {int(eval_up_frames)}",
        f"funceval TFTEDIT.TFTEDIT.setxuanzhong_del $main.TFTEDIT0 0",
        f"funceval TFTEDIT.TFTEDIT.setxuanzhong_add $main.TFTEDIT0 {int(object_index)}",
        "funceval HMIFORM.main.objselect $main",
        "detach",
        "quit",
    ]
    return invoke_mdbg_commands(commands=commands, log_path=log_path, mdbg_exe=mdbg_exe)


def _read_bytes_retry(path: Path, *, attempts: int = 5, delay_s: float = 0.2) -> bytes:
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


def resolve_object_index(*, hmi_path: Path, page_resource: str, object_name: str) -> int:
    source_path = hmi_path
    try:
        raw = _read_bytes_retry(hmi_path)
    except (PermissionError, OSError):
        fallback = hmi_path.with_suffix(hmi_path.suffix + ".before_official_automation.bak")
        if not fallback.exists():
            raise
        raw = _read_bytes_retry(fallback)
        source_path = fallback
    inspection = inspect_hmi(source_path)
    page_entry = next((entry for entry in inspection.entries if entry.name == page_resource), None)
    if page_entry is None or not page_entry.in_file:
        raise RuntimeError(f"{page_resource} not found in {source_path}")
    page = parse_page_data(raw[page_entry.data_offset : page_entry.data_offset + page_entry.length])
    for index, block in enumerate(page.blocks):
        if block.objname == object_name:
            return index
    raise RuntimeError(f"{page_resource}:{object_name} not found in {source_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run reproducible MDbg attach probes against the official USART HMI GUI.")
    parser.add_argument("mode", choices=["dump-current-form", "try-select-existing"])
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--object-index", type=int)
    parser.add_argument("--object-name")
    parser.add_argument("--hmi-path", type=Path)
    parser.add_argument("--page-resource", default="0.pa")
    parser.add_argument("--capture-thread-number", type=int, default=0)
    parser.add_argument("--eval-thread-number", type=int)
    parser.add_argument("--capture-main-up-frames", type=int, default=1)
    parser.add_argument("--eval-up-frames", type=int, default=3)
    parser.add_argument("--log-path", type=Path)
    parser.add_argument("--mdbg-exe", type=Path, default=DEFAULT_MDBG_EXE)
    args = parser.parse_args()

    if args.log_path is None:
        suffix = "current_form" if args.mode == "dump-current-form" else f"select_index_{args.object_index}"
        log_path = DEFAULT_LOG_DIR / f"{args.pid}_{suffix}.log"
    else:
        log_path = args.log_path

    if args.mode == "dump-current-form":
        result = attach_dump_current_form(pid=args.pid, log_path=log_path, mdbg_exe=args.mdbg_exe)
    else:
        object_index = args.object_index
        if args.object_name is not None:
            if args.hmi_path is None:
                raise SystemExit("--hmi-path is required when --object-name is used")
            object_index = resolve_object_index(
                hmi_path=args.hmi_path,
                page_resource=args.page_resource,
                object_name=str(args.object_name),
            )
        if object_index is None:
            raise SystemExit("try-select-existing requires --object-index or --object-name with --hmi-path")
        result = attach_try_select_existing(
            pid=args.pid,
            object_index=int(object_index),
            log_path=log_path,
            capture_thread_number=args.capture_thread_number,
            eval_thread_number=args.eval_thread_number,
            capture_main_up_frames=args.capture_main_up_frames,
            eval_up_frames=args.eval_up_frames,
            mdbg_exe=args.mdbg_exe,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result["returncode"])


if __name__ == "__main__":
    raise SystemExit(main())
