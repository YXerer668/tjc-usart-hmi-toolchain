from __future__ import annotations

import json
import unittest
from pathlib import Path

from usarthmi.scene import load_scene
from usarthmi.scene_check import check_scene_project


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = REPO_ROOT / "examples" / "econtest_templates"
TOUCHABLE_TYPES = {
    "button",
    "state-button",
    "dual-button",
    "hotspot",
    "slider",
    "checkbox",
    "radio",
    "combobox",
    "touch-capture",
}


class EcontestTemplateTests(unittest.TestCase):
    def test_index_lists_ten_templates(self) -> None:
        index = _load_index()

        self.assertEqual(index["schema"], "usarthmi.econtest_templates.v3")
        self.assertEqual(index["count"], 10)
        self.assertEqual(len(index["templates"]), 10)
        self.assertEqual({tuple(item["pages"]) for item in index["templates"]}, {("page0", "page1", "page2")})
        self.assertEqual(
            {item["home_kind"] for item in index["templates"]},
            {"power_flow", "scope", "source", "comms", "pid", "motor", "daq", "robot", "vision", "debug"},
        )

        slugs = [item["slug"] for item in index["templates"]]
        self.assertEqual(len(slugs), len(set(slugs)))
        for item in index["templates"]:
            self.assertTrue(item["problem_type"])
            self.assertGreaterEqual(len(item["topic_widgets"]), 4)
            self.assertGreaterEqual(len(item["page1_widgets"]), 4)
            self.assertGreaterEqual(len(item["page2_widgets"]), 4)
            self.assertEqual(set(item["page_roles"]), {"page0", "page1", "page2"})
            self.assertNotEqual(item["page_roles"]["page1"], item["page_roles"]["page2"])
            self.assertTrue((TEMPLATE_ROOT / item["scene"]).exists(), item["scene"])

    def test_templates_validate_check_and_keep_touch_targets_separate(self) -> None:
        for item in _load_index()["templates"]:
            with self.subTest(template=item["slug"]):
                scene_path = TEMPLATE_ROOT / item["scene"]
                scene = load_scene(scene_path)
                self.assertEqual(scene.canvas["width"], 800)
                self.assertEqual(scene.canvas["height"], 480)
                self.assertEqual([page.id for page in scene.pages], ["page0", "page1", "page2"])
                self.assertTrue(_has_widget_type(scene, "timer"))
                page0_ids = {widget.id for widget in scene.pages[0].widgets}
                for widget_id in item["topic_widgets"]:
                    self.assertIn(widget_id, page0_ids)
                page1_ids = {widget.id for widget in scene.pages[1].widgets}
                for widget_id in item["page1_widgets"]:
                    self.assertIn(widget_id, page1_ids)
                page2_ids = {widget.id for widget in scene.pages[2].widgets}
                for widget_id in item["page2_widgets"]:
                    self.assertIn(widget_id, page2_ids)

                report = check_scene_project(scene_path, simulate_events=True, max_event_slots=80, max_steps=20)
                self.assertTrue(report["summary"]["ok"], report["diagnostics"])
                self.assertEqual(report["summary"]["warning_count"], 0, report["diagnostics"])
                self.assertEqual(report["summary"]["event_error_count"], 0, report["diagnostics"])
                self.assert_no_touch_overlap(scene)

    def assert_no_touch_overlap(self, scene: object) -> None:
        for page in scene.pages:  # type: ignore[attr-defined]
            touchables = [
                widget
                for widget in page.widgets
                if widget.type in TOUCHABLE_TYPES and _rect(widget) is not None
            ]
            for left_index, left in enumerate(touchables):
                left_rect = _rect(left)
                self.assertIsNotNone(left_rect)
                for right in touchables[left_index + 1 :]:
                    right_rect = _rect(right)
                    self.assertIsNotNone(right_rect)
                    self.assertFalse(
                        _overlaps(left_rect, right_rect),
                        f"{page.id}.{left.id} overlaps {right.id}: {left_rect} vs {right_rect}",
                    )


def _load_index() -> dict[str, object]:
    return json.loads((TEMPLATE_ROOT / "template_index.json").read_text(encoding="utf-8"))


def _has_widget_type(scene: object, widget_type: str) -> bool:
    return any(widget.type == widget_type for page in scene.pages for widget in page.widgets)  # type: ignore[attr-defined]


def _rect(widget: object) -> tuple[int, int, int, int] | None:
    x = getattr(widget, "x")
    y = getattr(widget, "y")
    w = getattr(widget, "w")
    h = getattr(widget, "h")
    if x is None or y is None or w is None or h is None:
        return None
    return int(x), int(y), int(w), int(h)


def _overlaps(left: tuple[int, int, int, int], right: tuple[int, int, int, int]) -> bool:
    lx, ly, lw, lh = left
    rx, ry, rw, rh = right
    return lx < rx + rw and lx + lw > rx and ly < ry + rh and ly + lh > ry


if __name__ == "__main__":
    unittest.main()
