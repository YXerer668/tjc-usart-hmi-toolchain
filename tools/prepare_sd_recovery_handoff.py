from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "reverse_usarthmi" / "recovery_sd_card"
SOURCE_TFT = SOURCE_DIR / "lcd_test.tft"
SOURCE_README = SOURCE_DIR / "README_恢复说明.md"
DEFAULT_OUT_DIR = Path.home() / "Desktop" / "TJC_SD_RECOVERY_CURRENT"
DEFAULT_REPORT = ROOT / "examples" / "lifecycle_runtime_smoke" / "sd_recovery_handoff_2026-05-21.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a desktop-friendly SD recovery handoff bundle for the current TJC screen.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--report-out", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    out_dir = Path(args.out_dir).resolve()
    report_out = Path(args.report_out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    copied_tft = out_dir / "lcd_test.tft"
    copied_readme = out_dir / "README_恢复说明.md"
    shutil.copy2(SOURCE_TFT, copied_tft)
    shutil.copy2(SOURCE_README, copied_readme)

    after_commands = out_dir / "恢复后运行.txt"
    after_commands.write_text(
        "\n".join(
            [
                "恢复完成后按顺序执行：",
                f'1. python "{ROOT / "tools" / "sd_recovery_state.py"}" mark-pending --note "sd recovery in progress"',
                "2. 断电，拔出 SD 卡，再上电。",
                f'3. python "{ROOT / "tools" / "sd_recovery_state.py"}" clear --note "sd removed and clean boot confirmed"',
                f'4. python "{ROOT / "tools" / "recover_then_run_seed_side_runtime_limit.py"}" --out-dir "{ROOT / "reverse_usarthmi" / "recover_then_seed_side_run_20260521"}" --capture',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    after_ps1 = out_dir / "恢复后运行.ps1"
    after_ps1.write_text(
        "\n".join(
            [
                '$ErrorActionPreference = "Stop"',
                f'python "{ROOT / "tools" / "sd_recovery_state.py"}" mark-pending --note "sd recovery in progress"',
                'Write-Host "现在请断电、拔出 SD 卡、重新上电。完成后按回车继续..."',
                'Read-Host | Out-Null',
                f'python "{ROOT / "tools" / "sd_recovery_state.py"}" clear --note "sd removed and clean boot confirmed"',
                f'python "{ROOT / "tools" / "recover_then_run_seed_side_runtime_limit.py"}" --out-dir "{ROOT / "reverse_usarthmi" / "recover_then_seed_side_run_20260521"}" --capture',
                'Write-Host "完成。按回车关闭..."',
                'Read-Host | Out-Null',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    after_cmd = out_dir / "恢复后运行.cmd"
    after_cmd.write_text(
        "\r\n".join(
            [
                "@echo off",
                'setlocal',
                f'powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "{after_ps1}"',
                "pause",
            ]
        )
        + "\r\n",
        encoding="utf-8",
    )

    verify_ps1 = out_dir / "校验恢复包.ps1"
    verify_ps1.write_text(
        "\n".join(
            [
                '$ErrorActionPreference = "Stop"',
                f'python "{ROOT / "tools" / "verify_sd_recovery_handoff.py"}" --bundle-dir "{out_dir}"',
                'Write-Host "校验完成。按回车关闭..."',
                'Read-Host | Out-Null',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    verify_cmd = out_dir / "校验恢复包.cmd"
    verify_cmd.write_text(
        "\r\n".join(
            [
                "@echo off",
                "setlocal",
                f'powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "{verify_ps1}"',
                "pause",
            ]
        )
        + "\r\n",
        encoding="utf-8",
    )

    ordered_verify_cmd = out_dir / "00_先双击_校验恢复包.cmd"
    shutil.copy2(verify_cmd, ordered_verify_cmd)
    ordered_after_cmd = out_dir / "01_SD恢复完成后双击_继续验证.cmd"
    shutil.copy2(after_cmd, ordered_after_cmd)

    status_summary = out_dir / "当前状态摘要.md"
    status_summary.write_text(
        "\n".join(
            [
                "# 当前状态摘要",
                "",
                "- 目标屏: `TJC8048X543_011C`",
                "- 当前本地状态: `connect/sendme/get dim` 全静默",
                "- 常见与高波特率扫描也都静默",
                "- 官方 GUI 下载按钮多方法点击仍不切换到运行态",
                "- public `whmi-wri` 入口初始 ACK 也没有出现",
                "",
                "## 推荐顺序",
                "",
                "1. 先双击 `00_先双击_校验恢复包.cmd`",
                "2. 按 `README_恢复说明.md` 用 SD 卡恢复",
                "3. 恢复完成后双击 `01_SD恢复完成后双击_继续验证.cmd`",
                "",
                "## 说明",
                "",
                "- 当前软件侧自动化已经基本见底。",
                "- 恢复后脚本会继续跑串口检查和 seed-side runtime falsification。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    manifest = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "handoff-prepared",
        "bundle_dir": str(out_dir),
        "copied_files": {
            "lcd_test.tft": {
                "path": str(copied_tft),
                "bytes": copied_tft.stat().st_size,
                "sha256": _sha256(copied_tft),
            },
            "README_恢复说明.md": str(copied_readme),
            "恢复后运行.txt": str(after_commands),
            "恢复后运行.ps1": str(after_ps1),
            "恢复后运行.cmd": str(after_cmd),
            "校验恢复包.ps1": str(verify_ps1),
            "校验恢复包.cmd": str(verify_cmd),
            "00_先双击_校验恢复包.cmd": str(ordered_verify_cmd),
            "01_SD恢复完成后双击_继续验证.cmd": str(ordered_after_cmd),
            "当前状态摘要.md": str(status_summary),
        },
        "source_files": {
            "repo_tft": str(SOURCE_TFT),
            "repo_tft_sha256": _sha256(SOURCE_TFT),
            "repo_readme": str(SOURCE_README),
        },
        "notes": [
            "This bundle is intended for physical/SD-card recovery because the panel is currently transport-silent even at the public whmi-wri entrypoint.",
            "After the SD recovery finishes and the SD card is removed, run the listed follow-up commands so Codex can continue with the seed-side runtime limitation probes.",
        ],
    }

    manifest_path = out_dir / "package_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    zip_path = Path(shutil.make_archive(str(out_dir), "zip", root_dir=out_dir))

    report = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "handoff-prepared",
        "bundle_dir": str(out_dir),
        "bundle_zip": str(zip_path),
        "manifest_path": str(manifest_path),
        "repo_source_tft": str(SOURCE_TFT.relative_to(ROOT)),
        "repo_source_sha256": _sha256(SOURCE_TFT),
        "followup_command_file": str(after_commands),
        "followup_powershell_file": str(after_ps1),
        "followup_cmd_file": str(after_cmd),
        "verify_powershell_file": str(verify_ps1),
        "verify_cmd_file": str(verify_cmd),
        "ordered_verify_cmd": str(ordered_verify_cmd),
        "ordered_followup_cmd": str(ordered_after_cmd),
        "status_summary_file": str(status_summary),
    }
    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
