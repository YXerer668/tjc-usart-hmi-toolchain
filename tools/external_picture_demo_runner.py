from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from usarthmi.editor import build_scene
from usarthmi.scene import load_scene
from usarthmi.tft_checksum import inspect_tft_checksum


DEFAULT_SCENE = WORKSPACE_ROOT / "examples" / "external_picture_demo" / "scene.json"
DEFAULT_EXPECT = WORKSPACE_ROOT / "examples" / "external_picture_demo" / "smoke.expect.json"
DEFAULT_SEED = Path(r"D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI")
DEFAULT_BASELINE_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft")
DEFAULT_OUT = WORKSPACE_ROOT / "reverse_usarthmi" / "external_picture_demo_build"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and optionally live-smoke the external-picture demo."
    )
    parser.add_argument("--scene", type=Path, default=DEFAULT_SCENE)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--baseline-tft", type=Path, default=DEFAULT_BASELINE_TFT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--expect-json", type=Path, default=DEFAULT_EXPECT)
    parser.add_argument("--result-json", type=Path, help="Defaults to <out>/runner_result.json")
    parser.add_argument("--skip-build", action="store_true", help="Reuse an existing <out>/output.tft")
    parser.add_argument("--smoke", action="store_true", help="Run live serial checks after build/checksum")
    parser.add_argument("--upload", action="store_true", help="Upload before live smoke checks")
    parser.add_argument("--capture", action="store_true", help="Capture the screen during live smoke")
    parser.add_argument("--port", default="COM36")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--download-baud", type=int, default=921600)
    parser.add_argument("--timeout-ms", type=int, default=3000)
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--known-current", type=Path)
    parser.add_argument("--skip-if-identical", action="store_true")
    args = parser.parse_args()

    result = run(args)
    result_path = args.result_json or (Path(result["out_dir"]) / "runner_result.json")
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["summary"]["ok"] else 1


def run(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    output_tft = out_dir / "output.tft"

    build_result: dict[str, Any] | None = None
    if not args.skip_build:
        scene = load_scene(args.scene)
        build_result = build_scene(scene, args.seed, out_dir, baseline_tft=args.baseline_tft)
    elif not output_tft.exists():
        raise FileNotFoundError(f"--skip-build requested but {output_tft} does not exist")

    checksum = inspect_tft_checksum(output_tft)
    smoke_result = None
    if args.smoke or args.upload or args.capture:
        smoke_result = _run_live_smoke(args, output_tft, out_dir)

    smoke_ok = smoke_result is None or bool(smoke_result.get("summary", {}).get("ok"))
    summary = {
        "ok": bool(checksum.get("valid")) and smoke_ok,
        "checksum_valid": bool(checksum.get("valid")),
        "smoke_ok": smoke_ok if smoke_result is not None else None,
        "uploaded": bool(smoke_result and smoke_result.get("summary", {}).get("uploaded")),
        "camera_captured": bool(smoke_result and smoke_result.get("summary", {}).get("camera_captured")),
    }
    return {
        "scene": str(args.scene.resolve()),
        "seed": str(args.seed.resolve()),
        "baseline_tft": str(args.baseline_tft.resolve()),
        "out_dir": str(out_dir),
        "output_tft": str(output_tft),
        "build": build_result,
        "checksum": checksum,
        "smoke": smoke_result,
        "summary": summary,
    }


def _run_live_smoke(args: argparse.Namespace, output_tft: Path, out_dir: Path) -> dict[str, Any]:
    smoke_dir = out_dir / ("smoke_capture" if args.capture else "smoke")
    cmd = [
        sys.executable,
        str(WORKSPACE_ROOT / "tools" / "live_tft_smoke.py"),
        "--file",
        str(output_tft),
        "--out-dir",
        str(smoke_dir),
        "--expect-json",
        str(args.expect_json),
        "--port",
        args.port,
        "--baud",
        str(args.baud),
        "--download-baud",
        str(args.download_baud),
        "--timeout-ms",
        str(args.timeout_ms),
    ]
    if args.upload:
        cmd.append("--upload")
    if args.capture:
        cmd.append("--capture")
    if args.progress:
        cmd.append("--progress")
    if args.known_current:
        cmd.extend(["--known-current", str(args.known_current)])
    if args.skip_if_identical:
        cmd.append("--skip-if-identical")

    completed = subprocess.run(cmd, text=True, capture_output=True, check=False)
    payload = _parse_json_stdout(completed.stdout)
    payload["returncode"] = completed.returncode
    payload["command"] = cmd
    if completed.stderr.strip():
        payload["stderr"] = completed.stderr.strip()
    if completed.returncode != 0:
        payload.setdefault("summary", {})["ok"] = False
    return payload


def _parse_json_stdout(stdout: str) -> dict[str, Any]:
    if not stdout.strip():
        return {"stdout": stdout}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"stdout": stdout}


if __name__ == "__main__":
    raise SystemExit(main())
