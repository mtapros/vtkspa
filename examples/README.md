# VTK SPA Examples

This directory contains a self-contained working example demonstrating the full VTK SPA workflow.

## Files

- `template/` — Sample trading card template (JSON + assets)
- `photos/` — 3 tiny synthetic subject PNGs
- `roster.csv` — 3-row sample CSV

## Running the example

1. Install VTK SPA:
```bash
pip install -e .
```

2. Validate the template:
```bash
vtkspa validate examples/template
```

3. Render a single composite:
```bash
vtkspa render examples/template \
  --data '{"name": "Jane Smith", "team": "Red Sox", "number": "23"}' \
  --photo examples/photos/jane_smith.png \
  -o /tmp/jane_preview.jpg
```

4. Run the full batch:
```bash
vtkspa batch examples/template \
  --csv examples/roster.csv \
  --photos examples/photos \
  -o /tmp/vtkspa_output
```

Output files will be in `/tmp/vtkspa_output/`.
