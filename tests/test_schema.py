"""Tests for template schema load/save/validate round-trip."""
from pathlib import Path
import tempfile

from vtkspa.models import CanvasConfig, ImageLayer, PhotoSlot, Template, TextSlot
from vtkspa.template.schema import load_template, save_template, validate_template


def make_simple_template() -> Template:
    canvas = CanvasConfig(width=800, height=600, dpi=300)
    layers = [
        ImageLayer(id="bg", name="background", asset_path="bg.png", x=0, y=0, w=800, h=600),
        PhotoSlot(id="photo1", name="player photo", x=100, y=100, w=300, h=400, fit_mode="cover"),
        TextSlot(
            id="name_slot",
            name="player name",
            x=50,
            y=520,
            w=700,
            h=60,
            data_field="name",
            base_font_size=48,
            min_font_size=12,
            fill_color=(255, 255, 255, 255),
        ),
    ]
    return Template(name="test_template", canvas=canvas, layers=layers)


def test_save_and_load_roundtrip():
    template = make_simple_template()
    with tempfile.TemporaryDirectory() as tmp:
        save_template(template, tmp)
        assert (Path(tmp) / "template.json").exists()
        loaded = load_template(tmp)
        assert loaded.name == template.name
        assert loaded.canvas.width == 800
        assert loaded.canvas.height == 600
        assert len(loaded.layers) == 3
        assert loaded.layers[0].id == "bg"
        assert isinstance(loaded.layers[1], PhotoSlot)
        assert loaded.layers[1].fit_mode == "cover"
        assert isinstance(loaded.layers[2], TextSlot)
        assert loaded.layers[2].data_field == "name"


def test_load_from_json_file():
    template = make_simple_template()
    with tempfile.TemporaryDirectory() as tmp:
        save_template(template, tmp)
        loaded = load_template(Path(tmp) / "template.json")
        assert loaded.name == template.name


def test_validate_passes_on_valid_template():
    template = make_simple_template()
    errors = validate_template(template)
    assert errors == []


def test_validate_catches_duplicate_ids():
    template = make_simple_template()
    template.layers[2].id = "bg"
    errors = validate_template(template)
    assert any("Duplicate" in error for error in errors)


def test_validate_catches_missing_data_field():
    template = make_simple_template()
    template.layers[2].data_field = ""
    errors = validate_template(template)
    assert any("data_field" in error for error in errors)


def test_validate_catches_invalid_fit_mode():
    template = make_simple_template()
    template.layers[1].fit_mode = "invalid_mode"
    errors = validate_template(template)
    assert any("fit_mode" in error for error in errors)


def test_color_roundtrip():
    template = make_simple_template()
    template.layers[2].fill_color = (255, 128, 0, 200)
    with tempfile.TemporaryDirectory() as tmp:
        save_template(template, tmp)
        loaded = load_template(tmp)
        assert loaded.layers[2].fill_color == (255, 128, 0, 200)
