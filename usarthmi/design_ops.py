from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from .layout import resolve_page_layout
from .scene import PageSpec, SceneError, SceneModel, WidgetSpec, load_scene, validate_scene
from .scene_edit import read_scene_document, update_scene_widget, write_scene_document


DESIGN_PATCH_SCHEMA_VERSION = 1
DESIGN_NOT_CLAIMED = (
    "design operations edit scene geometry only",
    "design operations do not build or upload a TFT",
    "drag/resize preview is not live-panel proof",
    "non-absolute layouts may resolve geometry differently at render time",
)
ALIGN_EDGES = ("left", "right", "top", "bottom", "hcenter", "vcenter")
ALIGN_ANCHORS = ("first", "last", "canvas")
DISTRIBUTE_AXES = ("horizontal", "vertical")
MATCH_SIZE_MODES = ("width", "height", "both")
MATCH_SIZE_ANCHORS = ("first", "last")


def design_move_widget(
    scene_path: str | Path,
    out_dir: str | Path | None,
    *,
    page_id: str,
    widget_id: str,
    x: int | None = None,
    y: int | None = None,
    dx: int = 0,
    dy: int = 0,
    snap: int = 1,
    clamp: bool = True,
    source: str = "design-op",
) -> dict[str, Any]:
    """Move one widget in the editable scene model and write agent patch artifacts."""
    context = _widget_context(scene_path, page_id, widget_id)
    old = context["geometry"]
    requested = {
        "x": old["x"] + int(dx) if x is None else int(x),
        "y": old["y"] + int(dy) if y is None else int(y),
        "w": old["w"],
        "h": old["h"],
    }
    if requested["x"] == old["x"] and requested["y"] == old["y"]:
        raise SceneError("design move requires a changed x/y or non-zero dx/dy")
    new_geometry, diagnostics = _normalize_geometry(
        requested,
        canvas=context["canvas"],
        snap=snap,
        clamp=clamp,
        preserve_size=True,
    )
    op = _design_op(
        "move_widget",
        source=source,
        page_id=page_id,
        widget_id=widget_id,
        old=old,
        requested=requested,
        new_geometry=new_geometry,
        diagnostics=[*context["diagnostics"], *diagnostics],
        snap=snap,
        clamp=clamp,
    )
    result = update_scene_widget(
        scene_path,
        page_id=page_id,
        widget_id=widget_id,
        updates={"x": new_geometry["x"], "y": new_geometry["y"], "w": new_geometry["w"], "h": new_geometry["h"]},
    )
    return _design_result(scene_path, out_dir, result=result, op=op)


def design_resize_widget(
    scene_path: str | Path,
    out_dir: str | Path | None,
    *,
    page_id: str,
    widget_id: str,
    w: int | None = None,
    h: int | None = None,
    dw: int = 0,
    dh: int = 0,
    min_size: int = 1,
    snap: int = 1,
    clamp: bool = True,
    source: str = "design-op",
) -> dict[str, Any]:
    """Resize one widget in the editable scene model and write agent patch artifacts."""
    context = _widget_context(scene_path, page_id, widget_id)
    old = context["geometry"]
    requested = {
        "x": old["x"],
        "y": old["y"],
        "w": old["w"] + int(dw) if w is None else int(w),
        "h": old["h"] + int(dh) if h is None else int(h),
    }
    if requested["w"] == old["w"] and requested["h"] == old["h"]:
        raise SceneError("design resize requires a changed w/h or non-zero dw/dh")
    requested["w"] = max(int(min_size), requested["w"])
    requested["h"] = max(int(min_size), requested["h"])
    new_geometry, diagnostics = _normalize_geometry(
        requested,
        canvas=context["canvas"],
        snap=snap,
        clamp=clamp,
        preserve_size=False,
        min_size=min_size,
    )
    op = _design_op(
        "resize_widget",
        source=source,
        page_id=page_id,
        widget_id=widget_id,
        old=old,
        requested=requested,
        new_geometry=new_geometry,
        diagnostics=[*context["diagnostics"], *diagnostics],
        snap=snap,
        clamp=clamp,
    )
    result = update_scene_widget(
        scene_path,
        page_id=page_id,
        widget_id=widget_id,
        updates={"x": new_geometry["x"], "y": new_geometry["y"], "w": new_geometry["w"], "h": new_geometry["h"]},
    )
    return _design_result(scene_path, out_dir, result=result, op=op)


def design_align_widgets(
    scene_path: str | Path,
    out_dir: str | Path | None,
    *,
    page_id: str,
    widget_ids: list[str] | tuple[str, ...],
    edge: str,
    anchor: str = "first",
    snap: int = 1,
    clamp: bool = True,
    source: str = "design-op",
) -> dict[str, Any]:
    """Align multiple widgets in the editable scene model and write agent patch artifacts."""
    if edge not in ALIGN_EDGES:
        raise SceneError(f"Unsupported align edge: {edge}")
    if anchor not in ALIGN_ANCHORS:
        raise SceneError(f"Unsupported align anchor: {anchor}")
    ids = [str(item) for item in widget_ids if str(item)]
    if len(ids) < 1:
        raise SceneError("design align requires at least one widget")
    if len(set(ids)) != len(ids):
        raise SceneError("design align requires unique widgets")
    if anchor != "canvas" and len(ids) < 2:
        raise SceneError("design align requires at least two widgets unless --anchor canvas is used")

    scene = load_scene(scene_path)
    page = _find_page(scene, page_id)
    canvas = {"width": int(scene.canvas["width"]), "height": int(scene.canvas["height"])}
    geometry_by_id = _page_geometry_by_id(scene, page)
    missing = [widget_id for widget_id in ids if widget_id not in geometry_by_id]
    if missing:
        raise SceneError(f"Widget(s) not found on page '{page_id}': {', '.join(missing)}")
    target = _align_target(edge, anchor, ids, geometry_by_id, canvas)
    diagnostics: list[dict[str, Any]] = []
    layout_type = str(page.layout.get("type") or "absolute")
    if layout_type != "absolute":
        diagnostics.append(
            {
                "severity": "warning",
                "code": "NON_ABSOLUTE_LAYOUT",
                "message": f"Page {page_id!r} uses layout {layout_type!r}; explicit geometry may be re-resolved by layout.",
            }
        )
    updates: list[dict[str, Any]] = []
    for widget_id in ids:
        old = geometry_by_id[widget_id]
        requested = _aligned_geometry(old, edge=edge, target=target)
        new_geometry, item_diagnostics = _normalize_geometry(
            requested,
            canvas=canvas,
            snap=snap,
            clamp=clamp,
            preserve_size=True,
        )
        diagnostics.extend({"widget": widget_id, **item} for item in item_diagnostics)
        updates.append(
            {
                "widget": widget_id,
                "from": dict(old),
                "requested": dict(requested),
                "to": dict(new_geometry),
            }
        )
    changed = [item for item in updates if item["from"] != item["to"]]
    if not changed:
        raise SceneError("design align did not change any widget geometry")

    _write_widget_geometries(scene_path, page_id=page_id, updates=updates)
    op = {
        "op": "align_widgets",
        "source": source,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "page": page_id,
        "widgets": ids,
        "edge": edge,
        "anchor": anchor,
        "target": target,
        "snap": int(snap),
        "clamp": bool(clamp),
        "items": updates,
        "diagnostics": diagnostics,
    }
    outputs = _write_design_artifacts(scene_path, out_dir, op)
    return {
        "scene_path": str(Path(scene_path).resolve()),
        "page": page_id,
        "widgets": [{"id": item["widget"], **item["to"]} for item in updates],
        "op": op,
        "outputs": outputs,
        "not_claimed": list(DESIGN_NOT_CLAIMED),
    }


def design_distribute_widgets(
    scene_path: str | Path,
    out_dir: str | Path | None,
    *,
    page_id: str,
    widget_ids: list[str] | tuple[str, ...],
    axis: str,
    snap: int = 1,
    clamp: bool = True,
    source: str = "design-op",
) -> dict[str, Any]:
    """Distribute three or more widgets evenly by center point on one axis."""
    if axis not in DISTRIBUTE_AXES:
        raise SceneError(f"Unsupported distribute axis: {axis}")
    ids = [str(item) for item in widget_ids if str(item)]
    if len(ids) < 3:
        raise SceneError("design distribute requires at least three widgets")
    if len(set(ids)) != len(ids):
        raise SceneError("design distribute requires unique widgets")

    scene = load_scene(scene_path)
    page = _find_page(scene, page_id)
    canvas = {"width": int(scene.canvas["width"]), "height": int(scene.canvas["height"])}
    geometry_by_id = _page_geometry_by_id(scene, page)
    missing = [widget_id for widget_id in ids if widget_id not in geometry_by_id]
    if missing:
        raise SceneError(f"Widget(s) not found on page '{page_id}': {', '.join(missing)}")

    ordered_ids = sorted(ids, key=lambda widget_id: _geometry_center(geometry_by_id[widget_id], axis=axis))
    start = _geometry_center(geometry_by_id[ordered_ids[0]], axis=axis)
    end = _geometry_center(geometry_by_id[ordered_ids[-1]], axis=axis)
    step = (end - start) / max(1, len(ordered_ids) - 1)
    diagnostics: list[dict[str, Any]] = []
    layout_type = str(page.layout.get("type") or "absolute")
    if layout_type != "absolute":
        diagnostics.append(
            {
                "severity": "warning",
                "code": "NON_ABSOLUTE_LAYOUT",
                "message": f"Page {page_id!r} uses layout {layout_type!r}; explicit geometry may be re-resolved by layout.",
            }
        )
    updates: list[dict[str, Any]] = []
    for index, widget_id in enumerate(ordered_ids):
        old = geometry_by_id[widget_id]
        requested = dict(old)
        if index == 0 or index == len(ordered_ids) - 1:
            new_geometry = dict(old)
            item_diagnostics = []
        else:
            requested = _distributed_geometry(old, axis=axis, target_center=int(round(start + step * index)))
            new_geometry, item_diagnostics = _normalize_geometry(
                requested,
                canvas=canvas,
                snap=snap,
                clamp=clamp,
                preserve_size=True,
            )
        diagnostics.extend({"widget": widget_id, **item} for item in item_diagnostics)
        updates.append(
            {
                "widget": widget_id,
                "from": dict(old),
                "requested": dict(requested),
                "to": dict(new_geometry),
            }
        )
    changed = [item for item in updates if item["from"] != item["to"]]
    if not changed:
        raise SceneError("design distribute did not change any widget geometry")

    _write_widget_geometries(scene_path, page_id=page_id, updates=updates)
    op = {
        "op": "distribute_widgets",
        "source": source,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "page": page_id,
        "widgets": ordered_ids,
        "axis": axis,
        "start_center": start,
        "end_center": end,
        "step": step,
        "snap": int(snap),
        "clamp": bool(clamp),
        "items": updates,
        "diagnostics": diagnostics,
    }
    outputs = _write_design_artifacts(scene_path, out_dir, op)
    return {
        "scene_path": str(Path(scene_path).resolve()),
        "page": page_id,
        "widgets": [{"id": item["widget"], **item["to"]} for item in updates],
        "op": op,
        "outputs": outputs,
        "not_claimed": list(DESIGN_NOT_CLAIMED),
    }


def design_match_size_widgets(
    scene_path: str | Path,
    out_dir: str | Path | None,
    *,
    page_id: str,
    widget_ids: list[str] | tuple[str, ...],
    mode: str,
    anchor: str = "first",
    min_size: int = 1,
    snap: int = 1,
    clamp: bool = True,
    source: str = "design-op",
) -> dict[str, Any]:
    """Match width and/or height across multiple widgets on one page."""
    if mode not in MATCH_SIZE_MODES:
        raise SceneError(f"Unsupported match-size mode: {mode}")
    if anchor not in MATCH_SIZE_ANCHORS:
        raise SceneError(f"Unsupported match-size anchor: {anchor}")
    ids = [str(item) for item in widget_ids if str(item)]
    if len(ids) < 2:
        raise SceneError("design match-size requires at least two widgets")
    if len(set(ids)) != len(ids):
        raise SceneError("design match-size requires unique widgets")

    scene = load_scene(scene_path)
    page = _find_page(scene, page_id)
    canvas = {"width": int(scene.canvas["width"]), "height": int(scene.canvas["height"])}
    geometry_by_id = _page_geometry_by_id(scene, page)
    missing = [widget_id for widget_id in ids if widget_id not in geometry_by_id]
    if missing:
        raise SceneError(f"Widget(s) not found on page '{page_id}': {', '.join(missing)}")

    anchor_id = ids[0] if anchor == "first" else ids[-1]
    anchor_geometry = geometry_by_id[anchor_id]
    target_size = {"w": int(anchor_geometry["w"]), "h": int(anchor_geometry["h"])}
    diagnostics: list[dict[str, Any]] = []
    layout_type = str(page.layout.get("type") or "absolute")
    if layout_type != "absolute":
        diagnostics.append(
            {
                "severity": "warning",
                "code": "NON_ABSOLUTE_LAYOUT",
                "message": f"Page {page_id!r} uses layout {layout_type!r}; explicit geometry may be re-resolved by layout.",
            }
        )
    updates: list[dict[str, Any]] = []
    for widget_id in ids:
        old = geometry_by_id[widget_id]
        requested = dict(old)
        if mode in {"width", "both"}:
            requested["w"] = target_size["w"]
        if mode in {"height", "both"}:
            requested["h"] = target_size["h"]
        new_geometry, item_diagnostics = _normalize_geometry(
            requested,
            canvas=canvas,
            snap=snap,
            clamp=clamp,
            preserve_size=False,
            min_size=min_size,
        )
        diagnostics.extend({"widget": widget_id, **item} for item in item_diagnostics)
        updates.append(
            {
                "widget": widget_id,
                "from": dict(old),
                "requested": dict(requested),
                "to": dict(new_geometry),
            }
        )
    changed = [item for item in updates if item["from"] != item["to"]]
    if not changed:
        raise SceneError("design match-size did not change any widget geometry")

    _write_widget_geometries(scene_path, page_id=page_id, updates=updates)
    op = {
        "op": "match_size_widgets",
        "source": source,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "page": page_id,
        "widgets": ids,
        "mode": mode,
        "anchor": anchor,
        "target_size": target_size,
        "snap": int(snap),
        "clamp": bool(clamp),
        "items": updates,
        "diagnostics": diagnostics,
    }
    outputs = _write_design_artifacts(scene_path, out_dir, op)
    return {
        "scene_path": str(Path(scene_path).resolve()),
        "page": page_id,
        "widgets": [{"id": item["widget"], **item["to"]} for item in updates],
        "op": op,
        "outputs": outputs,
        "not_claimed": list(DESIGN_NOT_CLAIMED),
    }


def replay_agent_patch(
    scene_path: str | Path,
    patch_path: str | Path,
    out_dir: str | Path | None = None,
    *,
    source: str = "agent-patch-replay",
) -> dict[str, Any]:
    """Replay move, resize, or alignment operations from an agent_patch.json file."""
    patch = json.loads(Path(patch_path).read_text(encoding="utf-8"))
    ops = patch.get("ops")
    if not isinstance(ops, list):
        raise SceneError("agent patch requires an ops list")

    applied: list[dict[str, Any]] = []
    last_result: dict[str, Any] | None = None
    for op in ops:
        if not isinstance(op, Mapping):
            raise SceneError("each agent patch op must be an object")
        op_name = op.get("op")
        if op_name in {"move_widget", "resize_widget"}:
            target = op.get("to")
            if not isinstance(target, Mapping):
                raise SceneError("each agent patch op requires a to geometry")
            page_id = str(op.get("page") or "")
            widget_id = str(op.get("widget") or "")
            if not page_id or not widget_id:
                raise SceneError("each agent patch op requires page and widget")
        if op_name == "move_widget":
            last_result = design_move_widget(
                scene_path,
                out_dir,
                page_id=page_id,
                widget_id=widget_id,
                x=int(target["x"]),
                y=int(target["y"]),
                source=source,
            )
        elif op_name == "resize_widget":
            last_result = design_resize_widget(
                scene_path,
                out_dir,
                page_id=page_id,
                widget_id=widget_id,
                w=int(target["w"]),
                h=int(target["h"]),
                source=source,
            )
        elif op_name in {"align_widgets", "distribute_widgets", "match_size_widgets"}:
            page_id = str(op.get("page") or "")
            if not page_id:
                raise SceneError(f"{op_name} patch op requires page")
            raw_items = op.get("items")
            if not isinstance(raw_items, list):
                raise SceneError(f"{op_name} patch op requires an items list")
            items: list[dict[str, Any]] = []
            for item in raw_items:
                if not isinstance(item, Mapping) or not isinstance(item.get("to"), Mapping):
                    raise SceneError(f"{op_name} item requires a to geometry")
                widget_id = str(item.get("widget") or "")
                if not widget_id:
                    raise SceneError(f"{op_name} item requires widget")
                target = item["to"]
                items.append(
                    {
                        **dict(item),
                        "widget": widget_id,
                        "to": {key: int(target[key]) for key in ("x", "y", "w", "h")},
                    }
                )
            replayed_op = {
                **op,
                "source": source,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "items": items,
            }
            _write_widget_geometries(scene_path, page_id=page_id, updates=items)
            last_result = {"op": replayed_op, "outputs": _write_design_artifacts(scene_path, out_dir, replayed_op)}
        else:
            raise SceneError(f"Unsupported agent patch op: {op_name!r}")
        applied.append(last_result["op"])

    return {
        "scene_path": str(Path(scene_path).resolve()),
        "patch_path": str(Path(patch_path).resolve()),
        "applied_count": len(applied),
        "ops": applied,
        "outputs": last_result.get("outputs", {}) if last_result else {},
    }


def _design_result(
    scene_path: str | Path,
    out_dir: str | Path | None,
    *,
    result: dict[str, Any],
    op: dict[str, Any],
) -> dict[str, Any]:
    outputs = _write_design_artifacts(scene_path, out_dir, op)
    return {
        "scene_path": str(Path(scene_path).resolve()),
        "page": result["page"],
        "widget": result["widget"],
        "op": op,
        "outputs": outputs,
        "not_claimed": list(DESIGN_NOT_CLAIMED),
    }


def _widget_context(scene_path: str | Path, page_id: str, widget_id: str) -> dict[str, Any]:
    scene = load_scene(scene_path)
    page = _find_page(scene, page_id)
    widget = _find_widget(page, widget_id)
    resolved = _resolved_widget(scene, page, widget_id)
    bbox = _bbox(resolved or widget)
    diagnostics = []
    layout_type = str(page.layout.get("type") or "absolute")
    if layout_type != "absolute":
        diagnostics.append(
            {
                "severity": "warning",
                "code": "NON_ABSOLUTE_LAYOUT",
                "message": f"Page {page_id!r} uses layout {layout_type!r}; explicit geometry may be re-resolved by layout.",
            }
        )
    return {
        "scene": scene,
        "page": page,
        "widget": widget,
        "canvas": {
            "width": int(scene.canvas["width"]),
            "height": int(scene.canvas["height"]),
        },
        "geometry": {"x": bbox[0], "y": bbox[1], "w": bbox[2], "h": bbox[3]},
        "diagnostics": diagnostics,
    }


def _find_page(scene: SceneModel, page_id: str) -> PageSpec:
    for page in scene.pages:
        if page.id == page_id:
            return page
    raise SceneError(f"Page '{page_id}' not found in scene")


def _find_widget(page: PageSpec, widget_id: str) -> WidgetSpec:
    for widget in page.widgets:
        if widget.id == widget_id:
            return widget
    raise SceneError(f"Widget '{widget_id}' not found on page '{page.id}'")


def _resolved_widget(scene: SceneModel, page: PageSpec, widget_id: str) -> WidgetSpec | None:
    widgets = resolve_page_layout(
        page.widgets,
        page.layout,
        int(scene.canvas["width"]),
        int(scene.canvas["height"]),
    )
    return next((widget for widget in widgets if widget.id == widget_id), None)


def _page_geometry_by_id(scene: SceneModel, page: PageSpec) -> dict[str, dict[str, int]]:
    resolved_widgets = resolve_page_layout(
        page.widgets,
        page.layout,
        int(scene.canvas["width"]),
        int(scene.canvas["height"]),
    )
    resolved_by_id = {widget.id: widget for widget in resolved_widgets}
    return {
        widget.id: {
            "x": int((resolved_by_id.get(widget.id) or widget).x or 0),
            "y": int((resolved_by_id.get(widget.id) or widget).y or 0),
            "w": int((resolved_by_id.get(widget.id) or widget).w or 1),
            "h": int((resolved_by_id.get(widget.id) or widget).h or 1),
        }
        for widget in page.widgets
    }


def _align_target(
    edge: str,
    anchor: str,
    widget_ids: list[str],
    geometry_by_id: Mapping[str, Mapping[str, int]],
    canvas: Mapping[str, int],
) -> int:
    if anchor == "canvas":
        if edge == "left":
            return 0
        if edge == "right":
            return int(canvas["width"])
        if edge == "top":
            return 0
        if edge == "bottom":
            return int(canvas["height"])
        if edge == "hcenter":
            return int(canvas["width"]) // 2
        return int(canvas["height"]) // 2
    anchor_id = widget_ids[0] if anchor == "first" else widget_ids[-1]
    geometry = geometry_by_id[anchor_id]
    if edge == "left":
        return int(geometry["x"])
    if edge == "right":
        return int(geometry["x"]) + int(geometry["w"])
    if edge == "top":
        return int(geometry["y"])
    if edge == "bottom":
        return int(geometry["y"]) + int(geometry["h"])
    if edge == "hcenter":
        return int(geometry["x"]) + int(geometry["w"]) // 2
    return int(geometry["y"]) + int(geometry["h"]) // 2


def _aligned_geometry(geometry: Mapping[str, int], *, edge: str, target: int) -> dict[str, int]:
    requested = {key: int(geometry[key]) for key in ("x", "y", "w", "h")}
    if edge == "left":
        requested["x"] = int(target)
    elif edge == "right":
        requested["x"] = int(target) - requested["w"]
    elif edge == "hcenter":
        requested["x"] = int(target) - requested["w"] // 2
    elif edge == "top":
        requested["y"] = int(target)
    elif edge == "bottom":
        requested["y"] = int(target) - requested["h"]
    elif edge == "vcenter":
        requested["y"] = int(target) - requested["h"] // 2
    return requested


def _geometry_center(geometry: Mapping[str, int], *, axis: str) -> int:
    if axis == "horizontal":
        return int(geometry["x"]) + int(geometry["w"]) // 2
    return int(geometry["y"]) + int(geometry["h"]) // 2


def _distributed_geometry(geometry: Mapping[str, int], *, axis: str, target_center: int) -> dict[str, int]:
    requested = {key: int(geometry[key]) for key in ("x", "y", "w", "h")}
    if axis == "horizontal":
        requested["x"] = int(target_center) - requested["w"] // 2
    else:
        requested["y"] = int(target_center) - requested["h"] // 2
    return requested


def _write_widget_geometries(
    scene_path: str | Path,
    *,
    page_id: str,
    updates: list[dict[str, Any]],
) -> None:
    payload = read_scene_document(scene_path)
    pages = payload.get("pages")
    if not isinstance(pages, list):
        raise SceneError("scene pages must be a list")
    page = next((item for item in pages if isinstance(item, dict) and item.get("id") == page_id), None)
    if page is None:
        raise SceneError(f"Page '{page_id}' not found in scene")
    widgets = page.get("widgets")
    if not isinstance(widgets, list):
        raise SceneError(f"page '{page_id}' widgets must be a list")
    by_id = {str(item.get("id")): item for item in widgets if isinstance(item, dict)}
    for update in updates:
        widget = by_id.get(str(update["widget"]))
        if widget is None:
            raise SceneError(f"Widget '{update['widget']}' not found on page '{page_id}'")
        target = update["to"]
        for key in ("x", "y", "w", "h"):
            widget[key] = int(target[key])
    scene = validate_scene(deepcopy(payload))
    write_scene_document(scene_path, scene.to_dict())


def _bbox(widget: WidgetSpec) -> list[int]:
    return [
        int(widget.x or 0),
        int(widget.y or 0),
        int(widget.w or 1),
        int(widget.h or 1),
    ]


def _normalize_geometry(
    geometry: Mapping[str, int],
    *,
    canvas: Mapping[str, int],
    snap: int,
    clamp: bool,
    preserve_size: bool,
    min_size: int = 1,
) -> tuple[dict[str, int], list[dict[str, Any]]]:
    requested = {key: int(geometry[key]) for key in ("x", "y", "w", "h")}
    normalized = dict(requested)
    diagnostics: list[dict[str, Any]] = []
    grid = max(1, int(snap))
    if grid > 1:
        for key in ("x", "y", "w", "h"):
            if preserve_size and key in {"w", "h"}:
                continue
            normalized[key] = _snap_int(normalized[key], grid)
        if normalized != requested:
            diagnostics.append({"severity": "info", "code": "SNAPPED_TO_GRID", "grid": grid})

    normalized["w"] = max(int(min_size), normalized["w"])
    normalized["h"] = max(int(min_size), normalized["h"])
    if clamp:
        before = dict(normalized)
        width = int(canvas["width"])
        height = int(canvas["height"])
        if not preserve_size:
            normalized["w"] = min(normalized["w"], max(int(min_size), width - max(0, normalized["x"])))
            normalized["h"] = min(normalized["h"], max(int(min_size), height - max(0, normalized["y"])))
        max_x = max(0, width - max(1, normalized["w"]))
        max_y = max(0, height - max(1, normalized["h"]))
        normalized["x"] = min(max(0, normalized["x"]), max_x)
        normalized["y"] = min(max(0, normalized["y"]), max_y)
        if normalized != before:
            diagnostics.append({"severity": "warning", "code": "CLAMPED_TO_CANVAS", "canvas": dict(canvas)})
    return normalized, diagnostics


def _snap_int(value: int, grid: int) -> int:
    return int(round(int(value) / grid) * grid)


def _design_op(
    op_name: str,
    *,
    source: str,
    page_id: str,
    widget_id: str,
    old: Mapping[str, int],
    requested: Mapping[str, int],
    new_geometry: Mapping[str, int],
    diagnostics: list[dict[str, Any]],
    snap: int,
    clamp: bool,
) -> dict[str, Any]:
    return {
        "op": op_name,
        "source": source,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "page": page_id,
        "widget": widget_id,
        "from": dict(old),
        "requested": dict(requested),
        "to": dict(new_geometry),
        "snap": int(snap),
        "clamp": bool(clamp),
        "diagnostics": diagnostics,
    }


def _write_design_artifacts(
    scene_path: str | Path,
    out_dir: str | Path | None,
    op: dict[str, Any],
) -> dict[str, str]:
    scene = Path(scene_path).resolve()
    output_dir = Path(out_dir).resolve() if out_dir is not None else scene.parent / "design_session"
    output_dir.mkdir(parents=True, exist_ok=True)
    session_path = output_dir / "design_session.json"
    patch_path = output_dir / "agent_patch.json"
    modified_path = output_dir / "scene.modified.json"

    previous_ops: list[dict[str, Any]] = []
    if session_path.exists():
        try:
            previous = json.loads(session_path.read_text(encoding="utf-8"))
            if isinstance(previous.get("ops"), list):
                previous_ops = previous["ops"]
        except (OSError, json.JSONDecodeError):
            previous_ops = []
    ops = [*previous_ops, op]
    diagnostics = [item for operation in ops for item in operation.get("diagnostics", [])]
    payload = {
        "schema_version": DESIGN_PATCH_SCHEMA_VERSION,
        "scene_path": str(scene),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "op_count": len(ops),
        "ops": ops,
        "diagnostics": diagnostics,
        "not_claimed": list(DESIGN_NOT_CLAIMED),
    }
    session_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    patch_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    modified = read_scene_document(scene)
    clean = deepcopy(modified)
    if isinstance(clean.get("project"), dict):
        clean["project"] = {key: value for key, value in clean["project"].items() if not str(key).startswith("_")}
    write_scene_document(modified_path, clean)
    return {
        "design_session_json": str(session_path),
        "agent_patch_json": str(patch_path),
        "scene_modified_json": str(modified_path),
    }
