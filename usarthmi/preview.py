from __future__ import annotations

from hashlib import sha1
from io import BytesIO
from pathlib import Path
import re
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .hmi_inspect import inspect_hmi
from .layout import resolve_page_layout
from .page_format import PageBlock, PageFile, load_page_file, parse_page_data
from .scene import SceneError, SceneModel, WidgetSpec
from .zi_font import ZiFont, extract_zi_fonts_from_hmi, find_zi_fonts_in_directory, load_zi_fonts


PREVIEW_DEFAULT_WIDTH = 800
PREVIEW_DEFAULT_HEIGHT = 480
IMAGE_ENTRY_RE = re.compile(r"^(\d+)\.i[s]?$")
IMAGE_SIGNATURES = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")


def render_scene_preview(
    scene: SceneModel,
    out_path: str | Path,
    page_id: str = "page0",
    manifest_assets: dict[str, Any] | None = None,
    font_paths: dict[int, str | Path] | None = None,
) -> Path:
    width = int(scene.canvas["width"])
    height = int(scene.canvas["height"])
    background = int(scene.canvas.get("background_color", 65535))
    image = Image.new("RGBA", (width, height), _rgb565_to_rgb(background) + (255,))
    draw = ImageDraw.Draw(image)
    asset_lookup = _build_asset_lookup(scene, manifest_assets or {})
    fonts = load_zi_fonts(font_paths)

    page = next(page for page in scene.pages if page.id == page_id)
    widgets = resolve_page_layout(page.widgets, page.layout, width, height)

    for widget in widgets:
        _draw_widget(draw, image, widget, asset_lookup, fonts)

    target = Path(out_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(target)
    return target


def render_page_preview(
    page: PageFile,
    out_path: str | Path,
    *,
    width: int | None = None,
    height: int | None = None,
    show_labels: bool = True,
    picture_assets: dict[int, bytes] | None = None,
    fonts: dict[int, ZiFont] | None = None,
) -> Path:
    canvas_width, canvas_height = _resolve_page_size(page, width, height)
    page_block = _first_page_block(page)
    background = _rgb565_to_rgb(_field_int(page_block, "bco", 65535) if page_block else 65535)
    image = Image.new("RGBA", (canvas_width, canvas_height), background + (255,))
    draw = ImageDraw.Draw(image)

    for block in page.blocks:
        if block.type_code == "y":
            continue
        _draw_page_object(
            draw,
            image,
            block,
            show_labels=show_labels,
            picture_assets=picture_assets or {},
            fonts=fonts or {},
        )

    target = Path(out_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(target)
    return target


def render_pa_preview(
    pa_path: str | Path,
    out_path: str | Path,
    *,
    width: int | None = None,
    height: int | None = None,
    show_labels: bool = True,
    assets_dir: str | Path | None = None,
    font_paths: dict[int, str | Path] | None = None,
) -> dict[str, Any]:
    page_path = Path(pa_path).resolve()
    page = load_page_file(page_path)
    resource_dir = Path(assets_dir).resolve() if assets_dir else page_path.parent
    picture_assets = _load_picture_assets_from_dir(resource_dir)
    fonts = load_zi_fonts({**find_zi_fonts_in_directory(resource_dir), **(font_paths or {})})
    target = render_page_preview(
        page,
        out_path,
        width=width,
        height=height,
        show_labels=show_labels,
        picture_assets=picture_assets,
        fonts=fonts,
    )
    return _page_preview_result(page, target, source_path=page_path)


def render_hmi_preview(
    hmi_path: str | Path,
    out_path: str | Path,
    *,
    page: str = "0",
    width: int | None = None,
    height: int | None = None,
    show_labels: bool = True,
    font_paths: dict[int, str | Path] | None = None,
) -> dict[str, Any]:
    path = Path(hmi_path).resolve()
    entry_name = page if page.endswith(".pa") else f"{page}.pa"
    raw = path.read_bytes()
    inspection = inspect_hmi(path)
    entry = next((item for item in inspection.entries if item.name == entry_name), None)
    if entry is None or not entry.in_file:
        raise SceneError(f"HMI page entry '{entry_name}' was not found")
    page_file = parse_page_data(raw[entry.data_offset : entry.data_offset + entry.length])
    picture_assets = _load_picture_assets_from_hmi(raw, inspection.entries)
    fonts = {**extract_zi_fonts_from_hmi(raw, inspection.entries), **load_zi_fonts(font_paths)}
    target = render_page_preview(
        page_file,
        out_path,
        width=width,
        height=height,
        show_labels=show_labels,
        picture_assets=picture_assets,
        fonts=fonts,
    )
    return {
        **_page_preview_result(page_file, target, source_path=path),
        "entry": entry_name,
    }


def _draw_widget(
    draw: ImageDraw.ImageDraw,
    canvas: Image.Image,
    widget: WidgetSpec,
    manifest_assets: dict[str, Any],
    fonts: dict[int, ZiFont],
) -> None:
    x = int(widget.x or 0)
    y = int(widget.y or 0)
    w = int(widget.w or 0)
    h = int(widget.h or 0)
    if w <= 0 or h <= 0:
        return

    background = _rgb565_to_rgb(int(widget.style.get("background_color", 65535)))
    foreground = _rgb565_to_rgb(int(widget.style.get("foreground_color", 0)))
    border = _rgb565_to_rgb(int(widget.style.get("border_color", 0xC618)))
    shadow = tuple(max(channel - 28, 0) for channel in background)

    if widget.type == "text":
        draw.rounded_rectangle((x, y, x + w, y + h), radius=12, fill=background)
        _draw_text(
            draw,
            canvas,
            widget.text or "",
            (x, y, x + w, y + h),
            foreground,
            anchor="lt",
            font_id=int(widget.style.get("font_id", 0)),
            fonts=fonts,
        )
        return

    if widget.type == "number":
        draw.rounded_rectangle((x + 4, y + 6, x + w + 4, y + h + 6), radius=16, fill=shadow)
        draw.rounded_rectangle((x, y, x + w, y + h), radius=16, fill=background, outline=border, width=2)
        value_text = str(widget.value if widget.value is not None else 0)
        _draw_text(
            draw,
            canvas,
            value_text,
            (x, y, x + w, y + h),
            foreground,
            anchor="mm",
            font_id=int(widget.style.get("font_id", 0)),
            fonts=fonts,
        )
        return

    if widget.type in {"button", "image"}:
        draw.rounded_rectangle((x + 4, y + 6, x + w + 4, y + h + 6), radius=18, fill=shadow)
        draw.rounded_rectangle((x, y, x + w, y + h), radius=18, fill=background, outline=border, width=2)

        asset_ref = widget.resources.get("asset")
        asset_info = manifest_assets.get(asset_ref) if asset_ref else None
        _paste_widget_asset(canvas, widget, asset_info)

        if widget.type == "button" and widget.text:
            band_h = min(34, max(24, h // 3))
            band_color = tuple(max(channel - 24, 0) for channel in background)
            draw.rounded_rectangle((x, y + h - band_h, x + w, y + h), radius=18, fill=band_color)
            _draw_text(
                draw,
                canvas,
                widget.text,
                (x, y + h - band_h, x + w, y + h),
                foreground,
                anchor="mm",
                font_id=int(widget.style.get("font_id", 0)),
                fonts=fonts,
            )
        return

    if widget.type == "progress":
        value = _clamp_int(widget.value if widget.value is not None else 0, 0, 100)
        draw.rounded_rectangle((x, y, x + w, y + h), radius=max(h // 2, 1), fill=background, outline=border, width=2)
        fill_w = max((w - 4) * value // 100, 0)
        if fill_w:
            draw.rounded_rectangle((x + 2, y + 2, x + 2 + fill_w, y + h - 2), radius=max((h - 4) // 2, 1), fill=foreground)
        _draw_centered_label(draw, f"{value}%", (x, y, x + w, y + h), fill=(0, 0, 0))
        return

    if widget.type == "slider":
        value = _clamp_int(widget.value if widget.value is not None else 0, 0, 100)
        cy = y + h // 2
        draw.rounded_rectangle((x, cy - 5, x + w, cy + 5), radius=5, fill=background, outline=border, width=1)
        knob_x = x + value * max(w - 16, 1) // 100 + 8
        draw.ellipse((knob_x - 12, cy - 12, knob_x + 12, cy + 12), fill=foreground, outline=border, width=2)
        return

    if widget.type == "gauge":
        value = _clamp_int(widget.value if widget.value is not None else 0, 0, 100)
        box = (x, y, x + w, y + h)
        draw.ellipse(box, fill=(250, 250, 245), outline=border, width=3)
        draw.arc((x + 12, y + 12, x + w - 12, y + h - 12), 135, 405, fill=(210, 210, 205), width=9)
        draw.arc((x + 12, y + 12, x + w - 12, y + h - 12), 135, 135 + value * 270 // 100, fill=foreground, width=9)
        _draw_centered_label(draw, str(value), box, fill=(20, 28, 36))
        return

    if widget.type == "qrcode":
        draw.rectangle((x, y, x + w, y + h), fill=(255, 255, 255), outline=border, width=2)
        _draw_fake_qr(draw, widget.text or widget.id, (x + 8, y + 8, x + w - 8, y + h - 8))
        return

    if widget.type in {"scrolling-text", "dual-button", "state-button"}:
        radius = 8 if widget.type == "scrolling-text" else 14
        draw.rounded_rectangle((x, y, x + w, y + h), radius=radius, fill=background, outline=border, width=2)
        label = widget.text or widget.id
        if widget.type in {"dual-button", "state-button"} and widget.value:
            label = f"{label} ON"
        _draw_text(
            draw,
            canvas,
            label,
            (x, y, x + w, y + h),
            foreground,
            anchor="mm",
            font_id=int(widget.style.get("font_id", 0)),
            fonts=fonts,
        )
        return

    if widget.type == "checkbox":
        draw.rectangle((x, y, x + w, y + h), fill=background, outline=border, width=2)
        if widget.value:
            draw.line((x + 4, y + h // 2, x + w // 2, y + h - 5, x + w - 4, y + 4), fill=foreground, width=3)
        return

    if widget.type == "radio":
        draw.ellipse((x, y, x + w, y + h), fill=background, outline=border, width=2)
        if widget.value:
            pad = max(min(w, h) // 4, 3)
            draw.ellipse((x + pad, y + pad, x + w - pad, y + h - pad), fill=foreground)
        return

    if widget.type == "hotspot":
        _draw_dashed_rect(draw, (x, y, x + w, y + h), fill=(255, 128, 0))
        _draw_centered_label(draw, widget.id, (x, y, x + w, y + h), fill=(160, 72, 0))
        return

    if widget.type == "crop-image":
        draw.rectangle((x, y, x + w, y + h), fill=(232, 246, 255), outline=border, width=2)
        _draw_centered_label(draw, f"crop {widget.resources.get('picc', widget.resources.get('pic', ''))}", (x, y, x + w, y + h), fill=(40, 65, 80))
        return

    if widget.type == "waveform":
        draw.rectangle((x, y, x + w, y + h), fill=(12, 20, 26), outline=(60, 100, 120), width=2)
        for offset in range(1, 4):
            gy = y + offset * h // 4
            draw.line((x + 1, gy, x + w - 1, gy), fill=(28, 45, 55), width=1)
        points = []
        for index in range(32):
            px = x + 4 + index * max(w - 8, 1) // 31
            py = y + h // 2 + ((index * 37) % max(h // 2, 1)) - h // 4
            points.append((px, py))
        draw.line(points, fill=(0, 220, 120), width=2)
        return


def _paste_widget_asset(canvas: Image.Image, widget: WidgetSpec, asset_info: dict[str, Any] | None) -> None:
    if not asset_info:
        return
    variant = asset_info.get("variants", {}).get("normal") or asset_info
    png_path = variant.get("normalized_png")
    if not png_path:
        return

    source = Path(png_path)
    if not source.exists():
        return

    image = Image.open(source).convert("RGBA")
    x = int(widget.x or 0)
    y = int(widget.y or 0)
    w = int(widget.w or 0)
    h = int(widget.h or 0)
    pad = 14

    target_h = h - pad * 2
    if widget.type == "button" and widget.text:
        target_h -= min(34, max(24, h // 3))
    target_w = w - pad * 2
    if target_w <= 8 or target_h <= 8:
        return

    image.thumbnail((target_w, target_h))
    paste_x = x + (w - image.width) // 2
    paste_y = y + pad + max((target_h - image.height) // 2, 0)
    canvas.alpha_composite(image, (paste_x, paste_y))


def _build_asset_lookup(scene: SceneModel, manifest_assets: dict[str, Any]) -> dict[str, Any]:
    if manifest_assets:
        return manifest_assets

    lookup: dict[str, Any] = {}
    for key, asset in scene.assets.items():
        source = asset.normal or asset.source
        if not source:
            continue
        lookup[key] = {
            "variants": {
                "normal": {
                    "normalized_png": source,
                }
            }
        }
    return lookup


def _clamp_int(value: int, low: int, high: int) -> int:
    return max(low, min(high, int(value)))


def _draw_fake_qr(draw: ImageDraw.ImageDraw, text: str, box: tuple[int, int, int, int]) -> None:
    x1, y1, x2, y2 = box
    size = max(min(x2 - x1, y2 - y1), 21)
    cell = max(size // 21, 2)
    digest = sha1(text.encode("utf-8", errors="ignore")).digest()
    for row in range(21):
        for col in range(21):
            finder = (
                (row < 7 and col < 7)
                or (row < 7 and col >= 14)
                or (row >= 14 and col < 7)
            )
            if finder:
                on = row in {0, 6, 14, 20} or col in {0, 6, 14, 20} or (2 <= row % 14 <= 4 and 2 <= col % 14 <= 4)
            else:
                byte = digest[(row * 21 + col) % len(digest)]
                on = bool(byte & (1 << ((row + col) % 8)))
            if on:
                x = x1 + col * cell
                y = y1 + row * cell
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(0, 0, 0))


def _draw_dashed_rect(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], *, fill: tuple[int, int, int]) -> None:
    x1, y1, x2, y2 = box
    dash = 8
    for x in range(x1, x2, dash * 2):
        draw.line((x, y1, min(x + dash, x2), y1), fill=fill, width=2)
        draw.line((x, y2, min(x + dash, x2), y2), fill=fill, width=2)
    for y in range(y1, y2, dash * 2):
        draw.line((x1, y, x1, min(y + dash, y2)), fill=fill, width=2)
        draw.line((x2, y, x2, min(y + dash, y2)), fill=fill, width=2)


def _draw_text(
    draw: ImageDraw.ImageDraw,
    canvas: Image.Image,
    text: str,
    box: tuple[int, int, int, int],
    color: tuple[int, int, int],
    anchor: str = "mm",
    *,
    font_id: int = 0,
    fonts: dict[int, ZiFont] | None = None,
) -> None:
    x1, y1, x2, y2 = box
    width = max(x2 - x1, 1)
    height = max(y2 - y1, 1)
    zi_font = (fonts or {}).get(font_id)
    if zi_font is not None:
        text_w, text_h = zi_font.measure_text(text)
        if anchor == "lt":
            x, y = x1 + 8, y1 + max((height - text_h) // 2, 0)
        else:
            x = x1 + max((width - text_w) // 2, 0)
            y = y1 + max((height - text_h) // 2, 0)
        _paste_zi_text(canvas, zi_font, text, color, (x, y), box)
        return

    font = _load_font(max(min(height - 8, 32), 14))

    if anchor == "lt":
        draw.text((x1 + 8, y1 + 6), text, fill=color, font=font)
        return

    draw.text(((x1 + x2) // 2, (y1 + y2) // 2), text, fill=color, font=font, anchor="mm")


def _paste_zi_text(
    canvas: Image.Image,
    font: ZiFont,
    text: str,
    color: tuple[int, int, int],
    position: tuple[int, int],
    clip_box: tuple[int, int, int, int],
) -> None:
    glyphs = font.render_text(text, color)
    x, y = position
    x1, y1, x2, y2 = clip_box
    left = max(x1 - x, 0)
    top = max(y1 - y, 0)
    right = min(x2 - x + 1, glyphs.width)
    bottom = min(y2 - y + 1, glyphs.height)
    if right <= left or bottom <= top:
        return
    cropped = glyphs.crop((left, top, right, bottom))
    canvas.alpha_composite(cropped, (x + left, y + top))


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\nsimsun.ttc",
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyhbd.ttc",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _draw_page_object(
    draw: ImageDraw.ImageDraw,
    canvas: Image.Image,
    block: PageBlock,
    *,
    show_labels: bool,
    picture_assets: dict[int, bytes],
    fonts: dict[int, ZiFont],
) -> None:
    box = _block_box(block)
    if box is None:
        return

    x, y, w, h = box
    if w <= 0 or h <= 0:
        return

    x2 = x + w - 1
    y2 = y + h - 1
    type_code = block.type_code or "?"
    name = block.objname or type_code

    if type_code == "t":
        fill = _rgb565_to_rgb(_field_int(block, "bco", 65535))
        outline = _rgb565_to_rgb(_field_int(block, "borderc", 0xC618))
        draw.rectangle((x, y, x2, y2), fill=fill, outline=outline)
        _draw_page_text(draw, canvas, block, (x, y, x2, y2), fonts=fonts)
    elif type_code == "b":
        fill = _rgb565_to_rgb(_field_int(block, "bco", 50712))
        border = _rgb565_to_rgb(_field_int(block, "borderc", 0))
        border_width = max(_field_int(block, "borderw", 2), 1)
        shadow = tuple(max(channel - 35, 0) for channel in fill)
        draw.rectangle((x + 2, y + 2, x2 + 2, y2 + 2), fill=shadow)
        draw.rectangle((x, y, x2, y2), fill=fill, outline=border, width=border_width)
        _draw_page_text(draw, canvas, block, (x, y, x2, y2), fonts=fonts)
    elif type_code == "p":
        pic = _field_int(block, "pic", 0)
        if not _paste_picture_asset(canvas, picture_assets.get(pic), (x, y, x2, y2)):
            fill = (231, 255, 255)
            border = (60, 78, 90)
            draw.rectangle((x, y, x2, y2), fill=fill, outline=border, width=2)
            _draw_centered_label(draw, f"pic {pic}", (x, y, x2, y2), fill=(40, 48, 58))
            draw.line((x + 5, y + 5, x2 - 5, y2 - 5), fill=(135, 170, 180), width=1)
            draw.line((x2 - 5, y + 5, x + 5, y2 - 5), fill=(135, 170, 180), width=1)
    elif type_code in {"n", "x", "4"}:
        fill = _rgb565_to_rgb(_field_int(block, "bco", 65535))
        border = _rgb565_to_rgb(_field_int(block, "borderc", 0x8410))
        draw.rectangle((x, y, x2, y2), fill=fill, outline=border, width=1)
        _draw_centered_label(draw, str(_field_int(block, "val", 0)), (x, y, x2, y2), fill=_rgb565_to_rgb(_field_int(block, "pco", 0)))
    else:
        draw.rectangle((x, y, x2, y2), fill=(245, 245, 245), outline=(180, 85, 45), width=1)
        _draw_centered_label(draw, f"{name} ({type_code})", (x, y, x2, y2), fill=(120, 45, 20))

    if show_labels:
        _draw_object_label(draw, name, x, y)


def _draw_page_text(
    draw: ImageDraw.ImageDraw,
    canvas: Image.Image,
    block: PageBlock,
    box: tuple[int, int, int, int],
    *,
    fonts: dict[int, ZiFont],
) -> None:
    text = _field_text(block, "txt") or ""
    if not text:
        return
    color = _rgb565_to_rgb(_field_int(block, "pco", 0))
    x1, y1, x2, y2 = box
    xcen = _field_int(block, "xcen", 0)
    ycen = _field_int(block, "ycen", 0)
    font_id = _field_int(block, "font", 0) or 0
    zi_font = fonts.get(font_id)
    if zi_font is not None:
        text_w, text_h = zi_font.measure_text(text)
    else:
        font = _load_font(_font_size_for_box(box))
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

    if xcen == 1:
        x = x1 + max((x2 - x1 + 1 - text_w) // 2, 2)
    elif xcen == 2:
        x = x2 - text_w - 4
    else:
        x = x1 + 4

    if ycen == 1:
        y = y1 + max((y2 - y1 + 1 - text_h) // 2, 1) - 1
    elif ycen == 2:
        y = y2 - text_h - 2
    else:
        y = y1 + 2

    if zi_font is not None:
        _paste_zi_text(canvas, zi_font, text, color, (x, y), box)
    else:
        draw.text((x, y), text, fill=color, font=font)


def _paste_picture_asset(canvas: Image.Image, data: bytes | None, box: tuple[int, int, int, int]) -> bool:
    if not data:
        return False
    try:
        image = Image.open(BytesIO(data)).convert("RGBA")
    except OSError:
        return False
    x1, y1, x2, y2 = box
    width = max(x2 - x1 + 1, 1)
    height = max(y2 - y1 + 1, 1)
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    image = image.resize((width, height), resampling)
    canvas.alpha_composite(image, (x1, y1))
    return True


def _draw_object_label(draw: ImageDraw.ImageDraw, name: str, x: int, y: int) -> None:
    font = _load_font(12)
    bbox = draw.textbbox((0, 0), name, font=font)
    w = max(bbox[2] - bbox[0] + 4, 14)
    h = max(bbox[3] - bbox[1] + 3, 12)
    draw.rectangle((x, y, x + w, y + h), fill=(255, 255, 0))
    draw.text((x + 2, y), name, fill=(0, 0, 0), font=font)


def _draw_centered_label(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    *,
    fill: tuple[int, int, int],
) -> None:
    font = _load_font(_font_size_for_box(box))
    x1, y1, x2, y2 = box
    draw.text(((x1 + x2) // 2, (y1 + y2) // 2), text, fill=fill, font=font, anchor="mm")


def _font_size_for_box(box: tuple[int, int, int, int]) -> int:
    _, y1, _, y2 = box
    return max(min(y2 - y1 - 4, 30), 11)


def _block_box(block: PageBlock) -> tuple[int, int, int, int] | None:
    x = _field_int(block, "x")
    y = _field_int(block, "y")
    w = _field_int(block, "w")
    h = _field_int(block, "h")
    if x is not None and y is not None and w is not None and h is not None:
        return x, y, w, h

    endx = _field_int(block, "endx")
    endy = _field_int(block, "endy")
    if None not in {x, y, endx, endy}:
        assert x is not None and y is not None and endx is not None and endy is not None
        return x, y, endx - x + 1, endy - y + 1
    return None


def _first_page_block(page: PageFile) -> PageBlock | None:
    return next((block for block in page.blocks if block.type_code == "y"), None)


def _resolve_page_size(page: PageFile, width: int | None, height: int | None) -> tuple[int, int]:
    page_block = _first_page_block(page)
    resolved_width = width or _field_int(page_block, "w", PREVIEW_DEFAULT_WIDTH) if page_block else width
    resolved_height = height or _field_int(page_block, "h", PREVIEW_DEFAULT_HEIGHT) if page_block else height
    return int(resolved_width or PREVIEW_DEFAULT_WIDTH), int(resolved_height or PREVIEW_DEFAULT_HEIGHT)


def _page_preview_result(page: PageFile, target: Path, *, source_path: Path) -> dict[str, Any]:
    return {
        "source": str(source_path),
        "preview_png": str(target),
        "page_name": page.page_name,
        "object_count": len(page.blocks),
        "objects": [
            {
                "name": block.objname,
                "type": block.type_code,
                "box": _block_box(block),
            }
            for block in page.blocks
        ],
    }


def _field_int(block: PageBlock | None, name: str, default: int | None = None) -> int | None:
    if block is None:
        return default
    field = block.get_field(name)
    if field is None or not field.value:
        return default
    return int.from_bytes(field.value, "little")


def _field_text(block: PageBlock, name: str) -> str | None:
    field = block.get_field(name)
    if field is None:
        return None
    for encoding in ("utf-8", "gbk", "ascii"):
        try:
            return field.value.decode(encoding)
        except UnicodeDecodeError:
            continue
    return field.value.decode("latin-1", errors="replace")


def _load_picture_assets_from_dir(directory: Path) -> dict[int, bytes]:
    assets: dict[int, bytes] = {}
    if not directory.exists():
        return assets
    for path in sorted(directory.iterdir(), key=_picture_path_sort_key):
        match = IMAGE_ENTRY_RE.match(path.name)
        if not match:
            continue
        image_bytes = _extract_embedded_image(path.read_bytes())
        if image_bytes is None:
            continue
        pic_id = int(match.group(1))
        assets.setdefault(pic_id, image_bytes)
    return assets


def _load_picture_assets_from_hmi(raw: bytes, entries: list[Any]) -> dict[int, bytes]:
    assets: dict[int, bytes] = {}
    for entry in sorted(entries, key=lambda item: _picture_path_sort_key(Path(item.name))):
        match = IMAGE_ENTRY_RE.match(entry.name)
        if not match or not entry.in_file:
            continue
        data = raw[entry.data_offset : entry.data_offset + entry.length]
        image_bytes = _extract_embedded_image(data)
        if image_bytes is None:
            continue
        assets.setdefault(int(match.group(1)), image_bytes)
    return assets


def _picture_path_sort_key(path: Path) -> tuple[int, int, str]:
    match = IMAGE_ENTRY_RE.match(path.name)
    pic_id = int(match.group(1)) if match else 0xFFFF
    suffix_priority = 0 if path.suffix == ".i" else 1
    return pic_id, suffix_priority, path.name


def _extract_embedded_image(data: bytes) -> bytes | None:
    starts = [data.find(signature) for signature in IMAGE_SIGNATURES]
    starts = [item for item in starts if item >= 0]
    if not starts:
        return None
    return data[min(starts) :]


def _rgb565_to_rgb(value: int) -> tuple[int, int, int]:
    red = ((value >> 11) & 0x1F) * 255 // 31
    green = ((value >> 5) & 0x3F) * 255 // 63
    blue = (value & 0x1F) * 255 // 31
    return red, green, blue
