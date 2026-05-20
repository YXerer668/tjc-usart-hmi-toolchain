from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_bundle(bundle_dir: Path) -> dict[str, object]:
    manifest_path = bundle_dir / "package_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    copied = manifest["copied_files"]["lcd_test.tft"]
    tft_path = Path(copied["path"])
    actual_size = tft_path.stat().st_size
    actual_sha = _sha256(tft_path)
    report = {
        "bundle_dir": str(bundle_dir),
        "manifest_path": str(manifest_path),
        "tft_path": str(tft_path),
        "expected_size": copied["bytes"],
        "actual_size": actual_size,
        "expected_sha256": copied["sha256"],
        "actual_sha256": actual_sha,
        "size_ok": actual_size == copied["bytes"],
        "sha256_ok": actual_sha == copied["sha256"],
    }
    report["ok"] = bool(report["size_ok"] and report["sha256_ok"])
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the prepared SD recovery handoff bundle before use.")
    parser.add_argument("--bundle-dir", required=True)
    parser.add_argument("--out")
    args = parser.parse_args()

    bundle_dir = Path(args.bundle_dir).resolve()
    report = verify_bundle(bundle_dir)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        out_path = Path(args.out).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
