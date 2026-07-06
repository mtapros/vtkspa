# VTK SPA — Sports Photo Automation

A Photoshop-free Python tool for batch-producing personalized sports composites (memory mates, trading cards, banners). Replicates the core functionality of Pixnub's Sports Photo Automation plugin with no Adobe dependency.

## Architecture

VTK SPA uses a **PSD Import Wizard → Native Template** approach:
1. Import PSD files once → converts to a native JSON template format
2. Runtime rendering uses a pure Python/Pillow compositing engine

## Install

```bash
pip install -e .
# or
pip install vtkspa
```

## Quick Start

```bash
# Generate example assets
python examples/generate_example_assets.py

# Validate template
vtkspa validate examples/template

# Single render
vtkspa render examples/template \
  --data '{"name": "Jane Smith", "team": "Red Sox", "number": "23"}' \
  --photo examples/photos/jane_smith.png \
  -o /tmp/preview.jpg

# Batch render from CSV
vtkspa batch examples/template \
  --csv examples/roster.csv \
  --photos examples/photos \
  -o /tmp/output
```

## Import a PSD

```bash
vtkspa import-psd my_design.psd -o templates/my_template/
```

**PSD naming conventions:**
- `@photo` or `@photo:slotname` → photo slot (placeholder for subject images)
- `@text:fieldname` → text slot bound to CSV column `fieldname` (e.g. `@text:name`, `@text:team`, `@text:number`)
- Everything else → rasterized to static PNG art

## Native Template Format

Templates live in a directory with:
- `template.json` — layered design definition
- `assets/` — PNG assets (backgrounds, logos, frames)

### Canvas
```json
{
  "schema_version": "vtkspa_v1",
  "name": "trading_card",
  "canvas": {
    "width": 600, "height": 800, "dpi": 300,
    "background_color": [255, 255, 255, 255]
  },
  "layers": [...]
}
```

### Layer types

**image** — static art:
```json
{
  "layer_type": "image",
  "id": "background",
  "asset_path": "background.png",
  "x": 0, "y": 0, "w": 600, "h": 800,
  "opacity": 1.0, "rotation": 0.0
}
```

**photo_slot** — subject photo placeholder:
```json
{
  "layer_type": "photo_slot",
  "id": "player_photo",
  "x": 50, "y": 50, "w": 500, "h": 550,
  "fit_mode": "cover",
  "anchor_h": "center", "anchor_v": "center",
  "corner_radius": 10
}
```

Fit modes: `cover` (fill + crop), `contain` (letterbox), `stretch`

**text_slot** — data-driven text:
```json
{
  "layer_type": "text_slot",
  "id": "player_name",
  "x": 30, "y": 620, "w": 540, "h": 80,
  "data_field": "name",
  "base_font_size": 60, "min_font_size": 18,
  "fill_color": [255, 255, 255, 255],
  "align": "center", "valign": "center",
  "all_caps": true
}
```

## CLI Reference

```
vtkspa import-psd <psd> -o <template_dir>
vtkspa validate <template_dir>
vtkspa render <template_dir> --data '{"name":"..."}' --photo <img> -o <out.jpg>
vtkspa batch <template_dir> --csv <roster.csv> --photos <dir> -o <output_dir>
         [--pattern "{name_slug}_{template_name}"]
         [--quality 95]
         [--column-map "CSV Column=field_name"]
```

## Roadmap

- GUI (Tkinter or PyQt6 — no Adobe required)
- Skia-python render backend for advanced blend modes / shadows
- Team composites (multi-player layouts)
- Watch-folder / hot-folder batch mode
- Cloud rendering API
