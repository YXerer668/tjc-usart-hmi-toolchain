from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from usarthmi.hmi_donor_patch import (  # noqa: E402
    SHADOW_SYNC_MODE_CASE83_DELETE_B1_GUI,
    _entry_data,
    _rebuild_hmi_container_with_index_overrides,
    _summarize_pa_like_entries,
    patch_hmi_donor,
)
from usarthmi.hmi_inspect import inspect_hmi  # noqa: E402


FIXTURE_DIR = REPO_ROOT / "reverse_usarthmi" / "hmi_donor_lowlevel_probe_20260522" / "fixture_corpus" / "fixtures" / "page0_basic_delete"
DONOR_HMI = FIXTURE_DIR / "input_donor.HMI"
BASELINE_HMI = FIXTURE_DIR / "generated.HMI"
DEFAULT_OUT_DIR = REPO_ROOT / "reverse_usarthmi" / "case83_shadow_sync_matrix_20260523"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the current case83 shadow-sync experiment matrix.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Output directory for matrix artifacts")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_case83_shadow_sync_matrix(args.out_dir.resolve())
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def build_case83_shadow_sync_matrix(out_dir: Path) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    variants: list[tuple[str, Callable[[Path], Path]]] = [
        ("baseline_compile_ok_gui_fail", _build_baseline_variant),
        ("gui_shadow_sync_shrink", _build_gui_shadow_sync_variant),
        ("gui_shadow_sync_dualshadow", _build_dualshadow_variant),
        ("gui_shadow_sync_idx11_named", _build_idx11_named_variant),
        ("gui_shadow_sync_hide_idx13", _build_hide_idx13_variant),
    ]
    rows = []
    for name, builder in variants:
        variant_dir = out_dir / name
        if variant_dir.exists():
            shutil.rmtree(variant_dir)
        variant_dir.mkdir(parents=True, exist_ok=True)
        generated_hmi = builder(variant_dir)
        rows.append(_probe_variant(name, generated_hmi, variant_dir))

    summary = {
        "schema_version": 1,
        "mode": "case83_shadow_sync_matrix",
        "donor_hmi": str(DONOR_HMI),
        "baseline_hmi": str(BASELINE_HMI),
        "variants": rows,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "summary.md").write_text(_render_summary_md(summary), encoding="utf-8")
    return summary


def _build_baseline_variant(out_dir: Path) -> Path:
    target = out_dir / "generated.HMI"
    shutil.copy2(BASELINE_HMI, target)
    return target


def _build_gui_shadow_sync_variant(out_dir: Path) -> Path:
    report = patch_hmi_donor(
        donor_hmi=DONOR_HMI,
        out_dir=out_dir,
        delete_objects=["b1"],
        probe_lowlevel=False,
        probe_reopen=False,
        shadow_sync_mode=SHADOW_SYNC_MODE_CASE83_DELETE_B1_GUI,
    )
    return Path(report["output_hmi"])


def _build_dualshadow_variant(out_dir: Path) -> Path:
    base_hmi = _build_gui_shadow_sync_variant(out_dir)
    donor_raw = DONOR_HMI.read_bytes()
    donor_insp = inspect_hmi(DONOR_HMI)
    donor_shadow = _entry_data(donor_raw, next(entry for entry in donor_insp.entries if entry.index == 11))
    return _rewrite_variant(base_hmi, out_dir / "generated.HMI", overrides={13: {"data": donor_shadow}})


def _build_idx11_named_variant(out_dir: Path) -> Path:
    base_hmi = _build_gui_shadow_sync_variant(out_dir)
    return _rewrite_variant(
        base_hmi,
        out_dir / "generated.HMI",
        overrides={
            11: {
                "name_bytes": b"0.pa" + (b"\x00" * 12),
                "field3": 0x00B3BF00,
            },
            14: {
                "name_bytes": b"\x00.pa" + (b"\x00" * 12),
                "field3": 0x05111601,
            },
        },
    )


def _build_hide_idx13_variant(out_dir: Path) -> Path:
    base_hmi = _build_gui_shadow_sync_variant(out_dir)
    return _rewrite_variant(base_hmi, out_dir / "generated.HMI", overrides={13: {"name_bytes": b"\x00" * 16}})


def _rewrite_variant(source_hmi: Path, out_path: Path, *, overrides: dict[int, dict[str, object]]) -> Path:
    raw = source_hmi.read_bytes()
    inspection = inspect_hmi(source_hmi)
    rewritten = _rebuild_hmi_container_with_index_overrides(raw, inspection.entries, overrides=overrides)
    out_path.write_bytes(rewritten)
    return out_path


def _probe_variant(name: str, generated_hmi: Path, variant_dir: Path) -> dict[str, object]:
    inspection = inspect_hmi(generated_hmi)
    raw = generated_hmi.read_bytes()
    pre_candidates = _summarize_pa_like_entries(raw, inspection.entries)

    lowlevel_input = variant_dir / "lowlevel_input.HMI"
    shutil.copy2(generated_hmi, lowlevel_input)
    lowlevel = _run_json_tool(
        [
            sys.executable,
            str(REPO_ROOT / "tools" / "official_hmi_lowlevel_probe.py"),
            str(lowlevel_input),
            "--out-dir",
            str(variant_dir / "official_lowlevel_probe"),
        ]
    )

    reopen_input = variant_dir / "reopen_input.HMI"
    shutil.copy2(generated_hmi, reopen_input)
    reopen = _run_json_tool(
        [
            sys.executable,
            str(REPO_ROOT / "tools" / "official_hmi_reopen_probe.py"),
            str(reopen_input),
            "--out-dir",
            str(variant_dir / "official_reopen_probe"),
            "--page-index",
            "0",
            "--timeout-s",
            "120",
        ]
    )

    before_objects = [{"name": item["objname"], "type": item["type_code"]} for item in reopen["before_blocks"]]
    after_objects = [{"name": item["objname"], "type": item["type_code"]} for item in reopen["after_blocks"]]
    gui_reopen_ok = not reopen["changed"] and before_objects == after_objects
    compile_info = lowlevel["compile_lowlevel"]

    return {
        "name": name,
        "generated_hmi": str(generated_hmi),
        "pre_probe_pa_candidates": pre_candidates,
        "open_lowlevel_ok": bool(lowlevel["accepted_by_open_lowlevel"]),
        "compile_lowlevel_ok": bool(lowlevel["accepted_by_compile_lowlevel"]),
        "compiled_output_size": compile_info.get("compiled_output_size"),
        "empty_shell_class": bool(compile_info.get("empty_shell_class")),
        "gui_reopen_ok": bool(gui_reopen_ok),
        "gui_reopen_changed": bool(reopen["changed"]),
        "gui_reopen_before_objects": before_objects,
        "gui_reopen_after_objects": after_objects,
        "lowlevel_probe_json": str(variant_dir / "official_lowlevel_probe"),
        "reopen_probe_json": str(variant_dir / "official_reopen_probe" / "reopen_probe.json"),
    }


def _run_json_tool(command: list[str]) -> dict[str, object]:
    proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode:
        raise RuntimeError(
            f"Command failed with exit code {proc.returncode}: {' '.join(command)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


def _render_summary_md(summary: dict[str, object]) -> str:
    variants = summary["variants"]

    def yesno(value: bool) -> str:
        return "yes" if value else "no"

    lines = [
        "# Case83 Shadow Sync Matrix",
        "",
        "| variant | open-lowlevel | compile-lowlevel | gui-reopen | empty-shell | before objects | after objects |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in variants:
        before_objects = ", ".join(f"{item['name']}:{item['type']}" for item in row["gui_reopen_before_objects"])
        after_objects = ", ".join(f"{item['name']}:{item['type']}" for item in row["gui_reopen_after_objects"])
        lines.append(
            f"| {row['name']} | {yesno(row['open_lowlevel_ok'])} | {yesno(row['compile_lowlevel_ok'])} | "
            f"{yesno(row['gui_reopen_ok'])} | {yesno(row['empty_shell_class'])} | {before_objects} | {after_objects} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
