from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).absolute().parents[1]
TEMPLATE_ROOT = ROOT / "examples" / "econtest_templates"
DEFAULT_OUT_DIR = Path("build") / "econtest_preview_gallery"
PAGES = ("page0", "page1", "page2")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render all econtest template pages into a single gallery image.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--thumb-width", type=int, default=400)
    parser.add_argument("--thumb-height", type=int, default=240)
    parser.add_argument("--skip-render", action="store_true", help="Only rebuild the gallery from existing page PNG files.")
    args = parser.parse_args()
    out_dir = args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir

    index = json.loads((TEMPLATE_ROOT / "template_index.json").read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.skip_render:
        for template in index["templates"]:
            scene = TEMPLATE_ROOT / template["scene"]
            for page in PAGES:
                out_file = out_dir / f"{template['slug']}_{page}.png"
                subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "usarthmi",
                        "--json",
                        "scene",
                        "preview",
                        str(scene),
                        "--page",
                        page,
                        "--out",
                        str(out_file),
                    ],
                    cwd=ROOT,
                    check=True,
                    stdout=subprocess.DEVNULL,
                )

    gallery = compose_gallery(index["templates"], out_dir, args.thumb_width, args.thumb_height)
    gallery_path = out_dir / "all_templates_pages_gallery.png"
    gallery.save(gallery_path)
    print(gallery_path)
    return 0


def compose_gallery(templates: list[dict[str, object]], out_dir: Path, thumb_width: int, thumb_height: int) -> Image.Image:
    label_width = 150
    header_height = 24
    gallery = Image.new(
        "RGB",
        (label_width + thumb_width * len(PAGES), header_height + thumb_height * len(templates)),
        (30, 41, 59),
    )
    draw = ImageDraw.Draw(gallery)
    font = ImageFont.load_default()

    for column, page in enumerate(PAGES):
        x = label_width + column * thumb_width
        draw.rectangle([x, 0, x + thumb_width, header_height], fill=(15, 23, 42))
        draw.text((x + 8, 7), page, fill=(255, 255, 255), font=font)

    for row, template in enumerate(templates):
        slug = str(template["slug"])
        y = header_height + row * thumb_height
        draw.rectangle([0, y, label_width, y + thumb_height], fill=(30, 41, 59))
        draw.text((8, y + 12), slug, fill=(255, 255, 255), font=font)
        for column, page in enumerate(PAGES):
            image = Image.open(out_dir / f"{slug}_{page}.png").convert("RGB")
            image = image.resize((thumb_width, thumb_height))
            gallery.paste(image, (label_width + column * thumb_width, y))

    return gallery


if __name__ == "__main__":
    raise SystemExit(main())
