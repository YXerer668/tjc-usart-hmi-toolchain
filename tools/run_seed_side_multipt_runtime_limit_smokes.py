from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LIVE_TFT_SMOKE = ROOT / "tools" / "live_tft_smoke.py"
FS_TFT = ROOT / "reverse_usarthmi" / "page0_filestream_multipt_blank_page1_probe_20260521" / "output.tft"
FS_EXPECT = ROOT / "examples" / "lifecycle_runtime_smoke" / "page0_filestream_multipt_blank_page1_smoke_2026-05-21.json"
FB_TFT = ROOT / "reverse_usarthmi" / "page0_filebrowser_multipt_blank_page1_probe_20260521" / "output.tft"
FB_EXPECT = ROOT / "examples" / "lifecycle_runtime_smoke" / "page0_filebrowser_multipt_blank_page1_smoke_2026-05-21.json"


@dataclass(frozen=True)
class ProbeSpec:
    name: str
    tft: Path
    expect_json: Path


PROBES = [
    ProbeSpec("page0_filestream_blank_page1", FS_TFT, FS_EXPECT),
    ProbeSpec("page0_filebrowser_blank_page1", FB_TFT, FB_EXPECT),
]


def build_smoke_command(
    probe: ProbeSpec,
    *,
    out_dir: Path,
    port: str,
    baud: int,
    download_baud: int,
    timeout_ms: int,
    post_upload_wait_s: float,
    capture: bool,
) -> list[str]:
    cmd = [
        sys.executable,
        str(LIVE_TFT_SMOKE),
        "--file",
        str(probe.tft),
        "--out-dir",
        str(out_dir),
        "--expect-json",
        str(probe.expect_json),
        "--port",
        port,
        "--baud",
        str(baud),
        "--download-baud",
        str(download_baud),
        "--timeout-ms",
        str(timeout_ms),
        "--post-upload-wait-s",
        str(post_upload_wait_s),
        "--upload",
    ]
    if capture:
        cmd.append("--capture")
    return cmd


def classify_results(results: dict[str, dict[str, Any]]) -> dict[str, str]:
    fs_ok = bool(results["page0_filestream_blank_page1"]["summary"]["ok"])
    fb_ok = bool(results["page0_filebrowser_blank_page1"]["summary"]["ok"])
    if fs_ok and fb_ok:
        label = "both_positive"
        meaning = "extra-page/page1 placement is the primary limiter, not multi-page in general"
    elif fs_ok and not fb_ok:
        label = "filestream_positive_and_filebrowser_negative"
        meaning = "strong evidence for A-type-specific multi-page runtime limitation"
    elif not fs_ok and not fb_ok:
        label = "both_negative"
        meaning = "seed-side runtime page 1 itself may still be the limiter, or multi-page advanced runtime is more broadly constrained"
    else:
        label = "filebrowser_positive_filestream_negative"
        meaning = "unexpected control result; verify transport and smoke expectations before drawing runtime conclusions"
    return {"label": label, "meaning": meaning}


def run_probe(cmd: list[str]) -> dict[str, Any]:
    completed = subprocess.run(cmd, text=True, capture_output=True, check=False, encoding="utf-8", errors="replace")
    if completed.returncode not in {0, 1}:
        raise RuntimeError(f"Smoke runner failed to execute: rc={completed.returncode}\nstdout={completed.stdout}\nstderr={completed.stderr}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Smoke runner did not return JSON.\nstdout={completed.stdout}\nstderr={completed.stderr}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the prepared seed-side multi-page runtime limitation probes in sequence.")
    parser.add_argument("--out-dir", required=True, help="Parent output directory for the two probe smoke runs and summary.")
    parser.add_argument("--port", default="COM36")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--download-baud", type=int, default=921600)
    parser.add_argument("--timeout-ms", type=int, default=3000)
    parser.add_argument("--post-upload-wait-s", type=float, default=2.0)
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    out_root = Path(args.out_dir).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    commands = {
        probe.name: build_smoke_command(
            probe,
            out_dir=out_root / probe.name,
            port=args.port,
            baud=args.baud,
            download_baud=args.download_baud,
            timeout_ms=args.timeout_ms,
            post_upload_wait_s=args.post_upload_wait_s,
            capture=args.capture,
        )
        for probe in PROBES
    }

    summary: dict[str, Any] = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "prepared" if args.dry_run else "ran",
        "out_dir": str(out_root),
        "commands": commands,
    }

    if args.dry_run:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    results = {name: run_probe(cmd) for name, cmd in commands.items()}
    summary["results"] = results
    summary["classification"] = classify_results(results)
    report_path = out_root / "seed_side_multipt_runtime_limit_summary.json"
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if all(result["summary"]["ok"] for result in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
