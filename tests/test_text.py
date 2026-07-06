"""Tests for text rendering: auto-shrink, wrapping, alignment."""
from PIL import Image, ImageDraw

from vtkspa.models import TextSlot
from vtkspa.render.text import find_font, measure_text, render_text_slot, wrap_text


def make_text_slot(**kwargs) -> TextSlot:
    defaults = dict(
        id="t1",
        name="name slot",
        x=0,
        y=0,
        w=300,
        h=60,
        font_path="",
        font_family="DejaVuSans",
        base_font_size=40,
        min_font_size=8,
        fill_color=(0, 0, 0, 255),
        stroke_color=(0, 0, 0, 0),
        stroke_width=0,
        align="center",
        valign="center",
        data_field="name",
        all_caps=False,
        max_lines=1,
    )
    defaults.update(kwargs)
    return TextSlot(**defaults)


def test_find_font_returns_something():
    font = find_font("", "DejaVuSans", 24)
    assert font is not None


def test_measure_text_positive():
    font = find_font("", "DejaVuSans", 24)
    width, height = measure_text("Hello", font)
    assert width > 0
    assert height > 0


def test_wrap_text_single_word():
    font = find_font("", "DejaVuSans", 24)
    lines = wrap_text("Hello", font, 500, 1)
    assert len(lines) == 1
    assert lines[0] == "Hello"


def test_wrap_text_multiple_words():
    font = find_font("", "DejaVuSans", 24)
    lines = wrap_text("Hello World Test", font, 1000, 2)
    assert len(lines) >= 1
    combined = " ".join(lines)
    assert "Hello" in combined


def test_short_name_no_shrink():
    slot = make_text_slot(w=400, h=80, base_font_size=40, min_font_size=8)
    img = Image.new("RGBA", (400, 80), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    render_text_slot(draw, slot, "Joe")


def test_long_name_shrinks():
    slot = make_text_slot(w=200, h=40, base_font_size=40, min_font_size=8)
    img = Image.new("RGBA", (200, 40), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    render_text_slot(draw, slot, "Alexander Hamilton Worthington III")
    pixels = list(img.getdata())
    non_white = [pixel for pixel in pixels if pixel != (255, 255, 255, 255)]
    assert len(non_white) > 0


def test_all_caps():
    slot = make_text_slot(all_caps=True, w=400, h=80)
    img = Image.new("RGBA", (400, 80), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    render_text_slot(draw, slot, "lowercase text")


def test_empty_text_no_crash():
    slot = make_text_slot()
    img = Image.new("RGBA", (300, 60), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    render_text_slot(draw, slot, "")
