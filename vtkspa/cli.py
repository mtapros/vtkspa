"""Command-line interface for VTK SPA."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger("vtkspa")


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def cmd_import_psd(args: argparse.Namespace) -> int:
    from vtkspa.template.psd_importer import import_psd

    try:
        report = import_psd(args.psd, args.output)
        print(f"✓ Imported PSD: {args.psd}")
        print(f"  Layers imported: {len(report['layers_imported'])}")
        print(f"  Static groups flattened: {len(report['layers_flattened'])}")
        if report["warnings"]:
            for warning in report["warnings"]:
                print(f"  ⚠ {warning}")
        print(f"  Output: {args.output}")
        return 0
    except Exception as exc:
        print(f"✗ PSD import failed: {exc}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    from vtkspa.template.schema import load_template, validate_template

    try:
        template = load_template(args.template_dir)
        errors = validate_template(template, args.template_dir)
        if errors:
            print(f"✗ Validation failed: {len(errors)} issue(s)")
            for error in errors:
                print(f"  • {error}")
            return 1
        print(f"✓ Template valid: {template.name!r} ({len(template.layers)} layers)")
        return 0
    except Exception as exc:
        print(f"✗ Could not load template: {exc}", file=sys.stderr)
        return 1


def cmd_render(args: argparse.Namespace) -> int:
    from vtkspa.render.engine import RenderEngine
    from vtkspa.template.schema import load_template

    try:
        template = load_template(args.template_dir)
        data = json.loads(args.data) if args.data else {}
        engine = RenderEngine()
        img = engine.render(
            template=template,
            template_dir=args.template_dir,
            data_context=data,
            photo_path=args.photo,
        )
        engine.save(img, args.output)
        print(f"✓ Rendered: {args.output}")
        return 0
    except Exception as exc:
        print(f"✗ Render failed: {exc}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


def cmd_batch(args: argparse.Namespace) -> int:
    from vtkspa.batch import BatchOptions, run_batch

    options = BatchOptions(jpeg_quality=args.quality, output_pattern=args.pattern, continue_on_error=True)
    if args.column_map:
        for item in args.column_map:
            key, _, value = item.partition("=")
            options.column_mapping[key.strip()] = value.strip()

    def on_start(index, row):
        name = row.data.get("name", row.data.get("first_name", f"row {index}"))
        print(f"  [{index + 1}] Rendering {name!r}...", end="\r")

    def on_done(index, row, path):
        name = row.data.get("name", row.data.get("first_name", f"row {index}"))
        print(f"  [{index + 1}] ✓ {name!r} → {path}")

    def on_fail(index, row, exc):
        name = row.data.get("name", row.data.get("first_name", f"row {index}"))
        print(f"  [{index + 1}] ✗ {name!r}: {exc}")

    print("Starting batch render...")
    print(f"  Template: {args.template_dir}")
    print(f"  CSV: {args.csv}")
    print(f"  Photos: {args.photos}")
    print(f"  Output: {args.output}")

    result = run_batch(
        template_path=args.template_dir,
        csv_path=args.csv,
        photos_dir=args.photos,
        output_dir=args.output,
        options=options,
        on_row_start=on_start,
        on_row_done=on_done,
        on_row_fail=on_fail,
    )

    print(f"\nBatch complete: {len(result.successes)} succeeded, {len(result.failures)} failed")
    print(f"  Elapsed: {result.elapsed_seconds:.1f}s")
    if result.unmatched_rows:
        print(f"  ⚠ {len(result.unmatched_rows)} rows without photos")
    if result.unmatched_photos:
        print(f"  ⚠ {len(result.unmatched_photos)} photos unmatched")
    print(f"  Report: {Path(args.output) / 'batch_report.json'}")
    return 0 if not result.failures else 1


def cmd_gui(args: argparse.Namespace) -> int:
    from vtkspa.gui import main as gui_main

    gui_main()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vtkspa", description="VTK SPA — Photoshop-free Sports Photo Automation")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p_import = sub.add_parser("import-psd", help="Convert a PSD to native template")
    p_import.add_argument("psd", help="Input PSD file")
    p_import.add_argument("-o", "--output", required=True, help="Output template directory")

    p_validate = sub.add_parser("validate", help="Validate a template directory")
    p_validate.add_argument("template_dir", help="Template directory")

    p_render = sub.add_parser("render", help="Render a single composite")
    p_render.add_argument("template_dir", help="Template directory")
    p_render.add_argument("--data", default="{}", help="JSON data context e.g. '{\"name\":\"Jane\"}'")
    p_render.add_argument("--photo", default=None, help="Subject photo path")
    p_render.add_argument("-o", "--output", required=True, help="Output file (.jpg or .png)")

    p_batch = sub.add_parser("batch", help="Batch render from CSV roster")
    p_batch.add_argument("template_dir", help="Template directory")
    p_batch.add_argument("--csv", required=True, help="Roster CSV file")
    p_batch.add_argument("--photos", required=True, help="Photos directory")
    p_batch.add_argument("-o", "--output", required=True, help="Output directory")
    p_batch.add_argument("--pattern", default="{name_slug}_{template_name}", help="Output filename pattern")
    p_batch.add_argument("--quality", type=int, default=95, help="JPEG quality (1-100)")
    p_batch.add_argument("--column-map", action="append", metavar="CSV_COL=FIELD", help="Map CSV column to data field (repeatable)")

    sub.add_parser("gui", help="Launch the graphical interface")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    _setup_logging(getattr(args, "verbose", False))

    dispatch = {
        "import-psd": cmd_import_psd,
        "validate": cmd_validate,
        "render": cmd_render,
        "batch": cmd_batch,
        "gui": cmd_gui,
    }
    fn = dispatch.get(args.command)
    if fn is None:
        parser.print_help()
        sys.exit(1)
    sys.exit(fn(args))


if __name__ == "__main__":
    main()
