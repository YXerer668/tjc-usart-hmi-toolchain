from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any


def sanitize_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned.strip("._") or "hmi_screen"


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def backend_id(cv2: Any, name: str) -> int:
    normalized = name.strip().lower()
    if normalized in {"default", "auto", ""}:
        return 0
    if normalized in {"dshow", "directshow"}:
        return int(cv2.CAP_DSHOW)
    if normalized in {"msmf", "mediafoundation"}:
        return int(cv2.CAP_MSMF)
    raise ValueError("backend must be default, dshow, or msmf")


def open_capture(cv2: Any, camera_index: int, backend: str) -> Any:
    backend_value = backend_id(cv2, backend)
    if backend_value:
        return cv2.VideoCapture(camera_index, backend_value)
    return cv2.VideoCapture(camera_index)


def apply_focus_controls(
    cv2: Any,
    cap: Any,
    autofocus: bool,
    focus: float | None,
    auto_exposure: float | None,
    exposure: float | None,
) -> dict[str, Any]:
    controls: dict[str, Any] = {}

    if auto_exposure is not None:
        auto_exposure_ok = bool(cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, auto_exposure))
        controls["auto_exposure"] = {
            "requested": auto_exposure,
            "set_ok": auto_exposure_ok,
            "readback": float(cap.get(cv2.CAP_PROP_AUTO_EXPOSURE)),
        }

    if exposure is not None:
        exposure_ok = bool(cap.set(cv2.CAP_PROP_EXPOSURE, exposure))
        controls["exposure"] = {
            "requested": exposure,
            "set_ok": exposure_ok,
            "readback": float(cap.get(cv2.CAP_PROP_EXPOSURE)),
        }

    requested_autofocus = 1 if autofocus else 0
    autofocus_ok = bool(cap.set(cv2.CAP_PROP_AUTOFOCUS, requested_autofocus))
    autofocus_readback = float(cap.get(cv2.CAP_PROP_AUTOFOCUS))
    if not autofocus and autofocus_readback not in {0.0, 2.0}:
        autofocus_ok = bool(cap.set(cv2.CAP_PROP_AUTOFOCUS, 2)) or autofocus_ok
        autofocus_readback = float(cap.get(cv2.CAP_PROP_AUTOFOCUS))
    controls["autofocus"] = {
        "requested": autofocus,
        "set_ok": autofocus_ok,
        "readback": autofocus_readback,
    }

    if focus is not None:
        focus_ok = bool(cap.set(cv2.CAP_PROP_FOCUS, focus))
        controls["focus"] = {
            "requested": focus,
            "set_ok": focus_ok,
            "readback": float(cap.get(cv2.CAP_PROP_FOCUS)),
        }
    else:
        controls["focus"] = {
            "requested": None,
            "readback": float(cap.get(cv2.CAP_PROP_FOCUS)),
        }
    return controls


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture the local USART HMI screen with the sharp-focus preset.")
    parser.add_argument("--camera-index", type=int, default=1)
    parser.add_argument("--backend", choices=["default", "dshow", "msmf"], default="dshow")
    focus_mode = parser.add_mutually_exclusive_group()
    focus_mode.add_argument("--autofocus", dest="autofocus", action="store_true", default=True)
    focus_mode.add_argument("--manual-focus", dest="autofocus", action="store_false")
    parser.add_argument("--focus", type=float, default=68.0, help="Manual focus value used with --manual-focus.")
    parser.add_argument("--auto-exposure", type=float, default=1.0)
    parser.add_argument("--exposure", type=float, default=-7.0)
    parser.add_argument("--warmup-frames", type=int, default=3)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--jpeg-quality", type=int, default=95)
    parser.add_argument("--output-dir", type=Path, default=Path("reverse_usarthmi") / "camera_checks" / "hmi_screen")
    parser.add_argument("--filename", default="")
    args = parser.parse_args()

    import cv2  # type: ignore

    args.output_dir.mkdir(parents=True, exist_ok=True)
    filename = sanitize_filename(args.filename or f"hmi_screen_{timestamp()}.jpg")
    if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
        filename += ".jpg"
    output_path = (args.output_dir / filename).resolve()

    cap = open_capture(cv2, args.camera_index, args.backend)
    try:
        if not cap.isOpened():
            raise RuntimeError(f"camera index {args.camera_index} could not be opened")
        if args.width:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        if args.height:
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

        controls = apply_focus_controls(
            cv2,
            cap,
            args.autofocus,
            None if args.autofocus else args.focus,
            args.auto_exposure,
            args.exposure,
        )

        frame = None
        ok = False
        for _ in range(max(args.warmup_frames, 0) + 1):
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.05)
        if not ok or frame is None:
            raise RuntimeError(f"camera index {args.camera_index} opened but did not return a frame")

        height, width = [int(v) for v in frame.shape[:2]]
        if output_path.suffix.lower() == ".png":
            saved = bool(cv2.imwrite(str(output_path), frame))
        else:
            quality = max(1, min(100, int(args.jpeg_quality)))
            saved = bool(cv2.imwrite(str(output_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality]))
        if not saved:
            raise RuntimeError(f"failed to save frame to {output_path}")

        result = {
            "path": str(output_path),
            "camera_index": args.camera_index,
            "backend": args.backend,
            "width": width,
            "height": height,
            "controls": controls,
            "warmup_frames": args.warmup_frames,
            "bytes": output_path.stat().st_size,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    finally:
        cap.release()


if __name__ == "__main__":
    raise SystemExit(main())
