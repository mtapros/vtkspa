"""CSV parsing, column mapping, validation, and photo filename matching."""
from __future__ import annotations

import csv
import logging
import re
from pathlib import Path

from vtkspa.models import RosterRow

logger = logging.getLogger(__name__)


def _normalize_name(s: str) -> str:
    """Normalize a filename/name for fuzzy matching."""
    s = s.lower()
    return re.sub(r"[_\-\s\.]+", "", s)


def parse_csv(
    csv_path: str | Path,
    column_mapping: dict[str, str] | None = None,
    computed_fields: dict[str, str] | None = None,
) -> list[RosterRow]:
    """Parse a CSV roster file."""
    csv_path = Path(csv_path)
    column_mapping = column_mapping or {}
    computed_fields = computed_fields or {}
    rows: list[RosterRow] = []

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, raw_row in enumerate(reader):
            mapped: dict[str, str] = {}
            for key, value in raw_row.items():
                stripped = key.strip() if key else key
                if stripped in column_mapping:
                    mapped[column_mapping[stripped]] = (value or "").strip()
                else:
                    mapped[stripped] = (value or "").strip()
            for out_field, template_str in computed_fields.items():
                try:
                    mapped[out_field] = template_str.format(**mapped)
                except KeyError as exc:
                    logger.warning("Row %s: computed field %r missing key %s", index, out_field, exc)
            rows.append(RosterRow(data=mapped, row_index=index))

    return rows


def validate_rows(rows: list[RosterRow], required_fields: list[str]) -> list[dict]:
    """Validate rows for required fields. Returns list of error dicts."""
    errors: list[dict] = []
    for row in rows:
        missing = [field for field in required_fields if not row.data.get(field)]
        if missing:
            errors.append({"row_index": row.row_index, "missing_fields": missing, "data": row.data})
    return errors


def match_photos(
    rows: list[RosterRow],
    photos_dir: str | Path,
    name_fields: list[str] | None = None,
) -> tuple[list[RosterRow], list[str], list[str]]:
    """Match roster rows to subject photo files."""
    photos_dir = Path(photos_dir)
    if name_fields is None:
        name_fields = ["name", "first_name", "last_name"]
    if not photos_dir.exists():
        return rows, [str(row.row_index) for row in rows], []

    extensions = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
    photo_files = [path for path in photos_dir.iterdir() if path.is_file() and path.suffix.lower() in extensions]
    photo_norm = {_normalize_name(path.stem): path for path in photo_files}

    unmatched_photos = {str(path) for path in photo_files}
    unmatched_rows: list[str] = []
    matched_rows: list[RosterRow] = []

    for row in rows:
        explicit_name = row.data.get("photo_file")
        if explicit_name:
            explicit = photos_dir / explicit_name
            if explicit.exists():
                row.photo_path = str(explicit)
                matched_rows.append(row)
                unmatched_photos.discard(str(explicit))
                continue

        matched = False
        for field in name_fields:
            value = row.data.get(field, "")
            if not value:
                continue
            normalized = _normalize_name(value)
            if normalized in photo_norm:
                row.photo_path = str(photo_norm[normalized])
                matched_rows.append(row)
                unmatched_photos.discard(row.photo_path)
                matched = True
                break
            tokens = re.findall(r"[a-z0-9]+", normalized)
            for norm_stem, photo_file in photo_norm.items():
                if all(token in norm_stem for token in tokens):
                    row.photo_path = str(photo_file)
                    matched_rows.append(row)
                    unmatched_photos.discard(row.photo_path)
                    matched = True
                    break
            if matched:
                break

        if not matched:
            matched_rows.append(row)
            unmatched_rows.append(str(row.row_index))

    return matched_rows, unmatched_rows, list(unmatched_photos)
