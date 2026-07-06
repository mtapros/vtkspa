"""Text rendering: font loading, auto-shrink-to-fit, alignment, stroke."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from PIL import ImageDraw, ImageFont

from vtkspa.models import TextSlot

logger = logging.getLogger(__name__)

_FONT_CACHE: dict[tuple[str, str, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}

FALLBACK_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Windows/Fonts/arial.ttf",
]


def find_font(font_path: str = "", font_family: str = "DejaVuSans", size: int = 12) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a font, with fallback to PIL default."""
    cache_key = (font_path, font_family, size)
    if cache_key in _FONT_CACHE:
        return _FONT_CACHE[cache_key]

    font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None
    if font_path and Path(font_path).exists():
        try:
            font = ImageFont.truetype(font_path, size)
        except Exception as exc:  # pragma: no cover - warning path
            logger.warning("Could not load font at %r: %s", font_path, exc)

    if font is None:
        try:
            import matplotlib.font_manager as fm

            match = fm.findfont(fm.FontProperties(family=font_family), fallback_to_default=False)
            if match and os.path.exists(match):
                font = ImageFont.truetype(match, size)
        except Exception:
            pass

    if font is None:
        for path in FALLBACK_FONT_PATHS:
            if os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, size)
                    break
                except Exception:
                    pass

    if font is None:
        logger.warning("Could not find font %r, using PIL default", font_family)
        font = ImageFont.load_default()

    _FONT_CACHE[cache_key] = font
    return font


def measure_text(text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> tuple[int, int]:
    """Return (width, height) of text with the given font."""
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def wrap_text(text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: int, max_lines: int) -> list[str]:
    """Simple word wrap. Returns list of lines (up to max_lines)."""
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    truncated = False
    for word in words[1:]:
        candidate = current + " " + word
        width, _ = measure_text(candidate, font)
        if width <= max_width:
            current = candidate
        else:
            lines.append(current)
            if len(lines) >= max_lines:
                truncated = True
                break
            current = word
    if len(lines) < max_lines and not truncated:
        lines.append(current)
    elif lines:
        last = lines[-1]
        while last and measure_text(last + "…", font)[0] > max_width:
            last = last[:-1]
        lines[-1] = last + "…"
    return lines or [""]


def render_text_slot(draw: ImageDraw.ImageDraw, slot: TextSlot, text: str, offset_x: int = 0, offset_y: int = 0) -> None:
    """Render text into a slot on the given ImageDraw."""
    if not text:
        return
    if slot.all_caps:
        text = text.upper()

    max_lines = max(1, slot.max_lines)
    slot_w, slot_h = slot.w, slot.h
    font_size = slot.base_font_size
    min_size = slot.min_font_size
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None
    lines = [text]

    while font_size >= min_size:
        font = find_font(slot.font_path, slot.font_family, font_size)
        lines = wrap_text(text, font, slot_w, max_lines)
        line_heights = [measure_text(line, font)[1] for line in lines]
        total_h = sum(line_heights) + (len(lines) - 1) * max(2, font_size // 8)
        max_line_w = max((measure_text(line, font)[0] for line in lines), default=0)
        if max_line_w <= slot_w and total_h <= slot_h:
            break
        font_size -= 1

    if font is None:
        font = find_font(slot.font_path, slot.font_family, min_size)
        lines = wrap_text(text, font, slot_w, max_lines)

    line_heights = [measure_text(line, font)[1] for line in lines]
    line_spacing = max(2, max(min_size, font_size) // 8)
    total_h = sum(line_heights) + (len(lines) - 1) * line_spacing

    if slot.valign == "top":
        y_start = slot.y + offset_y
    elif slot.valign == "bottom":
        y_start = slot.y + offset_y + slot_h - total_h
    else:
        y_start = slot.y + offset_y + (slot_h - total_h) // 2

    fill = tuple(slot.fill_color)
    stroke = tuple(slot.stroke_color) if slot.stroke_width > 0 else None
    stroke_width = slot.stroke_width if slot.stroke_width > 0 else 0

    y = y_start
    for index, line in enumerate(lines):
        line_w, line_h = measure_text(line, font)
        if slot.align == "left":
            x = slot.x + offset_x
        elif slot.align == "right":
            x = slot.x + offset_x + slot_w - line_w
        else:
            x = slot.x + offset_x + (slot_w - line_w) // 2

        kwargs = {"xy": (x, y), "text": line, "font": font, "fill": fill}
        if stroke_width > 0 and stroke is not None:
            kwargs["stroke_width"] = stroke_width
            kwargs["stroke_fill"] = stroke
        draw.text(**kwargs)
        y += line_h + (line_spacing if index < len(lines) - 1 else 0)
