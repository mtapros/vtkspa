"""Compositing engine: render a template + data context → final image."""
from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw

from vtkspa.models import ImageLayer, PhotoSlot, RenderJob, Template, TextSlot
from vtkspa.render.photo import fit_photo
from vtkspa.render.text import render_text_slot

logger = logging.getLogger(__name__)


class RenderEngine:
    """Pillow-based compositing engine."""

    def render(
        self,
        template: Template,
        template_dir: str | Path,
        data_context: dict[str, str],
        photo_path: str | Path | None = None,
        jpeg_quality: int = 95,
    ) -> Image.Image:
        del jpeg_quality
        template_dir = Path(template_dir)
        assets_dir = template_dir / "assets"

        canvas_w, canvas_h = template.canvas.width, template.canvas.height
        canvas = Image.new("RGBA", (canvas_w, canvas_h), tuple(template.canvas.background_color))

        subject_photo: Image.Image | None = None
        if photo_path and Path(photo_path).exists():
            try:
                subject_photo = Image.open(photo_path).convert("RGBA")
            except Exception as exc:
                logger.warning("Could not load photo %r: %s", photo_path, exc)

        for layer in template.layers:
            if not layer.visible:
                continue
            try:
                if isinstance(layer, ImageLayer):
                    self._composite_image_layer(canvas, layer, assets_dir)
                elif isinstance(layer, PhotoSlot):
                    self._composite_photo_slot(canvas, layer, subject_photo, assets_dir)
                elif isinstance(layer, TextSlot):
                    self._composite_text_slot(canvas, layer, data_context)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("Error rendering layer %r (%s): %s", layer.id, type(layer).__name__, exc)

        return canvas

    def _composite_image_layer(self, canvas: Image.Image, layer: ImageLayer, assets_dir: Path) -> None:
        asset_path = assets_dir / layer.asset_path
        if not asset_path.exists():
            logger.warning("Asset not found: %s", asset_path)
            return

        img = Image.open(asset_path).convert("RGBA")
        if layer.w > 0 and layer.h > 0:
            img = img.resize((layer.w, layer.h), Image.LANCZOS)
        if layer.rotation != 0.0:
            img = img.rotate(-layer.rotation, expand=True, resample=Image.BICUBIC)
        if layer.opacity < 1.0:
            red, green, blue, alpha = img.split()
            alpha = alpha.point(lambda value: int(value * layer.opacity))
            img = Image.merge("RGBA", (red, green, blue, alpha))
        canvas.alpha_composite(img, dest=(layer.x, layer.y))

    def _composite_photo_slot(self, canvas: Image.Image, slot: PhotoSlot, photo: Image.Image | None, assets_dir: Path) -> None:
        if photo is None:
            return

        mask_path: Path | None = None
        if slot.mask_asset_path:
            candidate = assets_dir / slot.mask_asset_path
            if candidate.exists():
                mask_path = candidate

        fitted = fit_photo(photo, slot, mask_full_path=mask_path)
        canvas.alpha_composite(fitted, dest=(slot.x, slot.y))

    def _composite_text_slot(self, canvas: Image.Image, slot: TextSlot, data_context: dict[str, str]) -> None:
        text = data_context.get(slot.data_field, slot.sample_text or "")
        if not text:
            return
        draw = ImageDraw.Draw(canvas)
        render_text_slot(draw, slot, text)

    def save(self, image: Image.Image, output_path: str | Path, jpeg_quality: int = 95, dpi: int = 300) -> None:
        """Save image to file (PNG or JPEG based on extension)."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        ext = output_path.suffix.lower()
        if ext in (".jpg", ".jpeg"):
            image.convert("RGB").save(str(output_path), "JPEG", quality=jpeg_quality, dpi=(dpi, dpi))
        else:
            image.save(str(output_path), "PNG", dpi=(dpi, dpi))


_default_engine = RenderEngine()


def render_job(job: RenderJob) -> Image.Image:
    """Render a RenderJob using the default engine."""
    return _default_engine.render(
        template=job.template,
        template_dir=job.template_dir,
        data_context=job.roster_row.data,
        photo_path=job.roster_row.photo_path,
        jpeg_quality=job.jpeg_quality,
    )
