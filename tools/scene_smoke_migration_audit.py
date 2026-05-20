from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from usarthmi.scene import load_scene
from usarthmi.scene_smoke import _check_expect_file, _generated_expectation_payload

DEFAULT_ROOT = WORKSPACE_ROOT / "examples" / "advanced_direct_tft_demo"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit scene/live_smoke convergence against legacy smoke.expect.json files.")
    parser.add_argument("root", nargs="?", default=str(DEFAULT_ROOT), help="Directory containing scene and smoke.expect files")
    parser.add_argument("--out", help="Write the audit JSON to this path")
    args = parser.parse_args()

    result = run(Path(args.root))
    if args.out:
        out_path = Path(args.out).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def run(root: Path) -> dict[str, Any]:
    root = root.resolve()
    scene_entries: list[dict[str, Any]] = []
    expected_scene_names = set()
    for scene_path in sorted(root.glob("*_scene.json")):
        scene_name = scene_path.name
        expected_scene_names.add(scene_name)
        scene = load_scene(scene_path)
        generated = _generated_expectation_payload(scene)
        has_live_smoke = isinstance(scene.project.get("live_smoke"), dict)
        legacy_expect = scene_path.with_name(scene_path.name.replace("_scene.json", "_smoke.expect.json"))
        check = None
        if legacy_expect.exists():
            check = _check_expect_file(scene_path, generated, legacy_expect)
        scene_entries.append(
            {
                "scene": str(scene_path.relative_to(WORKSPACE_ROOT)).replace("\\", "/"),
                "has_live_smoke": has_live_smoke,
                "generated_available": generated is not None,
                "generated_source": (generated or {}).get("source"),
                "conventional_legacy_expect": (
                    str(legacy_expect.relative_to(WORKSPACE_ROOT)).replace("\\", "/") if legacy_expect.exists() else None
                ),
                "conventional_legacy_match": None if check is None else bool(check.get("match")),
                "expectation_count": len((generated or {}).get("expectations", [])),
                "step_count": len((generated or {}).get("steps", [])),
            }
        )

    orphan_expect_files = []
    for expect_path in sorted(root.glob("*_smoke.expect.json")):
        expected_scene = expect_path.with_name(expect_path.name.replace("_smoke.expect.json", "_scene.json")).name
        if expected_scene not in expected_scene_names:
            orphan_expect_files.append(str(expect_path.relative_to(WORKSPACE_ROOT)).replace("\\", "/"))

    summary = {
        "scene_count": len(scene_entries),
        "scene_with_live_smoke": sum(1 for item in scene_entries if item["has_live_smoke"]),
        "scene_without_live_smoke": sum(1 for item in scene_entries if not item["has_live_smoke"]),
        "scene_with_conventional_legacy_expect": sum(1 for item in scene_entries if item["conventional_legacy_expect"]),
        "scene_with_matching_conventional_legacy": sum(1 for item in scene_entries if item["conventional_legacy_match"] is True),
        "scene_with_mismatching_conventional_legacy": sum(1 for item in scene_entries if item["conventional_legacy_match"] is False),
        "orphan_legacy_expect_count": len(orphan_expect_files),
    }
    return {
        "schema_version": 1,
        "root": str(root),
        "summary": summary,
        "scenes": scene_entries,
        "orphan_legacy_expect_files": orphan_expect_files,
    }


if __name__ == "__main__":
    raise SystemExit(main())
