"""Tests for roster CSV parsing, column mapping, and photo matching."""
import csv
import tempfile
from pathlib import Path

from PIL import Image

from vtkspa.data.roster import match_photos, parse_csv, validate_rows
from vtkspa.models import RosterRow


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_parse_csv_basic():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "roster.csv"
        write_csv(
            path,
            [
                {"name": "Alice Smith", "team": "Red Sox", "number": "7"},
                {"name": "Bob Jones", "team": "Yankees", "number": "42"},
            ],
            ["name", "team", "number"],
        )
        rows = parse_csv(path)
        assert len(rows) == 2
        assert rows[0].data["name"] == "Alice Smith"
        assert rows[1].data["number"] == "42"


def test_parse_csv_column_mapping():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "roster.csv"
        write_csv(path, [{"Player Name": "Alice Smith", "Team Name": "Red Sox"}], ["Player Name", "Team Name"])
        rows = parse_csv(path, column_mapping={"Player Name": "name", "Team Name": "team"})
        assert rows[0].data["name"] == "Alice Smith"
        assert rows[0].data["team"] == "Red Sox"


def test_parse_csv_computed_fields():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "roster.csv"
        write_csv(path, [{"first_name": "Alice", "last_name": "Smith"}], ["first_name", "last_name"])
        rows = parse_csv(path, computed_fields={"name": "{first_name} {last_name}"})
        assert rows[0].data["name"] == "Alice Smith"


def test_validate_rows_missing_fields():
    rows = [
        RosterRow(data={"name": "Alice", "team": "Red Sox"}, row_index=0),
        RosterRow(data={"name": "", "team": "Yankees"}, row_index=1),
    ]
    errors = validate_rows(rows, required_fields=["name", "team"])
    assert len(errors) == 1
    assert errors[0]["row_index"] == 1


def test_match_photos_exact():
    with tempfile.TemporaryDirectory() as tmp:
        photos_dir = Path(tmp) / "photos"
        photos_dir.mkdir()
        img = Image.new("RGBA", (10, 10), (255, 0, 0, 255))
        img.save(photos_dir / "alice_smith.png")
        img.save(photos_dir / "bob_jones.png")

        rows = [
            RosterRow(data={"name": "Alice Smith"}, row_index=0),
            RosterRow(data={"name": "Bob Jones"}, row_index=1),
        ]
        matched, unmatched_rows, unmatched_photos = match_photos(rows, photos_dir)

        assert matched[0].photo_path.endswith("alice_smith.png")
        assert matched[1].photo_path.endswith("bob_jones.png")
        assert unmatched_rows == []
        assert unmatched_photos == []


def test_match_photos_explicit_file():
    with tempfile.TemporaryDirectory() as tmp:
        photos_dir = Path(tmp) / "photos"
        photos_dir.mkdir()
        img = Image.new("RGBA", (10, 10))
        img.save(photos_dir / "player7.png")

        rows = [RosterRow(data={"name": "Alice Smith", "photo_file": "player7.png"}, row_index=0)]
        matched, unmatched_rows, unmatched_photos = match_photos(rows, photos_dir)
        assert matched[0].photo_path.endswith("player7.png")
        assert unmatched_rows == []


def test_match_photos_unmatched():
    with tempfile.TemporaryDirectory() as tmp:
        photos_dir = Path(tmp) / "photos"
        photos_dir.mkdir()
        img = Image.new("RGBA", (10, 10))
        img.save(photos_dir / "charlie_brown.png")

        rows = [RosterRow(data={"name": "Alice Smith"}, row_index=0)]
        matched, unmatched_rows, unmatched_photos = match_photos(rows, photos_dir)
        assert "0" in unmatched_rows
        assert any("charlie_brown" in path for path in unmatched_photos)
