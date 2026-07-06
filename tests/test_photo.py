"""Tests for photo slot placement: fit modes, anchor, corner radius."""
from PIL import Image

from vtkspa.models import PhotoSlot
from vtkspa.render.photo import apply_corner_radius, fit_photo


def make_photo_slot(**kwargs) -> PhotoSlot:
    defaults = dict(
        id="p1",
        name="photo",
        x=0,
        y=0,
        w=300,
        h=400,
        fit_mode="cover",
        anchor_h="center",
        anchor_v="center",
        corner_radius=0,
        mask_asset_path="",
    )
    defaults.update(kwargs)
    return PhotoSlot(**defaults)


def make_test_photo(w=200, h=300, color=(255, 0, 0, 255)) -> Image.Image:
    return Image.new("RGBA", (w, h), color)


def test_cover_mode_correct_size():
    slot = make_photo_slot(w=300, h=400, fit_mode="cover")
    photo = make_test_photo(200, 300)
    result = fit_photo(photo, slot)
    assert result.size == (300, 400)


def test_contain_mode_correct_size():
    slot = make_photo_slot(w=300, h=400, fit_mode="contain")
    photo = make_test_photo(200, 300)
    result = fit_photo(photo, slot)
    assert result.size == (300, 400)


def test_stretch_mode_correct_size():
    slot = make_photo_slot(w=300, h=400, fit_mode="stretch")
    photo = make_test_photo(200, 300)
    result = fit_photo(photo, slot)
    assert result.size == (300, 400)


def test_cover_fills_slot():
    slot = make_photo_slot(w=100, h=100, fit_mode="cover")
    photo = make_test_photo(200, 100, color=(255, 0, 0, 255))
    result = fit_photo(photo, slot)
    center_pixel = result.getpixel((50, 50))
    assert center_pixel[3] == 255


def test_contain_may_have_transparent_borders():
    slot = make_photo_slot(w=100, h=100, fit_mode="contain")
    photo = make_test_photo(200, 100, color=(255, 0, 0, 255))
    result = fit_photo(photo, slot)
    assert result.size == (100, 100)
    top_pixel = result.getpixel((50, 0))
    assert top_pixel[3] == 0


def test_corner_radius():
    img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
    result = apply_corner_radius(img, radius=10)
    corner = result.getpixel((0, 0))
    assert corner[3] == 0


def test_zero_corner_radius_no_change():
    img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
    result = apply_corner_radius(img, radius=0)
    corner = result.getpixel((0, 0))
    assert corner[3] == 255


def test_cover_with_tall_photo():
    slot = make_photo_slot(w=300, h=200, fit_mode="cover")
    photo = make_test_photo(100, 400)
    result = fit_photo(photo, slot)
    assert result.size == (300, 200)
