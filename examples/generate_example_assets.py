#!/usr/bin/env python3
"""Generate example assets for vtkspa examples."""
import csv
import json
from pathlib import Path

from PIL import Image, ImageDraw

SCRIPT_DIR = Path(__file__).parent


def make_background(out_path: Path, w: int = 600, h: int = 800) -> None:
    img = Image.new("RGB", (w, h), (30, 60, 120))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, h - 120), (w, h)], fill=(200, 20, 20))
    img.save(out_path)


def make_subject_photo(out_path: Path, color: tuple[int, int, int], w: int = 150, h: int = 200) -> None:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([(30, 10), (120, 80)], fill=color + (255,))
    draw.rectangle([(40, 80), (110, 180)], fill=color + (200,))
    img.save(out_path)


def generate() -> None:
    template_dir = SCRIPT_DIR / "template"
    assets_dir = template_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    photos_dir = SCRIPT_DIR / "photos"
    photos_dir.mkdir(exist_ok=True)

    make_background(assets_dir / "background.png", 600, 800)

    template = {
        "schema_version": "vtkspa_v1",
        "name": "trading_card",
        "canvas": {"width": 600, "height": 800, "dpi": 300, "background_color": [30, 60, 120, 255]},
        "layers": [
            {
                "layer_type": "image",
                "id": "background",
                "name": "Background",
                "asset_path": "background.png",
                "x": 0,
                "y": 0,
                "w": 600,
                "h": 800,
                "opacity": 1.0,
                "rotation": 0.0,
                "visible": True,
            },
            {
                "layer_type": "photo_slot",
                "id": "player_photo",
                "name": "Player Photo",
                "x": 50,
                "y": 50,
                "w": 500,
                "h": 550,
                "fit_mode": "contain",
                "anchor_h": "center",
                "anchor_v": "center",
                "corner_radius": 10,
                "mask_asset_path": "",
                "visible": True,
            },
            {
                "layer_type": "text_slot",
                "id": "player_name",
                "name": "Player Name",
                "x": 30,
                "y": 620,
                "w": 540,
                "h": 80,
                "font_family": "DejaVuSans",
                "font_path": "",
                "base_font_size": 60,
                "min_font_size": 18,
                "fill_color": [255, 255, 255, 255],
                "stroke_color": [0, 0, 0, 255],
                "stroke_width": 2,
                "align": "center",
                "valign": "center",
                "data_field": "name",
                "all_caps": True,
                "max_lines": 1,
                "sample_text": "PLAYER NAME",
                "visible": True,
            },
            {
                "layer_type": "text_slot",
                "id": "team_name",
                "name": "Team Name",
                "x": 30,
                "y": 710,
                "w": 400,
                "h": 60,
                "font_family": "DejaVuSans",
                "font_path": "",
                "base_font_size": 36,
                "min_font_size": 12,
                "fill_color": [255, 220, 50, 255],
                "stroke_color": [0, 0, 0, 0],
                "stroke_width": 0,
                "align": "left",
                "valign": "center",
                "data_field": "team",
                "all_caps": False,
                "max_lines": 1,
                "sample_text": "Team Name",
                "visible": True,
            },
            {
                "layer_type": "text_slot",
                "id": "jersey_number",
                "name": "Jersey Number",
                "x": 500,
                "y": 710,
                "w": 70,
                "h": 60,
                "font_family": "DejaVuSans",
                "font_path": "",
                "base_font_size": 48,
                "min_font_size": 20,
                "fill_color": [255, 255, 255, 255],
                "stroke_color": [0, 0, 0, 0],
                "stroke_width": 0,
                "align": "right",
                "valign": "center",
                "data_field": "number",
                "all_caps": False,
                "max_lines": 1,
                "sample_text": "00",
                "visible": True,
            },
        ],
    }
    with open(template_dir / "template.json", "w", encoding="utf-8") as handle:
        json.dump(template, handle, indent=2)

    players = [
        ("jane_smith", (180, 120, 80)),
        ("bob_jones", (120, 150, 200)),
        ("maria_garcia", (200, 160, 100)),
    ]
    for filename, color in players:
        make_subject_photo(photos_dir / f"{filename}.png", color)

    roster = [
        {"name": "Jane Smith", "team": "Red Sox", "number": "23"},
        {"name": "Bob Jones", "team": "Yankees", "number": "7"},
        {"name": "Maria Garcia", "team": "Cubs", "number": "42"},
    ]
    with open(SCRIPT_DIR / "roster.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["name", "team", "number"])
        writer.writeheader()
        writer.writerows(roster)

    print("Example assets generated!")
    print(f"  Template: {template_dir}/template.json")
    print(f"  Photos: {photos_dir}/")
    print(f"  Roster: {SCRIPT_DIR}/roster.csv")


if __name__ == "__main__":
    generate()
