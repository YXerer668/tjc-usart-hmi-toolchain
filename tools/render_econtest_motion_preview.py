from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).absolute().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usarthmi.scene import load_scene  # noqa: E402

TEMPLATE_ROOT = ROOT / "examples" / "econtest_templates"
DEFAULT_OUT_DIR = Path("build") / "econtest_motion_preview"
DEFAULT_PAGE = "page0"
SWEEP_IDS = ("sweep_a", "sweep_b", "sweep_c")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render animated GIF previews for econtest template motion layers.")
    parser.add_argument("--template", default="power_converter", help="Template slug to render, or use --all.")
    parser.add_argument("--page", default=DEFAULT_PAGE, help="Page id to render.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--all", action="store_true", help="Render every template from template_index.json.")
    parser.add_argument("--frames", type=int, default=9)
    parser.add_argument("--duration-ms", type=int, default=160)
    args = parser.parse_args()

    if args.frames < 3:
        raise SystemExit("--frames must be at least 3")

    out_dir = args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    templates = _load_templates()
    selected = templates if args.all else [_template_by_slug(templates, args.template)]
    rendered: list[Path] = []
    for template in selected:
        rendered.append(
            render_motion_preview(
                template,
                page_id=args.page,
                out_dir=out_dir,
                frames=args.frames,
                duration_ms=args.duration_ms,
            )
        )

    if len(rendered) > 1:
        sheet = compose_contact_sheet(rendered)
        sheet_path = out_dir / f"motion_preview_{args.page}_contact_sheet.png"
        sheet.save(sheet_path)
        print(sheet_path)
    else:
        print(rendered[0])
    return 0


def render_motion_preview(template: dict[str, Any], *, page_id: str, out_dir: Path, frames: int, duration_ms: int) -> Path:
    slug = str(template["slug"])
    scene_path = TEMPLATE_ROOT / str(template["scene"])
    base_path = out_dir / f"{slug}_{page_id}_base.png"
    _render_scene_page(scene_path, page_id, base_path)

    scene = load_scene(scene_path)
    page = next(page for page in scene.pages if page.id == page_id)
    widgets = {widget.id: widget for widget in page.widgets}
    base = Image.open(base_path).convert("RGB")
    font = ImageFont.load_default()
    gif_frames = []
    for index in range(frames):
        frame = base.copy()
        draw = ImageDraw.Draw(frame)
        _paint_header_sweep(draw, widgets, index)
        _paint_beat(draw, widgets, index, font)
        _paint_topic_pulse(draw, widgets, index)
        gif_frames.append(frame)

    gif_path = out_dir / f"{slug}_{page_id}_motion.gif"
    gif_frames[0].save(
        gif_path,
        save_all=True,
        append_images=gif_frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=False,
    )
    return gif_path


def compose_contact_sheet(gif_paths: list[Path]) -> Image.Image:
    thumb_w = 320
    thumb_h = 192
    label_h = 22
    columns = 2
    rows = (len(gif_paths) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * thumb_w, rows * (thumb_h + label_h)), (15, 23, 42))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, gif_path in enumerate(gif_paths):
        row = index // columns
        column = index % columns
        x = column * thumb_w
        y = row * (thumb_h + label_h)
        image = Image.open(gif_path).convert("RGB").resize((thumb_w, thumb_h))
        sheet.paste(image, (x, y + label_h))
        draw.text((x + 8, y + 6), gif_path.stem.replace("_page0_motion", ""), fill=(255, 255, 255), font=font)
    return sheet


def _render_scene_page(scene_path: Path, page_id: str, out_file: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "usarthmi",
            "--json",
            "scene",
            "preview",
            str(scene_path),
            "--page",
            page_id,
            "--out",
            str(out_file),
        ],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )


def _paint_header_sweep(draw: ImageDraw.ImageDraw, widgets: dict[str, Any], frame_index: int) -> None:
    active = frame_index % len(SWEEP_IDS)
    for index, widget_id in enumerate(SWEEP_IDS):
        widget = widgets.get(widget_id)
        if widget is None:
            continue
        color = _rgb565_to_rgb(widget.style.get("background_color", 0))
        fill = _boost(color) if index == active else _dim(color)
        draw.rectangle(_rect(widget), fill=fill)


def _paint_beat(draw: ImageDraw.ImageDraw, widgets: dict[str, Any], frame_index: int, font: ImageFont.ImageFont) -> None:
    widget = widgets.get("beat")
    if widget is None:
        return
    rect = _rect(widget)
    draw.rectangle(rect, fill=(248, 250, 252), outline=_rgb565_to_rgb(widget.style.get("border_color", 0)))
    draw.text((rect[0] + 8, rect[1] + 4), f"{frame_index:03d}", fill=_rgb565_to_rgb(widget.style.get("foreground_color", 0)), font=font)


def _paint_topic_pulse(draw: ImageDraw.ImageDraw, widgets: dict[str, Any], frame_index: int) -> None:
    timer = widgets.get("tm_scene")
    if timer is None:
        return
    target_id = _first_hidden_target(timer.events.get("timer", []))
    if target_id is None or target_id not in widgets:
        return
    target = widgets[target_id]
    rect = _rect(target)
    if frame_index % 3 == 1:
        draw.rectangle(rect, outline=(255, 255, 255), width=3)
    else:
        draw.rectangle(rect, outline=_rgb565_to_rgb(target.style.get("foreground_color", 0)), width=2)


def _first_hidden_target(lines: list[str]) -> str | None:
    for line in lines:
        clean = line.strip()
        if clean.startswith("vis ") and clean.endswith(",0"):
            return clean[4:-2].strip()
    return None


def _rect(widget: Any) -> tuple[int, int, int, int]:
    return (int(widget.x), int(widget.y), int(widget.x + widget.w), int(widget.y + widget.h))


def _rgb565_to_rgb(value: int) -> tuple[int, int, int]:
    red = ((value >> 11) & 0x1F) * 255 // 31
    green = ((value >> 5) & 0x3F) * 255 // 63
    blue = (value & 0x1F) * 255 // 31
    return red, green, blue


def _boost(color: tuple[int, int, int]) -> tuple[int, int, int]:
    return tuple(min(255, int(channel * 1.35) + 18) for channel in color)


def _dim(color: tuple[int, int, int]) -> tuple[int, int, int]:
    return tuple(max(0, int(channel * 0.45)) for channel in color)


def _load_templates() -> list[dict[str, Any]]:
    index = json.loads((TEMPLATE_ROOT / "template_index.json").read_text(encoding="utf-8"))
    return list(index["templates"])


def _template_by_slug(templates: list[dict[str, Any]], slug: str) -> dict[str, Any]:
    for template in templates:
        if template["slug"] == slug:
            return template
    raise SystemExit(f"Unknown template slug: {slug}")


if __name__ == "__main__":
    raise SystemExit(main())
