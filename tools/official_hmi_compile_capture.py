from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from pywinauto import Desktop
from pywinauto.application import Application


DEFAULT_EXE = Path(r"C:\Program Files (x86)\USART HMI\USART HMI.exe")
DEFAULT_WORK_ROOT = Path.home() / r"AppData\Roaming\USART HMI\work"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile one USART HMI project with the official GUI and capture the generated run.run."
    )
    parser.add_argument("hmi", type=Path, help="Input .HMI file")
    parser.add_argument("--out-dir", type=Path, required=True, help="Directory for captured official outputs")
    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE, help="USART HMI.exe path")
    parser.add_argument("--work-root", type=Path, default=DEFAULT_WORK_ROOT, help="USART HMI roaming work root")
    parser.add_argument("--timeout-s", type=float, default=90.0, help="Compile timeout")
    parser.add_argument("--close", action="store_true", help="Close the official GUI after capture")
    args = parser.parse_args()

    hmi_path = args.hmi.resolve()
    exe_path = args.exe.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if not hmi_path.exists():
        raise SystemExit(f"HMI does not exist: {hmi_path}")
    if not exe_path.exists():
        raise SystemExit(f"USART HMI.exe does not exist: {exe_path}")

    start_time = time.time()
    before = _latest_run(args.work_root)
    app = Application(backend="uia").start(
        f'"{exe_path}" "{hmi_path}"',
        work_dir=str(exe_path.parent),
    )
    window = _wait_main_window(app.process, hmi_path, timeout=30)
    _dismiss_known_dialogs(app.process, timeout=10)
    output_before = _read_output_text(window)
    _click_compile(window)
    run_path, output_text = _wait_for_compile_result(
        window,
        args.work_root,
        after_time=start_time,
        before_path=before,
        timeout=args.timeout_s,
    )

    target_run = out_dir / f"{hmi_path.stem}.run"
    _copy_when_available(run_path, target_run, timeout=10.0)
    copied_output_files = _copy_output_folder(run_path.parent / "output", out_dir / "output")
    metadata = {
        "hmi": str(hmi_path),
        "official_exe": str(exe_path),
        "work_run": str(run_path),
        "captured_run": str(target_run),
        "captured_size": target_run.stat().st_size,
        "captured_output_files": copied_output_files,
        "output_before": output_before,
        "output_after": output_text,
        "compiled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    metadata_path = out_dir / f"{hmi_path.stem}.official_compile.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.close:
        _close_window(window)

    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


def _wait_main_window(process_id: int, hmi_path: Path, *, timeout: float):
    deadline = time.time() + timeout
    needle = hmi_path.name.lower()
    last_error: Exception | None = None
    while time.time() < deadline:
        for window in Desktop(backend="uia").windows():
            try:
                if window.process_id() != process_id:
                    continue
                title = window.window_text()
                if "USART HMI" in title and (needle in title.lower() or title.strip() == "USART HMI"):
                    return window
            except Exception as exc:  # pragma: no cover - defensive UI polling
                last_error = exc
        time.sleep(0.5)
    raise RuntimeError(f"Unable to find USART HMI main window for {hmi_path} ({last_error})")


def _click_compile(window) -> None:
    buttons = [
        control
        for control in window.descendants()
        if control.element_info.control_type == "Button"
    ]
    for control in buttons:
        if control.window_text() == "编译":
            control.click_input()
            return

    # Fallback for machines where UIA returns mojibake for the Chinese label:
    # choose the top toolbar button between Save and Debug by geometry.
    rect = window.rectangle()
    toolbar_buttons = []
    for control in buttons:
        crect = control.rectangle()
        if rect.top + 70 <= crect.top <= rect.top + 130:
            toolbar_buttons.append((crect.left, control))
    toolbar_buttons.sort(key=lambda item: item[0])
    for _left, control in toolbar_buttons:
        text = control.window_text()
        if text in {"保存", "调试"}:
            continue
        crect = control.rectangle()
        if rect.left + 240 <= crect.left <= rect.left + 360:
            control.click_input()
            return
    raise RuntimeError("Unable to locate the official Compile button")


def _dismiss_known_dialogs(process_id: int, *, timeout: float) -> None:
    deadline = time.time() + timeout
    ok_labels = {"OK", "\u786e\u5b9a"}
    while time.time() < deadline:
        clicked = False
        for dialog in Desktop(backend="uia").windows():
            try:
                if dialog.process_id() != process_id:
                    continue
            except Exception:
                continue
            for control in dialog.descendants():
                try:
                    if control.element_info.control_type == "Button" and control.window_text() in ok_labels:
                        control.click_input()
                        clicked = True
                        time.sleep(0.5)
                        break
                except Exception:
                    continue
            if clicked:
                break
        if not clicked:
            return


def _wait_for_compile_result(window, work_root: Path, *, after_time: float, before_path: Path | None, timeout: float):
    deadline = time.time() + timeout
    last_text = ""
    while time.time() < deadline:
        last_text = _read_output_text(window)
        run_path = _latest_run(work_root)
        if run_path is not None and run_path != before_path and run_path.stat().st_mtime >= after_time - 2:
            if "编译成功" in last_text or time.time() > after_time + 3:
                return run_path, last_text
        if "编译失败" in last_text or "错误" in last_text and "0个错误" not in last_text:
            raise RuntimeError(f"Official compile failed: {last_text}")
        time.sleep(0.5)
    raise TimeoutError(f"Timed out waiting for official compile output. Last output: {last_text!r}")


def _latest_run(work_root: Path) -> Path | None:
    if not work_root.exists():
        return None
    runs = sorted(work_root.glob("a-*/*.run"), key=lambda path: path.stat().st_mtime, reverse=True)
    return runs[0] if runs else None


def _copy_when_available(src: Path, dst: Path, *, timeout: float) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            shutil.copy2(src, dst)
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(0.5)
    raise PermissionError(f"Timed out waiting for official output to unlock: {src}") from last_error


def _copy_output_folder(src_dir: Path, dst_dir: Path) -> list[str]:
    if not src_dir.exists():
        return []
    copied: list[str] = []
    for src in sorted(path for path in src_dir.rglob("*") if path.is_file()):
        rel = src.relative_to(src_dir)
        dst = dst_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        _copy_when_available(src, dst, timeout=10.0)
        copied.append(str(dst))
    return copied


def _read_output_text(window) -> str:
    values: list[str] = []
    for control in window.descendants():
        class_name = control.class_name()
        if control.element_info.control_type != "Edit" and "RichEdit" not in class_name:
            continue
        try:
            legacy = control.legacy_properties()
            value = legacy.get("Value") or ""
        except Exception:
            value = control.window_text() or ""
        if value:
            values.append(value)
    return "\n".join(values)


def _close_window(window) -> None:
    try:
        window.close()
        time.sleep(1)
    except Exception:
        return
    for dialog in Desktop(backend="uia").windows():
        try:
            if dialog.process_id() != window.process_id():
                continue
        except Exception:
            continue
        for control in dialog.descendants():
            if control.element_info.control_type == "Button" and control.window_text() in {"否", "No", "不保存"}:
                control.click_input()
                return


if __name__ == "__main__":
    raise SystemExit(main())
