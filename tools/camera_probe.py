from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any


BACKENDS = {
    "default": 0,
    "dshow": 700,
    "msmf": 1400,
}


def fourcc_to_text(value: float) -> str:
    code = int(value)
    if code <= 0:
        return ""
    return "".join(chr((code >> (8 * i)) & 0xFF) for i in range(4)).strip("\x00")


def run_command(argv: list[str]) -> dict[str, Any]:
    proc = subprocess.run(argv, text=True, capture_output=True, encoding="utf-8", errors="replace")
    output = "\n".join(part for part in [proc.stdout, proc.stderr] if part)
    return {
        "argv": argv,
        "returncode": proc.returncode,
        "output": output,
    }


def ffmpeg_path() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found
    winget_root = Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
    for candidate in winget_root.glob("Gyan.FFmpeg_*/ffmpeg-*/bin/ffmpeg.exe"):
        return str(candidate)
    return None


def ffmpeg_probe(device_name: str | None) -> dict[str, Any]:
    ffmpeg = ffmpeg_path()
    if not ffmpeg:
        return {"available": False, "reason": "ffmpeg not found"}

    result: dict[str, Any] = {
        "available": True,
        "ffmpeg": ffmpeg,
        "devices": run_command([ffmpeg, "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"]),
    }
    if device_name:
        result["options"] = run_command(
            [ffmpeg, "-hide_banner", "-f", "dshow", "-list_options", "true", "-i", f"video={device_name}"]
        )
    return result


def pygrabber_devices() -> dict[str, Any]:
    try:
        from pygrabber.dshow_graph import FilterGraph  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on local Windows COM state.
        return {"available": False, "error": repr(exc)}

    try:
        graph = FilterGraph()
        return {"available": True, "devices": list(graph.get_input_devices())}
    except Exception as exc:  # pragma: no cover - depends on local DirectShow state.
        return {"available": False, "error": repr(exc)}


def opencv_probe(max_index: int, backends: list[str], warmup_frames: int) -> list[dict[str, Any]]:
    import cv2  # type: ignore

    rows: list[dict[str, Any]] = []
    for backend_name in backends:
        backend_id = BACKENDS[backend_name]
        for index in range(max_index + 1):
            cap = cv2.VideoCapture(index, backend_id) if backend_id else cv2.VideoCapture(index)
            item: dict[str, Any] = {"backend": backend_name, "index": index, "opened": bool(cap.isOpened())}
            try:
                if item["opened"]:
                    for _ in range(max(0, warmup_frames)):
                        cap.read()
                    ok, frame = cap.read()
                    item.update(
                        {
                            "width": float(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                            "height": float(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                            "fps": float(cap.get(cv2.CAP_PROP_FPS)),
                            "fourcc": fourcc_to_text(cap.get(cv2.CAP_PROP_FOURCC)),
                            "autofocus": float(cap.get(cv2.CAP_PROP_AUTOFOCUS)),
                            "focus": float(cap.get(cv2.CAP_PROP_FOCUS)),
                            "auto_exposure": float(cap.get(cv2.CAP_PROP_AUTO_EXPOSURE)),
                            "exposure": float(cap.get(cv2.CAP_PROP_EXPOSURE)),
                            "read_ok": bool(ok),
                        }
                    )
                    if ok and frame is not None:
                        item["frame_shape"] = [int(v) for v in frame.shape]
                        item["frame_mean_bgr"] = [float(v) for v in frame.mean(axis=(0, 1))]
            finally:
                cap.release()
            rows.append(item)
    return rows


def save_frame(index: int, backend: str, output: Path, warmup_frames: int) -> dict[str, Any]:
    import cv2  # type: ignore

    backend_id = BACKENDS[backend]
    cap = cv2.VideoCapture(index, backend_id) if backend_id else cv2.VideoCapture(index)
    try:
        if not cap.isOpened():
            raise RuntimeError(f"camera index {index} could not be opened with backend {backend}")
        frame = None
        ok = False
        for _ in range(max(0, warmup_frames) + 1):
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.05)
        if not ok or frame is None:
            raise RuntimeError(f"camera index {index} opened but returned no frame")
        output.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(output), frame):
            raise RuntimeError(f"failed to save frame to {output}")
        return {
            "path": str(output.resolve()),
            "width": int(frame.shape[1]),
            "height": int(frame.shape[0]),
            "bytes": output.stat().st_size,
        }
    finally:
        cap.release()


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe Windows camera devices through DirectShow and OpenCV.")
    parser.add_argument("--device-name", default="USB Cam", help="DirectShow device name for ffmpeg -list_options.")
    parser.add_argument("--max-index", type=int, default=5)
    parser.add_argument("--backend", action="append", choices=sorted(BACKENDS), help="OpenCV backend to probe.")
    parser.add_argument("--warmup-frames", type=int, default=3)
    parser.add_argument("--save-index", type=int, help="Optional OpenCV camera index to capture.")
    parser.add_argument("--save-backend", choices=sorted(BACKENDS), default="dshow")
    parser.add_argument("--save-output", type=Path, default=Path("reverse_usarthmi/camera_checks/camera_probe/frame.jpg"))
    args = parser.parse_args()

    backends = args.backend or ["dshow", "msmf"]
    result: dict[str, Any] = {
        "ffmpeg": ffmpeg_probe(args.device_name),
        "pygrabber": pygrabber_devices(),
        "opencv": opencv_probe(args.max_index, backends, args.warmup_frames),
    }
    if args.save_index is not None:
        result["saved_frame"] = save_frame(args.save_index, args.save_backend, args.save_output, args.warmup_frames)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
