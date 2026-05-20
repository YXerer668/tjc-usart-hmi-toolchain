from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import win32api
from pywinauto.application import Application
from pywinauto.keyboard import send_keys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.official_gui_toolbox_probe import (  # noqa: E402
    _drag_screen,
    _load_page,
    _post_click_screen,
    _wait_main_window,
)
from tools.official_hmi_gui_create_widgets import (  # noqa: E402
    _click_save_prompt,
    _wait_for_process_window_closed,
)
from tools.official_hmi_session import close_or_kill_existing_official_window  # noqa: E402
from tools.official_page1_advanced_gui_create import _post_wheel_screen  # noqa: E402


DEFAULT_EXE = Path(r"C:\Program Files (x86)\USART HMI\USART HMI.exe")
DEFAULT_MULTI_PAGE_HMI = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_31_multi_page_navigation\lcd_test.HMI")
DEFAULT_PAGE_LIST_X = 3600
DEFAULT_PAGE1_ROW_Y = 247
DEFAULT_TOOLBOX_X = 87
DEFAULT_CANVAS_X = 712
DEFAULT_CANVAS_Y = 432


def _snapshot(blocks: list[dict[str, Any]]) -> set[tuple[str | None, str | None, int | None]]:
    return {
        (
            block.get("objname"),
            block.get("type_code"),
            int(block.get("id")) if block.get("id") is not None else None,
        )
        for block in blocks
    }


def _new_blocks(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> list[dict[str, Any]]:
    before_keys = _snapshot(before)
    return [
        block
        for block in after
        if (
            block.get("objname"),
            block.get("type_code"),
            int(block.get("id")) if block.get("id") is not None else None,
        )
        not in before_keys
    ]


def _save_current_hmi() -> None:
    win32api.keybd_event(0x11, 0, 0, 0)  # Ctrl down
    time.sleep(0.03)
    win32api.keybd_event(0x53, 0, 0, 0)  # S down
    time.sleep(0.03)
    win32api.keybd_event(0x53, 0, 2, 0)  # S up
    time.sleep(0.03)
    win32api.keybd_event(0x11, 0, 2, 0)  # Ctrl up


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a single-session official USART HMI toolbox scan without reopening the GUI for every probe."
    )
    parser.add_argument("--seed-hmi", type=Path, default=DEFAULT_MULTI_PAGE_HMI)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE)
    parser.add_argument("--page-index", type=int, default=1)
    parser.add_argument("--page-list-x", type=int, default=DEFAULT_PAGE_LIST_X)
    parser.add_argument("--page-row-y", type=int, default=DEFAULT_PAGE1_ROW_Y)
    parser.add_argument("--toolbox-x", type=int, default=DEFAULT_TOOLBOX_X)
    parser.add_argument("--canvas-x", type=int, default=DEFAULT_CANVAS_X)
    parser.add_argument("--canvas-y", type=int, default=DEFAULT_CANVAS_Y)
    parser.add_argument("--drag-scroll-start-y", type=int, default=238)
    parser.add_argument("--drag-scroll-end-y", type=int, default=640)
    parser.add_argument("--y-values", nargs="+", type=int, required=True)
    parser.add_argument("--wheel-values", nargs="+", type=int, default=[0])
    parser.add_argument("--timeout-s", type=float, default=45.0)
    args = parser.parse_args()

    seed_hmi = args.seed_hmi.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    output_hmi = out_dir / "lcd_test.HMI"
    report_path = out_dir / "session_scan_report.json"

    close_or_kill_existing_official_window(output_hmi)
    shutil.copy2(seed_hmi, output_hmi)
    before_blocks = _load_page(output_hmi, page_index=args.page_index)

    app = Application(backend="uia").start(
        f'"{args.exe.resolve()}" "{output_hmi}"',
        work_dir=str(args.exe.resolve().parent),
    )
    window = _wait_main_window(app.process, output_hmi, timeout=args.timeout_s)
    window.maximize()
    time.sleep(2.0)
    rect = window.rectangle()

    page_click = _post_click_screen(rect.left + args.page_list_x, rect.top + args.page_row_y)
    time.sleep(0.6)

    items: list[dict[str, Any]] = []
    for y in args.y_values:
        for wheel in args.wheel_values:
            drag_action = _drag_screen(
                (rect.left + args.toolbox_x + 235, rect.top + int(args.drag_scroll_start_y)),
                (rect.left + args.toolbox_x + 235, rect.top + int(args.drag_scroll_end_y)),
            )
            time.sleep(0.25)
            wheel_action = None
            if wheel:
                wheel_action = _post_wheel_screen(
                    rect.left + args.toolbox_x,
                    rect.top + int(y),
                    detents=int(wheel),
                )
                time.sleep(0.25)
            toolbox_click = _post_click_screen(rect.left + args.toolbox_x, rect.top + int(y))
            time.sleep(0.3)
            canvas_click = _post_click_screen(rect.left + args.canvas_x, rect.top + args.canvas_y)
            items.append(
                {
                    "tool_rel_y": int(y),
                    "toolbox_wheel": int(wheel),
                    "drag_action": drag_action,
                    "wheel_action": wheel_action,
                    "toolbox_click": toolbox_click,
                    "canvas_click": canvas_click,
                }
            )
            time.sleep(0.8)

    screenshot_path = out_dir / "after_session_scan.png"
    window.capture_as_image().save(str(screenshot_path))
    main_rect = window.rectangle()
    window.close()
    time.sleep(0.8)
    save_prompt_seen = True
    try:
        _click_save_prompt(app.process, main_rect, timeout=12.0)
    except TimeoutError:
        save_prompt_seen = False
    forced_kill = False
    if not save_prompt_seen:
        app.kill()
        forced_kill = True
        time.sleep(0.8)
    else:
        try:
            _wait_for_process_window_closed(app.process, timeout=30.0)
        except TimeoutError:
            app.kill()
            forced_kill = True
            time.sleep(0.8)

    after_blocks = _load_page(output_hmi, page_index=args.page_index)
    added_blocks = _new_blocks(before_blocks, after_blocks)

    report = {
        "schema_version": 1,
        "mode": "official_gui_toolbox_session_scan",
        "seed_hmi": str(seed_hmi),
        "output_hmi": str(output_hmi),
        "page_index": args.page_index,
        "page_click": page_click,
        "screenshot": str(screenshot_path),
        "save_prompt_seen": save_prompt_seen,
        "forced_kill_after_timeout": forced_kill,
        "before_page_blocks": before_blocks,
        "after_page_blocks": after_blocks,
        "added_blocks": added_blocks,
        "items": items,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
