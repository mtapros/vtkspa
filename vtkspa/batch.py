"""Headless batch orchestrator: template + roster + photos → outputs."""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from vtkspa.data.roster import match_photos, parse_csv
from vtkspa.models import RosterRow
from vtkspa.render.engine import RenderEngine
from vtkspa.template.schema import load_template

logger = logging.getLogger(__name__)


@dataclass
class BatchOptions:
    jpeg_quality: int = 95
    output_pattern: str = "{name_slug}_{template_name}"
    column_mapping: dict[str, str] = field(default_factory=dict)
    computed_fields: dict[str, str] = field(default_factory=dict)
    name_fields: list[str] = field(default_factory=lambda: ["name", "first_name", "last_name"])
    continue_on_error: bool = True
    dpi: int = 300


@dataclass
class BatchResult:
    successes: list[dict] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)
    unmatched_rows: list[str] = field(default_factory=list)
    unmatched_photos: list[str] = field(default_factory=list)
    total_rows: int = 0
    elapsed_seconds: float = 0.0


def _slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower().strip()).strip("_")


def _build_output_name(pattern: str, data: dict[str, str], template_name: str, ext: str = ".jpg") -> str:
    context = dict(data)
    for key, value in list(context.items()):
        context[f"{key}_slug"] = _slugify(value)
    context["template_name"] = _slugify(template_name)
    context["name_slug"] = _slugify(data.get("name", data.get("first_name", "player")))
    try:
        name = pattern.format(**context)
    except KeyError as exc:
        logger.warning("Output pattern key %s not found, using fallback", exc)
        name = f"output_{context.get('name_slug', 'unknown')}"
    return name + ext


def run_batch(
    template_path: str | Path,
    csv_path: str | Path,
    photos_dir: str | Path,
    output_dir: str | Path,
    options: BatchOptions | None = None,
    on_row_start: Callable[[int, RosterRow], None] | None = None,
    on_row_done: Callable[[int, RosterRow, str], None] | None = None,
    on_row_fail: Callable[[int, RosterRow, Exception], None] | None = None,
) -> BatchResult:
    """Run a batch render job."""
    options = options or BatchOptions()
    template_path = Path(template_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    template = load_template(template_path)
    engine = RenderEngine()
    rows = parse_csv(csv_path, column_mapping=options.column_mapping, computed_fields=options.computed_fields)
    rows, unmatched_row_idxs, unmatched_photos = match_photos(rows, photos_dir, name_fields=options.name_fields)

    result = BatchResult(
        total_rows=len(rows),
        unmatched_rows=unmatched_row_idxs,
        unmatched_photos=unmatched_photos,
    )

    for index, row in enumerate(rows):
        if on_row_start:
            on_row_start(index, row)
        try:
            img = engine.render(
                template=template,
                template_dir=template_path,
                data_context=row.data,
                photo_path=row.photo_path if row.photo_path else None,
                jpeg_quality=options.jpeg_quality,
            )
            out_name = _build_output_name(options.output_pattern, row.data, template.name, ext=".jpg")
            out_path = output_dir / out_name
            engine.save(img, out_path, jpeg_quality=options.jpeg_quality, dpi=options.dpi)
            result.successes.append({"row_index": row.row_index, "output": str(out_path), "data": row.data})
            if on_row_done:
                on_row_done(index, row, str(out_path))
        except Exception as exc:
            logger.error("Row %s failed: %s", index, exc)
            result.failures.append({"row_index": row.row_index, "error": str(exc), "data": row.data})
            if on_row_fail:
                on_row_fail(index, row, exc)
            if not options.continue_on_error:
                raise

    result.elapsed_seconds = time.time() - start_time
    report = {
        "total_rows": result.total_rows,
        "successes": len(result.successes),
        "failures": len(result.failures),
        "unmatched_rows": result.unmatched_rows,
        "unmatched_photos": result.unmatched_photos,
        "elapsed_seconds": result.elapsed_seconds,
        "outputs": result.successes,
        "errors": result.failures,
    }
    with open(output_dir / "batch_report.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    return result
