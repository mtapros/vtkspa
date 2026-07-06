"""Native JSON template schema: load, save, validate."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vtkspa.models import CanvasConfig, ImageLayer, Layer, PhotoSlot, Template, TextSlot

SCHEMA_VERSION = "vtkspa_v1"


def _parse_color(val: Any, default: tuple[int, int, int, int] = (0, 0, 0, 255)) -> tuple[int, int, int, int]:
    if val is None:
        return default
    if isinstance(val, (list, tuple)) and len(val) == 4:
        return tuple(int(x) for x in val)
    if isinstance(val, (list, tuple)) and len(val) == 3:
        return (int(val[0]), int(val[1]), int(val[2]), 255)
    return default


def _layer_from_dict(d: dict[str, Any]) -> Layer:
    layer_type = d.get("layer_type")
    if layer_type == "image":
        return ImageLayer(
            layer_type="image",
            id=d.get("id", ""),
            name=d.get("name", ""),
            asset_path=d.get("asset_path", ""),
            x=int(d.get("x", 0)),
            y=int(d.get("y", 0)),
            w=int(d.get("w", 0)),
            h=int(d.get("h", 0)),
            opacity=float(d.get("opacity", 1.0)),
            rotation=float(d.get("rotation", 0.0)),
            visible=bool(d.get("visible", True)),
        )
    if layer_type == "photo_slot":
        return PhotoSlot(
            layer_type="photo_slot",
            id=d.get("id", ""),
            name=d.get("name", ""),
            x=int(d.get("x", 0)),
            y=int(d.get("y", 0)),
            w=int(d.get("w", 0)),
            h=int(d.get("h", 0)),
            fit_mode=d.get("fit_mode", "cover"),
            anchor_h=d.get("anchor_h", "center"),
            anchor_v=d.get("anchor_v", "center"),
            corner_radius=int(d.get("corner_radius", 0)),
            mask_asset_path=d.get("mask_asset_path", ""),
            visible=bool(d.get("visible", True)),
        )
    if layer_type == "text_slot":
        return TextSlot(
            layer_type="text_slot",
            id=d.get("id", ""),
            name=d.get("name", ""),
            x=int(d.get("x", 0)),
            y=int(d.get("y", 0)),
            w=int(d.get("w", 0)),
            h=int(d.get("h", 0)),
            font_family=d.get("font_family", "DejaVuSans"),
            font_path=d.get("font_path", ""),
            base_font_size=int(d.get("base_font_size", 48)),
            min_font_size=int(d.get("min_font_size", 12)),
            fill_color=_parse_color(d.get("fill_color"), (0, 0, 0, 255)),
            stroke_color=_parse_color(d.get("stroke_color"), (0, 0, 0, 0)),
            stroke_width=int(d.get("stroke_width", 0)),
            align=d.get("align", "center"),
            valign=d.get("valign", "center"),
            data_field=d.get("data_field", ""),
            all_caps=bool(d.get("all_caps", False)),
            max_lines=int(d.get("max_lines", 1)),
            sample_text=d.get("sample_text", ""),
            visible=bool(d.get("visible", True)),
        )
    raise ValueError(f"Unknown layer_type: {layer_type!r}")


def _layer_to_dict(layer: Layer) -> dict[str, Any]:
    import dataclasses

    data = dataclasses.asdict(layer)
    for key in ("fill_color", "stroke_color", "background_color"):
        if key in data and isinstance(data[key], (tuple, list)):
            data[key] = list(data[key])
    return data


def load_template(path: str | Path) -> Template:
    """Load a template from a directory containing template.json."""
    path = Path(path)
    json_path = path / "template.json" if path.is_dir() else path
    with open(json_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    canvas_d = data.get("canvas", {})
    canvas = CanvasConfig(
        width=int(canvas_d.get("width", 800)),
        height=int(canvas_d.get("height", 600)),
        dpi=int(canvas_d.get("dpi", 300)),
        background_color=_parse_color(canvas_d.get("background_color"), (255, 255, 255, 255)),
    )
    layers = [_layer_from_dict(layer_dict) for layer_dict in data.get("layers", [])]
    return Template(
        schema_version=data.get("schema_version", SCHEMA_VERSION),
        name=data.get("name", ""),
        canvas=canvas,
        layers=layers,
    )


def save_template(template: Template, path: str | Path) -> None:
    """Save a template to a directory."""
    import dataclasses

    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    canvas_d = dataclasses.asdict(template.canvas)
    canvas_d["background_color"] = list(canvas_d["background_color"])
    data = {
        "schema_version": template.schema_version,
        "name": template.name,
        "canvas": canvas_d,
        "layers": [_layer_to_dict(layer) for layer in template.layers],
    }
    with open(path / "template.json", "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def validate_template(template: Template, template_dir: str | Path | None = None) -> list[str]:
    """Validate a template. Returns list of error/warning strings."""
    errors: list[str] = []
    if template.schema_version != SCHEMA_VERSION:
        errors.append(f"Unknown schema_version: {template.schema_version!r}")
    if template.canvas.width <= 0 or template.canvas.height <= 0:
        errors.append("Canvas width and height must be positive")

    ids_seen: set[str] = set()
    for index, layer in enumerate(template.layers):
        layer_id = layer.id
        if layer_id in ids_seen:
            errors.append(f"Duplicate layer id {layer_id!r} at index {index}")
        if layer_id:
            ids_seen.add(layer_id)

        if isinstance(layer, ImageLayer):
            if not layer.asset_path:
                errors.append(f"Image layer {layer_id!r} has no asset_path")
            elif template_dir:
                asset = Path(template_dir) / "assets" / layer.asset_path
                if not asset.exists():
                    errors.append(f"Image layer {layer_id!r} asset not found: {asset}")
        elif isinstance(layer, TextSlot):
            if not layer.data_field:
                errors.append(f"TextSlot {layer_id!r} has no data_field")
            if layer.align not in ("left", "center", "right"):
                errors.append(f"TextSlot {layer_id!r} invalid align: {layer.align!r}")
        elif isinstance(layer, PhotoSlot):
            if layer.fit_mode not in ("cover", "contain", "stretch"):
                errors.append(f"PhotoSlot {layer_id!r} invalid fit_mode: {layer.fit_mode!r}")

    return errors
