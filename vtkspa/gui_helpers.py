from __future__ import annotations

from typing import Any


def format_psd_import_summary(report: dict[str, Any], output_dir: str) -> list[str]:
    warnings = report.get("warnings") or []
    return [
        f"✓ Imported PSD: {report.get('source', '(unknown)')}",
        f"  Layers imported: {len(report.get('layers_imported') or [])}",
        f"  Static groups flattened: {len(report.get('layers_flattened') or [])}",
        *[f"  ⚠ {warning}" for warning in warnings],
        f"  Output: {output_dir}",
    ]
