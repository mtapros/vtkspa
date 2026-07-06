from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class CanvasConfig:
    width: int
    height: int
    dpi: int = 300
    background_color: tuple[int, int, int, int] = (255, 255, 255, 255)


@dataclass
class ImageLayer:
    layer_type: Literal["image"] = "image"
    id: str = ""
    name: str = ""
    asset_path: str = ""
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    opacity: float = 1.0
    rotation: float = 0.0
    visible: bool = True


@dataclass
class PhotoSlot:
    layer_type: Literal["photo_slot"] = "photo_slot"
    id: str = ""
    name: str = ""
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    fit_mode: Literal["cover", "contain", "stretch"] = "cover"
    anchor_h: Literal["left", "center", "right"] = "center"
    anchor_v: Literal["top", "center", "bottom"] = "center"
    corner_radius: int = 0
    mask_asset_path: str = ""
    visible: bool = True


@dataclass
class TextSlot:
    layer_type: Literal["text_slot"] = "text_slot"
    id: str = ""
    name: str = ""
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    font_family: str = "DejaVuSans"
    font_path: str = ""
    base_font_size: int = 48
    min_font_size: int = 12
    fill_color: tuple[int, int, int, int] = (0, 0, 0, 255)
    stroke_color: tuple[int, int, int, int] = (0, 0, 0, 0)
    stroke_width: int = 0
    align: Literal["left", "center", "right"] = "center"
    valign: Literal["top", "center", "bottom"] = "center"
    data_field: str = ""
    all_caps: bool = False
    max_lines: int = 1
    sample_text: str = ""
    visible: bool = True


Layer = ImageLayer | PhotoSlot | TextSlot


@dataclass
class Template:
    schema_version: str = "vtkspa_v1"
    name: str = ""
    canvas: CanvasConfig = field(default_factory=lambda: CanvasConfig(width=800, height=600))
    layers: list[Layer] = field(default_factory=list)


@dataclass
class RosterRow:
    data: dict[str, str] = field(default_factory=dict)
    photo_path: str = ""
    row_index: int = 0


@dataclass
class RenderJob:
    template: Template
    template_dir: str
    roster_row: RosterRow
    output_path: str
    jpeg_quality: int = 95
