from __future__ import annotations

import argparse
import html
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from usarthmi.hmi_inspect import inspect_hmi  # noqa: E402


W, H = 800, 480


PALETTE = {
    "bg": "#071016",
    "panel": "#0f2230",
    "panel2": "#142b3a",
    "panel3": "#1d2735",
    "text": "#ecf7fb",
    "muted": "#9ab0bd",
    "line": "#2d4352",
    "teal": "#00a7b7",
    "blue": "#2a6fdb",
    "green": "#25a86f",
    "lime": "#73d13d",
    "amber": "#f0b429",
    "red": "#d94d64",
    "magenta": "#9b5de5",
    "cyan_soft": "#65d9e8",
    "white": "#ffffff",
    "black": "#000000",
}


PAGE_ROLES = {
    "PLANT CONTROL DASHBOARD": {"role": "dashboard", "header": "teal"},
    "ADVANCED DATA AND SERVICE": {"role": "detail", "header": "blue"},
    "ALARM RESPONSE MATRIX": {"role": "alarm", "header": "red"},
    "MAINTENANCE LOG AND FILES": {"role": "log", "header": "magenta"},
}


GEOMETRY_PATCHES: dict[str, dict[str, dict[str, int]]] = {
    "0.pa": {
        "recipe": {"x": 24, "y": 78, "w": 220, "h": 150},
        "filesvc": {"x": 290, "y": 78, "w": 230, "h": 150},
        "trendrec": {"x": 548, "y": 78, "w": 228, "h": 150},
        "svcbtn": {"x": 24, "y": 252, "w": 140, "h": 52},
        "alarmtx": {"x": 24, "y": 322, "w": 520, "h": 40},
        "p3btn": {"x": 328, "y": 392, "w": 124, "h": 50},
        "p2btn": {"x": 492, "y": 392, "w": 124, "h": 50},
        "homebtn": {"x": 652, "y": 392, "w": 124, "h": 50},
    },
    "1.pa": {
        "statbox": {"x": 24, "y": 76, "w": 170, "h": 54},
        "tempnum": {"x": 218, "y": 76, "w": 118, "h": 54},
        "rpmnum": {"x": 356, "y": 76, "w": 136, "h": 54},
        "assetqr": {"x": 654, "y": 76, "w": 118, "h": 118},
        "loadbar": {"x": 24, "y": 166, "w": 280, "h": 28},
        "pressbar": {"x": 24, "y": 218, "w": 280, "h": 28},
        "setslide": {"x": 24, "y": 270, "w": 280, "h": 34},
        "gauflow": {"x": 336, "y": 150, "w": 144, "h": 144},
        "chkauto": {"x": 526, "y": 156, "w": 34, "h": 34},
        "rdline": {"x": 526, "y": 210, "w": 34, "h": 34},
        "swrun": {"x": 588, "y": 204, "w": 92, "h": 44},
        "modebox": {"x": 500, "y": 270, "w": 180, "h": 42},
        "ticker": {"x": 24, "y": 326, "w": 560, "h": 38},
        "trendbtn": {"x": 280, "y": 392, "w": 104, "h": 50},
        "logbtn": {"x": 404, "y": 392, "w": 104, "h": 50},
        "detailbtn": {"x": 528, "y": 392, "w": 104, "h": 50},
        "alarmbtn": {"x": 652, "y": 392, "w": 112, "h": 50},
    },
    "2.pa": {
        "p2sev": {"x": 42, "y": 82, "w": 130, "h": 58},
        "p2risk": {"x": 206, "y": 98, "w": 310, "h": 30},
        "p2qr": {"x": 626, "y": 76, "w": 120, "h": 120},
        "p2ack": {"x": 54, "y": 176, "w": 34, "h": 34},
        "p2route": {"x": 54, "y": 236, "w": 34, "h": 34},
        "p2mute": {"x": 196, "y": 172, "w": 130, "h": 54},
        "p2tick": {"x": 420, "y": 172, "w": 130, "h": 54},
        "p2msg": {"x": 42, "y": 300, "w": 520, "h": 48},
        "p2next": {"x": 448, "y": 392, "w": 136, "h": 50},
        "p2home": {"x": 604, "y": 392, "w": 136, "h": 50},
    },
    "3.pa": {
        "p3status": {"x": 28, "y": 272, "w": 540, "h": 44},
        "p3cnt": {"x": 612, "y": 272, "w": 128, "h": 44},
        "p3bump": {"x": 292, "y": 392, "w": 130, "h": 50},
        "p3alarm": {"x": 448, "y": 392, "w": 136, "h": 50},
        "p3home": {"x": 604, "y": 392, "w": 136, "h": 50},
    },
}


BUTTON_COLORS = {
    "home": "green",
    "detail": "green",
    "alarm": "red",
    "p2": "red",
    "log": "magenta",
    "p3": "magenta",
    "trend": "blue",
    "service": "amber",
    "tick": "amber",
    "bump": "amber",
}


@dataclass(frozen=True)
class Obj:
    page: str
    index: int
    name: str
    kind: str
    fields: dict[str, Any]

    @property
    def x(self) -> int:
        return int(self.fields.get("x", 0))

    @property
    def y(self) -> int:
        return int(self.fields.get("y", 0))

    @property
    def w(self) -> int:
        return int(self.fields.get("w", 0))

    @property
    def h(self) -> int:
        return int(self.fields.get("h", 0))

    @property
    def r(self) -> int:
        return self.x + self.w

    @property
    def b(self) -> int:
        return self.y + self.h

    @property
    def txt(self) -> str:
        return str(self.fields.get("txt") or "")

    @property
    def visible(self) -> bool:
        return self.r > 0 and self.b > 0 and self.x < W and self.y < H


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a preview-only beautification proposal for a USART HMI project.")
    parser.add_argument("--hmi", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--title", default="Codex USART HMI beauty proposal")
    parser.add_argument("--current-only", action="store_true", help="Render the current HMI as-is without applying the built-in beauty proposal.")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    pages = load_pages(args.hmi)
    patch_plan = {} if args.current_only else build_patch_plan(pages)
    collisions = detect_collisions_for_plan(pages, patch_plan)

    page_images: list[tuple[str, Path]] = []
    for page_name, objects in ordered_pages(pages):
        image = render_page(page_name, objects, patch_plan.get(page_name, {}))
        safe = page_name.replace(".", "_")
        out = args.out_dir / f"beauty_{safe}.png"
        image.save(out)
        page_images.append((page_name, out))

    contact_sheet = render_contact_sheet(page_images, args.title)
    contact_path = args.out_dir / "beauty_preview_contact_sheet.png"
    contact_sheet.save(contact_path)

    plan_path = args.out_dir / "beauty_patch_plan.json"
    report_path = args.out_dir / "beauty_preview_report.json"
    html_path = args.out_dir / "beauty_preview.html"

    plan_payload = {
        "source": str(args.hmi.resolve()),
        "applied": False,
        "current_only": bool(args.current_only),
        "note": (
            "Current HMI rendered as-is; no proposal patches were applied."
            if args.current_only
            else "Preview only. These x/y/w/h/bco/pco changes are HMI-compatible candidates; no HMI bytes were modified."
        ),
        "patches": patch_plan,
    }
    plan_path.write_text(json.dumps(plan_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    report = {
        "source": str(args.hmi.resolve()),
        "preview_only": True,
        "current_only": bool(args.current_only),
        "page_count": len(pages),
        "collision_count": sum(len(items) for items in collisions.values()),
        "collisions": collisions,
        "outputs": {
            "contact_sheet": str(contact_path.resolve()),
            "html": str(html_path.resolve()),
            "patch_plan": str(plan_path.resolve()),
            "page_pngs": {page: str(path.resolve()) for page, path in page_images},
        },
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    html_path.write_text(render_html(args.title, page_images, report, patch_plan), encoding="utf-8")

    print(json.dumps({"ok": report["collision_count"] == 0, **report["outputs"]}, ensure_ascii=False, indent=2))
    return 0 if report["collision_count"] == 0 else 2


def ordered_pages(pages: dict[str, list[Obj]]) -> list[tuple[str, list[Obj]]]:
    role_order = {"dashboard": 0, "detail": 1, "alarm": 2, "log": 3}
    return sorted(
        pages.items(),
        key=lambda item: (role_order.get(page_role(item[1]).get("role", ""), 99), item[0]),
    )


def load_pages(path: Path) -> dict[str, list[Obj]]:
    inspection = inspect_hmi(path)
    pages: dict[str, list[Obj]] = {}
    for page in inspection.pa_pages:
        objects: list[Obj] = []
        for block in page.blocks:
            fields = block.fields or {}
            if not all(key in fields for key in ("x", "y", "w", "h")):
                continue
            keep = {
                key: value
                for key, value in fields.items()
                if key in {"x", "y", "w", "h", "txt", "val", "bco", "pco", "pic", "picc", "font", "sta"}
            }
            objects.append(
                Obj(
                    page=page.entry_name,
                    index=int(block.index),
                    name=str(block.objname or block.attr_name or ""),
                    kind=str(block.type_code or ""),
                    fields=keep,
                )
            )
        pages[page.entry_name] = objects
    return pages


def build_patch_plan(pages: dict[str, list[Obj]]) -> dict[str, dict[str, dict[str, int]]]:
    plan: dict[str, dict[str, dict[str, int]]] = {}
    for page_name, objects in pages.items():
        role = page_role(objects)
        header_key = role.get("header", "teal")
        for obj in objects:
            fields: dict[str, int] = dict(GEOMETRY_PATCHES.get(page_name, {}).get(obj.name, {}))
            lower = obj.name.lower()
            if obj.kind == "y":
                fields["bco"] = rgb565(PALETTE["bg"])
            elif obj.name in {"hbar", "dbar", "p2title", "p3title"}:
                fields["bco"] = rgb565(PALETTE[header_key])
                fields["pco"] = rgb565(PALETTE["white"])
            elif obj.kind == "b":
                key = next((value for token, value in BUTTON_COLORS.items() if token in lower or token in obj.txt.lower()), "blue")
                fields["bco"] = rgb565(PALETTE[key])
                fields["pco"] = rgb565(PALETTE["white"] if key != "amber" else "#081018")
            elif obj.kind in {"D", "A", "B", "=", "\x01"}:
                fields["bco"] = rgb565(PALETTE["panel2"])
                fields["pco"] = rgb565(PALETTE["text"])
            elif obj.kind == "6":
                fields["bco"] = rgb565(PALETTE["panel"])
                fields["pco"] = rgb565(PALETTE["amber"] if "temp" in lower or "sev" in lower else PALETTE["cyan_soft"])
            elif obj.kind == "j":
                fields["bco"] = rgb565(PALETTE["panel3"])
                fields["pco"] = rgb565(PALETTE["red"] if "risk" in lower else PALETTE["green"])
            elif obj.kind == "z":
                fields["bco"] = rgb565(PALETTE["panel"])
                fields["pco"] = rgb565(PALETTE["green"])
            elif obj.kind in {"t", ">"}:
                fields["bco"] = rgb565(PALETTE["panel"] if obj.y > 52 else PALETTE["bg"])
                fields["pco"] = rgb565(PALETTE["cyan_soft"] if obj.kind == ">" else PALETTE["text"])
            elif obj.kind == ":":
                fields["bco"] = rgb565(PALETTE["white"])
                fields["pco"] = rgb565(PALETTE["black"])
            elif obj.kind in {"8", "9"}:
                fields["bco"] = rgb565(PALETTE["white"])
                fields["pco"] = rgb565(PALETTE[header_key])
            elif obj.kind == "C":
                fields["bco"] = rgb565(PALETTE["green"])
                fields["pco"] = rgb565(PALETTE["white"])
            if fields:
                changed = {
                    key: value
                    for key, value in fields.items()
                    if int(obj.fields.get(key, -1)) != value
                }
                if changed:
                    plan.setdefault(page_name, {})[obj.name] = changed
    return plan


def page_role(objects: list[Obj]) -> dict[str, str]:
    for obj in objects:
        text = obj.txt.strip().upper()
        if text in PAGE_ROLES:
            return PAGE_ROLES[text]
    return {"role": "page", "header": "teal"}


def render_page(page_name: str, objects: list[Obj], page_patch: dict[str, dict[str, int]]) -> Image.Image:
    scale = 2
    image = Image.new("RGB", (W * scale, H * scale), hex_rgb(PALETTE["bg"]))
    draw = ImageDraw.Draw(image)

    def sx(value: int | float) -> int:
        return int(round(value * scale))

    role = page_role(objects)
    header_key = role.get("header", "teal")
    draw_grid(draw, scale)

    proposed_objects = apply_page_patch(objects, page_patch)

    for obj in sorted(proposed_objects, key=lambda item: item.index):
        if not obj.visible:
            continue
        draw_object(draw, scale, obj, obj.fields, header_key)

    draw.rectangle([0, 0, sx(W) - 1, sx(H) - 1], outline=hex_rgb(PALETTE["line"]), width=sx(2))
    return image.resize((W, H), Image.Resampling.LANCZOS)


def draw_grid(draw: ImageDraw.ImageDraw, scale: int) -> None:
    for x in range(0, W, 80):
        draw.line([(x * scale, 52 * scale), (x * scale, H * scale)], fill=(10, 28, 37), width=1)
    for y in range(52, H, 80):
        draw.line([(0, y * scale), (W * scale, y * scale)], fill=(10, 28, 37), width=1)


def draw_object(draw: ImageDraw.ImageDraw, scale: int, obj: Obj, fields: dict[str, Any], header_key: str) -> None:
    x, y, w, h = [int(fields.get(key, getattr(obj, key))) for key in ("x", "y", "w", "h")]
    box = [x * scale, y * scale, (x + w) * scale, (y + h) * scale]
    kind = obj.kind
    text = str(fields.get("txt") or obj.txt or obj.name)
    fill = color_from_field(fields.get("bco"), PALETTE["panel"])
    text_color = color_from_field(fields.get("pco"), PALETTE["text"])

    if kind == "y":
        draw.rectangle([0, 0, W * scale, H * scale], fill=fill)
        draw_grid(draw, scale)
        return
    if obj.name in {"hbar", "dbar", "p2title", "p3title"}:
        draw.rectangle(box, fill=fill)
        draw.rectangle([box[0], box[3] - scale, box[2], box[3]], fill=hex_rgb(PALETTE["cyan_soft"]))
        draw_text_fit(draw, text, (x + 24) * scale, (y + 12) * scale, max(120, w - 48) * scale, (h - 18) * scale, 24 * scale, text_color, bold=True)
        draw_status_pill(draw, scale, x + w - 142, y + 13, 118, 26, header_key)
        return
    if kind == "b":
        draw.rectangle(box, fill=fill, outline=hex_rgb("#d9f3fb"), width=max(1, scale))
        draw.rectangle([box[0], box[1], box[2], box[1] + 4 * scale], fill=lighten(fill, 0.24))
        draw_text_center(draw, text, box, 18 * scale, text_color, bold=True)
        return
    if kind == "j":
        val = max(0, min(100, int(fields.get("val", 0))))
        draw.rectangle(box, fill=fill, outline=hex_rgb(PALETTE["line"]), width=max(1, scale))
        pad = 3 * scale
        inner = [box[0] + pad, box[1] + pad, box[2] - pad, box[3] - pad]
        filled = inner[0] + int((inner[2] - inner[0]) * val / 100)
        draw.rectangle([inner[0], inner[1], filled, inner[3]], fill=text_color)
        label = f"{pretty_name(obj.name)} {val}%"
        draw_text_fit(draw, label, box[0] + 8 * scale, box[1] - 22 * scale, (w + 60) * scale, 18 * scale, 15 * scale, hex_rgb(PALETTE["muted"]))
        return
    if kind == "z":
        draw.rectangle(box, fill=fill, outline=hex_rgb(PALETTE["line"]), width=max(1, scale))
        val = max(0, min(240, int(fields.get("val", 0))))
        cx, cy = (x + w // 2) * scale, (y + h // 2 + 12) * scale
        radius = min(w, h) * scale // 2 - 18 * scale
        draw.arc([cx - radius, cy - radius, cx + radius, cy + radius], 210, 510, fill=hex_rgb(PALETTE["line"]), width=8 * scale)
        draw.arc([cx - radius, cy - radius, cx + radius, cy + radius], 210, 210 + int(300 * val / 240), fill=text_color, width=8 * scale)
        angle = math.radians(210 + 300 * val / 240)
        draw.line([cx, cy, cx + int(math.cos(angle) * radius * 0.72), cy + int(math.sin(angle) * radius * 0.72)], fill=hex_rgb(PALETTE["white"]), width=3 * scale)
        draw_text_center(draw, pretty_name(obj.name), [box[0], box[1] + 8 * scale, box[2], box[1] + 32 * scale], 14 * scale, hex_rgb(PALETTE["muted"]))
        return
    if kind == "6":
        draw.rectangle(box, fill=fill, outline=hex_rgb(PALETTE["line"]), width=max(1, scale))
        draw_text_fit(draw, pretty_name(obj.name), box[0] + 8 * scale, box[1] + 6 * scale, (w - 16) * scale, 16 * scale, 13 * scale, hex_rgb(PALETTE["muted"]))
        draw_text_center(draw, str(fields.get("val", "")), [box[0], box[1] + 18 * scale, box[2], box[3] - 4 * scale], 24 * scale, text_color, bold=True)
        return
    if kind == ":":
        draw.rectangle(box, fill=fill, outline=hex_rgb(PALETTE["line"]), width=max(1, scale))
        draw_qr_pattern(draw, box, scale)
        return
    if kind in {"8", "9"}:
        draw.rectangle(box, fill=fill, outline=hex_rgb(PALETTE["line"]), width=max(1, scale))
        if int(fields.get("val", 0)):
            if kind == "8":
                draw.line([box[0] + 7 * scale, box[1] + h * scale // 2, box[0] + 14 * scale, box[3] - 8 * scale, box[2] - 6 * scale, box[1] + 7 * scale], fill=text_color, width=4 * scale)
            else:
                draw.ellipse([box[0] + 8 * scale, box[1] + 8 * scale, box[2] - 8 * scale, box[3] - 8 * scale], fill=text_color)
        return
    if kind == "C":
        draw.rectangle(box, fill=fill, outline=hex_rgb(PALETTE["line"]), width=max(1, scale))
        draw_text_center(draw, text, box, 15 * scale, text_color, bold=True)
        return
    if kind in {"D", "A", "B", "="}:
        draw.rectangle(box, fill=fill, outline=hex_rgb(PALETTE["line"]), width=max(1, scale))
        draw.rectangle([box[0], box[1], box[2], box[1] + 24 * scale], fill=darken(fill, 0.16))
        draw_text_fit(draw, pretty_name(obj.name), box[0] + 10 * scale, box[1] + 5 * scale, (w - 20) * scale, 16 * scale, 13 * scale, hex_rgb(PALETTE["muted"]), bold=True)
        draw_wrapped_text(draw, text, box[0] + 10 * scale, box[1] + 36 * scale, (w - 20) * scale, (h - 44) * scale, 15 * scale, text_color)
        return

    draw.rectangle(box, fill=fill, outline=hex_rgb(PALETTE["line"]), width=max(1, scale))
    if text:
        draw_wrapped_text(draw, text, box[0] + 8 * scale, box[1] + 8 * scale, (w - 16) * scale, (h - 12) * scale, 15 * scale, text_color)


def draw_status_pill(draw: ImageDraw.ImageDraw, scale: int, x: int, y: int, w: int, h: int, header_key: str) -> None:
    box = [x * scale, y * scale, (x + w) * scale, (y + h) * scale]
    draw.rectangle(box, fill=hex_rgb("#081018"), outline=lighten(hex_rgb(PALETTE[header_key]), 0.18), width=max(1, scale))
    draw_text_center(draw, "LIVE COM36", box, 12 * scale, hex_rgb(PALETTE["cyan_soft"]), bold=True)


def draw_qr_pattern(draw: ImageDraw.ImageDraw, box: list[int], scale: int) -> None:
    size = min(box[2] - box[0], box[3] - box[1]) - 18 * scale
    left = box[0] + ((box[2] - box[0]) - size) // 2
    top = box[1] + ((box[3] - box[1]) - size) // 2
    cell = max(2 * scale, size // 21)
    for row in range(21):
        for col in range(21):
            finder = (row < 7 and col < 7) or (row < 7 and col > 13) or (row > 13 and col < 7)
            filled = finder or ((row * 5 + col * 7 + row * col) % 9 in {0, 2, 5})
            if filled:
                draw.rectangle([left + col * cell, top + row * cell, left + (col + 1) * cell - 1, top + (row + 1) * cell - 1], fill=hex_rgb(PALETTE["black"]))


def render_contact_sheet(page_images: list[tuple[str, Path]], title: str) -> Image.Image:
    thumb_w, thumb_h = 400, 240
    cols = 2
    rows = math.ceil(len(page_images) / cols)
    margin = 28
    header = 54
    sheet = Image.new("RGB", (cols * thumb_w + (cols + 1) * margin, rows * (thumb_h + 34) + header + margin), hex_rgb(PALETTE["bg"]))
    draw = ImageDraw.Draw(sheet)
    draw_text_fit(draw, title, margin, 14, sheet.width - margin * 2, 32, 24, hex_rgb(PALETTE["text"]), bold=True)
    for idx, (page, path) in enumerate(page_images):
        img = Image.open(path).convert("RGB").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = margin + (idx % cols) * (thumb_w + margin)
        y = header + (idx // cols) * (thumb_h + 34)
        sheet.paste(img, (x, y))
        draw.rectangle([x, y, x + thumb_w - 1, y + thumb_h - 1], outline=hex_rgb(PALETTE["line"]))
        draw_text_fit(draw, page, x, y + thumb_h + 7, thumb_w, 22, 16, hex_rgb(PALETTE["muted"]), bold=True)
    return sheet


def render_html(title: str, page_images: list[tuple[str, Path]], report: dict[str, Any], patch_plan: dict[str, Any]) -> str:
    cards = []
    for page, path in page_images:
        cards.append(
            f"""
            <section>
              <h2>{html.escape(page)}</h2>
              <img src="{html.escape(path.name)}" alt="{html.escape(page)} preview">
            </section>
            """
        )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
body {{ margin: 0; background: #071016; color: #ecf7fb; font-family: Segoe UI, Arial, sans-serif; }}
header {{ padding: 18px 24px; border-bottom: 1px solid #2d4352; background: #0f2230; }}
h1 {{ margin: 0; font-size: 22px; }}
.meta {{ color: #9ab0bd; margin-top: 6px; font-size: 13px; }}
main {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; padding: 20px 24px; }}
section {{ min-width: 0; }}
h2 {{ font-size: 15px; color: #9ab0bd; margin: 0 0 8px; }}
img {{ width: 100%; max-width: 800px; height: auto; border: 1px solid #2d4352; background: #071016; }}
code {{ color: #65d9e8; }}
</style>
</head>
<body>
<header>
  <h1>{html.escape(title)}</h1>
  <div class="meta">Preview only. Collision count: <code>{int(report["collision_count"])}</code>. Proposed object color patches: <code>{sum(len(v) for v in patch_plan.values())}</code>.</div>
</header>
<main>
{''.join(cards)}
</main>
</body>
</html>
"""


def detect_collisions(pages: dict[str, list[Obj]]) -> dict[str, list[dict[str, Any]]]:
    interactive = {"b", "C", "8", "9", "\x01"}
    result: dict[str, list[dict[str, Any]]] = {}
    for page, objects in pages.items():
        visible = [obj for obj in objects if obj.visible and not (obj.kind == "y" and obj.x == 0 and obj.y == 0 and obj.w >= W and obj.h >= H)]
        collisions: list[dict[str, Any]] = []
        for i, left in enumerate(visible):
            for right in visible[i + 1 :]:
                ix = max(0, min(left.r, right.r) - max(left.x, right.x))
                iy = max(0, min(left.b, right.b) - max(left.y, right.y))
                if ix < 4 or iy < 4:
                    continue
                if left.kind not in interactive and right.kind not in interactive:
                    continue
                collisions.append(
                    {
                        "a": left.name,
                        "b": right.name,
                        "intersection": [max(left.x, right.x), max(left.y, right.y), ix, iy],
                    }
                )
        result[page] = collisions
    return result


def detect_collisions_for_plan(pages: dict[str, list[Obj]], patch_plan: dict[str, dict[str, dict[str, int]]]) -> dict[str, list[dict[str, Any]]]:
    patched = {page: apply_page_patch(objects, patch_plan.get(page, {})) for page, objects in pages.items()}
    return detect_collisions(patched)


def apply_page_patch(objects: list[Obj], page_patch: dict[str, dict[str, int]]) -> list[Obj]:
    result: list[Obj] = []
    for obj in objects:
        patch = page_patch.get(obj.name)
        if not patch:
            result.append(obj)
            continue
        fields = dict(obj.fields)
        fields.update(patch)
        result.append(Obj(page=obj.page, index=obj.index, name=obj.name, kind=obj.kind, fields=fields))
    return result


def draw_text_center(draw: ImageDraw.ImageDraw, text: str, box: list[int], size: int, fill: tuple[int, int, int], *, bold: bool = False) -> None:
    font = font_for(size, bold=bold)
    text = fit_text(draw, text, font, max(1, box[2] - box[0] - 8))
    bbox = draw.textbbox((0, 0), text, font=font)
    tx = box[0] + ((box[2] - box[0]) - (bbox[2] - bbox[0])) // 2
    ty = box[1] + ((box[3] - box[1]) - (bbox[3] - bbox[1])) // 2 - bbox[1]
    draw.text((tx, ty), text, font=font, fill=fill)


def draw_text_fit(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    w: int,
    h: int,
    size: int,
    fill: tuple[int, int, int],
    *,
    bold: bool = False,
) -> None:
    font = font_for(size, bold=bold)
    text = fit_text(draw, text, font, max(1, w))
    draw.text((x, y), text, font=font, fill=fill)


def draw_wrapped_text(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, w: int, h: int, size: int, fill: tuple[int, int, int]) -> None:
    font = font_for(size)
    words = text.replace("_", "_ ").split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if draw.textlength(candidate, font=font) <= w:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    line_h = int(size * 1.18)
    max_lines = max(1, h // max(1, line_h))
    for idx, line in enumerate(lines[:max_lines]):
        if idx == max_lines - 1 and len(lines) > max_lines:
            line = fit_text(draw, line + " ...", font, w)
        draw.text((x, y + idx * line_h), line, font=font, fill=fill)


def fit_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> str:
    if draw.textlength(text, font=font) <= width:
        return text
    ellipsis = "..."
    while text and draw.textlength(text + ellipsis, font=font) > width:
        text = text[:-1]
    return (text + ellipsis) if text else ellipsis


def font_for(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    font_name = "segoeuib.ttf" if bold else "segoeui.ttf"
    path = Path("C:/Windows/Fonts") / font_name
    if path.exists():
        return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def pretty_name(name: str) -> str:
    table = {
        "tempnum": "TEMP",
        "rpmnum": "RPM",
        "loadbar": "LOAD",
        "pressbar": "PRESS",
        "setslide": "SETPOINT",
        "gauflow": "FLOW",
        "p2sev": "SEVERITY",
        "p2risk": "RISK",
        "p3cnt": "COUNT",
    }
    return table.get(name.lower(), name.upper())


def rgb565(hex_color: str) -> int:
    r, g, b = hex_rgb(hex_color)
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


def color_from_field(value: object, fallback_hex: str) -> tuple[int, int, int]:
    if isinstance(value, int):
        return rgb565_to_rgb(value)
    if isinstance(value, str) and value.isdigit():
        return rgb565_to_rgb(int(value))
    return hex_rgb(fallback_hex)


def rgb565_to_rgb(value: int) -> tuple[int, int, int]:
    r = ((value >> 11) & 0x1F) * 255 // 31
    g = ((value >> 5) & 0x3F) * 255 // 63
    b = (value & 0x1F) * 255 // 31
    return r, g, b


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def lighten(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(min(255, int(c + (255 - c) * amount)) for c in color)


def darken(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(max(0, int(c * (1 - amount))) for c in color)


if __name__ == "__main__":
    raise SystemExit(main())
