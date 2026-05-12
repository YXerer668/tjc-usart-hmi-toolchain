from __future__ import annotations

from dataclasses import replace
from hashlib import sha1
import json
from pathlib import Path
from typing import Any

from PIL import Image

from .hmi_inspect import inspect_hmi
from .layout import resolve_page_layout
from .page_format import find_block_by_objname, load_page_file, parse_page_data
from .preview import render_scene_preview
from .scene import SceneModel, save_scene_json, widget_to_dict
from .tft_checksum import inspect_tft_checksum
from .tft_images import compile_hmi_picture_resource, pack_picture_resources_into_tft
from .tft_patch import DEFAULT_CASE_ROOT, TYPE_RECORD_LENGTHS, patch_added_object_tft, patch_multi_page_tft


class EditorError(RuntimeError):
    """Raised when scene build or page patching fails."""


FIXTURE_WIDGET_TEMPLATE_CASES = {
    "slider": ("case_17_slider", "\x01"),
    "gauge": ("case_18_gauge", "z"),
    "progress": ("case_20_progress", "j"),
    "qrcode": ("case_21_qrcode", ":"),
    "scrolling-text": ("case_22_scrolling_text", "7"),
    "dual-button": ("case_23_dual_state_button", "5"),
    "dualstate-button": ("case_23_dual_state_button", "5"),
    "state-button": ("case_24_state_button", "C"),
    "hotspot": ("case_25_hotspot_touch_area", "m"),
    "variable": ("case_26_variable_numeric_string", "4"),
    "waveform": ("case_27_waveform_basic", "\x00"),
    "checkbox": ("case_28_checkbox", "8"),
    "radio": ("case_29_radio", "9"),
    "crop-image": ("case_30_crop_image", "q"),
}
NON_VISUAL_WIDGET_TYPE_CODES = {"3", "4"}
STYLE_FIELD_ALIASES = {
    "background_color": "bco",
    "foreground_color": "pco",
    "border_color": "borderc",
    "font_id": "font",
    "enabled": "en",
    "interval_ms": "tim",
}
RESOURCE_FIELD_ALIASES = {
    "normal": "pic",
    "pressed": "pic2",
    "crop": "picc",
}
PAGE1_PLAIN_WIDGET_TYPES = {"text", "button", "number", "progress", "slider", "gauge"}


def import_asset(source: str | Path, out_dir: str | Path) -> dict[str, Any]:
    src = Path(source).resolve()
    out_base = Path(out_dir).resolve()
    out_base.mkdir(parents=True, exist_ok=True)

    image = Image.open(src).convert("RGBA")
    digest = sha1(src.read_bytes()).hexdigest()[:12]
    png_path = out_base / f"{src.stem}_{digest}.png"
    raw_path = out_base / f"{src.stem}_{digest}.rgb565"
    image.save(png_path)
    raw_path.write_bytes(_image_to_rgb565(image))
    return {
        "source": str(src),
        "normalized_png": str(png_path),
        "rgb565": str(raw_path),
        "width": image.width,
        "height": image.height,
        "digest": digest,
        "resource_id": int(digest[:4], 16) & 0xFFFF,
    }


def build_scene(
    scene: SceneModel,
    seed_hmi: str | Path,
    out_dir: str | Path,
    *,
    baseline_tft: str | Path | None = None,
) -> dict[str, Any]:
    seed_path = Path(seed_hmi).resolve()
    build_dir = Path(out_dir).resolve()
    build_dir.mkdir(parents=True, exist_ok=True)
    asset_dir = build_dir / "assets"
    asset_dir.mkdir(exist_ok=True)

    normalized_pages = []
    for page in scene.pages:
        normalized_widgets = resolve_page_layout(
            page.widgets,
            page.layout,
            int(scene.canvas["width"]),
            int(scene.canvas["height"]),
        )
        normalized_pages.append(replace(page, widgets=normalized_widgets))

    normalized_scene = SceneModel(
        project=scene.project,
        canvas=scene.canvas,
        assets=scene.assets,
        pages=normalized_pages,
    )
    if len(normalized_scene.pages) > 1:
        _validate_multi_page_scene_support(normalized_scene)

    manifest_assets: dict[str, Any] = {}
    for asset_key, asset in scene.assets.items():
        manifest_assets[asset_key] = _import_scene_asset(asset, asset_dir)
    packed_picture_ids = _assign_tft_picture_resource_ids(seed_path, normalized_scene, manifest_assets)

    output_hmi = build_dir / "output.hmi"
    hmi_picture_resources = build_hmi(normalized_scene, manifest_assets, seed_path, output_hmi)
    preview_png = render_scene_preview(normalized_scene, build_dir / "preview.png", manifest_assets=manifest_assets)
    baseline_pa = build_dir / "seed_0.pa"
    target_pa = build_dir / "target_0.pa"
    _write_hmi_entry(seed_path, "0.pa", baseline_pa)
    target_pages = []
    for index, _page in enumerate(normalized_pages):
        page_path = build_dir / f"target_{index}.pa"
        _write_hmi_entry(output_hmi, f"{index}.pa", page_path)
        target_pages.append(page_path)

    output_tft = None
    tft_patch = None
    tft_checksum = None
    tft_picture_pack = None
    resource_seed_tft = None
    warnings = [
        "Image assets are normalized and assigned resource ids; TFT image resource packing is experimental.",
    ]
    if baseline_tft is not None:
        baseline_tft_path = Path(baseline_tft).resolve()
        tft_seed_path = baseline_tft_path
        picture_sources = _collect_tft_picture_sources(manifest_assets, packed_picture_ids)
        if picture_sources:
            resource_seed_tft_path = build_dir / "resource_seed.tft"
            pack_result = pack_picture_resources_into_tft(
                baseline_tft_path,
                picture_sources,
                out_tft=resource_seed_tft_path,
            )
            tft_seed_path = resource_seed_tft_path
            resource_seed_tft = str(resource_seed_tft_path)
            tft_picture_pack = pack_result.to_dict()
        output_tft_path = build_dir / "output.tft"
        if len(target_pages) == 1:
            _validate_tft_target_support(baseline_pa, target_pa, packed_picture_ids=packed_picture_ids)
            patch_result = patch_added_object_tft(
                tft_seed_path,
                baseline_pa=baseline_pa,
                target_pa=target_pa,
                out_tft=output_tft_path,
            )
        else:
            if packed_picture_ids:
                raise EditorError("Multi-page TFT scene build does not support new image resources yet")
            patch_result = patch_multi_page_tft(
                tft_seed_path,
                baseline_pa=baseline_pa,
                target_pages=target_pages,
                out_tft=output_tft_path,
                allow_experimental_events=_experimental_multi_page_events_enabled(normalized_scene),
            )
        output_tft = str(output_tft_path)
        tft_patch = patch_result.to_dict()
        tft_checksum = inspect_tft_checksum(output_tft_path)
    else:
        warnings.append("output_tft is not emitted unless baseline_tft is provided.")

    normalized_path = build_dir / "scene.normalized.json"
    save_scene_json(normalized_scene, normalized_path)

    manifest = {
        "seed_hmi": str(seed_path),
        "baseline_tft": str(Path(baseline_tft).resolve()) if baseline_tft is not None else None,
        "resource_seed_tft": resource_seed_tft,
        "baseline_pa": str(baseline_pa),
        "target_pa": str(target_pa),
        "target_pages": [str(path) for path in target_pages],
        "output_hmi": str(output_hmi),
        "output_tft": output_tft,
        "tft_picture_pack": tft_picture_pack,
        "hmi_picture_resources": hmi_picture_resources,
        "preview_png": str(preview_png),
        "tft_patch": tft_patch,
        "tft_checksum": tft_checksum,
        "assets": manifest_assets,
        "pages": [
            {
                "id": page.id,
                "widgets": [widget_to_dict(widget) for widget in page.widgets],
            }
            for page in normalized_pages
        ],
        "warnings": warnings,
    }
    manifest_path = build_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def build_hmi(
    scene: SceneModel,
    manifest_assets: dict[str, Any],
    seed_hmi: Path,
    output_hmi: Path,
) -> list[dict[str, Any]]:
    inspection = inspect_hmi(seed_hmi)
    seed_bytes = seed_hmi.read_bytes()
    seed_entries = inspection.entries
    page_entry = next(entry for entry in seed_entries if entry.name == "0.pa")
    page_data = seed_bytes[page_entry.data_offset : page_entry.data_offset + page_entry.length]
    page = parse_page_data(page_data)

    seed_page_block = next(block.clone() for block in page.blocks if block.type_code == "y")
    unknown_blocks = [block.clone() for block in page.blocks if block.type_code not in {"y"}]
    if scene.project.get("clean_seed_objects"):
        _move_seed_objects_offscreen(
            unknown_blocks,
            width=int(scene.canvas["width"]),
            height=int(scene.canvas["height"]),
        )

    template_page_button = load_page_file(r"C:\Program Files (x86)\USART HMI\keyboardch\800480\1.page")
    button_proto = _first_block_of_type(page.blocks, "b") or find_block_by_objname(template_page_button, "b0").clone()
    number_proto = _first_block_of_type(page.blocks, "6")
    if number_proto is None:
        number_proto = _load_case_last_block("case_16_number_basic")
    timer_proto = _first_block_of_type(page.blocks, "3")
    if timer_proto is None:
        timer_proto = _load_case_last_block("case_19_timer")
    text_proto = _first_block_of_type(page.blocks, "t")
    if text_proto is None:
        template_page_text = load_page_file(r"C:\Program Files (x86)\USART HMI\keyboardch\800480\2.page")
        text_proto = find_block_by_objname(template_page_text, "t0").clone()
    picture_proto = next(block.clone() for block in page.blocks if block.type_code == "p")
    advanced_protos = _load_fixture_widget_templates(
        widget.type
        for scene_page in scene.pages
        for widget in scene_page.widgets
    )

    # Update page styling from scene canvas.
    if "background_color" in scene.canvas:
        seed_page_block.set_int("bco", int(scene.canvas["background_color"]), width=2)

    page0 = next(page for page in scene.pages if page.id == "page0")
    _apply_event_fields(seed_page_block, page0.events, owner="page0")

    next_id = max((_block_int(block, "id") or 0) for block in page.blocks) + 1
    generated_blocks = []
    for widget in page0.widgets:
        block = _build_widget_block(
            widget,
            next_id,
            button_proto=button_proto,
            picture_proto=picture_proto,
            number_proto=number_proto,
            timer_proto=timer_proto,
            text_proto=text_proto,
            advanced_protos=advanced_protos,
            manifest_assets=manifest_assets,
        )
        if block is None:
            raise EditorError(f"Scene widget type {widget.type!r} cannot be emitted by the HMI builder yet")
        generated_blocks.append(block)
        next_id += 1

    page.blocks = [seed_page_block] + unknown_blocks + generated_blocks
    rebuilt_page = page.serialize()
    page_entries = _build_extra_page_entries(
        page,
        scene.pages[1:],
        button_proto=button_proto,
        number_proto=number_proto,
        text_proto=text_proto,
        advanced_protos=advanced_protos,
        manifest_assets=manifest_assets,
    )
    picture_entries, picture_manifest = _build_hmi_picture_entries(seed_entries, manifest_assets)
    rebuilt_hmi = _rebuild_hmi_container(
        seed_bytes,
        seed_entries,
        replacements={"0.pa": rebuilt_page},
        additions=[*page_entries, *picture_entries],
    )
    output_hmi.write_bytes(rebuilt_hmi)
    return picture_manifest


def _build_extra_page_entries(
    seed_page,
    extra_pages,
    *,
    button_proto,
    number_proto,
    text_proto,
    advanced_protos,
    manifest_assets: dict[str, Any],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seed_page_block = next(block.clone() for block in seed_page.blocks if block.type_code == "y")
    for index, page_spec in enumerate(extra_pages, start=1):
        if page_spec.events:
            raise EditorError(
                "Multi-page HMI/TFT build V1 does not support extra-page events yet; "
                f"page {page_spec.id!r} has events"
            )
        if page_spec.id != f"page{index}":
            raise EditorError(
                "Multi-page HMI/TFT build V1 requires consecutive page ids page0, page1"
            )
        page = parse_page_data(seed_page.serialize())
        page.page_name = page_spec.id
        block = seed_page_block.clone()
        block.set_string("objname", page_spec.id, encoding="ascii")
        block.set_int("id", 0, width=1)
        generated_blocks = []
        for next_id, widget in enumerate(page_spec.widgets, start=1):
            widget_block = _build_widget_block(
                widget,
                next_id,
                button_proto=button_proto,
                picture_proto=None,
                number_proto=number_proto,
                timer_proto=None,
                text_proto=text_proto,
                advanced_protos=advanced_protos,
                manifest_assets=manifest_assets,
            )
            if widget_block is None:
                raise EditorError(
                    "Multi-page HMI/TFT build V1 extra pages currently support only "
                    "text/button/number/progress/slider/gauge widgets"
                )
            generated_blocks.append(widget_block)
        page.blocks = [block, *generated_blocks]
        entries.append(
            {
                "name": f"{index}.pa",
                "data": page.serialize(),
                "field3": 0x05111600,
                "kind": "page",
            }
        )
    return entries


def _build_widget_block(
    widget,
    next_id: int,
    *,
    button_proto,
    picture_proto,
    number_proto,
    timer_proto,
    text_proto,
    advanced_protos,
    manifest_assets: dict[str, Any],
):
    if widget.type == "button":
        block = button_proto.clone()
        _apply_common_widget_fields(block, widget, next_id)
        _apply_textual_fields(block, widget)
        _apply_color_fields(block, widget)
        _apply_button_asset_fields(block, widget, manifest_assets)
    elif widget.type == "image":
        if picture_proto is None:
            return None
        block = picture_proto.clone()
        _apply_common_widget_fields(block, widget, next_id)
        _apply_picture_fields(block, widget, manifest_assets)
    elif widget.type == "number":
        if number_proto is None:
            return None
        block = number_proto.clone()
        _apply_common_widget_fields(block, widget, next_id)
        block.set_int("val", int(widget.value or 0), width=4)
        _apply_color_fields(block, widget)
    elif widget.type == "text":
        block = text_proto.clone()
        _apply_common_widget_fields(block, widget, next_id)
        _apply_textual_fields(block, widget)
        _apply_color_fields(block, widget)
    elif widget.type == "timer":
        if timer_proto is None:
            return None
        block = timer_proto.clone()
        _apply_object_identity_fields(block, widget, next_id)
        _apply_timer_fields(block, widget)
    elif widget.type in FIXTURE_WIDGET_TEMPLATE_CASES:
        proto = advanced_protos.get(widget.type)
        if proto is None:
            return None
        block = proto.clone()
        _apply_common_widget_fields(block, widget, next_id)
        _apply_advanced_widget_fields(block, widget, manifest_assets)
    else:
        return None

    _clear_existing_events(block)
    _apply_event_fields(block, widget.events, owner=widget.id)
    return block


def _apply_common_widget_fields(block, widget, next_id: int) -> None:
    _apply_object_identity_fields(block, widget, next_id)
    if block.type_code in NON_VISUAL_WIDGET_TYPE_CODES:
        return
    _apply_geometry_fields(block, widget)


def _apply_object_identity_fields(block, widget, next_id: int) -> None:
    block.set_string("objname", widget.id, encoding="ascii")
    block.set_int("id", next_id, width=1)


def _apply_geometry_fields(block, widget) -> None:
    block.set_int("x", int(widget.x or 0), width=2)
    block.set_int("y", int(widget.y or 0), width=2)
    block.set_int("w", int(widget.w or 0), width=2)
    block.set_int("h", int(widget.h or 0), width=2)
    block.set_int("endx", int(widget.x or 0) + int(widget.w or 0) - 1, width=2)
    block.set_int("endy", int(widget.y or 0) + int(widget.h or 0) - 1, width=2)


def _move_seed_objects_offscreen(blocks, *, width: int, height: int) -> None:
    x = max(width + 32, 0)
    y = max(height + 32, 0)
    for block in blocks:
        if block.type_code == "y":
            continue
        block.set_int("x", x, width=2)
        block.set_int("y", y, width=2)
        block.set_int("w", 1, width=2)
        block.set_int("h", 1, width=2)
        block.set_int("endx", x, width=2)
        block.set_int("endy", y, width=2)


def _first_block_of_type(blocks, type_code: str):
    return next((block.clone() for block in blocks if block.type_code == type_code), None)


def _load_fixture_widget_templates(widget_types) -> dict[str, Any]:
    templates: dict[str, Any] = {}
    for widget_type in sorted(set(widget_types)):
        spec = FIXTURE_WIDGET_TEMPLATE_CASES.get(widget_type)
        if spec is None:
            continue
        case_name, type_code = spec
        templates[widget_type] = _load_case_block_of_type(case_name, type_code)
    return templates


def _load_case_last_block(case_name: str):
    hmi_path = DEFAULT_CASE_ROOT / case_name / "lcd_test.HMI"
    if not hmi_path.exists():
        raise EditorError(
            f"Timer/widget template fixture is missing: {hmi_path}. "
            "Provide local case fixtures or avoid this widget type for now."
        )
    inspection = inspect_hmi(hmi_path)
    raw = hmi_path.read_bytes()
    entry = next(item for item in inspection.entries if item.name == "0.pa")
    return parse_page_data(raw[entry.data_offset : entry.data_offset + entry.length]).blocks[-1].clone()


def _load_case_block_of_type(case_name: str, type_code: str):
    hmi_path = DEFAULT_CASE_ROOT / case_name / "lcd_test.HMI"
    if not hmi_path.exists():
        raise EditorError(
            f"Widget template fixture is missing: {hmi_path}. "
            f"Cannot create fixture-backed widget type {type_code!r} yet."
        )
    inspection = inspect_hmi(hmi_path)
    raw = hmi_path.read_bytes()
    entry = next(item for item in inspection.entries if item.name == "0.pa")
    page = parse_page_data(raw[entry.data_offset : entry.data_offset + entry.length])
    for block in page.blocks:
        if block.type_code == type_code:
            return block.clone()
    raise EditorError(f"Fixture {hmi_path} does not contain widget type {type_code!r}")


def _apply_textual_fields(block, widget) -> None:
    if widget.text is not None:
        block.set_string("txt", widget.text, encoding="gbk")
        existing_max = _block_int(block, "txt_maxl") or 0
        required = len(widget.text.encode("gbk"))
        block.set_int("txt_maxl", max(existing_max, required, 1), width=2)
    font_id = widget.style.get("font_id")
    if font_id is not None:
        block.set_int("font", int(font_id), width=1)


def _apply_color_fields(block, widget) -> None:
    if "background_color" in widget.style and block.get_field("bco"):
        block.set_int("bco", int(widget.style["background_color"]), width=2)
    if "foreground_color" in widget.style and block.get_field("pco"):
        block.set_int("pco", int(widget.style["foreground_color"]), width=2)
    if "border_color" in widget.style and block.get_field("borderc"):
        block.set_int("borderc", int(widget.style["border_color"]), width=2)
    if "style" in widget.style and block.get_field("style"):
        block.set_int("style", int(widget.style["style"]), width=1)


def _apply_asset_fields(block, widget, manifest_assets: dict[str, Any]) -> None:
    asset_ref = widget.resources.get("asset")
    if not asset_ref:
        return
    asset_info = manifest_assets.get(asset_ref)
    if not asset_info:
        raise EditorError(f"Asset '{asset_ref}' not imported")
    normal_id = int(_variant_resource_id(asset_info, "normal"))
    pressed_id = int(_variant_resource_id(asset_info, "pressed", fallback="normal"))
    disabled_id = _variant_resource_id(asset_info, "disabled")
    if block.get_field("pic"):
        block.set_int("pic", normal_id, width=2)
    if block.get_field("picc"):
        block.set_int("picc", pressed_id, width=2)
    if disabled_id is not None:
        if block.get_field("pic2"):
            block.set_int("pic2", int(disabled_id), width=2)
        if block.get_field("picc2"):
            block.set_int("picc2", int(disabled_id), width=2)


def _apply_button_asset_fields(block, widget, manifest_assets: dict[str, Any]) -> None:
    asset_ref = widget.resources.get("asset")
    if not asset_ref:
        return
    asset_info = manifest_assets.get(asset_ref)
    if not asset_info:
        raise EditorError(f"Asset '{asset_ref}' not imported")

    mode = str(widget.style.get("image_mode", "image")).lower()
    if mode not in {"image", "crop"}:
        raise EditorError(f"Button image_mode must be 'image' or 'crop', got {mode!r}")

    normal_id = int(_variant_resource_id(asset_info, "normal"))
    pressed_id = int(_variant_resource_id(asset_info, "pressed", fallback="normal"))
    disabled_id = _variant_resource_id(asset_info, "disabled")

    if mode == "crop":
        # sta=0 uses crop-image slots. Keep full-image slots untouched.
        block.set_int("sta", 0, width=1)
        if block.get_field("picc"):
            block.set_int("picc", normal_id, width=2)
        if block.get_field("picc2"):
            block.set_int("picc2", pressed_id, width=2)
    else:
        # sta=2 uses full-image slots: pic = normal, pic2 = pressed.
        block.set_int("sta", 2, width=1)
        if block.get_field("pic"):
            block.set_int("pic", normal_id, width=2)
        if block.get_field("pic2"):
            block.set_int("pic2", pressed_id, width=2)

    if disabled_id is not None:
        # The screen has no verified automatic disabled-state switch here yet;
        # keep the ID in the HMI/manifest for later event/usercode work.
        widget.resources.setdefault("disabled_pic", int(disabled_id))


def _apply_picture_fields(block, widget, manifest_assets: dict[str, Any]) -> None:
    explicit_pic = widget.resources.get("pic")
    if explicit_pic is not None:
        block.set_int("pic", int(explicit_pic), width=2)
        return
    _apply_asset_fields(block, widget, manifest_assets)


def _apply_timer_fields(block, widget) -> None:
    tim = widget.style.get("tim", widget.style.get("interval_ms", widget.value))
    if tim is not None:
        block.set_int("tim", int(tim), width=2)
    en = widget.style.get("en", widget.style.get("enabled"))
    if en is not None:
        block.set_int("en", 1 if bool(en) else 0, width=1)


def _apply_advanced_widget_fields(block, widget, manifest_assets: dict[str, Any]) -> None:
    if widget.text is not None:
        if block.get_field("txt") is None:
            raise EditorError(f"Widget {widget.id!r} of type {widget.type!r} does not support text")
        _apply_textual_fields(block, widget)
    else:
        font_id = widget.style.get("font_id")
        if font_id is not None and block.get_field("font") is not None:
            block.set_int("font", int(font_id), width=1)

    if widget.value is not None:
        _set_existing_int_field(block, "val", int(widget.value), owner=widget.id)

    _apply_color_fields(block, widget)
    _apply_style_fields(block, widget)
    _apply_resource_fields(block, widget, manifest_assets)


def _apply_style_fields(block, widget) -> None:
    handled = {
        "background_color",
        "foreground_color",
        "border_color",
        "font_id",
        "image_mode",
    }
    for raw_name, raw_value in widget.style.items():
        if raw_name in handled:
            continue
        field_name = STYLE_FIELD_ALIASES.get(raw_name, raw_name)
        if block.get_field(field_name) is None:
            raise EditorError(
                f"Style field {raw_name!r} is not supported by widget {widget.id!r} ({widget.type})"
            )
        if isinstance(raw_value, bool):
            value = 1 if raw_value else 0
        else:
            value = int(raw_value)
        _set_existing_int_field(block, field_name, value, owner=widget.id)


def _apply_resource_fields(block, widget, manifest_assets: dict[str, Any]) -> None:
    asset_ref = widget.resources.get("asset")
    if asset_ref:
        _apply_asset_fields(block, widget, manifest_assets)

    handled = {"asset", "disabled_pic"}
    for raw_name, raw_value in widget.resources.items():
        if raw_name in handled:
            continue
        field_name = RESOURCE_FIELD_ALIASES.get(raw_name, raw_name)
        if block.get_field(field_name) is None:
            raise EditorError(
                f"Resource field {raw_name!r} is not supported by widget {widget.id!r} ({widget.type})"
            )
        _set_existing_int_field(block, field_name, int(raw_value), owner=widget.id)


def _set_existing_int_field(block, name: str, value: int, *, owner: str) -> None:
    field = block.get_field(name)
    if field is None:
        raise EditorError(f"Widget {owner!r} does not have integer field {name!r}")
    block.set_int(name, value, width=max(1, len(field.value)))


def _apply_event_fields(block, events: dict[str, list[str]], *, owner: str) -> None:
    prefixes = {
        "load": "codesload-",
        "loadend": "codesloadend-",
        "down": "codesdown-",
        "up": "codesup-",
        "unload": "codesunload-",
        "timer": "codestimer-",
        "slide": "codesslide-",
    }
    for name, lines in events.items():
        prefix = prefixes.get(name)
        if prefix is None:
            raise EditorError(f"Unsupported event '{name}' on {owner}")
        block.set_event(prefix, list(lines))


def _build_hmi_picture_entries(entries, manifest_assets: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    existing_names = {entry.name for entry in entries if entry.name}
    image_field3 = _field3_template(entries, ".i")
    source_field3 = _field3_template(entries, ".is")
    additions: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []

    for picture_id, source in _collect_hmi_picture_sources(manifest_assets):
        image_name = f"{picture_id}.i"
        source_name = f"{picture_id}.is"
        if image_name in existing_names and source_name in existing_names:
            continue

        resource, image_entry, source_entry = compile_hmi_picture_resource(source, picture_id)
        if source_name not in existing_names:
            additions.append(
                {
                    "name": source_name,
                    "data": source_entry,
                    "field3": source_field3,
                    "kind": "source",
                }
            )
            existing_names.add(source_name)
        if image_name not in existing_names:
            additions.append(
                {
                    "name": image_name,
                    "data": image_entry,
                    "field3": image_field3,
                    "kind": "image",
                }
            )
            existing_names.add(image_name)
        manifest.append(resource.to_dict())

    return additions, manifest


def _collect_hmi_picture_sources(manifest_assets: dict[str, Any]) -> list[tuple[int, str]]:
    sources: dict[int, str] = {}
    for asset_info in manifest_assets.values():
        variants = asset_info.get("variants") or {}
        for variant_name in ("normal", "pressed", "disabled"):
            variant = variants.get(variant_name)
            if not variant or "resource_id" not in variant:
                continue
            sources[int(variant["resource_id"])] = str(variant["source"])
    return sorted(sources.items(), key=lambda item: item[0])


def _validate_multi_page_scene_support(scene: SceneModel) -> None:
    allow_events = _experimental_multi_page_events_enabled(scene)
    if len(scene.pages) != 2:
        raise EditorError("Multi-page build V1 supports exactly two pages: page0 and page1")
    expected_ids = ["page0", "page1"]
    page_ids = [page.id for page in scene.pages]
    if page_ids != expected_ids:
        raise EditorError(f"Multi-page build V1 requires pages {expected_ids}, got {page_ids}")
    if scene.pages[0].widgets or scene.pages[0].events:
        raise EditorError("Multi-page build V1 requires page0 to keep the seed object layout unchanged")
    if scene.pages[1].events:
        raise EditorError("Multi-page build V1 does not support page1 events yet")
    seen_ids = {"page0", "page1"}
    for widget in scene.pages[1].widgets:
        if widget.type not in PAGE1_PLAIN_WIDGET_TYPES:
            raise EditorError(
                "Multi-page build V1 page1 supports only "
                "text/button/number/progress/slider/gauge widgets"
            )
        if widget.id in seen_ids:
            raise EditorError(f"Multi-page build V1 page1 object name conflicts with {widget.id!r}")
        seen_ids.add(widget.id)
        if widget.events and not (
            allow_events and _is_supported_experimental_page1_event_widget(widget)
        ):
            raise EditorError("Multi-page build V1 does not support page1 widget events yet")
        if widget.resources:
            raise EditorError("Multi-page build V1 does not support page1 widget resources yet")
        if widget.children:
            raise EditorError("Multi-page build V1 does not support page1 child widgets yet")


def _experimental_multi_page_events_enabled(scene: SceneModel) -> bool:
    return bool(scene.project.get("experimental_multi_page_events"))


def _is_supported_experimental_page1_event_widget(widget) -> bool:
    if widget.type != "button":
        return False
    event_items = [(name, lines) for name, lines in widget.events.items() if lines]
    if len(event_items) != 1:
        return False
    event_name, lines = event_items[0]
    if event_name not in {"down", "up"} or len(lines) != 1:
        return False
    line = lines[0].strip().lower()
    return line in {"page 0", "page page0"}


def _field3_template(entries, suffix: str) -> int:
    for entry in reversed(entries):
        if entry.name.endswith(suffix):
            return entry.field3
    return 0


def _rebuild_hmi_container(
    seed_bytes: bytes,
    entries,
    *,
    replacements: dict[str, bytes],
    additions: list[dict[str, Any]],
) -> bytes:
    data_start = min(entry.data_offset for entry in entries if entry.in_file)
    source_additions = [item for item in additions if item.get("kind") == "source"]
    image_additions = [item for item in additions if item.get("kind") == "image"]
    page_additions = [item for item in additions if item.get("kind") == "page"]
    last_source_index = _last_entry_index(entries, ".is")
    last_image_index = _last_entry_index(entries, ".i")

    specs: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if entry.name == "0.pa":
            specs.extend(page_additions)
        data = replacements.get(entry.name)
        if data is None:
            data = seed_bytes[entry.data_offset : entry.data_offset + entry.length]
        specs.append({"name": entry.name, "data": data, "field3": entry.field3})
        if index == last_source_index:
            specs.extend(source_additions)
        if index == last_image_index:
            specs.extend(image_additions)

    if last_source_index < 0:
        specs.extend(source_additions)
    if last_image_index < 0:
        specs.extend(image_additions)

    directory_end = 4 + len(specs) * 28
    if directory_end > data_start:
        raise EditorError(
            f"HMI directory with {len(specs)} entries would overlap resource data at 0x{data_start:X}"
        )

    result = bytearray(seed_bytes[:data_start])
    result[0:4] = len(specs).to_bytes(4, "little")
    result[4:directory_end] = b"\x00" * (directory_end - 4)

    cursor = data_start
    for index, spec in enumerate(specs):
        base = 4 + index * 28
        name = str(spec["name"]).encode("ascii", errors="ignore")
        if len(name) > 16:
            raise EditorError(f"HMI entry name is too long: {spec['name']!r}")
        data = bytes(spec["data"])
        result[base : base + 16] = name.ljust(16, b"\x00")
        result[base + 16 : base + 20] = cursor.to_bytes(4, "little")
        result[base + 20 : base + 24] = len(data).to_bytes(4, "little")
        result[base + 24 : base + 28] = int(spec["field3"]).to_bytes(4, "little")
        if len(result) != cursor:
            raise EditorError("Internal HMI rebuild cursor drifted")
        result.extend(data)
        cursor += len(data)
    return bytes(result)


def _last_entry_index(entries, suffix: str) -> int:
    for index in range(len(entries) - 1, -1, -1):
        if entries[index].name.endswith(suffix):
            return index
    return -1


def _replace_hmi_entry(seed_bytes: bytes, entries, target_name: str, replacement: bytes) -> bytes:
    target = next((entry for entry in entries if entry.name == target_name), None)
    if target is None:
        raise EditorError(f"Entry '{target_name}' not found in seed HMI")

    result = bytearray(seed_bytes)
    target_end = target.data_offset + target.length
    last_end = max(entry.data_offset + entry.length for entry in entries)
    if target_end == last_end:
        result[target.data_offset:target_end] = replacement
        new_offset = target.data_offset
    else:
        new_offset = len(result)
        result.extend(replacement)

    base = target.dir_offset
    result[base + 16 : base + 20] = int(new_offset).to_bytes(4, "little")
    result[base + 20 : base + 24] = len(replacement).to_bytes(4, "little")
    return bytes(result)


def _write_hmi_entry(hmi_path: Path, entry_name: str, out_path: Path) -> Path:
    inspection = inspect_hmi(hmi_path)
    entry = next((item for item in inspection.entries if item.name == entry_name), None)
    if entry is None or not entry.in_file:
        raise EditorError(f"Entry '{entry_name}' not found in {hmi_path}")
    raw = hmi_path.read_bytes()
    out_path.write_bytes(raw[entry.data_offset : entry.data_offset + entry.length])
    return out_path


def _validate_tft_target_support(
    baseline_pa: Path,
    target_pa: Path,
    *,
    packed_picture_ids: set[int] | None = None,
) -> None:
    baseline_page = load_page_file(baseline_pa)
    target_page = load_page_file(target_pa)
    existing_pics = _existing_picture_ids(baseline_page.blocks)
    packed_pics = set(packed_picture_ids or set())
    allowed_pics = existing_pics | packed_pics
    added_blocks = target_page.blocks[len(baseline_page.blocks) :]
    for block in added_blocks:
        if block.type_code not in TYPE_RECORD_LENGTHS:
            raise EditorError(
                "TFT scene build does not know how to compile this object type yet: "
                f"object {block.objname!r} has type {block.type_code!r}"
            )
        for field_name in ("pic", "picc", "pic2", "picc2"):
            value = _block_int(block, field_name)
            if value is None or value == 0xFFFF:
                continue
            if value in packed_pics and block.type_code not in {"p", "b", "q"}:
                raise EditorError(
                    "TFT scene build can pack new image resources only for picture/button/crop-image objects in this pass: "
                    f"object {block.objname!r} has type {block.type_code!r} and references {field_name}={value}"
                )
            if value not in allowed_pics:
                raise EditorError(
                    "TFT scene build cannot pack new image resources yet: "
                    f"object {block.objname!r} references {field_name}={value}, "
                    f"but only existing seed pictures {sorted(existing_pics)} and packed pictures {sorted(packed_pics)} are available"
                )


def _existing_picture_ids(blocks) -> set[int]:
    values = {0xFFFF}
    for block in blocks:
        for field_name in ("pic", "picc", "pic2", "picc2"):
            value = _block_int(block, field_name)
            if value is not None:
                values.add(value)
    return values


def _block_int(block, name: str) -> int | None:
    field = block.get_field(name)
    if field is None or not field.value:
        return None
    return int.from_bytes(field.value, "little")


def _assign_tft_picture_resource_ids(
    seed_hmi: Path,
    scene: SceneModel,
    manifest_assets: dict[str, Any],
) -> set[int]:
    if not manifest_assets:
        return set()
    inspection = inspect_hmi(seed_hmi)
    seed_bytes = seed_hmi.read_bytes()
    page_entry = next(entry for entry in inspection.entries if entry.name == "0.pa")
    page = parse_page_data(seed_bytes[page_entry.data_offset : page_entry.data_offset + page_entry.length])
    existing_pics = {value for value in _existing_picture_ids(page.blocks) if value != 0xFFFF}
    next_picture_id = (max(existing_pics) + 1) if existing_pics else 0
    referenced_assets = _referenced_asset_keys(scene)
    packed_ids: set[int] = set()
    for asset_key in sorted(referenced_assets):
        asset_info = manifest_assets.get(asset_key)
        if not asset_info:
            raise EditorError(f"Asset '{asset_key}' not imported")
        variants = asset_info.get("variants") or {}
        for variant_name in ("normal", "pressed", "disabled"):
            variant = variants.get(variant_name)
            if not variant:
                continue
            while next_picture_id in existing_pics or next_picture_id in packed_ids:
                next_picture_id += 1
            variant["resource_id"] = next_picture_id
            packed_ids.add(next_picture_id)
            next_picture_id += 1
        normal_id = _variant_resource_id(asset_info, "normal")
        if normal_id is not None:
            asset_info["resource_id"] = int(normal_id)
    return packed_ids


def _referenced_asset_keys(scene: SceneModel) -> set[str]:
    keys: set[str] = set()
    for page in scene.pages:
        for widget in page.widgets:
            asset_key = widget.resources.get("asset")
            if asset_key:
                keys.add(str(asset_key))
    return keys


def _collect_tft_picture_sources(
    manifest_assets: dict[str, Any],
    packed_picture_ids: set[int],
) -> list[tuple[int, str]]:
    sources: list[tuple[int, str]] = []
    for asset_info in manifest_assets.values():
        variants = asset_info.get("variants") or {}
        for variant_name in ("normal", "pressed", "disabled"):
            variant = variants.get(variant_name)
            if not variant:
                continue
            picture_id = int(variant["resource_id"])
            if picture_id in packed_picture_ids:
                sources.append((picture_id, str(variant["source"])))
    return sources


def _image_to_rgb565(image: Image.Image) -> bytes:
    output = bytearray()
    rgba = image.convert("RGBA").tobytes()
    for offset in range(0, len(rgba), 4):
        red, green, blue, alpha = rgba[offset : offset + 4]
        if alpha == 0:
            red = green = blue = 0
        value = ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)
        output.extend(value.to_bytes(2, "little"))
    return bytes(output)


def _clear_existing_events(block) -> None:
    prefixes = []
    for token in block.event_tokens:
        if token.startswith("codes"):
            prefix = token.rsplit("-", 1)[0] + "-"
            if prefix not in prefixes:
                prefixes.append(prefix)
    for prefix in prefixes:
        block.set_event(prefix, [])


def _import_scene_asset(asset, out_dir: Path) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "id": asset.id,
        "source": asset.source,
        "variants": {},
    }

    if asset.normal or asset.pressed or asset.disabled:
        if asset.normal:
            manifest["variants"]["normal"] = import_asset(asset.normal, out_dir)
        if asset.pressed:
            manifest["variants"]["pressed"] = import_asset(asset.pressed, out_dir)
        if asset.disabled:
            manifest["variants"]["disabled"] = import_asset(asset.disabled, out_dir)
        if "normal" not in manifest["variants"] and asset.source:
            manifest["variants"]["normal"] = import_asset(asset.source, out_dir)
    else:
        manifest["variants"]["normal"] = import_asset(asset.source, out_dir)

    primary = manifest["variants"]["normal"]
    manifest.update(
        {
            "normalized_png": primary["normalized_png"],
            "rgb565": primary["rgb565"],
            "width": primary["width"],
            "height": primary["height"],
            "digest": primary["digest"],
            "resource_id": primary["resource_id"],
        }
    )
    return manifest


def _variant_resource_id(asset_info: dict[str, Any], variant: str, fallback: str | None = None) -> int | None:
    variants = asset_info.get("variants", {})
    if variant in variants:
        return int(variants[variant]["resource_id"])
    if fallback and fallback in variants:
        return int(variants[fallback]["resource_id"])
    if variant == "normal" and "resource_id" in asset_info:
        return int(asset_info["resource_id"])
    return None
