"""Tests for batch orchestrator."""
import csv
import tempfile
from pathlib import Path

from PIL import Image

from vtkspa.batch import BatchOptions, run_batch
from vtkspa.models import CanvasConfig, PhotoSlot, Template, TextSlot
from vtkspa.template.schema import save_template


def make_test_template(tmp_dir: Path) -> None:
    assets = tmp_dir / "assets"
    assets.mkdir(parents=True)
    bg = Image.new("RGB", (400, 300), (200, 200, 200))
    bg.save(assets / "bg.png")

    from vtkspa.models import ImageLayer

    template = Template(
        name="test_card",
        canvas=CanvasConfig(width=400, height=300, dpi=72),
        layers=[
            ImageLayer(id="bg", asset_path="bg.png", x=0, y=0, w=400, h=300),
            PhotoSlot(id="photo", x=10, y=10, w=150, h=200, fit_mode="cover"),
            TextSlot(id="name", x=0, y=230, w=400, h=60, data_field="name", base_font_size=36, min_font_size=8, fill_color=(0, 0, 0, 255)),
        ],
    )
    save_template(template, tmp_dir)


def make_test_photos(photos_dir: Path, names: list[str]) -> None:
    for name in names:
        img = Image.new("RGBA", (100, 150), (255, 100, 50, 255))
        slug = name.lower().replace(" ", "_")
        img.save(photos_dir / f"{slug}.png")


def make_test_csv(csv_path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_batch_happy_path():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        template_dir = tmp / "template"
        photos_dir = tmp / "photos"
        output_dir = tmp / "output"
        photos_dir.mkdir()

        make_test_template(template_dir)
        make_test_photos(photos_dir, ["Alice Smith", "Bob Jones", "Carol White"])

        csv_path = tmp / "roster.csv"
        make_test_csv(csv_path, [{"name": "Alice Smith"}, {"name": "Bob Jones"}, {"name": "Carol White"}])

        result = run_batch(template_path=template_dir, csv_path=csv_path, photos_dir=photos_dir, output_dir=output_dir)

        assert len(result.successes) == 3
        assert len(result.failures) == 0
        assert (output_dir / "batch_report.json").exists()
        for success in result.successes:
            assert Path(success["output"]).exists()


def test_batch_continues_on_error():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        template_dir = tmp / "template"
        photos_dir = tmp / "photos"
        output_dir = tmp / "output"
        photos_dir.mkdir()

        make_test_template(template_dir)
        csv_path = tmp / "roster.csv"
        make_test_csv(csv_path, [{"name": "Alice Smith"}, {"name": "Bob Jones"}])

        options = BatchOptions(continue_on_error=True)
        result = run_batch(
            template_path=template_dir,
            csv_path=csv_path,
            photos_dir=photos_dir,
            output_dir=output_dir,
            options=options,
        )

        assert len(result.successes) == 2


def test_batch_output_pattern():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        template_dir = tmp / "template"
        photos_dir = tmp / "photos"
        output_dir = tmp / "output"
        photos_dir.mkdir()

        make_test_template(template_dir)
        csv_path = tmp / "roster.csv"
        make_test_csv(csv_path, [{"name": "Alice Smith"}])

        options = BatchOptions(output_pattern="{name_slug}_card")
        result = run_batch(
            template_path=template_dir,
            csv_path=csv_path,
            photos_dir=photos_dir,
            output_dir=output_dir,
            options=options,
        )
        assert len(result.successes) == 1
        assert "alice_smith" in result.successes[0]["output"]
