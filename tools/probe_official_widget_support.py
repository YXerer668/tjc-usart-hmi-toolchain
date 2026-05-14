from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from usarthmi.editor import _rebuild_hmi_container
from usarthmi.hmi_inspect import extract_hmi, inspect_hmi
from usarthmi.page_format import parse_page_data
from usarthmi.tft_patch import _header, _header_int
from usarthmi.tft_toolchain import inspect_tft


DEFAULT_SEED = Path(r"D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Clone one widget from an official sample HMI into the current seed "
            "and optionally ask the official compiler whether the target model emits it."
        )
    )
    parser.add_argument("--source-hmi", type=Path, required=True, help="Official/sample HMI containing the widget")
    parser.add_argument("--source-page", default="0.pa", help="Source page entry to read from the sample HMI")
    parser.add_argument("--object-name", required=True, help="Object name to clone from the source HMI")
    parser.add_argument("--case-dir", type=Path, required=True, help="Output case directory")
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED, help="Current seed HMI")
    parser.add_argument("--target-name", help="Object name in the generated seed HMI; defaults to --object-name")
    parser.add_argument("--x", type=int, default=64)
    parser.add_argument("--y", type=int, default=96)
    parser.add_argument("--w", type=int, default=260)
    parser.add_argument("--h", type=int, default=160)
    parser.add_argument("--compile-official", action="store_true", help="Run tools/official_hmi_compile_capture.py")
    parser.add_argument("--timeout-s", type=float, default=120.0)
    parser.add_argument("--close", action="store_true", help="Close the official GUI after capture")
    args = parser.parse_args()

    result = probe_widget(
        seed=args.seed,
        source_hmi=args.source_hmi,
        source_page=args.source_page,
        object_name=args.object_name,
        target_name=args.target_name or args.object_name,
        case_dir=args.case_dir,
        rect=(args.x, args.y, args.w, args.h),
        compile_official=args.compile_official,
        timeout_s=args.timeout_s,
        close=args.close,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def probe_widget(
    *,
    seed: Path,
    source_hmi: Path,
    source_page: str,
    object_name: str,
    target_name: str,
    case_dir: Path,
    rect: tuple[int, int, int, int],
    compile_official: bool,
    timeout_s: float,
    close: bool,
) -> dict[str, Any]:
    case_dir = case_dir.resolve()
    case_dir.mkdir(parents=True, exist_ok=True)

    hmi_path, target_type, target_count = _write_grafted_hmi(
        seed=seed.resolve(),
        source_hmi=source_hmi.resolve(),
        source_page=source_page,
        object_name=object_name,
        target_name=target_name,
        case_dir=case_dir,
        rect=rect,
    )
    extract_dir = case_dir / "extract"
    written = extract_hmi(hmi_path, extract_dir)

    result: dict[str, Any] = {
        "seed": str(seed.resolve()),
        "source_hmi": str(source_hmi.resolve()),
        "case_dir": str(case_dir),
        "hmi": str(hmi_path),
        "extract_count": len(written),
        "object_name": target_name,
        "type_code": target_type,
        "hmi_object_count": target_count,
    }

    if compile_official:
        official = _compile_with_official_gui(
            hmi_path,
            out_dir=case_dir / "official_gui_probe",
            timeout_s=timeout_s,
            close=close,
        )
        run_path = Path(str(official["captured_run"]))
        tft_path = case_dir / "lcd_test.tft"
        shutil.copy2(run_path, tft_path)
        result["official_compile"] = official
        result["tft"] = str(tft_path)
        result["support_probe"] = _probe_compiled_tft(
            tft_path,
            expected_object_count=target_count,
            type_code=target_type,
            object_id=target_count - 1,
        )

    return result


def _write_grafted_hmi(
    *,
    seed: Path,
    source_hmi: Path,
    source_page: str,
    object_name: str,
    target_name: str,
    case_dir: Path,
    rect: tuple[int, int, int, int],
) -> tuple[Path, str | None, int]:
    seed_raw = seed.read_bytes()
    seed_inspection = inspect_hmi(seed)
    seed_page_entry = _entry(seed_inspection.entries, "0.pa")
    seed_page = parse_page_data(seed_raw[seed_page_entry.data_offset : seed_page_entry.data_offset + seed_page_entry.length])

    source_raw = source_hmi.read_bytes()
    source_inspection = inspect_hmi(source_hmi)
    source_page_entry = _entry(source_inspection.entries, source_page)
    source_page_data = parse_page_data(
        source_raw[source_page_entry.data_offset : source_page_entry.data_offset + source_page_entry.length]
    )
    block = next((item for item in source_page_data.blocks if item.objname == object_name), None)
    if block is None:
        names = ", ".join(str(item.objname) for item in source_page_data.blocks)
        raise ValueError(f"Object {object_name!r} not found in source page {source_page!r}; available: {names}")

    cloned = block.clone()
    object_id = len(seed_page.blocks)
    x, y, w, h = rect
    cloned.set_int("id", object_id, width=1)
    cloned.set_string("objname", target_name)
    cloned.set_int("x", x, width=2)
    cloned.set_int("y", y, width=2)
    cloned.set_int("w", w, width=2)
    cloned.set_int("h", h, width=2)
    cloned.set_int("endx", x + w - 1, width=2)
    cloned.set_int("endy", y + h - 1, width=2)
    seed_page.blocks.append(cloned)

    hmi_path = case_dir / "lcd_test.HMI"
    hmi_path.write_bytes(
        _rebuild_hmi_container(seed_raw, seed_inspection.entries, replacements={"0.pa": seed_page.serialize()}, additions=[])
    )
    return hmi_path, cloned.type_code, len(seed_page.blocks)


def _compile_with_official_gui(hmi_path: Path, *, out_dir: Path, timeout_s: float, close: bool) -> dict[str, Any]:
    command = [
        sys.executable,
        str(Path(__file__).with_name("official_hmi_compile_capture.py")),
        str(hmi_path),
        "--out-dir",
        str(out_dir),
        "--timeout-s",
        str(timeout_s),
    ]
    if close:
        command.append("--close")
    proc = subprocess.run(command, capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(
            "Official compile probe failed with "
            f"exit code {proc.returncode}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


def _probe_compiled_tft(
    tft_path: Path,
    *,
    expected_object_count: int,
    type_code: str | None,
    object_id: int,
) -> dict[str, Any]:
    raw = tft_path.read_bytes()
    inspection = inspect_tft(tft_path)
    header2 = _header(inspection, "Header2")
    object_start = _header_int(header2, "unknown_objects_address")
    picture_start = _header_int(header2, "pictures_address")
    compiled_count = _header_int(header2, "audios_count")
    tail = raw[object_start:picture_start] if object_start is not None and picture_start is not None else b""
    type_id_hits: list[int] = []
    if type_code:
        needle = bytes([ord(type_code), object_id])
        cursor = 0
        while True:
            hit = tail.find(needle, cursor)
            if hit < 0:
                break
            type_id_hits.append(hit)
            cursor = hit + 1

    return {
        "model": inspection.get("model"),
        "compiled_object_count": compiled_count,
        "expected_object_count": expected_object_count,
        "object_region_size": len(tail),
        "accepted_by_current_target": compiled_count == expected_object_count,
        "type_id_hits": [f"0x{item:X}" for item in type_id_hits],
    }


def _entry(entries, name: str):
    entry = next((item for item in entries if item.name == name), None)
    if entry is None:
        raise ValueError(f"Entry {name!r} not found")
    return entry


if __name__ == "__main__":
    raise SystemExit(main())
