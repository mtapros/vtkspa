"""PSD → native template conversion."""
from __future__ import annotations

import io
import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any

from vtkspa.models import CanvasConfig, ImageLayer, PhotoSlot, Template, TextSlot
from vtkspa.template.schema import save_template

logger = logging.getLogger(__name__)


def _slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", s.lower().strip())


def _parse_layer_name(name: str) -> dict[str, Any]:
    """Parse @-prefixed layer naming convention."""
    name = name.strip()
    if name.startswith("@photo"):
        parts = name.split(":", 1)
        slot_id = parts[1].strip() if len(parts) > 1 else "photo"
        return {"kind": "photo_slot", "id": slot_id}
    if name.startswith("@text:"):
        field = name[6:].strip()
        return {"kind": "text_slot", "id": field, "data_field": field}
    return {"kind": "image"}


def _export_layer_pixels(layer: Any) -> bytes | None:
    """Export a psd-tools layer to PNG bytes."""
    try:
        img = layer.composite()
        if img is None:
            return None
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to composite layer %r: %s", getattr(layer, "name", ""), exc)
        return None


def _get_layer_bbox(layer: Any) -> tuple[int, int, int, int]:
    """Return (x, y, w, h) for a layer."""
    # psd-tools 1.9+ returns bbox as a plain (left, top, right, bottom) tuple.
    left, top, right, bottom = layer.bbox
    return left, top, right - left, bottom - top


def import_psd(psd_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    """Convert a PSD file to a vtkspa native template."""
    try:
        from psd_tools import PSDImage
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise ImportError("psd-tools is required for PSD import: pip install psd-tools") from exc

    from PIL import Image

    psd_path = Path(psd_path)
    output_dir = Path(output_dir)
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    psd = PSDImage.open(str(psd_path))
    report: dict[str, Any] = {
        "source": str(psd_path),
        "output": str(output_dir),
        "canvas": {"width": psd.width, "height": psd.height},
        "layers_imported": [],
        "layers_flattened": [],
        "warnings": [],
    }

    canvas = CanvasConfig(
        width=psd.width,
        height=psd.height,
        dpi=int(getattr(psd.header, "y_density", 300) or 300),
        background_color=(255, 255, 255, 255),
    )

    vtk_layers: list[ImageLayer | PhotoSlot | TextSlot] = []
    static_group: list[dict[str, Any]] = []

    def flush_static(group: list[dict[str, Any]]) -> None:
        if not group:
            return
        min_x = min(item["x"] for item in group)
        min_y = min(item["y"] for item in group)
        max_x = max(item["x"] + item["w"] for item in group)
        max_y = max(item["y"] + item["h"] for item in group)
        canvas_w = max_x - min_x
        canvas_h = max_y - min_y
        if canvas_w <= 0 or canvas_h <= 0:
            group.clear()
            return
        composite = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        for item in group:
            if item.get("pixels"):
                img = Image.open(io.BytesIO(item["pixels"])).convert("RGBA")
                composite.paste(img, (item["x"] - min_x, item["y"] - min_y), img)
        asset_name = f"static_{uuid.uuid4().hex[:8]}.png"
        composite.save(assets_dir / asset_name)
        layer_id = f"static_{uuid.uuid4().hex[:8]}"
        vtk_layers.append(
            ImageLayer(
                layer_type="image",
                id=layer_id,
                name="flattened_static",
                asset_path=asset_name,
                x=min_x,
                y=min_y,
                w=canvas_w,
                h=canvas_h,
            )
        )
        report["layers_flattened"].append({"count": len(group), "asset": asset_name})
        group.clear()

    def process_layers(layers: Any, depth: int = 0) -> None:
        del depth
        for layer in reversed(list(layers)):
            if not layer.is_visible():
                continue
            name = layer.name or ""
            parsed = _parse_layer_name(name)
            x, y, w, h = _get_layer_bbox(layer)
            if w <= 0 or h <= 0:
                continue

            if parsed["kind"] == "photo_slot":
                flush_static(static_group)
                mask_asset = ""
                try:
                    if getattr(layer, "mask", None) is not None:
                        pixels = _export_layer_pixels(layer)
                        if pixels:
                            img = Image.open(io.BytesIO(pixels)).convert("RGBA")
                            alpha = img.split()[3]
                            mask_asset_name = f"mask_{parsed['id']}.png"
                            alpha.save(assets_dir / mask_asset_name)
                            mask_asset = mask_asset_name
                except Exception as exc:  # pragma: no cover - best effort
                    report["warnings"].append(f"Could not extract mask from @photo layer: {exc}")

                vtk_layers.append(
                    PhotoSlot(
                        layer_type="photo_slot",
                        id=parsed["id"],
                        name=name,
                        x=x,
                        y=y,
                        w=w,
                        h=h,
                        fit_mode="cover",
                        mask_asset_path=mask_asset,
                    )
                )
                report["layers_imported"].append({"name": name, "type": "photo_slot", "id": parsed["id"]})
            elif parsed["kind"] == "text_slot":
                flush_static(static_group)
                font_size = 48
                fill_color = (0, 0, 0, 255)
                sample_text = ""
                try:
                    if getattr(layer, "engine_dict", None):
                        style_run = layer.engine_dict.get("StyleRun", {})
                        runs = style_run.get("RunArray", [])
                        if runs:
                            style = runs[0].get("RunData", {}).get("StyleSheet", {}).get("StyleSheetData", {})
                            font_size = int(style.get("FontSize", 48))
                            color_arr = style.get("FillColor", {}).get("Values", [])
                            if len(color_arr) >= 4:
                                fill_color = (
                                    int(color_arr[1] * 255),
                                    int(color_arr[2] * 255),
                                    int(color_arr[3] * 255),
                                    255,
                                )
                    if getattr(layer, "text", None):
                        sample_text = str(layer.text)
                except Exception as exc:  # pragma: no cover - best effort
                    report["warnings"].append(f"Could not extract text properties for {name!r}: {exc}")

                vtk_layers.append(
                    TextSlot(
                        layer_type="text_slot",
                        id=parsed["id"],
                        name=name,
                        x=x,
                        y=y,
                        w=w,
                        h=h,
                        base_font_size=font_size,
                        min_font_size=max(8, font_size // 4),
                        fill_color=fill_color,
                        data_field=parsed["data_field"],
                        sample_text=sample_text,
                    )
                )
                report["layers_imported"].append(
                    {
                        "name": name,
                        "type": "text_slot",
                        "id": parsed["id"],
                        "data_field": parsed["data_field"],
                    }
                )
            else:
                if hasattr(layer, "__iter__") and not hasattr(layer, "engine_dict"):
                    process_layers(layer, depth + 1)
                else:
                    pixels = _export_layer_pixels(layer)
                    if pixels:
                        static_group.append({"x": x, "y": y, "w": w, "h": h, "pixels": pixels, "name": name})
                    else:
                        report["warnings"].append(f"Could not rasterize layer {name!r}")

                    kind_str = type(layer).__name__.lower()
                    if "adjustment" in kind_str:
                        report["warnings"].append(f"Adjustment layer {name!r} rasterized (effects may not match)")
                    if getattr(layer, "smart_object_id", None):
                        report["warnings"].append(f"Smart object {name!r} rasterized")

    process_layers(psd)
    flush_static(static_group)

    template = Template(schema_version="vtkspa_v1", name=psd_path.stem, canvas=canvas, layers=vtk_layers)
    save_template(template, output_dir)

    log_lines = ["VTK SPA PSD Import Report", f"Source: {psd_path}", "", f"Canvas: {psd.width}x{psd.height}"]
    log_lines.append(f"Layers imported: {len(report['layers_imported'])}")
    log_lines.append(f"Static groups flattened: {len(report['layers_flattened'])}")
    log_lines.append("")
    if report["warnings"]:
        log_lines.append("Warnings:")
        for warning in report["warnings"]:
            log_lines.append(f"  ⚠ {warning}")

    with open(output_dir / "import_report.txt", "w", encoding="utf-8") as handle:
        handle.write("\n".join(log_lines))
    with open(output_dir / "import_report.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    return report
