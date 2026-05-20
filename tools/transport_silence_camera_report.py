from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "reverse_usarthmi" / "transport_silence_camera_20260521" / "camera_current.jpg"
OUT_PATH = ROOT / "examples" / "lifecycle_runtime_smoke" / "transport_silence_camera_status_2026-05-21.json"

CANDIDATES = {
    "page1_filebrowser_whiteboard": ROOT / "reverse_usarthmi" / "page1_filebrowser_local_multipt_probe_20260521" / "camera_page0_20260521_024931.jpg",
    "page1_textselect_positive": ROOT / "reverse_usarthmi" / "page1_textselect_local_multipt_probe_20260521" / "camera_20260521_014544.jpg",
    "page1_filestream_positive": ROOT / "reverse_usarthmi" / "page1_filestream_local_multipt_probe_20260521" / "camera_20260521_015505.jpg",
}


def _ahash(path: Path) -> str:
    img = Image.open(path).convert("L").resize((8, 8))
    pixels = list(img.getdata())
    avg = sum(pixels) / len(pixels)
    return "".join("1" if value >= avg else "0" for value in pixels)


def _hamming(a: str, b: str) -> int:
    return sum(left != right for left, right in zip(a, b))


def main() -> int:
    img = Image.open(CURRENT).convert("L")
    pixels = list(img.getdata())
    current_hash = _ahash(CURRENT)
    comparisons = {
        name: {
            "path": str(path.relative_to(ROOT)),
            "hamming_8x8_ahash": _hamming(current_hash, _ahash(path)),
        }
        for name, path in CANDIDATES.items()
    }

    payload = {
        "schema_version": 1,
        "date": "2026-05-21",
        "target": "TJC8048X543_011C",
        "status": "captured",
        "current_camera": {
            "path": str(CURRENT.relative_to(ROOT)),
            "size": img.size,
            "mean_luma": sum(pixels) / len(pixels),
            "min_luma": min(pixels),
            "max_luma": max(pixels),
        },
        "coarse_similarity": comparisons,
        "conclusions": {
            "screen_not_black": (sum(pixels) / len(pixels)) > 20,
            "panel_appears_powered_enough_for_camera_visibility": True,
            "camera_similarity_only_is_not_strong_enough_to_identify_the_exact_page_state": True,
        },
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
