from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from usarthmi.hmi_inspect import inspect_hmi  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPECTED_CONNECT = {
    "mode": "2",
    "flash_descriptor": "1089-0",
    "model": "TJC8048X543_011C",
    "firmware": "277",
    "mcu_code": "10501",
    "feature_descriptor": "128974848-0",
}
STRESS_OWNER_QUERY = r"""
Get-CimInstance Win32_Process |
  Where-Object {
    $_.Name -eq 'python.exe' -and
    ($_.CommandLine -like '*codex_fourpage_dashboard_runtime_stress.py*' -or
     $_.CommandLine -like '*codex_fourpage_dashboard_burst_stress.py*' -or
     $_.CommandLine -like '*codex_touch_coordinate_probe.py*')
  } |
  Select-Object ProcessId,Name,CommandLine |
  ConvertTo-Json -Compress
"""


class PipelineError(RuntimeError):
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Reusable touch-safe official USART HMI build/flash pipeline.")
    parser.add_argument("--spec", type=Path, help="Pipeline JSON spec. CLI flags override matching fields.")
    parser.add_argument("--source-hmi", type=Path, help="Input .HMI file.")
    parser.add_argument("--patch-plan", type=Path, help="Optional patch plan with a top-level patches object.")
    parser.add_argument("--out-dir", type=Path, help="Output directory for generated artifacts.")
    parser.add_argument("--name", help="Pipeline/build name.")
    parser.add_argument("--title", help="Preview title.")
    parser.add_argument("--install-dir", type=Path, help="Official USART HMI headless install/runtime directory.")
    parser.add_argument("--port", default=None)
    parser.add_argument("--baud", type=int, default=None)
    parser.add_argument("--download-baud", type=int, default=None)
    parser.add_argument("--chunk-size", type=int, default=None)
    parser.add_argument("--flash", action="store_true", help="Upload the compiled TFT after target gate checks.")
    parser.add_argument("--no-flash", action="store_true", help="Force build-only mode even if the spec requests flashing.")
    parser.add_argument("--skip-preview", action="store_true")
    parser.add_argument("--skip-official-compile", action="store_true")
    parser.add_argument("--camera", action="store_true", help="Capture USB Cam after a successful flash.")
    parser.add_argument("--serial-smoke", action="store_true", help="Run serial_smoke commands from the spec after flash.")
    parser.add_argument("--dry-run", action="store_true", help="Write normalized config only.")
    args = parser.parse_args()

    config = normalize_config(load_spec(args.spec), args)
    out_dir = Path(config["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "pipeline_manifest.json"
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "name": config["name"],
        "created_at_utc": utc_now(),
        "config": config_for_report(config),
        "steps": [],
        "status": "running",
    }

    try:
        if args.dry_run:
            manifest["status"] = "dry_run"
            write_json(manifest_path, manifest)
            print(json.dumps({"status": "dry_run", "manifest": str(manifest_path.resolve())}, indent=2))
            return 0

        work_hmi = prepare_hmi(config, manifest)
        audit_touch_geometry(work_hmi, out_dir / "touchsafe_geometry_audit.json", manifest)

        if not config["skip_preview"]:
            run_preview(work_hmi, config, manifest)

        tft_path = compile_tft(work_hmi, config, manifest)
        checksum_tft(tft_path, config, manifest)

        if config["flash"]:
            assert_no_com36_owner(out_dir / "com36_owner_check.json", manifest)
            connect_gate(config, manifest)
            upload_tft(tft_path, config, manifest)
            post_upload_health(config, manifest)
            if config["run_serial_smoke"]:
                serial_smoke(config, manifest)
            if config["camera"]:
                capture_camera(config, manifest)

        manifest["status"] = "ok"
        manifest["completed_at_utc"] = utc_now()
        write_json(manifest_path, manifest)
        print(json.dumps({"status": "ok", "manifest": str(manifest_path.resolve()), "tft": str(tft_path.resolve())}, indent=2))
        return 0
    except Exception as exc:
        manifest["status"] = "failed"
        manifest["error"] = str(exc)
        manifest["completed_at_utc"] = utc_now()
        write_json(manifest_path, manifest)
        raise


def load_spec(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalize_config(spec: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    target = dict(spec.get("target") or {})
    official = dict(spec.get("official") or {})
    out_dir_raw = args.out_dir or spec.get("out_dir")
    source_raw = args.source_hmi or spec.get("source_hmi")
    if not out_dir_raw:
        raise SystemExit("--out-dir or spec.out_dir is required")
    if not source_raw:
        raise SystemExit("--source-hmi or spec.source_hmi is required")

    name = args.name or spec.get("name") or Path(str(out_dir_raw)).name
    flash = bool(spec.get("flash", False))
    if args.flash:
        flash = True
    if args.no_flash:
        flash = False

    config = {
        "name": str(name),
        "source_hmi": str(resolve_path(source_raw)),
        "patch_plan": None if (args.patch_plan or spec.get("patch_plan")) in (None, "") else str(resolve_path(args.patch_plan or spec.get("patch_plan"))),
        "out_dir": str(resolve_path(out_dir_raw)),
        "title": str(args.title or spec.get("title") or name),
        "official_install_dir": None
        if (args.install_dir or official.get("install_dir")) in (None, "")
        else str(resolve_path(args.install_dir or official.get("install_dir"))),
        "skip_preview": bool(args.skip_preview or spec.get("skip_preview", False)),
        "skip_official_compile": bool(args.skip_official_compile or spec.get("skip_official_compile", False)),
        "flash": flash,
        "camera": bool(args.camera or spec.get("camera", False)),
        "run_serial_smoke": bool(args.serial_smoke or spec.get("run_serial_smoke", False)),
        "target": {
            "port": str(args.port or target.get("port") or "COM36"),
            "baud": int(args.baud or target.get("baud") or 9600),
            "download_baud": int(args.download_baud or target.get("download_baud") or 921600),
            "chunk_size": int(args.chunk_size or target.get("chunk_size") or 4096),
            "timeout_ms": int(target.get("timeout_ms") or 3000),
            "upload_timeout_ms": int(target.get("upload_timeout_ms") or 8000),
            "expected_connect": dict(target.get("expected_connect") or DEFAULT_EXPECTED_CONNECT),
        },
        "serial_smoke": list(spec.get("serial_smoke") or []),
    }
    return config


def resolve_path(value: Any) -> Path:
    path = Path(str(value))
    if path.is_absolute():
        return path.resolve()
    return (REPO_ROOT / path).resolve()


def config_for_report(config: dict[str, Any]) -> dict[str, Any]:
    clean = dict(config)
    return clean


def prepare_hmi(config: dict[str, Any], manifest: dict[str, Any]) -> Path:
    source = Path(config["source_hmi"])
    if not source.exists():
        raise PipelineError(f"source HMI does not exist: {source}")
    out_dir = Path(config["out_dir"])
    work_hmi = out_dir / "lcd_test.HMI"

    if config.get("patch_plan"):
        report = out_dir / "hmi_patch_report.json"
        command = [
            sys.executable,
            str(REPO_ROOT / "tools" / "codex_apply_hmi_patch_plan.py"),
            "--source",
            str(source),
            "--plan",
            str(config["patch_plan"]),
            "--output",
            str(work_hmi),
            "--report",
            str(report),
        ]
        result = run_command("apply_patch_plan", command, out_dir)
        append_step(manifest, "apply_patch_plan", "ok", result=result, report=str(report.resolve()))
    else:
        shutil.copy2(source, work_hmi)
        append_step(manifest, "copy_hmi", "ok", source=str(source.resolve()), output=str(work_hmi.resolve()))
    return work_hmi


def audit_touch_geometry(hmi_path: Path, out_path: Path, manifest: dict[str, Any]) -> None:
    inspection = inspect_hmi(hmi_path)
    raw = hmi_path.read_bytes()
    entries = {entry.name: entry for entry in inspection.entries}
    checked: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    missing_end_fields: list[dict[str, Any]] = []
    for page in inspection.pa_pages:
        entry = entries.get(page.entry_name)
        page_data = b""
        if entry is not None and entry.in_file:
            page_data = raw[entry.data_offset : entry.data_offset + entry.length]
        for block in page.blocks:
            fields = block.fields or {}
            if not all(name in fields for name in ("x", "y", "w", "h")):
                continue
            endx = read_field_int(page_data, block.index, "endx")
            endy = read_field_int(page_data, block.index, "endy")
            has_end = endx is not None or endy is not None
            item = {
                "page": page.entry_name,
                "object": block.objname or block.attr_name or f"block{block.index}",
                "index": block.index,
                "x": int(fields["x"]),
                "y": int(fields["y"]),
                "w": int(fields["w"]),
                "h": int(fields["h"]),
            }
            if not has_end:
                missing_end_fields.append(item)
                continue
            expected_endx = item["x"] + item["w"] - 1
            expected_endy = item["y"] + item["h"] - 1
            item.update(
                {
                    "endx": endx,
                    "endy": endy,
                    "expected_endx": expected_endx,
                    "expected_endy": expected_endy,
                }
            )
            checked.append(item)
            if endx != expected_endx or endy != expected_endy:
                mismatches.append(item)
    report = {
        "hmi": str(hmi_path.resolve()),
        "checked_count": len(checked),
        "missing_end_field_count": len(missing_end_fields),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "missing_end_fields": missing_end_fields,
        "status": "ok" if not mismatches else "failed",
    }
    write_json(out_path, report)
    append_step(manifest, "touchsafe_geometry_audit", report["status"], report=str(out_path.resolve()), summary=report)
    if mismatches:
        raise PipelineError(f"touch geometry audit failed: {len(mismatches)} mismatch(es)")


def read_field_int(page_data: bytes, block_index: int, field_name: str) -> int | None:
    value_range = field_value_range(page_data, block_index, field_name)
    if value_range is None:
        return None
    start, end = value_range
    return int.from_bytes(page_data[start:end], "little", signed=False)


def field_value_range(page_data: bytes, block_index: int, field_name: str) -> tuple[int, int] | None:
    if not page_data:
        return None
    table_offset = 0x38 + block_index * 12
    if table_offset + 8 > len(page_data):
        return None
    rel_offset = int.from_bytes(page_data[table_offset : table_offset + 4], "little")
    block_length = int.from_bytes(page_data[table_offset + 4 : table_offset + 8], "little")
    cursor = 0x38 + rel_offset
    block_end = cursor + block_length
    if cursor + 4 > len(page_data) or block_end > len(page_data):
        return None

    attr_len = int.from_bytes(page_data[cursor : cursor + 4], "little")
    cursor += 4 + attr_len
    while cursor + 4 <= block_end:
        chunk_len = int.from_bytes(page_data[cursor : cursor + 4], "little")
        cursor += 4
        if chunk_len == 0:
            return None
        chunk_start = cursor
        chunk_end = cursor + chunk_len
        if chunk_end > block_end:
            return None
        if chunk_len >= 16:
            raw_name = page_data[chunk_start : chunk_start + 16]
            name = raw_name.split(b"\x00", 1)[0].decode("ascii", errors="ignore")
            if name == field_name:
                return chunk_start + 16, chunk_end
        cursor = chunk_end
    return None


def run_preview(hmi_path: Path, config: dict[str, Any], manifest: dict[str, Any]) -> None:
    out_dir = Path(config["out_dir"]) / "preview"
    command = [
        sys.executable,
        str(REPO_ROOT / "tools" / "codex_hmi_beauty_preview.py"),
        "--hmi",
        str(hmi_path),
        "--out-dir",
        str(out_dir),
        "--title",
        str(config["title"]),
        "--current-only",
    ]
    result = run_command("preview", command, Path(config["out_dir"]))
    report_path = out_dir / "beauty_preview_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    status = "ok" if int(report.get("collision_count", 1)) == 0 else "failed"
    append_step(manifest, "preview_collision_gate", status, result=result, report=str(report_path.resolve()), summary=report)
    if status != "ok":
        raise PipelineError(f"preview collision gate failed: {report.get('collision_count')} collision(s)")


def compile_tft(hmi_path: Path, config: dict[str, Any], manifest: dict[str, Any]) -> Path:
    out_dir = Path(config["out_dir"])
    tft_path = out_dir / f"{config['name']}.tft"
    if config["skip_official_compile"]:
        if not tft_path.exists():
            raise PipelineError(f"--skip-official-compile requires existing TFT: {tft_path}")
        append_step(manifest, "official_compile", "skipped", tft=str(tft_path.resolve()))
        return tft_path

    official_dir = out_dir / "official_compile"
    official_report = official_dir / "official_compile_report.json"
    spec = {
        "name": f"{config['name']}_official_compile",
        "mode": "macro",
        "single_session": True,
        "hmi_path": str(hmi_path.resolve()),
        "out_dir": str(official_dir.resolve()),
        "report_path": str(official_report.resolve()),
        "install_dir": config.get("official_install_dir"),
        "actions": [{"kind": "save"}, {"kind": "compile", "output": str(tft_path.resolve())}],
    }
    spec_path = out_dir / "official_compile_spec.json"
    write_json(spec_path, spec)
    command = [sys.executable, str(REPO_ROOT / "tools" / "official_hmi_hook_runner.py"), "--script-json", str(spec_path)]
    result = run_command("official_compile", command, out_dir)
    if not tft_path.exists():
        raise PipelineError(f"official compile did not create TFT: {tft_path}")
    append_step(
        manifest,
        "official_compile",
        "ok",
        result=result,
        spec=str(spec_path.resolve()),
        report=str(official_report.resolve()),
        tft=str(tft_path.resolve()),
        size=tft_path.stat().st_size,
    )
    return tft_path


def checksum_tft(tft_path: Path, config: dict[str, Any], manifest: dict[str, Any]) -> None:
    out = Path(config["out_dir"]) / "checksum.json"
    command = usarthmi_cmd(["--json", "tft", "checksum", "--file", str(tft_path)])
    result = run_command("checksum", command, Path(config["out_dir"]))
    parsed = parse_json_file(result["stdout_path"])
    write_json(out, parsed)
    status = "ok" if parsed.get("valid") is True else "failed"
    append_step(manifest, "checksum", status, result=result, report=str(out.resolve()), summary=parsed)
    if status != "ok":
        raise PipelineError("TFT checksum failed")


def assert_no_com36_owner(out_path: Path, manifest: dict[str, Any]) -> None:
    command = ["powershell", "-NoProfile", "-Command", STRESS_OWNER_QUERY]
    result = run_command("com36_owner_check", command, out_path.parent, check=False)
    text = Path(result["stdout_path"]).read_text(encoding="utf-8", errors="replace").strip()
    report = {"stdout": text, "owner_detected": bool(text and text != "null")}
    write_json(out_path, report)
    status = "failed" if report["owner_detected"] else "ok"
    append_step(manifest, "com36_owner_check", status, result=result, report=str(out_path.resolve()), summary=report)
    if report["owner_detected"]:
        raise PipelineError("COM36 appears to be owned by a background stress/probe process")


def connect_gate(config: dict[str, Any], manifest: dict[str, Any]) -> None:
    target = config["target"]
    out = Path(config["out_dir"]) / "connect_gate.json"
    command = usarthmi_cmd(
        [
            "--json",
            "connect",
            "--port",
            target["port"],
            "--baud",
            str(target["baud"]),
            "--timeout-ms",
            str(target["timeout_ms"]),
        ]
    )
    result = run_command("connect_gate", command, Path(config["out_dir"]))
    parsed = parse_json_file(result["stdout_path"])
    write_json(out, parsed)
    details = (((parsed.get("response") or {}).get("details")) or {})
    mismatches = [
        {"field": key, "expected": str(expected), "actual": str(details.get(key))}
        for key, expected in target["expected_connect"].items()
        if str(details.get(key)) != str(expected)
    ]
    status = "ok" if not mismatches else "failed"
    append_step(manifest, "connect_gate", status, result=result, report=str(out.resolve()), mismatches=mismatches)
    if mismatches:
        raise PipelineError(f"connect gate mismatch: {mismatches}")


def upload_tft(tft_path: Path, config: dict[str, Any], manifest: dict[str, Any]) -> None:
    target = config["target"]
    out = Path(config["out_dir"]) / "upload.json"
    command = usarthmi_cmd(
        [
            "--json",
            "tft",
            "upload",
            "--file",
            str(tft_path),
            "--port",
            target["port"],
            "--baud",
            str(target["baud"]),
            "--download-baud",
            str(target["download_baud"]),
            "--chunk-size",
            str(target["chunk_size"]),
            "--timeout-ms",
            str(target["upload_timeout_ms"]),
            "--progress",
        ]
    )
    result = run_command("upload", command, Path(config["out_dir"]))
    parsed = parse_json_file(result["stdout_path"])
    write_json(out, parsed)
    append_step(manifest, "upload", "ok", result=result, report=str(out.resolve()), summary=summarize_upload(parsed))


def post_upload_health(config: dict[str, Any], manifest: dict[str, Any]) -> None:
    target = config["target"]
    out = Path(config["out_dir"]) / "postupload_health.json"
    command = usarthmi_cmd(
        [
            "--json",
            "tft",
            "health",
            "--port",
            target["port"],
            "--baud",
            str(target["baud"]),
            "--timeout-ms",
            str(target["timeout_ms"]),
        ]
    )
    result = run_command("postupload_health", command, Path(config["out_dir"]))
    parsed = parse_json_file(result["stdout_path"])
    write_json(out, parsed)
    healthy = (((parsed.get("summary") or {}).get("healthy")) is True)
    status = "ok" if healthy else "failed"
    append_step(manifest, "postupload_health", status, result=result, report=str(out.resolve()), summary=parsed.get("summary"))
    if not healthy:
        raise PipelineError("post-upload health check failed")


def serial_smoke(config: dict[str, Any], manifest: dict[str, Any]) -> None:
    target = config["target"]
    smoke_dir = Path(config["out_dir"]) / "serial_smoke"
    smoke_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for index, item in enumerate(config.get("serial_smoke") or [], start=1):
        label = str(item.get("label") or f"command_{index:02d}")
        command_text = str(item["command"])
        command = usarthmi_cmd(
            [
                "--json",
                "raw",
                command_text,
                "--port",
                target["port"],
                "--baud",
                str(target["baud"]),
                "--timeout-ms",
                str(target["timeout_ms"]),
            ]
        )
        result = run_command(f"serial_smoke_{index:02d}_{safe_name(label)}", command, smoke_dir)
        parsed = parse_json_file(result["stdout_path"])
        report_path = smoke_dir / f"{index:02d}_{safe_name(label)}.json"
        write_json(report_path, parsed)
        ok = matches_expect(parsed, item.get("expect"))
        results.append({"label": label, "command": command_text, "ok": ok, "report": str(report_path.resolve())})
        if not ok:
            append_step(manifest, "serial_smoke", "failed", results=results)
            raise PipelineError(f"serial smoke failed at {label}: {command_text}")
    append_step(manifest, "serial_smoke", "ok", results=results)


def capture_camera(config: dict[str, Any], manifest: dict[str, Any]) -> None:
    out = Path(config["out_dir"]) / "camera_after_upload.jpg"
    script = Path.home() / ".codex" / "skills" / "tjc-usart-hmi-workflow" / "scripts" / "capture_usb_cam.ps1"
    command = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Output", str(out)]
    result = run_command("camera_capture", command, Path(config["out_dir"]))
    append_step(manifest, "camera_capture", "ok", result=result, output=str(out.resolve()), sha256=sha256_file(out) if out.exists() else None)


def usarthmi_cmd(args: list[str]) -> list[str]:
    script = REPO_ROOT / "usarthmi.cmd"
    if script.exists():
        return ["cmd", "/c", str(script), *args]
    return [sys.executable, "-m", "usarthmi", *args]


def run_command(name: str, command: list[str], cwd: Path, *, check: bool = True) -> dict[str, Any]:
    command_dir = cwd / "commands"
    command_dir.mkdir(parents=True, exist_ok=True)
    safe = safe_name(name)
    stdout_path = command_dir / f"{safe}.stdout.txt"
    stderr_path = command_dir / f"{safe}.stderr.txt"
    started = utc_now()
    completed = subprocess.run(command, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    result = {
        "name": name,
        "command": command,
        "returncode": completed.returncode,
        "started_at_utc": started,
        "completed_at_utc": utc_now(),
        "stdout_path": str(stdout_path.resolve()),
        "stderr_path": str(stderr_path.resolve()),
    }
    if check and completed.returncode != 0:
        raise PipelineError(f"{name} failed with return code {completed.returncode}; see {stderr_path}")
    return result


def parse_json_file(path_raw: str) -> dict[str, Any]:
    text = Path(path_raw).read_text(encoding="utf-8-sig", errors="replace").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def matches_expect(parsed: dict[str, Any], expect: Any) -> bool:
    if not expect:
        return True
    response = parsed.get("response") or {}
    for key, expected in dict(expect).items():
        actual = response.get(key)
        if str(actual) != str(expected):
            return False
    return True


def summarize_upload(parsed: dict[str, Any]) -> dict[str, Any]:
    return {
        "success": parsed.get("success"),
        "file": parsed.get("file") or parsed.get("path"),
        "bytes": parsed.get("bytes") or parsed.get("size") or parsed.get("file_size"),
        "last_upload_manifest": parsed.get("last_upload_manifest"),
    }


def append_step(manifest: dict[str, Any], name: str, status: str, **kwargs: Any) -> None:
    item = {"name": name, "status": status, **kwargs}
    manifest.setdefault("steps", []).append(item)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def safe_name(value: str) -> str:
    out = []
    for ch in value:
        if ch.isalnum() or ch in {"-", "_"}:
            out.append(ch)
        else:
            out.append("_")
    return "".join(out).strip("_") or "item"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
