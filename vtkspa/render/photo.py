"""Photo slot placement: fit modes, anchor, corner radius, mask."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from vtkspa.models import PhotoSlot


def apply_corner_radius(img: Image.Image, radius: int) -> Image.Image:
    """Apply rounded corners to image (returns RGBA)."""
    if radius <= 0:
        return img
    img = img.convert("RGBA")
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), (img.width - 1, img.height - 1)], radius=radius, fill=255)
    result = img.copy()
    result.putalpha(mask)
    return result


def apply_mask(img: Image.Image, mask_path: str | Path) -> Image.Image:
    """Apply an external alpha mask asset to the image."""
    mask = Image.open(mask_path).convert("L")
    mask = mask.resize(img.size, Image.LANCZOS)
    result = img.convert("RGBA")
    result.putalpha(mask)
    return result


def fit_photo(photo: Image.Image, slot: PhotoSlot, mask_full_path: str | Path | None = None) -> Image.Image:
    """Fit a photo into the slot rect using the slot's fit_mode and anchors."""
    slot_w, slot_h = slot.w, slot.h
    if slot_w <= 0 or slot_h <= 0:
        return Image.new("RGBA", (max(slot_w, 1), max(slot_h, 1)), (0, 0, 0, 0))

    photo = photo.convert("RGBA")
    photo_w, photo_h = photo.size
    fit_mode = slot.fit_mode

    if fit_mode == "stretch":
        resized = photo.resize((slot_w, slot_h), Image.LANCZOS)
        paste_x, paste_y = 0, 0
    elif fit_mode == "cover":
        scale = max(slot_w / photo_w, slot_h / photo_h)
        new_w = max(1, int(photo_w * scale))
        new_h = max(1, int(photo_h * scale))
        resized = photo.resize((new_w, new_h), Image.LANCZOS)
        if slot.anchor_h == "left":
            crop_x = 0
        elif slot.anchor_h == "right":
            crop_x = new_w - slot_w
        else:
            crop_x = (new_w - slot_w) // 2
        if slot.anchor_v == "top":
            crop_y = 0
        elif slot.anchor_v == "bottom":
            crop_y = new_h - slot_h
        else:
            crop_y = (new_h - slot_h) // 2
        resized = resized.crop((crop_x, crop_y, crop_x + slot_w, crop_y + slot_h))
        paste_x, paste_y = 0, 0
    else:
        scale = min(slot_w / photo_w, slot_h / photo_h)
        new_w = max(1, int(photo_w * scale))
        new_h = max(1, int(photo_h * scale))
        resized = photo.resize((new_w, new_h), Image.LANCZOS)
        if slot.anchor_h == "left":
            paste_x = 0
        elif slot.anchor_h == "right":
            paste_x = slot_w - new_w
        else:
            paste_x = (slot_w - new_w) // 2
        if slot.anchor_v == "top":
            paste_y = 0
        elif slot.anchor_v == "bottom":
            paste_y = slot_h - new_h
        else:
            paste_y = (slot_h - new_h) // 2

    canvas = Image.new("RGBA", (slot_w, slot_h), (0, 0, 0, 0))
    if fit_mode == "cover":
        canvas.paste(resized, (0, 0), resized)
    else:
        canvas.paste(resized, (paste_x, paste_y), resized)

    if mask_full_path and Path(mask_full_path).exists():
        canvas = apply_mask(canvas, mask_full_path)
    if slot.corner_radius > 0:
        canvas = apply_corner_radius(canvas, slot.corner_radius)
    return canvas
