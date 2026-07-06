"""Shared fixtures for vtkspa tests."""
from pathlib import Path

import pytest


@pytest.fixture
def sample_template_dir(tmp_path):
    """Create a minimal sample template directory for testing."""
    from PIL import Image

    from vtkspa.models import CanvasConfig, ImageLayer, PhotoSlot, Template, TextSlot
    from vtkspa.template.schema import save_template

    assets = tmp_path / "assets"
    assets.mkdir()
    bg = Image.new("RGB", (600, 400), (100, 150, 200))
    bg.save(assets / "background.png")

    template = Template(
        name="sample",
        canvas=CanvasConfig(width=600, height=400, dpi=150),
        layers=[
            ImageLayer(id="bg", asset_path="background.png", x=0, y=0, w=600, h=400),
            PhotoSlot(id="photo", x=20, y=20, w=200, h=280, fit_mode="cover"),
            TextSlot(id="name", x=240, y=30, w=340, h=60, data_field="name", base_font_size=40, min_font_size=10, fill_color=(255, 255, 255, 255)),
            TextSlot(id="team", x=240, y=110, w=340, h=50, data_field="team", base_font_size=30, min_font_size=8, fill_color=(255, 255, 0, 255)),
        ],
    )
    save_template(template, tmp_path)
    return tmp_path
