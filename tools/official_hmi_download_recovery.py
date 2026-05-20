from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from pywinauto import Desktop
from pywinauto.keyboard import send_keys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.official_hmi_compile_capture import (
    DEFAULT_EXE,
    DEFAULT_WORK_ROOT,
    _activate_control,
    _click_compile,
    _click_control,
    _click_download,
    _dismiss_known_dialogs,
    _post_click_screen,
    _wait_for_compile_result,
    _wait_main_window,
)
from tools.official_hmi_session import (
    close_or_kill_existing_official_window,
    start_or_attach_official_window,
    stabilize_reused_window,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile one official USART HMI project, open the embedded serial-download panel, "
            "and optionally click the real '联机并开始下载' recovery path."
        )
    )
    parser.add_argument("hmi", type=Path, help="Input .HMI file")
    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE)
    parser.add_argument("--work-root", type=Path, default=DEFAULT_WORK_ROOT)
    parser.add_argument("--port", default="COM36")
    parser.add_argument("--download-baud", default="921600")
    parser.add_argument("--compile-timeout-s", type=float, default=120.0)
    parser.add_argument("--download-wait-s", type=float, default=240.0)
    parser.add_argument("--start-download", action="store_true")
    parser.add_argument("--keep-open", action="store_true")
    args = parser.parse_args()

    hmi_path = args.hmi.resolve()
    exe_path = args.exe.resolve()
    if not hmi_path.exists():
        raise SystemExit(f"HMI does not exist: {hmi_path}")
    if not exe_path.exists():
        raise SystemExit(f"USART HMI.exe does not exist: {exe_path}")

    close_or_kill_existing_official_window(hmi_path)
    app, window, started_new = start_or_attach_official_window(
        exe_path,
        hmi_path,
        wait_main_window=_wait_main_window,
        timeout=30.0,
    )
    if not started_new:
        stabilize_reused_window(window)
    window.maximize()
    time.sleep(1.0)
    _dismiss_known_dialogs(app.process, timeout=8)

    start_time = time.time()
    before = _latest_run(args.work_root)
    _click_compile(window)
    run_path, output_text = _wait_for_compile_result(
        window,
        args.work_root,
        after_time=start_time,
        before_path=before,
        timeout=args.compile_timeout_s,
    )
    _click_download(window)
    time.sleep(1.5)

    panel = _find_download_panel(window)
    controls = _download_panel_controls(panel)
    configured = _configure_download_panel(panel, args.port, args.download_baud)

    started = False
    start_attempt: dict[str, object] | None = None
    status_samples: list[list[str]] = []
    if args.start_download:
        start_attempt = _click_download_start(panel)
        started = True
        status_samples = _wait_after_start(panel, wait_s=args.download_wait_s)

    result = {
        "hmi": str(hmi_path),
        "official_exe": str(exe_path),
        "reused_existing_window": not started_new,
        "work_run": str(run_path),
        "output_after": output_text,
        "download_panel_controls": controls,
        "configured_port": args.port,
        "configured_download_baud": args.download_baud,
        "selected_port": configured["selected_port"],
        "selected_download_baud": configured["selected_download_baud"],
        "start_download_clicked": started,
        "start_attempt": start_attempt,
        "status_tail": status_samples[-10:],
    }

    if not args.keep_open:
        try:
            app.kill()
        except Exception:
            pass

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _latest_run(work_root: Path) -> Path | None:
    if not work_root.exists():
        return None
    runs = sorted(work_root.glob("a-*/*.run"), key=lambda path: path.stat().st_mtime, reverse=True)
    return runs[0] if runs else None


def _find_download_panel(window):
    for control in window.descendants():
        try:
            if control.element_info.control_type == "Window" and control.window_text() == "串口下载":
                return control
        except Exception:
            continue
    raise RuntimeError("Embedded official download panel was not found")


def _download_panel_controls(panel) -> list[dict[str, object]]:
    controls: list[dict[str, object]] = []
    for control in panel.descendants():
        try:
            controls.append(
                {
                    "type": control.element_info.control_type,
                    "text": (control.window_text() or "").strip(),
                    "rect": [
                        control.rectangle().left,
                        control.rectangle().top,
                        control.rectangle().right,
                        control.rectangle().bottom,
                    ],
                }
            )
        except Exception:
            continue
    return controls


def _configure_download_panel(panel, port: str, download_baud: str) -> dict[str, str]:
    combos = []
    for control in panel.descendants():
        try:
            if control.element_info.control_type != "ComboBox":
                continue
            rect = control.rectangle()
            if rect.top < panel.rectangle().top + 60 or rect.top > panel.rectangle().bottom - 300:
                continue
            combos.append((rect.left, control))
        except Exception:
            continue
    combos.sort(key=lambda item: item[0])
    if len(combos) < 2:
        raise RuntimeError("Did not find the expected port/baud combo boxes in the embedded download panel")

    port_combo = combos[0][1]
    baud_combo = combos[1][1]
    _select_combo_entry(port_combo, port)
    time.sleep(0.4)
    _select_combo_entry(baud_combo, download_baud)
    time.sleep(0.4)
    return {
        "selected_port": _combo_selected_text(port_combo),
        "selected_download_baud": _combo_selected_text(baud_combo),
    }


def _select_combo_entry(combo, value: str) -> None:
    try:
        wrapper = combo.wrapper_object()
    except Exception:
        wrapper = None

    try:
        if wrapper is not None and hasattr(wrapper, "select"):
            wrapper.select(value)
            time.sleep(0.3)
            selected = _combo_selected_text(combo)
            if selected == value:
                return
    except Exception:
        pass

    _click_control(combo)
    time.sleep(0.3)
    try:
        if wrapper is not None and hasattr(wrapper, "expand"):
            wrapper.expand()
            time.sleep(0.3)
    except Exception:
        pass

    item = _find_global_list_item(value, anchor_rect=combo.rectangle())
    if item is not None:
        _click_control(item)
        time.sleep(0.5)
        selected = _combo_selected_text(combo)
        if selected == value:
            return

    _click_control(combo)
    time.sleep(0.2)
    send_keys("^a{BACKSPACE}", pause=0.02)
    send_keys(f"{value}{{ENTER}}", with_spaces=True, pause=0.02)
    time.sleep(0.5)
    selected = _combo_selected_text(combo)
    if selected == value:
        return
    raise RuntimeError(f"Unable to select combo entry {value!r}; current selection is {selected!r}")


def _combo_selected_text(combo) -> str:
    try:
        wrapper = combo.wrapper_object()
        if hasattr(wrapper, "selected_text"):
            text = wrapper.selected_text() or ""
            if text:
                return text.strip()
    except Exception:
        pass
    try:
        legacy = combo.legacy_properties()
        value = legacy.get("Value")
        if isinstance(value, str):
            return value.strip()
    except Exception:
        pass
    try:
        return (combo.window_text() or "").strip()
    except Exception:
        return ""


def _find_global_list_item(text: str, *, anchor_rect) -> object | None:
    candidates = []
    for window in Desktop(backend="uia").windows():
        for control in window.descendants():
            try:
                if control.element_info.control_type != "ListItem":
                    continue
                if (control.window_text() or "").strip() != text:
                    continue
                rect = control.rectangle()
            except Exception:
                continue
            distance = abs(rect.left - anchor_rect.left) + abs(rect.top - anchor_rect.bottom)
            candidates.append((distance, control))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _click_download_start(panel) -> dict[str, object]:
    attempts: list[dict[str, object]] = []
    for attempt_index in range(1, 4):
        button, before_text = _find_download_button(panel)
        if button is None:
            break
        if before_text == "停止":
            return {
                "transitioned": True,
                "final_text": before_text,
                "attempts": attempts,
            }

        _activate_control(button)
        after_text = _wait_download_button_text(panel, timeout_s=2.0)
        attempts.append(
            {
                "attempt": attempt_index,
                "method": "activate_control",
                "before_text": before_text,
                "after_text": after_text,
            }
        )
        if after_text == "停止":
            return {
                "transitioned": True,
                "final_text": after_text,
                "attempts": attempts,
            }

        rect = button.rectangle()
        _post_click_screen((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
        after_text = _wait_download_button_text(panel, timeout_s=2.0)
        attempts.append(
            {
                "attempt": attempt_index,
                "method": "post_click_screen_center",
                "before_text": before_text,
                "after_text": after_text,
            }
        )
        if after_text == "停止":
            return {
                "transitioned": True,
                "final_text": after_text,
                "attempts": attempts,
            }

    final_text = _wait_download_button_text(panel, timeout_s=0.5)
    return {
        "transitioned": final_text == "停止",
        "final_text": final_text,
        "attempts": attempts,
    }


def _find_download_button(panel):
    for control in panel.descendants():
        try:
            if control.element_info.control_type != "Button":
                continue
            text = (control.window_text() or "").strip()
            if text in {"联机并开始下载", "停止"}:
                return control, text
        except Exception:
            continue
    return None, None


def _wait_download_button_text(panel, *, timeout_s: float) -> str | None:
    deadline = time.time() + timeout_s
    latest: str | None = None
    while time.time() < deadline:
        _button, text = _find_download_button(panel)
        latest = text
        if text == "停止":
            return text
        time.sleep(0.1)
    return latest


def _visible_texts(panel) -> list[str]:
    texts: list[str] = []
    for control in panel.descendants():
        try:
            text = (control.window_text() or "").strip()
        except Exception:
            continue
        if text:
            texts.append(text)
    return texts


def _wait_after_start(panel, *, wait_s: float) -> list[list[str]]:
    samples: list[list[str]] = []
    start = time.time()
    while time.time() - start < wait_s:
        texts = _visible_texts(panel)
        if texts:
            samples.append(texts)
        time.sleep(1.0)
    return samples


if __name__ == "__main__":
    raise SystemExit(main())
